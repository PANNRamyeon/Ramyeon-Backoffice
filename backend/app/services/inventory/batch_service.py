from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from pynamodb.exceptions import UpdateError
from models.Batches import Batch, BatchManager
from models.Product import Product
from models.Shipment import Shipment
from notifications.services import notification_service
from app.services.core.audit_service import AuditLogService
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION
import logging
import boto3

logger = logging.getLogger(__name__)

_SYSTEM_USER = {'user_id': 'system', 'username': 'system', 'branch_id': None, 'source': 'service'}


def _canonical_product_id(product_id: str) -> str:
    """Return product_id in canonical form PROD-xxxxx (5 digits) so it matches Product.SK and batch GSI."""
    if not product_id or not str(product_id).strip():
        return ""
    s = str(product_id).strip().upper()
    if s.startswith("PROD-"):
        num = s[5:].lstrip("0") or "0"
    else:
        num = s.lstrip("0") or "0"
    try:
        n = int(num)
        return f"PROD-{n:05d}"
    except ValueError:
        return s if s.startswith("PROD-") else f"PROD-{s.zfill(5)}"

class BatchService:
    """
    Service layer for batch management operations.
    Uses singleton pattern for efficient resource utilization.
    Import via: from app.utils.singleton import get_singleton
    Usage: batch_service = get_singleton(BatchService)
    """
    
    def __init__(self):
        """Initialize BatchService - called once per application lifecycle via singleton"""
        logger.info("Initializing BatchService singleton instance")
        self._product_name_cache = {}  # Simple cache for product names
        self.audit_service = AuditLogService()

    def _get_product_name(self, product_id: str) -> str:
        """
        Fetch product name with caching for efficiency.
        
        Args:
            product_id: Product ID (e.g., 'PROD-00001')
        
        Returns:
            str: Product name or 'Unknown Product' if not found
        """
        if not product_id:
            return "Unknown Product"
        
        # Check cache first
        if product_id in self._product_name_cache:
            return self._product_name_cache[product_id]
        
        # Fetch from database
        try:
            product = Product.get_by_id(product_id)
            if product:
                product_name = product.product_name
                self._product_name_cache[product_id] = product_name
                return product_name
        except Exception as e:
            logger.warning(f"Failed to fetch product name for {product_id}: {e}")
        
        return "Unknown Product"

    def _send_batch_notification(self, action_type, product_name, additional_metadata=None):
        """Centralized notification helper for batch actions"""
        try:
            titles = {
                'created': "New Batch Added",
                'stock_received': "Stock Received",
                'stock_ordered': "Purchase Order Created",
                'activated': "Stock Activated",
                'expiry_warning': "Expiry Warning",
                'batch_expired': "Batch Expired",
                'batch_depleted': "Batch Depleted",
                'shipment_activated': "Shipment Stock Activated",
                'shipment_cancelled': "Shipment Batches Cancelled",
            }

            messages = {
                'created': f"New batch created for '{product_name}'",
                'stock_received': f"Stock received for '{product_name}'",
                'stock_ordered': f"Purchase order created for '{product_name}'",
                'activated': f"Stock activated for '{product_name}'",
                'expiry_warning': f"Batch expiring soon for '{product_name}'",
                'batch_expired': f"Batch expired for '{product_name}'",
                'batch_depleted': f"Batch depleted for '{product_name}'",
                'shipment_activated': f"Shipment received — stock for '{product_name}' is now available",
                'shipment_cancelled': f"Shipment cancelled — pending stock for '{product_name}' removed",
            }
            
            # Set priority based on action type
            if action_type in ['batch_expired', 'expiry_warning']:
                priority = "high"
                notification_type = "alert"
            elif action_type == 'batch_depleted':
                priority = "medium"
                notification_type = "alert"
            elif action_type in ['stock_ordered', 'activated', 'shipment_activated']:
                priority = "low"
                notification_type = "inventory"
            elif action_type == 'shipment_cancelled':
                priority = "medium"
                notification_type = "inventory"
            else:
                priority = "low"
                notification_type = "system"
            
            metadata = {
                "action_type": f"batch_{action_type}",
                "product_name": product_name
            }
            
            if additional_metadata:
                metadata.update(additional_metadata)
            
            notification_service.create_notification(
                title=titles.get(action_type, "Batch Action"),
                message=messages.get(action_type, f"Batch action '{action_type}' for '{product_name}'"),
                priority=priority,
                notification_type=notification_type,
                metadata=metadata
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                logger.warning(
                    "Batch notification skipped: notifications table/resource not found (create it to enable)."
                )
            else:
                logger.warning("Failed to send batch notification: %s", e)
        except Exception as e:
            logger.warning("Failed to send batch notification: %s", e)

    def _sync_product_totals_from_batches(
        self,
        product_id: str,
        source: str,
        reason: str | None = None,
        include_batch: Optional[Any] = None,
        include_batches: Optional[List[Any]] = None,
    ) -> None:
        """
        Recalculate Product.total_stock from non-expired batches (quantity_remaining),
        and update oldest/newest batch expiry from non-expired batches.

        include_batch / include_batches: When syncing immediately after creating or
        updating batches, pass them here so they are used in the sum. This avoids
        DynamoDB GSI eventual consistency (new/updated items may not appear yet).
        """
        if not product_id or not str(product_id).strip():
            return
        product_id = str(product_id).strip()

        try:
            product = Product.get_by_id(product_id, include_deleted=False)
            if not product:
                logger.warning(f"_sync_product_totals_from_batches: product {product_id} not found")
                return

            try:
                batches = list(Batch.get_by_product_id(product_id, limit=500))
            except Exception as e:
                logger.warning(f"Could not query batches for {product_id} to sync total_stock: {e}")
                batches = []

            valid = [
                b for b in batches
                if getattr(b, "quantity_remaining", 0) and int(b.quantity_remaining) > 0
                and getattr(b, "status", None) not in ["expired", "exhausted"]
                and not b.is_expired()
            ]

            def _batch_sk(b):
                return getattr(b, "sk", None) or getattr(b, "SK", None)

            def _merge_batch(b):
                """Use this batch's data (replacing stale GSI row if present) or add if new."""
                sk = _batch_sk(b)
                if not sk:
                    return
                qty = int(getattr(b, "quantity_remaining", 0) or 0)
                if callable(getattr(b, "is_expired", None)) and b.is_expired():
                    qty = 0
                for i, v in enumerate(valid):
                    if _batch_sk(v) == sk:
                        valid[i] = b
                        return
                if qty > 0:
                    valid.append(b)

            if include_batch is not None:
                _merge_batch(include_batch)
            for b in include_batches or []:
                _merge_batch(b)

            total_remaining = sum(int(b.quantity_remaining) for b in valid)

            expiry_dates = [b.expiry_date.isoformat() for b in valid if getattr(b, "expiry_date", None)]
            oldest_expiry = min(expiry_dates) if expiry_dates else None
            newest_expiry = max(expiry_dates) if expiry_dates else None

            logger.info(
                f"Syncing total_stock for {product_id}: setting to {total_remaining} (source={source}, batches_count={len(valid)})"
            )

            def _do_set(p):
                p.set_total_stock_absolute(
                    new_total_stock=total_remaining,
                    source=source,
                    reason=reason,
                    oldest_expiry=oldest_expiry,
                    newest_expiry=newest_expiry,
                )

            try:
                _do_set(product)
                return
            except UpdateError as first_err:
                # Version conflict is expected when product is updated elsewhere; skip retry and use direct update
                if "ConditionalCheckFailedException" in str(first_err):
                    logger.info(
                        "Product %s version conflict during sync; updating total_stock via direct write.",
                        product_id,
                    )
                    self._update_product_total_stock_direct(product_id, total_remaining, oldest_expiry, newest_expiry)
                    return
                logger.warning(f"First set_total_stock_absolute failed for {product_id}: {first_err}. Retrying.")
            except Exception as first_err:
                logger.warning(
                    f"First set_total_stock_absolute failed for {product_id}: {first_err}. Retrying with fresh product load."
                )
            try:
                product = Product.get_by_id(product_id, include_deleted=False)
                if product:
                    _do_set(product)
                    return
            except Exception as retry_err:
                logger.warning(f"Retry set_total_stock_absolute failed for {product_id}: {retry_err}")

            # Fallback: direct DynamoDB update so total_stock is never left stale (e.g. version conflict or legacy missing version)
            self._update_product_total_stock_direct(product_id, total_remaining, oldest_expiry, newest_expiry)
        except Exception as e:
            logger.warning(f"Could not sync product {product_id} from batches: {e}")

    def _update_product_total_stock_direct(
        self,
        product_id: str,
        total_stock: int,
        oldest_expiry: Optional[str] = None,
        newest_expiry: Optional[str] = None,
    ) -> None:
        """Update product total_stock (and expiry fields) via boto3 when conditional save fails."""
        try:
            client = boto3.client("dynamodb", region_name=AWS_REGION)
            key = {"PK": {"S": "products"}, "SK": {"S": product_id}}
            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"
            expr = "SET #ts = :ts, #upd = :upd, #lsu = :lsu"
            names = {"#ts": "total_stock", "#upd": "updated_at", "#lsu": "last_stock_update"}
            values = {":ts": {"N": str(int(total_stock))}, ":upd": {"S": now}, ":lsu": {"S": now}}
            if oldest_expiry is not None:
                expr += ", #old = :old"
                names["#old"] = "oldest_batch_expiry"
                values[":old"] = {"S": oldest_expiry}
            if newest_expiry is not None:
                expr += ", #new = :new"
                names["#new"] = "newest_batch_expiry"
                values[":new"] = {"S": newest_expiry}
            client.update_item(
                TableName=DYNAMO_TABLE_NAME,
                Key=key,
                UpdateExpression=expr,
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
            logger.info(f"Direct DynamoDB update: {product_id} total_stock={total_stock}")
        except ClientError as e:
            logger.error(f"Direct total_stock update failed for {product_id}: {e}")
        except Exception as e:
            logger.error(f"Direct total_stock update failed for {product_id}: {e}")

    def get_total_stock_from_batches(self, product_id: str) -> int:
        """
        Return the sum of quantity_remaining for all non-expired, non-exhausted batches
        for the product. Used for reconciling 'set' operations and validation.
        """
        if not product_id:
            return 0
        try:
            batches = Batch.get_by_product_id(product_id, limit=500)
        except Exception as e:
            logger.warning(f"Could not query batches for {product_id}: {e}")
            return 0
        valid = [
            b for b in batches
            if getattr(b, "quantity_remaining", 0) and int(b.quantity_remaining) > 0
            and getattr(b, "status", None) not in ["expired", "exhausted"]
            and not b.is_expired()
        ]
        return sum(int(b.quantity_remaining) for b in valid)

    def create_batch(self, batch_data: Dict[str, Any], current_user=None) -> Dict[str, Any]:
        """
        Create a new batch using the Batch model.

        batch_data can include optional shipment_id (SHIP-#####). When provided,
        the batch is linked to that Shipment and the shipment's total_products
        is incremented.
        """
        try:
            product_id = batch_data.get('product_id')
            if not product_id:
                raise ValueError("product_id is required to create a batch")
            shipment_id = batch_data.get('shipment_id')
            logger.info(f"Creating batch for product: {product_id}" + (f" (shipment {shipment_id})" if shipment_id else ""))

            new_batch = Batch.create_batch(**batch_data)

            # Keep Product.total_stock consistent with non-expired batches.
            # Pass the new batch so it's included despite GSI eventual consistency.
            self._sync_product_totals_from_batches(
                product_id,
                source="batch_created",
                reason=f"Batch {new_batch.sk} created",
                include_batch=new_batch,
            )

            if shipment_id:
                try:
                    shipment = Shipment.get_by_id(shipment_id)
                    if shipment and shipment.total_products is not None:
                        shipment.total_products = (shipment.total_products or 0) + 1
                        shipment.updated_at = datetime.utcnow()
                        shipment.save()
                    elif shipment:
                        shipment.total_products = 1
                        shipment.updated_at = datetime.utcnow()
                        shipment.save()
                except Exception as e:
                    logger.warning(f"Could not update Shipment {shipment_id} total_products: {e}")

            product_name = self._get_product_name(product_id)
            notification_type = 'stock_ordered' if new_batch.status == 'pending' else 'stock_received'
            self._send_batch_notification(
                notification_type,
                product_name,
                {
                    'batch_id': new_batch.sk,
                    'quantity': new_batch.quantity_received,
                    'status': new_batch.status,
                    'expiry_date': new_batch.expiry_date.isoformat() if new_batch.expiry_date else None,
                    'supplier_id': new_batch.supplier_id,
                    'shipment_id': new_batch.shipment_id
                }
            )

            batch_dict = new_batch.to_dict()
            try:
                self.audit_service.log_batch_create(current_user or _SYSTEM_USER, batch_dict)
            except Exception as ae:
                logger.error(f"Audit logging failed for batch create: {ae}")

            return batch_dict

        except Exception as e:
            logger.error(f"Error creating batch: {str(e)}")
            raise Exception(f"Error creating batch: {str(e)}")

    def get_batches_by_product(self, product_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all batches for a specific product, with optional status filter"""
        try:
            batches = Batch.get_by_product_id(product_id)
            
            if status:
                batches = [b for b in batches if b.status == status]
            
            return [b.to_dict() for b in batches]
            
        except Exception as e:
            logger.error(f"Error getting batches for product {product_id}: {str(e)}")
            raise Exception(f"Error getting batches: {str(e)}")
    
    def get_expiring_batches(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get batches expiring within a specified number of days."""
        try:
            logger.info(f"Checking for batches expiring within {days_ahead} days")
            
            # Use the new model's method to get expiring batches
            expiring_batches = Batch.get_expiring_soon(days_threshold=days_ahead)
            
            logger.info(f"Found {len(expiring_batches)} expiring batches")
            return [b.to_dict() for b in expiring_batches]
            
        except Exception as e:
            logger.error(f"Error getting expiring batches: {str(e)}")
            raise Exception(f"Error getting expiring batches: {str(e)}")

    def check_and_alert_expiring_batches(self, days_ahead: int = 30) -> Dict[str, Any]:
        """Check for expiring batches, send alerts, and return enriched batch list."""
        try:
            logger.info(f"Checking for batches expiring within {days_ahead} days")

            expiring_batches = self.get_expiring_batches(days_ahead)
            logger.info(f"Found {len(expiring_batches)} expiring batches to alert")

            for batch_data in expiring_batches:
                try:
                    product_id = batch_data.get('product_id')
                    product_name = self._get_product_name(product_id)
                    batch_data['product_name'] = product_name

                    self._send_batch_notification(
                        'expiry_warning',
                        product_name,
                        {
                            'batch_id': batch_data['batch_id'],
                            'batch_number': batch_data.get('batch_number', 'Unknown'),
                            'expiry_date': batch_data['expiry_date'],
                            'days_until_expiry': batch_data['days_until_expiry'],
                            'quantity_remaining': batch_data['quantity_remaining']
                        }
                    )
                except Exception as batch_error:
                    logger.error(f"Error processing batch alert for {batch_data.get('batch_id')}: {str(batch_error)}")
                    continue

            logger.info(f"Total alerts sent: {len(expiring_batches)}")
            return {
                'alerts_sent': len(expiring_batches),
                'expiring_batches': expiring_batches,
            }

        except Exception as e:
            logger.error(f"Error checking expiring batches: {str(e)}")
            raise Exception(f"Error checking expiring batches: {str(e)}")

    # ================================================================
    # BATCH QUERIES AND REPORTING
    # ================================================================
    
    def get_all_batches(self, filters: Optional[Dict[str, Any]] = None, enrich_with_product: bool = False) -> List[Dict[str, Any]]:
        """
        Get all batches with optional filters.

        Supported filters: product_id, status, expiring_soon (days_ahead),
        shipment_id, supplier_id (with optional status/product_id/expiring_soon).
        """
        try:
            batches = []
            if filters:
                if filters.get('product_id'):
                    batches = Batch.get_by_product_id(filters['product_id'])
                elif filters.get('status'):
                    batches = Batch.get_by_status(filters['status'])
                elif filters.get('expiring_soon'):
                    days = filters.get('days_ahead', 30)
                    batches = Batch.get_expiring_soon(days)
                elif filters.get('shipment_id'):
                    batches = Batch.get_by_shipment_id(filters['shipment_id'])
                elif filters.get('supplier_id'):
                    batches = list(Batch.query(
                        "batches",
                        filter_condition=Batch.supplier_id == filters['supplier_id'],
                        limit=500
                    ))
                    if filters.get('status'):
                        batches = [b for b in batches if b.status == filters['status']]
                    if filters.get('product_id'):
                        batches = [b for b in batches if b.product_id == filters['product_id']]
                    if filters.get('expiring_soon'):
                        end = datetime.utcnow() + timedelta(days=filters.get('days_ahead', 30))
                        batches = [b for b in batches if b.expiry_date and datetime.utcnow() <= b.expiry_date <= end]
                else:
                    batches = Batch.get_all_batches()
            else:
                batches = Batch.get_all_batches()

            batch_dicts = [b.to_dict() for b in batches]
            if enrich_with_product:
                for batch_dict in batch_dicts:
                    product_id = batch_dict.get('product_id')
                    if product_id:
                        batch_dict['product_name'] = self._get_product_name(product_id)
            return batch_dicts

        except Exception as e:
            logger.error(f"Error getting all batches: {str(e)}")
            raise Exception(f"Error getting all batches: {str(e)}")

    def get_batches_by_shipment(self, shipment_id: str, enrich_with_product: bool = False) -> List[Dict[str, Any]]:
        """Get all batches that belong to a shipment (convenience wrapper)."""
        return self.get_all_batches(
            filters={'shipment_id': shipment_id},
            enrich_with_product=enrich_with_product
        )

    def get_batch_by_id(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch by ID"""
        try:
            batch = Batch.get_by_id(batch_id)
            if batch:
                return batch.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting batch {batch_id}: {str(e)}")
            raise Exception(f"Error getting batch: {str(e)}")

    def get_products_with_expiry_summary(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """
        Get products that have batches expiring within days_ahead, with summary per product.
        """
        try:
            expiring = Batch.get_expiring_soon(days_threshold=days_ahead)
            by_product: Dict[str, Dict[str, Any]] = {}
            for batch in expiring:
                pid = batch.product_id
                if pid not in by_product:
                    by_product[pid] = {
                        "product_id": pid,
                        "product_name": self._get_product_name(pid),
                        "total_quantity_expiring": 0,
                        "oldest_expiry": None,
                        "batches_count": 0,
                    }
                by_product[pid]["total_quantity_expiring"] += int(batch.quantity_remaining or 0)
                by_product[pid]["batches_count"] += 1
                exp = batch.expiry_date.isoformat() if batch.expiry_date else None
                if exp and (by_product[pid]["oldest_expiry"] is None or exp < by_product[pid]["oldest_expiry"]):
                    by_product[pid]["oldest_expiry"] = exp
            return list(by_product.values())
        except Exception as e:
            logger.error(f"Error getting products with expiry summary: {str(e)}")
            return []

    def update_batch_quantity(self, batch_id: str, quantity_used: int, adjustment_type: str = "correction",
                              adjusted_by: Optional[str] = None, notes: Optional[str] = None,
                              current_user=None) -> Optional[Dict[str, Any]]:
        """Update batch quantity when stock is used/sold. Rejects updates on expired batches."""
        try:
            batch = Batch.get_by_id(batch_id)
            if not batch:
                raise Exception(f"Batch with ID {batch_id} not found")

            if batch.is_expired():
                raise ValueError(
                    "Cannot apply quantity update to an expired batch. "
                    "Sales and adjustments must use non-expired batches only."
                )

            product_name = self._get_product_name(batch.product_id)

            # Use the consume_quantity method for deductions
            updated_batch = batch.consume_quantity(
                quantity=quantity_used,
                reason=adjustment_type,
                adjusted_by=adjusted_by,
                notes=notes
            )

            # Keep Product.total_stock consistent; use updated batch so GSI eventual consistency doesn't leave total_stock stale
            self._sync_product_totals_from_batches(
                batch.product_id,
                source="batch_quantity_update",
                reason=f"{adjustment_type} on batch {batch.sk}",
                include_batch=updated_batch,
            )

            # Send notification if batch is depleted
            if updated_batch.status == 'exhausted':
                self._send_batch_notification(
                    'batch_depleted',
                    product_name,
                    {
                        'batch_id': batch.sk,
                        'batch_number': batch.batch_number
                    }
                )

            audit_user = current_user or (
                {'user_id': adjusted_by, 'username': adjusted_by, 'source': 'service'}
                if adjusted_by else _SYSTEM_USER
            )
            try:
                self.audit_service.log_batch_deduct(
                    audit_user, batch_id, product_name, quantity_used, adjustment_type
                )
            except Exception as ae:
                logger.error(f"Audit logging failed for batch quantity update: {ae}")

            return updated_batch.to_dict()

        except Exception as e:
            logger.error(f"Error updating batch quantity for {batch_id}: {str(e)}")
            raise Exception(f"Error updating batch quantity: {str(e)}")

    def update_batch(self, batch_id: str, update_data: Dict[str, Any], current_user=None) -> Optional[Dict[str, Any]]:
        """Update batch details (quantity, price, expiry, status, shipment_id, etc.). pk/sk are read-only."""
        try:
            batch = Batch.get_by_id(batch_id)
            if not batch:
                raise Exception(f"Batch with ID {batch_id} not found")

            old_dict = batch.to_dict()

            read_only = {'pk', 'sk'}
            for key, value in update_data.items():
                if key in read_only:
                    continue
                if hasattr(batch, key):
                    setattr(batch, key, value)
            batch.updated_at = datetime.utcnow()
            batch.save()

            new_dict = batch.to_dict()
            try:
                self.audit_service.log_batch_update(
                    current_user or _SYSTEM_USER, batch_id, old_dict, new_dict
                )
            except Exception as ae:
                logger.error(f"Audit logging failed for batch update: {ae}")

            return new_dict

        except Exception as e:
            logger.error(f"Error updating batch {batch_id}: {str(e)}")
            raise Exception(f"Error updating batch: {str(e)}")

    # ================================================================
    # INTEGRATION WITH SALES
    # ================================================================
    
    def deduct_stock_fifo(self, product_id: str, quantity_needed: int, reason: str,
                          adjusted_by: Optional[str] = None, notes: Optional[str] = None,
                          current_user=None) -> List[Dict[str, Any]]:
        """
        Deduct stock from batches using FIFO logic.
        This method replaces process_sale_fifo and process_batch_adjustment.
        """
        if not product_id:
            raise ValueError("product_id is required for deduction")
        try:
            logger.info(f"Deducting {quantity_needed} of {product_id} for reason: {reason}")

            fulfillment_plan = BatchManager.get_batch_for_fulfillment(product_id, quantity_needed)

            if not fulfillment_plan['can_fulfill']:
                raise Exception(f"Insufficient stock for product {product_id}. "
                                f"Needed: {quantity_needed}, "
                                f"Available: {quantity_needed - fulfillment_plan['remaining_quantity']}")

            deductions = []
            updated_batches = []
            for item in fulfillment_plan['batches_to_use']:
                batch = item['batch']
                quantity_to_take = item['quantity_to_take']

                updated_batch = batch.consume_quantity(
                    quantity=quantity_to_take,
                    reason=reason,
                    adjusted_by=adjusted_by,
                    notes=notes
                )
                updated_batches.append(updated_batch)

                deductions.append({
                    'batch_id': updated_batch.sk,
                    'batch_number': updated_batch.batch_number,
                    'quantity_deducted': quantity_to_take,
                    'expiry_date': updated_batch.expiry_date.isoformat() if updated_batch.expiry_date else None,
                    'cost_price': float(updated_batch.cost_price)
                })

            # Keep Product.total_stock consistent; use updated batches so GSI eventual consistency doesn't leave total_stock stale
            self._sync_product_totals_from_batches(
                product_id,
                source="batch_deduction",
                reason=reason or "FIFO deduction",
                include_batches=updated_batches,
            )

            audit_user = current_user or (
                {'user_id': adjusted_by, 'username': adjusted_by, 'source': 'service'}
                if adjusted_by else _SYSTEM_USER
            )
            product_name = self._get_product_name(product_id)
            batch_ids = ', '.join(d['batch_id'] for d in deductions)
            try:
                self.audit_service.log_batch_deduct(
                    audit_user, batch_ids, product_name, quantity_needed, reason
                )
            except Exception as ae:
                logger.error(f"Audit logging failed for FIFO deduction: {ae}")

            return deductions

        except Exception as e:
            logger.error(f"Error processing FIFO deduction for {product_id}: {str(e)}")
            raise Exception(f"Error processing FIFO deduction: {str(e)}")

    def process_sale_fifo(self, product_id: str, quantity_sold: int) -> List[Dict[str, Any]]:
        """
        Process a sale using FIFO deduction. Returns list of batches used (for receipts/rollback).
        """
        return self.deduct_stock_fifo(
            product_id=product_id,
            quantity_needed=quantity_sold,
            reason="sale",
            adjusted_by=None,
            notes=None
        )

    def process_batch_adjustment(
        self,
        product_id: str,
        quantity_used: int,
        adjustment_type: str = "correction",
        adjusted_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Process a batch adjustment (e.g. damage, correction) using FIFO. Returns deductions list."""
        return self.deduct_stock_fifo(
            product_id=product_id,
            quantity_needed=quantity_used,
            reason=adjustment_type,
            adjusted_by=adjusted_by,
            notes=notes
        )

    def check_batch_availability(self, product_id: str, quantity_needed: int) -> Dict[str, Any]:
        """
        Check if sufficient stock is available in batches.
        """
        try:
            # Get all batches for the product, including non-active ones
            all_batches = Batch.get_by_product_id(product_id)
            
            # Filter for active and available batches in Python
            active_batches = [
                b for b in all_batches if b.status in ["active", "low_stock", "expiring_soon"] and b.quantity_remaining > 0
            ]
            
            total_stock = sum(b.quantity_remaining for b in active_batches)
            
            return {
                'available': total_stock >= quantity_needed,
                'total_stock': total_stock,
                'batches_count': len(active_batches)
            }
            
        except Exception as e:
            logger.error(f"Error checking batch availability for {product_id}: {str(e)}")
            return {
                'available': False,
                'total_stock': 0,
                'batches_count': 0
            }
    
    def restore_stock_to_batches(self, batches_used: List[Dict[str, Any]], transaction_date: datetime, transaction_info: Optional[Dict[str, Any]] = None):
        """
        Restore stock to batches (for cancellations/voids) with usage_history tracking.
        """
        try:
            logger.info("Restoring stock to batches...")

            for batch_info in batches_used:
                batch_id = batch_info['batch_id']
                quantity_to_restore = batch_info['quantity_deducted']
                
                batch = Batch.get_by_id(batch_id)
                if not batch:
                    logger.warning(f"Batch {batch_id} not found, skipping restoration.")
                    continue

                batch.add_quantity(
                    quantity=quantity_to_restore,
                    reason="restoration",
                    adjusted_by=transaction_info.get('adjusted_by') if transaction_info else "system",
                    notes=transaction_info.get('reason') if transaction_info else "Stock restored"
                )
                
                logger.info(f"Restored {quantity_to_restore} to batch {batch.sk}")

            # If this restoration is for a single product, sync it; otherwise skip (caller can resync globally).
            try:
                product_ids = {b.get("product_id") for b in batches_used if isinstance(b, dict) and b.get("product_id")}
                if len(product_ids) == 1:
                    pid = next(iter(product_ids))
                    self._sync_product_totals_from_batches(pid, source="batch_restoration", reason="restore_stock_to_batches")
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Stock restoration failed: {str(e)}")
            raise Exception(f"Stock restoration failed: {str(e)}")

    def mark_expired_batches(self) -> List[Dict[str, Any]]:
        """Mark expired batches as expired using the BatchManager."""
        try:
            logger.info("Marking expired batches...")
            updated_batches = BatchManager.update_expired_batches()
            logger.info(f"Marked {len(updated_batches)} batches as expired.")
            for batch in updated_batches:
                try:
                    product_id = batch.get('product_id') if isinstance(batch, dict) else getattr(batch, 'product_id', None)
                    batch_id = batch.get('batch_id') if isinstance(batch, dict) else getattr(batch, 'sk', None)
                    product_name = self._get_product_name(product_id) if product_id else "Unknown Product"
                    self._send_batch_notification(
                        'batch_expired',
                        product_name,
                        {'batch_id': batch_id, 'product_id': product_id}
                    )
                    try:
                        self.audit_service.log_batch_expired(_SYSTEM_USER, batch_id or '', product_name)
                    except Exception as ae:
                        logger.error(f"Audit logging failed for batch expired: {ae}")
                except Exception:
                    pass
            return updated_batches
        except Exception as e:
            logger.error(f"Error marking expired batches: {str(e)}")
            raise Exception(f"Error marking expired batches: {str(e)}")

    def activate_batches_for_shipment(self, shipment_id: str, current_user=None) -> List[Dict[str, Any]]:
        """
        Activate all pending batches for a shipment (set status to 'active').
        Called when a shipment is set as received so its batches become usable.
        Returns list of activated batch dicts; syncs product total_stock for affected products.
        """
        if not shipment_id or not str(shipment_id).strip():
            return []
        try:
            batches = Batch.get_by_shipment_id(shipment_id)
            activated = []
            product_ids = set()
            for batch in batches:
                if getattr(batch, "status", None) != "pending":
                    continue
                batch.status = "active"
                batch.updated_at = datetime.utcnow()
                batch.save()
                activated.append(batch.to_dict())
                product_ids.add(batch.product_id)
            for pid in product_ids:
                try:
                    self._sync_product_totals_from_batches(
                        pid,
                        source="shipment_received",
                        reason=f"Batches activated for shipment {shipment_id}",
                    )
                except Exception as sync_err:
                    logger.warning("Sync total_stock after activate_batches_for_shipment %s: %s", pid, sync_err)
            if activated:
                logger.info("Activated %d batch(es) for shipment %s", len(activated), shipment_id)
                for pid in product_ids:
                    try:
                        product_name = self._get_product_name(pid)
                        self._send_batch_notification(
                            'shipment_activated',
                            product_name,
                            {'shipment_id': shipment_id, 'product_id': pid}
                        )
                    except Exception:
                        pass
                try:
                    self.audit_service.log_batch_shipment_activated(
                        current_user or _SYSTEM_USER, shipment_id, len(product_ids), len(activated)
                    )
                except Exception as ae:
                    logger.error(f"Audit logging failed for shipment activation: {ae}")
            return activated
        except Exception as e:
            logger.error("Error activating batches for shipment %s: %s", shipment_id, e)
            raise Exception(f"Error activating batches for shipment: {str(e)}") from e

    def cancel_batches_for_shipment(self, shipment_id: str, current_user=None) -> List[Dict[str, Any]]:
        """
        Cancel all pending batches for a shipment (set status to 'cancelled').
        Called when a shipment is cancelled so its unreceived batches are excluded
        from total_stock. Only pending batches are affected; active batches (already
        received and in use) are left untouched.
        Returns list of cancelled batch dicts; syncs product total_stock for affected products.
        """
        if not shipment_id or not str(shipment_id).strip():
            return []
        try:
            batches = Batch.get_by_shipment_id(shipment_id)
            cancelled = []
            product_ids = set()
            for batch in batches:
                if getattr(batch, "status", None) != "pending":
                    continue
                batch.status = "cancelled"
                batch.updated_at = datetime.utcnow()
                batch.save()
                cancelled.append(batch.to_dict())
                product_ids.add(batch.product_id)
            for pid in product_ids:
                try:
                    self._sync_product_totals_from_batches(
                        pid,
                        source="shipment_cancelled",
                        reason=f"Batches cancelled for shipment {shipment_id}",
                    )
                except Exception as sync_err:
                    logger.warning("Sync total_stock after cancel_batches_for_shipment %s: %s", pid, sync_err)
            if cancelled:
                logger.info("Cancelled %d batch(es) for shipment %s", len(cancelled), shipment_id)
                for pid in product_ids:
                    try:
                        product_name = self._get_product_name(pid)
                        self._send_batch_notification(
                            'shipment_cancelled',
                            product_name,
                            {'shipment_id': shipment_id, 'product_id': pid}
                        )
                    except Exception:
                        pass
                try:
                    self.audit_service.log_batch_shipment_cancelled(
                        current_user or _SYSTEM_USER, shipment_id, len(product_ids), len(cancelled)
                    )
                except Exception as ae:
                    logger.error(f"Audit logging failed for shipment cancellation: {ae}")
            return cancelled
        except Exception as e:
            logger.error("Error cancelling batches for shipment %s: %s", shipment_id, e)
            raise Exception(f"Error cancelling batches for shipment: {str(e)}") from e

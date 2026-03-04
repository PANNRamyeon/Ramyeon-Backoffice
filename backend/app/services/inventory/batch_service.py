from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from models.Batches import Batch, BatchManager
from models.Product import Product
from models.Shipment import Shipment
from notifications.services import notification_service
import logging

logger = logging.getLogger(__name__)

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
                'batch_depleted': "Batch Depleted"
            }
            
            messages = {
                'created': f"New batch created for '{product_name}'",
                'stock_received': f"Stock received for '{product_name}'",
                'stock_ordered': f"Purchase order created for '{product_name}'",
                'activated': f"Stock activated for '{product_name}'",
                'expiry_warning': f"Batch expiring soon for '{product_name}'",
                'batch_expired': f"Batch expired for '{product_name}'",
                'batch_depleted': f"Batch depleted for '{product_name}'"
            }
            
            # Set priority based on action type
            if action_type in ['batch_expired', 'expiry_warning']:
                priority = "high"
                notification_type = "alert"
            elif action_type == 'batch_depleted':
                priority = "medium"
                notification_type = "alert"
            elif action_type in ['stock_ordered', 'activated']:
                priority = "low"
                notification_type = "info"
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
        except Exception as e:
            logger.error(f"Failed to send batch notification: {e}")

    def create_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new batch using the Batch model.

        batch_data can include optional shipment_id (SHIP-#####). When provided,
        the batch is linked to that Shipment and the shipment's total_products
        is incremented.
        """
        try:
            product_id = batch_data.get('product_id')
            shipment_id = batch_data.get('shipment_id')
            logger.info(f"Creating batch for product: {product_id}" + (f" (shipment {shipment_id})" if shipment_id else ""))

            new_batch = Batch.create_batch(**batch_data)

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

            return new_batch.to_dict()

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

    def check_and_alert_expiring_batches(self, days_ahead: int = 7) -> int:
        """Check for expiring batches and send alerts"""
        try:
            logger.info(f"Checking for batches expiring within {days_ahead} days")
            
            expiring_batches = self.get_expiring_batches(days_ahead)
            logger.info(f"Found {len(expiring_batches)} expiring batches to alert")
            
            for batch_data in expiring_batches:
                try:
                    # Fetch product name for notification
                    product_id = batch_data.get('product_id')
                    product_name = self._get_product_name(product_id)
                    
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
            return len(expiring_batches)
            
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
                    batches = list(Batch.scan(
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

    def update_batch_quantity(self, batch_id: str, quantity_used: int, adjustment_type: str = "correction", adjusted_by: Optional[str] = None, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update batch quantity when stock is used/sold"""
        try:
            batch = Batch.get_by_id(batch_id)
            if not batch:
                raise Exception(f"Batch with ID {batch_id} not found")

            # Use the consume_quantity method for deductions
            updated_batch = batch.consume_quantity(
                quantity=quantity_used,
                reason=adjustment_type,
                adjusted_by=adjusted_by,
                notes=notes
            )

            # Send notification if batch is depleted
            if updated_batch.status == 'exhausted':
                product_name = self._get_product_name(batch.product_id)
                self._send_batch_notification(
                    'batch_depleted',
                    product_name,
                    {
                        'batch_id': batch.sk,
                        'batch_number': batch.batch_number
                    }
                )
            
            return updated_batch.to_dict()

        except Exception as e:
            logger.error(f"Error updating batch quantity for {batch_id}: {str(e)}")
            raise Exception(f"Error updating batch quantity: {str(e)}")

    def update_batch(self, batch_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update batch details (quantity, price, expiry, status, shipment_id, etc.). pk/sk are read-only."""
        try:
            batch = Batch.get_by_id(batch_id)
            if not batch:
                raise Exception(f"Batch with ID {batch_id} not found")

            read_only = {'pk', 'sk'}
            for key, value in update_data.items():
                if key in read_only:
                    continue
                if hasattr(batch, key):
                    setattr(batch, key, value)
            batch.updated_at = datetime.utcnow()
            batch.save()
            return batch.to_dict()

        except Exception as e:
            logger.error(f"Error updating batch {batch_id}: {str(e)}")
            raise Exception(f"Error updating batch: {str(e)}")

    # ================================================================
    # INTEGRATION WITH SALES
    # ================================================================
    
    def deduct_stock_fifo(self, product_id: str, quantity_needed: int, reason: str, adjusted_by: Optional[str] = None, notes: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Deduct stock from batches using FIFO logic.
        This method replaces process_sale_fifo and process_batch_adjustment.
        """
        try:
            logger.info(f"Deducting {quantity_needed} of {product_id} for reason: {reason}")

            fulfillment_plan = BatchManager.get_batch_for_fulfillment(product_id, quantity_needed)

            if not fulfillment_plan['can_fulfill']:
                raise Exception(f"Insufficient stock for product {product_id}. "
                                f"Needed: {quantity_needed}, "
                                f"Available: {quantity_needed - fulfillment_plan['remaining_quantity']}")

            deductions = []
            for item in fulfillment_plan['batches_to_use']:
                batch = item['batch']
                quantity_to_take = item['quantity_to_take']

                updated_batch = batch.consume_quantity(
                    quantity=quantity_to_take,
                    reason=reason,
                    adjusted_by=adjusted_by,
                    notes=notes
                )

                deductions.append({
                    'batch_id': updated_batch.sk,
                    'batch_number': updated_batch.batch_number,
                    'quantity_deducted': quantity_to_take,
                    'expiry_date': updated_batch.expiry_date.isoformat() if updated_batch.expiry_date else None,
                    'cost_price': float(updated_batch.cost_price)
                })
            
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

        except Exception as e:
            logger.error(f"Stock restoration failed: {str(e)}")
            raise Exception(f"Stock restoration failed: {str(e)}")

    def mark_expired_batches(self) -> List[Dict[str, Any]]:
        """Mark expired batches as expired using the BatchManager."""
        try:
            logger.info("Marking expired batches...")
            updated_batches = BatchManager.update_expired_batches()
            logger.info(f"Marked {len(updated_batches)} batches as expired.")
            return updated_batches
        except Exception as e:
            logger.error(f"Error marking expired batches: {str(e)}")
            raise Exception(f"Error marking expired batches: {str(e)}")

    def activate_batch(self, batch_number: str, product_id: str, supplier_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Activate a pending batch by updating its status to active."""
        try:
            # Since we don't have a GSI for this query, we have to scan.
            # This operation should be infrequent.
            pending_batches = Batch.scan(
                (Batch.batch_number == batch_number) &
                (Batch.product_id == product_id) &
                (Batch.supplier_id == supplier_id) &
                (Batch.status == 'pending')
            )
            
            batch_to_activate = next(pending_batches, None)

            if not batch_to_activate:
                raise Exception(f"Pending batch with number {batch_number} not found for product {product_id}")

            # Update status and other fields
            batch_to_activate.status = 'active'
            batch_to_activate.date_received = datetime.utcnow()

            for key, value in kwargs.items():
                if hasattr(batch_to_activate, key):
                    setattr(batch_to_activate, key, value)

            batch_to_activate.save()
            
            # Fetch product name for notification
            product_name = self._get_product_name(product_id)
            self._send_batch_notification(
                'activated',
                product_name,
                additional_metadata={
                    'batch_number': batch_number,
                    'quantity': batch_to_activate.quantity_received,
                    'supplier_id': supplier_id
                }
            )
            
            return batch_to_activate.to_dict()

        except Exception as e:
            logger.error(f"Error activating batch {batch_number}: {str(e)}")
            raise Exception(f"Error activating batch: {str(e)}")
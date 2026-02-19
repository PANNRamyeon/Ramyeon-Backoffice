from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from models.Batches import Batch, BatchManager
# from models.Product import Product
# from models.Supplier import Supplier
from notifications.services import notification_service
import logging

logger = logging.getLogger(__name__)

class BatchService:
    def __init__(self):
        pass


    def _send_batch_notification(self, action_type, product_name, additional_metadata=None):
        """Centralized notification helper for batch actions"""
        try:
            titles = {
                'created': "New Batch Added",
                'stock_received': "Stock Received",
                'stock_ordered': "Purchase Order Created",  # ✅ NEW
                'activated': "Stock Activated",  # ✅ NEW
                'expiry_warning': "Expiry Warning",
                'batch_expired': "Batch Expired",
                'batch_depleted': "Batch Depleted"
            }
            
            messages = {
                'created': f"New batch created for '{product_name}'",
                'stock_received': f"Stock received for '{product_name}'",
                'stock_ordered': f"Purchase order created for '{product_name}'",  # ✅ NEW
                'activated': f"Stock activated for '{product_name}'",  # ✅ NEW
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
        """Create a new batch using the Batch model"""
        try:
            logger.info(f"Creating batch for product: {batch_data.get('product_id')}")

            # Create the batch using the new model's classmethod
            new_batch = Batch.create_batch(**batch_data)

            # Send notification
            product_name = "Unknown Product"  # TODO: Fetch product name if needed for notification
            
            notification_type = 'stock_ordered' if new_batch.status == 'pending' else 'stock_received'
            
            self._send_batch_notification(
                notification_type,
                product_name,
                {
                    'batch_id': new_batch.sk,
                    'quantity': new_batch.quantity_received,
                    'status': new_batch.status,
                    'expiry_date': new_batch.expiry_date.isoformat() if new_batch.expiry_date else None,
                    'supplier_id': new_batch.supplier_id
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
                    # TODO: Fetch product name if needed for notification
                    product_name = "Unknown Product"
                    
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
    
    def get_all_batches(self, filters: Optional[Dict[str, Any]] = None, enrich_with_product: bool = True) -> List[Dict[str, Any]]:
        """
        Get all batches with optional filters.
        Enrichment with product data is not yet implemented.
        """
        try:
            batches = []
            if filters:
                # TODO: Implement more complex filtering logic.
                # This is a simplified version.
                if filters.get('product_id'):
                    batches = Batch.get_by_product_id(filters['product_id'])
                elif filters.get('status'):
                    batches = Batch.get_by_status(filters['status'])
                elif filters.get('expiring_soon'):
                    days = filters.get('days_ahead', 30)
                    batches = Batch.get_expiring_soon(days)
                else:
                    batches = Batch.get_all_batches()
            else:
                batches = Batch.get_all_batches()

            # TODO: Re-implement product enrichment if required.
            # This would involve fetching product details for each batch.
            if enrich_with_product:
                logger.warning("Product enrichment is not yet implemented in the refactored BatchService.")

            return [b.to_dict() for b in batches]

        except Exception as e:
            logger.error(f"Error getting all batches: {str(e)}")
            raise Exception(f"Error getting all batches: {str(e)}")

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
                # TODO: Fetch product name if needed
                product_name = "Unknown Product"
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
        """Update batch details like quantity, price, expiry date, etc."""
        try:
            batch = Batch.get_by_id(batch_id)
            if not batch:
                raise Exception(f"Batch with ID {batch_id} not found")

            # Update attributes
            for key, value in update_data.items():
                if hasattr(batch, key):
                    setattr(batch, key, value)
            
            # The save method in the model should handle the updated_at timestamp
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
            
            # TODO: Fetch product name if needed
            product_name = "Unknown Product"
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
from datetime import datetime, timedelta
from ...models.Batches import Batch
from ...models.Product import Product
import logging

logger = logging.getLogger(__name__)


class BatchFIFOService:
    """
    Advanced FIFO batch service for POS operations using DynamoDB
    Replaces MongoDB-based service with optimized DynamoDB queries
    """
    
    def __init__(self):
        # No MongoDB connection needed - using PynamoDB models directly
        pass
    
    # ================================================================
    # FIFO/FEFO STOCK DEDUCTION (Main POS Function)
    # ================================================================
    
    def deduct_stock_fifo(self, product_id, quantity_needed, transaction_date, transaction_info=None):
        """
        Deduct stock from batches using FEFO (First Expired First Out) with usage_history tracking
        
        Args:
            product_id: Product ID (PROD-##### format)
            quantity_needed: Quantity to deduct
            transaction_date: Transaction timestamp
            transaction_info: Optional dict with {
                'transaction_id': str,
                'adjusted_by': str (cashier_id or customer_id),
                'source': 'pos_sale' | 'online_order' | 'manual_adjustment',
                'notes': str
            }
        
        Returns:
            List of batch deductions with tracking info
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 FEFO Stock Deduction (DynamoDB)")
            print(f"   Product: {product_id}")
            print(f"   Quantity needed: {quantity_needed}")
            if transaction_info:
                print(f"   Transaction: {transaction_info.get('transaction_id', 'N/A')}")
                print(f"   Source: {transaction_info.get('source', 'N/A')}")
            print(f"{'='*60}\n")
            
            # Use Batch model's built-in method for stock deduction
            batch_deductions = Batch.deduct_stock_from_batches(
                product_id=product_id,
                quantity_needed=quantity_needed,
                transaction_date=transaction_date,
                transaction_info=transaction_info
            )
            
            print(f"📦 Used {len(batch_deductions)} batches")
            print(f"{'='*60}")
            print(f"✅ FEFO deduction complete")
            print(f"{'='*60}\n")
            
            return batch_deductions
            
        except Exception as e:
            logger.error(f"❌ FEFO deduction failed: {str(e)}", exc_info=True)
            raise
    
    # ================================================================
    # STOCK VALIDATION (Check before checkout)
    # ================================================================
    
    def check_batch_availability(self, product_id, quantity_needed):
        """
        Check if sufficient stock is available in batches
        
        Args:
            product_id: Product ID
            quantity_needed: Quantity to check
        
        Returns:
            dict: {
                'available': bool,
                'total_stock': int,
                'batches_count': int,
                'can_fulfill': bool
            }
        """
        try:
            # Use Batch model's optimized availability check
            result = Batch.check_batch_availability(product_id, quantity_needed)
            
            # Add additional metadata for backward compatibility
            result['message'] = (
                f"Available: {result['total_stock']} units in {result['batches_count']} batches"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking batch availability: {str(e)}", exc_info=True)
            return {
                'available': False,
                'total_stock': 0,
                'batches_count': 0,
                'can_fulfill': False,
                'message': f"Error: {str(e)}"
            }
    
    # ================================================================
    # BATCH RESTORE (For voided sales)
    # ================================================================
    
    def restore_stock_to_batches(self, batches_used, transaction_date, transaction_info=None):
        """
        Restore stock to batches (for cancellations/voids) with usage_history tracking
        
        Args:
            batches_used: List of batch deductions to restore
            transaction_date: Restoration timestamp
            transaction_info: Optional dict with {
                'transaction_id': str,
                'adjusted_by': str,
                'reason': str,
                'notes': str
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 Restoring Stock to Batches (DynamoDB)")
            if transaction_info:
                print(f"   Transaction: {transaction_info.get('transaction_id', 'N/A')}")
                print(f"   Reason: {transaction_info.get('reason', 'N/A')}")
            print(f"{'='*60}\n")
            
            print(f"   Restoring {len(batches_used)} batch deductions...")
            
            # Use Batch model's built-in restoration method
            Batch.restore_stock_to_batches(
                batch_deductions=batches_used,
                transaction_date=transaction_date,
                transaction_info=transaction_info
            )
            
            print(f"{'='*60}")
            print(f"✅ Stock restoration complete")
            print(f"{'='*60}\n")
            
        except Exception as e:
            logger.error(f"❌ Stock restoration failed: {str(e)}", exc_info=True)
            raise
    
    # ================================================================
    # BATCH INFO (Quick lookups)
    # ================================================================
    
    def get_product_batches(self, product_id, strategy="fefo"):
        """
        Get all active batches for a product
        
        Args:
            product_id: Product ID
            strategy: "fefo" (default, sort by expiry) or "fifo" (sort by date_received)
        
        Returns:
            List of batch documents sorted by chosen strategy
        """
        try:
            if strategy.lower() == "fifo":
                # Get batches sorted by FIFO (oldest first)
                batches = Batch.get_active_batches_by_product_fifo(product_id)
            else:
                # Default to FEFO (soonest expiry first)
                batches = Batch.get_active_batches_by_product_fefo(product_id)
            
            # Convert to dictionary format for backward compatibility
            batch_dicts = []
            for batch in batches:
                batch_dicts.append({
                    'batch_id': batch.sk,
                    'batch_number': batch.batch_number,
                    'product_id': batch.product_id,
                    'quantity_received': batch.quantity_received,
                    'quantity_remaining': batch.quantity_remaining,
                    'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                    'date_received': batch.date_received.isoformat() if batch.date_received else None,
                    'status': batch.status,
                    'cost_price': batch.cost_price if batch.cost_price else 0,
                    'days_until_expiry': batch.days_until_expiry(),
                    'is_expired': batch.is_expired()
                })
            
            return batch_dicts
            
        except Exception as e:
            logger.error(f"❌ Get batches failed: {str(e)}", exc_info=True)
            return []
    
    def get_near_expiry_batches(self, days_threshold=30, product_id=None):
        """
        Get all batches expiring within the threshold
        
        Args:
            days_threshold: Number of days (default: 30)
            product_id: Optional filter for specific product
        
        Returns:
            List of batches near expiry with details
        """
        try:
            # Use enhanced method from Batch model
            batches = Batch.get_near_expiry_batches_enhanced(
                days_threshold=days_threshold,
                product_id=product_id
            )
            
            return batches
            
        except Exception as e:
            logger.error(f"❌ Get near-expiry batches failed: {str(e)}", exc_info=True)
            return []
    
    # ================================================================
    # ADDITIONAL HELPER METHODS
    # ================================================================
    
    def get_batch_usage_summary(self, product_id=None, batch_id=None):
        """
        Get detailed usage summary for batches
        
        Args:
            product_id: Optional - get summaries for all batches of a product
            batch_id: Optional - get summary for specific batch
        
        Returns:
            dict or list of usage summaries
        """
        try:
            if batch_id:
                # Single batch summary
                batch = Batch.get_by_id(batch_id)
                if not batch:
                    return {"error": f"Batch {batch_id} not found"}
                return batch.get_usage_summary()
            
            elif product_id:
                # All batches for product
                batches = Batch.get_by_product_id(product_id)
                summaries = []
                for batch in batches:
                    summaries.append(batch.get_usage_summary())
                return summaries
            
            else:
                return {"error": "Must provide either product_id or batch_id"}
                
        except Exception as e:
            logger.error(f"Error getting usage summary: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def update_expired_batches(self):
        """
        Scan and update status for expired batches
        Returns list of updated batches
        """
        try:
            # Use BatchManager to update expired batches
            from ...models.Batches import BatchManager
            updated = BatchManager.update_expired_batches()
            
            logger.info(f"Updated {len(updated)} expired batches")
            return updated
            
        except Exception as e:
            logger.error(f"Error updating expired batches: {str(e)}", exc_info=True)
            return []
    
    def batch_fulfillment_plan(self, product_id, quantity_needed, strategy="fefo"):
        """
        Get a fulfillment plan for an order (which batches to use)
        
        Args:
            product_id: Product ID
            quantity_needed: Quantity needed
            strategy: "fefo" or "fifo"
        
        Returns:
            dict with fulfillment plan
        """
        try:
            # Use BatchManager's fulfillment planning
            from ...models.Batches import BatchManager
            plan = BatchManager.get_batch_for_fulfillment(
                product_id=product_id,
                quantity_needed=quantity_needed,
                strategy=strategy
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"Error getting fulfillment plan: {str(e)}", exc_info=True)
            return {
                "batches_to_use": [],
                "remaining_quantity": quantity_needed,
                "can_fulfill": False,
                "message": f"Error: {str(e)}"
            }
    
    def get_product_expiry_summary(self, product_id):
        """
        Get expiry summary for a product's batches
        
        Args:
            product_id: Product ID
        
        Returns:
            dict with expiry statistics
        """
        try:
            from ...models.Batches import BatchManager
            summary = BatchManager.get_expiry_summary(product_id)
            return summary
            
        except Exception as e:
            logger.error(f"Error getting expiry summary: {str(e)}", exc_info=True)
            return {}
    
    # ================================================================
    # COMPATIBILITY METHODS (For seamless migration)
    # ================================================================
    
    def deduct_stock_fifo_legacy(self, product_id, quantity_needed, transaction_date, transaction_info=None):
        """
        Legacy-compatible method that mimics old MongoDB behavior
        Uses new DynamoDB methods internally
        """
        try:
            # Convert to new method call
            return self.deduct_stock_fifo(
                product_id=product_id,
                quantity_needed=quantity_needed,
                transaction_date=transaction_date,
                transaction_info=transaction_info
            )
        except Exception as e:
            logger.error(f"Legacy deduction failed: {str(e)}")
            raise
    
    def restore_stock_to_batches_legacy(self, batches_used, transaction_date, transaction_info=None):
        """
        Legacy-compatible restoration method
        """
        try:
            # Ensure batch_ids are in correct format
            formatted_deductions = []
            for batch_info in batches_used:
                batch_id = batch_info.get('batch_id')
                if batch_id and not batch_id.startswith('BATCH-'):
                    batch_info['batch_id'] = f"BATCH-{batch_id}"
                formatted_deductions.append(batch_info)
            
            # Call new method
            self.restore_stock_to_batches(
                batches_used=formatted_deductions,
                transaction_date=transaction_date,
                transaction_info=transaction_info
            )
        except Exception as e:
            logger.error(f"Legacy restoration failed: {str(e)}")
            raise
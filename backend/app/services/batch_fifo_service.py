from datetime import datetime, timedelta
from ..database import db_manager
import logging

logger = logging.getLogger(__name__)


class BatchFIFOService:
    """
    Advanced FIFO batch service for POS operations
    Handles FIFO stock deduction and batch availability checks with usage_history tracking
    """
    
    def __init__(self):
        self.db = db_manager.get_database()
        self.batches_collection = self.db.batches  # ✅ Note: batches_collection with 's'
        self.products_collection = self.db.products
    
    # ================================================================
    # FIFO STOCK DEDUCTION (Main POS Function)
    # ================================================================
    
    def deduct_stock_fifo(self, product_id, quantity_needed, transaction_date, transaction_info=None):
        """
        Deduct stock from batches using FIFO with usage_history tracking
        
        Args:
            product_id: Product ID (PROD-##### format)
            quantity_needed: Quantity to deduct
            transaction_date: Transaction timestamp
            transaction_info: Optional dict with {
                'transaction_id': str,
                'adjusted_by': str (cashier_id or customer_id),
                'source': 'pos_sale' | 'online_order' | 'manual_adjustment'
            }
        
        Returns:
            List of batch deductions with tracking info
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 FIFO Stock Deduction")
            print(f"   Product: {product_id}")
            print(f"   Quantity needed: {quantity_needed}")
            if transaction_info:
                print(f"   Transaction: {transaction_info.get('transaction_id', 'N/A')}")
                print(f"   Source: {transaction_info.get('source', 'N/A')}")
            print(f"{'='*60}\n")
            
            # ✅ FIXED: Changed batch_collection to batches_collection
            batches = list(self.batches_collection.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }).sort('expiry_date', 1))
            
            if not batches:
                raise ValueError(f"No active batches available for product {product_id}")
            
            # Calculate total available stock
            total_available = sum(batch['quantity_remaining'] for batch in batches)
            
            print(f"📦 Found {len(batches)} active batches")
            print(f"   Total available: {total_available}")
            print(f"   Requested: {quantity_needed}\n")
            
            if total_available < quantity_needed:
                raise ValueError(
                    f"Insufficient stock in batches. "
                    f"Need {quantity_needed}, have {total_available}"
                )
            
            batch_deductions = []
            remaining_quantity = quantity_needed
            
            for batch in batches:
                if remaining_quantity <= 0:
                    break
                
                # Calculate how much to deduct from this batch
                deduct_amount = min(remaining_quantity, batch['quantity_remaining'])
                new_quantity = batch['quantity_remaining'] - deduct_amount
                
                print(f"   Batch {batch['batch_number']}:")
                print(f"      Before: {batch['quantity_remaining']}")
                print(f"      Deduct: {deduct_amount}")
                print(f"      After: {new_quantity}")
                print(f"      Expires: {batch['expiry_date']}")
                
                # ✅ CREATE USAGE_HISTORY ENTRY
                usage_entry = {
                    'timestamp': transaction_date,
                    'quantity_used': deduct_amount,
                    'remaining_after': new_quantity,
                    'adjustment_type': 'sale',
                    'adjusted_by': transaction_info.get('adjusted_by') if transaction_info else None,
                    'approved_by': None,
                    'notes': f"Transaction {transaction_info.get('transaction_id', 'N/A')}" if transaction_info else '',
                    'source': transaction_info.get('source', 'pos_sale') if transaction_info else 'pos_sale'
                }
                
                # ✅ FIXED: Changed batch_collection to batches_collection
                self.batches_collection.update_one(
                    {'_id': batch['_id']},
                    {
                        '$set': {
                            'quantity_remaining': new_quantity,
                            'status': 'depleted' if new_quantity == 0 else 'active',
                            'updated_at': transaction_date
                        },
                        '$push': {
                            'usage_history': usage_entry
                        }
                    }
                )
                
                # Track batch usage for transaction record
                batch_deductions.append({
                    'batch_id': batch['_id'],
                    'batch_number': batch['batch_number'],
                    'quantity_deducted': deduct_amount,
                    'expiry_date': batch['expiry_date'],
                    'cost_price': batch.get('cost_price', 0)
                })
                
                remaining_quantity -= deduct_amount
                
                if new_quantity == 0:
                    print(f"      ⚠️  Batch depleted!\n")
                else:
                    print(f"      ✅ Updated\n")
            
            print(f"{'='*60}")
            print(f"✅ FIFO deduction complete")
            print(f"   Used {len(batch_deductions)} batches")
            print(f"{'='*60}\n")
            
            return batch_deductions
            
        except Exception as e:
            logger.error(f"❌ FIFO deduction failed: {str(e)}")
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
                'batches_count': int
            }
        """
        try:
            # ✅ FIXED: Changed batch_collection to batches_collection
            batches = list(self.batches_collection.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }))
            
            total_stock = sum(batch['quantity_remaining'] for batch in batches)
            
            return {
                'available': total_stock >= quantity_needed,
                'total_stock': total_stock,
                'batches_count': len(batches)
            }
            
        except Exception as e:
            logger.error(f"Error checking batch availability: {str(e)}")
            return {
                'available': False,
                'total_stock': 0,
                'batches_count': 0
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
                'reason': str
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 Restoring Stock to Batches")
            if transaction_info:
                print(f"   Transaction: {transaction_info.get('transaction_id', 'N/A')}")
                print(f"   Reason: {transaction_info.get('reason', 'N/A')}")
            print(f"{'='*60}\n")
            
            for batch_info in batches_used:
                batch_id = batch_info['batch_id']
                quantity_to_restore = batch_info['quantity_deducted']
                
                print(f"   Restoring to batch {batch_info['batch_number']}:")
                print(f"      Quantity: +{quantity_to_restore}")
                
                # ✅ FIXED: Changed batch_collection to batches_collection
                batch = self.batches_collection.find_one({'_id': batch_id})
                
                if not batch:
                    logger.warning(f"      ⚠️  Batch {batch_id} not found, skipping")
                    continue
                
                new_quantity = batch['quantity_remaining'] + quantity_to_restore
                
                print(f"      Before: {batch['quantity_remaining']}")
                print(f"      After: {new_quantity}")
                
                # ✅ CREATE USAGE_HISTORY ENTRY FOR RESTORATION
                usage_entry = {
                    'timestamp': transaction_date,
                    'quantity_used': -quantity_to_restore,  # Negative = restoration
                    'remaining_after': new_quantity,
                    'adjustment_type': 'restoration',
                    'adjusted_by': transaction_info.get('adjusted_by') if transaction_info else None,
                    'approved_by': None,
                    'notes': transaction_info.get('reason', 'Stock restored from cancelled/voided transaction') if transaction_info else 'Stock restored',
                    'source': 'restoration'
                }
                
                # ✅ FIXED: Changed batch_collection to batches_collection
                self.batches_collection.update_one(
                    {'_id': batch_id},
                    {
                        '$set': {
                            'quantity_remaining': new_quantity,
                            'status': 'active',  # Reactivate if was depleted
                            'updated_at': transaction_date
                        },
                        '$push': {
                            'usage_history': usage_entry
                        }
                    }
                )
                
                print(f"      ✅ Restored\n")
            
            print(f"{'='*60}")
            print(f"✅ Stock restoration complete")
            print(f"{'='*60}\n")
            
        except Exception as e:
            logger.error(f"❌ Stock restoration failed: {str(e)}")
            raise
    
    # ================================================================
    # BATCH INFO (Quick lookups)
    # ================================================================
    
    def get_product_batches(self, product_id):
        """
        Get all active batches for a product
        
        Returns:
            List of batch documents sorted by FIFO
        """
        try:
            batches = list(self.batches_collection.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }).sort('date_received', 1))
            
            return batches
            
        except Exception as e:
            logger.error(f"❌ Get batches failed: {str(e)}")
            return []
    
    def get_near_expiry_batches(self, days_threshold=30):
        """
        Get all batches expiring within the threshold
        
        Args:
            days_threshold: Number of days (default: 30)
        
        Returns:
            List of batches near expiry
        """
        try:
            threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
            
            batches = list(self.batches_collection.find({
                'status': 'active',
                'quantity_remaining': {'$gt': 0},
                'expiry_date': {'$lte': threshold_date}
            }).sort('expiry_date', 1))
            
            return batches
            
        except Exception as e:
            logger.error(f"❌ Get near-expiry batches failed: {str(e)}")
            return []

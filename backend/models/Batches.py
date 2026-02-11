# app/models/Batch.py
"""
Batch Model - Following ERD Specification with Optimistic Locking
PK = "batches", SK = "BATCH-#####"
Single Table Design using RamyeonCornerDB
Enhanced with FIFO/FEFO support and comprehensive batch management
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.exceptions import UpdateError
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

# ============= NESTED MAP ATTRIBUTES =============
class SyncLogDetailItem(MapAttribute):
    """Details for sync_logs entries"""
    field_name = UnicodeAttribute(null=True)
    old_value = UnicodeAttribute(null=True)
    new_value = UnicodeAttribute(null=True)
    error_message = UnicodeAttribute(null=True)
    record_id = UnicodeAttribute(null=True)


class SyncLogItem(MapAttribute):
    """MapAttribute for sync_logs array items"""
    last_updated = UTCDateTimeAttribute()
    source = UnicodeAttribute()
    status = UnicodeAttribute()
    details = ListAttribute(of=SyncLogDetailItem, default=list)
    action = UnicodeAttribute()


class UsageHistoryItem(MapAttribute):
    """MapAttribute for usage_history array items"""
    timestamp = UTCDateTimeAttribute()
    quantity_used = NumberAttribute()
    reason = UnicodeAttribute()
    remaining_after = NumberAttribute()
    adjustment_type = UnicodeAttribute()
    adjusted_by = UnicodeAttribute()
    approved_by = UnicodeAttribute(null=True)
    notes = UnicodeAttribute(null=True)
    source = UnicodeAttribute()


# ============= GLOBAL SECONDARY INDEXES =============
class ProductIdIndex(GlobalSecondaryIndex):
    """GSI for querying batches by product_id"""
    class Meta:
        index_name = 'batch-product-id-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    product_id = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)


class StatusExpiryIndex(GlobalSecondaryIndex):
    """GSI for querying batches by status with expiry date range"""
    class Meta:
        index_name = 'batch-status-expiry-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    status = UnicodeAttribute(hash_key=True)
    expiry_date = UTCDateTimeAttribute(range_key=True)


class ProductStatusIndex(GlobalSecondaryIndex):
    """GSI for querying batches by product_id and status"""
    class Meta:
        index_name = 'batch-product-status-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    product_id = UnicodeAttribute(hash_key=True)
    status = UnicodeAttribute(range_key=True)


class ProductExpiryIndex(GlobalSecondaryIndex):
    """
    GSI for FEFO queries: product_id + expiry_date
    Enables efficient sorting by expiry date (soonest first)
    """
    class Meta:
        index_name = 'batch-product-expiry-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    product_id = UnicodeAttribute(hash_key=True)
    expiry_date = UTCDateTimeAttribute(range_key=True)


class ProductDateReceivedIndex(GlobalSecondaryIndex):
    """
    GSI for FIFO queries: product_id + date_received
    Enables efficient sorting by receipt date (oldest first)
    """
    class Meta:
        index_name = 'batch-product-date-received-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    product_id = UnicodeAttribute(hash_key=True)
    date_received = UTCDateTimeAttribute(range_key=True)


# ============= MAIN BATCH MODEL =============
class Batch(Model):
    """
    BATCH MODEL - Enhanced with FIFO/FEFO capabilities and optimistic locking
    
    This model represents inventory batches with full support for:
    - Stock receipt and consumption
    - Expiry date tracking
    - FIFO (First In First Out) and FEFO (First Expired First Out) strategies
    - Automatic status updates based on quantity and expiry
    - Usage history with audit trail
    - Optimistic locking for concurrent operations
    - Integration with Product and Supplier models
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB
        region = AWS_REGION
        read_capacity_units = 5
        write_capacity_units = 10
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, default="batches")
    sk = UnicodeAttribute(range_key=True)  # "BATCH-#####"
    
    # ============= GSI DEFINITIONS =============
    product_id_index = ProductIdIndex()
    status_expiry_index = StatusExpiryIndex()
    product_status_index = ProductStatusIndex()
    product_expiry_index = ProductExpiryIndex()          # For FEFO
    product_date_received_index = ProductDateReceivedIndex()  # For FIFO
    
    # ============= BATCH IDENTIFICATION =============
    product_id = UnicodeAttribute()
    batch_number = UnicodeAttribute()
    
    # ============= QUANTITY MANAGEMENT =============
    quantity_received = NumberAttribute()
    quantity_remaining = NumberAttribute()
    
    # ============= FINANCIAL INFORMATION =============
    cost_price = NumberAttribute()
    
    # ============= DATE INFORMATION =============
    expiry_date = UTCDateTimeAttribute(null=True)
    expected_delivery_date = UTCDateTimeAttribute(null=True)
    date_received = UTCDateTimeAttribute(null=True)
    
    # ============= SUPPLIER INFORMATION =============
    supplier_id = UnicodeAttribute(null=True)
    
    # ============= STATUS AND METADATA =============
    status = UnicodeAttribute(default="pending")
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    notes = UnicodeAttribute(null=True)
    
    # ============= NESTED ARRAYS =============
    sync_logs = ListAttribute(of=SyncLogItem, default=list)
    usage_history = ListAttribute(of=UsageHistoryItem, default=list)
    
    # ============= OPTIMISTIC LOCKING =============
    version = NumberAttribute(default=1)
    
    # ============= CLASS METHODS (CRUD) =============
    
    @classmethod
    def create_batch(cls, **kwargs) -> 'Batch':
        """
        Create a new batch with auto-generated SK and automatic status
        
        Args:
            **kwargs: All batch attributes except pk/sk/status/version
        
        Returns:
            Batch: Created batch instance
        """
        try:
            # Generate SK using utils.py
            sk = generate_sk('BATCH-', 'batch_seq')
            
            # Set required fields
            kwargs['pk'] = 'batches'
            kwargs['sk'] = sk
            
            # Set timestamps
            now = datetime.utcnow()
            if 'created_at' not in kwargs:
                kwargs['created_at'] = now
            if 'updated_at' not in kwargs:
                kwargs['updated_at'] = now
            
            # Ensure date_received is set (for FIFO sorting)
            if 'date_received' not in kwargs:
                kwargs['date_received'] = now
            
            # Set quantity_remaining if not provided
            if 'quantity_remaining' not in kwargs and 'quantity_received' in kwargs:
                kwargs['quantity_remaining'] = kwargs['quantity_received']
            
            # Create batch instance
            batch = cls(**kwargs)
            
            # Run initial status calculation
            batch._calculate_and_set_status()
            
            # Save the batch
            batch.save()
            
            logger.info(f"Batch created: {sk} - Product: {batch.product_id}, Status: {batch.status}")
            return batch
            
        except Exception as e:
            logger.error(f"Failed to create batch: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, batch_id: str) -> Optional['Batch']:
        """
        Get batch by ID (SK)
        
        Args:
            batch_id: Batch ID (with or without BATCH- prefix)
        
        Returns:
            Batch or None if not found
        """
        try:
            if not batch_id.startswith('BATCH-'):
                batch_id = f"BATCH-{batch_id}"
            
            return cls.get("batches", batch_id)
        except cls.DoesNotExist:
            logger.warning(f"Batch not found: {batch_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching batch {batch_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_product_id(cls, product_id: str, limit: int = 100) -> List['Batch']:
        """
        Get all batches for a specific product using GSI
        
        Args:
            product_id: Product ID
            limit: Maximum number of batches to return
        
        Returns:
            List of Batch objects
        """
        try:
            return list(cls.product_id_index.query(
                product_id,
                limit=limit,
                scan_index_forward=True
            ))
        except Exception as e:
            logger.error(f"Error querying batches for product {product_id}: {str(e)}")
            return []
    
    @classmethod
    def get_by_product_and_status(cls, product_id: str, status: str, limit: int = 100) -> List['Batch']:
        """
        Get batches by product_id and status using GSI
        
        Args:
            product_id: Product ID
            status: Batch status (active, depleted, expired, etc.)
            limit: Maximum number of batches to return
        
        Returns:
            List of Batch objects
        """
        try:
            return list(cls.product_status_index.query(
                product_id,
                cls.status == status,
                limit=limit,
                scan_index_forward=True
            ))
        except Exception as e:
            logger.error(f"Error querying batches for product {product_id} with status {status}: {str(e)}")
            return []
    
    @classmethod
    def get_by_status(cls, status: str, limit: int = 100) -> List['Batch']:
        """
        Get batches by status using GSI
        
        Args:
            status: Batch status
            limit: Maximum number of batches to return
        
        Returns:
            List of Batch objects
        """
        try:
            return list(cls.status_expiry_index.query(
                status,
                limit=limit
            ))
        except Exception as e:
            logger.error(f"Error querying batches by status {status}: {str(e)}")
            return []
    
    @classmethod
    def get_all_batches(cls, limit: int = 1000) -> List['Batch']:
        """
        Get all batches (paginated)
        
        Args:
            limit: Maximum number of batches to return
        
        Returns:
            List of Batch objects
        """
        try:
            return list(cls.query("batches", limit=limit))
        except Exception as e:
            logger.error(f"Error querying all batches: {str(e)}")
            return []
    
    # ============= FIFO/FEFO QUERY METHODS =============
    
    @classmethod
    def get_active_batches_by_product_fefo(cls, product_id: str, limit: int = 100) -> List['Batch']:
        """
        Get active batches for a product sorted by expiry_date (FEFO - First Expired First Out)
        Returns batches with:
        - status = 'active'
        - quantity_remaining > 0
        - expiry_date > now (or no expiry date)
        - sorted by expiry_date ascending (soonest expiry first)
        
        Args:
            product_id: Product ID
            limit: Maximum number of batches to return
        
        Returns:
            List of Batch objects sorted by FEFO
        """
        try:
            # Query using product-expiry GSI (sorted by expiry_date)
            batches = list(cls.product_expiry_index.query(
                product_id,
                limit=limit,
                scan_index_forward=True  # Ascending = soonest expiry first
            ))
            
            # Filter for active, non-expired batches with quantity > 0
            now = datetime.utcnow()
            filtered = []
            for batch in batches:
                if (batch.status == "active" and 
                    batch.quantity_remaining > 0 and
                    (not batch.expiry_date or batch.expiry_date > now)):
                    filtered.append(batch)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error in get_active_batches_by_product_fefo: {str(e)}")
            return []
    
    @classmethod
    def get_active_batches_by_product_fifo(cls, product_id: str, limit: int = 100) -> List['Batch']:
        """
        Get active batches for a product sorted by date_received (FIFO - First In First Out)
        Returns batches with:
        - status = 'active'
        - quantity_remaining > 0
        - expiry_date > now (or no expiry date)
        - sorted by date_received ascending (oldest first)
        
        Args:
            product_id: Product ID
            limit: Maximum number of batches to return
        
        Returns:
            List of Batch objects sorted by FIFO
        """
        try:
            # Query using product-date-received GSI (sorted by date_received)
            batches = list(cls.product_date_received_index.query(
                product_id,
                limit=limit,
                scan_index_forward=True  # Ascending = oldest first
            ))
            
            # Filter for active, non-expired batches with quantity > 0
            now = datetime.utcnow()
            filtered = []
            for batch in batches:
                if (batch.status == "active" and 
                    batch.quantity_remaining > 0 and
                    (not batch.expiry_date or batch.expiry_date > now)):
                    filtered.append(batch)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error in get_active_batches_by_product_fifo: {str(e)}")
            return []
    
    @classmethod
    def get_product_batches_fefo(cls, product_id: str) -> List[Dict]:
        """
        Get all active batches for a product sorted by FEFO (soonest expiry first)
        Returns simplified dictionary representation suitable for API responses
        
        Args:
            product_id: Product ID
        
        Returns:
            List of batch dictionaries with essential fields
        """
        try:
            batches = cls.get_active_batches_by_product_fefo(product_id)
            return [batch.to_simple_dict() for batch in batches]
        except Exception as e:
            logger.error(f"Error in get_product_batches_fefo: {str(e)}")
            return []
    
    @classmethod
    def get_product_batches_fifo(cls, product_id: str) -> List[Dict]:
        """
        Get all active batches for a product sorted by FIFO (oldest first)
        Returns simplified dictionary representation suitable for API responses
        
        Args:
            product_id: Product ID
        
        Returns:
            List of batch dictionaries with essential fields
        """
        try:
            batches = cls.get_active_batches_by_product_fifo(product_id)
            return [batch.to_simple_dict() for batch in batches]
        except Exception as e:
            logger.error(f"Error in get_product_batches_fifo: {str(e)}")
            return []
    
    @classmethod
    def get_near_expiry_batches_enhanced(cls, days_threshold: int = 30, 
                                        product_id: Optional[str] = None) -> List[Dict]:
        """
        Get batches expiring within the threshold days, optionally filtered by product_id
        
        Args:
            days_threshold: Number of days from now (default: 30)
            product_id: Optional product filter
        
        Returns:
            List of batch dictionaries with expiry details
        """
        try:
            now = datetime.utcnow()
            threshold_date = now + timedelta(days=days_threshold)
            batches = []
            
            if product_id:
                # Use product-expiry GSI for efficient product-specific query
                product_batches = list(cls.product_expiry_index.query(
                    product_id,
                    cls.expiry_date.between(now, threshold_date),
                    limit=100
                ))
                for batch in product_batches:
                    if batch.quantity_remaining > 0:
                        batches.append(batch)
            else:
                # Use status-expiry GSI for each active status
                for status in ["active", "low_stock", "expiring_soon"]:
                    status_batches = list(cls.status_expiry_index.query(
                        status,
                        cls.expiry_date.between(now, threshold_date),
                        limit=100
                    ))
                    for batch in status_batches:
                        if batch.quantity_remaining > 0:
                            batches.append(batch)
            
            # Sort by expiry date (soonest first)
            batches.sort(key=lambda x: x.expiry_date if x.expiry_date else datetime.max)
            
            # Convert to dictionary format with calculated fields
            result = []
            for batch in batches:
                result.append({
                    "batch_id": batch.sk,
                    "batch_number": batch.batch_number,
                    "product_id": batch.product_id,
                    "quantity_remaining": batch.quantity_remaining,
                    "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
                    "days_until_expiry": (batch.expiry_date - now).days if batch.expiry_date else None,
                    "status": batch.status
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in get_near_expiry_batches_enhanced: {str(e)}")
            return []
    
    @classmethod
    def check_batch_availability(cls, product_id: str, quantity_needed: int) -> Dict:
        """
        Check if sufficient stock is available in active batches for a product
        
        Args:
            product_id: Product ID
            quantity_needed: Quantity requested
        
        Returns:
            Dict: {
                'available': bool,
                'total_stock': int,
                'batches_count': int,
                'can_fulfill': bool
            }
        """
        try:
            # Get active batches via FEFO method (any sorting works for aggregation)
            batches = cls.get_active_batches_by_product_fefo(product_id)
            total_stock = sum(batch.quantity_remaining for batch in batches)
            
            return {
                'available': total_stock >= quantity_needed,
                'total_stock': total_stock,
                'batches_count': len(batches),
                'can_fulfill': total_stock >= quantity_needed
            }
        except Exception as e:
            logger.error(f"Error in check_batch_availability: {str(e)}")
            return {
                'available': False,
                'total_stock': 0,
                'batches_count': 0,
                'can_fulfill': False
            }
    
    # ============= STOCK OPERATION METHODS =============
    
    @classmethod
    def deduct_stock_from_batches(cls, product_id: str, quantity_needed: int,
                                 transaction_date: datetime,
                                 transaction_info: Optional[Dict] = None) -> List[Dict]:
        """
        Deduct stock from batches using FEFO strategy (soonest expiry first)
        
        Args:
            product_id: Product ID
            quantity_needed: Quantity to deduct
            transaction_date: Timestamp of transaction
            transaction_info: Optional metadata {
                'transaction_id': str,
                'adjusted_by': str,
                'source': str,
                'notes': str,
                'reason': str
            }
        
        Returns:
            List of batch deduction details: [{
                'batch_id': str,
                'batch_number': str,
                'quantity_deducted': int,
                'expiry_date': str (ISO format),
                'cost_price': float
            }]
        
        Raises:
            ValueError: If insufficient stock or no active batches
        """
        try:
            logger.info(f"Starting stock deduction for product {product_id}, quantity {quantity_needed}")
            
            # Get batches sorted by FEFO
            batches = cls.get_active_batches_by_product_fefo(product_id)
            
            if not batches:
                raise ValueError(f"No active batches available for product {product_id}")
            
            total_available = sum(batch.quantity_remaining for batch in batches)
            
            if total_available < quantity_needed:
                raise ValueError(
                    f"Insufficient stock. Need {quantity_needed}, have {total_available}"
                )
            
            batch_deductions = []
            remaining_quantity = quantity_needed
            
            for batch in batches:
                if remaining_quantity <= 0:
                    break
                
                deduct_amount = min(remaining_quantity, batch.quantity_remaining)
                
                try:
                    # Use batch's consume_quantity method (with optimistic locking)
                    batch.consume_quantity(
                        quantity=deduct_amount,
                        reason=transaction_info.get('reason', 'sale') if transaction_info else 'sale',
                        adjusted_by=transaction_info.get('adjusted_by', 'system') if transaction_info else 'system',
                        source=transaction_info.get('source', 'pos_sale') if transaction_info else 'pos_sale',
                        notes=transaction_info.get('notes', 
                            f"Transaction {transaction_info.get('transaction_id', 'N/A')}" 
                            if transaction_info else '')
                    )
                    
                    # Record deduction details
                    batch_deductions.append({
                        'batch_id': batch.sk,
                        'batch_number': batch.batch_number,
                        'quantity_deducted': deduct_amount,
                        'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                        'cost_price': batch.cost_price if batch.cost_price else 0
                    })
                    
                    remaining_quantity -= deduct_amount
                    
                    logger.info(f"Deducted {deduct_amount} from batch {batch.batch_number}, "
                              f"remaining: {batch.quantity_remaining}")
                    
                except UpdateError as e:
                    logger.warning(f"Concurrent update on batch {batch.batch_number}, retrying...")
                    batch.refresh()
                    continue
                except Exception as e:
                    logger.error(f"Error deducting from batch {batch.batch_number}: {str(e)}")
                    raise
            
            logger.info(f"Stock deduction complete. Used {len(batch_deductions)} batches.")
            return batch_deductions
            
        except Exception as e:
            logger.error(f"Error in deduct_stock_from_batches: {str(e)}")
            raise
    
    @classmethod
    def restore_stock_to_batches(cls, batch_deductions: List[Dict],
                                transaction_date: datetime,
                                transaction_info: Optional[Dict] = None) -> None:
        """
        Restore stock to batches (for cancellations/voids)
        
        Args:
            batch_deductions: List of batch deduction records from deduct_stock_from_batches
            transaction_date: Restoration timestamp
            transaction_info: Optional metadata {
                'transaction_id': str,
                'adjusted_by': str,
                'reason': str,
                'notes': str
            }
        """
        try:
            logger.info(f"Restoring stock for {len(batch_deductions)} batches")
            
            for deduction in batch_deductions:
                batch_id = deduction['batch_id']
                
                try:
                    batch = cls.get_by_id(batch_id)
                    if not batch:
                        logger.warning(f"Batch {batch_id} not found, skipping")
                        continue
                    
                    # Add quantity back using batch's add_quantity method
                    batch.add_quantity(
                        quantity=deduction['quantity_deducted'],
                        reason=transaction_info.get('reason', 'restoration') if transaction_info else 'restoration',
                        adjusted_by=transaction_info.get('adjusted_by', 'system') if transaction_info else 'system',
                        source='restoration',
                        notes=transaction_info.get('notes', 
                            'Stock restored from cancelled transaction' 
                            if transaction_info else 'Stock restored')
                    )
                    
                    logger.info(f"Restored {deduction['quantity_deducted']} to batch {batch.batch_number}")
                    
                except UpdateError as e:
                    logger.warning(f"Concurrent update on batch {batch_id}, retrying...")
                    continue
                except Exception as e:
                    logger.error(f"Error restoring batch {batch_id}: {str(e)}")
                    # Continue with other batches
                    continue
            
            logger.info("Stock restoration complete")
            
        except Exception as e:
            logger.error(f"Error in restore_stock_to_batches: {str(e)}")
            raise
    
    # ============= INSTANCE METHODS =============
    
    def update_quantity(self, quantity_change: int, reason: str,
                       adjusted_by: str, adjustment_type: str,
                       source: str = "manual", notes: Optional[str] = None,
                       approved_by: Optional[str] = None,
                       retry_count: int = 3) -> 'Batch':
        """
        Update batch quantity with optimistic locking and automatic status updates
        
        Args:
            quantity_change: Positive (add) or negative (deduct) quantity
            reason: Reason for adjustment
            adjusted_by: User ID of person making adjustment
            adjustment_type: Type of adjustment (e.g., 'sale', 'receipt', 'restoration')
            source: Source system (pos_sale, online_order, manual, etc.)
            notes: Optional notes
            approved_by: Optional approver user ID
            retry_count: Number of retry attempts for optimistic locking
        
        Returns:
            Batch: Updated batch instance
        
        Raises:
            ValueError: If insufficient quantity for deduction
            UpdateError: If optimistic locking fails after retries
        """
        for attempt in range(retry_count):
            try:
                # For deductions, check sufficient quantity
                if quantity_change < 0 and abs(quantity_change) > self.quantity_remaining:
                    raise ValueError(
                        f"Insufficient quantity. Available: {self.quantity_remaining}, "
                        f"Requested: {abs(quantity_change)}"
                    )
                
                # Calculate new quantity
                new_quantity = self.quantity_remaining + quantity_change
                quantity_used = abs(quantity_change) if quantity_change < 0 else 0
                
                # Create usage history record
                history_item = UsageHistoryItem(
                    timestamp=datetime.utcnow(),
                    quantity_used=quantity_used,
                    reason=reason,
                    remaining_after=new_quantity,
                    adjustment_type=adjustment_type,
                    adjusted_by=adjusted_by,
                    approved_by=approved_by,
                    notes=notes,
                    source=source
                )
                
                # Update with optimistic locking
                current_version = self.version
                self.quantity_remaining = new_quantity
                self.usage_history.append(history_item)
                self.updated_at = datetime.utcnow()
                self.version = current_version + 1
                
                # Automatically update status based on new state
                self._calculate_and_set_status()
                
                # Save with optimistic locking condition
                condition = (Batch.version == current_version)
                self.save(condition=condition)
                
                logger.info(f"Batch {self.sk} quantity updated: {self.quantity_remaining}")
                return self
                
            except UpdateError as e:
                if "ConditionalCheckFailedException" in str(e) and attempt < retry_count - 1:
                    # Optimistic lock failed - reload and retry
                    logger.warning(f"Optimistic lock failed for batch {self.sk}, retry {attempt + 1}")
                    self.refresh()
                    continue
                else:
                    logger.error(f"Failed to update batch {self.sk} after {retry_count} attempts: {str(e)}")
                    raise UpdateError(f"Failed to update batch due to concurrent modification. Please try again.")
                    
            except Exception as e:
                logger.error(f"Error updating quantity for batch {self.sk}: {str(e)}")
                raise
    
    def consume_quantity(self, quantity: int, reason: str,
                        adjusted_by: str, source: str = "sale",
                        notes: Optional[str] = None) -> 'Batch':
        """
        Consume/deduct quantity from batch (convenience wrapper)
        
        Args:
            quantity: Positive quantity to deduct
            reason: Reason for consumption
            adjusted_by: User ID
            source: Source system
            notes: Optional notes
        
        Returns:
            Batch: Updated batch
        """
        return self.update_quantity(
            quantity_change=-quantity,
            reason=reason,
            adjusted_by=adjusted_by,
            adjustment_type="deduction",
            source=source,
            notes=notes
        )
    
    def add_quantity(self, quantity: int, reason: str,
                    adjusted_by: str, source: str = "receipt",
                    notes: Optional[str] = None) -> 'Batch':
        """
        Add quantity to batch (convenience wrapper)
        
        Args:
            quantity: Positive quantity to add
            reason: Reason for addition
            adjusted_by: User ID
            source: Source system
            notes: Optional notes
        
        Returns:
            Batch: Updated batch
        """
        return self.update_quantity(
            quantity_change=quantity,
            reason=reason,
            adjusted_by=adjusted_by,
            adjustment_type="addition",
            source=source,
            notes=notes
        )
    
    def update_quantity_with_details(self, quantity_change: int,
                                    adjustment_type: str,
                                    adjusted_by: str,
                                    source: str = "manual",
                                    notes: Optional[str] = None,
                                    approved_by: Optional[str] = None,
                                    reason: str = "adjustment") -> 'Batch':
        """
        Enhanced update method with more detailed parameters
        Aligned with FIFO service requirements
        
        Args:
            quantity_change: Positive (add) or negative (deduct)
            adjustment_type: Type of adjustment
            adjusted_by: User ID
            source: Source system
            notes: Optional notes
            approved_by: Optional approver
            reason: Reason for adjustment
        
        Returns:
            Batch: Updated batch
        """
        return self.update_quantity(
            quantity_change=quantity_change,
            reason=reason,
            adjusted_by=adjusted_by,
            adjustment_type=adjustment_type,
            source=source,
            notes=notes,
            approved_by=approved_by
        )
    
    def update_usage_history(self, quantity_used: int,
                            remaining_after: int,
                            adjustment_type: str,
                            adjusted_by: str,
                            source: str,
                            notes: Optional[str] = None,
                            approved_by: Optional[str] = None) -> None:
        """
        Directly add a usage history entry without changing quantity
        Useful for custom transaction logging or corrections
        
        Args:
            quantity_used: Quantity used (positive for consumption, negative for restoration)
            remaining_after: Quantity remaining after this operation
            adjustment_type: Type of adjustment
            adjusted_by: User ID
            source: Source system
            notes: Optional notes
            approved_by: Optional approver
        
        Raises:
            UpdateError: If optimistic locking fails
        """
        try:
            history_item = UsageHistoryItem(
                timestamp=datetime.utcnow(),
                quantity_used=quantity_used,
                reason=adjustment_type,
                remaining_after=remaining_after,
                adjustment_type=adjustment_type,
                adjusted_by=adjusted_by,
                approved_by=approved_by,
                notes=notes,
                source=source
            )
            
            current_version = self.version
            self.usage_history.append(history_item)
            self.updated_at = datetime.utcnow()
            self.version = current_version + 1
            
            condition = (Batch.version == current_version)
            self.save(condition=condition)
            
            logger.info(f"Usage history added to batch {self.sk}: {adjustment_type}")
            
        except UpdateError as e:
            logger.error(f"Concurrent modification while updating usage history: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to update usage history: {str(e)}")
            raise
    
    def add_sync_log(self, source: str, status: str, action: str,
                    details: Optional[List[Dict]] = None) -> 'Batch':
        """
        Add a synchronization log entry
        
        Args:
            source: Source system (POS, Online, ERP, etc.)
            status: Sync status (success, pending, failed)
            action: Action performed
            details: Optional list of detail dictionaries
        
        Returns:
            Batch: Updated batch
        
        Raises:
            UpdateError: If optimistic locking fails
        """
        try:
            # Convert details dicts to SyncLogDetailItem
            detail_items = []
            if details:
                for detail in details:
                    detail_items.append(SyncLogDetailItem(**detail))
            
            sync_log = SyncLogItem(
                last_updated=datetime.utcnow(),
                source=source,
                status=status,
                action=action,
                details=detail_items
            )
            
            current_version = self.version
            self.sync_logs.append(sync_log)
            self.updated_at = datetime.utcnow()
            self.version = current_version + 1
            
            condition = (Batch.version == current_version)
            self.save(condition=condition)
            
            logger.info(f"Sync log added to batch {self.sk}: {action} - {status}")
            return self
            
        except UpdateError as e:
            logger.error(f"Concurrent modification while adding sync log to batch {self.sk}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to add sync log to batch {self.sk}: {str(e)}")
            raise
    
    # ============= STATUS MANAGEMENT =============
    
    def _calculate_and_set_status(self):
        """
        Fully automatic status calculation based on quantity and expiry date
        Called after any quantity change or at creation
        """
        now = datetime.utcnow()
        
        # Check if expired
        if self.expiry_date and now > self.expiry_date:
            self.status = "expired"
            return
        
        # Check if exhausted
        if self.quantity_remaining <= 0:
            self.status = "exhausted"
            return
        
        # Check if low stock (less than 10% remaining)
        if self.quantity_received > 0:
            remaining_percentage = self.quantity_remaining / self.quantity_received
            if remaining_percentage <= 0.1:  # 10% or less
                self.status = "low_stock"
                return
        
        # Check if expiring soon (within 7 days)
        if self.expiry_date:
            days_until_expiry = (self.expiry_date - now).days
            if 0 <= days_until_expiry <= 7:
                self.status = "expiring_soon"
                return
        
        # Default active status
        self.status = "active"
    
    def is_expired(self) -> bool:
        """Check if batch is expired based on current date"""
        if not self.expiry_date:
            return False
        return datetime.utcnow() > self.expiry_date
    
    def days_until_expiry(self) -> int:
        """Calculate days until expiry (negative if expired)"""
        if not self.expiry_date:
            return float('inf')
        delta = self.expiry_date - datetime.utcnow()
        return delta.days
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        Get detailed status information with warnings
        
        Returns:
            Dict: {
                'current_status': str,
                'is_expired': bool,
                'days_until_expiry': int/float,
                'quantity_remaining': int,
                'quantity_received': int,
                'percentage_remaining': float,
                'needs_attention': bool,
                'reasons': List[str]
            }
        """
        now = datetime.utcnow()
        
        info = {
            "current_status": self.status,
            "is_expired": self.is_expired(),
            "days_until_expiry": self.days_until_expiry(),
            "quantity_remaining": self.quantity_remaining,
            "quantity_received": self.quantity_received,
            "percentage_remaining": 0,
            "needs_attention": False,
            "reasons": []
        }
        
        if self.quantity_received > 0:
            info["percentage_remaining"] = (self.quantity_remaining / self.quantity_received) * 100
        
        # Determine if needs attention and why
        if self.status in ["expired", "exhausted"]:
            info["needs_attention"] = True
            info["reasons"].append(self.status)
        elif self.status == "low_stock":
            info["needs_attention"] = True
            info["reasons"].append("Low stock")
        elif self.status == "expiring_soon":
            info["needs_attention"] = True
            info["reasons"].append(f"Expiring in {self.days_until_expiry()} days")
        elif info["percentage_remaining"] < 20:  # Less than 20% remaining
            info["needs_attention"] = True
            info["reasons"].append("Stock running low")
        
        return info
    
    # ============= ANALYTICS METHODS =============
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Get summary of batch usage history
        
        Returns:
            Dict: {
                'batch_id': str,
                'batch_number': str,
                'total_received': int,
                'total_remaining': int,
                'total_used': int,
                'usage_percentage': float,
                'usage_by_reason': Dict[str, int],
                'usage_by_type': Dict[str, int],
                'usage_history_count': int
            }
        """
        try:
            total_used = self.quantity_received - self.quantity_remaining
            usage_by_reason = {}
            usage_by_type = {}
            
            for record in self.usage_history:
                reason = record.reason
                adjustment_type = record.adjustment_type
                qty_used = record.quantity_used
                
                usage_by_reason[reason] = usage_by_reason.get(reason, 0) + qty_used
                usage_by_type[adjustment_type] = usage_by_type.get(adjustment_type, 0) + qty_used
            
            return {
                "batch_id": self.sk,
                "batch_number": self.batch_number,
                "total_received": self.quantity_received,
                "total_remaining": self.quantity_remaining,
                "total_used": total_used,
                "usage_percentage": (
                    (total_used / self.quantity_received * 100) 
                    if self.quantity_received > 0 else 0
                ),
                "usage_by_reason": usage_by_reason,
                "usage_by_type": usage_by_type,
                "usage_history_count": len(self.usage_history)
            }
        except Exception as e:
            logger.error(f"Error generating usage summary for batch {self.sk}: {str(e)}")
            return {}
    
    # ============= SERIALIZATION METHODS =============
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert batch to full dictionary for API response
        
        Returns:
            Dict: Complete batch representation
        """
        try:
            return {
                "batch_id": self.sk,
                "batch_number": self.batch_number,
                "product_id": self.product_id,
                "quantity_received": self.quantity_received,
                "quantity_remaining": self.quantity_remaining,
                "cost_price": float(self.cost_price) if self.cost_price else None,
                "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
                "expected_delivery_date": self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
                "date_received": self.date_received.isoformat() if self.date_received else None,
                "supplier_id": self.supplier_id,
                "status": self.status,
                "notes": self.notes,
                "status_info": self.get_status_info(),
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "is_expired": self.is_expired(),
                "days_until_expiry": self.days_until_expiry(),
                "sync_logs_count": len(self.sync_logs),
                "usage_history_count": len(self.usage_history),
                "version": self.version
            }
        except Exception as e:
            logger.error(f"Error converting batch to dict: {str(e)}")
            return {}
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """
        Simplified dictionary for listings and API responses
        
        Returns:
            Dict: Essential batch information
        """
        try:
            return {
                "batch_id": self.sk,
                "batch_number": self.batch_number,
                "product_id": self.product_id,
                "quantity_remaining": self.quantity_remaining,
                "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
                "status": self.status,
                "cost_price": float(self.cost_price) if self.cost_price else None,
                "days_until_expiry": self.days_until_expiry()
            }
        except Exception as e:
            logger.error(f"Error converting batch to simple dict: {str(e)}")
            return {}
    
    def save(self, condition=None, **kwargs):
        """Override save to auto-update updated_at timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(condition=condition, **kwargs)
    
    def refresh(self):
        """Reload the batch from database to get latest data"""
        try:
            refreshed = self.get("batches", self.sk)
            for attribute_name in self.attribute_values:
                setattr(self, attribute_name, getattr(refreshed, attribute_name))
        except Exception as e:
            logger.error(f"Error refreshing batch {self.sk}: {str(e)}")
            raise


# ============= BATCH MANAGER WITH AUTO STATUS UPDATES =============
class BatchManager:
    """
    Manager for batch operations with automatic status management
    Handles system-wide batch maintenance and planning
    """
    
    @staticmethod
    def update_expired_batches() -> List[Dict]:
        """
        Scan and update status for expired batches
        Returns list of updated batch IDs with old/new status
        
        Returns:
            List[Dict]: Each entry contains batch_id, old_status, new_status
        """
        updated_batches = []
        try:
            # Get batches that are not already marked as expired
            for status in ["active", "low_stock", "expiring_soon"]:
                batches = Batch.get_by_status(status, limit=1000)
                for batch in batches:
                    if batch.is_expired() and batch.status != "expired":
                        try:
                            # Update status to expired
                            current_version = batch.version
                            batch.status = "expired"
                            batch.updated_at = datetime.utcnow()
                            batch.version = current_version + 1
                            
                            condition = (Batch.version == current_version)
                            batch.save(condition=condition)
                            
                            updated_batches.append({
                                "batch_id": batch.sk,
                                "old_status": status,
                                "new_status": "expired"
                            })
                            logger.info(f"Batch {batch.sk} marked as expired")
                            
                        except UpdateError:
                            logger.warning(f"Concurrent update on batch {batch.sk}, skipping")
                            continue
            
            return updated_batches
            
        except Exception as e:
            logger.error(f"Error updating expired batches: {str(e)}")
            return []
    
    @staticmethod
    def get_batch_for_fulfillment(product_id: str, 
                                 quantity_needed: int,
                                 strategy: str = "fefo") -> Dict:
        """
        Get batches for fulfilling an order with automatic status consideration
        
        Args:
            product_id: Product ID
            quantity_needed: Quantity needed
            strategy: "fefo" (first-expired-first-out) or "fifo" (first-in-first-out)
        
        Returns:
            Dict: {
                'batches_to_use': List of batch dicts with quantity_to_take,
                'remaining_quantity': int,
                'can_fulfill': bool,
                'message': str
            }
        """
        try:
            # Get all non-exhausted, non-expired batches for the product
            valid_batches = []
            if strategy == "fefo":
                valid_batches = Batch.get_active_batches_by_product_fefo(product_id)
            else:
                valid_batches = Batch.get_active_batches_by_product_fifo(product_id)
            
            if not valid_batches:
                return {
                    "batches_to_use": [],
                    "remaining_quantity": quantity_needed,
                    "can_fulfill": False,
                    "message": f"No valid batches found for product {product_id}"
                }
            
            batches_to_use = []
            remaining_quantity = quantity_needed
            
            for batch in valid_batches:
                if remaining_quantity <= 0:
                    break
                
                # Determine how much to take from this batch
                take_quantity = min(batch.quantity_remaining, remaining_quantity)
                
                batches_to_use.append({
                    "batch_id": batch.sk,
                    "batch_number": batch.batch_number,
                    "quantity_to_take": take_quantity,
                    "quantity_remaining_before": batch.quantity_remaining,
                    "batch_status": batch.status,
                    "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
                    "days_until_expiry": batch.days_until_expiry()
                })
                
                remaining_quantity -= take_quantity
            
            can_fulfill = remaining_quantity == 0
            
            return {
                "batches_to_use": batches_to_use,
                "remaining_quantity": remaining_quantity,
                "can_fulfill": can_fulfill,
                "message": f"Can fulfill {quantity_needed - remaining_quantity} of {quantity_needed}" 
                          if not can_fulfill else "Can fully fulfill"
            }
            
        except Exception as e:
            logger.error(f"Error getting batches for fulfillment: {str(e)}")
            return {
                "batches_to_use": [],
                "remaining_quantity": quantity_needed,
                "can_fulfill": False,
                "message": f"Error: {str(e)}"
            }
    
    @staticmethod
    def get_expiry_summary(product_id: str) -> Dict:
        """
        Get expiry summary for a product's batches
        
        Args:
            product_id: Product ID
        
        Returns:
            Dict: Summary statistics about batch expiry
        """
        try:
            batches = Batch.get_by_product_id(product_id, limit=100)
            
            active_batches = []
            expiring_soon_batches = []
            expired_batches = []
            
            now = datetime.utcnow()
            thirty_days_from_now = now + timedelta(days=30)
            
            for batch in batches:
                if batch.is_expired():
                    expired_batches.append(batch)
                elif batch.expiry_date and batch.expiry_date <= thirty_days_from_now:
                    expiring_soon_batches.append(batch)
                elif batch.status in ["active", "low_stock"]:
                    active_batches.append(batch)
            
            return {
                "product_id": product_id,
                "total_batches": len(batches),
                "active_batches": len(active_batches),
                "expiring_soon_batches": len(expiring_soon_batches),
                "expired_batches": len(expired_batches),
                "total_stock": sum(b.quantity_remaining for b in batches if b.status != "expired"),
                "active_stock": sum(b.quantity_remaining for b in active_batches),
                "expiring_soon_stock": sum(b.quantity_remaining for b in expiring_soon_batches),
                "oldest_expiry": min([b.expiry_date for b in active_batches if b.expiry_date], default=None),
                "expiry_alert": len(expiring_soon_batches) > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting expiry summary for product {product_id}: {str(e)}")
            return {}
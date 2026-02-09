"""
Batch Model - Following ERD Specification with Optimistic Locking
PK = "batches", SK = "BATCH-#####"
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.exceptions import UpdateError
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
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
    remaining_after = UnicodeAttribute()
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


# ============= MAIN BATCH MODEL =============
class Batch(Model):
    """
    BATCH MODEL - Following ERD Specification with Optimistic Locking
    
    Features:
    1. Fully automatic status updates based on quantity and expiry
    2. Optimistic locking using updated_at timestamp
    3. Essential GSIs for common queries
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB
        region = AWS_REGION
        
        #if DYNAMODB_LOCAL:
         #   host = DYNAMODB_LOCAL_HOST
        
        read_capacity_units = 5
        write_capacity_units = 10
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, default="batches")
    sk = UnicodeAttribute(range_key=True)  # "BATCH-00001"
    
    # ============= GSI DEFINITIONS =============
    product_id_index = ProductIdIndex()
    status_expiry_index = StatusExpiryIndex()
    
    # ============= BATCH IDENTIFICATION =============
    product_id = UnicodeAttribute()
    batch_number = UnicodeAttribute()
    
    # ============= QUANTITY MANAGEMENT =============
    quantity_received = NumberAttribute()
    quantity_remaining = NumberAttribute()
    
    # ============= FINANCIAL INFORMATION =============
    cost_price = NumberAttribute()
    
    # ============= DATE INFORMATION =============
    expiry_date = UTCDateTimeAttribute()
    date_received = UTCDateTimeAttribute()
    
    # ============= SUPPLIER INFORMATION =============
    supplier_id = UnicodeAttribute()
    
    # ============= STATUS AND METADATA =============
    status = UnicodeAttribute(default="pending")  # Initial status
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    
    # ============= NESTED ARRAYS =============
    sync_logs = ListAttribute(of=SyncLogItem, default=list)
    usage_history = ListAttribute(of=UsageHistoryItem, default=list)
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_batch(cls, **kwargs) -> 'Batch':
        """
        Create a new batch with auto-generated SK and automatic status
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
            
            # Set quantity_remaining if not provided
            if 'quantity_remaining' not in kwargs and 'quantity_received' in kwargs:
                kwargs['quantity_remaining'] = kwargs['quantity_received']
            
            # Create batch instance
            batch = cls(**kwargs)
            
            # Run initial status calculation
            batch._calculate_and_set_status()
            
            # Save the batch
            batch.save()
            
            logger.info(f"Batch created: {sk} - Status: {batch.status}")
            return batch
            
        except Exception as e:
            logger.error(f"Failed to create batch: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, batch_id: str) -> 'Batch | None':
        """
        Get batch by ID
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
    def get_by_product_id(cls, product_id: str, limit: int = 100) -> list:
        """
        Get all batches for a specific product using GSI
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
    def get_by_status(cls, status: str, limit: int = 100) -> list:
        """
        Get batches by status using GSI
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
    def get_expiring_soon(cls, days_threshold: int = 30, 
                         status_filter: Optional[List[str]] = None) -> list:
        """
        Get batches expiring within X days (using GSI)
        """
        try:
            now = datetime.utcnow()
            future_date = now + timedelta(days=days_threshold)
            
            # If no status filter, get all statuses
            if not status_filter:
                # We need to query by each status individually
                batches = []
                for status in ["active", "low_stock", "expiring_soon"]:
                    batches.extend(list(cls.status_expiry_index.query(
                        status,
                        cls.expiry_date.between(now, future_date)
                    )))
                return batches
            else:
                batches = []
                for status in status_filter:
                    batches.extend(list(cls.status_expiry_index.query(
                        status,
                        cls.expiry_date.between(now, future_date)
                    )))
                return batches
                
        except Exception as e:
            logger.error(f"Error querying expiring batches: {str(e)}")
            return []
    
    @classmethod
    def get_low_stock_batches(cls, threshold_percentage: float = 0.1) -> list:
        """
        Get batches with low stock (less than threshold percentage)
        Note: This requires scanning, but for low-frequency alerts it's acceptable
        """
        try:
            low_stock_batches = []
            
            # Query active and low_stock batches
            for status in ["active", "low_stock"]:
                batches = cls.get_by_status(status, limit=1000)
                for batch in batches:
                    if batch.quantity_received > 0:
                        remaining_percentage = batch.quantity_remaining / batch.quantity_received
                        if remaining_percentage < threshold_percentage:
                            low_stock_batches.append(batch)
            
            return low_stock_batches
            
        except Exception as e:
            logger.error(f"Error getting low stock batches: {str(e)}")
            return []
    
    @classmethod
    def get_all_batches(cls, limit: int = 1000) -> list:
        """
        Get all batches (paginated)
        """
        try:
            return list(cls.query("batches", limit=limit))
        except Exception as e:
            logger.error(f"Error querying all batches: {str(e)}")
            return []
    
    # ============= INSTANCE METHODS =============
    
    def update_quantity(self, quantity_change: int, reason: str, 
                       adjusted_by: str, adjustment_type: str,
                       source: str = "manual", notes: Optional[str] = None,
                       approved_by: Optional[str] = None,
                       retry_count: int = 3) -> 'Batch':
        """
        Update batch quantity with optimistic locking and automatic status updates
        
        Args:
            quantity_change: Positive for additions, negative for deductions
            reason: Reason for adjustment
            adjusted_by: User/System that made adjustment
            adjustment_type: addition or deduction
            source: manual, pos, api, etc.
            notes: Additional notes
            approved_by: User who approved (if required)
            retry_count: Number of retry attempts on optimistic lock failure
        
        Returns:
            Batch: Updated batch instance
        
        Raises:
            ValueError: If insufficient quantity for deduction
            UpdateError: If optimistic lock fails after retries
        """
        for attempt in range(retry_count):
            try:
                # Capture current timestamp for optimistic locking
                original_updated_at = self.updated_at
                
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
                    remaining_after=str(new_quantity),
                    adjustment_type=adjustment_type,
                    adjusted_by=adjusted_by,
                    approved_by=approved_by,
                    notes=notes,
                    source=source
                )
                
                # Update batch attributes
                self.quantity_remaining = new_quantity
                self.usage_history.append(history_item)
                self.updated_at = datetime.utcnow()
                
                # Automatically update status based on new state
                self._calculate_and_set_status()
                
                # Save with optimistic locking condition
                condition = (Batch.pk == self.pk) & (Batch.sk == self.sk) & (Batch.updated_at == original_updated_at)
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
    
    def adjust_quantity(self, new_quantity: int, reason: str,
                       adjusted_by: str, source: str = "manual",
                       notes: Optional[str] = None) -> 'Batch':
        """
        Set quantity to a specific value (absolute adjustment)
        """
        quantity_change = new_quantity - self.quantity_remaining
        return self.update_quantity(
            quantity_change=quantity_change,
            reason=reason,
            adjusted_by=adjusted_by,
            adjustment_type="adjustment",
            source=source,
            notes=notes
        )
    
    def consume_quantity(self, quantity: int, reason: str,
                        adjusted_by: str, source: str = "sale",
                        notes: Optional[str] = None) -> 'Batch':
        """
        Consume/deduct quantity from batch
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
        Add quantity to batch
        """
        return self.update_quantity(
            quantity_change=quantity,
            reason=reason,
            adjusted_by=adjusted_by,
            adjustment_type="addition",
            source=source,
            notes=notes
        )
    
    def add_sync_log(self, source: str, status: str, action: str,
                    details: Optional[List[Dict]] = None) -> 'Batch':
        """
        Add a synchronization log entry
        """
        try:
            # Capture current timestamp for optimistic locking
            original_updated_at = self.updated_at
            
            # Convert details dicts to SyncLogDetailItem objects
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
            
            self.sync_logs.append(sync_log)
            self.updated_at = datetime.utcnow()
            
            # Save with optimistic locking
            condition = (Batch.pk == self.pk) & (Batch.sk == self.sk) & (Batch.updated_at == original_updated_at)
            self.save(condition=condition)
            
            logger.info(f"Sync log added to batch {self.sk}: {action} - {status}")
            return self
            
        except UpdateError as e:
            logger.error(f"Concurrent modification while adding sync log to batch {self.sk}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to add sync log to batch {self.sk}: {str(e)}")
            raise
    
    def _calculate_and_set_status(self):
        """
        Fully automatic status calculation based on quantity and expiry date
        This is called after every quantity change
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
        
        # Check if low stock (less than 10%)
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
        """Check if batch is expired"""
        if not self.expiry_date:
            return False
        return datetime.utcnow() > self.expiry_date
    
    def days_until_expiry(self) -> int:
        """Calculate days until expiry"""
        if not self.expiry_date:
            return float('inf')
        
        delta = self.expiry_date - datetime.utcnow()
        return delta.days
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        Get detailed status information
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
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Get summary of batch usage
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
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert batch to dictionary for API response
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
                "date_received": self.date_received.isoformat() if self.date_received else None,
                "supplier_id": self.supplier_id,
                "status": self.status,
                "status_info": self.get_status_info(),
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "is_expired": self.is_expired(),
                "days_until_expiry": self.days_until_expiry(),
                "sync_logs_count": len(self.sync_logs),
                "usage_history_count": len(self.usage_history)
            }
        except Exception as e:
            logger.error(f"Error converting batch to dict: {str(e)}")
            return {}
    
    def save(self, condition=None, **kwargs):
        """Override save to handle optimistic locking"""
        self.updated_at = datetime.utcnow()
        return super().save(condition=condition, **kwargs)


# ============= BATCH MANAGER WITH AUTO STATUS UPDATES =============
class BatchManager:
    """
    Manager for batch operations with automatic status management
    """
    
    @staticmethod
    def update_expired_batches() -> List[Dict]:
        """
        Scan and update status for expired batches
        Returns list of updated batches
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
                            original_updated_at = batch.updated_at
                            batch.status = "expired"
                            batch.updated_at = datetime.utcnow()
                            
                            condition = (Batch.pk == batch.pk) & (Batch.sk == batch.sk) & (Batch.updated_at == original_updated_at)
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
            dict: Batches to use and remaining quantity needed
        """
        try:
            # Get all non-exhausted, non-expired batches for the product
            batches = Batch.get_by_product_id(product_id, limit=100)
            
            valid_batches = [
                b for b in batches 
                if b.status in ["active", "low_stock", "expiring_soon"]
                and not b.is_expired()
                and b.quantity_remaining > 0
            ]
            
            if not valid_batches:
                return {
                    "batches_to_use": [],
                    "remaining_quantity": quantity_needed,
                    "can_fulfill": False,
                    "message": f"No valid batches found for product {product_id}"
                }
            
            # Sort based on strategy
            if strategy == "fefo":
                valid_batches.sort(key=lambda x: x.expiry_date)  # Soonest expiry first
            else:  # fifo
                valid_batches.sort(key=lambda x: x.date_received)  # Oldest first
            
            batches_to_use = []
            remaining_quantity = quantity_needed
            
            for batch in valid_batches:
                if remaining_quantity <= 0:
                    break
                
                # Determine how much to take from this batch
                take_quantity = min(batch.quantity_remaining, remaining_quantity)
                
                batches_to_use.append({
                    "batch": batch,
                    "quantity_to_take": take_quantity,
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
                "message": f"Can fulfill {quantity_needed - remaining_quantity} of {quantity_needed}" if not can_fulfill else "Can fully fulfill"
            }
            
        except Exception as e:
            logger.error(f"Error getting batches for fulfillment: {str(e)}")
            return {
                "batches_to_use": [],
                "remaining_quantity": quantity_needed,
                "can_fulfill": False,
                "message": f"Error: {str(e)}"
            }
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any



class SyncLogDetailItem(MapAttribute):
    """MapAttribute for sync_logs.details items"""
    # You can add specific fields here based on your needs
    # For example: field_name, old_value, new_value, error_message
    pass


class SyncLogItem(MapAttribute):
    """MapAttribute for sync_logs items"""
    last_updated = UTCDateTimeAttribute()
    source = UnicodeAttribute()
    status = UnicodeAttribute()
    details = ListAttribute(of=SyncLogDetailItem, default=list)
    action = UnicodeAttribute()


class UsageHistoryItem(MapAttribute):
    """MapAttribute for usage_history items"""
    timestamp = UTCDateTimeAttribute()
    quantity_used = NumberAttribute()
    reason = UnicodeAttribute()
    remaining_after = UnicodeAttribute()
    adjustment_type = UnicodeAttribute()
    adjusted_by = UnicodeAttribute()
    approved_by = UnicodeAttribute(null=True)
    notes = UnicodeAttribute(null=True)
    source = UnicodeAttribute()


class Batch(Model):
    """
    Batch model for DynamoDB
    PK = batches (partition key)
    SK = BATCH-#### (sort key)
    """
    class Meta:
        table_name = "your-table-name"  # Replace with your table name
        region = "your-region"  # Replace with your AWS region
        # Add billing_mode, read_capacity_units, write_capacity_units if needed

    # Primary Key Attributes
    PK = UnicodeAttribute(hash_key=True, default="batches")
    SK = UnicodeAttribute(range_key=True)

    # Batch Identification
    product_id = UnicodeAttribute()
    batch_number = UnicodeAttribute()

    # Quantity Management
    quantity_received = NumberAttribute()
    quantity_remaining = NumberAttribute()

    # Financial Information
    cost_price = NumberAttribute()

    # Date Information
    expiry_date = UTCDateTimeAttribute()
    date_received = UTCDateTimeAttribute()

    # Supplier Information
    supplier_id = UnicodeAttribute()

    # Status and Metadata
    status = UnicodeAttribute()
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)

    # Synchronization Logs
    sync_logs = ListAttribute(of=SyncLogItem, default=list)

    # Usage History
    usage_history = ListAttribute(of=UsageHistoryItem, default=list)

    @classmethod
    def create_batch(cls, batch_id: str, **kwargs):
        """Helper method to create a new batch with proper SK format"""
        sk = f"BATCH-{batch_id}"
        return cls(SK=sk, **kwargs)

    @classmethod
    def get_batch(cls, batch_id: str):
        """Helper method to retrieve a batch by ID"""
        sk = f"BATCH-{batch_id}"
        return cls.get("batches", sk)

    @classmethod
    def query_by_product_id(cls, product_id: str):
        """Query all batches for a specific product"""
        # This requires a Global Secondary Index (GSI) on product_id
        return cls.query(
            product_id,
            cls.SK.startswith("BATCH-"),
            index_name="ProductIdIndex"  # You'll need to create this GSI
        )

    @classmethod
    def query_by_status(cls, status: str):
        """Query batches by status"""
        # This requires a GSI on status
        return cls.query(
            status,
            cls.SK.startswith("BATCH-"),
            index_name="StatusIndex"  # You'll need to create this GSI
        )

    @classmethod
    def query_expiring_batches(cls, days_threshold: int = 30):
        """Query batches expiring within a certain number of days"""
        # This requires careful design as DynamoDB doesn't support range queries
        # on non-key attributes. You might need a GSI with expiry_date as sort key
        now = datetime.utcnow()
        future_date = now + timedelta(days=days_threshold)
        # Implementation depends on your indexing strategy
        pass

    def update_quantity(self, quantity_change: int, reason: str, 
                       adjusted_by: str, adjustment_type: str, 
                       source: str = "manual", notes: Optional[str] = None,
                       approved_by: Optional[str] = None):
        """
        Update the batch quantity and record in usage history
        
        Args:
            quantity_change: Positive for additions, negative for deductions
            reason: Reason for the adjustment
            adjusted_by: User/System that made the adjustment
            adjustment_type: Type of adjustment (e.g., 'sale', 'return', 'damage', 'adjustment')
            source: Source of the adjustment (e.g., 'manual', 'pos', 'api')
            notes: Additional notes
            approved_by: User who approved the adjustment (if required)
        """
        # Calculate new remaining quantity
        new_quantity = self.quantity_remaining + quantity_change
        
        if new_quantity < 0:
            raise ValueError(f"Insufficient quantity. Available: {self.quantity_remaining}, Requested: {-quantity_change}")
        
        # Create usage history record
        history_item = UsageHistoryItem(
            timestamp=datetime.utcnow(),
            quantity_used=abs(quantity_change) if quantity_change < 0 else 0,
            reason=reason,
            remaining_after=str(new_quantity),
            adjustment_type=adjustment_type,
            adjusted_by=adjusted_by,
            approved_by=approved_by,
            notes=notes,
            source=source
        )
        
        # Update batch
        self.quantity_remaining = new_quantity
        self.usage_history.append(history_item)
        self.updated_at = datetime.utcnow()
        
        # Update status based on quantity
        if self.quantity_remaining <= 0:
            self.status = "exhausted"
        elif self.quantity_remaining < self.quantity_received * 0.1:  # Less than 10% remaining
            self.status = "low_stock"
        else:
            self.status = "active"
        
        self.save()
        return self

    def add_sync_log(self, source: str, status: str, action: str, 
                    details: Optional[List[Dict]] = None):
        """
        Add a synchronization log entry
        
        Args:
            source: Source system (e.g., 'erp', 'pos', 'wms')
            status: Sync status (e.g., 'success', 'failed', 'partial')
            action: Action performed (e.g., 'create', 'update', 'delete')
            details: List of detail items for the sync operation
        """
        sync_log = SyncLogItem(
            last_updated=datetime.utcnow(),
            source=source,
            status=status,
            action=action,
            details=details or []
        )
        
        self.sync_logs.append(sync_log)
        self.updated_at = datetime.utcnow()
        self.save()

    def is_expired(self) -> bool:
        """Check if the batch is expired"""
        return datetime.utcnow() > self.expiry_date

    def days_until_expiry(self) -> int:
        """Calculate days until expiry"""
        delta = self.expiry_date - datetime.utcnow()
        return max(0, delta.days)

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of batch usage"""
        total_used = self.quantity_received - self.quantity_remaining
        usage_by_reason = {}
        usage_by_type = {}
        
        for record in self.usage_history:
            reason = record.reason
            adjustment_type = record.adjustment_type
            
            usage_by_reason[reason] = usage_by_reason.get(reason, 0) + record.quantity_used
            usage_by_type[adjustment_type] = usage_by_type.get(adjustment_type, 0) + record.quantity_used
        
        return {
            "total_received": self.quantity_received,
            "total_remaining": self.quantity_remaining,
            "total_used": total_used,
            "usage_by_reason": usage_by_reason,
            "usage_by_type": usage_by_type,
            "usage_percentage": (total_used / self.quantity_received * 100) if self.quantity_received > 0 else 0
        }
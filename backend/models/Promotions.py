from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from datetime import datetime
from typing import Optional, List, Dict, Any


class DiscountConfigItem(MapAttribute):
    """MapAttribute for discount_config items"""
    promotion_type = UnicodeAttribute()


class TargetIdItem(MapAttribute):
    """MapAttribute for target_ids items"""
    category_id = UnicodeAttribute()


class UsageHistoryItem(MapAttribute):
    """MapAttribute for usage_history items
    Assuming this contains usage records with details"""
    # You can add specific fields here based on your needs
    # For example: user_id, order_id, timestamp, discount_amount
    pass


class Promotion(Model):
    """
    Promotion model for DynamoDB
    PK = promotions (partition key)
    SK = PROMO-#### (sort key)
    """
    class Meta:
        table_name = "your-table-name"  # Replace with your table name
        region = "your-region"  # Replace with your AWS region
        # Add billing_mode, read_capacity_units, write_capacity_units if needed

    # Primary Key Attributes
    PK = UnicodeAttribute(hash_key=True, default="promotions")
    SK = UnicodeAttribute(range_key=True)

    # Promotion Details
    name = UnicodeAttribute()
    description = UnicodeAttribute()
    type = UnicodeAttribute()
    discount_value = UnicodeAttribute()  # String to accommodate various formats (percentage, fixed amount, etc.)
    
    # Discount Configuration
    discount_config = ListAttribute(of=DiscountConfigItem)
    
    # Target Information
    target_type = UnicodeAttribute()
    target_ids = ListAttribute(of=TargetIdItem)
    
    # Date Attributes
    start_date = UTCDateTimeAttribute()
    end_date = UTCDateTimeAttribute()
    
    # Status and Management
    isDeleted = BooleanAttribute(default=False)
    usage_limit = NumberAttribute(null=True)  # null means no limit
    current_usage = NumberAttribute(default=0)
    total_revenue_impact = NumberAttribute(default=0.0)
    
    # Usage History
    usage_history = ListAttribute(of=UsageHistoryItem, default=list)
    
    # Audit Fields
    created_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    status = UnicodeAttribute()
    deactivated_at = UTCDateTimeAttribute(null=True)
    deactivated_by = UnicodeAttribute(null=True)

    @classmethod
    def create_promotion(cls, promo_id: str, **kwargs):
        """Helper method to create a new promotion with proper SK format"""
        sk = f"PROMO-{promo_id}"
        return cls(SK=sk, **kwargs)

    @classmethod
    def get_promotion(cls, promo_id: str):
        """Helper method to retrieve a promotion by ID"""
        sk = f"PROMO-{promo_id}"
        return cls.get("promotions", sk)

    @classmethod
    def query_active_promotions(cls):
        """Query all non-deleted promotions"""
        return cls.query(
            "promotions",
            cls.SK.startswith("PROMO-"),
            filter_condition=cls.isDeleted == False
        )

    def increment_usage(self, amount: float = 0.0, usage_data: Optional[Dict] = None):
        """Increment the usage counter and update revenue impact"""
        self.current_usage += 1
        self.total_revenue_impact += amount
        
        if usage_data:
            history_item = UsageHistoryItem()
            # Add usage_data fields to history_item
            for key, value in usage_data.items():
                setattr(history_item, key, value)
            self.usage_history.append(history_item)
        
        self.save()

    def deactivate(self, deactivated_by: str):
        """Deactivate the promotion"""
        self.status = "deactivated"
        self.deactivated_at = datetime.utcnow()
        self.deactivated_by = deactivated_by
        self.save()

    def is_active(self) -> bool:
        """Check if promotion is currently active"""
        now = datetime.utcnow()
        return (
            not self.isDeleted
            and self.status == "active"
            and self.start_date <= now <= self.end_date
            and (self.usage_limit is None or self.current_usage < self.usage_limit)
        )
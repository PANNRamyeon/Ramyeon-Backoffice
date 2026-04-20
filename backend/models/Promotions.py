"""
Promotion Model - Following ERD Specification with POS Sync & Seasonal Promotions
PK = "promotions", SK = "PROMO-#####" (5-digit format)
Single Table Design using RamyeonCornerDB
"""
import os
import re
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import logging
import json

# Import existing utils for consistency
from app.utils import generate_sk, get_dynamo_table, DYNAMO_TABLE_NAME, AWS_REGION
from models.Product import Product  # For product/category validation

logger = logging.getLogger(__name__)


# ============= CUSTOM DATETIME ATTRIBUTE TO FIX MALFORMED STRINGS =============

class FixedUTCDateTimeAttribute(UTCDateTimeAttribute):
    """
    Custom UTCDateTimeAttribute that attempts to fix malformed datetime strings
    (e.g., '000002025-10-12T16:48:54.458000') by stripping leading zeros from the year
    and ensuring the string is in the expected format (YYYY-MM-DDTHH:MM:SS.ffffff+0000).
    """
    def deserialize(self, value):
        if isinstance(value, str):
            # Remove leading zeros before the year, capturing the datetime part (without timezone)
            match = re.search(r'0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)(?:[+-]\d{2}:\d{2}|Z)?', value)
            if match:
                corrected = match.group(1)
                try:
                    # Try parsing with fromisoformat (handles +00:00 and Z)
                    dt = datetime.fromisoformat(corrected)
                except ValueError:
                    # If no timezone, assume UTC
                    dt = datetime.fromisoformat(corrected + '+00:00')
                # Format to the exact expected format: YYYY-MM-DDTHH:MM:SS.ffffff+0000
                iso = dt.isoformat(timespec='microseconds')
                if iso.endswith('+00:00'):
                    iso = iso.replace('+00:00', '+0000')
                elif iso.endswith('Z'):
                    iso = iso.replace('Z', '+0000')
                else:
                    # In case something else, append +0000
                    iso += '+0000'
                value = iso
        return super().deserialize(value)


# ============= MAP ATTRIBUTES FOR COMPLEX FIELDS =============

class TargetIdItem(MapAttribute):
    """MapAttribute for target_ids items"""
    target_id = UnicodeAttribute()  # category_id or product_id based on target_type
    target_name = UnicodeAttribute(null=True)  # For display purposes


class UsageHistoryItem(MapAttribute):
    """MapAttribute for usage_history items with POS transaction details"""
    order_id = UnicodeAttribute()
    user_id = UnicodeAttribute(null=True)  # If tracking individual customers
    branch_id = UnicodeAttribute(null=True)  # Which branch used the promotion
    discount_amount = NumberAttribute()  # Actual discount applied
    transaction_amount = NumberAttribute()  # Total transaction amount
    timestamp = FixedUTCDateTimeAttribute()  # <-- Use custom attribute
    pos_terminal_id = UnicodeAttribute(null=True)  # Which POS terminal
    items = UnicodeAttribute(null=True)  # JSON string of items in transaction


class AuditLogItem(MapAttribute):
    """MapAttribute for tracking promotion changes"""
    action = UnicodeAttribute()  # 'created', 'activated', 'modified', 'deactivated'
    user_id = UnicodeAttribute()
    timestamp = FixedUTCDateTimeAttribute()  # <-- Use custom attribute
    changes = UnicodeAttribute(null=True)  # JSON string of what changed
    reason = UnicodeAttribute(null=True)


# ============= PROMOTION MODEL =============

class Promotion(Model):
    """
    PROMOTION MODEL - Enhanced for POS Integration & Seasonal Promotions
    
    Core ERD Fields:
    - PK = promotions
    - SK = PROMO-##### (5-digit)
    - name (String)
    - description (String)
    - type (String)
    - discount_value (String)
    - promotion_type (String)           # 'percentage' or 'fixed_amount'
    - target_type (String)
    - target_ids (array)
    - start_date (ISODATE)
    - end_date (ISODATE)
    - isDeleted (boolean)
    - usage_limit (integer)
    - current_usage (integer)
    - total_revenue_impact (float)
    - usage_history (array)
    - created_by (String)
    - created_at (ISODATE)
    - status (String)
    - deactivated_at (ISODATE)
    - deactivated_by (String)
    
    Enhanced with POS Integration:
    - pos_sync_status: Track POS synchronization
    - last_pos_sync: Timestamp of last POS sync
    - priority: For stackable promotions
    - min_purchase_amount: Minimum cart value required
    - stackable: Whether can combine with other promotions
    - pos_promo_id: ID in POS system
    - auto_apply: Apply automatically at checkout
    - audit_log: Track all changes
    - seasonal_tag: For recurring promotions (e.g., 'christmas', 'summer')
    - customer_segment: For future customer targeting
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        # Capacity settings (promotions are read-heavy during checkout)
        read_capacity_units = 5
        write_capacity_units = 3
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="promotions")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "PROMO-00001" (5-digit)
    
    # ============= PROMOTION DETAILS =============
    name = UnicodeAttribute()
    description = UnicodeAttribute()
    type = UnicodeAttribute()  # Main type: 'discount', 'bundle', 'flash_sale'
    discount_value = UnicodeAttribute()  # String for flexibility: "10%" or "5.00"
    promotion_type = UnicodeAttribute()  # 'percentage' or 'fixed_amount'
    
    # ============= TARGET INFORMATION =============
    target_type = UnicodeAttribute()  # 'category', 'product', 'all'
    target_ids = ListAttribute(of=TargetIdItem, default=list)
    
    # ============= DATE ATTRIBUTES =============
    start_date = FixedUTCDateTimeAttribute()   # <-- Use custom attribute
    end_date = FixedUTCDateTimeAttribute()     # <-- Use custom attribute
    
    # ============= STATUS AND MANAGEMENT =============
    isDeleted = BooleanAttribute(default=False)
    usage_limit = NumberAttribute(null=True)  # null means no limit
    current_usage = NumberAttribute(default=0)
    total_revenue_impact = NumberAttribute(default=0.0)
    
    # ============= USAGE HISTORY =============
    usage_history = ListAttribute(of=UsageHistoryItem, default=list)
    
    # ============= AUDIT FIELDS =============
    created_by = UnicodeAttribute()
    created_at = FixedUTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))
    status = UnicodeAttribute(default="draft")  # 'draft', 'active', 'inactive', 'deactivated', 'expired'
    deactivated_at = FixedUTCDateTimeAttribute(null=True)
    deactivated_by = UnicodeAttribute(null=True)
    
    # ============= ENHANCED FIELDS =============
    pos_sync_status = UnicodeAttribute(default="synced")  # 'synced', 'pending', 'failed'
    last_pos_sync = FixedUTCDateTimeAttribute(null=True)
    priority = NumberAttribute(default=1)  # Lower number = higher priority
    min_purchase_amount = NumberAttribute(null=True)  # Minimum cart value
    stackable = BooleanAttribute(default=True)  # Can combine with other promotions
    pos_promo_id = UnicodeAttribute(null=True)  # ID in POS system
    auto_apply = BooleanAttribute(default=False)  # Apply automatically at checkout
    audit_log = ListAttribute(of=AuditLogItem, default=list)  # Track all changes
    seasonal_tag = UnicodeAttribute(null=True)  # e.g., 'christmas', 'summer', 'back_to_school'
    customer_segment = UnicodeAttribute(default="all")  # 'all', 'new', 'returning'
    updated_at = FixedUTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))
    
    # ============= INDEXES FOR COMMON QUERIES =============
    
    class StatusIndex(GlobalSecondaryIndex):
        """GSI for querying by status"""
        class Meta:
            index_name = 'PromotionStatusIndex'
            read_capacity_units = 5
            write_capacity_units = 2
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True, attr_name="PK")  # Will be set to 'promotions'
        status = UnicodeAttribute(range_key=True)
    
    class DateRangeIndex(GlobalSecondaryIndex):
        """GSI for querying by date range (active promotions)"""
        class Meta:
            index_name = 'PromotionDateRangeIndex'
            read_capacity_units = 5
            write_capacity_units = 2
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True, attr_name="PK")
        start_date = FixedUTCDateTimeAttribute(range_key=True)
    
    class TargetTypeIndex(GlobalSecondaryIndex):
        """GSI for querying by target type"""
        class Meta:
            index_name = 'PromotionTargetTypeIndex'
            read_capacity_units = 3
            write_capacity_units = 2
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True, attr_name="PK")
        target_type = UnicodeAttribute(range_key=True)
    
    class SeasonalIndex(GlobalSecondaryIndex):
        """GSI for seasonal promotions"""
        class Meta:
            index_name = 'PromotionSeasonalIndex'
            read_capacity_units = 2
            write_capacity_units = 1
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True, attr_name="PK")
        seasonal_tag = UnicodeAttribute(range_key=True)
    
    # Index instances
    status_index = StatusIndex()
    date_range_index = DateRangeIndex()
    target_type_index = TargetTypeIndex()
    seasonal_index = SeasonalIndex()
    
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_promotion(cls, name: str, description: str, discount_value: str,
                        start_date: datetime, end_date: datetime, created_by: str,
                        target_type: str = "all", promotion_type: str = None, **kwargs) -> 'Promotion':
        """
        Create a new promotion with auto-generated 5-digit SK
        
        Args:
            name: Name of the promotion (required)
            description: Description of the promotion (required)
            discount_value: Discount value (e.g., "10%" or "5.00") (required)
            start_date: When promotion starts (required)
            end_date: When promotion ends (required)
            created_by: User who created the promotion (required)
            target_type: Type of targeting ('category', 'product', 'all') (default: 'all')
            promotion_type: 'percentage' or 'fixed_amount'. If not provided, auto-detected from discount_value.
            **kwargs: Additional promotion attributes
        
        Returns:
            Promotion: Created and saved promotion instance
        
        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Validate required fields
            if not name or not name.strip():
                raise ValueError("Promotion name is required")
            if not description or not description.strip():
                raise ValueError("Promotion description is required")
            if not discount_value:
                raise ValueError("Discount value is required")
            if not start_date or not end_date:
                raise ValueError("Start date and end date are required")
            if start_date >= end_date:
                raise ValueError("Start date must be before end date")
            if not created_by:
                raise ValueError("Created by user is required")
            
            # Validate target type
            if target_type not in ['category', 'product', 'all']:
                raise ValueError("Target type must be 'category', 'product', or 'all'")
            
            # Auto-detect promotion_type if not provided
            if not promotion_type:
                if discount_value.endswith('%'):
                    promotion_type = 'percentage'
                else:
                    promotion_type = 'fixed_amount'
            elif promotion_type not in ['percentage', 'fixed_amount']:
                raise ValueError("promotion_type must be 'percentage' or 'fixed_amount'")
            
            # Validate discount value format and consistency with promotion_type
            cls._validate_discount_value(discount_value, promotion_type)
            
            # Generate 5-digit SK using utils.py
            from app.utils import counter_service
            raw_seq = counter_service.get_next_id(collection_name='promo_seq', prefix='', width=5)
            next_seq = raw_seq.lstrip('-')
            sk_value = f"PROMO-{next_seq}"
            
            # Create and save promotion
            promotion = cls(
                pk="promotions",
                sk=sk_value,
                name=name.strip(),
                description=description.strip(),
                discount_value=discount_value,
                promotion_type=promotion_type,
                start_date=start_date,
                end_date=end_date,
                created_by=created_by,
                target_type=target_type,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                **kwargs
            )
            
            promotion.save()
            
            # Add to audit log
            promotion._add_audit_log(
                action="created",
                user_id=created_by,
                changes=json.dumps({"status": "draft"})
            )
            
            # Add initial sync log if POS promo ID is provided
            if promotion.pos_promo_id:
                promotion.mark_pos_synced()
            
            logger.info(f"Promotion created: {sk_value} - '{name}' by {created_by}")
            return promotion
            
        except Exception as e:
            logger.error(f"Failed to create promotion: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, promotion_id: str, include_deleted: bool = False) -> 'Promotion | None':
        """
        Get promotion by ID
        
        Args:
            promotion_id: Format "PROMO-00001" or just "00001"
            include_deleted: Whether to include soft-deleted promotions
        
        Returns:
            Promotion or None if not found
        """
        try:
            # Ensure proper format
            if not promotion_id.startswith('PROMO-'):
                promotion_id = f"PROMO-{promotion_id.zfill(5)}"  # Pad to 5 digits if needed
            
            promotion = cls.get("promotions", promotion_id)
            
            # Check if deleted and if we should return it
            if promotion.isDeleted and not include_deleted:
                logger.warning(f"Promotion {promotion_id} is soft-deleted")
                return None
            
            return promotion
        except cls.DoesNotExist:
            logger.warning(f"Promotion not found: {promotion_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching promotion {promotion_id}: {str(e)}")
            return None
    
    @classmethod
    def get_active_promotions(cls, target_type: str = None, 
                            target_id: str = None) -> List['Promotion']:
        """
        Get all currently active promotions using PromotionStatusIndex GSI
        """
        try:
            now = datetime.now(timezone.utc)
            active_promotions = []
            
            # Correct GSI query: hash key PK = "promotions", range key status = "active"
            for promotion in cls.status_index.query(
                hash_key="promotions",
                range_key_condition=(cls.status == "active"),
                filter_condition=(cls.isDeleted == False)
            ):
                # Check date range
                if promotion.start_date <= now <= promotion.end_date:
                    # Check usage limit
                    if promotion.usage_limit is None or promotion.current_usage < promotion.usage_limit:
                        # Check target filters
                        if target_type and promotion.target_type != target_type:
                            continue
                        if target_id and not cls._matches_target(promotion, target_id):
                            continue
                        
                        active_promotions.append(promotion)
            
            # Sort by priority (lower number = higher priority)
            active_promotions.sort(key=lambda x: x.priority)
            return active_promotions
            
        except Exception as e:
            logger.error(f"Error getting active promotions: {str(e)}")
            return []
    
    @classmethod
    def get_expiring_soon_promotions(cls, days: int = 7) -> List['Promotion']:
        """
        Get promotions that will expire soon (scan-based, no GSI required)
        """
        try:
            now = datetime.now(timezone.utc)
            cutoff_date = now + timedelta(days=days)
            expiring = []
            
            # Scan active promotions
            for promo in cls.scan(
                filter_condition=(cls.isDeleted == False) & (cls.status == "active")
            ):
                if promo.end_date <= cutoff_date and promo.end_date >= now:
                    expiring.append(promo)
            return expiring
        except Exception as e:
            logger.error(f"Error getting expiring soon promotions: {str(e)}")
            return []
    
    @classmethod
    def get_seasonal_promotions(cls, seasonal_tag: str = None) -> List['Promotion']:
        """
        Get seasonal promotions (scan-based)
        """
        try:
            seasonal = []
            filter_cond = (cls.isDeleted == False) & (cls.status == "active")
            if seasonal_tag:
                filter_cond &= (cls.seasonal_tag == seasonal_tag)
            else:
                filter_cond &= (cls.seasonal_tag != None)
            
            for promo in cls.scan(filter_condition=filter_cond):
                seasonal.append(promo)
            return seasonal
        except Exception as e:
            logger.error(f"Error getting seasonal promotions: {str(e)}")
            return []
    
    @classmethod
    def get_promotions_by_target(cls, target_type: str, target_id: str = None) -> List['Promotion']:
        """
        Get promotions by target type and optional target ID (scan-based)
        """
        try:
            promotions = []
            # Scan all active promotions
            for promo in cls.scan(
                filter_condition=(cls.isDeleted == False) & (cls.status == "active")
            ):
                if promo.target_type == target_type:
                    if target_id and not cls._matches_target(promo, target_id):
                        continue
                    promotions.append(promo)
            return promotions
        except Exception as e:
            logger.error(f"Error getting promotions by target: {str(e)}")
            return []
    
    @classmethod
    def get_all_promotions(cls, include_deleted: bool = False) -> List['Promotion']:
        """
        Get all promotions
        
        Args:
            include_deleted: Whether to include soft-deleted promotions
        
        Returns:
            list: List of all promotions
        """
        try:
            if include_deleted:
                return list(cls.query("promotions"))
            else:
                return list(cls.query("promotions", filter_condition=cls.isDeleted == False))
        except Exception as e:
            logger.error(f"Error getting all promotions: {str(e)}")
            return []
    
    @classmethod
    def get_promotion_count(cls, status: str = None) -> int:
        """
        Get count of promotions
        
        Args:
            status: Filter by status
        
        Returns:
            int: Number of promotions
        """
        try:
            count = 0
            filter_condition = cls.isDeleted == False
            if status:
                filter_condition = filter_condition & (cls.status == status)
            
            for _ in cls.query("promotions", filter_condition=filter_condition):
                count += 1
            
            return count
        except Exception as e:
            logger.error(f"Error counting promotions: {str(e)}")
            return 0
    
    @classmethod
    def _matches_target(cls, promotion: 'Promotion', target_id: str) -> bool:
        """Check if promotion matches a specific target ID"""
        if promotion.target_type == "all":
            return True
        elif promotion.target_type in ["category", "product"]:
            return any(item.target_id == target_id for item in promotion.target_ids)
        return False
    
    @classmethod
    def _validate_discount_value(cls, discount_value: str, promotion_type: str) -> None:
        """Validate discount value format and consistency with promotion_type"""
        if not discount_value:
            raise ValueError("Discount value cannot be empty")
        
        if promotion_type == 'percentage':
            if not discount_value.endswith('%'):
                raise ValueError("Percentage discount must end with '%'")
            try:
                percentage = float(discount_value[:-1])
                if not 0 < percentage <= 100:
                    raise ValueError("Percentage must be between 0 and 100")
            except ValueError:
                raise ValueError("Invalid percentage format")
        elif promotion_type == 'fixed_amount':
            if discount_value.endswith('%'):
                raise ValueError("Fixed amount discount should not end with '%'")
            try:
                amount = float(discount_value)
                if amount <= 0:
                    raise ValueError("Fixed amount must be greater than 0")
            except ValueError:
                raise ValueError("Invalid fixed amount format")
        else:
            raise ValueError("Invalid promotion_type; must be 'percentage' or 'fixed_amount'")
    
    # ============= INSTANCE METHODS =============
    
    def is_active(self) -> bool:
        """
        Check if promotion is currently active
        
        Returns:
            bool: True if promotion is active
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Basic checks
            if self.isDeleted:
                return False
            if self.status != "active":
                return False
            if not (self.start_date <= now <= self.end_date):
                return False
            
            # Check usage limit
            if self.usage_limit is not None and self.current_usage >= self.usage_limit:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if promotion is active: {str(e)}")
            return False
    
    def calculate_discount_amount(self, original_amount: float) -> float:
        """
        Calculate discount amount for a given original amount
        
        Args:
            original_amount: Original amount to apply discount to
        
        Returns:
            float: Discount amount
        """
        try:
            if not self.is_active():
                return 0.0
            
            # Check minimum purchase amount
            if self.min_purchase_amount and original_amount < self.min_purchase_amount:
                return 0.0
            
            discount_amount = 0.0
            
            # Parse discount value based on promotion_type
            if self.promotion_type == 'percentage':
                percentage = float(self.discount_value[:-1])
                discount_amount = original_amount * (percentage / 100)
            else:  # fixed_amount
                discount_amount = float(self.discount_value)
            
            # Ensure discount doesn't exceed original amount
            return min(discount_amount, original_amount)
            
        except Exception as e:
            logger.error(f"Error calculating discount amount: {str(e)}")
            return 0.0
    
    def activate(self, activated_by: str, reason: str = None) -> 'Promotion':
        """
        Activate the promotion
        
        Args:
            activated_by: User who activated the promotion
            reason: Reason for activation
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            # Validate dates
            now = datetime.now(timezone.utc)
            if self.end_date <= now:
                raise ValueError("Cannot activate promotion that has already ended")
            
            old_status = self.status
            self.status = "active"
            self.updated_at = datetime.now(timezone.utc)
            self.pos_sync_status = "pending"  # Flag for POS sync
            
            # Clear deactivation fields if previously deactivated
            if self.deactivated_at:
                self.deactivated_at = None
                self.deactivated_by = None
            
            self.save()
            
            # Add to audit log
            self._add_audit_log(
                action="activated",
                user_id=activated_by,
                changes=json.dumps({"status": {"old": old_status, "new": "active"}}),
                reason=reason
            )
            
            # Mark for POS sync
            self.mark_pos_pending(f"Promotion activated by {activated_by}")
            
            logger.info(f"Promotion {self.sk} activated by {activated_by}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to activate promotion {self.sk}: {str(e)}")
            raise
    
    def deactivate(self, deactivated_by: str, reason: str) -> 'Promotion':
        """
        Deactivate the promotion
        
        Args:
            deactivated_by: User who deactivated the promotion
            reason: Reason for deactivation
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            if not reason or not reason.strip():
                raise ValueError("Reason is required for deactivation")
            
            old_status = self.status
            self.status = "deactivated"
            self.deactivated_at = datetime.now(timezone.utc)
            self.deactivated_by = deactivated_by
            self.updated_at = datetime.now(timezone.utc)
            self.pos_sync_status = "pending"  # Flag for POS sync
            
            self.save()
            
            # Add to audit log
            self._add_audit_log(
                action="deactivated",
                user_id=deactivated_by,
                changes=json.dumps({"status": {"old": old_status, "new": "deactivated"}}),
                reason=reason.strip()
            )
            
            # Mark for POS sync
            self.mark_pos_pending(f"Promotion deactivated: {reason}")
            
            logger.info(f"Promotion {self.sk} deactivated by {deactivated_by}: {reason}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to deactivate promotion {self.sk}: {str(e)}")
            raise
    
    def increment_usage(self, order_id: str, discount_amount: float,
                       transaction_amount: float, branch_id: str = None,
                       user_id: str = None, pos_terminal_id: str = None,
                       items: List[Dict] = None) -> 'Promotion':
        """
        Increment usage counter and add to history
        
        Args:
            order_id: Order/transaction ID
            discount_amount: Amount discounted
            transaction_amount: Total transaction amount
            branch_id: Branch where used (optional)
            user_id: User who used promotion (optional)
            pos_terminal_id: POS terminal ID (optional)
            items: List of items in transaction (optional)
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            # Check if promotion is still active
            if not self.is_active():
                raise ValueError("Cannot use inactive promotion")
            
            # Check usage limit
            if self.usage_limit is not None and self.current_usage >= self.usage_limit:
                raise ValueError("Promotion usage limit reached")
            
            # Update counters
            self.current_usage += 1
            self.total_revenue_impact += discount_amount
            self.updated_at = datetime.now(timezone.utc)
            
            # Add to usage history
            history_item = UsageHistoryItem(
                order_id=order_id,
                user_id=user_id,
                branch_id=branch_id,
                discount_amount=discount_amount,
                transaction_amount=transaction_amount,
                timestamp=datetime.now(timezone.utc),
                pos_terminal_id=pos_terminal_id,
                items=json.dumps(items) if items else None
            )
            
            # Limit history to last 1000 entries
            if len(self.usage_history) >= 1000:
                self.usage_history = self.usage_history[-999:]
            
            self.usage_history.append(history_item)
            
            # Check if usage limit reached
            if self.usage_limit is not None and self.current_usage >= self.usage_limit:
                self.status = "inactive"
                logger.info(f"Promotion {self.sk} reached usage limit")
            
            self.save()
            
            logger.info(f"Promotion {self.sk} used in order {order_id}, discount: {discount_amount}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to increment usage for promotion {self.sk}: {str(e)}")
            raise
    
    def update_promotion(self, updated_by: str, **kwargs) -> 'Promotion':
        """
        Update promotion attributes
        
        Args:
            updated_by: User making the update
            **kwargs: Promotion attributes to update
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            changes = {}
            updated_fields = []
            
            for key, value in kwargs.items():
                if hasattr(self, key):
                    old_value = getattr(self, key)
                    
                    # Handle special cases
                    if key == 'discount_value' or key == 'promotion_type':
                        # Validate the pair
                        disc_val = value if key == 'discount_value' else self.discount_value
                        promo_type = value if key == 'promotion_type' else self.promotion_type
                        self._validate_discount_value(disc_val, promo_type)
                    
                    if key == 'start_date' or key == 'end_date':
                        # Validate date range
                        if key == 'start_date':
                            if value >= self.end_date:
                                raise ValueError("Start date must be before end date")
                        elif key == 'end_date':
                            if value <= self.start_date:
                                raise ValueError("End date must be after start date")
                    
                    # Update if value changed
                    if old_value != value:
                        setattr(self, key, value)
                        updated_fields.append(key)
                        changes[key] = {"old": old_value, "new": value}
            
            if updated_fields:
                self.updated_at = datetime.now(timezone.utc)
                self.pos_sync_status = "pending"  # Flag for POS sync
                self.save()
                
                # Add to audit log
                self._add_audit_log(
                    action="modified",
                    user_id=updated_by,
                    changes=json.dumps(changes)
                )
                
                # Mark for POS sync
                self.mark_pos_pending(f"Promotion updated: {', '.join(updated_fields)}")
                
                logger.info(f"Promotion {self.sk} updated fields: {', '.join(updated_fields)} by {updated_by}")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to update promotion {self.sk}: {str(e)}")
            raise
    
    def soft_delete(self, deleted_by: str, reason: str) -> 'Promotion':
        """
        Soft delete the promotion
        
        Args:
            deleted_by: User who deleted the promotion
            reason: Reason for deletion
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            if not reason or not reason.strip():
                raise ValueError("Reason is required for deletion")
            
            self.isDeleted = True
            self.status = "deactivated"
            self.updated_at = datetime.now(timezone.utc)
            self.pos_sync_status = "pending"  # Flag for POS sync
            
            # Add to audit log
            self._add_audit_log(
                action="deleted",
                user_id=deleted_by,
                reason=reason.strip()
            )
            
            self.save()
            
            # Mark for POS sync
            self.mark_pos_pending(f"Promotion deleted: {reason}")
            
            logger.info(f"Promotion {self.sk} soft-deleted by {deleted_by}: {reason}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to soft delete promotion {self.sk}: {str(e)}")
            raise
    
    def restore(self, restored_by: str) -> 'Promotion':
        """
        Restore a soft-deleted promotion
        
        Args:
            restored_by: User who restored the promotion
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            self.isDeleted = False
            self.status = "draft"  # Restored promotions go back to draft
            self.updated_at = datetime.now(timezone.utc)
            self.pos_sync_status = "pending"  # Flag for POS sync
            
            self.save()
            
            # Add to audit log
            self._add_audit_log(
                action="restored",
                user_id=restored_by
            )
            
            logger.info(f"Promotion {self.sk} restored by {restored_by}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to restore promotion {self.sk}: {str(e)}")
            raise
    
    def mark_pos_synced(self, terminal_id: str = None) -> 'Promotion':
        """
        Mark promotion as successfully synced with POS
        
        Args:
            terminal_id: POS terminal ID that synced
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            self.pos_sync_status = "synced"
            self.last_pos_sync = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
            self.save()
            
            logger.info(f"Promotion {self.sk} marked as POS synced")
            return self
            
        except Exception as e:
            logger.error(f"Failed to mark promotion as POS synced: {str(e)}")
            raise
    
    def mark_pos_pending(self, reason: str = None) -> 'Promotion':
        """
        Mark promotion as needing POS sync
        
        Args:
            reason: Reason for pending sync
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            self.pos_sync_status = "pending"
            self.updated_at = datetime.now(timezone.utc)
            self.save()
            
            if reason:
                logger.info(f"Promotion {self.sk} marked as pending POS sync: {reason}")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to mark promotion as pending POS sync: {str(e)}")
            raise
    
    def add_target(self, target_id: str, target_name: str = None) -> 'Promotion':
        """
        Add a target to the promotion
        
        Args:
            target_id: ID of the target (category_id, product_id, etc.)
            target_name: Display name of the target
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            # Check if target already exists
            for item in self.target_ids:
                if item.target_id == target_id:
                    logger.warning(f"Target {target_id} already exists in promotion {self.sk}")
                    return self
            
            # Add new target
            target_item = TargetIdItem(
                target_id=target_id,
                target_name=target_name
            )
            self.target_ids.append(target_item)
            self.updated_at = datetime.now(timezone.utc)
            self.pos_sync_status = "pending"  # Flag for POS sync
            
            self.save()
            
            logger.info(f"Target {target_id} added to promotion {self.sk}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to add target to promotion {self.sk}: {str(e)}")
            raise
    
    def remove_target(self, target_id: str) -> 'Promotion':
        """
        Remove a target from the promotion
        
        Args:
            target_id: ID of the target to remove
        
        Returns:
            Promotion: Updated promotion instance
        """
        try:
            # Find and remove target
            new_target_ids = []
            removed = False
            
            for item in self.target_ids:
                if item.target_id != target_id:
                    new_target_ids.append(item)
                else:
                    removed = True
            
            if removed:
                self.target_ids = new_target_ids
                self.updated_at = datetime.now(timezone.utc)
                self.pos_sync_status = "pending"  # Flag for POS sync
                self.save()
                
                logger.info(f"Target {target_id} removed from promotion {self.sk}")
            else:
                logger.warning(f"Target {target_id} not found in promotion {self.sk}")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to remove target from promotion {self.sk}: {str(e)}")
            raise
    
    def _add_audit_log(self, action: str, user_id: str, 
                      changes: str = None, reason: str = None) -> None:
        """
        Add entry to audit log
        
        Args:
            action: Action performed
            user_id: User who performed the action
            changes: JSON string of changes
            reason: Reason for the action
        """
        try:
            audit_item = AuditLogItem(
                action=action,
                user_id=user_id,
                timestamp=datetime.now(timezone.utc),
                changes=changes,
                reason=reason
            )
            
            # Limit audit log to last 100 entries
            if len(self.audit_log) >= 100:
                self.audit_log = self.audit_log[-99:]
            
            self.audit_log.append(audit_item)
            self.save()
            
        except Exception as e:
            logger.error(f"Failed to add audit log for promotion {self.sk}: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert promotion to dictionary for API response
        
        Returns:
            dict: Dictionary representation
        """
        try:
            promotion_dict = {
                "promotion_id": self.sk.replace("PROMO-", ""),
                "name": self.name,
                "description": self.description,
                "type": self.type,
                "discount_value": self.discount_value,
                "promotion_type": self.promotion_type,
                "target_type": self.target_type,
                "target_ids": [
                    {"target_id": item.target_id, "target_name": item.target_name}
                    for item in self.target_ids
                ],
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
                "isDeleted": self.isDeleted,
                "usage_limit": int(self.usage_limit) if self.usage_limit is not None else None,
                "current_usage": int(self.current_usage) if self.current_usage else 0,
                "total_revenue_impact": float(self.total_revenue_impact) if self.total_revenue_impact else 0.0,
                "created_by": self.created_by,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "status": self.status,
                "deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
                "deactivated_by": self.deactivated_by,
                "pos_sync_status": self.pos_sync_status,
                "last_pos_sync": self.last_pos_sync.isoformat() if self.last_pos_sync else None,
                "priority": int(self.priority) if self.priority else 1,
                "min_purchase_amount": float(self.min_purchase_amount) if self.min_purchase_amount else None,
                "stackable": self.stackable,
                "pos_promo_id": self.pos_promo_id,
                "auto_apply": self.auto_apply,
                "seasonal_tag": self.seasonal_tag,
                "customer_segment": self.customer_segment,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "is_active": self.is_active(),
                "days_remaining": (self.end_date.date() - datetime.now(timezone.utc).date()).days 
                                if self.end_date and datetime.now(timezone.utc).date() <= self.end_date.date() 
                                else 0,
                "usage_percentage": (self.current_usage / self.usage_limit * 100) 
                                  if self.usage_limit and self.usage_limit > 0 
                                  else None
            }
            
            # Add usage history count (not full history to avoid huge responses)
            promotion_dict["usage_history_count"] = len(self.usage_history)
            
            # Add audit log count
            promotion_dict["audit_log_count"] = len(self.audit_log)
            
            # Add recent audit entries (last 5)
            if self.audit_log:
                promotion_dict["recent_audit"] = [
                    {
                        "action": item.action,
                        "user_id": item.user_id,
                        "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                        "reason": item.reason
                    }
                    for item in self.audit_log[-5:]  # Last 5 entries
                ]
            
            return promotion_dict
            
        except Exception as e:
            logger.error(f"Error converting promotion to dict: {str(e)}")
            return {}
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """
        Minimal dictionary representation (for listings)
        
        Returns:
            dict: Basic promotion info
        """
        try:
            return {
                "id": self.sk.replace("PROMO-", ""),
                "name": self.name,
                "type": self.type,
                "discount_value": self.discount_value,
                "promotion_type": self.promotion_type,
                "target_type": self.target_type,
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
                "status": self.status,
                "is_active": self.is_active(),
                "current_usage": self.current_usage,
                "usage_limit": self.usage_limit,
                "priority": self.priority,
                "stackable": self.stackable
            }
        except Exception as e:
            logger.error(f"Error converting promotion to simple dict: {str(e)}")
            return {}
    
    def to_pos_representation(self) -> Dict[str, Any]:
        """
        Get promotion data formatted for POS system
        
        Returns:
            dict: POS-friendly promotion representation
        """
        try:
            pos_data = {
                "promotion_id": self.pos_promo_id or self.sk.replace("PROMO-", ""),
                "name": self.name,
                "type": self.type,
                "discount_value": self.discount_value,
                "discount_type": self.promotion_type,  # 'percentage' or 'fixed_amount'
                "target_type": self.target_type,
                "target_ids": [item.target_id for item in self.target_ids],
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
                "status": self.status,
                "is_active": self.is_active(),
                "usage_limit": self.usage_limit,
                "current_usage": self.current_usage,
                "min_purchase_amount": float(self.min_purchase_amount) if self.min_purchase_amount else 0.0,
                "priority": self.priority,
                "stackable": self.stackable,
                "auto_apply": self.auto_apply,
                "customer_segment": self.customer_segment,
                "last_updated": self.updated_at.isoformat() if self.updated_at else None
            }
            
            return pos_data
            
        except Exception as e:
            logger.error(f"Error converting promotion to POS representation: {str(e)}")
            return {}


# ============= PROMOTION VALIDATION =============

def validate_promotion_id(promotion_id: str) -> bool:
    """
    Validate if a promotion ID is in correct format
    
    Args:
        promotion_id: Promotion ID to validate
    
    Returns:
        bool: True if valid format, False otherwise
    """
    try:
        if not promotion_id:
            return False
        
        # Check format: PROMO-##### where ##### are exactly 5 digits
        if not promotion_id.startswith('PROMO-'):
            return False
        
        number_part = promotion_id[6:]  # Remove "PROMO-"
        if len(number_part) != 5:
            return False
        
        # Check if it's a valid number (00001-99999)
        number = int(number_part)
        return 1 <= number <= 99999
        
    except (ValueError, IndexError):
        return False


def validate_promotion_data(name: str, description: str, discount_value: str,
                           start_date: datetime, end_date: datetime, 
                           created_by: str, promotion_type: str = None) -> tuple[bool, str]:
    """
    Validate promotion data before creation
    
    Args:
        name: Promotion name to validate
        description: Promotion description to validate
        discount_value: Discount value to validate
        start_date: Start date to validate
        end_date: End date to validate
        created_by: Created by user to validate
        promotion_type: 'percentage' or 'fixed_amount'. Auto-detected if None.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Promotion name is required"
    
    if len(name.strip()) > 100:
        return False, "Promotion name must be 100 characters or less"
    
    if not description or not description.strip():
        return False, "Promotion description is required"
    
    if len(description.strip()) > 500:
        return False, "Promotion description must be 500 characters or less"
    
    if not discount_value:
        return False, "Discount value is required"
    
    # Auto-detect promotion_type if not provided
    if not promotion_type:
        if discount_value.endswith('%'):
            promotion_type = 'percentage'
        else:
            promotion_type = 'fixed_amount'
    
    # Validate discount value format with promotion_type
    try:
        Promotion._validate_discount_value(discount_value, promotion_type)
    except ValueError as e:
        return False, str(e)
    
    if not start_date or not end_date:
        return False, "Start date and end date are required"
    
    if start_date >= end_date:
        return False, "Start date must be before end date"
    
    if not created_by:
        return False, "Created by user is required"
    
    return True, ""


# ============= BULK OPERATIONS =============

def create_seasonal_promotions(seasonal_data: List[Dict], created_by: str) -> Dict:
    """
    Create multiple seasonal promotions at once
    
    Args:
        seasonal_data: List of dictionaries with promotion data
        created_by: User creating the promotions
    
    Returns:
        dict: Summary of creation results
    """
    created_promotions = []
    errors = []
    
    for data in seasonal_data:
        try:
            name = data.get('name')
            description = data.get('description')
            discount_value = data.get('discount_value')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            seasonal_tag = data.get('seasonal_tag')
            
            # Validate required fields
            if not all([name, description, discount_value, start_date, end_date, seasonal_tag]):
                errors.append(f"Missing required fields in data: {data}")
                continue
            
            # Create promotion
            promotion = Promotion.create_promotion(
                name=name,
                description=description,
                discount_value=discount_value,
                start_date=start_date,
                end_date=end_date,
                created_by=created_by,
                seasonal_tag=seasonal_tag,
                **{k: v for k, v in data.items() if k not in ['name', 'description', 'discount_value', 'start_date', 'end_date', 'seasonal_tag']}
            )
            
            created_promotions.append(promotion.to_dict())
            
        except Exception as e:
            errors.append(f"Failed to create promotion from data {data}: {str(e)}")
    
    return {
        "created": created_promotions,
        "total_created": len(created_promotions),
        "errors": errors,
        "success": len(errors) == 0
    }


def activate_batch_promotions(promotion_ids: List[str], activated_by: str, reason: str = None) -> Dict:
    """
    Activate multiple promotions at once
    
    Args:
        promotion_ids: List of promotion IDs to activate
        activated_by: User activating the promotions
        reason: Reason for activation
    
    Returns:
        dict: Summary of activation results
    """
    activated = []
    errors = []
    
    for promo_id in promotion_ids:
        try:
            promotion = Promotion.get_by_id(promo_id)
            if not promotion:
                errors.append(f"Promotion not found: {promo_id}")
                continue
            
            if promotion.isDeleted:
                errors.append(f"Cannot activate deleted promotion: {promo_id}")
                continue
            
            promotion.activate(activated_by, reason)
            activated.append(promo_id)
            
        except Exception as e:
            errors.append(f"Failed to activate promotion {promo_id}: {str(e)}")
    
    return {
        "activated": activated,
        "total_activated": len(activated),
        "errors": errors,
        "success": len(errors) == 0
    }


# ============= PROMOTION MANAGER =============

class PromotionManager:
    """
    Manager class for promotion-related operations
    """
    
    @staticmethod
    def get_promotion_summary() -> Dict:
        """
        Get summary statistics for all promotions
        
        Returns:
            dict: Promotion summary
        """
        try:
            promotions = Promotion.get_all_promotions()
            total = len(promotions)
            
            # Count by status
            status_counts = {}
            type_counts = {}
            target_type_counts = {}
            
            active_promotions = 0
            total_revenue_impact = 0.0
            total_usage = 0
            
            for promotion in promotions:
                # Status counts
                status = promotion.status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Type counts
                promo_type = promotion.type
                type_counts[promo_type] = type_counts.get(promo_type, 0) + 1
                
                # Target type counts
                target_type = promotion.target_type
                target_type_counts[target_type] = target_type_counts.get(target_type, 0) + 1
                
                # Active promotions
                if promotion.is_active():
                    active_promotions += 1
                
                # Totals
                total_revenue_impact += float(promotion.total_revenue_impact or 0)
                total_usage += int(promotion.current_usage or 0)
            
            # Expiring soon (next 7 days)
            expiring_soon = len(Promotion.get_expiring_soon_promotions(days=7))
            
            # Seasonal promotions
            seasonal_promotions = len(Promotion.get_seasonal_promotions())
            
            return {
                "total_promotions": total,
                "active_promotions": active_promotions,
                "expiring_soon": expiring_soon,
                "seasonal_promotions": seasonal_promotions,
                "by_status": status_counts,
                "by_type": type_counts,
                "by_target_type": target_type_counts,
                "total_revenue_impact": round(total_revenue_impact, 2),
                "total_usage": total_usage,
                "average_usage_per_promotion": round(total_usage / total, 2) if total > 0 else 0,
                "average_revenue_impact": round(total_revenue_impact / total, 2) if total > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting promotion summary: {str(e)}")
            return {}
    
    @staticmethod
    def get_effective_discounts(original_amount: float, target_type: str = None,
                               target_id: str = None, branch_id: str = None) -> List[Dict]:
        """
        Get all applicable discounts for a given transaction
        
        Args:
            original_amount: Original transaction amount
            target_type: Type of target ('category', 'product', 'all')
            target_id: Specific target ID
            branch_id: Branch ID for location-specific promotions
        
        Returns:
            list: List of applicable promotions with calculated discounts
        """
        try:
            applicable_promotions = []
            
            # Get active promotions
            active_promotions = Promotion.get_active_promotions(target_type, target_id)
            
            for promotion in active_promotions:
                # Check minimum purchase amount
                if promotion.min_purchase_amount and original_amount < promotion.min_purchase_amount:
                    continue
                
                # Calculate discount amount
                discount_amount = promotion.calculate_discount_amount(original_amount)
                
                if discount_amount > 0:
                    applicable_promotions.append({
                        "promotion_id": promotion.sk.replace("PROMO-", ""),
                        "name": promotion.name,
                        "type": promotion.type,
                        "discount_value": promotion.discount_value,
                        "promotion_type": promotion.promotion_type,
                        "discount_amount": discount_amount,
                        "priority": promotion.priority,
                        "stackable": promotion.stackable,
                        "auto_apply": promotion.auto_apply,
                        "min_purchase_amount": float(promotion.min_purchase_amount) if promotion.min_purchase_amount else None
                    })
            
            # Sort by priority (lower number = higher priority)
            applicable_promotions.sort(key=lambda x: x["priority"])
            
            return applicable_promotions
            
        except Exception as e:
            logger.error(f"Error getting effective discounts: {str(e)}")
            return []
    
    @staticmethod
    def calculate_best_discount(original_amount: float, target_type: str = None,
                               target_id: str = None, branch_id: str = None) -> Dict:
        """
        Calculate the best discount for a transaction
        
        Args:
            original_amount: Original transaction amount
            target_type: Type of target ('category', 'product', 'all')
            target_id: Specific target ID
            branch_id: Branch ID for location-specific promotions
        
        Returns:
            dict: Best discount information
        """
        try:
            applicable_promotions = PromotionManager.get_effective_discounts(
                original_amount, target_type, target_id, branch_id
            )
            
            if not applicable_promotions:
                return {
                    "discount_amount": 0.0,
                    "discount_percentage": 0.0,
                    "applicable_promotions": [],
                    "total_discount": 0.0
                }
            
            # Find stackable and non-stackable promotions
            stackable_promos = [p for p in applicable_promotions if p["stackable"]]
            non_stackable_promos = [p for p in applicable_promotions if not p["stackable"]]
            
            best_discount = 0.0
            best_promotion = None
            combined_discount = 0.0
            used_promotions = []
            
            # First, check non-stackable promotions (highest priority first)
            if non_stackable_promos:
                best_promotion = non_stackable_promos[0]  # Already sorted by priority
                best_discount = best_promotion["discount_amount"]
                used_promotions = [best_promotion]
            else:
                # Use all stackable promotions
                for promo in stackable_promos:
                    combined_discount += promo["discount_amount"]
                    used_promotions.append(promo)
                
                if combined_discount > best_discount:
                    best_discount = combined_discount
            
            # Ensure discount doesn't exceed original amount
            final_discount = min(best_discount or combined_discount, original_amount)
            
            return {
                "discount_amount": final_discount,
                "discount_percentage": (final_discount / original_amount * 100) if original_amount > 0 else 0,
                "applicable_promotions": applicable_promotions,
                "used_promotions": used_promotions,
                "total_discount": final_discount,
                "final_amount": original_amount - final_discount
            }
            
        except Exception as e:
            logger.error(f"Error calculating best discount: {str(e)}")
            return {
                "discount_amount": 0.0,
                "discount_percentage": 0.0,
                "applicable_promotions": [],
                "total_discount": 0.0,
                "final_amount": original_amount
            }
    
    @staticmethod
    def get_promotion_effectiveness_report(days: int = 30) -> Dict:
        """
        Get promotion effectiveness report
        
        Args:
            days: Number of days to look back
        
        Returns:
            dict: Promotion effectiveness report
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            promotions = Promotion.get_all_promotions()
            report = {
                "period_days": days,
                "total_promotions": len(promotions),
                "promotions_used": 0,
                "total_discounts_given": 0.0,
                "average_discount_per_use": 0.0,
                "most_effective_promotions": [],
                "least_effective_promotions": []
            }
            
            promotion_stats = []
            
            for promotion in promotions:
                # Count recent usage
                recent_usage = 0
                recent_discount = 0.0
                
                for usage in promotion.usage_history:
                    if usage.timestamp >= cutoff_date:
                        recent_usage += 1
                        recent_discount += float(usage.discount_amount or 0)
                
                if recent_usage > 0:
                    report["promotions_used"] += 1
                    report["total_discounts_given"] += recent_discount
                
                promotion_stats.append({
                    "promotion_id": promotion.sk.replace("PROMO-", ""),
                    "name": promotion.name,
                    "recent_usage": recent_usage,
                    "recent_discount": recent_discount,
                    "total_usage": promotion.current_usage,
                    "total_discount": promotion.total_revenue_impact,
                    "effectiveness": recent_discount / recent_usage if recent_usage > 0 else 0
                })
            
            # Sort by effectiveness
            promotion_stats.sort(key=lambda x: x["effectiveness"], reverse=True)
            
            # Get most and least effective
            report["most_effective_promotions"] = promotion_stats[:5]
            report["least_effective_promotions"] = promotion_stats[-5:] if len(promotion_stats) >= 5 else []
            
            # Calculate averages
            if report["promotions_used"] > 0:
                report["average_discount_per_use"] = report["total_discounts_given"] / sum(
                    stat["recent_usage"] for stat in promotion_stats
                )
            
            return report
            
        except Exception as e:
            logger.error(f"Error getting promotion effectiveness report: {str(e)}")
            return {}
    
    @staticmethod
    def sync_promotions_to_pos(promotion_ids: List[str] = None) -> Dict:
        """
        Sync promotions to POS system
        
        Args:
            promotion_ids: Specific promotion IDs to sync (all if None)
        
        Returns:
            dict: Sync operation results
        """
        try:
            promotions_to_sync = []
            
            if promotion_ids:
                for promo_id in promotion_ids:
                    promotion = Promotion.get_by_id(promo_id)
                    if promotion and not promotion.isDeleted:
                        promotions_to_sync.append(promotion)
            else:
                # Sync all promotions that need sync
                promotions_to_sync = [
                    p for p in Promotion.get_all_promotions() 
                    if p.pos_sync_status != "synced"
                ]
            
            synced = []
            failed = []
            
            for promotion in promotions_to_sync:
                try:
                    # In a real implementation, this would call the POS API
                    # For now, simulate successful sync
                    promotion.mark_pos_synced()
                    synced.append(promotion.sk.replace("PROMO-", ""))
                    
                except Exception as e:
                    logger.error(f"Failed to sync promotion {promotion.sk}: {str(e)}")
                    failed.append({
                        "promotion_id": promotion.sk.replace("PROMO-", ""),
                        "error": str(e)
                    })
            
            return {
                "synced": synced,
                "failed": failed,
                "total_synced": len(synced),
                "total_failed": len(failed),
                "success_rate": len(synced) / len(promotions_to_sync) if promotions_to_sync else 0
            }
            
        except Exception as e:
            logger.error(f"Error syncing promotions to POS: {str(e)}")
            return {"error": str(e)}
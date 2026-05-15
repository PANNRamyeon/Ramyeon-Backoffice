"""
Promotion Model - Following ERD Specification with POS Sync & Seasonal Promotions
PK = "promotions", SK = "PROMO-#####" (5-digit format)
Single Table Design using RamyeonCornerDB
Supports recurrence rules (e.g., "monthly:15,30")
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

from app.utils import generate_sk, get_dynamo_table, DYNAMO_TABLE_NAME, AWS_REGION
from models.Product import Product

logger = logging.getLogger(__name__)


class FixedUTCDateTimeAttribute(UTCDateTimeAttribute):
    def deserialize(self, value):
        if isinstance(value, str):
            match = re.search(r'0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)(?:[+-]\d{2}:\d{2}|Z)?', value)
            if match:
                corrected = match.group(1)
                try:
                    dt = datetime.fromisoformat(corrected)
                except ValueError:
                    dt = datetime.fromisoformat(corrected + '+00:00')
                iso = dt.isoformat(timespec='microseconds')
                if iso.endswith('+00:00'):
                    iso = iso.replace('+00:00', '+0000')
                elif iso.endswith('Z'):
                    iso = iso.replace('Z', '+0000')
                else:
                    iso += '+0000'
                value = iso
        return super().deserialize(value)


class TargetIdItem(MapAttribute):
    target_id = UnicodeAttribute()
    target_name = UnicodeAttribute(null=True)


class UsageHistoryItem(MapAttribute):
    order_id = UnicodeAttribute()
    user_id = UnicodeAttribute(null=True)
    branch_id = UnicodeAttribute(null=True)
    discount_amount = NumberAttribute()
    transaction_amount = NumberAttribute()
    timestamp = FixedUTCDateTimeAttribute()
    pos_terminal_id = UnicodeAttribute(null=True)
    items = UnicodeAttribute(null=True)


class AuditLogItem(MapAttribute):
    action = UnicodeAttribute()
    user_id = UnicodeAttribute()
    timestamp = FixedUTCDateTimeAttribute()
    changes = UnicodeAttribute(null=True)
    reason = UnicodeAttribute(null=True)


class Promotion(Model):
    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION
        read_capacity_units = 5
        write_capacity_units = 3

    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="promotions")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")

    name = UnicodeAttribute()
    description = UnicodeAttribute()
    type = UnicodeAttribute()
    discount_value = UnicodeAttribute()
    promotion_type = UnicodeAttribute()

    target_type = UnicodeAttribute()
    target_ids = ListAttribute(of=TargetIdItem, default=list)

    start_date = FixedUTCDateTimeAttribute()
    end_date = FixedUTCDateTimeAttribute()

    isDeleted = BooleanAttribute(default=False)
    usage_limit = NumberAttribute(null=True)
    current_usage = NumberAttribute(default=0)
    total_revenue_impact = NumberAttribute(default=0.0)

    usage_history = ListAttribute(of=UsageHistoryItem, default=list)

    created_by = UnicodeAttribute()
    created_at = FixedUTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))
    status = UnicodeAttribute(default="draft")
    deactivated_at = FixedUTCDateTimeAttribute(null=True)
    deactivated_by = UnicodeAttribute(null=True)

    pos_sync_status = UnicodeAttribute(default="synced")
    last_pos_sync = FixedUTCDateTimeAttribute(null=True)
    priority = NumberAttribute(default=1)
    min_purchase_amount = NumberAttribute(null=True)
    stackable = BooleanAttribute(default=True)
    pos_promo_id = UnicodeAttribute(null=True)
    auto_apply = BooleanAttribute(default=False)
    audit_log = ListAttribute(of=AuditLogItem, default=list)
    seasonal_tag = UnicodeAttribute(null=True)
    customer_segment = UnicodeAttribute(default="all")
    updated_at = FixedUTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))

    recurrence_rule = UnicodeAttribute(null=True)  # e.g., "monthly:15,30"

    # New: per‑customer usage limit
    per_customer_limit = NumberAttribute(null=True)  # max uses per customer, null = unlimited

    class StatusIndex(GlobalSecondaryIndex):
        class Meta:
            index_name = 'PromotionStatusIndex'
            read_capacity_units = 5
            write_capacity_units = 2
            projection = AllProjection()
        pk = UnicodeAttribute(hash_key=True, attr_name="PK")
        status = UnicodeAttribute(range_key=True)

    class TargetTypeIndex(GlobalSecondaryIndex):
        class Meta:
            index_name = 'PromotionTargetTypeIndex'
            read_capacity_units = 3
            write_capacity_units = 2
            projection = AllProjection()
        pk = UnicodeAttribute(hash_key=True, attr_name="PK")
        target_type = UnicodeAttribute(range_key=True)

    class SeasonalIndex(GlobalSecondaryIndex):
        class Meta:
            index_name = 'PromotionSeasonalIndex'
            read_capacity_units = 2
            write_capacity_units = 1
            projection = AllProjection()
        pk = UnicodeAttribute(hash_key=True, attr_name="PK")
        seasonal_tag = UnicodeAttribute(range_key=True)

    status_index = StatusIndex()
    target_type_index = TargetTypeIndex()
    seasonal_index = SeasonalIndex()

    @classmethod
    def create_promotion(cls, name: str, description: str, discount_value: str,
                        start_date: datetime, end_date: datetime, created_by: str,
                        target_type: str = "all", promotion_type: str = None,
                        recurrence_rule: str = None,
                        min_purchase_amount: Optional[float] = None,
                        per_customer_limit: Optional[int] = None,
                        **kwargs) -> 'Promotion':
        if not name or not name.strip():
            raise ValueError("Promotion name is required")
        # description is optional – no validation
        if not discount_value:
            raise ValueError("Discount value is required")
        if not start_date or not end_date:
            raise ValueError("Start date and end date are required")
        if start_date.date() > end_date.date():
            raise ValueError("Start date cannot be after end date")
        if not created_by:
            raise ValueError("Created by user is required")

        if target_type not in ['category', 'product', 'all']:
            raise ValueError("Target type must be 'category', 'product', or 'all'")

        if not promotion_type:
            promotion_type = 'percentage' if discount_value.endswith('%') else 'fixed_amount'
        elif promotion_type not in ['percentage', 'fixed_amount']:
            raise ValueError("promotion_type must be 'percentage' or 'fixed_amount'")

        cls._validate_discount_value(discount_value, promotion_type)

        if min_purchase_amount is None:
            min_purchase_amount = 100  # default minimum

        from app.utils import counter_service
        raw_seq = counter_service.get_next_id(collection_name='promo_seq', prefix='', width=5)
        next_seq = raw_seq.lstrip('-')
        sk_value = f"PROMO-{next_seq}"

        promotion = cls(
            pk="promotions",
            sk=sk_value,
            name=name.strip(),
            description=description.strip() if description else '',  # safe handling
            discount_value=discount_value,
            promotion_type=promotion_type,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by,
            target_type=target_type,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            recurrence_rule=recurrence_rule,
            min_purchase_amount=min_purchase_amount,
            per_customer_limit=per_customer_limit,
            **kwargs
        )
        promotion.save()

        promotion._add_audit_log(
            action="created",
            user_id=created_by,
            changes=json.dumps({"status": "draft"})
        )
        if promotion.pos_promo_id:
            promotion.mark_pos_synced()

        logger.info(f"Promotion created: {sk_value} - '{name}' by {created_by}")
        return promotion

    @classmethod
    def get_by_id(cls, promotion_id: str, include_deleted: bool = False) -> 'Promotion | None':
        if not promotion_id.startswith('PROMO-'):
            promotion_id = f"PROMO-{promotion_id.zfill(5)}"
        try:
            promotion = cls.get("promotions", promotion_id)
            if promotion.isDeleted and not include_deleted:
                return None
            return promotion
        except cls.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error fetching promotion {promotion_id}: {e}")
            return None

    @classmethod
    def get_active_promotions(cls, target_type: str = None, target_id: str = None) -> List['Promotion']:
        try:
            active = []
            for promo in cls.status_index.query(
                "promotions", cls.status == "active", filter_condition=(cls.isDeleted == False)
            ):
                if promo.is_active():
                    if target_type and promo.target_type != target_type:
                        continue
                    if target_id and not cls._matches_target(promo, target_id):
                        continue
                    active.append(promo)
            active.sort(key=lambda x: x.priority)
            return active
        except Exception as e:
            logger.error(f"Error getting active promotions: {e}")
            return []

    @classmethod
    def get_expiring_soon_promotions(cls, days: int = 7) -> List['Promotion']:
        try:
            now = datetime.now(timezone.utc)
            cutoff = now + timedelta(days=days)
            expiring = []
            for promo in cls.status_index.query(
                "promotions", cls.status == "active", filter_condition=(cls.isDeleted == False)
            ):
                if promo.recurrence_rule:
                    continue
                if promo.end_date <= cutoff and promo.end_date >= now:
                    expiring.append(promo)
            return expiring
        except Exception as e:
            return []

    @classmethod
    def get_seasonal_promotions(cls, seasonal_tag: str = None) -> List['Promotion']:
        try:
            if seasonal_tag:
                return list(cls.seasonal_index.query("promotions", cls.seasonal_tag == seasonal_tag))
            else:
                result = []
                for promo in cls.query("promotions", filter_condition=(cls.seasonal_tag != None) & (cls.isDeleted == False)):
                    result.append(promo)
                return result
        except Exception as e:
            return []

    @classmethod
    def get_promotions_by_target(cls, target_type: str, target_id: str = None) -> List['Promotion']:
        try:
            promotions = []
            query_iter = cls.target_type_index.query(
                "promotions", cls.target_type == target_type,
                filter_condition=(cls.isDeleted == False) & (cls.status == "active")
            )
            for promo in query_iter:
                if target_id and not cls._matches_target(promo, target_id):
                    continue
                promotions.append(promo)
            return promotions
        except Exception as e:
            return []

    @classmethod
    def get_all_promotions(cls, include_deleted: bool = False) -> List['Promotion']:
        if include_deleted:
            return list(cls.query("promotions"))
        else:
            return list(cls.query("promotions", filter_condition=cls.isDeleted == False))

    @classmethod
    def _matches_target(cls, promo, target_id):
        if promo.target_type == "all":
            return True
        if promo.target_type in ["category", "product"]:
            return any(item.target_id == target_id for item in promo.target_ids)
        return False

    @classmethod
    def _validate_discount_value(cls, discount_value, promotion_type):
        if not discount_value:
            raise ValueError("Discount value cannot be empty")
        if promotion_type == 'percentage':
            if not discount_value.endswith('%'):
                raise ValueError("Percentage discount must end with '%'")
            percentage = float(discount_value[:-1])
            if not 0 < percentage <= 100:
                raise ValueError("Percentage must be between 0 and 100")
        elif promotion_type == 'fixed_amount':
            if discount_value.endswith('%'):
                raise ValueError("Fixed amount discount should not end with '%'")
            amount = float(discount_value)
            if amount <= 0:
                raise ValueError("Fixed amount must be greater than 0")
        else:
            raise ValueError("Invalid promotion_type")

    def _matches_recurrence(self, now: datetime) -> bool:
        if not self.recurrence_rule:
            return False
        try:
            parts = self.recurrence_rule.split(':', 1)
            freq = parts[0]
            specifics = parts[1].split(',') if len(parts) > 1 else []
            if freq == 'monthly':
                return str(now.day) in specifics
            elif freq == 'yearly':
                for spec in specifics:
                    try:
                        month, day = map(int, spec.split('-'))
                        if now.month == month and now.day == day:
                            return True
                    except:
                        continue
                return False
            else:
                return False
        except Exception as e:
            logger.error(f"Error parsing recurrence rule: {e}")
            return False

    def is_active(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.isDeleted or self.status != "active":
            return False
        if self.recurrence_rule:
            if self.start_date and self.end_date:
                if not (self.start_date <= now <= self.end_date):
                    return False
            if not self._matches_recurrence(now):
                return False
        else:
            if not (self.start_date <= now <= self.end_date):
                return False
        if self.usage_limit is not None and self.current_usage >= self.usage_limit:
            return False
        return True

    def calculate_discount_amount(self, original_amount: float) -> float:
        if not self.is_active():
            return 0.0
        if self.min_purchase_amount and self.min_purchase_amount > 0 and original_amount < self.min_purchase_amount:
            return 0.0
        if self.promotion_type == 'percentage':
            discount = original_amount * float(self.discount_value[:-1]) / 100
        else:
            discount = float(self.discount_value)
        return min(discount, original_amount)

    def activate(self, activated_by: str, reason: str = None) -> 'Promotion':
        old_status = self.status
        self.status = "active"
        self.updated_at = datetime.now(timezone.utc)
        self.pos_sync_status = "pending"
        if self.deactivated_at:
            self.deactivated_at = None
            self.deactivated_by = None
        self.save()
        self._add_audit_log("activated", activated_by,
                            json.dumps({"status": {"old": old_status, "new": "active"}}), reason)
        self.mark_pos_pending(f"Promotion activated by {activated_by}")
        return self

    def deactivate(self, deactivated_by: str, reason: str) -> 'Promotion':
        old_status = self.status
        self.status = "deactivated"
        self.deactivated_at = datetime.now(timezone.utc)
        self.deactivated_by = deactivated_by
        self.updated_at = datetime.now(timezone.utc)
        self.pos_sync_status = "pending"
        self.save()
        self._add_audit_log("deactivated", deactivated_by,
                            json.dumps({"status": {"old": old_status, "new": "deactivated"}}), reason.strip())
        self.mark_pos_pending(f"Promotion deactivated: {reason}")
        return self

    def update_promotion(self, updated_by: str, **kwargs) -> 'Promotion':
        changes = {}
        updated_fields = []
        for key, value in kwargs.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                if key in ['discount_value', 'promotion_type']:
                    disc = value if key == 'discount_value' else self.discount_value
                    ptype = value if key == 'promotion_type' else self.promotion_type
                    self._validate_discount_value(disc, ptype)
                if key in ['start_date', 'end_date'] and not self.recurrence_rule:
                    if key == 'start_date' and value.date() > self.end_date.date():
                        raise ValueError("Start date cannot be after end date")
                    if key == 'end_date' and value.date() < self.start_date.date():
                        raise ValueError("End date cannot be before start date")
                if old_value != value:
                    setattr(self, key, value)
                    updated_fields.append(key)
                    changes[key] = {"old": old_value, "new": value}
        if updated_fields:
            self.updated_at = datetime.now(timezone.utc)
            self.pos_sync_status = "pending"
            self.save()
            def _serialize(v):
                return v.isoformat() if isinstance(v, datetime) else v
            safe_changes = {k: {"old": _serialize(v["old"]), "new": _serialize(v["new"])} for k, v in changes.items()}
            self._add_audit_log("modified", updated_by, json.dumps(safe_changes))
            self.mark_pos_pending(f"Promotion updated: {', '.join(updated_fields)}")
        return self

    def soft_delete(self, deleted_by: str, reason: str) -> 'Promotion':
        if not reason or not reason.strip():
            raise ValueError("Reason is required")
        self.isDeleted = True
        self.status = "deactivated"
        self.updated_at = datetime.now(timezone.utc)
        self.pos_sync_status = "pending"
        self._add_audit_log("deleted", deleted_by, reason=reason.strip())
        self.save()
        self.mark_pos_pending(f"Promotion deleted: {reason}")
        return self

    def restore(self, restored_by: str) -> 'Promotion':
        self.isDeleted = False
        self.status = "draft"
        self.updated_at = datetime.now(timezone.utc)
        self.pos_sync_status = "pending"
        self.save()
        self._add_audit_log("restored", restored_by)
        return self

    def mark_pos_synced(self, terminal_id: str = None) -> 'Promotion':
        self.pos_sync_status = "synced"
        self.last_pos_sync = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.save()
        return self

    def mark_pos_pending(self, reason: str = None) -> 'Promotion':
        self.pos_sync_status = "pending"
        self.updated_at = datetime.now(timezone.utc)
        self.save()
        return self

    def add_target(self, target_id: str, target_name: str = None) -> 'Promotion':
        for item in self.target_ids:
            if item.target_id == target_id:
                return self
        self.target_ids.append(TargetIdItem(target_id=target_id, target_name=target_name))
        self.updated_at = datetime.now(timezone.utc)
        self.pos_sync_status = "pending"
        self.save()
        return self

    def remove_target(self, target_id: str) -> 'Promotion':
        new_list = [item for item in self.target_ids if item.target_id != target_id]
        if len(new_list) < len(self.target_ids):
            self.target_ids = new_list
            self.updated_at = datetime.now(timezone.utc)
            self.pos_sync_status = "pending"
            self.save()
        return self

    def _add_audit_log(self, action, user_id, changes=None, reason=None):
        audit_item = AuditLogItem(
            action=action, user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            changes=changes, reason=reason
        )
        if len(self.audit_log) >= 100:
            self.audit_log = self.audit_log[-99:]
        self.audit_log.append(audit_item)
        self.save()

    def to_dict(self) -> Dict[str, Any]:
        try:
            promo_id = self.sk.replace("PROMO-", "")
            data = {
                "promotion_id": promo_id,
                "name": self.name,
                "description": self.description,
                "type": self.type,
                "discount_value": self.discount_value,
                "promotion_type": self.promotion_type,
                "target_type": self.target_type,
                "target_ids": [{"target_id": item.target_id, "target_name": item.target_name} for item in self.target_ids],
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
                "recurrence_rule": self.recurrence_rule,
                "per_customer_limit": int(self.per_customer_limit) if self.per_customer_limit is not None else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "is_active": self.is_active(),
            }
            if self.audit_log:
                data["recent_audit"] = [{
                    "action": item.action,
                    "user_id": item.user_id,
                    "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                    "reason": item.reason
                } for item in self.audit_log[-5:]]
            return data
        except Exception as e:
            logger.error(f"Error in to_dict: {e}")
            return {}

    def to_simple_dict(self):
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
            "stackable": self.stackable,
            "recurrence_rule": self.recurrence_rule,
            "per_customer_limit": self.per_customer_limit,
            "min_purchase_amount": float(self.min_purchase_amount) if self.min_purchase_amount else None,
        }

    def to_pos_representation(self):
        return {
            "promotion_id": self.pos_promo_id or self.sk.replace("PROMO-", ""),
            "name": self.name,
            "type": self.type,
            "discount_value": self.discount_value,
            "discount_type": self.promotion_type,
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
            "recurrence_rule": self.recurrence_rule,
            "per_customer_limit": self.per_customer_limit,
            "last_updated": self.updated_at.isoformat() if self.updated_at else None
        }


# ============= VALIDATION & BULK =============

def validate_promotion_id(promotion_id: str) -> bool:
    if not promotion_id or not promotion_id.startswith('PROMO-'):
        return False
    number_part = promotion_id[6:]
    if len(number_part) != 5:
        return False
    try:
        num = int(number_part)
        return 1 <= num <= 99999
    except ValueError:
        return False


def validate_promotion_data(name, description, discount_value, start_date, end_date, created_by, promotion_type=None):
    if not name or not name.strip() or len(name.strip()) > 100:
        return False, "Invalid name"
    if not description or not description.strip() or len(description.strip()) > 500:
        return False, "Invalid description"
    if not discount_value:
        return False, "Discount value required"
    if not promotion_type:
        promotion_type = 'percentage' if discount_value.endswith('%') else 'fixed_amount'
    try:
        Promotion._validate_discount_value(discount_value, promotion_type)
    except ValueError as e:
        return False, str(e)
    if not start_date or not end_date:
        return False, "Dates required"
    if start_date.date() > end_date.date():
        return False, "Start date cannot be after end date"
    if not created_by:
        return False, "Created by required"
    return True, ""


def create_seasonal_promotions(seasonal_data, created_by):
    created = []
    errors = []
    for data in seasonal_data:
        try:
            promo = Promotion.create_promotion(
                name=data['name'], description=data['description'],
                discount_value=data['discount_value'],
                start_date=data['start_date'], end_date=data['end_date'],
                created_by=created_by, seasonal_tag=data.get('seasonal_tag'),
                recurrence_rule=data.get('recurrence_rule'),
                **{k: v for k, v in data.items() if k not in ['name','description','discount_value','start_date','end_date','seasonal_tag','recurrence_rule']}
            )
            created.append(promo.to_dict())
        except Exception as e:
            errors.append(str(e))
    return {"created": created, "total_created": len(created), "errors": errors, "success": len(errors) == 0}


def activate_batch_promotions(promotion_ids, activated_by, reason=None):
    activated = []
    errors = []
    for pid in promotion_ids:
        try:
            promo = Promotion.get_by_id(pid)
            if not promo or promo.isDeleted:
                errors.append(f"Promotion {pid} not found or deleted")
                continue
            promo.activate(activated_by, reason)
            activated.append(pid)
        except Exception as e:
            errors.append(str(e))
    return {"activated": activated, "total_activated": len(activated), "errors": errors, "success": len(errors) == 0}


# ============= PROMOTION MANAGER =============

class PromotionManager:
    """Manager class for statistics, discount calculations, POS sync."""
    @staticmethod
    def get_promotion_summary():
        try:
            promotions = Promotion.get_all_promotions()
            total = len(promotions)
            by_status = {}
            by_type = {}
            by_target = {}
            active_count = 0
            total_rev = 0.0
            total_usage = 0
            for p in promotions:
                by_status[p.status] = by_status.get(p.status, 0) + 1
                by_type[p.type] = by_type.get(p.type, 0) + 1
                by_target[p.target_type] = by_target.get(p.target_type, 0) + 1
                if p.is_active():
                    active_count += 1
                total_rev += float(p.total_revenue_impact or 0)
                total_usage += int(p.current_usage or 0)
            expiring = len(Promotion.get_expiring_soon_promotions(7))
            seasonal = len(Promotion.get_seasonal_promotions())
            return {
                "total_promotions": total,
                "active_promotions": active_count,
                "expiring_soon": expiring,
                "seasonal_promotions": seasonal,
                "by_status": by_status,
                "by_type": by_type,
                "by_target_type": by_target,
                "total_revenue_impact": round(total_rev, 2),
                "total_usage": total_usage,
                "average_usage_per_promotion": round(total_usage / total, 2) if total else 0,
                "average_revenue_impact": round(total_rev / total, 2) if total else 0
            }
        except Exception as e:
            logger.error(f"Summary error: {e}")
            return {}

    @staticmethod
    def get_effective_discounts(original_amount, target_type=None, target_id=None, branch_id=None):
        try:
            applicable = []
            for promo in Promotion.get_active_promotions(target_type, target_id):
                discount = promo.calculate_discount_amount(original_amount)
                if discount > 0:
                    applicable.append({
                        "promotion_id": promo.sk.replace("PROMO-", ""),
                        "name": promo.name,
                        "type": promo.type,
                        "discount_value": promo.discount_value,
                        "promotion_type": promo.promotion_type,
                        "discount_amount": discount,
                        "priority": promo.priority,
                        "stackable": promo.stackable,
                        "auto_apply": promo.auto_apply,
                        "min_purchase_amount": float(promo.min_purchase_amount) if promo.min_purchase_amount else None
                    })
            applicable.sort(key=lambda x: x["priority"])
            return applicable
        except Exception as e:
            logger.error(f"Effective discounts error: {e}")
            return []

    @staticmethod
    def calculate_best_discount(original_amount, target_type=None, target_id=None, branch_id=None):
        applicable = PromotionManager.get_effective_discounts(original_amount, target_type, target_id, branch_id)
        if not applicable:
            return {"discount_amount": 0.0, "discount_percentage": 0.0, "applicable_promotions": [], "total_discount": 0.0}
        stackable = [p for p in applicable if p["stackable"]]
        non_stackable = [p for p in applicable if not p["stackable"]]
        best = 0.0
        used = []
        if non_stackable:
            best_promo = non_stackable[0]
            best = best_promo["discount_amount"]
            used = [best_promo]
        else:
            combined = 0.0
            for p in stackable:
                combined += p["discount_amount"]
                used.append(p)
            best = combined
        final = min(best, original_amount)
        return {
            "discount_amount": final,
            "discount_percentage": (final / original_amount * 100) if original_amount else 0,
            "applicable_promotions": applicable,
            "used_promotions": used,
            "total_discount": final,
            "final_amount": original_amount - final
        }

    @staticmethod
    def get_promotion_effectiveness_report(days=30):
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            promotions = Promotion.get_all_promotions()
            stats = []
            for p in promotions:
                recent_use = sum(1 for u in p.usage_history if u.timestamp >= cutoff)
                recent_disc = sum(float(u.discount_amount) for u in p.usage_history if u.timestamp >= cutoff)
                effectiveness = recent_disc / recent_use if recent_use else 0
                stats.append({
                    "promotion_id": p.sk.replace("PROMO-", ""),
                    "name": p.name,
                    "recent_usage": recent_use,
                    "recent_discount": recent_disc,
                    "total_usage": p.current_usage,
                    "total_discount": p.total_revenue_impact,
                    "effectiveness": effectiveness
                })
            stats.sort(key=lambda x: x["effectiveness"], reverse=True)
            return {
                "period_days": days,
                "total_promotions": len(promotions),
                "promotions_used": sum(1 for s in stats if s["recent_usage"] > 0),
                "total_discounts_given": sum(s["recent_discount"] for s in stats),
                "most_effective": stats[:5],
                "least_effective": stats[-5:] if len(stats) >= 5 else []
            }
        except Exception as e:
            logger.error(f"Effectiveness report error: {e}")
            return {}

    @staticmethod
    def sync_promotions_to_pos(promotion_ids=None):
        try:
            to_sync = []
            if promotion_ids:
                to_sync = [Promotion.get_by_id(pid) for pid in promotion_ids if Promotion.get_by_id(pid) and not Promotion.get_by_id(pid).isDeleted]
            else:
                to_sync = [p for p in Promotion.get_all_promotions() if p.pos_sync_status != "synced"]
            synced = []
            failed = []
            for p in to_sync:
                try:
                    p.mark_pos_synced()
                    synced.append(p.sk.replace("PROMO-", ""))
                except Exception as e:
                    failed.append({"promotion_id": p.sk.replace("PROMO-", ""), "error": str(e)})
            return {
                "synced": synced,
                "failed": failed,
                "total_synced": len(synced),
                "total_failed": len(failed),
                "success_rate": len(synced) / len(to_sync) if to_sync else 0
            }
        except Exception as e:
            logger.error(f"POS sync error: {e}")
            return {"error": str(e)}
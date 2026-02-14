"""
SalesLog Model - Following Single‑Table Design
PK = "saleslogs", SK = "SLOG-#####" (5‑digit)
Supports invoice/transaction logging with date‑based GSI.
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION

logger = logging.getLogger(__name__)


class SalesLogDateIndex(GlobalSecondaryIndex):
    """GSI for querying sales logs by transaction_date."""
    class Meta:
        index_name = 'saleslog-date-index'
        projection = AllProjection()
    pk = UnicodeAttribute(hash_key=True)          # always "saleslogs"
    transaction_date = UTCDateTimeAttribute(range_key=True)


class SalesLog(Model):
    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION

    # Primary key
    pk = UnicodeAttribute(hash_key=True, default="saleslogs")
    sk = UnicodeAttribute(range_key=True)          # "SLOG-00001"

    # GSI
    date_index = SalesLogDateIndex()

    # Core fields (aligned with your original SalesLog model)
    saleslog_id = UnicodeAttribute()               # same as sk without prefix
    transaction_date = UTCDateTimeAttribute()
    sales_type = UnicodeAttribute()                 # e.g., 'pos', 'online'
    customer_id = UnicodeAttribute(null=True)
    cashier_id = UnicodeAttribute(null=True)
    items = ListAttribute(of=MapAttribute, default=list)
    subtotal = NumberAttribute(default=0)
    tax_amount = NumberAttribute(default=0)
    discount_amount = NumberAttribute(default=0)
    total_amount = NumberAttribute(default=0)
    payment_method = UnicodeAttribute()
    status = UnicodeAttribute(default="completed")  # e.g., 'completed', 'voided'
    is_voided = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)

    # Additional metadata
    notes = UnicodeAttribute(null=True)
    sync_state = UnicodeAttribute(default="pending")

    @classmethod
    def create_saleslog(cls, **kwargs) -> 'SalesLog':
        """Factory method to create a new sales log with auto‑generated SK."""
        sk = generate_sk('SLOG-', 'saleslog_seq')
        kwargs.setdefault('pk', 'saleslogs')
        kwargs.setdefault('sk', sk)
        kwargs.setdefault('saleslog_id', sk.replace('SLOG-', ''))
        kwargs.setdefault('created_at', datetime.utcnow())
        kwargs.setdefault('updated_at', datetime.utcnow())
        instance = cls(**kwargs)
        instance.save()
        logger.info(f"SalesLog created: {sk}")
        return instance

    @classmethod
    def get_by_id(cls, saleslog_id: str) -> Optional['SalesLog']:
        """Retrieve a sales log by its ID (e.g., '00001' or 'SLOG-00001')."""
        if not saleslog_id.startswith('SLOG-'):
            saleslog_id = f"SLOG-{saleslog_id.zfill(5)}"
        try:
            return cls.get("saleslogs", saleslog_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_date_range(cls, start_date: datetime, end_date: datetime) -> list:
        """Query sales logs within a date range using the GSI."""
        condition = (cls.transaction_date >= start_date) & (cls.transaction_date <= end_date)
        return list(cls.date_index.query("saleslogs", range_key_condition=condition))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, matching the original interface."""
        return {
            "saleslog_id": self.saleslog_id,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "sales_type": self.sales_type,
            "customer_id": self.customer_id,
            "cashier_id": self.cashier_id,
            "items": self.items,
            "subtotal": float(self.subtotal),
            "tax_amount": float(self.tax_amount),
            "discount_amount": float(self.discount_amount),
            "total_amount": float(self.total_amount),
            "payment_method": self.payment_method,
            "status": self.status,
            "is_voided": self.is_voided,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "notes": self.notes,
            "sync_state": self.sync_state,
        }

    def save(self, condition=None, **kwargs):
        self.updated_at = datetime.utcnow()
        super().save(condition=condition, **kwargs)
import decimal
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from pynamodb.attributes import (
    MapAttribute, NumberAttribute, UnicodeAttribute,
)
from pynamodb.models import Model

from app.custom_attributes import FixedUTCDateTimeAttribute
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION

logger = logging.getLogger(__name__)


class Shift(Model):
    """
    PK = "shifts"  SK = "SHIFT-#####"
    Represents a single cashier shift at the POS terminal.
    One open shift per cashier at a time; never deleted, only closed.
    """

    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION

    # Primary keys
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="shifts")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")

    # Identity
    cashier_id = UnicodeAttribute()

    # Status: "open" | "closed"
    status = UnicodeAttribute(default="open")

    # Cash fields
    opening_cash = NumberAttribute(default=0.0)          # Counted at open
    closing_cash = NumberAttribute(null=True)             # Counted at close
    expected_cash = NumberAttribute(null=True)            # opening_cash + cash_sales (set at close)
    cash_variance = NumberAttribute(null=True)            # closing_cash - expected_cash (set at close)

    # Running totals (updated in real-time as sales are recorded)
    total_sales = NumberAttribute(default=0.0)
    total_transactions = NumberAttribute(default=0)
    cash_sales = NumberAttribute(default=0.0)
    payment_breakdown = MapAttribute(default=dict)        # e.g. {"cash": 800, "gcash": 400}

    # Timestamps
    start_time = FixedUTCDateTimeAttribute()
    end_time = FixedUTCDateTimeAttribute(null=True)
    last_transaction_time = FixedUTCDateTimeAttribute(null=True)

    # -------------------------------------------------------------------------
    # Class methods
    # -------------------------------------------------------------------------

    @classmethod
    def get_by_id(cls, shift_id: str) -> 'Shift | None':
        if not shift_id.startswith('SHIFT-'):
            shift_id = f"SHIFT-{shift_id.zfill(5)}"
        try:
            return cls.get("shifts", shift_id)
        except cls.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error fetching shift {shift_id}: {e}")
            return None

    @classmethod
    def get_active_shift_by_cashier(cls, cashier_id: str) -> 'Shift | None':
        try:
            for shift in cls.query(
                "shifts",
                filter_condition=(cls.cashier_id == cashier_id) & (cls.status == "open")
            ):
                return shift
            return None
        except Exception as e:
            logger.error(f"Error finding active shift for cashier {cashier_id}: {e}")
            return None

    @classmethod
    def get_all_shifts(cls) -> list:
        try:
            return list(cls.query("shifts"))
        except Exception as e:
            logger.error(f"Error getting all shifts: {e}")
            return []

    @classmethod
    def query_shifts_by_cashier(cls, cashier_id: str) -> list:
        try:
            shifts = [s for s in cls.query("shifts", filter_condition=cls.cashier_id == cashier_id)]
            shifts.sort(key=lambda s: s.start_time, reverse=True)
            return shifts
        except Exception as e:
            logger.error(f"Error querying shifts for cashier {cashier_id}: {e}")
            return []

    # -------------------------------------------------------------------------
    # Instance methods
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        try:
            pb = {}
            if self.payment_breakdown:
                for k, v in self.payment_breakdown.attribute_values.items():
                    pb[k] = float(v) if isinstance(v, (int, float, decimal.Decimal)) else v

            return {
                "shift_id": self.sk,
                "cashier_id": self.cashier_id,
                "status": self.status,
                "opening_cash": float(self.opening_cash or 0),
                "closing_cash": float(self.closing_cash) if self.closing_cash is not None else None,
                "expected_cash": float(self.expected_cash) if self.expected_cash is not None else None,
                "cash_variance": float(self.cash_variance) if self.cash_variance is not None else None,
                "total_sales": float(self.total_sales or 0),
                "total_transactions": int(self.total_transactions or 0),
                "cash_sales": float(self.cash_sales or 0),
                "payment_breakdown": pb,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "last_transaction_time": self.last_transaction_time.isoformat() if self.last_transaction_time else None,
            }
        except Exception as e:
            logger.error(f"Error converting shift {self.sk} to dict: {e}")
            return {}

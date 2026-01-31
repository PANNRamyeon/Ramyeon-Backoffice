from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal


class PaymentBreakdownItem(MapAttribute):
    """MapAttribute for payment_breakdown items"""
    cash = NumberAttribute(default=0.0)
    # Note: You can extend this with other payment methods as needed
    # credit_card = NumberAttribute(default=0.0)
    # debit_card = NumberAttribute(default=0.0)
    # digital_wallet = NumberAttribute(default=0.0)
    # voucher = NumberAttribute(default=0.0)


class Shift(Model):
    """
    Shift model for DynamoDB
    PK = shifts (partition key)
    SK = SHIFT-#### (sort key)
    """
    class Meta:
        table_name = "your-table-name"  # Replace with your table name
        region = "your-region"  # Replace with your AWS region
        # Add billing_mode, read_capacity_units, write_capacity_units if needed

    # Primary Key Attributes
    PK = UnicodeAttribute(hash_key=True, default="shifts")
    SK = UnicodeAttribute(range_key=True)

    # Shift Identification
    cashier_id = UnicodeAttribute()
    
    # Timing Information
    start_time = UTCDateTimeAttribute()
    end_time = UTCDateTimeAttribute(null=True)
    closed_at = UTCDateTimeAttribute(null=True)
    last_transaction_time = UTCDateTimeAttribute(null=True)
    statistics_calculated_at = UTCDateTimeAttribute(null=True)
    
    # Status and Sequence
    status = UnicodeAttribute(default="open")  # e.g., 'open', 'closed', 'paused'
    next_seq = NumberAttribute(default=1)  # Next transaction sequence number
    
    # Sales Information
    total_sales = NumberAttribute(default=0.0)
    total_transactions = NumberAttribute(default=0)
    cash_sales = NumberAttribute(default=0.0)
    
    # Payment Breakdown
    payment_breakdown = ListAttribute(of=PaymentBreakdownItem, default=list)
    
    # Cash Management
    expected_cash = NumberAttribute(null=True)
    closing_cash = NumberAttribute(null=True)
    cash_variance = NumberAttribute(null=True)

    @classmethod
    def create_shift(cls, shift_id: str, **kwargs):
        """Helper method to create a new shift with proper SK format"""
        sk = f"SHIFT-{shift_id}"
        return cls(SK=sk, **kwargs)

    @classmethod
    def get_shift(cls, shift_id: str):
        """Helper method to retrieve a shift by ID"""
        sk = f"SHIFT-{shift_id}"
        return cls.get("shifts", sk)

    @classmethod
    def get_active_shift_by_cashier(cls, cashier_id: str):
        """Get active shift for a cashier"""
        for shift in cls.query(
            "shifts",
            cls.SK.startswith("SHIFT-"),
            filter_condition=(cls.cashier_id == cashier_id) & (cls.status == "open")
        ):
            return shift
        return None

    @classmethod
    def query_shifts_by_cashier(cls, cashier_id: str, days: int = 7):
        """Query shifts for a specific cashier within the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return [
            shift for shift in cls.query(
                "shifts",
                cls.SK.startswith("SHIFT-"),
                filter_condition=cls.cashier_id == cashier_id
            )
            if shift.start_time >= cutoff_date
        ]

    @classmethod
    def query_open_shifts(cls):
        """Query all open shifts"""
        return cls.query(
            "shifts",
            cls.SK.startswith("SHIFT-"),
            filter_condition=cls.status == "open"
        )

    @classmethod
    def query_shifts_by_date_range(cls, start_date: datetime, end_date: datetime):
        """Query shifts within a date range"""
        # Note: This scans the table; consider using a GSI with start_time as sort key
        return [
            shift for shift in cls.query("shifts", cls.SK.startswith("SHIFT-"))
            if start_date <= shift.start_time <= end_date
        ]

    def add_transaction(self, amount: float, payment_method: str = "cash", 
                       transaction_time: Optional[datetime] = None):
        """
        Add a transaction to the shift
        
        Args:
            amount: Transaction amount
            payment_method: Payment method used (e.g., 'cash', 'card')
            transaction_time: Time of transaction (defaults to now)
        """
        if self.status != "open":
            raise ValueError("Cannot add transaction to a closed shift")
        
        # Update totals
        self.total_sales += amount
        self.total_transactions += 1
        self.last_transaction_time = transaction_time or datetime.utcnow()
        
        # Update payment method breakdown
        if payment_method.lower() == "cash":
            self.cash_sales += amount
            
        # Initialize payment breakdown if empty
        if not self.payment_breakdown:
            self.payment_breakdown = [PaymentBreakdownItem()]
        
        # Update payment breakdown (assuming first item is for cash)
        # You might want to extend this to handle multiple payment methods
        self.payment_breakdown[0].cash = self.cash_sales
        
        # Increment sequence number for next transaction
        self.next_seq += 1
        
        self.save()
        return self

    def close_shift(self, closing_cash: float, expected_cash: Optional[float] = None):
        """
        Close the shift
        
        Args:
            closing_cash: Actual cash counted at closing
            expected_cash: Expected cash (if not provided, calculated from cash_sales)
        """
        if self.status == "closed":
            raise ValueError("Shift is already closed")
        
        self.closing_cash = closing_cash
        self.expected_cash = expected_cash or self.cash_sales
        
        # Calculate cash variance
        self.cash_variance = self.closing_cash - self.expected_cash
        
        # Update status and timestamps
        self.status = "closed"
        self.closed_at = datetime.utcnow()
        self.end_time = self.closed_at
        
        self.save()
        return self

    def pause_shift(self):
        """Pause the shift (for breaks, etc.)"""
        if self.status == "closed":
            raise ValueError("Cannot pause a closed shift")
        
        self.status = "paused"
        self.save()
        return self

    def resume_shift(self):
        """Resume a paused shift"""
        if self.status != "paused":
            raise ValueError("Cannot resume a shift that is not paused")
        
        self.status = "open"
        self.save()
        return self

    def calculate_statistics(self):
        """Calculate and update shift statistics"""
        self.statistics_calculated_at = datetime.utcnow()
        
        # Here you could add more complex statistics calculations
        # For example: average transaction value, hourly sales rate, etc.
        
        self.save()
        return self

    def get_next_transaction_number(self) -> int:
        """Get the next transaction sequence number"""
        return self.next_seq

    def get_shift_duration(self) -> Optional[timedelta]:
        """Get shift duration in timedelta"""
        if not self.end_time:
            return datetime.utcnow() - self.start_time
        return self.end_time - self.start_time

    def get_shift_duration_hours(self) -> Optional[float]:
        """Get shift duration in hours"""
        duration = self.get_shift_duration()
        if duration:
            return duration.total_seconds() / 3600
        return None

    def get_average_transaction_value(self) -> float:
        """Get average transaction value"""
        if self.total_transactions == 0:
            return 0.0
        return self.total_sales / self.total_transactions

    def get_hourly_sales_rate(self) -> float:
        """Get hourly sales rate"""
        duration_hours = self.get_shift_duration_hours()
        if not duration_hours or duration_hours == 0:
            return 0.0
        return self.total_sales / duration_hours

    def is_variance_acceptable(self, threshold: float = 10.0) -> bool:
        """Check if cash variance is within acceptable threshold"""
        if self.cash_variance is None:
            return True  # No variance calculated yet
        return abs(self.cash_variance) <= threshold

    def get_shift_summary(self) -> Dict[str, Any]:
        """Get summary of the shift"""
        duration = self.get_shift_duration()
        duration_hours = self.get_shift_duration_hours()
        
        return {
            "shift_id": self.SK.replace("SHIFT-", ""),
            "cashier_id": self.cashier_id,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_hours": round(duration_hours, 2) if duration_hours else None,
            "total_sales": self.total_sales,
            "total_transactions": self.total_transactions,
            "cash_sales": self.cash_sales,
            "average_transaction": round(self.get_average_transaction_value(), 2),
            "hourly_sales_rate": round(self.get_hourly_sales_rate(), 2) if duration_hours else None,
            "next_seq": self.next_seq,
            "cash_variance": self.cash_variance,
            "closing_cash": self.closing_cash,
            "expected_cash": self.expected_cash,
            "last_transaction_time": self.last_transaction_time.isoformat() if self.last_transaction_time else None
        }

    def get_detailed_report(self) -> Dict[str, Any]:
        """Get detailed shift report"""
        summary = self.get_shift_summary()
        
        # Add payment breakdown details
        payment_breakdown = []
        if self.payment_breakdown:
            for i, breakdown in enumerate(self.payment_breakdown):
                payment_breakdown.append({
                    "cash": breakdown.cash,
                    # Add other payment methods here if extended
                })
        
        summary.update({
            "payment_breakdown": payment_breakdown,
            "statistics_calculated_at": self.statistics_calculated_at.isoformat() if self.statistics_calculated_at else None,
            "is_variance_acceptable": self.is_variance_acceptable(),
            "variance_percentage": self._get_variance_percentage()
        })
        
        return summary

    def _get_variance_percentage(self) -> Optional[float]:
        """Get cash variance as percentage of expected cash"""
        if self.cash_variance is None or self.expected_cash is None or self.expected_cash == 0:
            return None
        return (self.cash_variance / self.expected_cash) * 100

    @classmethod
    def start_shift(cls, shift_id: str, cashier_id: str, expected_cash: Optional[float] = None):
        """
        Start a new shift
        
        Args:
            shift_id: Unique shift identifier
            cashier_id: ID of the cashier
            expected_cash: Expected starting cash (floatings)
        """
        shift = cls.create_shift(
            shift_id=shift_id,
            cashier_id=cashier_id,
            start_time=datetime.utcnow(),
            status="open",
            expected_cash=expected_cash,
            next_seq=1,
            payment_breakdown=[PaymentBreakdownItem(cash=0.0)]
        )
        
        return shift

    def add_cash_float(self, amount: float):
        """
        Add cash float to the shift
        This should be called at the beginning of the shift
        """
        self.expected_cash = (self.expected_cash or 0) + amount
        self.save()
        return self

    def add_cash_drop(self, amount: float):
        """
        Add cash drop (removing excess cash during shift)
        This reduces the expected_cash
        """
        if self.expected_cash is None:
            self.expected_cash = 0
        
        self.expected_cash -= amount
        self.save()
        return self

    def get_remaining_cash(self) -> Optional[float]:
        """
        Get remaining cash in drawer
        This is expected_cash + cash_sales
        """
        if self.expected_cash is None:
            return None
        
        return self.expected_cash + self.cash_sales
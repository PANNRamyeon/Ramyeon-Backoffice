from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, 
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST

logger = logging.getLogger(__name__)


class PaymentBreakdownItem(MapAttribute):
    """MapAttribute for payment_breakdown items"""
    cash = NumberAttribute(default=0.0)


class Shift(Model):
    """
    Shift Model - Following ERD Specification
    PK = shifts, SK = SHIFT-#### (4-digit format)
    Single Table Design using RamyeonCornerDB
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        #if DYNAMODB_LOCAL:
        #    host = DYNAMODB_LOCAL_HOST
        
        # Capacity settings for shift operations
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="shifts")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "SHIFT-0001" (4-digit)
    
    # ============= CORE ERD FIELDS =============
    cashier_id = UnicodeAttribute()
    start_time = UTCDateTimeAttribute()
    status = UnicodeAttribute(default="open")
    next_seq = NumberAttribute(default=1)
    total_sales = NumberAttribute(default=0.0)
    total_transactions = NumberAttribute(default=0)
    cash_sales = NumberAttribute(default=0.0)
    payment_breakdown = ListAttribute(of=PaymentBreakdownItem, default=list)
    last_transaction_time = UTCDateTimeAttribute(null=True)
    cash_variance = NumberAttribute(null=True)
    closed_at = UTCDateTimeAttribute(null=True)
    closing_cash = NumberAttribute(null=True)
    end_time = UTCDateTimeAttribute(null=True)
    expected_cash = NumberAttribute(null=True)
    statistics_calculated_at = UTCDateTimeAttribute(null=True)
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_shift(cls, cashier_id: str, expected_cash: float = 0.0) -> 'Shift':
        """
        Create a new shift with auto-generated 4-digit SK
        
        Args:
            cashier_id: ID of the cashier (required)
            expected_cash: Opening cash amount (optional)
            
        Returns:
            Shift: Created and saved shift instance
            
        Raises:
            ValueError: If cashier_id is not provided
        """
        try:
            if not cashier_id or not cashier_id.strip():
                raise ValueError("cashier_id is required")
            
            # Generate 4-digit SK using utils.py
            sk = generate_sk('SHIFT-', 'shift_seq')
            
            # Create initial payment breakdown
            payment_breakdown = [PaymentBreakdownItem(cash=0.0)]
            
            # Create and save shift
            shift = cls(
                pk="shifts",
                sk=sk,
                cashier_id=cashier_id.strip(),
                start_time=datetime.utcnow(),
                status="open",
                next_seq=1,
                total_sales=0.0,
                total_transactions=0,
                cash_sales=0.0,
                payment_breakdown=payment_breakdown,
                expected_cash=float(expected_cash) if expected_cash else None,
                last_transaction_time=None,
                cash_variance=None,
                closed_at=None,
                closing_cash=None,
                end_time=None,
                statistics_calculated_at=None
            )
            shift.save()
            
            logger.info(f"Shift created: {sk} - Cashier: {cashier_id}")
            return shift
            
        except Exception as e:
            logger.error(f"Failed to create shift: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, shift_id: str) -> 'Shift | None':
        """
        Get shift by ID
        
        Args:
            shift_id: Format "SHIFT-0001" or just "0001"
            
        Returns:
            Shift or None if not found
        """
        try:
            # Ensure proper format
            if not shift_id.startswith('SHIFT-'):
                shift_id = f"SHIFT-{shift_id.zfill(4)}"  # Pad to 4 digits if needed
            
            return cls.get("shifts", shift_id)
        except cls.DoesNotExist:
            logger.warning(f"Shift not found: {shift_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching shift {shift_id}: {str(e)}")
            return None
    
    @classmethod
    def get_active_shift_by_cashier(cls, cashier_id: str) -> 'Shift | None':
        """
        Get active shift for a cashier
        
        Args:
            cashier_id: Cashier ID to find active shift
            
        Returns:
            Shift or None if no active shift found
        """
        try:
            # Query with filter condition for open status
            for shift in cls.query(
                "shifts",
                filter_condition=(cls.cashier_id == cashier_id) & (cls.status == "open")
            ):
                return shift
            return None
        except Exception as e:
            logger.error(f"Error finding active shift for cashier {cashier_id}: {str(e)}")
            return None
    
    @classmethod
    def query_shifts_by_cashier(cls, cashier_id: str, days: int = 7) -> list:
        """
        Query shifts for a specific cashier within the last N days
        
        Args:
            cashier_id: Cashier ID
            days: Number of days to look back
            
        Returns:
            list: List of shifts
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            shifts = []
            
            for shift in cls.query("shifts", filter_condition=cls.cashier_id == cashier_id):
                if shift.start_time >= cutoff_date:
                    shifts.append(shift)
            
            # Sort by start_time descending (newest first)
            shifts.sort(key=lambda x: x.start_time, reverse=True)
            return shifts
        except Exception as e:
            logger.error(f"Error querying shifts by cashier: {str(e)}")
            return []
    
    @classmethod
    def query_open_shifts(cls) -> list:
        """
        Query all open shifts
        
        Returns:
            list: List of open shifts
        """
        try:
            return list(cls.query("shifts", filter_condition=cls.status == "open"))
        except Exception as e:
            logger.error(f"Error querying open shifts: {str(e)}")
            return []
    
    @classmethod
    def query_shifts_by_date_range(cls, start_date: datetime, end_date: datetime) -> list:
        """
        Query shifts within a date range
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            list: List of shifts in date range
        """
        try:
            shifts = []
            for shift in cls.query("shifts"):
                if start_date <= shift.start_time <= end_date:
                    shifts.append(shift)
            
            # Sort by start_time
            shifts.sort(key=lambda x: x.start_time, reverse=True)
            return shifts
        except Exception as e:
            logger.error(f"Error querying shifts by date range: {str(e)}")
            return []
    
    @classmethod
    def get_all_shifts(cls) -> list:
        """
        Get all shifts
        
        Returns:
            list: List of all shifts
        """
        try:
            return list(cls.query("shifts"))
        except Exception as e:
            logger.error(f"Error getting all shifts: {str(e)}")
            return []
    
    @classmethod
    def get_shift_count(cls) -> int:
        """
        Get total number of shifts
        
        Returns:
            int: Number of shifts
        """
        try:
            count = 0
            for _ in cls.query("shifts"):
                count += 1
            return count
        except Exception as e:
            logger.error(f"Error counting shifts: {str(e)}")
            return 0
    
    @classmethod
    def get_open_shift_count(cls) -> int:
        """
        Get count of open shifts
        
        Returns:
            int: Number of open shifts
        """
        try:
            return len(cls.query_open_shifts())
        except Exception as e:
            logger.error(f"Error counting open shifts: {str(e)}")
            return 0
    
    # ============= INSTANCE METHODS =============
    
    def add_transaction(self, amount: float, payment_method: str = "cash", 
                       transaction_time: Optional[datetime] = None) -> 'Shift':
        """
        Add a transaction to the shift
        
        Args:
            amount: Transaction amount
            payment_method: Payment method used (default: 'cash')
            transaction_time: Time of transaction (defaults to now)
            
        Returns:
            Shift: Updated shift instance
            
        Raises:
            ValueError: If shift is not open
        """
        try:
            if self.status != "open":
                raise ValueError("Cannot add transaction to a closed or paused shift")
            
            # Update totals
            self.total_sales += float(amount)
            self.total_transactions += 1
            self.last_transaction_time = transaction_time or datetime.utcnow()
            
            # Update payment method breakdown
            if payment_method.lower() == "cash":
                self.cash_sales += float(amount)
                
            # Update payment breakdown
            if not self.payment_breakdown:
                self.payment_breakdown = [PaymentBreakdownItem()]
            
            # Update cash in payment breakdown
            self.payment_breakdown[0].cash = self.cash_sales
            
            # Increment sequence number for next transaction
            self.next_seq += 1
            
            self.save()
            logger.info(f"Transaction added to shift {self.sk}: ${amount} via {payment_method}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to add transaction to shift {self.sk}: {str(e)}")
            raise
    
    def close_shift(self, closing_cash: float) -> 'Shift':
        """
        Close the shift
        
        Args:
            closing_cash: Actual cash counted at closing
            
        Returns:
            Shift: Updated shift instance
            
        Raises:
            ValueError: If shift is already closed
        """
        try:
            if self.status == "closed":
                raise ValueError("Shift is already closed")
            
            self.closing_cash = float(closing_cash)
            
            # Calculate expected cash (opening cash + cash sales)
            expected = (self.expected_cash or 0) + self.cash_sales
            self.cash_variance = self.closing_cash - expected
            
            # Update status and timestamps
            self.status = "closed"
            self.closed_at = datetime.utcnow()
            self.end_time = self.closed_at
            
            self.save()
            logger.info(f"Shift closed: {self.sk} - Variance: ${self.cash_variance}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to close shift {self.sk}: {str(e)}")
            raise
    
    def pause_shift(self) -> 'Shift':
        """
        Pause the shift (for breaks, etc.)
        
        Returns:
            Shift: Updated shift instance
            
        Raises:
            ValueError: If shift is not open
        """
        try:
            if self.status != "open":
                raise ValueError("Can only pause an open shift")
            
            self.status = "paused"
            self.save()
            logger.info(f"Shift paused: {self.sk}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to pause shift {self.sk}: {str(e)}")
            raise
    
    def resume_shift(self) -> 'Shift':
        """
        Resume a paused shift
        
        Returns:
            Shift: Updated shift instance
            
        Raises:
            ValueError: If shift is not paused
        """
        try:
            if self.status != "paused":
                raise ValueError("Can only resume a paused shift")
            
            self.status = "open"
            self.save()
            logger.info(f"Shift resumed: {self.sk}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to resume shift {self.sk}: {str(e)}")
            raise
    
    def add_cash_float(self, amount: float) -> 'Shift':
        """
        Add cash float to the shift
        
        Args:
            amount: Amount to add as float
            
        Returns:
            Shift: Updated shift instance
        """
        try:
            if self.expected_cash is None:
                self.expected_cash = 0.0
            
            self.expected_cash += float(amount)
            self.save()
            logger.info(f"Cash float added to shift {self.sk}: ${amount}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to add cash float to shift {self.sk}: {str(e)}")
            raise
    
    def add_cash_drop(self, amount: float) -> 'Shift':
        """
        Add cash drop (removing excess cash during shift)
        
        Args:
            amount: Amount to drop
            
        Returns:
            Shift: Updated shift instance
            
        Raises:
            ValueError: If insufficient cash
        """
        try:
            if self.expected_cash is None:
                self.expected_cash = 0.0
            
            if amount > self.expected_cash:
                raise ValueError("Cannot drop more cash than available")
            
            self.expected_cash -= float(amount)
            self.save()
            logger.info(f"Cash drop from shift {self.sk}: ${amount}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to add cash drop to shift {self.sk}: {str(e)}")
            raise
    
    def calculate_statistics(self) -> 'Shift':
        """
        Calculate and update shift statistics
        
        Returns:
            Shift: Updated shift instance
        """
        try:
            self.statistics_calculated_at = datetime.utcnow()
            self.save()
            logger.info(f"Statistics calculated for shift {self.sk}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to calculate statistics for shift {self.sk}: {str(e)}")
            raise
    
    def get_next_transaction_number(self) -> int:
        """
        Get the next transaction sequence number
        
        Returns:
            int: Next transaction number
        """
        return self.next_seq
    
    def get_shift_duration(self) -> Optional[timedelta]:
        """
        Get shift duration in timedelta
        
        Returns:
            timedelta or None: Duration of shift
        """
        if not self.end_time:
            return datetime.utcnow() - self.start_time
        return self.end_time - self.start_time
    
    def get_shift_duration_hours(self) -> Optional[float]:
        """
        Get shift duration in hours
        
        Returns:
            float or None: Duration in hours
        """
        duration = self.get_shift_duration()
        if duration:
            return duration.total_seconds() / 3600
        return None
    
    def get_average_transaction_value(self) -> float:
        """
        Get average transaction value
        
        Returns:
            float: Average transaction value
        """
        if self.total_transactions == 0:
            return 0.0
        return self.total_sales / self.total_transactions
    
    def get_hourly_sales_rate(self) -> float:
        """
        Get hourly sales rate
        
        Returns:
            float: Sales per hour
        """
        duration_hours = self.get_shift_duration_hours()
        if not duration_hours or duration_hours == 0:
            return 0.0
        return self.total_sales / duration_hours
    
    def get_remaining_cash(self) -> Optional[float]:
        """
        Get remaining cash in drawer (opening cash + cash sales)
        
        Returns:
            float or None: Expected remaining cash
        """
        if self.expected_cash is None:
            return None
        return self.expected_cash + self.cash_sales
    
    def is_variance_acceptable(self, threshold: float = 10.0) -> bool:
        """
        Check if cash variance is within acceptable threshold
        
        Args:
            threshold: Acceptable variance amount
            
        Returns:
            bool: True if variance is acceptable
        """
        if self.cash_variance is None:
            return True
        return abs(self.cash_variance) <= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert shift to dictionary for API response
        
        Returns:
            dict: Dictionary representation
        """
        try:
            duration = self.get_shift_duration()
            duration_hours = self.get_shift_duration_hours()
            
            return {
                "shift_id": self.sk,
                "cashier_id": self.cashier_id,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "status": self.status,
                "duration_hours": round(duration_hours, 2) if duration_hours else None,
                "total_sales": self.total_sales,
                "total_transactions": self.total_transactions,
                "cash_sales": self.cash_sales,
                "average_transaction": round(self.get_average_transaction_value(), 2),
                "hourly_sales_rate": round(self.get_hourly_sales_rate(), 2) if duration_hours else None,
                "next_transaction_seq": self.next_seq,
                "opening_cash": self.expected_cash,
                "closing_cash": self.closing_cash,
                "cash_variance": self.cash_variance,
                "remaining_cash": self.get_remaining_cash(),
                "payment_breakdown": [{"cash": item.cash} for item in self.payment_breakdown],
                "last_transaction_time": self.last_transaction_time.isoformat() if self.last_transaction_time else None,
                "closed_at": self.closed_at.isoformat() if self.closed_at else None,
                "statistics_calculated_at": self.statistics_calculated_at.isoformat() if self.statistics_calculated_at else None
            }
        except Exception as e:
            logger.error(f"Error converting shift to dict: {str(e)}")
            return {}
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """
        Minimal dictionary representation (for basic listings)
        
        Returns:
            dict: Basic shift info
        """
        try:
            return {
                "shift_id": self.sk,
                "cashier_id": self.cashier_id,
                "status": self.status,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "duration_hours": round(self.get_shift_duration_hours(), 2) if self.get_shift_duration_hours() else None,
                "total_sales": self.total_sales,
                "total_transactions": self.total_transactions
            }
        except Exception as e:
            logger.error(f"Error converting shift to simple dict: {str(e)}")
            return {}


# ============= SHIFT VALIDATION =============
def validate_shift_id(shift_id: str) -> bool:
    """
    Validate if a shift ID is in correct format
    
    Args:
        shift_id: Shift ID to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    try:
        if not shift_id:
            return False
        
        # Check format: SHIFT-#### where #### are exactly 4 digits
        if not shift_id.startswith('SHIFT-'):
            return False
        
        number_part = shift_id[6:]  # Remove "SHIFT-"
        if len(number_part) != 4:
            return False
        
        # Check if it's a valid number (0001-9999)
        number = int(number_part)
        return 1 <= number <= 9999
        
    except (ValueError, IndexError):
        return False


def format_shift_id(number: int) -> str:
    """
    Format a number as a shift ID
    
    Args:
        number: Number to format (1-9999)
        
    Returns:
        str: Formatted shift ID (SHIFT-####)
        
    Raises:
        ValueError: If number is not between 1 and 9999
    """
    if not 1 <= number <= 9999:
        raise ValueError("Shift number must be between 1 and 9999")
    
    return f"SHIFT-{number:04d}"


def validate_shift_data(cashier_id: str, expected_cash: float = None) -> tuple[bool, str]:
    """
    Validate shift data before creation
    
    Args:
        cashier_id: Cashier ID to validate
        expected_cash: Opening cash amount to validate (optional)
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not cashier_id or not cashier_id.strip():
        return False, "Cashier ID is required"
    
    if len(cashier_id.strip()) > 50:
        return False, "Cashier ID must be 50 characters or less"
    
    if expected_cash is not None and expected_cash < 0:
        return False, "Opening cash cannot be negative"
    
    return True, ""


# ============= SHIFT MANAGER =============
class ShiftManager:
    """
    Manager class for shift-related operations
    """
    
    @staticmethod
    def get_shift_summary() -> Dict[str, Any]:
        """
        Get summary statistics for all shifts
        
        Returns:
            dict: Shift summary
        """
        try:
            shifts = Shift.get_all_shifts()
            total = len(shifts)
            open_shifts = sum(1 for s in shifts if s.status == "open")
            closed_shifts = sum(1 for s in shifts if s.status == "closed")
            paused_shifts = sum(1 for s in shifts if s.status == "paused")
            
            # Calculate totals
            total_sales = sum(s.total_sales for s in shifts)
            total_transactions = sum(s.total_transactions for s in shifts)
            
            # Group by status and cashier
            by_cashier = {}
            for shift in shifts:
                cashier = shift.cashier_id
                if cashier not in by_cashier:
                    by_cashier[cashier] = {
                        "total_shifts": 0,
                        "open_shifts": 0,
                        "total_sales": 0.0,
                        "total_transactions": 0
                    }
                
                by_cashier[cashier]["total_shifts"] += 1
                by_cashier[cashier]["total_sales"] += shift.total_sales
                by_cashier[cashier]["total_transactions"] += shift.total_transactions
                if shift.status == "open":
                    by_cashier[cashier]["open_shifts"] += 1
            
            return {
                "total_shifts": total,
                "open_shifts": open_shifts,
                "closed_shifts": closed_shifts,
                "paused_shifts": paused_shifts,
                "total_sales": total_sales,
                "total_transactions": total_transactions,
                "average_sales_per_shift": total_sales / total if total > 0 else 0,
                "average_transactions_per_shift": total_transactions / total if total > 0 else 0,
                "shifts_by_cashier": by_cashier
            }
            
        except Exception as e:
            logger.error(f"Error getting shift summary: {str(e)}")
            return {}
    
    @staticmethod
    def get_cashier_performance(cashier_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get performance statistics for a cashier
        
        Args:
            cashier_id: Cashier ID
            days: Number of days to analyze
            
        Returns:
            dict: Cashier performance summary
        """
        try:
            shifts = Shift.query_shifts_by_cashier(cashier_id, days)
            
            if not shifts:
                return {
                    "cashier_id": cashier_id,
                    "total_shifts": 0,
                    "message": "No shifts found for this cashier in the specified period"
                }
            
            # Calculate statistics
            closed_shifts = [s for s in shifts if s.status == "closed"]
            open_shifts = [s for s in shifts if s.status == "open"]
            
            total_sales = sum(s.total_sales for s in shifts)
            total_transactions = sum(s.total_transactions for s in shifts)
            avg_variance = sum(abs(s.cash_variance or 0) for s in closed_shifts) / len(closed_shifts) if closed_shifts else 0
            
            return {
                "cashier_id": cashier_id,
                "period_days": days,
                "total_shifts": len(shifts),
                "open_shifts": len(open_shifts),
                "closed_shifts": len(closed_shifts),
                "total_sales": total_sales,
                "total_transactions": total_transactions,
                "average_sales_per_shift": total_sales / len(shifts) if shifts else 0,
                "average_transactions_per_shift": total_transactions / len(shifts) if shifts else 0,
                "average_cash_variance": avg_variance,
                "shifts": [s.to_simple_dict() for s in shifts[:10]]  # Last 10 shifts
            }
            
        except Exception as e:
            logger.error(f"Error getting cashier performance: {str(e)}")
            return {}
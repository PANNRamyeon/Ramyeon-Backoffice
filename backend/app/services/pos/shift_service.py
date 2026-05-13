import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.Shifts import Shift
from app.utils.counters import counter_service

logger = logging.getLogger(__name__)


def _send_shift_close_notification(shift: Shift) -> None:
    """Fire a back-office notification summarising a just-closed shift."""
    try:
        from notifications.services import notification_service

        shift_id = shift.sk
        cashier_id = shift.cashier_id
        total_sales = float(shift.total_sales or 0)
        total_transactions = int(shift.total_transactions or 0)
        opening_cash = float(shift.opening_cash or 0)
        closing_cash = float(shift.closing_cash or 0)
        expected_cash = float(shift.expected_cash or 0)
        cash_variance = float(shift.cash_variance or 0)

        # Duration
        duration_str = "N/A"
        duration_minutes = 0
        if shift.start_time and shift.end_time:
            delta = shift.end_time - shift.start_time
            total_secs = int(delta.total_seconds())
            duration_minutes = total_secs // 60
            duration_str = f"{total_secs // 3600}h {(total_secs % 3600) // 60}m"

        # Variance label and priority
        abs_var = abs(cash_variance)
        if cash_variance < 0:
            variance_label = f"SHORT ₱{abs_var:,.2f}"
            priority = "high"
        elif cash_variance > 0:
            variance_label = f"OVER ₱{abs_var:,.2f}"
            priority = "high" if abs_var >= 100 else "medium"
        else:
            variance_label = "BALANCED"
            priority = "low"

        # Payment breakdown summary
        pb_summary = ""
        if shift.payment_breakdown:
            parts = []
            for method, amount in shift.payment_breakdown.attribute_values.items():
                parts.append(f"{method.capitalize()}: ₱{float(amount):,.2f}")
            pb_summary = " | ".join(parts)

        message_lines = [
            f"Cashier {cashier_id} has closed shift {shift_id}.",
            f"Duration: {duration_str}  |  Transactions: {total_transactions}  |  Total Sales: ₱{total_sales:,.2f}",
            f"Opening Cash: ₱{opening_cash:,.2f}  |  Closing Cash: ₱{closing_cash:,.2f}  |  Expected: ₱{expected_cash:,.2f}",
            f"Cash Variance: {variance_label}",
        ]
        if pb_summary:
            message_lines.append(f"Payment Breakdown: {pb_summary}")

        # Build metadata dict (plain Python types only — no Decimal)
        pb_dict = {}
        if shift.payment_breakdown:
            for k, v in shift.payment_breakdown.attribute_values.items():
                pb_dict[k] = float(v)

        notification_service.create_notification(
            title=f"Shift Closed — {shift_id}",
            message="\n".join(message_lines),
            notification_type="pos",
            priority=priority,
            action_type="shift_report",
            metadata={
                "shift_id": shift_id,
                "cashier_id": cashier_id,
                "total_sales": total_sales,
                "total_transactions": total_transactions,
                "opening_cash": opening_cash,
                "closing_cash": closing_cash,
                "expected_cash": expected_cash,
                "cash_variance": cash_variance,
                "duration_minutes": duration_minutes,
                "payment_breakdown": pb_dict,
                "start_time": shift.start_time.isoformat() if shift.start_time else None,
                "end_time": shift.end_time.isoformat() if shift.end_time else None,
            },
        )
        logger.info(f"Shift close notification sent for {shift_id}")
    except Exception as e:
        logger.warning(f"Shift close notification failed (non-fatal): {e}")


class ShiftService:
    """
    Business logic for cashier shifts.
    One open shift per cashier at a time.
    Shifts are never deleted — status moves from "open" to "closed" only.
    """

    # -------------------------------------------------------------------------
    # Read operations
    # -------------------------------------------------------------------------

    def get_active_shift(self, cashier_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the currently open shift for a cashier, or None if there is none.
        """
        shift = Shift.get_active_shift_by_cashier(cashier_id)
        return shift.to_dict() if shift else None

    def get_shift_by_id(self, shift_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single shift by its ID.
        """
        shift = Shift.get_by_id(shift_id)
        return shift.to_dict() if shift else None

    def get_all_shifts(
        self,
        cashier_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List shifts, with optional filters for cashier and status.
        Returns up to `limit` results, sorted newest first.
        """
        if cashier_id:
            shifts = Shift.query_shifts_by_cashier(cashier_id)
        else:
            shifts = Shift.get_all_shifts()
            shifts.sort(key=lambda s: s.start_time, reverse=True)

        if status:
            shifts = [s for s in shifts if s.status == status]

        results = [s.to_dict() for s in shifts[:limit]]
        return [r for r in results if r]

    # -------------------------------------------------------------------------
    # Write operations
    # -------------------------------------------------------------------------

    def start_shift(self, cashier_id: str, opening_cash: float) -> Dict[str, Any]:
        """
        Open a new shift for a cashier.

        Args:
            cashier_id: ID of the cashier opening the shift.
            opening_cash: Cash counted in the drawer at open.

        Returns:
            dict: The created shift.

        Raises:
            ValueError: If cashier already has an open shift.
        """
        existing = Shift.get_active_shift_by_cashier(cashier_id)
        if existing:
            raise ValueError(f"Cashier {cashier_id} already has an open shift: {existing.sk}")

        shift_id = counter_service.get_next_id('shifts', prefix='SHIFT', width=5)

        shift = Shift(
            pk="shifts",
            sk=shift_id,
            cashier_id=cashier_id,
            status="open",
            opening_cash=float(opening_cash),
            total_sales=0.0,
            total_transactions=0,
            cash_sales=0.0,
            payment_breakdown={},
            start_time=datetime.utcnow(),
        )
        shift.save()

        logger.info(f"Shift started: {shift_id} — cashier: {cashier_id}")
        return shift.to_dict()

    def end_shift(self, shift_id: str, closing_cash: float) -> Dict[str, Any]:
        """
        Close a shift and finalise its statistics.

        Computes expected_cash = opening_cash + cash_sales
        and cash_variance = closing_cash - expected_cash.

        Note: When the Sales module is wired, pass recalculate=True to have
        this method recompute totals from source Sale records before closing.

        Args:
            shift_id: ID of the shift to close.
            closing_cash: Cash counted in the drawer at close.

        Returns:
            dict: The closed shift.

        Raises:
            ValueError: If shift not found or already closed.
        """
        shift = Shift.get_by_id(shift_id)
        if not shift:
            raise ValueError(f"Shift not found: {shift_id}")
        if shift.status == "closed":
            raise ValueError(f"Shift {shift_id} is already closed")

        now = datetime.utcnow()
        opening_cash = float(shift.opening_cash or 0)
        cash_sales = float(shift.cash_sales or 0)
        expected_cash = opening_cash + cash_sales

        shift.closing_cash = float(closing_cash)
        shift.expected_cash = expected_cash
        shift.cash_variance = float(closing_cash) - expected_cash
        shift.status = "closed"
        shift.end_time = now
        shift.save()

        logger.info(
            f"Shift closed: {shift_id} — variance: {shift.cash_variance:.2f}"
        )

        _send_shift_close_notification(shift)

        return shift.to_dict()

    def update_shift_totals(
        self,
        shift_id: str,
        amount: float,
        payment_method: str,
        transaction_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Increment shift totals when a sale is recorded.
        Called by the Sales service — do not call directly from views.

        Args:
            shift_id: ID of the open shift.
            amount: Sale amount to add.
            payment_method: Payment method used (e.g. "cash", "gcash").
            transaction_time: Time of the sale (defaults to now).

        Returns:
            dict: Updated shift.

        Raises:
            ValueError: If shift not found or not open.
        """
        shift = Shift.get_by_id(shift_id)
        if not shift:
            raise ValueError(f"Shift not found: {shift_id}")
        if shift.status != "open":
            raise ValueError(f"Shift {shift_id} is not open")

        amount = float(amount)
        method = payment_method.lower()

        shift.total_sales = float(shift.total_sales or 0) + amount
        shift.total_transactions = int(shift.total_transactions or 0) + 1
        shift.last_transaction_time = transaction_time or datetime.utcnow()

        if method == "cash":
            shift.cash_sales = float(shift.cash_sales or 0) + amount

        # Update the payment breakdown map
        current_pb = {}
        if shift.payment_breakdown:
            for k, v in shift.payment_breakdown.attribute_values.items():
                current_pb[k] = float(v)
        current_pb[method] = current_pb.get(method, 0.0) + amount
        shift.payment_breakdown = current_pb

        shift.save()
        logger.info(f"Shift {shift_id} totals updated: +{amount} via {method}")
        return shift.to_dict()

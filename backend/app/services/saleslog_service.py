# app/services/saleslog_service.py
from datetime import datetime
import logging
from typing import Optional, List, Dict, Any, Tuple

from ...models.SalesLog import SalesLog

logger = logging.getLogger(__name__)


class SalesLogService:
    """
    Sales Log Service – uses PynamoDB SalesLog model.
    Provides CRUD operations and export queries.
    """

    def __init__(self):
        pass   # No direct table reference needed

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------

    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new sales log / invoice.
        invoice_data must contain at least 'transaction_date' and 'sales_type'.
        """
        try:
            # PynamoDB handles attribute conversion; we just pass the dict.
            saleslog = SalesLog.create_saleslog(**invoice_data)
            return saleslog.to_dict()
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            raise Exception(f"Error creating invoice: {str(e)}")

    def get_invoice_by_id(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single invoice by its ID (e.g., '00001' or 'SLOG-00001')."""
        try:
            saleslog = SalesLog.get_by_id(invoice_id)
            return saleslog.to_dict() if saleslog else None
        except Exception as e:
            logger.error(f"Error retrieving invoice {invoice_id}: {e}")
            raise Exception(f"Error retrieving invoice: {str(e)}")

    def get_all_invoices(self, limit: int = 100, start_key: Optional[Dict] = None) -> Tuple[List[Dict], Optional[Dict]]:
        """
        Paginated scan of all invoices.
        Returns (items, last_evaluated_key).
        """
        try:
            # PynamoDB's scan returns an iterator; we manually implement pagination.
            # This is simplified – for production, use a more efficient pattern.
            items = []
            last_key = None
            for idx, saleslog in enumerate(SalesLog.scan()):
                if idx >= limit:
                    # We cannot easily get the last evaluated key from PynamoDB's iterator.
                    # For real pagination, you'd need to use the underlying client.
                    # As a workaround, we return None for last_key.
                    break
                items.append(saleslog.to_dict())
            return items, None   # last_key omitted for simplicity
        except Exception as e:
            logger.error(f"Error retrieving all invoices: {e}")
            raise Exception(f"Error retrieving invoices: {str(e)}")

    def update_invoice(self, invoice_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an invoice. Only the provided fields are updated.
        """
        try:
            saleslog = SalesLog.get_by_id(invoice_id)
            if not saleslog:
                raise Exception(f"Invoice {invoice_id} not found")

            # Update attributes
            for key, value in update_data.items():
                if hasattr(saleslog, key) and key not in ('pk', 'sk', 'saleslog_id', 'created_at'):
                    setattr(saleslog, key, value)

            saleslog.save()   # optimistic locking can be added if needed
            return saleslog.to_dict()
        except Exception as e:
            logger.error(f"Error updating invoice {invoice_id}: {e}")
            raise Exception(f"Error updating invoice: {str(e)}")

    def delete_invoice(self, invoice_id: str) -> bool:
        """Delete an invoice by ID."""
        try:
            saleslog = SalesLog.get_by_id(invoice_id)
            if saleslog:
                saleslog.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting invoice {invoice_id}: {e}")
            raise Exception(f"Error deleting invoice: {str(e)}")

    # -------------------------------------------------------------------------
    # Export & Reporting
    # -------------------------------------------------------------------------

    def get_transactions_for_export(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Get transactions matching the given filters.
        Supports: 'start_date', 'end_date', 'sales_type', 'status', 'is_voided'.
        Uses the GSI for efficient date range filtering.
        """
        try:
            filters = filters or {}
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')

            # Parse dates if provided as strings
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                # Include the entire end day
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Query by date range if both dates are given
            if start_date and end_date:
                saleslogs = SalesLog.get_by_date_range(start_date, end_date)
            elif start_date:
                # Partial date range – fallback to scan with filter (less efficient)
                condition = SalesLog.transaction_date >= start_date
                saleslogs = list(SalesLog.scan(filter_condition=condition))
            elif end_date:
                condition = SalesLog.transaction_date <= end_date
                saleslogs = list(SalesLog.scan(filter_condition=condition))
            else:
                # No date filter – scan all
                saleslogs = list(SalesLog.scan())

            # Apply additional filters in memory (or add more GSIs if needed)
            filtered = []
            for sl in saleslogs:
                # Filter by sales_type
                sales_type = filters.get('sales_type')
                if sales_type and sl.sales_type != sales_type:
                    continue

                # Filter by status
                status = filters.get('status')
                if status and sl.status != status:
                    continue

                # Filter by voided flag
                is_voided = filters.get('is_voided')
                if is_voided is not None and sl.is_voided != is_voided:
                    continue

                filtered.append(sl.to_dict())

            return filtered

        except Exception as e:
            logger.error(f"Error retrieving transactions for export: {e}")
            raise Exception(f"Error retrieving transactions for export: {str(e)}")
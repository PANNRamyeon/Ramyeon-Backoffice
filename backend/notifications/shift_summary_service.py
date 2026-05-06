# pos/services/shift_summary_service.py
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from models.Users import User                     # PynamoDB User model
from models.Sessions import SessionLog             # PynamoDB SessionLog model
from app.services.sales.SalesService import SalesService   # refactored SalesService
from notifications.email_service import email_service 

logger = logging.getLogger(__name__)


class ShiftSummaryService:
    """Service for generating and sending shift summary emails."""

    def __init__(self):
        self.sales_service = SalesService()

    # ------------------------------------------------------------------
    # Admin email retrieval
    # ------------------------------------------------------------------
    def get_admin_emails(self) -> List[str]:
        """
        Get all verified admin email addresses.
        Uses User model's classmethod to fetch active admins.
        """
        try:
            # Assuming User model has a method to get active admins
            admins = User.get_active_admins()  # Returns list of User instances
            emails = []
            for admin in admins:
                if admin.email and admin.email_verified:
                    emails.append(admin.email)
            logger.info(f"Found {len(emails)} verified admin email(s)")
            return emails
        except Exception as e:
            logger.error(f"Error getting admin emails: {e}")
            return []

    # ------------------------------------------------------------------
    # Shift sales data
    # ------------------------------------------------------------------
    def get_shift_sales_data(self, user_id: Optional[str], shift_start: datetime, shift_end: datetime) -> Dict[str, Any]:
        """
        Get sales data for a shift period, optionally filtered by cashier.
        """
        try:
            # Use SalesService to get sales in date range
            sales = self.sales_service.get_sales_by_date_range(shift_start, shift_end)

            # Filter by cashier if needed
            if user_id:
                sales = [sale for sale in sales if sale.get('cashier_id') == user_id]

            # Calculate aggregates
            total_sales = sum(float(sale.get('final_amount', sale.get('total_amount', 0))) for sale in sales)
            total_transactions = len(sales)
            total_discounts = sum(float(sale.get('total_discount', 0)) for sale in sales)

            return {
                'total_sales': total_sales,
                'total_transactions': total_transactions,
                'total_discounts': total_discounts,
                'transactions': sales
            }
        except Exception as e:
            logger.error(f"Error getting shift sales data: {e}")
            return {
                'total_sales': 0,
                'total_transactions': 0,
                'total_discounts': 0,
                'transactions': []
            }

    # ------------------------------------------------------------------
    # Duration formatting
    # ------------------------------------------------------------------
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format duration in seconds to human‑readable string."""
        try:
            if seconds < 60:
                return f"{seconds} seconds"
            elif seconds < 3600:
                minutes = seconds // 60
                secs = seconds % 60
                return f"{minutes} minutes {secs} seconds" if secs > 0 else f"{minutes} minutes"
            else:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                if minutes > 0:
                    return f"{hours} hours {minutes} minutes"
                return f"{hours} hours"
        except Exception:
            return "N/A"

    # ------------------------------------------------------------------
    # Generate shift summary
    # ------------------------------------------------------------------
    def generate_shift_summary(self, session_data: Dict[str, Any], sales_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate shift summary data for email from session and sales data.
        """
        try:
            shift_start = session_data.get('login_time')
            shift_end = session_data.get('logout_time', datetime.utcnow())
            duration = session_data.get('session_duration', 0)

            # Convert string timestamps to datetime if needed
            if isinstance(shift_start, str):
                shift_start = datetime.fromisoformat(shift_start.replace('Z', '+00:00'))
            if isinstance(shift_end, str):
                shift_end = datetime.fromisoformat(shift_end.replace('Z', '+00:00'))

            shift_start_str = shift_start.strftime('%Y-%m-%d %H:%M:%S') if shift_start else 'N/A'
            shift_end_str = shift_end.strftime('%Y-%m-%d %H:%M:%S') if shift_end else 'N/A'

            return {
                'cashier_name': session_data.get('username', 'Unknown'),
                'cashier_id': session_data.get('user_id', ''),
                'shift_start': shift_start_str,
                'shift_end': shift_end_str,
                'session_duration': self.format_duration(duration),
                'total_sales': sales_data.get('total_sales', 0),
                'total_transactions': sales_data.get('total_transactions', 0),
                'total_discounts': sales_data.get('total_discounts', 0),
                'branch_id': session_data.get('branch_id', 'N/A')
            }
        except Exception as e:
            logger.error(f"Error generating shift summary: {e}")
            return {
                'cashier_name': session_data.get('username', 'Unknown'),
                'shift_start': 'N/A',
                'shift_end': 'N/A',
                'session_duration': 'N/A',
                'total_sales': 0,
                'total_transactions': 0,
                'total_discounts': 0,
                'branch_id': 'N/A'
            }

    # ------------------------------------------------------------------
    # Send shift summary email
    # ------------------------------------------------------------------
    def send_shift_summary_email(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send shift summary email to all admins.
        """
        try:
            # Get admin emails
            admin_emails = self.get_admin_emails()
            if not admin_emails:
                logger.warning("No admin emails found. Skipping shift summary email.")
                return {'success': False, 'error': 'No admin emails found'}

            # Extract shift details
            shift_start = session_data.get('login_time')
            shift_end = session_data.get('logout_time', datetime.utcnow())
            user_id = session_data.get('user_id')

            # Ensure datetime objects
            if isinstance(shift_start, str):
                shift_start = datetime.fromisoformat(shift_start.replace('Z', '+00:00'))
            if isinstance(shift_end, str):
                shift_end = datetime.fromisoformat(shift_end.replace('Z', '+00:00'))

            # Get sales data
            sales_data = self.get_shift_sales_data(user_id, shift_start, shift_end)

            # Generate summary
            shift_summary = self.generate_shift_summary(session_data, sales_data)

            # Send to each admin
            results = []
            for admin_email in admin_emails:
                try:
                    # Fetch admin name for personalisation
                    admin = User.get_by_email(admin_email)  # Assuming a method exists
                    admin_name = admin.full_name or admin.username if admin else 'Admin'

                    result = email_service.send_shift_summary_email(
                        to_email=admin_email,
                        shift_data=shift_summary,
                        admin_name=admin_name
                    )
                    results.append({
                        'email': admin_email,
                        'success': result.get('success', False)
                    })

                    if result.get('success'):
                        logger.info(f"Shift summary email sent to {admin_email}")
                    else:
                        logger.error(f"Failed to send to {admin_email}: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Error sending to {admin_email}: {e}")
                    results.append({'email': admin_email, 'success': False, 'error': str(e)})

            success_count = sum(1 for r in results if r.get('success'))
            return {
                'success': success_count > 0,
                'sent_count': success_count,
                'total_count': len(admin_emails),
                'results': results
            }

        except Exception as e:
            logger.error(f"Error sending shift summary email: {e}")
            return {'success': False, 'error': str(e)}


# Singleton instance
shift_summary_service = ShiftSummaryService()
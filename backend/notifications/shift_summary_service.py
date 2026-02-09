"""
Shift Summary Service
Collects shift data and sends summary emails to admins
"""
import logging
from datetime import datetime, timedelta
from app.database import db_manager
from notifications.email_service import email_service
from app.services.pos.SalesService import SalesService

logger = logging.getLogger(__name__)

class ShiftSummaryService:
    """Service for generating and sending shift summary emails"""
    
    def __init__(self):
        self.db = db_manager.get_database()
        self.user_collection = self.db.users
        self.sales_service = SalesService()
    
    def get_admin_emails(self):
        """
        Get all admin email addresses
        
        Returns:
            list: List of admin email addresses
        """
        try:
            admins = list(self.user_collection.find({
                "role": "admin",
                "status": "active",
                "isDeleted": {"$ne": True},
                "email_verified": True
            }))
            
            # Ensure we only return unique, non-empty emails
            admin_emails = []
            for admin in admins:
                email = admin.get("email")
                if email and email not in admin_emails:
                    admin_emails.append(email)
            
            logger.info(f"Found {len(admin_emails)} verified admin email(s)")
            return admin_emails
        
        except Exception as e:
            logger.error(f"Error getting admin emails: {e}")
            return []
    
    def get_shift_sales_data(self, user_id, shift_start, shift_end):
        """
        Get sales data for a shift period
        
        Args:
            user_id (str): User ID of the cashier
            shift_start (datetime): Shift start time
            shift_end (datetime): Shift end time
        
        Returns:
            dict: Sales summary data
        """
        try:
            # Get sales from both collections for the shift period
            sales = self.sales_service.get_sales_by_date_range(shift_start, shift_end)
            
            # Filter by cashier if user_id is provided
            if user_id:
                sales = [sale for sale in sales if sale.get('cashier_id') == user_id]
            
            # Calculate totals
            total_sales = sum(float(sale.get('final_amount', sale.get('total_amount', 0))) for sale in sales)
            total_transactions = len(sales)
            
            # Calculate discounts if available
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
    
    def format_duration(self, seconds):
        """
        Format duration in seconds to human-readable string
        
        Args:
            seconds (int): Duration in seconds
        
        Returns:
            str: Formatted duration string
        """
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
    
    def generate_shift_summary(self, session_data, sales_data):
        """
        Generate shift summary data for email
        
        Args:
            session_data (dict): Session data from session_logs
            sales_data (dict): Sales data from get_shift_sales_data
        
        Returns:
            dict: Formatted shift summary data
        """
        try:
            shift_start = session_data.get('login_time')
            shift_end = session_data.get('logout_time', datetime.utcnow())
            duration = session_data.get('session_duration', 0)
            
            # Format dates
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
    
    def send_shift_summary_email(self, session_data):
        """
        Send shift summary email to all admins
        
        Args:
            session_data (dict): Session data from session_logs
        
        Returns:
            dict: Result with success status
        """
        try:
            # Get admin emails
            admin_emails = self.get_admin_emails()
            
            if not admin_emails:
                logger.warning("No admin emails found. Skipping shift summary email.")
                return {
                    'success': False,
                    'error': 'No admin emails found'
                }
            
            # Get sales data for the shift
            shift_start = session_data.get('login_time')
            shift_end = session_data.get('logout_time', datetime.utcnow())
            user_id = session_data.get('user_id')
            
            # Convert to datetime if needed
            if isinstance(shift_start, str):
                shift_start = datetime.fromisoformat(shift_start.replace('Z', '+00:00'))
            if isinstance(shift_end, str):
                shift_end = datetime.fromisoformat(shift_end.replace('Z', '+00:00'))
            
            sales_data = self.get_shift_sales_data(user_id, shift_start, shift_end)
            
            # Generate shift summary
            shift_summary = self.generate_shift_summary(session_data, sales_data)
            
            # Send email to all admins
            results = []
            for admin_email in admin_emails:
                try:
                    # Get admin name if available
                    admin = self.user_collection.find_one({"email": admin_email})
                    admin_name = admin.get('full_name') or admin.get('username', 'Admin') if admin else 'Admin'
                    
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
                        logger.info(f"Shift summary email sent successfully to {admin_email}")
                    else:
                        logger.error(f"Failed to send shift summary email to {admin_email}: {result.get('error')}")
                
                except Exception as e:
                    logger.error(f"Error sending shift summary email to {admin_email}: {e}")
                    results.append({
                        'email': admin_email,
                        'success': False,
                        'error': str(e)
                    })
            
            # Check if at least one email was sent successfully
            success_count = sum(1 for r in results if r.get('success'))
            
            return {
                'success': success_count > 0,
                'sent_count': success_count,
                'total_count': len(admin_emails),
                'results': results
            }
        
        except Exception as e:
            logger.error(f"Error sending shift summary email: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Singleton instance
shift_summary_service = ShiftSummaryService()







from datetime import datetime
import bcrypt
import logging
from typing import Optional  # <-- Add this

from ..core.audit_service import AuditLogService
from notifications.services import notification_service
import csv
import io
from app.utils import DYNAMO_TABLE_NAME
from app.utils.qr_utils import generate_customer_qr_token, verify_customer_qr_token  # <-- Add this
from models.Customers import Customer, CustomerManager
from models.Sessions import SessionLog
from pynamodb.exceptions import PynamoDBException
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger(__name__)

class CustomerService:
    def __init__(self):
        self.audit_service = AuditLogService()

    # ==================== Password Helpers ====================
    def hash_password(self, password: str) -> str:
        if not password:
            raise ValueError("Password cannot be empty")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False

    # ==================== Notification Helper ====================
    def _send_customer_notification(self, action_type: str, customer_id: str,
                                    customer_name: str = None,
                                    additional_metadata: dict = None):
        """Send notification for customer actions"""
        templates = {
            'created': {
                'title': 'Customer Created',
                'message': f"Customer {customer_name or customer_id} has been created",
                'priority': 'low'
            },
            'updated': {
                'title': 'Customer Updated',
                'message': f"Customer {customer_name or customer_id} has been updated",
                'priority': 'low'
            },
            'soft_deleted': {
                'title': 'Customer Deleted',
                'message': f"Customer {customer_name or customer_id} has been deleted",
                'priority': 'medium'
            },
            'restored': {
                'title': 'Customer Restored',
                'message': f"Customer {customer_name or customer_id} has been restored",
                'priority': 'low'
            },
            'hard_deleted': {
                'title': 'Customer Permanently Deleted',
                'message': f"Customer {customer_name or customer_id} has been permanently deleted",
                'priority': 'high'
            }
        }
        template = templates.get(action_type)
        if not template:
            logger.warning(f"Unknown notification action type: {action_type}")
            return

        metadata = {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "action": f"customer_{action_type}"
        }
        if additional_metadata:
            metadata.update(additional_metadata)

        try:
            notification_service.create_notification(
                title=template['title'],
                message=template['message'],
                priority=template['priority'],
                notification_type="system",
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Failed to send customer notification: {e}")

    # ==================== CRUD Operations ====================
    def get_customers(self, page=1, limit=50, status=None,
                      min_loyalty_points=None, max_loyalty_points=None,
                      include_deleted=False, sort_by=None, search=None):
        try:
            scan_conditions = []
            if not include_deleted:
                scan_conditions.append(Customer.isDeleted == False)

            if status:
                scan_conditions.append(Customer.status == status)

            if min_loyalty_points is not None:
                scan_conditions.append(Customer.loyalty_points >= min_loyalty_points)

            if max_loyalty_points is not None:
                scan_conditions.append(Customer.loyalty_points <= max_loyalty_points)

            if search:
                search_condition = (
                    Customer.full_name.contains(search) |
                    Customer.email.contains(search) |
                    Customer.username.contains(search) |
                    Customer.phone_number.contains(search)
                )
                scan_conditions.append(search_condition)

            final_condition = None
            if scan_conditions:
                final_condition = scan_conditions[0]
                for condition in scan_conditions[1:]:
                    final_condition &= condition

            # TODO: Optimize by using status_index when status is provided.
            results = Customer.scan(final_condition)

            customers = [customer.to_dict() for customer in results]
            total = len(customers)

            start = (page - 1) * limit
            end = start + limit
            paginated_customers = customers[start:end]

            return {
                'customers': paginated_customers,
                'total': total,
                'page': page,
                'limit': limit,
                'has_more': end < total,
            }

        except PynamoDBException as e:
            raise Exception(f"Error getting customers: {str(e)}")

    def create_customer(self, customer_data, current_user=None):
        try:
            customer = Customer.create_with_password(**customer_data)
            result = customer.to_dict()

            if current_user and self.audit_service:
                self.audit_service.log_customer_create(current_user, result)

            self._send_customer_notification('created', customer.sk, customer.full_name)

            return result
        except PynamoDBException as e:
            raise Exception(f"Error creating customer: {str(e)}")

    def register_customer(self, customer_data: dict) -> dict:
        try:
            email = (customer_data.get('email') or '').strip().lower()
            password = customer_data.get('password') or ''
            if not email or not password:
                raise ValueError("Email and password are required")

            first_name = (customer_data.get('first_name') or '').strip()
            last_name = (customer_data.get('last_name') or '').strip()
            full_name = customer_data.get('full_name')
            if not full_name:
                full_name = f"{first_name} {last_name}".strip() or email.split('@')[0]

            base_username = (customer_data.get('username') or email.split('@')[0] or 'customer').strip()
            username_candidate = base_username
            suffix = 1
            while self.get_customer_by_username(username_candidate, include_deleted=True):
                username_candidate = f"{base_username}{suffix}"
                suffix += 1

            payload = {
                'email': email,
                'password_hash': self.hash_password(password),
                'full_name': full_name,
                'phone_number': customer_data.get('phone', ''),
                'username': username_candidate,
                'source': customer_data.get('source', 'web'),
            }

            # Pass current_user if present in customer_data (adjust as needed)
            current_user = customer_data.get('current_user')
            return self.create_customer(payload, current_user=current_user)
        except ValueError:
            raise
        except Exception as exc:
            raise Exception(f"Error registering customer: {exc}")

    def get_customer_by_id(self, customer_id, include_deleted=False):
        try:
            customer = Customer.get_by_id(customer_id)
            if customer:
                if include_deleted or not customer.isDeleted:
                    return customer.to_dict()
            return None
        except PynamoDBException as e:
            raise Exception(f"Error getting customer: {str(e)}")

    def update_customer(self, customer_id, customer_data, current_user=None):
        try:
            customer = Customer.get_by_id(customer_id)
            if not customer:
                return None

            old_data = customer.to_dict()
            actions = []

            for field, value in customer_data.items():
                if field == 'password':
                    actions.append(Customer.password.set(self.hash_password(value)))
                elif field == 'email':
                    existing = Customer.get_by_email(value)
                    if existing and existing.sk != customer_id:
                        raise ValueError(f"Email {value} already in use")
                    actions.append(Customer.email.set(value.lower().strip()))
                    actions.append(Customer.email_verified.set(False))
                elif hasattr(Customer, field):
                    actions.append(getattr(Customer, field).set(value))

            if actions:
                customer.update(actions=actions)

            updated = customer.to_dict()

            if current_user and self.audit_service:
                self.audit_service.log_customer_update(current_user, customer_id, old_data, updated)

            self._send_customer_notification('updated', customer_id, customer.full_name)

            return updated
        except PynamoDBException as e:
            raise Exception(f"Error updating customer: {str(e)}")

    def soft_delete_customer(self, customer_id, current_user=None):
        try:
            customer = Customer.get_by_id(customer_id)
            if not customer or customer.isDeleted:
                return False

            # Capture state before deletion
            old_data = customer.to_dict()

            # Perform soft delete (sets isDeleted=True, status='deleted')
            customer.soft_delete()

            # Capture state after deletion
            new_data = customer.to_dict()

            # Log as an update (since isDeleted and status changed)
            if current_user and self.audit_service:
                self.audit_service.log_customer_update(current_user, customer_id, old_data, new_data)

            # Notification
            self._send_customer_notification('soft_deleted', customer_id, customer.full_name)

            return True
        except PynamoDBException as e:
            raise Exception(f"Error soft deleting customer: {str(e)}")

    def restore_customer(self, customer_id, current_user=None):
        try:
            customer = Customer.get_by_id(customer_id)
            if not customer or not customer.isDeleted:
                return False

            old_data = customer.to_dict()
            customer.restore()
            new_data = customer.to_dict()

            if current_user and self.audit_service:
                self.audit_service.log_customer_update(current_user, customer_id, old_data, new_data)

            self._send_customer_notification('restored', customer_id, customer.full_name)

            return True
        except PynamoDBException as e:
            raise Exception(f"Error restoring customer: {str(e)}")

    def get_deleted_customers(self, page=1, limit=50):
        results = Customer.get_by_status('deleted', include_deleted=True)
        customers = [c.to_dict() for c in results]
        # Implement pagination if needed (the GSI returns all, so you can slice)
        start = (page - 1) * limit
        end = start + limit
        paginated = customers[start:end]
        return {
            'customers': paginated,
            'total': len(customers),
            'page': page,
            'limit': limit,
            'has_more': end < len(customers),
        }

    def hard_delete_customer(self, customer_id, current_user=None, confirmation_token=None):
        try:
            customer = Customer.get_by_id(customer_id)
            if not customer:
                return False

            # Capture data before deletion for audit
            customer_data = customer.to_dict()

            # Permanent deletion
            customer.delete()

            if current_user and self.audit_service:
                self.audit_service.log_customer_delete(current_user, customer_data)

            # Notification (high priority)
            self._send_customer_notification('hard_deleted', customer_id, customer_data.get('full_name'))

            logger.warning(f"Customer {customer_id} permanently deleted by {current_user}")
            return True
        except PynamoDBException as e:
            raise Exception(f"Error permanently deleting customer: {str(e)}")

    def get_customer_by_username(self, username, include_deleted=False):
        try:
            condition = Customer.username == username
            if not include_deleted:
                condition &= Customer.isDeleted == False

            # Add limit=1 to stop scanning after first match
            results = list(Customer.scan(condition, limit=1))
            if results:
                return results[0].to_dict()
            return None
        except PynamoDBException as e:
            raise Exception(f"Error getting customer by username: {str(e)}")

    def authenticate_customer(self, email, password):
        try:
            customer = Customer.get_by_email(email)
            if customer and self.verify_password(password, customer.password):
                return customer.to_dict()
            return None
        except PynamoDBException as e:
            raise Exception(f"Error authenticating customer: {str(e)}")

    def change_customer_password(self, customer_id, old_password, new_password):
        try:
            customer = Customer.get_by_id(customer_id)
            if customer and self.verify_password(old_password, customer.password):
                customer.set_password(self.hash_password(new_password))
                return True
            return False
        except PynamoDBException as e:
            raise Exception(f"Error changing password: {str(e)}")

    def get_customer_statistics(self):
        try:
            return CustomerManager.get_customer_statistics()
        except Exception as e:
            logger.error(f"Error in CustomerService.get_customer_statistics: {e}")
            raise Exception(f"Error getting customer statistics: {str(e)}")

    def update_loyalty_points(self, customer_id, points_to_add, reason="Purchase", current_user=None):
        try:
            customer = Customer.get_by_id(customer_id)
            if customer:
                customer.update(actions=[
                    Customer.loyalty_points.set(Customer.loyalty_points + points_to_add)
                ])
                if current_user and self.audit_service:
                    self.audit_service.log_action(
                        current_user, 'loyalty_points_add',
                        resource_id=customer_id, resource_type='customer',
                        changes={'points': points_to_add, 'reason': reason}
                    )
                return customer.to_dict()
            return None
        except PynamoDBException as e:
            raise Exception(f"Error updating loyalty points: {str(e)}")

    def redeem_loyalty_points(self, customer_id, points_to_redeem, reason="Redemption", current_user=None):
        try:
            customer = Customer.get_by_id(customer_id)
            if customer and customer.loyalty_points >= points_to_redeem:
                customer.update(actions=[
                    Customer.loyalty_points.set(Customer.loyalty_points - points_to_redeem)
                ])
                if current_user and self.audit_service:
                    self.audit_service.log_action(
                        current_user, 'loyalty_points_redeem',
                        resource_id=customer_id, resource_type='customer',
                        changes={'points': points_to_redeem, 'reason': reason}
                    )
                return customer.to_dict()
            raise ValueError("Insufficient loyalty points")
        except PynamoDBException as e:
            raise Exception(f"Error redeeming loyalty points: {str(e)}")

    def search_customers(self, search_term, include_deleted=False):
        return self.get_customers(search=search_term, include_deleted=include_deleted, limit=100)['customers']

    def get_customer_by_email(self, email, include_deleted=False):
        try:
            customer = Customer.get_by_email(email)
            if customer:
                if include_deleted or not customer.isDeleted:
                    return customer.to_dict()
            return None
        except PynamoDBException as e:
            raise Exception(f"Error getting customer by email: {str(e)}")

    # Stubbed methods (unchanged)
    def get_customer_by_qr_code(self, qr_code, include_deleted=False):
        raise NotImplementedError("get_customer_by_qr_code is not implemented for DynamoDB")

    def add_order_to_history(self, customer_id, order_data):
        raise NotImplementedError("add_order_to_history is not implemented for DynamoDB")

    def get_customer_order_history(self, customer_id, limit=50):
        raise NotImplementedError("get_customer_order_history is not implemented for DynamoDB")

    def export_customers_to_csv(self, include_deleted=False):
        raise NotImplementedError("export_customers_to_csv is not implemented for DynamoDB")

    def import_customers_from_csv(self, file_path, current_user=None):
        raise NotImplementedError("import_customers_from_csv is not implemented for DynamoDB")
    

      # ==================== QR Code Methods ====================
        # ==================== QR Code Methods ====================
    def generate_qr_token_for_customer(self, customer_id: str, expiry_hours: int = 24) -> Optional[str]:
        """
        Generate a dynamic QR token for a customer.

        Args:
            customer_id: Customer SK
            expiry_hours: Token validity in hours

        Returns:
            str: JWT token, or None if customer doesn't exist
        """
        try:
            # Verify customer exists and is active
            customer = Customer.get_by_id(customer_id)
            if not customer or customer.isDeleted:
                logger.warning(f"QR token requested for non-existent/deleted customer: {customer_id}")
                return None

            token = generate_customer_qr_token(customer.sk, expiry_hours)
            logger.info(f"Generated QR token for customer {customer_id}")
            return token
        except Exception as e:
            logger.error(f"Error generating QR token for customer {customer_id}: {e}")
            raise Exception(f"Failed to generate QR token: {str(e)}")

    def verify_qr_token(self, token: str) -> Optional[dict]:
        """
        Verify a QR token and return customer summary if valid.

        Args:
            token: JWT string

        Returns:
            dict: Customer summary (from to_dict) or None if invalid/expired
        """
        try:
            customer_id = verify_customer_qr_token(token)
            if not customer_id:
                return None

            customer = Customer.get_by_id(customer_id)
            if not customer or customer.isDeleted:
                logger.warning(f"QR token verified but customer not found/deleted: {customer_id}")
                return None

            return customer.to_dict()
        except Exception as e:
            logger.error(f"Error verifying QR token: {e}")
            raise Exception(f"QR verification failed: {str(e)}")

    def verify_qr_token(self, token: str) -> Optional[dict]:
        """
        Verify a QR token and return customer summary if valid.

        Args:
            token: JWT string

        Returns:
            dict: Customer summary (from to_dict) or None if invalid/expired
        """
        try:
            from app.utils.qr_utils import verify_customer_qr_token
            customer_id = verify_customer_qr_token(token)
            if not customer_id:
                return None

            customer = Customer.get_by_id(customer_id)
            if not customer or customer.isDeleted:
                logger.warning(f"QR token verified but customer not found/deleted: {customer_id}")
                return None

            return customer.to_dict()
        except Exception as e:
            logger.error(f"Error verifying QR token: {e}")
            raise Exception(f"QR verification failed: {str(e)}")
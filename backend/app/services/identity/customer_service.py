from datetime import datetime
import bcrypt
import logging
from typing import Optional

from ..core.audit_service import AuditLogService
from notifications.services import notification_service
import csv
import io
from app.utils import DYNAMO_TABLE_NAME
from app.utils.qr_utils import generate_customer_qr_token, verify_customer_qr_token
from models.Customers import Customer, CustomerManager
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

    # ==================== Unified creation (plain password) ====================
    def create_customer_with_password(self, data: dict, current_user=None) -> dict:
        """
        Create a customer from plain password. Hash it internally.
        data must contain: email (required), password (required plaintext)
        Optional: full_name, phone_number, username, source, current_user
        """
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        if not email or not password:
            raise ValueError("Email and password are required")

        # Hash the password
        password_hash = self.hash_password(password)

        # Build arguments for model
        model_kwargs = {
            'email': email,
            'password_hash': password_hash,
            'full_name': data.get('full_name'),
            'phone_number': data.get('phone_number') or data.get('phone'),
            'username': data.get('username'),
            'source': data.get('source', 'web'),
            'delivery_address': data.get('delivery_address') or None,
        }
        customer = Customer.create_with_password(**model_kwargs)
        result = customer.to_dict()

        if current_user and self.audit_service:
            self.audit_service.log_customer_create(current_user, result)

        self._send_customer_notification('created', customer.sk, customer.full_name)
        return result

    # ==================== Registration (uses unified creation) ====================
    def register_customer(self, customer_data: dict) -> dict:
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
            'password': password,                     # plaintext, will be hashed by create_customer_with_password
            'full_name': full_name,
            'phone_number': customer_data.get('phone', ''),
            'username': username_candidate,
            'source': customer_data.get('source', 'web'),
            'current_user': customer_data.get('current_user')   # if any
        }
        return self.create_customer_with_password(payload)

    # ==================== CRUD ====================
    def get_customers(self, limit=50, status=None,
                  min_loyalty_points=None, max_loyalty_points=None,
                  include_deleted=False, search=None,
                  exclusive_start_key=None):
        """
        Paginated scan with last_evaluated_key support.
        Returns: {
            'customers': [...],
            'last_evaluated_key': str or None,
            'has_more': bool,
            'limit': int
        }
        """
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

            # Query only the customers partition — avoids a full table scan
            query_kwargs = {'page_size': limit}
            if final_condition is not None:
                query_kwargs['filter_condition'] = final_condition
            if exclusive_start_key:
                query_kwargs['last_evaluated_key'] = exclusive_start_key

            customers = []
            last_evaluated_key = None
            page_iterator = Customer.query("customers", **query_kwargs)
            for customer in page_iterator:
                customers.append(customer)
                if len(customers) >= limit:
                    break
            try:
                last_evaluated_key = page_iterator.last_evaluated_key
            except AttributeError:
                pass

            # If we have less than limit, no more pages
            has_more = len(customers) == limit and last_evaluated_key is not None

            customer_dicts = [c.to_dict() for c in customers]
            return {
                'customers': customer_dicts,
                'last_evaluated_key': last_evaluated_key,
                'has_more': has_more,
                'limit': limit
            }
        except PynamoDBException as e:
            raise Exception(f"Error getting customers: {str(e)}")

    def get_customer_by_id(self, customer_id, include_deleted=False):
        try:
            customer = Customer.get_by_id(customer_id, include_deleted=include_deleted)
            return customer.to_dict() if customer else None
        except PynamoDBException as e:
            raise Exception(f"Error getting customer: {str(e)}")

    def update_customer(self, customer_id, customer_data, current_user=None):
        """
        customer_data may contain only whitelisted fields: email, full_name, phone_number, username, password
        """
        try:
            customer = Customer.get_by_id(customer_id)
            if not customer:
                return None

            old_data = customer.to_dict()
            actions = []

            # Normalize phone → phone_number
            if 'phone' in customer_data and 'phone_number' not in customer_data:
                customer_data['phone_number'] = customer_data.pop('phone')

            allowed_fields = {'email', 'full_name', 'phone_number', 'username', 'password', 'delivery_address'}
            for field, value in customer_data.items():
                if field not in allowed_fields:
                    continue
                if field == 'password':
                    actions.append(Customer.password.set(self.hash_password(value)))
                elif field == 'email':
                    if value:
                        existing = Customer.get_by_email(value)
                        if existing and existing.sk != customer_id:
                            raise ValueError(f"Email {value} already in use")
                        actions.append(Customer.email.set(value.lower().strip()))
                        actions.append(Customer.email_verified.set(False))
                elif field == 'delivery_address':
                    from models.Customers import DeliveryAddress
                    addr = DeliveryAddress(**{k: v for k, v in value.items() if v}) if value else None
                    actions.append(Customer.delivery_address.set(addr))
                elif hasattr(Customer, field):
                    actions.append(getattr(Customer, field).set(value))

            if actions:
                actions.append(Customer.updated_at.set(datetime.utcnow()))
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
            old_data = customer.to_dict()
            customer.soft_delete()
            new_data = customer.to_dict()
            if current_user and self.audit_service:
                self.audit_service.log_customer_update(current_user, customer_id, old_data, new_data)
            self._send_customer_notification('soft_deleted', customer_id, customer.full_name)
            return True
        except PynamoDBException as e:
            raise Exception(f"Error soft deleting customer: {str(e)}")

    def restore_customer(self, customer_id, current_user=None):
        try:
            customer = Customer.get_by_id(customer_id, include_deleted=True)
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
            customer = Customer.get_by_id(customer_id, include_deleted=True)
            if not customer:
                return False
            customer_data = customer.to_dict()
            customer.delete()
            if current_user and self.audit_service:
                self.audit_service.log_customer_delete(current_user, customer_data)
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
                    Customer.loyalty_points.set(Customer.loyalty_points + points_to_add),
                    Customer.updated_at.set(datetime.utcnow())
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
            if customer:
                # Use conditional update to prevent overspending
                try:
                    customer.update(
                        actions=[
                            Customer.loyalty_points.set(Customer.loyalty_points - points_to_redeem),
                            Customer.updated_at.set(datetime.utcnow())
                        ],
                        condition=Customer.loyalty_points >= points_to_redeem
                    )
                except Customer.DoesNotExist:
                    raise ValueError("Insufficient loyalty points or customer not found")
                if current_user and self.audit_service:
                    self.audit_service.log_action(
                        current_user, 'loyalty_points_redeem',
                        resource_id=customer_id, resource_type='customer',
                        changes={'points': points_to_redeem, 'reason': reason}
                    )
                return customer.to_dict()
            return None
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

    # Stubbed methods
    def get_customer_by_qr_code(self, qr_code, include_deleted=False):
        return self.verify_qr_token(qr_code)

    def add_order_to_history(self, customer_id, order_data):
        raise NotImplementedError("add_order_to_history is not implemented for DynamoDB")

    def get_customer_order_history(self, customer_id, limit=50):
        raise NotImplementedError("get_customer_order_history is not implemented for DynamoDB")

    def export_customers_to_csv(self, include_deleted=False):
        """
        Query all customers and serialize to CSV.
        Returns a StringIO buffer ready to read.
        """
        try:
            all_customers = []
            last_evaluated_key = None

            while True:
                query_kwargs = {'page_size': 100}
                if not include_deleted:
                    query_kwargs['filter_condition'] = Customer.isDeleted == False
                if last_evaluated_key:
                    query_kwargs['last_evaluated_key'] = last_evaluated_key

                page_iterator = Customer.query("customers", **query_kwargs)
                page_customers = list(page_iterator)
                all_customers.extend(page_customers)

                try:
                    last_evaluated_key = page_iterator.last_evaluated_key
                except AttributeError:
                    last_evaluated_key = None

                if not last_evaluated_key:
                    break

            fieldnames = [
                'customer_id', 'username', 'full_name', 'email',
                'phone_number', 'loyalty_points', 'status', 'auth_mode', 'date_created',
            ]
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for customer in all_customers:
                d = customer.to_dict()
                writer.writerow({
                    'customer_id': d.get('customer_id', ''),
                    'username': d.get('username', ''),
                    'full_name': d.get('full_name', ''),
                    'email': d.get('email', ''),
                    'phone_number': d.get('phone_number', ''),
                    'loyalty_points': d.get('loyalty_points', 0),
                    'status': d.get('status', 'active'),
                    'auth_mode': d.get('auth_mode', 'email_password'),
                    'date_created': d.get('date_created', ''),
                })

            output.seek(0)
            return output
        except Exception as e:
            logger.error(f"Error exporting customers: {e}")
            raise

    def import_customers_from_csv(self, file_path, current_user=None):
        """
        Import customers from a CSV file.
        Expected columns: username, full_name, email, phone_number, loyalty_points, status
        A temporary password is auto-generated for each imported customer.
        Returns a summary dict: created, skipped, errors, total.
        """
        import secrets
        results = {'created': 0, 'skipped': 0, 'errors': [], 'total': 0}

        try:
            with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            results['total'] = len(rows)

            for i, row in enumerate(rows, start=1):
                try:
                    email = (row.get('email') or '').strip().lower()
                    if not email:
                        results['errors'].append(f"Row {i}: email is required")
                        results['skipped'] += 1
                        continue

                    if Customer.get_by_email(email):
                        results['errors'].append(f"Row {i}: {email} already exists")
                        results['skipped'] += 1
                        continue

                    customer_data = {
                        'email': email,
                        'username': (row.get('username') or '').strip() or email.split('@')[0],
                        'full_name': (row.get('full_name') or '').strip(),
                        'phone_number': (row.get('phone_number') or row.get('phone') or '').strip(),
                        'loyalty_points': int(row.get('loyalty_points') or 0),
                        'status': (row.get('status') or 'active').strip(),
                        'password': secrets.token_urlsafe(12),
                        'auth_mode': 'email_password',
                    }

                    self.create_customer_with_password(customer_data, current_user=current_user)
                    results['created'] += 1
                except Exception as e:
                    results['errors'].append(f"Row {i}: {str(e)}")
                    results['skipped'] += 1

            return results
        except Exception as e:
            logger.error(f"Error importing customers: {e}")
            raise

    # ==================== QR Code Methods ====================
    def generate_qr_token_for_customer(self, customer_id: str, expiry_hours: int = 24) -> Optional[str]:
        try:
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
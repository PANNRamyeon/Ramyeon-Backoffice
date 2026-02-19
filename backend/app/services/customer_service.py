
from datetime import datetime, timedelta
from ..database import db_manager
import bcrypt
import logging
from .audit_service import AuditLogService
import csv
import io
import boto3
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger(__name__)

class CustomerService:
    def __init__(self):
        """Initialize CustomerService for DynamoDB"""
        self.db = db_manager.get_database()  # boto3.resource('dynamodb')

        # DynamoDB tables
        self.customer_table = self.db.Table("customers")
        self.session_logs_table = self.db.Table("session_logs")

        self.audit_service = AuditLogService()
        
    # ================================================================
    # UTILITY METHODS
    # ================================================================
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        if not password:
            raise ValueError("Password cannot be empty")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    
    # ================================================================
    # CRUD OPERATIONS
    # ================================================================
    
    def get_customers(self, page=1, limit=50, status=None, min_loyalty_points=None, max_loyalty_points=None, include_deleted=False, sort_by=None, search=None):
        """Get customers with pagination, search, and loyalty point range filtering"""
        try:
            query = {}

            # ----------------------------------------------------
            # BASIC FILTERS
            # ----------------------------------------------------
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}

            if status: 
                query['status'] = status

            # ----------------------------------------------------
            # LOYALTY POINT FILTERS (min / max)
            # ----------------------------------------------------
            if min_loyalty_points is not None:
                query['loyalty_points'] = {'$gte': min_loyalty_points}

            if max_loyalty_points is not None:
                query.setdefault('loyalty_points', {})
                query['loyalty_points']['$lte'] = max_loyalty_points

            # ----------------------------------------------------
            # SEARCH FILTER
            # ----------------------------------------------------
            if search:
                search_regex = {'$regex': search, '$options': 'i'}
                query['$or'] = [
                    {'full_name': search_regex},
                    {'email': search_regex},
                    {'username': search_regex},
                    {'phone': search_regex},
                ]

            # ----------------------------------------------------
            # SORTING
            # ----------------------------------------------------
            if sort_by == 'loyalty_desc':
                sort_options = [('loyalty_points', -1)]
            elif sort_by == 'date_asc':
                sort_options = [('date_created', 1)]
            else:
                sort_options = [('date_created', -1)]  # default

            # ----------------------------------------------------
            # PAGINATION
            # ----------------------------------------------------
            skip = (page - 1) * limit

            customers_cursor = (
                self.customer_collection
                    .find(query)
                    .sort(sort_options)
                    .skip(skip)
                    .limit(limit)
            )

            customers = list(customers_cursor)
            total = self.customer_collection.count_documents(query)

            return {
                'customers': customers,
                'total': total,
                'page': page,
                'limit': limit,
                'has_more': skip + limit < total,
                'filters_applied': {
                    'status': status,
                    'min_loyalty_points': min_loyalty_points,
                    'max_loyalty_points': max_loyalty_points,
                    'include_deleted': include_deleted,
                    'search': search
                }
            }

        except Exception as e:
            raise Exception(f"Error getting customers: {str(e)}")


    
    def generate_customer_id(self):
        """Generate sequential CUST-##### format ID"""
        try:
            pipeline = [
                {"$match": {"_id": {"$regex": "^CUST-"}}},
                {"$addFields": {
                    "id_number": {
                        "$toInt": {"$substr": ["$_id", 5, -1]}
                    }
                }},
                {"$sort": {"id_number": -1}},
                {"$limit": 1}
            ]
            
            result = list(self.customer_collection.aggregate(pipeline))
            next_number = (result[0]["id_number"] + 1) if result else 1
            
            return f"CUST-{next_number:05d}"  # 5 digits
            
        except Exception as e:
            logger.error(f"Error generating customer ID: {e}")
            import time
            return f"CUST-{int(time.time()) % 100000:05d}"

    def create_customer(self, customer_data, current_user=None):
        """Create customer with sequential CUST-##### ID"""
        try:
            required_fields = ["email", "password", "username", "full_name"]
            for field in required_fields:
                if not customer_data.get(field):
                    raise ValueError(f"{field.replace('_', ' ').title()} is required")
            
            # Check if email already exists
            existing_customer = self.customer_collection.find_one({
                "email": customer_data["email"].strip().lower(),
                "isDeleted": {"$ne": True}
            })
            if existing_customer:
                raise ValueError("Email already exists")
            
            # Check if username already exists
            existing_username = self.customer_collection.find_one({
                "username": customer_data["username"].strip(),
                "isDeleted": {"$ne": True}
            })
            if existing_username:
                raise ValueError("Username already exists")
            
            # Generate sequential ID
            customer_id = self.generate_customer_id()
            now = datetime.utcnow()
            
            # Create customer record with separate username
            customer_record = {
                "_id": customer_id,
                "username": customer_data["username"].strip(),
                "full_name": customer_data["full_name"].strip(),
                "email": customer_data["email"].strip().lower(),
                "password": self.hash_password(customer_data["password"]),
                "phone": customer_data.get("phone", ""),
                "delivery_address": customer_data.get("delivery_address", {}),
                "loyalty_points": customer_data.get("loyalty_points", 0),
                "last_purchase": customer_data.get("last_purchase"),
                "isDeleted": False,
                "date_created": now,
                "last_updated": now,
                "status": "active"
            }
            
            self.customer_table.put_item(Item=customer_record)

            
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_customer_create(current_user, customer_record)
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return customer_record
            
        except Exception as e:
            raise Exception(f"Error creating customer: {str(e)}")

    def register_customer(self, customer_data: dict) -> dict:
        """Public registration helper that wraps create_customer."""
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
                'password': password,
                'username': username_candidate,
                'full_name': full_name,
                'phone': customer_data.get('phone', ''),
                'delivery_address': customer_data.get('delivery_address', {}),
                'status': 'active',
                'auth_mode': 'password',
                'source': customer_data.get('source', 'web'),
            }

            return self.create_customer(payload)
        except ValueError:
            raise
        except Exception as exc:
            raise Exception(f"Error registering customer: {exc}")
    
    def get_customer_by_id(self, customer_id, include_deleted=False):
        """Get customer by CUST-##### ID"""
        try:
            if not customer_id:
                return None
                
            query = {'_id': customer_id}
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
                
            return self.customer_collection.find_one(query)
            
        except Exception as e:
           raise Exception(f"Error getting customer: {str(e)}")
    
    def update_customer(self, customer_id, customer_data, current_user=None):
        """Update customer including username validation"""
        try:
            if not customer_id:
                return None

            old_customer = self.customer_collection.find_one({
                '_id': customer_id,
                'isDeleted': {'$ne': True}
            })
            if not old_customer:
                return None

            update_data = {}
            allowed_fields = [
                'username', 'full_name', 'email', 'password', 'phone', 
                'delivery_address', 'loyalty_points', 'last_purchase', 'status'
            ]
            
            for field in allowed_fields:
                if field in customer_data:
                    update_data[field] = customer_data[field]
            
            update_data['last_updated'] = datetime.utcnow()

            # Handle password hashing
            if "password" in update_data:
                update_data["password"] = self.hash_password(update_data["password"])

            # Handle email validation
            if "email" in update_data:
                existing_customer = self.customer_collection.find_one({
                    "email": update_data["email"].strip().lower(),
                    "_id": {"$ne": customer_id},
                    "isDeleted": {"$ne": True}
                })
                if existing_customer:
                    raise ValueError("Email already exists")
                update_data["email"] = update_data["email"].strip().lower()

            # Handle username validation
            if "username" in update_data:
                existing_username = self.customer_collection.find_one({
                    "username": update_data["username"].strip(),
                    "_id": {"$ne": customer_id},
                    "isDeleted": {"$ne": True}
                })
                if existing_username:
                    raise ValueError("Username already exists")
                update_data["username"] = update_data["username"].strip()

            result = self.customer_collection.update_one(
                {'_id': customer_id, 'isDeleted': {'$ne': True}},
                {'$set': update_data}
            )

            if result.modified_count == 0:
                return old_customer

            updated_customer = self.customer_collection.find_one({'_id': customer_id})

            if current_user and self.audit_service:
                try:
                    self.audit_service.log_customer_update(
                        current_user, customer_id, old_customer, update_data
                    )
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")

            return updated_customer

        except Exception as e:
            raise Exception(f"Error updating customer: {str(e)}")
    
    def soft_delete_customer(self, customer_id, current_user=None):
        """Soft delete customer - change isDeleted to true"""
        try:
            if not customer_id:
                return False
            
            customer = self.customer_collection.find_one({
                '_id': customer_id,
                'isDeleted': {'$ne': True}
            })
            
            if not customer:
                print(f"❌ Customer not found or already deleted")
                return False
            
            now = datetime.utcnow()
            
            result = self.customer_collection.update_one(
                {'_id': customer_id, 'isDeleted': {'$ne': True}},
                {
                    '$set': {
                        'isDeleted': True,
                        'last_updated': now,
                        'status': 'inactive'
                    }
                }
            )
            
            success = result.modified_count > 0
            
            if success and current_user and self.audit_service:
                try:
                    self.audit_service.log_customer_delete(current_user, customer_id, 'soft_delete')
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return success
            
        except Exception as e:
            raise Exception(f"Error soft deleting customer: {str(e)}")

    def restore_customer(self, customer_id, current_user=None):
        """Restore soft deleted customer"""
        try:
            if not customer_id:
                return False
            
            customer = self.customer_collection.find_one({
                '_id': customer_id,
                'isDeleted': True
            })
            
            if not customer:
                return False
            
            now = datetime.utcnow()
            
            result = self.customer_collection.update_one(
                {'_id': customer_id, 'isDeleted': True},
                {
                    '$set': {
                        'isDeleted': False,
                        'last_updated': now,
                        'status': 'active'
                    }
                }
            )
            
            success = result.modified_count > 0
            
            if success and current_user and self.audit_service:
                try:
                    self.audit_service.log_customer_restore(current_user, customer_id)
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return success
            
        except Exception as e:
            raise Exception(f"Error restoring customer: {str(e)}")

    def get_deleted_customers(self, page=1, limit=50):
        """Get soft deleted customers"""
        try:
            skip = (page - 1) * limit
            
            # Query for deleted customers
            query = {'isDeleted': True}
            
            customers = list(
                self.customer_collection.find(query)
                .sort([('deletedAt', -1)])
                .skip(skip)
                .limit(limit)
            )
            
            total = self.customer_collection.count_documents(query)
            
            return {
                'customers': customers,
                'total': total,
                'page': page,
                'limit': limit,
                'has_more': skip + limit < total
            }
            
        except Exception as e:
            raise Exception(f"Error getting deleted customers: {str(e)}")

    def hard_delete_customer(self, customer_id, current_user=None, confirmation_token=None):
        """Permanently delete customer"""
        try:
            if not customer_id:
                return False
            
            # Verify confirmation token if provided
            if confirmation_token:
                # You can implement token verification logic here
                pass
            
            customer = self.customer_collection.find_one({'_id': customer_id})
            if not customer:
                return False
            
            # Delete the customer record
            result = self.customer_collection.delete_one({'_id': customer_id})
            success = result.deleted_count > 0
            
            # Audit logging
            if success and current_user and self.audit_service:
                try:
                    self.audit_service.log_customer_delete(current_user, customer_id, 'hard_delete')
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return success
            
        except Exception as e:
            raise Exception(f"Error permanently deleting customer: {str(e)}")
        
    def get_customer_by_username(self, username, include_deleted=False):
        """Get customer by username"""
        try:
            if not username:
                return None
                
            query = {'username': username.strip()}
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
                
            return self.customer_collection.find_one(query)
        except Exception as e:
            raise Exception(f"Error getting customer by username: {str(e)}")
    
    # ================================================================
    # AUTHENTICATION METHODS
    # ================================================================
    
    def authenticate_customer(self, email, password):
        """Authenticate customer with email and password"""
        try:
            if not email or not password:
                return None
            
            customer = self.customer_collection.find_one({
                'email': email.strip().lower(),
                'isDeleted': {'$ne': True},
                'status': 'active'
            })
            
            if not customer:
                return None
            
            if self.verify_password(password, customer['password']):
                # Update last login timestamp
                self.customer_collection.update_one(
                    {'_id': customer['_id']},
                    {'$set': {'last_updated': datetime.utcnow()}}
                )
                return customer
            
            return None
            
        except Exception as e:
            raise Exception(f"Error authenticating customer: {str(e)}")
    
    def change_customer_password(self, customer_id, old_password, new_password):
        """Change customer password"""
        try:
            customer = self.get_customer_by_id(customer_id)
            if not customer:
                return False
            
            if not self.verify_password(old_password, customer['password']):
                raise ValueError("Current password is incorrect")
            
            result = self.customer_collection.update_one(
                {'_id': customer_id},
                {
                    '$set': {
                        'password': self.hash_password(new_password),
                        'last_updated': datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise Exception(f"Error changing password: {str(e)}")
    
    # ================================================================
    # ANALYTICS AND METRICS
    # ================================================================
    
    def get_customer_statistics(self):
        """Get customer statistics"""
        try:
            total_customers = self.customer_collection.count_documents({"isDeleted": {"$ne": True}})
            active_customers = self.customer_collection.count_documents({
                "status": "active", "isDeleted": {"$ne": True}
            })
            
            # Monthly registrations
            today = datetime.now()
            start_of_month = datetime(today.year, today.month, 1)
            monthly_registrations = self.customer_collection.count_documents({
                "date_created": {"$gte": start_of_month},
                "isDeleted": {"$ne": True}
            })
            
            # Loyalty stats
            loyalty_pipeline = [
                {"$match": {"isDeleted": {"$ne": True}}},
                {"$group": {
                    "_id": None,
                    "total_loyalty_points": {"$sum": "$loyalty_points"},
                    "avg_loyalty_points": {"$avg": "$loyalty_points"}
                }}
            ]

            loyalty_stats = list(self.customer_collection.aggregate(loyalty_pipeline))
            loyalty_data = loyalty_stats[0] if loyalty_stats else {}
           
            return {
                'total_customers': total_customers,
                'active_customers': active_customers,
                'inactive_customers': total_customers - active_customers,
                'monthly_registrations': monthly_registrations,
                'total_loyalty_points': loyalty_data.get('total_loyalty_points', 0) or 0,
                'avg_loyalty_points': round(loyalty_data.get('avg_loyalty_points', 0) or 0, 2)
            }

        except Exception as e:
            raise Exception(f"Error getting customer statistics: {str(e)}")
    
    # ================================================================
    # LOYALTY SYSTEM METHODS
    # ================================================================
    
    def update_loyalty_points(self, customer_id, points_to_add, reason="Purchase", current_user=None):
        """Update customer loyalty points"""
        try:
            if not customer_id or points_to_add < 0:
                return None
            
            result = self.customer_collection.update_one(
                {'_id': customer_id, 'isDeleted': {'$ne': True}},
                {
                    '$inc': {'loyalty_points': points_to_add},
                    '$set': {'last_updated': datetime.utcnow()}
                }
            )
            
            if result.modified_count == 0:
                return None
            
            return self.customer_collection.find_one({'_id': customer_id})
            
        except Exception as e:
            raise Exception(f"Error updating loyalty points: {str(e)}")
    
    def redeem_loyalty_points(self, customer_id, points_to_redeem, reason="Redemption", current_user=None):
        """Redeem customer loyalty points"""
        try:
            if not customer_id or points_to_redeem <= 0:
                return None
            
            customer = self.get_customer_by_id(customer_id)
            if not customer or customer['loyalty_points'] < points_to_redeem:
                raise ValueError("Insufficient loyalty points")
            
            result = self.customer_collection.update_one(
                {'_id': customer_id, 'isDeleted': {'$ne': True}},
                {
                    '$inc': {'loyalty_points': -points_to_redeem},
                    '$set': {'last_updated': datetime.utcnow()},
                    '$push': {
                        'loyalty_history': {
                            'points': -points_to_redeem,
                            'reason': reason,
                            'date': datetime.utcnow(),
                            'redeemed_by': current_user.get('_id') if current_user else None
                        }
                    }
                }
            )
            
            if result.modified_count == 0:
                return None
            
            return self.customer_collection.find_one({'_id': customer_id})
            
        except Exception as e:
            raise Exception(f"Error redeeming loyalty points: {str(e)}")
    
    # ================================================================
    # SEARCH AND FILTER METHODS
    # ================================================================
    
    def search_customers(self, search_term, include_deleted=False):
        """Search customers by name, email, phone, or username"""
        try:
            if not search_term or not search_term.strip():
                return []

            import re
            escaped_term = re.escape(search_term.strip())
            regex_pattern = {'$regex': escaped_term, '$options': 'i'}

            query = {
                '$or': [
                    {'full_name': regex_pattern},
                    {'email': regex_pattern},
                    {'phone': regex_pattern},
                    {'username': regex_pattern},  # Add username to search
                    {'_id': regex_pattern}
                ]
            }
            
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}

            customers = list(self.customer_collection.find(query).limit(100))
            return customers

        except Exception as e:
            raise Exception(f"Error searching customers: {str(e)}")
        
    def get_customer_by_username(self, username, include_deleted=False):
        """Get customer by username"""
        try:
            if not username:
                return None
                
            query = {'username': username.strip()}
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
                
            return self.customer_collection.find_one(query)
        except Exception as e:
            raise Exception(f"Error getting customer by username: {str(e)}")
    
    def get_customer_by_email(self, email, include_deleted=False):
        """Get customer by email"""
        try:
            if not email:
                return None
                
            query = {'email': email.strip().lower()}
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
                
            return self.customer_collection.find_one(query)
        except Exception as e:
            raise Exception(f"Error getting customer by email: {str(e)}")
    
    def get_customer_by_qr_code(self, qr_code, include_deleted=False):
        """Get customer by QR code"""
        try:
            if not qr_code:
                return None
                
            query = {'qr_code': qr_code}
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
                
            return self.customer_collection.find_one(query)
        except Exception as e:
            raise Exception(f"Error getting customer by QR code: {str(e)}")
    
    # ================================================================
    # ORDER HISTORY METHODS
    # ================================================================
    
    def add_order_to_history(self, customer_id, order_data):
        """Add order to customer's order history"""
        try:
            if not customer_id or not order_data:
                return None
            
            order_entry = {
                'order_id': order_data.get('order_id'),
                'total_amount': order_data.get('total_amount', 0),
                'items': order_data.get('items', []),
                'date': datetime.utcnow(),
                'status': order_data.get('status', 'completed')
            }
            
            result = self.customer_collection.update_one(
                {'_id': customer_id, 'isDeleted': {'$ne': True}},
                {
                    '$push': {'order_history': order_entry},
                    '$set': {
                        'last_purchase': datetime.utcnow(),
                        'last_updated': datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise Exception(f"Error adding order to history: {str(e)}")
    
    def get_customer_order_history(self, customer_id, limit=50):
        """Get customer's order history"""
        try:
            if not customer_id:
                return []
            
            customer = self.customer_collection.find_one(
                {'_id': customer_id, 'isDeleted': {'$ne': True}},
                {'order_history': 1}
            )
            
            if not customer or 'order_history' not in customer:
                return []
            
            # Sort by date descending and limit
            order_history = sorted(
                customer['order_history'], 
                key=lambda x: x.get('date', datetime.min), 
                reverse=True
            )
            
            return order_history[:limit]
            
        except Exception as e:
            raise Exception(f"Error getting order history: {str(e)}")
        
    # ================================================================
    # IMPORT & EXPORT METHODS
    # ================================================================
    
    def export_customers_to_csv(self, include_deleted=False):
        """Export customers to CSV format"""
        try:
            query = {}
            if not include_deleted:
                query["isDeleted"] = {"$ne": True}

            customers = list(self.customer_collection.find(query))
            if not customers:
                return None

            headers = [
                "_id", "username", "full_name", "email", "phone",
                "loyalty_points", "status", "date_created", "last_updated", "isDeleted"
            ]

            def safe_date(value):
                from datetime import datetime
                if not value:
                    return ""
                if isinstance(value, datetime):
                    return value.strftime("%Y-%m-%d %H:%M:%S")
                return str(value)

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()

            for c in customers:
                writer.writerow({
                    "_id": c.get("_id", ""),
                    "username": c.get("username", ""),
                    "full_name": c.get("full_name", ""),
                    "email": c.get("email", ""),
                    "phone": c.get("phone", ""),
                    "loyalty_points": c.get("loyalty_points", 0),
                    "status": c.get("status", ""),
                    "date_created": safe_date(c.get("date_created")),
                    "last_updated": safe_date(c.get("last_updated")),
                    "isDeleted": c.get("isDeleted", False),
                })

            output.seek(0)
            return output.getvalue()

        except Exception as e:
            raise Exception(f"Error exporting customers: {str(e)}")

    

    def import_customers_from_csv(self, file_path, current_user=None):
        """Import customers from a CSV file"""
        try:
            imported_count = 0
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip rows without required fields
                    if not row.get("email") or not row.get("username"):
                        continue

                    # Check if customer already exists
                    existing = self.customer_collection.find_one({
                        "email": row["email"].strip().lower(),
                        "isDeleted": {"$ne": True}
                    })
                    if existing:
                        continue  # skip duplicates

                    # Generate sequential ID
                    customer_id = self.generate_customer_id()
                    now = datetime.utcnow()

                    new_customer = {
                        "_id": customer_id,
                        "username": row["username"].strip(),
                        "full_name": row.get("full_name", "").strip(),
                        "email": row["email"].strip().lower(),
                        "phone": row.get("phone", ""),
                        "password": self.hash_password(row.get("password", "123456")),  # Default password
                        "loyalty_points": int(row.get("loyalty_points", 0)),
                        "isDeleted": False,
                        "status": row.get("status", "active"),
                        "date_created": now,
                        "last_updated": now
                    }

                    self.customer_collection.insert_one(new_customer)
                    imported_count += 1

            # Log import action
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_bulk_action(current_user, "import_customers", {"count": imported_count})
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")

            return {"imported_count": imported_count}

        except Exception as e:
            raise Exception(f"Error importing customers: {str(e)}")
import uuid
from datetime import datetime
from ..services.database_service import DatabaseService
from ..models import User
import bcrypt
import logging
from .audit_service import AuditLogService
from notifications.services import  NotificationService
from notifications.email_verification_service import email_verification_service
logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        """Initialize UserService with audit logging"""
        db_service = DatabaseService()
        self.table = db_service.get_table('users')
        self.audit_service = AuditLogService()
        self.notification_service = NotificationService()
    
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
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        if not password or not hashed:
            return False
        
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    # ================================================================
    # NOTIFICATION METHODS
    # ================================================================
    
    def _send_user_notification(self, action_type, user_name, user_id=None):
        """Simple notification helper for user actions"""
        try:
            titles = {
                'created': "New User Created",
                'updated': "User Updated", 
                'password_changed': "Password Updated", 
                'soft_deleted': "User Deleted",
                'hard_deleted': "User Permanently Deleted",
                'restored': "User Restored"
            }
            
            if action_type in titles:
                self.notification_service.create_notification(
                    title=titles[action_type],
                    message=f"User '{user_name}' has been {action_type.replace('_', ' ')}",
                    priority="high" if action_type == 'hard_deleted' else "medium",
                    notification_type="system",
                    metadata={
                        "user_id": str(user_id) if user_id else "",
                        "user_name": user_name,
                        "action_type": f"user_{action_type}"
                    }
                )
        except Exception as e:
            logger.error(f"Failed to send user notification: {e}")

    
    # ================================================================
    # CRUD OPERATIONS
    # ================================================================
    def update_user_profile(self, user_id, user_data, current_user=None, role_context=None):
        """Update user with role-based restrictions in DynamoDB"""
        try:
            if not user_id:
                return None
            
            response = self.table.get_item(Key={'user_id': user_id})
            old_user = response.get('Item')
            if not old_user or old_user.get('isDeleted'):
                return None
            
            allowed_fields = {}
            if role_context == 'self_service':
                allowed_fields = {'password': user_data.get('password')}
            elif role_context == 'admin':
                allowed_fields = user_data.copy()
            else:
                raise Exception("Invalid role context")

            allowed_fields['last_updated'] = datetime.utcnow().isoformat() + "Z"
            update_data = {k: v for k, v in allowed_fields.items() if v is not None}
            if update_data.get('password'):
                update_data['password'] = self.hash_password(update_data['password'])
            
            update_expression = "SET " + ", ".join(f"#{k}=:{k}" for k in update_data.keys())
            expression_attribute_names = {f"#{k}": k for k in update_data.keys()}
            expression_attribute_values = {f":{k}": v for k, v in update_data.items()}

            self.table.update_item(
                Key={'user_id': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )
            
            response = self.table.get_item(Key={'user_id': user_id})
            updated_user = response.get('Item')
            
            user_name = updated_user.get('full_name', updated_user.get('username', 'User'))
            action = 'password_changed' if role_context == 'self_service' else 'updated'
            self._send_user_notification(action, user_name, user_id)
            
            return updated_user
            
        except Exception as e:
            raise Exception(f"Error updating user profile: {str(e)}")

    def generate_user_id(self):
        """Generate a unique USER-#### format ID"""
        return f"USER-{uuid.uuid4()}"

    def create_user(self, user_data, current_user=None):
        """Create a new user in DynamoDB"""
        try:
            user_id = self.generate_user_id()
            user_data['user_id'] = user_id
            
            if user_data.get('password'):
                user_data['password'] = self.hash_password(user_data['password'])
            
            now_iso = datetime.utcnow().isoformat() + "Z"
            user_data.update({
                'date_created': now_iso,
                'last_updated': now_iso,
                'status': user_data.get('status', 'active'),
                'isDeleted': False,
                'email_verified': False
            })
            
            user_data.pop('_id', None) # remove old _id if present
            item_to_put = {k: v for k, v in user_data.items() if v not in [None, '']}
            
            self.table.put_item(Item=item_to_put)
            
            user_name = user_data.get('full_name', user_data.get('username', 'User'))
            self._send_user_notification('created', user_name, user_id)
            
            # ... (email verification and audit logging) ...
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise Exception(f"Error creating user: {str(e)}")
        
    def get_users(self, page=1, limit=50, status=None, role=None, include_deleted=False, search=None, start_key=None):
        """Get users with pagination and filtering from DynamoDB."""
        try:
            scan_kwargs = {'Limit': limit}
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            
            filter_expressions = []
            if not include_deleted:
                filter_expressions.append(Attr('isDeleted').ne(True))
            if status:
                filter_expressions.append(Attr('status').eq(status))
            if role:
                filter_expressions.append(Attr('role').eq(role))
            if search:
                filter_expressions.append(
                    Attr('username').contains(search) | Attr('email').contains(search) | Attr('full_name').contains(search)
                )

            if filter_expressions:
                scan_kwargs['FilterExpression'] = filter_expressions[0]
                for expression in filter_expressions[1:]:
                    scan_kwargs['FilterExpression'] &= expression
        
            response = self.table.scan(**scan_kwargs)
        
            return {
                'users': response.get('Items', []),
                'last_evaluated_key': response.get('LastEvaluatedKey')
            }
        except Exception as e:
            raise Exception(f"Error getting users: {str(e)}")

    def get_user_by_id(self, user_id, include_deleted=False):
        """Get user by user_id from DynamoDB."""
        try:
            if not user_id:
                return None
        
            response = self.table.get_item(Key={'user_id': user_id})
            user = response.get('Item')

            if user and not include_deleted and user.get('isDeleted'):
                return None
        
            return user
        except Exception as e:
            raise Exception(f"Error getting user: {str(e)}")
    
    def get_user_by_username(self, username, include_deleted=False):
        """Get user by username from DynamoDB. NOTE: This is inefficient without a GSI on username."""
        try:
            if not username:
                return None
        
            filter_expression = Attr('username').eq(username)
            if not include_deleted:
                filter_expression &= Attr('isDeleted').ne(True)
            
            response = self.table.scan(FilterExpression=filter_expression)
        
            return response.get('Items')[0] if response.get('Items') else None
        except Exception as e:
            raise Exception(f"Error getting user by username: {str(e)}")

    def get_user_by_email(self, email, include_deleted=False):
        """Get user by email from DynamoDB. NOTE: This is inefficient without a GSI on email."""
        try:
            if not email:
                return None
                
            filter_expression = Attr('email').eq(email)
            if not include_deleted:
                filter_expression &= Attr('isDeleted').ne(True)
                
            response = self.table.scan(FilterExpression=filter_expression)
        
            return response.get('Items')[0] if response.get('Items') else None
        except Exception as e:
            raise Exception(f"Error getting user by email: {str(e)}")
    
    def get_disabled_users(self, page=1, limit=50, start_key=None):
        """Get users with disabled status from DynamoDB"""
        try:
            scan_kwargs = {'Limit': limit}
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
                
            scan_kwargs['FilterExpression'] = Attr('status').eq('disabled') & Attr('isDeleted').ne(True)
            
            response = self.table.scan(**scan_kwargs)

            return {
                'users': response.get('Items', []),
                'last_evaluated_key': response.get('LastEvaluatedKey')
            }
        except Exception as e:
            raise Exception(f"Error getting disabled users: {str(e)}")

    def soft_delete_user(self, user_id, current_user=None):
        """Soft delete user - streamlined"""
        try:
            logger.info(f"Soft deleting user {user_id}")
            if current_user:
                logger.info(f"Deleted by: {current_user['username']}")
            
            if not user_id:
                return False
            
            # Get user data before deletion (only active users)
            user_to_delete = self.collection.find_one({
                '_id': user_id,  # No ObjectId needed
                'isDeleted': {'$ne': True}
            })
            
            if not user_to_delete:
                return False
            
            # Soft delete
            update_data = {
                'isDeleted': True,
                'deletedAt': datetime.utcnow(),
                'deletedBy': current_user.get('username') if current_user else 'system',
                'last_updated': datetime.utcnow()
            }
            
            result = self.collection.update_one(
                {'_id': user_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                # Send notification
                user_name = user_to_delete.get('full_name', user_to_delete.get('username', 'User'))
                self._send_user_notification('soft_deleted', user_name, user_id)
                
                # Audit logging
                if current_user and self.audit_service:
                    try:
                        self.audit_service.log_user_delete(current_user, user_to_delete, deletion_type="soft_delete")
                        logger.info("Audit log created for user soft deletion")
                    except Exception as audit_error:
                        logger.error(f"Audit logging failed: {audit_error}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error soft deleting user {user_id}: {str(e)}")
            raise Exception(f"Error soft deleting user: {str(e)}")
        
    def restore_user(self, user_id, current_user=None):
        """Restore soft-deleted user (compliance feature)"""
        try:
            if not user_id:
                return False
            
            # Find deleted user
            deleted_user = self.collection.find_one({
                '_id': user_id,
                'isDeleted': True
            })
            
            if not deleted_user:
                return False
            
            # Restore with minimal data
            result = self.collection.update_one(
                {'_id': user_id},
                {
                    '$set': {
                        'isDeleted': False,
                        'restoredAt': datetime.utcnow(),
                        'restoredBy': current_user.get('username') if current_user else 'system',
                        'last_updated': datetime.utcnow(),
                        'status': 'active'
                    },
                    '$unset': {
                        'deletedAt': "",
                        'deletedBy': ""
                    }
                }
            )
            
            if result.modified_count > 0:
                user_name = deleted_user.get('full_name', deleted_user.get('username', 'User'))
                self._send_user_notification('restored', user_name, user_id)
                
                # Audit for compliance
                if current_user and self.audit_service:
                    self.audit_service.log_user_restore(current_user, deleted_user)
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error restoring user {user_id}: {str(e)}")
            raise Exception(f"Error restoring user: {str(e)}")
    
    def hard_delete_user(self, user_id, current_user=None, confirmation_token=None):
        """PERMANENT deletion - compliance only (requires confirmation)"""
        try:
            # Extra safety check
            if not confirmation_token or confirmation_token != "PERMANENT_DELETE_CONFIRMED":
                raise Exception("Hard delete requires explicit confirmation token")
            
            logger.warning(f"PERMANENT DELETION initiated for {user_id}")
            
            if not user_id:
                return False
            
            # Get user before permanent deletion
            user_to_delete = self.collection.find_one({'_id': user_id})
            if not user_to_delete:
                return False
            
            # PERMANENTLY DELETE
            result = self.collection.delete_one({'_id': user_id})
            
            if result.deleted_count > 0:
                user_name = user_to_delete.get('full_name', user_to_delete.get('username', 'User'))
                
                # Critical notification
                self._send_user_notification('hard_deleted', user_name, user_id)
                
                # Compliance audit
                if current_user and self.audit_service:
                    self.audit_service.log_user_hard_delete(current_user, user_to_delete)
                
                logger.warning(f"User {user_id} PERMANENTLY DELETED")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error permanently deleting user {user_id}: {str(e)}")
            raise Exception(f"Error permanently deleting user: {str(e)}")

    def get_disabled_users(self, page=1, limit=50):
        """Get users with disabled status"""
        try:
            query = {
                'status': 'disabled',
                'isDeleted': {'$ne': True}  # Not actually deleted, just disabled
            }
            
            skip = (page - 1) * limit
            users = list(self.collection.find(query).skip(skip).limit(limit))
            total = self.collection.count_documents(query)
            
            return {
                'users': users,
                'total': total,
                'page': page,
                'limit': limit,
                'has_more': skip + limit < total
            }
        except Exception as e:
            raise Exception(f"Error getting disabled users: {str(e)}")
        
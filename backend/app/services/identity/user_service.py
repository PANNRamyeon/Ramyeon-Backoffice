from datetime import datetime
from models.Users import User
import bcrypt
import logging
from ..core.audit_service import AuditLogService
from notifications.services import NotificationService
from notifications.email_verification_service import email_verification_service

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        """Initialize UserService using PynamoDB User model"""
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
        """Update user with role-based restrictions using PynamoDB model"""
        try:
            if not user_id:
                return None
            
            # Get existing user
            user = User.get_by_id(user_id)
            if not user or user.isDeleted:
                return None

            old_dict = user.to_dict()

            # Determine allowed fields based on role context
            allowed_fields = {}
            if role_context == 'self_service':
                # Self-service users can only update their password
                if user_data.get('password'):
                    password_hash = self.hash_password(user_data['password'])
                    user.update_password(password_hash)
                    action = 'password_changed'
                else:
                    # No update needed
                    return user.to_dict()
            elif role_context == 'admin':
                # Admin can update any field
                allowed_fields = user_data.copy()
                
                # Hash password if provided
                if 'password' in allowed_fields:
                    password = allowed_fields.pop('password')
                    password_hash = self.hash_password(password)
                    user.update_password(password_hash)
                
                # Filter to only updatable fields (prevents tzinfo errors from frontend)
                updatable_fields = ['username', 'email', 'full_name', 'role', 'status']
                filtered_fields = {k: v for k, v in allowed_fields.items() if k in updatable_fields}
                
                if filtered_fields:
                    user.update_user(**filtered_fields)
                
                action = 'updated'
            else:
                raise Exception("Invalid role context")
            
            user_dict = user.to_dict()
            
            # Send notification
            user_name = user.full_name or user.username
            self._send_user_notification(action, user_name, user_id)
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_user_update(current_user, user_id, old_dict, user_dict)
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return user_dict
            
        except ValueError as ve:
            logger.error(f"Validation error updating user: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            raise Exception(f"Error updating user profile: {str(e)}")

    def create_user(self, user_data, current_user=None):
        """Create a new user using PynamoDB model"""
        try:
            logger.info(f"Creating user: {user_data.get('username')}")
            
            # Validate required fields
            username = user_data.get('username')
            email = user_data.get('email')
            password = user_data.get('password')
            
            if not username:
                raise ValueError("Username is required")
            if not email:
                raise ValueError("Email is required")
            if not password:
                raise ValueError("Password is required")
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create user using model's class method
            user = User.create_user(
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=user_data.get('full_name'),
                role=user_data.get('role', 'user'),
                status=user_data.get('status', 'active')
            )
            
            user_dict = user.to_dict()
            
            # Send notification
            user_name = user.full_name or user.username
            self._send_user_notification('created', user_name, user.sk)
            
            # Send email verification
            try:
                email_verification_service.send_verification_email(user.email, user.sk)
                logger.info(f"Verification email sent to {user.email}")
            except Exception as email_error:
                logger.error(f"Failed to send verification email: {email_error}")
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_user_create(current_user, user_dict)
                    logger.debug("Audit log created for user creation")
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            logger.info(f"User '{user.username}' created successfully with ID {user.sk}")
            return user_dict
            
        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise Exception(f"Error creating user: {str(e)}")
        
    def get_users(self, page=1, limit=50, status=None, role=None, include_deleted=False, search=None):
        """Get users with pagination and filtering using PynamoDB model"""
        try:
            # Get users with optional role/status filtering
            if role or status:
                # Note: get_users_by_role_status excludes deleted users by default.
                # If include_deleted=True, we need to include them; fallback to scanning all users.
                if include_deleted:
                    # Use get_all_users and filter manually
                    all_users = User.get_all_users(include_deleted=True)
                    users = []
                    for u in all_users:
                        role_match = not role or u.role.upper() == role.upper()
                        status_match = not status or u.status.upper() == status.upper()
                        if role_match and status_match:
                            users.append(u)
                else:
                    users = User.get_users_by_role_status(role=role, status=status)
            else:
                users = User.get_all_users(include_deleted=include_deleted)
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                users = [
                    u for u in users
                    if (u.username and search_lower in u.username.lower()) or
                       (u.email and search_lower in u.email.lower()) or
                       (u.full_name and search_lower in u.full_name.lower())
                ]
            
            # Apply pagination
            skip = (page - 1) * limit
            total = len(users)
            users_page = users[skip:skip + limit]
            
            # Convert to dicts
            users_data = [u.to_dict() for u in users_page]
            
            return {
                'users': users_data,
                'total': total,
                'page': page,
                'limit': limit,
                'has_more': skip + limit < total
            }
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            raise Exception(f"Error getting users: {str(e)}")

    def get_user_by_id(self, user_id, include_deleted=False):
        """Get user by ID using PynamoDB model"""
        try:
            if not user_id:
                return None
            
            user = User.get_by_id(user_id)
            
            if not user:
                return None
            
            if not include_deleted and user.isDeleted:
                return None
            
            return user.to_dict()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise Exception(f"Error getting user: {str(e)}")
    
    def get_user_by_username(self, username, include_deleted=False):
        """Get user by username using PynamoDB model (scan-based)"""
        try:
            if not username:
                return None
            
            user = User.get_by_username(username)
            
            if not user:
                return None
            
            if not include_deleted and user.isDeleted:
                return None
            
            return user.to_dict()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            raise Exception(f"Error getting user by username: {str(e)}")

    def get_user_by_email(self, email, include_deleted=False):
        """Get user by email using PynamoDB model (GSI-based)"""
        try:
            if not email:
                return None
            
            user = User.get_by_email(email)
            
            if not user:
                return None
            
            if not include_deleted and user.isDeleted:
                return None
            
            return user.to_dict()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            raise Exception(f"Error getting user by email: {str(e)}")
    
    def get_disabled_users(self, page=1, limit=50):
        """Get users with inactive status"""
        try:
            users = User.get_users_by_role_status(status='inactive')
            
            # Apply pagination
            skip = (page - 1) * limit
            total = len(users)
            users_page = users[skip:skip + limit]
            
            # Convert to dicts
            users_data = [u.to_dict() for u in users_page]
            
            return {
                'users': users_data,
                'total': total,
                'page': page,
                'limit': limit,
                'has_more': skip + limit < total
            }
        except Exception as e:
            logger.error(f"Error getting disabled users: {e}")
            raise Exception(f"Error getting disabled users: {str(e)}")

    def get_deleted_users(self, page=1, limit=50):
        """Get all soft‑deleted users"""
        try:
            all_users = User.get_all_users(include_deleted=True)
            deleted_users = [u for u in all_users if u.isDeleted]
            
            # Apply pagination
            skip = (page - 1) * limit
            total = len(deleted_users)
            users_page = deleted_users[skip:skip + limit]
            
            users_data = [u.to_dict() for u in users_page]
            
            return {
                'users': users_data,
                'total': total,
                'page': page,
                'limit': limit,
                'has_more': skip + limit < total
            }
        except Exception as e:
            logger.error(f"Error getting deleted users: {e}")
            raise Exception(f"Error getting deleted users: {str(e)}")

    def soft_delete_user(self, user_id, current_user=None):
        """Soft delete user using PynamoDB model"""
        try:
            logger.info(f"Soft deleting user {user_id}")
            if current_user:
                logger.info(f"Deleted by: {current_user.get('username')}")
            
            if not user_id:
                return False
            
            # Get user
            user = User.get_by_id(user_id)
            if not user or user.isDeleted:
                logger.warning(f"User {user_id} not found or already deleted")
                return False
            
            # Use User model's soft_delete method
            user.soft_delete()
            
            # Log deletion details
            deleted_by = current_user.get('username') if current_user else 'system'
            logger.info(f"User {user_id} soft deleted by {deleted_by}")
            
            user_dict = user.to_dict()
            
            # Send notification
            user_name = user.full_name or user.username
            self._send_user_notification('soft_deleted', user_name, user_id)
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_user_delete(current_user, user_dict)
                    logger.info("Audit log created for user soft deletion")
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error soft deleting user {user_id}: {e}")
            raise Exception(f"Error soft deleting user: {str(e)}")
        
    def restore_user(self, user_id, current_user=None):
        """Restore soft-deleted user using PynamoDB model"""
        try:
            if not user_id:
                return False
            
            # Get deleted user
            user = User.get_by_id(user_id)
            if not user or not user.isDeleted:
                logger.warning(f"User {user_id} not found or not deleted")
                return False
            
            # Use User model's restore method
            user.restore()
            
            # Log restoration details
            restored_by = current_user.get('username') if current_user else 'system'
            logger.info(f"User {user_id} restored by {restored_by}")
            
            user_dict = user.to_dict()
            
            # Send notification
            user_name = user.full_name or user.username
            self._send_user_notification('restored', user_name, user_id)
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_user_restore(current_user, user_dict)
                    logger.info("Audit log created for user restoration")
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error restoring user {user_id}: {e}")
            raise Exception(f"Error restoring user: {str(e)}")
    
    def hard_delete_user(self, user_id, current_user=None, confirmation_token=None):
        """PERMANENT deletion using PynamoDB model - compliance only (requires confirmation)"""
        try:
            # Extra safety check
            if not confirmation_token or confirmation_token != "PERMANENT_DELETE_CONFIRMED":
                raise Exception("Hard delete requires explicit confirmation token")
            
            logger.warning(f"PERMANENT DELETION initiated for {user_id}")
            
            if not user_id:
                return False
            
            # Get user before permanent deletion
            user = User.get_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            user_dict = user.to_dict()
            user_name = user.full_name or user.username
            
            # PERMANENTLY DELETE (calls User.hard_delete() -> self.delete())
            user.hard_delete()
            
            # Critical notification
            self._send_user_notification('hard_deleted', user_name, user_id)
            
            # Compliance audit
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_user_hard_delete(current_user, user_dict)
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            logger.warning(f"User {user_id} PERMANENTLY DELETED")
            return True
            
        except Exception as e:
            logger.error(f"Error permanently deleting user {user_id}: {e}")
            raise Exception(f"Error permanently deleting user: {str(e)}")
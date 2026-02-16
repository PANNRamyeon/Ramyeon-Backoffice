import uuid
from datetime import datetime
from pynamodb.exceptions import DoesNotExist
import bcrypt
import logging

from ..models.Users import User
from ..services.audit_service import AuditLogService
from notifications.services import NotificationService
from notifications.email_verification_service import email_verification_service

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self):
        """Initialize UserService with audit and notification services."""
        self.audit_service = AuditLogService()
        self.notification_service = NotificationService()

    # ================================================================
    # UTILITY METHODS
    # ================================================================

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        if not password:
            raise ValueError("Password cannot be empty")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
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

    def _send_user_notification(self, action_type: str, user_name: str, user_id: str = None):
        """Simple notification helper for user actions."""
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

    def create_user(self, user_data: dict, current_user: dict = None) -> dict:
        """Create a new user using the User model (GSI checks, auto SK)."""
        try:
            # Hash password if present
            password_hash = None
            if user_data.get('password'):
                password_hash = self.hash_password(user_data['password'])

            # Delegate creation to the model – handles uniqueness, SK, GSIs, timestamps
            user = User.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=password_hash,
                full_name=user_data.get('full_name'),
                role=user_data.get('role', 'user'),
                status=user_data.get('status', 'active'),
                email_verified=user_data.get('email_verified', False)
            )

            user_dict = user.to_dict()
            user_name = user_dict.get('full_name') or user_dict.get('username') or 'User'

            # Notification
            self._send_user_notification('created', user_name, user_dict['user_id'])

            # Email verification (if not already verified)
            if not user.email_verified:
                try:
                    email_verification_service.send_verification_email(user.email, user_dict['user_id'])
                    logger.info(f"Verification email sent to {user.email}")
                except Exception as e:
                    logger.error(f"Failed to send verification email: {e}")

            # Audit logging
            if current_user and self.audit_service:
                self.audit_service.log_user_creation(current_user, user_dict)

            return user_dict

        except ValueError as e:
            logger.error(f"Validation error creating user: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    def get_user_by_id(self, user_id: str, include_deleted: bool = False) -> User | None:
        """Retrieve a user by their SK (e.g., USER-001)."""
        try:
            user = User.get("users", user_id)
            if not include_deleted and user.isDeleted:
                return None
            return user
        except DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise

    def get_user_by_username(self, username: str, include_deleted: bool = False) -> User | None:
        """Retrieve a user by username using the identifier GSI."""
        try:
            user = User.get_by_username(username)
            if user and not include_deleted and user.isDeleted:
                return None
            return user
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None

    def get_user_by_email(self, email: str, include_deleted: bool = False) -> User | None:
        """Retrieve a user by email using the identifier GSI."""
        try:
            user = User.get_by_email(email)
            if user and not include_deleted and user.isDeleted:
                return None
            return user
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    def get_users(self, page: int = 1, limit: int = 50, status: str = None,
                  role: str = None, include_deleted: bool = False,
                  search: str = None, start_key: dict = None) -> dict:
        """
        Get users with pagination and filtering.
        Uses scan with filter conditions (fallback to GSI for role/status if possible).
        """
        try:
            # Build filter condition
            conditions = []

            # Soft delete filter
            if not include_deleted:
                conditions.append(User.isDeleted == False)

            if status:
                conditions.append(User.status == status)
            if role:
                conditions.append(User.role == role)
            if search:
                search_lower = search.lower()
                conditions.append(
                    (User.username.contains(search_lower)) |
                    (User.email.contains(search_lower)) |
                    (User.full_name.contains(search_lower))
                )

            # Combine all conditions with AND
            filter_condition = None
            if conditions:
                filter_condition = conditions[0]
                for cond in conditions[1:]:
                    filter_condition &= cond

            # Perform scan with pagination
            scan_kwargs = {
                'limit': limit,
                'filter_condition': filter_condition
            }
            if start_key:
                scan_kwargs['last_evaluated_key'] = start_key

            iterator = User.scan(**scan_kwargs)
            users = list(iterator)
            last_key = iterator.last_evaluated_key

            return {
                'users': [u.to_dict() for u in users],
                'last_evaluated_key': last_key
            }

        except Exception as e:
            logger.error(f"Error getting users: {e}")
            raise

    def get_disabled_users(self, page: int = 1, limit: int = 50, start_key: dict = None) -> dict:
        """Convenience method: get users with status 'disabled' (not deleted)."""
        return self.get_users(
            page=page,
            limit=limit,
            status='disabled',
            include_deleted=False,
            start_key=start_key
        )

    def update_user_profile(self, user_id: str, user_data: dict,
                            current_user: dict = None, role_context: str = None) -> dict:
        """
        Update user with role‑based restrictions.
        - 'self_service': only password can be changed.
        - 'admin': all fields can be updated.
        """
        try:
            user = self.get_user_by_id(user_id, include_deleted=False)
            if not user:
                raise ValueError("User not found or deleted")

            old_user_dict = user.to_dict()

            if role_context == 'self_service':
                # Only allow password update
                if 'password' in user_data and user_data['password']:
                    new_hash = self.hash_password(user_data['password'])
                    user.update_password(new_hash)
                    action = 'password_changed'
                else:
                    raise ValueError("No password provided for self‑service update")

            elif role_context == 'admin':
                # Prepare update data – exclude password because we handle it separately
                update_kwargs = user_data.copy()
                password_new = update_kwargs.pop('password', None)
                if password_new:
                    update_kwargs['password'] = self.hash_password(password_new)

                # Delegate to model's update method (handles GSIs, uniqueness, timestamps)
                user.update_user(**update_kwargs)
                action = 'updated'

            else:
                raise ValueError("Invalid role_context")

            # Refresh user and get dict
            updated_user = self.get_user_by_id(user_id)
            updated_dict = updated_user.to_dict()
            user_name = updated_dict.get('full_name') or updated_dict.get('username') or 'User'

            # Notification
            self._send_user_notification(action, user_name, user_id)

            # Audit logging
            if current_user and self.audit_service:
                self.audit_service.log_user_update(current_user, old_user_dict, updated_dict)

            return updated_dict

        except ValueError as e:
            logger.error(f"Validation error updating user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise

    def soft_delete_user(self, user_id: str, current_user: dict = None) -> bool:
        """Soft delete a user (set isDeleted=True, status='inactive')."""
        try:
            user = self.get_user_by_id(user_id, include_deleted=False)
            if not user:
                return False

            # Capture user data before deletion for audit
            user_dict = user.to_dict()
            user.soft_delete()

            user_name = user_dict.get('full_name') or user_dict.get('username') or 'User'
            self._send_user_notification('soft_deleted', user_name, user_id)

            if current_user and self.audit_service:
                self.audit_service.log_user_delete(current_user, user_dict, deletion_type="soft_delete")

            return True

        except Exception as e:
            logger.error(f"Error soft deleting user {user_id}: {e}")
            raise

    def restore_user(self, user_id: str, current_user: dict = None) -> bool:
        """Restore a soft‑deleted user."""
        try:
            user = self.get_user_by_id(user_id, include_deleted=True)
            if not user or not user.isDeleted:
                return False

            user_dict = user.to_dict()
            user.restore()

            user_name = user_dict.get('full_name') or user_dict.get('username') or 'User'
            self._send_user_notification('restored', user_name, user_id)

            if current_user and self.audit_service:
                self.audit_service.log_user_restore(current_user, user_dict)

            return True

        except Exception as e:
            logger.error(f"Error restoring user {user_id}: {e}")
            raise

    def hard_delete_user(self, user_id: str, current_user: dict = None,
                         confirmation_token: str = None) -> bool:
        """
        PERMANENT deletion – requires explicit confirmation token.
        This physically removes the item from DynamoDB.
        """
        try:
            if not confirmation_token or confirmation_token != "PERMANENT_DELETE_CONFIRMED":
                raise ValueError("Hard delete requires explicit confirmation token")

            user = self.get_user_by_id(user_id, include_deleted=True)
            if not user:
                return False

            user_dict = user.to_dict()
            user_name = user_dict.get('full_name') or user_dict.get('username') or 'User'

            # PynamoDB delete operation
            user.delete()

            self._send_user_notification('hard_deleted', user_name, user_id)

            if current_user and self.audit_service:
                self.audit_service.log_user_hard_delete(current_user, user_dict)

            logger.warning(f"User {user_id} PERMANENTLY DELETED")
            return True

        except ValueError as e:
            logger.error(f"Confirmation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error permanently deleting user {user_id}: {e}")
            raise
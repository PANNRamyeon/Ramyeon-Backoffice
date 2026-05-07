"""
User Model - Following ERD Specification with Single Table Design
PK = users, SK = USER-### (3-digit format)
Single Table Design using RamyeonCornerDB with 1 GSI for auth lookups
Email is indexed via the GSI; username lookups use a scan fallback.
Only items with SK starting with "USER-" are considered users.
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from datetime import datetime
import logging
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST
from app.custom_attributes import FixedUTCDateTimeAttribute as UTCDateTimeAttribute
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


# ============= GLOBAL SECONDARY INDEXES =============

class UserIdentifierGSI(GlobalSecondaryIndex):
    """
    GSI for unique user identifier lookups (email).
    Will be reused for customer email lookups with different identifier_type values.
    """
    class Meta:
        index_name = 'gsi-user-identifiers'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    identifier_type = UnicodeAttribute(hash_key=True)
    identifier_value = UnicodeAttribute(range_key=True)


class User(Model):
    """
    USER MODEL - Following ERD Specification with GSIs
    
    Core ERD Fields:
    - PK = users
    - SK = USER-### (3-digit)
    - username (String)
    - email (String)
    - password (String)
    - full_name (String)
    - role (String)
    - status (String)
    - date_created (ISODATE)
    - last_updated (ISODATE)
    - isDeleted (boolean)
    - last_login (ISODATE)
    - email_verified (boolean)
    - email_verified_at (ISODATE)
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="users")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "USER-001" (3-digit)
    
    # ============= GSI KEYS (Email only) =============
    identifier_type = UnicodeAttribute(null=True)   # set to "EMAIL"
    identifier_value = UnicodeAttribute(null=True)  # lowercased email
    
    # ============= GSI REFERENCES =============
    identifier_gsi = UserIdentifierGSI()
    
    # ============= CORE ERD FIELDS =============
    username = UnicodeAttribute(null=True)
    email = UnicodeAttribute(null=True)
    password = UnicodeAttribute(null=True)
    full_name = UnicodeAttribute(null=True)
    role = UnicodeAttribute(default="user")
    status = UnicodeAttribute(default="active")
    date_created = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    last_updated = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    isDeleted = BooleanAttribute(default=False)
    last_login = UTCDateTimeAttribute(null=True)
    email_verified = BooleanAttribute(default=False)
    email_verified_at = UTCDateTimeAttribute(null=True)
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_user(cls, username: str, email: str, password_hash: str, **kwargs) -> 'User':
        """
        Create a new user with auto-generated 3-digit SK and email GSI.
        """
        try:
            if not username or not username.strip():
                raise ValueError("username is required")
            if not email or not email.strip():
                raise ValueError("email is required")
            if not password_hash or not password_hash.strip():
                raise ValueError("password_hash is required")
            
            username_norm = username.strip().lower()
            email_norm = email.strip().lower()
            
            # Check uniqueness
            if cls.get_by_email(email_norm):
                raise ValueError(f"Email '{email_norm}' already exists")
            if cls.get_by_username(username_norm):
                raise ValueError(f"Username '{username_norm}' already exists")
            
            # Generate SK (3-digit)
            sk = generate_sk('USER', 'user_seq', width=4)
            
            # Create user item with email GSI fields
            user = cls(
                pk="users",
                sk=sk,
                username=username_norm,
                email=email_norm,
                password=password_hash,
                full_name=kwargs.get('full_name'),
                role=kwargs.get('role', 'user'),
                status=kwargs.get('status', 'active'),
                isDeleted=kwargs.get('isDeleted', False),
                email_verified=kwargs.get('email_verified', False),
                email_verified_at=kwargs.get('email_verified_at'),
                # GSI fields
                identifier_type="EMAIL",
                identifier_value=email_norm,
                date_created=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                last_login=None
            )
            user.save()
            
            logger.info(f"User created: {sk} - '{username_norm}'")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise
    
    # ============= GSI-BASED QUERY METHODS =============
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """
        Get user by email using GSI (fast lookup).
        """
        try:
            email_norm = email.strip().lower()
            for user in cls.identifier_gsi.query(
                hash_key="EMAIL",
                range_key_condition=cls.identifier_value == email_norm
            ):
                return user
            return None
        except Exception as e:
            logger.error(f"Error in get_by_email GSI query: {str(e)}")
            return cls._get_by_email_scan(email_norm)
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """
        Get user by username using scan (no GSI for username).
        Only scans items with SK starting with "USER-".
        """
        username_norm = username.strip().lower()
        for user in cls.query("users", range_key_condition=cls.sk.startswith("USER-")):
            if user.username and user.username.lower() == username_norm:
                return user
        return None
    
    @classmethod
    def get_all_users(cls, include_deleted: bool = False) -> List['User']:
        try:
            users = []
            for user in cls.query("users", range_key_condition=cls.sk.startswith("USER-")):
                if not include_deleted and user.isDeleted:
                    continue
                users.append(user)
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []
    
    @classmethod
    def get_users_by_role_status(cls, role: str = None, status: str = None) -> List['User']:
        try:
            users = []
            for user in cls.query("users", range_key_condition=cls.sk.startswith("USER-")):
                if user.isDeleted:
                    continue
                role_match = not role or (user.role and user.role.upper() == role.upper())
                status_match = not status or (user.status and user.status.upper() == status.upper())
                if role_match and status_match:
                    users.append(user)
            return users
        except Exception as e:
            logger.error(f"Error getting users by role/status: {str(e)}")
            return []
    
    @classmethod
    def get_cashiers(cls, active_only: bool = True) -> List['User']:
        try:
            if active_only:
                return cls.get_users_by_role_status(role="cashier", status="active")
            else:
                return cls.get_users_by_role_status(role="cashier")
        except Exception as e:
            logger.error(f"Error getting cashiers: {str(e)}")
            return []
    
    @classmethod
    def get_admins(cls, active_only: bool = True) -> List['User']:
        try:
            if active_only:
                return cls.get_users_by_role_status(role="admin", status="active")
            else:
                return cls.get_users_by_role_status(role="admin")
        except Exception as e:
            logger.error(f"Error getting admins: {str(e)}")
            return []
    
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['User']:
        if not user_id:
            return None
        try:
            return cls.get('users', user_id)
        except cls.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting user by id {user_id}: {e}")
            return None
    
    # ============= FALLBACK SCAN =============
    
    @classmethod
    def _get_by_email_scan(cls, email: str) -> Optional['User']:
        for user in cls.query("users", range_key_condition=cls.sk.startswith("USER-")):
            if user.email and user.email.lower() == email:
                return user
        return None
    
    # ============= INSTANCE METHODS =============
    
    def _update_gsi_identifier(self):
        """Update the GSI identifier fields for email."""
        if self.email:
            self.identifier_type = "EMAIL"
            self.identifier_value = self.email.lower()
            self.save()
    
    def update_user(self, **kwargs) -> 'User':
        """
        Update user information, keeping GSI in sync when email changes.
        """
        try:
            updated = False
            email_changed = False
            
            if 'username' in kwargs:
                new_username = kwargs['username'].strip().lower()
                existing = self.get_by_username(new_username)
                if existing and existing.sk != self.sk:
                    raise ValueError(f"Username '{new_username}' already taken")
                self.username = new_username
                updated = True
            
            if 'email' in kwargs:
                new_email = kwargs['email'].strip().lower()
                existing = self.get_by_email(new_email)
                if existing and existing.sk != self.sk:
                    raise ValueError(f"Email '{new_email}' already taken")
                self.email = new_email
                email_changed = True
                updated = True
            
            if 'role' in kwargs:
                new_role = kwargs['role']
                valid_roles = ['admin', 'manager', 'staff']
                if new_role not in valid_roles:
                    raise ValueError(f"Role must be one of: {valid_roles}")
                self.role = new_role
                updated = True
            
            if 'status' in kwargs:
                new_status = kwargs['status']
                valid_statuses = ['active', 'inactive', 'suspended']
                if new_status not in valid_statuses:
                    raise ValueError(f"Status must be one of: {valid_statuses}")
                self.status = new_status
                updated = True
            
            for key, value in kwargs.items():
                if key not in ['username', 'email', 'role', 'status'] and hasattr(self, key) and getattr(self, key) != value:
                    setattr(self, key, value)
                    updated = True
            
            if updated:
                self.last_updated = datetime.utcnow()
                if email_changed:
                    self._update_gsi_identifier()  # updates identifier_type and identifier_value
                else:
                    self.save()
                logger.info(f"User {self.sk} updated: {list(kwargs.keys())}")
            
            return self
        except Exception as e:
            logger.error(f"Failed to update user: {str(e)}")
            raise
    
    def update_password(self, new_password_hash: str) -> 'User':
        try:
            self.password = new_password_hash
            self.last_updated = datetime.utcnow()
            self.save()
            logger.info(f"Password updated for user {self.sk}")
            return self
        except Exception as e:
            logger.error(f"Failed to update password: {str(e)}")
            raise
    
    def record_login(self) -> 'User':
        try:
            self.last_login = datetime.utcnow()
            self.save()
            return self
        except Exception as e:
            logger.error(f"Failed to record login: {str(e)}")
            raise
    
    def verify_email(self) -> 'User':
        try:
            self.email_verified = True
            self.email_verified_at = datetime.utcnow()
            self.last_updated = datetime.utcnow()
            self.save()
            logger.info(f"Email verified for user {self.sk}")
            return self
        except Exception as e:
            logger.error(f"Failed to verify email: {str(e)}")
            raise
    
    def soft_delete(self) -> 'User':
        """Soft delete user (frontend accessible). Leaves GSI intact."""
        try:
            self.isDeleted = True
            self.status = 'inactive'
            self.last_updated = datetime.utcnow()
            self.save()
            logger.info(f"User soft deleted: {self.sk}")
            return self
        except Exception as e:
            logger.error(f"Failed to soft delete user: {str(e)}")
            raise
    
    def restore(self) -> 'User':
        """Restore a soft-deleted user."""
        try:
            self.isDeleted = False
            self.status = 'active'
            self.last_updated = datetime.utcnow()
            self.save()
            logger.info(f"User restored: {self.sk}")
            return self
        except Exception as e:
            logger.error(f"Failed to restore user: {str(e)}")
            raise
    
    def hard_delete(self):
        """Permanently delete the user (terminal/URL only)."""
        self.delete()
        logger.warning(f"User {self.sk} permanently deleted.")
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        def safe_isoformat(dt):
            if not dt:
                return None
            try:
                if hasattr(dt, 'year') and (dt.year < 1900 or dt.year > 9999):
                    logger.warning(f"Invalid year detected: {dt.year}, using current time")
                    return datetime.utcnow().isoformat()
                return dt.isoformat()
            except Exception as e:
                logger.error(f"Error formatting datetime: {e}")
                return None
        
        try:
            result = {
                "user_id": self.sk,
                "username": self.username,
                "email": self.email,
                "full_name": self.full_name,
                "role": self.role,
                "status": self.status,
                "isDeleted": self.isDeleted,
                "email_verified": self.email_verified,
                "date_created": safe_isoformat(self.date_created),
                "last_updated": safe_isoformat(self.last_updated),
                "last_login": safe_isoformat(self.last_login),
                "email_verified_at": safe_isoformat(self.email_verified_at)
            }
            if include_sensitive:
                result["password"] = self.password
            return result
        except Exception as e:
            logger.error(f"Error converting user to dict: {str(e)}")
            return {}


# ============= GSI-SPECIFIC UTILITIES =============

class UserGSIManager:
    @staticmethod
    def rebuild_gsi_for_user(user_id: str):
        """
        Manually rebuild GSI for a user (useful for backfill).
        """
        try:
            user = User.get_by_id(user_id)
            if user:
                user._update_gsi_identifier()
                logger.info(f"GSI rebuilt for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to rebuild GSI for user {user_id}: {str(e)}")
            return False

    @staticmethod
    def get_user_stats_via_scan() -> Dict[str, Any]:
        stats = {"total_users": 0, "by_role": {}, "by_status": {}}
        try:
            for user in User.query("users", range_key_condition=User.sk.startswith("USER-")):
                if user.isDeleted:
                    continue
                stats["total_users"] += 1
                role = user.role.upper() if user.role else "UNKNOWN"
                stats["by_role"][role] = stats["by_role"].get(role, 0) + 1
                status = user.status.upper() if user.status else "UNKNOWN"
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
        return stats

    @staticmethod
    def find_duplicate_emails() -> List[str]:
        try:
            emails_seen = set()
            duplicates = []
            for item in User.identifier_gsi.query("EMAIL"):
                email = item.identifier_value
                if email in emails_seen:
                    duplicates.append(email)
                else:
                    emails_seen.add(email)
            return duplicates
        except Exception as e:
            logger.error(f"Error finding duplicate emails: {str(e)}")
            return []
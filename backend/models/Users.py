"""
User Model - Following ERD Specification with Single Table Design
PK = users, SK = USER-### (3-digit format)
Single Table Design using RamyeonCornerDB with 1 GSI for auth lookups
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from datetime import datetime
import logging
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


# ============= GLOBAL SECONDARY INDEXES =============

class UserIdentifierGSI(GlobalSecondaryIndex):
    """
    GSI for unique user identifier lookups (email, username)
    Query patterns:
    1. Find user by email: identifier_type="EMAIL", identifier_value="user@example.com"
    2. Find user by username: identifier_type="USERNAME", identifier_value="john_doe"
    """
    class Meta:
        index_name = 'gsi-user-identifiers'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    identifier_type = UnicodeAttribute(hash_key=True)  # "EMAIL", "USERNAME"
    identifier_value = UnicodeAttribute(range_key=True)  # actual email or username


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
        
        #if DYNAMODB_LOCAL:
        #    host = DYNAMODB_LOCAL_HOST
        
        # Capacity settings for user operations
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="users")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "USER-001" (3-digit)
    
    # ============= GSI KEYS =============
    # GSI 1: Identifier index
    identifier_type = UnicodeAttribute(null=True)  # "EMAIL", "USERNAME"
    identifier_value = UnicodeAttribute(null=True)  # actual value
    
    # ============= GSI REFERENCES =============
    identifier_gsi = UserIdentifierGSI()
    
    # ============= CORE ERD FIELDS =============
    username = UnicodeAttribute(null=True)
    email = UnicodeAttribute(null=True)
    password = UnicodeAttribute(null=True)  # Store hashed passwords only!
    full_name = UnicodeAttribute(null=True)
    role = UnicodeAttribute(default="user")  # "user", "admin", "manager", "staff", "cashier"
    status = UnicodeAttribute(default="active")  # "active", "inactive", "suspended"
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
        Create a new user with auto-generated 3-digit SK and GSIs
        
        Args:
            username: Username (required)
            email: Email address (required)
            password_hash: Hashed password (required)
            **kwargs: Additional user attributes
            
        Returns:
            User: Created and saved user instance
            
        Raises:
            ValueError: If required fields are not provided
        """
        try:
            # Validate required fields
            if not username or not username.strip():
                raise ValueError("username is required")
            if not email or not email.strip():
                raise ValueError("email is required")
            if not password_hash or not password_hash.strip():
                raise ValueError("password_hash is required")
            
            # Normalize inputs
            username_norm = username.strip().lower()
            email_norm = email.strip().lower()
            
            # Check if username or email already exists using GSI
            if cls.get_by_username(username_norm):
                raise ValueError(f"Username '{username_norm}' already exists")
            if cls.get_by_email(email_norm):
                raise ValueError(f"Email '{email_norm}' already exists")
            
            # Generate 3-digit SK using utils.py
            sk = generate_sk('USER-', 'user_seq', digits=3)
            
            # Get role and status
            role = kwargs.get('role', 'user')
            status = kwargs.get('status', 'active')
            
            # Create and save user
            user = cls(
                pk="users",
                sk=sk,
                username=username_norm,
                email=email_norm,
                password=password_hash,
                full_name=kwargs.get('full_name'),
                role=role,
                status=status,
                isDeleted=kwargs.get('isDeleted', False),
                email_verified=kwargs.get('email_verified', False),
                email_verified_at=kwargs.get('email_verified_at'),
                
                # GSI 1: Identifier index
                identifier_type=None,  # Will be set via _update_gsi_identifiers()
                identifier_value=None,
                
                date_created=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                last_login=None
            )
            
            # Save to create the item
            user.save()
            
            # Update identifier GSI after save (to avoid duplicate key issues)
            user._update_gsi_identifiers()
            
            logger.info(f"User created: {sk} - '{username_norm}'")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise
    
    # ============= GSI-BASED QUERY METHODS =============
    
    @classmethod
    def get_by_email(cls, email: str) -> 'User | None':
        """
        Get user by email using GSI (fast lookup)
        
        Args:
            email: Email to find
            
        Returns:
            User or None if not found
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
            logger.error(f"Error finding user by email '{email}': {str(e)}")
            # Fallback to scan
            return cls._get_by_email_scan(email_norm)
    
    @classmethod
    def get_by_username(cls, username: str) -> 'User | None':
        """
        Get user by username using GSI (fast lookup)
        
        Args:
            username: Username to find
            
        Returns:
            User or None if not found
        """
        try:
            username_norm = username.strip().lower()
            for user in cls.identifier_gsi.query(
                hash_key="USERNAME",
                range_key_condition=cls.identifier_value == username_norm
            ):
                return user
            return None
        except Exception as e:
            logger.error(f"Error finding user by username '{username}': {str(e)}")
            # Fallback to scan
            return cls._get_by_username_scan(username_norm)
    
    @classmethod
    def get_users_by_role_status(cls, role: str = None, status: str = None) -> List['User']:
        """
        Get users by role and/or status using scan (optimized for small user base)
        
        Args:
            role: Role to filter by (optional)
            status: Status to filter by (optional)
            
        Returns:
            list: List of users matching criteria
        """
        try:
            users = []
            
            # Scan all users and filter (efficient for small datasets < 100 users)
            for user in cls.query("users"):
                if user.isDeleted:
                    continue
                
                role_match = not role or user.role.upper() == role.upper()
                status_match = not status or user.status.upper() == status.upper()
                
                if role_match and status_match:
                    users.append(user)
            
            return users
        except Exception as e:
            logger.error(f"Error getting users by role/status: {str(e)}")
            return []
    
    @classmethod
    def get_cashiers(cls, active_only: bool = True) -> List['User']:
        """
        Get all cashier users using GSI
        
        Args:
            active_only: Only return active cashiers
            
        Returns:
            list: List of cashier users
        """
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
        """
        Get all admin users using GSI
        
        Args:
            active_only: Only return active admins
            
        Returns:
            list: List of admin users
        """
        try:
            if active_only:
                return cls.get_users_by_role_status(role="admin", status="active")
            else:
                return cls.get_users_by_role_status(role="admin")
        except Exception as e:
            logger.error(f"Error getting admins: {str(e)}")
            return []
    
    @classmethod
    def get_all_users(cls, include_deleted: bool = False) -> List['User']:
        """
        Get all users
        
        Args:
            include_deleted: Whether to include deleted users
            
        Returns:
            list: List of all users
        """
        try:
            users = []
            for user in cls.query("users"):
                if not include_deleted and user.isDeleted:
                    continue
                users.append(user)
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []
    
    # ============= FALLBACK SCAN METHODS (if GSI fails) =============
    
    @classmethod
    def _get_by_email_scan(cls, email: str) -> 'User | None':
        """Fallback method to find user by email (scan)"""
        for user in cls.query("users"):
            if user.email and user.email.lower() == email:
                return user
        return None
    
    @classmethod
    def _get_by_username_scan(cls, username: str) -> 'User | None':
        """Fallback method to find user by username (scan)"""
        for user in cls.query("users"):
            if user.username and user.username.lower() == username:
                return user
        return None
    
    # ============= INSTANCE METHODS =============
    
    def _update_gsi_identifiers(self):
        """Update GSI identifier fields"""
        try:
            # Update identifier GSI
            if self.email:
                self.identifier_type = "EMAIL"
                self.identifier_value = self.email.lower()
            elif self.username:
                self.identifier_type = "USERNAME"
                self.identifier_value = self.username.lower()
            
            self.save()
        except Exception as e:
            logger.error(f"Failed to update GSI identifiers for user {self.sk}: {str(e)}")
    
    def update_user(self, **kwargs) -> 'User':
        """
        Update user information with GSI updates
        
        Args:
            **kwargs: User attributes to update
            
        Returns:
            User: Updated user instance
        """
        try:
            updated = False
            
            # Handle special fields that affect GSIs
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
                updated = True
            
            if 'role' in kwargs:
                new_role = kwargs['role']
                valid_roles = ['user', 'admin', 'manager', 'staff', 'cashier']
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
            
            # Handle other fields
            for key, value in kwargs.items():
                if key not in ['username', 'email', 'role', 'status'] and hasattr(self, key) and getattr(self, key) != value:
                    setattr(self, key, value)
                    updated = True
            
            if updated:
                self.last_updated = datetime.utcnow()
                # Update GSIs
                self._update_gsi_identifiers()
                logger.info(f"User {self.sk} updated: {list(kwargs.keys())}")
            
            return self
        except Exception as e:
            logger.error(f"Failed to update user: {str(e)}")
            raise
    
    # ============= REST OF THE METHODS (similar to before but with GSI awareness) =============
    
    def update_password(self, new_password_hash: str) -> 'User':
        """Update user password"""
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
        """Record user login timestamp"""
        try:
            self.last_login = datetime.utcnow()
            self.save()
            return self
        except Exception as e:
            logger.error(f"Failed to record login: {str(e)}")
            raise
    
    def verify_email(self) -> 'User':
        """Mark email as verified"""
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
        """Soft delete user (mark as deleted)"""
        try:
            self.isDeleted = True
            self.status = 'inactive'
            self.last_updated = datetime.utcnow()
            # Update GSIs
            self._update_gsi_identifiers()
            logger.info(f"User soft deleted: {self.sk}")
            return self
        except Exception as e:
            logger.error(f"Failed to soft delete user: {str(e)}")
            raise
    
    def restore(self) -> 'User':
        """Restore soft-deleted user"""
        try:
            self.isDeleted = False
            self.status = 'active'
            self.last_updated = datetime.utcnow()
            # Update GSIs
            self._update_gsi_identifiers()
            logger.info(f"User restored: {self.sk}")
            return self
        except Exception as e:
            logger.error(f"Failed to restore user: {str(e)}")
            raise
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert user to dictionary for API response
        """
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
                "date_created": self.date_created.isoformat() if self.date_created else None,
                "last_updated": self.last_updated.isoformat() if self.last_updated else None,
                "last_login": self.last_login.isoformat() if self.last_login else None,
                "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None
            }
            
            if include_sensitive:
                result["password"] = self.password
            
            return result
        except Exception as e:
            logger.error(f"Error converting user to dict: {str(e)}")
            return {}


# ============= GSI-SPECIFIC UTILITIES =============

class UserGSIManager:
    """
    Manager for GSI-specific operations
    """
    
    @staticmethod
    def rebuild_gsi_for_user(user_id: str):
        """
        Manually rebuild GSI entries for a user
        Useful if GSI gets out of sync
        
        Args:
            user_id: User ID to rebuild GSIs for
        """
        try:
            user = User.get_by_id(user_id)
            if user:
                user._update_gsi_identifiers()
                logger.info(f"GSI rebuilt for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to rebuild GSI for user {user_id}: {str(e)}")
            return False
    
    @staticmethod
    def get_user_stats_via_scan() -> Dict[str, Any]:
        """
        Get user statistics using scan (efficient for small user base)
        """
        try:
            stats = {
                "total_users": 0,
                "by_role": {},
                "by_status": {}
            }
            
            # Scan all users and count (fast for < 100 users)
            for user in User.query("users"):
                if user.isDeleted:
                    continue
                
                stats["total_users"] += 1
                
                # Count by role
                role = user.role.upper() if user.role else "UNKNOWN"
                stats["by_role"][role] = stats["by_role"].get(role, 0) + 1
                
                # Count by status
                status = user.status.upper() if user.status else "UNKNOWN"
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            return stats
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {}
    
    @staticmethod
    def find_duplicate_emails() -> List[str]:
        """
        Find duplicate emails using GSI
        Should return empty list if email uniqueness constraint is working
        """
        try:
            emails_seen = set()
            duplicates = []
            
            # Query all email entries from GSI
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
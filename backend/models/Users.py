"""
User Model - Following Exact ERD Specification
PK = "users", SK = "USER-###"
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, 
    UTCDateTimeAttribute
)
from datetime import datetime
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, List
import time


class User(Model):
    """
    USER MODEL - Following Exact ERD Specification
    
    PK/SK Pattern:
    - PK: "users" (table name/entity type)
    - SK: "USER-###" (3-digit auto-increment: 001, 002, etc.)
    
    Attributes as per ERD with exact data types
    """
    
    class Meta:
        table_name = os.environ.get('USER_TABLE_NAME', 'Users')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        if os.environ.get('DYNAMODB_LOCAL', 'false').lower() == 'true':
            host = os.environ.get('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True)   # Partition Key: "users"
    sk = UnicodeAttribute(range_key=True)  # Sort Key: "USER-001"
    
    # ============= USER DATA (EXACT ERD FIELDS) =============
    
    # User ID (derived from SK, but stored for easy access)
    user_id = UnicodeAttribute()  # "USER-001"
    user_number = UnicodeAttribute()  # "001" (string to preserve leading zeros)
    
    # Authentication & Profile
    username = UnicodeAttribute(null=True)  # String
    email = UnicodeAttribute(null=True)  # String
    password = UnicodeAttribute(null=True)  # String (hashed)
    full_name = UnicodeAttribute(null=True)  # String
    
    # Role & Permissions
    role = UnicodeAttribute(default="user")  # String: "user", "admin", "manager", "staff"
    
    # Status
    status = UnicodeAttribute(default="active")  # String: "active", "inactive", "suspended"
    isDeleted = BooleanAttribute(default=False)  # boolean (keeping ERD casing)
    
    # Email Verification
    email_verified = BooleanAttribute(default=False)  # boolean
    email_verified_at = UTCDateTimeAttribute(null=True)  # ISODATE
    
    # Activity Tracking
    last_login = UTCDateTimeAttribute(null=True)  # ISODATE
    
    # Audit Trail
    date_created = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    last_updated = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    
    # ============= COUNTER CONFIGURATION =============
    ID_PREFIX = "USER-"
    DIGITS = 3  # 3-digit format: USER-001 to USER-999
    DEFAULT_START_NUMBER = 1
    
    # ============= COUNTER MANAGEMENT =============
    
    @classmethod
    def _get_dynamodb_client(cls):
        """Get DynamoDB client"""
        return boto3.resource(
            'dynamodb', 
            region_name=cls.Meta.region,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
    
    @classmethod
    def _format_user_id(cls, number: int) -> str:
        """Format user ID with prefix and 3 digits"""
        return f"{cls.ID_PREFIX}{number:0{cls.DIGITS}d}"
    
    @classmethod
    def _get_next_user_id(cls) -> Dict[str, Any]:
        """
        Get next auto-incrementing user ID (thread-safe)
        Returns: {"user_id": "USER-001", "user_number": "001", "numeric_number": 1}
        """
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Atomic increment
                response = table.update_item(
                    Key={
                        'pk': 'COUNTERS',
                        'sk': 'USER'
                    },
                    UpdateExpression='SET #value = if_not_exists(#value, :start) + :inc, updated_at = :now',
                    ExpressionAttributeNames={'#value': 'value'},
                    ExpressionAttributeValues={
                        ':start': cls.DEFAULT_START_NUMBER - 1,
                        ':inc': 1,
                        ':now': datetime.utcnow().isoformat()
                    },
                    ReturnValues='UPDATED_NEW'
                )
                
                new_number = response['Attributes']['value']
                user_id = cls._format_user_id(new_number)
                user_number_str = f"{new_number:0{cls.DIGITS}d}"
                
                return {
                    "user_id": user_id,
                    "user_number": user_number_str,
                    "numeric_number": new_number
                }
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    time.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    # Create counter if doesn't exist
                    try:
                        table.put_item(
                            Item={
                                'pk': 'COUNTERS',
                                'sk': 'USER',
                                'value': cls.DEFAULT_START_NUMBER - 1,
                                'created_at': datetime.utcnow().isoformat()
                            },
                            ConditionExpression='attribute_not_exists(pk)'
                        )
                        time.sleep(0.1)
                        continue
                    except:
                        pass
        
        # Fallback
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        return {
            "user_id": f"{cls.ID_PREFIX}T{timestamp}",
            "user_number": f"T{timestamp}",
            "numeric_number": timestamp
        }
    
    @classmethod
    def get_current_counter(cls) -> Dict[str, Any]:
        """Get current counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        try:
            response = table.get_item(
                Key={'pk': 'COUNTERS', 'sk': 'USER'}
            )
            
            if 'Item' in response:
                current = response['Item'].get('value', cls.DEFAULT_START_NUMBER - 1)
                return {
                    "current_value": current,
                    "next_id": cls._format_user_id(current + 1)
                }
        except:
            pass
        
        return {
            "current_value": cls.DEFAULT_START_NUMBER - 1,
            "next_id": cls._format_user_id(cls.DEFAULT_START_NUMBER)
        }
    
    @classmethod
    def set_counter_value(cls, value: int):
        """Manually set counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        table.update_item(
            Key={'pk': 'COUNTERS', 'sk': 'USER'},
            UpdateExpression='SET #value = :val',
            ExpressionAttributeNames={'#value': 'value'},
            ExpressionAttributeValues={':val': value}
        )
    
    @classmethod
    def initialize_counter(cls, start_value: int = None):
        """Initialize counter"""
        if start_value is None:
            start_value = cls.DEFAULT_START_NUMBER - 1
        
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        try:
            table.put_item(
                Item={
                    'pk': 'COUNTERS',
                    'sk': 'USER',
                    'value': start_value,
                    'created_at': datetime.utcnow().isoformat()
                },
                ConditionExpression='attribute_not_exists(pk)'
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print("User counter already exists")
    
    # ============= TEMPLATE METHODS =============
    
    @classmethod
    def create_user(cls, user_data: Dict[str, Any]) -> 'User':
        """
        Create user from data
        
        Args:
            user_data: Dictionary with user fields
        
        Returns: User instance (not saved yet)
        """
        # Get next ID
        id_info = cls._get_next_user_id()
        user_id = id_info["user_id"]
        user_number = id_info["user_number"]
        
        # Set PK/SK
        pk = "users"
        sk = user_id
        
        # Prepare data
        user_data_with_ids = {
            "pk": pk,
            "sk": sk,
            "user_id": user_id,
            "user_number": user_number,
            **user_data
        }
        
        # Create instance
        return cls(**user_data_with_ids)
    
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['User']:
        """
        Get user by ID
        
        Args:
            user_id: "USER-001" format
        
        Returns: User or None
        """
        try:
            return cls.get("users", user_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """
        Get user by email (scan - for small datasets)
        
        Args:
            email: Email address
        
        Returns: User or None
        """
        for user in cls.scan(cls.email == email):
            return user
        return None
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """
        Get user by username
        
        Args:
            username: Username
        
        Returns: User or None
        """
        for user in cls.scan(cls.username == username):
            return user
        return None
    
    @classmethod
    def get_all_users(cls, limit: int = 100) -> List['User']:
        """
        Get all users
        
        Args:
            limit: Maximum number to return
        
        Returns: List of users
        """
        return list(cls.query("users", limit=limit))
    
    @classmethod
    def get_active_users(cls) -> List['User']:
        """Get all active, non-deleted users"""
        users = []
        for user in cls.query("users"):
            if user.status == "active" and not user.isDeleted:
                users.append(user)
        return users
    
    @classmethod
    def get_by_role(cls, role: str) -> List['User']:
        """Get users by role"""
        users = []
        for user in cls.query("users"):
            if user.role == role and not user.isDeleted:
                users.append(user)
        return users
    
    def save(self, *args, **kwargs):
        """Override save to update last_updated timestamp"""
        self.last_updated = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    def record_login(self):
        """Record user login"""
        self.last_login = datetime.utcnow()
        self.save()
    
    def verify_email(self):
        """Mark email as verified"""
        self.email_verified = True
        self.email_verified_at = datetime.utcnow()
        self.save()
    
    def set_password(self, hashed_password: str):
        """Set password"""
        self.password = hashed_password
        self.save()
    
    def update_role(self, new_role: str):
        """Update user role"""
        valid_roles = ["user", "admin", "manager", "staff", "support"]
        if new_role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")
        
        self.role = new_role
        self.save()
    
    def update_status(self, new_status: str):
        """Update user status"""
        valid_statuses = ["active", "inactive", "suspended", "pending"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        self.status = new_status
        self.save()
    
    def soft_delete(self):
        """Soft delete user"""
        self.isDeleted = True
        self.status = "inactive"
        self.save()
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary for API response
        
        Args:
            include_sensitive: Include sensitive fields like password
        
        Returns: Dictionary representation
        """
        data = {
            'user_id': self.user_id,
            'user_number': self.user_number,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'status': self.status,
            'isDeleted': self.isDeleted,
            'email_verified': self.email_verified,
        }
        
        # Add dates
        if self.date_created:
            data['date_created'] = self.date_created.isoformat()
        if self.last_updated:
            data['last_updated'] = self.last_updated.isoformat()
        if self.last_login:
            data['last_login'] = self.last_login.isoformat()
        if self.email_verified_at:
            data['email_verified_at'] = self.email_verified_at.isoformat()
        
        # Add sensitive fields if requested
        if include_sensitive:
            data['password'] = self.password  # Hashed password
        
        return data
    
    def authenticate(self, password_hash: str) -> bool:
        """
        Authenticate user by comparing password hashes
        
        Args:
            password_hash: Hashed password to compare
        
        Returns: True if authentication successful
        """
        if not self.password:
            return False
        
        # In production, use proper password hashing library (bcrypt, argon2, etc.)
        return self.password == password_hash


# ============= FACTORY CLASS =============
class UserFactory:
    """
    Factory for creating users
    """
    
    @staticmethod
    def create_admin_user(email: str, password_hash: str, 
                         full_name: str = None) -> User:
        """
        Create admin user
        
        Args:
            email: Email address
            password_hash: Hashed password
            full_name: Full name (optional)
        
        Returns: User instance
        """
        username = email.split('@')[0] if '@' in email else email
        
        user = User.create_user({
            "username": username,
            "email": email,
            "full_name": full_name,
            "role": "admin",
            "status": "active"
        })
        
        user.set_password(password_hash)
        return user
    
    @staticmethod
    def create_regular_user(email: str, password_hash: str,
                           full_name: str = None, username: str = None) -> User:
        """
        Create regular user
        
        Args:
            email: Email address
            password_hash: Hashed password
            full_name: Full name (optional)
            username: Username (optional, defaults to email prefix)
        
        Returns: User instance
        """
        if not username and '@' in email:
            username = email.split('@')[0]
        
        user = User.create_user({
            "username": username,
            "email": email,
            "full_name": full_name,
            "role": "user",
            "status": "active"
        })
        
        user.set_password(password_hash)
        return user
    
    @staticmethod
    def create_staff_user(email: str, password_hash: str,
                         full_name: str, role: str = "staff") -> User:
        """
        Create staff user (manager, support, etc.)
        
        Args:
            email: Email address
            password_hash: Hashed password
            full_name: Full name
            role: "staff", "manager", "support" (default: "staff")
        
        Returns: User instance
        """
        username = email.split('@')[0] if '@' in email else email
        
        user = User.create_user({
            "username": username,
            "email": email,
            "full_name": full_name,
            "role": role,
            "status": "active"
        })
        
        user.set_password(password_hash)
        return user


# ============= GLOBAL SECONDARY INDEXES =============
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

class EmailIndex(GlobalSecondaryIndex):
    """GSI for querying by email"""
    class Meta:
        index_name = 'user-email-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    email = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute(range_key=True)


class UsernameIndex(GlobalSecondaryIndex):
    """GSI for querying by username"""
    class Meta:
        index_name = 'user-username-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    username = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute(range_key=True)


class RoleIndex(GlobalSecondaryIndex):
    """GSI for querying by role"""
    class Meta:
        index_name = 'user-role-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    role = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute(range_key=True)


# To use GSIs, add to User class:
# email_index = EmailIndex()
# username_index = UsernameIndex()
# role_index = RoleIndex()


# ============= USAGE EXAMPLES =============
if __name__ == "__main__":
    print("User Model (Exact ERD Specification) Ready!")
    print("=" * 60)
    
    # Initialize table and counter
    if not User.exists():
        User.create_table(wait=True)
        print("Table created successfully")
        User.initialize_counter()
        print("Counter initialized")
    
    # Check counter status
    counter = User.get_current_counter()
    print(f"Next user ID will be: {counter['next_id']}")
    
    # Example 1: Create admin user
    print("\n1. Creating admin user:")
    
    admin_user = UserFactory.create_admin_user(
        email="admin@example.com",
        password_hash="$2b$12$...hashedpassword...",  # Use proper hashing
        full_name="System Administrator"
    )
    admin_user.save()
    
    print(f"Created: {admin_user.user_id}")
    print(f"Email: {admin_user.email}")
    print(f"Role: {admin_user.role}")
    print(f"Status: {admin_user.status}")
    
    # Example 2: Create regular user
    print("\n2. Creating regular user:")
    
    regular_user = UserFactory.create_regular_user(
        email="john.doe@example.com",
        password_hash="$2b$12$...hashedpassword...",
        full_name="John Doe",
        username="johndoe"
    )
    regular_user.save()
    
    print(f"Created: {regular_user.user_id}")
    print(f"Username: {regular_user.username}")
    print(f"Email verified: {regular_user.email_verified}")
    
    # Example 3: Record login and verify email
    print("\n3. Recording login and verifying email:")
    regular_user.record_login()
    regular_user.verify_email()
    
    print(f"Last login: {regular_user.last_login}")
    print(f"Email verified at: {regular_user.email_verified_at}")
    
    # Example 4: Retrieve user
    print("\n4. Retrieving user:")
    retrieved = User.get_by_id(admin_user.user_id)
    if retrieved:
        print(f"Found: {retrieved.full_name}")
        print(f"Data: {retrieved.to_dict().keys()}")
    
    # Example 5: Get users by role
    print("\n5. Getting admin users:")
    admins = User.get_by_role("admin")
    print(f"Found {len(admins)} admin users")
    
    # Example 6: Authenticate user
    print("\n6. Authenticating user:")
    # In real scenario, you'd hash the provided password first
    is_authenticated = regular_user.authenticate("$2b$12$...hashedpassword...")
    print(f"Authentication successful: {is_authenticated}")
    
    # Example 7: Update user role
    print("\n7. Updating user role:")
    regular_user.update_role("manager")
    print(f"New role: {regular_user.role}")
    
    # Example 8: Get all users
    print("\n8. All users:")
    users = User.get_all_users()
    for user in users:
        print(f"  - {user.user_id}: {user.username} ({user.role})")
    
    # Example 9: Soft delete user
    print("\n9. Soft deleting user:")
    regular_user.soft_delete()
    print(f"isDeleted: {regular_user.isDeleted}")
    print(f"Status: {regular_user.status}")
    
    # Example 10: Get only active users
    print("\n10. Active users (should exclude deleted):")
    active_users = User.get_active_users()
    print(f"Active users count: {len(active_users)}")
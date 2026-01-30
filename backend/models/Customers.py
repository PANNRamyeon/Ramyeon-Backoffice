"""
Customer Model - Following Exact ERD Specification
PK = "customers", SK = "CUST-####"
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, 
    BooleanAttribute, UTCDateTimeAttribute,
    JSONAttribute, ListAttribute, MapAttribute
)
from datetime import datetime
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, List
import time


class AuthProvider(MapAttribute):
    """
    Authentication provider details
    For OAuth providers like Google, Facebook, etc.
    """
    provider = UnicodeAttribute()  # "google", "facebook", "github"
    provider_user_id = UnicodeAttribute()  # User ID from provider
    email = UnicodeAttribute(null=True)  # Email from provider
    full_name = UnicodeAttribute(null=True)  # Full name from provider
    first_name = UnicodeAttribute(null=True)  # First name from provider
    last_name = UnicodeAttribute(null=True)  # Last name from provider
    avatar_url = UnicodeAttribute(null=True)  # Avatar URL from provider
    locale = UnicodeAttribute(null=True)  # Locale from provider
    last_login = UnicodeAttribute(null=True)  # Last login timestamp from provider


class Customer(Model):
    """
    CUSTOMER MODEL - Following Exact ERD Specification
    
    PK/SK Pattern:
    - PK: "customers" (table name/entity type)
    - SK: "CUST-####" (4-digit auto-increment: 0001, 0002, etc.)
    
    Attributes as per ERD with exact data types
    """
    
    class Meta:
        table_name = os.environ.get('CUSTOMER_TABLE_NAME', 'Customers')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        if os.environ.get('DYNAMODB_LOCAL', 'false').lower() == 'true':
            host = os.environ.get('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')
        read_capacity_units = 10
        write_capacity_units = 10
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True)   # Partition Key: "customers"
    sk = UnicodeAttribute(range_key=True)  # Sort Key: "CUST-0001"
    
    # ============= CUSTOMER DATA (EXACT ERD FIELDS) =============
    
    # Customer ID (derived from SK, but stored for easy access)
    customer_id = UnicodeAttribute()  # "CUST-0001"
    customer_number = NumberAttribute()  # 1, 2, 3, etc.
    
    # Personal Information
    username = UnicodeAttribute(null=True)  # string
    full_name = UnicodeAttribute(null=True)  # string
    email = UnicodeAttribute(null=True)  # string
    email_verified = BooleanAttribute(default=False)  # boolean
    
    # Authentication
    password = UnicodeAttribute(null=True)  # string (hashed password)
    password_set = BooleanAttribute(default=False)  # boolean
    auth_mode = UnicodeAttribute(default="email_password")  # string
    
    # Authentication Providers (array)
    auth_providers = ListAttribute(of=AuthProvider, null=True)
    
    # Contact
    phone_number = UnicodeAttribute(null=True)  # string
    
    # Loyalty
    loyalty_points = NumberAttribute(default=0.0)  # float
    
    # Activity
    last_purchase = UTCDateTimeAttribute(null=True)  # ISODATE
    
    # Status
    isDeleted = BooleanAttribute(default=False)  # boolean (keeping ERD casing)
    status = UnicodeAttribute(default="active")  # string
    
    # Audit
    date_created = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    source = UnicodeAttribute(null=True)  # string
    
    # ============= COUNTER CONFIGURATION =============
    ID_PREFIX = "CUST-"
    DIGITS = 4
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
    def _format_customer_id(cls, number: int) -> str:
        """Format customer ID with prefix and 4 digits"""
        return f"{cls.ID_PREFIX}{number:0{cls.DIGITS}d}"
    
    @classmethod
    def _get_next_customer_id(cls) -> Dict[str, Any]:
        """
        Get next auto-incrementing customer ID (thread-safe)
        Returns: {"customer_id": "CUST-0001", "customer_number": 1}
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
                        'sk': 'CUSTOMER'
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
                customer_id = cls._format_customer_id(new_number)
                
                return {
                    "customer_id": customer_id,
                    "customer_number": new_number
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
                                'sk': 'CUSTOMER',
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
            "customer_id": f"{cls.ID_PREFIX}T{timestamp}",
            "customer_number": timestamp
        }
    
    @classmethod
    def get_current_counter(cls) -> Dict[str, Any]:
        """Get current counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        try:
            response = table.get_item(
                Key={'pk': 'COUNTERS', 'sk': 'CUSTOMER'}
            )
            
            if 'Item' in response:
                current = response['Item'].get('value', cls.DEFAULT_START_NUMBER - 1)
                return {
                    "current_value": current,
                    "next_id": cls._format_customer_id(current + 1)
                }
        except:
            pass
        
        return {
            "current_value": cls.DEFAULT_START_NUMBER - 1,
            "next_id": cls._format_customer_id(cls.DEFAULT_START_NUMBER)
        }
    
    @classmethod
    def set_counter_value(cls, value: int):
        """Manually set counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        table.update_item(
            Key={'pk': 'COUNTERS', 'sk': 'CUSTOMER'},
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
                    'sk': 'CUSTOMER',
                    'value': start_value,
                    'created_at': datetime.utcnow().isoformat()
                },
                ConditionExpression='attribute_not_exists(pk)'
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print("Counter already exists")
    
    # ============= TEMPLATE METHODS =============
    
    @classmethod
    def create_customer(cls, customer_data: Dict[str, Any]) -> 'Customer':
        """
        Create customer from data
        
        Args:
            customer_data: Dictionary with customer fields
        
        Returns: Customer instance (not saved yet)
        """
        # Get next ID
        id_info = cls._get_next_customer_id()
        customer_id = id_info["customer_id"]
        customer_number = id_info["customer_number"]
        
        # Set PK/SK
        pk = "customers"
        sk = customer_id
        
        # Prepare data
        customer_data_with_ids = {
            "pk": pk,
            "sk": sk,
            "customer_id": customer_id,
            "customer_number": customer_number,
            **customer_data
        }
        
        # Create instance
        return cls(**customer_data_with_ids)
    
    @classmethod
    def get_by_id(cls, customer_id: str) -> Optional['Customer']:
        """
        Get customer by ID
        
        Args:
            customer_id: "CUST-0001" format
        
        Returns: Customer or None
        """
        try:
            return cls.get("customers", customer_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['Customer']:
        """
        Get customer by email (scan - for small datasets)
        
        Args:
            email: Email address
        
        Returns: Customer or None
        """
        for customer in cls.scan(cls.email == email):
            return customer
        return None
    
    @classmethod
    def get_all_customers(cls, limit: int = 100) -> List['Customer']:
        """
        Get all customers
        
        Args:
            limit: Maximum number to return
        
        Returns: List of customers
        """
        return list(cls.query("customers", limit=limit))
    
    def save(self, *args, **kwargs):
        """Override save to update timestamps"""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    def add_auth_provider(self, provider_data: Dict[str, Any]):
        """
        Add authentication provider
        
        Args:
            provider_data: Dictionary with provider fields
        """
        if not self.auth_providers:
            self.auth_providers = []
        
        # Check if provider already exists
        for provider in self.auth_providers:
            if provider.provider == provider_data.get('provider'):
                # Update existing
                for key, value in provider_data.items():
                    if hasattr(provider, key):
                        setattr(provider, key, value)
                self.save()
                return
        
        # Add new provider
        provider = AuthProvider(**provider_data)
        self.auth_providers.append(provider)
        self.save()
    
    def record_purchase(self, amount: float = None):
        """Record customer purchase"""
        self.last_purchase = datetime.utcnow()
        if amount:
            self.loyalty_points += amount * 0.01  # Example: 1% of purchase as points
        self.save()
    
    def verify_email(self):
        """Mark email as verified"""
        self.email_verified = True
        self.save()
    
    def set_password(self, hashed_password: str):
        """Set password"""
        self.password = hashed_password
        self.password_set = True
        self.save()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API response
        
        Returns: Dictionary representation
        """
        data = {
            'customer_id': self.customer_id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'email_verified': self.email_verified,
            'password_set': self.password_set,
            'auth_mode': self.auth_mode,
            'phone_number': self.phone_number,
            'loyalty_points': float(self.loyalty_points) if self.loyalty_points else 0.0,
            'isDeleted': self.isDeleted,
            'status': self.status,
            'source': self.source,
        }
        
        # Add dates
        if self.date_created:
            data['date_created'] = self.date_created.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        if self.last_purchase:
            data['last_purchase'] = self.last_purchase.isoformat()
        
        # Add auth providers
        if self.auth_providers:
            data['auth_providers'] = [
                {
                    'provider': provider.provider,
                    'provider_user_id': provider.provider_user_id,
                    'email': provider.email,
                    'full_name': provider.full_name,
                    'first_name': provider.first_name,
                    'last_name': provider.last_name,
                    'avatar_url': provider.avatar_url,
                    'locale': provider.locale,
                    'last_login': provider.last_login
                }
                for provider in self.auth_providers
            ]
        
        return data


# ============= FACTORY CLASS =============
class CustomerFactory:
    """
    Factory for creating customers
    """
    
    @staticmethod
    def create_email_password_customer(email: str, password_hash: str, 
                                      full_name: str = None) -> Customer:
        """
        Create customer with email/password auth
        
        Args:
            email: Email address
            password_hash: Hashed password
            full_name: Full name (optional)
        
        Returns: Customer instance
        """
        customer = Customer.create_customer({
            "email": email,
            "full_name": full_name,
            "auth_mode": "email_password"
        })
        
        customer.set_password(password_hash)
        return customer
    
    @staticmethod
    def create_oauth_customer(provider: str, provider_user_id: str,
                             email: str = None, full_name: str = None,
                             first_name: str = None, last_name: str = None,
                             avatar_url: str = None) -> Customer:
        """
        Create customer from OAuth provider
        
        Args:
            provider: "google", "facebook", etc.
            provider_user_id: Provider's user ID
            email: Email from provider
            full_name: Full name from provider
            first_name: First name from provider
            last_name: Last name from provider
            avatar_url: Avatar URL from provider
        
        Returns: Customer instance
        """
        customer = Customer.create_customer({
            "email": email,
            "full_name": full_name,
            "auth_mode": "oauth",
            "email_verified": True  # OAuth emails are usually verified
        })
        
        customer.add_auth_provider({
            "provider": provider,
            "provider_user_id": provider_user_id,
            "email": email,
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "avatar_url": avatar_url,
            "last_login": datetime.utcnow().isoformat()
        })
        
        return customer


# ============= GLOBAL SECONDARY INDEXES =============
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

class EmailIndex(GlobalSecondaryIndex):
    """GSI for querying by email"""
    class Meta:
        index_name = 'customer-email-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    email = UnicodeAttribute(hash_key=True)
    customer_id = UnicodeAttribute(range_key=True)


# Add to Customer class if needed:
# email_index = EmailIndex()


# ============= USAGE EXAMPLES =============
if __name__ == "__main__":
    print("Customer Model (Exact ERD Specification) Ready!")
    print("=" * 60)
    
    # Initialize table and counter
    if not Customer.exists():
        Customer.create_table(wait=True)
        print("Table created successfully")
        Customer.initialize_counter()
        print("Counter initialized")
    
    # Check counter status
    counter = Customer.get_current_counter()
    print(f"Next customer ID will be: {counter['next_id']}")
    
    # Example 1: Create email/password customer
    print("\n1. Creating email/password customer:")
    
    customer1 = CustomerFactory.create_email_password_customer(
        email="john.doe@example.com",
        password_hash="$2b$12$...hashedpassword...",  # Use proper hashing in production
        full_name="John Doe"
    )
    customer1.save()
    
    print(f"Created: {customer1.customer_id}")
    print(f"Email: {customer1.email}")
    print(f"Auth mode: {customer1.auth_mode}")
    print(f"Password set: {customer1.password_set}")
    
    # Example 2: Create OAuth customer
    print("\n2. Creating OAuth customer:")
    
    customer2 = CustomerFactory.create_oauth_customer(
        provider="google",
        provider_user_id="google_123456789",
        email="alice@gmail.com",
        full_name="Alice Smith",
        first_name="Alice",
        last_name="Smith",
        avatar_url="https://lh3.googleusercontent.com/photo.jpg"
    )
    customer2.save()
    
    print(f"Created: {customer2.customer_id}")
    print(f"Email: {customer2.email}")
    print(f"Auth providers: {len(customer2.auth_providers)}")
    
    # Example 3: Record purchase
    print("\n3. Recording purchase:")
    customer1.record_purchase(100.0)
    print(f"Loyalty points: {customer1.loyalty_points}")
    print(f"Last purchase: {customer1.last_purchase}")
    
    # Example 4: Retrieve customer
    print("\n4. Retrieving customer:")
    retrieved = Customer.get_by_id(customer1.customer_id)
    if retrieved:
        print(f"Found: {retrieved.full_name}")
        print(f"Data: {retrieved.to_dict().keys()}")
    
    # Example 5: Get all customers
    print("\n5. All customers:")
    customers = Customer.get_all_customers()
    for cust in customers:
        print(f"  - {cust.customer_id}: {cust.email}")
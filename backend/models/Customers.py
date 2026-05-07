"""
Customer Model - Following ERD Specification
PK = "customers", SK = "CUST-####" (4-digit format)
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UTCDateTimeAttribute, UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST
from datetime import datetime
import re
import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class LenientUTCDateTimeAttribute(UTCDateTimeAttribute):
    """
    A UTCDateTimeAttribute that returns None if deserialization fails,
    instead of raising an exception.
    """
    def deserialize(self, value):
        try:
            return super().deserialize(value)
        except Exception as e:
            logger.error(f"Failed to deserialize datetime '{value}': {e}. Returning None.")
            return None
        
class LenientNumberAttribute(NumberAttribute):
    """
    A NumberAttribute that returns 0.0 if deserialization fails.
    """
    def deserialize(self, value):
        try:
            return super().deserialize(value)
        except Exception as e:
            logger.error(f"Failed to deserialize number '{value}': {e}. Returning 0.0.")
            return 0.0

# ============= NESTED MAP ATTRIBUTES =============
class AuthProvider(MapAttribute):
    """
    Authentication provider details
    """
    provider = UnicodeAttribute()  # google, facebook, github, apple
    provider_user_id = UnicodeAttribute()
    email = UnicodeAttribute(null=True)
    full_name = UnicodeAttribute(null=True)
    first_name = UnicodeAttribute(null=True)
    last_name = UnicodeAttribute(null=True)
    avatar_url = UnicodeAttribute(null=True)
    locale = UnicodeAttribute(null=True)
    last_login = LenientUTCDateTimeAttribute(null=True)  # Changed to LenientUTCDateTimeAttribute


# ============= GLOBAL SECONDARY INDEXES =============
class EmailIndex(GlobalSecondaryIndex):
    """
    GSI for querying customers by email (essential for login)
    """
    class Meta:
        index_name = 'customer-email-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    email = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True, attr_name="SK")


class StatusIndex(GlobalSecondaryIndex):
    """
    GSI for querying customers by status
    """
    class Meta:
        index_name = 'customer-status-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    status = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True, attr_name="SK")



# ============= MAIN CUSTOMER MODEL =============
class Customer(Model):
    """
    CUSTOMER MODEL - Following ERD with Enhanced Security
    
    ERD Fields:
    - PK = customers
    - SK = CUST-#### (4-digit)
    - username (string)
    - full_name (string)
    - email (string)
    - email_verified (boolean)
    - password (string)
    - password_set (boolean)
    - auth_mode (string)
    - auth_providers (array)
    - phone_number (string)
    - loyalty_points (float)
    - last_purchase (ISODATE)
    - isDeleted (boolean)
    - status (string)
    - date_created (ISODATE)
    - updated_at (ISODATE)
    - source (string)
    
    Enhanced with:
    - password_last_changed (ISODATE) - for password security
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION

        # Log the actual config (using os.getenv for local flag)
        logger.info(f"Customer model config: DYNAMODB_LOCAL={os.getenv('DYNAMODB_LOCAL', 'false')}, "
                    f"DYNAMODB_LOCAL_HOST={os.getenv('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')}, "
                    f"table={DYNAMO_TABLE_NAME}, region={AWS_REGION}")

        if os.getenv('DYNAMODB_LOCAL', 'false').lower() == 'true':
            host = os.getenv('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')

        read_capacity_units = 10
        write_capacity_units = 10

    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="customers")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "CUST-0001" (4-digit)
    
    # ============= GSI DEFINITIONS =============
    email_index = EmailIndex()
    status_index = StatusIndex()
    
    # ============= PERSONAL INFORMATION =============
    username = UnicodeAttribute(null=True)
    full_name = UnicodeAttribute(null=True)
    email = UnicodeAttribute(null=True)
    email_verified = BooleanAttribute(default=False)
    
    # ============= AUTHENTICATION =============
    password = UnicodeAttribute(null=True)  # Hashed password
    password_set = BooleanAttribute(default=False)
    password_last_changed = LenientUTCDateTimeAttribute(null=True)   # Enhanced security
    auth_mode = UnicodeAttribute(default="email_password")  # email_password, oauth
    
    # ============= AUTH PROVIDERS =============
    auth_providers = ListAttribute(of=AuthProvider, null=True)
    
    # ============= CONTACT =============
    phone_number = UnicodeAttribute(null=True)
    
    # ============= LOYALTY =============
    loyalty_points = LenientNumberAttribute(default=0.0)
    
    # ============= ACTIVITY =============
    last_purchase = LenientUTCDateTimeAttribute(null=True)
    
    # ============= STATUS =============
    isDeleted = BooleanAttribute(default=False)  # ERD casing
    status = UnicodeAttribute(default="active")  # active, inactive, suspended, banned
    
    # ============= AUDIT =============
    date_created = LenientUTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = LenientUTCDateTimeAttribute(default_for_new=datetime.utcnow)
    source = UnicodeAttribute(null=True)  # web, mobile, pos, import, api
    
    # ============= VALIDATION METHODS =============
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format
        
        Args:
            email: Email address to validate
        
        Returns:
            bool: True if valid, False otherwise
        """
        if not email:
            return False
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_regex, email.strip()))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """
        Validate phone number format
        
        Args:
            phone: Phone number to validate
        
        Returns:
            bool: True if valid, False otherwise
        """
        if not phone:
            return False
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone.strip())
        
        # Check for valid lengths (7-15 digits is typical)
        return 7 <= len(digits) <= 15
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_with_password(cls, email: str, password_hash: str,
                           full_name: str = None, phone_number: str = None,
                           username: str = None, source: str = "web") -> 'Customer':
        """
        Create customer with email/password authentication
        
        Args:
            email: Customer email (required)
            password_hash: Hashed password
            full_name: Customer full name
            phone_number: Customer phone number
            username: Customer username
            source: Source of customer creation
        
        Returns:
            Customer: Created and saved customer instance
        
        Raises:
            ValueError: If email is invalid or customer already exists
        """
        try:
            # Validate email
            if not cls.validate_email(email):
                raise ValueError(f"Invalid email format: {email}")
            
            # Check for existing customer with this email
            existing = cls.get_by_email(email)
            if existing:
                raise ValueError(f"Customer with email {email} already exists")
            
            # Validate phone if provided
            if phone_number and not cls.validate_phone(phone_number):
                raise ValueError(f"Invalid phone number format: {phone_number}")
            
            sk = generate_sk('CUST', 'customer_seq', width=5)
            
            # Create customer
            customer = cls(
                pk="customers",
                sk=sk,
                email=email.lower().strip(),
                full_name=full_name.strip() if full_name else None,
                phone_number=phone_number.strip() if phone_number else None,
                username=username.strip() if username else None,
                source=source,
                status="active",
                isDeleted=False,
                auth_mode="email_password",
                date_created=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Set password
            customer.set_password(password_hash)
            
            logger.info(f"Customer created with password: {sk} - Email: {email}")
            return customer
            
        except Exception as e:
            logger.error(f"Failed to create customer with password: {str(e)}")
            raise
    
    @classmethod
    def create_with_oauth(cls, provider: str, provider_user_id: str,
                         email: str = None, full_name: str = None,
                         first_name: str = None, last_name: str = None,
                         avatar_url: str = None, locale: str = None,
                         source: str = "web") -> 'Customer':
        """
        Create customer from OAuth provider
        
        Args:
            provider: OAuth provider (google, facebook, github, apple)
            provider_user_id: User ID from provider
            email: Email from provider (required for OAuth)
            full_name: Full name from provider
            first_name: First name from provider
            last_name: Last name from provider
            avatar_url: Avatar URL from provider
            locale: Locale from provider
            source: Source of customer creation
        
        Returns:
            Customer: Created and saved customer instance
        
        Raises:
            ValueError: If email is invalid
        """
        try:
            # Email is required for OAuth (since login is required for checkout)
            if not email:
                raise ValueError("Email is required for OAuth authentication")
            
            # Validate email
            if not cls.validate_email(email):
                raise ValueError(f"Invalid email format from provider: {email}")
            
            # Check for existing customer with this email
            existing = cls.get_by_email(email)
            
            # If customer exists, add OAuth provider to existing account
            if existing:
                # Check if provider already exists
                for auth_provider in existing.auth_providers or []:
                    if (auth_provider.provider == provider and 
                        auth_provider.provider_user_id == provider_user_id):
                        # Update last login
                        auth_provider.last_login = datetime.utcnow()
                        existing.save()
                        logger.info(f"Updated OAuth provider {provider} for customer {existing.sk}")
                        return existing
                
                # Set auth_mode first so add_auth_provider's save() captures it
                existing.auth_mode = "oauth"
                existing.add_auth_provider({
                    "provider": provider,
                    "provider_user_id": provider_user_id,
                    "email": email,
                    "full_name": full_name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "avatar_url": avatar_url,
                    "locale": locale,
                    "last_login": datetime.utcnow()
                })
                
                logger.info(f"Added OAuth provider {provider} to existing customer {existing.sk}")
                return existing
            
            # Create new customer
            sk = generate_sk('CUST', 'customer_seq', width=5)
            
            customer = cls(
                pk="customers",
                sk=sk,
                email=email.lower().strip(),
                full_name=full_name.strip() if full_name else None,
                source=source,
                status="active",
                isDeleted=False,
                auth_mode="oauth",
                email_verified=True,  # OAuth emails are usually verified
                date_created=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Add OAuth provider
            customer.add_auth_provider({
                "provider": provider,
                "provider_user_id": provider_user_id,
                "email": email,
                "full_name": full_name,
                "first_name": first_name,
                "last_name": last_name,
                "avatar_url": avatar_url,
                "locale": locale,
                "last_login": datetime.utcnow()
            })
            
            customer.save()
            logger.info(f"Customer created with OAuth: {sk} - Email: {email} via {provider}")
            return customer
            
        except Exception as e:
            logger.error(f"Failed to create customer with OAuth: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, customer_id: str, include_deleted: bool = False) -> 'Customer | None':
        """
        Get customer by ID (SK)

        Args:
            customer_id: Format "CUST-00001" or just "00001"
            include_deleted: If True, returns soft-deleted customers too

        Returns:
            Customer or None if not found
        """
        try:
            # Ensure proper format
            if not customer_id.startswith('CUST-'):
                customer_id = f"CUST-{customer_id.zfill(5)}"

            customer = cls.get("customers", customer_id)
            if customer and customer.isDeleted and not include_deleted:
                return None
            return customer
        except cls.DoesNotExist:
            logger.warning(f"Customer not found: {customer_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching customer {customer_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_email(cls, email: str) -> 'Customer | None':
        """
        Get customer by email using GSI
        
        Args:
            email: Email address to search
        
        Returns:
            Customer or None if not found
        """
        try:
            if not email:
                return None
            
            # Query by email using GSI
            for customer in cls.email_index.query(email.lower()):
                if not customer.isDeleted:
                    return customer
            return None
        except Exception as e:
            logger.error(f"Error finding customer by email '{email}': {str(e)}")
            return None
    
    @classmethod
    def get_by_status(cls, status: str, include_deleted: bool = False) -> list:
        try:
            customers = []
            filter_cond = None if include_deleted else (cls.isDeleted == False)
            for customer in cls.status_index.query(status, filter_condition=filter_cond):
                customers.append(customer)
            return customers
        except Exception as e:
            logger.error(f"Error getting customers by status {status}: {str(e)}")
            return []
    
    @classmethod
    def get_active_customers(cls) -> list:
        """
        Get all active, non-deleted customers
        
        Returns:
            list: List of active customers
        """
        return cls.get_by_status("active")
    
    @classmethod
    def search_customers(cls, search_term: str, limit: int = 20) -> list:
        try:
            customers = []
            search_term_lower = search_term.lower()
            for customer in cls.query("customers", limit=1000):
                if customer.isDeleted:
                    continue
                try:
                    # Check name
                    if (customer.full_name and search_term_lower in customer.full_name.lower()) or \
                    (customer.username and search_term_lower in customer.username.lower()):
                        customers.append(customer)
                        if len(customers) >= limit:
                            break
                        continue
                    if customer.email and search_term_lower in customer.email.lower():
                        customers.append(customer)
                        if len(customers) >= limit:
                            break
                        continue
                    if customer.phone_number and search_term_lower in customer.phone_number.lower():
                        customers.append(customer)
                        if len(customers) >= limit:
                            break
                except Exception as e:
                    logger.error(f"Error processing customer {customer.sk}: {e}")
                    continue
            return customers
        except Exception as e:
            logger.error(f"Error searching customers: {str(e)}")
            return []
    
    @classmethod
    def get_all_customers(cls, limit: int = 1000) -> list:
        """
        Get all non-deleted customers using server-side filter.
        """
        try:
            customers = []
            for customer in cls.query(
                "customers",
                filter_condition=cls.isDeleted == False,
                limit=limit
            ):
                customers.append(customer)
            return customers
        except Exception as e:
            logger.error(f"Error getting all customers: {str(e)}")
            return []
        
    @classmethod
    # DEPRECATION NOTICE:
    # This classmethod scans all customers to find a matching OAuth provider.
    # It should be replaced by a service-layer method that uses a dedicated GSI
    # for efficient lookup. Kept temporarily to avoid breaking the OAuth flow;
    # coordinate with your partner before refactoring.
    def authenticate_oauth(cls, provider: str, provider_user_id: str, email: str = None) -> 'Customer | None':
        """
        Authenticate customer with OAuth provider
        
        Args:
            provider: OAuth provider
            provider_user_id: User ID from provider
            email: Email from provider (optional)
        
        Returns:
            Customer if authentication successful, None otherwise
        """
        try:
            # Try to find customer by email first
            if email:
                customer = cls.get_by_email(email)
                if customer:
                    # Check if this provider is linked to the customer
                    for auth_provider in customer.auth_providers or []:
                        if (auth_provider.provider == provider and 
                            auth_provider.provider_user_id == provider_user_id):
                            # Update last login
                            auth_provider.last_login = datetime.utcnow()
                            customer.updated_at = datetime.utcnow()
                            customer.save()
                            logger.info(f"Customer authenticated via OAuth: {customer.sk}")
                            return customer
            
            # If no email or not found by email, search all customers for matching provider
            for customer in cls.get_all_customers():
                if customer.auth_providers:
                    for auth_provider in customer.auth_providers:
                        if (auth_provider.provider == provider and 
                            auth_provider.provider_user_id == provider_user_id):
                            # Update last login
                            auth_provider.last_login = datetime.utcnow()
                            customer.updated_at = datetime.utcnow()
                            customer.save()
                            logger.info(f"Customer authenticated via OAuth: {customer.sk}")
                            return customer
            
            return None
            
        except Exception as e:
            logger.error(f"OAuth authentication error for {provider}: {str(e)}")
            return None
    
    # ============= INSTANCE METHODS =============
    
    def set_password(self, password_hash: str):
        """
        Set or update customer password
        
        Args:
            password_hash: Hashed password
        """
        try:
            self.password = password_hash
            self.password_set = True
            self.password_last_changed = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            self.save()
            logger.info(f"Password set/updated for customer {self.sk}")
        except Exception as e:
            logger.error(f"Failed to set password for customer {self.sk}: {str(e)}")
            raise
    
    def verify_email(self):
        """
        Mark customer email as verified
        """
        try:
            self.email_verified = True
            self.updated_at = datetime.utcnow()
            self.save()
            logger.info(f"Email verified for customer {self.sk}")
        except Exception as e:
            logger.error(f"Failed to verify email for customer {self.sk}: {str(e)}")
            raise
    
    def add_auth_provider(self, provider_data: Dict[str, Any]):
        """
        Add or update authentication provider
        
        Args:
            provider_data: Dictionary with provider fields
        """
        try:
            if not self.auth_providers:
                self.auth_providers = []
            
            provider_name = provider_data.get('provider')
            provider_user_id = provider_data.get('provider_user_id')
            
            # Check if provider already exists
            for i, provider in enumerate(self.auth_providers):
                if provider.provider == provider_name and provider.provider_user_id == provider_user_id:
                    # Update existing provider
                    for key, value in provider_data.items():
                        if hasattr(provider, key):
                            setattr(provider, key, value)
                    self.updated_at = datetime.utcnow()
                    self.save()
                    logger.info(f"Updated auth provider {provider_name} for customer {self.sk}")
                    return
            
            # Add new provider
            provider = AuthProvider(**provider_data)
            self.auth_providers.append(provider)
            self.updated_at = datetime.utcnow()
            self.save()
            logger.info(f"Added auth provider {provider_name} for customer {self.sk}")
            
        except Exception as e:
            logger.error(f"Failed to add auth provider for customer {self.sk}: {str(e)}")
            raise
    
    def record_purchase(self, amount: float, points_earned: float = None):
        """
        Record customer purchase
        
        Args:
            amount: Purchase amount
            points_earned: Optional points earned (defaults to 1% of amount)
        """
        try:
            self.last_purchase = datetime.utcnow()
            
            # Calculate points if not provided (1% of purchase amount)
            if points_earned is None:
                points_earned = amount * 0.01
            
            self.loyalty_points += points_earned
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Purchase recorded for customer {self.sk}: ${amount}, earned {points_earned} points")
            
        except Exception as e:
            logger.error(f"Failed to record purchase for customer {self.sk}: {str(e)}")
            raise
    
    def update_profile(self, full_name: str = None, phone_number: str = None,
                      username: str = None) -> 'Customer':
        """
        Update customer profile information
        
        Args:
            full_name: New full name
            phone_number: New phone number
            username: New username
        
        Returns:
            Updated customer instance
        """
        try:
            updated = False
            
            if full_name is not None:
                self.full_name = full_name.strip()
                updated = True
            
            if phone_number is not None:
                if phone_number and not self.validate_phone(phone_number):
                    raise ValueError(f"Invalid phone number format: {phone_number}")
                self.phone_number = phone_number.strip() if phone_number else None
                updated = True
            
            if username is not None:
                self.username = username.strip()
                updated = True
            
            if updated:
                self.updated_at = datetime.utcnow()
                self.save()
                logger.info(f"Profile updated for customer {self.sk}")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to update profile for customer {self.sk}: {str(e)}")
            raise
    
    def update_email(self, new_email: str):
        """
        Update customer email address
        
        Args:
            new_email: New email address
        
        Raises:
            ValueError: If email is invalid or already in use
        """
        try:
            if not self.validate_email(new_email):
                raise ValueError(f"Invalid email format: {new_email}")
            
            # Check if email is already in use by another customer
            existing = self.get_by_email(new_email)
            if existing and existing.sk != self.sk:
                raise ValueError(f"Email {new_email} is already in use")
            
            self.email = new_email.lower().strip()
            self.email_verified = False  # Require re-verification
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Email updated for customer {self.sk}")
            
        except Exception as e:
            logger.error(f"Failed to update email for customer {self.sk}: {str(e)}")
            raise
    
    def add_loyalty_points(self, points: float, reason: str = None):
        """
        Add loyalty points to customer
        
        Args:
            points: Points to add
            reason: Reason for adding points
        """
        try:
            self.loyalty_points += points
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Added {points} loyalty points to customer {self.sk}" + 
                       (f" (reason: {reason})" if reason else ""))
            
        except Exception as e:
            logger.error(f"Failed to add loyalty points to customer {self.sk}: {str(e)}")
            raise
    
    def deduct_loyalty_points(self, points: float, reason: str = None):
        """
        Deduct loyalty points from customer
        
        Args:
            points: Points to deduct
            reason: Reason for deducting points
        
        Raises:
            ValueError: If insufficient points
        """
        try:
            if self.loyalty_points < points:
                raise ValueError(f"Insufficient loyalty points. Available: {self.loyalty_points}, Required: {points}")
            
            self.loyalty_points -= points
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Deducted {points} loyalty points from customer {self.sk}" + 
                       (f" (reason: {reason})" if reason else ""))
            
        except Exception as e:
            logger.error(f"Failed to deduct loyalty points from customer {self.sk}: {str(e)}")
            raise
    
    def activate(self):
        """Activate customer account"""
        self.status = "active"
        self.updated_at = datetime.utcnow()
        self.save()
        logger.info(f"Customer {self.sk} activated")
    
    def deactivate(self):
        """Deactivate customer account"""
        self.status = "inactive"
        self.updated_at = datetime.utcnow()
        self.save()
        logger.info(f"Customer {self.sk} deactivated")
    
    def suspend(self):
        """Suspend customer account"""
        self.status = "suspended"
        self.updated_at = datetime.utcnow()
        self.save()
        logger.info(f"Customer {self.sk} suspended")
    
    def ban(self):
        """Ban customer account"""
        self.status = "banned"
        self.updated_at = datetime.utcnow()
        self.save()
        logger.info(f"Customer {self.sk} banned")
    
    def soft_delete(self):
        """Soft delete customer account"""
        self.isDeleted = True
        self.status = "deleted"
        self.updated_at = datetime.utcnow()
        self.save()
        logger.info(f"Customer {self.sk} soft deleted")
    
    def restore(self):
        """Restore soft-deleted customer account"""
        self.isDeleted = False
        self.status = "active"
        self.updated_at = datetime.utcnow()
        self.save()
        logger.info(f"Customer {self.sk} restored")
    
    def get_summary(self) -> dict:
        """
        Get customer summary
        
        Returns:
            dict: Customer summary information
        """
        try:
                return {
                "customer_id": self.sk,
                "email": self.email,
                "full_name": self.full_name,
                "username": self.username,
                "email_verified": self.email_verified,
                "auth_mode": self.auth_mode,
                "phone_number": self.phone_number,
                "loyalty_points": float(self.loyalty_points) if self.loyalty_points else 0.0,
                "status": self.status,
                "isDeleted": self.isDeleted,
                "date_created": self.date_created.isoformat() if self.date_created else None,
                "last_purchase": self.last_purchase.isoformat() if self.last_purchase else None,
                "auth_providers_count": len(self.auth_providers) if self.auth_providers else 0,
                "source": self.source
            }
        except Exception as e:
            logger.error(f"Error getting summary for customer {self.sk}: {str(e)}")
            return {}
    
    def to_dict(self) -> dict:
        """
        Convert customer to dictionary for API response
        
        Returns:
            dict: Complete customer information
        """
        try:
            customer_dict = {
                "customer_id": self.sk,
                "username": self.username,
                "full_name": self.full_name,
                "email": self.email,
                "email_verified": self.email_verified,
                "password_set": self.password_set,
                "auth_mode": self.auth_mode,
                "phone_number": self.phone_number,
                "loyalty_points": float(self.loyalty_points) if self.loyalty_points else 0.0,
                "status": self.status,
                "isDeleted": self.isDeleted,
                "source": self.source,
                "date_created": self.date_created.isoformat() if self.date_created else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "last_purchase": self.last_purchase.isoformat() if self.last_purchase else None,
                "password_last_changed": self.password_last_changed.isoformat() if self.password_last_changed else None
            }

            if self.auth_providers:
                customer_dict["auth_providers"] = [
                    {
                        "provider": provider.provider,
                        "provider_user_id": provider.provider_user_id,
                        "email": provider.email,
                        "full_name": provider.full_name,
                        "first_name": provider.first_name,
                        "last_name": provider.last_name,
                        "avatar_url": provider.avatar_url,
                        "locale": provider.locale,
                        "last_login": provider.last_login.isoformat() if provider.last_login else None
                    }
                    for provider in self.auth_providers
                ]

            return customer_dict
        except Exception as e:
            logger.error(f"Error converting customer to dict: {str(e)}")
            return {}
    
    def save(self, condition=None, **kwargs):
        """Override save to update updated_at timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(condition=condition, **kwargs)


# ============= CUSTOMER MANAGER =============
class CustomerManager:
    """
    Manager class for customer-related operations
    """
    
    @staticmethod
    def get_customer_statistics():
        """
        Get customer statistics using a raw DynamoDB scan that bypasses
        PynamoDB deserialization issues.
        """
        import boto3
        from app.utils import DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST

        # Create boto3 client with the same configuration as the model
        client_kwargs = {'region_name': AWS_REGION}
        if DYNAMODB_LOCAL:
            client_kwargs['endpoint_url'] = DYNAMODB_LOCAL_HOST
            # Local DynamoDB uses dummy credentials
            client_kwargs.update({
                'aws_access_key_id': 'fake',
                'aws_secret_access_key': 'fake'
            })

        dynamodb = boto3.resource('dynamodb', **client_kwargs)
        table = dynamodb.Table(DYNAMO_TABLE_NAME)

        from boto3.dynamodb.conditions import Key
        items = []
        last_key = None
        while True:
            query_kwargs = {
                'KeyConditionExpression': Key('PK').eq('customers')
            }
            if last_key:
                query_kwargs['ExclusiveStartKey'] = last_key
            try:
                response = table.query(**query_kwargs)
            except Exception as e:
                logger.error(f"DynamoDB query failed: {e}")
                return {}
            items.extend(response.get('Items', []))
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break

        # Initialize counters
        total_customers = 0
        status_counts = {"active": 0, "inactive": 0, "suspended": 0, "banned": 0}
        auth_mode_counts = {"email_password": 0, "oauth": 0}
        verified_count = 0
        total_loyalty_points = 0.0
        customers_with_points = 0

        for item in items:
            # Skip soft-deleted customers
            if item.get('isDeleted', False):
                continue

            total_customers += 1

            # Status
            status = item.get('status', 'active')
            status_counts[status] = status_counts.get(status, 0) + 1

            # Auth mode
            auth_mode = item.get('auth_mode', 'email_password')
            auth_mode_counts[auth_mode] = auth_mode_counts.get(auth_mode, 0) + 1

            # Email verified
            if item.get('email_verified', False):
                verified_count += 1

            # Loyalty points – safely attempt conversion
            points_raw = item.get('loyalty_points')
            if points_raw is not None:
                try:
                    # Handle both number (N) and string (S) types
                    if isinstance(points_raw, (int, float)):
                        points = float(points_raw)
                    elif isinstance(points_raw, str):
                        points = float(points_raw)
                    else:
                        continue
                    if points > 0:
                        total_loyalty_points += points
                        customers_with_points += 1
                except (ValueError, TypeError):
                    # Silently skip corrupted points
                    pass

        return {
            "total_customers": total_customers,
            "status_distribution": status_counts,
            "auth_mode_distribution": auth_mode_counts,
            "email_verified_percentage": (verified_count / total_customers * 100) if total_customers > 0 else 0,
            "total_loyalty_points": total_loyalty_points,
            "avg_loyalty_points": (total_loyalty_points / customers_with_points) if customers_with_points > 0 else 0,
            "customers_with_loyalty_points": customers_with_points
        }
        
    @staticmethod
    def get_top_loyalty_customers(limit: int = 10) -> list:
        """
        Get customers with highest loyalty points
        
        Args:
            limit: Number of customers to return
        
        Returns:
            list: Top customers by loyalty points
        """
        try:
            customers = Customer.get_active_customers()
            
            # Sort by loyalty points (descending)
            customers.sort(key=lambda x: x.loyalty_points, reverse=True)
            
            return customers[:limit]
        except Exception as e:
            logger.error(f"Error getting top loyalty customers: {str(e)}")
            return []
    
    @staticmethod
    def get_inactive_customers(days_threshold: int = 90) -> list:
        """
        Get customers who haven't made a purchase in X days
        
        Args:
            days_threshold: Number of days since last purchase
        
        Returns:
            list: Inactive customers
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
            inactive_customers = []
            
            for customer in Customer.get_active_customers():
                if not customer.last_purchase or customer.last_purchase < cutoff_date:
                    inactive_customers.append(customer)
            
            return inactive_customers
        except Exception as e:
            logger.error(f"Error getting inactive customers: {str(e)}")
            return []
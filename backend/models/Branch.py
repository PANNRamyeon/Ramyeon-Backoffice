"""
Branch Model - Following Exact ERD Specification
PK = "branches", SK = "BRAN-##"
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, 
    UTCDateTimeAttribute, JSONAttribute
)
from datetime import datetime
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, List
import time


class Branch(Model):
    """
    BRANCH MODEL - Following Exact ERD Specification
    
    PK/SK Pattern:
    - PK: "branches" (table name/entity type)
    - SK: "BRAN-##" (2-digit auto-increment: 01, 02, etc.)
    
    For tracking business branches/locations.
    """
    
    class Meta:
        table_name = os.environ.get('BRANCH_TABLE_NAME', 'Branches')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        if os.environ.get('DYNAMODB_LOCAL', 'false').lower() == 'true':
            host = os.environ.get('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True)   # Partition Key: "branches"
    sk = UnicodeAttribute(range_key=True)  # Sort Key: "BRAN-01"
    
    # ============= BRANCH DATA (EXACT ERD FIELDS) =============
    
    # Branch ID (derived from SK, but stored for easy access)
    branch_id = UnicodeAttribute()  # "BRAN-01"
    branch_number = UnicodeAttribute()  # "01" (string to preserve leading zeros)
    
    # Required field from ERD
    branch_name = UnicodeAttribute()  # String
    
    # ============= ADDITIONAL FIELDS (Not in ERD but practical) =============
    # We'll include these but make them optional/nullable
    
    # Contact Information
    address = UnicodeAttribute(null=True)  # String: Physical address
    phone_number = UnicodeAttribute(null=True)  # String
    email = UnicodeAttribute(null=True)  # String
    
    # Branch Details
    description = UnicodeAttribute(null=True)  # String
    branch_type = UnicodeAttribute(null=True)  # String: "main", "retail", "warehouse", "office"
    
    # Management
    manager_id = UnicodeAttribute(null=True)  # String: ID of branch manager
    manager_name = UnicodeAttribute(null=True)  # String: Name of branch manager
    
    # Status
    status = UnicodeAttribute(default="active")  # String: "active", "inactive", "closed", "under_maintenance"
    is_deleted = BooleanAttribute(default=False)  # Boolean
    
    # Operating Information
    opening_time = UnicodeAttribute(null=True)  # String: "09:00"
    closing_time = UnicodeAttribute(null=True)  # String: "18:00"
    timezone = UnicodeAttribute(null=True)  # String: "America/New_York"
    
    # Geolocation
    latitude = UnicodeAttribute(null=True)  # String: "40.7128"
    longitude = UnicodeAttribute(null=True)  # String: "-74.0060"
    
    # Metadata
    metadata = JSONAttribute(null=True)  # JSON: Additional configuration/data
    
    # Audit Trail
    date_created = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    last_updated = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    
    # ============= COUNTER CONFIGURATION =============
    ID_PREFIX = "BRAN-"
    DIGITS = 2  # 2-digit format: BRAN-01 to BRAN-99
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
    def _format_branch_id(cls, number: int) -> str:
        """Format branch ID with prefix and 2 digits"""
        return f"{cls.ID_PREFIX}{number:0{cls.DIGITS}d}"
    
    @classmethod
    def _get_next_branch_id(cls) -> Dict[str, Any]:
        """
        Get next auto-incrementing branch ID (thread-safe)
        Returns: {"branch_id": "BRAN-01", "branch_number": "01", "numeric_number": 1}
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
                        'sk': 'BRANCH'
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
                branch_id = cls._format_branch_id(new_number)
                branch_number_str = f"{new_number:0{cls.DIGITS}d}"
                
                return {
                    "branch_id": branch_id,
                    "branch_number": branch_number_str,
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
                                'sk': 'BRANCH',
                                'value': cls.DEFAULT_START_NUMBER - 1,
                                'created_at': datetime.utcnow().isoformat()
                            },
                            ConditionExpression='attribute_not_exists(pk)'
                        )
                        time.sleep(0.1)
                        continue
                    except:
                        pass
        
        # Fallback - use timestamp
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        return {
            "branch_id": f"{cls.ID_PREFIX}T{timestamp}",
            "branch_number": f"T{timestamp}",
            "numeric_number": timestamp
        }
    
    @classmethod
    def get_current_counter(cls) -> Dict[str, Any]:
        """Get current counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        try:
            response = table.get_item(
                Key={'pk': 'COUNTERS', 'sk': 'BRANCH'}
            )
            
            if 'Item' in response:
                current = response['Item'].get('value', cls.DEFAULT_START_NUMBER - 1)
                return {
                    "current_value": current,
                    "next_id": cls._format_branch_id(current + 1)
                }
        except:
            pass
        
        return {
            "current_value": cls.DEFAULT_START_NUMBER - 1,
            "next_id": cls._format_branch_id(cls.DEFAULT_START_NUMBER)
        }
    
    @classmethod
    def set_counter_value(cls, value: int):
        """Manually set counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        table.update_item(
            Key={'pk': 'COUNTERS', 'sk': 'BRANCH'},
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
                    'sk': 'BRANCH',
                    'value': start_value,
                    'created_at': datetime.utcnow().isoformat()
                },
                ConditionExpression='attribute_not_exists(pk)'
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print("Branch counter already exists")
    
    # ============= TEMPLATE METHODS =============
    
    @classmethod
    def create_branch(cls, branch_data: Dict[str, Any]) -> 'Branch':
        """
        Create branch from data
        
        Args:
            branch_data: Dictionary with branch fields (must include 'branch_name')
        
        Returns: Branch instance (not saved yet)
        
        Raises:
            ValueError: If branch_name is not provided
        """
        # Validate required field
        if 'branch_name' not in branch_data:
            raise ValueError("branch_name is required")
        
        # Get next ID
        id_info = cls._get_next_branch_id()
        branch_id = id_info["branch_id"]
        branch_number = id_info["branch_number"]
        
        # Set PK/SK
        pk = "branches"
        sk = branch_id
        
        # Prepare data
        branch_data_with_ids = {
            "pk": pk,
            "sk": sk,
            "branch_id": branch_id,
            "branch_number": branch_number,
            **branch_data
        }
        
        # Create instance
        return cls(**branch_data_with_ids)
    
    @classmethod
    def get_by_id(cls, branch_id: str) -> Optional['Branch']:
        """
        Get branch by ID
        
        Args:
            branch_id: "BRAN-01" format
        
        Returns: Branch or None
        """
        try:
            return cls.get("branches", branch_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_by_name(cls, branch_name: str) -> Optional['Branch']:
        """
        Get branch by name (exact match)
        
        Args:
            branch_name: Branch name to search for
        
        Returns: Branch or None
        """
        for branch in cls.scan(cls.branch_name == branch_name):
            return branch
        return None
    
    @classmethod
    def search_by_name(cls, search_term: str, limit: int = 10) -> List['Branch']:
        """
        Search branches by name (partial match)
        
        Args:
            search_term: Search term (case-insensitive)
            limit: Maximum number of branches to return
        
        Returns: List of matching branches
        """
        branches = []
        search_term_lower = search_term.lower()
        
        for branch in cls.scan(cls.is_deleted == False, limit=100):  # Scan with limit
            if search_term_lower in branch.branch_name.lower():
                branches.append(branch)
                if len(branches) >= limit:
                    break
        
        return branches
    
    @classmethod
    def get_all_branches(cls, limit: int = 100) -> List['Branch']:
        """
        Get all branches
        
        Args:
            limit: Maximum number of branches to return
        
        Returns: List of branches
        """
        return list(cls.query("branches", limit=limit))
    
    @classmethod
    def get_active_branches(cls) -> List['Branch']:
        """
        Get all active, non-deleted branches
        
        Returns: List of active branches
        """
        branches = []
        for branch in cls.query("branches"):
            if branch.status == "active" and not branch.is_deleted:
                branches.append(branch)
        return branches
    
    @classmethod
    def get_branches_by_type(cls, branch_type: str) -> List['Branch']:
        """
        Get branches by type
        
        Args:
            branch_type: Type of branch to filter by
        
        Returns: List of branches of specified type
        """
        branches = []
        for branch in cls.query("branches"):
            if branch.branch_type == branch_type and not branch.is_deleted:
                branches.append(branch)
        return branches
    
    def save(self, *args, **kwargs):
        """Override save to update last_updated timestamp"""
        self.last_updated = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    def update_branch(self, update_data: Dict[str, Any]) -> 'Branch':
        """
        Update branch with provided data
        
        Args:
            update_data: Dictionary with fields to update
        
        Returns: Updated Branch instance
        """
        for key, value in update_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.save()
        return self
    
    def set_status(self, new_status: str) -> 'Branch':
        """
        Update branch status
        
        Args:
            new_status: New status value
        
        Returns: Updated Branch instance
        """
        valid_statuses = ["active", "inactive", "closed", "under_maintenance"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        self.status = new_status
        self.save()
        return self
    
    def soft_delete(self):
        """Soft delete branch"""
        self.is_deleted = True
        self.status = "closed"
        self.save()
    
    def set_manager(self, manager_id: str, manager_name: str = None) -> 'Branch':
        """
        Set branch manager
        
        Args:
            manager_id: ID of the manager
            manager_name: Name of the manager (optional)
        
        Returns: Updated Branch instance
        """
        self.manager_id = manager_id
        if manager_name:
            self.manager_name = manager_name
        self.save()
        return self
    
    def set_location(self, latitude: str, longitude: str) -> 'Branch':
        """
        Set branch geolocation
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
        
        Returns: Updated Branch instance
        """
        self.latitude = latitude
        self.longitude = longitude
        self.save()
        return self
    
    def set_operating_hours(self, opening_time: str, closing_time: str, 
                           timezone: str = None) -> 'Branch':
        """
        Set branch operating hours
        
        Args:
            opening_time: Opening time (e.g., "09:00")
            closing_time: Closing time (e.g., "18:00")
            timezone: Timezone (e.g., "America/New_York")
        
        Returns: Updated Branch instance
        """
        self.opening_time = opening_time
        self.closing_time = closing_time
        if timezone:
            self.timezone = timezone
        self.save()
        return self
    
    def is_open_now(self) -> bool:
        """
        Check if branch is currently open based on operating hours
        
        Returns: True if branch is open, False otherwise
        """
        # This is a simplified implementation
        # In production, you'd need to handle timezones and days of the week
        if not self.opening_time or not self.closing_time:
            return True  # Assume open if hours not set
        
        # Simple check (ignoring timezone for this example)
        try:
            from datetime import time as dt_time
            
            # Get current time in UTC
            now = datetime.utcnow()
            
            # Parse opening and closing times
            open_hour, open_minute = map(int, self.opening_time.split(':'))
            close_hour, close_minute = map(int, self.closing_time.split(':'))
            
            open_time = now.replace(hour=open_hour, minute=open_minute, second=0)
            close_time = now.replace(hour=close_hour, minute=close_minute, second=0)
            
            # Adjust for closing times past midnight
            if close_time < open_time:
                close_time = close_time.replace(day=close_time.day + 1)
            
            return open_time <= now <= close_time
            
        except (ValueError, AttributeError):
            return True  # Assume open if there's an error parsing times
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API response
        
        Returns: Dictionary representation
        """
        data = {
            'branch_id': self.branch_id,
            'branch_number': self.branch_number,
            'branch_name': self.branch_name,
            'status': self.status,
            'is_deleted': self.is_deleted,
        }
        
        # Add optional fields if they exist
        optional_fields = [
            'address', 'phone_number', 'email', 'description', 'branch_type',
            'manager_id', 'manager_name', 'opening_time', 'closing_time',
            'timezone', 'latitude', 'longitude'
        ]
        
        for field in optional_fields:
            if hasattr(self, field) and getattr(self, field) is not None:
                data[field] = getattr(self, field)
        
        # Add timestamps
        if self.date_created:
            data['date_created'] = self.date_created.isoformat()
        if self.last_updated:
            data['last_updated'] = self.last_updated.isoformat()
        
        # Add metadata if exists
        if self.metadata:
            data['metadata'] = self.metadata
        
        # Add computed field
        if hasattr(self, 'opening_time') and hasattr(self, 'closing_time'):
            data['is_open_now'] = self.is_open_now()
        
        return data


# ============= BRANCH FACTORY =============
class BranchFactory:
    """
    Factory for creating branches
    """
    
    @staticmethod
    def create_main_branch(branch_name: str, 
                          address: str = None,
                          phone_number: str = None) -> Branch:
        """
        Create main/headquarters branch
        
        Args:
            branch_name: Name of the branch
            address: Physical address
            phone_number: Contact phone number
        
        Returns: Branch instance
        """
        return Branch.create_branch({
            "branch_name": branch_name,
            "branch_type": "main",
            "address": address,
            "phone_number": phone_number,
            "status": "active"
        })
    
    @staticmethod
    def create_retail_branch(branch_name: str,
                            address: str,
                            opening_time: str = "09:00",
                            closing_time: str = "18:00") -> Branch:
        """
        Create retail branch
        
        Args:
            branch_name: Name of the branch
            address: Physical address
            opening_time: Opening time
            closing_time: Closing time
        
        Returns: Branch instance
        """
        return Branch.create_branch({
            "branch_name": branch_name,
            "branch_type": "retail",
            "address": address,
            "opening_time": opening_time,
            "closing_time": closing_time,
            "status": "active"
        })
    
    @staticmethod
    def create_warehouse_branch(branch_name: str,
                               address: str,
                               manager_id: str = None) -> Branch:
        """
        Create warehouse branch
        
        Args:
            branch_name: Name of the branch
            address: Physical address
            manager_id: ID of warehouse manager
        
        Returns: Branch instance
        """
        return Branch.create_branch({
            "branch_name": branch_name,
            "branch_type": "warehouse",
            "address": address,
            "manager_id": manager_id,
            "status": "active"
        })


# ============= GLOBAL SECONDARY INDEXES =============
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

class BranchNameIndex(GlobalSecondaryIndex):
    """GSI for querying by branch name"""
    class Meta:
        index_name = 'branch-name-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    branch_name = UnicodeAttribute(hash_key=True)
    branch_id = UnicodeAttribute(range_key=True)


class BranchTypeIndex(GlobalSecondaryIndex):
    """GSI for querying by branch type"""
    class Meta:
        index_name = 'branch-type-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    branch_type = UnicodeAttribute(hash_key=True)
    branch_id = UnicodeAttribute(range_key=True)


class StatusIndex(GlobalSecondaryIndex):
    """GSI for querying by status"""
    class Meta:
        index_name = 'branch-status-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    status = UnicodeAttribute(hash_key=True)
    branch_id = UnicodeAttribute(range_key=True)


# To use GSIs, add to Branch class:
# name_index = BranchNameIndex()
# type_index = BranchTypeIndex()
# status_index = StatusIndex()


# ============= USAGE EXAMPLES =============
if __name__ == "__main__":
    print("Branch Model (Exact ERD Specification) Ready!")
    print("=" * 60)
    
    # Initialize table and counter
    if not Branch.exists():
        Branch.create_table(wait=True)
        print("Table created successfully")
        Branch.initialize_counter()
        print("Counter initialized")
    
    # Check counter status
    counter = Branch.get_current_counter()
    print(f"Next branch ID will be: {counter['next_id']}")
    
    # Example 1: Create main branch
    print("\n1. Creating main branch:")
    
    main_branch = BranchFactory.create_main_branch(
        branch_name="Headquarters",
        address="123 Main Street, New York, NY 10001",
        phone_number="+1-212-555-1234"
    )
    main_branch.save()
    
    print(f"Created: {main_branch.branch_id}")
    print(f"Name: {main_branch.branch_name}")
    print(f"Type: {main_branch.branch_type}")
    print(f"Address: {main_branch.address}")
    
    # Example 2: Create retail branch
    print("\n2. Creating retail branch:")
    
    retail_branch = BranchFactory.create_retail_branch(
        branch_name="Downtown Store",
        address="456 Oak Avenue, New York, NY 10002",
        opening_time="10:00",
        closing_time="20:00"
    )
    retail_branch.save()
    
    print(f"Created: {retail_branch.branch_id}")
    print(f"Hours: {retail_branch.opening_time} - {retail_branch.closing_time}")
    
    # Example 3: Create warehouse branch
    print("\n3. Creating warehouse branch:")
    
    warehouse_branch = BranchFactory.create_warehouse_branch(
        branch_name="Brooklyn Warehouse",
        address="789 Industrial Blvd, Brooklyn, NY 11201",
        manager_id="USER-005"
    )
    warehouse_branch.save()
    
    print(f"Created: {warehouse_branch.branch_id}")
    print(f"Manager ID: {warehouse_branch.manager_id}")
    
    # Example 4: Direct branch creation
    print("\n4. Direct branch creation:")
    
    office_branch = Branch.create_branch({
        "branch_name": "Midtown Office",
        "branch_type": "office",
        "address": "101 Park Avenue, New York, NY 10003",
        "email": "midtown@company.com",
        "phone_number": "+1-212-555-5678"
    })
    office_branch.save()
    
    print(f"Created: {office_branch.branch_id}")
    print(f"Email: {office_branch.email}")
    
    # Example 5: Update branch
    print("\n5. Updating branch:")
    
    retail_branch.update_branch({
        "phone_number": "+1-212-555-9999",
        "email": "downtown@company.com"
    })
    
    print(f"Updated phone: {retail_branch.phone_number}")
    print(f"Updated email: {retail_branch.email}")
    
    # Example 6: Set location
    print("\n6. Setting branch location:")
    
    main_branch.set_location("40.7128", "-74.0060")
    print(f"Location: {main_branch.latitude}, {main_branch.longitude}")
    
    # Example 7: Check if branch is open
    print("\n7. Checking if branch is open:")
    is_open = retail_branch.is_open_now()
    print(f"Downtown Store is currently open: {is_open}")
    
    # Example 8: Retrieve branch
    print("\n8. Retrieving branch by ID:")
    retrieved = Branch.get_by_id(main_branch.branch_id)
    if retrieved:
        print(f"Found: {retrieved.branch_name}")
        print(f"Data: {retrieved.to_dict().keys()}")
    
    # Example 9: Get all branches
    print("\n9. All branches:")
    branches = Branch.get_all_branches()
    for branch in branches:
        print(f"  - {branch.branch_id}: {branch.branch_name} ({branch.branch_type})")
    
    # Example 10: Get active branches
    print("\n10. Active branches:")
    active_branches = Branch.get_active_branches()
    print(f"Active branches count: {len(active_branches)}")
    
    # Example 11: Search branches by name
    print("\n11. Searching branches by name:")
    search_results = Branch.search_by_name("store", limit=5)
    print(f"Found {len(search_results)} branches with 'store' in name")
    
    # Example 12: Set branch manager
    print("\n12. Setting branch manager:")
    retail_branch.set_manager("USER-010", "John Manager")
    print(f"Manager: {retail_branch.manager_name} ({retail_branch.manager_id})")
    
    # Example 13: Soft delete branch
    print("\n13. Soft deleting branch:")
    warehouse_branch.soft_delete()
    print(f"Is deleted: {warehouse_branch.is_deleted}")
    print(f"Status: {warehouse_branch.status}")
    
    # Example 14: Convert to API response
    print("\n14. Converting branch to API response:")
    api_data = main_branch.to_dict()
    print(f"API response keys: {list(api_data.keys())}")
    print(f"Sample data: { {k: v for k, v in list(api_data.items())[:8]} }")
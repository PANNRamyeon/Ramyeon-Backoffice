"""
Audit Logs Model - Following Exact ERD Specification
PK = "audit_logs", SK = "AUD-#####"
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, UTCDateTimeAttribute,
    JSONAttribute
)
from datetime import datetime
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, List
import time


class AuditLog(Model):
    """
    AUDIT LOGS MODEL - Following Exact ERD Specification
    
    PK/SK Pattern:
    - PK: "audit_logs" (table name/entity type)
    - SK: "AUD-#####" (5-digit auto-increment: 00001, 00002, etc.)
    
    For tracking all system activities, user actions, and changes.
    """
    
    class Meta:
        table_name = os.environ.get('AUDIT_LOG_TABLE_NAME', 'AuditLogs')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        if os.environ.get('DYNAMODB_LOCAL', 'false').lower() == 'true':
            host = os.environ.get('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')
        read_capacity_units = 10  # Higher for frequent reads
        write_capacity_units = 20  # Higher for frequent writes
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True)   # Partition Key: "audit_logs"
    sk = UnicodeAttribute(range_key=True)  # Sort Key: "AUD-00001"
    
    # ============= AUDIT LOG DATA (EXACT ERD FIELDS) =============
    
    # Audit Log ID (derived from SK, but stored for easy access)
    audit_id = UnicodeAttribute()  # "AUD-00001"
    audit_number = UnicodeAttribute()  # "00001" (string to preserve leading zeros)
    
    # User Information
    user_id = UnicodeAttribute(null=True)  # String (optional - system actions may not have user)
    username = UnicodeAttribute(null=True)  # String
    
    # Location/Context
    branch_id = UnicodeAttribute(null=True)  # String (optional)
    
    # Timestamps
    timestamp = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    last_updated = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    
    # Action Details
    status = UnicodeAttribute(default="success")  # String: "success", "failed", "pending"
    source = UnicodeAttribute(null=True)  # String: "web", "mobile", "api", "system", "cron"
    
    # Target Information
    target_type = UnicodeAttribute(null=True)  # String: "user", "customer", "product", "order", "inventory"
    target_id = UnicodeAttribute(null=True)  # String: ID of the target (e.g., "CUST-0001")
    target_name = UnicodeAttribute(null=True)  # String: Name of the target
    
    # Additional Data
    metadata = JSONAttribute(null=True)  # array/object: Additional context data
    
    # ============= ADDITIONAL FIELDS FOR BETTER TRACKING =============
    # (Not in ERD but useful for audit logs)
    action = UnicodeAttribute(null=True)  # String: "create", "update", "delete", "login", "export"
    ip_address = UnicodeAttribute(null=True)  # String: User's IP address
    user_agent = UnicodeAttribute(null=True)  # String: Browser/device info
    description = UnicodeAttribute(null=True)  # String: Human-readable description
    
    # ============= COUNTER CONFIGURATION =============
    ID_PREFIX = "AUD-"
    DIGITS = 5  # 5-digit format: AUD-00001 to AUD-99999
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
    def _format_audit_id(cls, number: int) -> str:
        """Format audit ID with prefix and 5 digits"""
        return f"{cls.ID_PREFIX}{number:0{cls.DIGITS}d}"
    
    @classmethod
    def _get_next_audit_id(cls) -> Dict[str, Any]:
        """
        Get next auto-incrementing audit ID (thread-safe)
        Returns: {"audit_id": "AUD-00001", "audit_number": "00001", "numeric_number": 1}
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
                        'sk': 'AUDIT_LOG'
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
                audit_id = cls._format_audit_id(new_number)
                audit_number_str = f"{new_number:0{cls.DIGITS}d}"
                
                return {
                    "audit_id": audit_id,
                    "audit_number": audit_number_str,
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
                                'sk': 'AUDIT_LOG',
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
            "audit_id": f"{cls.ID_PREFIX}T{timestamp}",
            "audit_number": f"T{timestamp}",
            "numeric_number": timestamp
        }
    
    @classmethod
    def get_current_counter(cls) -> Dict[str, Any]:
        """Get current counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        try:
            response = table.get_item(
                Key={'pk': 'COUNTERS', 'sk': 'AUDIT_LOG'}
            )
            
            if 'Item' in response:
                current = response['Item'].get('value', cls.DEFAULT_START_NUMBER - 1)
                return {
                    "current_value": current,
                    "next_id": cls._format_audit_id(current + 1)
                }
        except:
            pass
        
        return {
            "current_value": cls.DEFAULT_START_NUMBER - 1,
            "next_id": cls._format_audit_id(cls.DEFAULT_START_NUMBER)
        }
    
    @classmethod
    def set_counter_value(cls, value: int):
        """Manually set counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        table.update_item(
            Key={'pk': 'COUNTERS', 'sk': 'AUDIT_LOG'},
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
                    'sk': 'AUDIT_LOG',
                    'value': start_value,
                    'created_at': datetime.utcnow().isoformat()
                },
                ConditionExpression='attribute_not_exists(pk)'
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print("Audit log counter already exists")
    
    # ============= TEMPLATE METHODS =============
    
    @classmethod
    def create_log(cls, log_data: Dict[str, Any]) -> 'AuditLog':
        """
        Create audit log entry from data
        
        Args:
            log_data: Dictionary with audit log fields
        
        Returns: AuditLog instance (not saved yet)
        """
        # Get next ID
        id_info = cls._get_next_audit_id()
        audit_id = id_info["audit_id"]
        audit_number = id_info["audit_number"]
        
        # Set PK/SK
        pk = "audit_logs"
        sk = audit_id
        
        # Prepare data
        log_data_with_ids = {
            "pk": pk,
            "sk": sk,
            "audit_id": audit_id,
            "audit_number": audit_number,
            **log_data
        }
        
        # Create instance
        return cls(**log_data_with_ids)
    
    @classmethod
    def log_action(cls, 
                   action: str,
                   user_id: str = None,
                   username: str = None,
                   target_type: str = None,
                   target_id: str = None,
                   target_name: str = None,
                   status: str = "success",
                   source: str = "system",
                   branch_id: str = None,
                   metadata: Dict = None,
                   description: str = None,
                   ip_address: str = None,
                   user_agent: str = None) -> 'AuditLog':
        """
        Convenience method to create and save an audit log entry
        
        Args:
            action: Action performed (create, update, delete, login, etc.)
            user_id: ID of user who performed action
            username: Username of user who performed action
            target_type: Type of target (user, customer, product, etc.)
            target_id: ID of target
            target_name: Name of target
            status: success, failed, pending
            source: web, mobile, api, system
            branch_id: Branch ID if applicable
            metadata: Additional context data
            description: Human-readable description
            ip_address: User's IP address
            user_agent: Browser/device info
        
        Returns: Saved AuditLog instance
        """
        log = cls.create_log({
            "action": action,
            "user_id": user_id,
            "username": username,
            "target_type": target_type,
            "target_id": target_id,
            "target_name": target_name,
            "status": status,
            "source": source,
            "branch_id": branch_id,
            "metadata": metadata or {},
            "description": description,
            "ip_address": ip_address,
            "user_agent": user_agent
        })
        
        log.save()
        return log
    
    @classmethod
    def get_by_id(cls, audit_id: str) -> Optional['AuditLog']:
        """
        Get audit log by ID
        
        Args:
            audit_id: "AUD-00001" format
        
        Returns: AuditLog or None
        """
        try:
            return cls.get("audit_logs", audit_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_by_user_id(cls, user_id: str, limit: int = 100) -> List['AuditLog']:
        """
        Get audit logs for specific user
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of logs to return
        
        Returns: List of audit logs
        """
        logs = []
        for log in cls.scan(cls.user_id == user_id, limit=limit):
            logs.append(log)
        return logs
    
    @classmethod
    def get_by_target(cls, target_type: str, target_id: str, limit: int = 100) -> List['AuditLog']:
        """
        Get audit logs for specific target
        
        Args:
            target_type: Type of target (user, customer, etc.)
            target_id: ID of target
            limit: Maximum number of logs to return
        
        Returns: List of audit logs
        """
        logs = []
        for log in cls.scan(
            (cls.target_type == target_type) & (cls.target_id == target_id),
            limit=limit
        ):
            logs.append(log)
        return logs
    
    @classmethod
    def get_by_action(cls, action: str, limit: int = 100) -> List['AuditLog']:
        """
        Get audit logs by action type
        
        Args:
            action: Action to filter by (create, update, delete, etc.)
            limit: Maximum number of logs to return
        
        Returns: List of audit logs
        """
        logs = []
        for log in cls.scan(cls.action == action, limit=limit):
            logs.append(log)
        return logs
    
    @classmethod
    def get_by_date_range(cls, 
                         start_date: datetime, 
                         end_date: datetime,
                         limit: int = 1000) -> List['AuditLog']:
        """
        Get audit logs within date range
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of logs to return
        
        Returns: List of audit logs
        """
        logs = []
        # Note: This is a scan operation. For production, consider using GSI on timestamp
        for log in cls.scan(cls.timestamp.between(start_date, end_date), limit=limit):
            logs.append(log)
        return logs
    
    @classmethod
    def get_recent_logs(cls, hours: int = 24, limit: int = 500) -> List['AuditLog']:
        """
        Get recent audit logs
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of logs to return
        
        Returns: List of recent audit logs
        """
        cutoff = datetime.utcnow() - datetime.timedelta(hours=hours)
        return cls.get_by_date_range(cutoff, datetime.utcnow(), limit)
    
    @classmethod
    def get_all_logs(cls, limit: int = 1000) -> List['AuditLog']:
        """
        Get all audit logs (paginated)
        
        Args:
            limit: Maximum number of logs to return
        
        Returns: List of audit logs
        """
        return list(cls.query("audit_logs", limit=limit, scan_index_forward=False))  # Newest first
    
    def save(self, *args, **kwargs):
        """Override save to update last_updated timestamp"""
        self.last_updated = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API response
        
        Returns: Dictionary representation
        """
        data = {
            'audit_id': self.audit_id,
            'audit_number': self.audit_number,
            'user_id': self.user_id,
            'username': self.username,
            'branch_id': self.branch_id,
            'status': self.status,
            'source': self.source,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'target_name': self.target_name,
        }
        
        # Add timestamps
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        if self.last_updated:
            data['last_updated'] = self.last_updated.isoformat()
        
        # Add metadata if exists
        if self.metadata:
            data['metadata'] = self.metadata
        
        # Add additional fields if they exist
        if hasattr(self, 'action') and self.action:
            data['action'] = self.action
        if hasattr(self, 'ip_address') and self.ip_address:
            data['ip_address'] = self.ip_address
        if hasattr(self, 'user_agent') and self.user_agent:
            data['user_agent'] = self.user_agent
        if hasattr(self, 'description') and self.description:
            data['description'] = self.description
        
        return data


# ============= AUDIT LOGGER UTILITY =============
class AuditLogger:
    """
    Utility class for standardized audit logging
    """
    
    @staticmethod
    def log_user_login(user_id: str, username: str, 
                      status: str = "success",
                      ip_address: str = None,
                      user_agent: str = None) -> AuditLog:
        """
        Log user login attempt
        
        Args:
            user_id: User ID
            username: Username
            status: success or failed
            ip_address: IP address
            user_agent: Browser/device info
        
        Returns: Created audit log
        """
        return AuditLog.log_action(
            action="login",
            user_id=user_id,
            username=username,
            target_type="user",
            target_id=user_id,
            target_name=username,
            status=status,
            source="web",
            description=f"User login attempt: {status}",
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_user_logout(user_id: str, username: str,
                       ip_address: str = None) -> AuditLog:
        """
        Log user logout
        
        Args:
            user_id: User ID
            username: Username
            ip_address: IP address
        
        Returns: Created audit log
        """
        return AuditLog.log_action(
            action="logout",
            user_id=user_id,
            username=username,
            target_type="user",
            target_id=user_id,
            target_name=username,
            source="web",
            description="User logged out",
            ip_address=ip_address
        )
    
    @staticmethod
    def log_create(target_type: str, target_id: str, target_name: str,
                  user_id: str = None, username: str = None,
                  metadata: Dict = None) -> AuditLog:
        """
        Log creation of an entity
        
        Args:
            target_type: Type of entity (customer, product, order, etc.)
            target_id: ID of created entity
            target_name: Name of created entity
            user_id: ID of user who created it
            username: Username of user who created it
            metadata: Additional context
        
        Returns: Created audit log
        """
        return AuditLog.log_action(
            action="create",
            user_id=user_id,
            username=username,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            status="success",
            description=f"Created {target_type}: {target_name}",
            metadata=metadata
        )
    
    @staticmethod
    def log_update(target_type: str, target_id: str, target_name: str,
                  user_id: str = None, username: str = None,
                  changes: Dict = None, metadata: Dict = None) -> AuditLog:
        """
        Log update of an entity
        
        Args:
            target_type: Type of entity
            target_id: ID of updated entity
            target_name: Name of updated entity
            user_id: ID of user who updated it
            username: Username of user who updated it
            changes: Dictionary of changed fields
            metadata: Additional context
        
        Returns: Created audit log
        """
        log_metadata = metadata or {}
        if changes:
            log_metadata['changes'] = changes
        
        return AuditLog.log_action(
            action="update",
            user_id=user_id,
            username=username,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            status="success",
            description=f"Updated {target_type}: {target_name}",
            metadata=log_metadata
        )
    
    @staticmethod
    def log_delete(target_type: str, target_id: str, target_name: str,
                  user_id: str = None, username: str = None,
                  metadata: Dict = None) -> AuditLog:
        """
        Log deletion of an entity
        
        Args:
            target_type: Type of entity
            target_id: ID of deleted entity
            target_name: Name of deleted entity
            user_id: ID of user who deleted it
            username: Username of user who deleted it
            metadata: Additional context
        
        Returns: Created audit log
        """
        return AuditLog.log_action(
            action="delete",
            user_id=user_id,
            username=username,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            status="success",
            description=f"Deleted {target_type}: {target_name}",
            metadata=metadata
        )
    
    @staticmethod
    def log_error(action: str, description: str,
                 user_id: str = None, username: str = None,
                 target_type: str = None, target_id: str = None,
                 error_message: str = None) -> AuditLog:
        """
        Log error/exception
        
        Args:
            action: Action that failed
            description: Description of what failed
            user_id: ID of user (if applicable)
            username: Username (if applicable)
            target_type: Type of target (if applicable)
            target_id: ID of target (if applicable)
            error_message: Error message/details
        
        Returns: Created audit log
        """
        metadata = {}
        if error_message:
            metadata['error'] = error_message
        
        return AuditLog.log_action(
            action=action,
            user_id=user_id,
            username=username,
            target_type=target_type,
            target_id=target_id,
            status="failed",
            description=description,
            metadata=metadata
        )


# ============= GLOBAL SECONDARY INDEXES =============
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

class UserIdIndex(GlobalSecondaryIndex):
    """GSI for querying by user_id"""
    class Meta:
        index_name = 'audit-user-id-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    user_id = UnicodeAttribute(hash_key=True)
    timestamp = UTCDateTimeAttribute(range_key=True)


class TargetIndex(GlobalSecondaryIndex):
    """GSI for querying by target"""
    class Meta:
        index_name = 'audit-target-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    target_type = UnicodeAttribute(hash_key=True)
    target_id = UnicodeAttribute(range_key=True)


class TimestampIndex(GlobalSecondaryIndex):
    """GSI for querying by timestamp"""
    class Meta:
        index_name = 'audit-timestamp-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    timestamp = UTCDateTimeAttribute(hash_key=True)
    audit_id = UnicodeAttribute(range_key=True)


class ActionIndex(GlobalSecondaryIndex):
    """GSI for querying by action"""
    class Meta:
        index_name = 'audit-action-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    action = UnicodeAttribute(hash_key=True)
    timestamp = UTCDateTimeAttribute(range_key=True)


# To use GSIs, add to AuditLog class:
# user_id_index = UserIdIndex()
# target_index = TargetIndex()
# timestamp_index = TimestampIndex()
# action_index = ActionIndex()


# ============= USAGE EXAMPLES =============
if __name__ == "__main__":
    print("Audit Logs Model (Exact ERD Specification) Ready!")
    print("=" * 60)
    
    # Initialize table and counter
    if not AuditLog.exists():
        AuditLog.create_table(wait=True)
        print("Table created successfully")
        AuditLog.initialize_counter()
        print("Counter initialized")
    
    # Check counter status
    counter = AuditLog.get_current_counter()
    print(f"Next audit log ID will be: {counter['next_id']}")
    
    # Example 1: Log user login
    print("\n1. Logging user login:")
    
    login_log = AuditLogger.log_user_login(
        user_id="USER-001",
        username="admin",
        ip_address="192.168.1.100",
        user_agent="Chrome/120.0.0.0"
    )
    
    print(f"Created: {login_log.audit_id}")
    print(f"Action: {login_log.action}")
    print(f"User: {login_log.username}")
    print(f"Status: {login_log.status}")
    
    # Example 2: Log creation of customer
    print("\n2. Logging customer creation:")
    
    customer_log = AuditLogger.log_create(
        target_type="customer",
        target_id="CUST-0001",
        target_name="John Doe",
        user_id="USER-001",
        username="admin",
        metadata={"method": "web_form", "category": "new_customer"}
    )
    
    print(f"Created: {customer_log.audit_id}")
    print(f"Target: {customer_log.target_type} - {customer_log.target_name}")
    print(f"Description: {customer_log.description}")
    
    # Example 3: Log update with changes
    print("\n3. Logging customer update with changes:")
    
    update_log = AuditLogger.log_update(
        target_type="customer",
        target_id="CUST-0001",
        target_name="John Doe",
        user_id="USER-002",
        username="manager",
        changes={
            "email": {"old": "john@old.com", "new": "john@new.com"},
            "phone": {"old": "test", "new": "+1234567890"}
        }
    )
    
    print(f"Created: {update_log.audit_id}")
    print(f"Changes: {update_log.metadata.get('changes')}")
    
    # Example 4: Log error
    print("\n4. Logging error:")
    
    error_log = AuditLogger.log_error(
        action="export_data",
        description="Failed to export customer data",
        user_id="USER-001",
        username="admin",
        error_message="Disk space insufficient"
    )
    
    print(f"Created: {error_log.audit_id}")
    print(f"Status: {error_log.status}")
    print(f"Error: {error_log.metadata.get('error')}")
    
    # Example 5: Direct log creation
    print("\n5. Direct audit log creation:")
    
    direct_log = AuditLog.log_action(
        action="search",
        user_id="USER-003",
        username="staff",
        target_type="inventory",
        description="Searched inventory for product XYZ",
        source="mobile",
        metadata={"query": "product XYZ", "results_count": 15}
    )
    
    print(f"Created: {direct_log.audit_id}")
    print(f"Source: {direct_log.source}")
    print(f"Metadata: {direct_log.metadata}")
    
    # Example 6: Retrieve logs by user
    print("\n6. Retrieving logs for user USER-001:")
    user_logs = AuditLog.get_by_user_id("USER-001", limit=5)
    print(f"Found {len(user_logs)} logs")
    for log in user_logs:
        print(f"  - {log.audit_id}: {log.action} ({log.timestamp})")
    
    # Example 7: Get recent logs
    print("\n7. Getting recent logs (last 1 hour):")
    recent_logs = AuditLog.get_recent_logs(hours=1, limit=10)
    print(f"Found {len(recent_logs)} logs in last hour")
    
    # Example 8: Get all logs (most recent first)
    print("\n8. All audit logs (most recent first):")
    all_logs = AuditLog.get_all_logs(limit=10)
    for log in all_logs:
        print(f"  - {log.audit_id}: {log.action} by {log.username} at {log.timestamp}")
    
    # Example 9: Convert to API response
    print("\n9. Converting log to API response:")
    api_data = login_log.to_dict()
    print(f"API response keys: {list(api_data.keys())}")
    print(f"Sample data: { {k: v for k, v in list(api_data.items())[:5]} }")
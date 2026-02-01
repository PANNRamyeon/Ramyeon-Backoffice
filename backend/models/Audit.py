"""
Audit Logs Model - Following Modified ERD Specification
Single Table Design: Uses RamyeonCornerDB with utils.py configuration
"""
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST
from datetime import datetime
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# ============= GSI DEFINITIONS =============
class UserIdTimestampIndex(GlobalSecondaryIndex):
    """
    GSI for querying audit logs by user_id with timestamp range
    Hash Key: user_id, Range Key: timestamp
    """
    class Meta:
        index_name = 'audit-user-timestamp-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5


# ============= MAIN AUDIT LOG MODEL =============
class AuditLog(Model):
    """
    AUDIT LOGS MODEL - Modified ERD Specification
    Single Table Design using RamyeonCornerDB
    
    PK/SK Pattern:
    - PK: "audit_logs" (entity type)
    - SK: "AUD-#####" (5-digit auto-increment using utils.py)
    
    Modified ERD Fields:
    - action (String) replaces metadata (array)
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # Use same table as utils.py
        region = AWS_REGION  # Use same region as utils.py
        
        # Add local DynamoDB support if enabled
        #if DYNAMODB_LOCAL:
        #    host = DYNAMODB_LOCAL_HOST
        
        # Capacity units - adjust based on expected volume
        read_capacity_units = 5
        write_capacity_units = 10  # Higher for frequent writes
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True)   # Partition Key: "audit_logs"
    sk = UnicodeAttribute(range_key=True)  # Sort Key: "AUD-00001" (generated)
    
    # ============= GSI DEFINITION =============
    user_id_index = UserIdTimestampIndex()
    
    # ============= ERD FIELDS (WITH MODIFICATION) =============
    user_id = UnicodeAttribute(null=True)
    username = UnicodeAttribute(null=True)
    branch_id = UnicodeAttribute(null=True)
    timestamp = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    status = UnicodeAttribute(default="success")  # success, failed, pending
    source = UnicodeAttribute(null=True)  # web, mobile, api, system, cron
    last_updated = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    target_type = UnicodeAttribute(null=True)  # user, customer, product, order, inventory
    target_id = UnicodeAttribute(null=True)
    target_name = UnicodeAttribute(null=True)
    action = UnicodeAttribute(null=True)  # create, update, delete, login, export, etc.
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_audit_log(cls, **kwargs) -> 'AuditLog':
        """
        Create and save an audit log entry with auto-generated SK
        """
        try:
            # Generate SK using utils.py function
            sk = generate_sk('AUD-', 'audit_seq')
            
            # Set required fields
            kwargs['pk'] = 'audit_logs'
            kwargs['sk'] = sk
            
            # Ensure timestamps are set
            current_time = datetime.utcnow()
            if 'timestamp' not in kwargs:
                kwargs['timestamp'] = current_time
            if 'last_updated' not in kwargs:
                kwargs['last_updated'] = current_time
            
            # Ensure status has default if not provided
            if 'status' not in kwargs:
                kwargs['status'] = 'success'
            
            # Create and save the audit log
            audit_log = cls(**kwargs)
            audit_log.save()
            
            logger.info(f"Audit log created: {sk} - Action: {kwargs.get('action', 'N/A')}")
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            logger.error(f"Audit log data: {kwargs}")
            
            # For debugging, you might want to raise in development
            if os.environ.get('ENVIRONMENT', 'production') == 'development':
                raise
            
            return None
    
    @classmethod
    def log_action(cls, **kwargs) -> 'AuditLog':
        """
        Convenience method for logging actions
        """
        return cls.create_audit_log(**kwargs)
    
    @classmethod
    def get_by_id(cls, audit_id: str) -> 'AuditLog | None':
        """
        Get audit log by ID (SK)
        """
        try:
            return cls.get("audit_logs", audit_id)
        except cls.DoesNotExist:
            logger.warning(f"Audit log not found: {audit_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching audit log {audit_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_user_id(cls, user_id: str, 
                      start_date: datetime = None,
                      end_date: datetime = None,
                      limit: int = 100,
                      reverse: bool = True) -> list:
        """
        Get audit logs for a specific user using GSI
        """
        try:
            if start_date and end_date:
                query_result = cls.user_id_index.query(
                    user_id,
                    cls.timestamp.between(start_date, end_date),
                    limit=limit,
                    scan_index_forward=not reverse
                )
            else:
                query_result = cls.user_id_index.query(
                    user_id,
                    limit=limit,
                    scan_index_forward=not reverse
                )
            
            return list(query_result)
            
        except Exception as e:
            logger.error(f"Error querying audit logs for user {user_id}: {str(e)}")
            return []
    
    @classmethod
    def get_all_logs(cls, limit: int = 1000, reverse: bool = True) -> list:
        """
        Get all audit logs (paginated)
        """
        try:
            return list(cls.query(
                "audit_logs",
                limit=limit,
                scan_index_forward=not reverse
            ))
        except Exception as e:
            logger.error(f"Error querying all audit logs: {str(e)}")
            return []
    
    def save(self, *args, **kwargs):
        """Override save to update last_updated timestamp"""
        try:
            self.last_updated = datetime.utcnow()
            return super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving audit log {self.sk}: {str(e)}")
            raise
    
    def to_dict(self) -> dict:
        """
        Convert audit log to dictionary for API responses
        """
        try:
            return {
                'audit_id': self.sk,
                'user_id': self.user_id,
                'username': self.username,
                'branch_id': self.branch_id,
                'timestamp': self.timestamp.isoformat() if self.timestamp else None,
                'status': self.status,
                'source': self.source,
                'last_updated': self.last_updated.isoformat() if self.last_updated else None,
                'target_type': self.target_type,
                'target_id': self.target_id,
                'target_name': self.target_name,
                'action': self.action
            }
        except Exception as e:
            logger.error(f"Error converting audit log to dict: {str(e)}")
            return {}


# ============= SIMPLIFIED AUDIT LOGGER =============
def log_audit_event(action: str, user_id: str = None, username: str = None,
                   target_type: str = None, target_id: str = None,
                   target_name: str = None, status: str = "success",
                   source: str = "system", branch_id: str = None) -> AuditLog | None:
    """
    Simplified function to create audit trail entries
    """
    try:
        return AuditLog.log_action(
            action=action,
            user_id=user_id,
            username=username,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            status=status,
            source=source,
            branch_id=branch_id
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {str(e)}")
        return None


# ============= PRE-DEFINED AUDIT TYPES =============
class AuditEvents:
    """Pre-defined audit event templates"""
    
    @staticmethod
    def user_login(user_id: str, username: str, status: str = "success", 
                  ip_address: str = None, user_agent: str = None) -> AuditLog | None:
        """Log user login attempt"""
        return log_audit_event(
            action="login",
            user_id=user_id,
            username=username,
            target_type="user",
            target_id=user_id,
            target_name=username,
            status=status,
            source="web",
            description=f"User login {status}"
        )
    
    @staticmethod
    def create_entity(target_type: str, target_id: str, target_name: str,
                     user_id: str = None, username: str = None) -> AuditLog | None:
        """Log creation of an entity"""
        return log_audit_event(
            action="create",
            user_id=user_id,
            username=username,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            status="success",
            description=f"Created {target_type}: {target_name}"
        )
    
    @staticmethod
    def update_entity(target_type: str, target_id: str, target_name: str,
                     user_id: str = None, username: str = None) -> AuditLog | None:
        """Log update of an entity"""
        return log_audit_event(
            action="update",
            user_id=user_id,
            username=username,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            status="success",
            description=f"Updated {target_type}: {target_name}"
        )
    
    @staticmethod
    def delete_entity(target_type: str, target_id: str, target_name: str,
                     user_id: str = None, username: str = None) -> AuditLog | None:
        """Log deletion of an entity"""
        return log_audit_event(
            action="delete",
            user_id=user_id,
            username=username,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            status="success",
            description=f"Deleted {target_type}: {target_name}"
        )
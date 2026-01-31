"""
Session Logs Model - Following Exact ERD Specification
PK = "session_logs", SK = "SES-#####"
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, UTCDateTimeAttribute,
    NumberAttribute
)
from datetime import datetime, timedelta
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, List
import time


class SessionLog(Model):
    """
    SESSION LOGS MODEL - Following Exact ERD Specification
    
    PK/SK Pattern:
    - PK: "session_logs" (table name/entity type)
    - SK: "SES-#####" (5-digit auto-increment: 00001, 00002, etc.)
    
    For tracking user sessions, login/logout times, and session duration.
    """
    
    class Meta:
        table_name = os.environ.get('SESSION_LOG_TABLE_NAME', 'SessionLogs')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        if os.environ.get('DYNAMODB_LOCAL', 'false').lower() == 'true':
            host = os.environ.get('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')
        read_capacity_units = 10
        write_capacity_units = 15  # Higher for frequent session tracking
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True)   # Partition Key: "session_logs"
    sk = UnicodeAttribute(range_key=True)  # Sort Key: "SES-00001"
    
    # ============= SESSION LOG DATA (EXACT ERD FIELDS) =============
    
    # Session ID (derived from SK, but stored for easy access)
    session_id = UnicodeAttribute()  # "SES-00001"
    session_number = UnicodeAttribute()  # "00001" (string to preserve leading zeros)
    
    # Session Context
    branch_id = UnicodeAttribute(null=True)  # String (optional - for multi-branch systems)
    username = UnicodeAttribute()  # String (who the session belongs to)
    
    # Timestamps
    login_time = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    logout_time = UTCDateTimeAttribute(null=True)  # ISODATE (null if still active)
    
    # Duration - stored as number of seconds for easier calculations
    # ERD says ISODATE but we'll store as Number (seconds) and provide ISO string in to_dict()
    session_duration_seconds = NumberAttribute(null=True)  # Duration in seconds
    
    # Session Details
    status = UnicodeAttribute(default="active")  # String: "active", "ended", "expired", "terminated", "failed"
    source = UnicodeAttribute(null=True)  # String: "web", "mobile", "desktop", "api", "cli"
    logout_reason = UnicodeAttribute(null=True)  # String: "user_logout", "timeout", "system_logout", "forced", "error"
    
    # ============= ADDITIONAL FIELDS FOR BETTER TRACKING =============
    # (Not in ERD but useful for session management)
    user_id = UnicodeAttribute(null=True)  # String: Reference to User table
    ip_address = UnicodeAttribute(null=True)  # String: IP address at login
    user_agent = UnicodeAttribute(null=True)  # String: Browser/device info
    device_info = UnicodeAttribute(null=True)  # String: Device type/model
    location = UnicodeAttribute(null=True)  # String: Geographic location
    auth_method = UnicodeAttribute(null=True)  # String: "password", "oauth", "sso", "biometric"
    session_token = UnicodeAttribute(null=True)  # String: Session token/JWT (hashed for security)
    is_active = BooleanAttribute(default=True)  # Boolean: Quick check for active sessions
    
    # ============= COUNTER CONFIGURATION =============
    ID_PREFIX = "SES-"
    DIGITS = 5  # 5-digit format: SES-00001 to SES-99999
    DEFAULT_START_NUMBER = 1
    
    # ============= SESSION DURATION CONSTANTS =============
    SESSION_TIMEOUT_MINUTES = 30  # Default session timeout
    MAX_SESSION_DURATION_HOURS = 24  # Max allowed session duration
    
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
    def _format_session_id(cls, number: int) -> str:
        """Format session ID with prefix and 5 digits"""
        return f"{cls.ID_PREFIX}{number:0{cls.DIGITS}d}"
    
    @classmethod
    def _get_next_session_id(cls) -> Dict[str, Any]:
        """
        Get next auto-incrementing session ID (thread-safe)
        Returns: {"session_id": "SES-00001", "session_number": "00001", "numeric_number": 1}
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
                        'sk': 'SESSION_LOG'
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
                session_id = cls._format_session_id(new_number)
                session_number_str = f"{new_number:0{cls.DIGITS}d}"
                
                return {
                    "session_id": session_id,
                    "session_number": session_number_str,
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
                                'sk': 'SESSION_LOG',
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
            "session_id": f"{cls.ID_PREFIX}T{timestamp}",
            "session_number": f"T{timestamp}",
            "numeric_number": timestamp
        }
    
    @classmethod
    def get_current_counter(cls) -> Dict[str, Any]:
        """Get current counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        try:
            response = table.get_item(
                Key={'pk': 'COUNTERS', 'sk': 'SESSION_LOG'}
            )
            
            if 'Item' in response:
                current = response['Item'].get('value', cls.DEFAULT_START_NUMBER - 1)
                return {
                    "current_value": current,
                    "next_id": cls._format_session_id(current + 1)
                }
        except:
            pass
        
        return {
            "current_value": cls.DEFAULT_START_NUMBER - 1,
            "next_id": cls._format_session_id(cls.DEFAULT_START_NUMBER)
        }
    
    @classmethod
    def set_counter_value(cls, value: int):
        """Manually set counter value"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        table.update_item(
            Key={'pk': 'COUNTERS', 'sk': 'SESSION_LOG'},
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
                    'sk': 'SESSION_LOG',
                    'value': start_value,
                    'created_at': datetime.utcnow().isoformat()
                },
                ConditionExpression='attribute_not_exists(pk)'
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print("Session log counter already exists")
    
    # ============= TEMPLATE METHODS =============
    
    @classmethod
    def create_session(cls, session_data: Dict[str, Any]) -> 'SessionLog':
        """
        Create session log entry from data
        
        Args:
            session_data: Dictionary with session log fields
        
        Returns: SessionLog instance (not saved yet)
        """
        # Get next ID
        id_info = cls._get_next_session_id()
        session_id = id_info["session_id"]
        session_number = id_info["session_number"]
        
        # Set PK/SK
        pk = "session_logs"
        sk = session_id
        
        # Prepare data
        session_data_with_ids = {
            "pk": pk,
            "sk": sk,
            "session_id": session_id,
            "session_number": session_number,
            **session_data
        }
        
        # Create instance
        return cls(**session_data_with_ids)
    
    @classmethod
    def start_session(cls, 
                      username: str,
                      user_id: str = None,
                      branch_id: str = None,
                      source: str = "web",
                      ip_address: str = None,
                      user_agent: str = None,
                      device_info: str = None,
                      location: str = None,
                      auth_method: str = "password") -> 'SessionLog':
        """
        Start a new user session
        
        Args:
            username: Username
            user_id: User ID (optional)
            branch_id: Branch ID (optional)
            source: Source of login (web, mobile, etc.)
            ip_address: IP address
            user_agent: Browser/device info
            device_info: Device type/model
            location: Geographic location
            auth_method: Authentication method
        
        Returns: SessionLog instance (saved)
        """
        session = cls.create_session({
            "username": username,
            "user_id": user_id,
            "branch_id": branch_id,
            "source": source,
            "status": "active",
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_info": device_info,
            "location": location,
            "auth_method": auth_method,
            "is_active": True,
            "login_time": datetime.utcnow()
        })
        
        session.save()
        return session
    
    def end_session(self, 
                   logout_reason: str = "user_logout",
                   status: str = "ended") -> 'SessionLog':
        """
        End an active session
        
        Args:
            logout_reason: Reason for logout
            status: Final status
        
        Returns: Updated SessionLog instance
        """
        if not self.is_active:
            raise ValueError(f"Session {self.session_id} is already inactive")
        
        self.logout_time = datetime.utcnow()
        self.logout_reason = logout_reason
        self.status = status
        self.is_active = False
        
        # Calculate duration
        if self.login_time and self.logout_time:
            duration = (self.logout_time - self.login_time).total_seconds()
            self.session_duration_seconds = duration
        
        self.save()
        return self
    
    def force_end_session(self, 
                         reason: str = "forced_logout",
                         by_user: str = None) -> 'SessionLog':
        """
        Force end a session (admin/system action)
        
        Args:
            reason: Reason for forced logout
            by_user: Who forced the logout
        
        Returns: Updated SessionLog instance
        """
        self.logout_reason = f"forced: {reason}"
        if by_user:
            self.logout_reason += f" by {by_user}"
        
        return self.end_session(
            logout_reason=self.logout_reason,
            status="terminated"
        )
    
    def check_session_timeout(self, timeout_minutes: int = None) -> bool:
        """
        Check if session has timed out
        
        Args:
            timeout_minutes: Timeout in minutes (defaults to class constant)
        
        Returns: True if session has timed out
        """
        if not self.is_active:
            return True
        
        if timeout_minutes is None:
            timeout_minutes = self.SESSION_TIMEOUT_MINUTES
        
        if not self.login_time:
            return False
        
        timeout_delta = timedelta(minutes=timeout_minutes)
        return datetime.utcnow() > self.login_time + timeout_delta
    
    def refresh_session(self) -> 'SessionLog':
        """
        Refresh session (extend login time for active sessions)
        
        Returns: Updated SessionLog instance
        """
        if not self.is_active:
            raise ValueError(f"Cannot refresh inactive session {self.session_id}")
        
        # Update login time to now (session refresh)
        self.login_time = datetime.utcnow()
        self.save()
        return self
    
    @classmethod
    def get_by_id(cls, session_id: str) -> Optional['SessionLog']:
        """
        Get session by ID
        
        Args:
            session_id: "SES-00001" format
        
        Returns: SessionLog or None
        """
        try:
            return cls.get("session_logs", session_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_active_sessions(cls, username: str = None, 
                           user_id: str = None, 
                           branch_id: str = None) -> List['SessionLog']:
        """
        Get active sessions with optional filters
        
        Args:
            username: Filter by username
            user_id: Filter by user ID
            branch_id: Filter by branch ID
        
        Returns: List of active sessions
        """
        sessions = []
        
        # Build filter conditions
        filter_conditions = []
        
        if username:
            filter_conditions.append(cls.username == username)
        if user_id:
            filter_conditions.append(cls.user_id == user_id)
        if branch_id:
            filter_conditions.append(cls.branch_id == branch_id)
        
        # Always filter by active status
        filter_conditions.append(cls.is_active == True)
        
        # Combine conditions
        combined_condition = filter_conditions[0]
        for condition in filter_conditions[1:]:
            combined_condition = combined_condition & condition
        
        # Query with conditions
        for session in cls.scan(combined_condition):
            sessions.append(session)
        
        return sessions
    
    @classmethod
    def get_user_sessions(cls, username: str, 
                         limit: int = 100,
                         active_only: bool = False) -> List['SessionLog']:
        """
        Get all sessions for a user
        
        Args:
            username: Username to filter by
            limit: Maximum number of sessions to return
            active_only: Only return active sessions
        
        Returns: List of user sessions
        """
        sessions = []
        
        condition = cls.username == username
        if active_only:
            condition = condition & (cls.is_active == True)
        
        for session in cls.scan(condition, limit=limit):
            sessions.append(session)
        
        # Sort by login_time (newest first)
        sessions.sort(key=lambda s: s.login_time if s.login_time else datetime.min, 
                     reverse=True)
        return sessions
    
    @classmethod
    def get_sessions_by_date_range(cls, 
                                  start_date: datetime, 
                                  end_date: datetime,
                                  limit: int = 1000) -> List['SessionLog']:
        """
        Get sessions within date range
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of sessions to return
        
        Returns: List of sessions
        """
        sessions = []
        # Note: This is a scan operation. For production, consider using GSI on login_time
        for session in cls.scan(cls.login_time.between(start_date, end_date), limit=limit):
            sessions.append(session)
        
        return sessions
    
    @classmethod
    def get_recent_sessions(cls, hours: int = 24, 
                           limit: int = 500) -> List['SessionLog']:
        """
        Get recent sessions
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of sessions to return
        
        Returns: List of recent sessions
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return cls.get_sessions_by_date_range(cutoff, datetime.utcnow(), limit)
    
    @classmethod
    def get_all_sessions(cls, limit: int = 1000) -> List['SessionLog']:
        """
        Get all sessions (paginated)
        
        Args:
            limit: Maximum number of sessions to return
        
        Returns: List of sessions
        """
        return list(cls.query("session_logs", limit=limit, scan_index_forward=False))  # Newest first
    
    @classmethod
    def cleanup_expired_sessions(cls, timeout_minutes: int = None) -> List['SessionLog']:
        """
        Find and mark expired sessions as ended
        
        Args:
            timeout_minutes: Session timeout in minutes
        
        Returns: List of expired sessions that were cleaned up
        """
        if timeout_minutes is None:
            timeout_minutes = cls.SESSION_TIMEOUT_MINUTES
        
        expired_sessions = []
        active_sessions = cls.get_active_sessions()
        
        for session in active_sessions:
            if session.check_session_timeout(timeout_minutes):
                session.end_session(
                    logout_reason="timeout",
                    status="expired"
                )
                expired_sessions.append(session)
        
        return expired_sessions
    
    @classmethod
    def get_session_statistics(cls, 
                              start_date: datetime = None,
                              end_date: datetime = None) -> Dict[str, Any]:
        """
        Get session statistics
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
        
        Returns: Dictionary with session statistics
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow()
        
        sessions = cls.get_sessions_by_date_range(start_date, end_date, limit=10000)
        
        stats = {
            'total_sessions': len(sessions),
            'active_sessions': 0,
            'average_duration': 0,
            'by_source': {},
            'by_status': {},
            'unique_users': set(),
        }
        
        total_duration = 0
        sessions_with_duration = 0
        
        for session in sessions:
            if session.is_active:
                stats['active_sessions'] += 1
            
            # Count by source
            source = session.source or 'unknown'
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
            
            # Count by status
            status = session.status or 'unknown'
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Track unique users
            if session.username:
                stats['unique_users'].add(session.username)
            
            # Calculate duration
            if session.session_duration_seconds:
                total_duration += session.session_duration_seconds
                sessions_with_duration += 1
        
        # Calculate average duration
        if sessions_with_duration > 0:
            stats['average_duration'] = total_duration / sessions_with_duration
        
        stats['unique_users_count'] = len(stats['unique_users'])
        
        return stats
    
    def save(self, *args, **kwargs):
        """Override save to ensure consistency"""
        # If session is marked as ended but logout_time is not set, set it
        if self.status in ["ended", "expired", "terminated", "failed"] and not self.logout_time:
            self.logout_time = datetime.utcnow()
            self.is_active = False
        
        # Calculate duration if login and logout times are set
        if self.login_time and self.logout_time and not self.session_duration_seconds:
            duration = (self.logout_time - self.login_time).total_seconds()
            self.session_duration_seconds = duration
        
        return super().save(*args, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API response
        
        Returns: Dictionary representation
        """
        data = {
            'session_id': self.session_id,
            'session_number': self.session_number,
            'username': self.username,
            'branch_id': self.branch_id,
            'status': self.status,
            'source': self.source,
            'logout_reason': self.logout_reason,
            'is_active': self.is_active,
        }
        
        # Add timestamps
        if self.login_time:
            data['login_time'] = self.login_time.isoformat()
        if self.logout_time:
            data['logout_time'] = self.logout_time.isoformat()
        
        # Add session duration in ISO format (as per ERD)
        if self.session_duration_seconds:
            # Convert seconds to ISO duration format (e.g., PT1H30M15S)
            hours = int(self.session_duration_seconds // 3600)
            minutes = int((self.session_duration_seconds % 3600) // 60)
            seconds = int(self.session_duration_seconds % 60)
            
            iso_duration = "PT"
            if hours > 0:
                iso_duration += f"{hours}H"
            if minutes > 0:
                iso_duration += f"{minutes}M"
            if seconds > 0:
                iso_duration += f"{seconds}S"
            
            data['session_duration'] = iso_duration
            data['session_duration_seconds'] = self.session_duration_seconds
        
        # Add additional fields if they exist
        if hasattr(self, 'user_id') and self.user_id:
            data['user_id'] = self.user_id
        if hasattr(self, 'ip_address') and self.ip_address:
            data['ip_address'] = self.ip_address
        if hasattr(self, 'user_agent') and self.user_agent:
            data['user_agent'] = self.user_agent
        if hasattr(self, 'device_info') and self.device_info:
            data['device_info'] = self.device_info
        if hasattr(self, 'location') and self.location:
            data['location'] = self.location
        if hasattr(self, 'auth_method') and self.auth_method:
            data['auth_method'] = self.auth_method
        
        return data
    
    def get_duration_human_readable(self) -> str:
        """
        Get session duration in human-readable format
        
        Returns: Human-readable duration string
        """
        if not self.session_duration_seconds:
            if self.is_active and self.login_time:
                # Calculate current duration for active sessions
                current_duration = (datetime.utcnow() - self.login_time).total_seconds()
                return self._format_duration(current_duration)
            return "N/A"
        
        return self._format_duration(self.session_duration_seconds)
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds into human-readable string"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


# ============= SESSION MANAGER UTILITY =============
class SessionManager:
    """
    Utility class for managing user sessions
    """
    
    @staticmethod
    def login_user(username: str, 
                   user_id: str = None,
                   ip_address: str = None,
                   user_agent: str = None,
                   **kwargs) -> SessionLog:
        """
        Create a new session for a logging in user
        
        Args:
            username: Username
            user_id: User ID (optional)
            ip_address: IP address
            user_agent: Browser/device info
            **kwargs: Additional session parameters
        
        Returns: New session log
        """
        # Check for existing active sessions
        active_sessions = SessionLog.get_active_sessions(username=username)
        
        # Option 1: Allow multiple sessions
        # Option 2: End existing sessions (uncomment below)
        # for session in active_sessions:
        #     session.end_session(logout_reason="new_login", status="ended")
        
        # Create new session
        session = SessionLog.start_session(
            username=username,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            **kwargs
        )
        
        return session
    
    @staticmethod
    def logout_user(username: str = None,
                   session_id: str = None,
                   logout_reason: str = "user_logout") -> List[SessionLog]:
        """
        Logout user - end all active sessions or specific session
        
        Args:
            username: Username to logout (all sessions)
            session_id: Specific session ID to logout
            logout_reason: Reason for logout
        
        Returns: List of ended sessions
        """
        ended_sessions = []
        
        if session_id:
            # End specific session
            session = SessionLog.get_by_id(session_id)
            if session and session.is_active:
                session.end_session(logout_reason=logout_reason)
                ended_sessions.append(session)
        elif username:
            # End all active sessions for user
            active_sessions = SessionLog.get_active_sessions(username=username)
            for session in active_sessions:
                session.end_session(logout_reason=logout_reason)
                ended_sessions.append(session)
        
        return ended_sessions
    
    @staticmethod
    def logout_all_except_current(username: str, 
                                 current_session_id: str) -> List[SessionLog]:
        """
        Logout all user sessions except the current one
        
        Args:
            username: Username
            current_session_id: Current session ID to keep
        
        Returns: List of ended sessions
        """
        ended_sessions = []
        active_sessions = SessionLog.get_active_sessions(username=username)
        
        for session in active_sessions:
            if session.session_id != current_session_id:
                session.end_session(logout_reason="other_device_login")
                ended_sessions.append(session)
        
        return ended_sessions
    
    @staticmethod
    def validate_session(session_id: str, 
                        username: str = None) -> tuple[bool, Optional[SessionLog], str]:
        """
        Validate if a session is still active and valid
        
        Args:
            session_id: Session ID to validate
            username: Optional username to match
        
        Returns: (is_valid, session, message)
        """
        session = SessionLog.get_by_id(session_id)
        
        if not session:
            return False, None, "Session not found"
        
        if not session.is_active:
            return False, session, "Session is inactive"
        
        if username and session.username != username:
            return False, session, "Session does not belong to user"
        
        # Check if session has timed out
        if session.check_session_timeout():
            session.end_session(logout_reason="timeout", status="expired")
            return False, session, "Session has expired"
        
        return True, session, "Session is valid"


# ============= GLOBAL SECONDARY INDEXES =============
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

class UsernameIndex(GlobalSecondaryIndex):
    """GSI for querying by username"""
    class Meta:
        index_name = 'session-username-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    username = UnicodeAttribute(hash_key=True)
    login_time = UTCDateTimeAttribute(range_key=True)


class UserIdIndex(GlobalSecondaryIndex):
    """GSI for querying by user_id"""
    class Meta:
        index_name = 'session-user-id-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    user_id = UnicodeAttribute(hash_key=True)
    login_time = UTCDateTimeAttribute(range_key=True)


class StatusIndex(GlobalSecondaryIndex):
    """GSI for querying by status"""
    class Meta:
        index_name = 'session-status-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    status = UnicodeAttribute(hash_key=True)
    login_time = UTCDateTimeAttribute(range_key=True)


class LoginTimeIndex(GlobalSecondaryIndex):
    """GSI for querying by login time"""
    class Meta:
        index_name = 'session-login-time-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    login_time = UTCDateTimeAttribute(hash_key=True)
    session_id = UnicodeAttribute(range_key=True)


# To use GSIs, add to SessionLog class:
# username_index = UsernameIndex()
# user_id_index = UserIdIndex()
# status_index = StatusIndex()
# login_time_index = LoginTimeIndex()


# ============= USAGE EXAMPLES =============
if __name__ == "__main__":
    print("Session Logs Model (Exact ERD Specification) Ready!")
    print("=" * 60)
    
    # Initialize table and counter
    if not SessionLog.exists():
        SessionLog.create_table(wait=True)
        print("Table created successfully")
        SessionLog.initialize_counter()
        print("Counter initialized")
    
    # Check counter status
    counter = SessionLog.get_current_counter()
    print(f"Next session ID will be: {counter['next_id']}")
    
    # Example 1: Start a new session
    print("\n1. Starting new user session:")
    
    session1 = SessionManager.login_user(
        username="john.doe",
        user_id="USER-001",
        ip_address="192.168.1.100",
        user_agent="Chrome/120.0.0.0",
        source="web",
        location="New York, USA",
        auth_method="password"
    )
    
    print(f"Created: {session1.session_id}")
    print(f"User: {session1.username}")
    print(f"Login time: {session1.login_time}")
    print(f"Status: {session1.status}")
    print(f"Active: {session1.is_active}")
    
    # Example 2: Start another session (mobile)
    print("\n2. Starting mobile session:")
    
    session2 = SessionLog.start_session(
        username="jane.smith",
        user_id="USER-002",
        source="mobile",
        ip_address="10.0.0.1",
        user_agent="iOS Safari/16.0",
        device_info="iPhone 14",
        location="San Francisco, USA",
        auth_method="biometric"
    )
    
    print(f"Created: {session2.session_id}")
    print(f"Source: {session2.source}")
    print(f"Device: {session2.device_info}")
    
    # Example 3: End a session
    print("\n3. Ending session:")
    
    session1.end_session(logout_reason="user_logout")
    
    print(f"Session ended: {session1.session_id}")
    print(f"Logout time: {session1.logout_time}")
    print(f"Duration: {session1.get_duration_human_readable()}")
    print(f"Active: {session1.is_active}")
    
    # Example 4: Check session timeout
    print("\n4. Checking session timeout:")
    print(f"Session 1 timeout: {session1.check_session_timeout()}")
    print(f"Session 2 timeout: {session2.check_session_timeout()}")
    
    # Example 5: Get active sessions
    print("\n5. Getting active sessions:")
    active_sessions = SessionLog.get_active_sessions()
    print(f"Total active sessions: {len(active_sessions)}")
    for s in active_sessions:
        print(f"  - {s.session_id}: {s.username} ({s.source})")
    
    # Example 6: Get user sessions
    print("\n6. Getting user sessions:")
    user_sessions = SessionLog.get_user_sessions("john.doe", limit=5)
    print(f"Found {len(user_sessions)} sessions for john.doe")
    for s in user_sessions:
        status = "ACTIVE" if s.is_active else "ENDED"
        print(f"  - {s.session_id}: {status} ({s.login_time})")
    
    # Example 7: Validate session
    print("\n7. Validating session:")
    is_valid, valid_session, message = SessionManager.validate_session(session2.session_id)
    print(f"Session {session2.session_id}: {message}")
    print(f"Is valid: {is_valid}")
    
    # Example 8: Session statistics
    print("\n8. Session statistics (last 7 days):")
    stats = SessionLog.get_session_statistics(
        start_date=datetime.utcnow() - timedelta(days=7),
        end_date=datetime.utcnow()
    )
    print(f"Total sessions: {stats['total_sessions']}")
    print(f"Active sessions: {stats['active_sessions']}")
    print(f"Unique users: {stats['unique_users_count']}")
    print(f"Average duration: {stats['average_duration']:.0f} seconds")
    
    # Example 9: Cleanup expired sessions
    print("\n9. Cleaning up expired sessions:")
    expired = SessionLog.cleanup_expired_sessions(timeout_minutes=1)  # Short timeout for demo
    print(f"Cleaned up {len(expired)} expired sessions")
    
    # Example 10: Convert to API response
    print("\n10. Converting session to API response:")
    api_data = session1.to_dict()
    print(f"API response keys: {list(api_data.keys())}")
    print(f"Session duration: {api_data.get('session_duration')}")
    
    # Example 11: Refresh session
    print("\n11. Refreshing active session:")
    try:
        session2.refresh_session()
        print(f"Session refreshed at: {session2.login_time}")
    except ValueError as e:
        print(f"Error: {e}")
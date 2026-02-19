"""
SessionLog Model - Following ERD Specification for Employee Session Tracking
PK = "session_logs", SK = "SES-#####" (5-digit format)
Single Table Design using RamyeonCornerDB
"""
import os
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, UTCDateTimeAttribute,
    NumberAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

# Import existing utils for consistency
from app.utils import generate_sk, get_dynamo_table, DYNAMO_TABLE_NAME, AWS_REGION
from models.Branch import Branch  # For branch validation

logger = logging.getLogger(__name__)


# ============= SESSION LOG MODEL =============

class SessionLog(Model):
    """
    SESSION LOG MODEL - For Employee Session Tracking & Work Hour Management
    
    ERD Fields:
    - PK = session_logs
    - SK = SES-#####
    - branch_id (String)
    - username (String)
    - login_time (ISODATE)
    - logout_time (ISODATE)
    - session_duration (ISODATE) - Stored as seconds, formatted as ISO duration
    - status (String)
    - source (String)
    - logout_reason (String)
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        # Capacity settings (moderate reads for reports)
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="session_logs")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "SES-00001" (5-digit)
    
    # ============= SESSION LOG DATA =============
    branch_id = UnicodeAttribute()  # Required for employee tracking
    username = UnicodeAttribute()  # Employee username (required)
    
    # ============= TIMESTAMPS =============
    login_time = UTCDateTimeAttribute()
    logout_time = UTCDateTimeAttribute(null=True)
    
    # ============= SESSION DURATION =============
    # Stored as seconds, formatted as ISO duration in to_dict()
    session_duration_seconds = NumberAttribute(null=True)
    
    # ============= SESSION DETAILS =============
    status = UnicodeAttribute(default="active")  # 'active', 'ended', 'expired', 'terminated'
    source = UnicodeAttribute(default="pos")  # 'pos', 'admin_panel', 'mobile'
    logout_reason = UnicodeAttribute(null=True)  # 'logout', 'timeout', 'shift_end', 'forced'
    
    # ============= ENHANCED FOR EMPLOYEE TRACKING =============
    employee_id = UnicodeAttribute(null=True)  # Link to employee record
    employee_name = UnicodeAttribute(null=True)  # For reporting
    role = UnicodeAttribute(null=True)  # 'cashier', 'manager', 'admin'
    shift_type = UnicodeAttribute(null=True)  # 'morning', 'afternoon', 'night'
    
    # ============= INDEXES FOR COMMON QUERIES =============
    
    class UsernameIndex(GlobalSecondaryIndex):
        """GSI for querying by username"""
        class Meta:
            index_name = 'SessionLogUsernameIndex'
            read_capacity_units = 5  # Higher for employee tracking reports
            write_capacity_units = 3
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True)  # Will be set to 'session_logs'
        username = UnicodeAttribute(range_key=True)
    
    class BranchIndex(GlobalSecondaryIndex):
        """GSI for querying by branch"""
        class Meta:
            index_name = 'SessionLogBranchIndex'
            read_capacity_units = 5
            write_capacity_units = 3
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True)  # Will be set to 'session_logs'
        branch_id = UnicodeAttribute(range_key=True)
    
    class DateIndex(GlobalSecondaryIndex):
        """GSI for querying by date range"""
        class Meta:
            index_name = 'SessionLogDateIndex'
            read_capacity_units = 5
            write_capacity_units = 3
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True)  # Will be set to 'session_logs'
        login_time = UTCDateTimeAttribute(range_key=True)
    
    class EmployeeIndex(GlobalSecondaryIndex):
        """GSI for querying by employee ID"""
        class Meta:
            index_name = 'SessionLogEmployeeIndex'
            read_capacity_units = 5
            write_capacity_units = 3
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True)  # Will be set to 'session_logs'
        employee_id = UnicodeAttribute(range_key=True)
    
    # Index instances
    username_index = UsernameIndex()
    branch_index = BranchIndex()
    date_index = DateIndex()
    employee_index = EmployeeIndex()
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_session_log(cls, username: str, branch_id: str, source: str = "pos",
                          employee_id: str = None, employee_name: str = None,
                          role: str = None, shift_type: str = None,
                          **kwargs) -> 'SessionLog':
        """
        Create a new session log for employee tracking
        
        Args:
            username: Employee username (required)
            branch_id: Branch where employee is working (required)
            source: Session source ('pos', 'admin_panel', 'mobile')
            employee_id: Employee ID (optional)
            employee_name: Employee full name (optional)
            role: Employee role (optional)
            shift_type: Shift type (optional)
            **kwargs: Additional session log attributes
        
        Returns:
            SessionLog: Created and saved session log instance
        
        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Validate required fields
            if not username or not username.strip():
                raise ValueError("Username is required")
            if not branch_id:
                raise ValueError("Branch ID is required")
            
            # Validate branch exists (optional but recommended)
            branch = Branch.get_by_id(branch_id)
            if not branch:
                logger.warning(f"Branch {branch_id} not found, but creating session anyway")
            
            # Generate 5-digit SK using utils.py
            sk_value = generate_sk('SES-', 'session_seq')
            
            # Create and save session log
            session_log = cls(
                pk="session_logs",
                sk=sk_value,
                username=username.strip(),
                branch_id=branch_id,
                source=source,
                employee_id=employee_id,
                employee_name=employee_name or username.strip(),
                role=role,
                shift_type=shift_type,
                login_time=datetime.utcnow(),
                status="active",
                **kwargs
            )
            
            session_log.save()
            
            logger.info(f"Session log created: {sk_value} - Employee: {username}, Branch: {branch_id}")
            return session_log
            
        except Exception as e:
            logger.error(f"Failed to create session log: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, session_id: str) -> 'SessionLog | None':
        """
        Get session log by ID
        
        Args:
            session_id: Format "SES-00001" or just "00001"
        
        Returns:
            SessionLog or None if not found
        """
        try:
            # Ensure proper format
            if not session_id.startswith('SES-'):
                session_id = f"SES-{session_id.zfill(5)}"
            
            return cls.get("session_logs", session_id)
        except cls.DoesNotExist:
            logger.warning(f"Session log not found: {session_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching session log {session_id}: {str(e)}")
            return None
    
    @classmethod
    def get_active_sessions(cls, username: str = None, branch_id: str = None,
                           role: str = None) -> List['SessionLog']:
        """
        Get active employee sessions
        
        Args:
            username: Filter by username
            branch_id: Filter by branch
            role: Filter by role
        
        Returns:
            list: List of active session logs
        """
        try:
            active_sessions = []
            
            # Query by status
            for session in cls.query(
                "session_logs",
                filter_condition=cls.status == "active"
            ):
                # Apply filters
                if username and session.username != username:
                    continue
                if branch_id and session.branch_id != branch_id:
                    continue
                if role and session.role != role:
                    continue
                
                active_sessions.append(session)
            
            return active_sessions
        except Exception as e:
            logger.error(f"Error getting active sessions: {str(e)}")
            return []
    
    @classmethod
    def get_employee_sessions(cls, username: str, start_date: datetime = None,
                             end_date: datetime = None) -> List['SessionLog']:
        """
        Get all sessions for an employee within date range
        
        Args:
            username: Employee username
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: now)
        
        Returns:
            list: List of employee session logs
        """
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            sessions = []
            
            # Query by username index
            for session in cls.username_index.query(
                "session_logs",
                cls.username == username,
                filter_condition=(cls.login_time >= start_date) & (cls.login_time <= end_date)
            ):
                sessions.append(session)
            
            # Sort by login time
            sessions.sort(key=lambda x: x.login_time if x.login_time else datetime.min)
            return sessions
        except Exception as e:
            logger.error(f"Error getting sessions for employee {username}: {str(e)}")
            return []
    
    @classmethod
    def get_branch_sessions(cls, branch_id: str, start_date: datetime = None,
                           end_date: datetime = None) -> List['SessionLog']:
        """
        Get all sessions for a branch within date range
        
        Args:
            branch_id: Branch ID
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: now)
        
        Returns:
            list: List of session logs for the branch
        """
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            sessions = []
            
            # Query by branch index
            for session in cls.branch_index.query(
                "session_logs",
                cls.branch_id == branch_id,
                filter_condition=(cls.login_time >= start_date) & (cls.login_time <= end_date)
            ):
                sessions.append(session)
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting sessions for branch {branch_id}: {str(e)}")
            return []
    
    @classmethod
    def get_sessions_by_date(cls, date: datetime = None) -> List['SessionLog']:
        """
        Get all sessions for a specific date
        
        Args:
            date: Date to query (default: today)
        
        Returns:
            list: List of session logs for the date
        """
        try:
            if not date:
                date = datetime.utcnow()
            
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            sessions = []
            
            # Query by date index
            for session in cls.date_index.query(
                "session_logs",
                cls.login_time >= start_date,
                filter_condition=cls.login_time <= end_date
            ):
                sessions.append(session)
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting sessions by date: {str(e)}")
            return []
    
    @classmethod
    def get_today_sessions(cls) -> List['SessionLog']:
        """
        Get today's sessions
        
        Returns:
            list: List of today's session logs
        """
        return cls.get_sessions_by_date()
    
    @classmethod
    def get_employee_work_hours(cls, username: str, start_date: datetime = None,
                               end_date: datetime = None) -> Dict[str, Any]:
        """
        Calculate work hours for an employee
        
        Args:
            username: Employee username
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: now)
        
        Returns:
            dict: Work hour statistics
        """
        try:
            sessions = cls.get_employee_sessions(username, start_date, end_date)
            
            total_hours = 0.0
            total_sessions = 0
            sessions_by_day = {}
            
            for session in sessions:
                if session.session_duration_seconds:
                    hours = session.session_duration_seconds / 3600
                    total_hours += hours
                    total_sessions += 1
                    
                    # Group by date
                    if session.login_time:
                        date_key = session.login_time.date().isoformat()
                        if date_key not in sessions_by_day:
                            sessions_by_day[date_key] = {
                                "date": date_key,
                                "sessions": 0,
                                "hours": 0.0,
                                "login_times": []
                            }
                        
                        sessions_by_day[date_key]["sessions"] += 1
                        sessions_by_day[date_key]["hours"] += hours
                        sessions_by_day[date_key]["login_times"].append(
                            session.login_time.time().isoformat()[:5]
                        )
            
            return {
                "employee": username,
                "total_sessions": total_sessions,
                "total_hours": round(total_hours, 2),
                "average_hours_per_session": round(total_hours / total_sessions, 2) if total_sessions > 0 else 0,
                "sessions_by_day": list(sessions_by_day.values()),
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }
        except Exception as e:
            logger.error(f"Error calculating work hours for {username}: {str(e)}")
            return {}
    
    @classmethod
    def get_branch_work_hours(cls, branch_id: str, start_date: datetime = None,
                             end_date: datetime = None) -> Dict[str, Any]:
        """
        Calculate work hours for a branch
        
        Args:
            branch_id: Branch ID
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: now)
        
        Returns:
            dict: Branch work hour statistics
        """
        try:
            sessions = cls.get_branch_sessions(branch_id, start_date, end_date)
            
            total_hours = 0.0
            total_sessions = 0
            employees = {}
            
            for session in sessions:
                if session.session_duration_seconds:
                    hours = session.session_duration_seconds / 3600
                    total_hours += hours
                    total_sessions += 1
                    
                    # Group by employee
                    employee_key = session.username
                    if employee_key not in employees:
                        employees[employee_key] = {
                            "username": session.username,
                            "employee_name": session.employee_name or session.username,
                            "role": session.role,
                            "sessions": 0,
                            "hours": 0.0
                        }
                    
                    employees[employee_key]["sessions"] += 1
                    employees[employee_key]["hours"] += hours
            
            return {
                "branch_id": branch_id,
                "total_sessions": total_sessions,
                "total_hours": round(total_hours, 2),
                "total_employees": len(employees),
                "employees": list(employees.values()),
                "average_hours_per_employee": round(total_hours / len(employees), 2) if employees else 0,
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }
        except Exception as e:
            logger.error(f"Error calculating work hours for branch {branch_id}: {str(e)}")
            return {}
    
    @classmethod
    def cleanup_expired_sessions(cls, timeout_hours: int = 24) -> List['SessionLog']:
        """
        Mark expired sessions as ended
        
        Args:
            timeout_hours: Hours after which active sessions expire
        
        Returns:
            list: List of expired sessions
        """
        try:
            expired_sessions = []
            active_sessions = cls.get_active_sessions()
            
            for session in active_sessions:
                if session.is_expired(timeout_hours):
                    session.end_session(
                        logout_reason="timeout",
                        status="expired"
                    )
                    expired_sessions.append(session)
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            return expired_sessions
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return []
    
    # ============= INSTANCE METHODS =============
    
    def end_session(self, logout_reason: str = "logout",
                   status: str = "ended") -> 'SessionLog':
        """
        End an employee session
        
        Args:
            logout_reason: Reason for logout ('logout', 'shift_end', 'timeout', 'forced')
            status: Final status ('ended', 'expired', 'terminated')
        
        Returns:
            SessionLog: Updated session log instance
        """
        try:
            if self.status != "active":
                raise ValueError(f"Session {self.sk} is not active")
            
            self.logout_time = datetime.utcnow()
            self.logout_reason = logout_reason
            self.status = status
            
            # Calculate duration in seconds
            if self.login_time and self.logout_time:
                duration = (self.logout_time - self.login_time).total_seconds()
                self.session_duration_seconds = duration
            
            self.save()
            
            logger.info(f"Session ended: {self.sk} - Employee: {self.username}, "
                       f"Duration: {self.get_duration_human_readable()}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to end session {self.sk}: {str(e)}")
            raise
    
    def is_expired(self, timeout_hours: int = 24) -> bool:
        """
        Check if session has expired (active too long)
        
        Args:
            timeout_hours: Hours after which session expires
        
        Returns:
            bool: True if session has expired
        """
        try:
            if self.status != "active":
                return True
            
            if not self.login_time:
                return False
            
            timeout_delta = timedelta(hours=timeout_hours)
            return datetime.utcnow() > self.login_time + timeout_delta
        except Exception as e:
            logger.error(f"Error checking session expiration: {str(e)}")
            return False
    
    def get_duration_iso_format(self) -> str:
        """
        Get session duration in ISO 8601 format
        
        Returns:
            str: ISO duration string (e.g., PT8H30M15S)
        """
        try:
            if not self.session_duration_seconds:
                return ""
            
            # Convert seconds to ISO duration format
            seconds = int(self.session_duration_seconds)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            
            iso_duration = "PT"
            if hours > 0:
                iso_duration += f"{hours}H"
            if minutes > 0:
                iso_duration += f"{minutes}M"
            if secs > 0:
                iso_duration += f"{secs}S"
            
            return iso_duration
        except Exception as e:
            logger.error(f"Error converting duration to ISO format: {str(e)}")
            return ""
    
    def get_duration_human_readable(self) -> str:
        """
        Get session duration in human-readable format
        
        Returns:
            str: Human-readable duration string
        """
        try:
            if self.session_duration_seconds:
                seconds = self.session_duration_seconds
            elif self.status == "active" and self.login_time:
                # Calculate current duration for active sessions
                seconds = (datetime.utcnow() - self.login_time).total_seconds()
            else:
                return "N/A"
            
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m"
            elif minutes > 0:
                return f"{minutes}m"
            else:
                return f"{int(seconds)}s"
        except Exception as e:
            logger.error(f"Error getting human-readable duration: {str(e)}")
            return "N/A"
    
    def get_work_hours(self) -> float:
        """
        Get session duration in work hours
        
        Returns:
            float: Duration in hours (decimal)
        """
        try:
            if self.session_duration_seconds:
                return round(self.session_duration_seconds / 3600, 2)
            elif self.status == "active" and self.login_time:
                # Calculate current duration for active sessions
                seconds = (datetime.utcnow() - self.login_time).total_seconds()
                return round(seconds / 3600, 2)
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating work hours: {str(e)}")
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session log to dictionary for API response
        
        Returns:
            dict: Dictionary representation
        """
        try:
            data = {
                "session_id": self.sk.replace("SES-", ""),
                "branch_id": self.branch_id,
                "username": self.username,
                "status": self.status,
                "source": self.source,
                "logout_reason": self.logout_reason,
                "employee_id": self.employee_id,
                "employee_name": self.employee_name or self.username,
                "role": self.role,
                "shift_type": self.shift_type,
            }
            
            # Add timestamps
            if self.login_time:
                data["login_time"] = self.login_time.isoformat()
                data["login_date"] = self.login_time.date().isoformat()
                data["login_time_display"] = self.login_time.strftime("%I:%M %p")
            
            if self.logout_time:
                data["logout_time"] = self.logout_time.isoformat()
                data["logout_date"] = self.logout_time.date().isoformat()
                data["logout_time_display"] = self.logout_time.strftime("%I:%M %p")
            
            # Add session duration in ISO format (as per ERD)
            data["session_duration"] = self.get_duration_iso_format()
            
            # Add human-readable duration
            data["duration_human"] = self.get_duration_human_readable()
            
            # Add work hours
            data["work_hours"] = self.get_work_hours()
            
            # Add duration in seconds for calculations
            if self.session_duration_seconds:
                data["session_duration_seconds"] = float(self.session_duration_seconds)
            
            return data
            
        except Exception as e:
            logger.error(f"Error converting session log to dict: {str(e)}")
            return {}
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """
        Minimal dictionary representation (for listings)
        
        Returns:
            dict: Basic session log info
        """
        try:
            return {
                "id": self.sk.replace("SES-", ""),
                "username": self.username,
                "employee_name": self.employee_name or self.username,
                "branch_id": self.branch_id,
                "login_time": self.login_time.isoformat() if self.login_time else None,
                "logout_time": self.logout_time.isoformat() if self.logout_time else None,
                "status": self.status,
                "duration": self.get_duration_human_readable(),
                "work_hours": self.get_work_hours()
            }
        except Exception as e:
            logger.error(f"Error converting session log to simple dict: {str(e)}")
            return {}


# ============= SESSION LOG VALIDATION =============

def validate_session_log_id(session_id: str) -> bool:
    """
    Validate if a session ID is in correct format
    
    Args:
        session_id: Session ID to validate
    
    Returns:
        bool: True if valid format, False otherwise
    """
    try:
        if not session_id:
            return False
        
        if not session_id.startswith('SES-'):
            return False
        
        number_part = session_id[4:]  # Remove "SES-"
        if len(number_part) != 5:
            return False
        
        number = int(number_part)
        return 1 <= number <= 99999
        
    except (ValueError, IndexError):
        return False


def validate_session_log_data(username: str, branch_id: str) -> tuple[bool, str]:
    """
    Validate session log data before creation
    
    Args:
        username: Username to validate
        branch_id: Branch ID to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not username or not username.strip():
        return False, "Username is required"
    
    if len(username.strip()) > 100:
        return False, "Username must be 100 characters or less"
    
    if not branch_id:
        return False, "Branch ID is required"
    
    # Validate branch format (optional)
    from Branch import validate_branch_id
    if not validate_branch_id(branch_id):
        logger.warning(f"Branch ID {branch_id} may not be in correct format")
    
    return True, ""


# ============= BULK OPERATIONS =============

def batch_end_sessions(session_ids: List[str], logout_reason: str = "shift_end") -> Dict:
    """
    End multiple sessions at once (e.g., end of shift)
    
    Args:
        session_ids: List of session IDs to end
        logout_reason: Reason for logout
    
    Returns:
        dict: Summary of end results
    """
    ended = []
    errors = []
    
    for session_id in session_ids:
        try:
            session = SessionLog.get_by_id(session_id)
            if not session:
                errors.append(f"Session not found: {session_id}")
                continue
            
            if session.status != "active":
                errors.append(f"Session not active: {session_id}")
                continue
            
            session.end_session(logout_reason)
            ended.append(session_id)
            
        except Exception as e:
            errors.append(f"Failed to end session {session_id}: {str(e)}")
    
    return {
        "ended": ended,
        "total_ended": len(ended),
        "errors": errors,
        "success": len(errors) == 0
    }


# ============= SESSION LOG MANAGER =============

class SessionLogManager:
    """
    Manager class for session log-related operations and reports
    """
    
    @staticmethod
    def get_daily_attendance_report(date: datetime = None) -> Dict:
        """
        Get daily attendance report
        
        Args:
            date: Date for report (default: today)
        
        Returns:
            dict: Daily attendance report
        """
        try:
            if not date:
                date = datetime.utcnow()
            
            sessions = SessionLog.get_sessions_by_date(date)
            branch_sessions = {}
            
            for session in sessions:
                branch_id = session.branch_id
                if branch_id not in branch_sessions:
                    branch_sessions[branch_id] = {
                        "branch_id": branch_id,
                        "employees": {},
                        "total_sessions": 0,
                        "total_hours": 0.0
                    }
                
                branch_data = branch_sessions[branch_id]
                branch_data["total_sessions"] += 1
                
                # Group by employee
                employee_key = session.username
                if employee_key not in branch_data["employees"]:
                    branch_data["employees"][employee_key] = {
                        "username": session.username,
                        "employee_name": session.employee_name or session.username,
                        "role": session.role,
                        "sessions": [],
                        "total_hours": 0.0,
                        "first_login": None,
                        "last_logout": None
                    }
                
                employee_data = branch_data["employees"][employee_key]
                employee_data["sessions"].append(session.to_dict())
                
                # Track hours
                hours = session.get_work_hours()
                employee_data["total_hours"] += hours
                branch_data["total_hours"] += hours
                
                # Track first login and last logout
                if session.login_time:
                    if not employee_data["first_login"] or session.login_time < employee_data["first_login"]:
                        employee_data["first_login"] = session.login_time
                
                if session.logout_time:
                    if not employee_data["last_logout"] or session.logout_time > employee_data["last_logout"]:
                        employee_data["last_logout"] = session.logout_time
            
            # Convert employees dict to list
            for branch_data in branch_sessions.values():
                employees_list = []
                for emp in branch_data["employees"].values():
                    # Format timestamps
                    if emp["first_login"]:
                        emp["first_login"] = emp["first_login"].strftime("%I:%M %p")
                    if emp["last_logout"]:
                        emp["last_logout"] = emp["last_logout"].strftime("%I:%M %p")
                    employees_list.append(emp)
                
                branch_data["employees"] = sorted(employees_list, key=lambda x: x.get("first_login", ""))
                branch_data["employee_count"] = len(employees_list)
            
            return {
                "report_date": date.date().isoformat(),
                "total_sessions": len(sessions),
                "branches": list(branch_sessions.values()),
                "branch_count": len(branch_sessions),
                "total_employees": sum(len(b["employees"]) for b in branch_sessions.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting daily attendance report: {str(e)}")
            return {}
    
    @staticmethod
    def get_employee_monthly_report(username: str, year: int = None, month: int = None) -> Dict:
        """
        Get monthly work report for an employee
        
        Args:
            username: Employee username
            year: Year (default: current)
            month: Month (default: current)
        
        Returns:
            dict: Monthly employee report
        """
        try:
            if not year:
                year = datetime.utcnow().year
            if not month:
                month = datetime.utcnow().month
            
            # Calculate date range for the month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            sessions = SessionLog.get_employee_sessions(username, start_date, end_date)
            
            # Group by date
            daily_stats = {}
            for session in sessions:
                if session.login_time:
                    date_key = session.login_time.date().isoformat()
                    if date_key not in daily_stats:
                        daily_stats[date_key] = {
                            "date": date_key,
                            "sessions": 0,
                            "hours": 0.0,
                            "login_times": [],
                            "logout_times": []
                        }
                    
                    daily_stats[date_key]["sessions"] += 1
                    daily_stats[date_key]["hours"] += session.get_work_hours()
                    
                    if session.login_time:
                        daily_stats[date_key]["login_times"].append(
                            session.login_time.strftime("%I:%M %p")
                        )
                    
                    if session.logout_time:
                        daily_stats[date_key]["logout_times"].append(
                            session.logout_time.strftime("%I:%M %p")
                        )
            
            # Calculate totals
            total_hours = sum(day["hours"] for day in daily_stats.values())
            total_days = len(daily_stats)
            avg_hours_per_day = total_hours / total_days if total_days > 0 else 0
            
            return {
                "employee": username,
                "period": {
                    "year": year,
                    "month": month,
                    "month_name": start_date.strftime("%B"),
                    "start": start_date.date().isoformat(),
                    "end": end_date.date().isoformat()
                },
                "total_sessions": len(sessions),
                "total_hours": round(total_hours, 2),
                "total_days_worked": total_days,
                "average_hours_per_day": round(avg_hours_per_day, 2),
                "daily_stats": sorted(list(daily_stats.values()), key=lambda x: x["date"]),
                "sessions": [s.to_dict() for s in sessions]
            }
            
        except Exception as e:
            logger.error(f"Error getting monthly report for {username}: {str(e)}")
            return {}
    
    @staticmethod
    def get_branch_monthly_report(branch_id: str, year: int = None, month: int = None) -> Dict:
        """
        Get monthly work report for a branch
        
        Args:
            branch_id: Branch ID
            year: Year (default: current)
            month: Month (default: current)
        
        Returns:
            dict: Monthly branch report
        """
        try:
            if not year:
                year = datetime.utcnow().year
            if not month:
                month = datetime.utcnow().month
            
            # Calculate date range for the month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            sessions = SessionLog.get_branch_sessions(branch_id, start_date, end_date)
            
            # Group by employee
            employee_stats = {}
            for session in sessions:
                employee_key = session.username
                if employee_key not in employee_stats:
                    employee_stats[employee_key] = {
                        "username": session.username,
                        "employee_name": session.employee_name or session.username,
                        "role": session.role,
                        "total_sessions": 0,
                        "total_hours": 0.0,
                        "days_worked": set()
                    }
                
                stats = employee_stats[employee_key]
                stats["total_sessions"] += 1
                stats["total_hours"] += session.get_work_hours()
                
                if session.login_time:
                    stats["days_worked"].add(session.login_time.date().isoformat())
            
            # Convert days_worked to count
            for stats in employee_stats.values():
                stats["days_worked"] = len(stats["days_worked"])
                stats["average_hours_per_day"] = round(
                    stats["total_hours"] / stats["days_worked"], 2
                ) if stats["days_worked"] > 0 else 0
            
            # Calculate branch totals
            employee_list = list(employee_stats.values())
            total_hours = sum(e["total_hours"] for e in employee_list)
            total_employees = len(employee_list)
            
            return {
                "branch_id": branch_id,
                "period": {
                    "year": year,
                    "month": month,
                    "month_name": start_date.strftime("%B")
                },
                "total_sessions": len(sessions),
                "total_hours": round(total_hours, 2),
                "total_employees": total_employees,
                "average_hours_per_employee": round(total_hours / total_employees, 2) if total_employees > 0 else 0,
                "employees": sorted(employee_list, key=lambda x: x["total_hours"], reverse=True)
            }
            
        except Exception as e:
            logger.error(f"Error getting monthly report for branch {branch_id}: {str(e)}")
            return {}
    
    @staticmethod
    def auto_end_overnight_sessions() -> Dict:
        """
        Automatically end sessions that span overnight
        
        Returns:
            dict: Auto-end results
        """
        try:
            active_sessions = SessionLog.get_active_sessions()
            ended_sessions = []
            
            for session in active_sessions:
                # Check if session started yesterday (more than 12 hours ago)
                if session.login_time:
                    hours_active = (datetime.utcnow() - session.login_time).total_seconds() / 3600
                    
                    if hours_active > 12:
                        session.end_session(
                            logout_reason="overnight_auto_end",
                            status="ended"
                        )
                        ended_sessions.append(session.sk.replace("SES-", ""))
            
            return {
                "ended_sessions": ended_sessions,
                "total_ended": len(ended_sessions),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error auto-ending overnight sessions: {str(e)}")
            return {"error": str(e)}
import csv
import os
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union

# DynamoDB model
from ...models.Sessions import SessionLog, validate_session_log_id, SessionLogManager
from app.utils import generate_sk  # For generating SES-##### keys

# External services (kept as in original)
from notifications.services import notification_service
from notifications.shift_summary_service import shift_summary_service

logger = logging.getLogger(__name__)


class SessionLogService:
    """
    Session Log Service – uses DynamoDB SessionLog model.
    Implements the same public interface as the original MongoDB service.
    """

    def __init__(self):
        self._cleanup_thread = None
        self._stop_cleanup = False

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _send_session_notification(self, action_type: str, session_dict: Dict[str, Any],
                                   additional_metadata: Optional[Dict] = None):
        """Send session-related notifications via the notification service."""
        try:
            username = session_dict.get("username", "Unknown User")
            session_id = session_dict.get("session_id") or session_dict.get("_id", "Unknown")

            notification_config = {
                "login": {
                    "message": f"User {username} logged in successfully",
                    "priority": "info"
                },
                "logout": {
                    "message": f"User {username} logged out",
                    "priority": "info"
                },
                "expired": {
                    "message": f"Session expired for user {username}",
                    "priority": "medium"
                },
                "replaced": {
                    "message": f"Session replaced by new login for user {username}",
                    "priority": "low"
                },
                "bulk_cleanup": {
                    "message": f"Bulk session cleanup completed",
                    "priority": "low"
                },
                "auto_cleanup": {
                    "message": f"Automatic 6-month cleanup completed",
                    "priority": "medium"
                },
                "auto_cleanup_failed": {
                    "message": f"Automatic cleanup failed",
                    "priority": "high"
                },
                "auto_cleanup_started": {
                    "message": f"Automated session cleanup started",
                    "priority": "medium"
                },
                "auto_cleanup_stopped": {
                    "message": "Automated session cleanup stopped",
                    "priority": "medium"
                },
                "manual_cleanup": {
                    "message": f"Manual session cleanup completed",
                    "priority": "medium"
                },
                "manual_cleanup_with_export": {
                    "message": f"Manual cleanup with CSV export completed",
                    "priority": "medium"
                }
            }

            config = notification_config.get(action_type, {
                "message": f"Session action '{action_type}' for user {username}",
                "priority": "info"
            })

            metadata = {
                "session_id": session_id,
                "username": username,
                "action_type": action_type,
                "branch_id": session_dict.get("branch_id", "N/A"),
                "timestamp": datetime.utcnow().isoformat()
            }
            if additional_metadata:
                metadata.update(additional_metadata)

            notification_service.create_notification(
                title=f"Session {action_type.replace('_', ' ').title()}",
                message=config["message"],
                notification_type="session_management",
                priority=config["priority"],
                metadata=metadata
            )
        except Exception as e:
            logger.warning(f"Failed to send session notification: {e}")

    def _close_existing_sessions(self, user_id: str, username: str):
        """
        Close any existing active sessions for a user.
        - Sessions older than 24h → status 'expired'
        - Other active sessions → status 'replaced' (new login)
        """
        try:
            # Find all active sessions for this employee_id (original user_id)
            active_sessions = []
            # Use EmployeeIndex to get all sessions for this employee
            for session in SessionLog.employee_index.query(
                "session_logs",
                SessionLog.employee_id == user_id
            ):
                if session.status == "active":
                    active_sessions.append(session)

            # Also include sessions with same username but possibly different employee_id
            # This catches legacy data or manual entries
            for session in SessionLog.username_index.query(
                "session_logs",
                SessionLog.username == username,
                filter_condition=SessionLog.status == "active"
            ):
                if session.employee_id != user_id and session not in active_sessions:
                    active_sessions.append(session)

            now = datetime.utcnow()
            cutoff = now - timedelta(hours=24)

            for session in active_sessions:
                if session.login_time and session.login_time < cutoff:
                    # Expire very old active sessions
                    session.end_session(logout_reason="session_expired", status="expired")
                    self._send_session_notification("expired", session.to_dict())
                else:
                    # Replace with new login
                    session.end_session(logout_reason="new_login", status="replaced")
                    self._send_session_notification("replaced", session.to_dict())

            if active_sessions:
                logger.info(f"Closed {len(active_sessions)} existing sessions for user {username}")
        except Exception as e:
            logger.error(f"Error closing existing sessions: {e}")

    # -------------------------------------------------------------------------
    # Core session operations
    # -------------------------------------------------------------------------

    def log_login(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new session log.
        user_data must contain at least 'user_id'.
        Optional: username, branch_id, source, role, shift_type.
        """
        try:
            user_id = user_data.get("user_id")
            if not user_id:
                raise ValueError("user_id is required")

            user_id_str = str(user_id)
            username = (
                user_data.get("username") or
                user_data.get("email") or
                f"user_{user_id_str}"
            )
            branch_id = user_data.get("branch_id", "1")   # default branch
            source = user_data.get("source", "auth_service")
            role = user_data.get("role")
            shift_type = user_data.get("shift_type")

            # Close any previous active sessions
            self._close_existing_sessions(user_id_str, username)

            # Create session using the model's factory method
            session = SessionLog.create_session_log(
                username=username,
                branch_id=branch_id,
                source=source,
                employee_id=user_id_str,
                employee_name=username,
                role=role,
                shift_type=shift_type
            )

            session_dict = session.to_dict()
            self._send_session_notification("login", session_dict)

            logger.info(f"Login session {session.sk} logged for user {username}")
            return session_dict

        except Exception as e:
            logger.error(f"Error logging session: {e}")
            raise Exception(f"Error logging session: {str(e)}")

    def log_logout(self, user_id: str, reason: str = "user_logout") -> Dict[str, Any]:
        """
        End the most recent active session for the given user.
        """
        try:
            if not user_id:
                raise ValueError("user_id is required")

            user_id_str = str(user_id)

            # Find the latest active session for this employee
            sessions = list(SessionLog.employee_index.query(
                "session_logs",
                SessionLog.employee_id == user_id_str,
                filter_condition=SessionLog.status == "active"
            ))
            if not sessions:
                logger.warning(f"No active session found for user_id: {user_id}")
                return {"success": False, "message": "No active session found"}

            # Sort descending by login_time
            sessions.sort(key=lambda x: x.login_time or datetime.min, reverse=True)
            session = sessions[0]

            # End session
            session.end_session(logout_reason=reason, status="ended")
            session_dict = session.to_dict()

            # Send notification
            self._send_session_notification("logout", session_dict, {
                "duration": session.session_duration_seconds,
                "logout_reason": reason
            })

            # Send shift summary email (existing external service)
            try:
                email_result = shift_summary_service.send_shift_summary_email(session_dict)
                if email_result.get('success'):
                    logger.info(f"Shift summary email sent. Recipients: {email_result.get('sent_count', 0)}")
                else:
                    logger.warning(f"Shift summary email failed: {email_result.get('error')}")
            except Exception as email_error:
                logger.error(f"Error sending shift summary email: {email_error}")

            logger.info(f"Logout logged for {session.username} (duration: {session.session_duration_seconds}s)")
            return {
                "success": True,
                "message": "Session logged out successfully",
                "duration": session.session_duration_seconds,
                "session_id": session.sk
            }

        except Exception as e:
            logger.error(f"Error logging logout: {e}")
            raise Exception(f"Error logging logout: {str(e)}")

    # -------------------------------------------------------------------------
    # Query methods
    # -------------------------------------------------------------------------

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Return all active sessions as dictionaries."""
        try:
            sessions = SessionLog.get_active_sessions()
            return [s.to_dict() for s in sessions]
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []

    def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return session history for a specific user (by employee_id)."""
        try:
            user_id_str = str(user_id)
            sessions = []
            # Use EmployeeIndex – sorted by SK (not login_time) so we sort manually
            for session in SessionLog.employee_index.query(
                "session_logs",
                SessionLog.employee_id == user_id_str
            ):
                sessions.append(session.to_dict())

            sessions.sort(key=lambda x: x.get("login_time", ""), reverse=True)
            return sessions[:limit]
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single session by its SK (e.g. 'SES-00001' or '00001')."""
        try:
            session = SessionLog.get_by_id(session_id)
            return session.to_dict() if session else None
        except Exception as e:
            logger.error(f"Error getting session by ID: {e}")
            return None

    def get_session_statistics(self) -> Dict[str, Any]:
        """Return basic statistics: active count, today's sessions, avg duration."""
        try:
            active_count = len(SessionLog.get_active_sessions())
            today_sessions = len(SessionLog.get_today_sessions())

            # Compute average duration from last 100 completed sessions
            sessions = []
            for session in SessionLog.date_index.query(
                "session_logs",
                range_key_condition=SessionLog.login_time >= (datetime.utcnow() - timedelta(days=30)),
                filter_condition=(SessionLog.status == "ended") | (SessionLog.status == "expired"),
                limit=100
            ):
                if session.session_duration_seconds:
                    sessions.append(session)

            total_duration = sum(s.session_duration_seconds or 0 for s in sessions)
            avg_duration = total_duration // len(sessions) if sessions else 0

            return {
                "active_sessions": active_count,
                "today_sessions": today_sessions,
                "avg_session_duration": avg_duration
            }
        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {"active_sessions": 0, "today_sessions": 0, "avg_session_duration": 0}

    # -------------------------------------------------------------------------
    # Cleanup operations
    # -------------------------------------------------------------------------

    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Delete sessions older than specified days (uses DateIndex)."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days_old)
            deleted_count = 0

            # Query all sessions with login_time <= cutoff using the DateIndex
            for session in SessionLog.date_index.query(
                "session_logs",
                SessionLog.login_time <= cutoff
            ):
                try:
                    session.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete session {session.sk}: {e}")

            if deleted_count:
                self._send_session_notification("bulk_cleanup", {
                    "username": "System",
                    "_id": "BULK-CLEANUP"
                }, {
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff.isoformat()
                })

            logger.info(f"Cleaned up {deleted_count} sessions older than {days_old} days")
            return deleted_count
        except Exception as e:
            logger.error(f"Error in cleanup_old_sessions: {e}")
            return 0

    def bulk_expire_user_sessions(self, user_ids: List[str]) -> Dict[str, Any]:
        """Expire all active sessions for the given list of users."""
        try:
            if not user_ids:
                return {"success": False, "message": "No user IDs provided"}

            user_ids = [str(uid) for uid in user_ids]
            expired_count = 0

            for uid in user_ids:
                for session in SessionLog.employee_index.query(
                    "session_logs",
                    SessionLog.employee_id == uid,
                    filter_condition=SessionLog.status == "active"
                ):
                    session.end_session(logout_reason="bulk_expiry", status="expired")
                    expired_count += 1

            if expired_count:
                self._send_session_notification("bulk_cleanup", {
                    "username": "System",
                    "_id": "BULK-EXPIRE"
                }, {
                    "expired_count": expired_count,
                    "user_count": len(user_ids)
                })

            logger.info(f"Bulk expired {expired_count} sessions for {len(user_ids)} users")
            return {"success": True, "expired_count": expired_count, "user_count": len(user_ids)}
        except Exception as e:
            logger.error(f"Error in bulk_expire_user_sessions: {e}")
            return {"success": False, "error": str(e)}

    def auto_cleanup_old_sessions(self, months_old: int = 6) -> Dict[str, Any]:
        """Delete sessions older than specified months (default 6)."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=months_old * 30)
            sessions_to_delete = []
            for session in SessionLog.date_index.query(
                "session_logs",
                SessionLog.login_time <= cutoff
            ):
                sessions_to_delete.append(session)

            if not sessions_to_delete:
                logger.info("No sessions older than {} months found".format(months_old))
                return {"success": True, "deleted_count": 0, "message": "No sessions to cleanup"}

            deleted_count = 0
            for session in sessions_to_delete:
                try:
                    session.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete session {session.sk}: {e}")

            self._send_session_notification("auto_cleanup", {
                "username": "System AutoCleanup",
                "_id": "AUTO-CLEANUP-6M"
            }, {
                "deleted_count": deleted_count,
                "cutoff_date": cutoff.isoformat(),
                "months_old": months_old,
                "cleanup_type": "automatic_6_month"
            })

            logger.info(f"Auto‑cleanup: deleted {deleted_count} sessions older than {months_old} months")
            return {
                "success": True,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff.isoformat(),
                "months_old": months_old
            }
        except Exception as e:
            logger.error(f"Error in auto_cleanup_old_sessions: {e}")
            self._send_session_notification("auto_cleanup_failed", {
                "username": "System AutoCleanup",
                "_id": "AUTO-CLEANUP-ERROR"
            }, {
                "error": str(e),
                "months_old": months_old,
                "cleanup_type": "automatic_6_month_failed"
            })
            return {"success": False, "error": str(e), "deleted_count": 0}

    # -------------------------------------------------------------------------
    # Automated cleanup thread
    # -------------------------------------------------------------------------

    def start_automated_cleanup(self, cleanup_interval_hours: int = 24, months_old: int = 6) -> Dict[str, Any]:
        """Start a background thread that runs auto_cleanup_old_sessions periodically."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return {"success": False, "message": "Cleanup thread already running"}

        def worker():
            logger.info(f"Automated cleanup thread started (interval={cleanup_interval_hours}h, retention={months_old} months)")
            while not self._stop_cleanup:
                try:
                    result = self.auto_cleanup_old_sessions(months_old)
                    if not result.get("success"):
                        logger.error(f"Auto‑cleanup failed: {result.get('error')}")
                except Exception as e:
                    logger.error(f"Error in cleanup worker: {e}")

                # Sleep in 1‑second increments to allow quick stop
                for _ in range(cleanup_interval_hours * 3600):
                    if self._stop_cleanup:
                        break
                    time.sleep(1)
            logger.info("Automated cleanup thread stopped")

        self._stop_cleanup = False
        self._cleanup_thread = threading.Thread(target=worker, daemon=True)
        self._cleanup_thread.start()

        self._send_session_notification("auto_cleanup_started", {
            "username": "System AutoCleanup",
            "_id": "AUTO-CLEANUP-START"
        }, {
            "cleanup_interval_hours": cleanup_interval_hours,
            "months_old": months_old
        })

        return {
            "success": True,
            "message": "Automated cleanup started",
            "interval_hours": cleanup_interval_hours,
            "retention_months": months_old
        }

    def stop_automated_cleanup(self) -> Dict[str, Any]:
        """Stop the background cleanup thread."""
        if not self._cleanup_thread or not self._cleanup_thread.is_alive():
            return {"success": False, "message": "No cleanup thread is running"}

        self._stop_cleanup = True
        self._cleanup_thread.join(timeout=5)

        self._send_session_notification("auto_cleanup_stopped", {
            "username": "System AutoCleanup",
            "_id": "AUTO-CLEANUP-STOP"
        }, {
            "thread_stopped": True,
            "stop_time": datetime.utcnow().isoformat()
        })

        return {"success": True, "message": "Automated cleanup stopped"}

    def get_cleanup_status(self) -> Dict[str, Any]:
        """Return current status of the automated cleanup thread and data age."""
        try:
            is_running = self._cleanup_thread and self._cleanup_thread.is_alive()
            six_months_ago = datetime.utcnow() - timedelta(days=180)

            # Count sessions older than 6 months
            old_count = 0
            for _ in SessionLog.date_index.query(
                "session_logs",
                SessionLog.login_time <= six_months_ago,
                limit=1000   # limit for performance, approximate
            ):
                old_count += 1

            # Oldest session date
            oldest = None
            # Use DateIndex with forward scan to get earliest login_time
            for session in SessionLog.date_index.query(
                "session_logs",
                range_key_condition=SessionLog.login_time > datetime.min,
                scan_index_forward=True,
                limit=1
            ):
                oldest = session.login_time

            return {
                "automated_cleanup_running": is_running,
                "thread_id": self._cleanup_thread.ident if is_running else None,
                "sessions_older_than_6_months": old_count,
                "oldest_session_date": oldest.isoformat() if oldest else None,
                "next_cleanup_eligible": old_count > 0,
                "cutoff_date_6_months": six_months_ago.isoformat(),
                "cleanup_schedule": "Monthly (every 30 days)",
                "retention_policy": "6 months"
            }
        except Exception as e:
            logger.error(f"Error getting cleanup status: {e}")
            return {"automated_cleanup_running": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Manual cleanup with export
    # -------------------------------------------------------------------------

    def manual_cleanup_with_date_range(self, start_date=None, end_date=None, dry_run=False) -> Dict[str, Any]:
        """
        Delete sessions within a date range. If dry_run=True, only count and preview.
        Uses DateIndex for efficient query.
        """
        try:
            # Parse/calculate dates
            if not start_date and not end_date:
                end_date = datetime.utcnow() - timedelta(days=180)
                start_date = datetime(2020, 1, 1)
            else:
                if start_date and isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date)
                if end_date and isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date)

            # Build condition – we need a range key condition on login_time.
            # Since we only have ≤ and ≥, we must query once with one bound and filter the other.
            # For simplicity, use the more restrictive lower bound and filter the upper bound.
            query_condition = None
            if start_date:
                query_condition = SessionLog.login_time >= start_date
            else:
                query_condition = SessionLog.login_time > datetime.min

            sessions = []
            for session in SessionLog.date_index.query(
                "session_logs",
                range_key_condition=query_condition
            ):
                if end_date and session.login_time and session.login_time > end_date:
                    continue
                sessions.append(session)

            sample = [
                {
                    "session_id": s.sk,
                    "username": s.username,
                    "login_time": s.login_time.isoformat() if s.login_time else None,
                    "status": s.status
                }
                for s in sessions[:10]
            ]

            deleted_count = 0
            if not dry_run:
                for session in sessions:
                    try:
                        session.delete()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {session.sk}: {e}")

                self._send_session_notification("manual_cleanup", {
                    "username": "Manual Cleanup",
                    "_id": "MANUAL-CLEANUP"
                }, {
                    "deleted_count": deleted_count,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "dry_run": dry_run,
                    "sample_sessions": sample
                })

            logger.info(f"Manual cleanup ({'dry run' if dry_run else 'executed'}): {len(sessions)} found, {deleted_count} deleted")
            return {
                "success": True,
                "sessions_found": len(sessions),
                "deleted_count": deleted_count,
                "sample_sessions": sample,
                "dry_run": dry_run,
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
        except Exception as e:
            logger.error(f"Error in manual_cleanup_with_date_range: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # CSV export
    # -------------------------------------------------------------------------

    @staticmethod
    def _export_sessions_to_csv(sessions: List[SessionLog], export_path: str) -> Dict[str, Any]:
        """Write a list of SessionLog objects to a CSV file."""
        try:
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            fieldnames = [
                'session_id', 'user_id', 'username', 'branch_id',
                'login_time', 'logout_time', 'session_duration', 'status',
                'logout_reason', 'source'
            ]

            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for session in sessions:
                    d = session.to_dict()
                    writer.writerow({
                        'session_id': d.get('session_id', ''),
                        'user_id': d.get('employee_id', ''),
                        'username': d.get('username', ''),
                        'branch_id': d.get('branch_id', ''),
                        'login_time': d.get('login_time', ''),
                        'logout_time': d.get('logout_time', ''),
                        'session_duration': d.get('session_duration_seconds', ''),
                        'status': d.get('status', ''),
                        'logout_reason': d.get('logout_reason', ''),
                        'source': d.get('source', '')
                    })
            return {"success": True, "exported_count": len(sessions), "export_path": export_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def manual_cleanup_with_export(self, start_date=None, end_date=None, export_path=None, dry_run=False) -> Dict[str, Any]:
        """
        Export sessions in a date range to CSV, then optionally delete them.
        """
        try:
            # Same date parsing as above
            if not start_date and not end_date:
                end_date = datetime.utcnow() - timedelta(days=180)
                start_date = datetime(2020, 1, 1)
            else:
                if start_date and isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date)
                if end_date and isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date)

            query_condition = None
            if start_date:
                query_condition = SessionLog.login_time >= start_date
            else:
                query_condition = SessionLog.login_time > datetime.min

            sessions = []
            for session in SessionLog.date_index.query(
                "session_logs",
                range_key_condition=query_condition
            ):
                if end_date and session.login_time and session.login_time > end_date:
                    continue
                sessions.append(session)

            if not sessions:
                return {
                    "success": True,
                    "sessions_found": 0,
                    "deleted_count": 0,
                    "exported_count": 0,
                    "dry_run": dry_run,
                    "message": "No sessions found in date range"
                }

            # Generate default export path if not provided
            if not export_path:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                date_range = f"{start_date.strftime('%Y%m%d') if start_date else 'start'}_to_{end_date.strftime('%Y%m%d') if end_date else 'end'}"
                export_filename = f"session_cleanup_export_{date_range}_{timestamp}.csv"
                export_path = os.path.join("exports", export_filename)

            export_result = self._export_sessions_to_csv(sessions, export_path)
            if not export_result["success"]:
                return {"success": False, "error": f"Export failed: {export_result['error']}"}

            deleted_count = 0
            if not dry_run:
                for session in sessions:
                    try:
                        session.delete()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {session.sk}: {e}")

                self._send_session_notification("manual_cleanup_with_export", {
                    "username": "Manual Cleanup with Export",
                    "_id": "MANUAL-CLEANUP-EXPORT"
                }, {
                    "deleted_count": deleted_count,
                    "exported_count": len(sessions),
                    "export_file": export_path,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "dry_run": dry_run
                })

            logger.info(f"Manual cleanup with export ({'dry run' if dry_run else 'executed'}): {len(sessions)} sessions, {deleted_count} deleted, export {export_path}")
            return {
                "success": True,
                "sessions_found": len(sessions),
                "deleted_count": deleted_count,
                "exported_count": len(sessions),
                "export_file": export_path,
                "dry_run": dry_run,
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
        except Exception as e:
            logger.error(f"Error in manual_cleanup_with_export: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Destructor – stop cleanup thread
    # -------------------------------------------------------------------------

    def __del__(self):
        if hasattr(self, '_cleanup_thread') and self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_cleanup = True
            try:
                self._cleanup_thread.join(timeout=2)
            except:
                pass


class SessionDisplayService:
    """
    Service for retrieving and formatting session logs for UI display.
    Replaces the MongoDB version – uses SessionLog model and GSIs.
    """

    def __init__(self):
        pass   # No more MongoDB collections

    def get_session_logs(self, limit: int = 100, status_filter: Optional[str] = None,
                         user_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Return a list of formatted session logs.
        Uses DateIndex to get recent sessions, then applies filters in memory.
        """
        try:
            # Start with the most recent sessions using the DateIndex (sorted descending)
            iterator = SessionLog.date_index.query(
                "session_logs",
                range_key_condition=SessionLog.login_time > datetime.min,
                scan_index_forward=False,   # descending order
                limit=limit * 2             # extra to allow filtering
            )

            sessions = []
            for session in iterator:
                # Apply status filter
                if status_filter and session.status != status_filter:
                    continue
                # Apply user filter (match username or employee_id)
                if user_filter:
                    username = session.username or ""
                    emp_id = session.employee_id or ""
                    if user_filter.lower() not in username.lower() and user_filter.lower() not in emp_id.lower():
                        continue
                sessions.append(session)
                if len(sessions) >= limit:
                    break

            formatted_logs = []
            for session in sessions:
                d = session.to_dict()
                # Human-readable duration
                duration_seconds = d.get("session_duration_seconds")
                if duration_seconds and duration_seconds > 0:
                    if duration_seconds < 60:
                        duration_str = f"{int(duration_seconds)}s"
                    elif duration_seconds < 3600:
                        minutes = int(duration_seconds // 60)
                        seconds = int(duration_seconds % 60)
                        duration_str = f"{minutes}m {seconds}s"
                    else:
                        hours = int(duration_seconds // 3600)
                        minutes = int((duration_seconds % 3600) // 60)
                        duration_str = f"{hours}h {minutes}m"
                else:
                    duration_str = "Active" if d.get("status") == "active" else "0s"

                log_entry = {
                    "log_id": d.get("session_id", ""),
                    "user_id": d.get("employee_id", ""),
                    "ref_id": d.get("session_id", ""),
                    "event_type": "Session",
                    "amount_qty": duration_str,
                    "status": d.get("status", "Unknown").title(),
                    "timestamp": d.get("login_time"),
                    "remarks": f"User: {d.get('username', 'Unknown')}, Status: {d.get('status', 'Unknown')}, Duration: {duration_str}",
                    "username": d.get("username", "Unknown"),
                    "login_time": d.get("login_time"),
                    "logout_time": d.get("logout_time"),
                    "branch_id": d.get("branch_id", "N/A"),
                    "logout_reason": d.get("logout_reason")
                }
                formatted_logs.append(log_entry)

            return {
                "success": True,
                "data": formatted_logs,
                "count": len(formatted_logs)
            }
        except Exception as e:
            logger.error(f"Error in get_session_logs: {e}")
            return {"success": False, "error": str(e), "data": []}

    def get_combined_logs(self, limit: int = 100, log_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Return session logs (audit logs are omitted – only session logs).
        Kept for compatibility with original interface.
        """
        # Original method combined session + audit logs. Here we return only session logs.
        session_result = self.get_session_logs(limit=limit, status_filter=None, user_filter=None)
        return {
            "success": session_result["success"],
            "data": session_result["data"],
            "total_count": session_result["count"]
        }

    def export_session_logs(self, export_format: str = "csv", date_filter: Optional[Dict] = None,
                            status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Export sessions matching the given filters.
        Returns data in the requested format (only 'csv' or 'json').
        """
        try:
            # Build filter condition for scan
            conditions = []
            if date_filter:
                start_date = date_filter.get("start_date")
                end_date = date_filter.get("end_date")
                if start_date:
                    start_dt = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
                    conditions.append(SessionLog.login_time >= start_dt)
                if end_date:
                    end_dt = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
                    conditions.append(SessionLog.login_time <= end_dt)
            if status_filter:
                conditions.append(SessionLog.status == status_filter)

            filter_condition = None
            for cond in conditions:
                filter_condition = cond if filter_condition is None else (filter_condition & cond)

            sessions = []
            for session in SessionLog.scan(filter_condition=filter_condition):
                sessions.append(session)

            export_data = []
            for s in sessions:
                d = s.to_dict()
                export_data.append({
                    "session_id": d.get("session_id"),
                    "user_id": d.get("employee_id"),
                    "username": d.get("username"),
                    "login_time": d.get("login_time"),
                    "logout_time": d.get("logout_time"),
                    "duration": d.get("session_duration_seconds"),
                    "status": d.get("status"),
                    "branch_id": d.get("branch_id"),
                    "logout_reason": d.get("logout_reason")
                })

            return {
                "success": True,
                "data": export_data,
                "format": export_format,
                "count": len(export_data)
            }
        except Exception as e:
            logger.error(f"Error exporting session logs: {e}")
            return {"success": False, "error": str(e)}
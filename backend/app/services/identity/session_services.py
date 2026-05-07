import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import threading
import time

from models.Sessions import SessionLog
from notifications.services import notification_service

logger = logging.getLogger(__name__)


class SessionLogService:
    def __init__(self):
        self.notification_service = notification_service
        self._cleanup_thread = None
        self._stop_cleanup = False

    # ==================== Notification Helper ====================

    def _send_session_notification(self, action_type: str, session_data: dict,
                                   additional_metadata: dict = None):
        try:
            username = session_data.get("username", "Unknown User")
            session_id = session_data.get("session_id", session_data.get("sk", "Unknown"))

            notification_config = {
                "login": {"message": f"User {username} logged in successfully", "priority": "info"},
                "logout": {"message": f"User {username} logged out", "priority": "info"},
                "expired": {"message": f"Session expired for user {username}", "priority": "medium"},
                "replaced": {"message": f"Session replaced by new login for user {username}", "priority": "low"},
                "bulk_cleanup": {"message": "Bulk session cleanup completed", "priority": "low"},
                "auto_cleanup": {
                    "message": f"Automatic cleanup completed - {(additional_metadata or {}).get('deleted_count', 0)} sessions removed",
                    "priority": "medium"
                },
                "auto_cleanup_failed": {
                    "message": f"Automatic cleanup failed: {(additional_metadata or {}).get('error', 'Unknown error')}",
                    "priority": "high"
                },
                "auto_cleanup_started": {
                    "message": f"Automated session cleanup started (every {(additional_metadata or {}).get('cleanup_interval_hours', 24)}h)",
                    "priority": "medium"
                },
                "auto_cleanup_stopped": {"message": "Automated session cleanup stopped", "priority": "medium"},
                "manual_cleanup": {
                    "message": f"Manual session cleanup completed - {(additional_metadata or {}).get('deleted_count', 0)} sessions removed",
                    "priority": "medium"
                },
            }

            config = notification_config.get(action_type, {
                "message": f"Session action '{action_type}' for user {username}",
                "priority": "info"
            })

            metadata = {
                "session_id": session_id,
                "username": username,
                "action_type": action_type,
                "branch_id": session_data.get("branch_id", "N/A"),
                "timestamp": datetime.utcnow().isoformat()
            }
            if additional_metadata:
                metadata.update(additional_metadata)

            self.notification_service.create_notification(
                title=f"Session {action_type.replace('_', ' ').title()}",
                message=config["message"],
                notification_type="session_management",
                priority=config["priority"],
                metadata=metadata
            )
        except Exception as e:
            logger.warning(f"Failed to send session notification: {e}")

    # ==================== Core Session Operations ====================

    def _close_existing_sessions(self, username: str):
        """End any active sessions for a user before creating a new one."""
        try:
            active_sessions = list(SessionLog.username_index.query(
                "session_logs",
                SessionLog.username == username,
                filter_condition=SessionLog.status == "active"
            ))

            for session in active_sessions:
                try:
                    session.end_session(logout_reason="new_login", status="ended")
                    self._send_session_notification("replaced", session.to_simple_dict())
                except Exception as e:
                    logger.warning(f"Failed to close session {session.sk}: {e}")

            if active_sessions:
                logger.info(f"Closed {len(active_sessions)} existing sessions for user {username}")

        except Exception as e:
            logger.error(f"Error closing existing sessions for {username}: {e}")

    def log_login(self, user_data: dict) -> dict:
        """Create a session log entry on user login."""
        try:
            username = (
                user_data.get("username") or
                user_data.get("email") or
                "unknown"
            )
            if not username or username == "unknown":
                raise ValueError("username is required")

            branch_id = str(user_data.get("branch_id", "1"))

            self._close_existing_sessions(username)

            session_log = SessionLog.create_session_log(
                username=username,
                branch_id=branch_id,
                source=user_data.get("source", "auth_service"),
                employee_id=user_data.get("employee_id") or user_data.get("user_id"),
                employee_name=user_data.get("employee_name") or user_data.get("full_name"),
                role=user_data.get("role"),
                shift_type=user_data.get("shift_type"),
            )

            self._send_session_notification("login", session_log.to_simple_dict())
            logger.info(f"Login session {session_log.sk} logged for user {username}")
            return session_log.to_dict()

        except Exception as e:
            logger.error(f"Error logging session: {e}")
            raise

    def log_logout(self, username: str, reason: str = "user_logout") -> dict:
        """End the most recent active session for a user."""
        try:
            if not username:
                raise ValueError("username is required")

            active_sessions = list(SessionLog.username_index.query(
                "session_logs",
                SessionLog.username == username,
                filter_condition=SessionLog.status == "active"
            ))

            if not active_sessions:
                logger.warning(f"No active session found for user: {username}")
                return {"success": False, "message": "No active session found"}

            session = max(active_sessions, key=lambda s: s.login_time or datetime.min)
            session.end_session(logout_reason=reason, status="ended")

            session_dict = session.to_dict()
            # shift_summary_service expects 'user_id' key
            session_dict["user_id"] = session.employee_id

            self._send_session_notification("logout", session_dict, {
                "duration": session.session_duration_seconds,
                "logout_reason": reason
            })

            try:
                from notifications.shift_summary_service import shift_summary_service
                email_result = shift_summary_service.send_shift_summary_email(session_dict)
                if email_result.get("success"):
                    logger.info(f"Shift summary email sent for user {username}")
                else:
                    logger.warning(f"Shift summary email failed: {email_result.get('error')}")
            except Exception as email_error:
                logger.error(f"Error sending shift summary email: {email_error}")

            logger.info(f"Logout logged for user {username} (duration: {session.session_duration_seconds}s)")
            return {
                "success": True,
                "message": "Session logged out successfully",
                "duration": session.session_duration_seconds,
                "session_id": session.sk
            }

        except Exception as e:
            logger.error(f"Error logging logout: {e}")
            raise

    def get_active_sessions(self) -> List[dict]:
        """Get all currently active sessions."""
        try:
            sessions = SessionLog.get_active_sessions()
            return [s.to_simple_dict() for s in sessions]
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []

    def get_user_sessions(self, username: str, limit: int = 50) -> List[dict]:
        """Get session history for a specific user."""
        try:
            sessions = SessionLog.get_employee_sessions(username)
            return [s.to_simple_dict() for s in sessions[:limit]]
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    def get_session_by_id(self, session_id: str) -> Optional[dict]:
        """Get session by ID (SESS-#####)."""
        try:
            session = SessionLog.get_by_id(session_id)
            return session.to_dict() if session else None
        except Exception as e:
            logger.error(f"Error getting session by ID: {e}")
            return None

    def get_session_statistics(self) -> dict:
        """Get session statistics."""
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            active_sessions = SessionLog.get_active_sessions()
            active_count = len(active_sessions)

            today_sessions = list(SessionLog.date_index.query(
                "session_logs",
                SessionLog.login_time.between(today_start, today_end)
            ))
            today_count = len(today_sessions)

            thirty_days_ago = now - timedelta(days=30)
            recent_ended = list(SessionLog.date_index.query(
                "session_logs",
                SessionLog.login_time >= thirty_days_ago,
                filter_condition=SessionLog.session_duration_seconds.exists()
            ))
            avg_duration = 0
            if recent_ended:
                total = sum(s.session_duration_seconds or 0 for s in recent_ended)
                avg_duration = int(total // len(recent_ended))

            return {
                "active_sessions": active_count,
                "today_sessions": today_count,
                "avg_session_duration": avg_duration
            }

        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {"active_sessions": 0, "today_sessions": 0, "avg_session_duration": 0}

    # ==================== Cleanup Operations ====================

    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Delete ended/expired sessions older than specified days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            old_sessions = list(SessionLog.date_index.query(
                "session_logs",
                SessionLog.login_time < cutoff_date,
                filter_condition=(
                    (SessionLog.status == "ended") |
                    (SessionLog.status == "expired") |
                    (SessionLog.status == "terminated")
                )
            ))

            if not old_sessions:
                return 0

            with SessionLog.batch_write() as batch:
                for session in old_sessions:
                    batch.delete(session)

            deleted_count = len(old_sessions)
            self._send_session_notification("bulk_cleanup", {
                "username": "System", "session_id": "BULK-CLEANUP", "branch_id": "N/A"
            }, {"deleted_count": deleted_count, "cutoff_date": cutoff_date.isoformat()})

            logger.info(f"Cleaned up {deleted_count} old sessions")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")
            return 0

    def bulk_expire_user_sessions(self, usernames: List[str]) -> dict:
        """Bulk end active sessions for multiple users."""
        try:
            if not usernames:
                return {"success": False, "message": "No usernames provided"}

            expired_count = 0
            errors = []

            for username in usernames:
                try:
                    active_sessions = list(SessionLog.username_index.query(
                        "session_logs",
                        SessionLog.username == username,
                        filter_condition=SessionLog.status == "active"
                    ))
                    for session in active_sessions:
                        session.end_session(logout_reason="bulk_expiry", status="expired")
                        expired_count += 1
                except Exception as e:
                    errors.append(f"Failed for {username}: {str(e)}")

            if errors:
                logger.warning(f"Bulk expire errors: {errors}")

            if expired_count > 0:
                self._send_session_notification("bulk_cleanup", {
                    "username": "System", "session_id": "BULK-EXPIRE", "branch_id": "N/A"
                }, {"expired_count": expired_count, "user_count": len(usernames)})

            logger.info(f"Bulk expired {expired_count} sessions for {len(usernames)} users")
            return {"success": True, "expired_count": expired_count, "user_count": len(usernames)}

        except Exception as e:
            logger.error(f"Error in bulk expire sessions: {e}")
            return {"success": False, "error": str(e)}

    def auto_cleanup_old_sessions(self, months_old: int = 6) -> dict:
        """Delete sessions older than specified months."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=months_old * 30)
            old_sessions = list(SessionLog.date_index.query(
                "session_logs",
                SessionLog.login_time < cutoff_date
            ))

            if not old_sessions:
                logger.info("No sessions found beyond retention period")
                return {"success": True, "deleted_count": 0, "message": "No sessions to cleanup"}

            with SessionLog.batch_write() as batch:
                for session in old_sessions:
                    batch.delete(session)

            deleted_count = len(old_sessions)
            self._send_session_notification("auto_cleanup", {
                "username": "System AutoCleanup", "session_id": "AUTO-CLEANUP", "branch_id": "N/A"
            }, {"deleted_count": deleted_count, "cutoff_date": cutoff_date.isoformat(), "months_old": months_old})

            logger.info(f"Auto-cleanup: Deleted {deleted_count} sessions older than {months_old} months")
            return {
                "success": True,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "months_old": months_old
            }

        except Exception as e:
            logger.error(f"Error in auto cleanup: {e}")
            self._send_session_notification("auto_cleanup_failed", {
                "username": "System AutoCleanup", "session_id": "AUTO-CLEANUP-ERROR", "branch_id": "N/A"
            }, {"error": str(e), "months_old": months_old})
            return {"success": False, "error": str(e), "deleted_count": 0}

    def manual_cleanup_with_date_range(self, start_date=None, end_date=None, dry_run: bool = False) -> dict:
        """Manual cleanup for a specific date range."""
        try:
            if not start_date and not end_date:
                end_date = datetime.utcnow() - timedelta(days=180)
                start_date = datetime(2020, 1, 1)
            else:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date)
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date)

            if start_date and end_date:
                target_sessions = list(SessionLog.date_index.query(
                    "session_logs",
                    SessionLog.login_time.between(start_date, end_date)
                ))
            elif start_date:
                target_sessions = list(SessionLog.date_index.query(
                    "session_logs",
                    SessionLog.login_time >= start_date
                ))
            else:
                target_sessions = list(SessionLog.date_index.query(
                    "session_logs",
                    SessionLog.login_time < end_date
                ))

            sessions_count = len(target_sessions)
            if sessions_count == 0:
                return {
                    "success": True, "deleted_count": 0,
                    "message": "No sessions found in specified date range", "dry_run": dry_run
                }

            sample = [s.to_simple_dict() for s in target_sessions[:10]]
            deleted_count = 0

            if not dry_run:
                with SessionLog.batch_write() as batch:
                    for session in target_sessions:
                        batch.delete(session)
                deleted_count = sessions_count

                self._send_session_notification("manual_cleanup", {
                    "username": "Manual Cleanup", "session_id": "MANUAL-CLEANUP", "branch_id": "N/A"
                }, {
                    "deleted_count": deleted_count,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                })

            logger.info(f"Manual cleanup ({'DRY RUN' if dry_run else 'EXECUTED'}): {sessions_count} sessions affected")
            return {
                "success": True,
                "sessions_found": sessions_count,
                "deleted_count": deleted_count,
                "sample_sessions": sample,
                "dry_run": dry_run,
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }

        except Exception as e:
            logger.error(f"Error in manual cleanup: {e}")
            return {"success": False, "error": str(e)}

    # ==================== Automated Cleanup Thread ====================

    def start_automated_cleanup(self, cleanup_interval_hours: int = 24, months_old: int = 6) -> dict:
        """Start automated cleanup thread."""
        try:
            if self._cleanup_thread and self._cleanup_thread.is_alive():
                return {"success": False, "message": "Cleanup thread already running"}

            def cleanup_worker():
                logger.info(f"Starting automated session cleanup (every {cleanup_interval_hours}h)")
                while not self._stop_cleanup:
                    try:
                        result = self.auto_cleanup_old_sessions(months_old)
                        if result["success"]:
                            logger.info(f"Automated cleanup: {result['deleted_count']} sessions deleted")
                        else:
                            logger.error(f"Automated cleanup failed: {result.get('error')}")
                        for _ in range(cleanup_interval_hours * 3600):
                            if self._stop_cleanup:
                                break
                            time.sleep(1)
                    except Exception as e:
                        logger.error(f"Error in cleanup worker: {e}")
                        time.sleep(3600)
                logger.info("Automated cleanup thread stopped")

            self._stop_cleanup = False
            self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
            self._cleanup_thread.start()

            self._send_session_notification("auto_cleanup_started", {
                "username": "System AutoCleanup", "session_id": "AUTO-CLEANUP-START", "branch_id": "N/A"
            }, {"cleanup_interval_hours": cleanup_interval_hours, "months_old": months_old})

            logger.info(f"Automated cleanup started (interval: {cleanup_interval_hours}h, retention: {months_old} months)")
            return {
                "success": True,
                "message": "Automated cleanup started",
                "interval_hours": cleanup_interval_hours,
                "retention_months": months_old
            }

        except Exception as e:
            logger.error(f"Error starting automated cleanup: {e}")
            return {"success": False, "error": str(e)}

    def stop_automated_cleanup(self) -> dict:
        """Stop the automated cleanup thread."""
        try:
            if not self._cleanup_thread or not self._cleanup_thread.is_alive():
                return {"success": False, "message": "No cleanup thread is running"}

            self._stop_cleanup = True
            self._cleanup_thread.join(timeout=5)

            self._send_session_notification("auto_cleanup_stopped", {
                "username": "System AutoCleanup", "session_id": "AUTO-CLEANUP-STOP", "branch_id": "N/A"
            }, {"stop_time": datetime.utcnow().isoformat()})

            logger.info("Automated cleanup thread stopped")
            return {"success": True, "message": "Automated cleanup stopped"}

        except Exception as e:
            logger.error(f"Error stopping automated cleanup: {e}")
            return {"success": False, "error": str(e)}

    def get_cleanup_status(self) -> dict:
        """Get automated cleanup thread status and retention stats."""
        try:
            is_running = bool(self._cleanup_thread and self._cleanup_thread.is_alive())
            six_months_ago = datetime.utcnow() - timedelta(days=180)

            old_sessions = list(SessionLog.date_index.query(
                "session_logs",
                SessionLog.login_time < six_months_ago
            ))
            old_count = len(old_sessions)

            oldest_date = None
            if old_sessions:
                oldest = min(old_sessions, key=lambda s: s.login_time or datetime.utcnow())
                if oldest.login_time:
                    oldest_date = oldest.login_time.isoformat()

            return {
                "automated_cleanup_running": is_running,
                "cleanup_schedule": "Monthly (every 30 days)",
                "thread_id": self._cleanup_thread.ident if is_running else None,
                "sessions_older_than_6_months": old_count,
                "oldest_session_date": oldest_date,
                "next_cleanup_eligible": old_count > 0,
                "cutoff_date_6_months": six_months_ago.isoformat(),
                "next_cleanup_estimate": (
                    (datetime.utcnow() + timedelta(days=30)).isoformat() if is_running else None
                ),
                "retention_policy": "6 months",
                "cleanup_frequency": "Monthly"
            }

        except Exception as e:
            logger.error(f"Error getting cleanup status: {e}")
            return {"automated_cleanup_running": False, "error": str(e)}

    # ==================== CSV Export ====================

    def _export_sessions_to_csv(self, sessions_data: List[dict], export_path: str) -> dict:
        """Export a list of session dicts to CSV."""
        try:
            fieldnames = [
                "session_id", "username", "branch_id",
                "login_time", "logout_time", "session_duration", "status",
                "logout_reason", "source", "role"
            ]
            os.makedirs(os.path.dirname(export_path) or ".", exist_ok=True)

            with open(export_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for session in sessions_data:
                    writer.writerow({field: session.get(field, "") for field in fieldnames})

            logger.info(f"Exported {len(sessions_data)} sessions to {export_path}")
            return {"success": True, "exported_count": len(sessions_data), "export_path": export_path}

        except Exception as e:
            logger.error(f"Error exporting sessions to CSV: {e}")
            return {"success": False, "error": str(e)}

    def __del__(self):
        if hasattr(self, "_cleanup_thread") and self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_cleanup = True
            try:
                self._cleanup_thread.join(timeout=2)
            except Exception:
                pass


class SessionDisplayService:
    def get_session_logs(self, limit: int = 100, status_filter: str = None,
                         user_filter: str = None) -> dict:
        """Get formatted session logs from DynamoDB."""
        try:
            if user_filter:
                sessions = list(SessionLog.username_index.query(
                    "session_logs",
                    SessionLog.username == user_filter
                ))
            else:
                filter_cond = (SessionLog.status == status_filter) if status_filter else None
                sessions = list(SessionLog.query("session_logs", filter_condition=filter_cond))

            sessions.sort(key=lambda s: s.login_time or datetime.min, reverse=True)

            formatted_logs = []
            for session in sessions[:limit]:
                try:
                    duration_str = session.get_duration_human_readable()
                    data = session.to_dict()
                    formatted_logs.append({
                        "log_id": session.sk,
                        "username": data.get("username"),
                        "employee_name": data.get("employee_name"),
                        "branch_id": data.get("branch_id", "N/A"),
                        "event_type": "Session",
                        "amount_qty": duration_str,
                        "status": data.get("status", "").title(),
                        "timestamp": data.get("login_time"),
                        "login_time": data.get("login_time"),
                        "logout_time": data.get("logout_time"),
                        "logout_reason": data.get("logout_reason"),
                        "role": data.get("role"),
                        "remarks": f"User: {data.get('username')}, Status: {data.get('status')}, Duration: {duration_str}",
                        "log_source": "session"
                    })
                except Exception as log_error:
                    logger.error(f"Error processing session log {session.sk}: {log_error}")

            return {"success": True, "data": formatted_logs, "count": len(formatted_logs)}

        except Exception as e:
            logger.error(f"Error getting session logs: {e}")
            return {"success": False, "error": str(e), "data": []}

    def get_combined_logs(self, limit: int = 100, log_type: str = None) -> dict:
        """Get combined session and audit logs."""
        try:
            all_logs = []

            if log_type in [None, "all", "session"]:
                session_limit = limit // 2 if log_type == "all" else limit
                session_result = self.get_session_logs(session_limit)
                if session_result["success"]:
                    all_logs.extend(session_result["data"])

            if log_type in [None, "all", "audit"]:
                try:
                    audit_limit = limit // 2 if log_type == "all" else limit
                    from models.Audit import AuditLog
                    audit_logs = list(AuditLog.query("audit_logs"))[:audit_limit]
                    for audit in audit_logs:
                        all_logs.append({
                            "log_id": audit.sk,
                            "username": getattr(audit, "username", "Unknown"),
                            "branch_id": getattr(audit, "branch_id", "N/A"),
                            "event_type": (getattr(audit, "action", "") or "").replace("_", " ").title(),
                            "amount_qty": self._format_audit_changes(audit),
                            "status": getattr(audit, "status", "Completed").title(),
                            "timestamp": getattr(audit, "timestamp", None),
                            "remarks": getattr(audit, "description", ""),
                            "target_type": getattr(audit, "target_type", None),
                            "log_source": "audit"
                        })
                except Exception as audit_error:
                    logger.warning(f"Could not fetch audit logs: {audit_error}")

            try:
                all_logs.sort(key=lambda x: x.get("timestamp") or datetime.min, reverse=True)
            except Exception:
                pass

            return {"success": True, "data": all_logs[:limit], "total_count": len(all_logs)}

        except Exception as e:
            logger.error(f"Error getting combined logs: {e}")
            return {"success": False, "error": str(e), "data": []}

    def _format_audit_changes(self, audit_log) -> str:
        action = (getattr(audit_log, "action", "") or "").lower()
        if "create" in action:
            return "Created"
        elif "delete" in action:
            return "Deleted"
        elif "update" in action:
            return "Updated"
        return "N/A"

    def export_session_logs(self, export_format: str = "csv", date_filter: dict = None,
                            status_filter: str = None) -> dict:
        """Export session logs, optionally filtered by date range and status."""
        try:
            filter_cond = (SessionLog.status == status_filter) if status_filter else None

            if date_filter:
                start_date = datetime.fromisoformat(date_filter.get("start_date"))
                end_date = datetime.fromisoformat(date_filter.get("end_date"))
                sessions = list(SessionLog.date_index.query(
                    "session_logs",
                    SessionLog.login_time.between(start_date, end_date),
                    filter_condition=filter_cond
                ))
            else:
                sessions = list(SessionLog.query("session_logs", filter_condition=filter_cond))

            return {
                "success": True,
                "data": [s.to_dict() for s in sessions],
                "format": export_format,
                "count": len(sessions)
            }

        except Exception as e:
            logger.error(f"Error exporting session logs: {e}")
            return {"success": False, "error": str(e)}

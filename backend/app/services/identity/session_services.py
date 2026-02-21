import csv
import os
from datetime import datetime, timedelta
from ...database import db_manager
from notifications.services import notification_service
from notifications.shift_summary_service import shift_summary_service
import logging
import threading
import time

logger = logging.getLogger(__name__)

class SessionLogService:
    def __init__(self):
        self.db = db_manager.get_database()
        self.collection = self.db.session_logs
        self.notification_service = notification_service
        self._cleanup_thread = None
        self._stop_cleanup = False

    def generate_session_id(self):
        """Generate sequential SESS-##### ID"""
        try:
            # Use aggregation to find the highest existing session number
            pipeline = [
                {
                    "$match": {
                        "_id": {"$regex": "^SESS-"}
                    }
                },
                {
                    "$addFields": {
                        "session_number": {
                            "$toInt": {
                                "$substr": ["$_id", 5, -1]
                            }
                        }
                    }
                },
                {
                    "$sort": {"session_number": -1}
                },
                {
                    "$limit": 1
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                next_number = result[0]["session_number"] + 1
            else:
                # Fallback to count-based method
                count = self.collection.count_documents({"_id": {"$regex": "^SESS-"}})
                next_number = count + 1
            
            return f"SESS-{next_number:05d}"
            
        except Exception as e:
            logger.error(f"Error generating session ID: {e}")
            # Emergency fallback
            timestamp = int(datetime.utcnow().timestamp())
            return f"SESS-{timestamp % 99999:05d}"

    def _send_session_notification(self, action_type, session_data, additional_metadata=None):
        """Enhanced notification helper with new cleanup actions"""
        try:
            username = session_data.get("username", "Unknown User")
            session_id = session_data.get("_id", "Unknown")
            
            # Enhanced notification messages for cleanup actions
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
                    "message": f"Automatic 6-month cleanup completed - {additional_metadata.get('deleted_count', 0)} sessions removed",
                    "priority": "medium"
                },
                "auto_cleanup_failed": {
                    "message": f"Automatic cleanup failed: {additional_metadata.get('error', 'Unknown error')}",
                    "priority": "high"
                },
                "auto_cleanup_started": {
                    "message": f"Automated session cleanup started (every {additional_metadata.get('cleanup_interval_hours', 24)}h)",
                    "priority": "medium"
                },
                "auto_cleanup_stopped": {
                    "message": "Automated session cleanup stopped",
                    "priority": "medium"
                },
                "manual_cleanup": {
                    "message": f"Manual session cleanup completed - {additional_metadata.get('deleted_count', 0)} sessions removed",
                    "priority": "medium"
                }
            }
            
            config = notification_config.get(action_type, {
                "message": f"Session action '{action_type}' for user {username}",
                "priority": "info"
            })
            
            # Prepare metadata (removed ip_address)
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

    def _close_existing_sessions(self, user_id):
        """Close any existing active sessions for a user (string-based)"""
        try:
            cutoff_time = datetime.utcnow()
            
            # Close sessions older than 24 hours
            expired_result = self.collection.update_many(
                {
                    "user_id": user_id,
                    "status": "active",
                    "login_time": {"$lt": cutoff_time - timedelta(hours=24)}
                },
                {
                    "$set": {
                        "logout_time": cutoff_time,
                        "status": "expired",
                        "logout_reason": "session_expired"
                    }
                }
            )
            
            # Get session data for notifications before closing
            recent_sessions = list(self.collection.find(
                {
                    "user_id": user_id,
                    "status": "active"
                },
                {"_id": 1, "username": 1, "branch_id": 1}
            ))
            
            # Close recent active sessions (new login replaces old)
            replaced_result = self.collection.update_many(
                {
                    "user_id": user_id,
                    "status": "active"
                },
                {
                    "$set": {
                        "logout_time": cutoff_time,
                        "status": "replaced",
                        "logout_reason": "new_login"
                    }
                }
            )
            
            # Send notifications for closed sessions
            total_closed = expired_result.modified_count + replaced_result.modified_count
            if total_closed > 0:
                logger.info(f"Closed {total_closed} existing sessions for user {user_id}")
                
                # Send notification for replaced sessions
                for session in recent_sessions:
                    self._send_session_notification("replaced", session)
                
        except Exception as e:
            logger.error(f"Error closing existing sessions: {e}")

    def log_login(self, user_data):
        """Log user login session with string _id"""
        try:  
            user_id = user_data.get("user_id")
            if not user_id:
                raise ValueError("user_id is required")
            
            # Ensure user_id is string format
            if not isinstance(user_id, str):
                user_id = str(user_id)
            
            username = (
                user_data.get("username") or 
                user_data.get("email") or 
                "unknown"
            )

            # Generate sequential session ID as string _id
            session_id = self.generate_session_id()

            # Close any existing active sessions
            self._close_existing_sessions(user_id)

            log_data = {
                "_id": session_id,           # String _id like "SESS-00001"
                "user_id": user_id,          # String-based user reference
                "branch_id": user_data.get("branch_id", 1),
                "username": username,
                "login_time": datetime.utcnow(),
                "logout_time": None,
                "session_duration": None,
                "status": "active",
                "source": "auth_service"
            }

            result = self.collection.insert_one(log_data)
            
            # Send login notification
            self._send_session_notification("login", log_data)

            logger.info(f"Login session {session_id} logged for user {username}")
            
            return log_data
        
        except Exception as e:
            logger.error(f"Error logging session: {e}")
            raise Exception(f"Error logging session: {str(e)}")
    
    def log_logout(self, user_id, reason="user_logout"):
        """Log user logout and calculate session duration (string-based)"""
        try:
            if not user_id:
                raise ValueError("user_id is required")
            
            # Ensure user_id is string format
            if not isinstance(user_id, str):
                user_id = str(user_id)
            
            # Find most recent active session using string-based user_id
            session = self.collection.find_one(
                {"user_id": user_id, "status": "active"},
                sort=[("login_time", -1)]
            )

            if not session:
                logger.warning(f"No active session found for user_id: {user_id}")
                return {"success": False, "message": "No active session found"}

            logout_time = datetime.utcnow()
            duration = int((logout_time - session["login_time"]).total_seconds())

            # Update session with logout info using string _id
            update_result = self.collection.update_one(
                {"_id": session["_id"]},  # Use string _id directly
                {
                    "$set": {
                        "logout_time": logout_time,
                        "session_duration": duration,
                        "status": "completed",
                        "logout_reason": reason
                    }
                }
            )

            if update_result.modified_count > 0:
                # Prepare session data with logout info
                session_with_logout = {
                    "_id": session["_id"],
                    "username": session.get("username"),
                    "branch_id": session.get("branch_id"),
                    "user_id": user_id,
                    "login_time": session.get("login_time"),
                    "logout_time": logout_time,
                    "session_duration": duration
                }
                
                # Send logout notification
                self._send_session_notification("logout", session_with_logout, {
                    "duration": duration,
                    "logout_reason": reason
                })
                
                # Send shift summary email to admins
                try:
                    email_result = shift_summary_service.send_shift_summary_email(session_with_logout)
                    if email_result.get('success'):
                        logger.info(f"Shift summary email sent successfully. Sent to {email_result.get('sent_count', 0)} admin(s)")
                    else:
                        logger.warning(f"Failed to send shift summary email: {email_result.get('error')}")
                except Exception as email_error:
                    logger.error(f"Error sending shift summary email: {email_error}")
                    # Don't fail logout if email fails
                
                logger.info(f"Logout logged for user {session.get('username')} (duration: {duration}s)")
                return {
                    "success": True, 
                    "message": "Session logged out successfully", 
                    "duration": duration,
                    "session_id": session["_id"]
                }
            else:
                logger.error("Failed to update session with logout info")
                return {"success": False, "message": "Failed to update session"}
        
        except Exception as e:
            logger.error(f"Error logging logout: {e}")
            raise Exception(f"Error logging logout: {str(e)}")
    
    def get_active_sessions(self):
        """Get all currently active sessions (no conversion needed)"""
        try:
            sessions = list(self.collection.find(
                {"status": "active"},
                sort=[("login_time", -1)]
            ))
            
            # No ObjectId conversion needed - _id is already string
            return sessions
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []

    def get_user_sessions(self, user_id, limit=50):
        """Get session history for a specific user (string-based)"""
        try:
            # Ensure user_id is string format
            if not isinstance(user_id, str):
                user_id = str(user_id)
                
            sessions = list(self.collection.find(
                {"user_id": user_id},
                sort=[("login_time", -1)],
                limit=limit
            ))
            
            # No ObjectId conversion needed - _id is already string
            return sessions
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    def get_session_by_id(self, session_id):
        """Get session by string _id (SESS-#####)"""
        try:
            session = self.collection.find_one({"_id": session_id})
            # No conversion needed - _id is already string
            return session
        except Exception as e:
            logger.error(f"Error getting session by ID: {e}")
            return None

    def get_session_statistics(self):
        """Get session statistics (no conversion dependencies)"""
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get counts
            active_count = self.collection.count_documents({"status": "active"})
            today_sessions = self.collection.count_documents({
                "login_time": {"$gte": today_start}
            })

            # Calculate average session duration
            recent_sessions = list(self.collection.find(
                {"session_duration": {"$exists": True, "$ne": None}},
                {"session_duration": 1}
            ).sort("login_time", -1).limit(100))
            
            avg_duration = 0
            if recent_sessions:
                total_duration = sum(s.get("session_duration", 0) for s in recent_sessions)
                avg_duration = total_duration // len(recent_sessions)
            
            return {
                "active_sessions": active_count,
                "today_sessions": today_sessions,
                "avg_session_duration": avg_duration
            }

        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {
                "active_sessions": 0,
                "today_sessions": 0,
                "avg_session_duration": 0
            } 

    def cleanup_old_sessions(self, days_old=30):
        """Clean up sessions older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            result = self.collection.delete_many({
                "login_time": {"$lt": cutoff_date},
                "status": {"$in": ["completed", "expired", "replaced"]}
            })
            
            if result.deleted_count > 0:
                # Send bulk cleanup notification
                self._send_session_notification("bulk_cleanup", {
                    "username": "System",
                    "_id": "BULK-CLEANUP"
                }, {
                    "deleted_count": result.deleted_count,
                    "cutoff_date": cutoff_date.isoformat()
                })
            
            logger.info(f"Cleaned up {result.deleted_count} old sessions")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")
            return 0

    def bulk_expire_user_sessions(self, user_ids):
        """Bulk expire sessions for multiple users"""
        try:
            if not user_ids:
                return {"success": False, "message": "No user IDs provided"}
            
            # Ensure all user_ids are strings
            user_ids = [str(uid) for uid in user_ids]
            
            cutoff_time = datetime.utcnow()
            
            result = self.collection.update_many(
                {
                    "user_id": {"$in": user_ids},
                    "status": "active"
                },
                {
                    "$set": {
                        "logout_time": cutoff_time,
                        "status": "expired",
                        "logout_reason": "bulk_expiry"
                    }
                }
            )
            
            if result.modified_count > 0:
                self._send_session_notification("bulk_cleanup", {
                    "username": "System",
                    "_id": "BULK-EXPIRE"
                }, {
                    "expired_count": result.modified_count,
                    "user_count": len(user_ids)
                })
            
            logger.info(f"Bulk expired {result.modified_count} sessions for {len(user_ids)} users")
            return {
                "success": True,
                "expired_count": result.modified_count,
                "user_count": len(user_ids)
            }
            
        except Exception as e:
            logger.error(f"Error in bulk expire sessions: {e}")
            return {"success": False, "error": str(e)}

    def auto_cleanup_old_sessions(self, months_old=6):
        """Automatically clean up sessions older than specified months (default 6 months)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=months_old * 30)
            
            # Get count of sessions to be deleted for reporting
            sessions_to_delete = self.collection.count_documents({
                "login_time": {"$lt": cutoff_date}
            })
            
            if sessions_to_delete == 0:
                logger.info("No sessions older than 6 months found for cleanup")
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": "No sessions to cleanup"
                }
            
            # Get some session details for notification before deletion
            sample_sessions = list(self.collection.find(
                {"login_time": {"$lt": cutoff_date}},
                {"_id": 1, "username": 1, "user_id": 1, "login_time": 1}
            ).limit(5))
            
            # Delete old sessions
            result = self.collection.delete_many({
                "login_time": {"$lt": cutoff_date}
            })
            
            # Send comprehensive notification
            self._send_session_notification("auto_cleanup", {
                "username": "System AutoCleanup",
                "_id": "AUTO-CLEANUP-6M"
            }, {
                "deleted_count": result.deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "months_old": months_old,
                "cleanup_type": "automatic_6_month",
                "sample_sessions": [
                    {
                        "session_id": s.get("_id"),
                        "username": s.get("username"),
                        "user_id": s.get("user_id"),
                        "login_time": s.get("login_time").isoformat() if s.get("login_time") else None
                    } for s in sample_sessions
                ],
                "total_sessions_before": sessions_to_delete
            })
            
            logger.info(f"Auto-cleanup: Deleted {result.deleted_count} sessions older than {months_old} months")
            
            return {
                "success": True,
                "deleted_count": result.deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "months_old": months_old
            }
            
        except Exception as e:
            logger.error(f"Error in auto cleanup old sessions: {e}")
            
            # Send error notification
            self._send_session_notification("auto_cleanup_failed", {
                "username": "System AutoCleanup",
                "_id": "AUTO-CLEANUP-ERROR"
            }, {
                "error": str(e),
                "months_old": months_old,
                "cleanup_type": "automatic_6_month_failed"
            })
            
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0
            }


    def start_automated_cleanup(self, cleanup_interval_hours=24, months_old=6):
        """Start automated cleanup thread that runs every 24 hours"""
        try:
            if self._cleanup_thread and self._cleanup_thread.is_alive():
                logger.warning("Automated cleanup thread is already running")
                return {"success": False, "message": "Cleanup thread already running"}
            
            def cleanup_worker():
                logger.info(f"Starting automated session cleanup thread (every {cleanup_interval_hours} hours)")
                
                while not self._stop_cleanup:
                    try:
                        # Perform cleanup
                        result = self.auto_cleanup_old_sessions(months_old)
                        
                        if result["success"]:
                            logger.info(f"Automated cleanup completed: {result['deleted_count']} sessions deleted")
                        else:
                            logger.error(f"Automated cleanup failed: {result.get('error')}")
                        
                        # Wait for next cleanup interval
                        for _ in range(cleanup_interval_hours * 3600):  # Convert hours to seconds
                            if self._stop_cleanup:
                                break
                            time.sleep(1)
                            
                    except Exception as e:
                        logger.error(f"Error in automated cleanup worker: {e}")
                        time.sleep(3600)  # Wait 1 hour before retrying on error
                
                logger.info("Automated cleanup thread stopped")
            
            self._stop_cleanup = False
            self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
            self._cleanup_thread.start()
            
            # Send startup notification - FIXED: use _id
            self._send_session_notification("auto_cleanup_started", {
                "username": "System AutoCleanup",
                "_id": "AUTO-CLEANUP-START"
            }, {
                "cleanup_interval_hours": cleanup_interval_hours,
                "months_old": months_old,
                "thread_id": self._cleanup_thread.ident
            })
            
            logger.info(f"Automated cleanup thread started (interval: {cleanup_interval_hours}h, retention: {months_old} months)")
            
            return {
                "success": True,
                "message": "Automated cleanup started",
                "interval_hours": cleanup_interval_hours,
                "retention_months": months_old
            }
            
        except Exception as e:
            logger.error(f"Error starting automated cleanup: {e}")
            return {"success": False, "error": str(e)}

    def stop_automated_cleanup(self):
        """Stop the automated cleanup thread"""
        try:
            if not self._cleanup_thread or not self._cleanup_thread.is_alive():
                return {"success": False, "message": "No cleanup thread is running"}
            
            self._stop_cleanup = True
            self._cleanup_thread.join(timeout=5)  # Wait up to 5 seconds for thread to stop
            
            # Send stop notification - FIXED: use _id
            self._send_session_notification("auto_cleanup_stopped", {
                "username": "System AutoCleanup",
                "_id": "AUTO-CLEANUP-STOP"
            }, {
                "thread_stopped": True,
                "stop_time": datetime.utcnow().isoformat()
            })
            
            logger.info("Automated cleanup thread stopped")
            
            return {
                "success": True,
                "message": "Automated cleanup stopped"
            }
            
        except Exception as e:
            logger.error(f"Error stopping automated cleanup: {e}")
            return {"success": False, "error": str(e)}

    def get_cleanup_status(self):
        """Get status of automated cleanup"""
        try:
            is_running = self._cleanup_thread and self._cleanup_thread.is_alive()
            
            # Get statistics about data that would be cleaned up
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            old_sessions_count = self.collection.count_documents({
                "login_time": {"$lt": six_months_ago}
            })
            
            # Get oldest session date
            oldest_session = self.collection.find_one(
                {},
                sort=[("login_time", 1)]
            )
            
            oldest_date = None
            if oldest_session and oldest_session.get("login_time"):
                oldest_date = oldest_session["login_time"].isoformat()
            
            return {
                "automated_cleanup_running": is_running,
                "thread_id": self._cleanup_thread.ident if is_running else None,
                "sessions_older_than_6_months": old_sessions_count,
                "oldest_session_date": oldest_date,
                "next_cleanup_eligible": old_sessions_count > 0,
                "cutoff_date_6_months": six_months_ago.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting cleanup status: {e}")
            return {
                "automated_cleanup_running": False,
                "error": str(e)
            }

    def manual_cleanup_with_date_range(self, start_date=None, end_date=None, dry_run=False):
        """Manual cleanup with specific date range (useful for testing or custom cleanup)"""
        try:
            if not start_date and not end_date:
                # Default to 6 months ago if no dates specified
                end_date = datetime.utcnow() - timedelta(days=180)
                start_date = datetime(2020, 1, 1)  # Very old date to catch all old sessions
            else:
                if start_date:
                    start_date = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
                if end_date:
                    end_date = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
            
            query = {}
            if start_date and end_date:
                query["login_time"] = {"$gte": start_date, "$lte": end_date}
            elif start_date:
                query["login_time"] = {"$gte": start_date}
            elif end_date:
                query["login_time"] = {"$lte": end_date}
            
            # Count sessions that would be affected
            sessions_count = self.collection.count_documents(query)
            
            if sessions_count == 0:
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": "No sessions found in specified date range",
                    "dry_run": dry_run
                }
            
            # Get sample sessions for reporting - FIXED: use _id instead of session_id
            sample_sessions = list(self.collection.find(
                query,
                {"_id": 1, "username": 1, "login_time": 1, "status": 1}
            ).limit(10))
            
            deleted_count = 0
            if not dry_run:
                # Actually delete the sessions
                result = self.collection.delete_many(query)
                deleted_count = result.deleted_count
                
                # Send notification - FIXED: use _id
                self._send_session_notification("manual_cleanup", {
                    "username": "Manual Cleanup",
                    "_id": "MANUAL-CLEANUP"
                }, {
                    "deleted_count": deleted_count,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "cleanup_type": "manual_date_range",
                    "sample_sessions": sample_sessions
                })
            
            logger.info(f"Manual cleanup ({'DRY RUN' if dry_run else 'EXECUTED'}): {sessions_count} sessions {'would be' if dry_run else 'were'} deleted")
            
            return {
                "success": True,
                "sessions_found": sessions_count,
                "deleted_count": deleted_count if not dry_run else 0,
                "sample_sessions": sample_sessions,
                "dry_run": dry_run,
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error in manual cleanup with date range: {e}")
            return {"success": False, "error": str(e)}


    def generate_monthly_cleanup_report(self, months_old=6):
        """Generate detailed monthly report before cleanup for admin review"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=months_old * 30)
            
            # Get sessions to be deleted grouped by user and month
            pipeline = [
                {
                    "$match": {
                        "login_time": {"$lt": cutoff_date}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "user_id": "$user_id",
                            "username": "$username",
                            "year": {"$year": "$login_time"},
                            "month": {"$month": "$login_time"}
                        },
                        "session_count": {"$sum": 1},
                        "total_duration": {"$sum": "$session_duration"},
                        "first_session": {"$min": "$login_time"},
                        "last_session": {"$max": "$login_time"},
                        "statuses": {"$addToSet": "$status"}
                    }
                },
                {
                    "$sort": {
                        "_id.year": -1,
                        "_id.month": -1,
                        "_id.username": 1
                    }
                }
            ]
            
            user_monthly_data = list(self.collection.aggregate(pipeline))
            
            # Get overall statistics
            total_sessions = self.collection.count_documents({"login_time": {"$lt": cutoff_date}})
            
            # Get user activity summary
            active_users_pipeline = [
                {
                    "$match": {
                        "login_time": {"$lt": cutoff_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$user_id",
                        "username": {"$first": "$username"},
                        "total_sessions": {"$sum": 1},
                        "total_duration": {"$sum": "$session_duration"},
                        "first_session": {"$min": "$login_time"},
                        "last_session": {"$max": "$login_time"}
                    }
                },
                {
                    "$sort": {"total_sessions": -1}
                },
                {
                    "$limit": 20  # Top 20 users
                }
            ]
            
            top_users = list(self.collection.aggregate(active_users_pipeline))
            
            # Calculate monthly breakdown
            monthly_summary = {}
            for record in user_monthly_data:
                month_key = f"{record['_id']['year']}-{record['_id']['month']:02d}"
                if month_key not in monthly_summary:
                    monthly_summary[month_key] = {
                        "total_sessions": 0,
                        "unique_users": set(),
                        "total_duration": 0
                    }
                
                monthly_summary[month_key]["total_sessions"] += record["session_count"]
                monthly_summary[month_key]["unique_users"].add(record["_id"]["user_id"])
                monthly_summary[month_key]["total_duration"] += record.get("total_duration", 0) or 0
            
            # Convert sets to counts
            for month_data in monthly_summary.values():
                month_data["unique_users"] = len(month_data["unique_users"])
            
            return {
                "cutoff_date": cutoff_date.isoformat(),
                "total_sessions_to_delete": total_sessions,
                "monthly_breakdown": monthly_summary,
                "top_users_affected": top_users,
                "user_monthly_details": user_monthly_data,
                "report_generated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating monthly cleanup report: {e}")
            return {
                "error": str(e),
                "total_sessions_to_delete": 0,
                "report_generated": datetime.utcnow().isoformat()
            }

    def _send_monthly_cleanup_notification(self, cleanup_result, monthly_report):
        """Send brief monthly cleanup notification directing admins to full report"""
        try:
            total_deleted = cleanup_result.get("deleted_count", 0)
            users_affected = len(monthly_report.get("top_users_affected", []))
            months_affected = len(monthly_report.get("monthly_breakdown", {}))

            # Short, actionable notification
            message = f"Monthly cleanup completed: {total_deleted} sessions deleted affecting {users_affected} users across {months_affected} months. Full report available in admin logs."

            self.notification_service.create_notification(
                title="Monthly Session Cleanup Complete",
                message=message,
                notification_type="session_management",
                priority="medium",
                metadata={
                    "action_type": "monthly_cleanup_complete",
                    "sessions_deleted": total_deleted,
                    "users_affected": users_affected,
                    "months_affected": months_affected,
                    "cleanup_date": datetime.utcnow().isoformat(),
                    "report_available": True,
                    "report_location": "admin_logs"
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to send monthly cleanup notification: {e}")

    def get_cleanup_preview(self, months_old=6):
        """Get a preview of what would be deleted in next cleanup - for admin review"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=months_old * 30)
            
            # Get preview without actually deleting
            preview_data = self.generate_monthly_cleanup_report(months_old)
            
            # Add next cleanup date prediction
            if self._cleanup_thread and self._cleanup_thread.is_alive():
                # Estimate next cleanup based on thread start time
                next_cleanup = datetime.utcnow() + timedelta(hours=720)  # Default monthly
            else:
                next_cleanup = None
            
            return {
                "success": True,
                "preview": preview_data,
                "next_scheduled_cleanup": next_cleanup.isoformat() if next_cleanup else None,
                "cleanup_running": self._cleanup_thread and self._cleanup_thread.is_alive(),
                "cutoff_date": cutoff_date.isoformat(),
                "days_until_cleanup": (next_cleanup - datetime.utcnow()).days if next_cleanup else None
            }
            
        except Exception as e:
            logger.error(f"Error getting cleanup preview: {e}")
            return {"success": False, "error": str(e)}

    def get_cleanup_status(self):
        """Enhanced cleanup status with monthly scheduling info"""
        try:
            is_running = self._cleanup_thread and self._cleanup_thread.is_alive()
            
            # Get statistics about data that would be cleaned up
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            old_sessions_count = self.collection.count_documents({
                "login_time": {"$lt": six_months_ago}
            })
            
            # Get oldest session date
            oldest_session = self.collection.find_one(
                {},
                sort=[("login_time", 1)]
            )
            
            oldest_date = None
            if oldest_session and oldest_session.get("login_time"):
                oldest_date = oldest_session["login_time"].isoformat()
            
            # Calculate next cleanup date (approximately)
            next_cleanup_estimate = None
            if is_running:
                # Rough estimate - cleanup runs monthly
                next_cleanup_estimate = (datetime.utcnow() + timedelta(days=30)).isoformat()
            
            return {
                "automated_cleanup_running": is_running,
                "cleanup_schedule": "Monthly (every 30 days)",
                "thread_id": self._cleanup_thread.ident if is_running else None,
                "sessions_older_than_6_months": old_sessions_count,
                "oldest_session_date": oldest_date,
                "next_cleanup_eligible": old_sessions_count > 0,
                "cutoff_date_6_months": six_months_ago.isoformat(),
                "next_cleanup_estimate": next_cleanup_estimate,
                "retention_policy": "6 months",
                "cleanup_frequency": "Monthly"
            }
            
        except Exception as e:
            logger.error(f"Error getting cleanup status: {e}")
            return {
                "automated_cleanup_running": False,
                "error": str(e)
            }
    
    
    def manual_cleanup_with_export(self, start_date=None, end_date=None, export_path=None, dry_run=False):
        """Manual cleanup with automatic CSV export of affected data before deletion"""
        try:
            # Parse and validate dates
            if start_date:
                start_date = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
            if end_date:
                end_date = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
            
            # Default to 6 months ago if no dates specified
            if not start_date and not end_date:
                end_date = datetime.utcnow() - timedelta(days=180)
                start_date = datetime(2020, 1, 1)
            
            # Build query
            query = {}
            if start_date and end_date:
                query["login_time"] = {"$gte": start_date, "$lte": end_date}
            elif start_date:
                query["login_time"] = {"$gte": start_date}
            elif end_date:
                query["login_time"] = {"$lte": end_date}
            
            # Get all sessions that will be affected
            sessions_to_export = list(self.collection.find(query).sort("login_time", -1))
            
            if not sessions_to_export:
                return {
                    "success": True,
                    "deleted_count": 0,
                    "exported_count": 0,
                    "message": "No sessions found in specified date range",
                    "dry_run": dry_run,
                    "export_file": None
                }
            
            # Generate export filename if not provided
            if not export_path:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                date_range = f"{start_date.strftime('%Y%m%d') if start_date else 'start'}_to_{end_date.strftime('%Y%m%d') if end_date else 'end'}"
                export_filename = f"session_cleanup_export_{date_range}_{timestamp}.csv"
                export_path = os.path.join("exports", export_filename)
            
            # Ensure export directory exists
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            # Export data to CSV before deletion
            export_result = self._export_sessions_to_csv(sessions_to_export, export_path)
            
            if not export_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to export data: {export_result['error']}",
                    "deleted_count": 0,
                    "exported_count": 0
                }
            
            deleted_count = 0
            if not dry_run:
                # Actually delete the sessions after successful export
                delete_result = self.collection.delete_many(query)
                deleted_count = delete_result.deleted_count
                
                # Send notification with export info - FIXED: use _id
                self._send_session_notification("manual_cleanup_with_export", {
                    "username": "Manual Cleanup with Export",
                    "_id": "MANUAL-CLEANUP-EXPORT"
                }, {
                    "deleted_count": deleted_count,
                    "exported_count": len(sessions_to_export),
                    "export_file": export_path,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "cleanup_type": "manual_with_export"
                })
            
            logger.info(f"Manual cleanup with export ({'DRY RUN' if dry_run else 'EXECUTED'}): {len(sessions_to_export)} sessions {'would be' if dry_run else 'were'} deleted, exported to {export_path}")
            
            return {
                "success": True,
                "sessions_found": len(sessions_to_export),
                "deleted_count": deleted_count if not dry_run else 0,
                "exported_count": len(sessions_to_export),
                "export_file": export_path,
                "dry_run": dry_run,
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error in manual cleanup with export: {e}")
            return {"success": False, "error": str(e)}

    def _export_sessions_to_csv(self, sessions_data, export_path):
        """Export session data to CSV file"""
        try:
            # Removed 'ip_address' and 'user_agent' from fieldnames
            fieldnames = [
                'session_id', 'user_id', 'username', 'branch_id',
                'login_time', 'logout_time', 'session_duration', 'status',
                'logout_reason', 'source'
            ]
            
            with open(export_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for session in sessions_data:
                    # No conversion needed - _id is already string
                    
                    # Format datetime fields for CSV - FIXED: use _id for session_id
                    row_data = {
                        'session_id': session.get('_id', ''),  # FIXED: use _id
                        'user_id': session.get('user_id', ''),
                        'username': session.get('username', ''),
                        'branch_id': session.get('branch_id', ''),
                        'login_time': session.get('login_time').isoformat() if session.get('login_time') else '',
                        'logout_time': session.get('logout_time').isoformat() if session.get('logout_time') else '',
                        'session_duration': session.get('session_duration', ''),
                        'status': session.get('status', ''),
                        'logout_reason': session.get('logout_reason', ''),
                        'source': session.get('source', '')
                    }
                    writer.writerow(row_data)
            
            logger.info(f"Successfully exported {len(sessions_data)} sessions to {export_path}")
            return {
                "success": True,
                "exported_count": len(sessions_data),
                "export_path": export_path
            }
            
        except Exception as e:
            logger.error(f"Error exporting sessions to CSV: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def scheduled_cleanup_with_export(self, retention_months=6, export_enabled=True):
        """Enhanced automatic cleanup that exports data before deletion"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_months * 30)
            
            # Get sessions to be deleted
            sessions_to_delete = list(self.collection.find(
                {"login_time": {"$lt": cutoff_date}}
            ).sort("login_time", -1))
            
            if not sessions_to_delete:
                logger.info("No sessions older than 6 months found for cleanup")
                return {
                    "success": True,
                    "deleted_count": 0,
                    "exported_count": 0,
                    "message": "No sessions to cleanup"
                }
            
            export_path = None
            if export_enabled:
                # Generate automatic export filename
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                export_filename = f"auto_cleanup_export_{retention_months}months_{timestamp}.csv"
                export_path = os.path.join("exports", "auto_cleanup", export_filename)
                
                # Export before deletion
                export_result = self._export_sessions_to_csv(sessions_to_delete, export_path)
                
                if not export_result["success"]:
                    logger.error(f"Failed to export data before cleanup: {export_result['error']}")
                    # Continue with cleanup even if export fails, but log the issue
                    export_path = None
            
            # Delete old sessions
            result = self.collection.delete_many({
                "login_time": {"$lt": cutoff_date}
            })
            
            # Send notification - FIXED: use _id
            self._send_session_notification("auto_cleanup_with_export", {
                "username": "System AutoCleanup",
                "_id": "AUTO-CLEANUP-EXPORT"
            }, {
                "deleted_count": result.deleted_count,
                "exported_count": len(sessions_to_delete),
                "export_file": export_path,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_months": retention_months,
                "export_enabled": export_enabled
            })
            
            logger.info(f"Auto-cleanup with export: Deleted {result.deleted_count} sessions, exported to {export_path}")
            
            return {
                "success": True,
                "deleted_count": result.deleted_count,
                "exported_count": len(sessions_to_delete),
                "export_file": export_path,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_months": retention_months
            }
            
        except Exception as e:
            logger.error(f"Error in scheduled cleanup with export: {e}")
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0,
                "exported_count": 0
            }

    def __del__(self):
        """Cleanup when service is destroyed"""
        if hasattr(self, '_cleanup_thread') and self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_cleanup = True
            try:
                self._cleanup_thread.join(timeout=2)
            except:
                pass
    
class SessionDisplayService:
    def __init__(self):
        self.db = db_manager.get_database()
        self.collection = self.db.session_logs
        self.audit_collection = self.db.audit_logs

    def get_session_logs(self, limit=100, status_filter=None, user_filter=None):
        """Get formatted session logs - handle mixed ObjectId/string data"""
        try:
            
            from datetime import datetime
            
            query = {}
            if status_filter:
                query["status"] = status_filter
            if user_filter:
                query["$or"] = [
                    {"username": {"$regex": user_filter, "$options": "i"}},
                    {"user_id": user_filter}
                ]
            
            session_logs = list(self.collection.find(query)
                              .sort("login_time", -1)
                              .limit(limit))
            
            formatted_logs = []
            for i, log in enumerate(session_logs):
                try:
                    # Convert ALL values to JSON-safe types immediately
                    safe_log = {}
                    for key, value in log.items():
                        if isinstance(value, datetime):
                            safe_log[key] = value.isoformat()
                        elif value is None:
                            safe_log[key] = None
                        else:
                            safe_log[key] = value
                    
                    # Format duration safely
                    duration = safe_log.get('session_duration')
                    if duration and isinstance(duration, (int, float)) and duration > 0:
                        if duration < 60:
                            duration_str = f"{int(duration)}s"
                        elif duration < 3600:
                            minutes = int(duration // 60)
                            seconds = int(duration % 60)
                            duration_str = f"{minutes}m {seconds}s"
                        else:
                            hours = int(duration // 3600)
                            minutes = int((duration % 3600) // 60)
                            duration_str = f"{hours}h {minutes}m"
                    else:
                        duration_str = "Active" if safe_log.get('status') == 'active' else "0s"
                
                    # Use session_id if available, otherwise use _id
                    log_id = safe_log.get('session_id') or safe_log.get('_id') or f"SESS-{i+1:05d}"
                    
                    # Create completely clean formatted log with only JSON-safe values
                    formatted_log = {
                        "log_id": str(log_id),
                        "user_id": str(safe_log.get('user_id', '')),
                        "ref_id": str(safe_log.get('_id', '')),
                        "event_type": "Session",
                        "amount_qty": duration_str,
                        "status": str(safe_log.get('status', 'Unknown')).title(),
                        "timestamp": safe_log.get('login_time'),
                        "remarks": f"User: {safe_log.get('username', 'Unknown')}, Status: {safe_log.get('status', 'Unknown')}, Duration: {duration_str}",
                        "username": str(safe_log.get('username', 'Unknown')),
                        "login_time": safe_log.get('login_time'),
                        "logout_time": safe_log.get('logout_time'),
                        "branch_id": safe_log.get('branch_id', 'N/A'),
                        "logout_reason": str(safe_log.get('logout_reason', '')) if safe_log.get('logout_reason') else None
                    }
                    
                    formatted_logs.append(formatted_log)
                    
                except Exception as log_error:
                    logger.error(f"Error processing session log {i+1}: {log_error}")
                    continue
            
            return {
                'success': True,
                'data': formatted_logs,
                'count': len(formatted_logs)
            }
            
        except Exception as e:
            logger.error(f"Error getting session logs: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    def get_combined_logs(self, limit=100, log_type=None):
        """Get combined session and audit logs"""
        try:
            all_logs = []
            
            # Get session logs if requested
            if log_type in [None, 'all', 'session']:
                session_limit = limit//2 if log_type == 'all' else limit
                
                try:
                    session_result = self.get_session_logs(session_limit)
                    
                    if session_result['success']:
                        for log in session_result['data']:
                            log['log_source'] = 'session'
                            all_logs.append(log)
                        
                except Exception as session_error:
                    logger.error(f"Session logs error: {session_error}")
            
            # Get audit logs if requested
            if log_type in [None, 'all', 'audit']:
                try:
                    audit_limit = limit//2 if log_type == 'all' else limit
                    
                    if self.audit_collection is not None:
                        audit_count = self.audit_collection.count_documents({})
                        
                        if audit_count > 0:
                            audit_logs = list(self.audit_collection.find()
                                            .sort("timestamp", -1)
                                            .limit(audit_limit))
                            
                            for i, audit in enumerate(audit_logs):
                                formatted_audit = {
                                    "log_id": f"AUD-{i+1:04d}",
                                    "user_id": audit.get('user_id', 'Unknown'),
                                    "ref_id": str(audit["_id"]),
                                    "event_type": audit.get('event_type', 'Unknown').replace('_', ' ').title(),
                                    "amount_qty": self._format_audit_changes(audit),
                                    "status": audit.get('status', 'Unknown').title(),
                                    "timestamp": audit.get('timestamp'),
                                    "remarks": audit.get('remarks', f"Audit: {audit.get('event_type', 'Unknown')}"),
                                    "username": audit.get('username', 'Unknown'),
                                    "branch_id": audit.get('branch_id', 'N/A'),
                                    "target_type": audit.get('target_type'),
                                    "log_source": "audit"
                                }
                                all_logs.append(formatted_audit)
                            
                except Exception as audit_error:
                    logger.warning(f"Could not fetch audit logs: {audit_error}")
            
            # Sort all logs by timestamp (newest first)
            try:
                all_logs.sort(key=lambda x: x.get('timestamp') or datetime.min, reverse=True)
            except Exception:
                pass  # Continue without sorting if there's an issue
            
            return {
                'success': True,
                'data': all_logs[:limit],
                'total_count': len(all_logs)
            }
            
        except Exception as e:
            logger.error(f"Error getting combined logs: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    def _format_audit_changes(self, audit_log):
        """Format audit log changes for display"""
        event_type = audit_log.get('event_type', '')
        
        if 'create' in event_type:
            return "Created"
        elif 'delete' in event_type:
            return "Deleted"
        elif 'update' in event_type:
            changes = audit_log.get('changes', {})
            if isinstance(changes, dict):
                changed_fields = changes.get('changed_fields', [])
                return f"{len(changed_fields)} fields" if changed_fields else "Updated"
        
        return "N/A"

    def export_session_logs(self, export_format="csv", date_filter=None, status_filter=None):
        """Export session logs in specified format"""
        try:
            
            from datetime import datetime
            
            query = {}
            if date_filter:
                start_date = datetime.fromisoformat(date_filter.get('start_date'))
                end_date = datetime.fromisoformat(date_filter.get('end_date'))
                query["login_time"] = {"$gte": start_date, "$lte": end_date}
            
            if status_filter:
                query["status"] = status_filter
            
            sessions = list(self.collection.find(query).sort("login_time", -1))
            
            export_data = []
            for session in sessions:
                # Clean the session data
                clean_session = {}
                for key, value in session.items():
                    if isinstance(value, datetime):
                        clean_session[key] = value.isoformat()
                    else:
                        clean_session[key] = value
                
                export_data.append({
                    "session_id": clean_session.get("_id"),
                    "user_id": clean_session.get("user_id"),
                    "username": clean_session.get("username"),
                    "login_time": clean_session.get("login_time"),
                    "logout_time": clean_session.get("logout_time"),
                    "duration": clean_session.get("session_duration"),
                    "status": clean_session.get("status"),
                    "branch_id": clean_session.get("branch_id"),
                    "logout_reason": clean_session.get("logout_reason")
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
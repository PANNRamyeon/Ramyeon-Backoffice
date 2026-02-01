from datetime import datetime, timedelta

from ..database import db_manager  # ✅ Updated import

##THIS IS FOR LEGACY USE AND FOR TESTING
class SessionManagementService:
    def __init__(self):
        self.db = db_manager.get_database()  # ✅ Get database connection
        self.session_collection = self.db.session_logs  # ✅ Use cloud database
        self.user_collection = self.db.users  # ✅ Use cloud database
    
    def convert_object_id(self, document):
        """Convert ObjectId to string for JSON serialization"""
        if document and '_id' in document:
            document['_id'] = str(document['_id'])
        if document and 'user_id' in document:
            document['user_id'] = str(document['user_id'])  # Add this line
        return document
    
    def convert_datetime_to_string(self, document):
        """Convert datetime objects to ISO string format"""
        datetime_fields = ['login_time', 'logout_time', 'last_updated']
        for field in datetime_fields:
            if document and field in document and document[field]:
                if hasattr(document[field], 'isoformat'):
                    document[field] = document[field].isoformat()
        return document
    
    def process_session_document(self, document):
        """Process a session document for JSON serialization"""
        if document:
            document = self.convert_object_id(document)
            document = self.convert_datetime_to_string(document)
        return document
    
    def get_user_sessions(self, user_id):
        """Get all sessions for a specific user"""
        try:
            
            sessions = list(self.session_collection.find(
                {"user_id": user_id}
            ).sort("login_time", -1))
            
            return [self.process_session_document(session) for session in sessions]
        except Exception as e:
            raise Exception(f"Error getting user sessions: {str(e)}")
    
    def get_active_sessions(self):
        """Get all currently active sessions"""
        try:
            sessions = list(self.session_collection.find(
                {"status": "active"}
            ).sort("login_time", -1))
            
            return [self.process_session_document(session) for session in sessions]
        except Exception as e:
            raise Exception(f"Error getting active sessions: {str(e)}")
    
    def force_logout_user(self, user_id):
        """Force logout all sessions for a specific user"""
        try:
            
            logout_time = datetime.utcnow()
            
            # Update all active sessions for this user
            result = self.session_collection.update_many(
                {"user_id": user_id, "status": "active"},
                {
                    "$set": {
                        "logout_time": logout_time,
                        "status": "force_logged_out",
                        "last_updated": logout_time
                    }
                }
            )
            
            return {
                "message": f"Force logged out {result.modified_count} sessions",
                "sessions_affected": result.modified_count
            }
        except Exception as e:
            raise Exception(f"Error force logging out user: {str(e)}")
    
    def cleanup_old_sessions(self, days_old=30):
        """Clean up sessions older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = self.session_collection.delete_many(
                {"login_time": {"$lt": cutoff_date}}
            )
            
            return {
                "message": f"Cleaned up {result.deleted_count} old sessions",
                "sessions_deleted": result.deleted_count
            }
        except Exception as e:
            raise Exception(f"Error cleaning up sessions: {str(e)}")
    
    def get_session_statistics(self):
        """Get session statistics"""
        try:
            total_sessions = self.session_collection.count_documents({})
            active_sessions = self.session_collection.count_documents({"status": "active"})
            completed_sessions = self.session_collection.count_documents({"status": "completed"})
            
            # Get average session duration
            pipeline = [
                {"$match": {"session_duration": {"$exists": True, "$ne": None}}},
                {"$group": {"_id": None, "avg_duration": {"$avg": "$session_duration"}}}
            ]
            avg_duration_result = list(self.session_collection.aggregate(pipeline))
            avg_duration = avg_duration_result[0]["avg_duration"] if avg_duration_result else 0
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "completed_sessions": completed_sessions,
                "average_session_duration_seconds": round(avg_duration, 2) if avg_duration else 0
            }
        except Exception as e:
            raise Exception(f"Error getting session statistics: {str(e)}")
"""
Notifications Model - Following ERD Specification with Enhancements
PK = "notifications", SK = "NOTIF-#####" (5-digit format)
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute,
    UTCDateTimeAttribute, JSONAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST
from datetime import datetime, timedelta
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# ============= GLOBAL SECONDARY INDEXES =============
class NotificationTypeIndex(GlobalSecondaryIndex):
    """
    GSI for querying notifications by type
    """
    class Meta:
        index_name = 'notification-type-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    notification_type = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class PriorityIndex(GlobalSecondaryIndex):
    """
    GSI for querying notifications by priority
    """
    class Meta:
        index_name = 'notification-priority-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    priority = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class IsReadIndex(GlobalSecondaryIndex):
    """
    GSI for querying notifications by read status
    This is essential for unread notifications dashboard
    """
    class Meta:
        index_name = 'notification-is-read-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    is_read = BooleanAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class ActionTypeIndex(GlobalSecondaryIndex):
    """
    GSI for querying notifications by action type
    """
    class Meta:
        index_name = 'notification-action-type-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    action_type = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


# ============= MAIN NOTIFICATION MODEL =============
class Notification(Model):
    """
    NOTIFICATION MODEL - Following ERD with Actionable Notifications
    
    ERD Fields:
    - PK = notifications
    - SK = NOTIF-##### (5-digit)
    - title (String)
    - message (String)
    - priority (String)
    - is_read (boolean)
    - archived (boolean)
    - created_at (ISODATE)
    - updated_at (ISODATE)
    - notification_type (String)
    - metadata (array) - but we'll use JSONAttribute for flexibility
    
    Enhanced with:
    - delivered_at (ISODATE) - when the event occurred
    - action_type (String) - for actionable notifications filtering
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        if DYNAMODB_LOCAL:
            host = DYNAMODB_LOCAL_HOST
        
        read_capacity_units = 10
        write_capacity_units = 20  # Higher for frequent notification writes
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, default="notifications")
    sk = UnicodeAttribute(range_key=True)  # "NOTIF-00001" (5-digit)
    
    # ============= GSI DEFINITIONS =============
    type_index = NotificationTypeIndex()
    priority_index = PriorityIndex()
    is_read_index = IsReadIndex()
    action_type_index = ActionTypeIndex()
    
    # ============= NOTIFICATION CONTENT =============
    title = UnicodeAttribute()
    message = UnicodeAttribute()
    priority = UnicodeAttribute()  # low, medium, high, critical
    notification_type = UnicodeAttribute()  # system, user, order, inventory, promotion, alert, reminder
    
    # ============= ACTIONABLE NOTIFICATIONS =============
    action_type = UnicodeAttribute(null=True)  # view_order, update_inventory, approve_request, etc.
    
    # ============= STATUS FLAGS =============
    is_read = BooleanAttribute(default=False)
    archived = BooleanAttribute(default=False)
    
    # ============= TIMESTAMPS =============
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    delivered_at = UTCDateTimeAttribute(null=True)  # When the event occurred
    
    # ============= METADATA =============
    metadata = JSONAttribute(null=True)  # Flexible JSON for event details
    
    # ============= VALIDATION METHODS =============
    
    @staticmethod
    def validate_priority(priority: str) -> bool:
        """Validate priority value"""
        valid_priorities = {"low", "medium", "high", "critical"}
        return priority in valid_priorities
    
    @staticmethod
    def validate_notification_type(notification_type: str) -> bool:
        """Validate notification type"""
        valid_types = {
            "system", "user", "order", "inventory", "promotion", 
            "alert", "reminder", "security", "maintenance", "update"
        }
        return notification_type in valid_types
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_notification(cls, title: str, message: str, 
                          notification_type: str, priority: str = "medium",
                          action_type: str = None, metadata: Dict = None,
                          delivered_at: datetime = None) -> 'Notification':
        """
        Create a new notification with auto-generated 5-digit SK
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level (low, medium, high, critical)
            action_type: Action type for actionable notifications
            metadata: JSON metadata about what happened, where, etc.
            delivered_at: When the event occurred (defaults to now)
        
        Returns:
            Notification: Created and saved notification instance
        """
        try:
            # Validate inputs
            if not cls.validate_notification_type(notification_type):
                raise ValueError(f"Invalid notification type: {notification_type}")
            
            if not cls.validate_priority(priority):
                raise ValueError(f"Invalid priority: {priority}")
            
            # Generate 5-digit SK using utils.py
            sk = generate_sk('NOTIF-', 'notification_seq')
            
            # Create and save notification
            notification = cls(
                pk="notifications",
                sk=sk,
                title=title.strip(),
                message=message.strip(),
                notification_type=notification_type,
                priority=priority,
                action_type=action_type,
                metadata=metadata or {},
                delivered_at=delivered_at or datetime.utcnow(),
                is_read=False,
                archived=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            notification.save()
            
            logger.info(f"Notification created: {sk} - Type: {notification_type}, Priority: {priority}")
            return notification
            
        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            raise
    
    @classmethod
    def create_system_notification(cls, title: str, message: str,
                                 priority: str = "medium", metadata: Dict = None) -> 'Notification':
        """
        Create a system notification
        
        Args:
            title: Notification title
            message: Notification message
            priority: Priority level
            metadata: Event details
        
        Returns:
            Notification: Created system notification
        """
        return cls.create_notification(
            title=title,
            message=message,
            notification_type="system",
            priority=priority,
            action_type="system_alert",
            metadata=metadata
        )
    
    @classmethod
    def create_order_notification(cls, title: str, message: str,
                                order_id: str, order_status: str,
                                priority: str = "medium") -> 'Notification':
        """
        Create an order notification
        
        Args:
            title: Notification title
            message: Notification message
            order_id: Order ID
            order_status: Order status
            priority: Priority level
        
        Returns:
            Notification: Created order notification
        """
        metadata = {
            "event": "order_update",
            "order_id": order_id,
            "order_status": order_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return cls.create_notification(
            title=title,
            message=message,
            notification_type="order",
            priority=priority,
            action_type="view_order",
            metadata=metadata
        )
    
    @classmethod
    def create_inventory_notification(cls, title: str, message: str,
                                    product_id: str, batch_id: str,
                                    change_type: str, priority: str = "high") -> 'Notification':
        """
        Create an inventory notification
        
        Args:
            title: Notification title
            message: Notification message
            product_id: Product ID
            batch_id: Batch ID
            change_type: Type of inventory change
            priority: Priority level
        
        Returns:
            Notification: Created inventory notification
        """
        metadata = {
            "event": "inventory_change",
            "product_id": product_id,
            "batch_id": batch_id,
            "change_type": change_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return cls.create_notification(
            title=title,
            message=message,
            notification_type="inventory",
            priority=priority,
            action_type="update_inventory",
            metadata=metadata
        )
    
    @classmethod
    def create_security_notification(cls, title: str, message: str,
                                   event_type: str, ip_address: str = None,
                                   priority: str = "critical") -> 'Notification':
        """
        Create a security notification
        
        Args:
            title: Notification title
            message: Notification message
            event_type: Type of security event
            ip_address: IP address involved
            priority: Priority level
        
        Returns:
            Notification: Created security notification
        """
        metadata = {
            "event": "security_alert",
            "event_type": event_type,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return cls.create_notification(
            title=title,
            message=message,
            notification_type="security",
            priority=priority,
            action_type="review_security",
            metadata=metadata
        )
    
    @classmethod
    def get_by_id(cls, notification_id: str) -> 'Notification | None':
        """
        Get notification by ID
        
        Args:
            notification_id: Format "NOTIF-00001" or just "00001"
        
        Returns:
            Notification or None if not found
        """
        try:
            # Ensure proper format
            if not notification_id.startswith('NOTIF-'):
                notification_id = f"NOTIF-{notification_id.zfill(5)}"  # Pad to 5 digits
            
            notification = cls.get("notifications", notification_id)
            if notification and notification.archived:
                return None
            return notification
        except cls.DoesNotExist:
            logger.warning(f"Notification not found: {notification_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching notification {notification_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_type(cls, notification_type: str, 
                   limit: int = 50, include_archived: bool = False) -> list:
        """
        Get notifications by type using GSI
        
        Args:
            notification_type: Type of notification to filter by
            limit: Maximum number of notifications to return
            include_archived: Include archived notifications
        
        Returns:
            list: List of notifications of specified type
        """
        try:
            notifications = []
            
            for notification in cls.type_index.query(
                notification_type,
                scan_index_forward=False,  # Newest first
                limit=limit
            ):
                if include_archived or not notification.archived:
                    notifications.append(notification)
            
            return notifications
        except Exception as e:
            logger.error(f"Error getting notifications by type {notification_type}: {str(e)}")
            return []
    
    @classmethod
    def get_by_priority(cls, priority: str, 
                       limit: int = 50, include_archived: bool = False) -> list:
        """
        Get notifications by priority using GSI
        
        Args:
            priority: Priority level to filter by
            limit: Maximum number of notifications to return
            include_archived: Include archived notifications
        
        Returns:
            list: List of notifications with specified priority
        """
        try:
            notifications = []
            
            for notification in cls.priority_index.query(
                priority,
                scan_index_forward=False,  # Newest first
                limit=limit
            ):
                if include_archived or not notification.archived:
                    notifications.append(notification)
            
            return notifications
        except Exception as e:
            logger.error(f"Error getting notifications by priority {priority}: {str(e)}")
            return []
    
    @classmethod
    def get_unread_notifications(cls, limit: int = 100) -> list:
        """
        Get unread notifications using GSI
        
        Args:
            limit: Maximum number of notifications to return
        
        Returns:
            list: List of unread notifications
        """
        try:
            notifications = []
            
            for notification in cls.is_read_index.query(
                False,  # is_read = False
                scan_index_forward=False,  # Newest first
                limit=limit
            ):
                if not notification.archived:
                    notifications.append(notification)
            
            return notifications
        except Exception as e:
            logger.error(f"Error getting unread notifications: {str(e)}")
            return []
    
    @classmethod
    def get_by_action_type(cls, action_type: str,
                          limit: int = 50, include_archived: bool = False) -> list:
        """
        Get notifications by action type using GSI
        
        Args:
            action_type: Action type to filter by
            limit: Maximum number of notifications to return
            include_archived: Include archived notifications
        
        Returns:
            list: List of notifications with specified action type
        """
        try:
            if not action_type:
                return []
            
            notifications = []
            
            for notification in cls.action_type_index.query(
                action_type,
                scan_index_forward=False,  # Newest first
                limit=limit
            ):
                if include_archived or not notification.archived:
                    notifications.append(notification)
            
            return notifications
        except Exception as e:
            logger.error(f"Error getting notifications by action type {action_type}: {str(e)}")
            return []
    
    @classmethod
    def get_recent_notifications(cls, hours: int = 24, 
                                limit: int = 100) -> list:
        """
        Get recent notifications (not archived)
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of notifications to return
        
        Returns:
            list: List of recent notifications
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            notifications = []
            
            for notification in cls.query(
                "notifications",
                cls.created_at >= cutoff,
                filter_condition=cls.archived == False,
                scan_index_forward=False,  # Newest first
                limit=limit
            ):
                notifications.append(notification)
            
            return notifications
        except Exception as e:
            logger.error(f"Error getting recent notifications: {str(e)}")
            return []
    
    @classmethod
    def get_urgent_notifications(cls, include_read: bool = False) -> list:
        """
        Get urgent notifications (high or critical priority)
        
        Args:
            include_read: Include read notifications
        
        Returns:
            list: List of urgent notifications
        """
        try:
            notifications = []
            
            # Get high priority notifications
            for notification in cls.priority_index.query("high", limit=100):
                if not notification.archived and (include_read or not notification.is_read):
                    notifications.append(notification)
            
            # Get critical priority notifications
            for notification in cls.priority_index.query("critical", limit=100):
                if not notification.archived and (include_read or not notification.is_read):
                    notifications.append(notification)
            
            # Sort by created_at (newest first)
            notifications.sort(key=lambda x: x.created_at, reverse=True)
            
            return notifications
        except Exception as e:
            logger.error(f"Error getting urgent notifications: {str(e)}")
            return []
    
    @classmethod
    def get_unread_count(cls) -> int:
        """
        Get count of unread notifications (not archived)
        
        Returns:
            int: Number of unread notifications
        """
        try:
            count = 0
            for _ in cls.is_read_index.query(False, limit=1000):  # is_read = False
                count += 1
            return count
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return 0
    
    @classmethod
    def get_notification_counts(cls) -> dict:
        """
        Get counts of notifications by type and status
        
        Returns:
            dict: Notification counts
        """
        try:
            counts = {
                "total": 0,
                "unread": 0,
                "urgent": 0,
                "by_type": {},
                "by_priority": {}
            }
            
            for notification in cls.query("notifications", limit=1000):
                if notification.archived:
                    continue
                
                counts["total"] += 1
                
                if not notification.is_read:
                    counts["unread"] += 1
                
                if notification.priority in ["high", "critical"]:
                    counts["urgent"] += 1
                
                # Count by type
                counts["by_type"][notification.notification_type] = \
                    counts["by_type"].get(notification.notification_type, 0) + 1
                
                # Count by priority
                counts["by_priority"][notification.priority] = \
                    counts["by_priority"].get(notification.priority, 0) + 1
            
            return counts
        except Exception as e:
            logger.error(f"Error getting notification counts: {str(e)}")
            return {"total": 0, "unread": 0, "urgent": 0, "by_type": {}, "by_priority": {}}
    
    @classmethod
    def mark_all_as_read(cls):
        """
        Mark all active notifications as read
        
        Returns:
            int: Number of notifications marked as read
        """
        try:
            count = 0
            for notification in cls.get_unread_notifications(limit=1000):
                notification.mark_as_read()
                count += 1
            
            logger.info(f"Marked {count} notifications as read")
            return count
        except Exception as e:
            logger.error(f"Error marking all as read: {str(e)}")
            return 0
    
    @classmethod
    def archive_old_notifications(cls, days: int = 30) -> int:
        """
        Archive notifications older than specified days
        
        Args:
            days: Number of days
        
        Returns:
            int: Number of notifications archived
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            archived_count = 0
            
            for notification in cls.query(
                "notifications",
                cls.created_at < cutoff,
                filter_condition=cls.archived == False,
                limit=1000
            ):
                notification.archive()
                archived_count += 1
            
            logger.info(f"Archived {archived_count} notifications older than {days} days")
            return archived_count
        except Exception as e:
            logger.error(f"Error archiving old notifications: {str(e)}")
            return 0
    
    @classmethod
    def cleanup_read_notifications(cls, days: int = 90) -> int:
        """
        Delete archived notifications older than specified days
        This should be run periodically to clean up old data
        
        Args:
            days: Number of days
        
        Returns:
            int: Number of notifications deleted
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            deleted_count = 0
            
            for notification in cls.query(
                "notifications",
                cls.created_at < cutoff,
                filter_condition=cls.archived == True,
                limit=1000
            ):
                notification.delete()
                deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} archived notifications older than {days} days")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up notifications: {str(e)}")
            return 0
    
    # ============= INSTANCE METHODS =============
    
    def mark_as_read(self) -> 'Notification':
        """
        Mark notification as read
        
        Returns:
            Notification: Updated notification
        """
        try:
            if not self.is_read:
                self.is_read = True
                self.updated_at = datetime.utcnow()
                self.save()
                logger.info(f"Notification {self.sk} marked as read")
            
            return self
        except Exception as e:
            logger.error(f"Failed to mark notification {self.sk} as read: {str(e)}")
            raise
    
    def mark_as_unread(self) -> 'Notification':
        """
        Mark notification as unread
        
        Returns:
            Notification: Updated notification
        """
        try:
            if self.is_read:
                self.is_read = False
                self.updated_at = datetime.utcnow()
                self.save()
                logger.info(f"Notification {self.sk} marked as unread")
            
            return self
        except Exception as e:
            logger.error(f"Failed to mark notification {self.sk} as unread: {str(e)}")
            raise
    
    def archive(self) -> 'Notification':
        """
        Archive notification
        
        Returns:
            Notification: Updated notification
        """
        try:
            if not self.archived:
                self.archived = True
                self.updated_at = datetime.utcnow()
                self.save()
                logger.info(f"Notification {self.sk} archived")
            
            return self
        except Exception as e:
            logger.error(f"Failed to archive notification {self.sk}: {str(e)}")
            raise
    
    def unarchive(self) -> 'Notification':
        """
        Unarchive notification
        
        Returns:
            Notification: Updated notification
        """
        try:
            if self.archived:
                self.archived = False
                self.updated_at = datetime.utcnow()
                self.save()
                logger.info(f"Notification {self.sk} unarchived")
            
            return self
        except Exception as e:
            logger.error(f"Failed to unarchive notification {self.sk}: {str(e)}")
            raise
    
    def update_metadata(self, key: str, value: Any):
        """
        Update metadata field
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        try:
            if not self.metadata:
                self.metadata = {}
            
            self.metadata[key] = value
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Updated metadata for notification {self.sk}: {key}={value}")
        except Exception as e:
            logger.error(f"Failed to update metadata for notification {self.sk}: {str(e)}")
            raise
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value by key
        
        Args:
            key: Metadata key
            default: Default value if key not found
        
        Returns:
            Metadata value or default
        """
        if self.metadata and key in self.metadata:
            return self.metadata[key]
        return default
    
    def is_urgent(self) -> bool:
        """
        Check if notification is urgent
        
        Returns:
            bool: True if urgent (high or critical priority)
        """
        return self.priority in ["high", "critical"]
    
    def get_age_days(self) -> float:
        """
        Get age of notification in days
        
        Returns:
            float: Age in days
        """
        if not self.created_at:
            return 0.0
        
        delta = datetime.utcnow() - self.created_at
        return delta.days + delta.seconds / 86400.0
    
    def is_actionable(self) -> bool:
        """
        Check if notification is actionable
        
        Returns:
            bool: True if has action_type
        """
        return bool(self.action_type)
    
    def to_dict(self) -> dict:
        """
        Convert notification to dictionary for API response
        
        Returns:
            dict: Complete notification information
        """
        try:
            return {
                "notification_id": self.sk,
                "title": self.title,
                "message": self.message,
                "priority": self.priority,
                "notification_type": self.notification_type,
                "action_type": self.action_type,
                "is_read": self.is_read,
                "archived": self.archived,
                "is_urgent": self.is_urgent(),
                "is_actionable": self.is_actionable(),
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
                "age_days": round(self.get_age_days(), 1),
                "metadata": self.metadata or {}
            }
        except Exception as e:
            logger.error(f"Error converting notification to dict: {str(e)}")
            return {}
    
    def to_summary_dict(self) -> dict:
        """
        Get summary representation of notification
        
        Returns:
            dict: Summary information
        """
        try:
            return {
                "notification_id": self.sk,
                "title": self.title,
                "priority": self.priority,
                "notification_type": self.notification_type,
                "action_type": self.action_type,
                "is_read": self.is_read,
                "is_urgent": self.is_urgent(),
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "age_days": round(self.get_age_days(), 1)
            }
        except Exception as e:
            logger.error(f"Error converting notification to summary dict: {str(e)}")
            return {}
    
    def save(self, condition=None, **kwargs):
        """Override save to update updated_at timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(condition=condition, **kwargs)


# ============= NOTIFICATION MANAGER =============
class NotificationManager:
    """
    Manager class for notification-related operations
    """
    
    @staticmethod
    def get_dashboard_stats() -> dict:
        """
        Get dashboard statistics for notifications
        
        Returns:
            dict: Dashboard statistics
        """
        try:
            counts = Notification.get_notification_counts()
            
            # Get recent urgent notifications
            urgent = Notification.get_urgent_notifications(include_read=False)
            
            # Get recent notifications by type
            recent_by_type = {}
            for n_type in counts["by_type"].keys():
                recent = Notification.get_by_type(n_type, limit=5)
                if recent:
                    recent_by_type[n_type] = [n.to_summary_dict() for n in recent]
            
            return {
                "counts": counts,
                "urgent_notifications": [n.to_summary_dict() for n in urgent[:10]],  # Top 10 urgent
                "recent_by_type": recent_by_type,
                "unread_count": counts["unread"],
                "urgent_count": counts["urgent"]
            }
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            return {
                "counts": {"total": 0, "unread": 0, "urgent": 0, "by_type": {}, "by_priority": {}},
                "urgent_notifications": [],
                "recent_by_type": {},
                "unread_count": 0,
                "urgent_count": 0
            }
    
    @staticmethod
    def send_bulk_notification(title: str, message: str,
                              notification_type: str, priority: str = "medium",
                              metadata_list: List[Dict] = None) -> dict:
        """
        Send bulk notifications with different metadata
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            metadata_list: List of metadata dicts for each notification
        
        Returns:
            dict: Results of bulk notification sending
        """
        try:
            if not metadata_list:
                metadata_list = [{}]
            
            results = {
                "successful": [],
                "failed": [],
                "total": len(metadata_list)
            }
            
            for i, metadata in enumerate(metadata_list):
                try:
                    notification = Notification.create_notification(
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        priority=priority,
                        metadata=metadata
                    )
                    results["successful"].append({
                        "index": i,
                        "notification_id": notification.sk,
                        "metadata": metadata
                    })
                except Exception as e:
                    results["failed"].append({
                        "index": i,
                        "error": str(e),
                        "metadata": metadata
                    })
            
            logger.info(f"Bulk notification sent: {len(results['successful'])} successful, {len(results['failed'])} failed")
            return results
            
        except Exception as e:
            logger.error(f"Error sending bulk notification: {str(e)}")
            return {"successful": [], "failed": [], "total": 0, "error": str(e)}
    
    @staticmethod
    def notify_inventory_low(product_id: str, product_name: str,
                           current_quantity: int, threshold: int) -> 'Notification':
        """
        Send inventory low notification
        
        Args:
            product_id: Product ID
            product_name: Product name
            current_quantity: Current quantity
            threshold: Threshold quantity
        
        Returns:
            Notification: Created inventory notification
        """
        title = f"Low Inventory Alert: {product_name}"
        message = f"Inventory for {product_name} is low. Current: {current_quantity}, Threshold: {threshold}"
        
        metadata = {
            "event": "inventory_low",
            "product_id": product_id,
            "product_name": product_name,
            "current_quantity": current_quantity,
            "threshold": threshold,
            "action_required": "restock"
        }
        
        return Notification.create_inventory_notification(
            title=title,
            message=message,
            product_id=product_id,
            batch_id="N/A",
            change_type="low_stock",
            priority="high"
        )
    
    @staticmethod
    def notify_order_status_change(order_id: str, order_number: str,
                                 old_status: str, new_status: str) -> 'Notification':
        """
        Send order status change notification
        
        Args:
            order_id: Order ID
            order_number: Order number
            old_status: Previous status
            new_status: New status
        
        Returns:
            Notification: Created order notification
        """
        title = f"Order Status Updated: {order_number}"
        message = f"Order {order_number} status changed from {old_status} to {new_status}"
        
        metadata = {
            "event": "order_status_change",
            "order_id": order_id,
            "order_number": order_number,
            "old_status": old_status,
            "new_status": new_status
        }
        
        return Notification.create_order_notification(
            title=title,
            message=message,
            order_id=order_id,
            order_status=new_status,
            priority="medium" if new_status in ["processing", "shipped"] else "low"
        )
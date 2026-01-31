from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute,
    UnicodeSetAttribute, JSONAttribute
)
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


class MetadataItem(MapAttribute):
    """MapAttribute for metadata items"""
    # Using DynamicMapAttribute for flexibility since metadata structure may vary
    pass


class Notification(Model):
    """
    Notification model for DynamoDB
    PK = notifications (partition key)
    SK = NOTIF-##### (sort key)
    """
    class Meta:
        table_name = "your-table-name"  # Replace with your table name
        region = "your-region"  # Replace with your AWS region
        # Add billing_mode, read_capacity_units, write_capacity_units if needed

    # Primary Key Attributes
    PK = UnicodeAttribute(hash_key=True, default="notifications")
    SK = UnicodeAttribute(range_key=True)

    # Notification Content
    title = UnicodeAttribute()
    message = UnicodeAttribute()
    priority = UnicodeAttribute()  # e.g., 'low', 'medium', 'high', 'critical'
    
    # Status Flags
    is_read = BooleanAttribute(default=False)
    archived = BooleanAttribute(default=False)
    
    # Timestamps
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    
    # Notification Type
    notification_type = UnicodeAttribute()  # e.g., 'system', 'user', 'order', 'inventory', 'promotion'
    
    # Metadata
    metadata = ListAttribute(of=MetadataItem, default=list)

    @classmethod
    def create_notification(cls, notification_id: str, **kwargs):
        """Helper method to create a new notification with proper SK format"""
        sk = f"NOTIF-{notification_id}"
        return cls(SK=sk, **kwargs)

    @classmethod
    def get_notification(cls, notification_id: str):
        """Helper method to retrieve a notification by ID"""
        sk = f"NOTIF-{notification_id}"
        return cls.get("notifications", sk)

    @classmethod
    def query_unread(cls):
        """Query all unread notifications"""
        return cls.query(
            "notifications",
            cls.SK.startswith("NOTIF-"),
            filter_condition=cls.is_read == False
        )

    @classmethod
    def query_by_priority(cls, priority: str):
        """Query notifications by priority"""
        # This requires a GSI on priority
        return cls.query(
            priority,
            cls.SK.startswith("NOTIF-"),
            index_name="PriorityIndex",  # You'll need to create this GSI
            filter_condition=cls.archived == False
        )

    @classmethod
    def query_by_type(cls, notification_type: str):
        """Query notifications by type"""
        # This requires a GSI on notification_type
        return cls.query(
            notification_type,
            cls.SK.startswith("NOTIF-"),
            index_name="TypeIndex",  # You'll need to create this GSI
            filter_condition=cls.archived == False
        )

    @classmethod
    def query_active(cls):
        """Query all active (non-archived) notifications"""
        return cls.query(
            "notifications",
            cls.SK.startswith("NOTIF-"),
            filter_condition=cls.archived == False
        )

    @classmethod
    def query_recent(cls, days: int = 7):
        """Query notifications from the last N days"""
        # This requires a GSI with created_at as sort key
        # For now, we'll filter after querying (inefficient for large datasets)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return [
            notification for notification in cls.query_active()
            if notification.created_at >= cutoff_date
        ]

    @classmethod
    def get_unread_count(cls) -> int:
        """Get count of unread notifications"""
        # Note: This scans the table, consider using a GSI with is_read as partition key
        # for better performance
        count = 0
        for _ in cls.query(
            "notifications",
            cls.SK.startswith("NOTIF-"),
            filter_condition=(cls.is_read == False) & (cls.archived == False)
        ):
            count += 1
        return count

    def mark_as_read(self):
        """Mark the notification as read"""
        if not self.is_read:
            self.is_read = True
            self.updated_at = datetime.utcnow()
            self.save()
        return self

    def mark_as_unread(self):
        """Mark the notification as unread"""
        if self.is_read:
            self.is_read = False
            self.updated_at = datetime.utcnow()
            self.save()
        return self

    def archive(self):
        """Archive the notification"""
        if not self.archived:
            self.archived = True
            self.updated_at = datetime.utcnow()
            self.save()
        return self

    def unarchive(self):
        """Unarchive the notification"""
        if self.archived:
            self.archived = False
            self.updated_at = datetime.utcnow()
            self.save()
        return self

    def add_metadata(self, key: str, value: Any):
        """
        Add metadata to the notification
        
        Args:
            key: Metadata key
            value: Metadata value (must be JSON serializable)
        """
        metadata_item = MetadataItem()
        metadata_item[key] = value
        self.metadata.append(metadata_item)
        self.updated_at = datetime.utcnow()
        self.save()

    def get_metadata_value(self, key: str) -> Optional[Any]:
        """
        Get a specific metadata value by key
        
        Args:
            key: Metadata key to search for
            
        Returns:
            The value if found, None otherwise
        """
        for item in self.metadata:
            if key in item:
                return item[key]
        return None

    def update_metadata(self, key: str, value: Any):
        """
        Update existing metadata or add if not exists
        
        Args:
            key: Metadata key
            value: New metadata value
        """
        found = False
        for item in self.metadata:
            if key in item:
                item[key] = value
                found = True
                break
        
        if not found:
            self.add_metadata(key, value)
        else:
            self.updated_at = datetime.utcnow()
            self.save()

    def get_metadata_dict(self) -> Dict[str, Any]:
        """
        Convert metadata list to a dictionary
        Note: If there are duplicate keys, the last value wins
        """
        result = {}
        for item in self.metadata:
            # Each item is a dict-like MapAttribute
            for key, value in item.attribute_values.items():
                result[key] = value
        return result

    def is_urgent(self) -> bool:
        """Check if notification is urgent (high or critical priority)"""
        return self.priority in ['high', 'critical']

    def get_age_days(self) -> float:
        """Get age of notification in days"""
        age = datetime.utcnow() - self.created_at
        return age.days + age.seconds / 86400.0

    def to_summary_dict(self) -> Dict[str, Any]:
        """Get summary representation of the notification"""
        return {
            "notification_id": self.SK.replace("NOTIF-", ""),
            "title": self.title,
            "priority": self.priority,
            "type": self.notification_type,
            "is_read": self.is_read,
            "archived": self.archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "age_days": round(self.get_age_days(), 1),
            "is_urgent": self.is_urgent()
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Get full representation of the notification"""
        return {
            "notification_id": self.SK.replace("NOTIF-", ""),
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "type": self.notification_type,
            "is_read": self.is_read,
            "archived": self.archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.get_metadata_dict(),
            "age_days": round(self.get_age_days(), 1),
            "is_urgent": self.is_urgent()
        }

    @classmethod
    def create_system_notification(cls, notification_id: str, title: str, message: str, 
                                   priority: str = "medium", metadata: Optional[Dict] = None):
        """Create a system notification"""
        notification = cls.create_notification(
            notification_id=notification_id,
            title=title,
            message=message,
            priority=priority,
            notification_type="system"
        )
        
        if metadata:
            for key, value in metadata.items():
                notification.add_metadata(key, value)
        
        return notification

    @classmethod
    def create_user_notification(cls, notification_id: str, title: str, message: str, 
                                 user_id: str, priority: str = "medium", metadata: Optional[Dict] = None):
        """Create a user-specific notification"""
        notification = cls.create_notification(
            notification_id=notification_id,
            title=title,
            message=message,
            priority=priority,
            notification_type="user"
        )
        
        # Add user_id to metadata
        notification.add_metadata("user_id", user_id)
        
        if metadata:
            for key, value in metadata.items():
                notification.add_metadata(key, value)
        
        return notification

    @classmethod
    def mark_all_as_read(cls):
        """Mark all active notifications as read"""
        for notification in cls.query_active():
            if not notification.is_read:
                notification.mark_as_read()
        return True

    @classmethod
    def archive_old_notifications(cls, days: int = 30):
        """Archive notifications older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        archived_count = 0
        
        for notification in cls.query_active():
            if notification.created_at < cutoff_date:
                notification.archive()
                archived_count += 1
        
        return archived_count
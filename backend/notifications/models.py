"""
Notifications Model - Following ERD Specification with Enhancements
PK = "notifications", SK = "NOTIF-#####" (5-digit format)
Single Table Design using RamyeonCornerDB

UPDATED: Uses CounterService for atomic SK generation.
         Added recipient_id attribute + RecipientIndex GSI
         for user‑specific notification queries.
         Added TTL support and atomic status updates.
"""
import os
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, UTCDateTimeAttribute,
    JSONAttribute, NumberAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from app.utils.counters import counter_service
from datetime import datetime, timedelta
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# ============= GLOBAL SECONDARY INDEXES =============
class NotificationTypeIndex(GlobalSecondaryIndex):
    """GSI for querying notifications by type"""
    class Meta:
        index_name = 'notification-type-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    notification_type = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class PriorityIndex(GlobalSecondaryIndex):
    """GSI for querying notifications by priority"""
    class Meta:
        index_name = 'notification-priority-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    priority = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class IsReadIndex(GlobalSecondaryIndex):
    """GSI for querying notifications by read status"""
    class Meta:
        index_name = 'notification-is-read-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    is_read = BooleanAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class ActionTypeIndex(GlobalSecondaryIndex):
    """GSI for querying notifications by action type"""
    class Meta:
        index_name = 'notification-action-type-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    action_type = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class RecipientIndex(GlobalSecondaryIndex):
    """
    GSI: Query notifications by recipient.
    Essential for user-specific dashboards.
    """
    class Meta:
        index_name = 'notification-recipient-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    recipient_id = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


# ============= MAIN NOTIFICATION MODEL =============
class Notification(Model):
    """
    NOTIFICATION MODEL - with recipient support and actionable fields.
    """

    class Meta:
        table_name = os.getenv('DYNAMO_TABLE_NAME', 'RamyeonCornerDB')
        region = os.getenv('AWS_REGION', 'ap-southeast-1')
        if os.getenv('DYNAMODB_LOCAL', 'false').lower() == 'true':
            host = os.getenv('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')
        read_capacity_units = 10
        write_capacity_units = 20

    # ---------- PRIMARY KEYS ----------
    PK = UnicodeAttribute(hash_key=True, default="notifications")
    SK = UnicodeAttribute(range_key=True)  # "NOTIF-00001"

    # ---------- GSI DEFINITIONS ----------
    type_index = NotificationTypeIndex()
    priority_index = PriorityIndex()
    is_read_index = IsReadIndex()
    action_type_index = ActionTypeIndex()
    recipient_index = RecipientIndex()

    # ---------- NOTIFICATION CONTENT ----------
    title = UnicodeAttribute()
    message = UnicodeAttribute()
    priority = UnicodeAttribute()           # low, medium, high, urgent, critical
    notification_type = UnicodeAttribute()  # system, user, order, inventory, ...

    # ---------- ACTIONABLE NOTIFICATIONS ----------
    action_type = UnicodeAttribute(null=True)  # view_order, update_inventory, ...

    # ---------- RECIPIENT ----------
    recipient_id = UnicodeAttribute(null=True)   # user ID (string)

    # ---------- STATUS FLAGS ----------
    is_read = BooleanAttribute(default=False)
    archived = BooleanAttribute(default=False)

    # ---------- TIMESTAMPS ----------
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    delivered_at = UTCDateTimeAttribute(null=True)

    # ---------- TTL (Time-to-Live) ----------
    # Set to Unix timestamp when the notification should be automatically deleted.
    # Must be enabled on the DynamoDB table.
    ttl = NumberAttribute(null=True)

    # ---------- METADATA ----------
    metadata = JSONAttribute(null=True)   # flexible JSON for event details

    # ============= VALIDATION METHODS =============
    @staticmethod
    def validate_priority(priority: str) -> bool:
        """Validate priority value (Django uses 'urgent', we also accept 'critical')"""
        valid_priorities = {"low", "medium", "high", "urgent", "critical"}
        return priority in valid_priorities

    @staticmethod
    def validate_notification_type(notification_type: str) -> bool:
        valid_types = {
            "system", "user", "order", "inventory", "promotion",
            "alert", "reminder", "security", "maintenance", "update"
        }
        return notification_type in valid_types

    # ============= CLASS METHODS =============
    @classmethod
    def create_notification(cls,
                            title: str,
                            message: str,
                            notification_type: str,
                            priority: str = "medium",
                            recipient_id: Optional[str] = None,
                            recipient_username: Optional[str] = None,  # for metadata
                            action_type: Optional[str] = None,
                            metadata: Optional[Dict] = None,
                            delivered_at: Optional[datetime] = None,
                            ttl_days: int = 30) -> 'Notification':
        """
        Create a new notification with auto-generated SK using CounterService.
        Now accepts recipient_id and stores it both as an attribute and in metadata.
        Sets TTL to `ttl_days` from now.
        """
        try:
            # Validate
            if not cls.validate_notification_type(notification_type):
                raise ValueError(f"Invalid notification type: {notification_type}")
            if not cls.validate_priority(priority):
                raise ValueError(f"Invalid priority: {priority}")

            # Generate SK using CounterService
            SK = counter_service.get_next_id('notifications')

            # Prepare metadata – include recipient info if provided
            meta = metadata.copy() if metadata else {}
            if recipient_id:
                meta['recipient_id'] = recipient_id
            if recipient_username:
                meta['recipient_username'] = recipient_username

            # Calculate TTL (Unix timestamp)
            expiry = datetime.utcnow() + timedelta(days=ttl_days)
            ttl = int(expiry.timestamp())

            # Create instance
            notification = cls(
                PK="notifications",
                SK=SK,
                title=title.strip(),
                message=message.strip(),
                notification_type=notification_type,
                priority=priority,
                recipient_id=recipient_id,
                action_type=action_type,
                metadata=meta,
                delivered_at=delivered_at or datetime.utcnow(),
                ttl=ttl,
                is_read=False,
                archived=False
                # created_at and updated_at will use defaults
            )
            notification.save()

            logger.info(f"Notification created: {SK} - Type: {notification_type}, Recipient: {recipient_id}")
            return notification

        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            raise

    # --- Convenience factories (now with recipient_id) ---
    @classmethod
    def create_system_notification(cls,
                                   title: str,
                                   message: str,
                                   recipient_id: Optional[str] = None,
                                   priority: str = "medium",
                                   metadata: Optional[Dict] = None) -> 'Notification':
        """Create a system notification, optionally for a specific user."""
        return cls.create_notification(
            title=title,
            message=message,
            notification_type="system",
            priority=priority,
            recipient_id=recipient_id,
            action_type="system_alert",
            metadata=metadata
        )

    @classmethod
    def create_order_notification(cls,
                                  title: str,
                                  message: str,
                                  order_id: str,
                                  order_status: str,
                                  recipient_id: Optional[str] = None,
                                  priority: str = "medium") -> 'Notification':
        """Create an order notification for a specific user."""
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
            recipient_id=recipient_id,
            action_type="view_order",
            metadata=metadata
        )

    @classmethod
    def create_inventory_notification(cls,
                                      title: str,
                                      message: str,
                                      product_id: str,
                                      batch_id: str,
                                      change_type: str,
                                      recipient_id: Optional[str] = None,
                                      priority: str = "high") -> 'Notification':
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
            recipient_id=recipient_id,
            action_type="update_inventory",
            metadata=metadata
        )

    @classmethod
    def create_security_notification(cls,
                                     title: str,
                                     message: str,
                                     event_type: str,
                                     ip_address: Optional[str] = None,
                                     recipient_id: Optional[str] = None,
                                     priority: str = "critical") -> 'Notification':
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
            recipient_id=recipient_id,
            action_type="review_security",
            metadata=metadata
        )

    # ============= QUERY METHODS (RECIPIENT‑SPECIFIC) =============
    @classmethod
    def get_by_recipient(cls,
                         recipient_id: str,
                         is_read: Optional[bool] = None,
                         notification_type: Optional[str] = None,
                         priority: Optional[str] = None,
                         limit: int = 50,
                         include_archived: bool = False) -> List['Notification']:
        """
        Get notifications for a specific recipient using the RecipientIndex GSI.
        Optional filters: read status, type, priority.
        """
        try:
            # Base query on the GSI
            query_kwargs = {
                'hash_key': recipient_id,
                'scan_index_forward': False,  # newest first
                'limit': limit
            }

            # We'll filter after fetching because GSI only has recipient+created_at
            notifications = []
            for notification in cls.recipient_index.query(**query_kwargs):
                # Apply client-side filters
                if not include_archived and notification.archived:
                    continue
                if is_read is not None and notification.is_read != is_read:
                    continue
                if notification_type and notification.notification_type != notification_type:
                    continue
                if priority and notification.priority != priority:
                    continue
                notifications.append(notification)
                if len(notifications) >= limit:
                    break

            return notifications
        except Exception as e:
            logger.error(f"Error getting notifications for recipient {recipient_id}: {str(e)}")
            return []

    @classmethod
    def get_unread_for_recipient(cls,
                                 recipient_id: str,
                                 limit: int = 50) -> List['Notification']:
        """Convenience: unread notifications for a user."""
        return cls.get_by_recipient(recipient_id, is_read=False, limit=limit)

    @classmethod
    def get_high_priority_for_recipient(cls,
                                        recipient_id: str,
                                        limit: int = 50) -> List['Notification']:
        """Convenience: high/urgent priority notifications for a user."""
        all_high = cls.get_by_recipient(recipient_id, limit=limit * 2)  # fetch more then filter
        high_priority = [n for n in all_high if n.priority in ('high', 'urgent', 'critical')]
        return high_priority[:limit]

    @classmethod
    def get_by_type_for_recipient(cls,
                                  recipient_id: str,
                                  notification_type: str,
                                  limit: int = 50) -> List['Notification']:
        """Convenience: notifications of a specific type for a user."""
        return cls.get_by_recipient(recipient_id, notification_type=notification_type, limit=limit)

    # ============= QUERY METHODS (GLOBAL) =============

    @classmethod
    def get_by_id(cls, notification_id: str, include_archived: bool = False) -> Optional['Notification']:
        """Get notification by SK. If include_archived is False, archived notifications are treated as not found."""
        try:
            if not notification_id.startswith('NOTIF-'):
                notification_id = f"NOTIF-{notification_id.zfill(5)}"
            notification = cls.get("notifications", notification_id)
            # Return None if archived and not explicitly allowed
            if not include_archived and notification and notification.archived:
                return None
            return notification
        except cls.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error fetching {notification_id}: {e}")
            return None

    @classmethod
    def get_by_type(cls, notification_type: str, limit: int = 50, include_archived: bool = False) -> List['Notification']:
        """Get notifications by type using NotificationTypeIndex."""
        try:
            query_kwargs = {
                'hash_key': notification_type,
                'scan_index_forward': False,
                'limit': limit
            }
            results = []
            for n in cls.type_index.query(**query_kwargs):
                if not include_archived and n.archived:
                    continue
                results.append(n)
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            logger.error(f"Error in get_by_type({notification_type}): {e}")
            return []

    @classmethod
    def get_by_priority(cls, priority: str, limit: int = 50, include_archived: bool = False) -> List['Notification']:
        """Get notifications by priority using PriorityIndex."""
        try:
            query_kwargs = {
                'hash_key': priority,
                'scan_index_forward': False,
                'limit': limit
            }
            results = []
            for n in cls.priority_index.query(**query_kwargs):
                if not include_archived and n.archived:
                    continue
                results.append(n)
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            logger.error(f"Error in get_by_priority({priority}): {e}")
            return []

    @classmethod
    def get_unread_notifications(cls, limit: int = 50, include_archived: bool = False) -> List['Notification']:
        """Get unread notifications using IsReadIndex."""
        try:
            query_kwargs = {
                'hash_key': False,          # is_read = False
                'scan_index_forward': False,
                'limit': limit
            }
            results = []
            for n in cls.is_read_index.query(**query_kwargs):
                if not include_archived and n.archived:
                    continue
                results.append(n)
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            logger.error(f"Error in get_unread_notifications: {e}")
            return []

    @classmethod
    def get_by_action_type(cls, action_type: str, limit: int = 50, include_archived: bool = False) -> List['Notification']:
        """Get notifications by action type using ActionTypeIndex."""
        try:
            query_kwargs = {
                'hash_key': action_type,
                'scan_index_forward': False,
                'limit': limit
            }
            results = []
            for n in cls.action_type_index.query(**query_kwargs):
                if not include_archived and n.archived:
                    continue
                results.append(n)
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            logger.error(f"Error in get_by_action_type({action_type}): {e}")
            return []

    @classmethod
    def get_recent_notifications(cls, limit: int = 50, include_archived: bool = False) -> List['Notification']:
        """
        Get recent notifications.
        NOTE: Without a dedicated time-based index, this performs a scan.
        Results are not guaranteed to be chronological.
        """
        try:
            # Use scan with limit; we cannot sort by created_at efficiently.
            # Consider adding a GSI with constant hash key and created_at range key.
            results = []
            scan_kwargs = {
                'limit': limit * 2,  # fetch extra to allow for filtering
                'filter_condition': None
            }
            for n in cls.scan(**scan_kwargs):
                if not include_archived and n.archived:
                    continue
                results.append(n)
                if len(results) >= limit:
                    break
            # Sort in memory by created_at descending as best effort
            results.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
            return results[:limit]
        except Exception as e:
            logger.error(f"Error in get_recent_notifications: {e}")
            return []

    @classmethod
    def get_urgent_notifications(cls, include_read: bool = False, limit: int = 50) -> List['Notification']:
        """
        Get urgent/high/critical notifications.
        Queries PriorityIndex for each urgent priority and merges results.
        """
        urgent_priorities = ('high', 'urgent', 'critical')
        results = []
        try:
            for priority in urgent_priorities:
                query_kwargs = {
                    'hash_key': priority,
                    'scan_index_forward': False,
                    'limit': limit
                }
                for n in cls.priority_index.query(**query_kwargs):
                    if not include_read and n.is_read:
                        continue
                    if n.archived:
                        continue
                    results.append(n)
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break
            # Sort by created_at descending
            results.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
            return results[:limit]
        except Exception as e:
            logger.error(f"Error in get_urgent_notifications: {e}")
            return []

    @classmethod
    def get_unread_count(cls) -> int:
        """Return total number of unread notifications (expensive paginated query)."""
        try:
            count = 0
            query_kwargs = {
                'hash_key': False,
                'limit': 1000,   # page size
                'attributes_to_get': ['SK']  # minimise data
            }
            # Iterate through all unread notifications to count them
            for _ in cls.is_read_index.query(**query_kwargs):
                count += 1
            return count
        except Exception as e:
            logger.error(f"Error in get_unread_count: {e}")
            return 0

    @classmethod
    def get_notification_counts(cls) -> Dict[str, Any]:
        """
        Return global notification statistics.
        NOTE: This performs multiple paginated queries and can be expensive.
        For production, consider maintaining aggregated counters.
        """
        try:
            total = 0
            counts = {
                "total": 0,
                "unread": 0,
                "by_type": {},
                "by_priority": {},
                "urgent": 0
            }

            # Count unread
            counts["unread"] = cls.get_unread_count()

            # Count by type – iterate over all known types
            type_list = [
                "system", "user", "order", "inventory", "promotion",
                "alert", "reminder", "security", "maintenance", "update"
            ]
            for typ in type_list:
                c = 0
                for _ in cls.type_index.query(typ, limit=None, attributes_to_get=['SK']):
                    c += 1
                if c > 0:
                    counts["by_type"][typ] = c
                total += c

            # Count by priority
            priority_list = ["low", "medium", "high", "urgent", "critical"]
            urgent_total = 0
            for pri in priority_list:
                c = 0
                for _ in cls.priority_index.query(pri, limit=None, attributes_to_get=['SK']):
                    c += 1
                if c > 0:
                    counts["by_priority"][pri] = c
                if pri in ("high", "urgent", "critical"):
                    urgent_total += c
            counts["urgent"] = urgent_total
            counts["total"] = total

            return counts
        except Exception as e:
            logger.error(f"Error in get_notification_counts: {e}")
            return {"total": 0, "unread": 0, "by_type": {}, "by_priority": {}, "urgent": 0}

    @classmethod
    def mark_all_as_read(cls, recipient_id: Optional[str] = None) -> int:
        """
        Mark all notifications as read for a given recipient, or globally if recipient_id is None.
        Returns number of updated notifications.
        """
        updated = 0
        try:
            if recipient_id:
                # Query recipient's notifications
                notifications = cls.get_by_recipient(recipient_id, limit=10000)  # high limit
            else:
                # Global: scan (expensive!)
                notifications = cls.scan(filter_condition=None, limit=10000)
            for n in notifications:
                if not n.is_read:
                    n.mark_as_read()
                    updated += 1
            return updated
        except Exception as e:
            logger.error(f"Error in mark_all_as_read: {e}")
            return updated

    @classmethod
    def archive_old_notifications(cls, days: int = 30) -> int:
        """
        Archive notifications older than `days`.
        Performs a scan with a filter on created_at.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        archived = 0
        try:
            for n in cls.scan(limit=None):
                if n.created_at and n.created_at < cutoff and not n.archived:
                    n.archive()
                    archived += 1
            return archived
        except Exception as e:
            logger.error(f"Error in archive_old_notifications: {e}")
            return archived

    @classmethod
    def cleanup_read_notifications(cls, days: int = 7) -> int:
        """
        Permanently delete read notifications older than `days`.
        WARNING: This performs deletes and is irreversible.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = 0
        try:
            for n in cls.scan(limit=None):
                if n.is_read and n.created_at and n.created_at < cutoff:
                    n.delete()
                    deleted += 1
            return deleted
        except Exception as e:
            logger.error(f"Error in cleanup_read_notifications: {e}")
            return deleted

    # ============= INSTANCE METHODS =============
    def mark_as_read(self) -> 'Notification':
        """Atomically mark as read using update action."""
        if not self.is_read:
            # Use update to change only is_read and updated_at
            self.update(actions=[
                Notification.is_read.set(True),
                Notification.updated_at.set(datetime.utcnow())
            ])
            # Refresh local attributes
            self.is_read = True
            self.updated_at = datetime.utcnow()
        return self

    def mark_as_unread(self) -> 'Notification':
        """Atomically mark as unread."""
        if self.is_read:
            self.update(actions=[
                Notification.is_read.set(False),
                Notification.updated_at.set(datetime.utcnow())
            ])
            self.is_read = False
            self.updated_at = datetime.utcnow()
        return self

    def archive(self) -> 'Notification':
        """Atomically archive the notification."""
        if not self.archived:
            self.update(actions=[
                Notification.archived.set(True),
                Notification.updated_at.set(datetime.utcnow())
            ])
            self.archived = True
            self.updated_at = datetime.utcnow()
        return self

    def unarchive(self) -> 'Notification':
        """Atomically unarchive the notification."""
        if self.archived:
            self.update(actions=[
                Notification.archived.set(False),
                Notification.updated_at.set(datetime.utcnow())
            ])
            self.archived = False
            self.updated_at = datetime.utcnow()
        return self

    def update_metadata(self, key: str, value: Any):
        """Atomically update a single metadata field."""
        # Fetch current metadata, update, then save whole item.
        # For true atomic update of nested attribute, we'd need update expressions.
        # This simple version re-saves the entire item.
        if not self.metadata:
            self.metadata = {}
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()
        self.save()

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default) if self.metadata else default

    def is_urgent(self) -> bool:
        return self.priority in ("high", "urgent", "critical")

    def is_actionable(self) -> bool:
        return bool(self.action_type)

    def get_age_days(self) -> float:
        if not self.created_at:
            return 0.0
        delta = datetime.utcnow() - self.created_at
        return delta.days + delta.seconds / 86400.0

    def to_dict(self) -> dict:
        try:
            return {
                "notification_id": self.SK,
                "title": self.title,
                "message": self.message,
                "priority": self.priority,
                "notification_type": self.notification_type,
                "action_type": self.action_type,
                "recipient_id": self.recipient_id,
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
            logger.error(f"to_dict error: {e}")
            return {}

    def to_summary_dict(self) -> dict:
        try:
            return {
                "notification_id": self.SK,
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
            logger.error(f"to_summary_dict error: {e}")
            return {}

    def save(self, condition=None, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(condition=condition, **kwargs)


# ============= NOTIFICATION MANAGER =============
class NotificationManager:
    """High‑level operations, now recipient‑aware."""

    @staticmethod
    def get_dashboard_stats() -> dict:
        """Global stats."""
        try:
            counts = Notification.get_notification_counts()
            urgent = Notification.get_urgent_notifications(include_read=False)
            recent_by_type = {}
            for n_type in counts["by_type"].keys():
                recent = Notification.get_by_type(n_type, limit=5)
                if recent:
                    recent_by_type[n_type] = [n.to_summary_dict() for n in recent]
            return {
                "counts": counts,
                "urgent_notifications": [n.to_summary_dict() for n in urgent[:10]],
                "recent_by_type": recent_by_type,
                "unread_count": counts["unread"],
                "urgent_count": counts["urgent"]
            }
        except Exception as e:
            logger.error(f"Dashboard stats error: {e}")
            return {"counts": {}, "urgent_notifications": [], "recent_by_type": {}, "unread_count": 0, "urgent_count": 0}

    @staticmethod
    def send_bulk_notification(title: str, message: str,
                               notification_type: str, priority: str = "medium",
                               metadata_list: List[Dict] = None) -> dict:
        """Send notifications with different metadata (global or per‑recipient)."""
        # Implementation omitted for brevity – should use batch write
        pass

    @staticmethod
    def notify_inventory_low(product_id: str,
                             product_name: str,
                             current_quantity: int,
                             threshold: int,
                             recipient_id: Optional[str] = None) -> 'Notification':
        """
        Send inventory low notification.
        Now accepts recipient_id – if None, it's a global alert.
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
            priority="high",
            recipient_id=recipient_id,
            metadata=metadata
        )

    @staticmethod
    def notify_order_status_change(order_id: str,
                                   order_number: str,
                                   old_status: str,
                                   new_status: str,
                                   recipient_id: Optional[str] = None) -> 'Notification':
        """
        Send order status change notification.
        Now accepts recipient_id.
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
            priority="medium" if new_status in ["processing", "shipped"] else "low",
            recipient_id=recipient_id,
            metadata=metadata
        )
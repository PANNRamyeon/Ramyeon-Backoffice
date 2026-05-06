# notifications/services.py
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional, List, Dict, Tuple

from .models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Service layer for notification operations."""

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    def create_notification(self, title: str, message: str,
                            notification_type: str = 'system',
                            priority: str = 'medium',
                            action_type: Optional[str] = None,
                            metadata: Optional[Dict] = None) -> Dict:
        try:
            notification = Notification.create_notification(
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                action_type=action_type,
                metadata=metadata
            )
            return notification.to_dict()
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise Exception(f"Error creating notification: {str(e)}")

    def create_inventory_alert(self, product_id: str,
                               product_name: str,
                               current_stock: int) -> Dict:
        return self.create_notification(
            title=f"Low Stock Alert: {product_name}",
            message=f"Inventory for {product_name} is low. Current: {current_stock}",
            notification_type='inventory',
            priority='high',
            action_type='update_inventory',
            metadata={
                "event": "inventory_low",
                "product_id": product_id,
                "current_stock": current_stock
            }
        )

    # ------------------------------------------------------------------
    # RETRIEVAL
    # ------------------------------------------------------------------
    def get_notifications(self,
                          notification_type: Optional[str] = None,
                          is_read: Optional[bool] = None,
                          action_type: Optional[str] = None,
                          limit: int = 50,
                          last_key: Optional[Dict] = None,
                          include_archived: bool = False) -> Tuple[List[Dict], Optional[Dict]]:
        """
        Retrieve notifications with optional filters and pagination.
        include_archived allows fetching archived notifications.
        """
        try:
            if notification_type:
                items, lk = Notification.get_by_type(
                    notification_type=notification_type,
                    limit=limit,
                    last_key=last_key,
                    include_archived=include_archived
                )
                if is_read is not None:
                    items = [n for n in items if n.is_read == is_read]
                if action_type:
                    items = [n for n in items if n.action_type == action_type]
                return [n.to_dict() for n in items], lk

            if action_type:
                items, lk = Notification.get_by_action_type(
                    action_type=action_type,
                    limit=limit,
                    last_key=last_key,
                    include_archived=include_archived
                )
                if is_read is not None:
                    items = [n for n in items if n.is_read == is_read]
                return [n.to_dict() for n in items], lk

            if is_read is False:
                items, lk = Notification.get_unread_notifications(
                    limit=limit,
                    last_key=last_key,
                    include_archived=include_archived
                )
                return [n.to_dict() for n in items], lk

            # Fallback: recent notifications
            items = Notification.get_recent_notifications(
                limit=limit,
                include_archived=include_archived
            )
            return [n.to_dict() for n in items], None

        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return [], None

    def get_notification_by_id(self, notification_id: str,
                               include_archived: bool = False) -> Optional[Dict]:
        try:
            notification = Notification.get_by_id(notification_id, include_archived=include_archived)
            return notification.to_dict() if notification else None
        except Exception as e:
            logger.error(f"Error getting notification {notification_id}: {e}")
            return None

    def get_recent_notifications(self, hours: int = 24,
                                 limit: int = 50,
                                 include_archived: bool = False) -> List[Dict]:
        try:
            notifications = Notification.get_recent_notifications(
                hours=hours, limit=limit, include_archived=include_archived
            )
            return [n.to_dict() for n in notifications]
        except Exception as e:
            logger.error(f"Error getting recent notifications: {e}")
            return []

    def get_all_notifications(self, limit: int = 50,
                              start_key: Optional[Dict] = None) -> Tuple[List[Dict], Optional[Dict]]:
        try:
            scan_kwargs = {'limit': limit}
            if start_key:
                scan_kwargs['exclusive_start_key'] = start_key
            results = list(Notification.scan(**scan_kwargs))
            active = [n for n in results if not n.archived]
            last_key = results.last_evaluated_key if hasattr(results, 'last_evaluated_key') else None
            return [n.to_dict() for n in active], last_key
        except Exception as e:
            logger.error(f"Error scanning notifications: {e}")
            return [], None

    def get_unread_count(self) -> int:
        try:
            return Notification.get_unread_count()
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    # ------------------------------------------------------------------
    # STATUS UPDATES
    # ------------------------------------------------------------------
    def mark_as_read(self, notification_id: str) -> bool:
        try:
            notification = Notification.get_by_id(notification_id)
            if notification:
                notification.mark_as_read()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking {notification_id} as read: {e}")
            return False

    def mark_as_unread(self, notification_id: str) -> bool:
        try:
            notification = Notification.get_by_id(notification_id)
            if notification:
                notification.mark_as_unread()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking {notification_id} as unread: {e}")
            return False

    def mark_all_as_read(self) -> int:
        try:
            return Notification.mark_all_as_read()
        except Exception as e:
            logger.error(f"Error in mark_all_as_read: {e}")
            return 0

    # ------------------------------------------------------------------
    # ARCHIVAL AND DELETION
    # ------------------------------------------------------------------
    def archive_notification(self, notification_id: str) -> bool:
        try:
            notification = Notification.get_by_id(notification_id)
            if notification:
                notification.archive()
                return True
            return False
        except Exception as e:
            logger.error(f"Error archiving {notification_id}: {e}")
            return False

    def unarchive_notification(self, notification_id: str) -> bool:
        try:
            # Must fetch even if archived
            notification = Notification.get_by_id_including_archived(notification_id)
            if notification and notification.archived:
                notification.unarchive()
                return True
            return False
        except Exception as e:
            logger.error(f"Error unarchiving {notification_id}: {e}")
            return False

    def delete_notification(self, notification_id: str) -> bool:
        try:
            notification = Notification.get_by_id(notification_id)
            if notification:
                notification.delete()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting {notification_id}: {e}")
            return False


# Singleton
notification_service = NotificationService()
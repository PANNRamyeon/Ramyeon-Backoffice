# notifications/services.py
from datetime import datetime, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple

from .models import Notification  # PynamoDB model

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service layer for notification operations using the PynamoDB Notification model.
    """

    # ================================================================
    # NOTIFICATION CREATION METHODS
    # ================================================================

    def create_notification(self, title: str, message: str,
                            recipient_id: Optional[str] = None,
                            recipient_username: Optional[str] = None,
                            priority: str = 'medium',
                            notification_type: str = 'system',
                            metadata: Optional[Dict] = None) -> Dict:
        """
        Create a new notification using the Notification model.
        """
        try:
            notification = Notification.create_notification(
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                recipient_id=recipient_id,
                recipient_username=recipient_username,
                metadata=metadata,
                # delivered_at defaults to now
            )
            return notification.to_dict()
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise Exception(f"Error creating notification: {str(e)}")

    def create_inventory_alert(self, recipient_id: str, product_id: str,
                               current_stock: int, product_name: Optional[str] = None) -> Dict:
        """
        Create an inventory alert notification.
        """
        title = "Low Stock Alert"
        message = f"{product_name or 'Product'} is running low"
        metadata = {"product_id": product_id, "current_stock": current_stock}
        return self.create_notification(
            title=title,
            message=message,
            recipient_id=recipient_id,
            priority='high',
            notification_type='inventory',
            metadata=metadata
        )

    # ================================================================
    # NOTIFICATION RETRIEVAL METHODS
    # ================================================================

    def get_notifications(self, recipient_id: Optional[str] = None,
                          notification_type: Optional[str] = None,
                          is_read: Optional[bool] = None,
                          limit: int = 50,
                          include_archived: bool = False) -> List[Dict]:
        """
        Get notifications with filters. If recipient_id is provided, uses the recipient GSI;
        otherwise falls back to type/read indexes or scan.
        """
        try:
            if recipient_id:
                notifications = Notification.get_by_recipient(
                    recipient_id=recipient_id,
                    is_read=is_read,
                    notification_type=notification_type,
                    limit=limit,
                    include_archived=include_archived
                )
            elif notification_type:
                notifications = Notification.get_by_type(
                    notification_type=notification_type,
                    limit=limit,
                    include_archived=include_archived
                )
                if is_read is not None:
                    notifications = [n for n in notifications if n.is_read == is_read]
            elif is_read is not None:
                if is_read is False:
                    notifications = Notification.get_unread_notifications(
                        limit=limit,
                        include_archived=include_archived
                    )
                else:
                    # For read notifications, fallback to scan
                    notifications = self._scan_with_filters(
                        is_read=True,
                        include_archived=include_archived,
                        limit=limit
                    )
            else:
                notifications = Notification.get_recent_notifications(
                    limit=limit,
                    include_archived=include_archived
                )

            return [n.to_dict() for n in notifications]

        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return []

    def _scan_with_filters(self, is_read: bool = None,
                           notification_type: str = None,
                           recipient_id: str = None,
                           include_archived: bool = False,
                           limit: int = 50) -> List[Notification]:
        """
        Fallback method using scan with filter expressions.
        Should be used sparingly; prefer indexed queries.
        """
        conditions = []
        if not include_archived:
            conditions.append(Notification.archived == False)
        if is_read is not None:
            conditions.append(Notification.is_read == is_read)
        if notification_type:
            conditions.append(Notification.notification_type == notification_type)
        if recipient_id:
            conditions.append(Notification.recipient_id == recipient_id)

        filter_condition = None
        for cond in conditions:
            filter_condition = cond if filter_condition is None else filter_condition & cond

        try:
            scan_kwargs = {'limit': limit * 2}
            if filter_condition:
                scan_kwargs['filter_condition'] = filter_condition
            results = list(Notification.scan(**scan_kwargs))
            results.sort(key=lambda n: n.created_at or datetime.min, reverse=True)
            return results[:limit]
        except Exception as e:
            logger.error(f"Scan with filters failed: {e}")
            return []

    def get_notification_by_id(self, notification_id: str, include_archived: bool = False) -> Optional[Dict]:
        """Get a specific notification by its SK."""
        try:
            notification = Notification.get_by_id(notification_id, include_archived=include_archived)
            return notification.to_dict() if notification else None
        except Exception as e:
            logger.error(f"Error getting notification {notification_id}: {e}")
            return None

    def get_recent_notifications(self, limit: int = 10,
                                 hours: Optional[int] = None,
                                 include_archived: bool = False) -> List[Dict]:
        """
        Get recent notifications, optionally filtered by last N hours.
        """
        try:
            if hours:
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                filter_cond = Notification.created_at >= cutoff
                if not include_archived:
                    filter_cond &= (Notification.archived == False)
                results = list(Notification.scan(filter_condition=filter_cond, limit=limit * 2))
                results.sort(key=lambda n: n.created_at or datetime.min, reverse=True)
                return [n.to_dict() for n in results[:limit]]
            else:
                notifications = Notification.get_recent_notifications(limit=limit, include_archived=include_archived)
                return [n.to_dict() for n in notifications]
        except Exception as e:
            logger.error(f"Error getting recent notifications: {e}")
            return []

    def get_all_notifications(self, limit: int = 50,
                              include_archived: bool = False,
                              start_key: Optional[Dict] = None) -> Tuple[List[Dict], Optional[Dict]]:
        """
        Get all notifications with pagination using scan.
        Returns (items, last_evaluated_key).
        Note: Pagination is not fully implemented; returns all items up to limit.
        """
        try:
            notifications = list(Notification.scan(limit=limit))
            if not include_archived:
                notifications = [n for n in notifications if not n.archived]
            # For real pagination, we would need to use the underlying client's LastEvaluatedKey.
            # This is a simplified version.
            return [n.to_dict() for n in notifications], None
        except Exception as e:
            logger.error(f"Error getting all notifications: {e}")
            return [], None

    def get_unread_count(self, recipient_id: Optional[str] = None,
                         include_archived: bool = False) -> int:
        """
        Get count of unread notifications.
        If recipient_id is provided, uses recipient GSI; otherwise counts globally (expensive).
        """
        try:
            if recipient_id:
                unread = Notification.get_by_recipient(
                    recipient_id=recipient_id,
                    is_read=False,
                    include_archived=include_archived,
                    limit=10000
                )
                return len(unread)
            else:
                return Notification.get_unread_count()
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    # ================================================================
    # NOTIFICATION STATUS UPDATE METHODS
    # ================================================================

    def mark_as_read(self, notification_id: str) -> bool:
        """
        Mark a single notification as read.
        """
        try:
            notification = Notification.get_by_id(notification_id)
            if notification and not notification.is_read:
                notification.mark_as_read()
            return True
        except Exception as e:
            logger.error(f"Error marking {notification_id} as read: {e}")
            return False

    def mark_as_unread(self, notification_id: str) -> bool:
        """
        Mark a single notification as unread.
        """
        try:
            notification = Notification.get_by_id(notification_id)
            if notification and notification.is_read:
                notification.mark_as_unread()
            return True
        except Exception as e:
            logger.error(f"Error marking {notification_id} as unread: {e}")
            return False

    def mark_all_as_read(self, recipient_id: Optional[str] = None) -> int:
        """
        Mark all notifications as read for a recipient (or all if no recipient).
        Returns number updated.
        """
        try:
            if recipient_id:
                notifications = Notification.get_by_recipient(
                    recipient_id=recipient_id,
                    is_read=False,
                    limit=10000
                )
            else:
                notifications = Notification.get_unread_notifications(limit=10000)

            updated = 0
            for n in notifications:
                n.mark_as_read()
                updated += 1
            return updated
        except Exception as e:
            logger.error(f"Error in mark_all_as_read: {e}")
            return 0

    # ================================================================
    # NOTIFICATION DELETION & ARCHIVING
    # ================================================================

    def archive_notification(self, notification_id: str) -> bool:
        """
        Archive a notification.
        """
        try:
            notification = Notification.get_by_id(notification_id)
            if notification and not notification.archived:
                notification.archive()
            return True
        except Exception as e:
            logger.error(f"Error archiving {notification_id}: {e}")
            return False

    def delete_notification(self, notification_id: str) -> bool:
        """
        Permanently delete a notification.
        """
        try:
            notification = Notification.get_by_id(notification_id)
            if notification:
                notification.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting {notification_id}: {e}")
            return False
        
    def unarchive_notification(self, notification_id: str) -> bool:
        """Unarchive a notification."""
        try:
            # Retrieve the notification even if archived
            notification = Notification.get_by_id(notification_id, include_archived=True)
            if not notification:
                logger.warning(f"Notification {notification_id} not found")
                return False
            if not notification.archived:
                logger.info(f"Notification {notification_id} is already not archived")
                return True   # nothing to do, but consider it success
            notification.unarchive()
            return True
        except Exception as e:
            logger.error(f"Error unarchiving {notification_id}: {e}")
            return False


# Singleton instance
notification_service = NotificationService()
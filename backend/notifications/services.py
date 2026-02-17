# notifications/services.py
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from django.contrib.auth.models import User
from django.http import JsonResponse

# Import both the model AND its manager utility
from notifications.models import Notification, NotificationManager

from app.utils import generate_sk

import logging
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Notification service refactored to use the PynamoDB Notification model.
    All DynamoDB operations are performed through the model's methods,
    leveraging GSIs and the single‑table design.
    """

    @staticmethod
    def generate_notification_id() -> str:
        """Generate a sequential 5-digit notification ID: NOTIF-#####"""
        return generate_sk('NOTIF-', 'notification_seq')

    # ----------------------------------------------------------------
    # NOTIFICATION CREATION
    # ----------------------------------------------------------------
    def create_notification(
        self,
        title: str,
        message: str,
        recipient_id: Optional[int] = None,
        recipient_username: Optional[str] = None,
        priority: str = 'medium',
        notification_type: str = 'system',
        action_type: Optional[str] = None,
        delivered_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a notification using the model's factory."""
        try:
            recipient_str_id = None
            if recipient_id or recipient_username:
                recipient = self._get_recipient(recipient_id, recipient_username)
                if not recipient:
                    raise ValueError("Recipient not found")
                recipient_str_id = str(recipient.id)

            meta = metadata.copy() if metadata else {}
            if recipient_str_id:
                meta['recipient_id'] = recipient_str_id
            if recipient_username:
                meta['recipient_username'] = recipient_username

            notification = Notification.create_notification(
                title=title.strip(),
                message=message.strip(),
                notification_type=notification_type,
                priority=priority,
                recipient_id=recipient_str_id,
                action_type=action_type,
                metadata=meta,
                delivered_at=delivered_at or datetime.utcnow()
            )
            logger.info(f"Notification created: {notification.sk} for recipient {recipient_str_id}")
            return notification.to_dict()
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            raise

    def create_inventory_alert(
        self,
        recipient_id: int,
        product_id: str,
        current_stock: int,
        product_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an inventory low-stock notification.
        Delegates to the model's NotificationManager helper.
        """
        notification = NotificationManager.notify_inventory_low(
            product_id=product_id,
            product_name=product_name or "Product",
            current_quantity=current_stock,
            threshold=0,                     # adjust as needed
            recipient_id=str(recipient_id)
        )
        if product_name:
            notification.update_metadata('product_name', product_name)
        return notification.to_dict()

    # ----------------------------------------------------------------
    # NOTIFICATION RETRIEVAL
    # ----------------------------------------------------------------
    def get_notifications(
        self,
        recipient_id: Optional[int] = None,
        notification_type: Optional[str] = None,
        is_read: Optional[bool] = None,
        limit: int = 50,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve notifications with filters – uses GSI when possible."""
        try:
            if recipient_id:
                notifications = Notification.get_by_recipient(
                    recipient_id=str(recipient_id),
                    is_read=is_read,
                    notification_type=notification_type,
                    limit=limit,
                    include_archived=include_archived
                )
                return [n.to_dict() for n in notifications]

            # Fallback to scan (for admin views)
            filters = []
            if not include_archived:
                filters.append(Notification.archived == False)
            if notification_type:
                filters.append(Notification.notification_type == notification_type)
            if is_read is not None:
                filters.append(Notification.is_read == is_read)

            filter_cond = None
            for f in filters:
                filter_cond = f if filter_cond is None else (filter_cond & f)

            notifications = Notification.scan(filter_condition=filter_cond, limit=limit)
            result = [n.to_dict() for n in notifications]
            result.sort(key=lambda x: x['created_at'], reverse=True)
            return result[:limit]
        except Exception as e:
            logger.error(f"Error in get_notifications: {e}")
            return []

    def get_notification_by_id(self, notification_id: str) -> Optional[Dict[str, Any]]:
        notification = Notification.get_by_id(notification_id)
        return notification.to_dict() if notification else None

    def get_recent_notifications(
        self,
        limit: int = 10,
        hours: Optional[int] = None,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """Recent notifications, optionally filtered by age."""
        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            notifications = Notification.query(
                'notifications',
                Notification.created_at >= cutoff,
                filter_condition=None if include_archived else (Notification.archived == False),
                scan_index_forward=False,
                limit=limit
            )
        else:
            # default to last 24h
            cutoff = datetime.utcnow() - timedelta(hours=24)
            notifications = Notification.query(
                'notifications',
                Notification.created_at >= cutoff,
                filter_condition=None if include_archived else (Notification.archived == False),
                scan_index_forward=False,
                limit=limit
            )
        return [n.to_dict() for n in notifications]

    def get_all_notifications(
        self,
        limit: int = 50,
        include_archived: bool = False,
        start_key: Optional[Dict] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict]]:
        """Paginated scan of all notifications."""
        filter_cond = None if include_archived else (Notification.archived == False)
        try:
            scan_kwargs = {'filter_condition': filter_cond, 'limit': limit}
            if start_key:
                scan_kwargs['last_evaluated_key'] = start_key
            notifications = Notification.scan(**scan_kwargs)
            items = [n.to_dict() for n in notifications]
            last_key = getattr(notifications, 'last_evaluated_key', None)
            return items, last_key
        except Exception as e:
            logger.error(f"Error in get_all_notifications: {e}")
            return [], None

    def get_unread_count(
        self,
        recipient_id: Optional[int] = None,
        include_archived: bool = False
    ) -> int:
        """Count unread notifications – uses GSI where possible."""
        try:
            if recipient_id:
                # Use recipient GSI and count unread manually (acceptable for moderate scale)
                count = 0
                for n in Notification.recipient_index.query(str(recipient_id), limit=1000):
                    if not n.is_read and (include_archived or not n.archived):
                        count += 1
                return count
            else:
                # Global unread count via is_read GSI
                if include_archived:
                    return Notification.get_unread_count()  # model's method doesn't filter archived
                else:
                    count = 0
                    for n in Notification.is_read_index.query(False, limit=1000):
                        if not n.archived:
                            count += 1
                    return count
        except Exception as e:
            logger.error(f"Error in get_unread_count: {e}")
            return 0

    # ----------------------------------------------------------------
    # NOTIFICATION STATUS UPDATE
    # ----------------------------------------------------------------
    def mark_as_read(self, notification_id: str) -> bool:
        notification = Notification.get_by_id(notification_id)
        if notification:
            notification.mark_as_read()
            return True
        return False

    def mark_as_unread(self, notification_id: str) -> bool:
        notification = Notification.get_by_id(notification_id)
        if notification:
            notification.mark_as_unread()
            return True
        return False

    def mark_all_as_read(self, recipient_id: Optional[int] = None) -> int:
        count = 0
        if recipient_id:
            for n in Notification.get_by_recipient(str(recipient_id), is_read=False, limit=1000):
                n.mark_as_read()
                count += 1
        else:
            count = Notification.mark_all_as_read()
        return count

    # ----------------------------------------------------------------
    # NOTIFICATION DELETION & ARCHIVING
    # ----------------------------------------------------------------
    def archive_notification(self, notification_id: str) -> bool:
        notification = Notification.get_by_id(notification_id)
        if notification:
            notification.archive()
            return True
        return False

    def unarchive_notification(self, notification_id: str) -> bool:
        notification = Notification.get_by_id(notification_id)
        if notification:
            notification.unarchive()
            return True
        return False

    def delete_notification(self, notification_id: str) -> bool:
        try:
            notification = Notification.get('notifications', notification_id)
            notification.delete()
            return True
        except Notification.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error deleting {notification_id}: {e}")
            return False

    # ----------------------------------------------------------------
    # API METHODS
    # ----------------------------------------------------------------
    def get_all_notifications_api(self, request):
        limit = int(request.GET.get('limit', 50))
        include_archived = request.GET.get('include_archived', 'false').lower() == 'true'
        items, last_key = self.get_all_notifications(
            limit=limit,
            include_archived=include_archived,
            start_key=None
        )
        return JsonResponse({
            'notifications': items,
            'last_evaluated_key': last_key,
            'count': len(items)
        })

    def get_recent_notifications_api(self, request):
        limit = int(request.GET.get('limit', 10))
        hours = request.GET.get('hours')
        hours = int(hours) if hours else None
        include_archived = request.GET.get('include_archived', 'false').lower() == 'true'
        items = self.get_recent_notifications(
            limit=limit,
            hours=hours,
            include_archived=include_archived
        )
        return JsonResponse({'notifications': items})

    def mark_as_read_api(self, notification_id):
        success = self.mark_as_read(notification_id)
        return JsonResponse({'success': success})

    def mark_all_as_read_api(self, request):
        user = request.user if request.user.is_authenticated else None
        recipient_id = user.id if user else None
        count = self.mark_all_as_read(recipient_id=recipient_id)
        return JsonResponse({'marked_count': count})

    def archive_notification_api(self, notification_id):
        success = self.archive_notification(notification_id)
        return JsonResponse({'success': success})

    def unarchive_notification_api(self, notification_id):
        success = self.unarchive_notification(notification_id)
        return JsonResponse({'success': success})

    def delete_notification_api(self, notification_id):
        success = self.delete_notification(notification_id)
        return JsonResponse({'success': success})

    # ----------------------------------------------------------------
    # PRIVATE HELPERS
    # ----------------------------------------------------------------
    @staticmethod
    def _get_recipient(recipient_id=None, recipient_username=None):
        if recipient_id:
            try:
                return User.objects.get(id=recipient_id)
            except User.DoesNotExist:
                return None
        if recipient_username:
            try:
                return User.objects.get(username=recipient_username)
            except User.DoesNotExist:
                return None
        return None


# Singleton instance
notification_service = NotificationService()
import json
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import notification_service
from .email_verification_service import email_verification_service

logger = logging.getLogger(__name__)


# ================================================================
# UTILITY FUNCTIONS
# ================================================================
def validate_notification_id(notification_id):
    """Validate notification ID format (NOTIF-XXXXX)"""
    if not notification_id or not notification_id.startswith('NOTIF-'):
        raise ValueError('Invalid notification ID format. Expected format: NOTIF-XXXXX')
    return notification_id

def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ================================================================
# NOTIFICATION CREATION
# ================================================================
@api_view(['POST'])
def create_notification(request):
    """Create a new notification"""
    try:
        data = request.data
        title = data.get('title')
        message = data.get('message')
        if not title or not message:
            return Response({'success': False, 'message': 'title and message are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        notification = notification_service.create_notification(
            title=title,
            message=message,
            notification_type=data.get('notification_type', 'system'),
            priority=data.get('priority', 'medium'),
            action_type=data.get('action_type'),
            metadata=data.get('metadata', {})
        )
        return Response({'success': True, 'message': 'Notification created', 'data': notification},
                        status=status.HTTP_201_CREATED)
    except ValueError as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error creating notification")
        return Response({'success': False, 'message': f'Error creating notification: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_inventory_alert(request):
    """Create an inventory alert notification"""
    try:
        product_id = request.data.get('product_id')
        current_stock = request.data.get('current_stock')
        product_name = request.data.get('product_name', 'Product')
        threshold = safe_int(request.data.get('threshold', 0), 0)
        if not all([product_id, current_stock is not None]):
            return Response({'success': False, 'message': 'product_id and current_stock are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        notification = notification_service.create_inventory_alert(
            product_id=product_id,
            current_stock=current_stock,
            product_name=product_name,
            threshold=threshold
        )
        return Response({'success': True, 'message': 'Inventory alert created', 'data': notification},
                        status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.exception("Error creating inventory alert")
        return Response({'success': False, 'message': f'Error creating inventory alert: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# NOTIFICATION RETRIEVAL
# ================================================================
@api_view(['GET'])
def list_notifications(request):
    """List notifications with optional filters, pagination, and include_archived"""
    try:
        notification_type = request.query_params.get('type')
        is_read = request.query_params.get('is_read')
        action_type = request.query_params.get('action_type')
        limit = safe_int(request.query_params.get('limit', 50), 50)
        last_key = request.query_params.get('last_key')
        include_archived = request.query_params.get('include_archived', 'false').lower() == 'true'
        if last_key:
            last_key = json.loads(last_key)
        if is_read is not None:
            is_read = is_read.lower() in ['true', '1', 'yes']

        items, new_last_key = notification_service.get_notifications(
            notification_type=notification_type,
            is_read=is_read,
            action_type=action_type,
            limit=limit,
            last_key=last_key,
            include_archived=include_archived
        )
        return Response({
            'success': True,
            'count': len(items),
            'last_key': json.dumps(new_last_key) if new_last_key else None,
            'data': items
        })
    except Exception as e:
        logger.exception("Error listing notifications")
        return Response({'success': False, 'message': f'Error retrieving notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_notification(request, notification_id):
    """Get a specific notification, optionally including archived"""
    try:
        include_archived = request.query_params.get('include_archived', 'false').lower() == 'true'
        validate_notification_id(notification_id)
        notification = notification_service.get_notification_by_id(notification_id, include_archived=include_archived)
        if not notification:
            return Response({'success': False, 'message': 'Notification not found'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': notification})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error getting notification")
        return Response({'success': False, 'message': f'Error retrieving notification: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def recent_notifications(request):
    """Get recent notifications with optional hours and include_archived"""
    try:
        limit = safe_int(request.query_params.get('limit', 10), 10)
        hours = safe_int(request.query_params.get('hours', 24), 24)
        include_archived = request.query_params.get('include_archived', 'false').lower() == 'true'

        notifications = notification_service.get_recent_notifications(
            hours=hours,
            limit=limit,
            include_archived=include_archived
        )
        return Response({
            'success': True,
            'count': len(notifications),
            'data': notifications
        })
    except Exception as e:
        logger.exception("Error getting recent notifications")
        return Response({'success': False, 'message': f'Error retrieving recent notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def all_notifications(request):
    """Get all notifications (scan) with pagination"""
    try:
        limit = safe_int(request.query_params.get('limit', 50), 50)
        include_archived = request.query_params.get('include_archived', 'false').lower() == 'true'

        items, new_last_key = notification_service.get_all_notifications(
            limit=limit,
            include_archived=include_archived
        )
        return Response({
            'success': True,
            'count': len(items),
            'last_key': json.dumps(new_last_key) if new_last_key else None,
            'data': items
        })
    except Exception as e:
        logger.exception("Error getting all notifications")
        return Response({'success': False, 'message': f'Error retrieving all notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def unread_count(request):
    """Get current unread notification count"""
    try:
        count = notification_service.get_unread_count()
        return Response({'success': True, 'data': {'unread_count': count}})
    except Exception as e:
        logger.exception("Error getting unread count")
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# NOTIFICATION STATUS UPDATES
# ================================================================
@api_view(['PATCH'])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        validate_notification_id(notification_id)
        success = notification_service.mark_as_read(notification_id)
        if not success:
            return Response({'success': False, 'message': 'Notification not found'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'message': 'Notification marked as read'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error marking notification read")
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def mark_notification_unread(request, notification_id):
    """Mark a notification as unread"""
    try:
        validate_notification_id(notification_id)
        success = notification_service.mark_as_unread(notification_id)
        if not success:
            return Response({'success': False, 'message': 'Notification not found'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'message': 'Notification marked as unread'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error marking notification unread")
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def mark_all_notifications_read(request):
    """Mark all unread notifications as read"""
    try:
        count = notification_service.mark_all_as_read()
        return Response({'success': True, 'message': f'Marked {count} notifications as read', 'modified_count': count})
    except Exception as e:
        logger.exception("Error in mark all read")
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# ARCHIVE OPERATIONS
# ================================================================
@api_view(['PATCH'])
def archive_notification(request, notification_id):
    """Manually archive a notification"""
    try:
        validate_notification_id(notification_id)
        success = notification_service.archive_notification(notification_id)
        if not success:
            return Response({'success': False, 'message': 'Notification not found'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'message': 'Notification archived'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error archiving notification")
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def unarchive_notification(request, notification_id):
    """Unarchive a previously archived notification"""
    try:
        validate_notification_id(notification_id)
        success = notification_service.unarchive_notification(notification_id)
        if not success:
            return Response({'success': False, 'message': 'Notification not found or not archived'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'message': 'Notification unarchived'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error unarchiving notification")
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# DELETION OPERATIONS
# ================================================================
@api_view(['DELETE'])
def delete_notification(request, notification_id):
    """Permanently delete a notification"""
    try:
        validate_notification_id(notification_id)
        success = notification_service.delete_notification(notification_id)
        if not success:
            return Response({'success': False, 'message': 'Notification not found'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'message': 'Notification deleted'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error deleting notification")
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# STATISTICS
# ================================================================
@api_view(['GET'])
def notification_stats(request):
    """Global notification stats (unread count)"""
    try:
        count = notification_service.get_unread_count()
        return Response({'success': True, 'data': {'unread_count': count}})
    except Exception as e:
        logger.exception("Error in stats")
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# EMAIL VERIFICATION ENDPOINTS (unchanged)
# ================================================================
@api_view(['GET'])
def verify_email(request):
    try:
        token = request.query_params.get('token')
        if not token:
            return Response({'success': False, 'message': 'Verification token is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        result = email_verification_service.verify_email(token)
        if result.get('success'):
            return Response({'success': True, 'message': result.get('message', 'Email verified'),
                             'data': {'email': result.get('email'), 'user_id': result.get('user_id'),
                                      'username': result.get('username')}})
        else:
            return Response({'success': False, 'message': result.get('error', 'Email verification failed')},
                            status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error verifying email")
        return Response({'success': False, 'message': f'Error verifying email: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def resend_verification_email(request):
    try:
        email = request.data.get('email')
        if not email:
            return Response({'success': False, 'message': 'Email address is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        result = email_verification_service.resend_verification_code(email)
        if result.get('success'):
            return Response({'success': True, 'message': 'Verification code sent', 'token': result.get('token')})
        else:
            return Response({'success': False, 'message': result.get('error', 'Failed to send')},
                            status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error resending verification email")
        return Response({'success': False, 'message': f'Error resending verification code: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def send_verification_code(request):
    try:
        email = request.data.get('email')
        if not email:
            return Response({'success': False, 'message': 'Email address is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        result = email_verification_service.send_verification_code(email)
        if result.get('success'):
            return Response({'success': True, 'message': 'Verification code sent', 'token': result.get('token')})
        else:
            return Response({'success': False, 'message': result.get('error', 'Failed to send')},
                            status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error sending verification code")
        return Response({'success': False, 'message': f'Error sending verification code: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def verify_code(request):
    try:
        token = request.data.get('token')
        code = request.data.get('code')
        if not token or not code:
            return Response({'success': False, 'message': 'token and code are required'},
                            status=status.HTTP_400_BAD_REQUEST)
        result = email_verification_service.verify_code(token, code)
        if result.get('success'):
            return Response({'success': True, 'message': result.get('message', 'Email verified'),
                             'data': {'email': result.get('email'), 'user_id': result.get('user_id'),
                                      'username': result.get('username')}})
        else:
            return Response({'success': False, 'message': result.get('error', 'Email verification failed')},
                            status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error verifying code")
        return Response({'success': False, 'message': f'Error verifying code: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
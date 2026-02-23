# notifications/views.py
import json
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from app.decorators.authenticationDecorator import get_authenticated_user_from_jwt
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
    """Convert value to int, return default on failure."""
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
            return Response({
                'success': False,
                'message': 'title and message are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        notification = notification_service.create_notification(
            title=title,
            message=message,
            recipient_id=data.get('recipient_id'),
            recipient_username=data.get('recipient_username'),
            priority=data.get('priority', 'medium'),
            notification_type=data.get('notification_type', 'system'),
            metadata=data.get('metadata', {})
        )
        return Response({
            'success': True,
            'message': 'Notification created successfully',
            'data': notification
        }, status=status.HTTP_201_CREATED)
    except ValueError as e:
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error creating notification")
        return Response({'success': False, 'message': f'Error creating notification: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_inventory_alert(request):
    """Create an inventory alert notification"""
    try:
        recipient_id = request.data.get('recipient_id')
        product_id = request.data.get('product_id')
        current_stock = request.data.get('current_stock')
        product_name = request.data.get('product_name', 'Product')
        if not all([recipient_id, product_id, current_stock is not None]):
            return Response({
                'success': False,
                'message': 'recipient_id, product_id, and current_stock are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        notification = notification_service.create_inventory_alert(
            recipient_id=recipient_id,
            product_id=product_id,
            current_stock=current_stock,
            product_name=product_name
        )
        return Response({
            'success': True,
            'message': 'Inventory alert created successfully',
            'data': notification
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.exception("Error creating inventory alert")
        return Response({'success': False, 'message': f'Error creating inventory alert: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# NOTIFICATION RETRIEVAL
# ================================================================

@api_view(['GET'])
def list_notifications(request):
    """List notifications with optional filters"""
    try:
        recipient_id = request.query_params.get('recipient_id')
        notification_type = request.query_params.get('type')
        is_read = request.query_params.get('is_read')
        limit = safe_int(request.query_params.get('limit', 50), 50)

        if is_read is not None:
            is_read = is_read.lower() in ['true', '1', 'yes']

        notifications = notification_service.get_notifications(
            recipient_id=recipient_id,
            notification_type=notification_type,
            is_read=is_read,
            limit=limit
        )
        return Response({
            'success': True,
            'count': len(notifications),
            'data': notifications
        })
    except Exception as e:
        logger.exception("Error listing notifications")
        return Response({'success': False, 'message': f'Error retrieving notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_notification(request, notification_id):
    """Get a specific notification"""
    try:
        validate_notification_id(notification_id)
        notification = notification_service.get_notification_by_id(notification_id)
        if not notification:
            return Response({'success': False, 'message': 'Notification not found'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': notification})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error getting notification")
        return Response({'success': False, 'message': f'Error retrieving notification: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def user_notifications(request, user_id):
    """Get all notifications for a specific user"""
    try:
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            is_read = is_read.lower() in ['true', '1', 'yes']

        notifications = notification_service.get_notifications(
            recipient_id=user_id,
            is_read=is_read
        )
        unread_count = notification_service.get_unread_count(user_id)

        # Try to get username from first notification, otherwise use 'Unknown'
        username = notifications[0].get('recipient_username', 'Unknown') if notifications else 'Unknown'

        return Response({
            'success': True,
            'user': username,
            'total_count': len(notifications),
            'unread_count': unread_count,
            'data': notifications
        })
    except Exception as e:
        logger.exception("Error getting user notifications")
        return Response({'success': False, 'message': f'Error retrieving user notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def recent_notifications(request):
    """Get recent notifications with archive support"""
    try:
        limit = safe_int(request.query_params.get('limit', 10), 10)
        hours = request.query_params.get('hours')
        include_archived = request.query_params.get('include_archived', 'false').lower() == 'true'

        notifications = notification_service.get_recent_notifications(
            limit=limit,
            hours=safe_int(hours) if hours else None,
            include_archived=include_archived
        )
        return Response({
            'success': True,
            'message': f'Retrieved {len(notifications)} recent notifications',
            'count': len(notifications),
            'data': notifications
        })
    except Exception as e:
        logger.exception("Error getting recent notifications")
        return Response({'success': False, 'message': f'Error retrieving recent notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def all_notifications(request):
    """
    Get all notifications with DynamoDB‑style pagination.
    Query parameters:
        - limit: number of items per page (default 50)
        - last_key: JSON string of the last evaluated key from previous response
        - include_archived: boolean
    """
    try:
        limit = safe_int(request.query_params.get('limit', 50), 50)
        include_archived = request.query_params.get('include_archived', 'false').lower() == 'true'
        last_key = request.query_params.get('last_key')
        if last_key:
            last_key = json.loads(last_key)  # expects a dict like {'sk': 'NOTIF-00123'}

        notifications, last_evaluated_key = notification_service.get_all_notifications(
            limit=limit,
            include_archived=include_archived,
            start_key=last_key
        )

        return Response({
            'success': True,
            'message': f'Retrieved {len(notifications)} notifications',
            'count': len(notifications),
            'last_key': json.dumps(last_evaluated_key) if last_evaluated_key else None,
            'data': notifications
        })
    except Exception as e:
        logger.exception("Error getting all notifications")
        return Response({'success': False, 'message': f'Error retrieving all notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_archived_notifications(request):
    """
    Get archived notifications.
    Since the service doesn't have a dedicated archived index, we use
    get_notifications with include_archived=True and filter client‑side.
    """
    try:
        limit = safe_int(request.query_params.get('limit', 50), 50)
        recipient_id = request.query_params.get('recipient_id')
        # We ignore pagination for simplicity; can be added later.
        notifications = notification_service.get_notifications(
            recipient_id=recipient_id,
            limit=limit * 2,  # fetch extra to account for filtering
            include_archived=True
        )
        archived = [n for n in notifications if n.get('archived')]
        paginated = archived[:limit]

        return Response({
            'success': True,
            'message': f'Retrieved {len(paginated)} archived notifications',
            'count': len(paginated),
            'data': paginated
        })
    except Exception as e:
        logger.exception("Error getting archived notifications")
        return Response({'success': False, 'message': f'Error retrieving archived notifications: {str(e)}'},
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
            return Response({'success': False, 'message': 'Notification not found or already read'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'message': 'Notification marked as read'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error marking notification as read")
        return Response({'success': False, 'message': f'Error marking notification as read: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def mark_notification_unread(request, notification_id):
    """Mark a notification as unread"""
    try:
        validate_notification_id(notification_id)
        success = notification_service.mark_as_unread(notification_id)
        if not success:
            return Response({'success': False, 'message': 'Notification not found or already unread'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'message': 'Notification marked as unread'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error marking notification as unread")
        return Response({'success': False, 'message': f'Error marking notification as unread: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def mark_all_notifications_read(request):
    """Mark all notifications as read for a recipient (or all if no recipient)"""
    try:
        data = request.data if request.data else {}
        recipient_id = data.get('recipient_id')
        modified_count = notification_service.mark_all_as_read(recipient_id=recipient_id)
        msg = f'Successfully marked {modified_count} notifications as read'
        if recipient_id:
            msg += f' for user {recipient_id}'
        return Response({'success': True, 'message': msg, 'modified_count': modified_count})
    except Exception as e:
        logger.exception("Error marking all notifications as read")
        return Response({'success': False, 'message': f'Error marking notifications as read: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def mark_all_notifications_unread(request):
    """
    Mark all notifications as unread.
    This is implemented by fetching all notifications and marking each unread one as read.
    Inefficient; consider adding a batch method to the service if needed.
    """
    try:
        data = request.data if request.data else {}
        recipient_id = data.get('recipient_id')

        # Fetch all notifications (or use a more efficient approach)
        if recipient_id:
            all_user_notif = notification_service.get_notifications(recipient_id=recipient_id, limit=10000)
        else:
            all_user_notif, _ = notification_service.get_all_notifications(limit=10000)

        modified = 0
        for n in all_user_notif:
            if n.get('is_read'):  # only toggle those that are read
                if notification_service.mark_as_unread(n['notification_id']):
                    modified += 1

        msg = f'Successfully marked {modified} notifications as unread'
        if recipient_id:
            msg += f' for user {recipient_id}'
        return Response({'success': True, 'message': msg, 'modified_count': modified})
    except Exception as e:
        logger.exception("Error marking all notifications as unread")
        return Response({'success': False, 'message': f'Error marking notifications as unread: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# ARCHIVE OPERATIONS
# ================================================================

@api_view(['PATCH'])
def archive_notification(request, notification_id):
    """Archive a specific notification"""
    try:
        validate_notification_id(notification_id)
        success = notification_service.archive_notification(notification_id)
        if not success:
            return Response({'success': False, 'message': 'Notification not found'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'message': 'Notification archived successfully'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error archiving notification")
        return Response({'success': False, 'message': f'Error archiving notification: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def unarchive_notification(request, notification_id):
    """Unarchive a specific notification."""
    try:
        validate_notification_id(notification_id)
        # Use include_archived=True to find archived notifications
        notification = notification_service.get_notification_by_id(notification_id, include_archived=True)
        if not notification:
            return Response({'success': False, 'message': 'Notification not found'},
                            status=status.HTTP_404_NOT_FOUND)

        # Call the unarchive method
        success = notification_service.unarchive_notification(notification_id)
        if not success:
            return Response({'success': False, 'message': 'Failed to unarchive notification'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'success': True, 'message': 'Notification unarchived successfully'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error unarchiving notification")
        return Response({'success': False, 'message': f'Error unarchiving notification: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def archive_all_read_notifications(request):
    """Archive all read notifications (client‑side implementation)"""
    try:
        data = request.data if request.data else {}
        recipient_id = data.get('recipient_id')

        # Fetch all read notifications
        read_notif = notification_service.get_notifications(
            recipient_id=recipient_id,
            is_read=True,
            limit=10000
        )
        archived = 0
        for n in read_notif:
            if notification_service.archive_notification(n['notification_id']):
                archived += 1

        msg = f'Successfully archived {archived} read notifications'
        if recipient_id:
            msg += f' for user {recipient_id}'
        return Response({'success': True, 'message': msg, 'archived_count': archived})
    except Exception as e:
        logger.exception("Error archiving read notifications")
        return Response({'success': False, 'message': f'Error archiving read notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# DELETION OPERATIONS
# ================================================================

@api_view(['DELETE'])
def delete_notification(request, notification_id):
    """Delete a notification"""
    try:
        validate_notification_id(notification_id)
        success = notification_service.delete_notification(notification_id)
        if not success:
            return Response({'success': False, 'message': 'Notification not found'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'message': 'Notification deleted successfully'})
    except ValueError as e:
        return Response({'success': False, 'message': str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error deleting notification")
        return Response({'success': False, 'message': f'Error deleting notification: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_all_read_notifications(request):
    """Delete all read notifications (client‑side implementation)"""
    try:
        data = request.data if request.data else {}
        recipient_id = data.get('recipient_id')

        read_notif = notification_service.get_notifications(
            recipient_id=recipient_id,
            is_read=True,
            limit=10000
        )
        deleted = 0
        for n in read_notif:
            if notification_service.delete_notification(n['notification_id']):
                deleted += 1

        msg = f'Successfully deleted {deleted} read notifications'
        if recipient_id:
            msg += f' for user {recipient_id}'
        return Response({'success': True, 'message': msg, 'deleted_count': deleted})
    except Exception as e:
        logger.exception("Error deleting read notifications")
        return Response({'success': False, 'message': f'Error deleting read notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_archived_notifications(request):
    """Delete all archived notifications permanently"""
    try:
        data = request.data if request.data else {}
        recipient_id = data.get('recipient_id')

        # Get archived notifications
        all_notif = notification_service.get_notifications(
            recipient_id=recipient_id,
            include_archived=True,
            limit=10000
        )
        archived = [n for n in all_notif if n.get('archived')]
        deleted = 0
        for n in archived:
            if notification_service.delete_notification(n['notification_id']):
                deleted += 1

        msg = f'Successfully deleted {deleted} archived notifications'
        if recipient_id:
            msg += f' for user {recipient_id}'
        return Response({'success': True, 'message': msg, 'deleted_count': deleted})
    except Exception as e:
        logger.exception("Error deleting archived notifications")
        return Response({'success': False, 'message': f'Error deleting archived notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_all_notifications(request):
    """Delete all notifications with optional filters"""
    try:
        data = request.data if request.data else {}
        recipient_id = data.get('recipient_id')
        notification_type = data.get('notification_type')

        # Fetch matching notifications
        filters = {}
        if recipient_id:
            filters['recipient_id'] = recipient_id
        if notification_type:
            filters['notification_type'] = notification_type

        all_matching = notification_service.get_notifications(**filters, limit=10000)

        deleted = 0
        for n in all_matching:
            if notification_service.delete_notification(n['notification_id']):
                deleted += 1

        msg = f'Successfully deleted {deleted} notifications'
        if recipient_id:
            msg += f' for user {recipient_id}'
        if notification_type:
            msg += f' of type {notification_type}'
        return Response({'success': True, 'message': msg, 'deleted_count': deleted})
    except Exception as e:
        logger.exception("Error deleting all notifications")
        return Response({'success': False, 'message': f'Error deleting notifications: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# STATISTICS AND ANALYTICS
# ================================================================

@api_view(['GET'])
def notification_stats(request):
    """
    Get notification statistics.
    Computes counts on the fly; may be inefficient for large datasets.
    """
    try:
        recipient_id = request.query_params.get('recipient_id')
        include_archived = request.query_params.get('include_archived', 'false').lower() in ['true', '1', 'yes']

        if recipient_id:
            unread = notification_service.get_unread_count(recipient_id)
            all_user = notification_service.get_notifications(
                recipient_id=recipient_id,
                include_archived=include_archived,
                limit=10000
            )
            total = len(all_user)
            stats = {
                'total': total,
                'unread': unread,
                'read': total - unread
            }
        else:
            all_notif, _ = notification_service.get_all_notifications(limit=10000, include_archived=include_archived)
            total = len(all_notif)
            unread = sum(1 for n in all_notif if not n.get('is_read'))
            stats = {
                'total': total,
                'unread': unread,
                'read': total - unread
            }

        return Response({
            'success': True,
            'message': 'Notification statistics retrieved',
            'data': stats
        })
    except Exception as e:
        logger.exception("Error retrieving notification statistics")
        return Response({'success': False, 'message': f'Error retrieving notification statistics: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================================================
# EMAIL VERIFICATION ENDPOINTS
# ================================================================
# These endpoints rely on email_verification_service which is assumed
# to be already refactored or independent of the notification model.
# They are kept unchanged.

@api_view(['GET'])
def verify_email(request):
    """Verify user email using JWT token"""
    try:
        token = request.query_params.get('token')
        if not token:
            return Response({
                'success': False,
                'message': 'Verification token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        result = email_verification_service.verify_email(token)

        if result.get('success'):
            return Response({
                'success': True,
                'message': result.get('message', 'Email verified successfully'),
                'data': {
                    'email': result.get('email'),
                    'user_id': result.get('user_id'),
                    'username': result.get('username')
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': result.get('error', 'Email verification failed')
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.exception("Error verifying email")
        return Response({
            'success': False,
            'message': f'Error verifying email: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def resend_verification_email(request):
    """Resend verification email to user (legacy - sends code now)"""
    try:
        email = request.data.get('email')
        if not email:
            return Response({
                'success': False,
                'message': 'Email address is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        result = email_verification_service.resend_verification_code(email)

        if result.get('success'):
            return Response({
                'success': True,
                'message': 'Verification code sent successfully',
                'token': result.get('token')
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': result.get('error', 'Failed to send verification code')
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.exception("Error resending verification email")
        return Response({
            'success': False,
            'message': f'Error resending verification code: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def send_verification_code(request):
    """Send verification code to user's email"""
    try:
        email = request.data.get('email')
        if not email:
            return Response({
                'success': False,
                'message': 'Email address is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get current user from JWT token if available
        user_id = None
        user_name = None
        current_user = get_authenticated_user_from_jwt(request)
        if current_user:
            user_id = current_user.get('user_id') or current_user.get('_id')
            if user_id:
                user_id = str(user_id)
            user_name = current_user.get('full_name') or current_user.get('username', '')

        result = email_verification_service.send_verification_code(email, user_id=user_id, user_name=user_name)

        if result.get('success'):
            return Response({
                'success': True,
                'message': 'Verification code sent successfully',
                'token': result.get('token')
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': result.get('error', 'Failed to send verification code')
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.exception("Error sending verification code")
        return Response({
            'success': False,
            'message': f'Error sending verification code: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def verify_code(request):
    """Verify email using verification code"""
    try:
        token = request.data.get('token')
        code = request.data.get('code')

        if not token:
            return Response({
                'success': False,
                'message': 'Verification token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not code:
            return Response({
                'success': False,
                'message': 'Verification code is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        result = email_verification_service.verify_code(token, code)

        if result.get('success'):
            return Response({
                'success': True,
                'message': result.get('message', 'Email verified successfully'),
                'data': {
                    'email': result.get('email'),
                    'user_id': result.get('user_id'),
                    'username': result.get('username')
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': result.get('error', 'Email verification failed')
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.exception("Error verifying code")
        return Response({
            'success': False,
            'message': f'Error verifying code: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
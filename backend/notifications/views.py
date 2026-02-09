# notifications/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from app.decorators.authenticationDecorator import get_authenticated_user_from_jwt
from .services import notification_service
from .email_verification_service import email_verification_service

# ================================================================
# UTILITY FUNCTIONS
# ================================================================

def validate_notification_id(notification_id):
    """Validate notification ID format (NOTIF-XXXXXX)"""
    if not notification_id or not notification_id.startswith('NOTIF-'):
        raise ValueError('Invalid notification ID format. Expected format: NOTIF-XXXXXX')
    return notification_id

# ================================================================
# NOTIFICATION CREATION
# ================================================================

@api_view(['POST'])
def create_notification(request):
    """Create a new notification"""
    try:
        data = request.data
        
        # Required fields
        title = data.get('title')
        message = data.get('message')
        
        if not title or not message:
            return Response({
                'success': False,
                'message': 'title and message are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Optional fields
        recipient_id = data.get('recipient_id')
        recipient_username = data.get('recipient_username')
        priority = data.get('priority', 'medium')
        notification_type = data.get('notification_type', 'system')
        metadata = data.get('metadata', {})
        
        notification = notification_service.create_notification(
            title=title,
            message=message,
            recipient_id=recipient_id,
            recipient_username=recipient_username,
            priority=priority,
            notification_type=notification_type,
            metadata=metadata
        )
        
        return Response({
            'success': True,
            'message': 'Notification created successfully',
            'data': notification
        }, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error creating notification: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        return Response({
            'success': False,
            'message': f'Error creating inventory alert: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        limit = int(request.query_params.get('limit', 50))
        
        # Convert is_read string to boolean
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
        return Response({
            'success': False,
            'message': f'Error retrieving notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_notification(request, notification_id):
    """Get a specific notification"""
    try:
        # Validate ID format
        validate_notification_id(notification_id)
        
        notification = notification_service.get_notification_by_id(notification_id)
        
        if not notification:
            return Response({
                'success': False,
                'message': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'data': notification
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving notification: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def user_notifications(request, user_id):
    """Get all notifications for a specific user"""
    try:
        # Verify user exists
        user = get_object_or_404(User, id=user_id)
        
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            is_read = is_read.lower() in ['true', '1', 'yes']
        
        notifications = notification_service.get_notifications(
            recipient_id=user_id,
            is_read=is_read
        )
        
        unread_count = notification_service.get_unread_count(user_id)
        
        return Response({
            'success': True,
            'user': user.username,
            'total_count': len(notifications),
            'unread_count': unread_count,
            'data': notifications
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving user notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def recent_notifications(request):
    """Get recent notifications with archive support"""
    try:
        limit = int(request.query_params.get('limit', 10))
        hours = request.query_params.get('hours')
        include_archived = request.query_params.get('include_archived', 'false').lower() == 'true'
        
        notifications = notification_service.get_recent_notifications(
            limit=limit,
            hours=int(hours) if hours else None,
            include_archived=include_archived
        )
        
        return Response({
            'success': True,
            'message': f'Retrieved {len(notifications)} recent notifications',
            'count': len(notifications),
            'data': notifications
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving recent notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def all_notifications(request):
    """Get all notifications (paginated) with archive support"""
    try:
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 50))
        include_archived = request.query_params.get('include_archived', 'false').lower() == 'true'
        
        # Calculate skip for pagination
        skip = (page - 1) * limit
        
        notifications, total_count = notification_service.get_all_notifications(
            skip=skip,
            limit=limit,
            include_archived=include_archived
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return Response({
            'success': True,
            'message': f'Retrieved {len(notifications)} notifications (page {page} of {total_pages})',
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_count': total_count,
                'per_page': limit,
                'has_next': has_next,
                'has_previous': has_prev
            },
            'data': notifications
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving all notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_archived_notifications(request):
    """Get archived notifications with pagination"""
    try:
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 50))
        recipient_id = request.query_params.get('recipient_id')
        
        # Calculate skip for pagination
        skip = (page - 1) * limit
        
        notifications, total_count = notification_service.get_archived_notifications(
            recipient_id=recipient_id,
            skip=skip,
            limit=limit
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return Response({
            'success': True,
            'message': f'Retrieved {len(notifications)} archived notifications (page {page} of {total_pages})',
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_count': total_count,
                'per_page': limit,
                'has_next': has_next,
                'has_previous': has_prev
            },
            'data': notifications
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving archived notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================================================
# NOTIFICATION STATUS UPDATES
# ================================================================

@api_view(['PATCH'])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        # Validate ID format
        validate_notification_id(notification_id)
        
        success = notification_service.mark_as_read(notification_id)
        
        if not success:
            return Response({
                'success': False,
                'message': 'Notification not found or already read'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'message': 'Notification marked as read'
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error marking notification as read: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
def mark_notification_unread(request, notification_id):
    """Mark a notification as unread"""
    try:
        # Validate ID format
        validate_notification_id(notification_id)
        
        success = notification_service.mark_as_unread(notification_id)
        
        if not success:
            return Response({
                'success': False,
                'message': 'Notification not found or already unread'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'message': 'Notification marked as unread'
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error marking notification as unread: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    try:
        data = request.data if hasattr(request, 'data') and request.data else {}
        recipient_id = data.get('recipient_id', None)
        
        modified_count = notification_service.mark_all_as_read(recipient_id=recipient_id)
        
        response_message = f'Successfully marked {modified_count} notifications as read'
        if recipient_id:
            response_message += f' for user {recipient_id}'
        
        return Response({
            'success': True,
            'message': response_message,
            'modified_count': modified_count
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error marking notifications as read: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
def mark_all_notifications_unread(request):
    """Mark all notifications as unread"""
    try:
        data = request.data if hasattr(request, 'data') and request.data else {}
        recipient_id = data.get('recipient_id', None)
        
        modified_count = notification_service.mark_all_as_unread(recipient_id=recipient_id)
        
        response_message = f'Successfully marked {modified_count} notifications as unread'
        if recipient_id:
            response_message += f' for user {recipient_id}'
        
        return Response({
            'success': True,
            'message': response_message,
            'modified_count': modified_count
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error marking notifications as unread: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================================================
# ARCHIVE OPERATIONS
# ================================================================

@api_view(['PATCH'])
def archive_notification(request, notification_id):
    """Archive a specific notification"""
    try:
        # Validate ID format
        validate_notification_id(notification_id)
        
        success = notification_service.archive_notification(notification_id)
        
        if not success:
            return Response({
                'success': False,
                'message': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'message': 'Notification archived successfully'
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error archiving notification: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
def unarchive_notification(request, notification_id):
    """Unarchive a specific notification"""
    try:
        # Validate ID format
        validate_notification_id(notification_id)
        
        success = notification_service.unarchive_notification(notification_id)
        
        if not success:
            return Response({
                'success': False,
                'message': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'message': 'Notification unarchived successfully'
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error unarchiving notification: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
def archive_all_read_notifications(request):
    """Archive all read notifications"""
    try:
        data = request.data if hasattr(request, 'data') and request.data else {}
        recipient_id = data.get('recipient_id', None)
        
        archived_count = notification_service.archive_all_read_notifications(recipient_id=recipient_id)
        
        response_message = f'Successfully archived {archived_count} read notifications'
        if recipient_id:
            response_message += f' for user {recipient_id}'
        
        return Response({
            'success': True,
            'message': response_message,
            'archived_count': archived_count
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error archiving read notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================================================
# DELETION OPERATIONS
# ================================================================

@api_view(['DELETE'])
def delete_notification(request, notification_id):
    """Delete a notification"""
    try:
        # Validate ID format
        validate_notification_id(notification_id)
        
        success = notification_service.delete_notification(notification_id)
        
        if not success:
            return Response({
                'success': False,
                'message': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'message': 'Notification deleted successfully'
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error deleting notification: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
def delete_all_read_notifications(request):
    """Delete all read notifications"""
    try:
        data = request.data if hasattr(request, 'data') and request.data else {}
        recipient_id = data.get('recipient_id', None)
        
        deleted_count = notification_service.delete_read_notifications(recipient_id=recipient_id)
        
        response_message = f'Successfully deleted {deleted_count} read notifications'
        if recipient_id:
            response_message += f' for user {recipient_id}'
        
        return Response({
            'success': True,
            'message': response_message,
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error deleting read notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
def delete_archived_notifications(request):
    """Delete all archived notifications permanently"""
    try:
        data = request.data if hasattr(request, 'data') and request.data else {}
        recipient_id = data.get('recipient_id', None)
        
        deleted_count = notification_service.delete_archived_notifications(recipient_id=recipient_id)
        
        response_message = f'Successfully deleted {deleted_count} archived notifications'
        if recipient_id:
            response_message += f' for user {recipient_id}'
        
        return Response({
            'success': True,
            'message': response_message,
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error deleting archived notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
def delete_all_notifications(request):
    """Delete all notifications with optional filters"""
    try:
        data = request.data if hasattr(request, 'data') and request.data else {}
        recipient_id = data.get('recipient_id', None)
        notification_type = data.get('notification_type', None)
        
        deleted_count = notification_service.delete_all_notifications(
            recipient_id=recipient_id,
            notification_type=notification_type
        )
        
        response_message = f'Successfully deleted {deleted_count} notifications'
        if recipient_id:
            response_message += f' for user {recipient_id}'
        if notification_type:
            response_message += f' of type {notification_type}'
        
        return Response({
            'success': True,
            'message': response_message,
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error deleting notifications: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================================================
# STATISTICS AND ANALYTICS
# ================================================================

@api_view(['GET'])
def notification_stats(request):
    """Get notification statistics"""
    try:
        recipient_id = request.query_params.get('recipient_id')
        include_archived = request.query_params.get('include_archived', 'false').lower() in ['true', '1', 'yes']
        
        stats = notification_service.get_notification_stats(
            recipient_id=recipient_id,
            include_archived=include_archived
        )
        
        return Response({
            'success': True,
            'message': 'Notification statistics retrieved successfully',
            'data': stats
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error retrieving notification statistics: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================================================
# EMAIL VERIFICATION ENDPOINTS
# ================================================================

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
                'token': result.get('token')  # Return token for frontend
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': result.get('error', 'Failed to send verification code')
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
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
            # Get user_id - it might be in different formats
            user_id = current_user.get('user_id') or current_user.get('_id')
            if user_id:
                user_id = str(user_id)
            user_name = current_user.get('full_name') or current_user.get('username', '')
        
        result = email_verification_service.send_verification_code(email, user_id=user_id, user_name=user_name)
        
        if result.get('success'):
            return Response({
                'success': True,
                'message': 'Verification code sent successfully',
                'token': result.get('token')  # Return token for frontend to use when verifying
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': result.get('error', 'Failed to send verification code')
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
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
        return Response({
            'success': False,
            'message': f'Error verifying code: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
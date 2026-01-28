# notifications/services.py
from datetime import datetime, timedelta
import uuid
from decimal import Decimal
from django.contrib.auth.models import User
from django.http import JsonResponse
from app.services.database_service import DatabaseService
from boto3.dynamodb.conditions import Key, Attr

# Helper to convert floats to Decimals for DynamoDB
def floats_to_decimals(obj):
    if isinstance(obj, list):
        return [floats_to_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

class NotificationService:
    def __init__(self):
        db_service = DatabaseService()
        self.table = db_service.get_table('notifications')

    def _build_filter_expression(self, filters):
        expression = None
        for f in filters:
            if expression is None:
                expression = f
            else:
                expression &= f
        return expression

    # ================================================================
    # ID GENERATION METHOD
    # ================================================================
    
    def generate_notification_id(self):
        """
        Generate a unique notification ID using UUID.
        """
        return f"NOTIF-{uuid.uuid4()}"

    # ================================================================
    # NOTIFICATION CREATION METHODS
    # ================================================================
    
    def create_notification(self, title, message, recipient_id=None, recipient_username=None, 
                          priority='medium', notification_type='system', metadata=None):
        """Create a new notification in DynamoDB"""
        try:
            notification_id = self.generate_notification_id()
            now_utc_iso = datetime.utcnow().isoformat() + "Z"
            
            notification_item = {
                "notification_id": notification_id,
                "title": title,
                "message": message,
                "priority": priority,
                "is_read": False,
                "archived": False,
                "created_at": now_utc_iso,
                "updated_at": now_utc_iso,
                "notification_type": notification_type,
                "metadata": metadata or {}
            }
            
            if recipient_id or recipient_username:
                recipient = self._get_recipient(recipient_id, recipient_username)
                if not recipient:
                    raise ValueError("Recipient not found")
                
                notification_item.update({
                    "recipient_id": str(recipient.id),
                    "recipient_username": recipient.username
                })
            
            notification_item = floats_to_decimals(notification_item)
            notification_item = {k: v for k, v in notification_item.items() if v not in [None, '']}

            self.table.put_item(Item=notification_item)
            
            return notification_item
            
        except Exception as e:
            raise Exception(f"Error creating notification: {str(e)}")

    def create_inventory_alert(self, recipient_id, product_id, current_stock, product_name=None):
        """Create an inventory alert notification"""
        title = "Low Stock Alert"
        message = f"{product_name or 'Product'} is running low"
        metadata = {"product_id": product_id, "current_stock": current_stock}
        return self.create_notification(title=title, message=message, recipient_id=recipient_id,
                                      priority='high', notification_type='inventory', metadata=metadata)

    # ================================================================
    # NOTIFICATION RETRIEVAL METHODS
    # ================================================================
    
    def get_notifications(self, recipient_id=None, notification_type=None, is_read=None, limit=50, include_archived=False):
        """Get notifications with filters from DynamoDB."""
        filters = []
        if not include_archived:
            filters.append(Attr('archived').ne(True))
        if recipient_id:
            filters.append(Attr('recipient_id').eq(str(recipient_id)))
        if notification_type:
            filters.append(Attr('notification_type').eq(notification_type))
        if is_read is not None:
            filters.append(Attr('is_read').eq(is_read))

        scan_kwargs = {'Limit': limit}
        if filters:
            scan_kwargs['FilterExpression'] = self._build_filter_expression(filters)

        try:
            response = self.table.scan(**scan_kwargs)
            items = response.get('Items', [])
            items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return items
        except Exception as e:
            print(f"Error getting notifications: {e}")
            return []

    def get_notification_by_id(self, notification_id):
        """Get a specific notification by ID from DynamoDB"""
        try:
            response = self.table.get_item(Key={'notification_id': notification_id})
            return response.get('Item')
        except Exception as e:
            print(f"Error getting notification {notification_id}: {e}")
            return None

    def get_recent_notifications(self, limit=10, hours=None, include_archived=False):
        """Get recent notifications from DynamoDB"""
        filters = []
        if not include_archived:
            filters.append(Attr('archived').ne(True))
        if hours:
            time_threshold = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
            filters.append(Attr('created_at').gte(time_threshold))
        
        scan_kwargs = {'Limit': limit}
        if filters:
            scan_kwargs['FilterExpression'] = self._build_filter_expression(filters)

        try:
            response = self.table.scan(**scan_kwargs)
            items = response.get('Items', [])
            items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return items
        except Exception as e:
            raise Exception(f"Error getting recent notifications: {str(e)}")

    def get_all_notifications(self, limit=50, include_archived=False, start_key=None):
        """Get all notifications with pagination from DynamoDB."""
        filters = []
        if not include_archived:
            filters.append(Attr('archived').ne(True))

        scan_kwargs = {'Limit': limit}
        if filters:
            scan_kwargs['FilterExpression'] = self._build_filter_expression(filters)
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        
        try:
            response = self.table.scan(**scan_kwargs)
            return response.get('Items', []), response.get('LastEvaluatedKey')
        except Exception as e:
            raise Exception(f"Error getting all notifications: {str(e)}")

    def get_unread_count(self, recipient_id=None, include_archived=False):
        """Get count of unread notifications from DynamoDB"""
        filters = [Attr('is_read').eq(False)]
        if not include_archived:
            filters.append(Attr('archived').ne(True))
        if recipient_id:
            filters.append(Attr('recipient_id').eq(str(recipient_id)))
        
        scan_kwargs = {'Select': 'COUNT'}
        if filters:
            scan_kwargs['FilterExpression'] = self._build_filter_expression(filters)

        try:
            response = self.table.scan(**scan_kwargs)
            return response.get('Count', 0)
        except Exception as e:
            raise Exception(f"Error getting unread count: {str(e)}")

    # ================================================================
    # NOTIFICATION STATUS UPDATE METHODS
    # ================================================================
    
    def mark_as_read(self, notification_id):
        """Mark notification as read in DynamoDB"""
        try:
            self.table.update_item(
                Key={'notification_id': notification_id},
                UpdateExpression="SET is_read = :r, updated_at = :u",
                ExpressionAttributeValues={':r': True, ':u': datetime.utcnow().isoformat() + "Z"}
            )
            return True
        except Exception:
            return False

    def mark_as_unread(self, notification_id):
        """Mark notification as unread in DynamoDB"""
        try:
            self.table.update_item(
                Key={'notification_id': notification_id},
                UpdateExpression="SET is_read = :r, updated_at = :u",
                ExpressionAttributeValues={':r': False, ':u': datetime.utcnow().isoformat() + "Z"}
            )
            return True
        except Exception:
            return False

    def mark_all_as_read(self, recipient_id=None):
        """Mark all notifications as read in DynamoDB. Inefficient for large tables."""
        items, _ = self.get_all_notifications(limit=1000, include_archived=False) # Add pagination for more than 1000
        count = 0
        for item in items:
            if not item.get('is_read'):
                if recipient_id and item.get('recipient_id') != str(recipient_id):
                    continue
                self.mark_as_read(item['notification_id'])
                count += 1
        return count

    # ================================================================
    # NOTIFICATION DELETION & ARCHIVING
    # ================================================================
    
    def archive_notification(self, notification_id):
        """Archive a notification in DynamoDB"""
        try:
            self.table.update_item(
                Key={'notification_id': notification_id},
                UpdateExpression="SET archived = :a, archived_at = :t, updated_at = :u",
                ExpressionAttributeValues={
                    ':a': True,
                    ':t': datetime.utcnow().isoformat() + "Z",
                    ':u': datetime.utcnow().isoformat() + "Z"
                }
            )
            return True
        except Exception as e:
            raise Exception(f"Error archiving notification: {str(e)}")
            
    def delete_notification(self, notification_id):
        """Delete a notification from DynamoDB"""
        try:
            self.table.delete_item(Key={'notification_id': notification_id})
            return True
        except Exception:
            return False

    # ================================================================
    # UTILITY & API METHODS (API methods need refactoring)
    # ================================================================
    
    def get_all_notifications_api(self, request):
        raise NotImplementedError("API method not yet refactored for DynamoDB")

    def get_recent_notifications_api(self, request):
        raise NotImplementedError("API method not yet refactored for DynamoDB")

    def mark_as_read_api(self, notification_id):
        raise NotImplementedError("API method not yet refactored for DynamoDB")

    def mark_all_as_read_api(self, request):
        raise NotImplementedError("API method not yet refactored for DynamoDB")

    def archive_notification_api(self, notification_id):
        raise NotImplementedError("API method not yet refactored for DynamoDB")

    def unarchive_notification_api(self, notification_id):
        raise NotImplementedError("API method not yet refactored for DynamoDB")

    def delete_notification_api(self, notification_id):
        raise NotImplementedError("API method not yet refactored for DynamoDB")

    def _get_recipient(self, recipient_id=None, recipient_username=None):
        """Helper method to get recipient User object"""
        if recipient_id:
            try:
                return User.objects.get(id=recipient_id)
            except User.DoesNotExist:
                return None
        elif recipient_username:
            try:
                return User.objects.get(username=recipient_username)
            except User.DoesNotExist:
                return None
        return None

# Singleton instance
notification_service = NotificationService()
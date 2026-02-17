# app/services/audit_service.py
from datetime import datetime
import json
from decimal import Decimal
from ..models.Audit import AuditLog, log_audit_event, AuditEvents
import logging

logger = logging.getLogger(__name__)

class AuditLogService:
    def __init__(self):
        # No need for DatabaseService anymore
        pass

    def _convert_to_serializable(self, obj):
        """Convert object to JSON serializable format."""
        if isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(i) for i in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    def _create_audit_log(self, event_type, user_data, target_data=None, old_values=None, new_values=None, metadata=None):
        """Create a standardized audit log entry using PynamoDB model."""
        try:
            # Convert changes to JSON string if they exist
            changes = None
            if old_values or new_values:
                changes_data = {
                    "old_values": self._convert_to_serializable(old_values) or {},
                    "new_values": self._convert_to_serializable(new_values) or {},
                    "changed_fields": list(new_values.keys()) if new_values else []
                }
                changes = json.dumps(changes_data)
            
            # Convert metadata to JSON string
            metadata_str = json.dumps(self._convert_to_serializable(metadata)) if metadata else None
            
            # Build description from action and target
            description = f"{event_type.replace('_', ' ').title()}: {target_data.get('name') if target_data else 'Unknown'}"
            
            # Create audit log using the model
            audit_log = AuditLog.create_audit_log(
                action=event_type,
                user_id=user_data.get("user_id", "system"),
                username=user_data.get("username", "system"),
                branch_id=str(user_data.get("branch_id", 1)),
                status="success",
                source="audit_service",
                target_type=target_data.get("type") if target_data else None,
                target_id=target_data.get("id") if target_data else None,
                target_name=target_data.get("name") if target_data else None,
                changes=changes,
                metadata=metadata_str,
                description=description
            )
            
            if audit_log:
                return {"audit_id": audit_log.sk}
            else:
                raise Exception("Failed to create audit log")
                
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            raise Exception(f"Error creating audit log: {str(e)}")

    # Simplified method using the helper functions from the model
    def log_sale_create(self, user_data, sale_data):
        """Log sale creation using simplified audit event."""
        return AuditEvents.create_entity(
            target_type="sale",
            target_id=sale_data.get("sale_id"),
            target_name=f"Sale #{sale_data.get('sale_id')}",
            user_id=user_data.get("user_id"),
            username=user_data.get("username")
        )

    def log_customer_update(self, user_data, customer_id, old_customer_data, new_customer_data):
        """Log customer update with detailed changes."""
        changed_fields = {k: {"old": old_customer_data.get(k), "new": v} 
                         for k, v in new_customer_data.items() 
                         if old_customer_data.get(k) != v}
        
        # Use the detailed logging method for complex changes
        return self._create_audit_log(
            event_type="customer_update",
            user_data=user_data,
            target_data={
                "type": "customer", 
                "id": customer_id, 
                "name": old_customer_data.get("full_name")
            },
            old_values={k: v['old'] for k, v in changed_fields.items()},
            new_values={k: v['new'] for k, v in changed_fields.items()},
            metadata={
                "action": "update", 
                "module": "customers", 
                "fields_changed": list(changed_fields.keys())
            }
        )

    def log_action(self, action, resource_type, resource_id, user_id=None, changes=None, metadata=None):
        """Generic action logging method."""
        user_data = {'user_id': user_id or 'system', 'username': user_id or 'system'}
        
        return self._create_audit_log(
            event_type=action,
            user_data=user_data,
            target_data={
                'type': resource_type, 
                'id': resource_id, 
                'name': f"{resource_type.title()} {resource_id}"
            },
            new_values=changes or {},
            metadata=metadata or {}
        )

    # Query methods using PynamoDB
    def get_audit_logs_by_target(self, target_type, target_id, limit=50):
        """Get audit logs for a specific entity using GSI."""
        try:
            # Use GSI for efficient querying
            logs = AuditLog.get_by_target(
                target_type=target_type,
                target_id=target_id,
                limit=limit,
                reverse=True  # Latest first
            )
            
            data = []
            for log in logs:
                log_data = log.to_dict()
                # Parse JSON strings for changes and metadata
                if log.changes:
                    try:
                        log_data['changes'] = json.loads(log.changes)
                    except:
                        log_data['changes'] = log.changes
                if log.metadata:
                    try:
                        log_data['metadata'] = json.loads(log.metadata)
                    except:
                        log_data['metadata'] = log.metadata
                data.append(log_data)
            
            return {'success': True, 'data': data, 'count': len(data)}
            
        except Exception as e:
            logger.error(f"Error getting audit logs by target: {str(e)}")
            return {'success': False, 'error': str(e), 'data': []}

    def get_audit_logs_by_user(self, user_id, limit=100):
        """Get audit logs for a specific user using GSI."""
        try:
            logs = AuditLog.get_by_user_id(
                user_id=user_id,
                limit=limit,
                reverse=True
            )
            
            data = []
            for log in logs:
                log_data = log.to_dict()
                # Parse JSON strings for changes and metadata
                if log.changes:
                    try:
                        log_data['changes'] = json.loads(log.changes)
                    except:
                        log_data['changes'] = log.changes
                if log.metadata:
                    try:
                        log_data['metadata'] = json.loads(log.metadata)
                    except:
                        log_data['metadata'] = log.metadata
                data.append(log_data)
            
            return {'success': True, 'data': data, 'count': len(data)}
            
        except Exception as e:
            logger.error(f"Error getting audit logs by user: {str(e)}")
            return {'success': False, 'error': str(e), 'data': []}

    def get_audit_statistics(self, limit=1000):
        """Get audit log statistics."""
        try:
            logs = AuditLog.get_all_logs(limit=limit)
            
            stats = {}
            for log in logs:
                action = log.action
                if action not in stats:
                    stats[action] = {'count': 0, 'latest': '', 'last_user': ''}
                stats[action]['count'] += 1
                
                log_timestamp = log.timestamp.isoformat() if log.timestamp else ''
                if log_timestamp > stats[action]['latest']:
                    stats[action]['latest'] = log_timestamp
                    stats[action]['last_user'] = log.username or log.user_id or 'Unknown'
            
            total_logs = len(logs)
            by_event_type = [{'action': k, **v} for k, v in stats.items()]
            by_event_type.sort(key=lambda x: x['count'], reverse=True)

            return {
                'success': True,
                'total_logs': total_logs,
                'by_action': by_event_type,
                'sample_size': limit
            }
            
        except Exception as e:
            logger.error(f"Error getting audit statistics: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_audit_log_by_id(self, audit_id):
        """Get specific audit log by ID."""
        try:
            log = AuditLog.get_by_id(audit_id)
            if log:
                data = log.to_dict()
                # Parse changes and metadata from JSON strings
                if log.changes:
                    try:
                        data['changes'] = json.loads(log.changes)
                    except:
                        data['changes'] = log.changes
                if log.metadata:
                    try:
                        data['metadata'] = json.loads(log.metadata)
                    except:
                        data['metadata'] = log.metadata
                return {'success': True, 'data': data}
            else:
                return {'success': False, 'error': 'Audit log not found', 'data': None}
                
        except Exception as e:
            logger.error(f"Error getting audit log by ID: {str(e)}")
            return {'success': False, 'error': str(e), 'data': None}

    def get_recent_activity(self, limit=50):
        """Get recent audit activity across all entities."""
        try:
            logs = AuditLog.get_all_logs(limit=limit)
            
            data = []
            for log in logs:
                log_data = log.to_dict()
                # Add a human-readable description
                if not log_data.get('description'):
                    log_data['description'] = f"{log.action.replace('_', ' ').title()}: {log.target_name or log.target_type}"
                data.append(log_data)
            
            return {'success': True, 'data': data, 'count': len(data)}
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {str(e)}")
            return {'success': False, 'error': str(e), 'data': []}

    # Pre-defined audit events using the model's AuditEvents class
    def log_user_login(self, user_id, username, status="success", ip_address=None):
        """Log user login attempt."""
        return AuditEvents.user_login(
            user_id=user_id,
            username=username,
            status=status,
            ip_address=ip_address
        )

    def log_create_entity(self, target_type, target_id, target_name, user_id=None, username=None):
        """Log creation of an entity."""
        return AuditEvents.create_entity(
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            user_id=user_id,
            username=username
        )

    def log_update_entity(self, target_type, target_id, target_name, user_id=None, username=None):
        """Log update of an entity."""
        return AuditEvents.update_entity(
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            user_id=user_id,
            username=username
        )

    def log_delete_entity(self, target_type, target_id, target_name, user_id=None, username=None):
        """Log deletion of an entity."""
        return AuditEvents.delete_entity(
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            user_id=user_id,
            username=username
        )

    def log_error_event(self, error_type, error_message, user_id=None, username=None, metadata=None):
        """Log error events."""
        return self._create_audit_log(
            event_type=f"error_{error_type}",
            user_data={'user_id': user_id or 'system', 'username': username or 'system'},
            target_data={
                'type': 'system',
                'id': 'error',
                'name': f"System Error: {error_type}"
            },
            metadata={
                'error_message': error_message,
                'error_type': error_type,
                **(metadata or {})
            }
        )

    def search_audit_logs(self, filters=None, limit=100):
        """
        Search audit logs with multiple filters.
        Note: This uses scan operations and should be used sparingly.
        """
        try:
            if not filters:
                return self.get_recent_activity(limit=limit)
            
            scan_filter = None
            # Build filter conditions based on provided filters
            if 'action' in filters:
                scan_filter = AuditLog.action == filters['action']
            if 'user_id' in filters:
                user_condition = AuditLog.user_id == filters['user_id']
                scan_filter = user_condition if not scan_filter else (scan_filter & user_condition)
            if 'target_type' in filters:
                target_condition = AuditLog.target_type == filters['target_type']
                scan_filter = target_condition if not scan_filter else (scan_filter & target_condition)
            if 'status' in filters:
                status_condition = AuditLog.status == filters['status']
                scan_filter = status_condition if not scan_filter else (scan_filter & status_condition)
            
            logs = []
            for item in AuditLog.scan(filter_condition=scan_filter, limit=limit):
                logs.append(item.to_dict())
            
            # Sort by timestamp descending
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return {'success': True, 'data': logs, 'count': len(logs)}
            
        except Exception as e:
            logger.error(f"Error searching audit logs: {str(e)}")
            return {'success': False, 'error': str(e), 'data': []}
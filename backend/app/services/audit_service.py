# app/services/audit_service.py
from datetime import datetime
import uuid
from decimal import Decimal
from ..services.database_service import DatabaseService
from boto3.dynamodb.conditions import Key, Attr
import logging

# Helper to convert floats to Decimals for DynamoDB
def floats_to_decimals(obj):
    if isinstance(obj, list):
        return [floats_to_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

class AuditLogService:
    def __init__(self):
        db_service = DatabaseService()
        self.table = db_service.get_table('audit_logs')

    def generate_audit_id(self):
        """Generate a unique audit ID using UUID."""
        return f"AUD-{uuid.uuid4()}"

    def _create_audit_log(self, event_type, user_data, target_data=None, old_values=None, new_values=None, metadata=None):
        """Create a standardized audit log entry in DynamoDB."""
        try:
            audit_id = self.generate_audit_id()
            now_utc_iso = datetime.utcnow().isoformat() + "Z"
            
            audit_item = {
                "audit_id": audit_id,  # Partition Key
                "event_type": event_type,
                "user_id": user_data.get("user_id", "system"),
                "username": user_data.get("username", "system"),
                "branch_id": user_data.get("branch_id", 1),
                "timestamp": now_utc_iso,
                "status": "success",
                "source": "audit_service",
                "last_updated": now_utc_iso
            }
            
            if target_data:
                audit_item.update({
                    "target_type": target_data.get("type"),
                    "target_id": target_data.get("id"),
                    "target_name": target_data.get("name")
                })
            
            if old_values or new_values:
                audit_item["changes"] = {
                    "old_values": old_values or {},
                    "new_values": new_values or {},
                    "changed_fields": list(new_values.keys()) if new_values else []
                }
            
            if metadata:
                audit_item["metadata"] = metadata

            audit_item = floats_to_decimals(audit_item)
            audit_item = {k: v for k, v in audit_item.items() if v not in [None, '']}
            
            self.table.put_item(Item=audit_item)
            return {"audit_id": audit_id}
            
        except Exception as e:
            raise Exception(f"Error creating audit log: {str(e)}")

    # The logging methods below should now work with the new _create_audit_log method.
    # No changes are needed for them unless their data structures are incompatible with DynamoDB.
    
    def log_sale_create(self, user_data, sale_data):
        return self._create_audit_log(
            event_type="sale_create",
            user_data=user_data,
            target_data={"type": "sale", "id": sale_data.get("sale_id"), "name": f"Sale #{sale_data.get('sale_id')}"},
            new_values=sale_data,
            metadata={"action": "create", "module": "sales"}
        )

    # ... other log_* methods ...

    def get_audit_logs_by_target(self, target_type, target_id, limit=50):
        """Get audit logs for a specific entity from DynamoDB."""
        try:
            # This requires a GSI on target_type and target_id to be efficient.
            response = self.table.scan(
                FilterExpression=Attr('target_type').eq(target_type) & Attr('target_id').eq(target_id),
                Limit=limit
            )
            items = response.get('Items', [])
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return {'success': True, 'data': items, 'count': len(items)}
        except Exception as e:
            return {'success': False, 'error': str(e), 'data': []}

    def get_audit_logs_by_user(self, user_id, limit=100):
        """Get audit logs for a specific user from DynamoDB."""
        try:
            # This requires a GSI on user_id to be efficient.
            response = self.table.scan(
                FilterExpression=Attr('user_id').eq(user_id),
                Limit=limit
            )
            items = response.get('Items', [])
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return {'success': True, 'data': items, 'count': len(items)}
        except Exception as e:
            return {'success': False, 'error': str(e), 'data': []}

    def get_audit_statistics(self):
        """Get audit log statistics from DynamoDB. Inefficient for large tables."""
        try:
            response = self.table.scan(AttributesToGet=['event_type', 'timestamp'])
            items = response.get('Items', [])
            
            stats = {}
            for item in items:
                event_type = item['event_type']
                if event_type not in stats:
                    stats[event_type] = {'count': 0, 'latest': ''}
                stats[event_type]['count'] += 1
                if item['timestamp'] > stats[event_type]['latest']:
                    stats[event_type]['latest'] = item['timestamp']
            
            total_logs = len(items)
            by_event_type = [{'event_type': k, **v} for k, v in stats.items()]
            by_event_type.sort(key=lambda x: x['count'], reverse=True)

            return {
                'success': True,
                'total_logs': total_logs,
                'by_event_type': by_event_type,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ... other methods like log_customer_update, log_action can be kept if they call the new _create_audit_log ...
    def log_customer_update(self, user_data, customer_id, old_customer_data, new_customer_data):
        changed_fields = {k: {"old": old_customer_data.get(k), "new": v} for k, v in new_customer_data.items() if old_customer_data.get(k) != v}
        
        return self._create_audit_log(
            event_type="customer_update",
            user_data=user_data,
            target_data={"type": "customer", "id": customer_id, "name": old_customer_data.get("full_name")},
            old_values= {k: v['old'] for k,v in changed_fields.items()},
            new_values= {k: v['new'] for k,v in changed_fields.items()},
            metadata={"action": "update", "module": "customers", "fields_changed": list(changed_fields.keys())}
        )
    
    def log_action(self, action, resource_type, resource_id, user_id=None, changes=None, metadata=None):
        return self._create_audit_log(
            event_type=action,
            user_data={'user_id': user_id or 'system'},
            target_data={'type': resource_type, 'id': resource_id, 'name': f"{resource_type.title()} {resource_id}"},
            new_values=changes or {},
            metadata=metadata or {}
        )
    
# Keep other log_* methods as they are, assuming they correctly call the refactored _create_audit_log.
# Make sure to review each one to ensure data structures are compatible.
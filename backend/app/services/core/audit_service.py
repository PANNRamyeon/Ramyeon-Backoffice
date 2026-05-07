from datetime import datetime
from models.Audit import AuditLog
import logging

logger = logging.getLogger(__name__)

class AuditLogService:
    """
    Audit Log Service – template‑based design.
    All public methods delegate to a generic _log_event() which uses a registry of event templates.
    """

    def __init__(self):
        # Registry of event templates.
        # Each template is a function that receives the keyword arguments passed to _log_event
        # and returns a dict with keys: target_data, old_values, new_values, metadata.
        self._event_templates = {
            # ========== CUSTOMER ==========
            "customer_create": self._template_customer_create,
            "customer_update": self._template_customer_update,
            "customer_delete": self._template_customer_delete,
            "customer_bulk_delete": self._template_customer_bulk_delete,

            # ========== CATEGORY ==========
            "category_create": self._template_category_create,
            "category_update": self._template_category_update,
            "category_delete": self._template_category_delete,
            "category_restore": self._template_category_restore,

            # ========== PRODUCT ==========
            "product_create": self._template_product_create,
            "product_update": self._template_product_update,
            "product_delete": self._template_product_delete,
            "product_stock_update": self._template_product_stock_update,

            # ========== USER ==========
            "user_create": self._template_user_create,
            "user_update": self._template_user_update,
            "user_delete": self._template_user_delete,

            # ========== SYSTEM ==========
            "data_export": self._template_data_export,
            "data_import": self._template_data_import,
            "login_failed": self._template_login_failed,
        }

    # ------------------------------------------------------------------
    # Generic logging method – used by all public wrappers
    # ------------------------------------------------------------------
    def _log_event(self, event_type, user_data, **kwargs):
        """Look up the template and create the audit log."""
        template_func = self._event_templates.get(event_type)
        if not template_func:
            raise ValueError(f"No template registered for event type '{event_type}'")

        # Get the structured data from the template
        template_data = template_func(**kwargs)

        # Build the final audit arguments
        audit_kwargs = {
            'action': event_type,
            'user_id': user_data.get('user_id'),
            'username': user_data.get('username'),
            'branch_id': user_data.get('branch_id'),
            'source': user_data.get('source', 'audit_service'),
            'status': 'success',
        }

        # Add target data if provided
        if 'target_data' in template_data:
            audit_kwargs.update({
                'target_type': template_data['target_data'].get('type'),
                'target_id': str(template_data['target_data'].get('id', '')),
                'target_name': template_data['target_data'].get('name', ''),
            })

        # Build description from changes/metadata
        description_parts = []
        if 'old_values' in template_data or 'new_values' in template_data:
            old = template_data.get('old_values', {})
            new = template_data.get('new_values', {})
            changed = list(new.keys())
            if changed:
                description_parts.append(f"Changed fields: {', '.join(changed)}")
        if 'metadata' in template_data:
            meta_str = ', '.join(f"{k}={v}" for k, v in template_data['metadata'].items())
            description_parts.append(f"Metadata: {meta_str}")
        if description_parts:
            audit_kwargs['description'] = '; '.join(description_parts)

        # Optionally store old/new values in a JSON field if the model supports it.
        # For now, we rely on description and metadata. If detailed change tracking is needed,
        # you could add a 'changes' attribute to the AuditLog model and store JSON there.

        # Create the audit log
        audit_log = AuditLog.create_audit_log(**audit_kwargs)
        return {'audit_id': audit_log.sk} if audit_log else None

    # ------------------------------------------------------------------
    # Public methods – each is a one‑liner that calls _log_event
    # ------------------------------------------------------------------

    # ----- CUSTOMER -----
    def log_customer_create(self, user_data, customer_data):
        return self._log_event("customer_create", user_data, customer_data=customer_data)

    def log_customer_update(self, user_data, customer_id, old_values, new_values):
        return self._log_event("customer_update", user_data,
                               customer_id=customer_id, old_values=old_values, new_values=new_values)

    def log_customer_delete(self, user_data, customer_data):
        return self._log_event("customer_delete", user_data, customer_data=customer_data)

    def log_customer_bulk_delete(self, user_data, deleted_count, deleted_ids):
        return self._log_event("customer_bulk_delete", user_data,
                               deleted_count=deleted_count, deleted_ids=deleted_ids)

    # ----- CATEGORY -----
    def log_category_create(self, user_data, category_data):
        return self._log_event("category_create", user_data, category_data=category_data)

    def log_category_update(self, user_data, category_id, old_values, new_values):
        return self._log_event("category_update", user_data,
                               category_id=category_id, old_values=old_values, new_values=new_values)

    def log_category_delete(self, user_data, category_data):
        return self._log_event("category_delete", user_data, category_data=category_data)

    def log_category_restore(self, user_data, category_data):
        return self._log_event("category_restore", user_data, category_data=category_data)

    # ----- PRODUCT -----
    def log_product_create(self, user_data, product_data):
        return self._log_event("product_create", user_data, product_data=product_data)

    def log_product_update(self, user_data, product_id, old_values, new_values):
        return self._log_event("product_update", user_data,
                               product_id=product_id, old_values=old_values, new_values=new_values)

    def log_product_delete(self, user_data, product_data):
        return self._log_event("product_delete", user_data, product_data=product_data)

    def log_product_stock_update(self, user_data, product_id, product_name, old_stock, new_stock, reason="manual"):
        return self._log_event("product_stock_update", user_data,
                               product_id=product_id, product_name=product_name,
                               old_stock=old_stock, new_stock=new_stock, reason=reason)

    # ----- USER -----
    def log_user_create(self, admin_user, new_user_data):
        return self._log_event("user_create", admin_user, new_user_data=new_user_data)

    def log_user_update(self, admin_user, user_id, old_values, new_values):
        return self._log_event("user_update", admin_user,
                               user_id=user_id, old_values=old_values, new_values=new_values)

    def log_user_delete(self, admin_user, deleted_user_data):
        return self._log_event("user_delete", admin_user, deleted_user_data=deleted_user_data)

    # ----- SYSTEM -----
    def log_data_export(self, user_data, export_type, record_count=0, filename=None):
        return self._log_event("data_export", user_data,
                               export_type=export_type, record_count=record_count, filename=filename)

    def log_data_import(self, user_data, import_type, success_count=0, failure_count=0, filename=None):
        return self._log_event("data_import", user_data,
                               import_type=import_type, success_count=success_count,
                               failure_count=failure_count, filename=filename)

    def log_login_failed(self, username, ip_address=None, reason="invalid_credentials"):
        # Note: user_data is built from the parameters (no logged‑in user)
        user_data = {
            "user_id": None,
            "username": username,
            "ip_address": ip_address,
            "branch_id": None,
            "source": "web"
        }
        return self._log_event("login_failed", user_data, username=username, reason=reason)

    # ------------------------------------------------------------------
    # Template functions (private) – each returns a dict with keys:
    # target_data, old_values, new_values, metadata (any can be omitted)
    # ------------------------------------------------------------------

    def _template_customer_create(self, customer_data):
        return {
            "target_data": {
                "type": "customer",
                "id": customer_data.get("_id", customer_data.get("customer_id", "")),
                "name": customer_data.get("full_name", customer_data.get("username", "Unknown"))
            },
            "new_values": {
                "username": customer_data.get("username"),
                "full_name": customer_data.get("full_name"),
                "email": customer_data.get("email"),
                "phone": customer_data.get("phone"),
                "loyalty_points": customer_data.get("loyalty_points", 0)
            },
            "metadata": {"action": "create"}
        }

    def _template_customer_update(self, customer_id, old_values, new_values):
        return {
            "target_data": {
                "type": "customer",
                "id": customer_id,
                "name": old_values.get("full_name", old_values.get("username", "Unknown"))
            },
            "old_values": old_values,
            "new_values": new_values,
            "metadata": {"action": "update"}
        }

    def _template_customer_delete(self, customer_data):
        return {
            "target_data": {
                "type": "customer",
                "id": customer_data.get("_id", customer_data.get("customer_id", "")),
                "name": customer_data.get("full_name", customer_data.get("username", "Unknown"))
            },
            "old_values": customer_data,
            "metadata": {"action": "delete"}
        }

    def _template_customer_bulk_delete(self, deleted_count, deleted_ids):
        return {
            "target_data": {
                "type": "customer",
                "id": "bulk_operation",
                "name": f"{deleted_count} customers"
            },
            "metadata": {
                "action": "bulk_delete",
                "count": deleted_count,
                "deleted_ids": deleted_ids
            }
        }

    # ----- CATEGORY -----
    def _template_category_create(self, category_data):
        return {
            "target_data": {
                "type": "category",
                "id": category_data.get("_id", category_data.get("category_id", "")),
                "name": category_data.get("category_name", category_data.get("name", "Unknown"))
            },
            "new_values": {
                "name": category_data.get("category_name", category_data.get("name")),
                "description": category_data.get("description"),
                "subcategories": category_data.get("subcategories", [])
            },
            "metadata": {"action": "create"}
        }

    def _template_category_update(self, category_id, old_values, new_values):
        return {
            "target_data": {
                "type": "category",
                "id": category_id,
                "name": old_values.get("category_name", old_values.get("name", "Unknown"))
            },
            "old_values": old_values,
            "new_values": new_values,
            "metadata": {"action": "update"}
        }

    def _template_category_delete(self, category_data):
        return {
            "target_data": {
                "type": "category",
                "id": category_data.get("_id", category_data.get("category_id", "")),
                "name": category_data.get("category_name", category_data.get("name", "Unknown"))
            },
            "old_values": category_data,
            "metadata": {"action": "delete"}
        }

    def _template_category_restore(self, category_data):
        return {
            "target_data": {
                "type": "category",
                "id": category_data.get("_id", category_data.get("category_id", "")),
                "name": category_data.get("category_name", category_data.get("name", "Unknown"))
            },
            "new_values": {"is_active": True},
            "metadata": {"action": "restore"}
        }

    # ----- PRODUCT -----
    def _template_product_create(self, product_data):
        return {
            "target_data": {
                "type": "product",
                "id": product_data.get("_id", product_data.get("product_id", "")),
                "name": product_data.get("product_name", product_data.get("name", "Unknown"))
            },
            "new_values": {
                "name": product_data.get("product_name", product_data.get("name")),
                "category": product_data.get("category"),
                "price": product_data.get("price"),
                "stock_quantity": product_data.get("stock_quantity", 0),
                "description": product_data.get("description")
            },
            "metadata": {"action": "create"}
        }

    def _template_product_update(self, product_id, old_values, new_values):
        return {
            "target_data": {
                "type": "product",
                "id": product_id,
                "name": old_values.get("product_name", old_values.get("name", "Unknown"))
            },
            "old_values": old_values,
            "new_values": new_values,
            "metadata": {"action": "update"}
        }

    def _template_product_delete(self, product_data):
        return {
            "target_data": {
                "type": "product",
                "id": product_data.get("_id", product_data.get("product_id", "")),
                "name": product_data.get("product_name", product_data.get("name", "Unknown"))
            },
            "old_values": product_data,
            "metadata": {"action": "delete"}
        }

    def _template_product_stock_update(self, product_id, product_name, old_stock, new_stock, reason):
        return {
            "target_data": {
                "type": "product",
                "id": product_id,
                "name": product_name
            },
            "old_values": {"stock_quantity": old_stock},
            "new_values": {"stock_quantity": new_stock},
            "metadata": {
                "action": "stock_update",
                "difference": new_stock - old_stock,
                "reason": reason
            }
        }

    # ----- USER -----
    def _template_user_create(self, new_user_data):
        return {
            "target_data": {
                "type": "user",
                "id": new_user_data.get("_id", new_user_data.get("user_id", "")),
                "name": new_user_data.get("username", new_user_data.get("email", "Unknown"))
            },
            "new_values": {
                "username": new_user_data.get("username"),
                "email": new_user_data.get("email"),
                "role": new_user_data.get("role"),
                "status": new_user_data.get("status", "active")
            },
            "metadata": {"action": "create"}
        }

    def _template_user_update(self, user_id, old_values, new_values):
        return {
            "target_data": {
                "type": "user",
                "id": user_id,
                "name": old_values.get("username", old_values.get("email", "Unknown"))
            },
            "old_values": old_values,
            "new_values": new_values,
            "metadata": {"action": "update"}
        }

    def _template_user_delete(self, deleted_user_data):
        return {
            "target_data": {
                "type": "user",
                "id": deleted_user_data.get("_id", deleted_user_data.get("user_id", "")),
                "name": deleted_user_data.get("username", deleted_user_data.get("email", "Unknown"))
            },
            "old_values": deleted_user_data,
            "metadata": {"action": "delete"}
        }

    # ----- SYSTEM -----
    def _template_data_export(self, export_type, record_count, filename):
        return {
            "target_data": {
                "type": "system",
                "id": f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "name": f"{export_type.title()} Export"
            },
            "metadata": {
                "action": "export",
                "export_type": export_type,
                "record_count": record_count,
                "filename": filename,
                "format": "CSV"
            }
        }

    def _template_data_import(self, import_type, success_count, failure_count, filename):
        total = success_count + failure_count
        success_rate = round((success_count / total) * 100, 2) if total > 0 else 0
        return {
            "target_data": {
                "type": "system",
                "id": f"import_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "name": f"{import_type.title()} Import"
            },
            "metadata": {
                "action": "import",
                "import_type": import_type,
                "success_count": success_count,
                "failure_count": failure_count,
                "total_count": total,
                "filename": filename,
                "success_rate": success_rate
            }
        }

    def _template_login_failed(self, username, reason):
        return {
            "target_data": {
                "type": "authentication",
                "id": "login_attempt",
                "name": f"Failed login for {username}"
            },
            "metadata": {
                "action": "login_failed",
                "reason": reason,
                "attempted_username": username
            }
        }

    # ============= QUERY METHODS =============
    # (These remain unchanged – they use the model directly)

    def get_audit_logs_by_user(self, user_id, limit=100):
        try:
            logs = AuditLog.get_by_user_id(user_id, limit=limit)
            return {
                'success': True,
                'data': [log.to_dict() for log in logs],
                'count': len(logs)
            }
        except Exception as e:
            logger.error(f"Error fetching audit logs for user {user_id}: {e}")
            return {'success': False, 'error': str(e), 'data': []}

    def get_audit_logs_by_target(self, target_type, target_id, limit=50):
        try:
            logs = AuditLog.scan(
                (AuditLog.target_type == target_type) & (AuditLog.target_id == target_id),
                limit=limit
            )
            logs = list(logs)
            logs.sort(key=lambda log: log.timestamp, reverse=True)
            return {
                'success': True,
                'data': [log.to_dict() for log in logs],
                'count': len(logs)
            }
        except Exception as e:
            logger.error(f"Error fetching audit logs for target {target_type}:{target_id}: {e}")
            return {'success': False, 'error': str(e), 'data': []}

    def get_audit_statistics(self, limit: int = 10000):
        try:
            logs = list(AuditLog.scan(limit=limit))
            total_logs = len(logs)
            stats = {}
            for log in logs:
                action = log.action or 'unknown'
                if action not in stats:
                    stats[action] = {'count': 0, 'latest': ''}
                stats[action]['count'] += 1
                if log.timestamp and (not stats[action]['latest'] or log.timestamp > stats[action]['latest']):
                    stats[action]['latest'] = log.timestamp.isoformat() if log.timestamp else ''

            by_event_type = [
                {'event_type': action, **data}
                for action, data in stats.items()
            ]
            by_event_type.sort(key=lambda x: x['count'], reverse=True)

            return {
                'success': True,
                'total_logs': total_logs,
                'by_event_type': by_event_type,
            }
        except Exception as e:
            logger.error(f"Error generating audit statistics: {e}")
            return {'success': False, 'error': str(e)}
        
    def log_action(self, user_data, action, resource_id=None, resource_type=None, changes=None):
        """
        Generic audit log for arbitrary actions (e.g., loyalty points updates).
        """
        event_type = f"{resource_type}_{action}" if resource_type else action
        audit_kwargs = {
            'action': event_type,
            'user_id': user_data.get('user_id'),
            'username': user_data.get('username'),
            'branch_id': user_data.get('branch_id'),
            'source': user_data.get('source', 'audit_service'),
            'status': 'success',
            'target_type': resource_type,
            'target_id': str(resource_id) if resource_id else '',
            'target_name': '',
            'description': f"{action} on {resource_type}: {changes}" if changes else ""
        }
        audit_log = AuditLog.create_audit_log(**audit_kwargs)
        return {'audit_id': audit_log.sk} if audit_log else None
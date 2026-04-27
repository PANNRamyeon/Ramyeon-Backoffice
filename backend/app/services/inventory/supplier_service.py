import re
from datetime import datetime
from pynamodb.exceptions import DoesNotExist
from models.Supplier import Supplier
from models.Batches import Batch
from notifications.services import NotificationService
from ..core.audit_service import AuditLogService
import logging

logger = logging.getLogger(__name__)


class SupplierService:
    def __init__(self):
        self.audit_service = AuditLogService()
        self.notification_service = NotificationService()

    # ─── Validation ─────────────────────────────────────────────────────────────

    def validate_supplier_data(self, supplier_data, is_partial_update=False):
        """Validate supplier data before creation/update."""
        if not is_partial_update:
            if not supplier_data.get('supplier_name'):
                raise ValueError("Required field 'supplier_name' is missing or empty")

        if supplier_data.get('email'):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, supplier_data['email']):
                raise ValueError("Invalid email format")

        if supplier_data.get('phone_number'):
            phone = supplier_data['phone_number'].strip()
            if len(phone) < 10:
                raise ValueError("Phone number must be at least 10 digits")

    # ─── Notifications & Audit ──────────────────────────────────────────────────

    def _send_supplier_notification(self, action_type, supplier_name, supplier_id=None):
        """Centralized notification helper for supplier actions."""
        try:
            titles = {
                'created': "New Supplier Added",
                'updated': "Supplier Updated",
                'contact_updated': "Supplier Contact Updated",
                'soft_deleted': "Supplier Deleted",
                'hard_deleted': "Supplier Permanently Deleted",
                'restored': "Supplier Restored"
            }
            messages = {
                'created': f"Supplier '{supplier_name}' has been added to the system",
                'updated': f"Supplier '{supplier_name}' has been updated",
                'contact_updated': f"Contact information for '{supplier_name}' has been updated",
                'soft_deleted': f"Supplier '{supplier_name}' has been moved to trash",
                'hard_deleted': f"Supplier '{supplier_name}' has been permanently removed",
                'restored': f"Supplier '{supplier_name}' has been restored from trash"
            }
            if action_type in titles:
                priority = "high" if action_type == 'hard_deleted' else ("medium" if 'deleted' in action_type else "low")
                self.notification_service.create_notification(
                    title=titles[action_type],
                    message=messages[action_type],
                    priority=priority,
                    notification_type="system",
                    metadata={
                        "supplier_id": str(supplier_id) if supplier_id else "",
                        "supplier_name": supplier_name,
                        "action_type": f"supplier_{action_type}"
                    }
                )
        except Exception as e:
            logger.error(f"Failed to send supplier notification: {e}")

    def _log_audit(self, action, supplier_id, supplier_name, user_id='system', details=None):
        """Log an audit trail entry."""
        try:
            self.audit_service.log_action(
                action=action,
                resource_type='supplier',
                resource_id=supplier_id,
                user_id=user_id,
                changes=None,
                metadata={'supplier_name': supplier_name, **(details or {})}
            )
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")

    # ─── CRUD ───────────────────────────────────────────────────────────────────

    def create_supplier(self, supplier_data, user_id='system'):
        """Create a new supplier with validation, audit, and notification."""
        try:
            self.validate_supplier_data(supplier_data)

            supplier = Supplier.create_supplier(
                supplier_name=supplier_data['supplier_name'],
                contact_person=supplier_data.get('contact_person'),
                email=supplier_data.get('email'),
                phone_number=supplier_data.get('phone_number'),
                address=supplier_data.get('address'),
                type=supplier_data.get('type'),
                notes=supplier_data.get('notes'),
                isFavorite=supplier_data.get('isFavorite', False),
                lead_time_days=supplier_data.get('lead_time_days'),
                payment_terms=supplier_data.get('payment_terms'),
                delivery_method=supplier_data.get('delivery_method'),
                created_by=user_id,
                updated_by=user_id,
            )

            self._log_audit('supplier_created', supplier.sk, supplier.supplier_name, user_id)
            self._send_supplier_notification('created', supplier.supplier_name, supplier.sk)

            return supplier.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error creating supplier: {str(e)}")

    def get_suppliers(self, filters=None, include_deleted=False):
        """Get all suppliers with optional search/type filters."""
        try:
            all_suppliers = list(Supplier.query("suppliers"))
            results = []

            for s in all_suppliers:
                if not include_deleted and s.isDeleted:
                    continue

                d = s.to_dict()

                if filters:
                    if filters.get('search'):
                        search = filters['search'].lower()
                        match = (
                            search in (d.get('supplier_name') or '').lower() or
                            search in (d.get('contact_person') or '').lower() or
                            search in (d.get('email') or '').lower()
                        )
                        if not match:
                            continue

                    if filters.get('type') and filters['type'] != 'all':
                        if d.get('type') != filters['type']:
                            continue

                results.append(d)

            results.sort(key=lambda x: x.get('supplier_name', ''))
            return results
        except Exception as e:
            raise Exception(f"Error getting suppliers: {str(e)}")

    def get_supplier_by_id(self, supplier_id, include_deleted=False, include_batch_stats=False):
        """Get a single supplier by ID, optionally with batch statistics."""
        try:
            if not supplier_id:
                return None

            supplier = Supplier.get("suppliers", supplier_id)

            if not include_deleted and supplier.isDeleted:
                return None

            result = supplier.to_dict()

            if include_batch_stats:
                stats = self.get_supplier_statistics(supplier_id)
                result.update(stats)

            return result
        except DoesNotExist:
            return None
        except Exception as e:
            raise Exception(f"Error getting supplier: {str(e)}")

    def update_supplier(self, supplier_id, supplier_data, user_id='system'):
        """Update supplier fields with validation, audit, and notification."""
        try:
            if not supplier_id:
                raise ValueError("Invalid supplier ID")

            try:
                supplier = Supplier.get("suppliers", supplier_id)
            except DoesNotExist:
                raise Exception(f"Supplier {supplier_id} not found")

            if supplier.isDeleted:
                raise Exception(f"Supplier {supplier_id} not found")

            is_partial = 'supplier_name' not in supplier_data
            self.validate_supplier_data(supplier_data, is_partial_update=is_partial)

            updatable_fields = [
                'supplier_name', 'contact_person', 'email', 'phone_number',
                'address', 'type', 'notes', 'isFavorite',
                'lead_time_days', 'payment_terms', 'delivery_method'
            ]
            for field in updatable_fields:
                if field in supplier_data:
                    setattr(supplier, field, supplier_data[field])

            supplier.updated_at = datetime.utcnow()
            supplier.updated_by = user_id
            supplier.save()

            self._log_audit('supplier_updated', supplier_id, supplier.supplier_name, user_id)
            self._send_supplier_notification('updated', supplier.supplier_name, supplier_id)

            return supplier.to_dict()
        except (ValueError, Exception):
            raise

    def delete_supplier(self, supplier_id, hard_delete=False, user_id='system'):
        """Soft-delete (default) or hard-delete a supplier.

        Hard delete is blocked when the supplier has active batches.
        """
        try:
            if not supplier_id:
                return False

            try:
                supplier = Supplier.get("suppliers", supplier_id)
            except DoesNotExist:
                return False

            if hard_delete:
                active_count = sum(
                    1 for b in Batch.query("batches")
                    if getattr(b, 'supplier_id', None) == supplier_id
                    and getattr(b, 'status', '') == 'active'
                )
                if active_count > 0:
                    raise Exception(
                        f"Cannot delete supplier with {active_count} active batches. "
                        "Please deplete or reassign batches first."
                    )

                supplier_name = supplier.supplier_name
                supplier.delete()
                self._log_audit('supplier_hard_deleted', supplier_id, supplier_name, user_id)
                self._send_supplier_notification('hard_deleted', supplier_name, supplier_id)
                return True
            else:
                if supplier.isDeleted:
                    return False

                supplier.isDeleted = True
                supplier.updated_at = datetime.utcnow()
                supplier.updated_by = user_id
                supplier.save()
                self._log_audit('supplier_soft_deleted', supplier_id, supplier.supplier_name, user_id)
                self._send_supplier_notification('soft_deleted', supplier.supplier_name, supplier_id)
                return True

        except Exception as e:
            raise Exception(f"Error deleting supplier: {str(e)}")

    def restore_supplier(self, supplier_id, user_id='system'):
        """Restore a soft-deleted supplier."""
        try:
            if not supplier_id:
                return False

            try:
                supplier = Supplier.get("suppliers", supplier_id)
            except DoesNotExist:
                return False

            if not supplier.isDeleted:
                return False

            supplier.isDeleted = False
            supplier.updated_at = datetime.utcnow()
            supplier.updated_by = user_id
            supplier.save()
            self._log_audit('supplier_restored', supplier_id, supplier.supplier_name, user_id)
            self._send_supplier_notification('restored', supplier.supplier_name, supplier_id)
            return True
        except Exception as e:
            raise Exception(f"Error restoring supplier: {str(e)}")

    def get_deleted_suppliers(self):
        """Get all soft-deleted suppliers."""
        try:
            all_suppliers = list(Supplier.query("suppliers"))
            deleted = [s.to_dict() for s in all_suppliers if s.isDeleted]
            deleted.sort(key=lambda x: x.get('supplier_name', ''))
            return deleted
        except Exception as e:
            raise Exception(f"Error getting deleted suppliers: {str(e)}")

    # ─── Batch Queries ───────────────────────────────────────────────────────────

    def get_supplier_batches(self, supplier_id, filters=None):
        """Get all batches for a supplier with optional status/product filters."""
        try:
            if not supplier_id:
                raise ValueError("Invalid supplier ID")

            if not self.get_supplier_by_id(supplier_id, include_deleted=False):
                raise Exception(f"Supplier {supplier_id} not found or is deleted")

            batches = []
            for b in Batch.query("batches"):
                if getattr(b, 'supplier_id', None) != supplier_id:
                    continue
                d = b.to_dict()
                if filters:
                    if filters.get('status') and d.get('status') != filters['status']:
                        continue
                    if filters.get('product_id') and d.get('product_id') != filters['product_id']:
                        continue
                batches.append(d)

            batches.sort(key=lambda x: x.get('date_received') or '', reverse=True)
            return batches
        except Exception as e:
            raise Exception(f"Error getting supplier batches: {str(e)}")

    def get_supplier_statistics(self, supplier_id):
        """Compute batch-based statistics for a supplier."""
        try:
            if not supplier_id:
                raise ValueError("Invalid supplier ID")

            supplier_batches = [
                b for b in Batch.query("batches")
                if getattr(b, 'supplier_id', None) == supplier_id
            ]

            if not supplier_batches:
                return {
                    'total_batches': 0,
                    'active_batches': 0,
                    'depleted_batches': 0,
                    'expired_batches': 0,
                    'total_quantity_received': 0,
                    'total_quantity_remaining': 0,
                    'total_cost_value': 0,
                    'unique_products_count': 0
                }

            stats = {
                'total_batches': 0,
                'active_batches': 0,
                'depleted_batches': 0,
                'expired_batches': 0,
                'total_quantity_received': 0,
                'total_quantity_remaining': 0,
                'total_cost_value': 0.0,
            }
            unique_products = set()

            for b in supplier_batches:
                stats['total_batches'] += 1
                status = getattr(b, 'status', '')
                if status == 'active':
                    stats['active_batches'] += 1
                elif status in ('exhausted', 'depleted'):
                    stats['depleted_batches'] += 1
                elif status == 'expired':
                    stats['expired_batches'] += 1

                qty_received = getattr(b, 'quantity_received', 0) or 0
                qty_remaining = getattr(b, 'quantity_remaining', 0) or 0
                cost_price = getattr(b, 'cost_price', 0) or 0

                stats['total_quantity_received'] += qty_received
                stats['total_quantity_remaining'] += qty_remaining
                stats['total_cost_value'] += qty_remaining * cost_price

                if getattr(b, 'product_id', None):
                    unique_products.add(b.product_id)

            stats['unique_products_count'] = len(unique_products)
            return stats
        except Exception as e:
            raise Exception(f"Error getting supplier statistics: {str(e)}")

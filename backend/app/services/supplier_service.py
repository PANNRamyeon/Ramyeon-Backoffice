import re
from datetime import datetime
from pynamodb.exceptions import DoesNotExist
import logging

from ...models.Supplier import Supplier, SyncLogItem
from ..utils import generate_sk
from notifications.services import NotificationService
from .audit_service import AuditLogService

logger = logging.getLogger(__name__)


class SupplierService:
    """
    Supplier service using PynamoDB (DynamoDB) single-table design.
    """

    def __init__(self):
        self.audit_service = AuditLogService()
        self.notification_service = NotificationService()

    # ==================== ID GENERATION ====================

    def generate_supplier_id(self) -> str:
        """Generate a sequential SUPP-### ID using a DynamoDB atomic counter."""
        return generate_sk('SUPP-', 'supplier_seq', digits=3)

    # ==================== SYNC LOG HELPER ====================

    def add_sync_log(self, source='cloud', status='synced', details=None, action=None):
        """Create a SyncLogItem for the supplier's sync_logs list."""
        return SyncLogItem(
            object='supplier',
            last_updated=datetime.utcnow(),
            source=source,
            status=status,
            details=details or {},
            action=action
        )

    # ==================== VALIDATION ====================

    def validate_supplier_data(self, supplier_data, is_partial_update=False):
        """
        Validate supplier data according to the Supplier model.
        For partial updates (e.g. only isFavorite), skip required field checks.
        """
        if not is_partial_update:
            # Core required field
            if not supplier_data.get('supplier_name'):
                raise ValueError("Required field 'supplier_name' is missing or empty")

        # Email format
        if supplier_data.get('email'):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, supplier_data['email']):
                raise ValueError("Invalid email format")

        # Phone number minimal length
        if supplier_data.get('phone_number'):
            phone = supplier_data['phone_number'].strip()
            if len(phone) < 10:
                raise ValueError("Phone number must be at least 10 digits")

    # ==================== NOTIFICATION & AUDIT ====================

    def _send_supplier_notification(self, action_type, supplier_name, supplier_id=None):
        """Centralized notification helper for supplier actions."""
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
            priority = "high" if 'hard_deleted' in action_type else (
                "medium" if 'deleted' in action_type else "low"
            )
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

    def _log_audit(self, action, supplier_id, supplier_name, user_id='system', details=None):
        """Log audit trail for supplier actions."""
        try:
            self.audit_service.log_action(
                action=action,
                resource_type='supplier',
                resource_id=supplier_id,
                user_id=user_id,
                changes=None,
                metadata={
                    'supplier_name': supplier_name,
                    **(details or {})
                }
            )
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")

    # ==================== CORE CRUD ====================

    def create_supplier(self, supplier_data, user_id='system'):
        """Create a new supplier using the Supplier model factory method."""
        try:
            self.validate_supplier_data(supplier_data)

            # Check for duplicate supplier name (case‑insensitive)
            # Since no GSI on supplier_name, we scan and filter in Python
            existing = list(Supplier.scan(
                Supplier.supplier_name == supplier_data['supplier_name'].strip(),
                filter_condition=Supplier.isDeleted == False
            ))
            if existing:
                raise ValueError(
                    f"Supplier with name '{supplier_data['supplier_name']}' already exists"
                )

            # Prepare sync log
            sync_logs = [
                self.add_sync_log(
                    source='cloud',
                    status='pending',
                    details={},
                    action='created'
                )
            ]

            # Use the model's factory method
            supplier = Supplier.create_supplier(
                supplier_name=supplier_data['supplier_name'].strip(),
                contact_person=supplier_data.get('contact_person'),
                email=supplier_data.get('email'),
                phone_number=supplier_data.get('phone_number'),
                address=supplier_data.get('address'),
                type=supplier_data.get('type'),
                notes=supplier_data.get('notes'),
                lead_time_days=supplier_data.get('lead_time_days'),
                payment_terms=supplier_data.get('payment_terms'),
                delivery_method=supplier_data.get('delivery_method'),
                isFavorite=supplier_data.get('isFavorite', False),
                created_by=user_id,
                updated_by=user_id,
                sync_logs=sync_logs
            )

            self._log_audit(
                action='supplier_created',
                supplier_id=supplier.sk,
                supplier_name=supplier.supplier_name,
                user_id=user_id
            )
            self._send_supplier_notification(
                'created',
                supplier.supplier_name,
                supplier.sk
            )

            return supplier.to_dict()

        except Exception as e:
            logger.error(f"Error creating supplier: {str(e)}")
            raise

    def get_supplier_by_id(self, supplier_id, include_deleted=False):
        """
        Retrieve a single supplier by its SK (e.g. 'SUPP-001').
        By default, only non‑deleted suppliers are returned.
        """
        try:
            supplier = Supplier.get('suppliers', supplier_id)
            if not include_deleted and supplier.isDeleted:
                return None
            return supplier.to_dict()
        except DoesNotExist:
            return None

    def get_suppliers(self, filters=None, include_deleted=False, page=1, per_page=50):
        """
        Retrieve a paginated list of suppliers.
        Supports filtering by search term, type, and isDeleted flag.
        """
        try:
            # Base condition: partition key is 'suppliers'
            condition = Supplier.pk == 'suppliers'
            if not include_deleted:
                condition &= Supplier.isDeleted == False

            # Apply type filter if provided
            if filters and filters.get('type'):
                condition &= Supplier.type == filters['type']

            # Scan with the built condition
            # For real pagination, we would use `last_evaluated_key`;
            # here we use simple skip/limit on the result list.
            all_suppliers = list(Supplier.scan(filter_condition=condition))

            # Post-filter: search (case‑insensitive substring match)
            if filters and filters.get('search'):
                search_term = filters['search'].lower()
                all_suppliers = [
                    s for s in all_suppliers
                    if search_term in s.supplier_name.lower()
                    or (s.contact_person and search_term in s.contact_person.lower())
                    or (s.email and search_term in s.email.lower())
                    or (s.sk and search_term in s.sk.lower())
                ]

            # Sort by supplier name
            all_suppliers.sort(key=lambda s: s.supplier_name)

            # Pagination
            total_count = len(all_suppliers)
            start = (page - 1) * per_page
            end = start + per_page
            paginated = all_suppliers[start:end]

            return {
                'suppliers': [s.to_dict() for s in paginated],
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page
                }
            }

        except Exception as e:
            logger.error(f"Error getting suppliers: {str(e)}")
            raise

    def update_supplier(self, supplier_id, supplier_data, user_id='system'):
        """
        Update an existing supplier.
        Accepts both core ERD fields and optional enhanced fields.
        """
        try:
            supplier = self._get_active_supplier(supplier_id)
            if not supplier:
                raise ValueError(f"Supplier with ID {supplier_id} not found or is deleted")

            # Partial update detection – if supplier_name is not provided, skip required validation
            is_partial = 'supplier_name' not in supplier_data
            self.validate_supplier_data(supplier_data, is_partial_update=is_partial)

            # Duplicate name check (if name is being changed)
            if 'supplier_name' in supplier_data:
                new_name = supplier_data['supplier_name'].strip()
                # Exclude current supplier from duplicate check
                existing = list(Supplier.scan(
                    Supplier.supplier_name == new_name,
                    filter_condition=(Supplier.sk != supplier_id) & (Supplier.isDeleted == False)
                ))
                if existing:
                    raise ValueError(f"Supplier with name '{new_name}' already exists")
                supplier.supplier_name = new_name

            # Update simple attributes
            simple_fields = [
                'contact_person', 'email', 'phone_number', 'address', 'type', 'notes',
                'lead_time_days', 'payment_terms', 'delivery_method', 'isFavorite'
            ]
            for field in simple_fields:
                if field in supplier_data:
                    setattr(supplier, field, supplier_data[field])

            # Update enhanced fields (if provided)
            if 'addresses' in supplier_data:
                # Expecting list of SupplierAddress dicts
                supplier.addresses = supplier_data['addresses']
            if 'contact_persons' in supplier_data:
                # Expecting list of ContactPerson dicts
                supplier.contact_persons = supplier_data['contact_persons']

            # Update timestamps and user
            supplier.updated_at = datetime.utcnow()
            supplier.updated_by = user_id

            supplier.save()

            self._log_audit(
                action='supplier_updated',
                supplier_id=supplier.sk,
                supplier_name=supplier.supplier_name,
                user_id=user_id
            )
            self._send_supplier_notification('updated', supplier.supplier_name, supplier.sk)

            return supplier.to_dict()

        except Exception as e:
            logger.error(f"Error updating supplier {supplier_id}: {str(e)}")
            raise

    def delete_supplier(self, supplier_id, hard_delete=False, user_id='system'):
        """
        Soft delete (default) or hard delete a supplier.
        Hard delete removes the item permanently.
        """
        try:
            supplier = self._get_supplier_even_deleted(supplier_id)
            if not supplier:
                return False

            supplier_name = supplier.supplier_name

            if hard_delete:
                supplier.delete()
                action = 'supplier_hard_deleted'
                notification_action = 'hard_deleted'
            else:
                supplier.isDeleted = True
                supplier.updated_at = datetime.utcnow()
                supplier.updated_by = user_id
                supplier.save()
                action = 'supplier_soft_deleted'
                notification_action = 'soft_deleted'

            self._log_audit(
                action=action,
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                user_id=user_id
            )
            self._send_supplier_notification(notification_action, supplier_name, supplier_id)

            return True

        except Exception as e:
            logger.error(f"Error deleting supplier {supplier_id}: {str(e)}")
            raise

    def restore_supplier(self, supplier_id, user_id='system'):
        """Restore a soft‑deleted supplier."""
        try:
            supplier = self._get_supplier_even_deleted(supplier_id)
            if not supplier or not supplier.isDeleted:
                return False

            supplier.isDeleted = False
            supplier.updated_at = datetime.utcnow()
            supplier.updated_by = user_id
            supplier.save()

            self._log_audit(
                action='supplier_restored',
                supplier_id=supplier_id,
                supplier_name=supplier.supplier_name,
                user_id=user_id
            )
            self._send_supplier_notification('restored', supplier.supplier_name, supplier_id)

            return True

        except Exception as e:
            logger.error(f"Error restoring supplier {supplier_id}: {str(e)}")
            raise

    def get_deleted_suppliers(self, page=1, per_page=50):
        """Retrieve a paginated list of soft‑deleted suppliers."""
        try:
            condition = (Supplier.pk == 'suppliers') & (Supplier.isDeleted == True)
            all_deleted = list(Supplier.scan(filter_condition=condition))
            all_deleted.sort(key=lambda s: s.updated_at, reverse=True)

            total_count = len(all_deleted)
            start = (page - 1) * per_page
            end = start + per_page
            paginated = all_deleted[start:end]

            return {
                'suppliers': [s.to_dict() for s in paginated],
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page
                }
            }

        except Exception as e:
            logger.error(f"Error getting deleted suppliers: {str(e)}")
            raise

    # ==================== INTERNAL HELPERS ====================

    def _get_active_supplier(self, supplier_id):
        """Retrieve a non‑deleted supplier by SK. Returns None if not found or deleted."""
        try:
            supplier = Supplier.get('suppliers', supplier_id)
            if supplier.isDeleted:
                return None
            return supplier
        except DoesNotExist:
            return None

    def _get_supplier_even_deleted(self, supplier_id):
        """Retrieve a supplier by SK regardless of deletion status."""
        try:
            return Supplier.get('suppliers', supplier_id)
        except DoesNotExist:
            return None
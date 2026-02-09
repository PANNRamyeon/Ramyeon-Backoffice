import re
from datetime import datetime
from ..database import db_manager
from ..models import Supplier
from notifications.services import NotificationService
import logging
from .audit_service import AuditLogService

logger = logging.getLogger(__name__)

class SupplierService:
    def __init__(self):
        self.db = db_manager.get_database()
        self.supplier_collection = self.db.suppliers
        self.batch_collection = self.db.batches
        self.audit_service = AuditLogService()
        self.notification_service = NotificationService()
    
    def _get_user_info(self, user_id):
        """Get user display information for history logging"""
        try:
            if user_id == 'system':
                return {
                    'display_name': 'System',
                    'email': 'system@pann.com'
                }
            
            user = self.db.users.find_one({'_id': user_id})
            if user:
                display_name = user.get('full_name') or user.get('username') or user.get('email', 'Unknown User')
                return {
                    'display_name': display_name,
                    'email': user.get('email', '')
                }
            else:
                return {
                    'display_name': 'Unknown User',
                    'email': ''
                }
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return {
                'display_name': 'Unknown User',
                'email': ''
            }
    
    def generate_supplier_id(self):
        """Generate sequential SUPP-### ID"""
        try:
            pipeline = [
                {'$match': {'_id': {'$regex': r'^SUPP-\d{3}$'}}},
                {'$project': {
                    'id_number': {
                        '$toInt': {
                            '$substr': ['$_id', 5, -1]
                        }
                    }
                }},
                {'$sort': {'id_number': -1}},
                {'$limit': 1}
            ]
            
            result = list(self.supplier_collection.aggregate(pipeline))
            next_number = (result[0]['id_number'] + 1) if result else 1
            
            return f"SUPP-{next_number:03d}"
        
        except Exception:
            count = self.supplier_collection.count_documents({}) + 1
            return f"SUPP-{count:03d}"
    
    def add_sync_log(self, source='cloud', status='synced', details=None):
        """Helper method to create sync log entries"""
        return {
            'last_updated': datetime.utcnow(),
            'source': source,
            'status': status,
            'details': details or {}
        }
    
    def validate_supplier_data(self, supplier_data, is_partial_update=False):
        """Validate supplier data before creation/update"""
        # For partial updates (e.g., only updating isFavorite), skip required field checks
        if not is_partial_update:
            required_fields = ['supplier_name']
            
            for field in required_fields:
                if not supplier_data.get(field):
                    raise ValueError(f"Required field '{field}' is missing or empty")
        
        # Validate email if provided
        if supplier_data.get('email'):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, supplier_data['email']):
                raise ValueError("Invalid email format")
        
        # Validate phone number if provided
        if supplier_data.get('phone_number'):
            phone = supplier_data['phone_number'].strip()
            if len(phone) < 10:
                raise ValueError("Phone number must be at least 10 digits")
    
    def _send_supplier_notification(self, action_type, supplier_name, supplier_id=None):
        """Centralized notification helper for supplier actions"""
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
                priority = "high" if 'hard_deleted' in action_type else ("medium" if 'deleted' in action_type else "low")
                
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
        """Helper method to log audit trail"""
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

    def create_supplier(self, supplier_data, user_id='system'):
        """Create a new supplier - NO PURCHASE ORDERS"""
        try:
            self.validate_supplier_data(supplier_data)
            
            if not supplier_data.get('_id'):
                supplier_data['_id'] = self.generate_supplier_id()
            
            existing_supplier = self.supplier_collection.find_one({
                'supplier_name': {'$regex': f'^{re.escape(supplier_data["supplier_name"])}$', '$options': 'i'},
                'isDeleted': {'$ne': True}
            })
            if existing_supplier:
                raise ValueError(f"Supplier with name '{supplier_data['supplier_name']}' already exists")
            
            current_time = datetime.utcnow()
            supplier_data.update({
                'isDeleted': False,
                'created_at': current_time,
                'updated_at': current_time,
                'created_by': user_id,
                'sync_logs': [
                    self.add_sync_log(source='cloud', status='pending', details={'action': 'created'})
                ]
            })
            
            result = self.supplier_collection.insert_one(supplier_data)
            
            self._log_audit(
                action='supplier_created',
                supplier_id=supplier_data['_id'],
                supplier_name=supplier_data['supplier_name'],
                user_id=user_id
            )
            
            self._send_supplier_notification('created', supplier_data['supplier_name'], supplier_data['_id'])
            
            return self.supplier_collection.find_one({'_id': supplier_data['_id']})
        
        except Exception as e:
            raise Exception(f"Error creating supplier: {str(e)}")

    def get_suppliers(self, filters=None, include_deleted=False, page=1, per_page=50):
        """Get suppliers with optional filters and pagination"""
        try:
            query = {}
            
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            if filters:
                if filters.get('search'):
                    search_regex = {'$regex': filters['search'], '$options': 'i'}
                    query['$or'] = [
                        {'supplier_name': search_regex},
                        {'contact_person': search_regex},
                        {'email': search_regex},
                        {'_id': search_regex}
                    ]
                
                if filters.get('status'):
                    query['status'] = filters['status']
                
                if filters.get('type'):
                    query['type'] = filters['type']
            
            skip = (page - 1) * per_page
            total_count = self.supplier_collection.count_documents(query)
            
            # Aggregate to include batch statistics
            pipeline = [
                {'$match': query},
                {'$lookup': {
                    'from': 'batches',
                    'localField': '_id',
                    'foreignField': 'supplier_id',
                    'as': 'batches'
                }},
                {'$addFields': {
                    'total_batches': {'$size': '$batches'},
                    'active_batches': {
                        '$size': {
                            '$filter': {
                                'input': '$batches',
                                'as': 'batch',
                                'cond': {'$eq': ['$$batch.status', 'active']}
                            }
                        }
                    }
                }},
                {'$project': {
                    'batches': 0  # Remove the full batches array from response
                }},
                {'$sort': {'supplier_name': 1}},
                {'$skip': skip},
                {'$limit': per_page}
            ]
            
            suppliers = list(self.supplier_collection.aggregate(pipeline))
            
            return {
                'suppliers': suppliers,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page
                }
            }
        
        except Exception as e:
            raise Exception(f"Error getting suppliers: {str(e)}")
    
    def get_supplier_by_id(self, supplier_id, include_deleted=False, include_batch_stats=True):
        """Get supplier by ID with optional batch statistics"""
        try:
            if not supplier_id or not isinstance(supplier_id, str):
                return None
            
            query = {'_id': supplier_id}
            
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            if include_batch_stats:
                pipeline = [
                    {'$match': query},
                    {'$lookup': {
                        'from': 'batches',
                        'localField': '_id',
                        'foreignField': 'supplier_id',
                        'as': 'batches'
                    }},
                    {'$addFields': {
                        'total_batches': {'$size': '$batches'},
                        'active_batches': {
                            '$size': {
                                '$filter': {
                                    'input': '$batches',
                                    'as': 'batch',
                                    'cond': {'$eq': ['$$batch.status', 'active']}
                                }
                            }
                        },
                        'depleted_batches': {
                            '$size': {
                                '$filter': {
                                    'input': '$batches',
                                    'as': 'batch',
                                    'cond': {'$eq': ['$$batch.status', 'depleted']}
                                }
                            }
                        }
                    }},
                    {'$project': {
                        'batches': 0
                    }}
                ]
                
                result = list(self.supplier_collection.aggregate(pipeline))
                return result[0] if result else None
            else:
                return self.supplier_collection.find_one(query)
        
        except Exception as e:
            raise Exception(f"Error getting supplier: {str(e)}")
    
    def get_supplier_batches(self, supplier_id, filters=None):
        """Get all batches for a specific supplier"""
        try:
            if not supplier_id or not isinstance(supplier_id, str):
                raise ValueError("Invalid supplier ID")
            
            supplier = self.get_supplier_by_id(supplier_id, include_deleted=False, include_batch_stats=False)
            if not supplier:
                raise Exception(f"Supplier with ID {supplier_id} not found or is deleted")
            
            query = {'supplier_id': supplier_id}
            
            if filters:
                if filters.get('status'):
                    query['status'] = filters['status']
                
                if filters.get('product_id'):
                    query['product_id'] = filters['product_id']
                
                if filters.get('expiring_soon'):
                    days = filters.get('days_ahead', 30)
                    future_date = datetime.utcnow() + timedelta(days=days)
                    query['expiry_date'] = {'$lte': future_date, '$gte': datetime.utcnow()}
            
            # Lookup product information for each batch
            pipeline = [
                {'$match': query},
                {'$lookup': {
                    'from': 'products',
                    'localField': 'product_id',
                    'foreignField': '_id',
                    'as': 'product_info'
                }},
                {'$unwind': {
                    'path': '$product_info',
                    'preserveNullAndEmptyArrays': True
                }},
                {'$sort': {'date_received': -1}}
            ]
            
            batches = list(self.batch_collection.aggregate(pipeline))
            return batches
        
        except Exception as e:
            raise Exception(f"Error getting supplier batches: {str(e)}")
    
    def get_supplier_statistics(self, supplier_id):
        """Get comprehensive statistics for a supplier"""
        try:
            if not supplier_id or not isinstance(supplier_id, str):
                raise ValueError("Invalid supplier ID")
            
            pipeline = [
                {'$match': {'supplier_id': supplier_id}},
                {'$group': {
                    '_id': None,
                    'total_batches': {'$sum': 1},
                    'active_batches': {
                        '$sum': {'$cond': [{'$eq': ['$status', 'active']}, 1, 0]}
                    },
                    'depleted_batches': {
                        '$sum': {'$cond': [{'$eq': ['$status', 'depleted']}, 1, 0]}
                    },
                    'expired_batches': {
                        '$sum': {'$cond': [{'$eq': ['$status', 'expired']}, 1, 0]}
                    },
                    'total_quantity_received': {'$sum': '$quantity_received'},
                    'total_quantity_remaining': {'$sum': '$quantity_remaining'},
                    'total_cost_value': {
                        '$sum': {'$multiply': ['$quantity_remaining', '$cost_price']}
                    },
                    'unique_products': {'$addToSet': '$product_id'}
                }},
                {'$addFields': {
                    'unique_products_count': {'$size': '$unique_products'}
                }},
                {'$project': {
                    '_id': 0,
                    'unique_products': 0
                }}
            ]
            
            result = list(self.batch_collection.aggregate(pipeline))
            
            if result:
                return result[0]
            else:
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
        
        except Exception as e:
            raise Exception(f"Error getting supplier statistics: {str(e)}")
    
    def update_supplier(self, supplier_id, supplier_data, user_id='system'):
        """Update supplier"""
        try:
            if not supplier_id or not isinstance(supplier_id, str):
                raise ValueError("Invalid supplier ID")
            
            existing_supplier = self.get_supplier_by_id(supplier_id, include_deleted=False, include_batch_stats=False)
            if not existing_supplier:
                raise Exception(f"Supplier with ID {supplier_id} not found or is deleted")
            
            # Check if this is a partial update (only non-required fields)
            is_partial = 'supplier_name' not in supplier_data
            self.validate_supplier_data(supplier_data, is_partial_update=is_partial)
            
            if 'supplier_name' in supplier_data:
                existing_name = self.supplier_collection.find_one({
                    'supplier_name': {'$regex': f'^{re.escape(supplier_data["supplier_name"])}$', '$options': 'i'},
                    '_id': {'$ne': supplier_id},
                    'isDeleted': {'$ne': True}
                })
                if existing_name:
                    raise ValueError(f"Supplier with name '{supplier_data['supplier_name']}' already exists")
            
            supplier_data['updated_at'] = datetime.utcnow()
            supplier_data['updated_by'] = user_id
            
            result = self.supplier_collection.update_one(
                {'_id': supplier_id, 'isDeleted': {'$ne': True}},
                {'$set': supplier_data}
            )
            
            if result.modified_count > 0:
                updated_supplier = self.supplier_collection.find_one({'_id': supplier_id})
                
                self._log_audit(
                    action='supplier_updated',
                    supplier_id=supplier_id,
                    supplier_name=updated_supplier['supplier_name'],
                    user_id=user_id
                )
                
                self._send_supplier_notification('updated', updated_supplier['supplier_name'], supplier_id)
                
                return updated_supplier
            
            return None
        
        except Exception as e:
            raise Exception(f"Error updating supplier: {str(e)}")
    
    def delete_supplier(self, supplier_id, hard_delete=False, user_id='system'):
        """Soft delete or hard delete a supplier"""
        try:
            if not supplier_id or not isinstance(supplier_id, str):
                return False
            
            supplier_to_delete = self.supplier_collection.find_one({'_id': supplier_id})
            if not supplier_to_delete:
                return False
            
            # Check if supplier has active batches
            active_batches_count = self.batch_collection.count_documents({
                'supplier_id': supplier_id,
                'status': 'active'
            })
            
            if active_batches_count > 0 and hard_delete:
                raise Exception(f"Cannot delete supplier with {active_batches_count} active batches. Please deplete or reassign batches first.")
            
            if hard_delete:
                result = self.supplier_collection.delete_one({'_id': supplier_id})
                
                if result.deleted_count > 0:
                    self._log_audit(
                        action='supplier_hard_deleted',
                        supplier_id=supplier_id,
                        supplier_name=supplier_to_delete['supplier_name'],
                        user_id=user_id
                    )
                    
                    self._send_supplier_notification('hard_deleted', supplier_to_delete['supplier_name'], supplier_id)
                    
                    return True
                return False
            else:
                current_time = datetime.utcnow()
                deletion_log = {
                    'deleted_at': current_time,
                    'deleted_by': user_id,
                    'reason': 'Manual deletion'
                }
                
                result = self.supplier_collection.update_one(
                    {'_id': supplier_id, 'isDeleted': {'$ne': True}},
                    {
                        '$set': {
                            'isDeleted': True,
                            'updated_at': current_time,
                            'deletion_log': deletion_log
                        }
                    }
                )
                
                if result.modified_count > 0:
                    self._log_audit(
                        action='supplier_soft_deleted',
                        supplier_id=supplier_id,
                        supplier_name=supplier_to_delete['supplier_name'],
                        user_id=user_id
                    )
                    
                    self._send_supplier_notification('soft_deleted', supplier_to_delete['supplier_name'], supplier_id)
                    
                    return True
                
                return False
        
        except Exception as e:
            raise Exception(f"Error deleting supplier: {str(e)}")
    
    def restore_supplier(self, supplier_id, user_id='system'):
        """Restore a soft-deleted supplier"""
        try:
            if not supplier_id or not isinstance(supplier_id, str):
                return False
            
            current_time = datetime.utcnow()
            restoration_log = {
                'restored_at': current_time,
                'restored_by': user_id,
                'reason': 'Manual restoration'
            }
            
            result = self.supplier_collection.update_one(
                {'_id': supplier_id, 'isDeleted': True},
                {
                    '$set': {
                        'isDeleted': False,
                        'updated_at': current_time,
                        'restoration_log': restoration_log
                    },
                    '$unset': {
                        'deletion_log': 1
                    }
                }
            )
            
            if result.modified_count > 0:
                restored_supplier = self.supplier_collection.find_one({'_id': supplier_id})
                
                self._log_audit(
                    action='supplier_restored',
                    supplier_id=supplier_id,
                    supplier_name=restored_supplier['supplier_name'],
                    user_id=user_id
                )
                
                self._send_supplier_notification('restored', restored_supplier['supplier_name'], supplier_id)
                
                return True
            
            return False
        
        except Exception as e:
            raise Exception(f"Error restoring supplier: {str(e)}")
    
    def get_deleted_suppliers(self, page=1, per_page=50):
        """Get all soft-deleted suppliers"""
        try:
            query = {'isDeleted': True}
            skip = (page - 1) * per_page
            
            total_count = self.supplier_collection.count_documents(query)
            
            suppliers = list(
                self.supplier_collection.find(query)
                .sort('deletion_log.deleted_at', -1)
                .skip(skip)
                .limit(per_page)
            )
            
            return {
                'suppliers': suppliers,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page
                }
            }
        
        except Exception as e:
            raise Exception(f"Error getting deleted suppliers: {str(e)}")
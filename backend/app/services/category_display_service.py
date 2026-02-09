from datetime import datetime
from ..database import db_manager
from ..models import Category
import logging
import re
from .audit_service import AuditLogService
from notifications.services import notification_service

logger = logging.getLogger(__name__)

class CategoryService:
    def __init__(self):
        """Initialize CategoryService with simplified architecture"""
        self.db = db_manager.get_database()
        self.collection = self.db.category
        self.product_collection = self.db.products  
        self.audit_service = AuditLogService()
        self._ensure_indexes()
        self.ensure_uncategorized_category_exists()

    # ================================================================
    # UTILITY METHODS
    # ================================================================

    def ensure_uncategorized_category_exists(self):
        """Ensure an 'Uncategorized' category exists, create if not"""
        try:
            # Check if uncategorized category already exists
            uncategorized = self.collection.find_one({
                '_id': 'UNCTGRY-001',
                'isDeleted': {'$ne': True}
            })
            
            if uncategorized:
                logger.info("Uncategorized category already exists")
                return uncategorized
            
            # Create default uncategorized category
            now = datetime.utcnow()
            uncategorized_data = {
                '_id': 'UNCTGRY-001',
                'category_name': 'Uncategorized',
                'description': 'Default category for products without specific categorization',
                'status': 'active',
                'sub_categories': [{
                    'subcategory_id': 'SUBCAT-00001',
                    'name': 'General',
                    'description': 'General uncategorized products',
                    'created_at': now.isoformat(),
                    'status': 'active'
                    # NO products array
                }],
                'isDeleted': False,
                'date_created': now.isoformat(),
                'last_updated': now.isoformat()
            }
            
            # Insert the category
            result = self.collection.insert_one(uncategorized_data)
            
            logger.info("Created default 'Uncategorized' category with ID: UNCTGRY-001")
            
            # Send notification about system initialization
            self._send_category_notification('created', 'Uncategorized', 'UNCTGRY-001', {
                'system_generated': True,
                'action_type': 'system_initialization'
            })
            
            return uncategorized_data
            
        except Exception as e:
            logger.error(f"Error ensuring uncategorized category exists: {e}")
            raise Exception(f"Error creating uncategorized category: {str(e)}")

    def generate_category_id(self):
        """Generate sequential CTGY-### ID"""
        try:
            # Use aggregation to find highest existing number
            pipeline = [
                {
                    '$match': {
                        '_id': {'$regex': '^CTGY-\\d{3}$'}
                    }
                },
                {
                    '$addFields': {
                        'numeric_part': {
                            '$toInt': {'$substr': ['$_id', 5, 3]}
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'max_number': {'$max': '$numeric_part'}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result and result[0]['max_number'] is not None:
                next_number = result[0]['max_number'] + 1
            else:
                # Fallback to count-based approach
                next_number = self.collection.count_documents({}) + 1
            
            return f"CTGY-{next_number:03d}"
            
        except Exception as e:
            logger.error(f"Error generating category ID: {e}")
            # Emergency fallback
            import time
            fallback_number = int(time.time()) % 1000
            return f"CTGY-{fallback_number:03d}"

    def generate_subcategory_id(self):
        """Generate sequential SUBCAT-##### ID"""
        try:
            # Use aggregation to find highest existing number across all categories
            pipeline = [
                {"$unwind": "$sub_categories"},
                {
                    '$match': {
                        'sub_categories.subcategory_id': {'$regex': '^SUBCAT-\\d{5}$'}
                    }
                },
                {
                    '$addFields': {
                        'numeric_part': {
                            '$toInt': {'$substr': ['$sub_categories.subcategory_id', 7, 5]}
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'max_number': {'$max': '$numeric_part'}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result and result[0]['max_number'] is not None:
                next_number = result[0]['max_number'] + 1
            else:
                next_number = 1
            
            return f"SUBCAT-{next_number:05d}"
            
        except Exception as e:
            logger.error(f"Error generating subcategory ID: {e}")
            # Emergency fallback
            import time
            fallback_number = int(time.time()) % 100000
            return f"SUBCAT-{fallback_number:05d}"

    def _ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            indexes = [
                [("_id", 1), ("isDeleted", 1)],
                [("category_name", 1), ("isDeleted", 1)],
                [("status", 1), ("isDeleted", 1)],
                [("sub_categories.name", 1)]
            ]
            
            # Add product collection indexes for efficient category queries
            product_indexes = [
                [("category_id", 1), ("subcategory_name", 1)],
                [("category_id", 1), ("isDeleted", 1)],
                [("subcategory_name", 1)]
            ]
            
            for index_fields in indexes:
                self.collection.create_index(index_fields, background=True)
                
            for index_fields in product_indexes:
                self.product_collection.create_index(index_fields, background=True)
                
            logger.info("Category and product indexes created successfully")
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")

    def _validate_category_data(self, category_data):
        """Validate category data before processing"""
        if not category_data:
            raise ValueError("Category data is required")
        
        category_name = category_data.get("category_name", "").strip()
        if not category_name:
            raise ValueError("Category name is required")
        
        # Check for duplicates
        existing = self.collection.find_one({
            'category_name': category_name,
            'isDeleted': {'$ne': True}
        })

        if existing:
            raise ValueError(f"Category '{category_name}' already exists")
        
        # Validate status if provided
        status = category_data.get("status", "active")
        if status not in ['active', 'inactive']:
            raise ValueError("Status must be 'active' or 'inactive'")
        
        return category_name

    def _prepare_subcategories(self, existing_sub_categories):
        """Prepare subcategories without product arrays"""
        subcategories_list = existing_sub_categories or []
        
        # Check if "None" subcategory already exists
        none_exists = any(
            sub.get('name', '').lower() == 'none' 
            for sub in subcategories_list
        )
        
        if not none_exists:
            default_none = {
                'subcategory_id': self.generate_subcategory_id(),
                'name': "None",
                'description': "Default holding subcategory for products without specific subcategorization",
                'created_at': datetime.utcnow(),
                'status': 'active'
                # NO products array
            }
            subcategories_list.insert(0, default_none)
            logger.debug("Auto-added 'None' subcategory")
        
        # Process existing subcategories
        processed_subcategories = []
        for sub in subcategories_list:
            # If subcategory doesn't have an ID, generate one
            if not sub.get('subcategory_id'):
                sub['subcategory_id'] = self.generate_subcategory_id()
            
            clean_sub = {
                'subcategory_id': sub['subcategory_id'],
                'name': sub.get('name', ''),
                'description': sub.get('description', ''),
                'created_at': sub.get('created_at', datetime.utcnow()),
                'status': sub.get('status', 'active')
                # NO products array
            }
            processed_subcategories.append(clean_sub)
        
        return processed_subcategories
    
    def _send_category_notification(self, action_type, category_name, category_id=None, additional_metadata=None):
        """Centralized notification helper for category actions"""
        try:
            templates = {
                'created': {
                    'title': "Category Created",
                    'message': f"Category '{category_name}' has been created",
                    'priority': "medium"
                },
                'updated': {
                    'title': "Category Updated", 
                    'message': f"Category '{category_name}' has been updated",
                    'priority': "medium"
                },
                'soft_deleted': {
                    'title': "Category Deleted",
                    'message': f"Category '{category_name}' has been deleted",
                    'priority': "medium"
                },
                'hard_deleted': {
                    'title': "Category Permanently Deleted",
                    'message': f"Category '{category_name}' has been permanently deleted",
                    'priority': "high"
                },
                'restored': {
                    'title': "Category Restored",
                    'message': f"Category '{category_name}' has been restored",
                    'priority': "medium"
                },
                'bulk_created': {
                    'title': "Categories Bulk Created",
                    'message': f"Multiple categories created including '{category_name}'",
                    'priority': "low"
                },
                'bulk_updated': {
                    'title': "Categories Bulk Updated",
                    'message': f"Multiple categories updated including '{category_name}'",
                    'priority': "low"
                },
                'subcategory_added': {
                    'title': "Subcategory Added",
                    'message': f"Subcategory added to category '{category_name}'",
                    'priority': "low"
                },
                'subcategory_removed': {
                    'title': "Subcategory Removed", 
                    'message': f"Subcategory removed from category '{category_name}'",
                    'priority': "low"
                },
                'products_moved': {
                    'title': "Products Moved",
                    'message': f"Products moved in category '{category_name}'",
                    'priority': "low"
                }
            }
            
            template = templates.get(action_type)
            if not template:
                logger.warning(f"Unknown notification action type: {action_type}")
                return
            
            # Prepare metadata
            metadata = {
                "category_id": str(category_id) if category_id else "",
                "category_name": category_name,
                "action_type": f"category_{action_type}"
            }
            
            # Add additional metadata if provided
            if additional_metadata and isinstance(additional_metadata, dict):
                metadata.update(additional_metadata)
            
            # Send notification
            notification_service.create_notification(
                title=template['title'],
                message=template['message'],
                priority=template['priority'],
                notification_type="system",
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to send category notification: {e}")

    # ================================================================
    # CORE CATEGORY CRUD OPERATIONS
    # ================================================================
    
    def create_category(self, category_data, current_user=None):
        try:
            category_name = self._validate_category_data(category_data)
            logger.info(f"Creating category: {category_name}")
            
            # Generate string ID
            category_id = self.generate_category_id()
            
            # Prepare subcategories (without product arrays)
            existing_sub_categories = category_data.get("sub_categories", [])
            sub_categories = self._prepare_subcategories(existing_sub_categories)
            
            # Add timestamps and default values
            now = datetime.utcnow()
            category_kwargs = {
                '_id': category_id,
                'category_name': category_name,
                'description': category_data.get("description", ''),
                'status': category_data.get("status", 'active'),
                'sub_categories': sub_categories,
                'isDeleted': False,
                'date_created': now.isoformat(),
                'last_updated': now.isoformat()
            }
            
            # Add image fields if present
            image_fields = ['image_url', 'image_filename', 'image_size', 'image_type', 'image_uploaded_at']
            for field in image_fields:
                if field in category_data and category_data[field] is not None:
                    category_kwargs[field] = category_data[field]
            
            # Create and insert category
            category = Category(**category_kwargs)
            self.collection.insert_one(category.to_dict())
            
            # Send notification
            self._send_category_notification('created', category_name, category_id)
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    audit_data = {**category_kwargs, "category_id": category_id}
                    self.audit_service.log_category_create(current_user, audit_data)
                    logger.debug("Audit log created for category creation")
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            logger.info(f"Category '{category_name}' created successfully with ID {category_id}")
            
            return category_kwargs

        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error creating category: {e}", exc_info=True)
            raise Exception(f"Error creating category: {str(e)}")
    
    def get_all_categories(self, include_deleted=False, limit=None, skip=None):
        """Get all categories with optional product counts"""
        try:
            query = {}
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            cursor = self.collection.find(query)
            
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            categories = list(cursor)
            
            # Optionally add product counts for each category
            for category in categories:
                category['product_count'] = self.get_category_product_count(category['_id'])
                
                # Add product counts per subcategory
                for subcategory in category.get('sub_categories', []):
                    subcategory['product_count'] = self.get_subcategory_product_count(
                        category['_id'], 
                        subcategory['name']
                    )
            
            return categories
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            raise Exception(f"Error getting categories: {str(e)}")
    
    def get_category_by_id(self, category_id, include_deleted=False):
        """Get category by ID with product information"""
        try:
            if not category_id or not category_id.startswith('CTGY-'):
                return None
            
            query = {'_id': category_id}
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}

            category = self.collection.find_one(query)
            
            if category:
                # Add product counts
                category['product_count'] = self.get_category_product_count(category_id)
                
                # Add product counts per subcategory
                for subcategory in category.get('sub_categories', []):
                    subcategory['product_count'] = self.get_subcategory_product_count(
                        category_id, 
                        subcategory['name']
                    )
            
            return category
        except Exception as e:
            logger.error(f"Error getting category by ID {category_id}: {e}")
            raise Exception(f"Error getting category: {str(e)}")
        
    def update_category(self, category_id, category_data, current_user=None):
        """Update category"""
        try:
            logger.info(f"Updating category {category_id}")
            if current_user:
                logger.info(f"Updated by: {current_user['username']}")
            
            if not category_id or not category_id.startswith('CTGY-'):
                return None
            
            # Get current category data for audit
            old_category = self.collection.find_one({
                '_id': category_id,
                'isDeleted': {'$ne': True}
            })
            
            if not old_category:
                logger.error(f"Category {category_id} not found for update")
                return None
            
            # Prepare update data
            update_data = category_data.copy()
            update_data['last_updated'] = datetime.utcnow().isoformat()
            
            # Validate category name if being updated
            if 'category_name' in update_data:
                new_name = update_data['category_name'].strip()
                if new_name != old_category.get('category_name'):
                    existing = self.collection.find_one({
                        'category_name': new_name,
                        'isDeleted': {'$ne': True},
                        '_id': {'$ne': category_id}
                    })
                    if existing:
                        raise ValueError(f"Category name '{new_name}' already exists")

            # Update category
            result = self.collection.update_one(
                {
                    '_id': category_id,
                    'isDeleted': {'$ne': True}
                },
                {'$set': update_data}
            )
            
            if result.modified_count == 0:
                return None

            # Get updated category
            updated_category = self.collection.find_one({'_id': category_id})
            
            # Send notification
            self._send_category_notification('updated', updated_category['category_name'], category_id)
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_action(
                        current_user, 
                        category_id, 
                        old_values=old_category, 
                        new_values=update_data
                    )
                    logger.debug("Audit log created for category update")
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            logger.info(f"Category updated successfully")
            return updated_category

        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error updating category: {e}", exc_info=True)
            raise Exception(f"Error updating category: {str(e)}")
        
    def soft_delete_category(self, category_id, current_user=None, deletion_context=None):
        """Soft delete category - moves all products to Uncategorized"""
        try:
            logger.info(f"Soft deleting category {category_id}")
            if current_user:
                logger.info(f"Deleted by: {current_user['username']}")
            
            if not category_id or not category_id.startswith('CTGY-'):
                return False
            
            # Get category data before deletion
            category_to_delete = self.collection.find_one({
                '_id': category_id,
                'isDeleted': {'$ne': True}
            })
            
            if not category_to_delete:
                return False
            
            # Move all products in this category to Uncategorized
            products_moved = self.move_all_products_to_uncategorized(category_id)
            
            now = datetime.utcnow()
            
            # Soft delete data
            update_data = {
                'isDeleted': True,
                'deleted_at': now,
                'deletedBy': current_user.get('username') if current_user else 'system',
                'last_updated': now,
                'deletionContext': deletion_context or "category_deletion",
                'products_moved_count': products_moved
            }
            
            # Update category
            result = self.collection.update_one(
                {'_id': category_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                # Send notification
                self._send_category_notification('soft_deleted', category_to_delete['category_name'], category_id, {
                    'products_moved': products_moved
                })
                
                # Audit logging
                if current_user and self.audit_service:
                    try:
                        category_for_audit = category_to_delete.copy()
                        category_for_audit['deletion_type'] = 'soft_delete'
                        category_for_audit['products_moved'] = products_moved
                        
                        self.audit_service.log_action(current_user, category_for_audit)
                        logger.info("Audit log created for category soft deletion")
                    except Exception as audit_error:
                        logger.error(f"Audit logging failed: {audit_error}")
                
                logger.info(f"Category soft deleted successfully, {products_moved} products moved")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error soft deleting category {category_id}: {str(e)}")
            raise Exception(f"Error soft deleting category: {str(e)}")

    def restore_category(self, category_id, current_user=None):
        """Restore a soft-deleted category"""
        try:
            logger.info(f"Restoring category {category_id}")
            if current_user:
                logger.info(f"Restored by: {current_user['username']}")
            
            if not category_id or not category_id.startswith('CTGY-'):
                return False
            
            # Find deleted category
            deleted_category = self.collection.find_one({
                '_id': category_id,
                'isDeleted': True
            })
            
            if not deleted_category:
                return False
            
            now = datetime.utcnow()
            
            # Restore data
            restore_data = {
                'isDeleted': False,
                'restoredAt': now,
                'restoredBy': current_user.get('username') if current_user else 'system',
                'last_updated': now,
                'status': 'active'
            }
            
            # Remove deletion metadata
            unset_data = {
                'deleted_at': "",
                'deletedBy': "",
                'deletionContext': "",
                'products_moved_count': ""
            }
            
            # Restore category
            result = self.collection.update_one(
                {'_id': category_id},
                {'$set': restore_data, '$unset': unset_data}
            )
            
            if result.modified_count > 0:
                restored_category = self.collection.find_one({'_id': category_id})
                
                # Send notification
                self._send_category_notification('restored', restored_category['category_name'], category_id)
                
                # Audit logging
                if current_user and self.audit_service:
                    try:
                        self.audit_service.log_category_restore(current_user, restored_category)
                        logger.info("Audit log created for category restoration")
                    except Exception as audit_error:
                        logger.error(f"Audit logging failed: {audit_error}")
                
                logger.info("Category restored successfully")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error restoring category {category_id}: {str(e)}")
            raise Exception(f"Error restoring category: {str(e)}")

    def hard_delete_category(self, category_id, current_user=None):
        """Permanently delete category (use with extreme caution)"""
        try:
            logger.warning(f"HARD DELETING category {category_id} - THIS IS PERMANENT!")
            if current_user:
                logger.info(f"Deleted by: {current_user['username']}")
            
            if not category_id or not category_id.startswith('CTGY-'):
                return False
            
            # Get category data before permanent deletion
            category_to_delete = self.collection.find_one({'_id': category_id})
            if not category_to_delete:
                return False
            
            category_name = category_to_delete.get('category_name', 'Unknown Category')
            
            # Move all products to uncategorized before deletion
            products_moved = self.move_all_products_to_uncategorized(category_id)
            
            # Permanently delete from collection
            result = self.collection.delete_one({'_id': category_id})
            
            if result.deleted_count > 0:
                # Send critical notification
                self._send_category_notification('hard_deleted', category_name, category_id, {
                    "warning": "PERMANENT_DELETION",
                    "deleted_by": current_user.get('username') if current_user else 'system',
                    "products_moved": products_moved
                })
                
                # Audit logging
                if current_user and self.audit_service:
                    try:
                        category_for_audit = category_to_delete.copy()
                        category_for_audit['deletion_type'] = 'hard_delete'
                        category_for_audit['products_moved'] = products_moved
                        
                        self.audit_service.log_action(current_user, category_for_audit)
                        logger.info("Audit log created for PERMANENT category deletion")
                    except Exception as audit_error:
                        logger.error(f"Audit logging failed: {audit_error}")
                
                logger.warning(f"Category PERMANENTLY deleted, {products_moved} products moved")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error permanently deleting category {category_id}: {str(e)}")
            raise Exception(f"Error permanently deleting category: {str(e)}")

    def get_deleted_categories(self):
        """Get all soft-deleted categories"""
        try:
            categories = list(self.collection.find({'isDeleted': True}))
            return categories
        except Exception as e:
            logger.error(f"Error getting deleted categories: {e}")
            raise Exception(f"Error getting deleted categories: {str(e)}")

    # ================================================================
    # PRODUCT QUERY METHODS (replacing array-based methods)
    # ================================================================
    
    def get_category_product_count(self, category_id):
        """Get total number of products in a category"""
        try:
            count = self.product_collection.count_documents({
                'category_id': category_id,
                'isDeleted': {'$ne': True}
            })
            return count
        except Exception as e:
            logger.error(f"Error getting category product count: {e}")
            return 0
    
    def get_subcategory_product_count(self, category_id, subcategory_name):
        """Get number of products in a specific subcategory"""
        try:
            count = self.product_collection.count_documents({
                'category_id': category_id,
                'subcategory_name': subcategory_name,
                'isDeleted': {'$ne': True}
            })
            return count
        except Exception as e:
            logger.error(f"Error getting subcategory product count: {e}")
            return 0
    
    def get_products_in_category(self, category_id, include_deleted=False):
        """Get all products in a category"""
        try:
            query = {'category_id': category_id}
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            products = list(self.product_collection.find(query).sort('product_name', 1))
            return products
        except Exception as e:
            logger.error(f"Error getting products in category: {e}")
            raise Exception(f"Error getting products in category: {str(e)}")
    
    def get_products_in_subcategory(self, category_id, subcategory_name, include_deleted=False):
        """Get all products in a specific subcategory"""
        try:
            query = {
                'category_id': category_id,
                'subcategory_name': subcategory_name
            }
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            products = list(self.product_collection.find(query).sort('product_name', 1))
            return products
        except Exception as e:
            logger.error(f"Error getting products in subcategory: {e}")
            raise Exception(f"Error getting products in subcategory: {str(e)}")

    def get_category_with_products(self, category_id, include_deleted=False):
        """Get category with all its products organized by subcategory"""
        try:
            category = self.get_category_by_id(category_id, include_deleted)
            if not category:
                return None
            
            # Get all products in this category
            products = self.get_products_in_category(category_id, include_deleted)
            
            # Organize products by subcategory
            for subcategory in category.get('sub_categories', []):
                subcategory_name = subcategory['name']
                subcategory_products = [
                    p for p in products 
                    if p.get('subcategory_name') == subcategory_name
                ]
                subcategory['products'] = subcategory_products
                subcategory['product_count'] = len(subcategory_products)
            
            return category
        except Exception as e:
            logger.error(f"Error getting category with products: {e}")
            raise Exception(f"Error getting category with products: {str(e)}")

    # ================================================================
    # PRODUCT MANAGEMENT PROXY METHODS
    # ================================================================
    
    def move_product_to_category(self, product_id, new_category_id, new_subcategory_name=None, current_user=None):
        """Proxy method: Move product to a different category"""
        try:
            logger.info(f"Moving product {product_id} to category {new_category_id}")
            
            # Validate category exists
            if new_category_id:
                category = self.get_category_by_id(new_category_id)
                if not category:
                    raise ValueError(f"Category {new_category_id} not found")
                
                # If no subcategory specified, use "General" or first available
                if not new_subcategory_name:
                    subcategories = category.get('sub_categories', [])
                    if subcategories:
                        new_subcategory_name = 'General' if any(s['name'] == 'General' for s in subcategories) else subcategories[0]['name']
                    else:
                        new_subcategory_name = 'General'
                
                # Validate subcategory exists
                subcategory_exists = any(
                    sub['name'] == new_subcategory_name 
                    for sub in category.get('sub_categories', [])
                )
                if not subcategory_exists:
                    raise ValueError(f"Subcategory '{new_subcategory_name}' not found in category")
            
            # Update product document
            update_data = {}
            if new_category_id:
                update_data['category_id'] = new_category_id
                update_data['subcategory_name'] = new_subcategory_name
            else:
                # Moving to uncategorized
                update_data['category_id'] = 'UNCTGRY-001'
                update_data['subcategory_name'] = 'General'
            
            update_data['updated_at'] = datetime.utcnow()
            
            result = self.product_collection.update_one(
                {'_id': product_id, 'isDeleted': {'$ne': True}},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                updated_product = self.product_collection.find_one({'_id': product_id})
                logger.info(f"Product moved successfully")
                return updated_product
            
            return None
            
        except Exception as e:
            logger.error(f"Error moving product to category: {e}")
            raise Exception(f"Error moving product to category: {str(e)}")
    
    def move_product_to_subcategory(self, product_id, category_id, subcategory_name, current_user=None):
        """Proxy method: Move product to a different subcategory within the same category"""
        try:
            logger.info(f"Moving product {product_id} to subcategory {subcategory_name} in category {category_id}")
            
            # Validate category and subcategory exist
            category = self.get_category_by_id(category_id)
            if not category:
                raise ValueError(f"Category {category_id} not found")
            
            subcategory_exists = any(
                sub['name'] == subcategory_name 
                for sub in category.get('sub_categories', [])
            )
            if not subcategory_exists:
                raise ValueError(f"Subcategory '{subcategory_name}' not found in category")
            
            # Update product
            result = self.product_collection.update_one(
                {'_id': product_id, 'isDeleted': {'$ne': True}},
                {
                    '$set': {
                        'category_id': category_id,
                        'subcategory_name': subcategory_name,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                updated_product = self.product_collection.find_one({'_id': product_id})
                logger.info(f"Product moved to subcategory successfully")
                return updated_product
            
            return None
            
        except Exception as e:
            logger.error(f"Error moving product to subcategory: {e}")
            raise Exception(f"Error moving product to subcategory: {str(e)}")
    
    def bulk_move_products_to_category(self, product_ids, new_category_id, new_subcategory_name=None, current_user=None):
        """Proxy method: Bulk move products to a different category"""
        try:
            logger.info(f"Bulk moving {len(product_ids)} products to category {new_category_id}")
            
            # Validate category exists
            if new_category_id:
                category = self.get_category_by_id(new_category_id)
                if not category:
                    raise ValueError(f"Category {new_category_id} not found")
                
                # If no subcategory specified, use "General" or first available
                if not new_subcategory_name:
                    subcategories = category.get('sub_categories', [])
                    if subcategories:
                        new_subcategory_name = 'General' if any(s['name'] == 'General' for s in subcategories) else subcategories[0]['name']
                    else:
                        new_subcategory_name = 'General'
            else:
                # Moving to uncategorized
                new_category_id = 'UNCTGRY-001'
                new_subcategory_name = 'General'
            
            # Bulk update products
            result = self.product_collection.update_many(
                {
                    '_id': {'$in': product_ids},
                    'isDeleted': {'$ne': True}
                },
                {
                    '$set': {
                        'category_id': new_category_id,
                        'subcategory_name': new_subcategory_name,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Send notification
                category_name = category.get('category_name', 'Uncategorized') if category else 'Uncategorized'
                self._send_category_notification('products_moved', category_name, new_category_id, {
                    'products_moved': result.modified_count,
                    'target_subcategory': new_subcategory_name
                })
                
                logger.info(f"Bulk moved {result.modified_count} products successfully")
                return result.modified_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error bulk moving products: {e}")
            raise Exception(f"Error bulk moving products: {str(e)}")
    
    def bulk_move_products_to_subcategory(self, product_ids, category_id, subcategory_name, current_user=None):
        """Proxy method: Bulk move products to a different subcategory"""
        try:
            logger.info(f"Bulk moving {len(product_ids)} products to subcategory {subcategory_name}")
            
            # Validate category and subcategory exist
            category = self.get_category_by_id(category_id)
            if not category:
                raise ValueError(f"Category {category_id} not found")
            
            subcategory_exists = any(
                sub['name'] == subcategory_name 
                for sub in category.get('sub_categories', [])
            )
            if not subcategory_exists:
                raise ValueError(f"Subcategory '{subcategory_name}' not found in category")
            
            # Bulk update products
            result = self.product_collection.update_many(
                {
                    '_id': {'$in': product_ids},
                    'isDeleted': {'$ne': True}
                },
                {
                    '$set': {
                        'category_id': category_id,
                        'subcategory_name': subcategory_name,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Send notification
                self._send_category_notification('products_moved', category['category_name'], category_id, {
                    'products_moved': result.modified_count,
                    'target_subcategory': subcategory_name
                })
                
                logger.info(f"Bulk moved {result.modified_count} products to subcategory successfully")
                return result.modified_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error bulk moving products to subcategory: {e}")
            raise Exception(f"Error bulk moving products to subcategory: {str(e)}")
    
    def move_all_products_to_uncategorized(self, category_id):
        """Move all products from a category to Uncategorized"""
        try:
            logger.info(f"Moving all products from category {category_id} to Uncategorized")
            
            result = self.product_collection.update_many(
                {
                    'category_id': category_id,
                    'isDeleted': {'$ne': True}
                },
                {
                    '$set': {
                        'category_id': 'UNCTGRY-001',
                        'subcategory_name': 'General',
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Moved {result.modified_count} products to Uncategorized")
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error moving products to uncategorized: {e}")
            return 0

    # ================================================================
    # SUBCATEGORY MANAGEMENT
    # ================================================================
    
    def add_subcategory(self, category_id, subcategory_data, current_user=None):
        """Add a subcategory to a category"""
        try:
            logger.info(f"Adding subcategory to category {category_id}")
            if current_user:
                logger.info(f"Added by: {current_user['username']}")
            
            if not category_id or not category_id.startswith('CTGY-'):
                return False
            
            # Validate subcategory data
            if not subcategory_data or not subcategory_data.get('name', '').strip():
                raise ValueError("Subcategory name is required")
            
            # Check if category exists and is not deleted
            category = self.collection.find_one({
                '_id': category_id,
                'isDeleted': {'$ne': True}
            })
            
            if not category:
                raise ValueError("Category not found or is deleted")
            
            # Check for duplicate subcategory name
            existing_names = [sub.get('name', '').lower() for sub in category.get('sub_categories', [])]
            new_name = subcategory_data.get('name', '').strip().lower()
            
            if new_name in existing_names:
                raise ValueError(f"Subcategory '{subcategory_data.get('name')}' already exists")
            
            # Prepare subcategory data
            subcategory_data['subcategory_id'] = self.generate_subcategory_id()
            subcategory_data['created_at'] = datetime.utcnow().isoformat()
            subcategory_data['status'] = subcategory_data.get('status', 'active')
            # NO products array
            
            # Add subcategory
            result = self.collection.update_one(
                {'_id': category_id},
                {
                    '$addToSet': {'sub_categories': subcategory_data},
                    '$set': {'last_updated': datetime.utcnow().isoformat()}
                }
            )
            
            if result.modified_count > 0:
                # Send notification
                self._send_category_notification('subcategory_added', category.get('category_name', 'Unknown'), category_id, {
                    "subcategory_name": subcategory_data.get('name', 'Unknown'),
                    "action_type": "subcategory_added"
                })
                
                logger.info(f"Subcategory '{subcategory_data.get('name')}' added successfully")
                return True
            
            return False
            
        except ValueError as ve:
            logger.error(f"Validation error adding subcategory: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error adding subcategory: {e}", exc_info=True)
            raise Exception(f"Error adding subcategory: {str(e)}")

    def remove_subcategory(self, category_id, subcategory_name, current_user=None):
        """Remove a subcategory from a category - moves products to 'General'"""
        try:
            logger.info(f"Removing subcategory '{subcategory_name}' from category {category_id}")
            
            if not category_id or not category_id.startswith('CTGY-'):
                return False
            
            # Check if category exists and is not deleted
            category = self.collection.find_one({
                '_id': category_id,
                'isDeleted': {'$ne': True}
            })
            
            if not category:
                raise ValueError("Category not found or is deleted")
            
            # Find subcategory
            subcategory_to_remove = None
            for sub in category.get('sub_categories', []):
                if sub.get('name') == subcategory_name:
                    subcategory_to_remove = sub
                    break
            
            if not subcategory_to_remove:
                raise ValueError(f"Subcategory '{subcategory_name}' not found")
            
            # Move products to 'General' subcategory
            products_moved = self.bulk_move_products_to_subcategory(
                product_ids=[], # Will be determined by the query
                category_id=category_id,
                subcategory_name='General'
            )
            
            # Actually move the products
            result = self.product_collection.update_many(
                {
                    'category_id': category_id,
                    'subcategory_name': subcategory_name,
                    'isDeleted': {'$ne': True}
                },
                {
                    '$set': {
                        'subcategory_name': 'General',
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            products_moved = result.modified_count
            
            # Remove subcategory from category
            remove_result = self.collection.update_one(
                {'_id': category_id},
                {
                    '$pull': {'sub_categories': {'name': subcategory_name}},
                    '$set': {'last_updated': datetime.utcnow()}
                }
            )
            
            if remove_result.modified_count > 0:
                self._send_category_notification('subcategory_removed', category.get('category_name', 'Unknown'), category_id, {
                    "subcategory_name": subcategory_name,
                    "action_type": "subcategory_removed",
                    "products_moved": products_moved
                })
                
                logger.info(f"Subcategory '{subcategory_name}' removed successfully, {products_moved} products moved to General")
                return True
            
            return False
            
        except ValueError as ve:
            logger.error(f"Validation error removing subcategory: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error removing subcategory: {e}", exc_info=True)
            raise Exception(f"Error removing subcategory: {str(e)}")

    def get_subcategories(self, category_id):
        """Get all subcategories for a specific category with product counts"""
        try:
            if not category_id or not category_id.startswith('CTGY-'):
                return []
            
            category = self.collection.find_one(
                {
                    '_id': category_id,
                    'isDeleted': {'$ne': True}
                },
                {'sub_categories': 1}
            )
            
            if not category:
                return []
            
            subcategories = category.get('sub_categories', [])
            
            # Add product counts
            for subcategory in subcategories:
                subcategory['product_count'] = self.get_subcategory_product_count(
                    category_id, 
                    subcategory['name']
                )
            
            return subcategories
            
        except Exception as e:
            logger.error(f"Error getting subcategories: {e}")
            raise Exception(f"Error getting subcategories: {str(e)}")

    # ================================================================
    # UTILITY AND STATS METHODS
    # ================================================================
    
    def get_active_categories(self, include_deleted=False):
        """Get only active categories"""
        try:
            query = {'status': 'active'}
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            categories = list(self.collection.find(query))
            return categories
        except Exception as e:
            logger.error(f"Error getting active categories: {e}")
            raise Exception(f"Error getting active categories: {str(e)}")

    def search_categories(self, search_term, include_deleted=False, limit=20):
        """Search categories by name or description"""
        try:
            if not search_term or not search_term.strip():
                return []
            
            search_term = search_term.strip()
            regex_pattern = {'$regex': search_term, '$options': 'i'}
            
            query = {
                '$or': [
                    {'category_name': regex_pattern},
                    {'description': regex_pattern}
                ]
            }
            
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            categories = list(self.collection.find(query).limit(limit))
            return categories
        except Exception as e:
            logger.error(f"Error searching categories: {e}")
            raise Exception(f"Error searching categories: {str(e)}")
    
    def get_category_stats(self):
        """Get comprehensive category statistics"""
        try:
            # Get category stats
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total_categories': {'$sum': 1},
                        'active_categories': {
                            '$sum': {
                                '$cond': [
                                    {'$and': [
                                        {'$eq': ['$status', 'active']},
                                        {'$ne': ['$isDeleted', True]}
                                    ]},
                                    1, 0
                                ]
                            }
                        },
                        'deleted_categories': {
                            '$sum': {'$cond': [{'$eq': ['$isDeleted', True]}, 1, 0]}
                        },
                        'total_subcategories': {
                            '$sum': {'$size': {'$ifNull': ['$sub_categories', []]}}
                        }
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            category_stats = result[0] if result else {
                'total_categories': 0,
                'active_categories': 0,
                'deleted_categories': 0,
                'total_subcategories': 0
            }
            
            # Get product stats
            total_products = self.product_collection.count_documents({'isDeleted': {'$ne': True}})
            
            category_stats['total_products'] = total_products
            
            return category_stats
            
        except Exception as e:
            logger.error(f"Error getting category stats: {e}")
            return {
                'total_categories': 0,
                'active_categories': 0,
                'deleted_categories': 0,
                'total_subcategories': 0,
                'total_products': 0
            }

    def get_category_delete_info(self, category_id):
        """Get information about a category before deletion"""
        try:
            if not category_id or not category_id.startswith('CTGY-'):
                return None
            
            category = self.collection.find_one({'_id': category_id})
            if not category:
                return None
            
            # Count subcategories and products
            subcategories_count = len(category.get('sub_categories', []))
            products_count = self.get_category_product_count(category_id)
            
            return {
                'category_id': category['_id'],
                'category_name': category.get('category_name', 'Unknown'),
                'description': category.get('description', ''),
                'status': category.get('status', 'active'),
                'isDeleted': category.get('isDeleted', False),
                'subcategories_count': subcategories_count,
                'products_count': products_count,
                'can_soft_delete': not category.get('isDeleted', False),
                'can_restore': category.get('isDeleted', False),
                'created_at': category.get('date_created'),
                'last_updated': category.get('last_updated'),
                'deleted_at': category.get('deleted_at')
            }
            
        except Exception as e:
            logger.error(f"Error getting category delete info: {e}")
            raise Exception(f"Error getting category delete info: {str(e)}")
    
    def bulk_soft_delete_categories(self, category_ids, current_user=None):
        """Soft delete multiple categories at once"""
        try:
            if not category_ids:
                return {'success': 0, 'failed': 0, 'errors': []}
            
            logger.info(f"Bulk soft deleting {len(category_ids)} categories")
            
            success_count = 0
            failed_count = 0
            errors = []
            
            for category_id in category_ids:
                try:
                    if not category_id.startswith('CTGY-'):
                        failed_count += 1
                        errors.append(f"Invalid category ID: {category_id}")
                        continue
                        
                    result = self.soft_delete_category(category_id, current_user)
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"Failed to soft delete {category_id}")
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Error deleting {category_id}: {str(e)}")
            
            logger.info(f"Bulk delete completed: {success_count} successful, {failed_count} failed")
            
            return {
                'success': success_count,
                'failed': failed_count,
                'errors': errors,
                'total_requested': len(category_ids)
            }
            
        except Exception as e:
            logger.error(f"Error in bulk soft delete: {e}")
            raise Exception(f"Error in bulk soft delete: {str(e)}")

    def bulk_update_categories_status(self, category_ids, new_status, current_user=None):
        """Efficiently update multiple categories status"""
        try:
            if new_status not in ['active', 'inactive']:
                raise ValueError("Status must be 'active' or 'inactive'")
            
            logger.info(f"Bulk updating {len(category_ids)} categories to status: {new_status}")
            
            # Filter valid category IDs
            valid_ids = [cid for cid in category_ids if cid.startswith('CTGY-')]
            
            result = self.collection.update_many(
                {
                    '_id': {'$in': valid_ids},
                    'isDeleted': {'$ne': True}
                },
                {
                    '$set': {
                        'status': new_status,
                        'last_updated': datetime.utcnow()
                    }
                }
            )
            
            # Send bulk notification
            if result.modified_count > 0:
                self._send_category_notification('bulk_updated', f"{result.modified_count} categories", None, {
                    "updated_count": result.modified_count,
                    "new_status": new_status,
                    "action_type": "categories_bulk_status_update",
                    "updated_by": current_user.get('username') if current_user else 'system'
                })
            
            logger.info(f"Updated {result.modified_count} categories to {new_status}")
            return {
                'success': result.modified_count,
                'total_requested': len(category_ids)
            }
            
        except ValueError as ve:
            logger.error(f"Validation error in bulk update: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            raise Exception(f"Bulk update failed: {str(e)}")
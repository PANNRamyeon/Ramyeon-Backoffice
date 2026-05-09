from datetime import datetime
from models.Categories import Category, SubCategoryItem
from models.Product import Product
import logging
import re
import time
from ..core.audit_service import AuditLogService
from notifications.services import notification_service
from app.utils.counters import counter_service

logger = logging.getLogger(__name__)

class CategoryService:
    VALID_CATEGORY_PREFIXES = ('CAT-', 'CTGY-', 'UNCTGRY-', 'UNGTY-')
    UNCATEGORIZED_ID_CANDIDATES = ['UNCTGRY-001', 'UNGTY-001']
    DEFAULT_SUBCATEGORY_NAME = 'None'
    
    # Class-level flag to ensure uncategorized check runs only once
    _uncategorized_checked = False

    _COUNT_MAP_TTL = 60  # seconds

    def __init__(self):
        """Initialize CategoryService using PynamoDB models"""
        self.audit_service = AuditLogService()
        self._count_map_cache = None
        self._count_map_cached_at = 0.0
        # Only check uncategorized once per server lifetime
        if not CategoryService._uncategorized_checked:
            self.ensure_uncategorized_category_exists()
            CategoryService._uncategorized_checked = True

    # ================================================================
    # UTILITY METHODS
    # ================================================================

    def _is_valid_category_id(self, category_id):
        """Allow CTGY-* plus legacy uncategorized IDs"""
        return isinstance(category_id, str)

    def _ensure_subcategory_present(self, category_id, category_doc, subcategory_name):
        """Ensure a subcategory exists for a given category; create if missing."""
        # This logic is now handled by Category model methods
        pass

    def ensure_uncategorized_category_exists(self):
        """Ensure an 'Uncategorized' category exists, create if not"""
        try:
            # Check if uncategorized category already exists
            # Try standard ID first
            uncategorized = Category.get_by_id('UNCTGRY-001')
            if not uncategorized:
                # Try finding by name
                uncategorized = Category.get_by_name('Uncategorized')
            
            if uncategorized:
                # Ensure default subcategory exists
                has_default = False
                for sub in uncategorized.sub_categories:
                    if sub.name == self.DEFAULT_SUBCATEGORY_NAME:
                        has_default = True
                        break
                
                if not has_default:
                    uncategorized.add_subcategory(
                        name=self.DEFAULT_SUBCATEGORY_NAME,
                        description='Default holding subcategory for uncategorized products'
                    )
                
                logger.info("Uncategorized category already exists")
                return uncategorized.to_dict()
            
            # Create default uncategorized category
            # We manually create it to force the ID
            uncategorized = Category(
                pk="category",
                sk="UNCTGRY-001",
                category_name="Uncategorized",
                description="Default category for products without specific categorization",
                status="active",
                isDeleted=False,
                date_created=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            uncategorized.save()
            
            # Add default subcategory
            uncategorized.add_subcategory(
                name=self.DEFAULT_SUBCATEGORY_NAME,
                description="Default holding subcategory for uncategorized products"
            )
            
            logger.info("Created default 'Uncategorized' category with ID: UNCTGRY-001")
            
            # Send notification about system initialization
            self._send_category_notification('created', 'Uncategorized', 'UNCTGRY-001', {
                'system_generated': True,
                'action_type': 'system_initialization'
            })
            
            return uncategorized.to_dict()
            
        except Exception as e:
            logger.error(f"Error ensuring uncategorized category exists: {e}")
            raise Exception(f"Error creating uncategorized category: {str(e)}")

    def _ensure_indexes(self):
        """Indexes are managed by PynamoDB models"""
        pass

    def _validate_category_data(self, category_data):
        """Validate category data before processing"""
        if not category_data:
            raise ValueError("Category data is required")
        
        category_name = (category_data.get("category_name") or "").strip()
        if not category_name:
            raise ValueError("Category name is required")
        
        # Check for duplicates
        existing = Category.get_by_name(category_name)

        if existing and not existing.isDeleted:
            raise ValueError(f"Category '{category_name}' already exists")
        
        # Validate status if provided
        status = category_data.get("status", "active")
        if status not in ['active', 'inactive']:
            raise ValueError("Status must be 'active' or 'inactive'")
        
        return category_name

    def _prepare_subcategories(self, existing_sub_categories):
        """Prepare subcategories with proper sequential IDs"""
        subcategories_list = existing_sub_categories or []
        
        # Check if "None" subcategory already exists
        none_exists = any(
            sub.get('name', '').lower() == self.DEFAULT_SUBCATEGORY_NAME.lower()
            for sub in subcategories_list
        )
        
        # Add default "None" subcategory if it doesn't exist
        if not none_exists:
            none_subcategory = {
                'name': self.DEFAULT_SUBCATEGORY_NAME,
                'description': 'Default holding subcategory for products without specific subcategorization'
            }
            subcategories_list.insert(0, none_subcategory)
        
        if not subcategories_list:
            return []
        
        prepared_subcategories = []
        for i, subcategory in enumerate(subcategories_list):
            # Note: IDs will be generated by Category.add_subcategory or create_category
            # We just pass the data structure for now
            prepared_subcategories.append(subcategory)
        
        return prepared_subcategories
    
    def _send_category_notification(self, action_type, category_name, category_id=None, additional_metadata=None):
        """Centralized notification helper for category actions"""
        try:
            # Define notification templates - UPDATED with missing ones
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
                # MISSING TEMPLATES - ADDED:
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
                'product_added_to_subcategory': {
                    'title': "Product Assigned to Subcategory",
                    'message': f"A product has been assigned to a subcategory in '{category_name}'",
                    'priority': "low"
                },
                'product_removed_from_subcategory': {
                    'title': "Product Removed from Subcategory",
                    'message': f"A product has been removed from a subcategory in '{category_name}'",
                    'priority': "low"
                },
                'product_moved_to_default': {
                    'title': "Product Moved to Default Subcategory",
                    'message': f"A product has been moved to the default subcategory in '{category_name}'",
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
    
    def create_category(self, category_data, current_user=None):
        try:
            category_name = self._validate_category_data(category_data)
            logger.info(f"Creating category: {category_name}")
            
            # Use the model's classmethod to create the category.
            # This correctly uses the counter service we set up in the model.
            category = Category.create_category(
                category_name=category_name,
                description=category_data.get("description"),
                icon=category_data.get("image_url"), # Mapping image_url to icon
                sort_order=category_data.get("sort_order", 0)
            )
            
            # After the category is created, add any subcategories.
            for sub in category_data.get("sub_categories", []):
                # Handle both string format ["Name"] and object format [{"name": "Name"}]
                if isinstance(sub, str):
                    if sub.strip():
                        category.add_subcategory(
                            name=sub.strip(),
                            description=None,
                            status='active',
                            sort_order=0,
                            icon=None
                        )
                elif isinstance(sub, dict) and sub.get('name'):
                    # Use the model's instance method to add subcategories.
                    # This correctly uses the counter service for subcategory IDs.
                    category.add_subcategory(
                        name=sub.get('name'),
                        description=sub.get('description'),
                        status=sub.get('status', 'active'),
                        sort_order=sub.get('sort_order', 0),
                        icon=sub.get('icon')
                    )

            # Always ensure the default "None" subcategory exists
            existing_names = {sc.name for sc in category.sub_categories}
            if self.DEFAULT_SUBCATEGORY_NAME not in existing_names:
                category.add_subcategory(
                    name=self.DEFAULT_SUBCATEGORY_NAME,
                    description='Default subcategory for products without a specific subcategory',
                    status='active',
                    sort_order=0
                )

            category_kwargs = category.to_dict()
            
            # Send notification
            self._send_category_notification('created', category.category_name, category.sk)
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    audit_data = {**category_kwargs, "category_id": category.sk}
                    self.audit_service.log_category_create(current_user, audit_data)
                    logger.debug("Audit log created for category creation")
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            logger.info(f"Category '{category.category_name}' created successfully with ID {category.sk}")
            
            # Return the created data
            return category_kwargs

        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error creating category: {e}", exc_info=True)
            raise Exception(f"Error creating category: {str(e)}")
        
    def _build_product_count_map(self) -> dict:
        """
        Single DynamoDB query for all active products, returning a nested dict
        { category_id: { subcategory_name: count } }.

        Result is cached for _COUNT_MAP_TTL seconds to avoid re-scanning all
        products on every category list request.
        """
        now = time.monotonic()
        if self._count_map_cache is not None and (now - self._count_map_cached_at) < self._COUNT_MAP_TTL:
            return self._count_map_cache

        try:
            condition = (Product.isDeleted == False) & (Product.status == "active")
            products = Product.query("products", filter_condition=condition)
            counts: dict = {}
            for p in products:
                cat = getattr(p, 'category_id', None) or 'unknown'
                sub = getattr(p, 'subcategory_name', None) or 'None'
                if cat not in counts:
                    counts[cat] = {}
                counts[cat][sub] = counts[cat].get(sub, 0) + 1
            self._count_map_cache = counts
            self._count_map_cached_at = now
            return counts
        except Exception as e:
            logger.error(f"Error building product count map: {e}")
            return {}

    def get_all_categories(self, include_deleted=False, limit=None, skip=None, include_product_counts=False):
        """Get all categories. Product counts are read from the stored subcategory field."""
        try:
            categories = Category.get_all_categories(include_deleted=include_deleted)
            if skip:
                categories = categories[skip:]
            if limit:
                categories = categories[:limit]
            # Filter out empty dicts — to_dict() swallows exceptions and returns {}
            # for records it cannot serialize; exclude those from the response.
            return [d for d in (cat.to_dict() for cat in categories) if d]
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            raise Exception(f"Error getting categories: {str(e)}")

    def _adjust_subcategory_count(self, category_id: str, subcategory_name: str, delta: int) -> None:
        """Adjust the stored product_count on a subcategory. Errors are logged and swallowed."""
        Category.adjust_subcategory_count(category_id, subcategory_name, delta)

    def sync_product_counts(self) -> dict:
        """
        One-time repair: recompute product counts from the products table and
        write them back to every subcategory. Call this after the initial deploy
        or whenever counts drift out of sync.
        Also heals any legacy subcategories that are missing a subcategory_id.
        """
        import uuid
        try:
            count_map = self._build_product_count_map()
            categories = Category.get_all_categories(include_deleted=True)
            updated = 0
            for category in categories:
                changed = False
                for sub in category.sub_categories:
                    if not sub.subcategory_id:
                        sub.subcategory_id = f"SUB-{uuid.uuid4().hex[:6].upper()}"
                        changed = True
                    correct = count_map.get(category.sk, {}).get(sub.name, 0)
                    if int(sub.product_count or 0) != correct:
                        sub.product_count = correct
                        changed = True
                if changed:
                    category.last_updated = datetime.utcnow()
                    category.save()
                    updated += 1
            logger.info(f"sync_product_counts: updated {updated} categories")
            return {"updated_categories": updated, "success": True}
        except Exception as e:
            logger.error(f"sync_product_counts failed: {e}")
            return {"success": False, "error": str(e)}

    def get_category_product_count(self, category_id):
        """Get total number of products in a category"""
        try:
            # Use Product model to count
            products = Product.query_by_category(category_id)
            count = len(products)
            return count
        except Exception as e:
            logger.error(f"Error getting category product count: {e}")
            return 0

    def get_subcategory_product_count(self, category_id, subcategory_name):
        """Get number of products in a specific subcategory"""
        try:
            # Use Product model to count
            products = Product.query_by_category(category_id)
            count = 0
            for p in products:
                if p.subcategory_name == subcategory_name:
                    count += 1
            return count
        except Exception as e:
            logger.error(f"Error getting subcategory product count: {e}")
            return 0
    
    def get_category_by_id(self, category_id, include_deleted=False, include_product_counts=True):
        """Get category by string ID, optionally with product counts (defaults to True for detail view)"""
        try:
            category = Category.get_by_id(category_id)
            if not category or (category.isDeleted and not include_deleted):
                return None

            cat_dict = category.to_dict()
            
            # Add product counts for subcategories (default True for detail view)
            if include_product_counts and 'sub_categories' in cat_dict:
                for subcategory in cat_dict['sub_categories']:
                    subcategory['product_count'] = self.get_subcategory_product_count(
                        category.sk,
                        subcategory['name']
                    )
            elif 'sub_categories' in cat_dict:
                for subcategory in cat_dict['sub_categories']:
                    subcategory['product_count'] = None

            return cat_dict
        except Exception as e:
            logger.error(f"Error getting category by ID {category_id}: {e}")
            raise Exception(f"Error getting category: {str(e)}")
        
    def update_category(self, category_id, category_data, current_user=None):
        """Update category with string ID operations"""
        try:
            logger.info(f"Updating category {category_id}")
            if current_user:
                logger.info(f"Updated by: {current_user['username']}")
            
            category = Category.get_by_id(category_id)
            if not category:
                return None
            
            old_data = category.to_dict()
            
            # Prepare update data
            update_kwargs = {}
            if 'category_name' in category_data:
                update_kwargs['category_name'] = category_data['category_name']
            if 'description' in category_data:
                update_kwargs['description'] = category_data['description']
            if 'status' in category_data:
                update_kwargs['status'] = category_data['status']
            if 'image_url' in category_data:
                update_kwargs['icon'] = category_data['image_url']

            # Update basic fields
            category.update_category(**update_kwargs)

            # Sync subcategories if provided
            if 'sub_categories' in category_data:
                submitted = [
                    s for s in (category_data['sub_categories'] or [])
                    if isinstance(s, dict) and s.get('name', '').strip()
                ]
                submitted_names = {s['name'].strip() for s in submitted}

                existing_names = {sc.name for sc in category.sub_categories}
                protected_names = {self.DEFAULT_SUBCATEGORY_NAME}  # never auto-remove "None"

                # Add new subcategories
                for sub in submitted:
                    name = sub['name'].strip()
                    if name not in existing_names:
                        category.add_subcategory(
                            name=name,
                            description=sub.get('description', '').strip() or None,
                        )
                        logger.info(f"Added subcategory '{name}' to category {category_id}")

                # Remove subcategories that were deleted from the form
                for sc in list(category.sub_categories):
                    if sc.name not in submitted_names and sc.name not in protected_names:
                        if category.remove_subcategory(sc.subcategory_id):
                            logger.info(f"Removed subcategory '{sc.name}' from category {category_id}")

            updated_category = category.to_dict()
            
            # Send notification
            self._send_category_notification('updated', category.category_name, category_id)
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_category_update(
                        current_user, category_id, old_data, updated_category
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
        """Soft delete category with string ID operations"""
        try:
            logger.info(f"Soft deleting category {category_id}")
            if current_user:
                logger.info(f"Deleted by: {current_user['username']}")
            
            category = Category.get_by_id(category_id)
            if not category or category.isDeleted:
                return False
            
            category_name = category.category_name
            category_data = category.to_dict()
            
            # Soft delete
            category.soft_delete()
            
            # Send notification
            self._send_category_notification('soft_deleted', category_name, category_id)
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    category_for_audit = category_data.copy()
                    category_for_audit['deletion_type'] = 'soft_delete'

                    self.audit_service.log_category_delete(current_user, category_for_audit)
                    logger.info("Audit log created for category soft deletion")
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error soft deleting category {category_id}: {str(e)}")
            raise Exception(f"Error soft deleting category: {str(e)}")

    def restore_category(self, category_id, current_user=None):
        """Restore a soft-deleted category"""
        try:
            logger.info(f"Restoring category {category_id}")
            if current_user:
                logger.info(f"Restored by: {current_user['username']}")
            
            category = Category.get_by_id(category_id)
            if not category or not category.isDeleted:
                return False
            
            category.restore_category()
            
            # Send notification
            self._send_category_notification('restored', category.category_name, category_id)
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    self.audit_service.log_category_restore(current_user, category.to_dict())
                    logger.info("Audit log created for category restoration")
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error restoring category {category_id}: {str(e)}")
            raise Exception(f"Error restoring category: {str(e)}")

    def hard_delete_category(self, category_id, current_user=None):
        """Permanently delete category (use with extreme caution)"""
        try:
            logger.warning(f"HARD DELETING category {category_id} - THIS IS PERMANENT!")
            if current_user:
                logger.info(f"Deleted by: {current_user['username']}")
            
            category = Category.get_by_id(category_id)
            if not category:
                return False
            
            category_name = category.category_name
            category_data = category.to_dict()
            
            category.delete()
            
            # Send critical notification
            self._send_category_notification('hard_deleted', category_name, category_id, {
                "warning": "PERMANENT_DELETION",
                "deleted_by": current_user.get('username') if current_user else 'system'
            })
            
            # Audit logging
            if current_user and self.audit_service:
                try:
                    category_for_audit = category_data.copy()
                    category_for_audit['deletion_type'] = 'hard_delete'

                    self.audit_service.log_category_delete(current_user, category_for_audit)
                    logger.info("Audit log created for PERMANENT category deletion")
                except Exception as audit_error:
                    logger.error(f"Audit logging failed: {audit_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error permanently deleting category {category_id}: {str(e)}")
            raise Exception(f"Error permanently deleting category: {str(e)}")

    def get_deleted_categories(self, include_product_counts=False):
        """Get all soft-deleted categories, optionally with product counts"""
        try:
            categories = [c for c in Category.get_all_categories(include_deleted=True) if c.isDeleted]

            result = []
            for category in categories:
                cat_dict = category.to_dict()
                if not cat_dict:
                    continue
                if include_product_counts:
                    for subcategory in cat_dict.get('sub_categories', []):
                        subcategory['product_count'] = self.get_subcategory_product_count(
                            category.sk,
                            subcategory['name']
                        )
                else:
                    for subcategory in cat_dict.get('sub_categories', []):
                        subcategory['product_count'] = None
                result.append(cat_dict)

            return result
        except Exception as e:
            logger.error(f"Error getting deleted categories: {e}")
            raise Exception(f"Error getting deleted categories: {str(e)}")
    
   
    def _resolve_product(self, product_identifier):
        """
        Resolve product identifier to get both string ID and name
        Updated to work with PROD-##### string IDs
        """
        try:
            product = None
            
            # Case 1: PROD-##### string ID
            if isinstance(product_identifier, str):
                if product_identifier.startswith('PROD-'):
                    # Direct lookup by string ID
                    product = Product.get_by_id(product_identifier)
                else:
                    # Try as product name (case-insensitive)
                    # Product model doesn't have regex search exposed easily, use scan or search_by_name
                    products = Product.search_by_name(product_identifier.strip(), limit=1)
                    product = products[0] if products else None
            
            # Case 2: Dictionary with product data (from imports)
            elif isinstance(product_identifier, dict):
                if 'product_id' in product_identifier:
                    product_id = product_identifier['product_id']
                    product = Product.get_by_id(product_id)
                elif 'product_name' in product_identifier:
                    products = Product.search_by_name(product_identifier['product_name'], limit=1)
                    product = products[0] if products else None
            
            if not product:
                raise ValueError(f"Product not found: {product_identifier}")
            
            return {
                'id': product.sk,
                'name': product.product_name
            }
            
        except Exception as e:
            raise ValueError(f"Failed to resolve product: {str(e)}")
        
    def add_product_to_subcategory(self, category_id, subcategory_name, product_identifier, current_user=None):
        """Add product to subcategory using string IDs"""
        try:
            logger.info(f"Adding product '{product_identifier}' to subcategory '{subcategory_name}' in category {category_id}")
            
            if not subcategory_name or not subcategory_name.strip():
                raise ValueError("Subcategory name is required")
            
            category = Category.get_by_id(category_id)
            
            if not category:
                raise ValueError("Category not found or deleted")
            
            # Check if subcategory exists
            subcategory_exists = any(
                sub.name == subcategory_name 
                for sub in category.sub_categories
            )
            
            if not subcategory_exists:
                raise ValueError(f"Subcategory '{subcategory_name}' not found in category")
            
            # Resolve product - get both string ID and name
            product_data = self._resolve_product(product_identifier)
            product_id = product_data['id']  # This should be PROD-##### 
            product_name = product_data['name']
            
            # Update product document with category reference
            product = Product.get_by_id(product_id)
            if product:
                product.update_product(
                    category_id=category_id,
                    subcategory_name=subcategory_name
                )
                
            self._send_category_notification(
                'product_added_to_subcategory', category.category_name, category_id,
                {'product_id': product_id, 'product_name': product_name, 'subcategory_name': subcategory_name}
            )
            return {
                'success': True,
                'action': 'added',
                'product_id': product_id,
                'product_name': product_name,
                'category_id': category_id,
                'subcategory_name': subcategory_name,
                'message': f"Product '{product_name}' added to subcategory '{subcategory_name}'"
            }

        except Exception as e:
            logger.error(f"Error adding product to subcategory: {e}")
            raise Exception(f"Error adding product to subcategory: {str(e)}")

    def _remove_product_from_all_subcategories(self, product_id):
        """Remove product from all subcategories using string ID"""
        # No longer needed as products are not stored in categories
        pass

    def remove_product_from_subcategory(self, category_id, subcategory_name, product_identifier, current_user=None):
        """Remove product from subcategory using string IDs"""
        try:
            logger.info(f"Removing product '{product_identifier}' from subcategory '{subcategory_name}' in category {category_id}")
            
            if not subcategory_name or not subcategory_name.strip():
                raise ValueError("Subcategory name is required")
            
            category = Category.get_by_id(category_id)
            
            if not category:
                raise ValueError("Category not found or deleted")
            
            # Resolve product
            product_data = self._resolve_product(product_identifier)
            product_id = product_data['id']
            product_name = product_data['name']
            
            # Update product to remove category reference
            product = Product.get_by_id(product_id)
            if product:
                # Move to Uncategorized instead of removing completely
                product.update_product(
                    category_id="UNCTGRY-001",
                    subcategory_name="General"
                )
                
            self._send_category_notification(
                'product_removed_from_subcategory', category.category_name, category_id,
                {'product_id': product_id, 'product_name': product_name, 'subcategory_name': subcategory_name}
            )
            return {
                'success': True,
                'action': 'removed',
                'product_id': product_id,
                'product_name': product_name,
                'category_id': category_id,
                'subcategory_name': subcategory_name,
                'message': f"Product '{product_name}' removed from subcategory '{subcategory_name}'"
            }

        except Exception as e:
            logger.error(f"Error removing product from subcategory: {e}")
            raise Exception(f"Error removing product from subcategory: {str(e)}")
    
    def get_active_categories(self, include_deleted=False, include_product_counts=False):
        """Get only active categories. Product counts come from the stored subcategory field."""
        try:
            return [d for d in (cat.to_dict() for cat in Category.get_active_categories()) if d]
        except Exception as e:
            logger.error(f"Error getting active categories: {e}")
            raise Exception(f"Error getting active categories: {str(e)}")

    def search_categories(self, search_term, include_deleted=False, limit=20, include_product_counts=False):
        """Search categories by name or description. Product counts come from stored subcategory field."""
        try:
            if not search_term or not search_term.strip():
                return []
            return [d for d in (cat.to_dict() for cat in Category.search_categories(search_term.strip(), limit=limit)) if d]
        except Exception as e:
            logger.error(f"Error searching categories: {e}")
            raise Exception(f"Error searching categories: {str(e)}")
    
    def add_subcategory(self, category_id, subcategory_data, current_user=None):
        """Add a subcategory to a category by delegating to the model."""
        try:
            logger.info(f"Adding subcategory to category {category_id}")
            if current_user:
                logger.info(f"Added by: {current_user['username']}")
            
            category = Category.get_by_id(category_id)
            if not category:
                raise ValueError("Category not found or is deleted")

            # Use the model's instance method directly
            category.add_subcategory(
                name=subcategory_data.get('name'),
                description=subcategory_data.get('description'),
                icon=subcategory_data.get('icon'),
                sort_order=subcategory_data.get('sort_order', 0),
                status=subcategory_data.get('status', 'active')
            )
            
            # Send notification
            self._send_category_notification('subcategory_added', category.category_name, category_id, {
                "subcategory_name": subcategory_data.get('name', 'Unknown'),
                "action_type": "subcategory_added"
            })
            
            return True
            
        except ValueError as ve:
            logger.error(f"Validation error adding subcategory: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error adding subcategory: {e}", exc_info=True)
            raise Exception(f"Error adding subcategory: {str(e)}")

    def remove_subcategory(self, category_id, subcategory_name, current_user=None):
        """Remove a subcategory from a category by its name."""
        try:
            logger.info(f"Removing subcategory '{subcategory_name}' from category {category_id}")
            
            category = Category.get_by_id(category_id)
            if not category:
                raise ValueError("Category not found or is deleted")
            
            # Find the subcategory by name to get its ID for removal
            sub_to_remove = next((sub for sub in category.sub_categories if sub.name == subcategory_name), None)
            
            if sub_to_remove:
                # Use the model's remove method with the found ID
                if category.remove_subcategory(sub_to_remove.subcategory_id):
                    self._send_category_notification('subcategory_removed', category.category_name, category_id, {
                        "subcategory_name": subcategory_name,
                        "action_type": "subcategory_removed"
                    })
                    return True
            
            logger.warning(f"Subcategory '{subcategory_name}' not found in category '{category.category_name}'.")
            return False
            
        except ValueError as ve:
            logger.error(f"Validation error removing subcategory: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error removing subcategory: {e}", exc_info=True)
            raise Exception(f"Error removing subcategory: {str(e)}")

    def get_subcategories(self, category_id):
        """Get all subcategories for a specific category"""
        try:
            category = Category.get_by_id(category_id)
            if not category:
                return []
            
            return [
                {'name': sub.name, 'description': sub.description, 'subcategory_id': sub.subcategory_id} 
                for sub in category.sub_categories
            ]
            
        except Exception as e:
            logger.error(f"Error getting subcategories: {e}")
            raise Exception(f"Error getting subcategories: {str(e)}")

    def get_subcategory_products_with_details(self, category_id, subcategory_name):
        """Get products in subcategory with full product details (ID + Name format)"""
        try:
            # Use Product model to query
            products = Product.query_by_category(category_id)
            return [
                {
                    'product_id': p.sk,
                    'product_name': p.product_name
                }
                for p in products if p.subcategory_name == subcategory_name
            ]
            
        except Exception as e:
            logger.error(f"Error getting subcategory products: {e}")
            raise Exception(f"Error getting subcategory products: {str(e)}")
    
    def get_category_stats(self):
        """Get comprehensive category statistics"""
        try:
            from models.Categories import CategoryManager
            return CategoryManager.get_category_statistics()
            
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
            category = Category.get_by_id(category_id)
            if not category:
                return None
            
            # Count subcategories and products
            subcategories_count = len(category.sub_categories)
            products_count = self.get_category_product_count(category_id)
            
            return {
                'category_id': category.sk,
                'category_name': category.category_name,
                'description': category.description,
                'status': category.status,
                'isDeleted': category.isDeleted,
                'subcategories_count': subcategories_count,
                'products_count': products_count,
                'can_soft_delete': not category.isDeleted,
                'can_restore': category.isDeleted,
                'created_at': category.date_created,
                'last_updated': category.last_updated
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
            
            updated_count = 0
            for category_id in category_ids:
                logger.info(f"Attempting to update category: {category_id}")
                category = Category.get_by_id(category_id)
                if category:
                    logger.info(f"Category found: {category.category_name}, isDeleted: {category.isDeleted}")
                    if not category.isDeleted:
                        category.status = new_status
                        category.save()
                        updated_count += 1
                        logger.info(f"Successfully updated category {category_id} to {new_status}")
                    else:
                        logger.warning(f"Category {category_id} is deleted, skipping")
                else:
                    logger.warning(f"Category {category_id} not found")
            
            # Send bulk notification
            if updated_count > 0:
                self._send_category_notification('bulk_updated', f"{updated_count} categories", None, {
                    "updated_count": updated_count,
                    "new_status": new_status,
                    "action_type": "categories_bulk_status_update",
                    "updated_by": current_user.get('username') if current_user else 'system'
                })
            
            logger.info(f"Updated {updated_count} categories to {new_status}")
            return {
                'success': updated_count,
                'total_requested': len(category_ids)
            }
            
        except ValueError as ve:
            logger.error(f"Validation error in bulk update: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            raise Exception(f"Bulk update failed: {str(e)}")
    
    def _get_subcategory_product_ids(self, category_id, subcategory_name):
        """Get all product IDs in a specific subcategory (string format only)"""
        # Use Product model
        products = Product.query_by_category(category_id)
        return [p.sk for p in products if p.subcategory_name == subcategory_name]

    def move_product_to_none_subcategory(self, product_id, category_id, current_user=None):
        """Move product to the default catch-all subcategory within the same category"""
        try:
            logger.info(f"Moving product {product_id} to '{self.DEFAULT_SUBCATEGORY_NAME}' subcategory in category {category_id}")
            
            product = Product.get_by_id(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")
            
            product.update_product(
                category_id=category_id,
                subcategory_name=self.DEFAULT_SUBCATEGORY_NAME
            )
            self._send_category_notification(
                'product_moved_to_default', category_id, category_id,
                {'product_id': product_id, 'product_name': product.product_name,
                 'subcategory_name': self.DEFAULT_SUBCATEGORY_NAME}
            )
            return {
                'success': True,
                'action': 'moved_to_default',
                'message': f"Product '{product.product_name}' moved to '{self.DEFAULT_SUBCATEGORY_NAME}' subcategory"
            }

        except Exception as e:
            logger.error(f"Error moving product to None subcategory: {e}")
            raise Exception(f"Error moving product to None subcategory: {str(e)}")
        
    def get_products_in_subcategory(self, category_id, subcategory_name, include_deleted=False):
        """Get all products in a specific subcategory"""
        try:
            # Use Product model
            products = Product.query_by_category(category_id)
            return [p.to_dict() for p in products if p.subcategory_name == subcategory_name]
            
        except Exception as e:
            logger.error(f"Error getting products in subcategory: {e}")
            raise Exception(f"Error getting products in subcategory: {str(e)}")
        
    def move_product_to_category(self, product_id, new_category_id, new_subcategory_name=None, current_user=None):
        """Move a product to a different category/subcategory using ProductService"""
        try:
            # If no subcategory specified, use default catch-all subcategory
            if not new_subcategory_name:
                new_subcategory_name = self.DEFAULT_SUBCATEGORY_NAME

            product = Product.get_by_id(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")

            old_category_id = product.category_id
            old_subcategory_name = product.subcategory_name

            product.update_product(
                category_id=new_category_id,
                subcategory_name=new_subcategory_name
            )

            if old_category_id != new_category_id or old_subcategory_name != new_subcategory_name:
                self._adjust_subcategory_count(old_category_id, old_subcategory_name, -1)
                self._adjust_subcategory_count(new_category_id, new_subcategory_name, +1)

            logger.info(f"Product {product_id} moved to category {new_category_id} > {new_subcategory_name}")
            return product.to_dict()
            
        except Exception as e:
            logger.error(f"Error moving product to category: {e}")
            raise Exception(f"Error moving product to category: {str(e)}")
    
    def bulk_move_products_to_category(self, product_ids, new_category_id, new_subcategory_name=None, current_user=None):
        """Bulk move multiple products to a different category/subcategory"""
        try:
            logger.info(f"Bulk moving {len(product_ids)} products to category {new_category_id}")
            
            # If no subcategory specified, use default catch-all subcategory
            if not new_subcategory_name:
                new_subcategory_name = self.DEFAULT_SUBCATEGORY_NAME
            
            moved_count = 0
            for pid in product_ids:
                product = Product.get_by_id(pid)
                if product:
                    product.update_product(
                        category_id=new_category_id,
                        subcategory_name=new_subcategory_name
                    )
                    moved_count += 1
            
            if moved_count > 0:
                logger.info(f"Bulk moved {moved_count} products to category {new_category_id} > {new_subcategory_name}")
                
                # Audit logging
                if current_user and self.audit_service:
                    try:
                        self.audit_service.log_action(
                            current_user,
                            'bulk_move',
                            resource_type='products',
                            resource_id=f"{moved_count}_products",
                            changes={
                                'target_category': new_category_id,
                                'target_subcategory': new_subcategory_name,
                                'products_moved': moved_count,
                                'product_ids': product_ids
                            }
                        )
                    except Exception as audit_error:
                        logger.warning(f"Audit logging failed for bulk move: {audit_error}")
            
            return moved_count
            
        except Exception as e:
            logger.error(f"Error bulk moving products to category: {e}")
            raise Exception(f"Error bulk moving products to category: {str(e)}")
            
    
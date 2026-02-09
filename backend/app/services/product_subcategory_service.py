from datetime import datetime
from ..database import db_manager
import logging
import re
from .audit_service import AuditLogService

logger = logging.getLogger(__name__)

class ProductSubcategoryService:
    UNCATEGORIZED_CATEGORY_NAME = "Uncategorized"
    UNCATEGORIZED_SUBCATEGORY_NAME = "General" 
    NONE_SUBCATEGORY_NAME = "None" 
    
    def __init__(self):
        self.db = db_manager.get_database()
        self.category_collection = self.db.category
        self.product_collection = self.db.products
        
        try:
            self.audit_service = AuditLogService()
            logger.info("Audit service initialized for ProductSubcategoryService")
        except Exception as e:
            logger.warning(f"Could not initialize audit service: {e}")
            self.audit_service = None

    def update_product_subcategory(self, product_id, new_subcategory, category_id, current_user=None):
        """Update product subcategory with validation and audit logging"""
        try:
            logger.info(f"Updating product {product_id} subcategory to '{new_subcategory}' in category {category_id}")
            
            if not product_id or not product_id.startswith('PROD-'):
                raise ValueError("Invalid product ID - must be PROD-##### format")
            
            if not category_id or not category_id.startswith('CTGY-'):
                raise ValueError("Invalid category ID - must be CTGY-### format")
            
            # Get product details
            product = self.product_collection.find_one({'product_id': product_id})
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")
            
            product_name = product.get('product_name')
            if not product_name:
                raise ValueError(f"Product {product_id} has no product_name")
            
            # Get target category
            target_category = self.category_collection.find_one({
                'category_id': category_id,
                'isDeleted': {'$ne': True}
            })
            
            if not target_category:
                raise ValueError("Target category not found or is deleted")
            
            # Find current category assignment
            current_category = self.category_collection.find_one({
                'sub_categories.products.product_id': product_id,
                'isDeleted': {'$ne': True}
            })
            
            current_subcategory = None
            if current_category:
                for subcategory in current_category.get('sub_categories', []):
                    products = subcategory.get('products', [])
                    if products and isinstance(products[0], dict):
                        if any(p.get('product_id') == product_id for p in products):
                            current_subcategory = subcategory['name']
                            break
            
            # Handle empty/null subcategory (move to uncategorized)
            if not new_subcategory or new_subcategory.strip() == '':
                return self._move_to_uncategorized_category(
                    product_id, product_name, current_category, current_subcategory
                )
            
            # Move to specified subcategory
            return self._move_product_to_subcategory(
                product_id, product_name, target_category, new_subcategory,
                current_category, current_subcategory, current_user
            )
                
        except ValueError as ve:
            logger.error(f"Validation error updating product subcategory: {ve}")
            raise Exception(f"Validation error: {str(ve)}")
        except Exception as e:
            logger.error(f"Error updating product subcategory: {e}", exc_info=True)
            raise Exception(f"Error updating product subcategory: {str(e)}")

    def _move_product_to_subcategory(self, product_id, product_name, target_category, new_subcategory, current_category, current_subcategory, current_user=None):
        """Move product to a specific subcategory with validation"""
        try:
            target_subcategory_exists = any(
                sub['name'] == new_subcategory 
                for sub in target_category.get('sub_categories', [])
            )
            
            if not target_subcategory_exists:
                raise ValueError(f"Subcategory '{new_subcategory}' does not exist in category '{target_category.get('category_name')}'")
            
            # Check if already in target location
            if (current_category and 
                current_category.get('category_id') == target_category.get('category_id') and 
                current_subcategory == new_subcategory):
                return {
                    'success': True,
                    'action': 'no_change',
                    'message': f"Product is already in {target_category.get('category_name')} > {new_subcategory}"
                }
            
            # Remove from current location
            if current_category and current_subcategory:
                self.category_collection.update_one(
                    {'category_id': current_category['category_id']},
                    {'$pull': {'sub_categories.$[elem].products': {'product_id': product_id}}},
                    array_filters=[{'elem.name': current_subcategory}]
                )
            
            # Add to new location with both ID and Name
            result = self.category_collection.update_one(
                {'category_id': target_category['category_id']},
                {
                    '$addToSet': {
                        'sub_categories.$[elem].products': {
                            'product_id': product_id,      # String ID
                            'product_name': product_name   # Product name
                        }
                    },
                    '$set': {'last_updated': datetime.utcnow()}
                },
                array_filters=[{'elem.name': new_subcategory}]
            )
            
            if result.modified_count > 0:
                # Update product document with category reference
                self.product_collection.update_one(
                    {'product_id': product_id},
                    {
                        '$set': {
                            'category_id': target_category['category_id'],
                            'subcategory_name': new_subcategory,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                logger.info(f"Moved product to {target_category.get('category_name')} > {new_subcategory}")
                
                return {
                    'success': True,
                    'action': 'moved_subcategory',
                    'old_category': current_category.get('category_name') if current_category else None,
                    'old_subcategory': current_subcategory,
                    'new_category': target_category.get('category_name'),
                    'new_subcategory': new_subcategory,
                    'message': f"Product moved to {target_category.get('category_name')} > {new_subcategory}"
                }
            
            return {'success': False, 'message': 'Failed to add product to new subcategory'}
                
        except Exception as e:
            raise Exception(f"Error moving product to subcategory: {str(e)}")

    def _move_to_uncategorized_category(self, product_id, product_name, current_category=None, current_subcategory=None):
        """Move product to uncategorized category"""
        try:
            logger.info(f"Moving {product_name} to Uncategorized category")
            
            uncategorized_category = self._ensure_uncategorized_category_exists()
            
            # Remove from current category
            if current_category and current_subcategory:
                self.category_collection.update_one(
                    {'category_id': current_category['category_id']},
                    {'$pull': {'sub_categories.$[elem].products': {'product_id': product_id}}},
                    array_filters=[{'elem.name': current_subcategory}]
                )
            
            # Add to uncategorized with both ID and Name
            result = self.category_collection.update_one(
                {'category_id': uncategorized_category['category_id']},
                {
                    '$addToSet': {
                        'sub_categories.$[elem].products': {
                            'product_id': product_id,      # String ID
                            'product_name': product_name   # Product name
                        }
                    },
                    '$set': {'last_updated': datetime.utcnow()}
                },
                array_filters=[{'elem.name': self.UNCATEGORIZED_SUBCATEGORY_NAME}]
            )
            
            if result.modified_count > 0:
                self.product_collection.update_one(
                    {'product_id': product_id},
                    {
                        '$set': {
                            'category_id': uncategorized_category['category_id'],
                            'subcategory_name': self.UNCATEGORIZED_SUBCATEGORY_NAME,
                            'updated_at': datetime.utcnow(),
                            'is_uncategorized': True
                        }
                    }
                )
                
                return {
                    'success': True,
                    'action': 'moved_to_uncategorized',
                    'message': f"Product moved to {self.UNCATEGORIZED_CATEGORY_NAME} category"
                }
            
            return {'success': False, 'message': 'Failed to move product to uncategorized category'}
                
        except Exception as e:
            raise Exception(f"Error moving to uncategorized category: {str(e)}")

    def _ensure_uncategorized_category_exists(self):
        """Ensure uncategorized category exists"""
        try:
            # Check if exists
            uncategorized_category = self.category_collection.find_one({
                'category_name': self.UNCATEGORIZED_CATEGORY_NAME,
                'isDeleted': {'$ne': True}
            })
            
            if uncategorized_category:
                return uncategorized_category
            
            # Create if doesn't exist
            from ..models import Category
            from .category_service import CategoryService
            
            category_service = CategoryService()
            category_id = category_service.generate_category_id()
            
            uncategorized_data = {
                'category_id': category_id,
                'category_name': self.UNCATEGORIZED_CATEGORY_NAME,
                'description': 'Auto-generated category for products without specific categorization',
                'status': 'active',
                'sub_categories': [{
                    'name': self.UNCATEGORIZED_SUBCATEGORY_NAME,
                    'description': 'General uncategorized products',
                    'products': [],
                    'created_at': datetime.utcnow()
                }],
                'isDeleted': False,
                'is_system_category': True,
                'auto_created': True,
                'date_created': datetime.utcnow(),
                'last_updated': datetime.utcnow()
            }
            
            category = Category(**uncategorized_data)
            result = self.category_collection.insert_one(category.to_dict())
            
            created_category = self.category_collection.find_one({'category_id': category_id})
            logger.info(f"Created uncategorized category: {category_id}")
            
            return created_category
            
        except Exception as e:
            raise Exception(f"Error ensuring uncategorized category exists: {str(e)}")

    def move_product_to_uncategorized_category(self, product_id, current_category_id=None):
        """Public method to move a product to Uncategorized category"""
        try:
            logger.info(f"Moving product {product_id} to Uncategorized category")
            
            if not product_id.startswith('PROD-'):
                raise ValueError("Invalid product ID - must be PROD-##### format")
            
            product = self.product_collection.find_one({'product_id': product_id})
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")
            
            product_name = product.get('product_name')
            if not product_name:
                raise ValueError(f"Product {product_id} has no product_name")
            
            # Find current category
            current_category = None
            current_subcategory = None
            
            if current_category_id and current_category_id.startswith('CTGY-'):
                current_category = self.category_collection.find_one({
                    'category_id': current_category_id,
                    'isDeleted': {'$ne': True}
                })
            else:
                current_category = self.category_collection.find_one({
                    'sub_categories.products.product_id': product_id,
                    'isDeleted': {'$ne': True}
                })
            
            if current_category:
                for subcategory in current_category.get('sub_categories', []):
                    products = subcategory.get('products', [])
                    if products and isinstance(products[0], dict):
                        if any(p.get('product_id') == product_id for p in products):
                            current_subcategory = subcategory['name']
                            break
            
            result = self._move_to_uncategorized_category(
                product_id, 
                product_name, 
                current_category, 
                current_subcategory
            )
            
            return {
                'success': result.get('success', False),
                'action': 'moved_to_uncategorized',
                'product_id': product_id,
                'previous_category_id': current_category_id,
                'new_category_id': self._get_uncategorized_category_id(),
                'message': result.get('message', 'Product moved to Uncategorized category'),
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error in move_product_to_uncategorized_category: {e}")
            return {
                'success': False,
                'error': str(e),
                'product_id': product_id
            }
    
    def bulk_move_products_to_uncategorized(self, product_ids, current_category_id=None):
        """Bulk move products to Uncategorized category"""
        try:
            logger.info(f"Bulk moving {len(product_ids)} products to Uncategorized")
            
            if not product_ids or not isinstance(product_ids, list):
                raise ValueError("product_ids must be a non-empty list")
            
            results = []
            successful = 0
            failed = 0
            
            for product_id in product_ids:
                try:
                    result = self.move_product_to_uncategorized_category(
                        product_id=product_id,
                        current_category_id=current_category_id
                    )
                    
                    if result.get('success'):
                        successful += 1
                    else:
                        failed += 1
                        
                    results.append(result)
                    
                    # Small delay to prevent overwhelming the database
                    import time
                    time.sleep(0.01)  # 10ms delay
                    
                except Exception as e:
                    failed += 1
                    results.append({
                        'success': False,
                        'error': str(e),
                        'product_id': product_id
                    })
            
            return {
                'success': successful > 0,
                'message': f'Bulk move completed: {successful} successful, {failed} failed',
                'successful': successful,
                'failed': failed,
                'results': results,
                'total_requested': len(product_ids)
            }
            
        except Exception as e:
            logger.error(f"Error in bulk_move_products_to_uncategorized: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Bulk move to uncategorized failed'
            }

    def _get_uncategorized_category_id(self):
        """Helper method to get the uncategorized category ID"""
        try:
            uncategorized_category = self.category_collection.find_one({
                'category_name': self.UNCATEGORIZED_CATEGORY_NAME,
                'isDeleted': {'$ne': True}
            })
            
            if uncategorized_category:
                return uncategorized_category['category_id']
            
            # If not found, create it and return ID
            created_category = self._ensure_uncategorized_category_exists()
            return created_category['category_id']
            
        except Exception as e:
            logger.error(f"Error getting uncategorized category ID: {e}")
            return None

    def validate_subcategory_update(self, product_id, new_subcategory, category_id):
        """Validate subcategory update before performing it"""
        try:
            # Check product exists
            if not product_id.startswith('PROD-'):
                return {'is_valid': False, 'error': 'Invalid product ID - must be PROD-##### format'}
            
            product = self.product_collection.find_one({'product_id': product_id})
            if not product:
                return {'is_valid': False, 'error': f'Product with ID {product_id} not found'}
            
            # Check category exists
            if not category_id.startswith('CTGY-'):
                return {'is_valid': False, 'error': 'Invalid category ID - must be CTGY-### format'}
            
            category = self.category_collection.find_one({
                'category_id': category_id,
                'isDeleted': {'$ne': True}
            })
            
            if not category:
                return {'is_valid': False, 'error': 'Category not found or is deleted'}
            
            # If empty subcategory, valid (move to uncategorized)
            if not new_subcategory or new_subcategory.strip() == '':
                return {
                    'is_valid': True,
                    'action': 'move_to_uncategorized',
                    'warning': 'Product will be moved to Uncategorized category'
                }
            
            # Check if subcategory exists
            subcategory_exists = any(
                sub['name'] == new_subcategory 
                for sub in category.get('sub_categories', [])
            )
            
            if not subcategory_exists:
                return {
                    'is_valid': False,
                    'error': f'Subcategory "{new_subcategory}" does not exist in category {category.get("category_name")}'
                }
            
            return {
                'is_valid': True,
                'action': 'move_to_subcategory',
                'target_category': category.get('category_name'),
                'target_subcategory': new_subcategory
            }
            
        except Exception as e:
            return {'is_valid': False, 'error': f'Validation error: {str(e)}'}
        
    def handle_product_removal_workflow(self, product_id, removal_type="move_to_none", target_category_id=None, current_user=None):
        """
        Handle product removal with proper workflow:
        1. Remove from specific subcategory → Move to 'None' subcategory
        2. From 'None' → Move to 'Uncategorized' category 
        3. From 'Uncategorized' → Transfer to another category
        """
        try:
            if removal_type == "move_to_none" and target_category_id:
                # Step 1: Move to None subcategory within same category
                from .category_service import CategoryService
                category_service = CategoryService()
                return category_service.move_product_to_none_subcategory(
                    product_id, target_category_id, current_user
                )
                
            elif removal_type == "move_to_uncategorized":
                # Step 2: Move to Uncategorized category
                return self.move_product_to_uncategorized_category(product_id)
                
            elif removal_type == "transfer_category":
                # Step 3: Transfer to another category (handled by update_product_subcategory)
                raise ValueError("Use update_product_subcategory for category transfers")
                
            else:
                raise ValueError("Invalid removal_type. Use: move_to_none, move_to_uncategorized")
                
        except Exception as e:
            logger.error(f"Error in product removal workflow: {e}")
            raise Exception(f"Product removal workflow failed: {str(e)}")
from datetime import datetime
from ..database import db_manager
import logging

logger = logging.getLogger(__name__)

class POSCategoryService:
    """Lightweight service optimized specifically for POS operations"""
    
    def __init__(self):
        self.db = db_manager.get_database()
        self.category_collection = self.db.category
        self.product_collection = self.db.products
        self._ensure_pos_indexes()

    def _ensure_pos_indexes(self):
        """Create indexes specifically optimized for POS operations"""
        try:
            # Essential POS indexes for string IDs
            pos_indexes = [
                # For category catalog loading
                [("status", 1), ("isDeleted", 1)],
                [("category_name", 1)],
                [("category_id", 1)],  # String-based category ID index
                
                # For subcategory product lookups
                [("sub_categories.products.product_id", 1)],
                [("sub_categories.name", 1)]
            ]
            
            for index_fields in pos_indexes:
                self.category_collection.create_index(index_fields, background=True)
            
            # Product collection indexes for string IDs
            product_indexes = [
                [("product_id", 1)],  # String-based product ID
                [("product_name", 1)],
                [("stock_quantity", 1)],
                [("barcode", 1)],
                [("product_code", 1)]
            ]
            
            for index_fields in product_indexes:
                self.product_collection.create_index(index_fields, background=True)
                
            logger.info("POS indexes created successfully")
        except Exception as e:
            logger.warning(f"Could not create POS indexes: {e}")

    def get_pos_catalog_structure(self):
        """
        Get lightweight catalog structure for POS display
        Returns active categories with subcategories and basic product info
        """
        try:
            categories = list(self.category_collection.find(
                {
                    "status": "active",
                    "isDeleted": {"$ne": True}
                },
                {
                    "category_id": 1,  # String ID
                    "category_name": 1,
                    "sub_categories.name": 1,
                    "sub_categories.products.product_id": 1,  # String product ID
                    "sub_categories.products.product_name": 1
                }
            ).sort("category_name", 1))
            
            return categories
            
        except Exception as e:
            logger.error(f"POS catalog structure failed: {e}")
            raise Exception(f"Failed to get POS catalog: {str(e)}")

    def get_products_for_pos_cart(self, product_ids):
        """
        Batch fetch multiple products for POS cart operations
        Optimized for speed with only essential cart fields
        """
        try:
            if not product_ids or not isinstance(product_ids, list):
                raise ValueError("product_ids must be a non-empty list")
            
            # Validate string product IDs
            valid_ids = []
            for pid in product_ids:
                if isinstance(pid, str) and pid.startswith('PROD-'):
                    valid_ids.append(pid)
                else:
                    logger.warning(f"Invalid product ID skipped: {pid}")
            
            if not valid_ids:
                raise ValueError("No valid PROD-##### product IDs provided")
            
            # Single batch query with only essential POS fields
            products = list(self.product_collection.find(
                {'product_id': {'$in': valid_ids}},  # String-based lookup
                {
                    'product_id': 1,  # String ID
                    'product_name': 1,
                    'unit_price': 1,
                    'stock_quantity': 1,
                    'product_code': 1,
                    'barcode': 1,
                    'tax_rate': 1,
                    'category_id': 1,  # String category ID
                    'subcategory_name': 1
                }
            ))
            
            return products
            
        except Exception as e:
            logger.error(f"POS batch product fetch failed: {e}")
            raise Exception(f"Failed to get products for cart: {str(e)}")

    def get_products_by_subcategory_for_pos(self, category_id, subcategory_name):
        """
        Get all products in a subcategory for bulk selection
        Useful when user wants to add entire subcategory to cart
        """
        try:
            if not category_id or not category_id.startswith('CTGY-'):
                raise ValueError("Invalid category ID - must be CTGY-### format")
            
            # Get the subcategory's product IDs using string-based lookup
            category = self.category_collection.find_one(
                {
                    'category_id': category_id,  # String ID
                    'status': 'active',
                    'isDeleted': {'$ne': True}
                },
                {'sub_categories': 1}
            )
            
            if not category:
                return []
            
            # Find the specific subcategory and extract product IDs
            product_ids = []
            for subcategory in category.get('sub_categories', []):
                if subcategory['name'] == subcategory_name:
                    products = subcategory.get('products', [])
                    # Handle combined format (product_id + product_name)
                    if products and isinstance(products[0], dict):
                        product_ids = [p['product_id'] for p in products]  # String IDs
                    break
            
            if not product_ids:
                return []
            
            # Batch fetch all products in this subcategory
            return self.get_products_for_pos_cart(product_ids)
            
        except Exception as e:
            logger.error(f"POS subcategory products fetch failed: {e}")
            raise Exception(f"Failed to get subcategory products: {str(e)}")

    def get_product_by_barcode_for_pos(self, barcode):
        """
        Quick product lookup by barcode for POS scanner integration
        """
        try:
            if not barcode or not barcode.strip():
                raise ValueError("Barcode is required")
            
            product = self.product_collection.find_one(
                {'barcode': barcode.strip()},
                {
                    'product_id': 1,  # String ID
                    'product_name': 1,
                    'unit_price': 1,
                    'stock_quantity': 1,
                    'product_code': 1,
                    'barcode': 1,
                    'tax_rate': 1,
                    'category_id': 1,  # String category ID
                    'subcategory_name': 1
                }
            )
            
            return product
            
        except Exception as e:
            logger.error(f"POS barcode lookup failed: {e}")
            raise Exception(f"Failed to get product by barcode: {str(e)}")

    def search_products_for_pos(self, search_term, limit=20):
        """
        Quick product search for POS - by name or product code
        """
        try:
            if not search_term or not search_term.strip():
                return []
            
            search_term = search_term.strip()
            regex_pattern = {'$regex': search_term, '$options': 'i'}
            
            products = list(self.product_collection.find(
                {
                    '$or': [
                        {'product_name': regex_pattern},
                        {'product_code': regex_pattern}
                    ]
                },
                {
                    'product_id': 1,  # String ID
                    'product_name': 1,
                    'unit_price': 1,
                    'stock_quantity': 1,
                    'product_code': 1,
                    'barcode': 1
                }
            ).limit(limit))
            
            return products
            
        except Exception as e:
            logger.error(f"POS product search failed: {e}")
            raise Exception(f"Failed to search products: {str(e)}")

    def check_product_stock_for_pos(self, product_id, requested_quantity):
        """
        Quick stock check for POS before adding to cart
        """
        try:
            if not product_id or not product_id.startswith('PROD-'):
                return {'available': False, 'error': 'Invalid product ID - must be PROD-##### format'}
            
            product = self.product_collection.find_one(
                {'product_id': product_id},  # String-based lookup
                {'stock_quantity': 1, 'product_name': 1}
            )
            
            if not product:
                return {'available': False, 'error': 'Product not found'}
            
            current_stock = product.get('stock_quantity', 0)
            
            return {
                'available': current_stock >= requested_quantity,
                'current_stock': current_stock,
                'requested_quantity': requested_quantity,
                'product_name': product.get('product_name', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"POS stock check failed: {e}")
            return {'available': False, 'error': str(e)}

    def get_low_stock_products_for_pos(self, threshold=10):
        """
        Get products with low stock for POS alerts
        """
        try:
            products = list(self.product_collection.find(
                {'stock_quantity': {'$lte': threshold}},
                {
                    'product_id': 1,  # String ID
                    'product_name': 1,
                    'stock_quantity': 1,
                    'product_code': 1
                }
            ).sort('stock_quantity', 1).limit(50))
            
            return products
            
        except Exception as e:
            logger.error(f"POS low stock check failed: {e}")
            raise Exception(f"Failed to get low stock products: {str(e)}")

    def get_category_products_for_pos_display(self, category_id):
        """
        Get all products in a category organized by subcategory for POS display
        """
        try:
            if not category_id or not category_id.startswith('CTGY-'):
                raise ValueError("Invalid category ID - must be CTGY-### format")
            
            category = self.category_collection.find_one(
                {
                    'category_id': category_id,  # String ID
                    'status': 'active',
                    'isDeleted': {'$ne': True}
                }
            )
            
            if not category:
                return {
                    'category_id': category_id,
                    'category_name': 'Unknown',
                    'subcategories': []
                }
            
            subcategories_data = []
            
            for subcategory in category.get('sub_categories', []):
                products_data = []
                products = subcategory.get('products', [])
                
                # Get product IDs from combined format
                if products and isinstance(products[0], dict):
                    product_ids = [p['product_id'] for p in products]  # String IDs
                    
                    # Fetch full product details for POS
                    full_products = self.get_products_for_pos_cart(product_ids)
                    products_data = full_products
                
                subcategories_data.append({
                    'name': subcategory['name'],
                    'description': subcategory.get('description', ''),
                    'product_count': len(products_data),
                    'products': products_data
                })
            
            return {
                'category_id': category['category_id'],
                'category_name': category['category_name'],
                'description': category.get('description', ''),
                'subcategories': subcategories_data
            }
            
        except Exception as e:
            logger.error(f"POS category products display failed: {e}")
            raise Exception(f"Failed to get category products for POS: {str(e)}")

    def get_pos_quick_access_products(self, limit=20):
        """
        Get frequently sold or featured products for quick access in POS
        """
        try:
            # For now, return products with high stock or featured status
            # Could be enhanced with sales frequency data later
            products = list(self.product_collection.find(
                {
                    'stock_quantity': {'$gt': 0},  # Only in-stock items
                    '$or': [
                        {'is_featured': True},
                        {'stock_quantity': {'$gte': 50}}  # High stock items
                    ]
                },
                {
                    'product_id': 1,  # String ID
                    'product_name': 1,
                    'unit_price': 1,
                    'stock_quantity': 1,
                    'product_code': 1,
                    'barcode': 1,
                    'category_id': 1,  # String category ID
                    'subcategory_name': 1
                }
            ).limit(limit))
            
            return products
            
        except Exception as e:
            logger.error(f"POS quick access products failed: {e}")
            raise Exception(f"Failed to get quick access products: {str(e)}")
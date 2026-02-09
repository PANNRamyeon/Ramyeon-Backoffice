import re 
from datetime import datetime
from ..database import db_manager
from ..models import Product
from notifications.services import notification_service
from .batch_service import BatchService
import pandas as pd
import logging
import csv
from io import StringIO

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self):
        self.db = db_manager.get_database()
        self.product_collection = self.db.products
        self.category_collection = self.db.category
        self.supplier_collection = self.db.suppliers
        self.branch_collection = self.db.branches
        self.batch_service = BatchService()
        
    def validate_foreign_keys(self, product_data):
        """Validate that foreign key references exist - using string IDs"""
        # Validate category_id (string-based lookup)
        if 'category_id' in product_data and product_data['category_id']:
            category = self.category_collection.find_one({'_id': product_data['category_id']})
            if not category:
                raise ValueError(f"Category with ID {product_data['category_id']} not found")
        
        # Validate supplier_id (expecting SUPP-### format)
        if 'supplier_id' in product_data and product_data['supplier_id']:
            supplier = self.supplier_collection.find_one({'_id': product_data['supplier_id']})
            if not supplier:
                raise ValueError(f"Supplier with ID {product_data['supplier_id']} not found")
        
        # Validate branch_id (string-based lookup)
        if 'branch_id' in product_data and product_data['branch_id']:
            branch = self.branch_collection.find_one({'_id': product_data['branch_id']})
            if not branch:
                raise ValueError(f"Branch with ID {product_data['branch_id']} not found")
    
    def _send_product_notification(self, action_type, product_name, product_id=None, additional_metadata=None):
        """Centralized notification helper for product actions"""
        try:
            titles = {
                'created': "New Product Added",
                'updated': "Product Updated",
                'stock_updated': "Stock Updated", 
                'stock_low': "Low Stock Alert",
                'stock_out': "Out of Stock Alert",
                'soft_deleted': "Product Deleted",
                'hard_deleted': "Product Permanently Deleted", 
                'restored': "Product Restored",
                'bulk_created': "Bulk Products Created",
                'bulk_stock_updated': "Bulk Stock Updated",
                'import_completed': "Product Import Completed"
            }
            
            messages = {
                'created': f"Product '{product_name}' has been added to the system",
                'updated': f"Product '{product_name}' has been updated",
                'stock_updated': f"Stock updated for product '{product_name}'",
                'stock_low': f"Low stock warning for product '{product_name}'",
                'stock_out': f"Product '{product_name}' is out of stock",
                'soft_deleted': f"Product '{product_name}' has been moved to trash",
                'hard_deleted': f"Product '{product_name}' has been permanently removed",
                'restored': f"Product '{product_name}' has been restored from trash",
                'bulk_created': f"Bulk product creation completed",
                'bulk_stock_updated': f"Bulk stock update completed", 
                'import_completed': f"Product import completed"
            }
            
            # Use custom message if provided, otherwise use default
            if additional_metadata and 'custom_message' in additional_metadata:
                message = additional_metadata['custom_message']
            else:
                message = messages.get(action_type, f"Product action '{action_type}' completed for '{product_name}'")
            
            # Set priority and notification type based on action
            if action_type == 'stock_out':
                priority = "high"
                notification_type = "alert"
            elif action_type in ['stock_low', 'hard_deleted']:
                priority = "medium" 
                notification_type = "alert"
            elif action_type in ['soft_deleted', 'bulk_created', 'bulk_stock_updated']:
                priority = "medium"
                notification_type = "system"
            else:
                priority = "low"
                notification_type = "system"
            
            # Base metadata
            metadata = {
                "product_id": str(product_id) if product_id else "",
                "product_name": product_name,
                "action_type": f"product_{action_type}"
            }
            
            # Add additional metadata if provided
            if additional_metadata:
                # Remove custom_message from metadata since we used it for the message
                filtered_metadata = {k: v for k, v in additional_metadata.items() if k != 'custom_message'}
                metadata.update(filtered_metadata)
            
            notification_service.create_notification(
                title=titles.get(action_type, "Product Action"),
                message=message,
                priority=priority,
                notification_type=notification_type,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Failed to send product notification: {e}")
        
    def generate_product_id(self):
        """Generate sequential PROD-##### ID"""
        try:
            # Get the highest existing product ID number
            pipeline = [
                {'$match': {'_id': {'$regex': r'^PROD-\d{5}$'}}},
                {'$project': {
                    'id_number': {
                        '$toInt': {
                            '$substr': ['$_id', 5, -1]  # Extract number after "PROD-"
                        }
                    }
                }},
                {'$sort': {'id_number': -1}},
                {'$limit': 1}
            ]
            
            result = list(self.product_collection.aggregate(pipeline))
            next_number = (result[0]['id_number'] + 1) if result else 1
            
            return f"PROD-{next_number:05d}"
        
        except Exception:
            # Fallback: count all products + 1
            count = self.product_collection.count_documents({}) + 1
            return f"PROD-{count:05d}"

    def add_sync_log(self, source='cloud', status='synced', details=None):
        """Helper method to create sync log entries"""
        return {
            'last_updated': datetime.utcnow(),
            'source': source,  # 'local' or 'cloud'
            'status': status,  # 'synced', 'pending', 'failed'
            'details': details or {}
        }
    
    def _ensure_default_category_assignment(self, product_document):
        """Auto-assign to 'Uncategorized' > 'General' if no category specified"""
        if not product_document.get('category_id'):
            product_document['category_id'] = "UNCTGRY-001"
            product_document['subcategory_name'] = "General"
            logger.debug(f"Auto-assigned product to Uncategorized > General")
        
        # Ensure subcategory_name is set if category is provided
        if product_document.get('category_id') and not product_document.get('subcategory_name'):
            product_document['subcategory_name'] = "General"
            logger.debug(f"Auto-assigned subcategory to General")
        
        return product_document

    def update_sync_status(self, product_id, sync_status='pending', source='cloud'):
        """Update sync status for a product - using string IDs"""
        try:
            sync_log = self.add_sync_log(source=source, status=sync_status)
            
            result = self.product_collection.update_one(
                {'_id': product_id},
                {'$push': {'sync_logs': sync_log}}
            )
            
            return result.modified_count > 0
        
        except Exception as e:
            logger.error(f"Error updating sync status: {str(e)}")
            return False

    def mark_as_synced(self, product_id, source='cloud'):
        """Mark a product as successfully synced"""
        return self.update_sync_status(product_id, sync_status='synced', source=source)
    
    def get_unsynced_products(self, source='local'):
        """Get products that need to be synced from specified source"""
        try:
            pipeline = [
                {
                    '$addFields': {
                        'latest_sync': {
                            '$arrayElemAt': [
                                {
                                    '$filter': {
                                        'input': '$sync_logs',
                                        'cond': {'$eq': ['$$this.source', source]}
                                    }
                                },
                                -1  # Get the latest entry for this source
                            ]
                        }
                    }
                },
                {
                    '$match': {
                        '$or': [
                            {'latest_sync': None},  # No sync log for this source
                            {'latest_sync.status': {'$ne': 'synced'}}  # Not synced
                        ]
                    }
                }
            ]
            
            products = list(self.product_collection.aggregate(pipeline))
            return products
        
        except Exception as e:
            raise Exception(f"Error getting unsynced products: {str(e)}")
    
    def generate_sku(self, product_name, category_id=None):
        """Generate a unique SKU for the product - string-based category lookup"""
        try:
            # Get category prefix
            category_prefix = "PROD"
            if category_id:
                category = self.category_collection.find_one({'_id': category_id})
                if category:
                    category_prefix = category.get('category_name', 'PROD')[:4].upper()
            
            # Get product name prefix
            name_prefix = ''.join(product_name.split()[:2])[:4].upper()
            
            # Count existing products to generate sequence number (exclude deleted products)
            count = self.product_collection.count_documents({'isDeleted': {'$ne': True}}) + 1
            
            # Generate SKU: CATEGORY-NAME-NUMBER
            sku = f"{category_prefix}-{name_prefix}-{count:03d}"
            
            # Ensure uniqueness (check against non-deleted products)
            while self.product_collection.find_one({'SKU': sku, 'isDeleted': {'$ne': True}}):
                count += 1
                sku = f"{category_prefix}-{name_prefix}-{count:03d}"
            
            return sku
        except Exception as e:
            # Fallback to simple SKU
            count = self.product_collection.count_documents({'isDeleted': {'$ne': True}}) + 1
            return f"PROD-{count:06d}"
    
    def calculate_similarity(self, str1, str2):
        """Calculate similarity between two strings (0.0 to 1.0)"""
        try:
            from difflib import SequenceMatcher
            return SequenceMatcher(None, str1, str2).ratio()
        except ImportError:
            # Fallback: simple character comparison
            if str1 == str2:
                return 1.0
            elif str1 in str2 or str2 in str1:
                return 0.8
            else:
                return 0.0
    
    # ================================================================
    # CORE PRODUCT CRUD OPERATIONS
    # ================================================================
    
    def create_product(self, product_data):
        """Create a new product with sequential PROD-##### ID"""
        try:
            logger.info(f"Creating single product: {product_data.get('product_name', 'Unknown')}")
            
            # VALIDATION: If stock is provided, cost_price must also be provided
            initial_stock = int(product_data.get('stock', 0))
            if initial_stock > 0:
                cost_price = product_data.get('cost_price')
                if cost_price is None or float(cost_price) == 0:
                    raise ValueError("Cost price is required when initial stock is provided")
            
            # Generate sequential product ID
            product_id = self.generate_product_id()
            
            # Validate foreign keys
            self.validate_foreign_keys(product_data)
            
            # Generate SKU if not provided
            if not product_data.get('SKU'):
                product_data['SKU'] = self.generate_sku(
                    product_data.get('product_name', 'Product'),
                    product_data.get('category_id')
                )
            
            # ENHANCED DUPLICATE VALIDATION FOR SINGLE PRODUCT
            existing_product = self.product_collection.find_one({
                'SKU': product_data['SKU'], 
                'isDeleted': {'$ne': True}
            })
            if existing_product:
                raise ValueError(f"Product with SKU '{product_data['SKU']}' already exists")
            
            product_name = product_data.get('product_name', '').strip()
            if product_name:
                existing_name = self.product_collection.find_one({
                    'product_name': {'$regex': f'^{re.escape(product_name)}$', '$options': 'i'}, 
                    'isDeleted': {'$ne': True}
                })
                if existing_name:
                    raise ValueError(f"Product with name '{product_name}' already exists")
            
            # Set default values - Create clean product document
            current_time = datetime.utcnow()
            product_document = {
                '_id': product_id,
                'product_name': product_data.get('product_name', ''),
                'category_id': product_data.get('category_id', ''),
                'subcategory_name': product_data.get('subcategory_name', ''),
                'SKU': product_data['SKU'],
                'unit': product_data.get('unit', ''),
                'stock': initial_stock,  # Use validated initial_stock
                'low_stock_threshold': int(product_data.get('low_stock_threshold', 10)),
                'cost_price': float(product_data.get('cost_price', 0)),
                'selling_price': float(product_data.get('selling_price', 0)),
                'status': product_data.get('status', 'active'),
                'is_taxable': product_data.get('is_taxable', True),
                'date_received': product_data.get('date_received', current_time),
                'isDeleted': False,
                'created_at': current_time,
                'updated_at': current_time,
                # Batch-related fields for simplified expiry tracking
                'total_stock': initial_stock,
                'oldest_batch_expiry': None,
                'newest_batch_expiry': None,
                'expiry_alert': False
            }
            
            # Add optional fields if present
            optional_fields = ['expiry_date', 'barcode', 'description', 'supplier_id', 'branch_id']
            for field in optional_fields:
                if field in product_data and product_data[field]:
                    product_document[field] = product_data[field]
                
            image_fields = ['image', 'image_url', 'image_filename', 'image_size', 'image_type', 'image_uploaded_at']
            for field in image_fields:
                if field in product_data and product_data[field] is not None:
                    product_document[field] = product_data[field]
                        
            # Initialize sync logs
            product_document['sync_logs'] = [
                self.add_sync_log(source='cloud', status='pending', details={'action': 'created'})
            ]
            
            # AUTO-ASSIGN TO CATEGORY/SUBCATEGORY - SIMPLIFIED
            product_document = self._ensure_default_category_assignment(product_document)
            
            # Insert product directly as dict
            self.product_collection.insert_one(product_document)
            
            # CREATE INITIAL BATCH IF STOCK WAS PROVIDED
            initial_batch = None
            if initial_stock > 0:
                try:
                    initial_batch = self._create_initial_batch_if_needed(product_id, product_data)
                except Exception as batch_error:
                    # If batch creation fails, log error but don't fail product creation
                    logger.error(f"Failed to create initial batch for product {product_id}: {str(batch_error)}")
                    # Optionally: rollback product creation if batch is critical
                    # self.product_collection.delete_one({'_id': product_id})
                    # raise batch_error
            
            # Get created product
            created_product = self.product_collection.find_one({'_id': product_id})
            
            # Send notification
            notification_metadata = {
                "SKU": product_document["SKU"],
                "category_id": created_product.get('category_id'),
                "subcategory_name": created_product.get('subcategory_name'),
                "initial_stock": initial_stock
            }
            
            if initial_batch:
                notification_metadata["initial_batch_id"] = initial_batch['_id']
                notification_metadata["initial_batch_created"] = True
            
            self._send_product_notification(
                'created',
                product_document.get("product_name", product_document.get("SKU", "Unknown Product")),
                product_id,
                notification_metadata
            )

            return created_product
        
        except Exception as e:
            raise Exception(f"Error creating product: {str(e)}")
    
    def get_all_products(self, filters=None, include_deleted=False, include_images=True):
        """Get all products with optional filters"""
        try:
            query = {}
            
            # By default, exclude deleted products unless specifically requested
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            # Define projection to exclude image fields if not needed
            projection = None
            if not include_images:
                projection = {
                    'image': 0,
                    'image_url': 0,
                    'image_filename': 0,
                    'image_size': 0,
                    'image_type': 0,
                    'image_uploaded_at': 0
                }
            
            if filters:
                # Category filter
                if filters.get('category_id'):
                    query['category_id'] = filters['category_id']
                
                # Subcategory filter
                if filters.get('subcategory_name'):
                    query['subcategory_name'] = filters['subcategory_name']
                
                # Status filter
                if filters.get('status'):
                    query['status'] = filters['status']
                
                # Stock level filter
                if filters.get('stock_level'):
                    if filters['stock_level'] == 'out_of_stock':
                        query['stock'] = 0
                    elif filters['stock_level'] == 'low_stock':
                        query['$expr'] = {'$lte': ['$stock', '$low_stock_threshold']}
                
                # Search filter
                if filters.get('search'):
                    search_regex = {'$regex': filters['search'], '$options': 'i'}
                    query['$or'] = [
                        {'product_name': search_regex},
                        {'SKU': search_regex},
                        {'_id': search_regex}
                    ]
            
            # Apply projection if images should be excluded
            if projection:
                products = list(self.product_collection.find(query, projection).sort('product_name', 1))
            else:
                products = list(self.product_collection.find(query).sort('product_name', 1))
            
            # OPTIMIZED: Fetch all batches in ONE query and group by product_id
            now = datetime.utcnow()
            batch_collection = self.db.batches
            
            # Get all product IDs
            product_ids = [p['_id'] for p in products]
            
            # Fetch all active batches for ALL products in a single query
            all_batches = list(batch_collection.find({
                'product_id': {'$in': product_ids},
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }))
            
            # Group batches by product_id for fast lookup
            from collections import defaultdict
            batches_by_product = defaultdict(list)
            for batch in all_batches:
                batches_by_product[batch['product_id']].append(batch)
            
            # Now enrich each product (no more database queries in the loop!)
            for product in products:
                active_batches = batches_by_product.get(product['_id'], [])
                
                # Filter out expired batches (handle both datetime and string dates)
                non_expired_batches = []
                for batch in active_batches:
                    expiry_date = batch.get('expiry_date')
                    if not expiry_date:
                        # No expiry date, include the batch
                        non_expired_batches.append(batch)
                    else:
                        # Convert to datetime if it's a string
                        if isinstance(expiry_date, str):
                            try:
                                from dateutil import parser
                                expiry_date = parser.parse(expiry_date)
                            except Exception:
                                # If parsing fails, include the batch to be safe
                                non_expired_batches.append(batch)
                                continue
                        
                        # Check if not expired
                        if isinstance(expiry_date, datetime) and expiry_date >= now:
                            non_expired_batches.append(batch)
                
                # Calculate total stock from non-expired batches
                total_stock = sum(batch['quantity_remaining'] for batch in non_expired_batches)
                product['total_stock'] = total_stock
                product['stock'] = total_stock  # Keep both fields in sync
                
                # Calculate average cost price from non-expired batches
                if non_expired_batches:
                    total_cost = sum(
                        batch.get('cost_price', 0) * batch['quantity_remaining']
                        for batch in non_expired_batches
                    )
                    product['average_cost_price'] = total_cost / total_stock if total_stock > 0 else 0
                else:
                    product['average_cost_price'] = product.get('cost_price', 0)
            
            return products
        
        except Exception as e:
            raise Exception(f"Error getting products: {str(e)}")
    
    def get_product_by_id(self, product_id, include_deleted=False):
        """Get product by string ID"""
        try:
            query = {'_id': product_id}
            
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            product = self.product_collection.find_one(query)
            return product
        
        except Exception as e:
            raise Exception(f"Error getting product: {str(e)}")
    
    def get_product_by_sku(self, sku, include_deleted=False):
        """Get product by SKU"""
        try:
            query = {'SKU': sku}
            
            if not include_deleted:
                query['isDeleted'] = {'$ne': True}
            
            product = self.product_collection.find_one(query)
            return product
        
        except Exception as e:
            raise Exception(f"Error getting product by SKU: {str(e)}")
    
    def update_product(self, product_id, product_data):
        """Update product - SIMPLIFIED without complex category sync"""
        try:
            # Check if product exists and is not deleted
            existing_product = self.get_product_by_id(product_id, include_deleted=False)
            if not existing_product:
                raise Exception(f"Product with ID {product_id} not found or is deleted")
            
            # Validate foreign keys if they're being updated
            self.validate_foreign_keys(product_data)
            
            # Ensure numeric fields are properly typed
            numeric_fields = ['stock', 'low_stock_threshold', 'cost_price', 'selling_price']
            for field in numeric_fields:
                if field in product_data:
                    try:
                        if field in ['stock', 'low_stock_threshold']:
                            product_data[field] = int(product_data[field])
                        else:
                            product_data[field] = float(product_data[field])
                    except (ValueError, TypeError):
                        pass  # Keep original value if conversion fails
            
            # Add updated timestamp
            product_data['updated_at'] = datetime.utcnow()
            
            # Update product (only non-deleted products)
            result = self.product_collection.update_one(
                {'_id': product_id, 'isDeleted': {'$ne': True}}, 
                {'$set': product_data}
            )
            
            if result.modified_count > 0:
                # Mark as needing sync since data was updated
                self.update_sync_status(product_id, sync_status='pending', source='cloud')
                
                updated_product = self.product_collection.find_one({'_id': product_id})
                
                # Send notification
                product_name = updated_product.get("product_name", updated_product.get("SKU", "Unknown Product"))
                
                notification_metadata = {
                    "SKU": updated_product.get("SKU"),
                    "updated_fields": list(product_data.keys()),
                    "category_id": updated_product.get('category_id'),
                    "subcategory_name": updated_product.get('subcategory_name')
                }
                
                self._send_product_notification(
                    'updated',
                    product_name,
                    product_id,
                    notification_metadata
                )
                
                return updated_product
            return None
        
        except Exception as e:
            raise Exception(f"Error updating product: {str(e)}")

    def delete_product(self, product_id, hard_delete=False):
        """Soft delete or hard delete a product"""
        try:
            # Get product details before deletion for notification
            product_to_delete = self.product_collection.find_one({'_id': product_id})
            if not product_to_delete:
                return False
            
            if hard_delete:
                # Hard delete - permanently remove from database
                result = self.product_collection.delete_one({'_id': product_id})
                
                if result.deleted_count > 0:
                    # Send notification for hard deletion
                    product_name = product_to_delete.get("product_name", product_to_delete.get("SKU", "Unknown Product"))
                    
                    self._send_product_notification(
                        'hard_deleted',
                        product_name,
                        product_id,
                        {
                            "SKU": product_to_delete.get("SKU"),
                            "deletion_type": "permanent",
                            "deleted_at": datetime.utcnow().isoformat(),
                            "stock_at_deletion": product_to_delete.get("stock", 0)
                        }
                    )
                    
                    return True
                return False
            else:
                # Soft delete - mark as deleted with timestamp and reason
                current_time = datetime.utcnow()
                
                # Create deletion log entry
                deletion_log = {
                    'deleted_at': current_time,
                    'deleted_by': 'system',  # This could be user ID in the future
                    'reason': 'Manual deletion'
                }
                
                # Update product to mark as deleted
                result = self.product_collection.update_one(
                    {'_id': product_id, 'isDeleted': {'$ne': True}},
                    {
                        '$set': {
                            'isDeleted': True,
                            'updated_at': current_time,
                            'deletion_log': deletion_log
                        }
                    }
                )
                
                if result.modified_count > 0:
                    # Mark as needing sync since product was deleted
                    self.update_sync_status(product_id, sync_status='pending_deletion', source='cloud')
                    
                    # Send notification for soft deletion
                    product_name = product_to_delete.get("product_name", product_to_delete.get("SKU", "Unknown Product"))
                    
                    self._send_product_notification(
                        'soft_deleted',
                        product_name,
                        product_id,
                        {
                            "SKU": product_to_delete.get("SKU"),
                            "deletion_type": "soft",
                            "deleted_at": current_time.isoformat(),
                            "deleted_by": deletion_log["deleted_by"],
                            "deletion_reason": deletion_log["reason"],
                            "stock_at_deletion": product_to_delete.get("stock", 0),
                            "can_be_restored": True
                        }
                    )
                    
                    return True
                
                return False
        
        except Exception as e:
            raise Exception(f"Error deleting product: {str(e)}")

    def restore_product(self, product_id):
        """Restore a soft-deleted product"""
        try:
            current_time = datetime.utcnow()
            
            # Create restoration log entry
            restoration_log = {
                'restored_at': current_time,
                'restored_by': 'system',  # This could be user ID in the future
                'reason': 'Manual restoration'
            }
            
            # Update product to restore it
            result = self.product_collection.update_one(
                {'_id': product_id, 'isDeleted': True},
                {
                    '$set': {
                        'isDeleted': False,
                        'updated_at': current_time,
                        'restoration_log': restoration_log
                    },
                    '$unset': {
                        'deletion_log': 1  # Remove deletion log when restoring
                    }
                }
            )
            
            if result.modified_count > 0:
                # Mark as needing sync since product was restored
                self.update_sync_status(product_id, sync_status='pending', source='cloud')
                
                # Get restored product and send notification
                restored_product = self.product_collection.find_one({'_id': product_id})
                product_name = restored_product.get("product_name", restored_product.get("SKU", "Unknown Product"))
                
                self._send_product_notification(
                    'restored',
                    product_name,
                    product_id,
                    {
                        "SKU": restored_product.get("SKU"),
                        "restored_at": current_time.isoformat(),
                        "restored_by": restoration_log["restored_by"]
                    }
                )
                
                return True
            
            return False
        
        except Exception as e:
            raise Exception(f"Error restoring product: {str(e)}")

    # ================================================================
    # STOCK MANAGEMENT WITH BATCH INTEGRATION
    # ================================================================
    
    def update_stock(self, product_id, stock_data):
        """Update product stock with various operation types"""
        try:
            # Get current product to access current stock (only non-deleted)
            current_product = self.product_collection.find_one({
                '_id': product_id,
                'isDeleted': {'$ne': True}
            })
            if not current_product:
                raise Exception(f"Product with ID {product_id} not found or is deleted")
            
            current_stock = current_product.get('stock', 0)
            
            # Extract operation details
            operation_type = stock_data.get('operation_type', 'set')
            quantity = int(stock_data.get('quantity', 0))
            reason = stock_data.get('reason', 'Manual adjustment')
            
            # Calculate new stock based on operation type
            if operation_type == 'add':
                new_stock = current_stock + quantity
            elif operation_type == 'remove':
                new_stock = max(0, current_stock - quantity)  # Don't allow negative stock
            elif operation_type == 'set':
                new_stock = quantity
            else:
                raise ValueError(f"Invalid operation type: {operation_type}")
            
            # Validate new stock
            if new_stock < 0:
                raise ValueError("Stock cannot be negative")
            
            # Create stock history entry
            current_time = datetime.utcnow()
            stock_history_entry = {
                'timestamp': current_time,
                'operation': operation_type,
                'quantity': quantity,
                'previous_stock': current_stock,
                'new_stock': new_stock,
                'reason': reason,
                'performed_by': 'system'  # This could be user ID in the future
            }
            
            # Update the product
            update_data = {
                'stock': new_stock,
                'total_stock': new_stock,  # Keep both fields in sync
                'updated_at': current_time
            }
            
            result = self.product_collection.update_one(
                {'_id': product_id, 'isDeleted': {'$ne': True}}, 
                {
                    '$set': update_data,
                    '$push': {'stock_history': stock_history_entry}
                }
            )
            
            if result.modified_count > 0:
                # Mark as needing sync since stock was updated
                self.update_sync_status(product_id, sync_status='pending', source='cloud')
                
                updated_product = self.product_collection.find_one({'_id': product_id})
                
                # Prepare notification data
                product_name = updated_product.get("product_name", updated_product.get("SKU", "Unknown Product"))
                low_stock_threshold = updated_product.get('low_stock_threshold', 0)
                
                # Determine notification type and create operation-specific message
                if new_stock == 0:
                    action_type = 'stock_out'
                    message_suffix = " - OUT OF STOCK!"
                elif new_stock <= low_stock_threshold and new_stock > 0:
                    action_type = 'stock_low' 
                    message_suffix = " - LOW STOCK WARNING!"
                else:
                    action_type = 'stock_updated'
                    message_suffix = ""
                
                # Create operation-specific message
                if operation_type == 'add':
                    base_message = f"Stock added to '{product_name}': +{quantity} units (Total: {new_stock})"
                elif operation_type == 'remove':
                    base_message = f"Stock removed from '{product_name}': -{quantity} units (Total: {new_stock})"
                elif operation_type == 'set':
                    base_message = f"Stock set for '{product_name}': {new_stock} units"
                
                custom_message = base_message + message_suffix
                
                # Send notification
                self._send_product_notification(
                    action_type,
                    product_name,
                    product_id,
                    {
                        "SKU": updated_product.get("SKU"),
                        "operation_type": operation_type,
                        "quantity_changed": quantity,
                        "previous_stock": current_stock,
                        "new_stock": new_stock,
                        "reason": reason,
                        "is_low_stock": new_stock <= low_stock_threshold,
                        "is_out_of_stock": new_stock == 0,
                        "low_stock_threshold": low_stock_threshold,
                        "custom_message": custom_message
                    }
                )
                
                return updated_product
            return None
        
        except Exception as e:
            raise Exception(f"Error updating stock: {str(e)}")
        
    def bulk_update_stock(self, stock_updates):
        """Update multiple products' stock in batch"""
        try:
            results = []
            for update in stock_updates:
                product_id = update.get('product_id')
                stock_data = {
                    'operation_type': update.get('operation_type', 'set'),
                    'quantity': update.get('quantity', 0),
                    'reason': update.get('reason', 'Bulk update')
                }
                
                result = self.update_stock(product_id, stock_data)
                results.append({
                    'product_id': product_id,
                    'success': result is not None,
                    'result': result
                })
            
            # Send unified notification for bulk stock update
            successful_count = len([r for r in results if r['success']])
            failed_count = len([r for r in results if not r['success']])
            total_updates = len(stock_updates)
            
            if failed_count == 0:
                message = f"Bulk stock update completed successfully: {successful_count} products updated"
            else:
                message = f"Bulk stock update completed: {successful_count} successful, {failed_count} failed out of {total_updates} total"
            
            self._send_product_notification(
                'bulk_stock_updated',
                f"{successful_count} products",
                None,  # No single product ID for bulk operations
                {
                    "total_products": total_updates,
                    "successful_updates": successful_count,
                    "failed_updates": failed_count,
                    "success_rate": round((successful_count / total_updates) * 100, 2) if total_updates > 0 else 0,
                    "custom_message": message
                }
            )
            
            return results
        
        except Exception as e:
            raise Exception(f"Error in bulk stock update: {str(e)}")
        
    def adjust_stock_for_sale(self, product_id, quantity_sold):
        """Reduce stock when a sale is made - now uses FIFO from batches"""
        try:
            # Process sale using FIFO from batch service
            batches_used = self.batch_service.process_sale_fifo(product_id, quantity_sold)
            
            # Update product stock using existing method
            stock_data = {
                'operation_type': 'remove',
                'quantity': quantity_sold,
                'reason': 'Sale transaction'    
            }
            updated_product = self.update_stock(product_id, stock_data)
            
            return {
                'product': updated_product,
                'batches_used': batches_used
            }

        except Exception as e:
            raise Exception(f"Error adjusting stock for sale: {str(e)}")
    
    def restock_product(self, product_id, quantity_received, supplier_info=None, batch_info=None):
        """Add stock when receiving new inventory - now creates batches"""
        try:
            # Create batch first
            batch_data = {
                'product_id': product_id,
                'quantity_received': quantity_received,
                'cost_price': batch_info.get('cost_price') if batch_info else 0,
                'expiry_date': batch_info.get('expiry_date') if batch_info else None,
                'supplier_id': supplier_info.get('supplier_id') if supplier_info else None,
                'batch_number': batch_info.get('batch_number') if batch_info else None
            }
            
            # Create the batch (this will automatically update product expiry summary)
            batch = self.batch_service.create_batch(batch_data)
            
            # Update product stock using the existing method
            reason = f"Restock from supplier"
            if supplier_info:
                reason += f" - {supplier_info.get('name', 'Unknown')}"
            
            stock_data = {
                'operation_type': 'add',
                'quantity': quantity_received,
                'reason': reason
            }
            
            updated_product = self.update_stock(product_id, stock_data)
            
            return {
                'product': updated_product,
                'batch': batch
            }
            
        except Exception as e:
            raise Exception(f"Error restocking product: {str(e)}")

    def get_product_with_batch_summary(self, product_id):
        """Get product with batch and expiry summary information"""
        try:
            product = self.get_product_by_id(product_id)
            if not product:
                return None
            
            # Get active batches for this product
            batches = self.batch_service.get_batches_by_product(product_id, status='active')
            
            product['active_batches'] = batches
            product['batch_count'] = len(batches)
            
            return product
        
        except Exception as e:
            raise Exception(f"Error getting product with batch summary: {str(e)}")

    def check_expiry_alerts(self, days_ahead=7):
        """Check for products with expiring batches and return alert summary"""
        try:
            return self.batch_service.check_and_alert_expiring_batches(days_ahead)
        
        except Exception as e:
            raise Exception(f"Error checking expiry alerts: {str(e)}")

    # ================================================================
    # PRODUCT QUERIES AND FILTERING
    # ================================================================
    
    def get_deleted_products(self):
        """Get all soft-deleted products"""
        try:
            products = list(self.product_collection.find({'isDeleted': True}).sort('deletion_log.deleted_at', -1))
            return products
        
        except Exception as e:
            raise Exception(f"Error getting deleted products: {str(e)}")
    
    def get_low_stock_products(self, branch_id=None):
        """Get products with low stock (excluding deleted)"""
        try:
            query = {
                '$expr': {'$lte': ['$stock', '$low_stock_threshold']},
                'isDeleted': {'$ne': True}
            }
            
            if branch_id:
                query['branch_id'] = branch_id
            
            products = list(self.product_collection.find(query))
            return products
        
        except Exception as e:
            raise Exception(f"Error getting low stock products: {str(e)}")
    
    def get_products_by_category(self, category_id, subcategory_name=None):
        """
        Returns full product details (with correct stock values)
        using the same engine as get_all_products().
        Ensures Category Details and Export show correct data.
        """
        try:
            # Apply filters
            filters = {"category_id": category_id}

            if subcategory_name:
                filters["subcategory_name"] = subcategory_name

            # Reuse get_all_products() to ensure full computed product data
            # Including: stock, total_stock, thresholds, status, etc.
            full_products = self.get_all_products(filters=filters, include_deleted=False)

            return full_products

        except Exception as e:
            raise Exception(f"Error getting full products by category: {str(e)}")


    
    def get_expiring_products(self, days_ahead=30):
        """Get products with expiring batches within specified days"""
        try:
            from datetime import timedelta
            
            future_date = datetime.utcnow() + timedelta(days=days_ahead)
            
            query = {
                'oldest_batch_expiry': {
                    '$lte': future_date,
                    '$gte': datetime.utcnow()
                },
                'isDeleted': {'$ne': True}
            }
            
            products = list(self.product_collection.find(query).sort('oldest_batch_expiry', 1))
            return products
        
        except Exception as e:
            raise Exception(f"Error getting expiring products: {str(e)}")

    # ================================================================
    # BULK OPERATIONS
    # ================================================================
        
    def bulk_create_products(self, products_data):
        """Create multiple products in batch with validation"""
        try:
            logger.info(f"Processing {len(products_data)} products for bulk creation")
            
            validated_products = []
            errors = []
            seen_skus = set()
            seen_names = set()
            
            for i, product_data in enumerate(products_data):
                try:
                    logger.debug(f"Processing product {i+1}: {product_data.get('product_name', 'Unknown')}")
                    
                    # VALIDATION: If stock is provided, cost_price must also be provided
                    initial_stock = int(product_data.get('stock', 0))
                    if initial_stock > 0:
                        cost_price = product_data.get('cost_price')
                        if cost_price is None or float(cost_price) == 0:
                            raise ValueError("Cost price is required when initial stock is provided")
                    
                    # Generate sequential product ID for each product
                    product_id = self.generate_product_id()
                    product_data['_id'] = product_id
                    
                    # Validate foreign keys
                    self.validate_foreign_keys(product_data)
                    
                    # Generate SKU if not provided
                    if not product_data.get('SKU'):
                        product_data['SKU'] = self.generate_sku(
                            product_data.get('product_name', 'Product'),
                            product_data.get('category_id')
                        )
                    
                    # DUPLICATE VALIDATION
                    if product_data['SKU'] in seen_skus:
                        raise ValueError(f"Duplicate SKU in current batch: {product_data['SKU']}")
                    
                    existing_sku = self.product_collection.find_one({
                        'SKU': product_data['SKU'], 
                        'isDeleted': {'$ne': True}
                    })
                    if existing_sku:
                        raise ValueError(f"Product with SKU '{product_data['SKU']}' already exists in database")
                    
                    product_name_lower = product_data.get('product_name', '').strip().lower()
                    if product_name_lower in seen_names:
                        raise ValueError(f"Duplicate product name in current batch: {product_data.get('product_name')}")
                    
                    if product_name_lower:
                        existing_name = self.product_collection.find_one({
                            'product_name': {'$regex': f'^{re.escape(product_data.get("product_name", ""))}$', '$options': 'i'}, 
                            'isDeleted': {'$ne': True}
                        })
                        if existing_name:
                            raise ValueError(f"Product with name '{product_data.get('product_name')}' already exists in database")
                    
                    seen_skus.add(product_data['SKU'])
                    seen_names.add(product_name_lower)
                    
                    # AUTO-ASSIGN CATEGORY FOR BULK PRODUCTS - SIMPLIFIED
                    product_data = self._ensure_default_category_assignment(product_data)
                    
                    # Set default values
                    current_time = datetime.utcnow()
                    product_data.update({
                        'date_received': product_data.get('date_received', current_time),
                        'status': product_data.get('status', 'active'),
                        'is_taxable': product_data.get('is_taxable', True),
                        'isDeleted': False,
                        'created_at': current_time,
                        'updated_at': current_time,
                        'sync_logs': [self.add_sync_log(source='cloud', status='pending', details={'action': 'bulk_created'})],
                        # Batch-related fields for simplified expiry tracking
                        'total_stock': initial_stock,
                        'oldest_batch_expiry': None,
                        'newest_batch_expiry': None,
                        'expiry_alert': False
                    })
                    
                    # Handle numeric fields
                    numeric_fields = ['stock', 'low_stock_threshold', 'cost_price', 'selling_price']
                    for field in numeric_fields:
                        if field in product_data:
                            try:
                                if field in ['stock', 'low_stock_threshold']:
                                    product_data[field] = int(product_data[field])
                                else:
                                    price_str = str(product_data[field])
                                    clean_price = price_str.replace('₱', '').replace(',', '').strip()
                                    product_data[field] = float(clean_price)
                            except (ValueError, TypeError):
                                product_data[field] = 0
                    
                    validated_products.append(product_data)
                    logger.debug(f"Product {i+1} validated and ready for creation")
                    
                except Exception as e:
                    logger.error(f"Product {i+1} validation failed: {str(e)}")
                    errors.append({
                        'index': i,
                        'data': product_data,
                        'error': str(e)
                    })
            
            # Perform bulk insert
            results = {
                'successful': [],
                'failed': errors,
                'total_processed': len(products_data),
                'total_successful': 0,
                'total_failed': len(errors),
                'batches_created': 0,
                'batch_creation_errors': []
            }
            
            if validated_products:
                logger.info(f"Inserting {len(validated_products)} validated products...")
                
                insert_result = self.product_collection.insert_many(validated_products, ordered=False)
                
                # Get inserted products
                inserted_products = list(self.product_collection.find({
                    '_id': {'$in': [product['_id'] for product in validated_products]}
                }))
                
                results['successful'] = inserted_products
                results['total_successful'] = len(inserted_products)
                
                # CREATE INITIAL BATCHES FOR PRODUCTS WITH STOCK
                logger.info(f"Creating initial batches for products with stock...")
                for product in inserted_products:
                    try:
                        initial_stock = product.get('stock', 0)
                        if initial_stock > 0:
                            # Find corresponding product_data to get full details
                            product_data = next(
                                (p for p in validated_products if p['_id'] == product['_id']), 
                                None
                            )
                            if product_data:
                                batch = self._create_initial_batch_if_needed(
                                    product['_id'], 
                                    product_data
                                )
                                if batch:
                                    results['batches_created'] += 1
                                    logger.debug(f"Created batch {batch['_id']} for product {product['_id']}")
                    except Exception as batch_error:
                        logger.error(f"Failed to create batch for product {product['_id']}: {str(batch_error)}")
                        results['batch_creation_errors'].append({
                            'product_id': product['_id'],
                            'error': str(batch_error)
                        })
                
                # Send notification for bulk creation
                total_processed = len(products_data)
                successful_count = len(inserted_products)
                failed_count = len(errors)
                batches_created = results['batches_created']
                
                if failed_count == 0 and len(results['batch_creation_errors']) == 0:
                    action_type = 'bulk_created'
                    message = f"Bulk product creation completed successfully: {successful_count} products created, {batches_created} initial batches created"
                else:
                    action_type = 'bulk_created'
                    message = f"Bulk product creation completed: {successful_count} products created ({batches_created} batches), {failed_count} failed, {len(results['batch_creation_errors'])} batch errors"
                
                self._send_product_notification(
                    action_type,
                    f"{successful_count} products",
                    None,  # No single product ID for bulk operations
                    {
                        "total_products": total_processed,
                        "successful_creations": successful_count,
                        "failed_creations": failed_count,
                        "batches_created": batches_created,
                        "batch_creation_errors": len(results['batch_creation_errors']),
                        "success_rate": round((successful_count / total_processed) * 100, 2) if total_processed > 0 else 0,
                        "custom_message": message
                    }
                )
            
            logger.info(f"Bulk creation completed: {results['total_successful']} successful, {results['total_failed']} failed, {results['batches_created']} batches created")
            return results
            
        except Exception as e:
            logger.error(f"Bulk create service error: {str(e)}")
            raise Exception(f"Error in bulk product creation: {str(e)}")

    # ================================================================
    # SYNC-RELATED METHODS
    # ================================================================
    
    def prepare_for_sync_to_local(self):
        """Get all products that need to be synced to local database"""
        return self.get_unsynced_products(source='cloud')
    
    def prepare_for_sync_to_cloud(self):
        """Get all products that need to be synced to cloud database"""
        return self.get_unsynced_products(source='local')
    
    def sync_from_local(self, local_products):
        """Sync products from local database to cloud"""
        try:
            sync_results = []
            
            for product_data in local_products:
                try:
                    product_id = product_data.get('_id')
                    
                    if product_id:
                        # Update existing product
                        result = self.update_product(product_id, product_data)
                        if result:
                            self.mark_as_synced(product_id, source='local')
                            sync_results.append({'product_id': product_id, 'status': 'updated'})
                    else:
                        # Create new product
                        result = self.create_product(product_data)
                        if result:
                            self.mark_as_synced(result['_id'], source='local')
                            sync_results.append({'product_id': result['_id'], 'status': 'created'})
                            
                except Exception as e:
                    sync_results.append({'product_id': product_data.get('_id'), 'status': 'error', 'error': str(e)})
            
            return sync_results
        
        except Exception as e:
            raise Exception(f"Error syncing from local: {str(e)}")
    
    def sync_to_local(self):
        """Prepare cloud products for sync to local database"""
        try:
            # Get all products that need to be synced
            products_to_sync = self.prepare_for_sync_to_local()
            
            # Mark them as synced once they're prepared for sync
            for product in products_to_sync:
                self.mark_as_synced(product['_id'], source='cloud')
            
            return products_to_sync
        
        except Exception as e:
            raise Exception(f"Error preparing sync to local: {str(e)}")
        
    def import_products_from_file(self, file_path, file_type='csv', validate_only=False):
        """
        Import products from CSV or Excel file with detailed validation
        Supplier removed entirely from import
        """
        try:
            # Read file based on type
            if file_type == 'csv':
                df = pd.read_csv(file_path)
            elif file_type in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Required + optional columns (supplier removed)
            required_columns = ['product_name', 'selling_price', 'category_name']
            optional_columns = ['subcategory_name', 'SKU', 'stock', 'cost_price',
                                'low_stock_threshold', 'unit', 'status', 'barcode',
                                'description', 'expiry_date']
            
            # Check missing required
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(
                    f"Missing required columns: {', '.join(missing_columns)}. "
                    f"Required columns are: {', '.join(required_columns)}"
                )
            
            validation_errors = []
            valid_products = []
            skipped_products = []
            missing_categories = {}
            
            for index, row in df.iterrows():
                row_num = index + 2
                errors = []
                
                # Required fields
                if pd.isna(row.get('product_name')) or not str(row.get('product_name')).strip():
                    errors.append(f"Row {row_num}: Product name is required")
                
                if pd.isna(row.get('selling_price')) or row.get('selling_price') <= 0:
                    errors.append(f"Row {row_num}: Selling price must be greater than 0")
                
                # Category logic
                category_name_raw = row.get('category_name', '')
                category_name = str(category_name_raw).strip() if not pd.isna(category_name_raw) else ''
                
                if not category_name:
                    errors.append(f"Row {row_num}: Category name is required")
                
                subcategory_name_raw = row.get('subcategory_name', '')
                subcategory_name = (
                    str(subcategory_name_raw).strip()
                    if not pd.isna(subcategory_name_raw) and str(subcategory_name_raw).strip()
                    else None
                )
                
                category = None
                category_id = None
                
                if category_name:
                    category = self.db.category.find_one({
                        'category_name': category_name,
                        'isDeleted': False
                    })
                    
                    if not category:
                        if category_name not in missing_categories:
                            missing_categories[category_name] = set()
                        if subcategory_name:
                            missing_categories[category_name].add(subcategory_name)
                        errors.append(f"Row {row_num}: Category '{category_name}' not found")
                    else:
                        category_id = str(category['_id'])
                        
                        # Validate subcategory only if provided
                        if subcategory_name:
                            subcategories = category.get('sub_categories', [])
                            subcat_names = []
                            for subcat in subcategories:
                                if isinstance(subcat, dict) and 'name' in subcat:
                                    subcat_names.append(subcat['name'])
                                elif isinstance(subcat, str):
                                    subcat_names.append(subcat)
                            
                            if subcategory_name not in subcat_names:
                                if category_name not in missing_categories:
                                    missing_categories[category_name] = set()
                                missing_categories[category_name].add(subcategory_name)
                                errors.append(
                                    f"Row {row_num}: Subcategory '{subcategory_name}' not found under category '{category_name}'"
                                )
                
                # Stock/cost/expiry validation
                stock = row.get('stock', 0)
                cost_price = row.get('cost_price', 0)
                expiry_date = row.get('expiry_date')
                
                if not pd.isna(stock) and stock > 0:
                    if pd.isna(cost_price) or cost_price <= 0:
                        errors.append(f"Row {row_num}: Cost price is required when stock is provided")
                    
                    if pd.isna(expiry_date) or not str(expiry_date).strip():
                        errors.append(f"Row {row_num}: Expiry date is required when stock is provided")
                
                # Numeric checks
                try:
                    if not pd.isna(row.get('selling_price')):
                        float(row['selling_price'])
                except:
                    errors.append(f"Row {row_num}: Selling price must be a valid number")
                
                try:
                    if not pd.isna(row.get('cost_price')):
                        float(row['cost_price'])
                except:
                    errors.append(f"Row {row_num}: Cost price must be a valid number")
                
                try:
                    if not pd.isna(row.get('stock')):
                        int(row['stock'])
                except:
                    errors.append(f"Row {row_num}: Stock must be a valid integer")
                
                try:
                    if not pd.isna(row.get('low_stock_threshold')):
                        int(row['low_stock_threshold'])
                except:
                    errors.append(f"Row {row_num}: Low stock threshold must be a valid integer")
                
                # Add errors and continue
                if errors:
                    validation_errors.extend(errors)
                    continue
                
                # Build product data (supplier removed)
                product_data = {
                    'product_name': str(row['product_name']).strip(),
                    'selling_price': float(row['selling_price']),
                    'category_id': category_id,
                }
                
                if subcategory_name:
                    product_data['subcategory_name'] = subcategory_name
                
                if not pd.isna(row.get('SKU')):
                    product_data['SKU'] = str(row['SKU']).strip()
                
                if not pd.isna(row.get('stock')):
                    product_data['stock'] = int(row['stock'])
                
                if not pd.isna(row.get('cost_price')):
                    product_data['cost_price'] = float(row['cost_price'])
                
                if not pd.isna(row.get('low_stock_threshold')):
                    product_data['low_stock_threshold'] = int(row['low_stock_threshold'])
                
                if not pd.isna(row.get('unit')):
                    product_data['unit'] = str(row['unit']).strip()
                
                if not pd.isna(row.get('status')):
                    product_data['status'] = str(row['status']).strip()
                
                if not pd.isna(row.get('barcode')):
                    product_data['barcode'] = str(row['barcode']).strip()
                
                if not pd.isna(row.get('description')):
                    product_data['description'] = str(row['description']).strip()
                
                if not pd.isna(row.get('expiry_date')):
                    product_data['expiry_date'] = str(row['expiry_date']).strip()
                
                valid_products.append(product_data)
            
            # Missing categories summary
            missing_categories_list = [
                {'category_name': cat, 'subcategories': list(subcats)}
                for cat, subcats in missing_categories.items()
            ]
            
            # Validation mode
            if validate_only:
                return {
                    'valid': len(validation_errors) == 0 and len(missing_categories) == 0,
                    'total_rows': len(df),
                    'valid_products': len(valid_products),
                    'errors': validation_errors,
                    'missing_categories': missing_categories_list,
                    'message': 'Validation completed' if not validation_errors else 'Validation failed'
                }
            
            # Stop import if validation errors
            if validation_errors:
                return {
                    'success': False,
                    'total_rows': len(df),
                    'valid_products': len(valid_products),
                    'errors': validation_errors,
                    'missing_categories': missing_categories_list,
                    'message': f'Import failed: {len(validation_errors)} validation error(s) found'
                }
            
            # Import process
            successful = []
            failed = []
            
            for product_data in valid_products:
                try:
                    if 'SKU' in product_data:
                        existing = self.db.products.find_one({
                            'SKU': product_data['SKU'],
                            'isDeleted': False
                        })
                        if existing:
                            skipped_products.append({
                                'product': product_data['product_name'],
                                'reason': f"SKU {product_data['SKU']} already exists"
                            })
                            continue
                    
                    new_product = self.create_product(product_data)
                    successful.append(new_product)
                
                except Exception as e:
                    failed.append({
                        'product': product_data.get('product_name', 'Unknown'),
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'total_rows': len(df),
                'successful': len(successful),
                'failed': len(failed),
                'skipped': len(skipped_products),
                'failed_details': failed,
                'skipped_details': skipped_products,
                'missing_categories': missing_categories_list,
                'message': f'Import completed: {len(successful)} created, {len(failed)} failed, {len(skipped_products)} skipped'
            }
        
        except Exception as e:
            raise Exception(f"Import failed: {str(e)}")


    def generate_import_template(self, file_type='csv'):
        """Generate a template file for product import without supplier column"""
        try:
            import pandas as pd
            from openpyxl import load_workbook
            from openpyxl.worksheet.datavalidation import DataValidation
            
            template_data = {
                'product_name': ['Sample Noodle 1', 'Sample Drink 1'],
                'SKU': ['NOOD-SAMP-001', 'DRIN-SAMP-001'],
                'category_name': ['Noodles', 'Drinks'],
                'subcategory_name': ['Instant', 'Beverages'],
                'stock': [100, 50],
                'low_stock_threshold': [10, 5],
                'cost_price': [15.00, 25.00],
                'selling_price': [20.00, 30.00],
                'unit': ['piece', 'bottle'],
                'expiry_date': ['2025-12-31', '2025-06-30'],
                'status': ['active', 'active']
            }
            
            df = pd.DataFrame(template_data)
            
            if file_type.lower() == 'csv':
                template_path = 'product_import_template.csv'
                df.to_csv(template_path, index=False)
            
            elif file_type.lower() == 'xlsx':
                template_path = 'product_import_template.xlsx'
                df.to_excel(template_path, index=False, engine='openpyxl')
                
                wb = load_workbook(template_path)
                ws = wb.active
                
                categories = list(self.db.category.find(
                    {'isDeleted': False},
                    {'category_name': 1, 'sub_categories': 1}
                ))
                
                category_names = [cat['category_name'] for cat in categories]
                
                # Extract all unique subcategories
                subcategory_values = set()
                for cat in categories:
                    subcats = cat.get('sub_categories', [])
                    for subcat in subcats:
                        if isinstance(subcat, dict) and 'name' in subcat:
                            subcategory_values.add(subcat['name'])
                        elif isinstance(subcat, str):
                            subcategory_values.add(subcat)
                
                subcategory_list = sorted(list(subcategory_values))
                
                # Category dropdown
                if category_names:
                    dv = DataValidation(
                        type="list",
                        formula1=f'"{",".join(category_names)}"'
                    )
                    ws.add_data_validation(dv)
                    dv.add('C2:C1000')
                
                # Subcategory dropdown
                if subcategory_list:
                    dv2 = DataValidation(
                        type="list",
                        formula1=f'"{",".join(subcategory_list)}"'
                    )
                    ws.add_data_validation(dv2)
                    dv2.add('D2:D1000')
                
                wb.save(template_path)
            
            else:
                raise ValueError(f"Unsupported template type: {file_type}")
            
            return template_path
            
        except Exception as e:
            raise Exception(f"Error generating import template: {str(e)}")

        
    @staticmethod
    def bulk_delete_products(product_ids, hard_delete=False):
        deleted_count = 0
        failed_deletions = []
        
        # Create service instance to use existing methods
        service = ProductService()
        
        for product_id in product_ids:
            try:
                # Use your existing delete method that already works
                success = service.delete_product(product_id, hard_delete)
                if success:
                    deleted_count += 1
                else:
                    failed_deletions.append({
                        'product_id': product_id,
                        'error': 'Product not found or delete failed'
                    })
            except Exception as e:
                failed_deletions.append({
                    'product_id': product_id,
                    'error': str(e)
                })
        
        return {
            'deleted_count': deleted_count,
            'failed_count': len(failed_deletions),
            'total_requested': len(product_ids),
            'failed_deletions': failed_deletions,
            'success': deleted_count > 0
        }
    
# Add this new method to ProductService class

    def _create_initial_batch_if_needed(self, product_id, product_data):
        """Create initial batch if stock is provided during product creation"""
        try:
            initial_stock = int(product_data.get('stock', 0))
            
            # Only create batch if stock is provided and > 0
            if initial_stock > 0:
                # Validate cost_price is provided when stock is given
                cost_price = product_data.get('cost_price')
                if cost_price is None or cost_price == 0:
                    raise ValueError("Cost price is required when initial stock is provided")
                
                # Prepare batch data
                batch_data = {
                    'product_id': product_id,
                    'quantity_received': initial_stock,
                    'cost_price': float(cost_price),
                    'expiry_date': product_data.get('expiry_date'),
                    'supplier_id': product_data.get('supplier_id'),
                    'date_received': product_data.get('date_received', datetime.utcnow()),
                    'batch_number': f"INITIAL-{datetime.utcnow().strftime('%Y%m%d')}"
                }
                
                # Create the batch using batch service
                batch = self.batch_service.create_batch(batch_data)
                logger.info(f"Created initial batch {batch['_id']} for product {product_id}")
                
                return batch
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating initial batch: {str(e)}")
            raise Exception(f"Error creating initial batch: {str(e)}")
    
    def export_product_details_csv(self, product_id):
        """Export a single product and all related batch data (purchases + adjustments) into a CSV"""
        try:
            product = self.get_product_by_id(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found")

            from io import StringIO
            import csv

            # Fetch all batches for this product
            batches = list(self.db.batches.find({"product_id": product_id}))
            output = StringIO()
            writer = csv.writer(output)

            # === PRODUCT DETAILS ===
            writer.writerow(["=== PRODUCT DETAILS ==="])
            writer.writerow(["Field", "Value"])
            for key, value in product.items():
                writer.writerow([key, value])
            writer.writerow([])

            # === PURCHASE HISTORY ===
            writer.writerow(["=== PURCHASE HISTORY ==="])
            if batches:
                writer.writerow([
                    "Batch Number", "Purchase Date", "Expiry Date", "Initial Qty",
                    "Current Qty", "Unit Cost", "Total Cost", "Status"
                ])
                for batch in batches:
                    total_cost = (
                        float(batch.get("quantity_received", 0)) *
                        float(batch.get("cost_price", 0))
                    )
                    writer.writerow([
                        batch.get("batch_number", ""),
                        batch.get("date_received", ""),
                        batch.get("expiry_date", ""),
                        batch.get("quantity_received", ""),
                        batch.get("quantity_remaining", ""),
                        batch.get("cost_price", ""),
                        total_cost,
                        batch.get("status", "")
                    ])
            else:
                writer.writerow(["No batches found"])
            writer.writerow([])

            # === STOCK ADJUSTMENTS ===
            writer.writerow(["=== STOCK ADJUSTMENTS ==="])
            adjustment_rows = []
            for batch in batches:
                usage_history = batch.get("usage_history", [])
                for usage in usage_history:
                    adjustment_rows.append({
                        "timestamp": usage.get("timestamp", ""),
                        "batch_number": batch.get("batch_number", ""),
                        "type": usage.get("adjustment_type", usage.get("reason", "")),
                        "quantity": usage.get("quantity_used", ""),
                        "remaining_after": usage.get("remaining_after", ""),
                        "adjusted_by": usage.get("adjusted_by", ""),
                        "notes": usage.get("notes", "")
                    })

            if adjustment_rows:
                writer.writerow([
                    "Date & Time", "Batch Number", "Type", "Quantity",
                    "Remaining After", "Adjusted By", "Notes"
                ])
                for adj in adjustment_rows:
                    writer.writerow([
                        adj["timestamp"],
                        adj["batch_number"],
                        adj["type"],
                        adj["quantity"],
                        adj["remaining_after"],
                        adj["adjusted_by"],
                        adj["notes"]
                    ])
            else:
                writer.writerow(["No adjustments found"])
            writer.writerow([])

            # === ACTIVE BATCHES ===
            writer.writerow(["=== ACTIVE BATCHES ==="])
            if batches:
                writer.writerow(["Batch ID", "Quantity", "Cost Price", "Expiry Date", "Status"])
                for batch in batches:
                    writer.writerow([
                        batch.get("_id", ""),
                        batch.get("quantity_remaining", ""),
                        batch.get("cost_price", ""),
                        batch.get("expiry_date", ""),
                        batch.get("status", "")
                    ])
            else:
                writer.writerow(["No active batches found"])
            writer.writerow([])

            csv_content = output.getvalue()
            output.close()
            return csv_content

        except Exception as e:
            raise Exception(f"Error exporting product details to CSV: {str(e)}")

# services/product_service.py
"""
Product Service - DynamoDB Single-Table Design (RamyeonCornerDB)
Uses PynamoDB Product model exclusively.
"""
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import pandas as pd
from io import StringIO
import csv

# --- DynamoDB Models (PynamoDB) ---
from ...models.Product import Product
from ...models.Categories import Category
from ...models.Supplier import Supplier
from ...models.Branch import Branch

# --- Other Services / Utils ---
from notifications.services import notification_service
from app.utils import generate_sk

logger = logging.getLogger(__name__)


class ProductService:
    """
    ProductService - DynamoDB edition.
    All operations delegate to the Product model.
    """

    def __init__(self):
        # No database connections – everything goes through PynamoDB models.
        pass

    # ----------------------------------------------------------------------
    # VALIDATION & HELPERS
    # ----------------------------------------------------------------------

    def validate_foreign_keys(self, product_data: dict):
        """
        Validate that referenced foreign keys exist in their respective DynamoDB tables.
        Assumes that Category, Supplier, Branch models implement get_or_none().
        """
        # Category
        if 'category_id' in product_data and product_data['category_id']:
            category = Category.get_or_none(product_data['category_id'])
            if not category:
                raise ValueError(f"Category with ID {product_data['category_id']} not found")

        # Supplier (if applicable – not in current Product model, but kept for compatibility)
        if 'supplier_id' in product_data and product_data['supplier_id']:
            supplier = Supplier.get_or_none(product_data['supplier_id'])
            if not supplier:
                raise ValueError(f"Supplier with ID {product_data['supplier_id']} not found")

        # Branch (if applicable)
        if 'branch_id' in product_data and product_data['branch_id']:
            branch = Branch.get_or_none(product_data['branch_id'])
            if not branch:
                raise ValueError(f"Branch with ID {product_data['branch_id']} not found")

    def _send_product_notification(self, action_type: str, product_name: str,
                                   product_id: Optional[str] = None,
                                   additional_metadata: Optional[dict] = None):
        """Centralized notification helper – unchanged logic."""
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
        message = (additional_metadata or {}).get('custom_message') or \
                  messages.get(action_type, f"Product action '{action_type}' completed for '{product_name}'")

        # Priority based on action
        if action_type == 'stock_out':
            priority = "high"
            n_type = "alert"
        elif action_type in ('stock_low', 'hard_deleted'):
            priority = "medium"
            n_type = "alert"
        elif action_type in ('soft_deleted', 'bulk_created', 'bulk_stock_updated'):
            priority = "medium"
            n_type = "system"
        else:
            priority = "low"
            n_type = "system"

        metadata = {
            "product_id": product_id or "",
            "product_name": product_name,
            "action_type": f"product_{action_type}"
        }
        if additional_metadata:
            # Remove custom_message from metadata to avoid duplication
            filtered = {k: v for k, v in additional_metadata.items() if k != 'custom_message'}
            metadata.update(filtered)

        notification_service.create_notification(
            title=titles.get(action_type, "Product Action"),
            message=message,
            priority=priority,
            notification_type=n_type,
            metadata=metadata
        )

    def _ensure_default_category_assignment(self, product_data: dict) -> dict:
        """
        Ensure product has a category_id and subcategory_name.
        Defaults to 'UNCTGRY-001' / 'General' if missing.
        """
        if not product_data.get('category_id'):
            product_data['category_id'] = "UNCTGRY-001"
            product_data['subcategory_name'] = "General"
            logger.debug("Auto-assigned product to Uncategorized > General")
        elif not product_data.get('subcategory_name'):
            product_data['subcategory_name'] = "General"
            logger.debug("Auto-assigned subcategory to General")
        return product_data

    def generate_sku(self, product_name: str, category_id: Optional[str] = None) -> str:
        """
        Generate a unique SKU: <CATEGORY_PREFIX>-<NAME_PREFIX>-<SEQUENCE>
        Checks uniqueness against non‑deleted products.
        """
        # Get category prefix
        if category_id:
            category = Category.get_or_none(category_id)
            category_prefix = (category.category_name[:4].upper()
                               if category else "PROD")
        else:
            category_prefix = "PROD"

        # Name prefix (first two words, up to 4 chars)
        name_prefix = ''.join(product_name.split()[:2])[:4].upper() or "PROD"

        # Find next available sequence number
        count = 1
        while True:
            sku = f"{category_prefix}-{name_prefix}-{count:03d}"
            existing = Product.get_by_sku(sku, include_deleted=False)
            if not existing:
                break
            count += 1
        return sku

    @staticmethod
    def calculate_similarity(str1: str, str2: str) -> float:
        """Simple string similarity ratio."""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()

    # ----------------------------------------------------------------------
    # CORE CRUD OPERATIONS
    # ----------------------------------------------------------------------

    def create_product(self, product_data: dict) -> Optional[Product]:
        """
        Create a new product using Product.create_product().
        Handles initial stock, SKU generation, and default category.
        """
        try:
            logger.info(f"Creating product: {product_data.get('product_name', 'Unknown')}")

            # --- VALIDATION ---
            initial_stock = int(product_data.get('stock', 0) or 0)
            if initial_stock > 0:
                cost_price = product_data.get('cost_price')
                if cost_price is None or float(cost_price) <= 0:
                    raise ValueError("Cost price must be >0 when initial stock is provided")

            # Foreign keys (if models exist)
            self.validate_foreign_keys(product_data)

            # SKU generation
            if not product_data.get('SKU'):
                product_data['SKU'] = self.generate_sku(
                    product_data.get('product_name', 'Product'),
                    product_data.get('category_id')
                )
            else:
                # Ensure SKU uniqueness
                existing = Product.get_by_sku(product_data['SKU'], include_deleted=False)
                if existing:
                    raise ValueError(f"Product with SKU '{product_data['SKU']}' already exists")

            # Unique product name (case-insensitive)
            product_name = product_data.get('product_name', '').strip()
            if product_name:
                # Use search_by_name to check duplicates (exact match)
                matches = Product.search_by_name(product_name, limit=1)
                for p in matches:
                    if p.product_name.lower() == product_name.lower():
                        raise ValueError(f"Product with name '{product_name}' already exists")

            # Auto-assign category
            product_data = self._ensure_default_category_assignment(product_data)

            # Prepare kwargs for Product.create_product
            create_kwargs = {
                'product_name': product_name,
                'sku': product_data['SKU'],
                'category_id': product_data['category_id'],
                'cost_price': float(product_data.get('cost_price', 0)),
                'selling_price': float(product_data.get('selling_price', 0)),
                'unit': product_data.get('unit', 'piece'),
                'date_received': product_data.get('date_received') or datetime.utcnow(),
                'subcategory_name': product_data.get('subcategory_name', 'General'),
                'low_stock_threshold': int(product_data.get('low_stock_threshold', 10)),
                'total_stock': initial_stock,
                'barcode': product_data.get('barcode'),
                'description': product_data.get('description'),
                'image_url': product_data.get('image_url'),
                'image_filename': product_data.get('image_filename'),
                'image_size': product_data.get('image_size'),
                'image_type': product_data.get('image_type'),
                'status': product_data.get('status', 'active'),
                'is_taxable': product_data.get('is_taxable', True),
                'oldest_batch_expiry': product_data.get('oldest_batch_expiry'),
                'newest_batch_expiry': product_data.get('newest_batch_expiry'),
                'expiry_alert': product_data.get('expiry_alert', False),
            }
            # Remove None values so defaults are used
            create_kwargs = {k: v for k, v in create_kwargs.items() if v is not None}

            product = Product.create_product(**create_kwargs)

            # If expiry date is provided directly, update expiry info accordingly
            if product_data.get('expiry_date') and initial_stock > 0:
                expiry_str = product_data['expiry_date']
                if isinstance(expiry_str, datetime):
                    expiry_str = expiry_str.isoformat()
                product.update_expiry_info(expiry_str, expiry_str)

            # Send notification
            self._send_product_notification(
                'created',
                product.product_name,
                product.sk,
                {
                    "SKU": product.SKU,
                    "category_id": product.category_id,
                    "subcategory_name": product.subcategory_name,
                    "initial_stock": initial_stock
                }
            )
            return product

        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            raise

    def get_all_products(self, filters: Optional[dict] = None,
                         include_deleted: bool = False,
                         include_images: bool = True) -> List[Product]:
        """
        Retrieve products based on filters.
        Delegates to Product model's query/index methods.
        """
        try:
            # Start with base query: all products (active or all)
            if include_deleted:
                # No direct method; we scan and filter later (acceptable for small scale)
                products = list(Product.query("products"))
            else:
                products = Product.get_all_active_products()

            # Apply filters
            if filters:
                # Category filter
                if filters.get('category_id'):
                    products = [p for p in products if p.category_id == filters['category_id']]
                # Subcategory filter
                if filters.get('subcategory_name'):
                    products = [p for p in products if p.subcategory_name == filters['subcategory_name']]
                # Status filter
                if filters.get('status'):
                    products = [p for p in products if p.status == filters['status']]
                # Stock level filter
                if filters.get('stock_level'):
                    if filters['stock_level'] == 'out_of_stock':
                        products = [p for p in products if p.total_stock == 0]
                    elif filters['stock_level'] == 'low_stock':
                        products = [p for p in products if
                                    p.low_stock_threshold and p.total_stock <= p.low_stock_threshold]
                # Search filter
                if filters.get('search'):
                    term = filters['search']
                    searched = Product.search_by_name(term, limit=100)
                    searched_ids = {p.sk for p in searched}
                    products = [p for p in products if p.sk in searched_ids]

            # Exclude image fields if not needed (PynamoDB doesn't support projection easily,
            # but we can omit from to_dict later. Here we just return full objects.)
            return products

        except Exception as e:
            logger.error(f"Error getting products: {str(e)}")
            return []

    def get_product_by_id(self, product_id: str,
                          include_deleted: bool = False) -> Optional[Product]:
        """Get a single product by its ID (PROD-#####)."""
        return Product.get_by_id(product_id, include_deleted)

    def get_product_by_sku(self, sku: str,
                           include_deleted: bool = False) -> Optional[Product]:
        """Get product by SKU using GSI."""
        return Product.get_by_sku(sku, include_deleted)

    def update_product(self, product_id: str,
                       product_data: dict) -> Optional[Product]:
        """Update product attributes using model's update_product method."""
        try:
            product = self.get_product_by_id(product_id, include_deleted=False)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found or deleted")

            # Validate foreign keys if they are being changed
            fk_fields = {}
            if 'category_id' in product_data:
                fk_fields['category_id'] = product_data['category_id']
            if 'supplier_id' in product_data:
                fk_fields['supplier_id'] = product_data['supplier_id']
            if 'branch_id' in product_data:
                fk_fields['branch_id'] = product_data['branch_id']
            if fk_fields:
                self.validate_foreign_keys(fk_fields)

            # Convert numeric fields
            for field in ['low_stock_threshold', 'cost_price', 'selling_price']:
                if field in product_data:
                    if field == 'low_stock_threshold':
                        product_data[field] = int(product_data[field])
                    else:
                        product_data[field] = float(product_data[field])

            # Call model's update method
            updated_product = product.update_product(**product_data)

            self._send_product_notification(
                'updated',
                updated_product.product_name,
                updated_product.sk,
                {
                    "SKU": updated_product.SKU,
                    "updated_fields": list(product_data.keys())
                }
            )
            return updated_product

        except Exception as e:
            logger.error(f"Error updating product {product_id}: {str(e)}")
            raise

    def delete_product(self, product_id: str, hard_delete: bool = False) -> bool:
        """
        Soft delete (default) or hard delete a product.
        Hard delete permanently removes the item from DynamoDB.
        """
        try:
            product = self.get_product_by_id(product_id, include_deleted=True)
            if not product:
                return False

            if hard_delete:
                # Permanently delete the DynamoDB item
                product.delete()
                self._send_product_notification(
                    'hard_deleted',
                    product.product_name,
                    product.sk,
                    {
                        "SKU": product.SKU,
                        "deletion_type": "permanent",
                        "stock_at_deletion": product.total_stock
                    }
                )
                return True
            else:
                # Soft delete using model method
                # (deleted_by and reason are required; we use placeholder values)
                product.soft_delete(deleted_by="system", reason="Manual deletion")
                self._send_product_notification(
                    'soft_deleted',
                    product.product_name,
                    product.sk,
                    {
                        "SKU": product.SKU,
                        "deletion_type": "soft",
                        "deleted_at": datetime.utcnow().isoformat(),
                        "can_be_restored": True
                    }
                )
                return True

        except Exception as e:
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            return False

    def restore_product(self, product_id: str) -> bool:
        """Restore a soft-deleted product."""
        try:
            product = Product.get_by_id(product_id, include_deleted=True)
            if not product or not product.isDeleted:
                return False

            product.restore(restored_by="system")
            self._send_product_notification(
                'restored',
                product.product_name,
                product.sk,
                {"SKU": product.SKU}
            )
            return True
        except Exception as e:
            logger.error(f"Error restoring product {product_id}: {str(e)}")
            return False

    # ----------------------------------------------------------------------
    # STOCK MANAGEMENT (NO SEPARATE BATCHES)
    # ----------------------------------------------------------------------

    def update_stock(self, product_id: str, stock_data: dict) -> Optional[Product]:
        """
        Update product stock using model.update_stock().
        stock_data must contain 'operation_type' and 'quantity'.
        """
        try:
            product = self.get_product_by_id(product_id, include_deleted=False)
            if not product:
                raise ValueError(f"Product {product_id} not found or deleted")

            operation = stock_data.get('operation_type', 'set')
            quantity = int(stock_data.get('quantity', 0))
            reason = stock_data.get('reason', 'Manual adjustment')

            # Convert operation to quantity_change
            if operation == 'add':
                change = quantity
            elif operation == 'remove':
                change = -quantity
            elif operation == 'set':
                # set absolute stock: calculate difference
                change = quantity - product.total_stock
            else:
                raise ValueError(f"Invalid operation type: {operation}")

            # Determine source (default: 'manual')
            source = stock_data.get('source', 'manual')
            terminal_id = stock_data.get('terminal_id')
            transaction_id = stock_data.get('transaction_id')

            # Execute stock update
            updated = product.update_stock(
                quantity_change=change,
                source=source,
                terminal_id=terminal_id,
                transaction_id=transaction_id,
                reason=reason
            )

            # Send notification with stock status
            action_type = 'stock_updated'
            if updated.total_stock == 0:
                action_type = 'stock_out'
            elif updated.low_stock_threshold and updated.total_stock <= updated.low_stock_threshold:
                action_type = 'stock_low'

            self._send_product_notification(
                action_type,
                updated.product_name,
                updated.sk,
                {
                    "SKU": updated.SKU,
                    "operation_type": operation,
                    "quantity_changed": change,
                    "previous_stock": product.total_stock,
                    "new_stock": updated.total_stock,
                    "reason": reason,
                    "stock_status": updated.get_stock_status()
                }
            )
            return updated

        except Exception as e:
            logger.error(f"Error updating stock for {product_id}: {str(e)}")
            raise

    def bulk_update_stock(self, stock_updates: List[dict]) -> List[dict]:
        """Batch stock update for multiple products."""
        results = []
        successful = 0
        failed = 0
        for update in stock_updates:
            product_id = update.get('product_id')
            try:
                result = self.update_stock(product_id, update)
                results.append({
                    'product_id': product_id,
                    'success': True,
                    'new_stock': result.total_stock if result else None
                })
                successful += 1
            except Exception as e:
                results.append({
                    'product_id': product_id,
                    'success': False,
                    'error': str(e)
                })
                failed += 1

        self._send_product_notification(
            'bulk_stock_updated',
            f"{successful} products",
            None,
            {
                "total_products": len(stock_updates),
                "successful_updates": successful,
                "failed_updates": failed,
                "success_rate": round(successful / len(stock_updates) * 100, 2) if stock_updates else 0
            }
        )
        return results

    def adjust_stock_for_sale(self, product_id: str, quantity_sold: int) -> Product:
        """Reduce stock for a sale transaction (FIFO no longer tracked)."""
        stock_data = {
            'operation_type': 'remove',
            'quantity': quantity_sold,
            'reason': 'Sale transaction',
            'source': 'pos'
        }
        return self.update_stock(product_id, stock_data)

    def restock_product(self, product_id: str, quantity_received: int,
                        supplier_info: Optional[dict] = None,
                        batch_info: Optional[dict] = None) -> Product:
        """
        Add stock and optionally update expiry information.
        batch_info may contain 'expiry_date', 'cost_price' (overrides product cost?).
        """
        product = self.get_product_by_id(product_id, include_deleted=False)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        # Update stock
        stock_data = {
            'operation_type': 'add',
            'quantity': quantity_received,
            'reason': f"Restock from {supplier_info.get('name', 'Unknown') if supplier_info else 'supplier'}",
            'source': 'inventory'
        }
        updated = self.update_stock(product_id, stock_data)

        # If batch expiry info is provided, update product's batch expiry fields
        if batch_info and batch_info.get('expiry_date'):
            expiry_date = batch_info['expiry_date']
            if isinstance(expiry_date, datetime):
                expiry_date = expiry_date.isoformat()

            # Determine new oldest/newest expiry
            oldest = updated.oldest_batch_expiry
            newest = updated.newest_batch_expiry
            if not oldest or expiry_date < oldest:
                oldest = expiry_date
            if not newest or expiry_date > newest:
                newest = expiry_date

            updated.update_expiry_info(oldest, newest)

        return updated

    def get_product_with_batch_summary(self, product_id: str) -> Optional[Product]:
        """
        Return product with its expiry fields (no separate batch list now).
        """
        product = self.get_product_by_id(product_id)
        return product

    def check_expiry_alerts(self, days_ahead: int = 7) -> List[Product]:
        """
        Get products that are expiring within the given days.
        """
        return Product.get_expiring_soon_products(days=days_ahead)

    # ----------------------------------------------------------------------
    # PRODUCT QUERIES & FILTERING
    # ----------------------------------------------------------------------

    def get_deleted_products(self) -> List[Product]:
        """Get all soft-deleted products."""
        # Use query with filter on isDeleted (scan, but limited scope)
        return list(Product.query(
            "products",
            filter_condition=Product.isDeleted == True
        ))

    def get_low_stock_products(self, branch_id: Optional[str] = None) -> List[Product]:
        """
        Get products with stock below threshold.
        Branch filtering is not supported by the Product model; ignore branch_id.
        """
        return Product.get_low_stock_products()

    def get_products_by_category(self, category_id: str,
                                 subcategory_name: Optional[str] = None) -> List[Product]:
        """Query products using Category GSI."""
        return Product.query_by_category(category_id, status="active")

    def get_expiring_products(self, days_ahead: int = 30) -> List[Product]:
        """Alias for check_expiry_alerts."""
        return self.check_expiry_alerts(days_ahead)

    # ----------------------------------------------------------------------
    # BULK OPERATIONS
    # ----------------------------------------------------------------------

    def bulk_create_products(self, products_data: List[dict]) -> dict:
        """
        Create multiple products in a loop.
        Returns summary with successes and failures.
        """
        successful = []
        errors = []
        for idx, data in enumerate(products_data):
            try:
                product = self.create_product(data)
                successful.append(product.to_dict())
            except Exception as e:
                errors.append({
                    'index': idx,
                    'data': data,
                    'error': str(e)
                })

        self._send_product_notification(
            'bulk_created',
            f"{len(successful)} products",
            None,
            {
                "total_products": len(products_data),
                "successful_creations": len(successful),
                "failed_creations": len(errors),
                "success_rate": round(len(successful) / len(products_data) * 100, 2) if products_data else 0
            }
        )

        return {
            'successful': successful,
            'failed': errors,
            'total_processed': len(products_data),
            'total_successful': len(successful),
            'total_failed': len(errors)
        }

    @staticmethod
    def bulk_delete_products(product_ids: List[str], hard_delete: bool = False) -> dict:
        """Bulk soft/hard delete using the service instance."""
        service = ProductService()
        deleted_count = 0
        failed = []
        for pid in product_ids:
            try:
                success = service.delete_product(pid, hard_delete)
                if success:
                    deleted_count += 1
                else:
                    failed.append({'product_id': pid, 'error': 'Delete returned False'})
            except Exception as e:
                failed.append({'product_id': pid, 'error': str(e)})

        return {
            'deleted_count': deleted_count,
            'failed_count': len(failed),
            'total_requested': len(product_ids),
            'failed_deletions': failed,
            'success': deleted_count > 0
        }

    # ----------------------------------------------------------------------
    # SYNC METHODS (POS / LOCAL) – delegated to Product model
    # ----------------------------------------------------------------------

    def prepare_for_sync_to_local(self) -> List[Product]:
        """Get products pending POS sync (to be pushed to local)."""
        return Product.get_products_needing_pos_sync()

    def prepare_for_sync_to_cloud(self) -> List[Product]:
        """Not applicable in pure cloud DynamoDB setup – kept for interface."""
        return []  # No local DB

    def sync_from_local(self, local_products: List[dict]) -> List[dict]:
        """
        Sync products from a local (MongoDB) source into DynamoDB.
        This method is kept for legacy integration but not actively used.
        """
        results = []
        for prod_data in local_products:
            try:
                # Attempt update first, then create
                if prod_data.get('_id'):
                    existing = Product.get_by_id(prod_data['_id'])
                    if existing:
                        existing.update_product(**prod_data)
                        results.append({'product_id': existing.sk, 'status': 'updated'})
                    else:
                        prod_data.pop('_id', None)  # let model generate new ID
                        product = self.create_product(prod_data)
                        results.append({'product_id': product.sk, 'status': 'created'})
                else:
                    product = self.create_product(prod_data)
                    results.append({'product_id': product.sk, 'status': 'created'})
            except Exception as e:
                results.append({'product_id': prod_data.get('_id'), 'status': 'error', 'error': str(e)})
        return results

    def sync_to_local(self) -> List[Product]:
        """Alias for prepare_for_sync_to_local."""
        return self.prepare_for_sync_to_local()

    # ----------------------------------------------------------------------
    # IMPORT / EXPORT
    # ----------------------------------------------------------------------

    def import_products_from_file(self, file_path: str, file_type: str = 'csv',
                                  validate_only: bool = False) -> dict:
        """
        Import products from CSV/Excel file.
        This method does NOT use DynamoDB directly; it only prepares data
        and then calls create_product().
        """
        try:
            # Read file
            if file_type == 'csv':
                df = pd.read_csv(file_path)
            elif file_type in ('xlsx', 'xls'):
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Required columns (supplier removed)
            required_columns = ['product_name', 'selling_price', 'category_name']
            missing = [c for c in required_columns if c not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")

            validation_errors = []
            valid_products = []
            missing_categories = {}

            for idx, row in df.iterrows():
                row_num = idx + 2
                errors = []

                # --- Required fields ---
                if pd.isna(row.get('product_name')) or not str(row['product_name']).strip():
                    errors.append(f"Row {row_num}: Product name is required")

                if pd.isna(row.get('selling_price')) or float(row['selling_price']) <= 0:
                    errors.append(f"Row {row_num}: Selling price must be >0")

                # Category lookup
                category_name = str(row.get('category_name', '')).strip()
                if not category_name:
                    errors.append(f"Row {row_num}: Category name is required")
                else:
                    # Find category ID by name (requires Category model)
                    # Assuming Category has a classmethod get_by_name that returns the Category item
                    category = Category.get_by_name(category_name)
                    if not category:
                        missing_categories.setdefault(category_name, set())
                        if not pd.isna(row.get('subcategory_name')):
                            missing_categories[category_name].add(str(row['subcategory_name']).strip())
                        errors.append(f"Row {row_num}: Category '{category_name}' not found")
                        category_id = None
                    else:
                        category_id = category.sk  # primary key of the category
                        # Validate subcategory if provided
                        subcat = row.get('subcategory_name')
                        if not pd.isna(subcat) and str(subcat).strip():
                            # Retrieve subcategories list from category; assume category.sub_categories is a list of names
                            subcats = category.get('sub_categories', [])
                            if isinstance(subcats, list) and str(subcat).strip() not in subcats:
                                missing_categories.setdefault(category_name, set())
                                missing_categories[category_name].add(str(subcat).strip())
                                errors.append(f"Row {row_num}: Subcategory '{subcat}' not found under category '{category_name}'")

                # Stock / cost / expiry validation
                stock = row.get('stock', 0)
                if not pd.isna(stock) and float(stock) > 0:
                    cost = row.get('cost_price')
                    if pd.isna(cost) or float(cost) <= 0:
                        errors.append(f"Row {row_num}: Cost price is required when stock > 0")
                    expiry = row.get('expiry_date')
                    if pd.isna(expiry) or not str(expiry).strip():
                        errors.append(f"Row {row_num}: Expiry date is required when stock > 0")

                # Numeric validations
                for field, cast in [('selling_price', float), ('cost_price', float),
                                    ('stock', int), ('low_stock_threshold', int)]:
                    if field in row and not pd.isna(row[field]):
                        try:
                            cast(row[field])
                        except:
                            errors.append(f"Row {row_num}: {field} must be a valid number")

                if errors:
                    validation_errors.extend(errors)
                    continue

                # Build product data dict
                product_data = {
                    'product_name': str(row['product_name']).strip(),
                    'selling_price': float(row['selling_price']),
                    'category_id': category_id,
                    'subcategory_name': (str(row['subcategory_name']).strip()
                                         if not pd.isna(row.get('subcategory_name')) else 'General'),
                    'stock': int(row['stock']) if not pd.isna(row.get('stock')) else 0,
                    'cost_price': float(row['cost_price']) if not pd.isna(row.get('cost_price')) else 0,
                    'unit': str(row.get('unit', 'piece')).strip(),
                    'low_stock_threshold': int(row.get('low_stock_threshold', 10)),
                    'status': str(row.get('status', 'active')).strip(),
                    'barcode': str(row['barcode']).strip() if not pd.isna(row.get('barcode')) else None,
                    'description': str(row['description']).strip() if not pd.isna(row.get('description')) else None,
                    'expiry_date': row['expiry_date'] if not pd.isna(row.get('expiry_date')) else None,
                }
                if not pd.isna(row.get('SKU')):
                    product_data['SKU'] = str(row['SKU']).strip()

                valid_products.append(product_data)

            # Summary of missing categories
            missing_cats_list = [
                {'category_name': cat, 'subcategories': list(subcats)}
                for cat, subcats in missing_categories.items()
            ]

            if validate_only:
                return {
                    'valid': len(validation_errors) == 0 and len(missing_categories) == 0,
                    'total_rows': len(df),
                    'valid_products': len(valid_products),
                    'errors': validation_errors,
                    'missing_categories': missing_cats_list
                }

            if validation_errors:
                return {
                    'success': False,
                    'total_rows': len(df),
                    'valid_products': len(valid_products),
                    'errors': validation_errors,
                    'missing_categories': missing_cats_list,
                    'message': f'Import failed: {len(validation_errors)} validation error(s)'
                }

            # Perform actual import
            successful = []
            failed = []
            for prod_data in valid_products:
                try:
                    new_prod = self.create_product(prod_data)
                    successful.append(new_prod.to_dict())
                except Exception as e:
                    failed.append({
                        'product': prod_data.get('product_name', 'Unknown'),
                        'error': str(e)
                    })

            self._send_product_notification(
                'import_completed',
                f"{len(successful)} products",
                None,
                {
                    "total_rows": len(df),
                    "successful": len(successful),
                    "failed": len(failed),
                    "custom_message": f'Import completed: {len(successful)} created, {len(failed)} failed'
                }
            )

            return {
                'success': True,
                'total_rows': len(df),
                'successful': len(successful),
                'failed': len(failed),
                'failed_details': failed,
                'missing_categories': missing_cats_list,
                'message': f'Import completed: {len(successful)} created, {len(failed)} failed'
            }

        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            raise

    def generate_import_template(self, file_type: str = 'csv') -> str:
        """
        Generate a CSV/Excel template for product import.
        Includes category and subcategory dropdowns for Excel.
        """
        try:
            import pandas as pd
            from openpyxl import load_workbook
            from openpyxl.worksheet.datavalidation import DataValidation

            # Template data
            template_data = {
                'product_name': ['Sample Noodle 1', 'Sample Drink 1'],
                'SKU': ['', ''],  # leave blank for auto-generation
                'category_name': ['Noodles', 'Drinks'],
                'subcategory_name': ['Instant', 'Beverages'],
                'stock': [100, 50],
                'low_stock_threshold': [10, 5],
                'cost_price': [15.00, 25.00],
                'selling_price': [20.00, 30.00],
                'unit': ['piece', 'bottle'],
                'expiry_date': ['2025-12-31', '2025-06-30'],
                'status': ['active', 'active'],
                'barcode': ['123456789', '987654321'],
                'description': ['Instant noodles', 'Soft drink']
            }

            df = pd.DataFrame(template_data)

            if file_type.lower() == 'csv':
                template_path = 'product_import_template.csv'
                df.to_csv(template_path, index=False)
                logger.info(f"CSV template generated: {template_path}")

            elif file_type.lower() == 'xlsx':
                template_path = 'product_import_template.xlsx'
                df.to_excel(template_path, index=False, engine='openpyxl')

                # Add data validation for category and subcategory
                wb = load_workbook(template_path)
                ws = wb.active

                # Fetch all categories from DynamoDB (using Category model)
                categories = list(Category.query("categories"))  # adjust PK if needed
                category_names = [cat.category_name for cat in categories]

                # Build subcategory mapping
                subcategory_values = set()
                for cat in categories:
                    subcats = cat.sub_categories if hasattr(cat, 'sub_categories') else []
                    if isinstance(subcats, list):
                        for subcat in subcats:
                            if isinstance(subcat, dict) and 'name' in subcat:
                                subcategory_values.add(subcat['name'])
                            elif isinstance(subcat, str):
                                subcategory_values.add(subcat)

                subcategory_list = sorted(subcategory_values)

                # Category dropdown (column C)
                if category_names:
                    dv_cat = DataValidation(
                        type="list",
                        formula1=f'"{",".join(category_names)}"',
                        allow_blank=False
                    )
                    ws.add_data_validation(dv_cat)
                    dv_cat.add('C2:C1000')

                # Subcategory dropdown (column D)
                if subcategory_list:
                    dv_sub = DataValidation(
                        type="list",
                        formula1=f'"{",".join(subcategory_list)}"',
                        allow_blank=True
                    )
                    ws.add_data_validation(dv_sub)
                    dv_sub.add('D2:D1000')

                # Save workbook
                wb.save(template_path)
                logger.info(f"Excel template generated: {template_path}")

            else:
                raise ValueError(f"Unsupported template type: {file_type}")

            return template_path

        except Exception as e:
            logger.error(f"Error generating import template: {str(e)}")
            raise

    def export_product_details_csv(self, product_id: str) -> str:
        """
        Export a single product's details to CSV.
        Since batch/adjustment history is no longer stored separately,
        we only export product attributes.
        """
        product = self.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        output = StringIO()
        writer = csv.writer(output)

        # Product details
        writer.writerow(["=== PRODUCT DETAILS ==="])
        writer.writerow(["Field", "Value"])
        prod_dict = product.to_dict()
        for key, value in prod_dict.items():
            writer.writerow([key, value])

        writer.writerow([])
        writer.writerow(["=== BATCH SUMMARY (Expiry Information) ==="])
        writer.writerow(["Oldest Batch Expiry", product.oldest_batch_expiry])
        writer.writerow(["Newest Batch Expiry", product.newest_batch_expiry])
        writer.writerow(["Expiry Alert", product.expiry_alert])

        csv_content = output.getvalue()
        output.close()
        return csv_content
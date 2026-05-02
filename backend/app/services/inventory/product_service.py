from models.Product import Product
from models.Batches import Batch
from models.Categories import Category
from pynamodb.exceptions import DoesNotExist, PutError, DeleteError, UpdateError
from app.utils.singleton import get_singleton
import base64
import json
import logging

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def _encode_page_token(last_evaluated_key: dict) -> str:
    """Encode DynamoDB last_evaluated_key for use as URL-safe page_token."""
    if not last_evaluated_key:
        return ""
    return base64.urlsafe_b64encode(json.dumps(last_evaluated_key).encode()).decode()


def _decode_page_token(page_token: str):
    """Decode page_token back to last_evaluated_key dict, or None if invalid."""
    if not page_token:
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(page_token.encode()).decode())
    except Exception:
        return None

class ProductService:
    """
    Service layer for interacting with the Product model (DynamoDB).
    Provides basic CRUD operations.
    """

    @staticmethod
    def create_product(data: dict):
        """
        Creates a new product.
        
        Args:
            data (dict): A dictionary containing product attributes. 
                         Must match the arguments for Product.create_product.
                         Required keys: product_name, sku, category_id, cost_price, selling_price, unit.
        
        Returns:
            Product: The created product object.
        
        Raises:
            ValueError: If required data is missing or if creation fails.
        """
        try:
            normalized = dict(data)
            # Frontend sends 'SKU' (uppercase); model expects 'sku' (lowercase)
            if 'SKU' in normalized and 'sku' not in normalized:
                normalized['sku'] = normalized.pop('SKU')
            # Strip fields that don't belong on the Product model:
            # - stock/expiry_date: managed via batches
            # - date_received/supplier_id/batch_number: batch-level fields sent by legacy frontend
            # - image_uploaded_at: never a model attribute
            for key in ('stock', 'expiry_date', 'date_received', 'supplier_id', 'batch_number', 'image_uploaded_at'):
                normalized.pop(key, None)
            product = Product.create_product(**normalized)
            logger.info(f"Successfully created product {product.sk}")
            Category.adjust_subcategory_count(product.category_id, product.subcategory_name, +1)
            return product
        except (PutError, ValueError) as e:
            logger.error(f"Error creating product: {str(e)}")
            raise ValueError(f"Could not create product: {str(e)}") from e

    @staticmethod
    def get_product_by_id(product_id: str, include_deleted: bool = False):
        """
        Retrieves a single product by its ID (e.g., 'PROD-00001').

        Args:
            product_id (str): The unique identifier of the product.
            include_deleted (bool): If True, return soft-deleted products. Default False.

        Returns:
            Product: The found product object, or None if not found.
        """
        try:
            product = Product.get_by_id(product_id, include_deleted=include_deleted)
            return product
        except DoesNotExist:
            logger.warning(f"Product with ID {product_id} not found.")
            return None
        except Exception as e:
            logger.error(f"Error retrieving product {product_id}: {str(e)}")
            raise

    @staticmethod
    def get_all_products():
        """
        Retrieves all active (not soft-deleted) products.

        Returns:
            list[Product]: A list of all active product objects.
        """
        try:
            return Product.get_all_active_products()
        except Exception as e:
            logger.error(f"Error retrieving all products: {str(e)}")
            return []

    @staticmethod
    def get_products_paginated(page_size: int = DEFAULT_PAGE_SIZE, page_token: str = None):
        """
        Retrieves a page of all non-deleted products for the admin list.
        Returns active, low_stock, and out_of_stock products — everything
        except soft-deleted items.
        Only fetches one page from DynamoDB (no full load).

        Returns:
            tuple: (list of Product, next_page_token or None).
        """
        try:
            size = min(max(1, int(page_size)), MAX_PAGE_SIZE)
            last_key = _decode_page_token(page_token)
            products, next_key = Product.get_all_non_deleted_paginated(limit=size, last_evaluated_key=last_key)
            next_token = _encode_page_token(next_key) if next_key else None
            return products, next_token
        except Exception as e:
            logger.error(f"Error retrieving paginated products: {str(e)}")
            return [], None

    @staticmethod
    def get_products_by_status_paginated(status: str, page_size: int = DEFAULT_PAGE_SIZE, page_token: str = None):
        """One page of products by status; only fetches one page from DynamoDB."""
        try:
            size = min(max(1, int(page_size)), MAX_PAGE_SIZE)
            last_key = _decode_page_token(page_token)
            products, next_key = Product.query_by_status_paginated(status=status, limit=size, last_evaluated_key=last_key)
            next_token = _encode_page_token(next_key) if next_key else None
            return products, next_token
        except Exception as e:
            logger.error(f"Error retrieving paginated products by status: {str(e)}")
            return [], None

    @staticmethod
    def get_products_by_category_paginated(category_id: str, page_size: int = DEFAULT_PAGE_SIZE, page_token: str = None, status: str = "active"):
        """One page of products by category; only fetches one page from DynamoDB."""
        try:
            size = min(max(1, int(page_size)), MAX_PAGE_SIZE)
            last_key = _decode_page_token(page_token)
            products, next_key = Product.query_by_category_paginated(
                category_id=category_id, status=status, limit=size, last_evaluated_key=last_key
            )
            next_token = _encode_page_token(next_key) if next_key else None
            return products, next_token
        except Exception as e:
            logger.error(f"Error retrieving paginated products by category: {str(e)}")
            return [], None

    @staticmethod
    def search_products_by_name_paginated(search_term: str, page_size: int = DEFAULT_PAGE_SIZE, page_token: str = None):
        """One page of search results by name; fetches in chunks from DynamoDB (no full table load)."""
        try:
            size = min(max(1, int(page_size)), MAX_PAGE_SIZE)
            last_key = _decode_page_token(page_token)
            products, next_key = Product.search_products_by_name_paginated(
                search_term=search_term, limit=size, last_evaluated_key=last_key
            )
            next_token = _encode_page_token(next_key) if next_key else None
            return products, next_token
        except Exception as e:
            logger.error(f"Error in search_products_by_name_paginated: {str(e)}")
            return [], None

    # ========== LOOKUP HELPERS ==========

    @staticmethod
    def get_product_by_sku(sku: str):
        """
        Retrieve a single product by SKU using the SKU GSI.
        """
        try:
            return Product.get_by_sku(sku)
        except Exception as e:
            logger.error(f"Error retrieving product with SKU {sku}: {str(e)}")
            return None

    @staticmethod
    def get_product_by_barcode(barcode: str, include_deleted: bool = False):
        """
        Retrieve a single product by barcode.
        """
        try:
            return Product.get_by_barcode(barcode, include_deleted=include_deleted)
        except Exception as e:
            logger.error(f"Error retrieving product with barcode {barcode}: {str(e)}")
            return None

    @staticmethod
    def sku_exists(sku: str) -> bool:
        """
        Check if a product with the given SKU already exists.
        """
        try:
            return Product.sku_exists(sku)
        except Exception as e:
            logger.error(f"Error checking SKU existence for {sku}: {str(e)}")
            return False

    @staticmethod
    def barcode_exists(barcode: str) -> bool:
        """
        Check if a product with the given barcode already exists.
        """
        try:
            return Product.barcode_exists(barcode)
        except Exception as e:
            logger.error(f"Error checking barcode existence for {barcode}: {str(e)}")
            return False

    @staticmethod
    def update_product(product_id: str, data: dict):
        """
        Updates an existing product.

        Args:
            product_id (str): The ID of the product to update.
            data (dict): A dictionary with the fields to update.

        Returns:
            Product: The updated product object.

        Raises:
            ValueError: If the product is not found or the update fails.
        """
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        old_category_id = product.category_id
        old_subcategory_name = product.subcategory_name

        try:
            # The update_product method in the model handles the update logic
            product.update_product(**data)
            logger.info(f"Successfully updated product {product_id}")

            new_category_id = data.get('category_id', old_category_id)
            new_subcategory_name = data.get('subcategory_name', old_subcategory_name)
            if old_category_id != new_category_id or old_subcategory_name != new_subcategory_name:
                Category.adjust_subcategory_count(old_category_id, old_subcategory_name, -1)
                Category.adjust_subcategory_count(new_category_id, new_subcategory_name, +1)

            # Re-fetch the instance to ensure the returned object is up-to-date
            return ProductService.get_product_by_id(product_id)
        except UpdateError as e:
            logger.error(f"Error updating product {product_id}: {str(e)}")
            raise ValueError(f"Could not update product: {str(e)}") from e

    # ========== QUERY HELPERS ==========

    @staticmethod
    def search_products_by_name(search_term: str, limit: int = 20):
        """
        Search products by (partial, case-insensitive) name.
        """
        try:
            return Product.search_by_name(search_term=search_term, limit=limit)
        except Exception as e:
            logger.error(f"Error searching products by name '{search_term}': {str(e)}")
            return []

    @staticmethod
    def get_products_by_category(category_id: str, status: str = "active"):
        """
        Get products by category.
        """
        try:
            return Product.query_by_category(category_id=category_id, status=status)
        except Exception as e:
            logger.error(f"Error querying products by category {category_id}: {str(e)}")
            return []

    @staticmethod
    def get_products_by_status(status: str, include_deleted: bool = False):
        """
        Get products by status.
        """
        try:
            return Product.query_by_status(status=status, include_deleted=include_deleted)
        except Exception as e:
            logger.error(f"Error querying products by status {status}: {str(e)}")
            return []

    @staticmethod
    def get_low_stock_products():
        """
        Get products that are at or below their low stock threshold.
        """
        try:
            return Product.get_low_stock_products()
        except Exception as e:
            logger.error(f"Error retrieving low stock products: {str(e)}")
            return []

    @staticmethod
    def get_out_of_stock_products():
        """
        Get products that are out of stock.
        """
        try:
            return Product.get_out_of_stock_products()
        except Exception as e:
            logger.error(f"Error retrieving out of stock products: {str(e)}")
            return []

    @staticmethod
    def get_expiring_soon_products(days: int = 30):
        """
        Get products with batches expiring within the next `days` days.
        """
        try:
            return Product.get_expiring_soon_products(days=days)
        except Exception as e:
            logger.error(f"Error retrieving expiring soon products (days={days}): {str(e)}")
            return []

    @staticmethod
    def get_products_needing_pos_sync():
        """
        Get products that need to be synced with POS.
        """
        try:
            return Product.get_products_needing_pos_sync()
        except Exception as e:
            logger.error(f"Error retrieving products needing POS sync: {str(e)}")
            return []

    @staticmethod
    def get_product_count() -> int:
        """
        Get total number of active products.
        """
        try:
            return Product.get_product_count()
        except Exception as e:
            logger.error(f"Error getting product count: {str(e)}")
            return 0

    @staticmethod
    def delete_product(product_id: str, hard_delete: bool = False, deleted_by: str = "system", reason: str = "Deleted via service"):
        """
        Deletes a product, either by soft-deleting or permanently removing it.

        Args:
            product_id (str): The ID of the product to delete.
            hard_delete (bool): If True, permanently delete the product. 
                                If False (default), soft-delete the product.
            deleted_by (str): Identifier for who performed the deletion (for soft-delete).
            reason (str): Reason for the deletion (for soft-delete).


        Returns:
            bool: True if deletion was successful, False otherwise.
        
        Raises:
            ValueError: If the product is not found.
        """
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        category_id = product.category_id
        subcategory_name = product.subcategory_name

        try:
            if hard_delete:
                product.delete()
                logger.info(f"Successfully hard-deleted product {product_id}")
            else:
                product.soft_delete(deleted_by=deleted_by, reason=reason)
                logger.info(f"Successfully soft-deleted product {product_id}")
            Category.adjust_subcategory_count(category_id, subcategory_name, -1)
            return True
        except (DeleteError, UpdateError, ValueError) as e:
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            return False

    @staticmethod
    def bulk_delete_products(product_ids: list, hard_delete: bool = False, deleted_by: str = "system", reason: str = "Bulk deleted via service") -> dict:
        """
        Delete multiple products in one call.

        Returns:
            dict: { success, deleted_count, failed_count, failed_ids }
        """
        deleted, failed = 0, []
        for product_id in product_ids:
            try:
                ok = ProductService.delete_product(
                    product_id,
                    hard_delete=hard_delete,
                    deleted_by=deleted_by,
                    reason=reason,
                )
                if ok:
                    deleted += 1
                else:
                    failed.append(product_id)
            except Exception as e:
                logger.error(f"bulk_delete_products: failed for {product_id}: {e}")
                failed.append(product_id)

        return {
            "success": len(failed) == 0,
            "deleted_count": deleted,
            "failed_count": len(failed),
            "failed_ids": failed,
        }

    # ========== STOCK & METADATA HELPERS ==========

    @staticmethod
    def update_stock_by_id(product_id: str, quantity_change: int, source: str = "manual",
                           terminal_id: str | None = None, transaction_id: str | None = None,
                           reason: str | None = None):
        """
        Update stock for a product identified by product_id.
        """
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        try:
            return product.update_stock(
                quantity_change=quantity_change,
                source=source,
                terminal_id=terminal_id,
                transaction_id=transaction_id,
                reason=reason,
            )
        except Exception as e:
            logger.error(f"Error updating stock for product {product_id}: {str(e)}")
            raise

    @staticmethod
    def update_stock_by_sku(sku: str, quantity_change: int, source: str = "manual",
                            terminal_id: str | None = None, transaction_id: str | None = None,
                            reason: str | None = None):
        """
        Update stock for a product identified by SKU.
        """
        product = ProductService.get_product_by_sku(sku)
        if not product:
            raise ValueError(f"Product with SKU {sku} not found.")

        try:
            return product.update_stock(
                quantity_change=quantity_change,
                source=source,
                terminal_id=terminal_id,
                transaction_id=transaction_id,
                reason=reason,
            )
        except Exception as e:
            logger.error(f"Error updating stock for product with SKU {sku}: {str(e)}")
            raise

    @staticmethod
    def update_expiry_info(product_id: str, oldest_expiry: str | None, newest_expiry: str | None):
        """
        Update batch expiry information for a product.
        """
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        try:
            return product.update_expiry_info(oldest_expiry=oldest_expiry, newest_expiry=newest_expiry)
        except Exception as e:
            logger.error(f"Error updating expiry info for product {product_id}: {str(e)}")
            raise

    @staticmethod
    def update_image(product_id: str, image_url: str, filename: str, size: int, image_type: str):
        """
        Update image metadata for a product.
        """
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        try:
            return product.update_image(
                image_url=image_url,
                filename=filename,
                size=size,
                image_type=image_type,
            )
        except Exception as e:
            logger.error(f"Error updating image for product {product_id}: {str(e)}")
            raise

    # ========== BATCH INTEGRATION ==========

    @staticmethod
    def get_product_with_batch_summary(product_id: str):
        """
        Get product plus batch summary (batches for this product, total qty from batches).
        Returns None if product not found.
        """
        product = ProductService.get_product_by_id(product_id)
        if not product:
            return None
        try:
            batches = Batch.get_by_product_id(product_id, limit=100)
            total_from_batches = sum(int(getattr(b, "quantity_remaining", 0) or 0) for b in batches)
            batch_dicts = [b.to_dict() for b in batches]
            out = product.to_dict()
            out["batches"] = batch_dicts
            out["batches_count"] = len(batch_dicts)
            out["total_stock_from_batches"] = total_from_batches
            return out
        except Exception as e:
            logger.error(f"Error getting product with batch summary for {product_id}: {str(e)}")
            out = product.to_dict()
            out["batches"] = []
            out["batches_count"] = 0
            out["total_stock_from_batches"] = 0
            return out

    @staticmethod
    def restock_product(product_id: str, quantity_received: int, supplier_info: dict = None, batch_info: dict = None):
        """
        Restock product by creating a batch and syncing product total_stock.
        supplier_info can include supplier_id; batch_info can include batch_number, cost_price, expiry_date, etc.
        """
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")
        supplier_info = supplier_info or {}
        batch_info = batch_info or {}
        batch_data = {
            "product_id": product_id,
            "quantity_received": quantity_received,
            "supplier_id": supplier_info.get("supplier_id") or "UNKNOWN",
            "batch_number": batch_info.get("batch_number") or f"RESTOCK-{product_id}",
            "cost_price": float(batch_info.get("cost_price") or product.cost_price or 0),
            "expiry_date": batch_info.get("expiry_date"),
            "date_received": batch_info.get("date_received"),
        }
        from datetime import datetime, timedelta
        from app.services.inventory.batch_service import BatchService
        if not batch_data.get("expiry_date"):
            batch_data["expiry_date"] = datetime.utcnow() + timedelta(days=90)
        if not batch_data.get("date_received"):
            batch_data["date_received"] = datetime.utcnow()
        batch_svc = get_singleton(BatchService)
        created = batch_svc.create_batch(batch_data)
        return {
            "batch": created,
            "product_id": product_id,
            "quantity_received": quantity_received,
            "product": ProductService.get_product_by_id(product_id).to_dict() if ProductService.get_product_by_id(product_id) else None,
        }
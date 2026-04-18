"""
Product Model - Following ERD Specification with POS Sync & Global Stock Management
PK = "products", SK = "PROD-#####" (5-digit format)
Single Table Design using RamyeonCornerDB
"""
import os
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from app.custom_attributes import FixedUTCDateTimeAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.exceptions import AttributeDeserializationError, UpdateError
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import traceback

# Import existing utils for consistency
from app.utils import get_dynamo_table, DYNAMO_TABLE_NAME, AWS_REGION
from app.utils.counters import counter_service

logger = logging.getLogger(__name__)


def _category_exists(category_id: str) -> bool:
    """Check that category_id exists in Category table (avoids circular import)."""
    if not category_id or not str(category_id).strip():
        return False
    try:
        from models.Categories import Category
        return Category.exists(category_id.strip())
    except Exception as e:
        logger.warning("Category existence check failed: %s", e)
        return False

# DynamoDB type keys (must match pynamodb.constants)
_DDB_MAP = "M"
_DDB_LIST = "L"


def _sanitize_details_list(raw_details: dict) -> dict:
    """Keep only Map (M) elements in details list so strict deserialization never sees L."""
    if not isinstance(raw_details, dict) or _DDB_LIST not in raw_details:
        return raw_details
    lst = raw_details[_DDB_LIST]
    if not isinstance(lst, list):
        return raw_details
    filtered = [x for x in lst if isinstance(x, dict) and _DDB_MAP in x]
    return {_DDB_LIST: filtered}


class TolerantListAttribute(ListAttribute):
    """
    ListAttribute that skips elements which are not Map (M) when deserializing.
    Use for sync_logs.details where some legacy records have L (list) elements
    instead of M (map), causing AttributeDeserializationError.
    """

    def deserialize(self, values):
        if not self.element_type:
            return super().deserialize(values)
        # Unwrap raw DynamoDB list format if present: {"L": [ ... ]}
        if isinstance(values, dict) and _DDB_LIST in values:
            values = values[_DDB_LIST]
        if not isinstance(values, (list, tuple)):
            return []
        element_attr = self.element_type()
        if isinstance(element_attr, MapAttribute):
            element_attr._make_attribute()
        deserialized_lst = []
        for idx, attribute_value in enumerate(values):
            if not isinstance(attribute_value, dict):
                continue
            if _DDB_MAP not in attribute_value:
                continue
            try:
                element_attr.attr_name = f"{self.attr_name}[{idx}]" if self.attr_name else f"[{idx}]"
                value = element_attr.deserialize(element_attr.get_value(attribute_value))
                deserialized_lst.append(value)
            except Exception:
                continue
        return deserialized_lst


class TolerantSyncLogListAttribute(ListAttribute):
    """
    ListAttribute for Product.sync_logs that sanitizes each entry's 'details' list
    (keeps only Map elements) before deserializing, so legacy L elements never reach
    SyncLogItem and cannot cause AttributeDeserializationError.
    """

    def deserialize(self, values):
        if not self.element_type:
            return super().deserialize(values)
        if isinstance(values, dict) and _DDB_LIST in values:
            values = values[_DDB_LIST]
        if not isinstance(values, (list, tuple)):
            return []
        deserialized_lst = []
        for idx, attribute_value in enumerate(values):
            if not isinstance(attribute_value, dict) or _DDB_MAP not in attribute_value:
                continue
            inner = attribute_value[_DDB_MAP]
            if not isinstance(inner, dict):
                continue
            inner = dict(inner)
            if "details" in inner:
                inner["details"] = _sanitize_details_list(inner["details"])
            wrapped = {_DDB_MAP: inner}
            element_attr = self.element_type()
            if isinstance(element_attr, MapAttribute):
                element_attr._make_attribute()
            element_attr.attr_name = f"{self.attr_name}[{idx}]" if self.attr_name else f"[{idx}]"
            try:
                value = element_attr.deserialize(element_attr.get_value(wrapped))
                deserialized_lst.append(value)
            except Exception:
                continue
        return deserialized_lst


def _log_products_raw_for_debug(model_cls, exc: Exception) -> None:
    """
    Query products at raw DynamoDB level and log each item's SK and sync_logs
    structure so we can identify which record causes deserialization errors
    (e.g. 'details' attribute from type L).
    """
    try:
        from decouple import config as decouple_config
        import boto3
        from boto3.dynamodb.conditions import Key, Attr

        table_name = decouple_config("DYNAMO_TABLE_NAME", default="RamyeonCornerDB")
        region = decouple_config("AWS_REGION_NAME", default="ap-southeast-1")
        dynamodb = boto3.resource(
            "dynamodb",
            region_name=region,
            aws_access_key_id=decouple_config("AWS_ACCESS_KEY_ID", default=""),
            aws_secret_access_key=decouple_config("AWS_SECRET_ACCESS_KEY", default=""),
        )
        table = dynamodb.Table(table_name)
        paginator = table.meta.client.get_paginator("query")
        page_iter = paginator.paginate(
            TableName=table_name,
            KeyConditionExpression="PK = :pk",
            FilterExpression="(attribute_not_exists(#del) OR #del = :false) AND (#st = :active)",
            ExpressionAttributeNames={"#del": "isDeleted", "#st": "status"},
            ExpressionAttributeValues={":pk": "products", ":false": False, ":active": "active"},
        )
        logged = 0
        for page in page_iter:
            for item in page.get("Items", []):
                if logged >= 3:
                    break
                sk = item.get("SK", "?")
                sync_logs = item.get("sync_logs", [])
                details_info = []
                for i, log in enumerate(sync_logs[:2]):
                    if isinstance(log, dict):
                        details = log.get("details")
                        if details is not None:
                            details_type = type(details).__name__
                            elem_types = []
                            if isinstance(details, list):
                                for j, d in enumerate(details[:3]):
                                    elem_types.append(type(d).__name__)
                            details_info.append(f"log[{i}].details type={details_type} elem_types={elem_types}")
                logger.info(
                    "Product raw SK=%s | sync_logs len=%s | %s (exception: %s)",
                    sk,
                    len(sync_logs),
                    "; ".join(details_info) or "no sync_logs",
                    str(exc)[:120],
                )
                logged += 1
        if logged > 0:
            logger.info("Logged %s raw product(s) for debug. Ensure TolerantListAttribute is used for sync_logs.details.", logged)
    except Exception as inner:
        logger.warning("Could not log raw products for debug: %s", inner, exc_info=True)


# ============= MAP ATTRIBUTES FOR COMPLEX FIELDS =============

class SyncLogDetailItem(MapAttribute):
    """MapAttribute for sync_logs.details items with POS-specific fields.
    All attributes optional so legacy/varied payloads (reason-only, updated_fields, etc.) deserialize."""
    field = UnicodeAttribute(null=True)
    old_value = UnicodeAttribute(null=True)
    new_value = UnicodeAttribute(null=True)
    terminal_id = UnicodeAttribute(null=True)  # POS terminal that made the change
    transaction_id = UnicodeAttribute(null=True)  # POS transaction ID
    # Keys used elsewhere in add_sync_log / sync_logs so DynamoDB maps deserialize without error
    reason = UnicodeAttribute(null=True)
    updated_fields = UnicodeAttribute(null=True)
    restored_at = UnicodeAttribute(null=True)
    restored_by = UnicodeAttribute(null=True)
    filename = UnicodeAttribute(null=True)
    size = UnicodeAttribute(null=True)  # stored as string in details
    type = UnicodeAttribute(null=True)   # image type etc.
    sync_time = UnicodeAttribute(null=True)
    deleted_by = UnicodeAttribute(null=True)


class SyncLogObjectItem(MapAttribute):
    """MapAttribute for sync_logs.object items with POS data"""
    entity_type = UnicodeAttribute()  # e.g., 'product', 'sale', 'inventory'
    entity_id = UnicodeAttribute()
    data = UnicodeAttribute(null=True)  # JSON string of the object


class SyncLogItem(MapAttribute):
    """MapAttribute for sync_logs items optimized for POS sync"""
    object = ListAttribute(of=SyncLogObjectItem, default=list)
    last_updated = FixedUTCDateTimeAttribute()
    source = UnicodeAttribute()  # 'pos_terminal_1', 'pos_terminal_2', 'admin_panel'
    status = UnicodeAttribute()  # 'success', 'failed', 'pending'
    details = TolerantListAttribute(of=SyncLogDetailItem, default=list)  # Tolerant: skips L elements
    action = UnicodeAttribute()  # 'create', 'update', 'stock_adjustment', 'sale'
    sync_id = UnicodeAttribute(null=True)  # Unique ID for this sync operation


class DeletionLog(MapAttribute):
    """MapAttribute for deletion_log"""
    deleted_at = FixedUTCDateTimeAttribute()
    deleted_by = UnicodeAttribute()
    reason = UnicodeAttribute()
    terminal_id = UnicodeAttribute(null=True)  # Which POS terminal performed deletion


# ============= PRODUCT MODEL =============

class Product(Model):
    """
    PRODUCT MODEL - Enhanced for POS Integration & Global Stock Management
    
    Core ERD Fields:
    - PK = products
    - SK = PROD-##### (5-digit)
    - product_name (String)
    - category_id (String)
    - subcategory_name (String)
    - SKU (String)
    - unit (String)
    - low_stock_threshold (integer)
    - cost_price (integer)
    - selling_price (float)
    - status (String)
    - is_taxable (boolean)
    - date_received (ISODATE)
    - isDeleted (boolean)
    - created_at (ISODATE)
    - updated_at (ISODATE)
    - total_stock (integer)
    - oldest_batch_expiry (string)
    - newest_batch_expiry (string)
    - expiry_alert (boolean)
    - barcode (string)
    - description (string)
    - image_url (string)
    - image_filename (string)
    - image_size (integer)
    - image_type (string)
    - sync_logs (array)
    - deletion_log
    
    Enhanced with POS Integration:
    - pos_sync_status: Track last POS sync status
    - last_pos_sync: Timestamp of last successful POS sync
    - pos_metadata: Flexible field for POS-specific data
    - last_stock_update: For real-time tracking
    - version: For optimistic concurrency control
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        # Capacity settings for product operations (higher than branches due to more frequent updates)
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, default="products", attr_name="PK")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "PROD-00001" (5-digit)
    
    # ============= PRODUCT IDENTIFICATION =============
    product_name = UnicodeAttribute()
    SKU = UnicodeAttribute()
    barcode = UnicodeAttribute(null=True)
    description = UnicodeAttribute(null=True)
    
    # ============= CATEGORY INFORMATION =============
    category_id = UnicodeAttribute()
    subcategory_name = UnicodeAttribute()
    
    # ============= PRICING INFORMATION =============
    cost_price = NumberAttribute()  # Stored as Decimal for precision
    selling_price = NumberAttribute()  # Stored as Decimal for precision
    is_taxable = BooleanAttribute(default=True)
    
    # ============= INVENTORY MANAGEMENT =============
    unit = UnicodeAttribute()  # e.g., 'piece', 'kg', 'liter', 'box'
    low_stock_threshold = NumberAttribute(null=True)
    total_stock = NumberAttribute(default=0)
    
    # ============= BATCH EXPIRY INFORMATION =============
    oldest_batch_expiry = UnicodeAttribute(null=True)  # ISO date string
    newest_batch_expiry = UnicodeAttribute(null=True)  # ISO date string
    expiry_alert = BooleanAttribute(default=False)
    
    # ============= STATUS AND METADATA =============
    status = UnicodeAttribute(default="active")  # 'active', 'inactive', 'discontinued', 'out_of_stock', 'low_stock'
    date_received = FixedUTCDateTimeAttribute()
    isDeleted = BooleanAttribute(default=False)
    created_at = FixedUTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = FixedUTCDateTimeAttribute(default=datetime.utcnow)
    
    # ============= IMAGE INFORMATION =============
    image_url = UnicodeAttribute(null=True)
    image_filename = UnicodeAttribute(null=True)
    image_size = NumberAttribute(null=True)  # in bytes
    image_type = UnicodeAttribute(null=True)  # e.g., 'image/jpeg', 'image/png'
    
    # ============= AUDIT AND SYNC LOGS =============
    sync_logs = TolerantSyncLogListAttribute(of=SyncLogItem, default=list)
    deletion_log = DeletionLog(null=True)
    
    # ============= ENHANCED FIELDS FOR POS & REAL-TIME SYNC =============
    pos_sync_status = UnicodeAttribute(default="synced")  # 'synced', 'pending', 'failed', 'out_of_sync'
    last_pos_sync = FixedUTCDateTimeAttribute(null=True)
    pos_metadata = UnicodeAttribute(null=True)  # JSON string for POS-specific data
    last_stock_update = FixedUTCDateTimeAttribute(null=True)
    version = NumberAttribute(default=1)  # For optimistic concurrency control
    
    # ============= INDEXES FOR COMMON QUERIES =============
    # Prioritized: name and barcode. No SKU index (search by SKU uses main table fallback).

    class ProductNameIndex(GlobalSecondaryIndex):
        """GSI for lookup/search by product name (exact or begins_with)."""
        class Meta:
            index_name = 'ProductNameIndex'
            read_capacity_units = 5
            write_capacity_units = 3
            projection = AllProjection()

        pk = UnicodeAttribute(hash_key=True)  # 'products'
        product_name = UnicodeAttribute(range_key=True)

    class BarcodeIndex(GlobalSecondaryIndex):
        """GSI for fast lookup by barcode."""
        class Meta:
            index_name = 'ProductBarcodeIndex'
            read_capacity_units = 5
            write_capacity_units = 3
            projection = AllProjection()

        pk = UnicodeAttribute(hash_key=True)  # 'products'
        barcode = UnicodeAttribute(range_key=True)

    name_index = ProductNameIndex()
    barcode_index = BarcodeIndex()
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_product(cls, product_name: str, sku: str, category_id: str,
                      cost_price: float, selling_price: float, unit: str,
                      date_received: datetime = None,
                      **kwargs) -> 'Product':
        """
        Create a new product with auto-generated 5-digit SK
        
        Args:
            product_name: Name of the product (required)
            sku: SKU code (required, must be unique)
            category_id: Category identifier (required)
            cost_price: Cost price (required)
            selling_price: Selling price (required)
            unit: Unit of measurement (required)
            date_received: Date product was received (defaults to now)
            **kwargs: Additional product attributes
        
        Returns:
            Product: Created and saved product instance
        
        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Validate required fields
            if not product_name or not product_name.strip():
                raise ValueError("product_name is required")
            if not sku or not sku.strip():
                raise ValueError("SKU is required")
            if not category_id:
                raise ValueError("category_id is required")
            if not _category_exists(category_id):
                raise ValueError("Category does not exist. Use an existing category_id (e.g. CTGY-001, CAT-001).")
            if cost_price is None or cost_price < 0:
                raise ValueError("cost_price must be non-negative")
            if selling_price is None or selling_price < 0:
                raise ValueError("selling_price must be non-negative")
            if not unit or not unit.strip():
                raise ValueError("unit is required")
            
            # Check if SKU already exists
            existing = cls.get_by_sku(sku)
            if existing and not existing.isDeleted:
                raise ValueError(f"Product with SKU '{sku}' already exists")
            
            # Generate SK using the centralized counter service
            sk_value = counter_service.get_next_id('products')
            
            # Set default date_received if not provided
            if date_received is None:
                date_received = datetime.utcnow()
            
            # Create and save product
            product = cls(
                pk="products",
                sk=sk_value,
                product_name=product_name.strip(),
                SKU=sku.strip(),
                category_id=category_id,
                cost_price=cost_price,
                selling_price=selling_price,
                unit=unit.strip(),
                date_received=date_received,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **kwargs
            )
            
            # Set default values if not provided
            if 'subcategory_name' not in kwargs:
                product.subcategory_name = "General"
            if 'low_stock_threshold' not in kwargs:
                product.low_stock_threshold = 10  # Default low stock threshold
            
            product.save()
            
            # Add initial sync log
            product.add_sync_log(
                source="system",
                status="success",
                action="create",
                details=[{"field": "initial_creation", "new_value": "product_created"}],
                object_data=[{
                    "entity_type": "product",
                    "entity_id": sk_value,
                    "data": product.to_json()
                }]
            )
            
            logger.info(f"Product created: {sk_value} - '{product_name}' (SKU: {sku})")
            return product
            
        except Exception as e:
            logger.error(f"Failed to create product: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, product_id: str, include_deleted: bool = False) -> 'Product | None':
        """
        Get product by ID. Tries the given id, then alternate forms (PROD-14 vs PROD-00014)
        so that both zero-padded and non-padded IDs find the same product.
        
        Args:
            product_id: Format "PROD-00001", "PROD-1", or "00001"
            include_deleted: Whether to include soft-deleted products
        
        Returns:
            Product or None if not found
        """
        if not product_id or not str(product_id).strip():
            return None
        product_id = str(product_id).strip()
        # Ensure PROD- prefix for first attempt
        try_id = product_id if product_id.upper().startswith("PROD-") else f"PROD-{product_id.zfill(5)}"
        try:
            product = cls.get("products", try_id)
            if product.isDeleted and not include_deleted:
                logger.warning(f"Product {try_id} is soft-deleted")
                return None
            return product
        except cls.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {str(e)}")
            return None
        # Try alternate formats (PROD-00014 <-> PROD-14) so either form finds the product
        try:
            if try_id.upper().startswith("PROD-"):
                num_part = try_id[5:].lstrip("0") or "0"
                n = int(num_part)
                for alt_id in (f"PROD-{n:05d}", f"PROD-{n}"):
                    if alt_id != try_id:
                        try:
                            product = cls.get("products", alt_id)
                            if product.isDeleted and not include_deleted:
                                return None
                            return product
                        except cls.DoesNotExist:
                            continue
            return None
        except (ValueError, cls.DoesNotExist):
            logger.warning(f"Product not found: {product_id} (tried {try_id} and alternates)")
            return None
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {str(e)}")
            return None
    
    @classmethod
    def _get_by_sku_fallback(cls, sku: str, include_deleted: bool) -> 'Product | None':
        """Query main table by SKU (PynamoDB filter)."""
        condition = cls.SKU == sku
        if not include_deleted:
            condition = condition & (cls.isDeleted == False)
        for product in cls.query("products", filter_condition=condition):
            return product
        return None

    @classmethod
    def _get_by_sku_raw(cls, sku: str, include_deleted: bool) -> 'Product | None':
        """
        Find product by SKU using boto3 query; matches 'SKU' or 'sku' and loads by PK+SK.
        Use when PynamoDB filter fails (e.g. attribute name/casing in table differs).
        """
        try:
            from decouple import config as decouple_config
            import boto3
            from boto3.dynamodb.conditions import Key

            table_name = decouple_config("DYNAMO_TABLE_NAME", default="RamyeonCornerDB")
            region = decouple_config("AWS_REGION_NAME", default="ap-southeast-1")
            dynamodb = boto3.resource(
                "dynamodb",
                region_name=region,
                aws_access_key_id=decouple_config("AWS_ACCESS_KEY_ID", default=""),
                aws_secret_access_key=decouple_config("AWS_SECRET_ACCESS_KEY", default=""),
            )
            table = dynamodb.Table(table_name)
            kwargs = {"KeyConditionExpression": Key("PK").eq("products")}
            while True:
                response = table.query(**kwargs)
                for item in response.get("Items", []):
                    sku_val = item.get("SKU") or item.get("sku")
                    if sku_val != sku:
                        continue
                    if not include_deleted and item.get("isDeleted"):
                        continue
                    sk_val = item.get("SK")
                    if sk_val:
                        return cls.get("products", sk_val)
                if "LastEvaluatedKey" not in response:
                    break
                kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            return None
        except Exception as e:
            logger.warning("_get_by_sku_raw failed for %s: %s", sku, e)
            return None

    @classmethod
    def get_by_sku(cls, sku: str, include_deleted: bool = False) -> 'Product | None':
        """
        Get product by SKU. No SKU GSI; uses main table filter then raw boto3 fallback.
        """
        if not sku or not str(sku).strip():
            return None
        sku = sku.strip()
        product = cls._get_by_sku_fallback(sku, include_deleted)
        if product is not None:
            return product
        return cls._get_by_sku_raw(sku, include_deleted)
    
    @classmethod
    def _get_by_barcode_raw(cls, barcode: str, include_deleted: bool) -> 'Product | None':
        """
        Find product by barcode using boto3; matches 'barcode' or 'Barcode', handles string/number.
        Use when GSI or PynamoDB filter fails (e.g. index missing or barcode stored as number).
        """
        try:
            from decouple import config as decouple_config
            import boto3
            from boto3.dynamodb.conditions import Key

            table_name = decouple_config("DYNAMO_TABLE_NAME", default="RamyeonCornerDB")
            region = decouple_config("AWS_REGION_NAME", default="ap-southeast-1")
            dynamodb = boto3.resource(
                "dynamodb",
                region_name=region,
                aws_access_key_id=decouple_config("AWS_ACCESS_KEY_ID", default=""),
                aws_secret_access_key=decouple_config("AWS_SECRET_ACCESS_KEY", default=""),
            )
            table = dynamodb.Table(table_name)
            barcode_str = str(barcode).strip()
            kwargs = {"KeyConditionExpression": Key("PK").eq("products")}
            while True:
                response = table.query(**kwargs)
                for item in response.get("Items", []):
                    candidate = item.get("barcode") or item.get("Barcode")
                    if candidate is None:
                        continue
                    if str(candidate).strip() != barcode_str:
                        continue
                    if not include_deleted and item.get("isDeleted"):
                        continue
                    sk_val = item.get("SK")
                    if sk_val:
                        return cls.get("products", sk_val)
                if "LastEvaluatedKey" not in response:
                    break
                kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            return None
        except Exception as e:
            logger.warning("_get_by_barcode_raw failed for %s: %s", barcode, e)
            return None

    @classmethod
    def get_by_barcode(cls, barcode: str, include_deleted: bool = False) -> 'Product | None':
        """
        Get product by barcode. Uses ProductBarcodeIndex when available; else main table filter; else raw boto3.
        """
        if not barcode or not str(barcode).strip():
            return None
        barcode = barcode.strip()
        product = None
        try:
            for p in cls.barcode_index.query(
                "products",
                cls.barcode == barcode,
                limit=1
            ):
                if not include_deleted and p.isDeleted:
                    continue
                product = p
                break
        except Exception as e:
            err_msg = str(e).lower()
            if "index" in err_msg or "validation" in err_msg:
                logger.debug("BarcodeIndex unavailable, using main table filter for barcode=%s", barcode)
            else:
                logger.error("Error fetching product by barcode '%s': %s", barcode, e)
        if product is not None:
            return product
        try:
            condition = cls.barcode == barcode
            if not include_deleted:
                condition = condition & (cls.isDeleted == False)
            for p in cls.query("products", filter_condition=condition):
                return p
        except Exception as e:
            logger.debug("Fallback get_by_barcode (PynamoDB filter) failed for %s: %s", barcode, e)
        return cls._get_by_barcode_raw(barcode, include_deleted)
    
    @classmethod
    def search_by_name(cls, search_term: str, limit: int = 20) -> list:
        """
        Search products by name (partial, case-insensitive)
        
        Args:
            search_term: Search term
            limit: Maximum number of products to return
        
        Returns:
            list: List of matching active products
        """
        try:
            products = []
            search_term_lower = search_term.lower()
            
            # Scan all active products (acceptable for hundreds of products)
            for product in cls.query("products", 
                                   filter_condition=(cls.isDeleted == False) & (cls.status == "active"),
                                   limit=500):  # Max 500 active products
                if search_term_lower in product.product_name.lower():
                    products.append(product)
                    if len(products) >= limit:
                        break
            
            return products
        except Exception as e:
            logger.error(f"Error searching products by name: {str(e)}")
            return []
    
    @classmethod
    def query_by_category(cls, category_id: str, status: str = "active") -> list:
        """
        Query products by category (filter on main table).
        For paginated access use query_by_category_paginated.
        """
        try:
            condition = (cls.isDeleted == False) & (cls.status == status) & (cls.category_id == category_id)
            return list(cls.query("products", filter_condition=condition))
        except Exception as e:
            logger.error(f"Error querying products by category: {str(e)}")
            return []
    
    @classmethod
    def query_by_status(cls, status: str, include_deleted: bool = False) -> list:
        """
        Query products by status using GSI
        
        Args:
            status: Status to filter by
            include_deleted: Whether to include soft-deleted products
        
        Returns:
            list: List of products with the given status
        """
        try:
            condition = cls.status == status
            if not include_deleted:
                condition = condition & (cls.isDeleted == False)
            
            return list(cls.query(
                "products",
                filter_condition=condition
            ))
        except Exception as e:
            logger.error(f"Error querying products by status: {str(e)}")
            return []
    
    @classmethod
    def get_all_active_products(cls) -> list:
        """
        Get all active, non-deleted products.
        Skips any item that fails deserialization and logs details for debugging.
        """
        result = []
        try:
            for product in cls.query(
                "products",
                filter_condition=(cls.isDeleted == False) & (cls.status == "active")
            ):
                result.append(product)
        except Exception as e:
            logger.error(
                "Error getting all active products: %s | type=%s",
                str(e),
                type(e).__name__,
                exc_info=True,
            )
            logger.error("Traceback: %s", traceback.format_exc())
            # Log raw product items to find which one has invalid 'details' (type L)
            _log_products_raw_for_debug(cls, e)
        return result

    @classmethod
    def get_all_active_products_paginated(cls, limit: int = 50, last_evaluated_key=None):
        """
        Get a page of active, non-deleted products for pagination.

        Args:
            limit: Max number of items per page (default 50).
            last_evaluated_key: DynamoDB key for the next page (from previous response).

        Returns:
            tuple: (list of Product, next_last_evaluated_key or None).
        """
        try:
            it = cls.query(
                "products",
                filter_condition=(cls.isDeleted == False) & (cls.status == "active"),
                limit=limit,
                last_evaluated_key=last_evaluated_key,
            )
            result = list(it)
            next_key = getattr(it, "last_evaluated_key", None)
            return result, next_key
        except Exception as e:
            logger.error(
                "Error getting paginated active products: %s | type=%s",
                str(e),
                type(e).__name__,
                exc_info=True,
            )
            _log_products_raw_for_debug(cls, e)
            return [], None

    @classmethod
    def query_by_status_paginated(cls, status: str, limit: int = 50, last_evaluated_key=None, include_deleted: bool = False):
        """
        One page of products by status; does not load the full result set.
        Returns (list of Product, next_last_evaluated_key or None).
        """
        try:
            condition = cls.status == status
            if not include_deleted:
                condition = condition & (cls.isDeleted == False)
            it = cls.query(
                "products",
                filter_condition=condition,
                limit=limit,
                last_evaluated_key=last_evaluated_key,
            )
            result = list(it)
            next_key = getattr(it, "last_evaluated_key", None)
            return result, next_key
        except Exception as e:
            logger.error("Error in query_by_status_paginated: %s", e, exc_info=True)
            return [], None

    @classmethod
    def query_by_category_paginated(cls, category_id: str, status: str = "active", limit: int = 50, last_evaluated_key=None):
        """
        One page of products by category_id (and status); does not load the full result set.
        Returns (list of Product, next_last_evaluated_key or None).
        """
        try:
            condition = (cls.isDeleted == False) & (cls.status == status) & (cls.category_id == category_id)
            it = cls.query(
                "products",
                filter_condition=condition,
                limit=limit,
                last_evaluated_key=last_evaluated_key,
            )
            result = list(it)
            next_key = getattr(it, "last_evaluated_key", None)
            return result, next_key
        except Exception as e:
            logger.error("Error in query_by_category_paginated: %s", e, exc_info=True)
            return [], None

    @classmethod
    def search_products_by_name_paginated(cls, search_term: str, limit: int = 50, last_evaluated_key=None):
        """
        One page of products whose name contains search_term (case-insensitive).
        Fetches one chunk from DynamoDB (up to read_limit items), filters in memory,
        returns up to `limit` matches and a token for the next chunk. Never loads
        the full table. Returns (list of Product, next_last_evaluated_key or None).
        """
        if not (search_term and search_term.strip()):
            return [], None
        search_term_lower = search_term.strip().lower()
        try:
            read_limit = min(limit * 4, 200)
            it = cls.query(
                "products",
                filter_condition=(cls.isDeleted == False) & (cls.status == "active"),
                limit=read_limit,
                last_evaluated_key=last_evaluated_key,
            )
            result = []
            for product in it:
                if search_term_lower in (product.product_name or "").lower():
                    result.append(product)
            next_key = getattr(it, "last_evaluated_key", None)
            return result[:limit], next_key
        except Exception as e:
            logger.error("Error in search_products_by_name_paginated: %s", e, exc_info=True)
            return [], None
    
    @classmethod
    def get_low_stock_products(cls) -> list:
        """
        Get products with stock below threshold
        
        Returns:
            list: List of low stock products
        """
        try:
            low_stock_products = []
            for product in cls.query(
                "products",
                filter_condition=(cls.isDeleted == False) & (cls.status == "active")
            ):
                if product.low_stock_threshold and product.total_stock <= product.low_stock_threshold:
                    low_stock_products.append(product)
            return low_stock_products
        except Exception as e:
            logger.error(f"Error getting low stock products: {str(e)}")
            return []
    
    @classmethod
    def get_out_of_stock_products(cls) -> list:
        """
        Get products that are out of stock
        
        Returns:
            list: List of out of stock products
        """
        try:
            return list(cls.query(
                "products",
                filter_condition=(cls.isDeleted == False) & (cls.total_stock == 0)
            ))
        except Exception as e:
            logger.error(f"Error getting out of stock products: {str(e)}")
            return []
    
    @classmethod
    def get_expiring_soon_products(cls, days: int = 30) -> list:
        """
        Get products with batches expiring soon
        
        Args:
            days: Number of days to look ahead for expiry
        
        Returns:
            list: List of products expiring soon
        """
        try:
            expiring_products = []
            cutoff_date = (datetime.utcnow() + timedelta(days=days)).isoformat()
            
            for product in cls.query(
                "products",
                filter_condition=(cls.isDeleted == False) & (cls.expiry_alert == True)
            ):
                if product.oldest_batch_expiry and product.oldest_batch_expiry <= cutoff_date:
                    expiring_products.append(product)
            
            return expiring_products
        except Exception as e:
            logger.error(f"Error getting expiring soon products: {str(e)}")
            return []
    
    @classmethod
    def get_products_needing_pos_sync(cls) -> list:
        """
        Get products that need to be synced with POS
        
        Returns:
            list: List of products with pending POS sync
        """
        try:
            pending_sync = []
            for product in cls.query(
                "products",
                filter_condition=(cls.isDeleted == False) & (cls.pos_sync_status != "synced")
            ):
                pending_sync.append(product)
            return pending_sync
        except Exception as e:
            logger.error(f"Error getting products needing POS sync: {str(e)}")
            return []
    
    @classmethod
    def get_product_count(cls) -> int:
        """
        Get total number of active products
        
        Returns:
            int: Number of active products
        """
        try:
            count = 0
            for _ in cls.query("products", filter_condition=cls.isDeleted == False):
                count += 1
            return count
        except Exception as e:
            logger.error(f"Error counting products: {str(e)}")
            return 0
    
    @classmethod
    def sku_exists(cls, sku: str) -> bool:
        """
        Check if a product with given SKU already exists
        
        Args:
            sku: SKU to check
        
        Returns:
            bool: True if SKU exists, False otherwise
        """
        try:
            return cls.get_by_sku(sku) is not None
        except Exception as e:
            logger.error(f"Error checking SKU existence: {str(e)}")
            return False
    
    @classmethod
    def barcode_exists(cls, barcode: str) -> bool:
        """
        Check if a product with given barcode already exists
        
        Args:
            barcode: Barcode to check
        
        Returns:
            bool: True if barcode exists, False otherwise
        """
        try:
            return cls.get_by_barcode(barcode) is not None
        except Exception as e:
            logger.error(f"Error checking barcode existence: {str(e)}")
            return False
    
    # ============= INSTANCE METHODS =============
    
    def update_stock(self, quantity_change: int, source: str = "manual", 
                    terminal_id: str = None, transaction_id: str = None,
                    reason: str = None) -> 'Product':
        """
        Update product stock level with optimistic locking
        
        Args:
            quantity_change: Positive for additions, negative for deductions
            source: Source of the update ('pos', 'manual', 'inventory', 'adjustment')
            terminal_id: POS terminal ID (if from POS)
            transaction_id: POS transaction ID (if from sale)
            reason: Reason for stock change
        
        Returns:
            Product: Updated product instance
        
        Raises:
            ValueError: If insufficient stock or invalid quantity
        """
        try:
            # Validate quantity
            if quantity_change == 0:
                raise ValueError("Quantity change cannot be zero")
            
            new_stock = self.total_stock + quantity_change
            
            if new_stock < 0:
                raise ValueError(f"Insufficient stock. Available: {self.total_stock}, Requested: {-quantity_change}")
            
            # Update with optimistic locking.
            # Legacy/migrated items may not have `version` set in DynamoDB yet; treat that as 0.
            current_version = getattr(self, "version", None)
            if current_version is None:
                current_version = 0
            self.total_stock = new_stock
            self.version = current_version + 1
            self.last_stock_update = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            
            # Update status based on stock
            if self.total_stock == 0:
                self.status = "out_of_stock"
                self.pos_sync_status = "pending"  # Flag for POS sync
            elif self.low_stock_threshold and self.total_stock <= self.low_stock_threshold:
                self.status = "low_stock"
                self.pos_sync_status = "pending"  # Flag for POS sync
            elif self.status in ["out_of_stock", "low_stock"] and self.total_stock > (self.low_stock_threshold or 0):
                self.status = "active"
                self.pos_sync_status = "pending"  # Flag for POS sync
            
            # Save with condition to prevent concurrent updates.
            # If this item did not previously have a version attribute, allow the first write.
            if current_version == 0:
                condition = (Product.version.does_not_exist()) | (Product.version == 0)
            else:
                condition = (Product.version == current_version)
            self.save(condition=condition)
            
            # Prepare sync details
            details = [
                {
                    "field": "total_stock",
                    "old_value": str(self.total_stock - quantity_change),
                    "new_value": str(self.total_stock),
                    "terminal_id": terminal_id,
                    "transaction_id": transaction_id
                }
            ]
            if reason:
                details.append({"reason": reason})
            
            # Add sync log
            self.add_sync_log(
                source=source,
                status="success",
                action="stock_update",
                details=details,
                object_data=[{
                    "entity_type": "product",
                    "entity_id": self.sk,
                    "data": self.to_json()
                }],
                sync_id=f"stock_update_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            )
            
            logger.info(f"Stock updated for {self.sk}: {quantity_change:+d} (new total: {self.total_stock}) from {source}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to update stock for {self.sk}: {str(e)}")
            raise

    def set_total_stock_absolute(
        self,
        new_total_stock: int,
        source: str = "system",
        reason: str | None = None,
        oldest_expiry: Optional[str] = None,
        newest_expiry: Optional[str] = None,
    ) -> 'Product':
        """
        Set Product.total_stock to an absolute value (e.g., recomputed from batches),
        using optimistic locking.

        This is used to keep total_stock consistent with batch quantities,
        especially when excluding expired batches.
        """
        try:
            new_total_stock = int(new_total_stock or 0)
            if new_total_stock < 0:
                new_total_stock = 0

            current_version = getattr(self, "version", None)
            if current_version is None:
                current_version = 0

            self.total_stock = new_total_stock
            self.version = current_version + 1
            self.last_stock_update = datetime.utcnow()
            self.updated_at = datetime.utcnow()

            if oldest_expiry is not None:
                self.oldest_batch_expiry = oldest_expiry
            if newest_expiry is not None:
                self.newest_batch_expiry = newest_expiry

            # Update status based on new stock
            if self.total_stock == 0:
                self.status = "out_of_stock"
                self.pos_sync_status = "pending"
            elif self.low_stock_threshold and self.total_stock <= self.low_stock_threshold:
                self.status = "low_stock"
                self.pos_sync_status = "pending"
            elif self.status in ["out_of_stock", "low_stock"] and self.total_stock > (self.low_stock_threshold or 0):
                self.status = "active"
                self.pos_sync_status = "pending"

            if current_version == 0:
                condition = (Product.version.does_not_exist()) | (Product.version == 0)
            else:
                condition = (Product.version == current_version)

            self.save(condition=condition)
            logger.info(
                f"total_stock set for {self.sk}: {self.total_stock} (source={source})"
                + (f" reason={reason}" if reason else "")
            )
            return self
        except UpdateError as e:
            # Version conflict is expected when syncing from batches; caller uses direct update fallback
            if "ConditionalCheckFailedException" in str(e):
                logger.info("Version conflict updating total_stock for %s (sync will use direct update)", self.sk)
            else:
                logger.error(f"Failed to set total_stock for {self.sk}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to set total_stock for {self.sk}: {str(e)}")
            raise
    
    def add_sync_log(self, source: str, status: str, action: str, 
                    details: Optional[List[Dict]] = None, 
                    object_data: Optional[List[Dict]] = None,
                    sync_id: str = None) -> None:
        """
        Add a synchronization log entry with rotation
        
        Args:
            source: Source system ('pos_terminal_X', 'admin_panel', 'system')
            status: Sync status ('success', 'failed', 'partial')
            action: Action performed ('create', 'update', 'stock_update', 'delete')
            details: List of detail items for the sync operation
            object_data: Object data that was synced
            sync_id: Optional unique ID for this sync operation
        """
        try:
            # Limit sync logs to last 100 entries to prevent unbounded growth
            if len(self.sync_logs) >= 100:
                self.sync_logs = self.sync_logs[-99:]  # Keep last 99, will add 1 more
            
            # Convert details dicts to SyncLogDetailItem
            detail_items = []
            if details:
                for detail in details:
                    item = SyncLogDetailItem()
                    for key, value in detail.items():
                        setattr(item, key, value)
                    detail_items.append(item)
            
            # Convert object_data dicts to SyncLogObjectItem
            object_items = []
            if object_data:
                for obj in object_data:
                    item = SyncLogObjectItem()
                    for key, value in obj.items():
                        setattr(item, key, value)
                    object_items.append(item)
            
            sync_log = SyncLogItem(
                last_updated=datetime.utcnow(),
                source=source,
                status=status,
                action=action,
                details=detail_items,
                object=object_items,
                sync_id=sync_id or f"sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            )
            
            self.sync_logs.append(sync_log)
            self.updated_at = datetime.utcnow()
            
            # Update POS sync status if this is a POS sync
            if source.startswith('pos_'):
                if status == "success":
                    self.pos_sync_status = "synced"
                    self.last_pos_sync = datetime.utcnow()
                else:
                    self.pos_sync_status = "failed"
            
            self.save()
            
        except Exception as e:
            logger.error(f"Failed to add sync log for {self.sk}: {str(e)}")
            # Don't raise, as this shouldn't break the main operation
    
    def mark_pos_synced(self, terminal_id: str = None) -> 'Product':
        """
        Mark product as successfully synced with POS
        
        Args:
            terminal_id: POS terminal ID that synced
        
        Returns:
            Product: Updated product instance
        """
        try:
            self.pos_sync_status = "synced"
            self.last_pos_sync = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            self.save()
            
            # Add sync log
            self.add_sync_log(
                source=f"pos_{terminal_id}" if terminal_id else "pos_system",
                status="success",
                action="sync_complete",
                details=[{"terminal_id": terminal_id, "sync_time": datetime.utcnow().isoformat()}]
            )
            
            logger.info(f"Product {self.sk} marked as POS synced")
            return self
            
        except Exception as e:
            logger.error(f"Failed to mark product as POS synced: {str(e)}")
            raise
    
    def mark_pos_pending(self, reason: str = None) -> 'Product':
        """
        Mark product as needing POS sync
        
        Args:
            reason: Reason for pending sync
        
        Returns:
            Product: Updated product instance
        """
        try:
            self.pos_sync_status = "pending"
            self.updated_at = datetime.utcnow()
            self.save()
            
            if reason:
                logger.info(f"Product {self.sk} marked as pending POS sync: {reason}")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to mark product as pending POS sync: {str(e)}")
            raise
    
    def soft_delete(self, deleted_by: str, reason: str, terminal_id: str = None) -> 'Product':
        """
        Soft delete the product
        
        Args:
            deleted_by: User who deleted the product
            reason: Reason for deletion
            terminal_id: POS terminal ID (if deleted from POS)
        
        Returns:
            Product: Updated product instance
        """
        try:
            if not reason or not reason.strip():
                raise ValueError("Reason is required for deletion")
            
            self.isDeleted = True
            self.status = "deleted"
            self.deletion_log = DeletionLog(
                deleted_at=datetime.utcnow(),
                deleted_by=deleted_by,
                reason=reason.strip(),
                terminal_id=terminal_id
            )
            self.pos_sync_status = "pending"  # Flag for POS sync
            self.updated_at = datetime.utcnow()
            self.save()
            
            # Add sync log for deletion
            self.add_sync_log(
                source="system" if not terminal_id else f"pos_{terminal_id}",
                status="success",
                action="delete",
                details=[{"reason": reason, "deleted_by": deleted_by, "terminal_id": terminal_id}]
            )
            
            logger.info(f"Product {self.sk} soft-deleted by {deleted_by}: {reason}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to soft delete product {self.sk}: {str(e)}")
            raise
    
    def restore(self, restored_by: str = None) -> 'Product':
        """
        Restore a soft-deleted product
        
        Args:
            restored_by: User who restored the product
        
        Returns:
            Product: Updated product instance
        """
        try:
            self.isDeleted = False
            self.status = "active"
            self.deletion_log = None
            self.pos_sync_status = "pending"  # Flag for POS sync
            self.updated_at = datetime.utcnow()
            self.save()
            
            # Add sync log for restoration
            self.add_sync_log(
                source="system",
                status="success",
                action="restore",
                details=[{"restored_at": datetime.utcnow().isoformat(), "restored_by": restored_by}]
            )
            
            logger.info(f"Product {self.sk} restored")
            return self
            
        except Exception as e:
            logger.error(f"Failed to restore product {self.sk}: {str(e)}")
            raise
    
    def update_product(self, **kwargs) -> 'Product':
        """
        Update product attributes
        
        Args:
            **kwargs: Product attributes to update
        
        Returns:
            Product: Updated product instance
        """
        try:
            if "category_id" in kwargs:
                new_category_id = kwargs["category_id"]
                if not new_category_id or not str(new_category_id).strip():
                    raise ValueError("category_id cannot be empty.")
                if not _category_exists(new_category_id):
                    raise ValueError("Category does not exist. Use an existing category_id (e.g. CTGY-001, CAT-001).")

            updated_fields = []
            
            for key, value in kwargs.items():
                if hasattr(self, key) and getattr(self, key) != value:
                    setattr(self, key, value)
                    updated_fields.append(key)
            
            if updated_fields:
                self.pos_sync_status = "pending"  # Flag for POS sync
                self.updated_at = datetime.utcnow()
                self.save()
                
                # Add sync log for update
                self.add_sync_log(
                    source="system",
                    status="success",
                    action="update",
                    details=[{"updated_fields": ", ".join(updated_fields)}]
                )
                
                logger.info(f"Product {self.sk} updated fields: {', '.join(updated_fields)}")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to update product {self.sk}: {str(e)}")
            raise
    
    def update_expiry_info(self, oldest_expiry: Optional[str], newest_expiry: Optional[str]) -> 'Product':
        """
        Update batch expiry information
        
        Args:
            oldest_expiry: ISO date string of oldest batch expiry
            newest_expiry: ISO date string of newest batch expiry
        
        Returns:
            Product: Updated product instance
        """
        try:
            self.oldest_batch_expiry = oldest_expiry
            self.newest_batch_expiry = newest_expiry
            
            # Check if any batch is expiring soon (within 30 days)
            if oldest_expiry:
                try:
                    expiry_date = datetime.fromisoformat(oldest_expiry.replace('Z', '+00:00'))
                    days_until_expiry = (expiry_date - datetime.utcnow()).days
                    self.expiry_alert = days_until_expiry <= 30
                except (ValueError, AttributeError):
                    self.expiry_alert = False
            
            self.pos_sync_status = "pending"  # Flag for POS sync
            self.updated_at = datetime.utcnow()
            self.save()
            
            # Add sync log
            self.add_sync_log(
                source="system",
                status="success",
                action="expiry_update",
                details=[{
                    "oldest_expiry": oldest_expiry,
                    "newest_expiry": newest_expiry,
                    "expiry_alert": self.expiry_alert
                }]
            )
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to update expiry info for {self.sk}: {str(e)}")
            raise
    
    def update_image(self, image_url: str, filename: str, 
                    size: int, image_type: str) -> 'Product':
        """
        Update product image information
        
        Args:
            image_url: URL of the uploaded image
            filename: Original filename
            size: File size in bytes
            image_type: MIME type of the image
        
        Returns:
            Product: Updated product instance
        """
        try:
            self.image_url = image_url
            self.image_filename = filename
            self.image_size = size
            self.image_type = image_type
            self.pos_sync_status = "pending"  # Flag for POS sync
            self.updated_at = datetime.utcnow()
            self.save()
            
            # Add sync log for image update
            self.add_sync_log(
                source="system",
                status="success",
                action="image_update",
                details=[{"filename": filename, "size": size, "type": image_type}]
            )
            
            logger.info(f"Image updated for product {self.sk}: {filename}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to update image for {self.sk}: {str(e)}")
            raise
    
    def get_stock_status(self) -> str:
        """
        Get stock status based on current stock and threshold
        
        Returns:
            str: Stock status ('out_of_stock', 'low_stock', 'in_stock')
        """
        if self.total_stock == 0:
            return "out_of_stock"
        elif self.low_stock_threshold and self.total_stock <= self.low_stock_threshold:
            return "low_stock"
        else:
            return "in_stock"
    
    def calculate_margin(self) -> float:
        """
        Calculate profit margin percentage
        
        Returns:
            float: Margin percentage
        """
        if self.cost_price <= 0 or self.selling_price <= self.cost_price:
            return 0.0
        
        margin = ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return round(float(margin), 2)
    
    def calculate_markup(self) -> float:
        """
        Calculate markup percentage
        
        Returns:
            float: Markup percentage
        """
        if self.cost_price <= 0 or self.selling_price <= 0:
            return 0.0
        
        markup = ((self.selling_price - self.cost_price) / self.selling_price) * 100
        return round(float(markup), 2)
    
    def get_pos_representation(self) -> Dict[str, Any]:
        """
        Get product data formatted for POS system
        
        Returns:
            dict: POS-friendly product representation
        """
        return {
            "product_id": self.sk.replace("PROD-", ""),
            "product_name": self.product_name,
            "sku": self.SKU,
            "barcode": self.barcode,
            "category_id": self.category_id,
            "unit": self.unit,
            "cost_price": float(self.cost_price) if self.cost_price else 0.0,
            "selling_price": float(self.selling_price) if self.selling_price else 0.0,
            "is_taxable": self.is_taxable,
            "current_stock": int(self.total_stock) if self.total_stock else 0,
            "low_stock_threshold": int(self.low_stock_threshold) if self.low_stock_threshold else 0,
            "status": self.status,
            "image_url": self.image_url,
            "last_updated": self.updated_at.isoformat() if self.updated_at else None,
            "sync_status": self.pos_sync_status
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert product to dictionary for API response
        
        Returns:
            dict: Dictionary representation
        """
        try:
            product_dict = {
                "product_id": self.sk.replace("PROD-", ""),
                "product_name": self.product_name,
                "sku": self.SKU,
                "barcode": self.barcode,
                "description": self.description,
                "category_id": self.category_id,
                "subcategory_name": self.subcategory_name,
                "unit": self.unit,
                "low_stock_threshold": float(self.low_stock_threshold) if self.low_stock_threshold else None,
                "cost_price": float(self.cost_price) if self.cost_price else 0.0,
                "selling_price": float(self.selling_price) if self.selling_price else 0.0,
                "is_taxable": self.is_taxable,
                "status": self.status,
                "stock_status": self.get_stock_status(),
                "date_received": self.date_received.isoformat() if self.date_received else None,
                "isDeleted": self.isDeleted,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "total_stock": int(self.total_stock) if self.total_stock else 0,
                "oldest_batch_expiry": self.oldest_batch_expiry,
                "newest_batch_expiry": self.newest_batch_expiry,
                "expiry_alert": self.expiry_alert,
                "image_url": self.image_url,
                "image_filename": self.image_filename,
                "image_size": self.image_size,
                "image_type": self.image_type,
                "margin_percentage": self.calculate_margin(),
                "markup_percentage": self.calculate_markup(),
                "pos_sync_status": self.pos_sync_status,
                "last_pos_sync": self.last_pos_sync.isoformat() if self.last_pos_sync else None,
                "last_stock_update": self.last_stock_update.isoformat() if self.last_stock_update else None,
                "version": int(self.version) if self.version else 1
            }
            
            # Add deletion log if exists
            if self.deletion_log:
                product_dict["deletion_log"] = {
                    "deleted_at": self.deletion_log.deleted_at.isoformat() if self.deletion_log.deleted_at else None,
                    "deleted_by": self.deletion_log.deleted_by,
                    "reason": self.deletion_log.reason,
                    "terminal_id": self.deletion_log.terminal_id
                }
            
            # Add sync logs count (not full logs to avoid huge responses)
            product_dict["sync_logs_count"] = len(self.sync_logs)
            
            # Add recent sync status
            if self.sync_logs:
                latest = self.sync_logs[-1]
                product_dict["last_sync"] = {
                    "source": latest.source,
                    "status": latest.status,
                    "action": latest.action,
                    "timestamp": latest.last_updated.isoformat() if latest.last_updated else None
                }
            
            return product_dict
            
        except Exception as e:
            logger.error(f"Error converting product to dict: {str(e)}")
            return {}
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """
        Minimal dictionary representation (for listings)
        
        Returns:
            dict: Basic product info
        """
        try:
            return {
                "id": self.sk.replace("PROD-", ""),
                "name": self.product_name,
                "sku": self.SKU,
                "category": self.category_id,
                "stock": int(self.total_stock) if self.total_stock else 0,
                "stock_status": self.get_stock_status(),
                "selling_price": float(self.selling_price) if self.selling_price else 0.0,
                "image_url": self.image_url
            }
        except Exception as e:
            logger.error(f"Error converting product to simple dict: {str(e)}")
            return {}
    
    def to_json(self) -> str:
        """
        Convert product to JSON string for sync logs
        
        Returns:
            str: JSON representation
        """
        import json
        return json.dumps(self.to_dict(), default=str)
    
    def check_low_stock_alert(self) -> bool:
        """
        Check if low stock alert should be triggered
        
        Returns:
            bool: True if alert should be triggered
        """
        if self.low_stock_threshold and self.total_stock <= self.low_stock_threshold:
            if self.status != "low_stock":  # Only alert if status hasn't been updated
                return True
        return False


# ============= PRODUCT VALIDATION =============

def validate_product_id(product_id: str) -> bool:
    """
    Validate if a product ID is in correct format
    
    Args:
        product_id: Product ID to validate
    
    Returns:
        bool: True if valid format, False otherwise
    """
    try:
        if not product_id:
            return False
        
        # Check format: PROD-##### where ##### are exactly 5 digits
        if not product_id.startswith('PROD-'):
            return False
        
        number_part = product_id[5:]  # Remove "PROD-"
        if len(number_part) != 5:
            return False
        
        # Check if it's a valid number (00001-99999)
        number = int(number_part)
        return 1 <= number <= 99999
        
    except (ValueError, IndexError):
        return False


def validate_product_data(product_name: str, sku: str, cost_price: float,
                         selling_price: float, unit: str, category_id: str) -> tuple[bool, str]:
    """
    Validate product data before creation
    
    Args:
        product_name: Product name to validate
        sku: SKU to validate
        cost_price: Cost price to validate
        selling_price: Selling price to validate
        unit: Unit to validate
        category_id: Category ID to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not product_name or not product_name.strip():
        return False, "Product name is required"
    
    if len(product_name.strip()) > 200:
        return False, "Product name must be 200 characters or less"
    
    if not sku or not sku.strip():
        return False, "SKU is required"
    
    if len(sku.strip()) > 50:
        return False, "SKU must be 50 characters or less"
    
    if cost_price is None or cost_price < 0:
        return False, "Cost price must be non-negative"
    
    if selling_price is None or selling_price < 0:
        return False, "Selling price must be non-negative"
    
    if selling_price < cost_price:
        return False, "Selling price must be greater than or equal to cost price"
    
    if not unit or not unit.strip():
        return False, "Unit is required"
    
    if len(unit.strip()) > 20:
        return False, "Unit must be 20 characters or less"
    
    if not category_id:
        return False, "Category ID is required"
    
    return True, ""


# ============= BULK OPERATIONS =============

def import_products_from_csv(csv_data: List[Dict]) -> Dict:
    """
    Import multiple products from CSV data
    
    Args:
        csv_data: List of dictionaries with product data
    
    Returns:
        dict: Summary of import results
    """
    created_products = []
    updated_products = []
    errors = []
    
    for row in csv_data:
        try:
            # Extract required fields
            product_name = row.get('product_name')
            sku = row.get('sku')
            category_id = row.get('category_id')
            cost_price = float(row.get('cost_price', 0))
            selling_price = float(row.get('selling_price', 0))
            unit = row.get('unit', 'piece')
            
            # Validate required fields
            is_valid, error_msg = validate_product_data(
                product_name, sku, cost_price, selling_price, unit, category_id
            )
            
            if not is_valid:
                errors.append(f"Invalid data for row {row}: {error_msg}")
                continue
            
            # Check if product already exists
            existing = Product.get_by_sku(sku)
            
            if existing:
                # Update existing product
                existing.update_product(
                    product_name=product_name,
                    category_id=category_id,
                    cost_price=cost_price,
                    selling_price=selling_price,
                    unit=unit,
                    **{k: v for k, v in row.items() if k not in ['product_name', 'sku', 'category_id', 'cost_price', 'selling_price', 'unit']}
                )
                updated_products.append(existing.to_dict())
            else:
                # Create new product
                product = Product.create_product(
                    product_name=product_name,
                    sku=sku,
                    category_id=category_id,
                    cost_price=cost_price,
                    selling_price=selling_price,
                    unit=unit,
                    **{k: v for k, v in row.items() if k not in ['product_name', 'sku', 'category_id', 'cost_price', 'selling_price', 'unit']}
                )
                created_products.append(product.to_dict())
                
        except Exception as e:
            errors.append(f"Failed to process row {row}: {str(e)}")
    
    return {
        "created": created_products,
        "updated": updated_products,
        "total_created": len(created_products),
        "total_updated": len(updated_products),
        "errors": errors,
        "success": len(errors) == 0
    }


def batch_update_stock(stock_updates: List[Dict]) -> Dict:
    """
    Batch update stock for multiple products
    
    Args:
        stock_updates: List of dicts with 'sku', 'quantity_change', and optional 'source', 'reason'
    
    Returns:
        dict: Summary of update results
    """
    updated = []
    errors = []
    
    for update in stock_updates:
        try:
            sku = update.get('sku')
            quantity_change = update.get('quantity_change')
            source = update.get('source', 'batch_update')
            reason = update.get('reason')
            
            if not sku:
                errors.append(f"Missing sku in update: {update}")
                continue
            
            if quantity_change is None:
                errors.append(f"Missing quantity_change for SKU {sku}")
                continue
            
            product = Product.get_by_sku(sku)
            if not product:
                errors.append(f"Product not found: SKU {sku}")
                continue
            
            product.update_stock(
                quantity_change=quantity_change,
                source=source,
                reason=reason
            )
            
            updated.append({
                "sku": sku,
                "product_id": product.sk.replace("PROD-", ""),
                "new_stock": product.total_stock,
                "stock_status": product.get_stock_status()
            })
            
        except Exception as e:
            errors.append(f"Failed to update stock for {update.get('sku')}: {str(e)}")
    
    return {
        "updated": updated,
        "total_updated": len(updated),
        "errors": errors,
        "success": len(errors) == 0
    }


# ============= PRODUCT MANAGER =============

class ProductManager:
    """
    Manager class for product-related operations
    """
    
    @staticmethod
    def get_product_summary() -> Dict:
        """
        Get summary statistics for all products
        
        Returns:
            dict: Product summary
        """
        try:
            products = Product.get_all_active_products()
            total = len(products)
            
            # Count by status
            status_counts = {}
            stock_status_counts = {"in_stock": 0, "low_stock": 0, "out_of_stock": 0}
            category_counts = {}
            
            total_stock_value = 0.0
            total_potential_revenue = 0.0
            
            for product in products:
                # Status counts
                status = product.status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Stock status counts
                stock_status = product.get_stock_status()
                stock_status_counts[stock_status] = stock_status_counts.get(stock_status, 0) + 1
                
                # Category counts
                category = product.category_id
                category_counts[category] = category_counts.get(category, 0) + 1
                
                # Financial calculations
                total_stock_value += float(product.cost_price or 0) * float(product.total_stock or 0)
                total_potential_revenue += float(product.selling_price or 0) * float(product.total_stock or 0)
            
            # Low stock alerts
            low_stock_alerts = len([p for p in products if p.check_low_stock_alert()])
            
            # Expiry alerts
            expiry_alerts = len([p for p in products if p.expiry_alert])
            
            # POS sync status
            sync_status_counts = {}
            for product in products:
                sync_status = product.pos_sync_status
                sync_status_counts[sync_status] = sync_status_counts.get(sync_status, 0) + 1
            
            return {
                "total_products": total,
                "by_status": status_counts,
                "by_stock_status": stock_status_counts,
                "by_category": category_counts,
                "by_sync_status": sync_status_counts,
                "low_stock_alerts": low_stock_alerts,
                "expiry_alerts": expiry_alerts,
                "total_stock_value": round(total_stock_value, 2),
                "total_potential_revenue": round(total_potential_revenue, 2),
                "potential_profit": round(total_potential_revenue - total_stock_value, 2),
                "average_margin": round(sum(p.calculate_margin() for p in products) / total if total > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting product summary: {str(e)}")
            return {}
    
    @staticmethod
    def get_low_stock_report() -> List[Dict]:
        """
        Get detailed low stock report
        
        Returns:
            list: List of low stock products with details
        """
        try:
            low_stock_products = Product.get_low_stock_products()
            report = []
            
            for product in low_stock_products:
                report.append({
                    "product_id": product.sk.replace("PROD-", ""),
                    "product_name": product.product_name,
                    "sku": product.SKU,
                    "current_stock": product.total_stock,
                    "low_stock_threshold": product.low_stock_threshold,
                    "stock_status": product.get_stock_status(),
                    "category": product.category_id,
                    "last_stock_update": product.last_stock_update.isoformat() if product.last_stock_update else None,
                    "urgency": "critical" if product.total_stock == 0 else "warning"
                })
            
            return sorted(report, key=lambda x: (x["urgency"], x["current_stock"]))
            
        except Exception as e:
            logger.error(f"Error getting low stock report: {str(e)}")
            return []
    
    @staticmethod
    def get_pos_sync_report() -> Dict:
        """
        Get POS synchronization report
        
        Returns:
            dict: POS sync status report
        """
        try:
            products = Product.get_all_active_products()
            
            sync_report = {
                "total_products": len(products),
                "synced": 0,
                "pending": 0,
                "failed": 0,
                "out_of_sync": 0,
                "last_sync_times": [],
                "products_needing_sync": []
            }
            
            for product in products:
                sync_status = product.pos_sync_status
                sync_report[sync_status] = sync_report.get(sync_status, 0) + 1
                
                if sync_status != "synced":
                    sync_report["products_needing_sync"].append({
                        "product_id": product.sk.replace("PROD-", ""),
                        "product_name": product.product_name,
                        "sku": product.SKU,
                        "sync_status": sync_status,
                        "last_updated": product.updated_at.isoformat() if product.updated_at else None
                    })
                
                if product.last_pos_sync:
                    sync_report["last_sync_times"].append(product.last_pos_sync)
            
            # Calculate average time since last sync
            if sync_report["last_sync_times"]:
                latest_sync = max(sync_report["last_sync_times"])
                sync_report["latest_sync"] = latest_sync.isoformat()
                sync_report["hours_since_latest_sync"] = (datetime.utcnow() - latest_sync).total_seconds() / 3600
            
            return sync_report
            
        except Exception as e:
            logger.error(f"Error getting POS sync report: {str(e)}")
            return {}
    
    @staticmethod
    def export_products_for_pos() -> List[Dict]:
        """
        Export products in POS-friendly format
        
        Returns:
            list: List of products formatted for POS
        """
        try:
            products = Product.get_all_active_products()
            pos_data = []
            
            for product in products:
                pos_data.append(product.get_pos_representation())
            
            return pos_data
            
        except Exception as e:
            logger.error(f"Error exporting products for POS: {str(e)}")
            return []
    
    @staticmethod
    def sync_products_to_pos(product_ids: List[str] = None) -> Dict:
        """
        Sync products to POS system
        
        Args:
            product_ids: Specific product IDs to sync (all if None)
        
        Returns:
            dict: Sync operation results
        """
        try:
            products_to_sync = []
            
            if product_ids:
                for product_id in product_ids:
                    product = Product.get_by_id(product_id)
                    if product and not product.isDeleted:
                        products_to_sync.append(product)
            else:
                # Sync all products that need sync
                products_to_sync = Product.get_products_needing_pos_sync()
            
            synced = []
            failed = []
            
            for product in products_to_sync:
                try:
                    # In a real implementation, this would call the POS API
                    # For now, we'll simulate successful sync
                    product.mark_pos_synced(terminal_id="batch_sync")
                    synced.append(product.sk.replace("PROD-", ""))
                    
                except Exception as e:
                    logger.error(f"Failed to sync product {product.sk}: {str(e)}")
                    failed.append({
                        "product_id": product.sk.replace("PROD-", ""),
                        "error": str(e)
                    })
            
            return {
                "synced": synced,
                "failed": failed,
                "total_synced": len(synced),
                "total_failed": len(failed),
                "success_rate": len(synced) / len(products_to_sync) if products_to_sync else 0
            }
            
        except Exception as e:
            logger.error(f"Error syncing products to POS: {str(e)}")
            return {"error": str(e)}
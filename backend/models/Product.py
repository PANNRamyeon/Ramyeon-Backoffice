from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute,
    BinaryAttribute
)
from datetime import datetime
from typing import Optional, List, Dict, Any


class SyncLogDetailItem(MapAttribute):
    """MapAttribute for sync_logs.details items"""
    # Using dynamic attributes for flexibility
    pass


class SyncLogObjectItem(MapAttribute):
    """MapAttribute for sync_logs.object items"""
    # Using dynamic attributes for flexibility
    pass


class SyncLogItem(MapAttribute):
    """MapAttribute for sync_logs items"""
    object = ListAttribute(of=SyncLogObjectItem, default=list)
    last_updated = UTCDateTimeAttribute()
    source = UnicodeAttribute()
    status = UnicodeAttribute()
    details = ListAttribute(of=SyncLogDetailItem, default=list)
    action = UnicodeAttribute()


class DeletionLog(MapAttribute):
    """MapAttribute for deletion_log"""
    deleted_at = UTCDateTimeAttribute()
    deleted_by = UnicodeAttribute()
    reason = UnicodeAttribute()


class Product(Model):
    """
    Product model for DynamoDB
    PK = products (partition key)
    SK = PROD-#### (sort key)
    """
    class Meta:
        table_name = "your-table-name"  # Replace with your table name
        region = "your-region"  # Replace with your AWS region
        # Add billing_mode, read_capacity_units, write_capacity_units if needed

    # Primary Key Attributes
    PK = UnicodeAttribute(hash_key=True, default="products")
    SK = UnicodeAttribute(range_key=True)

    # Product Identification
    product_name = UnicodeAttribute()
    SKU = UnicodeAttribute()
    barcode = UnicodeAttribute(null=True)
    description = UnicodeAttribute(null=True)

    # Category Information
    category_id = UnicodeAttribute()
    subcategory_name = UnicodeAttribute()

    # Pricing Information
    cost_price = NumberAttribute()
    selling_price = NumberAttribute()
    is_taxable = BooleanAttribute(default=True)

    # Inventory Management
    unit = UnicodeAttribute()  # e.g., 'piece', 'kg', 'liter', 'box'
    low_stock_threshold = NumberAttribute(null=True)
    total_stock = NumberAttribute(default=0)

    # Batch Expiry Information
    oldest_batch_expiry = UnicodeAttribute(null=True)  # ISO date string
    newest_batch_expiry = UnicodeAttribute(null=True)  # ISO date string
    expiry_alert = BooleanAttribute(default=False)

    # Status and Metadata
    status = UnicodeAttribute(default="active")  # e.g., 'active', 'inactive', 'discontinued'
    date_received = UTCDateTimeAttribute()
    isDeleted = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)

    # Image Information
    image_url = UnicodeAttribute(null=True)
    image_filename = UnicodeAttribute(null=True)
    image_size = NumberAttribute(null=True)  # in bytes
    image_type = UnicodeAttribute(null=True)  # e.g., 'image/jpeg', 'image/png'

    # Audit and Sync Logs
    sync_logs = ListAttribute(of=SyncLogItem, default=list)
    deletion_log = DeletionLog(null=True)

    # Indexes for common queries
    class CategoryIndex(GlobalSecondaryIndex):
        """GSI for querying by category"""
        class Meta:
            index_name = 'CategoryIndex'
            read_capacity_units = 2
            write_capacity_units = 1
            projection = AllProjection()
        
        PK = UnicodeAttribute(hash_key=True)  # Will be set to 'products' for all
        category_id = UnicodeAttribute(range_key=True)

    class StatusIndex(GlobalSecondaryIndex):
        """GSI for querying by status"""
        class Meta:
            index_name = 'StatusIndex'
            read_capacity_units = 2
            write_capacity_units = 1
            projection = AllProjection()
        
        PK = UnicodeAttribute(hash_key=True)  # Will be set to 'products' for all
        status = UnicodeAttribute(range_key=True)

    category_index = CategoryIndex()
    status_index = StatusIndex()

    @classmethod
    def create_product(cls, product_id: str, **kwargs):
        """Helper method to create a new product with proper SK format"""
        sk = f"PROD-{product_id}"
        return cls(SK=sk, **kwargs)

    @classmethod
    def get_product(cls, product_id: str):
        """Helper method to retrieve a product by ID"""
        sk = f"PROD-{product_id}"
        return cls.get("products", sk)

    @classmethod
    def get_product_by_sku(cls, sku: str):
        """Get product by SKU"""
        # This requires a GSI on SKU or a query scan
        for product in cls.scan(cls.SKU == sku, filter_condition=cls.isDeleted == False):
            return product
        return None

    @classmethod
    def query_by_category(cls, category_id: str, status: Optional[str] = None):
        """Query products by category"""
        filter_condition = None
        if status:
            filter_condition = cls.status == status
        
        return cls.query(
            category_id,
            cls.SK.startswith("PROD-"),
            index_name="CategoryIndex",
            filter_condition=filter_condition
        )

    @classmethod
    def query_by_status(cls, status: str):
        """Query products by status"""
        return cls.query(
            "products",
            cls.status == status,
            index_name="StatusIndex",
            filter_condition=cls.isDeleted == False
        )

    @classmethod
    def query_active_products(cls):
        """Query all active, non-deleted products"""
        return cls.query(
            "products",
            cls.SK.startswith("PROD-"),
            filter_condition=(cls.isDeleted == False) & (cls.status == "active")
        )

    @classmethod
    def query_low_stock(cls):
        """Query products with stock below threshold"""
        return [
            product for product in cls.query_active_products()
            if product.total_stock <= (product.low_stock_threshold or 0)
        ]

    @classmethod
    def query_expiring_soon(cls, days: int = 30):
        """Query products with batches expiring soon"""
        # This is a simplified implementation
        # In production, you might want to maintain a separate expiry tracking index
        expiring_products = []
        for product in cls.query_active_products():
            if product.expiry_alert and product.oldest_batch_expiry:
                try:
                    expiry_date = datetime.fromisoformat(product.oldest_batch_expiry.replace('Z', '+00:00'))
                    days_until_expiry = (expiry_date - datetime.utcnow()).days
                    if 0 <= days_until_expiry <= days:
                        expiring_products.append(product)
                except (ValueError, AttributeError):
                    continue
        return expiring_products

    def update_stock(self, quantity_change: int, source: str = "manual", 
                    batch_id: Optional[str] = None):
        """
        Update product stock level
        
        Args:
            quantity_change: Positive for additions, negative for deductions
            source: Source of the update (e.g., 'manual', 'batch', 'sale')
            batch_id: ID of the batch being updated (optional)
        """
        new_stock = self.total_stock + quantity_change
        
        if new_stock < 0:
            raise ValueError(f"Insufficient stock. Available: {self.total_stock}, Requested: {-quantity_change}")
        
        self.total_stock = new_stock
        
        # Update status if stock is low or out of stock
        if self.total_stock == 0:
            self.status = "out_of_stock"
        elif self.low_stock_threshold and self.total_stock <= self.low_stock_threshold:
            self.status = "low_stock"
        elif self.status in ["out_of_stock", "low_stock"] and self.total_stock > self.low_stock_threshold:
            self.status = "active"
        
        self.updated_at = datetime.utcnow()
        self.save()

        # Add sync log for stock update
        self.add_sync_log(
            source=source,
            status="success",
            action="stock_update",
            details=[
                {"field": "total_stock", "old_value": self.total_stock - quantity_change, "new_value": self.total_stock},
                {"quantity_change": quantity_change, "batch_id": batch_id}
            ]
        )
        
        return self

    def add_sync_log(self, source: str, status: str, action: str, 
                    details: Optional[List[Dict]] = None, 
                    object_data: Optional[List[Dict]] = None):
        """
        Add a synchronization log entry
        
        Args:
            source: Source system (e.g., 'erp', 'pos', 'wms')
            status: Sync status (e.g., 'success', 'failed', 'partial')
            action: Action performed (e.g., 'create', 'update', 'delete')
            details: List of detail items for the sync operation
            object_data: Object data that was synced
        """
        sync_log = SyncLogItem(
            last_updated=datetime.utcnow(),
            source=source,
            status=status,
            action=action,
            details=details or [],
            object=object_data or []
        )
        
        self.sync_logs.append(sync_log)
        self.updated_at = datetime.utcnow()
        self.save()

    def soft_delete(self, deleted_by: str, reason: str):
        """
        Soft delete the product
        
        Args:
            deleted_by: User who deleted the product
            reason: Reason for deletion
        """
        self.isDeleted = True
        self.status = "deleted"
        self.deletion_log = DeletionLog(
            deleted_at=datetime.utcnow(),
            deleted_by=deleted_by,
            reason=reason
        )
        self.updated_at = datetime.utcnow()
        self.save()

        # Add sync log for deletion
        self.add_sync_log(
            source="system",
            status="success",
            action="delete",
            details=[{"reason": reason, "deleted_by": deleted_by}]
        )

    def restore(self):
        """Restore a soft-deleted product"""
        self.isDeleted = False
        self.status = "active"
        self.deletion_log = None
        self.updated_at = datetime.utcnow()
        self.save()

        # Add sync log for restoration
        self.add_sync_log(
            source="system",
            status="success",
            action="restore",
            details=[{"restored_at": datetime.utcnow().isoformat()}]
        )

    def update_expiry_info(self, oldest_expiry: Optional[str], newest_expiry: Optional[str]):
        """
        Update batch expiry information
        
        Args:
            oldest_expiry: ISO date string of oldest batch expiry
            newest_expiry: ISO date string of newest batch expiry
        """
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
        
        self.updated_at = datetime.utcnow()
        self.save()

    def update_image(self, image_url: str, filename: str, 
                    size: int, image_type: str):
        """
        Update product image information
        
        Args:
            image_url: URL of the uploaded image
            filename: Original filename
            size: File size in bytes
            image_type: MIME type of the image
        """
        self.image_url = image_url
        self.image_filename = filename
        self.image_size = size
        self.image_type = image_type
        self.updated_at = datetime.utcnow()
        self.save()

        # Add sync log for image update
        self.add_sync_log(
            source="system",
            status="success",
            action="image_update",
            details=[{"filename": filename, "size": size, "type": image_type}]
        )

    def get_stock_status(self) -> str:
        """Get stock status based on current stock and threshold"""
        if self.total_stock == 0:
            return "out_of_stock"
        elif self.low_stock_threshold and self.total_stock <= self.low_stock_threshold:
            return "low_stock"
        else:
            return "in_stock"

    def get_margin(self) -> float:
        """Calculate profit margin percentage"""
        if self.cost_price <= 0:
            return 0.0
        margin = ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return round(margin, 2)

    def get_markup(self) -> float:
        """Calculate markup percentage"""
        if self.cost_price <= 0:
            return 0.0
        markup = ((self.selling_price - self.cost_price) / self.selling_price) * 100
        return round(markup, 2)

    def get_product_summary(self) -> Dict[str, Any]:
        """Get summary representation of the product"""
        return {
            "product_id": self.SK.replace("PROD-", ""),
            "product_name": self.product_name,
            "SKU": self.SKU,
            "category_id": self.category_id,
            "stock": self.total_stock,
            "stock_status": self.get_stock_status(),
            "selling_price": self.selling_price,
            "cost_price": self.cost_price,
            "margin": self.get_margin(),
            "status": self.status,
            "expiry_alert": self.expiry_alert,
            "oldest_batch_expiry": self.oldest_batch_expiry,
            "image_url": self.image_url
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Get full representation of the product"""
        product_dict = {
            "product_id": self.SK.replace("PROD-", ""),
            "product_name": self.product_name,
            "SKU": self.SKU,
            "barcode": self.barcode,
            "description": self.description,
            "category_id": self.category_id,
            "subcategory_name": self.subcategory_name,
            "unit": self.unit,
            "low_stock_threshold": self.low_stock_threshold,
            "cost_price": self.cost_price,
            "selling_price": self.selling_price,
            "is_taxable": self.is_taxable,
            "status": self.status,
            "date_received": self.date_received.isoformat() if self.date_received else None,
            "isDeleted": self.isDeleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "total_stock": self.total_stock,
            "oldest_batch_expiry": self.oldest_batch_expiry,
            "newest_batch_expiry": self.newest_batch_expiry,
            "expiry_alert": self.expiry_alert,
            "image_url": self.image_url,
            "image_filename": self.image_filename,
            "image_size": self.image_size,
            "image_type": self.image_type,
            "stock_status": self.get_stock_status(),
            "margin": self.get_margin(),
            "markup": self.get_markup()
        }
        
        # Add deletion log if exists
        if self.deletion_log:
            product_dict["deletion_log"] = {
                "deleted_at": self.deletion_log.deleted_at.isoformat() if self.deletion_log.deleted_at else None,
                "deleted_by": self.deletion_log.deleted_by,
                "reason": self.deletion_log.reason
            }
        
        # Add sync logs count
        product_dict["sync_logs_count"] = len(self.sync_logs)
        
        return product_dict
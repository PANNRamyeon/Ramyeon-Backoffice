"""
Product model for DynamoDB using PynamoDB
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, 
    BooleanAttribute, UTCDateTimeAttribute,
    JSONAttribute, ListAttribute, MapAttribute
)
from datetime import datetime, date
import os


class InventoryLog(MapAttribute):
    """Inventory change log entry"""
    action = UnicodeAttribute()  # received, sold, returned, adjusted, damaged
    quantity = NumberAttribute()
    previous_quantity = NumberAttribute(null=True)
    new_quantity = NumberAttribute()
    reason = UnicodeAttribute(null=True)
    performed_by = UnicodeAttribute(null=True)
    reference_id = UnicodeAttribute(null=True)  # order_id, return_id, etc.
    timestamp = UTCDateTimeAttribute()


class PricingInfo(MapAttribute):
    """Product pricing information"""
    cost_price = NumberAttribute(null=True)
    selling_price = NumberAttribute(null=True)
    margin = NumberAttribute(null=True)
    currency = UnicodeAttribute(default="USD")
    tax_rate = NumberAttribute(null=True)  # percentage
    discount_price = NumberAttribute(null=True)
    price_valid_until = UTCDateTimeAttribute(null=True)


class ProductAttributes(MapAttribute):
    """Flexible attributes for product variations, specifications, etc."""
    # Examples: color, size, weight, dimensions, material, etc.
    pass


class Product(Model):
    """
    Product table model for PynamoDB
    
    Note: Original schema had duplicate 'Deleted_at' fields - consolidated
    """
    
    class Meta:
        table_name = os.environ.get('PRODUCT_TABLE_NAME', 'Product')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        # For local development
        if os.environ.get('DYNAMODB_LOCAL', 'false').lower() == 'true':
            host = os.environ.get('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')
        read_capacity_units = 10
        write_capacity_units = 10
    
    # Primary Keys
    id = UnicodeAttribute(hash_key=True)
    
    # Product Identifiers
    product_id = UnicodeAttribute(null=True)  # External/SKU ID if different from id
    sku = UnicodeAttribute(null=True)  # Stock Keeping Unit
    barcode = UnicodeAttribute(null=True)  # UPC/EAN/ISBN
    upc = UnicodeAttribute(null=True)  # Universal Product Code
    mpn = UnicodeAttribute(null=True)  # Manufacturer Part Number
    
    # Basic Information
    name = UnicodeAttribute()  # Missing in original, but essential
    description = UnicodeAttribute(null=True)
    short_description = UnicodeAttribute(null=True)
    
    # Categorization
    category_id = UnicodeAttribute()
    subcategory_id = UnicodeAttribute(null=True)
    tags = ListAttribute(of=UnicodeAttribute, null=True)
    
    # Supplier Information
    supplier_id = UnicodeAttribute()
    supplier_name = UnicodeAttribute(null=True)  # Denormalized for faster queries
    manufacturer = UnicodeAttribute(null=True)
    brand = UnicodeAttribute(null=True)
    
    # Inventory Management
    quantity_received = NumberAttribute(default=0)
    quantity_remaining = NumberAttribute(default=0)
    quantity_sold = NumberAttribute(default=0)
    quantity_reserved = NumberAttribute(default=0)  # For pending orders
    quantity_available = NumberAttribute(default=0)  # Calculated: remaining - reserved
    minimum_stock_level = NumberAttribute(default=10)
    reorder_quantity = NumberAttribute(null=True)
    
    # Pricing
    pricing = PricingInfo(null=True)
    
    # Dates
    expiry_date = UTCDateTimeAttribute(null=True)
    date_received = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    manufactured_date = UTCDateTimeAttribute(null=True)
    
    # Location and Storage
    warehouse_location = UnicodeAttribute(null=True)
    shelf_location = UnicodeAttribute(null=True)
    bin_location = UnicodeAttribute(null=True)
    branch_id = UnicodeAttribute(null=True)  # If products are branch-specific
    
    # Status and Flags
    status = UnicodeAttribute(default="active")  # active, inactive, discontinued, out_of_stock
    is_active = BooleanAttribute(default=True)
    is_featured = BooleanAttribute(default=False)
    is_best_seller = BooleanAttribute(default=False)
    is_new_arrival = BooleanAttribute(default=False)
    
    # Physical Attributes
    weight = NumberAttribute(null=True)  # in grams
    weight_unit = UnicodeAttribute(default="g")
    dimensions = UnicodeAttribute(null=True)  # "10x5x3" or JSON
    unit = UnicodeAttribute(default="piece")  # piece, kg, liter, etc.
    
    # Media
    image_url = UnicodeAttribute(null=True)
    image_urls = ListAttribute(of=UnicodeAttribute, null=True)
    thumbnail_url = UnicodeAttribute(null=True)
    
    # Audit and Metadata
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    source = UnicodeAttribute(null=True)  # Import source or system
    
    # Inventory Tracking
    inventory_log = ListAttribute(of=InventoryLog, null=True)
    
    # Custom Attributes
    attributes = ProductAttributes(null=True)
    specifications = JSONAttribute(null=True)  # Technical specs as JSON
    
    # Soft Delete
    is_deleted = BooleanAttribute(default=False)
    deleted_at = UTCDateTimeAttribute(null=True)
    deleted_by = UnicodeAttribute(null=True)
    
    def save(self, *args, **kwargs):
        """Override save to update timestamps and calculated fields"""
        self.updated_at = datetime.utcnow()
        
        # Calculate available quantity
        self.quantity_available = self.quantity_remaining - self.quantity_reserved
        
        # Auto-update status based on quantity
        if self.quantity_available <= 0:
            self.status = "out_of_stock"
        elif self.quantity_available <= self.minimum_stock_level:
            self.status = "low_stock"
        elif self.status in ["out_of_stock", "low_stock"] and self.quantity_available > self.minimum_stock_level:
            self.status = "active"
        
        # Calculate sold quantity if not set
        if self.quantity_sold == 0 and self.quantity_received > 0:
            self.quantity_sold = self.quantity_received - self.quantity_remaining
        
        return super().save(*args, **kwargs)
    
    def receive_stock(self, quantity, reason="restock", performed_by=None, reference_id=None):
        """Receive new stock of this product"""
        previous_qty = self.quantity_remaining
        self.quantity_received += quantity
        self.quantity_remaining += quantity
        
        # Add to inventory log
        if not self.inventory_log:
            self.inventory_log = []
        
        self.inventory_log.append(InventoryLog(
            action="received",
            quantity=quantity,
            previous_quantity=previous_qty,
            new_quantity=self.quantity_remaining,
            reason=reason,
            performed_by=performed_by,
            reference_id=reference_id,
            timestamp=datetime.utcnow()
        ))
        
        self.save()
    
    def sell_stock(self, quantity, order_id=None, performed_by=None):
        """Sell stock from inventory"""
        if self.quantity_available < quantity:
            raise ValueError(f"Insufficient stock. Available: {self.quantity_available}, Requested: {quantity}")
        
        previous_qty = self.quantity_remaining
        self.quantity_remaining -= quantity
        self.quantity_sold += quantity
        
        # Add to inventory log
        if not self.inventory_log:
            self.inventory_log = []
        
        self.inventory_log.append(InventoryLog(
            action="sold",
            quantity=quantity,
            previous_quantity=previous_qty,
            new_quantity=self.quantity_remaining,
            reason="order_fulfillment",
            performed_by=performed_by,
            reference_id=order_id,
            timestamp=datetime.utcnow()
        ))
        
        self.save()
    
    def reserve_stock(self, quantity, order_id=None):
        """Reserve stock for pending order"""
        if self.quantity_available < quantity:
            raise ValueError(f"Insufficient available stock. Available: {self.quantity_available}, Requested: {quantity}")
        
        self.quantity_reserved += quantity
        self.save()
    
    def release_reserved_stock(self, quantity, order_id=None):
        """Release previously reserved stock"""
        if self.quantity_reserved < quantity:
            raise ValueError(f"Trying to release more than reserved. Reserved: {self.quantity_reserved}, Requested: {quantity}")
        
        self.quantity_reserved -= quantity
        self.save()
    
    def to_dict(self):
        """Convert model to dictionary"""
        result = {}
        for attr_name in self.get_attributes():
            value = getattr(self, attr_name)
            
            if value is None:
                continue
            
            if hasattr(value, 'to_dict'):
                result[attr_name] = value.to_dict()
            elif isinstance(value, list):
                result[attr_name] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item
                    for item in value
                ]
            elif isinstance(value, (datetime, date)):
                result[attr_name] = value.isoformat()
            else:
                result[attr_name] = value
        
        return result
    
    def check_expiry(self):
        """Check if product is expired or near expiry"""
        if not self.expiry_date:
            return "no_expiry"
        
        today = datetime.utcnow()
        days_to_expiry = (self.expiry_date - today).days
        
        if days_to_expiry < 0:
            return "expired"
        elif days_to_expiry <= 7:
            return "expiring_soon"
        elif days_to_expiry <= 30:
            return "expiring_month"
        else:
            return "ok"
    
    @classmethod
    def get_by_sku(cls, sku):
        """Get product by SKU (requires GSI)"""
        for product in cls.scan(cls.sku == sku, limit=1):
            return product
        return None
    
    @classmethod
    def get_by_category(cls, category_id):
        """Get all products in a category"""
        return list(cls.scan(
            filter_condition=cls.category_id == category_id
        ))
    
    @classmethod
    def get_low_stock_products(cls):
        """Get products that are low on stock"""
        return list(cls.scan(
            filter_condition=(cls.quantity_available <= cls.minimum_stock_level) & 
                           (cls.is_deleted == False) &
                           (cls.status != "discontinued")
        ))
    
    @classmethod
    def get_expiring_products(cls, days=30):
        """Get products expiring within specified days"""
        # Note: This requires a scan - for production, consider using GSI on expiry_date
        threshold_date = datetime.utcnow().replace(tzinfo=None) + datetime.timedelta(days=days)
        products = []
        
        for product in cls.scan(filter_condition=cls.is_deleted == False):
            if product.expiry_date and product.expiry_date.replace(tzinfo=None) <= threshold_date:
                products.append(product)
        
        return products
    
    def soft_delete(self, deleted_by=None):
        """Soft delete the product"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = deleted_by
        self.status = "discontinued"
        self.save()


# Optional: Global Secondary Indexes
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

class SKUIndex(GlobalSecondaryIndex):
    """GSI for querying by SKU"""
    class Meta:
        index_name = 'sku-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    sku = UnicodeAttribute(hash_key=True)


class CategoryIndex(GlobalSecondaryIndex):
    """GSI for querying by category"""
    class Meta:
        index_name = 'category-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    category_id = UnicodeAttribute(hash_key=True)


class StatusIndex(GlobalSecondaryIndex):
    """GSI for querying by status"""
    class Meta:
        index_name = 'status-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    status = UnicodeAttribute(hash_key=True)


# To use GSIs, add to Product model:
# sku_index = SKUIndex()
# category_index = CategoryIndex()
# status_index = StatusIndex()


if __name__ == "__main__":
    # Test the model
    print("Product model loaded successfully")
    print(f"Table name: {Product.Meta.table_name}")
    print(f"Region: {Product.Meta.region}")
    
    # Example usage
    product = Product(
        id="PROD001",
        product_id="EXT001",
        sku="SKU12345",
        name="Wireless Headphones",
        category_id="CAT001",
        supplier_id="SUPP001",
        quantity_received=100,
        quantity_remaining=80,
        pricing=PricingInfo(
            cost_price=50,
            selling_price=99.99,
            currency="USD"
        )
    )
    print("Sample product created")
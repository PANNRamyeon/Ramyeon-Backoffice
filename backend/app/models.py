from django.db import models
from datetime import datetime
from typing import Optional, List
import uuid

class User:
    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id', f"USER-{uuid.uuid4()}")
        self.username = kwargs.get('username', '')
        self.email = kwargs.get('email', '')
        self.password = kwargs.get('password', '')
        self.full_name = kwargs.get('full_name', '')
        self.role = kwargs.get('role', 'user')
        self.status = kwargs.get('status', 'active')
        self.date_created = kwargs.get('date_created', datetime.utcnow())
        self.last_updated = kwargs.get('last_updated', datetime.utcnow())
        self.last_login = kwargs.get('last_login')
        self.source = kwargs.get('source', 'system')
        self.reset_token = kwargs.get('reset_token')
        self.reset_token_expires = kwargs.get('reset_token_expires')

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'password': self.password,
            'full_name': self.full_name,
            'role': self.role,
            'status': self.status,
            'date_created': self.date_created.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'source': self.source,
        }

class Customer:
    def __init__(self, **kwargs):
        self.customer_id = kwargs.get('customer_id', f"CUST-{uuid.uuid4()}")
        self.full_name = kwargs.get('full_name', '')
        self.email = kwargs.get('email', '')
        self.phone = kwargs.get('phone', '')
        self.delivery_address = kwargs.get('delivery_address', {})
        self.loyalty_points = kwargs.get('loyalty_points', 0)
        self.last_purchase = kwargs.get('last_purchase')
        self.date_created = kwargs.get('date_created', datetime.utcnow())
        self.last_updated = kwargs.get('last_updated', datetime.utcnow())
        self.status = kwargs.get('status', 'active')
        self.source = kwargs.get('source', 'system')

    def to_dict(self):
        return {
            'customer_id': self.customer_id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'delivery_address': self.delivery_address,
            'loyalty_points': self.loyalty_points,
            'last_purchase': self.last_purchase.isoformat() if self.last_purchase else None,
            'date_created': self.date_created.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'status': self.status,
            'source': self.source
        }
    
class Product:
    def __init__(self, **kwargs):
        self.product_id = kwargs.get('product_id', f"PROD-{uuid.uuid4()}")
        self.product_name = kwargs.get('product_name', '')
        self.category_id = kwargs.get('category_id', None)
        self.supplier_id = kwargs.get('supplier_id', None)
        self.branch_id = kwargs.get('branch_id', None)
        self.unit = kwargs.get('unit', 'pcs')
        self.stock = kwargs.get('stock', 0)
        self.expiry_date = kwargs.get('expiry_date', None)
        self.low_stock_threshold = kwargs.get('low_stock_threshold', 10)
        self.cost_price = kwargs.get('cost_price', 0.0)
        self.selling_price = kwargs.get('selling_price', 0.0)
        self.date_received = kwargs.get('date_received', datetime.utcnow())
        self.status = kwargs.get('status', 'active')
        self.is_taxable = kwargs.get('is_taxable', True)
        self.SKU = kwargs.get('SKU', '')
        self.sync_logs = kwargs.get('sync_logs', [])

    def to_dict(self):
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'category_id': self.category_id,
            'supplier_id': self.supplier_id,
            'branch_id': self.branch_id,
            'unit': self.unit,
            'stock': self.stock,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'low_stock_threshold': self.low_stock_threshold,
            'cost_price': float(self.cost_price),
            'selling_price': float(self.selling_price),
            'date_received': self.date_received.isoformat(),
            'status': self.status,
            'is_taxable': self.is_taxable,
            'SKU': self.SKU,
            'sync_logs': self.sync_logs
        }

class Category:
    def __init__(self, **kwargs):
        self.category_id = kwargs.get('category_id', f"CTGY-{uuid.uuid4()}")
        self.category_name = kwargs.get('category_name', '')
        self.description = kwargs.get('description', '')
        self.status = kwargs.get('status', 'active')
        self.date_created = kwargs.get('date_created', datetime.utcnow())
        self.last_updated = kwargs.get('last_updated', datetime.utcnow())
        self.sub_categories = kwargs.get('sub_categories', [])
        self.isDeleted = kwargs.get('isDeleted', False)
        self.deleted_at = kwargs.get('deleted_at', None)
        self.restored_at = kwargs.get('restored_at', None)
        self.image_url = kwargs.get('image_url', None)

    def to_dict(self):
        """Convert Category object to a dictionary."""
        return {
            'category_id': self.category_id,
            'category_name': self.category_name,
            'description': self.description,
            'status': self.status,
            'date_created': self.date_created.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'sub_categories': self.sub_categories,
            'isDeleted': self.isDeleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'restored_at': self.restored_at.isoformat() if self.restored_at else None,
            'image_url': self.image_url
        }

class SalesLog:
    # ... (constants can remain)
    def __init__(self, **kwargs):
        self.saleslog_id = kwargs.get('saleslog_id', f"SALE-{uuid.uuid4()}")
        self.customer_id = kwargs.get('customer_id')
        self.user_id = kwargs.get('user_id')
        self.transaction_date = kwargs.get('transaction_date', datetime.utcnow())
        self.total_amount = kwargs.get('total_amount', 0.0)
        self.status = kwargs.get('status', 'completed')
        self.payment_method = kwargs.get('payment_method', 'cash')
        self.sales_type = kwargs.get('sales_type', 'dine_in')
        self.item_list = kwargs.get('item_list', [])
        # ... other fields

    def to_dict(self):
        """Convert to JSON-serializable dictionary."""
        return {
            'saleslog_id': self.saleslog_id,
            'customer_id': self.customer_id,
            'user_id': self.user_id,
            'transaction_date': self.transaction_date.isoformat(),
            'total_amount': float(self.total_amount),
            'status': self.status,
            'payment_method': self.payment_method,
            'sales_type': self.sales_type,
            'item_list': self.item_list,
        }
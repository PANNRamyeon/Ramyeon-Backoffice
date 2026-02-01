from django.db import models
from datetime import datetime
from typing import Optional, List
import uuid # Import uuid for generating unique IDs

class Promotions:
    def __init__(self, **kwargs):
        # Replace ObjectId with UUID for unique ID generation
        self._id = kwargs.get('_id', str(uuid.uuid4()))
        self.promotion_id = kwargs.get('promotion_id', str(uuid.uuid4()))
        self.promotion_name = kwargs.get('promotion_name', '')  
        self.discount_type = kwargs.get('discount_type', '')  
        self.discount_value = kwargs.get('discount_value', 0)
        self.last_updated = kwargs.get('last_updated', datetime.utcnow())
        self.applicable_products = kwargs.get('applicable_products', [])  # Added missing field
        self.product_id = kwargs.get('product_id', None)
        self.start_date = kwargs.get('start_date', datetime.utcnow())
        self.end_date = kwargs.get('end_date', datetime.utcnow())
        self.sync_logs = kwargs.get('sync_logs', [])  # Contains objects with last_updated, source, status
    
    def to_dict(self):
        return {
            '_id': self._id,
            'promotion_id': self.promotion_id,
            'promotion_name': self.promotion_name,
            'discount_type': self.discount_type, 
            'discount_value': self.discount_value,
            'last_updated': self.last_updated,
            'applicable_products': self.applicable_products,  
            'product_id': self.product_id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'sync_logs': self.sync_logs,  
        }
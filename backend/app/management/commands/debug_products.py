"""
Django Management Command: Debug Products
=========================================
Quick debug to see product data issues

Usage:
    python manage.py debug_products
"""

from django.core.management.base import BaseCommand
from app.services.product_service import ProductService

class Command(BaseCommand):
    help = 'Debug product data to find issues'

    def handle(self, *args, **options):
        service = ProductService()
        db = service.db
        
        # Check total products
        total = db.products.count_documents({})
        active = db.products.count_documents({'status': 'active'})
        not_deleted = db.products.count_documents({'isDeleted': {'$ne': True}})
        has_stock = db.products.count_documents({'stock': {'$gt': 0}})
        
        # Check products matching customer API query
        customer_query = {
            'status': 'active',
            'isDeleted': {'$ne': True},
            'stock': {'$gt': 0}
        }
        matching_customer_api = db.products.count_documents(customer_query)
        
        self.stdout.write("=" * 80)
        self.stdout.write("📊 PRODUCT DATA DEBUG")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total products: {total}")
        self.stdout.write(f"Status = 'active': {active}")
        self.stdout.write(f"isDeleted != True: {not_deleted}")
        self.stdout.write(f"Stock > 0: {has_stock}")
        self.stdout.write(f"\n✅ Products matching customer API query:")
        self.stdout.write(f"   (status='active' AND isDeleted!=True AND stock>0): {matching_customer_api}")
        
        # Sample products
        self.stdout.write(f"\n📦 Sample products:")
        sample = list(db.products.find(customer_query).limit(5))
        for product in sample:
            self.stdout.write(f"\n   Product: {product.get('product_name')}")
            self.stdout.write(f"   - ID: {product.get('_id')}")
            self.stdout.write(f"   - Status: {product.get('status')}")
            self.stdout.write(f"   - isDeleted: {product.get('isDeleted', 'Not set')}")
            self.stdout.write(f"   - Stock: {product.get('stock')}")
            self.stdout.write(f"   - Has image_url: {'Yes' if product.get('image_url') else 'No'}")
            self.stdout.write(f"   - Has image: {'Yes' if product.get('image') else 'No'}")
        
        # Check statuses
        self.stdout.write(f"\n📋 Status field values:")
        statuses = db.products.distinct('status')
        for stat in statuses:
            count = db.products.count_documents({'status': stat})
            self.stdout.write(f"   '{stat}': {count} products")
        
        # Check isDeleted
        self.stdout.write(f"\n🗑️  isDeleted field values:")
        deleted_true = db.products.count_documents({'isDeleted': True})
        deleted_false = db.products.count_documents({'isDeleted': False})
        deleted_not_set = db.products.count_documents({'isDeleted': {'$exists': False}})
        self.stdout.write(f"   True: {deleted_true}")
        self.stdout.write(f"   False: {deleted_false}")
        self.stdout.write(f"   Not set: {deleted_not_set}")
        
        self.stdout.write("=" * 80)



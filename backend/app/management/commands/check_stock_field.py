"""
Django Management Command: Check Stock Field
=============================================
Check if stock field has data type issues

Usage:
    python manage.py check_stock_field
"""

from django.core.management.base import BaseCommand
from app.services.product_service import ProductService

class Command(BaseCommand):
    help = 'Check stock field data types'

    def handle(self, *args, **options):
        service = ProductService()
        db = service.db
        
        self.stdout.write("=" * 80)
        self.stdout.write("🔍 CHECKING STOCK FIELD DATA TYPES")
        self.stdout.write("=" * 80)
        
        # Get some products with different stock values
        products_with_stock_shown = list(db.products.find({
            'status': 'active',
            'isDeleted': False
        }).limit(10))
        
        self.stdout.write(f"\n📦 Checking {len(products_with_stock_shown)} sample products:\n")
        
        for product in products_with_stock_shown:
            stock_value = product.get('stock')
            stock_type = type(stock_value).__name__
            
            self.stdout.write(f"Product: {product.get('product_name')}")
            self.stdout.write(f"  - Stock value: {stock_value}")
            self.stdout.write(f"  - Stock type: {stock_type}")
            self.stdout.write(f"  - Stock > 0?: {stock_value > 0 if isinstance(stock_value, (int, float)) else 'ERROR - not numeric'}")
            
            # Check if this would match the query
            test_query = {
                '_id': product['_id'],
                'status': 'active',
                'isDeleted': False,
                'stock': {'$gt': 0}
            }
            matches = db.products.count_documents(test_query)
            self.stdout.write(f"  - Matches customer API query?: {'YES' if matches > 0 else 'NO'}")
            self.stdout.write("")
        
        # Check different stock value types in database
        self.stdout.write("\n📊 Stock field statistics:")
        
        # Count by type
        pipeline = [
            {'$match': {'status': 'active', 'isDeleted': False}},
            {'$project': {
                'product_name': 1,
                'stock': 1,
                'stock_type': {'$type': '$stock'}
            }},
            {'$group': {
                '_id': '$stock_type',
                'count': {'$sum': 1}
            }}
        ]
        
        stock_types = list(db.products.aggregate(pipeline))
        for st in stock_types:
            self.stdout.write(f"  Stock field type '{st['_id']}': {st['count']} products")
        
        # Check stock values
        self.stdout.write("\n📈 Stock value ranges:")
        zero_stock = db.products.count_documents({
            'status': 'active',
            'isDeleted': False,
            'stock': 0
        })
        self.stdout.write(f"  Stock = 0: {zero_stock} products")
        
        greater_than_zero = db.products.count_documents({
            'status': 'active',
            'isDeleted': False,
            'stock': {'$gt': 0}
        })
        self.stdout.write(f"  Stock > 0: {greater_than_zero} products")
        
        # Check if stock field exists
        no_stock_field = db.products.count_documents({
            'status': 'active',
            'isDeleted': False,
            'stock': {'$exists': False}
        })
        self.stdout.write(f"  No stock field: {no_stock_field} products")
        
        # Check null stock
        null_stock = db.products.count_documents({
            'status': 'active',
            'isDeleted': False,
            'stock': None
        })
        self.stdout.write(f"  Stock = null: {null_stock} products")
        
        self.stdout.write("\n" + "=" * 80)
        
        # Recommendation
        if greater_than_zero < 10:
            self.stdout.write(self.style.ERROR("\n⚠️  ISSUE FOUND: Very few products have stock > 0"))
            self.stdout.write("This is why customers can't see products!")
            self.stdout.write("\nPossible causes:")
            self.stdout.write("1. Stock values are stored as strings instead of numbers")
            self.stdout.write("2. Stock field is missing from most products")
            self.stdout.write("3. Products need to be restocked")
            self.stdout.write("\nRun this to check a specific product:")
            self.stdout.write("  db.products.findOne({product_name: 'PRODUCT_NAME'})")
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✅ {greater_than_zero} products have stock > 0"))



"""
Django Management Command: Show Raw Products
=============================================
Show raw database data vs what ProductService.get_all_products() returns

Usage:
    python manage.py show_raw_products
"""

from django.core.management.base import BaseCommand
from app.services.product_service import ProductService
from tabulate import tabulate

class Command(BaseCommand):
    help = 'Show raw product data from database vs ProductService'

    def handle(self, *args, **options):
        service = ProductService()
        db = service.db
        
        self.stdout.write("=" * 120)
        self.stdout.write("📊 COMPARING RAW DATABASE vs ProductService.get_all_products()")
        self.stdout.write("=" * 120)
        
        # Get 20 random active products
        products_raw = list(db.products.find({
            'status': 'active',
            'isDeleted': False
        }).limit(20))
        
        self.stdout.write(f"\n✅ Fetched {len(products_raw)} products from database\n")
        
        # Show comparison
        table_data = []
        
        for product in products_raw:
            product_id = product['_id']
            product_name = product.get('product_name', 'Unknown')[:25]
            
            # RAW database value
            raw_stock = product.get('stock')
            raw_total = product.get('total_stock')
            
            # What ProductService.get_all_products() would show
            # (it recalculates from batches)
            product_from_service = service.get_product_by_id(product_id)
            service_stock = product_from_service.get('stock') if product_from_service else 'N/A'
            service_total = product_from_service.get('total_stock') if product_from_service else 'N/A'
            
            # Calculate from batches directly
            batches = list(db.batches.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }))
            batch_stock = sum(b['quantity_remaining'] for b in batches)
            
            table_data.append([
                product_name,
                str(raw_stock) if raw_stock is not None else 'NULL',
                str(raw_total) if raw_total is not None else 'NULL',
                str(service_stock),
                str(service_total),
                batch_stock,
                len(batches),
                '❌ MISMATCH' if raw_stock != batch_stock else '✅ OK'
            ])
        
        headers = [
            'Product Name',
            'DB Stock',
            'DB Total',
            'Service Stock',
            'Service Total',
            'Batch Calc',
            'Batches',
            'Status'
        ]
        
        self.stdout.write(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        self.stdout.write("\n" + "=" * 120)
        self.stdout.write("📝 EXPLANATION:")
        self.stdout.write("=" * 120)
        self.stdout.write("""
DB Stock/Total    = Raw value stored in MongoDB products.stock field
Service Stock     = What ProductService.get_product_by_id() returns
Batch Calc        = Actual stock calculated from batches collection
        
WHY THE DIFFERENCE?
- ProductService.get_all_products() has optimization that recalculates stock from batches
- This makes POS and other systems show correct stock
- BUT CustomerProductService uses the RAW database field (products.stock)
- If products.stock is NULL/0, customers won't see the product!

THE FIX:
Run: python manage.py sync_all_stock --live
This will sync products.stock field with batch calculations.
        """)
        
        # Show which products would be visible to customers
        self.stdout.write("\n" + "=" * 120)
        self.stdout.write("🌐 CUSTOMER API VISIBILITY CHECK")
        self.stdout.write("=" * 120)
        
        visible_count = 0
        invisible_count = 0
        
        for product in products_raw:
            raw_stock = product.get('stock')
            product_name = product.get('product_name', 'Unknown')[:30]
            
            # Check if would be visible in customer API
            if raw_stock is not None and raw_stock > 0:
                visible_count += 1
                status = "✅ VISIBLE"
            else:
                invisible_count += 1
                status = f"❌ HIDDEN (stock={raw_stock})"
            
            self.stdout.write(f"  {product_name:.<35} {status}")
        
        self.stdout.write("\n" + "=" * 120)
        self.stdout.write(f"Summary: {visible_count} visible, {invisible_count} hidden from customers")
        self.stdout.write("=" * 120)



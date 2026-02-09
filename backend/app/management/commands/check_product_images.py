"""
Django Management Command: Check Product Images
================================================
Check if products have image data stored

Usage:
    python manage.py check_product_images
"""

from django.core.management.base import BaseCommand
from app.services.product_service import ProductService
from tabulate import tabulate

class Command(BaseCommand):
    help = 'Check which products have images'

    def handle(self, *args, **options):
        service = ProductService()
        db = service.db
        
        self.stdout.write("=" * 100)
        self.stdout.write("🖼️  PRODUCT IMAGE CHECK")
        self.stdout.write("=" * 100)
        
        # Get all active products
        products = list(db.products.find({
            'status': 'active',
            'isDeleted': False,
            'total_stock': {'$gt': 0}
        }).limit(20))
        
        self.stdout.write(f"\n📦 Checking {len(products)} products:\n")
        
        table_data = []
        has_image = 0
        has_image_url = 0
        has_nothing = 0
        
        for product in products:
            name = product.get('product_name', 'Unknown')[:30]
            
            image = product.get('image')
            image_url = product.get('image_url')
            image_filename = product.get('image_filename')
            
            has_img = 'Yes' if image else 'No'
            has_url = 'Yes' if image_url else 'No'
            has_file = image_filename if image_filename else 'No'
            
            if image:
                has_image += 1
            if image_url:
                has_image_url += 1
            if not image and not image_url:
                has_nothing += 1
            
            table_data.append([
                name,
                has_img,
                has_url,
                has_file
            ])
        
        headers = ['Product Name', 'Has image', 'Has image_url', 'Filename']
        self.stdout.write(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("📊 SUMMARY:")
        self.stdout.write("=" * 100)
        self.stdout.write(f"Products with 'image' field: {has_image}")
        self.stdout.write(f"Products with 'image_url' field: {has_image_url}")
        self.stdout.write(f"Products with NO images: {has_nothing}")
        
        self.stdout.write("\n" + "=" * 100)
        
        if has_nothing == len(products):
            self.stdout.write(self.style.WARNING("\n⚠️  NO PRODUCTS HAVE IMAGES!"))
            self.stdout.write("\nYour products don't have images stored in the database.")
            self.stdout.write("You need to either:")
            self.stdout.write("1. Upload images through the POS admin interface")
            self.stdout.write("2. Bulk import products with image URLs")
            self.stdout.write("3. Add default images to products")
        elif has_nothing > 0:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {has_nothing} products are missing images"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ All products have images!"))
        
        # Show sample product data
        if products:
            self.stdout.write("\n" + "=" * 100)
            self.stdout.write("📋 SAMPLE PRODUCT DATA:")
            self.stdout.write("=" * 100)
            sample = products[0]
            self.stdout.write(f"\nProduct: {sample.get('product_name')}")
            self.stdout.write(f"  - image: {sample.get('image', 'NOT SET')}")
            self.stdout.write(f"  - image_url: {sample.get('image_url', 'NOT SET')}")
            self.stdout.write(f"  - image_filename: {sample.get('image_filename', 'NOT SET')}")
            self.stdout.write(f"  - image_type: {sample.get('image_type', 'NOT SET')}")
            
            # Show what API returns
            self.stdout.write("\n" + "=" * 100)
            self.stdout.write("🌐 WHAT CUSTOMER API RETURNS:")
            self.stdout.write("=" * 100)
            from app.kpi_views.customer_product_views import CustomerProductService
            customer_service = CustomerProductService()
            result = customer_service.get_product_by_id(sample['_id'])
            if result.get('success'):
                api_product = result['product']
                self.stdout.write(f"\nAPI Response for '{api_product.get('product_name')}':")
                self.stdout.write(f"  - Has 'image': {'Yes' if 'image' in api_product else 'No'}")
                self.stdout.write(f"  - Has 'image_url': {'Yes' if 'image_url' in api_product else 'No'}")
                if 'image_url' in api_product:
                    self.stdout.write(f"  - image_url value: {api_product['image_url']}")



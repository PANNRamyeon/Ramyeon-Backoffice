"""
Seed sample data for testing batches: ensures 1 category, 2 products, 1 supplier,
then creates 2 batches per product so batches correspond to real products.

Usage:
    python manage.py seed_sample_batches
"""
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
import logging

from models.Categories import Category
from models.Product import Product
from models.Supplier import Supplier
from models.Batches import Batch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seed a category, 2 products, 1 supplier, and 2 batches per product for testing"

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("SEED SAMPLE BATCHES (category → products → supplier → batches)")
        self.stdout.write("=" * 60)

        try:
            # 1. Category
            categories = Category.get_active_categories()
            if not categories:
                self.stdout.write("Creating category 'Test Category'...")
                category = Category.create_category(
                    category_name="Test Category",
                    description="For batch/product testing",
                )
                category_id = category.sk
                self.stdout.write(self.style.SUCCESS(f"  Created category: {category_id}"))
            else:
                category = categories[0]
                category_id = category.sk
                self.stdout.write(f"Using existing category: {category_id}")

            # 2. Products (need at least 2)
            products = Product.get_all_active_products()
            product_ids = []
            for i in range(2):
                if i < len(products):
                    product_ids.append(products[i].sk)
                    self.stdout.write(f"Using existing product: {products[i].sk} - {products[i].product_name}")
                else:
                    self.stdout.write(f"Creating product {i + 1}...")
                    product = Product.create_product(
                        product_name=f"Test Product {i + 1}",
                        sku=f"SEED-SKU-{datetime.utcnow().strftime('%H%M%S')}-{i}",
                        category_id=category_id,
                        cost_price=10.0 + i * 5,
                        selling_price=15.0 + i * 5,
                        unit="unit",
                    )
                    product_ids.append(product.sk)
                    self.stdout.write(self.style.SUCCESS(f"  Created product: {product.sk}"))

            if len(product_ids) < 2:
                self.stdout.write(self.style.WARNING("Need at least 2 products; created/used only %s" % len(product_ids)))

            # 3. Supplier
            suppliers = list(Supplier.scan(Supplier.pk == "suppliers", limit=5))
            if not suppliers:
                self.stdout.write("Creating supplier 'Test Supplier'...")
                supplier = Supplier.create_supplier("Test Supplier", contact_person="Seed", phone_number="0000000000")
                supplier_id = supplier.sk
                self.stdout.write(self.style.SUCCESS(f"  Created supplier: {supplier_id}"))
            else:
                supplier_id = suppliers[0].sk
                self.stdout.write(f"Using existing supplier: {supplier_id}")

            # 4. Batches (2 per product)
            now = datetime.utcnow()
            date_received = now - timedelta(days=2)
            expiry_date = now + timedelta(days=90)

            batches_created = 0
            for idx, product_id in enumerate(product_ids[:2]):
                for b in range(2):
                    batch_number = f"SEED-{product_id}-{b + 1}"
                    self.stdout.write(f"Creating batch for product {product_id}: {batch_number}...")
                    batch = Batch.create_batch(
                        product_id=product_id,
                        batch_number=batch_number,
                        quantity_received=50 + b * 25,
                        quantity_remaining=50 + b * 25,
                        cost_price=10.0 + idx * 5,
                        expiry_date=expiry_date,
                        date_received=date_received,
                        supplier_id=supplier_id,
                    )
                    batches_created += 1
                    self.stdout.write(self.style.SUCCESS(f"  Created batch: {batch.sk}"))

            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS(f"Done. Created {batches_created} batch(es)."))
            self.stdout.write("=" * 60)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            logger.exception("seed_sample_batches failed")
            raise

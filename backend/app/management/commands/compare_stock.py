"""
Django Management Command: Compare Stock
=========================================
Compares product stock across three sources:
1. Cloud MongoDB database (direct)
2. Customer API (what PANNRamyeonCorner sees)
3. Batch FIFO system (calculated)

Usage:
    python manage.py compare_stock
    python manage.py compare_stock --export report.json
    python manage.py compare_stock --product-id PROD-00001
    python manage.py compare_stock --show-matches
"""

from django.core.management.base import BaseCommand
from app.services.product_service import ProductService
from app.services.batch_service import BatchService
from app.kpi_views.customer_product_views import CustomerProductService
from datetime import datetime
from tabulate import tabulate
import json
import sys


class Command(BaseCommand):
    help = 'Compare product stock across database, customer API, and batch system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-id',
            type=str,
            help='Check specific product ID only'
        )
        parser.add_argument(
            '--show-matches',
            action='store_true',
            help='Show matching products too'
        )
        parser.add_argument(
            '--export',
            type=str,
            help='Export results to JSON file'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product_service = ProductService()
        self.batch_service = BatchService()
        self.customer_service = CustomerProductService()

    def calculate_batch_stock(self, product_id):
        """Calculate actual stock from active batches"""
        try:
            now = datetime.utcnow()
            db = self.batch_service.db
            batches_collection = db.batches
            
            # Get all active batches for this product
            batches = list(batches_collection.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }))
            
            # Filter out expired batches
            non_expired_batches = []
            for batch in batches:
                expiry_date = batch.get('expiry_date')
                if not expiry_date:
                    non_expired_batches.append(batch)
                else:
                    # Handle both datetime and string dates
                    if isinstance(expiry_date, str):
                        try:
                            from dateutil import parser
                            expiry_date = parser.parse(expiry_date)
                        except Exception:
                            non_expired_batches.append(batch)
                            continue
                    
                    if isinstance(expiry_date, datetime) and expiry_date >= now:
                        non_expired_batches.append(batch)
            
            # Calculate total stock from non-expired batches
            total_stock = sum(batch['quantity_remaining'] for batch in non_expired_batches)
            
            return {
                'total_stock': total_stock,
                'active_batches': len(non_expired_batches),
                'expired_batches': len(batches) - len(non_expired_batches)
            }
        except Exception as e:
            self.stderr.write(f"Error calculating batch stock for {product_id}: {e}")
            return {'total_stock': 0, 'active_batches': 0, 'expired_batches': 0}

    def check_specific_product(self, product_id):
        """Check stock for a specific product"""
        self.stdout.write(f"\n🔍 Checking product: {product_id}\n")
        
        # Get from database
        cloud_product = self.product_service.get_product_by_id(product_id)
        if not cloud_product:
            self.stderr.write(f"❌ Product {product_id} not found in database")
            return
        
        # Get from customer service (simulates API)
        customer_result = self.customer_service.get_product_by_id(product_id)
        api_product = customer_result.get('product') if customer_result.get('success') else None
        
        # Calculate batch stock
        batch_info = self.calculate_batch_stock(product_id)
        
        # Display details
        self.stdout.write("=" * 80)
        self.stdout.write(f"Product: {cloud_product.get('product_name')}")
        self.stdout.write(f"SKU: {cloud_product.get('SKU')}")
        self.stdout.write(f"Status: {cloud_product.get('status')}")
        self.stdout.write("=" * 80)
        self.stdout.write(f"\n📦 Cloud Database:")
        self.stdout.write(f"   Stock: {cloud_product.get('stock', 0)}")
        self.stdout.write(f"   Total Stock: {cloud_product.get('total_stock', 0)}")
        self.stdout.write(f"   Low Stock Threshold: {cloud_product.get('low_stock_threshold', 0)}")
        
        self.stdout.write(f"\n🌐 Customer API:")
        if api_product:
            self.stdout.write(f"   Stock: {api_product.get('stock', 0)}")
            self.stdout.write(f"   Status: Visible in API")
        else:
            self.stdout.write(f"   Status: NOT visible in API")
        
        self.stdout.write(f"\n📊 Batch System:")
        self.stdout.write(f"   Calculated Stock: {batch_info['total_stock']}")
        self.stdout.write(f"   Active Batches: {batch_info['active_batches']}")
        self.stdout.write(f"   Expired Batches: {batch_info['expired_batches']}")
        
        # Check for mismatches
        self.stdout.write(f"\n🔍 Analysis:")
        if cloud_product.get('stock', 0) != batch_info['total_stock']:
            self.stdout.write(
                self.style.WARNING(
                    f"   ⚠️  MISMATCH: Cloud stock ({cloud_product.get('stock', 0)}) != "
                    f"Batch stock ({batch_info['total_stock']})"
                )
            )
        
        if api_product and cloud_product.get('stock', 0) != api_product.get('stock', 0):
            self.stdout.write(
                self.style.WARNING(
                    f"   ⚠️  MISMATCH: Cloud stock ({cloud_product.get('stock', 0)}) != "
                    f"API stock ({api_product.get('stock', 0)})"
                )
            )
        
        if not api_product and cloud_product.get('stock', 0) > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"   ⚠️  ISSUE: Product has stock but not visible in customer API"
                )
            )
        
        self.stdout.write("=" * 80)

    def compare_all_products(self, show_matches=False, export_file=None):
        """Compare stock across all products"""
        self.stdout.write("\n🔍 Starting Stock Comparison...\n")
        
        # Get all products from database
        cloud_products = self.product_service.get_all_products(include_deleted=False)
        self.stdout.write(f"📦 Found {len(cloud_products)} products in cloud database")
        
        # Get customer-visible products (fetch all pages)
        api_products = []
        page = 1
        while True:
            customer_result = self.customer_service.get_all_active_products(page=page, limit=100)
            if customer_result.get('success') and customer_result.get('products'):
                api_products.extend(customer_result['products'])
                pagination = customer_result.get('pagination', {})
                if not pagination.get('has_next', False):
                    break
                page += 1
            else:
                break
        self.stdout.write(f"🌐 Found {len(api_products)} products from customer API")
        
        # Create lookup dictionaries
        cloud_dict = {str(p['_id']): p for p in cloud_products}
        api_dict = {str(p['_id']): p for p in api_products}
        
        # Comparison results
        mismatches = []
        matches = []
        missing_from_api = []
        
        self.stdout.write(f"\n📊 Analyzing {len(cloud_dict)} products...\n")
        
        for product_id, cloud_product in cloud_dict.items():
            api_product = api_dict.get(product_id)
            
            # Get stock values
            cloud_stock = int(cloud_product.get('stock', 0))
            cloud_total_stock = int(cloud_product.get('total_stock', cloud_stock))
            
            # Calculate batch stock
            batch_info = self.calculate_batch_stock(product_id)
            batch_stock = batch_info['total_stock']
            
            product_name = cloud_product.get('product_name', 'Unknown')
            sku = cloud_product.get('SKU', 'N/A')
            
            # Check if product appears in customer API
            if api_product:
                api_stock = int(api_product.get('stock', 0))
                
                # Check for mismatches
                has_mismatch = False
                mismatch_type = []
                
                if cloud_stock != api_stock:
                    has_mismatch = True
                    mismatch_type.append('cloud_vs_api')
                
                if cloud_stock != batch_stock:
                    has_mismatch = True
                    mismatch_type.append('cloud_vs_batch')
                
                if cloud_stock != cloud_total_stock:
                    has_mismatch = True
                    mismatch_type.append('stock_vs_total_stock')
                
                comparison = {
                    'product_id': product_id,
                    'product_name': product_name,
                    'sku': sku,
                    'cloud_stock': cloud_stock,
                    'cloud_total_stock': cloud_total_stock,
                    'api_stock': api_stock,
                    'batch_stock': batch_stock,
                    'active_batches': batch_info['active_batches'],
                    'expired_batches': batch_info['expired_batches'],
                    'status': cloud_product.get('status', 'N/A'),
                    'has_mismatch': has_mismatch,
                    'mismatch_type': ', '.join(mismatch_type) if mismatch_type else 'none'
                }
                
                if has_mismatch:
                    mismatches.append(comparison)
                else:
                    matches.append(comparison)
            else:
                # Product exists in cloud but not in API
                if cloud_stock > 0 and cloud_product.get('status') == 'active':
                    missing_from_api.append({
                        'product_id': product_id,
                        'product_name': product_name,
                        'sku': sku,
                        'cloud_stock': cloud_stock,
                        'cloud_total_stock': cloud_total_stock,
                        'batch_stock': batch_stock,
                        'status': cloud_product.get('status', 'N/A'),
                        'reason': 'Missing from customer API despite having stock > 0'
                    })
        
        # Display results
        self._display_results(mismatches, matches, missing_from_api, show_matches)
        
        # Export if requested
        if export_file:
            self._export_results(mismatches, matches, missing_from_api, export_file)
        
        return {
            'mismatches': mismatches,
            'matches': matches,
            'missing_from_api': missing_from_api,
            'total_checked': len(cloud_dict),
            'mismatch_count': len(mismatches),
            'match_count': len(matches),
            'missing_count': len(missing_from_api)
        }

    def _display_results(self, mismatches, matches, missing_from_api, show_matches):
        """Display comparison results in formatted tables"""
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("📊 STOCK COMPARISON SUMMARY")
        self.stdout.write("=" * 80)
        
        self.stdout.write(f"\n✅ Matching Products: {len(matches)}")
        self.stdout.write(
            self.style.ERROR(f"❌ Mismatched Products: {len(mismatches)}") 
            if mismatches else f"❌ Mismatched Products: 0"
        )
        self.stdout.write(
            self.style.WARNING(f"⚠️  Missing from API: {len(missing_from_api)}")
            if missing_from_api else f"⚠️  Missing from API: 0"
        )
        
        if mismatches:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR("❌ STOCK MISMATCHES FOUND"))
            self.stdout.write("=" * 80)
            
            table_data = []
            for item in mismatches:
                table_data.append([
                    item['product_name'][:30],
                    item['sku'],
                    item['cloud_stock'],
                    item['cloud_total_stock'],
                    item['api_stock'],
                    item['batch_stock'],
                    item['active_batches'],
                    item['mismatch_type']
                ])
            
            headers = ['Product Name', 'SKU', 'Cloud', 'Total', 'API', 'Batch', 'Batches', 'Type']
            self.stdout.write(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        if missing_from_api:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("⚠️  PRODUCTS MISSING FROM CUSTOMER API"))
            self.stdout.write("=" * 80)
            
            table_data = []
            for item in missing_from_api:
                table_data.append([
                    item['product_name'][:30],
                    item['sku'],
                    item['cloud_stock'],
                    item['batch_stock'],
                    item['status']
                ])
            
            headers = ['Product Name', 'SKU', 'Cloud Stock', 'Batch Stock', 'Status']
            self.stdout.write(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        if show_matches and matches:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS("✅ MATCHING PRODUCTS (First 20)"))
            self.stdout.write("=" * 80)
            
            table_data = []
            for item in matches[:20]:
                table_data.append([
                    item['product_name'][:30],
                    item['sku'],
                    item['cloud_stock'],
                    item['api_stock'],
                    item['batch_stock']
                ])
            
            headers = ['Product Name', 'SKU', 'Cloud', 'API', 'Batch']
            self.stdout.write(tabulate(table_data, headers=headers, tablefmt='grid'))
            
            if len(matches) > 20:
                self.stdout.write(f"\n... and {len(matches) - 20} more matching products")

    def _export_results(self, mismatches, matches, missing_from_api, filename):
        """Export comparison results to JSON file"""
        try:
            results = {
                'generated_at': datetime.utcnow().isoformat(),
                'summary': {
                    'total_mismatches': len(mismatches),
                    'total_matches': len(matches),
                    'total_missing_from_api': len(missing_from_api)
                },
                'mismatches': mismatches,
                'matches': matches,
                'missing_from_api': missing_from_api
            }
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            self.stdout.write(self.style.SUCCESS(f"\n💾 Results exported to: {filename}"))
        except Exception as e:
            self.stderr.write(f"❌ Error exporting results: {e}")

    def handle(self, *args, **options):
        """Main command handler"""
        try:
            if options['product_id']:
                # Check specific product
                self.check_specific_product(options['product_id'])
            else:
                # Full comparison
                results = self.compare_all_products(
                    show_matches=options['show_matches'],
                    export_file=options['export']
                )
                
                # Print summary
                self.stdout.write("\n" + "=" * 80)
                self.stdout.write(self.style.SUCCESS("✅ Comparison Complete!"))
                self.stdout.write("=" * 80)
                self.stdout.write(f"Total Products Checked: {results['total_checked']}")
                
                if results['mismatch_count'] > 0:
                    self.stdout.write(self.style.ERROR(f"Mismatches: {results['mismatch_count']}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"Mismatches: 0"))
                
                self.stdout.write(f"Matches: {results['match_count']}")
                
                if results['missing_count'] > 0:
                    self.stdout.write(self.style.WARNING(f"Missing from API: {results['missing_count']}"))
                else:
                    self.stdout.write(f"Missing from API: 0")
                
                if results['mismatch_count'] > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"\n⚠️  Found {results['mismatch_count']} products with stock mismatches!"
                        )
                    )
                    self.stdout.write("   Run: python manage.py fix_stock --help")
                else:
                    self.stdout.write(self.style.SUCCESS("\n✅ All product stocks are in sync!"))
        
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error: {str(e)}"))
            sys.exit(1)


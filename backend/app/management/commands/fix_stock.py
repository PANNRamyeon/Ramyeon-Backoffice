"""
Django Management Command: Fix Stock
====================================
Automatically fixes stock mismatches identified by compare_stock command.

Usage:
    python manage.py fix_stock --help
    python manage.py fix_stock --dry-run --fix-all
    python manage.py fix_stock --fix-batches
    python manage.py fix_stock --fix-fields
    python manage.py fix_stock --fix-missing
    python manage.py fix_stock --from-report report.json
    python manage.py fix_stock --product-id PROD-00001 --fix-all
"""

from django.core.management.base import BaseCommand
from app.services.product_service import ProductService
from app.services.batch_service import BatchService
from datetime import datetime
import json
import sys


class Command(BaseCommand):
    help = 'Fix stock mismatches in database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=True,
            help='Dry run mode (default) - show changes without applying them'
        )
        parser.add_argument(
            '--live',
            action='store_true',
            help='Live mode - actually apply fixes to database'
        )
        parser.add_argument(
            '--product-id',
            type=str,
            help='Fix specific product ID only'
        )
        parser.add_argument(
            '--from-report',
            type=str,
            help='Load and fix from comparison report JSON file'
        )
        parser.add_argument(
            '--fix-batches',
            action='store_true',
            help='Sync stock with batch calculations'
        )
        parser.add_argument(
            '--fix-fields',
            action='store_true',
            help='Sync stock and total_stock fields'
        )
        parser.add_argument(
            '--fix-missing',
            action='store_true',
            help='Fix products missing from API'
        )
        parser.add_argument(
            '--fix-all',
            action='store_true',
            help='Run all fixes'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product_service = ProductService()
        self.batch_service = BatchService()
        self.dry_run = True

    def calculate_batch_stock(self, product_id):
        """Calculate actual stock from active batches"""
        try:
            now = datetime.utcnow()
            db = self.batch_service.db
            batches_collection = db.batches
            
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
                    if isinstance(expiry_date, str):
                        try:
                            from dateutil import parser
                            expiry_date = parser.parse(expiry_date)
                        except Exception:
                            non_expired_batches.append(batch)
                            continue
                    
                    if isinstance(expiry_date, datetime) and expiry_date >= now:
                        non_expired_batches.append(batch)
            
            total_stock = sum(batch['quantity_remaining'] for batch in non_expired_batches)
            return total_stock
        except Exception as e:
            self.stderr.write(f"Error calculating batch stock for {product_id}: {e}")
            return 0

    def sync_stock_with_batches(self, product_id=None):
        """Fix products where stock doesn't match batch calculation"""
        self.stdout.write("\n🔧 Syncing product stock with batch system...\n")
        
        db = self.product_service.db
        query = {'isDeleted': {'$ne': True}}
        if product_id:
            query['_id'] = product_id
        
        products = list(db.products.find(query))
        
        fixed_count = 0
        errors = []
        
        for product in products:
            try:
                product_id = product['_id']
                current_stock = int(product.get('stock', 0))
                batch_stock = self.calculate_batch_stock(product_id)
                
                if current_stock != batch_stock:
                    self.stdout.write(
                        f"📦 {product.get('product_name', 'Unknown')} ({product.get('SKU', 'N/A')})"
                    )
                    self.stdout.write(f"   Current: {current_stock} | Batch Calculated: {batch_stock}")
                    
                    if self.dry_run:
                        self.stdout.write(
                            self.style.WARNING(f"   [DRY RUN] Would update to: {batch_stock}")
                        )
                    else:
                        # Update both stock and total_stock
                        result = db.products.update_one(
                            {'_id': product_id},
                            {
                                '$set': {
                                    'stock': batch_stock,
                                    'total_stock': batch_stock,
                                    'updated_at': datetime.utcnow()
                                }
                            }
                        )
                        
                        if result.modified_count > 0:
                            self.stdout.write(self.style.SUCCESS(f"   ✅ Updated to: {batch_stock}"))
                            fixed_count += 1
                        else:
                            self.stdout.write(self.style.WARNING(f"   ⚠️  Update failed"))
                    
                    self.stdout.write("")
            except Exception as e:
                errors.append({'product_id': product_id, 'error': str(e)})
                self.stderr.write(f"   ❌ Error: {e}\n")
        
        self.stdout.write("=" * 80)
        if self.dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would fix {fixed_count} products"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed_count} products"))
        
        if errors:
            self.stderr.write(self.style.ERROR(f"❌ Errors: {len(errors)}"))
        
        return fixed_count

    def sync_stock_and_total_stock(self, product_id=None):
        """Fix products where stock and total_stock don't match"""
        self.stdout.write("\n🔧 Syncing stock and total_stock fields...\n")
        
        db = self.product_service.db
        query = {'isDeleted': {'$ne': True}}
        if product_id:
            query['_id'] = product_id
        
        products = list(db.products.find(query))
        
        fixed_count = 0
        
        for product in products:
            try:
                product_id = product['_id']
                stock = int(product.get('stock', 0))
                total_stock = int(product.get('total_stock', stock))
                
                if stock != total_stock:
                    self.stdout.write(
                        f"📦 {product.get('product_name', 'Unknown')} ({product.get('SKU', 'N/A')})"
                    )
                    self.stdout.write(f"   stock: {stock} | total_stock: {total_stock}")
                    
                    if self.dry_run:
                        self.stdout.write(
                            self.style.WARNING(f"   [DRY RUN] Would set both to: {stock}")
                        )
                    else:
                        result = db.products.update_one(
                            {'_id': product_id},
                            {
                                '$set': {
                                    'total_stock': stock,
                                    'updated_at': datetime.utcnow()
                                }
                            }
                        )
                        
                        if result.modified_count > 0:
                            self.stdout.write(self.style.SUCCESS(f"   ✅ Set both to: {stock}"))
                            fixed_count += 1
                        else:
                            self.stdout.write(self.style.WARNING(f"   ⚠️  Update failed"))
                    
                    self.stdout.write("")
            except Exception as e:
                self.stderr.write(f"   ❌ Error: {e}\n")
        
        self.stdout.write("=" * 80)
        if self.dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would fix {fixed_count} products"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed_count} products"))
        
        return fixed_count

    def fix_missing_from_api(self, product_id=None):
        """Fix products that should appear in API but don't"""
        self.stdout.write("\n🔧 Fixing products missing from customer API...\n")
        
        db = self.product_service.db
        query = {
            'isDeleted': {'$ne': True},
            'stock': {'$gt': 0}
        }
        
        if product_id:
            query['_id'] = product_id
        
        products = list(db.products.find(query))
        
        fixed_count = 0
        
        for product in products:
            try:
                product_id = product['_id']
                status = product.get('status', 'unknown')
                
                # Check if status is not 'active' but has stock
                if status != 'active':
                    self.stdout.write(
                        f"📦 {product.get('product_name', 'Unknown')} ({product.get('SKU', 'N/A')})"
                    )
                    self.stdout.write(f"   Status: {status} | Stock: {product.get('stock', 0)}")
                    
                    if self.dry_run:
                        self.stdout.write(
                            self.style.WARNING(f"   [DRY RUN] Would set status to: active")
                        )
                    else:
                        result = db.products.update_one(
                            {'_id': product_id},
                            {
                                '$set': {
                                    'status': 'active',
                                    'updated_at': datetime.utcnow()
                                }
                            }
                        )
                        
                        if result.modified_count > 0:
                            self.stdout.write(self.style.SUCCESS(f"   ✅ Set status to: active"))
                            fixed_count += 1
                        else:
                            self.stdout.write(self.style.WARNING(f"   ⚠️  Update failed"))
                    
                    self.stdout.write("")
            except Exception as e:
                self.stderr.write(f"   ❌ Error: {e}\n")
        
        self.stdout.write("=" * 80)
        if self.dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would fix {fixed_count} products"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed_count} products"))
        
        return fixed_count

    def load_comparison_report(self, report_file):
        """Load mismatches from comparison report and fix them"""
        self.stdout.write(f"\n📂 Loading comparison report: {report_file}\n")
        
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
            
            mismatches = data.get('mismatches', [])
            missing_from_api = data.get('missing_from_api', [])
            
            self.stdout.write(
                f"Found {len(mismatches)} mismatches and {len(missing_from_api)} missing products\n"
            )
            
            # Fix each mismatch based on type
            for mismatch in mismatches:
                product_id = mismatch['product_id']
                mismatch_type = mismatch['mismatch_type']
                
                if 'cloud_vs_batch' in mismatch_type:
                    self.stdout.write(f"Fixing batch mismatch for {product_id}...")
                    self.sync_stock_with_batches(product_id)
                
                if 'stock_vs_total_stock' in mismatch_type:
                    self.stdout.write(f"Fixing stock/total_stock mismatch for {product_id}...")
                    self.sync_stock_and_total_stock(product_id)
            
            # Fix missing products
            for missing in missing_from_api:
                product_id = missing['product_id']
                self.stdout.write(f"Fixing missing product {product_id}...")
                self.fix_missing_from_api(product_id)
            
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"❌ Report file not found: {report_file}"))
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f"❌ Invalid JSON in report file"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error loading report: {e}"))

    def handle(self, *args, **options):
        """Main command handler"""
        # Determine dry-run mode
        self.dry_run = not options['live']
        
        if self.dry_run:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("⚠️  DRY RUN MODE - No changes will be made"))
            self.stdout.write("   Use --live flag to execute actual fixes")
            self.stdout.write("=" * 80 + "\n")
        else:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR("🚨 LIVE MODE - This will modify the database!"))
            self.stdout.write("=" * 80)
            
            # Confirmation in live mode
            response = input("\nAre you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                self.stdout.write("Aborted.")
                sys.exit(0)
            self.stdout.write("")
        
        try:
            if options['from_report']:
                # Fix from report file
                self.load_comparison_report(options['from_report'])
            elif options['fix_all']:
                # Run all fixes
                self.sync_stock_with_batches(options['product_id'])
                self.sync_stock_and_total_stock(options['product_id'])
                self.fix_missing_from_api(options['product_id'])
            else:
                # Run specific fixes
                ran_any_fix = False
                
                if options['fix_batches']:
                    self.sync_stock_with_batches(options['product_id'])
                    ran_any_fix = True
                
                if options['fix_fields']:
                    self.sync_stock_and_total_stock(options['product_id'])
                    ran_any_fix = True
                
                if options['fix_missing']:
                    self.fix_missing_from_api(options['product_id'])
                    ran_any_fix = True
                
                if not ran_any_fix:
                    self.stdout.write("No fix option specified. Use --help to see available options.")
                    self.stdout.write("\nQuick examples:")
                    self.stdout.write("  Dry run batch fix:     python manage.py fix_stock --fix-batches")
                    self.stdout.write("  Live batch fix:        python manage.py fix_stock --fix-batches --live")
                    self.stdout.write("  Fix all:               python manage.py fix_stock --fix-all --live")
                    self.stdout.write("  Fix from report:       python manage.py fix_stock --from-report report.json --live")
        
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error: {str(e)}"))
            sys.exit(1)



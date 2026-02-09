"""
Django Management Command: Sync All Stock
==========================================
Sync ALL product stock fields with batch calculations.
This fixes the issue where products have null/0 stock but batches show inventory.

Usage:
    python manage.py sync_all_stock --dry-run  (safe, shows what would change)
    python manage.py sync_all_stock --live     (applies changes)
"""

from django.core.management.base import BaseCommand
from app.services.product_service import ProductService
from app.services.batch_service import BatchService
from datetime import datetime

class Command(BaseCommand):
    help = 'Sync all product stock fields with batch calculations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=True,
            help='Dry run mode (default) - show changes without applying'
        )
        parser.add_argument(
            '--live',
            action='store_true',
            help='Live mode - actually apply changes to database'
        )

    def calculate_batch_stock(self, product_id, batch_collection):
        """Calculate actual stock from active batches"""
        try:
            now = datetime.utcnow()
            
            batches = list(batch_collection.find({
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
            return total_stock, len(non_expired_batches)
        except Exception as e:
            self.stderr.write(f"Error calculating batch stock for {product_id}: {e}")
            return 0, 0

    def handle(self, *args, **options):
        """Main command handler"""
        dry_run = not options['live']
        
        if dry_run:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("⚠️  DRY RUN MODE - No changes will be made"))
            self.stdout.write("   Use --live flag to apply changes")
            self.stdout.write("=" * 80 + "\n")
        else:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR("🚨 LIVE MODE - This will update the database!"))
            self.stdout.write("=" * 80)
            response = input("\nThis will update stock for ALL products. Continue? (yes/no): ")
            if response.lower() != 'yes':
                self.stdout.write("Aborted.")
                return
            self.stdout.write("")
        
        try:
            product_service = ProductService()
            batch_service = BatchService()
            db = product_service.db
            batch_collection = db.batches
            
            self.stdout.write("🔧 Syncing ALL product stock with batch system...\n")
            
            # Get all active, non-deleted products
            query = {
                'status': 'active',
                'isDeleted': {'$ne': True}
            }
            
            products = list(db.products.find(query))
            self.stdout.write(f"📦 Found {len(products)} active products to check\n")
            
            updated_count = 0
            null_fixed = 0
            zero_fixed = 0
            errors = []
            
            for i, product in enumerate(products, 1):
                try:
                    product_id = product['_id']
                    product_name = product.get('product_name', 'Unknown')
                    current_stock = product.get('stock')
                    
                    # Calculate correct stock from batches
                    batch_stock, batch_count = self.calculate_batch_stock(product_id, batch_collection)
                    
                    # Determine if update is needed
                    needs_update = False
                    reason = ""
                    
                    if current_stock is None:
                        needs_update = True
                        reason = f"NULL → {batch_stock}"
                        null_fixed += 1
                    elif current_stock == 0 and batch_stock > 0:
                        needs_update = True
                        reason = f"0 → {batch_stock}"
                        zero_fixed += 1
                    elif current_stock != batch_stock:
                        needs_update = True
                        reason = f"{current_stock} → {batch_stock}"
                    
                    if needs_update:
                        # Show progress every 50 products
                        if i % 50 == 0:
                            self.stdout.write(f"Processing... {i}/{len(products)}")
                        
                        self.stdout.write(
                            f"  [{i}/{len(products)}] {product_name[:30]:<30} | "
                            f"Stock: {reason:>15} | "
                            f"Batches: {batch_count}"
                        )
                        
                        if not dry_run:
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
                                updated_count += 1
                        else:
                            updated_count += 1
                
                except Exception as e:
                    errors.append({'product_id': product.get('_id'), 'error': str(e)})
                    self.stderr.write(f"   ❌ Error: {e}")
            
            # Summary
            self.stdout.write("\n" + "=" * 80)
            if dry_run:
                self.stdout.write(self.style.WARNING(f"[DRY RUN] Would update {updated_count} products:"))
                self.stdout.write(f"  - Fix NULL stock: {null_fixed} products")
                self.stdout.write(f"  - Fix zero stock: {zero_fixed} products")
                self.stdout.write(f"  - Fix mismatched: {updated_count - null_fixed - zero_fixed} products")
            else:
                self.stdout.write(self.style.SUCCESS(f"✅ Updated {updated_count} products:"))
                self.stdout.write(f"  - Fixed NULL stock: {null_fixed} products")
                self.stdout.write(f"  - Fixed zero stock: {zero_fixed} products")
                self.stdout.write(f"  - Fixed mismatched: {updated_count - null_fixed - zero_fixed} products")
            
            if errors:
                self.stderr.write(self.style.ERROR(f"\n❌ Errors: {len(errors)}"))
                for error in errors[:5]:
                    self.stderr.write(f"   - {error['product_id']}: {error['error']}")
            
            self.stdout.write("=" * 80)
            
            if dry_run and updated_count > 0:
                self.stdout.write(self.style.WARNING("\n💡 To apply these changes, run:"))
                self.stdout.write("   python manage.py sync_all_stock --live")
            elif not dry_run:
                self.stdout.write(self.style.SUCCESS("\n✅ Stock sync complete!"))
                self.stdout.write("   Run this to verify:")
                self.stdout.write("   python manage.py compare_stock")
        
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error: {str(e)}"))
            import traceback
            traceback.print_exc()



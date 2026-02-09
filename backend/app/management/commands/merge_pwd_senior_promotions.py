# management/commands/merge_pwd_senior_promotions.py

from django.core.management.base import BaseCommand
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Merge PWD and Senior Citizen promotions into a single combined promotion'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing anything',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        # Import here to avoid circular imports
        from app.services.promotions_service import PromotionService
        from app.database import db_manager

        promotion_service = PromotionService()
        db = db_manager.get_database()
        promotions_collection = db.promotions

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('MERGE PWD & SENIOR CITIZEN PROMOTIONS'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be made\n'))
        else:
            self.stdout.write(self.style.ERROR('\n⚠️  LIVE MODE - Database will be modified!\n'))

        # Find PWD promotions
        pwd_promos = list(promotions_collection.find({
            '$or': [
                {'name': {'$regex': 'pwd|person with disability', '$options': 'i'}},
                {'promotion_name': {'$regex': 'pwd|person with disability', '$options': 'i'}}
            ],
            'isDeleted': {'$ne': True}
        }))

        # Find Senior Citizen promotions
        senior_citizen_promos = list(promotions_collection.find({
            '$or': [
                {'name': {'$regex': 'senior|citizen|senior citizen', '$options': 'i'}},
                {'promotion_name': {'$regex': 'senior|citizen|senior citizen', '$options': 'i'}}
            ],
            'isDeleted': {'$ne': True}
        }))

        total_promos = len(pwd_promos) + len(senior_citizen_promos)

        if total_promos == 0:
            self.stdout.write(self.style.SUCCESS('✅ No PWD or Senior Citizen promotions found. Nothing to merge.'))
            return

        # Display found promotions
        self.stdout.write('\n📋 Found Promotions:')
        self.stdout.write(f'   PWD Promotions: {len(pwd_promos)}')
        for promo in pwd_promos:
            promo_id = promo.get('promotion_id') or promo.get('_id', 'N/A')
            promo_name = promo.get('name') or promo.get('promotion_name', 'N/A')
            status = promo.get('status', 'N/A')
            usage = promo.get('current_usage', 0)
            self.stdout.write(f'      - {promo_id}: "{promo_name}" (Status: {status}, Usage: {usage})')

        self.stdout.write(f'   Senior Citizen Promotions: {len(senior_citizen_promos)}')
        for promo in senior_citizen_promos:
            promo_id = promo.get('promotion_id') or promo.get('_id', 'N/A')
            promo_name = promo.get('name') or promo.get('promotion_name', 'N/A')
            status = promo.get('status', 'N/A')
            usage = promo.get('current_usage', 0)
            self.stdout.write(f'      - {promo_id}: "{promo_name}" (Status: {status}, Usage: {usage})')

        # Show what will happen
        all_promos = pwd_promos + senior_citizen_promos
        total_usage = sum(p.get('current_usage', 0) for p in all_promos)
        total_revenue = sum(p.get('total_revenue_impact', 0.0) for p in all_promos)
        
        self.stdout.write('\n📊 Merge Summary:')
        self.stdout.write(f'   Total promotions to merge: {total_promos}')
        self.stdout.write(f'   Combined usage count: {total_usage}')
        self.stdout.write(f'   Combined revenue impact: ₱{total_revenue:.2f}')
        self.stdout.write(f'   New promotion name: "PWD & Senior Citizen"')

        # Check for existing merged promotion
        existing_merged = promotions_collection.find_one({
            'name': 'PWD & Senior Citizen',
            'isDeleted': {'$ne': True}
        })

        if existing_merged:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  WARNING: A promotion named "PWD & Senior Citizen" already exists!'
            ))
            self.stdout.write(f'   Existing ID: {existing_merged.get("promotion_id") or existing_merged.get("_id")}')
            if not force:
                proceed = input('\n   Continue anyway? This will create a duplicate. (yes/no): ')
                if proceed.lower() != 'yes':
                    self.stdout.write(self.style.ERROR('Merge cancelled.'))
                    return

        # Confirm before proceeding
        if not dry_run and not force:
            self.stdout.write(self.style.ERROR('\n⚠️  WARNING: This will:'))
            self.stdout.write('   1. Create a new combined promotion "PWD & Senior Citizen"')
            self.stdout.write('   2. Update all sales records referencing old promotions')
            self.stdout.write('   3. Soft-delete the old PWD and Senior Citizen promotions')
            confirm = input('\n   Type "MERGE" to proceed: ')
            
            if confirm != 'MERGE':
                self.stdout.write(self.style.ERROR('Merge cancelled.'))
                return

        # Perform merge
        self.stdout.write('\n🚀 Starting merge...\n')

        if dry_run:
            self.stdout.write(self.style.NOTICE('[DRY RUN] Would merge promotions:'))
            for promo in all_promos:
                promo_id = promo.get('promotion_id') or promo.get('_id', 'N/A')
                promo_name = promo.get('name') or promo.get('promotion_name', 'N/A')
                self.stdout.write(f'   - {promo_id}: "{promo_name}"')
            
            self.stdout.write(self.style.NOTICE('\n[DRY RUN] Would create new promotion: "PWD & Senior Citizen"'))
            self.stdout.write(self.style.NOTICE('[DRY RUN] Would update sales records'))
            self.stdout.write(self.style.NOTICE('[DRY RUN] Would soft-delete old promotions'))
        else:
            try:
                result = promotion_service.merge_pwd_senior_citizen_promotions(user_id=None)
                
                if result['success']:
                    self.stdout.write(self.style.SUCCESS('✅ Merge completed successfully!'))
                    self.stdout.write(f'   New promotion ID: {result["merged_promotion_id"]}')
                    self.stdout.write(f'   Merged {len(result["old_promotion_ids"])} promotions')
                    self.stdout.write(f'   Total usage: {result["statistics"]["total_usage"]}')
                    self.stdout.write(f'   Total revenue impact: ₱{result["statistics"]["total_revenue_impact"]:.2f}')
                    
                    # Check sales updates
                    sales_collection = db.sales
                    updated_sales = sales_collection.count_documents({
                        'promotion_applied.promotion_id': result['merged_promotion_id']
                    })
                    self.stdout.write(f'   Updated sales records: {updated_sales}')
                else:
                    self.stdout.write(self.style.ERROR(f'❌ Merge failed: {result.get("message", "Unknown error")}'))
                    if 'error' in result:
                        self.stdout.write(self.style.ERROR(f'   Error details: {result["error"]}'))
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error during merge: {str(e)}'))
                logger.error(f"Error merging promotions: {e}", exc_info=True)

        self.stdout.write('\n' + '=' * 70)
        if not dry_run:
            self.stdout.write(self.style.SUCCESS('\n🎉 Merge process complete!\n'))
            self.stdout.write('Next steps:')
            self.stdout.write('   1. Verify the new "PWD & Senior Citizen" promotion exists')
            self.stdout.write('   2. Check that sales records were updated correctly')
            self.stdout.write('   3. Verify old promotions are soft-deleted')
            self.stdout.write('   4. Test applying the merged promotion')
        else:
            self.stdout.write(self.style.NOTICE('\n💡 This was a dry run. Run without --dry-run to apply changes.\n'))


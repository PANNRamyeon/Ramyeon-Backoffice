from django.core.management.base import BaseCommand
from datetime import datetime
from app.services.batch_service import BatchService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migrate existing batch usage_history to enhanced format (without reason field)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration without saving changes (preview only)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        try:
            batch_service = BatchService()
            batch_collection = batch_service.batch_collection
            
            # Get all batches
            all_batches = list(batch_collection.find({}))
            total_batches = len(all_batches)
            
            self.stdout.write(f'Found {total_batches} batches to process')
            
            updated_count = 0
            already_enhanced_count = 0
            no_history_count = 0
            
            for batch in all_batches:
                batch_id = batch['_id']
                usage_history = batch.get('usage_history', [])
                
                # Skip if no usage history
                if not usage_history:
                    no_history_count += 1
                    continue
                
                # Check if already enhanced
                if usage_history and 'adjustment_type' in usage_history[0]:
                    already_enhanced_count += 1
                    continue
                
                # Enhance usage history
                enhanced_history = []
                for entry in usage_history:
                    old_reason = entry.get('reason', 'Legacy entry')
                    
                    enhanced_entry = {
                        'timestamp': entry.get('timestamp', datetime.utcnow()),
                        'quantity_used': entry.get('quantity_used', 0),
                        'remaining_after': entry.get('remaining_after', 0),
                        'adjustment_type': self.determine_type(old_reason),
                        'adjusted_by': None,
                        'approved_by': None,
                        'notes': f"Migrated: {old_reason}",
                        'source': self.determine_source(old_reason)
                    }
                    enhanced_history.append(enhanced_entry)
                
                # Update batch
                if not dry_run:
                    batch_collection.update_one(
                        {'_id': batch_id},
                        {'$set': {'usage_history': enhanced_history}}
                    )
                
                updated_count += 1
                
                if updated_count % 50 == 0:
                    self.stdout.write(f'Processed {updated_count}/{total_batches} batches...')
            
            # Summary
            self.stdout.write(self.style.SUCCESS('\n=== Migration Summary ==='))
            self.stdout.write(f'Total batches: {total_batches}')
            self.stdout.write(f'Batches with no usage history: {no_history_count}')
            self.stdout.write(f'Already enhanced batches: {already_enhanced_count}')
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'Would update: {updated_count} batches'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Successfully updated: {updated_count} batches'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Migration failed: {str(e)}'))
            logger.error(f'Migration error: {str(e)}', exc_info=True)
            raise

    def determine_type(self, old_reason):
        """Determine adjustment type from legacy reason"""
        reason_lower = old_reason.lower()
        
        if 'sale' in reason_lower or 'sold' in reason_lower or 'transaction' in reason_lower:
            return 'sale'
        elif 'damage' in reason_lower:
            return 'damage'
        elif 'theft' in reason_lower or 'stolen' in reason_lower:
            return 'theft'
        elif 'expir' in reason_lower or 'spoil' in reason_lower:
            return 'spoilage'
        elif 'return' in reason_lower:
            return 'return'
        elif 'shrink' in reason_lower:
            return 'shrinkage'
        elif 'correction' in reason_lower or 'adjust' in reason_lower:
            return 'correction'
        else:
            return 'correction'

    def determine_source(self, old_reason):
        """Determine source from legacy reason"""
        reason_lower = old_reason.lower()
        
        if 'sale' in reason_lower or 'transaction' in reason_lower:
            return 'pos_sale'
        elif 'manual' in reason_lower or 'adjust' in reason_lower:
            return 'manual_adjustment'
        elif 'expir' in reason_lower:
            return 'expiry'
        else:
            return 'system'
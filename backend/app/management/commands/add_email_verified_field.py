from django.core.management.base import BaseCommand
from app.database import db_manager
from datetime import datetime, timezone

class Command(BaseCommand):
    help = 'Add email_verified field to users that are missing it'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing anything',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved\n'))
        
        db = db_manager.get_database()
        user_collection = db.users
        
        # Find all users missing the email_verified field
        # Users without the field OR where it's None
        users_missing_field = list(user_collection.find({
            '$or': [
                {'email_verified': {'$exists': False}},
                {'email_verified': None}
            ]
        }))
        
        total = len(users_missing_field)
        
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS('All users already have the email_verified field!')
            )
            return
        
        self.stdout.write(f'Found {total} user(s) missing email_verified field\n')
        
        updated_count = 0
        
        for user in users_missing_field:
            user_id = user.get('_id')
            email = user.get('email', 'N/A')
            username = user.get('username', 'N/A')
            
            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Would add email_verified=False to: {user_id} ({username}, {email})'
                )
                updated_count += 1
            else:
                try:
                    # Add email_verified field (default to False for unverified users)
                    update_result = user_collection.update_one(
                        {'_id': user_id},
                        {
                            '$set': {
                                'email_verified': False,
                                'last_updated': datetime.now(timezone.utc)
                            }
                        }
                    )
                    
                    if update_result.modified_count > 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Added email_verified=False to: {user_id} ({username}, {email})'
                            )
                        )
                        updated_count += 1
                    elif update_result.matched_count > 0:
                        self.stdout.write(
                            self.style.WARNING(
                                f'User {user_id} already updated (race condition?)'
                            )
                        )
                        updated_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to update {user_id} ({username}): {str(e)}'
                        )
                    )
        
        # Summary
        self.stdout.write('\n' + '=' * 70)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN SUMMARY'))
        else:
            self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total users processed: {total}')
        self.stdout.write(f'Successfully updated: {updated_count}')
        self.stdout.write(f'Failed: {total - updated_count}')
        self.stdout.write('=' * 70 + '\n')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    'This was a dry run. Run without --dry-run to apply changes.'
                )
            )


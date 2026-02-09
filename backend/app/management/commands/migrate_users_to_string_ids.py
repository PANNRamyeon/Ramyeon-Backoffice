# management/commands/migrate_users_to_string_ids.py

from django.core.management.base import BaseCommand

from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate user _id from ObjectId to USER-#### string format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing anything',
        )
        parser.add_argument(
            '--no-backup',
            action='store_true',
            help='Skip creating backup file (not recommended)',
        )
        parser.add_argument(
            '--start-from',
            type=int,
            default=None,
            help='Starting number for USER IDs (default: auto-detect highest + 1)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        create_backup = not options['no_backup']
        manual_start = options['start_from']

        # Import here to avoid circular imports
        from app.database import db_manager

        db = db_manager.get_database()
        users_collection = db.users

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('USER ID MIGRATION SCRIPT'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be made\n'))
        else:
            self.stdout.write(self.style.ERROR('\n⚠️  LIVE MODE - Database will be modified!\n'))

        # Step 1: Count documents
        self.stdout.write('📊 Counting documents...')
        total_users = users_collection.count_documents({})
        
        if total_users == 0:
            self.stdout.write(self.style.SUCCESS('✅ No users found. Nothing to migrate.'))
            return

        self.stdout.write(self.style.SUCCESS(f'   Found {total_users} users to migrate\n'))

        # Step 2: Check if migration already done
        self.stdout.write('🔍 Checking for existing string IDs...')
        string_id_count = users_collection.count_documents({'_id': {'$type': 'string'}})
        
        if string_id_count > 0:
            self.stdout.write(self.style.WARNING(
                f'   ⚠️  Found {string_id_count} users with string IDs already'
            ))
            
            if string_id_count == total_users:
                self.stdout.write(self.style.SUCCESS('✅ All users already migrated. Exiting.'))
                return
            
            proceed = input('\n   Some users already have string IDs. Continue? (yes/no): ')
            if proceed.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Migration cancelled.'))
                return

        # Step 3: Fetch all users sorted by date_created
        self.stdout.write('\n📥 Fetching users...')
        users = list(users_collection.find(
            {'_id': {'$not': {'$type': 'string'}}},  # Only non-string users
            sort=[('date_created', 1)]  # Oldest first
        ))
        
        if not users:
            self.stdout.write(self.style.SUCCESS('✅ No non-string ID users found. All already migrated.'))
            return

        self.stdout.write(self.style.SUCCESS(f'   Fetched {len(users)} users with non-string ID\n'))

        # Step 4: Create backup
        if create_backup and not dry_run:
            self.stdout.write('💾 Creating backup...')
            backup_path = self._create_backup(users)
            self.stdout.write(self.style.SUCCESS(f'   ✅ Backup saved to: {backup_path}\n'))

        # Step 5: Build migration mapping with smart numbering
        self.stdout.write('🗺️  Building ID mapping...')
        
        # Find highest existing USER-#### number
        existing_user_ids = list(users_collection.find(
            {'_id': {'$regex': '^USER-', '$type': 'string'}},
            {'_id': 1}
        ))
        
        existing_numbers = []
        for doc in existing_user_ids:
            try:
                # Extract number from "USER-0013" -> 13
                num = int(doc['_id'].split('-')[1])
                existing_numbers.append(num)
            except (IndexError, ValueError):
                continue
        
        # Determine starting number
        if manual_start is not None:
            # User provided explicit start number
            start_number = manual_start
            self.stdout.write(self.style.SUCCESS(
                f'   Using manual start number: USER-{start_number:04d}'
            ))
        elif existing_numbers:
            # Auto-detect from existing IDs
            highest = max(existing_numbers)
            start_number = highest + 1
            self.stdout.write(self.style.SUCCESS(
                f'   Found existing USER IDs up to USER-{highest:04d}'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   Auto-starting new migrations from USER-{start_number:04d}'
            ))
        else:
            # No existing string IDs, start from 1
            start_number = 1
            self.stdout.write(self.style.SUCCESS(
                f'   No existing USER IDs found, starting from USER-0001'
            ))
        
        migration_map = {}
        
        for idx, user in enumerate(users, start=start_number):
            old_id = user['_id']
            new_id = f"USER-{idx:04d}"
            migration_map[str(old_id)] = new_id

        self.stdout.write(self.style.SUCCESS(f'   ✅ Created mapping for {len(migration_map)} users\n'))

        # Step 6: Show preview
        self.stdout.write(self.style.WARNING('📋 PREVIEW (First 5 conversions):'))
        preview_count = min(5, len(users))
        for idx, user in enumerate(users[:preview_count], start=start_number):
            old_id = str(user['_id'])
            new_id = f"USER-{idx:04d}"
            username = user.get('username', 'N/A')
            date = user.get('date_created', 'N/A')
            
            self.stdout.write(f"   {old_id} → {new_id}")
            self.stdout.write(f"      Username: {username}, Created: {date}")

        if len(users) > preview_count:
            self.stdout.write(f"   ... and {len(users) - preview_count} more\n")

        # Step 7: Confirm before proceeding
        if not dry_run:
            self.stdout.write(self.style.ERROR('\n⚠️  WARNING: This will permanently modify the database!'))
            confirm = input('   Type "MIGRATE" to proceed: ')
            
            if confirm != 'MIGRATE':
                self.stdout.write(self.style.ERROR('Migration cancelled.'))
                return

        # Step 8: Perform migration
        self.stdout.write('\n🚀 Starting migration...\n')
        
        success_count = 0
        error_count = 0
        errors = []

        for idx, user in enumerate(users, start=start_number):
            old_id = user['_id']
            new_id = f"USER-{idx:04d}"
            username = user.get('username', 'unknown')

            try:
                if dry_run:
                    # Just simulate
                    self.stdout.write(f"   [DRY RUN] Would migrate: {old_id} → {new_id} ({username})")
                    success_count += 1
                else:
                    # Check if target ID already exists (extra safety)
                    existing = users_collection.find_one({'_id': new_id})
                    if existing:
                        raise Exception(f"Target ID {new_id} already exists")
                    
                    # Actually migrate
                    # Create new document with string ID
                    new_user = user.copy()
                    new_user['_id'] = new_id
                    new_user['legacy_object_id'] = str(old_id)  # Keep for reference
                    new_user['migrated_at'] = datetime.utcnow()
                    
                    # Insert new document
                    users_collection.insert_one(new_user)
                    
                    # Delete old document
                    users_collection.delete_one({'_id': old_id})
                    
                    success_count += 1
                    
                    # Progress indicator
                    if success_count % 10 == 0 or success_count == len(users):
                        self.stdout.write(f"   ✅ Migrated {success_count}/{len(users)} users...")

            except Exception as e:
                error_count += 1
                error_msg = f"Failed to migrate {old_id} ({username}): {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                self.stdout.write(self.style.ERROR(f"   ❌ {error_msg}"))

        # Step 9: Report results
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.WARNING('MIGRATION SUMMARY'))
        self.stdout.write('=' * 70)
        
        if dry_run:
            self.stdout.write(self.style.NOTICE(f'🔍 DRY RUN COMPLETE'))
            self.stdout.write(f'   Would migrate: {success_count} users')
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Successfully migrated: {success_count} users'))
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {error_count}'))
            self.stdout.write('\nError details:')
            for error in errors:
                self.stdout.write(self.style.ERROR(f'   - {error}'))

        # Step 10: Verify
        if not dry_run and success_count > 0:
            self.stdout.write('\n🔍 Verifying migration...')
            
            new_count = users_collection.count_documents({'_id': {'$type': 'string'}})
            old_count = users_collection.count_documents({'_id': {'$not': {'$type': 'string'}}})
            
            self.stdout.write(f'   String IDs: {new_count}')
            self.stdout.write(f'   Non-string IDs remaining: {old_count}')
            
            if old_count == 0:
                self.stdout.write(self.style.SUCCESS('\n✅ Migration completed successfully!'))
                self.stdout.write(self.style.SUCCESS('   All users now have USER-#### format IDs'))
            else:
                self.stdout.write(self.style.WARNING(
                    f'\n⚠️  Warning: {old_count} non-string ID users still remain'
                ))

        self.stdout.write('\n' + '=' * 70)

        if not dry_run:
            self.stdout.write(self.style.SUCCESS('\n🎉 Migration process complete!\n'))
            self.stdout.write('Next steps:')
            self.stdout.write('   1. Test your API endpoints')
            self.stdout.write('   2. Verify user login still works')
            self.stdout.write('   3. Check any user-related features')
        else:
            self.stdout.write(self.style.NOTICE('\n💡 This was a dry run. Run without --dry-run to apply changes.\n'))

    def _create_backup(self, users):
        """Create JSON backup of users before migration"""
        backup_dir = Path('backups')
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'users_backup_{timestamp}.json'
        
        # Convert ObjectId to string for JSON serialization
        backup_data = []
        for user in users:
            user_copy = user.copy()
            user_copy['_id'] = str(user_copy['_id'])
            
            # Convert datetime objects
            for key, value in user_copy.items():
                if isinstance(value, datetime):
                    user_copy[key] = value.isoformat()
            
            backup_data.append(user_copy)
        
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        return backup_file
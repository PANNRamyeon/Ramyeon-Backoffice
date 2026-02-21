"""
Django management command to fix corrupted user dates
Usage: python manage.py fix_user_dates
"""
from django.core.management.base import BaseCommand
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix corrupted user datetime fields'

    def handle(self, *args, **options):
        """Fix corrupted user dates"""
        
        # Import here to avoid circular import
        from models.Users import User
        
        self.stdout.write("=" * 60)
        self.stdout.write("FIXING USER DATES")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        
        try:
            fixed_count = 0
            error_count = 0
            
            # Get all users
            users = User.get_all_users(include_deleted=True)
            
            self.stdout.write(f"Found {len(users)} users to check")
            self.stdout.write("")
            
            for user in users:
                needs_fix = False
                user_id = user.sk
                
                try:
                    # Check date_created
                    if user.date_created:
                        if user.date_created.year < 1900 or user.date_created.year > 9999:
                            self.stdout.write(f"  {user_id}: Invalid date_created year: {user.date_created.year}")
                            user.date_created = datetime.utcnow()
                            needs_fix = True
                    
                    # Check last_updated
                    if user.last_updated:
                        if user.last_updated.year < 1900 or user.last_updated.year > 9999:
                            self.stdout.write(f"  {user_id}: Invalid last_updated year: {user.last_updated.year}")
                            user.last_updated = datetime.utcnow()
                            needs_fix = True
                    
                    # Check last_login
                    if user.last_login:
                        if user.last_login.year < 1900 or user.last_login.year > 9999:
                            self.stdout.write(f"  {user_id}: Invalid last_login year: {user.last_login.year}")
                            user.last_login = None  # Set to None rather than current time
                            needs_fix = True
                    
                    # Check email_verified_at
                    if user.email_verified_at:
                        if user.email_verified_at.year < 1900 or user.email_verified_at.year > 9999:
                            self.stdout.write(f"  {user_id}: Invalid email_verified_at year: {user.email_verified_at.year}")
                            user.email_verified_at = None
                            needs_fix = True
                    
                    if needs_fix:
                        user.save()
                        fixed_count += 1
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Fixed user {user_id}"))
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f"  ✗ Error fixing user {user_id}: {str(e)}"))
            
            self.stdout.write("")
            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS(f"COMPLETE: Fixed {fixed_count} users"))
            if error_count > 0:
                self.stdout.write(self.style.WARNING(f"Errors: {error_count}"))
            self.stdout.write("=" * 60)
            
        except Exception as e:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
            logger.error(f"Error fixing user dates: {str(e)}")
            raise

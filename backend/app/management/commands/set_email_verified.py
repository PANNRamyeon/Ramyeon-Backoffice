from django.core.management.base import BaseCommand
from app.database import db_manager
from datetime import datetime, timezone

class Command(BaseCommand):
    help = 'Set email_verified status for a specific user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Email address of the user'
        )
        parser.add_argument(
            '--verified',
            type=str,
            required=True,
            choices=['True', 'False', 'true', 'false'],
            help='Set to True or False'
        )

    def handle(self, *args, **options):
        email = options['email']
        verified_str = options['verified']
        verified = verified_str.lower() == 'true'
        
        db = db_manager.get_database()
        user_collection = db.users
        
        # Find user by email
        user = user_collection.find_one({"email": email})
        
        if not user:
            self.stdout.write(
                self.style.ERROR(f'User with email {email} not found')
            )
            return
        
        # Update email_verified status
        update_dict = {
            'email_verified': verified,
            'last_updated': datetime.now(timezone.utc)
        }
        
        if verified:
            update_dict['email_verified_at'] = datetime.now(timezone.utc)
        
        update_result = user_collection.update_one(
            {'_id': user.get('_id')},
            {'$set': update_dict}
        )
        
        # If setting to False, also remove email_verified_at
        if not verified:
            user_collection.update_one(
                {'_id': user.get('_id')},
                {'$unset': {'email_verified_at': ''}}
            )
        
        if update_result.modified_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully set email_verified={verified} for {email}'
                )
            )
        elif update_result.matched_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'User found but email_verified was already {verified}'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'Failed to update user {email}')
            )


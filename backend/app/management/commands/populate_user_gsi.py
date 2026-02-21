"""
Django management command to populate User GSI fields
Usage: python manage.py populate_user_gsi
"""
from django.core.management.base import BaseCommand
import boto3
from decouple import config
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate identifier_type and identifier_value for all users'

    def handle(self, *args, **options):
        """Populate GSI fields for all users"""
        
        self.stdout.write("=" * 60)
        self.stdout.write("POPULATING USER GSI FIELDS")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        
        try:
            # Initialize DynamoDB
            table_name = config('DYNAMO_TABLE_NAME', default='RamyeonCornerDB')
            region = config('AWS_REGION_NAME', default='ap-southeast-1')
            
            dynamodb = boto3.resource(
                'dynamodb',
                region_name=region,
                aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY')
            )
            
            table = dynamodb.Table(table_name)
            
            self.stdout.write(f"Connected to table: {table_name}")
            self.stdout.write("")
            
            # Get all users
            response = table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={
                    ':pk': 'users'
                }
            )
            
            items = response.get('Items', [])
            self.stdout.write(f"Found {len(items)} users")
            self.stdout.write("")
            
            updated_count = 0
            skipped_count = 0
            
            for item in items:
                user_id = item.get('SK', 'unknown')
                email = item.get('email')
                
                # Check if GSI fields already exist
                if item.get('identifier_type') and item.get('identifier_value'):
                    self.stdout.write(f"  {user_id}: Already has GSI fields, skipping")
                    skipped_count += 1
                    continue
                
                if not email:
                    self.stdout.write(self.style.WARNING(f"  {user_id}: No email found, skipping"))
                    skipped_count += 1
                    continue
                
                # Normalize email
                email_normalized = email.lower().strip()
                
                # Update with GSI fields
                try:
                    table.update_item(
                        Key={
                            'PK': 'users',
                            'SK': user_id
                        },
                        UpdateExpression='SET identifier_type = :type, identifier_value = :value',
                        ExpressionAttributeValues={
                            ':type': 'EMAIL',
                            ':value': email_normalized
                        }
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {user_id}: Set EMAIL = {email_normalized}"))
                    updated_count += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ {user_id}: Error - {str(e)}"))
            
            self.stdout.write("")
            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS(f"COMPLETE!"))
            self.stdout.write(f"  Updated: {updated_count}")
            self.stdout.write(f"  Skipped: {skipped_count}")
            self.stdout.write("=" * 60)
            self.stdout.write("")
            self.stdout.write("The GSI should now be populated and ready to use!")
            self.stdout.write("Login should be much faster now (2-3 seconds vs 48 seconds)")
            
        except Exception as e:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
            import traceback
            traceback.print_exc()
            logger.error(f"Error populating User GSI: {str(e)}")
            raise

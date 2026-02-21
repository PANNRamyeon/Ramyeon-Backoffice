"""
Django management command to debug user dates in DynamoDB
Usage: python manage.py debug_user_dates
"""
from django.core.management.base import BaseCommand
import boto3
from decouple import config
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Debug datetime fields in DynamoDB to see raw values'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Specific user email to debug',
            default=None
        )

    def handle(self, *args, **options):
        """Debug dates in DynamoDB"""
        
        self.stdout.write("=" * 60)
        self.stdout.write("DEBUGGING DYNAMODB USER DATES")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        
        try:
            # Initialize DynamoDB client
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
            
            # Scan for all users
            response = table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={
                    ':pk': 'users'
                }
            )
            
            items = response.get('Items', [])
            self.stdout.write(f"Found {len(items)} user records")
            self.stdout.write("")
            
            email_filter = options.get('email')
            
            for item in items:
                user_id = item.get('SK', 'unknown')
                email = item.get('email', 'no-email')
                
                # Filter by email if specified
                if email_filter and email_filter.lower() not in email.lower():
                    continue
                
                self.stdout.write(f"User: {user_id} ({email})")
                self.stdout.write("-" * 50)
                
                # Show all date fields with their raw values
                date_fields = ['date_created', 'last_updated', 'last_login', 'email_verified_at']
                
                for field in date_fields:
                    if field in item:
                        value = item[field]
                        value_type = type(value).__name__
                        self.stdout.write(f"  {field}:")
                        self.stdout.write(f"    Type: {value_type}")
                        self.stdout.write(f"    Value: {value}")
                    else:
                        self.stdout.write(f"  {field}: <not set>")
                
                self.stdout.write("")
                
                # Only show first user if no email filter
                if not email_filter:
                    self.stdout.write("(Showing only first user. Use --email to see specific user)")
                    break
            
            self.stdout.write("=" * 60)
            self.stdout.write("DEBUG COMPLETE")
            self.stdout.write("=" * 60)
            
        except Exception as e:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
            import traceback
            traceback.print_exc()
            logger.error(f"Error debugging DynamoDB dates: {str(e)}")
            raise

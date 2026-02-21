"""
Django management command to initialize Token Blacklist GSI
Usage: python manage.py init_token_blacklist
"""
import os
import boto3
from django.core.management.base import BaseCommand
from decouple import config
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize Token Blacklist GSI in DynamoDB table'

    def handle(self, *args, **options):
        """Create the TokenBlacklist GSI if it doesn't exist"""
        
        # Get configuration from environment
        table_name = os.getenv("DYNAMO_TABLE_NAME", "RamyeonCornerDB")
        region = config('AWS_REGION_NAME', default='ap-southeast-1')
        gsi_name = 'TokenBlacklistExpirationIndex'
        
        self.stdout.write(f"Initializing Token Blacklist for table: {table_name}")
        self.stdout.write(f"Region: {region}")
        self.stdout.write(f"GSI Name: {gsi_name}")
        self.stdout.write("")
        
        try:
            # Initialize DynamoDB client
            dynamodb = boto3.client(
                'dynamodb',
                region_name=region,
                aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY')
            )
            
            # Check if table exists
            try:
                table_description = dynamodb.describe_table(TableName=table_name)
                self.stdout.write(self.style.SUCCESS(f'✓ Table "{table_name}" exists'))
            except dynamodb.exceptions.ResourceNotFoundException:
                self.stdout.write(
                    self.style.ERROR(f'✗ Table "{table_name}" does not exist!')
                )
                self.stdout.write("Please run: python manage.py create_dynamodb_table")
                return
            
            # Check if GSI already exists
            existing_gsis = table_description.get('Table', {}).get('GlobalSecondaryIndexes', [])
            gsi_exists = any(gsi['IndexName'] == gsi_name for gsi in existing_gsis)
            
            if gsi_exists:
                self.stdout.write(
                    self.style.WARNING(f'GSI "{gsi_name}" already exists!')
                )
                
                # Show GSI status
                for gsi in existing_gsis:
                    if gsi['IndexName'] == gsi_name:
                        self.stdout.write(f"  Status: {gsi.get('IndexStatus', 'UNKNOWN')}")
                        self.stdout.write(f"  Projection: {gsi.get('Projection', {}).get('ProjectionType', 'UNKNOWN')}")
                
                self.stdout.write("")
                self.stdout.write(self.style.SUCCESS('✓ Token Blacklist is ready to use!'))
                self.stdout.write("")
                self.stdout.write("The TokenBlacklist model will work even with 0 blacklisted tokens.")
                self.stdout.write("Tokens will be added automatically when users log out.")
                return
            
            # Create GSI
            self.stdout.write(f"Creating GSI: {gsi_name}")
            self.stdout.write("  - Hash Key: PK (String)")
            self.stdout.write("  - Range Key: expires_at (String - ISO DateTime)")
            self.stdout.write("  - Projection: ALL")
            self.stdout.write("")
            
            response = dynamodb.update_table(
                TableName=table_name,
                AttributeDefinitions=[
                    {
                        'AttributeName': 'PK',
                        'AttributeType': 'S'  # String
                    },
                    {
                        'AttributeName': 'expires_at',
                        'AttributeType': 'S'  # String (ISO datetime)
                    }
                ],
                GlobalSecondaryIndexUpdates=[
                    {
                        'Create': {
                            'IndexName': gsi_name,
                            'KeySchema': [
                                {
                                    'AttributeName': 'PK',
                                    'KeyType': 'HASH'
                                },
                                {
                                    'AttributeName': 'expires_at',
                                    'KeyType': 'RANGE'
                                }
                            ],
                            'Projection': {
                                'ProjectionType': 'ALL'
                            },
                            'ProvisionedThroughput': {
                                'ReadCapacityUnits': 1,
                                'WriteCapacityUnits': 1
                            }
                        }
                    }
                ]
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ GSI "{gsi_name}" creation initiated!')
            )
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Note: GSI is being created. It may take a few minutes to become ACTIVE."
            ))
            self.stdout.write("The table will remain available during GSI creation.")
            self.stdout.write("")
            
            # Wait for GSI to be created
            self.stdout.write("Waiting for GSI to become active...")
            self.stdout.write("(This may take 2-5 minutes for the first GSI)")
            
            import time
            max_attempts = 60  # 5 minutes with 5-second intervals
            attempt = 0
            
            while attempt < max_attempts:
                time.sleep(5)
                attempt += 1
                
                table_description = dynamodb.describe_table(TableName=table_name)
                gsis = table_description.get('Table', {}).get('GlobalSecondaryIndexes', [])
                
                for gsi in gsis:
                    if gsi['IndexName'] == gsi_name:
                        status = gsi.get('IndexStatus', 'UNKNOWN')
                        
                        if status == 'ACTIVE':
                            self.stdout.write("")
                            self.stdout.write(self.style.SUCCESS(
                                f'✓ GSI "{gsi_name}" is now ACTIVE and ready to use!'
                            ))
                            self.stdout.write("")
                            self.stdout.write("=" * 60)
                            self.stdout.write(self.style.SUCCESS("TOKEN BLACKLIST INITIALIZATION COMPLETE!"))
                            self.stdout.write("=" * 60)
                            self.stdout.write("")
                            self.stdout.write("What happens now:")
                            self.stdout.write("  1. The blacklist starts empty (0 tokens)")
                            self.stdout.write("  2. When users log out, their tokens are added")
                            self.stdout.write("  3. On every API request, tokens are checked against the blacklist")
                            self.stdout.write("  4. Expired tokens are automatically cleaned up periodically")
                            self.stdout.write("")
                            self.stdout.write("Next steps:")
                            self.stdout.write("  - The auth service can now use TokenBlacklist.blacklist_token()")
                            self.stdout.write("  - Set up a daily cron job to run: cleanup_expired_tokens_job()")
                            self.stdout.write("")
                            return
                        elif status == 'CREATING':
                            self.stdout.write(f"  Status: {status} (attempt {attempt}/{max_attempts})")
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"  Unexpected status: {status}")
                            )
            
            # Timeout
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING('GSI creation is taking longer than expected.')
            )
            self.stdout.write('You can check the status with: python manage.py check_dynamodb_table')
            self.stdout.write('The GSI should be ready in a few minutes.')
            
        except Exception as e:
            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR(f'✗ Error initializing Token Blacklist: {str(e)}')
            )
            logger.error(f"Error initializing Token Blacklist: {str(e)}")
            
            # Provide helpful error messages
            if 'ValidationException' in str(e):
                self.stdout.write("")
                self.stdout.write("Possible issues:")
                self.stdout.write("  - The GSI might already exist")
                self.stdout.write("  - The table might not exist")
                self.stdout.write("  - Check your AWS credentials")
            
            raise

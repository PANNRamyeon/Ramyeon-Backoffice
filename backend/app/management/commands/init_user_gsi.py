"""
Django management command to create User GSI in DynamoDB
Usage: python manage.py init_user_gsi
"""
import os
import boto3
from django.core.management.base import BaseCommand
from decouple import config
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create User identifier GSI in DynamoDB table'

    def handle(self, *args, **options):
        """Create the User GSI if it doesn't exist"""
        
        table_name = os.getenv("DYNAMO_TABLE_NAME", "RamyeonCornerDB")
        region = config('AWS_REGION_NAME', default='ap-southeast-1')
        gsi_name = 'gsi-user-identifiers'
        
        self.stdout.write(f"Creating User GSI for table: {table_name}")
        self.stdout.write(f"Region: {region}")
        self.stdout.write(f"GSI Name: {gsi_name}")
        self.stdout.write("")
        
        try:
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
                self.stdout.write(self.style.ERROR(f'✗ Table "{table_name}" does not exist!'))
                return
            
            # Check if GSI already exists
            existing_gsis = table_description.get('Table', {}).get('GlobalSecondaryIndexes', [])
            gsi_exists = any(gsi['IndexName'] == gsi_name for gsi in existing_gsis)
            
            if gsi_exists:
                self.stdout.write(self.style.WARNING(f'GSI "{gsi_name}" already exists!'))
                return
            
            # Create GSI
            self.stdout.write(f"Creating GSI: {gsi_name}")
            self.stdout.write("  - Hash Key: identifier_type (String)")
            self.stdout.write("  - Range Key: identifier_value (String)")
            self.stdout.write("")
            
            response = dynamodb.update_table(
                TableName=table_name,
                AttributeDefinitions=[
                    {'AttributeName': 'identifier_type', 'AttributeType': 'S'},
                    {'AttributeName': 'identifier_value', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexUpdates=[
                    {
                        'Create': {
                            'IndexName': gsi_name,
                            'KeySchema': [
                                {'AttributeName': 'identifier_type', 'KeyType': 'HASH'},
                                {'AttributeName': 'identifier_value', 'KeyType': 'RANGE'}
                            ],
                            'Projection': {'ProjectionType': 'ALL'},
                            'ProvisionedThroughput': {
                                'ReadCapacityUnits': 5,
                                'WriteCapacityUnits': 5
                            }
                        }
                    }
                ]
            )
            
            self.stdout.write(self.style.SUCCESS(f'✓ GSI "{gsi_name}" creation initiated!'))
            self.stdout.write("")
            self.stdout.write("Waiting for GSI to become active (this may take 2-5 minutes)...")
            
            import time
            max_attempts = 60
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
                            self.stdout.write(self.style.SUCCESS(f'✓ GSI "{gsi_name}" is now ACTIVE!'))
                            self.stdout.write("")
                            self.stdout.write("=" * 60)
                            self.stdout.write("USER GSI CREATION COMPLETE!")
                            self.stdout.write("=" * 60)
                            return
                        elif status == 'CREATING':
                            self.stdout.write(f"  Status: {status} (attempt {attempt}/{max_attempts})")
            
            self.stdout.write("")
            self.stdout.write(self.style.WARNING('GSI creation is taking longer than expected.'))
            self.stdout.write('Check status with: python manage.py check_dynamodb_table')
            
        except Exception as e:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f'✗ Error creating User GSI: {str(e)}'))
            logger.error(f"Error creating User GSI: {str(e)}")
            raise

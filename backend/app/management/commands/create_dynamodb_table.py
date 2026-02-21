"""
Django management command to create the DynamoDB table
Usage: python manage.py create_dynamodb_table
"""
import os
import boto3
from django.core.management.base import BaseCommand
from decouple import config
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create the DynamoDB table for the POS system'

    def handle(self, *args, **options):
        """Create the DynamoDB table with proper configuration"""
        
        # Get table name and region directly from environment to avoid circular imports
        table_name = os.getenv("DYNAMO_TABLE_NAME", "RamyeonCornerDB")
        region = config('AWS_REGION_NAME', default='ap-southeast-1')
        
        self.stdout.write(f"Creating DynamoDB table: {table_name}")
        self.stdout.write(f"Region: {region}")
        
        try:
            # Initialize DynamoDB client
            dynamodb = boto3.client(
                'dynamodb',
                region_name=region,
                aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY')
            )
            
            # Check if table already exists
            try:
                response = dynamodb.describe_table(TableName=table_name)
                self.stdout.write(
                    self.style.WARNING(f'Table "{table_name}" already exists!')
                )
                self.stdout.write(f"Table Status: {response['Table']['TableStatus']}")
                return
            except dynamodb.exceptions.ResourceNotFoundException:
                # Table doesn't exist, we can create it
                pass
            
            # Create table with the structure required by our models
            self.stdout.write("Creating table with structure:")
            self.stdout.write("  - PK (String, Hash Key)")
            self.stdout.write("  - SK (String, Range Key)")
            self.stdout.write("  - Provisioned capacity: 5 read, 5 write units")
            
            response = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'PK',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'SK',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'PK',
                        'AttributeType': 'S'  # String
                    },
                    {
                        'AttributeName': 'SK',
                        'AttributeType': 'S'  # String
                    }
                ],
                BillingMode='PROVISIONED',
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                },
                Tags=[
                    {
                        'Key': 'Application',
                        'Value': 'PANN_POS_System'
                    },
                    {
                        'Key': 'Environment',
                        'Value': 'Development'
                    }
                ]
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Table "{table_name}" created successfully!')
            )
            self.stdout.write(f"Table ARN: {response['TableDescription']['TableArn']}")
            self.stdout.write(f"Table Status: {response['TableDescription']['TableStatus']}")
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Note: Table is being created. It may take a few moments to become ACTIVE."
            ))
            self.stdout.write("You can check the status with: python manage.py check_dynamodb_table")
            
            # Wait for table to be created
            self.stdout.write("")
            self.stdout.write("Waiting for table to become active...")
            waiter = dynamodb.get_waiter('table_exists')
            waiter.wait(
                TableName=table_name,
                WaiterConfig={
                    'Delay': 5,
                    'MaxAttempts': 20
                }
            )
            
            self.stdout.write(self.style.SUCCESS('✓ Table is now ACTIVE and ready to use!'))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error creating table: {str(e)}')
            )
            logger.error(f"Error creating DynamoDB table: {str(e)}")
            raise

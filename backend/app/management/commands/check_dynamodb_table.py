"""
Django management command to check DynamoDB table status
Usage: python manage.py check_dynamodb_table
"""
import boto3
from django.core.management.base import BaseCommand
from decouple import config
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check the status of the DynamoDB table'

    def handle(self, *args, **options):
        """Check DynamoDB table status and details"""
        
        table_name = DYNAMO_TABLE_NAME
        region = config('AWS_REGION_NAME', default=AWS_REGION)
        
        self.stdout.write(f"Checking DynamoDB table: {table_name}")
        
        try:
            # Initialize DynamoDB client
            dynamodb = boto3.client(
                'dynamodb',
                region_name=region,
                aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY')
            )
            
            # Get table description
            response = dynamodb.describe_table(TableName=table_name)
            table = response['Table']
            
            # Display table information
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f'✓ Table "{table_name}" exists'))
            self.stdout.write("")
            self.stdout.write("Table Details:")
            self.stdout.write(f"  Status: {table['TableStatus']}")
            self.stdout.write(f"  ARN: {table['TableArn']}")
            self.stdout.write(f"  Created: {table['CreationDateTime']}")
            self.stdout.write(f"  Item Count: {table.get('ItemCount', 0)}")
            self.stdout.write(f"  Table Size: {table.get('TableSizeBytes', 0)} bytes")
            self.stdout.write("")
            
            # Key schema
            self.stdout.write("Key Schema:")
            for key in table['KeySchema']:
                self.stdout.write(f"  {key['AttributeName']}: {key['KeyType']}")
            self.stdout.write("")
            
            # Provisioned throughput
            if 'ProvisionedThroughput' in table:
                throughput = table['ProvisionedThroughput']
                self.stdout.write("Provisioned Throughput:")
                self.stdout.write(f"  Read Capacity: {throughput['ReadCapacityUnits']}")
                self.stdout.write(f"  Write Capacity: {throughput['WriteCapacityUnits']}")
            elif 'BillingModeSummary' in table:
                self.stdout.write(f"Billing Mode: {table['BillingModeSummary']['BillingMode']}")
            
            self.stdout.write("")
            
            # Global Secondary Indexes
            gsis = table.get('GlobalSecondaryIndexes', [])
            if gsis:
                self.stdout.write("Global Secondary Indexes:")
                for gsi in gsis:
                    gsi_name = gsi['IndexName']
                    gsi_status = gsi.get('IndexStatus', 'UNKNOWN')
                    
                    status_symbol = '✓' if gsi_status == 'ACTIVE' else '⚠'
                    status_style = self.style.SUCCESS if gsi_status == 'ACTIVE' else self.style.WARNING
                    
                    self.stdout.write(f"  {status_symbol} {gsi_name}")
                    self.stdout.write(f"      Status: {status_style(gsi_status)}")
                    self.stdout.write(f"      Projection: {gsi.get('Projection', {}).get('ProjectionType', 'UNKNOWN')}")
                    
                    # Key schema
                    key_schema = gsi.get('KeySchema', [])
                    if key_schema:
                        self.stdout.write(f"      Keys: ", ending='')
                        keys = [f"{k['AttributeName']} ({k['KeyType']})" for k in key_schema]
                        self.stdout.write(', '.join(keys))
                    
                    self.stdout.write("")
                
                # Check for TokenBlacklist GSI specifically
                token_gsi_exists = any(gsi['IndexName'] == 'TokenBlacklistExpirationIndex' for gsi in gsis)
                if not token_gsi_exists:
                    self.stdout.write(self.style.WARNING(
                        '⚠ TokenBlacklistExpirationIndex not found!'
                    ))
                    self.stdout.write("  Run: python manage.py init_token_blacklist")
                    self.stdout.write("")
            else:
                self.stdout.write(self.style.WARNING('No Global Secondary Indexes found'))
                self.stdout.write("  For token blacklist support, run:")
                self.stdout.write("  python manage.py init_token_blacklist")
                self.stdout.write("")
            
            if table['TableStatus'] == 'ACTIVE':
                self.stdout.write(self.style.SUCCESS('✓ Table is ACTIVE and ready to use!'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ Table status: {table["TableStatus"]}'))
                
        except dynamodb.exceptions.ResourceNotFoundException:
            self.stdout.write(
                self.style.ERROR(f'✗ Table "{table_name}" does not exist!')
            )
            self.stdout.write("")
            self.stdout.write("To create the table, run:")
            self.stdout.write(self.style.WARNING("  python manage.py create_dynamodb_table"))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error checking table: {str(e)}')
            )
            logger.error(f"Error checking DynamoDB table: {str(e)}")
            raise

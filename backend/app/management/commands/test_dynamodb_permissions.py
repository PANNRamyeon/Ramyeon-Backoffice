"""
Django management command to test DynamoDB permissions
Usage: python manage.py test_dynamodb_permissions
"""
import os
import boto3
from django.core.management.base import BaseCommand
from decouple import config
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test DynamoDB table permissions'

    def handle(self, *args, **options):
        """Test various DynamoDB operations to verify permissions"""
        
        table_name = os.getenv("DYNAMO_TABLE_NAME", "RamyeonCornerDB")
        region = config('AWS_REGION_NAME', default='ap-southeast-1')
        
        self.stdout.write(f"Testing DynamoDB permissions for table: {table_name}")
        self.stdout.write(f"Region: {region}")
        self.stdout.write("")
        
        try:
            # Initialize DynamoDB client and resource
            dynamodb_client = boto3.client(
                'dynamodb',
                region_name=region,
                aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY')
            )
            
            dynamodb_resource = boto3.resource(
                'dynamodb',
                region_name=region,
                aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY')
            )
            
            # Test 1: List Tables
            self.stdout.write("Test 1: List Tables")
            try:
                response = dynamodb_client.list_tables()
                tables = response.get('TableNames', [])
                self.stdout.write(self.style.SUCCESS(f"[OK] Can list tables. Found {len(tables)} table(s)"))
                if table_name in tables:
                    self.stdout.write(self.style.SUCCESS(f"[OK] Table '{table_name}' found in the list"))
                else:
                    self.stdout.write(self.style.WARNING(f"[WARN] Table '{table_name}' NOT found in the list"))
                    self.stdout.write(f"  Available tables: {', '.join(tables)}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FAIL] Cannot list tables: {str(e)}"))
            
            self.stdout.write("")
            
            # Test 2: Describe Table
            self.stdout.write("Test 2: Describe Table")
            try:
                response = dynamodb_client.describe_table(TableName=table_name)
                table_status = response['Table']['TableStatus']
                self.stdout.write(self.style.SUCCESS(f"[OK] Can describe table. Status: {table_status}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FAIL] Cannot describe table: {str(e)}"))
            
            self.stdout.write("")
            
            # Test 3: Put Item (Write)
            self.stdout.write("Test 3: Put Item (Write)")
            try:
                table = dynamodb_resource.Table(table_name)
                test_item = {
                    'PK': 'test',
                    'SK': 'TEST-PERMISSION-001',
                    'test_field': 'Permission test item',
                    'timestamp': str(boto3.dynamodb.types.datetime.datetime.now())
                }
                table.put_item(Item=test_item)
                self.stdout.write(self.style.SUCCESS("[OK] Can write items to table"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FAIL] Cannot write items: {str(e)}"))
                self.stdout.write(self.style.WARNING("  Your IAM user may not have 'dynamodb:PutItem' permission"))
            
            self.stdout.write("")
            
            # Test 4: Get Item (Read)
            self.stdout.write("Test 4: Get Item (Read)")
            try:
                table = dynamodb_resource.Table(table_name)
                response = table.get_item(
                    Key={
                        'PK': 'test',
                        'SK': 'TEST-PERMISSION-001'
                    }
                )
                if 'Item' in response:
                    self.stdout.write(self.style.SUCCESS("[OK] Can read items from table"))
                else:
                    self.stdout.write(self.style.WARNING("[WARN] No item found (but read permission works)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FAIL] Cannot read items: {str(e)}"))
                self.stdout.write(self.style.WARNING("  Your IAM user may not have 'dynamodb:GetItem' permission"))
            
            self.stdout.write("")
            
            # Test 5: Query
            self.stdout.write("Test 5: Query Items")
            try:
                table = dynamodb_resource.Table(table_name)
                response = table.query(
                    KeyConditionExpression='PK = :pk',
                    ExpressionAttributeValues={
                        ':pk': 'test'
                    },
                    Limit=1
                )
                self.stdout.write(self.style.SUCCESS(f"[OK] Can query items. Found {response.get('Count', 0)} item(s)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FAIL] Cannot query items: {str(e)}"))
                self.stdout.write(self.style.WARNING("  Your IAM user may not have 'dynamodb:Query' permission"))
            
            self.stdout.write("")
            
            # Test 6: Scan
            self.stdout.write("Test 6: Scan Table")
            try:
                table = dynamodb_resource.Table(table_name)
                response = table.scan(Limit=1)
                self.stdout.write(self.style.SUCCESS(f"[OK] Can scan table. Found {response.get('Count', 0)} item(s)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FAIL] Cannot scan table: {str(e)}"))
                self.stdout.write(self.style.WARNING("  Your IAM user may not have 'dynamodb:Scan' permission"))
            
            self.stdout.write("")
            
            # Test 7: Delete test item (cleanup)
            self.stdout.write("Test 7: Delete Item (Cleanup)")
            try:
                table = dynamodb_resource.Table(table_name)
                table.delete_item(
                    Key={
                        'PK': 'test',
                        'SK': 'TEST-PERMISSION-001'
                    }
                )
                self.stdout.write(self.style.SUCCESS("[OK] Can delete items from table"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FAIL] Cannot delete items: {str(e)}"))
                self.stdout.write(self.style.WARNING("  Your IAM user may not have 'dynamodb:DeleteItem' permission"))
            
            self.stdout.write("")
            self.stdout.write("="*70)
            self.stdout.write("")
            self.stdout.write("RECOMMENDATION:")
            self.stdout.write("")
            self.stdout.write("If any tests failed, your IAM user needs these permissions:")
            self.stdout.write("  - dynamodb:DescribeTable")
            self.stdout.write("  - dynamodb:GetItem")
            self.stdout.write("  - dynamodb:PutItem")
            self.stdout.write("  - dynamodb:Query")
            self.stdout.write("  - dynamodb:Scan")
            self.stdout.write("  - dynamodb:UpdateItem")
            self.stdout.write("  - dynamodb:DeleteItem")
            self.stdout.write("")
            self.stdout.write("You can attach the 'AmazonDynamoDBFullAccess' policy to your IAM user")
            self.stdout.write("or create a custom policy with the permissions listed above.")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[FAIL] Error during testing: {str(e)}'))
            logger.error(f"Error testing DynamoDB permissions: {str(e)}")
            raise

"""
Django management command to fix corrupted dates directly in DynamoDB
Usage: python manage.py fix_dynamodb_dates
"""
from django.core.management.base import BaseCommand
from datetime import datetime
import boto3
from decouple import config
import re
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix corrupted datetime fields directly in DynamoDB'

    def handle(self, *args, **options):
        """Fix corrupted dates in DynamoDB"""
        
        self.stdout.write("=" * 60)
        self.stdout.write("FIXING DYNAMODB DATES (Direct)")
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
            
            fixed_count = 0
            
            for item in items:
                user_id = item.get('SK', 'unknown')
                email = item.get('email', 'no-email')
                needs_fix = False
                updates = {}
                
                self.stdout.write(f"Checking user: {user_id} ({email})")
                
                # Check each date field for corruption
                date_fields = ['date_created', 'last_updated', 'last_login', 'email_verified_at']
                
                for field in date_fields:
                    if field in item and item[field]:
                        value = item[field]
                        value_type = type(value).__name__
                        
                        # Show what we're checking
                        self.stdout.write(f"  {field}: {value_type} = {str(value)[:50]}")
                        
                        # Check if date string has corrupted year (leading zeros or invalid)
                        if isinstance(value, str):
                            # Pattern: year with more than 4 digits or leading zeros
                            # Check for: 000002025-... or any year that doesn't start with 1 or 2
                            if re.match(r'^0+\d{4,}', value) or re.match(r'^[3-9]\d{3,}', value):
                                self.stdout.write(self.style.WARNING(f"    ⚠️  FOUND CORRUPTION: {value[:40]}"))
                                
                                # Extract the actual year (remove leading zeros)
                                try:
                                    # Try to parse and fix
                                    # Pattern: 000002025-09-30T11:28:01.603000
                                    # Extract: 2025-09-30T11:28:01.603000
                                    match = re.search(r'0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)', value)
                                    if match:
                                        fixed_value = match.group(1)
                                        updates[field] = fixed_value
                                        self.stdout.write(f"    → Fixed to: {fixed_value}")
                                        needs_fix = True
                                    else:
                                        # Can't parse, set to current time or None
                                        if field in ['date_created', 'last_updated']:
                                            updates[field] = datetime.utcnow().isoformat()
                                        else:
                                            updates[field] = None
                                        self.stdout.write(f"    → Reset to: {updates[field]}")
                                        needs_fix = True
                                except Exception as e:
                                    self.stdout.write(f"    → Error parsing: {e}")
                            # Also check for dates that don't match standard format
                            elif not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', value):
                                self.stdout.write(f"  {user_id}: Invalid format {field}: {value[:40]}")
                                if field in ['date_created', 'last_updated']:
                                    updates[field] = datetime.utcnow().isoformat()
                                else:
                                    updates[field] = None
                                self.stdout.write(f"    → Reset to: {updates[field]}")
                                needs_fix = True
                    else:
                        self.stdout.write(f"  {field}: <not set or None>")
                
                # Summary for this user
                if needs_fix:
                    self.stdout.write(self.style.WARNING(f"  → User {user_id} NEEDS FIX: {len(updates)} field(s)"))
                else:
                    self.stdout.write(f"  → User {user_id} OK")
                self.stdout.write("")
                
                if needs_fix and updates:
                    try:
                        # Build update expression
                        update_expr_parts = []
                        expr_attr_values = {}
                        
                        for field, value in updates.items():
                            update_expr_parts.append(f"{field} = :{field}")
                            expr_attr_values[f':{field}'] = value
                        
                        update_expr = "SET " + ", ".join(update_expr_parts)
                        
                        # Update the item
                        table.update_item(
                            Key={
                                'PK': 'users',
                                'SK': user_id
                            },
                            UpdateExpression=update_expr,
                            ExpressionAttributeValues=expr_attr_values
                        )
                        
                        fixed_count += 1
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Fixed user {user_id}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  ✗ Error updating {user_id}: {e}"))
                
                self.stdout.write("")
            
            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS(f"COMPLETE: Fixed {fixed_count} users"))
            self.stdout.write("=" * 60)
            
        except Exception as e:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
            import traceback
            traceback.print_exc()
            logger.error(f"Error fixing DynamoDB dates: {str(e)}")
            raise

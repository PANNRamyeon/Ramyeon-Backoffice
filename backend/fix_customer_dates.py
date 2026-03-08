import os
import boto3
from datetime import datetime
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

TABLE_NAME = os.getenv('DYNAMO_TABLE_NAME', 'RamyeonCornerDB')
AWS_REGION = os.getenv('AWS_REGION_NAME') or os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
DYNAMODB_LOCAL = os.getenv('DYNAMODB_LOCAL', 'false').lower() == 'true'
DYNAMODB_LOCAL_HOST = os.getenv('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')

# Create DynamoDB client
client_kwargs = {'region_name': AWS_REGION}
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    client_kwargs.update({
        'aws_access_key_id': AWS_ACCESS_KEY,
        'aws_secret_access_key': AWS_SECRET_KEY
    })
if DYNAMODB_LOCAL:
    client_kwargs['endpoint_url'] = DYNAMODB_LOCAL_HOST

dynamodb = boto3.resource('dynamodb', **client_kwargs)
table = dynamodb.Table(TABLE_NAME)

def is_malformed(value):
    """Return True if value is a string containing '000002025' (indicating leading zeros in year)."""
    return isinstance(value, str) and '000002025' in value

def fix_malformed(value):
    """Convert a malformed string to a proper ISO datetime string."""
    # Example: "000002025-10-12T18:16:31.108000" -> "2025-10-12T18:16:31.108000"
    # Extract the year part (up to first '-')
    parts = value.split('-', 1)
    if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) > 4:
        # Take last 4 digits of the year part
        correct_year = parts[0][-4:]
        corrected = correct_year + '-' + parts[1]
        try:
            # Validate by parsing
            datetime.fromisoformat(corrected.replace('Z', '+00:00'))
            return corrected
        except ValueError:
            return datetime.utcnow().isoformat()
    return datetime.utcnow().isoformat()

def scan_and_fix(dry_run=True):
    logger.info("Starting comprehensive scan for malformed datetime fields...")
    last_key = None
    fixed_count = 0
    total_scanned = 0

    while True:
        scan_kwargs = {
            'FilterExpression': 'PK = :pk',
            'ExpressionAttributeValues': {':pk': 'customers'},
            'Limit': 100
        }
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = last_key

        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        total_scanned += len(items)

        for item in items:
            sk = item.get('SK')
            updated = False
            new_item = item.copy()

            # Recursively walk through the item and fix any string containing '000002025'
            def fix_value(obj, path=''):
                nonlocal updated
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        new_v = fix_value(v, f"{path}.{k}" if path else k)
                        if new_v is not v:
                            obj[k] = new_v
                            updated = True
                    return obj
                elif isinstance(obj, list):
                    new_list = []
                    for i, v in enumerate(obj):
                        new_v = fix_value(v, f"{path}[{i}]")
                        new_list.append(new_v)
                    return new_list
                elif is_malformed(obj):
                    new_val = fix_malformed(obj)
                    logger.warning(f"Fixing {path} for {sk}: {obj} -> {new_val}")
                    updated = True
                    return new_val
                else:
                    return obj

            fixed_item = fix_value(new_item)
            if updated:
                if not dry_run:
                    try:
                        table.put_item(Item=fixed_item)
                        fixed_count += 1
                        logger.info(f"✅ Updated {sk}")
                    except Exception as e:
                        logger.error(f"Failed to update {sk}: {e}")
                else:
                    logger.info(f"[DRY RUN] Would update {sk}")
                    fixed_count += 1

        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break

    logger.info(f"Scan complete. Scanned {total_scanned} customer items.")
    if dry_run:
        logger.info(f"Dry run: {fixed_count} items would be fixed.")
    else:
        logger.info(f"Fixed {fixed_count} customers.")

if __name__ == '__main__':
    logger.info("=== DRY RUN ===")
    scan_and_fix(dry_run=True)

    answer = input("Do you want to apply these fixes? (yes/no): ")
    if answer.lower() == 'yes':
        logger.info("=== APPLYING FIXES ===")
        scan_and_fix(dry_run=False)
    else:
        logger.info("Aborted.")
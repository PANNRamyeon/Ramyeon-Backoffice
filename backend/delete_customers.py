import os
import boto3
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

TABLE_NAME = os.getenv('DYNAMO_TABLE_NAME', 'RamyeonCornerDB')
AWS_REGION = os.getenv('AWS_REGION_NAME') or os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

client_kwargs = {'region_name': AWS_REGION}
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    client_kwargs.update({
        'aws_access_key_id': AWS_ACCESS_KEY,
        'aws_secret_access_key': AWS_SECRET_KEY
    })
dynamodb = boto3.resource('dynamodb', **client_kwargs)
table = dynamodb.Table(TABLE_NAME)

def delete_all_customers(dry_run=True):
    last_key = None
    deleted = 0
    total = 0
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
        total += len(items)
        for item in items:
            sk = item['SK']
            if not dry_run:
                table.delete_item(Key={'PK': 'customers', 'SK': sk})
                logger.info(f"Deleted {sk}")
                deleted += 1
            else:
                logger.info(f"[DRY RUN] Would delete {sk}")
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
    logger.info(f"Found {total} customers.")
    if dry_run:
        logger.info("Dry run complete. Run with dry_run=False to delete.")
    else:
        logger.info(f"Deleted {deleted} customers.")

if __name__ == '__main__':
    # First dry run to see what will be deleted
    delete_all_customers(dry_run=True)
    answer = input("Do you want to permanently delete ALL customers? (yes/no): ")
    if answer.lower() == 'yes':
        delete_all_customers(dry_run=False)
        print("All customers deleted. You can now register a new one.")
    else:
        print("Aborted.")
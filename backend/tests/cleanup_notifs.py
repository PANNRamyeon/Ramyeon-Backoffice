"""
cleanup_notifications.py

Deletes ALL notification items (old PK='notifications' and new PK='notifications#YYYY-MM-DD')
from the DynamoDB table. Works with both DynamoDB Local and AWS DynamoDB.

Usage:
    python cleanup_notifications.py          # with confirmation prompt
    python cleanup_notifications.py --yes    # skip confirmation
"""

import os
import sys
import boto3
from dotenv import load_dotenv

load_dotenv()

TABLE_NAME = os.getenv('DYNAMO_TABLE_NAME', 'RamyeonCornerDB')
AWS_REGION = os.getenv('AWS_REGION_NAME') or os.getenv('AWS_REGION', 'ap-southeast-1')
DYNAMODB_LOCAL = os.getenv('DYNAMODB_LOCAL', 'False').lower() == 'true'
DYNAMODB_LOCAL_HOST = os.getenv('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Configure boto3 client for local or real DynamoDB
client_kwargs = {'region_name': AWS_REGION}
if DYNAMODB_LOCAL:
    client_kwargs['endpoint_url'] = DYNAMODB_LOCAL_HOST
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    client_kwargs.update({
        'aws_access_key_id': AWS_ACCESS_KEY,
        'aws_secret_access_key': AWS_SECRET_KEY
    })

dynamodb = boto3.resource('dynamodb', **client_kwargs)
table = dynamodb.Table(TABLE_NAME)


def delete_all_notifications():
    """
    Scan for all items whose PK begins with 'notifications' (matches both
    'notifications' and 'notifications#...') and delete them.
    """
    last_key = None
    deleted = 0
    scanned = 0

    while True:
        scan_kwargs = {
            'FilterExpression': 'begins_with(PK, :p)',
            'ExpressionAttributeValues': {':p': 'notifications'},
            'Limit': 100
        }
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = last_key

        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        if not items:
            break

        for item in items:
            scanned += 1
            pk = item['PK']
            sk = item['SK']
            try:
                table.delete_item(Key={'PK': pk, 'SK': sk})
                deleted += 1
                print(f"Deleted {sk} (PK: {pk})")
            except Exception as e:
                print(f"Failed to delete {sk}: {e}")

        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break

    print(f"\nScanned {scanned} notification items, deleted {deleted}.")


if __name__ == '__main__':
    skip = '--yes' in sys.argv
    if not skip:
        print(f"This will delete ALL notification items from table '{TABLE_NAME}'.")
        print(f"DynamoDB Local: {DYNAMODB_LOCAL}, endpoint: {client_kwargs.get('endpoint_url', 'AWS default')}")
        confirm = input("Type 'yes' to proceed: ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    delete_all_notifications()
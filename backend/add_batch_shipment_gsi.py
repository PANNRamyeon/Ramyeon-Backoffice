"""
Script to add the batch-shipment-id-index GSI to RamyeonCornerDB.

GSI allows efficient lookup of batches by shipment_id without scanning
the entire batches partition. Used by:
  - Batch.get_by_shipment_id()
  - BatchService.activate_batches_for_shipment()
  - BatchService.cancel_batches_for_shipment()

Run from the backend directory:
    python add_batch_shipment_gsi.py
"""
import os
import sys
import time
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import boto3
from decouple import config
from botocore.exceptions import ClientError

TABLE_NAME  = config('DYNAMO_TABLE_NAME', default='RamyeonCornerDB')
REGION      = config('AWS_REGION_NAME',   default='ap-southeast-1')
ACCESS_KEY  = config('AWS_ACCESS_KEY_ID',     default='')
SECRET_KEY  = config('AWS_SECRET_ACCESS_KEY', default='')
INDEX_NAME  = 'batch-shipment-id-index'


def get_table(client):
    return client.describe_table(TableName=TABLE_NAME)['Table']


def gsi_exists(client):
    table = get_table(client)
    existing = [gsi['IndexName'] for gsi in table.get('GlobalSecondaryIndexes', [])]
    return INDEX_NAME in existing


def wait_for_active(client, interval=10):
    """Poll until the table and all GSIs are ACTIVE."""
    print('Waiting for table to become ACTIVE', end='', flush=True)
    while True:
        table = get_table(client)
        table_status = table['TableStatus']
        gsi_statuses = [
            gsi['IndexStatus']
            for gsi in table.get('GlobalSecondaryIndexes', [])
            if gsi['IndexName'] == INDEX_NAME
        ]
        gsi_status = gsi_statuses[0] if gsi_statuses else None

        if table_status == 'ACTIVE' and gsi_status == 'ACTIVE':
            print(' done.')
            return
        print('.', end='', flush=True)
        time.sleep(interval)


def add_gsi(client):
    # Check billing mode so we pass the right throughput settings
    table = get_table(client)
    billing_mode = table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')

    update_kwargs = {
        'TableName': TABLE_NAME,
        # shipment_id is a new attribute for the table's AttributeDefinitions;
        # SK is already defined as the table sort key, no need to re-declare it.
        'AttributeDefinitions': [
            {'AttributeName': 'shipment_id', 'AttributeType': 'S'},
            {'AttributeName': 'SK',          'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexUpdates': [
            {
                'Create': {
                    'IndexName': INDEX_NAME,
                    'KeySchema': [
                        {'AttributeName': 'shipment_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'SK',          'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    # Only include provisioned throughput for PROVISIONED tables
                    **({'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}}
                       if billing_mode != 'PAY_PER_REQUEST' else {}),
                }
            }
        ],
    }

    client.update_table(**update_kwargs)
    print(f"GSI '{INDEX_NAME}' creation initiated.")


def main():
    client = boto3.client(
        'dynamodb',
        region_name=REGION,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    print(f"Table : {TABLE_NAME}")
    print(f"Region: {REGION}")
    print(f"GSI   : {INDEX_NAME}")
    print()

    if gsi_exists(client):
        print(f"GSI '{INDEX_NAME}' already exists. Nothing to do.")
        return

    try:
        add_gsi(client)
    except ClientError as e:
        print(f"Error creating GSI: {e}")
        sys.exit(1)

    wait_for_active(client)
    print(f"\nGSI '{INDEX_NAME}' is active and ready.")
    print("You can now remove the filter-scan fallback warning from Batches.py if desired,")
    print("but the fallback is harmless and provides resilience if the index is ever missing.")


if __name__ == '__main__':
    main()

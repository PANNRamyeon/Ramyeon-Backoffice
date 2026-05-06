import boto3
from botocore.exceptions import ClientError
import time

# Configuration – change if needed
TABLE_NAME = 'RamyeonCornerDB'
ENDPOINT_URL = 'http://localhost:8000'  # for DynamoDB Local; omit for AWS

def add_recipient_index():
    # Create DynamoDB client (point to local if needed)
    if ENDPOINT_URL:
        dynamodb = boto3.client('dynamodb', endpoint_url=ENDPOINT_URL)
    else:
        dynamodb = boto3.client('dynamodb')

    # Define the GSI
    gsi = {
        'IndexName': 'notification-recipient-index',
        'KeySchema': [
            {'AttributeName': 'recipient_id', 'KeyType': 'HASH'},
            {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
        ],
        'Projection': {'ProjectionType': 'ALL'},
        'ProvisionedThroughput': {  # Not needed if table is on‑demand
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    }

    # Define the attribute definitions (required for the index keys)
    attribute_definitions = [
        {'AttributeName': 'recipient_id', 'AttributeType': 'S'},
        {'AttributeName': 'created_at', 'AttributeType': 'S'}
    ]

    try:
        # Update the table to add the GSI
        response = dynamodb.update_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=attribute_definitions,
            GlobalSecondaryIndexUpdates=[
                {'Create': gsi}
            ]
        )
        print("Index creation initiated. Response:", response)

        # Wait for the index to become active
        print("Waiting for index to become active...")
        while True:
            desc = dynamodb.describe_table(TableName=TABLE_NAME)
            indexes = desc['Table'].get('GlobalSecondaryIndexes', [])
            for idx in indexes:
                if idx['IndexName'] == 'notification-recipient-index':
                    status = idx['IndexStatus']
                    print(f"Index status: {status}")
                    if status == 'ACTIVE':
                        print("Index is now active.")
                        return
            time.sleep(2)

    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationException' and 'already exists' in str(e):
            print("Index already exists. No action needed.")
        else:
            print(f"Error: {e}")

if __name__ == '__main__':
    add_recipient_index()
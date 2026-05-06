import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
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
client = boto3.client('dynamodb', **client_kwargs)


def table_exists(table_name):
    try:
        client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise


def get_existing_indexes(table_name):
    response = client.describe_table(TableName=table_name)
    table = response['Table']
    return {idx['IndexName']: idx for idx in table.get('GlobalSecondaryIndexes', [])}


def add_index(table_name, index_name, hash_key, range_key, read_capacity=5, write_capacity=5):
    try:
        response = client.update_table(
            TableName=table_name,
            AttributeDefinitions=[
                {'AttributeName': hash_key, 'AttributeType': 'S'},
                {'AttributeName': range_key, 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    'Create': {
                        'IndexName': index_name,
                        'KeySchema': [
                            {'AttributeName': hash_key, 'KeyType': 'HASH'},
                            {'AttributeName': range_key, 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': read_capacity,
                            'WriteCapacityUnits': write_capacity
                        }
                    }
                }
            ]
        )
        print(f"✅ Initiated creation of index '{index_name}' on table '{table_name}'.")
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"ℹ️ Index '{index_name}' already exists or is being created.")
        else:
            print(f"❌ Error creating index '{index_name}': {e}")
        return None


def main():
    print(f"🔍 Checking table '{TABLE_NAME}'...")
    if not table_exists(TABLE_NAME):
        print(f"❌ Table '{TABLE_NAME}' does not exist. Please create it first.")
        return

    existing = get_existing_indexes(TABLE_NAME)
    print(f"📋 Existing indexes: {list(existing.keys())}")

    # Promotion GSIs – all have PK as hash key, different range keys
    required_indexes = [
        {
            'name': 'PromotionStatusIndex',
            'hash_key': 'PK',
            'range_key': 'status',
            'read': 5,
            'write': 2
        },
        {
            'name': 'PromotionDateRangeIndex',
            'hash_key': 'PK',
            'range_key': 'start_date',
            'read': 5,
            'write': 2
        },
        {
            'name': 'PromotionTargetTypeIndex',
            'hash_key': 'PK',
            'range_key': 'target_type',
            'read': 3,
            'write': 2
        },
        {
            'name': 'PromotionSeasonalIndex',
            'hash_key': 'PK',
            'range_key': 'seasonal_tag',
            'read': 2,
            'write': 1
        }
    ]

    for idx in required_indexes:
        if idx['name'] in existing:
            print(f"✅ Index '{idx['name']}' already exists.")
        else:
            print(f"🔄 Adding index '{idx['name']}'...")
            add_index(TABLE_NAME, idx['name'], idx['hash_key'], idx['range_key'],
                      idx['read'], idx['write'])

    print("""
✅ Script completed.

Index creation is asynchronous and may take several minutes to become active.
Monitor status in AWS Console → DynamoDB → Tables → RamyeonCornerDB → Indexes.
Once indexes are active, restart your Django server.
""")


if __name__ == '__main__':
    main()
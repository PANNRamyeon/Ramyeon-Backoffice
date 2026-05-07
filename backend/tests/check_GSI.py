import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# Configuration – matches your existing setup
# ------------------------------------------------------------------
TABLE_NAME = os.getenv('DYNAMO_TABLE_NAME', 'RamyeonCornerDB')
AWS_REGION = os.getenv('AWS_REGION_NAME') or os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
# For local DynamoDB (e.g. http://localhost:8000)
DYNAMO_ENDPOINT = os.getenv('DYNAMO_ENDPOINT_URL')

# ------------------------------------------------------------------
# Create DynamoDB client
# ------------------------------------------------------------------
client_kwargs = {'region_name': AWS_REGION}
if DYNAMO_ENDPOINT:                     # local DynamoDB
    client_kwargs['endpoint_url'] = DYNAMO_ENDPOINT
elif AWS_ACCESS_KEY and AWS_SECRET_KEY:  # AWS real
    client_kwargs['aws_access_key_id'] = AWS_ACCESS_KEY
    client_kwargs['aws_secret_access_key'] = AWS_SECRET_KEY
# else rely on IAM roles or default credentials

client = boto3.client('dynamodb', **client_kwargs)


def describe_table(table_name):
    """Return the full DescribeTable output or None if table missing."""
    try:
        response = client.describe_table(TableName=table_name)
        return response['Table']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"❌ Table '{table_name}' does not exist.")
            return None
        raise


def print_gsi_details(table):
    """Print detailed information about each GSI."""
    gsis = table.get('GlobalSecondaryIndexes', [])
    if not gsis:
        print("⚠️ No Global Secondary Indexes found on this table.")
        return

    print(f"📋 Found {len(gsis)} GSI(s) on table '{TABLE_NAME}':\n")
    for i, gsi in enumerate(gsis, start=1):
        name = gsi.get('IndexName', 'Unknown')
        key_schema = gsi.get('KeySchema', [])
        projection = gsi.get('Projection', {}).get('ProjectionType', 'Unknown')
        provisioned = gsi.get('ProvisionedThroughput', {})
        read_cap = provisioned.get('ReadCapacityUnits', 'N/A')
        write_cap = provisioned.get('WriteCapacityUnits', 'N/A')
        item_count = gsi.get('ItemCount', 'N/A')
        status = gsi.get('IndexStatus', 'Unknown')
        size_bytes = gsi.get('IndexSizeBytes', 0)

        # Build human-readable key description
        keys = []
        for k in key_schema:
            keys.append(f"{k['AttributeName']} ({k['KeyType']})")
        key_str = ' | '.join(keys)

        print(f"🔹 GSI #{i}: {name}")
        print(f"   • Status:        {status}")
        print(f"   • Keys:          {key_str}")
        print(f"   • Projection:    {projection}")
        print(f"   • Capacity:      Read {read_cap} / Write {write_cap}")
        print(f"   • Item count:    {item_count}")
        print(f"   • Size (bytes):  {size_bytes:,}")
        print(f"   • Size (MB):     {size_bytes / (1024*1024):.2f} MB")
        print("-" * 60)


def main():
    print(f"🔍 Checking table '{TABLE_NAME}'...")
    table = describe_table(TABLE_NAME)
    if not table:
        return

    print(f"✅ Table exists (Status: {table.get('TableStatus', 'Unknown')})")
    print(f"   • Primary Key:  {table['KeySchema']}")
    print(f"   • Item count:   {table.get('ItemCount', 'N/A')}")
    print()

    print_gsi_details(table)


if __name__ == '__main__':
    main()
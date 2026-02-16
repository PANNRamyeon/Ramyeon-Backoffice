import os
import boto3
from botocore.exceptions import ClientError

# Initialize DynamoDB resource
AWS_REGION = os.getenv('AWS_REGION', 'ap-southeast-1')
DYNAMO_TABLE_NAME = "RamyeonCornerDB"

DYNAMODB_LOCAL = os.getenv("DYNAMODB_LOCAL", "true").lower() == "true"
DYNAMODB_LOCAL_HOST = os.getenv("DYNAMODB_LOCAL_HOST", "http://localhost:8000")

def get_dynamo_table():
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    return dynamodb.Table(DYNAMO_TABLE_NAME)

def get_next_sequence(counter_name):
    """
    Atomically increments and returns the next sequence number for a given counter.
    
    Args:
        counter_name (str): The name of the counter (e.g., 'product_seq', 'category_seq', 'user_seq')
        
    Returns:
        int: The next sequence number.
    """
    table = get_dynamo_table()
    try:
        # Atomic increment using ADD
        # This ensures syncing/concurrency safety on the DB side
        response = table.update_item(
            Key={
                'PK': 'CONFIG',
                'SK': 'COUNTERS'
            },
            UpdateExpression=f'ADD {counter_name} :inc',
            ExpressionAttributeValues={
                ':inc': 1
            },
            ReturnValues="UPDATED_NEW"
        )
        
        # DynamoDB returns Decimal, convert to int
        return int(response['Attributes'][counter_name])
        
    except ClientError as e:
        print(f"Error generating sequence: {e}")
        raise e

def generate_sk(prefix, counter_name):
    """
    Generates a Sort Key (SK) using a prefix and an auto-incrementing sequence.
    Example: generate_sk('USER-', 'user_seq') -> 'USER-00042'
    """
    next_id = get_next_sequence(counter_name)
    return f"{prefix}{next_id:05d}"
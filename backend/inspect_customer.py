import os
import boto3
from dotenv import load_dotenv
import json

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

def scan_customers():
    last_key = None
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
        for item in items:
            sk = item.get('SK')
            print(f"Customer: {sk}")
            # Print datetime fields raw values
            for field in ['date_created', 'updated_at', 'last_purchase', 'password_last_changed']:
                if field in item:
                    print(f"  {field}: {item[field]}")
            if 'auth_providers' in item:
                for idx, prov in enumerate(item['auth_providers']):
                    if 'last_login' in prov:
                        print(f"  auth_providers[{idx}].last_login: {prov['last_login']}")
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break

if __name__ == '__main__':
    scan_customers()
import os
import boto3
from dotenv import load_dotenv

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

def delete_all_promotions():
    last_key = None
    deleted = 0
    while True:
        scan_kwargs = {
            'FilterExpression': 'PK = :pk',
            'ExpressionAttributeValues': {':pk': 'promotions'},
            'Limit': 100
        }
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = last_key
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        if not items:
            break
        for item in items:
            sk = item['SK']
            table.delete_item(Key={'PK': 'promotions', 'SK': sk})
            print(f"Deleted {sk}")
            deleted += 1
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
    print(f"Total promotions deleted: {deleted}")

if __name__ == '__main__':
    confirm = input("This will permanently delete ALL promotion data. Type 'yes' to confirm: ")
    if confirm.lower() == 'yes':
        delete_all_promotions()
    else:
        print("Aborted.")
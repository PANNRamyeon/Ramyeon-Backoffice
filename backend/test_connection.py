import os
from dotenv import load_dotenv
from pynamodb.connection import Connection

# Load environment variables from .env file
# This will look for .env in the current directory or parent directories
load_dotenv()

def test_dynamodb_connection():
    print("Attempting to connect to DynamoDB using PynamoDB...")
    
    try:
        # Initialize a PynamoDB Connection
        # PynamoDB will automatically look for AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
        # in os.environ, which load_dotenv() just populated.
        region = os.getenv('AWS_REGION', 'ap-southeast-1')
        connection = Connection(region=region)

        # Call list_tables to verify connection and permissions
        response = connection.list_tables()
        
        print("\n✅ Connection Successful!")
        print(f"Region: {region}")
        print(f"Tables found: {response['TableNames']}")
        
    except Exception as e:
        print("\n❌ Connection Failed")
        print(f"Error details: {e}")
        print("Tip: Check your .env file paths and ensure the IAM user has 'AmazonDynamoDBFullAccess' or similar permissions.")

if __name__ == "__main__":
    test_dynamodb_connection()
# app/database.py
import boto3
from django.conf import settings
from decouple import config
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.dynamodb = None
        
    def connect_to_dynamodb(self):
        """Connect to DynamoDB, either local or on AWS."""
        try:
            # Using decouple to get settings.
            # Set USE_LOCAL_DYNAMODB=True in your .env file for local development.
            if config('USE_LOCAL_DYNAMODB', default=False, cast=bool):
                logger.info("Connecting to local DynamoDB")
                self.dynamodb = boto3.resource(
                    'dynamodb',
                    endpoint_url=config('DYNAMODB_LOCAL_ENDPOINT', default='http://localhost:8000'),
                    region_name=config('AWS_REGION_NAME', default='ap-southeast-1'),
                    aws_access_key_id=config('AWS_ACCESS_KEY_ID', default='dummy'),
                    aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY', default='dummy')
                )
            else:
                logger.info("Connecting to AWS DynamoDB")
                # Explicitly load credentials from .env file
                self.dynamodb = boto3.resource(
                    'dynamodb',
                    region_name=config('AWS_REGION_NAME', default='ap-southeast-1'),
                    aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY')
                )
            
            logger.info("Successfully connected to DynamoDB")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to DynamoDB: {e}")
            return False
    
    def get_database(self):
        """
        Provides a singleton DynamoDB resource.
        It tries to connect if not already connected.
        """
        if self.dynamodb is None:
            if not self.connect_to_dynamodb():
                raise Exception("Could not connect to DynamoDB")
        return self.dynamodb

# Singleton instance for the rest of the application to use
db_manager = DatabaseManager()
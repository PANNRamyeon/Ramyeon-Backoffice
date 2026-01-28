import os
from pynamodb.models import Model

class BaseModel(Model):
    """
    Base model for all DynamoDB tables.
    This ensures all tables use the correct region from .env
    """
    class Meta:
        # PynamoDB will automatically use AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
        # from os.environ (loaded by manage.py)
        region = os.getenv('AWS_REGION', 'ap-southeast-1')
        
        # If you are using DynamoDB Local in the future, you would set 'host' here
        # host = "http://localhost:8000"
import os
from .counters import counter_service

# Define constants that the Product model and other parts of the app expect
DYNAMO_TABLE_NAME = os.getenv("DYNAMO_TABLE_NAME", "RamyeonCornerDB")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_LOCAL = os.getenv("DYNAMODB_LOCAL", "False").lower() == "true"
DYNAMODB_LOCAL_HOST = os.getenv("DYNAMODB_LOCAL_HOST", "http://localhost:8000")

def generate_sk(prefix: str, sequence_name: str) -> str:
    """
    Generates a sequential, formatted ID by calling the counter service.
    
    This function acts as an adapter. The Product model was trying to call 
    generate_sk('PROD-', 'product_seq'), but the actual service expects 
    the arguments in a different order and format. This function translates
    the call correctly.
    """
    # The call in the Product model is generate_sk('PROD-', 'product_seq')
    # We map this to the counter_service's expected arguments.
    # The width is hardcoded to 5 as expected by the PROD-##### format.
    return counter_service.get_next_id(collection_name=sequence_name, prefix=prefix, width=5)

def get_dynamo_table(table_name: str):
    """
    Dummy function to satisfy the import in the Product model.
    The PynamoDB model manages its own table connection through its Meta class,
    so this function is only here to prevent the ImportError.
    """
    from ..services.core.database_service import DatabaseService
    db_service = DatabaseService()
    return db_service.get_table(table_name)

# Define __all__ to control what 'from app.utils import *' imports, if used.
__all__ = ['generate_sk', 'get_dynamo_table', 'DYNAMO_TABLE_NAME', 'AWS_REGION', 'DYNAMODB_LOCAL', 'DYNAMODB_LOCAL_HOST']

# backend/app/services/database_service.py
from ...database import db_manager

class DatabaseService:
    def __init__(self):
        """
        Initializes the service by getting a DynamoDB resource from the database manager.
        """
        self.dynamodb = db_manager.get_database()
    
    def get_table(self, table_name):
        """
        Returns a Boto3 Table resource, which can be used to perform CRUD operations.
        
        Args:
            table_name (str): The name of the DynamoDB table.
        
        Returns:
            boto3.resources.factory.dynamodb.Table: The DynamoDB table resource.
        """
        return self.dynamodb.Table(table_name)

# You can add more generic helper functions here if needed, for example,
# a function to handle decimal to float conversion for JSON serialization,
# as DynamoDB's Decimal type is not directly JSON serializable.
#
# import decimal
#
# def decimal_default(obj):
#     if isinstance(obj, decimal.Decimal):
#         return float(obj)
#     raise TypeError
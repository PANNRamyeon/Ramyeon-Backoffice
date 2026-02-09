"""
backend/app/utils/counters.py
Utility for managing atomic counters and generating sequential IDs in DynamoDB.
"""
import logging
import os
from boto3.dynamodb.conditions import Key
from ..services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class CounterService:
    def __init__(self):
        self.db_service = DatabaseService()
        # Default to the table name used in migration if not set in env
        self.table_name = os.getenv("DYNAMO_TABLE_NAME", "RamyeonCornerDB")
        self.table = self.db_service.get_table(self.table_name)
        
        # Key names used in the single-table design
        # These match the defaults in migrate_mongo_to_dynamo.py
        self.pk_name = 'PK'
        self.sk_name = 'SK'
        self.counter_pk = 'COUNTERS'

    def _get_current_max_id(self, collection_name, prefix):
        """
        Internal method to find the highest existing ID number in a collection.
        Used for initializing the counter if it doesn't exist.
        """
        try:
            # Query the collection partition, sorting by SK descending to get the last item
            response = self.table.query(
                KeyConditionExpression=Key(self.pk_name).eq(collection_name),
                ScanIndexForward=False,  # Descending order
                Limit=1
            )
            
            if response.get('Items'):
                last_item = response['Items'][0]
                last_id = last_item.get(self.sk_name, '')
                
                # Check if the ID matches the expected prefix format (e.g., PROD-00001)
                if last_id and last_id.startswith(prefix):
                    try:
                        # Extract the numeric part (assumes format PREFIX-NUMBER)
                        # Split by the last hyphen to handle prefixes that might contain hyphens
                        number_part = last_id.rsplit('-', 1)[-1]
                        return int(number_part)
                    except ValueError:
                        logger.warning(f"Could not parse number from ID: {last_id}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error finding max ID for {collection_name}: {e}")
            return 0

    def initialize_counter(self, collection_name, prefix, width=5):
        """
        Initialize or update the counter for a collection, ensuring its configuration is correct.
        If the counter doesn't exist, it scans for the max existing ID.
        """
        try:
            response = self.table.get_item(
                Key={self.pk_name: self.counter_pk, self.sk_name: collection_name}
            )

            if 'Item' in response:
                item = response['Item']
                current_val = int(item.get('current_value', 0))
                # If item exists, ensure prefix and width are up-to-date.
                if item.get('prefix') != prefix or item.get('width') != width:
                    self.table.update_item(
                        Key={self.pk_name: self.counter_pk, self.sk_name: collection_name},
                        UpdateExpression="SET prefix = :p, width = :w",
                        ExpressionAttributeValues={':p': prefix, ':w': width},
                    )
                    logger.info(f"Updated config for '{collection_name}' to prefix='{prefix}', width={width}.")
                return current_val

            # If not, find the max existing ID to start from
            logger.info(f"Counter for '{collection_name}' not found. Initializing from existing data...")
            current_max = self._get_current_max_id(collection_name, prefix)
            
            # Create the counter item
            self.table.put_item(
                Item={
                    self.pk_name: self.counter_pk,
                    self.sk_name: collection_name,
                    'current_value': current_max,
                    'prefix': prefix,
                    'width': width,
                }
            )
            logger.info(f"Initialized counter for '{collection_name}' at {current_max} with width {width}.")
            return current_max
            
        except Exception as e:
            logger.error(f"Error initializing counter for {collection_name}: {e}")
            raise

    def get_next_id(self, collection_name, prefix=None, width=None):
        """
        Atomically increments a counter and returns a new formatted ID.
        The prefix and width are stored in the database during initialization.
        Passing prefix or width here will override the stored config for this call only.
        """
        try:
            # Atomically increment the counter.
            response = self.table.update_item(
                Key={
                    self.pk_name: self.counter_pk,
                    self.sk_name: collection_name
                },
                UpdateExpression="ADD current_value :inc",
                ExpressionAttributeValues={':inc': 1},
                ReturnValues="ALL_NEW"  # Return the full item after update
            )
            
            attributes = response.get('Attributes', {})
            next_val = int(attributes.get('current_value', 0))

            # Use override if provided, otherwise use stored value, finally fallback.
            final_prefix = prefix if prefix is not None else attributes.get('prefix', 'UNKNOWN')
            final_width = width if width is not None else attributes.get('width', 5)

            # Format the ID with proper padding
            formatted_id = f"{final_prefix}-{str(next_val).zfill(final_width)}"
            
            return formatted_id

        except self.table.meta.client.exceptions.ClientError as e:
            # If the counter item does not exist, update_item fails.
            # This is a critical error; counters must be initialized.
            logger.error(
                f"Failed to get next ID for '{collection_name}'. The counter does not exist. "
                f"Please run the initialization script. Error: {e}"
            )
            raise Exception(f"Counter '{collection_name}' is not initialized.") from e
        except Exception as e:
            logger.error(f"Error generating next ID for {collection_name}: {e}")
            raise

# Singleton instance for easy import
counter_service = CounterService()

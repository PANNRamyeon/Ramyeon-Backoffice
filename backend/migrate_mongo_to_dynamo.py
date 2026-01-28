import os
import sys
import json
import argparse
import boto3
import pymongo
from decimal import Decimal
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
# Ensure these match your environment or .env file
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = "pos_system"  # Updated to match your project DB name
DYNAMO_TABLE_NAME = "RamyeonCornerDB"
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1") # Adjust region as needed

def get_dynamo_table():
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    return dynamodb.Table(DYNAMO_TABLE_NAME)

def get_mongo_db():
    # Debugging: Print the URI host (hiding credentials)
    masked_uri = MONGO_URI.split('@')[-1] if '@' in MONGO_URI else MONGO_URI
    print(f"Connecting to MongoDB at: {masked_uri}")
    
    try:
        client = pymongo.MongoClient(MONGO_URI)
        # Verify connection
        client.admin.command('ping')
        return client[MONGO_DB_NAME]
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
        print(f"   Please check your MONGO_URI in the .env file.")
        print(f"   It looks like the URI is invalid (e.g. typo in 'mongodb.net').\n")
        sys.exit(1)

def clean_item(item):
    """
    Recursively cleans a dictionary to be DynamoDB compatible.
    1. Converts floats to Decimals.
    2. Converts ObjectIds to Strings.
    3. Removes empty strings (DynamoDB doesn't allow them).
    4. Converts datetimes to ISO strings.
    """
    if isinstance(item, dict):
        new_item = {}
        for k, v in item.items():
            if v == "": 
                continue # Skip empty strings
            
            cleaned_v = clean_item(v)
            if cleaned_v is not None:
                new_item[k] = cleaned_v
        return new_item
    
    elif isinstance(item, list):
        return [clean_item(i) for i in item if i is not None]
    
    elif isinstance(item, float):
        # DynamoDB requires Decimal for floating point numbers
        # Handle NaN/Infinity which DynamoDB does not support
        if item != item or item == float('inf') or item == float('-inf'):
            return None
        return Decimal(str(item))
    
    elif isinstance(item, ObjectId):
        return str(item)
        
    elif isinstance(item, datetime):
        return item.isoformat()
    
    return item

def prepare_for_display(item):
    """Helper to format items for clean console output (truncating long strings, handling Decimals)"""
    if isinstance(item, dict):
        return {k: prepare_for_display(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [prepare_for_display(i) for i in item]
    elif isinstance(item, Decimal):
        return float(item)
    elif isinstance(item, str) and len(item) > 50:
        return item[:47] + "..."
    elif isinstance(item, (bytes, bytearray)):
        return "<BINARY>"
    return item

def run_migration(dry_run=False, collection_name=None):
    mongo_db = get_mongo_db()
    print(f"Using MongoDB Database: {MONGO_DB_NAME}")

    # Default key names
    pk_name = 'pk'
    sk_name = 'sk'
    
    table = get_dynamo_table()
    try:
        # Detect actual key schema from DynamoDB
        table.load()
        pk_name = next(k['AttributeName'] for k in table.key_schema if k['KeyType'] == 'HASH')
        sk_name = next((k['AttributeName'] for k in table.key_schema if k['KeyType'] == 'RANGE'), None)
        print(f"Detected DynamoDB Schema: Partition Key='{pk_name}', Sort Key='{sk_name}'")
    except Exception as e:
        print(f"Schema Detection Warning: {e}. Using defaults: {pk_name}, {sk_name}")
    
    if not dry_run:
        print(f"Target DynamoDB Table: {DYNAMO_TABLE_NAME}")
    else:
        print("!!! DRY RUN MODE: No changes will be applied to DynamoDB !!!")
    
    # Determine which collections to migrate
    if collection_name:
        if collection_name not in mongo_db.list_collection_names():
            print(f"Error: Collection '{collection_name}' not found in MongoDB.")
            return
        collections = [collection_name]
    else:
        collections = mongo_db.list_collection_names()
    
    print(f"Collections to migrate: {collections}")

    summary_stats = []

    for col_name in collections:
        print(f"Processing collection: {col_name}...")
        collection = mongo_db[col_name]
        count = 0
        
        # Filter out soft-deleted documents
        query = {'isDeleted': {'$ne': True}}
        
        # Pre-fetch categories for product denormalization
        category_map = {}
        if col_name == 'products':
            print("  Loading category map for denormalization...")
            try:
                cat_col_name = 'category'
                if 'categories' in mongo_db.list_collection_names():
                    cat_col_name = 'categories'
                print(f"  Using '{cat_col_name}' collection for category names.")
                
                for cat in mongo_db[cat_col_name].find({}, {'_id': 1, 'category_name': 1}):
                    category_map[str(cat['_id'])] = cat.get('category_name')
                print(f"  Loaded {len(category_map)} categories.")
            except Exception as e:
                print(f"  Warning: Error loading categories: {e}")

        def process_doc(doc):
            # 1. Clean data types
            clean_doc = clean_item(doc)
            
            # --- Collection Specific Transformations ---
            # Category: Remove 'products' list from sub_categories to save space (use GSI instead)
            if col_name in ['category', 'categories']:
                if 'sub_categories' in clean_doc and isinstance(clean_doc['sub_categories'], list):
                    new_subs = []
                    for sub in clean_doc['sub_categories']:
                        if isinstance(sub, dict):
                            new_sub = {k: v for k, v in sub.items() if k not in ['products', 'product_ids', 'products_backup']}
                            new_subs.append(new_sub)
                    clean_doc['sub_categories'] = new_subs
            
            # Global: Omit images to save space (applied to all collections)
            for field in ['image_url', 'image_filename', 'image_size', 'image_type', 'image_uploaded_at']:
                clean_doc.pop(field, None)

            # Products: Denormalize category_name
            if col_name == 'products':
                # Denormalize category_name
                cat_id = clean_doc.get('category_id')
                if cat_id and str(cat_id) in category_map:
                    clean_doc['category_name'] = category_map[str(cat_id)]

            # 2. Map Schema: PK = Collection Name, SK = _id
            dynamo_item = {
                pk_name: col_name,        # Use detected Partition Key name
                **clean_doc               # Spread the rest of the attributes
            }
            if sk_name:
                dynamo_item[sk_name] = str(doc['_id']) # Use detected Sort Key name

            # Remove the original _id field as it's now in 'sk'
            if '_id' in dynamo_item:
                del dynamo_item['_id']
            return dynamo_item

        if dry_run:
            samples = []
            for doc in collection.find(query):
                item = process_doc(doc)
                count += 1
                if count <= 5:
                    samples.append(item)
            
            if samples:
                print(f"--- Sample Data (First {len(samples)}) ---")
                
                for i, item in enumerate(samples):
                    print(f"\n[Item {i+1}]")
                    display_item = prepare_for_display(item)
                    print(json.dumps(display_item, indent=2))
                print("\n" + "-" * 40)

            print(f" -> Would migrate {count} items from {col_name}")
            summary_stats.append({"Collection": col_name, "Items": count, "Status": "Dry Run"})
        else:
            with table.batch_writer() as batch:
                for doc in collection.find(query):
                    item = process_doc(doc)
                    batch.put_item(Item=item)
                    count += 1
            
            print(f" -> Migrated {count} items from {col_name}")
            summary_stats.append({"Collection": col_name, "Items": count, "Status": "Success"})

    print("\n" + "="*40)
    print("          MIGRATION SUMMARY")
    print("="*40)
    if summary_stats:
        print(f"{'Collection':<30} | {'Items':<10} | {'Status':<10}")
        print("-" * 56)
        for stat in summary_stats:
            print(f"{stat['Collection']:<30} | {stat['Items']:<10} | {stat['Status']:<10}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate MongoDB to DynamoDB")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without writing to DynamoDB")
    parser.add_argument("--collection", type=str, help="Specific collection to migrate (optional)")
    
    args = parser.parse_args()
    
    run_migration(dry_run=args.dry_run, collection_name=args.collection)
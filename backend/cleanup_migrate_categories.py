import os

# Add your project root to Python path (same as migrate_categories script)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Use the same database connection as your working migration script
from backend.app.database import db_manager
 
def remove_migration_fields():
    print("Removing migration fields using db_manager...")
    
    try:
        # This script is for MongoDB. It will not work with DynamoDB.
        # db = db_manager.get_database() # MongoDB-specific db_manager
        # category_collection = db.category # MongoDB-specific collection access
        
        # Check what we have
        count = category_collection.count_documents({})
        print(f"Found {count} documents in 'category' collection")
        
        # Show sample document with migration fields
        sample = category_collection.find_one({
            "$or": [
                {"migrated_at": {"$exists": True}},
                {"migration_completed": {"$exists": True}},
                {"combined_migrated_at": {"$exists": True}},
                {"combined_migration_completed": {"$exists": True}}
            ]
        })
        
        if sample:
            print(f"\nFound document with migration fields:")
            print(f"Category: {sample.get('category_name')}")
            
            migration_fields_found = []
            for field in ["migrated_at", "migration_completed", "combined_migrated_at", "combined_migration_completed"]:
                if field in sample:
                    migration_fields_found.append(f"{field}: {sample[field]}")
            
            print(f"Migration fields: {migration_fields_found}")
            
            # Remove the migration fields
            result = category_collection.update_many(
                {},
                {
                    "$unset": {
                        "migrated_at": "",
                        "migration_completed": "",
                        "combined_migrated_at": "",
                        "combined_migration_completed": ""
                    }
                }
            )
            
            print(f"\nRemoval result: {result.modified_count} documents modified")
            
            # Verify removal
            remaining = category_collection.count_documents({
                "$or": [
                    {"migrated_at": {"$exists": True}},
                    {"migration_completed": {"$exists": True}},
                    {"combined_migrated_at": {"$exists": True}},
                    {"combined_migration_completed": {"$exists": True}}
                ]
            })
            
            print(f"Documents still with migration fields: {remaining}")
            
            if remaining == 0:
                print("SUCCESS: All migration fields removed!")
            else:
                print("WARNING: Some migration fields still remain")
                
        else:
            print("No documents found with migration fields")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Cleanup Migration Fields (Using db_manager)")
    print("=" * 50)
    
    try:
        remove_migration_fields()
    except Exception as e:
        print(f"Cleanup failed: {e}")
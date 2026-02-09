#!/usr/bin/env python3
"""
Standalone migration script for converting category subcategories 
from product names to ObjectIDs
"""
import os
import argparse

# Add your project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now use absolute import - adjust this path to match your project structure
# from backend.app.database import db_manager # MongoDB-specific db_manager


def migrate_categories_combined(dry_run=True, force=False):
    """Migrate to combined product_id + product_name structure"""
    
    print("Starting migration to combined product structure...")
    print(f"Mode: {'DRY RUN' if dry_run else 'ACTUAL MIGRATION'} (NOTE: This script is for MongoDB and will not work with DynamoDB)")
    print("=" * 50)
    
    try:
        # This script is for MongoDB. It will not work with DynamoDB.
        # MongoDB-specific operations are commented out or removed.
        # db = db_manager.get_database()
        # category_collection = db.category
        # product_collection = db.products
        
        # Find categories that need migration to combined format
        if force:
            categories = list(category_collection.find({
                'sub_categories': {'$exists': True}
            }))
        else:
            categories = list(category_collection.find({
                '$or': [
                    {'sub_categories.products': {'$exists': True}},
                    {'sub_categories.product_ids': {'$exists': True}}
                ],
                'combined_migration_completed': {'$ne': True}
            }))
        
        print(f'Found {len(categories)} categories to migrate to combined format')
        
        migrated_count = 0
        error_count = 0
        
        for category in categories:
            try:
                category_name = category.get('category_name', 'Unknown')
                print(f'\nProcessing category: {category_name}')
                
                updated_subcategories = []
                
                for subcategory in category.get('sub_categories', []):
                    subcategory_name = subcategory.get('name', 'Unknown')
                    
                    # Handle both old formats
                    combined_products = []
                    
                    # Case 1: Old string array format
                    if 'products' in subcategory and isinstance(subcategory.get('products'), list):
                        products_list = subcategory.get('products', [])
                        if products_list and isinstance(products_list[0], str):
                            print(f'  Converting string products in "{subcategory_name}"')
                            
                            for product_name in products_list:
                                if not product_name or not product_name.strip():
                                    continue
                                    
                                product = product_collection.find_one({
                                    'product_name': {
                                        '$regex': f'^{product_name.strip()}$', 
                                        '$options': 'i'
                                    },
                                    'isDeleted': {'$ne': True}
                                })
                                
                                if product:
                                    combined_products.append({
                                        'product_id': product['_id'],
                                        'product_name': product['product_name']
                                    })
                                    print(f'    ✓ Combined: {product_name} -> {product["_id"]}')
                                else:
                                    print(f'    ✗ Product not found: {product_name}')
                        
                        # Case 1b: Already in combined format
                        elif products_list and isinstance(products_list[0], dict):
                            print(f'  "{subcategory_name}" already in combined format')
                            combined_products = products_list
                    
                    # Case 2: ObjectID array format (from previous migration)
                    elif 'product_ids' in subcategory:
                        print(f'  Converting ObjectID products in "{subcategory_name}"')
                        
                        for product_id in subcategory.get('product_ids', []):
                            product = product_collection.find_one({
                                '_id': product_id,
                                'isDeleted': {'$ne': True}
                            })
                            
                            if product:
                                combined_products.append({
                                    'product_id': product['_id'],
                                    'product_name': product['product_name']
                                })
                                print(f'    ✓ Combined: {product_id} -> {product["product_name"]}')
                            else:
                                print(f'    ✗ Product ID not found: {product_id}')
                    
                    # Case 3: Empty subcategory
                    else:
                        print(f'  "{subcategory_name}" has no products')
                        combined_products = []
                    
                    # Update subcategory with combined format
                    subcategory['products'] = combined_products
                    subcategory['updated_at'] = datetime.utcnow()
                    
                    # Remove old fields
                    subcategory.pop('product_ids', None)
                    subcategory.pop('products_backup', None)
                    
                    updated_subcategories.append(subcategory)
                
                if not dry_run:
                    result = category_collection.update_one(
                        {'_id': category['_id']},
                        {
                            '$set': {
                                'sub_categories': updated_subcategories,
                                'last_updated': datetime.utcnow(),
                                'combined_migration_completed': True,
                                'combined_migrated_at': datetime.utcnow()
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        migrated_count += 1
                        print(f'  ✓ Migrated to combined format: {category_name}')
                    else:
                        print(f'  ! No changes made to: {category_name}')
                else:
                    print(f'  [DRY RUN] Would migrate to combined format: {category_name}')
                    migrated_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f'ERROR migrating category {category_name}: {str(e)}')
        
        # Summary
        print('\n' + '='*50)
        if dry_run:
            print('DRY RUN COMPLETE - Combined format migration ready')
            print(f'Categories that would be migrated: {migrated_count}')
            print(f'Errors encountered: {error_count}')
            print('\nRun with --execute flag to perform actual migration')
        else:
            print('COMBINED FORMAT MIGRATION COMPLETE')
            print(f'Categories migrated: {migrated_count}')
            print(f'Errors: {error_count}')
        
        return migrated_count, error_count
        
    except Exception as e:
        print(f'Combined migration failed: {str(e)}')
        raise

def backup_categories():
    """Create a backup of current categories"""
    import json
    
    print("Creating backup...")
    
    try:
        # This function is for MongoDB. It will not work with DynamoDB.
        # db = db_manager.get_database()
        # categories = list(db.category.find({}))
        
        # Convert ObjectIds to strings for JSON
        # for category in categories:
        #     category['_id'] = str(category['_id'])
        #     for field in ['category_id', 'supplier_id', 'branch_id']:
        #         if field in category and category[field]:
        #             category[field] = str(category[field])
        
        backup_filename = f'categories_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(backup_filename, 'w') as f:
            json.dump(categories, f, indent=2, default=str)
        
        print(f'✓ Backup saved to: {backup_filename}')
        return backup_filename
        
    except Exception as e:
        print(f'ERROR creating backup: {str(e)}')
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate category subcategories to use ObjectIDs')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute the migration (default is dry-run)')
    parser.add_argument('--force', action='store_true', 
                       help='Force migration even if product_ids already exist')
    parser.add_argument('--backup', action='store_true', 
                       help='Create backup before migration')
    
    args = parser.parse_args()
    
    try:
        # Create backup if requested
        if args.backup:
            backup_categories()
            print()
        
        # Run migration
        migrate_categories_combined(dry_run=not args.execute, force=args.force)
        
    except KeyboardInterrupt:
        print('\nMigration interrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'\nMigration failed: {str(e)}')
        sys.exit(1)
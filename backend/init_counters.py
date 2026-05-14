import os
import sys
import django

# 1. Setup Django Environment
# Add the backend directory to the Python path so we can import 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# 2. Import the service (must be done after django.setup())
from app.utils.counters import counter_service

def initialize_counters():
    """
    Scans the DynamoDB table for the highest existing ID in each collection
    and initializes the atomic counters.
    """
    print("Starting DynamoDB Counter Initialization...")
    
    # Configuration: (Collection Name in DB, ID Prefix, Number of Digits)
    # Prefixes and widths MUST match counters.py configuration
    configs = [
        ('products', 'PROD', 5),
        ('category', 'CTGY', 3),  # PK='category' in DynamoDB
        ('subcategories', 'SUB', 5),
        ('users', 'USER', 4),
        ('customers', 'CUST', 5),
        ('batches', 'BATCH', 6),
        ('shipments', 'SHIP', 5),
        ('notifications', 'NOTIF', 6),
        ('online_transactions', 'ONLINE', 6),
        ('audit_logs', 'AUD', 6),
        ('session_logs', 'SESS', 5),
        ('shifts', 'SHIFT', 4),
        ('suppliers', 'SUPP', 3),
        ('sales', 'SALE', 6),
        ('promotions', 'PROM', 4),
        ('pos_pages', 'PAGE', 2),
    ]
    
    for collection, prefix, width in configs:
        try:
            print(f"   Processing '{collection}' (Prefix: {prefix}, Width: {width})...")
            # This method finds the max existing ID and sets/updates the counter
            current_val = counter_service.initialize_counter(collection, prefix, width)
            print(f"   [OK] Counter set to start from: {current_val}")
        except Exception as e:
            print(f"   [ERROR] Failed for '{collection}': {e}")

    print("\nCounter initialization complete.")

if __name__ == "__main__":
    initialize_counters()

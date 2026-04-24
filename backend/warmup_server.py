"""
Server Warm-up Script
Run this after deployment to hit all endpoints and eliminate cold starts
"""
import os
import sys
import django
import requests
import time
from typing import List, Dict

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Configuration
BASE_URL = os.getenv('WARMUP_BASE_URL', 'http://127.0.0.1:8000')
WARMUP_TOKEN = os.getenv('WARMUP_TOKEN', None)  # Optional: Use admin token for authenticated endpoints

# Endpoints to warm up (in order of dependency)
WARMUP_ENDPOINTS = [
    # Public/Health endpoints
    {'method': 'GET', 'path': '/api/v1/admin/users/health/', 'auth': False},
    
    # Authentication (if token not provided, skip authenticated endpoints)
    {'method': 'GET', 'path': '/api/v1/admin/auth/verify/', 'auth': True},
    
    # Categories
    {'method': 'GET', 'path': '/api/v1/admin/categories/', 'auth': True},
    {'method': 'GET', 'path': '/api/v1/admin/categories/uncategorized/', 'auth': True},
    
    # Products
    {'method': 'GET', 'path': '/api/v1/admin/products/', 'auth': True},
    
    # Customers
    {'method': 'GET', 'path': '/api/v1/admin/customers/', 'auth': True},
    
    # Suppliers
    {'method': 'GET', 'path': '/api/v1/admin/suppliers/', 'auth': True},
    
    # Batches
    {'method': 'GET', 'path': '/api/v1/admin/batches/', 'auth': True},
    
    # Promotions
    {'method': 'GET', 'path': '/api/v1/admin/promotions/', 'auth': True},
    
    # Sessions
    {'method': 'GET', 'path': '/api/v1/admin/sessions/', 'auth': True},
]

def warmup_endpoint(endpoint: Dict) -> bool:
    """Warm up a single endpoint"""
    url = f"{BASE_URL}{endpoint['path']}"
    method = endpoint['method']
    
    headers = {}
    if endpoint['auth'] and WARMUP_TOKEN:
        headers['Authorization'] = f'Bearer {WARMUP_TOKEN}'
    elif endpoint['auth'] and not WARMUP_TOKEN:
        print(f"  ⏭️  Skipping {method} {endpoint['path']} (no auth token)")
        return True
    
    try:
        print(f"  🔥 Warming up {method} {endpoint['path']}...", end=' ')
        start = time.time()
        
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=120)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json={}, timeout=120)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        elapsed = time.time() - start
        
        if response.status_code < 500:  # Accept 2xx, 3xx, 4xx (not 5xx)
            print(f"✅ ({response.status_code}) [{elapsed:.2f}s]")
            return True
        else:
            print(f"⚠️  ({response.status_code}) [{elapsed:.2f}s]")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Run server warm-up"""
    print("\n" + "="*60)
    print("🚀 PANN Back Office - Server Warm-up")
    print("="*60)
    print(f"Target: {BASE_URL}")
    print(f"Endpoints to warm: {len(WARMUP_ENDPOINTS)}")
    
    if WARMUP_TOKEN:
        print(f"Auth: Using provided token")
    else:
        print(f"Auth: No token (authenticated endpoints will be skipped)")
    
    print("="*60 + "\n")
    
    success_count = 0
    start_time = time.time()
    
    for endpoint in WARMUP_ENDPOINTS:
        if warmup_endpoint(endpoint):
            success_count += 1
        time.sleep(0.5)  # Small delay between requests
    
    total_time = time.time() - start_time
    
    print("\n" + "="*60)
    print(f"✨ Warm-up Complete!")
    print(f"Success: {success_count}/{len(WARMUP_ENDPOINTS)} endpoints")
    print(f"Total time: {total_time:.2f}s")
    print("="*60 + "\n")
    
    return success_count == len(WARMUP_ENDPOINTS)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

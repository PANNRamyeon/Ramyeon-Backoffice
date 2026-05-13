"""
init_pos_pages.py
-----------------
Prepares DynamoDB for POS Pages:
  1. Initializes the pos_pages counter under COUNTERS
  2. Verifies the PAGES partition is reachable
  3. Optionally creates a sample page for testing

Run from the backend/ directory:
    python init_pos_pages.py
    python init_pos_pages.py --sample   # also creates a sample page
"""
import os
import sys
import django
import argparse

# Bootstrap Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# PynamoDB uses boto3's standard credential chain and does not read .env directly.
# Load AWS credentials from .env into the environment before django.setup()
# so boto3 can find them via the environment variable provider.
try:
    from decouple import config as _env
    os.environ.setdefault('AWS_ACCESS_KEY_ID',     _env('AWS_ACCESS_KEY_ID', default=''))
    os.environ.setdefault('AWS_SECRET_ACCESS_KEY', _env('AWS_SECRET_ACCESS_KEY', default=''))
    os.environ.setdefault('AWS_DEFAULT_REGION',    _env('AWS_REGION_NAME', default='ap-southeast-1'))
except Exception as _e:
    print(f"[WARN] Could not load credentials from .env: {_e}")

django.setup()

from app.utils.counters import counter_service
from models.PosPage import PosPage


def init_counter():
    print("\n[1] Initializing pos_pages counter...")
    try:
        current_val = counter_service.initialize_counter('pos_pages', 'PAGE', 2)
        print(f"    [OK] Counter ready — next ID will be PAGE-{str(current_val + 1).zfill(2)}")
        return True
    except Exception as e:
        print(f"    [ERROR] {e}")
        return False


def verify_partition():
    print("\n[2] Verifying PAGES partition...")
    try:
        pages = PosPage.get_all_pages()
        print(f"    [OK] PAGES partition reachable — {len(pages)} page(s) found")
        for p in pages:
            print(f"         • {p.sk}: '{p.page_name}'  icon={p.icon}  products={len(p.product_ids or [])}")
        return True
    except Exception as e:
        print(f"    [ERROR] {e}")
        return False


def create_sample_page():
    print("\n[3] Creating sample page...")
    try:
        page = PosPage.create_page(page_name="Bestsellers", icon="ShoppingBag")
        print(f"    [OK] Created: {page.sk} — '{page.page_name}'")
        print(f"         Add products via:  POST /api/v1/admin/pos-pages/{page.sk}/products/")
        return page
    except Exception as e:
        print(f"    [ERROR] {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize POS Pages in DynamoDB")
    parser.add_argument("--sample", action="store_true", help="Create a sample page for testing")
    args = parser.parse_args()

    print("=" * 50)
    print("  POS Pages — DynamoDB Setup")
    print("=" * 50)

    counter_ok = init_counter()
    if not counter_ok:
        print("\nAborting — counter initialization failed.")
        sys.exit(1)

    verify_partition()

    if args.sample:
        create_sample_page()

    print("\nDone.")

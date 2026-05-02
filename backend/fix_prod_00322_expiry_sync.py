"""
One-off stock sync for PROD-00322.

Recomputes total_stock, oldest_batch_expiry, newest_batch_expiry, and
expiry_alert from the product's live batch data and writes the corrected
values back to DynamoDB.

Usage (from backend/):
    python fix_prod_00322_expiry_sync.py           # apply fix
    python fix_prod_00322_expiry_sync.py --dry-run # preview only
"""

import os
import sys
import argparse
from datetime import datetime, timedelta, timezone

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_BASE_DIR)

# Load .env into os.environ BEFORE django.setup() so PynamoDB picks up
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / DYNAMO_TABLE_NAME etc.
from dotenv import load_dotenv
load_dotenv(os.path.join(_BASE_DIR, ".env"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from models.Product import Product
from models.Batches import Batch

PRODUCT_ID = "PROD-00322"
EXPIRY_ALERT_DAYS = 30

# Statuses whose quantity counts toward live stock and whose expiry dates
# are considered when computing oldest/newest batch expiry on the product.
ACTIVE_STATUSES = {"active", "low_stock", "expiring_soon"}


def _utc_now():
    return datetime.now(timezone.utc)


def _normalize(dt):
    """Make datetime timezone-aware (assume UTC if naive)."""
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def compute_sync_values(batches: list) -> dict:
    """
    Derive the correct product-level values from its batch list.

    Only batches in ACTIVE_STATUSES with quantity_remaining > 0 and
    not past their expiry date contribute to stock and expiry windows.
    """
    now = _utc_now()
    total_stock = 0
    expiry_dates = []

    for batch in batches:
        if batch.status not in ACTIVE_STATUSES:
            continue
        if batch.quantity_remaining <= 0:
            continue
        # Skip physically expired batches even if status hasn't been updated yet.
        if batch.expiry_date and _normalize(batch.expiry_date) < now:
            continue

        total_stock += int(batch.quantity_remaining)

        if batch.expiry_date:
            expiry_dates.append(_normalize(batch.expiry_date))

    oldest = min(expiry_dates).date().isoformat() if expiry_dates else None
    newest = max(expiry_dates).date().isoformat() if expiry_dates else None

    expiry_alert = False
    if oldest:
        cutoff = (now + timedelta(days=EXPIRY_ALERT_DAYS)).date().isoformat()
        expiry_alert = oldest <= cutoff

    return {
        "total_stock": total_stock,
        "oldest_batch_expiry": oldest,
        "newest_batch_expiry": newest,
        "expiry_alert": expiry_alert,
    }


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description=f"Expiry sync for {PRODUCT_ID}")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to DynamoDB",
    )
    args = parser.parse_args()

    print_section(f"EXPIRY SYNC — {PRODUCT_ID}")
    if args.dry_run:
        print("  [DRY RUN] No changes will be written.\n")

    # ── 1. Fetch product ──────────────────────────────────────────────
    product = Product.get_by_id(PRODUCT_ID)
    if not product:
        print(f"ERROR: {PRODUCT_ID} not found or is soft-deleted.")
        sys.exit(1)

    print(f"\nProduct : {product.product_name}")
    print(f"SKU     : {product.SKU}")
    print(f"Status  : {product.status}")

    # ── 2. Fetch all batches for this product ────────────────────────
    batches = Batch.get_by_product_id(PRODUCT_ID)
    print(f"\nTotal batches found : {len(batches)}")

    if not batches:
        print("WARNING: No batches found. Nothing to sync.")
        sys.exit(0)

    # ── 3. Print batch summary ────────────────────────────────────────
    print("\n  Batch breakdown:")
    print(f"  {'Batch ID':<22} {'Status':<16} {'Remaining':>10} {'Expiry'}")
    print(f"  {'-'*22} {'-'*16} {'-'*10} {'-'*12}")
    for b in sorted(batches, key=lambda x: x.sk):
        expiry_str = b.expiry_date.date().isoformat() if b.expiry_date else "no expiry"
        print(f"  {b.sk:<22} {b.status:<16} {int(b.quantity_remaining):>10} {expiry_str}")

    # ── 4. Compute corrected values ───────────────────────────────────
    corrected = compute_sync_values(batches)

    # ── 5. Compare against current product values ─────────────────────
    print_section("Current vs Corrected")
    fields = [
        ("total_stock",          product.total_stock,           corrected["total_stock"]),
        ("oldest_batch_expiry",  product.oldest_batch_expiry,   corrected["oldest_batch_expiry"]),
        ("newest_batch_expiry",  product.newest_batch_expiry,   corrected["newest_batch_expiry"]),
        ("expiry_alert",         product.expiry_alert,          corrected["expiry_alert"]),
    ]

    needs_update = False
    for field, current, new in fields:
        status = "DIFFERS" if str(current) != str(new) else "ok"
        if status == "DIFFERS":
            needs_update = True
        print(f"  {field:<24} current={str(current):<16} corrected={str(new):<16} [{status}]")

    if not needs_update:
        print("\n  Product is already in sync. No changes needed.")
        sys.exit(0)

    # ── 6. Apply fix ──────────────────────────────────────────────────
    print_section("Applying Fix" if not args.dry_run else "Dry-Run Summary")

    if args.dry_run:
        print("  Would write the following values to DynamoDB:")
        for field, _, new in fields:
            print(f"    {field} = {new}")
        print("\n  Run without --dry-run to apply.")
        sys.exit(0)

    try:
        # Update expiry fields via the model's dedicated method.
        product.update_expiry_info(
            oldest_expiry=corrected["oldest_batch_expiry"],
            newest_expiry=corrected["newest_batch_expiry"],
        )

        # Sync total_stock using set_total_stock_absolute which handles
        # optimistic locking and status recalculation automatically.
        product.set_total_stock_absolute(
            new_total_stock=corrected["total_stock"],
            source="fix_script",
            reason="Manual expiry/stock sync for PROD-00322",
            oldest_expiry=corrected["oldest_batch_expiry"],
            newest_expiry=corrected["newest_batch_expiry"],
        )

        print(f"  ✓ {PRODUCT_ID} updated successfully.")
        print(f"    total_stock         = {corrected['total_stock']}")
        print(f"    oldest_batch_expiry = {corrected['oldest_batch_expiry']}")
        print(f"    newest_batch_expiry = {corrected['newest_batch_expiry']}")
        print(f"    expiry_alert        = {corrected['expiry_alert']}")

    except Exception as exc:
        print(f"  ✗ Update failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print_section("Done")


if __name__ == "__main__":
    main()

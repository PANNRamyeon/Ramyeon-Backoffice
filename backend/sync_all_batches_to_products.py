"""
System-wide batch → product sync script.

For every non-deleted product in the database this script:

  PASS 1 — Fix stale batch statuses
    Each non-pending batch has its status recalculated from live
    quantity_remaining and expiry_date and saved if it has drifted
    (e.g. a batch that expired but is still marked "active").

  PASS 2 — Sync product fields from corrected batches
    Re-derives the following product fields from the product's
    batch set and updates the product if anything differs:

      • total_stock          — sum of quantity_remaining for usable batches
      • oldest_batch_expiry  — earliest expiry among usable batches
      • newest_batch_expiry  — latest  expiry among usable batches
      • expiry_alert         — True when oldest expiry is ≤ 30 days away
      • status               — out_of_stock / low_stock / active
                               (only when currently one of those three;
                                discontinued / deleted are left untouched)
      • pos_sync_status      — set to "pending" whenever any field changes

Usage (run from backend/ with venv active):
    python sync_all_batches_to_products.py               # apply all fixes
    python sync_all_batches_to_products.py --dry-run     # preview only
    python sync_all_batches_to_products.py --product-id PROD-00322
    python sync_all_batches_to_products.py --skip-batch-status-fix
"""

import os
import sys
import argparse
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_BASE_DIR)

# ── Load .env before Django / PynamoDB try to read AWS creds ──────────
from dotenv import load_dotenv
load_dotenv(os.path.join(_BASE_DIR, ".env"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from models.Product import Product
from models.Batches import Batch
from pynamodb.exceptions import UpdateError
import boto3
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION

# ── Constants ─────────────────────────────────────────────────────────
USABLE_STATUSES = {"active", "low_stock", "expiring_soon"}
MANAGEABLE_PRODUCT_STATUSES = {"active", "low_stock", "out_of_stock"}
EXPIRY_ALERT_DAYS = 30


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _utc_now():
    return datetime.now(timezone.utc)


def _normalize(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _expiry_iso(dt) -> Optional[str]:
    """Return bare date ISO string (YYYY-MM-DD) from a datetime, or None."""
    if dt is None:
        return None
    try:
        return _normalize(dt).date().isoformat()
    except Exception:
        return None


def _recalculate_batch_status(batch) -> str:
    """
    Pure recalculation of what a batch's status *should* be right now.
    Mirrors Batch._calculate_and_set_status() but returns the value
    instead of mutating the object.
    """
    if batch.status == "pending":
        return "pending"  # pending batches are managed by shipment workflow

    now = _utc_now()

    if batch.expiry_date and now > _normalize(batch.expiry_date):
        return "expired"

    if int(batch.quantity_remaining or 0) <= 0:
        return "exhausted"

    received = int(batch.quantity_received or 0)
    if received > 0:
        pct = int(batch.quantity_remaining) / received
        if pct <= 0.10:
            return "low_stock"

    if batch.expiry_date:
        days = (_normalize(batch.expiry_date) - now).days
        if 0 <= days <= 7:
            return "expiring_soon"

    return "active"


def _compute_product_fields(batches: list) -> dict:
    """
    Derive the correct product-level values from a product's full batch list.
    Only batches in USABLE_STATUSES with quantity > 0 that aren't physically
    expired contribute to the totals.
    """
    now = _utc_now()
    total_stock = 0
    expiry_dates = []
    cost_prices = []

    for b in batches:
        if b.status not in USABLE_STATUSES:
            continue
        qty = int(b.quantity_remaining or 0)
        if qty <= 0:
            continue
        if b.expiry_date and _normalize(b.expiry_date) < now:
            continue

        total_stock += qty

        if b.expiry_date:
            expiry_dates.append(_normalize(b.expiry_date))

        cost = float(b.cost_price or 0)
        if cost > 0:
            cost_prices.append((cost, qty))

    oldest_expiry = _expiry_iso(min(expiry_dates)) if expiry_dates else None
    newest_expiry = _expiry_iso(max(expiry_dates)) if expiry_dates else None

    expiry_alert = False
    if oldest_expiry:
        cutoff = (_utc_now() + timedelta(days=EXPIRY_ALERT_DAYS)).date().isoformat()
        expiry_alert = oldest_expiry <= cutoff

    # Weighted average cost price from active batch quantities
    avg_cost = None
    if cost_prices:
        total_qty = sum(q for _, q in cost_prices)
        if total_qty > 0:
            avg_cost = round(sum(c * q for c, q in cost_prices) / total_qty, 4)

    return {
        "total_stock": total_stock,
        "oldest_batch_expiry": oldest_expiry,
        "newest_batch_expiry": newest_expiry,
        "expiry_alert": expiry_alert,
        "average_cost_price": avg_cost,   # None means "no change needed"
    }


def _desired_product_status(product, new_total_stock: int) -> str:
    """
    Return the status the product *should* have given the new stock figure.
    Only touches statuses in MANAGEABLE_PRODUCT_STATUSES; everything else
    (discontinued, deleted, etc.) is left as-is.
    """
    current = product.status
    if current not in MANAGEABLE_PRODUCT_STATUSES:
        return current  # don't touch discontinued / deleted

    if new_total_stock == 0:
        return "out_of_stock"
    threshold = int(product.low_stock_threshold or 0)
    if threshold > 0 and new_total_stock <= threshold:
        return "low_stock"
    return "active"


def _fields_differ(product, computed: dict) -> dict:
    """
    Return a dict of {field: (current, corrected)} for every field that
    would change.  average_cost_price is only included when the product
    model actually has that attribute AND the value differs.
    """
    diffs = {}

    def _check(attr, new_val):
        current = getattr(product, attr, None)
        # Normalise for comparison
        cur_str = str(current) if current is not None else None
        new_str = str(new_val) if new_val is not None else None
        if cur_str != new_str:
            diffs[attr] = (current, new_val)

    _check("total_stock",          computed["total_stock"])
    _check("oldest_batch_expiry",  computed["oldest_batch_expiry"])
    _check("newest_batch_expiry",  computed["newest_batch_expiry"])
    _check("expiry_alert",         computed["expiry_alert"])

    desired_status = _desired_product_status(product, computed["total_stock"])
    if product.status != desired_status:
        diffs["status"] = (product.status, desired_status)

    # average_cost_price only if the model has it and the value changed
    if computed["average_cost_price"] is not None and hasattr(product, "average_cost_price"):
        avg = computed["average_cost_price"]
        current_avg = getattr(product, "average_cost_price", None)
        try:
            if round(float(current_avg or 0), 4) != avg:
                diffs["average_cost_price"] = (current_avg, avg)
        except (TypeError, ValueError):
            diffs["average_cost_price"] = (current_avg, avg)

    return diffs


def _apply_product_update(product, diffs: dict, dry_run: bool) -> bool:
    """Write the diffs to the product. Returns True on success."""
    if not diffs or dry_run:
        return True
    for field, (_, new_val) in diffs.items():
        setattr(product, field, new_val)
    if diffs:
        product.pos_sync_status = "pending"
        product.updated_at = datetime.utcnow()

    # Try optimistic-lock save first; fall back to direct boto3 write
    try:
        current_version = getattr(product, "version", None) or 0
        product.version = current_version + 1
        if current_version == 0:
            condition = (Product.version.does_not_exist()) | (Product.version == 0)
        else:
            condition = Product.version == current_version
        product.save(condition=condition)
        return True
    except UpdateError:
        pass
    except Exception:
        pass

    # Direct boto3 fallback
    try:
        _direct_update_product(product.sk, diffs)
        return True
    except Exception:
        return False


def _direct_update_product(product_sk: str, diffs: dict):
    """Raw DynamoDB update when PynamoDB optimistic lock fails."""
    client = boto3.client("dynamodb", region_name=AWS_REGION)
    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"
    parts, names, values = [], {}, {}

    field_type_map = {
        "total_stock":          ("N", lambda v: str(int(v))),
        "oldest_batch_expiry":  ("S", str),
        "newest_batch_expiry":  ("S", str),
        "expiry_alert":         ("BOOL", lambda v: bool(v)),
        "status":               ("S", str),
        "average_cost_price":   ("N", lambda v: str(float(v))),
    }

    for field, (_, new_val) in diffs.items():
        if field not in field_type_map:
            continue
        ddb_type, converter = field_type_map[field]
        placeholder = f":f_{field}"
        name_token  = f"#f_{field}"
        parts.append(f"{name_token} = {placeholder}")
        names[name_token] = field
        if new_val is None:
            values[placeholder] = {"NULL": True}
        elif ddb_type == "BOOL":
            values[placeholder] = {"BOOL": converter(new_val)}
        else:
            values[placeholder] = {ddb_type: converter(new_val)}

    parts.append("#upd = :upd")
    parts.append("#pss = :pss")
    names["#upd"] = "updated_at"
    names["#pss"] = "pos_sync_status"
    values[":upd"] = {"S": now_str}
    values[":pss"] = {"S": "pending"}

    client.update_item(
        TableName=DYNAMO_TABLE_NAME,
        Key={"PK": {"S": "products"}, "SK": {"S": product_sk}},
        UpdateExpression="SET " + ", ".join(parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


# ══════════════════════════════════════════════════════════════════════
# Core per-product sync
# ══════════════════════════════════════════════════════════════════════

def sync_product(product, dry_run: bool, fix_batch_status: bool) -> dict:
    """
    Sync one product.  Returns a result dict:
      { ok, batches_fixed, product_updated, diffs, error }
    """
    result = {
        "ok": False,
        "batches_fixed": 0,
        "product_updated": False,
        "diffs": {},
        "error": None,
    }
    product_id = product.sk

    try:
        batches = list(Batch.get_by_product_id(product_id, limit=500))
    except Exception as e:
        result["error"] = f"batch fetch failed: {e}"
        return result

    # ── Pass 1: fix stale batch statuses ──────────────────────────────
    if fix_batch_status:
        for batch in batches:
            if batch.status == "pending":
                continue  # managed by shipment workflow — never touch
            correct_status = _recalculate_batch_status(batch)
            if batch.status == correct_status:
                continue
            if not dry_run:
                try:
                    original_updated_at = batch.updated_at
                    batch.status = correct_status
                    batch.updated_at = datetime.utcnow()
                    condition = (
                        (Batch.pk == batch.pk) &
                        (Batch.sk == batch.sk) &
                        (Batch.updated_at == original_updated_at)
                    )
                    batch.save(condition=condition)
                    result["batches_fixed"] += 1
                except UpdateError:
                    # Concurrent update: re-read and retry once
                    try:
                        fresh = Batch.get_by_id(batch.sk)
                        if fresh and _recalculate_batch_status(fresh) != fresh.status:
                            fresh.status = _recalculate_batch_status(fresh)
                            fresh.updated_at = datetime.utcnow()
                            fresh.save()
                            # Refresh local reference so product sync uses corrected status
                            for i, b in enumerate(batches):
                                if b.sk == fresh.sk:
                                    batches[i] = fresh
                                    break
                            result["batches_fixed"] += 1
                    except Exception:
                        pass
                except Exception:
                    pass
            else:
                result["batches_fixed"] += 1  # dry-run counts as "would fix"

    # ── Pass 2: recompute product fields ──────────────────────────────
    computed = _compute_product_fields(batches)
    diffs = _fields_differ(product, computed)

    if not diffs:
        result["ok"] = True
        return result

    result["diffs"] = diffs

    success = _apply_product_update(product, diffs, dry_run)
    result["ok"] = success
    result["product_updated"] = success and not dry_run
    return result


# ══════════════════════════════════════════════════════════════════════
# Pagination helpers
# ══════════════════════════════════════════════════════════════════════

def iter_all_products(single_product_id: Optional[str] = None):
    """Yield all non-deleted product objects (paginated)."""
    if single_product_id:
        p = Product.get_by_id(single_product_id, include_deleted=False)
        if p:
            yield p
        return

    last_key = None
    while True:
        kwargs = {
            "filter_condition": Product.isDeleted == False,
            "limit": 100,
        }
        if last_key:
            kwargs["last_evaluated_key"] = last_key
        try:
            it = Product.query("products", **kwargs)
            for product in it:
                yield product
            last_key = getattr(it, "last_evaluated_key", None)
        except Exception as e:
            print(f"\n  [ERROR] Pagination failed: {e}")
            break
        if not last_key:
            break


# ══════════════════════════════════════════════════════════════════════
# Reporting helpers
# ══════════════════════════════════════════════════════════════════════

FIELD_LABELS = {
    "total_stock":         "total_stock",
    "oldest_batch_expiry": "oldest_batch_expiry",
    "newest_batch_expiry": "newest_batch_expiry",
    "expiry_alert":        "expiry_alert",
    "status":              "status",
    "average_cost_price":  "average_cost_price",
}

def _fmt_diff(field, cur, new) -> str:
    label = FIELD_LABELS.get(field, field)
    return f"    {label:<24} {str(cur):<20} → {str(new)}"


def _print_section(title: str):
    print(f"\n{'═' * 64}")
    print(f"  {title}")
    print("═" * 64)


# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="System-wide batch → product sync"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing to DynamoDB")
    parser.add_argument("--product-id", metavar="PROD-XXXXX",
                        help="Run for a single product only")
    parser.add_argument("--skip-batch-status-fix", action="store_true",
                        help="Skip Pass 1 (batch status recalculation)")
    args = parser.parse_args()

    dry_run           = args.dry_run
    single_id         = args.product_id
    fix_batch_status  = not args.skip_batch_status_fix

    _print_section("SYSTEM-WIDE BATCH → PRODUCT SYNC" + (" [DRY RUN]" if dry_run else ""))
    print(f"  Batch status fix : {'yes' if fix_batch_status else 'skipped'}")
    print(f"  Target           : {single_id or 'all non-deleted products'}")
    print(f"  Started          : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")

    counters = {
        "products_checked":  0,
        "products_updated":  0,
        "products_would_update": 0,
        "products_already_ok":   0,
        "products_errored":  0,
        "batches_fixed":     0,
    }
    changed_products = []
    errored_products = []
    start_time = time.time()

    for product in iter_all_products(single_id):
        counters["products_checked"] += 1
        pid = product.sk
        name = getattr(product, "product_name", "?")

        result = sync_product(product, dry_run, fix_batch_status)
        counters["batches_fixed"] += result["batches_fixed"]

        if result["error"]:
            counters["products_errored"] += 1
            errored_products.append((pid, name, result["error"]))
            print(f"  ✗ {pid:<14} {name[:40]:<42}  ERROR: {result['error']}")
            continue

        if not result["diffs"] and result["batches_fixed"] == 0:
            counters["products_already_ok"] += 1
            print(f"  · {pid:<14} {name[:40]:<42}  ok")
            continue

        if result["diffs"]:
            if dry_run:
                counters["products_would_update"] += 1
                print(f"  ~ {pid:<14} {name[:40]:<42}  WOULD UPDATE")
            else:
                if result["product_updated"]:
                    counters["products_updated"] += 1
                    print(f"  ✓ {pid:<14} {name[:40]:<42}  updated")
                else:
                    counters["products_errored"] += 1
                    errored_products.append((pid, name, "update write failed"))
                    print(f"  ✗ {pid:<14} {name[:40]:<42}  write failed")

            changed_products.append((pid, name, result))
        elif result["batches_fixed"] > 0:
            label = f"  ✓ {pid:<14} {name[:40]:<42}  {result['batches_fixed']} batch(es) fixed"
            print(label)

    # ── Detailed diff report ─────────────────────────────────────────
    if changed_products:
        _print_section("CHANGE DETAILS")
        for pid, name, result in changed_products:
            print(f"\n  {pid}  {name}")
            if result["batches_fixed"]:
                verb = "would fix" if dry_run else "fixed"
                print(f"    batch statuses : {result['batches_fixed']} {verb}")
            if result["diffs"]:
                print(f"    {'field':<24} {'current':<20}   corrected")
                print(f"    {'-'*24} {'-'*20}   {'-'*20}")
                for field, (cur, new) in result["diffs"].items():
                    print(_fmt_diff(field, cur, new))

    # ── Error summary ────────────────────────────────────────────────
    if errored_products:
        _print_section("ERRORS")
        for pid, name, err in errored_products:
            print(f"  {pid}  {name}  —  {err}")

    # ── Final summary ────────────────────────────────────────────────
    elapsed = time.time() - start_time
    _print_section("SUMMARY")
    print(f"  Products checked        : {counters['products_checked']}")
    print(f"  Already in sync         : {counters['products_already_ok']}")
    if dry_run:
        print(f"  Would update (dry-run)  : {counters['products_would_update']}")
    else:
        print(f"  Products updated        : {counters['products_updated']}")
    print(f"  Batch statuses fixed    : {counters['batches_fixed']}")
    print(f"  Errors                  : {counters['products_errored']}")
    print(f"  Elapsed                 : {elapsed:.1f}s")
    if dry_run:
        print("\n  Run without --dry-run to apply all changes.")
    print()


if __name__ == "__main__":
    main()

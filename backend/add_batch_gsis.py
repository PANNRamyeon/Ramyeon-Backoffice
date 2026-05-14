"""
Adds the batch-product-id-index GSI to RamyeonCornerDB.

  Index name : batch-product-id-index
  Hash key   : product_id  (S)
  Range key  : SK           (S)
  Projection : ALL  ← every attribute (stock, expiry, cost, status …)
                      is copied into the index

DynamoDB will backfill all existing batch items automatically.
The script waits (polling every 15 s) until the index reaches ACTIVE.

Usage (from backend/ with venv active):
    python add_batch_gsis.py           # create the GSI
    python add_batch_gsis.py --dry-run # preview only, no writes
"""

import os
import sys
import time
import argparse

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BASE_DIR, ".env"))

import boto3
from decouple import config

TABLE_NAME = config("DYNAMO_TABLE_NAME", default="RamyeonCornerDB")
REGION     = config("AWS_REGION_NAME",   default="ap-southeast-1")

INDEX_NAME  = "batch-product-id-index"
HASH_KEY    = "product_id"   # attribute name on every batch item
RANGE_KEY   = "SK"           # table sort key — already an AttributeDefinition

POLL_INTERVAL = 15    # seconds between status checks
TIMEOUT       = 900   # 15 minutes max (large tables take longer to backfill)


def get_client():
    return boto3.client(
        "dynamodb",
        region_name=REGION,
        aws_access_key_id=config("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY"),
    )


def describe_table(client) -> dict:
    return client.describe_table(TableName=TABLE_NAME)["Table"]


def existing_gsi_names(table_desc: dict) -> set:
    return {g["IndexName"] for g in table_desc.get("GlobalSecondaryIndexes", [])}


def existing_attr_names(table_desc: dict) -> set:
    return {a["AttributeName"] for a in table_desc.get("AttributeDefinitions", [])}


def is_pay_per_request(table_desc: dict) -> bool:
    return (
        table_desc.get("BillingModeSummary", {}).get("BillingMode")
        == "PAY_PER_REQUEST"
    )


def print_section(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print("═" * 60)


def main():
    parser = argparse.ArgumentParser(description=f"Add {INDEX_NAME} to {TABLE_NAME}")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without writing anything")
    args = parser.parse_args()

    print_section("ADD batch-product-id-index" + (" [DRY RUN]" if args.dry_run else ""))

    # ── Connect & describe ────────────────────────────────────────────
    try:
        client     = get_client()
        table_desc = describe_table(client)
    except Exception as e:
        print(f"\n  ERROR: Cannot reach DynamoDB — {e}")
        sys.exit(1)

    mode   = "PAY_PER_REQUEST" if is_pay_per_request(table_desc) else "PROVISIONED"
    status = table_desc.get("TableStatus", "?")
    print(f"\n  Table   : {TABLE_NAME}  [{status}]")
    print(f"  Region  : {REGION}")
    print(f"  Billing : {mode}")

    existing_gsис = existing_gsi_names(table_desc)
    print(f"\n  Existing GSIs:")
    for name in sorted(existing_gsис):
        gsi_status = next(
            (g.get("IndexStatus", "?") for g in table_desc.get("GlobalSecondaryIndexes", [])
             if g["IndexName"] == name),
            "?"
        )
        print(f"    • {name}  [{gsi_status}]")

    # ── Already exists? ───────────────────────────────────────────────
    if INDEX_NAME in existing_gsис:
        current = next(
            g for g in table_desc.get("GlobalSecondaryIndexes", [])
            if g["IndexName"] == INDEX_NAME
        )
        print(f"\n  ✓ {INDEX_NAME} already exists  [{current.get('IndexStatus', '?')}]")
        print("  Nothing to do.")
        sys.exit(0)

    # ── Table must be ACTIVE before UpdateTable ───────────────────────
    if status != "ACTIVE":
        print(f"\n  ERROR: Table status is '{status}' — must be ACTIVE before adding a GSI.")
        sys.exit(1)

    # ── Build UpdateTable params ──────────────────────────────────────
    # UpdateTable requires AttributeDefinitions to include EVERY attribute
    # referenced in the new index's KeySchema — even ones already declared
    # on the table (like SK).  We always pass both explicitly.
    new_attr_defs = [
        {"AttributeName": HASH_KEY,  "AttributeType": "S"},   # product_id — new
        {"AttributeName": RANGE_KEY, "AttributeType": "S"},   # SK         — already exists, must re-declare
    ]

    gsi_create = {
        "IndexName": INDEX_NAME,
        "KeySchema": [
            {"AttributeName": HASH_KEY,  "KeyType": "HASH"},
            {"AttributeName": RANGE_KEY, "KeyType": "RANGE"},
        ],
        "Projection": {"ProjectionType": "ALL"},
    }
    if mode == "PROVISIONED":
        gsi_create["ProvisionedThroughput"] = {
            "ReadCapacityUnits":  5,
            "WriteCapacityUnits": 5,
        }

    print_section("PLAN")
    print(f"  IndexName  : {INDEX_NAME}")
    print(f"  Hash key   : {HASH_KEY}  (S)")
    print(f"  Range key  : {RANGE_KEY}  (S)")
    print(f"  Projection : ALL  — every attribute copied into the index")
    if mode == "PROVISIONED":
        print(f"  Throughput : 5 RCU / 5 WCU")
    print(f"  AttributeDefinitions  : {HASH_KEY} (S), {RANGE_KEY} (S)  [required by UpdateTable]")

    if args.dry_run:
        print("\n  Dry-run complete. Run without --dry-run to apply.")
        sys.exit(0)

    # ── Apply ─────────────────────────────────────────────────────────
    print_section("CREATING INDEX")
    print("  Calling UpdateTable …")

    try:
        client.update_table(
            TableName=TABLE_NAME,
            GlobalSecondaryIndexUpdates=[{"Create": gsi_create}],
            AttributeDefinitions=new_attr_defs,
        )
        print("  UpdateTable accepted ✓")
    except client.exceptions.ResourceInUseException:
        print("  ⚠  Table is busy (ResourceInUseException).")
        print("     Another operation is in progress — wait and re-run.")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # ── Wait for ACTIVE ───────────────────────────────────────────────
    print(f"\n  Waiting for index to reach ACTIVE …")
    print(f"  (DynamoDB backfills existing items — this can take several minutes)\n")

    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            desc    = describe_table(client)
            gsi_map = {g["IndexName"]: g for g in desc.get("GlobalSecondaryIndexes", [])}
        except Exception as e:
            print(f"  poll error: {e}")
            continue

        if INDEX_NAME not in gsi_map:
            print(f"  [{time.strftime('%H:%M:%S')}]  {INDEX_NAME}  CREATING …")
            continue

        idx_status = gsi_map[INDEX_NAME].get("IndexStatus", "?")
        item_count = gsi_map[INDEX_NAME].get("ItemCount", "?")
        print(f"  [{time.strftime('%H:%M:%S')}]  {INDEX_NAME}  {idx_status}  (items: {item_count})")

        if idx_status == "ACTIVE":
            break
    else:
        print(f"\n  ⚠  Timed out after {TIMEOUT}s. The index is still building.")
        print("     Re-run this script to check — it will skip creation if the index exists.")
        sys.exit(1)

    print_section("DONE")
    print(f"  ✓ {INDEX_NAME} is ACTIVE and ready.")
    print("  The batch-product fallback warning will no longer appear.\n")


if __name__ == "__main__":
    main()

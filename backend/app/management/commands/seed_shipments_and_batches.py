"""
Seed Shipments and Batches for testing (DynamoDB).

Creates 10 shipments with 5 batches each (50 batches total).
Suppliers are hardcoded; products are discovered from DynamoDB (first 5 non-deleted).

- Shipment 1 → SUPP-007, batches for the 5 discovered products
- Shipment 2 → SUPP-008, same 5 products
- ... (suppliers cycle: SUPP-007..SUPP-016, then repeat)
- Shipment 10 → SUPP-009

Usage:
    python manage.py seed_shipments_and_batches --yes-i-am-sure

Dry run (no DB writes, validates products/suppliers):
    python manage.py seed_shipments_and_batches --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
import logging

import boto3

from app.utils.singleton import get_singleton
from app.services.inventory.shipment_service import ShipmentService
from app.services.inventory.batch_service import BatchService
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION

logger = logging.getLogger(__name__)

# Hardcoded: suppliers in order; shipment i uses supplier at index (i % 7)
HARDCODED_SUPPLIER_IDS = [
    "SUPP-007",
    "SUPP-008",
    "SUPP-009",
    "SUPP-011",
    "SUPP-014",
    "SUPP-015",
    "SUPP-016",
]

BATCHES_PER_SHIPMENT = 5
NUM_SHIPMENTS = 10
MIN_PRODUCTS_NEEDED = 5


def _get_product_cost(ddb, product_id: str) -> float:
    """Read cost_price from product item via raw DynamoDB; avoid PynamoDB datetime issues."""
    try:
        resp = ddb.get_item(
            TableName=DYNAMO_TABLE_NAME,
            Key={"PK": {"S": "products"}, "SK": {"S": product_id}},
            ProjectionExpression="cost_price",
        )
        item = resp.get("Item") or {}
        cost_attr = item.get("cost_price")
        if cost_attr and "N" in cost_attr:
            return float(cost_attr["N"])
    except Exception:
        pass
    return 100.0


def _discover_product_ids(ddb, needed: int = MIN_PRODUCTS_NEEDED):
    """Query DynamoDB for existing, non-deleted products; return up to `needed` IDs (sorted)."""
    product_ids = []
    last_key = None
    while True:
        kwargs = {
            "TableName": DYNAMO_TABLE_NAME,
            "KeyConditionExpression": "PK = :pk",
            "ExpressionAttributeValues": {":pk": {"S": "products"}},
            "ProjectionExpression": "SK, isDeleted",
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        resp = ddb.query(**kwargs)
        for item in resp.get("Items", []):
            sk = (item.get("SK") or {}).get("S")
            if not sk:
                continue
            is_deleted = item.get("isDeleted", {}).get("BOOL", False)
            if is_deleted:
                continue
            product_ids.append(sk)
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
    product_ids.sort()
    if len(product_ids) < needed:
        raise CommandError(
            f"Found only {len(product_ids)} non-deleted product(s) in DynamoDB; need at least {needed}. "
            "Add or restore products first."
        )
    return product_ids[:needed]


class Command(BaseCommand):
    help = "Seed 10 shipments with 5 batches each (suppliers hardcoded; products discovered from DB)"

    def add_arguments(self, parser):
        parser.add_argument("--yes-i-am-sure", action="store_true", dest="confirm")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Validate products/suppliers and print what would be created; no DB writes.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")
        if not dry_run and not options.get("confirm"):
            raise CommandError(
                "Refusing to seed without --yes-i-am-sure. "
                "Run: python manage.py seed_shipments_and_batches --yes-i-am-sure"
            )

        num_shipments = NUM_SHIPMENTS
        batches_per_shipment = BATCHES_PER_SHIPMENT
        supplier_ids = list(HARDCODED_SUPPLIER_IDS)
        ddb = boto3.client("dynamodb", region_name=AWS_REGION)

        # Discover first 5 non-deleted products (no PynamoDB, so no datetime issues)
        product_ids = _discover_product_ids(ddb, needed=batches_per_shipment)

        # Validate all suppliers exist (raw DynamoDB)
        for sid in supplier_ids:
            try:
                resp = ddb.get_item(
                    TableName=DYNAMO_TABLE_NAME,
                    Key={"PK": {"S": "suppliers"}, "SK": {"S": sid}},
                    ConsistentRead=True,
                )
                if "Item" not in resp:
                    raise CommandError(f"Supplier {sid} not found in DynamoDB. Ensure suppliers exist.")
            except CommandError:
                raise
            except Exception as e:
                raise CommandError(f"Error checking supplier {sid}: {e}")

        if not dry_run:
            shipment_svc = get_singleton(ShipmentService)
            batch_svc = get_singleton(BatchService)

        self.stdout.write("=" * 60)
        self.stdout.write("SEEDING SHIPMENTS + BATCHES (hardcoded)" + (" [DRY RUN - no writes]" if dry_run else ""))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Shipments: {num_shipments}")
        self.stdout.write(f"Batches per shipment: {batches_per_shipment} (total {num_shipments * batches_per_shipment})")
        self.stdout.write(f"Products (discovered, first {batches_per_shipment}): {product_ids}")
        self.stdout.write(f"Suppliers (cycle): {supplier_ids}")
        self.stdout.write("")

        created_shipments = 0
        created_batches = 0
        now = datetime.utcnow()

        for si in range(num_shipments):
            supplier_id = supplier_ids[si % len(supplier_ids)]
            batch_number = f"LOT-{now.strftime('%Y%m%d')}-{str(si + 1).zfill(3)}"
            shipment_date = now - timedelta(days=si)  # predictable: ship 1 = today, ship 2 = 1 day ago, ...

            shipment_payload = {
                "supplier_id": supplier_id,
                "batch_number": batch_number,
                "shipment_date": shipment_date.isoformat(),
                "invoice_number": f"INV-{now.strftime('%Y%m%d')}-{str(si + 1).zfill(4)}",
                "status": "received",
                "freight_cost": 2000.0 + si * 500,
                "notes": "Seeded shipment for testing",
                "received_by": "seed_script",
            }

            if dry_run:
                shipment_id = "(would get new ID)"
                created_shipments += 1
                self.stdout.write(self.style.SUCCESS(f"Shipment {si + 1}: {shipment_id} (supplier {supplier_id})"))
            else:
                shipment_dict = shipment_svc.create_shipment(shipment_payload)
                shipment_id = shipment_dict.get("shipment_id")
                created_shipments += 1
                self.stdout.write(self.style.SUCCESS(f"Shipment {si + 1}: {shipment_id} (supplier {supplier_id})"))

            for pi, product_id in enumerate(product_ids):
                qty = 50 + (si * 5) + (pi * 2)  # predictable quantities
                cost = _get_product_cost(ddb, product_id)
                expiry = now + timedelta(days=90 + si * 10 + pi * 5)
                date_received = shipment_date

                if dry_run:
                    created_batches += 1
                    self.stdout.write(f"  - {product_id} qty={qty} cost={cost} (dry run)")
                else:
                    batch_payload = {
                        "product_id": product_id,
                        "batch_number": f"{batch_number}-{str(pi + 1).zfill(2)}",
                        "shipment_id": shipment_id,
                        "supplier_id": supplier_id,
                        "quantity_received": qty,
                        "quantity_remaining": qty,
                        "cost_price": cost,
                        "expiry_date": expiry,
                        "date_received": date_received,
                    }
                    batch_svc.create_batch(batch_payload)
                    created_batches += 1
                    self.stdout.write(f"  - {product_id} qty={qty} cost={cost}")

            self.stdout.write("")

        self.stdout.write("=" * 60)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. Would create {created_shipments} shipments, {created_batches} batches."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. Created {created_shipments} shipments, {created_batches} batches."))
        self.stdout.write("=" * 60)


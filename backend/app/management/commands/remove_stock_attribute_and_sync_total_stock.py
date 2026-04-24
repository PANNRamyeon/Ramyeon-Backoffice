"""
Remove legacy `stock` attribute from DynamoDB product items and sync `total_stock`
from non-expired batch quantities (sum of quantity_remaining).

Usage:
    python manage.py remove_stock_attribute_and_sync_total_stock --dry-run
    python manage.py remove_stock_attribute_and_sync_total_stock --yes-i-am-sure
"""

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime
import boto3
from decouple import config


def _parse_ddb_number(attr):
    if not isinstance(attr, dict):
        return None
    n = attr.get("N")
    if n is None:
        return None
    try:
        return float(n)
    except Exception:
        return None


def _parse_ddb_string(attr):
    if not isinstance(attr, dict):
        return None
    return attr.get("S")


def _is_batch_expired(batch_item: dict, now: datetime) -> bool:
    """
    expiry_date is stored as string like:
      2026-06-04T06:58:01.393943+0000
    """
    exp = _parse_ddb_string(batch_item.get("expiry_date"))
    if not exp:
        return False
    try:
        # Handle +0000 timezone format (no colon)
        if exp.endswith("+0000"):
            # with microseconds
            try:
                dt = datetime.strptime(exp, "%Y-%m-%dT%H:%M:%S.%f+0000")
            except ValueError:
                dt = datetime.strptime(exp, "%Y-%m-%dT%H:%M:%S+0000")
        else:
            # Best-effort fallback
            dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        return now > dt
    except Exception:
        # If we can't parse, treat as not expired (don't accidentally drop stock)
        return False


class Command(BaseCommand):
    help = "Remove legacy `stock` attribute and sync `total_stock` from batches (DynamoDB)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", dest="dry_run", help="No DB writes; print changes.")
        parser.add_argument(
            "--yes-i-am-sure",
            action="store_true",
            dest="confirm",
            help="Actually apply changes (required unless --dry-run).",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        if not dry_run and not options.get("confirm"):
            raise CommandError("Refusing to run without --yes-i-am-sure (or use --dry-run).")

        table_name = config("DYNAMO_TABLE_NAME", default="RamyeonCornerDB")
        region = config("AWS_REGION_NAME", default="ap-southeast-1")

        client = boto3.client(
            "dynamodb",
            region_name=region,
            aws_access_key_id=config("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY"),
        )

        now = datetime.utcnow()

        self.stdout.write("=" * 70)
        self.stdout.write("REMOVE `stock` + SYNC `total_stock` FROM BATCHES")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Table: {table_name}")
        self.stdout.write(f"Region: {region}")
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        self.stdout.write("")

        # Load all batches once, compute non-expired total remaining per product
        batch_totals: dict[str, int] = {}
        last_key = None
        while True:
            kwargs = {
                "TableName": table_name,
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": {"S": "batches"}},
                "ProjectionExpression": "product_id, quantity_remaining, #st, expiry_date",
                "ExpressionAttributeNames": {"#st": "status"},
            }
            if last_key:
                kwargs["ExclusiveStartKey"] = last_key
            resp = client.query(**kwargs)
            for b in resp.get("Items", []):
                pid = _parse_ddb_string(b.get("product_id"))
                if not pid:
                    continue
                status = _parse_ddb_string(b.get("status")) or ""
                if status in ("expired", "exhausted"):
                    continue
                if _is_batch_expired(b, now):
                    continue
                qr = _parse_ddb_number(b.get("quantity_remaining"))
                if qr is None or qr <= 0:
                    continue
                batch_totals[pid] = batch_totals.get(pid, 0) + int(qr)
            last_key = resp.get("LastEvaluatedKey")
            if not last_key:
                break

        # Iterate products and update
        scanned = 0
        updated = 0
        removed_stock_attr = 0
        last_key = None

        while True:
            kwargs = {
                "TableName": table_name,
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": {"S": "products"}},
                "ProjectionExpression": "SK, #stock, #ts",
                "ExpressionAttributeNames": {"#stock": "stock", "#ts": "total_stock"},
            }
            if last_key:
                kwargs["ExclusiveStartKey"] = last_key
            resp = client.query(**kwargs)

            for p in resp.get("Items", []):
                scanned += 1
                pid = _parse_ddb_string(p.get("SK"))
                if not pid:
                    continue

                has_stock_attr = "stock" in p
                current_total = _parse_ddb_number(p.get("total_stock")) or 0
                recomputed_total = int(batch_totals.get(pid, 0))

                needs_total_update = int(current_total) != int(recomputed_total)
                needs_remove_stock = has_stock_attr

                if not (needs_total_update or needs_remove_stock):
                    continue

                if dry_run:
                    self.stdout.write(
                        f"{pid}: total_stock {int(current_total)} -> {int(recomputed_total)}"
                        + (" | REMOVE stock" if needs_remove_stock else "")
                    )
                    updated += 1
                    if needs_remove_stock:
                        removed_stock_attr += 1
                    continue

                update_expr_parts = []
                expr_vals = {}
                expr_names = {}

                if needs_total_update:
                    update_expr_parts.append("#ts = :ts")
                    expr_names["#ts"] = "total_stock"
                    expr_vals[":ts"] = {"N": str(int(recomputed_total))}

                remove_expr = ""
                if needs_remove_stock:
                    remove_expr = "REMOVE #stock"
                    expr_names["#stock"] = "stock"

                set_expr = ""
                if update_expr_parts:
                    set_expr = "SET " + ", ".join(update_expr_parts)

                if set_expr and remove_expr:
                    update_expr = f"{set_expr} {remove_expr}"
                elif set_expr:
                    update_expr = set_expr
                else:
                    update_expr = remove_expr

                update_kwargs = {
                    "TableName": table_name,
                    "Key": {"PK": {"S": "products"}, "SK": {"S": pid}},
                    "UpdateExpression": update_expr,
                    "ExpressionAttributeNames": expr_names,
                }
                if expr_vals:
                    update_kwargs["ExpressionAttributeValues"] = expr_vals
                client.update_item(**update_kwargs)

                updated += 1
                if needs_remove_stock:
                    removed_stock_attr += 1

            last_key = resp.get("LastEvaluatedKey")
            if not last_key:
                break

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Products scanned: {scanned}")
        self.stdout.write(f"Products changed: {updated}")
        self.stdout.write(f"Products with `stock` removed: {removed_stock_attr}")
        self.stdout.write("=" * 70)


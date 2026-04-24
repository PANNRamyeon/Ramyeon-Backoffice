"""
Django management command to fix corrupted Product datetime fields in DynamoDB.

Normalizes all datetime strings to the format DynamoDB/PynamoDB expects:
  %Y-%m-%dT%H:%M:%S.%f+0000  (e.g. 2025-10-11T17:03:13.423000+0000)

Fixes:
- Corrupted years (e.g. 000002025 -> 2025)
- Missing timezone (+0000)
- Top-level: date_received, created_at, updated_at, last_pos_sync, last_stock_update
- Nested: sync_logs[].last_updated, deletion_log.deleted_at

Usage:
    python manage.py fix_product_dynamodb_dates
    python manage.py fix_product_dynamodb_dates --dry-run
"""
from django.core.management.base import BaseCommand
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from decouple import config
import re
import logging

logger = logging.getLogger(__name__)

# Canonical format for DynamoDB UTCDateTimeAttribute (matches PynamoDB expectation)
# Build as strftime(...) + "+0000" since strftime has no timezone code for +0000
DYNAMODB_DATETIME_SUFFIX = "+0000"


def normalize_datetime_string(value):
    """
    Normalize a datetime string to DynamoDB format: YYYY-MM-DDTHH:MM:SS.ffffff+0000

    Handles:
    - Corrupted year: 000002025-10-11T... -> 2025-10-11T...
    - No timezone -> append +0000
    - Already valid -> ensure +0000 suffix
    Returns None if value is empty or unparseable (caller can substitute default).
    """
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None

    # Strip existing timezone for consistent re-format
    value_base = value.replace("+0000", "").replace("Z", "").strip()

    # Fix corrupted year (e.g. 000002025 -> 2025): extract YYYY-MM-DDTHH:MM:SS[.ffffff]
    match = re.search(
        r"0*(\d{4})-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?",
        value_base,
    )
    if not match:
        return None
    year = match.group(1)
    if len(year) > 4:
        year = year[-4:] if year.startswith("0") else year[:4]
    # Replace leading junk + year with clean 4-digit year
    value_base = year + value_base[match.end(1) :]

    # Parse and re-format to canonical form: YYYY-MM-DDTHH:MM:SS.ffffff+0000
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            dt = datetime.strptime(value_base, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + DYNAMODB_DATETIME_SUFFIX
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = "Fix Product datetime fields in DynamoDB to match expected format (YYYY-MM-DDTHH:MM:SS.ffffff+0000)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be fixed, do not write to DynamoDB",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN – no changes will be written."))
        self.stdout.write("=" * 60)
        self.stdout.write("FIX PRODUCT DYNAMODB DATES")
        self.stdout.write("=" * 60)
        self.stdout.write("")

        try:
            table_name = config("DYNAMO_TABLE_NAME", default="RamyeonCornerDB")
            region = config("AWS_REGION_NAME", default="ap-southeast-1")
            dynamodb = boto3.resource(
                "dynamodb",
                region_name=region,
                aws_access_key_id=config("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY"),
            )
            table = dynamodb.Table(table_name)
            self.stdout.write(f"Table: {table_name}")
            self.stdout.write("")

            fixed_count = 0
            checked_count = 0
            last_evaluated_key = None

            while True:
                if last_evaluated_key:
                    response = table.query(
                        KeyConditionExpression=Key("PK").eq("products"),
                        ExclusiveStartKey=last_evaluated_key,
                    )
                else:
                    response = table.query(
                        KeyConditionExpression=Key("PK").eq("products"),
                    )

                items = response.get("Items", [])
                if not items and not last_evaluated_key:
                    self.stdout.write("No product records found.")
                    break

                for item in items:
                    checked_count += 1
                    sk = item.get("SK", "unknown")
                    needs_fix = False
                    updates = {}

                    # ---- Top-level datetime fields ----
                    date_fields = [
                        "date_received",
                        "created_at",
                        "updated_at",
                        "last_pos_sync",
                        "last_stock_update",
                    ]
                    for field in date_fields:
                        if field not in item or item[field] is None:
                            continue
                        value = item[field]
                        if not isinstance(value, str):
                            continue
                        normalized = normalize_datetime_string(value)
                        if normalized is None:
                            if field in ("created_at", "updated_at", "date_received"):
                                now = datetime.utcnow()
                                normalized = now.strftime("%Y-%m-%dT%H:%M:%S.%f") + DYNAMODB_DATETIME_SUFFIX
                            else:
                                continue
                        if normalized != value:
                            updates[field] = normalized
                            needs_fix = True
                            self.stdout.write(
                                self.style.WARNING(f"  {sk} {field}: {value[:44]}... -> {normalized}")
                            )

                    # ---- deletion_log.deleted_at ----
                    deletion_log = item.get("deletion_log")
                    if isinstance(deletion_log, dict):
                        val = deletion_log.get("deleted_at")
                        if isinstance(val, str):
                            normalized = normalize_datetime_string(val)
                            if normalized and normalized != val:
                                new_log = dict(deletion_log)
                                new_log["deleted_at"] = normalized
                                updates["deletion_log"] = new_log
                                needs_fix = True
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  {sk} deletion_log.deleted_at: {val[:44]}... -> {normalized}"
                                    )
                                )

                    # ---- sync_logs[].last_updated ----
                    sync_logs = item.get("sync_logs")
                    if isinstance(sync_logs, list) and sync_logs:
                        new_logs = []
                        logs_changed = False
                        for entry in sync_logs:
                            if not isinstance(entry, dict):
                                new_logs.append(entry)
                                continue
                            log_copy = dict(entry)
                            val = log_copy.get("last_updated")
                            if isinstance(val, str):
                                normalized = normalize_datetime_string(val)
                                if normalized and normalized != val:
                                    log_copy["last_updated"] = normalized
                                    logs_changed = True
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"  {sk} sync_logs[].last_updated: {val[:44]}... -> {normalized}"
                                        )
                                    )
                            new_logs.append(log_copy)
                        if logs_changed:
                            updates["sync_logs"] = new_logs
                            needs_fix = True

                    if needs_fix and updates:
                        if not dry_run:
                            try:
                                update_expr_parts = []
                                expr_attr_values = {}
                                for field, value in updates.items():
                                    update_expr_parts.append(f"{field} = :{field}")
                                    expr_attr_values[f":{field}"] = value
                                table.update_item(
                                    Key={"PK": "products", "SK": sk},
                                    UpdateExpression="SET " + ", ".join(update_expr_parts),
                                    ExpressionAttributeValues=expr_attr_values,
                                )
                                fixed_count += 1
                                self.stdout.write(self.style.SUCCESS(f"  ✓ Fixed {sk}"))
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"  ✗ Update {sk}: {e}"))
                        else:
                            fixed_count += 1
                            self.stdout.write(self.style.SUCCESS(f"  [dry-run] would fix {sk}"))

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break

            self.stdout.write("")
            self.stdout.write("=" * 60)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done: checked {checked_count} products, fixed {fixed_count}"
                    + (" (dry-run)" if dry_run else "")
                )
            )
            self.stdout.write("=" * 60)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()
            logger.exception("fix_product_dynamodb_dates failed")
            raise

"""
Django management command to fix corrupted batch datetime fields directly in DynamoDB.

Usage:
    python manage.py fix_batch_dynamodb_dates
"""
from django.core.management.base import BaseCommand
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from decouple import config
import re
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fix corrupted datetime fields for Batch records directly in DynamoDB"

    def handle(self, *args, **options):
        """Fix corrupted dates on Batch (PK='batches') items in DynamoDB."""

        self.stdout.write("=" * 60)
        self.stdout.write("FIXING DYNAMODB BATCH DATES (Direct)")
        self.stdout.write("=" * 60)
        self.stdout.write("")

        try:
            # Initialize DynamoDB client
            table_name = config("DYNAMO_TABLE_NAME", default="RamyeonCornerDB")
            region = config("AWS_REGION_NAME", default="ap-southeast-1")

            dynamodb = boto3.resource(
                "dynamodb",
                region_name=region,
                aws_access_key_id=config("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY"),
            )

            table = dynamodb.Table(table_name)

            self.stdout.write(f"Connected to table: {table_name}")
            self.stdout.write("")

            fixed_count = 0
            checked_count = 0

            # Date fields on Batch items that are stored as strings (UTCDateTimeAttribute)
            date_fields = ["expiry_date", "date_received", "created_at", "updated_at"]

            last_evaluated_key = None

            while True:
                if last_evaluated_key:
                    response = table.query(
                        KeyConditionExpression=Key("PK").eq("batches"),
                        ExclusiveStartKey=last_evaluated_key,
                    )
                else:
                    response = table.query(
                        KeyConditionExpression=Key("PK").eq("batches"),
                    )

                items = response.get("Items", [])
                if not items and not last_evaluated_key:
                    self.stdout.write("No batch records found.")

                self.stdout.write(f"Processing {len(items)} batch records")

                for item in items:
                    checked_count += 1
                    batch_id = item.get("SK", "unknown")
                    needs_fix = False
                    updates = {}

                    self.stdout.write(f"Checking batch: {batch_id}")

                    # ---- Top-level datetime fields ----
                    for field in date_fields:
                        if field in item and item[field]:
                            value = item[field]
                            value_type = type(value).__name__

                            self.stdout.write(
                                f"  {field}: {value_type} = {str(value)[:50]}"
                            )

                            if isinstance(value, str):
                                # Detect corrupted year formats like '000002025-10-08T...' etc.
                                if re.match(r"^0+\d{4,}", value) or re.match(
                                    r"^[3-9]\d{3,}", value
                                ):
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"    ⚠️  FOUND CORRUPTION: {value[:40]}"
                                        )
                                    )
                                    try:
                                        # Extract a sane ISO-like datetime fragment:
                                        # e.g. '000002025-10-08T12:10:51.644000'
                                        #  -> '2025-10-08T12:10:51.644000'
                                        match = re.search(
                                            r"0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)",
                                            value,
                                        )
                                        if match:
                                            fixed_value = match.group(1)
                                            updates[field] = fixed_value
                                            self.stdout.write(
                                                f"    → Fixed to: {fixed_value}"
                                            )
                                            needs_fix = True
                                        else:
                                            # If we can't parse, fall back to now / None
                                            if field in ["created_at", "updated_at"]:
                                                updates[field] = datetime.utcnow().isoformat()
                                            else:
                                                updates[field] = None
                                            self.stdout.write(
                                                f"    → Reset to: {updates[field]}"
                                            )
                                            needs_fix = True
                                    except Exception as e:
                                        self.stdout.write(f"    → Error parsing: {e}")
                                # Also log any completely invalid format for visibility
                                elif not re.match(
                                    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value
                                ):
                                    self.stdout.write(
                                        f"  {batch_id}: Invalid format {field}: {value[:40]}"
                                    )
                                    if field in ["created_at", "updated_at"]:
                                        updates[field] = datetime.utcnow().isoformat()
                                    else:
                                        updates[field] = None
                                    self.stdout.write(
                                        f"    → Reset to: {updates[field]}"
                                    )
                            needs_fix = True
                        else:
                            self.stdout.write(f"  {field}: <not set or None>")

                    # ---- Nested sync_logs.last_updated ----
                    sync_logs = item.get("sync_logs")
                    if isinstance(sync_logs, list) and sync_logs:
                        new_sync_logs = []
                        sync_logs_changed = False
                        for log_entry in sync_logs:
                            if isinstance(log_entry, dict):
                                log_copy = dict(log_entry)
                                val = log_copy.get("last_updated")
                                if isinstance(val, str):
                                    if re.match(r"^0+\d{4,}", val) or re.match(
                                        r"^[3-9]\d{3,}", val
                                    ):
                                        self.stdout.write(
                                            self.style.WARNING(
                                                f"    ⚠️  CORRUPT sync_logs.last_updated: {val[:40]}"
                                            )
                                        )
                                        match = re.search(
                                            r"0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)",
                                            val,
                                        )
                                        if match:
                                            fixed_value = match.group(1)
                                            log_copy["last_updated"] = fixed_value
                                            self.stdout.write(
                                                f"    → Fixed sync_logs.last_updated to: {fixed_value}"
                                            )
                                        else:
                                            log_copy["last_updated"] = datetime.utcnow().isoformat()
                                            self.stdout.write(
                                                f"    → Reset sync_logs.last_updated to: {log_copy['last_updated']}"
                                            )
                                        sync_logs_changed = True
                                        needs_fix = True
                                new_sync_logs.append(log_copy)
                            else:
                                new_sync_logs.append(log_entry)
                        if sync_logs_changed:
                            updates["sync_logs"] = new_sync_logs

                    # ---- Nested usage_history.timestamp ----
                    usage_history = item.get("usage_history")
                    if isinstance(usage_history, list) and usage_history:
                        new_history = []
                        history_changed = False
                        for hist_entry in usage_history:
                            if isinstance(hist_entry, dict):
                                hist_copy = dict(hist_entry)
                                val = hist_copy.get("timestamp")
                                if isinstance(val, str):
                                    if re.match(r"^0+\d{4,}", val) or re.match(
                                        r"^[3-9]\d{3,}", val
                                    ):
                                        self.stdout.write(
                                            self.style.WARNING(
                                                f"    ⚠️  CORRUPT usage_history.timestamp: {val[:40]}"
                                            )
                                        )
                                        match = re.search(
                                            r"0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)",
                                            val,
                                        )
                                        if match:
                                            fixed_value = match.group(1)
                                            hist_copy["timestamp"] = fixed_value
                                            self.stdout.write(
                                                f"    → Fixed usage_history.timestamp to: {fixed_value}"
                                            )
                                        else:
                                            hist_copy["timestamp"] = datetime.utcnow().isoformat()
                                            self.stdout.write(
                                                f"    → Reset usage_history.timestamp to: {hist_copy['timestamp']}"
                                            )
                                        history_changed = True
                                        needs_fix = True
                                new_history.append(hist_copy)
                            else:
                                new_history.append(hist_entry)
                        if history_changed:
                            updates["usage_history"] = new_history

                    if needs_fix:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  → Batch {batch_id} NEEDS FIX: {len(updates)} field(s)"
                            )
                        )
                    else:
                        self.stdout.write(f"  → Batch {batch_id} OK")

                    self.stdout.write("")

                    if needs_fix and updates:
                        try:
                            # Build update expression
                            update_expr_parts = []
                            expr_attr_values = {}

                            for field, value in updates.items():
                                update_expr_parts.append(f"{field} = :{field}")
                                expr_attr_values[f":{field}"] = value

                            update_expr = "SET " + ", ".join(update_expr_parts)

                            table.update_item(
                                Key={"PK": "batches", "SK": batch_id},
                                UpdateExpression=update_expr,
                                ExpressionAttributeValues=expr_attr_values,
                            )

                            fixed_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"  ✓ Fixed batch {batch_id}")
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"  ✗ Error updating {batch_id}: {e}")
                            )

                    self.stdout.write("")

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break

            self.stdout.write("=" * 60)
            self.stdout.write(
                self.style.SUCCESS(
                    f"COMPLETE: Checked {checked_count} batches, fixed {fixed_count}"
                )
            )
            self.stdout.write("=" * 60)

        except Exception as e:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f"✗ Error: {str(e)}"))
            import traceback

            traceback.print_exc()
            logger.error(f"Error fixing Batch DynamoDB dates: {str(e)}")
            raise


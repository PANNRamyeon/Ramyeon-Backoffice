"""
Django management command to fix corrupted Customer datetime fields in DynamoDB.

Normalizes all datetime strings to the format DynamoDB/PynamoDB expects:
  %Y-%m-%dT%H:%M:%S.%f+0000  (e.g. 2025-09-30T11:28:01.603000+0000)

Fixes:
- Corrupted years (e.g. 000002025 -> 2025)
- Missing timezone (+0000)
- Top-level: date_created, updated_at, last_purchase, password_last_changed
- Nested: auth_providers[].last_login

Usage:
    python manage.py fix_customer_dynamodb_dates
    python manage.py fix_customer_dynamodb_dates --dry-run
"""
from django.core.management.base import BaseCommand
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from decouple import config
import re
import logging

logger = logging.getLogger(__name__)

DYNAMODB_DATETIME_SUFFIX = "+0000"


def normalize_datetime_string(value):
    """
    Normalize a datetime string to DynamoDB format: YYYY-MM-DDTHH:MM:SS.ffffff+0000

    Handles:
    - Corrupted year: 000002025-09-30T... -> 2025-09-30T...
    - No timezone -> append +0000
    - Already valid -> ensure +0000 suffix
    Returns None if value is empty or unparseable.
    """
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None

    value_base = value.replace("+0000", "").replace("Z", "").strip()

    match = re.search(
        r"0*(\d{4})-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?",
        value_base,
    )
    if not match:
        return None
    year = match.group(1)
    if len(year) > 4:
        year = year[-4:] if year.startswith("0") else year[:4]
    value_base = year + value_base[match.end(1):]

    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(value_base, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + DYNAMODB_DATETIME_SUFFIX
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = "Fix Customer datetime fields in DynamoDB to match expected format (YYYY-MM-DDTHH:MM:SS.ffffff+0000)"

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
        self.stdout.write("FIX CUSTOMER DYNAMODB DATES")
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
                query_kwargs = {
                    "KeyConditionExpression": Key("PK").eq("customers")
                }
                if last_evaluated_key:
                    query_kwargs["ExclusiveStartKey"] = last_evaluated_key

                response = table.query(**query_kwargs)
                items = response.get("Items", [])

                if not items and not last_evaluated_key:
                    self.stdout.write("No customer records found.")
                    break

                for item in items:
                    checked_count += 1
                    sk = item.get("SK", "unknown")
                    needs_fix = False
                    updates = {}

                    # ---- Top-level datetime fields ----
                    top_level_fields = [
                        "date_created",
                        "updated_at",
                        "last_purchase",
                        "password_last_changed",
                    ]
                    for field in top_level_fields:
                        if field not in item or item[field] is None:
                            continue
                        value = item[field]
                        if not isinstance(value, str):
                            continue
                        normalized = normalize_datetime_string(value)
                        if normalized is None:
                            # Substitute now for critical audit fields
                            if field in ("date_created", "updated_at"):
                                normalized = (
                                    datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")
                                    + DYNAMODB_DATETIME_SUFFIX
                                )
                            else:
                                continue
                        if normalized != value:
                            updates[field] = normalized
                            needs_fix = True
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  {sk} {field}: {value[:50]}... -> {normalized}"
                                )
                            )

                    # ---- auth_providers[].last_login ----
                    auth_providers = item.get("auth_providers")
                    if isinstance(auth_providers, list) and auth_providers:
                        new_providers = []
                        providers_changed = False
                        for provider in auth_providers:
                            if not isinstance(provider, dict):
                                new_providers.append(provider)
                                continue
                            provider_copy = dict(provider)
                            val = provider_copy.get("last_login")
                            if isinstance(val, str):
                                normalized = normalize_datetime_string(val)
                                if normalized and normalized != val:
                                    provider_copy["last_login"] = normalized
                                    providers_changed = True
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"  {sk} auth_providers[{provider.get('provider','?')}].last_login: "
                                            f"{val[:50]}... -> {normalized}"
                                        )
                                    )
                            new_providers.append(provider_copy)
                        if providers_changed:
                            updates["auth_providers"] = new_providers
                            needs_fix = True

                    if needs_fix and updates:
                        if not dry_run:
                            try:
                                update_expr_parts = []
                                expr_attr_names = {}
                                expr_attr_values = {}
                                for field, value in updates.items():
                                    safe_key = f"#f_{field}"
                                    val_key = f":v_{field}"
                                    update_expr_parts.append(f"{safe_key} = {val_key}")
                                    expr_attr_names[safe_key] = field
                                    expr_attr_values[val_key] = value
                                table.update_item(
                                    Key={"PK": "customers", "SK": sk},
                                    UpdateExpression="SET " + ", ".join(update_expr_parts),
                                    ExpressionAttributeNames=expr_attr_names,
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
                    f"Done: checked {checked_count} customers, fixed {fixed_count}"
                    + (" (dry-run)" if dry_run else "")
                )
            )
            self.stdout.write("=" * 60)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()
            logger.exception("fix_customer_dynamodb_dates failed")
            raise

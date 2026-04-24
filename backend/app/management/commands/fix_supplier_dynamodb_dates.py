"""
Django management command to fix corrupted supplier datetime fields directly in DynamoDB.

Important: this command uses the SAME table/region variables as the PynamoDB models:
- table: `app.utils.DYNAMO_TABLE_NAME` (env `DYNAMO_TABLE_NAME`)
- region: `app.utils.AWS_REGION` (env `AWS_REGION`)

Fixes legacy patterns like:
  '000002025-10-13T12:45:55.020000' -> '2025-10-13T12:45:55.020000+0000'

Usage:
    python manage.py fix_supplier_dynamodb_dates
"""

from django.core.management.base import BaseCommand
from datetime import datetime
import boto3
import re
import logging

from app.utils import DYNAMO_TABLE_NAME, AWS_REGION

logger = logging.getLogger(__name__)

_ISO_FRAGMENT_RE = re.compile(
    r"0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
)


def _normalize_to_pynamo_utc(value: str) -> str | None:
    """
    Convert a possibly-corrupt/legacy datetime string to the format PynamoDB expects:
    '%Y-%m-%dT%H:%M:%S.%f+0000'
    """
    if not isinstance(value, str) or not value:
        return None

    # Normalize timezone suffix if present
    v = value.replace("Z", "+0000").replace("+00:00", "+0000")

    m = _ISO_FRAGMENT_RE.search(v)
    if not m:
        return None

    base = m.group(1)
    # Ensure timezone suffix exists, because your error shows Pynamo expects +0000
    if "+0000" not in v:
        return f"{base}+0000"

    # If timezone exists, keep +0000 (strip anything after +0000 just in case)
    idx = v.find("+0000")
    return f"{base}{v[idx:idx+5]}"


def _get_s(item: dict, attr: str) -> str | None:
    v = item.get(attr)
    if isinstance(v, dict) and "S" in v:
        return v["S"]
    return None


class Command(BaseCommand):
    help = "Fix corrupted datetime fields for Supplier records (PK='suppliers') in DynamoDB"

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("FIXING DYNAMODB SUPPLIER DATES (raw)")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Table: {DYNAMO_TABLE_NAME}")
        self.stdout.write(f"Region: {AWS_REGION}")
        self.stdout.write("")

        client = boto3.client("dynamodb", region_name=AWS_REGION)

        fixed_count = 0
        checked_count = 0
        last_evaluated_key = None

        while True:
            kwargs = {
                "TableName": DYNAMO_TABLE_NAME,
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": {"S": "suppliers"}},
            }
            if last_evaluated_key:
                kwargs["ExclusiveStartKey"] = last_evaluated_key

            resp = client.query(**kwargs)
            items = resp.get("Items", [])

            if not items and not last_evaluated_key:
                self.stdout.write("No supplier records found.")
                break

            for item in items:
                checked_count += 1
                sk = _get_s(item, "SK") or "unknown"
                updates: dict[str, dict] = {}

                # Top-level fields
                for field in ("created_at", "updated_at"):
                    raw = _get_s(item, field)
                    if not raw:
                        continue
                    normalized = _normalize_to_pynamo_utc(raw)
                    if normalized and normalized != raw:
                        updates[field] = {"S": normalized}
                        self.stdout.write(
                            self.style.WARNING(f"  {sk} {field}: {raw[:40]} -> {normalized}")
                        )

                # Nested: sync_logs[].last_updated
                sync_logs = item.get("sync_logs")
                if isinstance(sync_logs, dict) and "L" in sync_logs:
                    new_list = []
                    changed = False
                    for entry in sync_logs["L"]:
                        if not isinstance(entry, dict) or "M" not in entry:
                            new_list.append(entry)
                            continue
                        m = dict(entry["M"])
                        last_updated = m.get("last_updated")
                        raw = last_updated.get("S") if isinstance(last_updated, dict) else None
                        if raw:
                            normalized = _normalize_to_pynamo_utc(raw)
                            if normalized and normalized != raw:
                                m["last_updated"] = {"S": normalized}
                                changed = True
                        new_list.append({"M": m})

                    if changed:
                        updates["sync_logs"] = {"L": new_list}
                        self.stdout.write(self.style.WARNING(f"  {sk} sync_logs.last_updated: normalized"))

                if not updates:
                    continue

                try:
                    # UpdateExpression: SET a = :a, b = :b ...
                    expr_parts = []
                    expr_vals = {}
                    for k, v in updates.items():
                        placeholder = f":{k}"
                        expr_parts.append(f"{k} = {placeholder}")
                        expr_vals[placeholder] = v

                    client.update_item(
                        TableName=DYNAMO_TABLE_NAME,
                        Key={"PK": {"S": "suppliers"}, "SK": {"S": sk}},
                        UpdateExpression="SET " + ", ".join(expr_parts),
                        ExpressionAttributeValues=expr_vals,
                    )
                    fixed_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Fixed supplier {sk}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Error updating {sk}: {e}"))

            last_evaluated_key = resp.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS(f"COMPLETE: Checked {checked_count} suppliers, fixed {fixed_count}"))
        self.stdout.write("=" * 60)

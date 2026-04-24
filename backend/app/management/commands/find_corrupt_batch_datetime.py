"""
Scan DynamoDB to find any items containing the legacy corrupted datetime
string used in Batch records, e.g. '000002025-10-08T12:10:51.644000'.

Usage:
    python manage.py find_corrupt_batch_datetime
"""

from django.core.management.base import BaseCommand
from decouple import config
import boto3
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


TARGET_FULL = "000002025-10-08T12:10:51.644000"
TARGET_PARTIAL = "000002025-10-08"


class Command(BaseCommand):
    help = "Find any DynamoDB items that still contain the corrupted batch datetime string"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pk",
            dest="pk",
            default=None,
            help="Optional PK to restrict search (e.g. 'batches'). If omitted, scans entire table.",
        )

    def handle(self, *args, **options):
        table_name = config("DYNAMO_TABLE_NAME", default="RamyeonCornerDB")
        region = config("AWS_REGION_NAME", default="ap-southeast-1")

        self.stdout.write("=" * 60)
        self.stdout.write(f"SCANNING FOR CORRUPTED DATETIME IN TABLE: {table_name}")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Target (full)   : {TARGET_FULL}")
        self.stdout.write(f"Target (partial): {TARGET_PARTIAL}")
        self.stdout.write("")

        # Use low-level client for raw response (no automatic type conversion)
        dynamodb_client = boto3.client(
            "dynamodb",
            region_name=region,
            aws_access_key_id=config("AWS_ACCESS_KEY_ID", default=""),
            aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY", default=""),
        )

        pk_filter = options.get("pk")
        matches = 0
        scanned = 0

        def walk(value: Any, path: str = "") -> bool:
            """
            Recursively check any value. Returns True if a match is found anywhere below.
            """
            found_here = False
            if isinstance(value, str):
                if TARGET_FULL in value or TARGET_PARTIAL in value:
                    found_here = True
            elif isinstance(value, dict):
                for k, v in value.items():
                    if walk(v, f"{path}.{k}" if path else k):
                        found_here = True
            elif isinstance(value, list):
                for idx, v in enumerate(value):
                    if walk(v, f"{path}[{idx}]"):
                        found_here = True
            return found_here

        last_key: Dict[str, Any] | None = None

        def deserialize_dynamo_value(val):
            """Convert DynamoDB low-level format to Python (S->str, N->number, L->list, M->dict)."""
            if isinstance(val, dict):
                if "S" in val:
                    return val["S"]
                if "N" in val:
                    return val["N"]
                if "BOOL" in val:
                    return val["BOOL"]
                if "NULL" in val:
                    return None
                if "L" in val:
                    return [deserialize_dynamo_value(x) for x in val["L"]]
                if "M" in val:
                    return {k: deserialize_dynamo_value(v) for k, v in val["M"].items()}
            return val

        while True:
            if pk_filter:
                query_kwargs = {
                    "TableName": table_name,
                    "KeyConditionExpression": "PK = :pk",
                    "ExpressionAttributeValues": {":pk": {"S": pk_filter}},
                }
                if last_key:
                    query_kwargs["ExclusiveStartKey"] = last_key
                response = dynamodb_client.query(**query_kwargs)
            else:
                scan_kwargs = {"TableName": table_name}
                if last_key:
                    scan_kwargs["ExclusiveStartKey"] = last_key
                response = dynamodb_client.scan(**scan_kwargs)

            raw_items = response.get("Items", [])
            scanned += len(raw_items)

            for raw_item in raw_items:
                # Deserialize from DynamoDB format
                item = {k: deserialize_dynamo_value(v) for k, v in raw_item.items()}
                if walk(item):
                    matches += 1
                    pk_val = item.get("PK")
                    sk_val = item.get("SK")
                    self.stdout.write(self.style.WARNING("=== MATCH FOUND ==="))
                    self.stdout.write(f"PK: {pk_val}")
                    self.stdout.write(f"SK: {sk_val}")
                    self.stdout.write(f"Raw item (truncated): {str(raw_item)[:800]}...")
                    self.stdout.write("")

            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break

        self.stdout.write("=" * 60)
        self.stdout.write(f"Scan complete. Items scanned: {scanned}, matches found: {matches}")
        if matches == 0:
            self.stdout.write(self.style.SUCCESS("No items containing the corrupted datetime string were found."))
        else:
            self.stdout.write(self.style.WARNING("Review the matched items above and correct them as needed."))
        self.stdout.write("=" * 60)


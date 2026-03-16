"""
fix_promotion_datetimes.py

This script scans all promotion items in DynamoDB, detects malformed datetime strings
(e.g., '000002025-10-12T16:48:54.458000') and corrects them by stripping leading zeros
from the year. It updates the item if any fixes are applied.

Usage:
    python fix_promotion_datetimes.py
"""

import os
import re
import boto3
from dotenv import load_dotenv

load_dotenv()

TABLE_NAME = os.getenv('DYNAMO_TABLE_NAME', 'RamyeonCornerDB')
AWS_REGION = os.getenv('AWS_REGION_NAME') or os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

client_kwargs = {'region_name': AWS_REGION}
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    client_kwargs.update({
        'aws_access_key_id': AWS_ACCESS_KEY,
        'aws_secret_access_key': AWS_SECRET_KEY
    })

dynamodb = boto3.resource('dynamodb', **client_kwargs)
table = dynamodb.Table(TABLE_NAME)


def fix_datetime_string(value):
    """
    If value is a string, remove any leading zeros before the year.
    Returns the corrected string or the original value if no fix needed.
    """
    if isinstance(value, str):
        # Pattern: optional leading zeros, then 4-digit year, then rest of ISO datetime
        match = re.search(r'0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)?)', value)
        if match:
            corrected = match.group(1)
            if corrected != value:
                print(f"    Fixed: {value} -> {corrected}")
                return corrected
    return value


def fix_promotion_item(item):
    """Inspect a promotion item, fix datetime fields, return True if updated."""
    updated = False

    # Top-level datetime fields
    datetime_fields = [
        'start_date', 'end_date', 'created_at',
        'deactivated_at', 'last_pos_sync', 'updated_at'
    ]
    for field in datetime_fields:
        if field in item:
            original = item[field]
            fixed = fix_datetime_string(original)
            if fixed != original:
                item[field] = fixed
                updated = True

    # Nested usage_history (list of maps)
    if 'usage_history' in item and isinstance(item['usage_history'], list):
        for hist in item['usage_history']:
            if 'timestamp' in hist:
                original = hist['timestamp']
                fixed = fix_datetime_string(original)
                if fixed != original:
                    hist['timestamp'] = fixed
                    updated = True

    # Nested audit_log (list of maps)
    if 'audit_log' in item and isinstance(item['audit_log'], list):
        for log in item['audit_log']:
            if 'timestamp' in log:
                original = log['timestamp']
                fixed = fix_datetime_string(original)
                if fixed != original:
                    log['timestamp'] = fixed
                    updated = True

    return updated


def fix_all_promotions():
    """Scan all promotions, fix datetime fields, update items in batches."""
    last_key = None
    scanned = 0
    fixed_count = 0

    print(f"Scanning table '{TABLE_NAME}' for promotion items (PK='promotions')...")
    while True:
        scan_kwargs = {
            'FilterExpression': 'PK = :pk',
            'ExpressionAttributeValues': {':pk': 'promotions'},
            'Limit': 100
        }
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = last_key

        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        if not items:
            break

        for item in items:
            scanned += 1
            sk = item.get('SK', 'unknown')
            print(f"\nProcessing {sk} ...")

            if fix_promotion_item(item):
                # Update the item with corrected datetimes
                try:
                    table.put_item(Item=item)
                    print(f"  ✅ Updated {sk}")
                    fixed_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to update {sk}: {e}")
            else:
                print(f"  No changes needed for {sk}")

        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break

    print(f"\nScan complete. Scanned {scanned} promotion items, fixed {fixed_count}.")


if __name__ == '__main__':
    print("This script will scan all promotion items and fix malformed datetime strings.")
    print("It will update items in DynamoDB. It is recommended to back up your table first.")
    confirm = input("Type 'yes' to proceed: ")
    if confirm.lower() == 'yes':
        fix_all_promotions()
    else:
        print("Aborted.")
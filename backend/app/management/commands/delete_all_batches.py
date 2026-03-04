"""
Delete ALL batch items (PK = 'batches') from the DynamoDB single-table.

Usage (VERY DESTRUCTIVE):
    python manage.py delete_all_batches

You probably want to run this only in a development / staging environment.
"""

from django.core.management.base import BaseCommand, CommandError
from decouple import config
import boto3
from boto3.dynamodb.conditions import Key
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete ALL batch items (PK = 'batches') from DynamoDB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes-i-am-sure",
            action="store_true",
            dest="confirm",
            help="Required flag to actually perform the deletion.",
        )

    def handle(self, *args, **options):
        if not options.get("confirm"):
            raise CommandError(
                "Refusing to delete all batches without --yes-i-am-sure. "
                "Run: python manage.py delete_all_batches --yes-i-am-sure"
            )

        table_name = config("DYNAMO_TABLE_NAME", default="RamyeonCornerDB")
        region = config("AWS_REGION_NAME", default="ap-southeast-1")

        self.stdout.write("=" * 60)
        self.stdout.write(f"WARNING: DELETING ALL BATCHES FROM TABLE: {table_name}")
        self.stdout.write("=" * 60)

        dynamodb = boto3.resource(
            "dynamodb",
            region_name=region,
            aws_access_key_id=config("AWS_ACCESS_KEY_ID", default=""),
            aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY", default=""),
        )
        table = dynamodb.Table(table_name)

        deleted = 0
        scanned = 0
        last_evaluated_key = None

        while True:
            query_kwargs = {
                "KeyConditionExpression": Key("PK").eq("batches"),
            }
            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = table.query(**query_kwargs)
            items = response.get("Items", [])
            scanned += len(items)

            if not items:
                break

            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                    deleted += 1

            self.stdout.write(f"Deleted {deleted} batches so far (scanned {scanned}).")

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS(f"COMPLETE: Deleted {deleted} batch item(s)."))
        self.stdout.write("=" * 60)


# app/services/saleslog_service.py
from datetime import datetime
import uuid
from decimal import Decimal
from ..core.database_service import DatabaseService
from boto3.dynamodb.conditions import Key, Attr
from app.models import SalesLog
import logging

# Helper to convert floats to Decimals for DynamoDB
def floats_to_decimals(obj):
    if isinstance(obj, list):
        return [floats_to_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

class SalesLogService:
    def __init__(self):
        db_service = DatabaseService()
        self.table = db_service.get_table('sales_logs')

    def create_invoice(self, invoice_data):
        try:
            invoice = SalesLog(**invoice_data)
            invoice_dict = invoice.to_dict()
            
            invoice_dict = floats_to_decimals(invoice_dict)
            invoice_dict = {k: v for k, v in invoice_dict.items() if v not in [None, '']}
            
            self.table.put_item(Item=invoice_dict)
            return invoice.to_dict()
        except Exception as e:
            raise Exception(f"Error creating invoice: {str(e)}")

    def get_invoice_by_id(self, invoice_id):
        try:
            response = self.table.get_item(Key={'saleslog_id': invoice_id})
            return response.get('Item')
        except Exception as e:
            raise Exception(f"Error retrieving invoice: {str(e)}")

    def get_all_invoices(self, limit=100, start_key=None):
        scan_kwargs = {'Limit': limit}
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        try:
            response = self.table.scan(**scan_kwargs)
            return response.get('Items', []), response.get('LastEvaluatedKey')
        except Exception as e:
            raise Exception(f"Error retrieving invoices: {str(e)}")

    def update_invoice(self, invoice_id, update_data):
        try:
            update_data.pop('saleslog_id', None)
            
            update_expression = "SET " + ", ".join(f"#{k}=:{k}" for k in update_data.keys())
            expression_attribute_names = {f"#{k}": k for k in update_data.keys()}
            expression_attribute_values = {f":{k}": v for k, v in update_data.items()}

            self.table.update_item(
                Key={'saleslog_id': invoice_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )
            return self.get_invoice_by_id(invoice_id)
        except Exception as e:
            raise Exception(f"Error updating invoice: {str(e)}")

    def delete_invoice(self, invoice_id):
        try:
            self.table.delete_item(Key={'saleslog_id': invoice_id})
            return True
        except Exception as e:
            raise Exception(f"Error deleting invoice: {str(e)}")

    def get_transactions_for_export(self, filters=None):
        """Get transactions with filtering. Inefficient for large tables without GSIs."""
        try:
            filter_expressions = []
            if filters:
                if filters.get('start_date') and filters.get('end_date'):
                    # This requires the transaction_date to be an ISO 8601 string
                    filter_expressions.append(Attr('transaction_date').between(
                        filters['start_date'], filters['end_date']
                    ))
                if filters.get('sales_type'):
                    filter_expressions.append(Attr('sales_type').eq(filters['sales_type']))
                # ... add other filters
            
            scan_kwargs = {}
            if filter_expressions:
                scan_kwargs['FilterExpression'] = filter_expressions[0]
                for expression in filter_expressions[1:]:
                    scan_kwargs['FilterExpression'] &= expression
            
            response = self.table.scan(**scan_kwargs)
            return response.get('Items', [])
        except Exception as e:
            raise Exception(f"Error retrieving transactions for export: {str(e)}")
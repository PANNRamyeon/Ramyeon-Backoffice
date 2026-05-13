from datetime import datetime
import uuid
from decimal import Decimal
from ..core.database_service import DatabaseService
from notifications.services import notification_service
# from .promotionCon import PromoConnection # Needs refactoring
# from ..batch_service import BatchService # Needs refactoring
# from ..product_service import ProductService # Needs refactoring
import logging

logger = logging.getLogger(__name__)

# Helper to convert floats to Decimals for DynamoDB
def floats_to_decimals(obj):
    if isinstance(obj, list):
        return [floats_to_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

class SalesService:
    """
    Unified service for sales, adapted for DynamoDB.
    """
    def __init__(self):
        db_service = DatabaseService()
        self.sales_table = db_service.get_table('sales')
        self.sales_log_table = db_service.get_table('sales_log')
        self.products_table = db_service.get_table('products')
        self.promotions_table = db_service.get_table('promotions')
        self.customers_table = db_service.get_table('customers')
        self.users_table = db_service.get_table('users')

    def create_unified_sale(self, sale_data, source='pos'):
        """
        Create a sale record that works for both POS and manual entry
        """
        try:
            if source == 'pos':
                return self._create_pos_sale(sale_data)
            else:
                return self._create_sales_log(sale_data, source)
        except Exception as e:
            raise Exception(f"Error creating unified sale: {str(e)}")

    def _create_pos_sale(self, sale_data):
        """Create POS-style sale record in DynamoDB"""
        try:
            sale_id = f"SALE-{uuid.uuid4()}"
            sales_record = {
                'sale_id': sale_id,
                'items': sale_data['items'],
                'total_amount': sale_data['total_amount'],
                'final_amount': sale_data.get('final_amount', sale_data['total_amount']),
                'payment_method': sale_data.get('payment_method', 'cash'),
                'cashier_id': sale_data.get('cashier_id'),
                'customer_id': sale_data.get('customer_id'),
                'transaction_date': datetime.utcnow().isoformat() + "Z",
                'status': 'completed',
                'source': 'pos',
            }

            item_to_put = floats_to_decimals(sales_record)
            item_to_put = {k: v for k, v in item_to_put.items() if v not in [None, '']}
            
            self.sales_table.put_item(Item=item_to_put)
            
            self._send_sale_notification(sales_record, 'pos_sale_created')

            return {
                'success': True,
                'message': 'POS sale created successfully',
                'data': sales_record
            }
        except Exception as e:
            raise Exception(f"Error creating POS sale: {str(e)}")

    def _create_sales_log(self, sale_data, source):
        """Create sales log style record in DynamoDB"""
        try:
            log_id = f"SLOG-{uuid.uuid4()}"
            
            sales_log_record = {
                'saleslog_id': log_id,
                'customer_id': sale_data.get('customer_id'),
                'user_id': sale_data.get('user_id'),
                'transaction_date': (sale_data.get('transaction_date') or datetime.utcnow()).isoformat() + "Z",
                'total_amount': sale_data['total_amount'],
                'status': sale_data.get('status', 'completed'),
                'payment_method': sale_data.get('payment_method', 'cash'),
                'sales_type': sale_data.get('sales_type', 'retail'),
                'item_list': sale_data.get('item_list', []),
                'source': source,
            }
            
            item_to_put = floats_to_decimals(sales_log_record)
            item_to_put = {k: v for k, v in item_to_put.items() if v not in [None, '']}

            self.sales_log_table.put_item(Item=item_to_put)
            
            self._send_sale_notification(sales_log_record, f'{source}_sale_created')

            return {
                'success': True,
                'message': f'{source.title()} sale logged successfully',
                'data': sales_log_record
            }
        except Exception as e:
            raise Exception(f"Error creating sales log: {str(e)}")


    def _send_sale_notification(self, sale_record, notification_type):
        """Send notification for sale creation"""
        try:
            total_amount = sale_record.get('total_amount', 0)
            source = sale_record.get('source', 'unknown')
            
            if notification_type == 'pos_sale_created':
                title = "POS Sale Completed"
                message = f"New POS transaction completed for ₱{total_amount}"
                priority = "low"
            elif notification_type == 'csv_sale_created':
                title = "CSV Sale Imported"
                message = f"Sale imported from CSV for ₱{total_amount}"
                priority = "low"
            elif notification_type == 'manual_sale_created':
                title = "Manual Sale Entered"
                message = f"Manual sale entry for ₱{total_amount}"
                priority = "low"
            else:
                title = "Sale Created"
                message = f"New sale recorded for ₱{total_amount}"
                priority = "low"

            notification_service.create_notification(
                title=title,
                message=message,
                priority=priority,
                notification_type="sales",
                metadata={
                    "sale_id": str(sale_record.get('_id', '')),
                    "total_amount": total_amount,
                    "source": source,
                    "payment_method": sale_record.get('payment_method', ''),
                    "action_type": notification_type
                }
            )

        except Exception as notification_error:
            print(f"Failed to create sale notification: {notification_error}")

    def get_pos_sale_by_id(self, sale_id):
        """Get a POS sale by ID from the sales table"""
        try:
            response = self.sales_table.get_item(Key={'sale_id': sale_id})
            item = response.get('Item')
            if item:
                return {k: (float(v) if hasattr(v, 'is_finite') else v) for k, v in item.items()}
            return None
        except Exception as e:
            raise Exception(f"Error fetching POS sale by ID: {str(e)}")

    def void_sale(self, sale_id):
        """Mark a POS sale as voided"""
        try:
            response = self.sales_table.get_item(Key={'sale_id': sale_id})
            item = response.get('Item')
            if not item:
                return None

            self.sales_table.update_item(
                Key={'sale_id': sale_id},
                UpdateExpression='SET #s = :s',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':s': 'voided'},
            )
            item['status'] = 'voided'
            return {'success': True, 'message': f'Sale {sale_id} voided', 'data': item}
        except Exception as e:
            raise Exception(f"Error voiding sale: {str(e)}")

    def get_sale_receipt(self, sale_id):
        """Return receipt-formatted data for a completed POS sale"""
        try:
            response = self.sales_table.get_item(Key={'sale_id': sale_id})
            item = response.get('Item')
            if not item:
                return None

            items = item.get('items', [])
            receipt_lines = []
            for line in items:
                receipt_lines.append({
                    'product_id': line.get('product_id'),
                    'product_name': line.get('product_name', ''),
                    'sku': line.get('sku', ''),
                    'quantity': line.get('quantity', 0),
                    'unit_price': float(line.get('unit_price', 0)),
                    'subtotal': float(line.get('subtotal', 0)),
                })

            return {
                'sale_id': item.get('sale_id'),
                'transaction_date': item.get('transaction_date'),
                'cashier_id': item.get('cashier_id'),
                'customer_id': item.get('customer_id'),
                'payment_method': item.get('payment_method', 'cash'),
                'total_amount': float(item.get('total_amount', 0)),
                'final_amount': float(item.get('final_amount', item.get('total_amount', 0))),
                'status': item.get('status'),
                'items': receipt_lines,
            }
        except Exception as e:
            raise Exception(f"Error fetching sale receipt: {str(e)}")
    
    def get_recent_sales(self, limit=10):
        """Get recent sales from both POS and sales_log - Fixed version"""
        try:
            all_sales = []
            
            # Get POS sales
            pos_sales = list(self.sales_collection.find({}).sort('transaction_date', -1).limit(limit))
            for sale in pos_sales:
                sale['collection_source'] = 'sales'
                all_sales.append(self.convert_object_id(sale))  # ✅ Fix ObjectId
            
            # Get sales_log sales  
            log_sales = list(self.sales_log_collection.find({}).sort('transaction_date', -1).limit(limit))
            for sale in log_sales:
                sale['collection_source'] = 'sales_log'
                all_sales.append(self.convert_object_id(sale))  # ✅ Fix ObjectId
            
            # Sort by date and limit
            all_sales.sort(key=lambda x: x['transaction_date'], reverse=True)
            return all_sales[:limit]
            
        except Exception as e:
            raise Exception(f"Error fetching recent sales: {str(e)}")
        
    def get_sales_by_date_range(self, start_date, end_date, source=None):
        """Create sales log style record"""
        try:
           
            return

        except Exception as e:
            raise Exception(f"Error Fetching sale by ID: {str(e)}")
        
    def get_sales_log_by_id(self, log_id):
        """
        ✅ MISSING METHOD: Get sales log by ID from sales_log collection
        This is what SalesLogService.get_invoice_by_id() is trying to call
        """
        try:
            if isinstance(log_id, str):
                log_id = ObjectId(log_id)
            
            log_doc = self.sales_log_collection.find_one({"_id": log_id})
            
            if log_doc:
                return self.convert_object_id(log_doc)
            return None
            
        except Exception as e:
            raise Exception(f"Error retrieving sales log by ID: {str(e)}")

    def update_sales_log(self, log_id, update_data):
        """
        Update an existing sales log in DynamoDB.
        """
        try:
            update_data.pop('saleslog_id', None)
            
            update_expression_parts = []
            expression_attribute_names = {}
            expression_attribute_values = {}

            for key, value in update_data.items():
                update_expression_parts.append(f"#{key} = :{key}")
                expression_attribute_names[f"#{key}"] = key
                expression_attribute_values[f":{key}"] = value

            update_expression = "SET " + ", ".join(update_expression_parts)

            self.sales_log_table.update_item(
                Key={'saleslog_id': log_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )
            return self.get_sales_log_by_id(log_id)
        except Exception as e:
            raise Exception(f"Error updating sales log: {str(e)}")

    def delete_sales_log(self, log_id):
        """
        Delete a sales log from DynamoDB.
        """
        try:
            self.sales_log_table.delete_item(Key={'saleslog_id': log_id})
            return True
        except Exception as e:
            raise Exception(f"Error deleting sales log: {str(e)}")

    def get_all_sales_logs(self, limit=100, skip=0):
        """
        ✅ MISSING METHOD: Get all sales logs with pagination
        """
        try:
            logs = list(self.sales_log_collection.find().skip(skip).limit(limit))
            
            # Convert ObjectIds to strings
            for log in logs:
                self.convert_object_id(log)
            
            return logs
            
        except Exception as e:
            raise Exception(f"Error retrieving sales logs: {str(e)}")

    def get_sales_logs_paginated(self, page=1, page_size=50, filters=None):
        """
        ✅ MISSING METHOD: Get sales logs with advanced pagination and filtering
        """
        try:
            skip = (page - 1) * page_size
            query = {}
            
            # Apply filters if provided
            if filters:
                if filters.get('start_date') and filters.get('end_date'):
                    query['transaction_date'] = {
                        '$gte': filters['start_date'],
                        '$lte': filters['end_date']
                    }
                if filters.get('sales_type'):
                    query['sales_type'] = filters['sales_type']
                if filters.get('source'):
                    query['source'] = filters['source']
                if filters.get('payment_method'):
                    query['payment_method'] = filters['payment_method']
                if filters.get('customer_id'):
                    try:
                        query['customer_id'] = ObjectId(filters['customer_id'])
                    except:
                        pass  # Skip invalid customer_id
            
            # Get logs with pagination
            logs = list(self.sales_log_collection.find(query).skip(skip).limit(page_size))
            total_count = self.sales_log_collection.count_documents(query)
            total_pages = (total_count + page_size - 1) // page_size
            
            # Convert ObjectIds
            for log in logs:
                self.convert_object_id(log)
            
            return {
                "data": logs,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_records": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                },
                "filters_applied": filters or {}
            }
            
        except Exception as e:
            raise Exception(f"Error retrieving paginated sales logs: {str(e)}")

    def get_sales_logs_for_export(self, filters=None):
        """
        ✅ MISSING METHOD: Get sales logs for export with filtering
        """
        try:
            query = {}
            
            # Apply filters if provided
            if filters:
                # Date range filtering
                if filters.get('start_date') and filters.get('end_date'):
                    try:
                        from django.utils.dateparse import parse_date
                        from datetime import time
                        
                        # Parse dates
                        if isinstance(filters['start_date'], str):
                            start_date = parse_date(filters['start_date'])
                        else:
                            start_date = filters['start_date']
                        
                        if isinstance(filters['end_date'], str):
                            end_date = parse_date(filters['end_date'])
                        else:
                            end_date = filters['end_date']
                        
                        if start_date and end_date:
                            start_datetime = datetime.combine(start_date, time.min)
                            end_datetime = datetime.combine(end_date, time.max)
                            query['transaction_date'] = {
                                '$gte': start_datetime, 
                                '$lte': end_datetime
                            }
                    except Exception as date_error:
                        print(f"Date parsing error: {date_error}")
                
                # Other filters
                if filters.get('sales_type'):
                    query['sales_type'] = filters['sales_type']
                if filters.get('payment_method'):
                    query['payment_method'] = filters['payment_method']
                if filters.get('status'):
                    query['status'] = filters['status']
                if filters.get('source'):
                    query['source'] = filters['source']
                if filters.get('customer_id'):
                    try:
                        query['customer_id'] = ObjectId(filters['customer_id'])
                    except:
                        pass
            
            print(f"Export query: {query}")
            
            # Get transactions with a reasonable limit for export
            transactions = list(self.sales_log_collection.find(query).limit(10000))
            
            print(f"Found {len(transactions)} transactions for export")
            
            # Convert ObjectIds to strings
            for transaction in transactions:
                self.convert_object_id(transaction)
            
            return transactions
            
        except Exception as e:
            print(f"Error in get_sales_logs_for_export: {str(e)}")
            raise Exception(f"Error retrieving sales logs for export: {str(e)}")

    def get_sales_by_date_range(self, start_date, end_date, source=None):
        """
        ✅ COMPLETE THIS METHOD: Get sales by date range
        """
        try:
            query = {
                'transaction_date': {
                    '$gte': start_date,
                    '$lte': end_date
                }
            }
            
            if source:
                query['source'] = source
            
            # Get from both collections
            pos_sales = list(self.sales_collection.find(query))
            log_sales = list(self.sales_log_collection.find(query))
            
            # Combine and convert
            all_sales = []
            
            for sale in pos_sales:
                sale['collection_source'] = 'sales'
                all_sales.append(self.convert_object_id(sale))
            
            for sale in log_sales:
                sale['collection_source'] = 'sales_log'
                all_sales.append(self.convert_object_id(sale))
            
            # Sort by date
            all_sales.sort(key=lambda x: x['transaction_date'], reverse=True)
            
            return all_sales
            
        except Exception as e:
            raise Exception(f"Error fetching sales by date range: {str(e)}")

    # ================================================================
    # ENHANCED POS SALES WITH FIFO INTEGRATION (Backward Compatible)
    # ================================================================
    
    def generate_sale_id(self):
        """Generate a unique SALE-###### ID for enhanced POS sales"""
        return f"SALE-{uuid.uuid4()}"

    def calculate_loyalty_points_earned(self, subtotal_after_discount):
        return int(subtotal_after_discount * 0.20)

    def calculate_points_discount(self, points_to_redeem):
        return points_to_redeem / 4.0

    def validate_points_redemption(self, customer_id, points_to_redeem, subtotal):
        try:
            if points_to_redeem == 0:
                return {'valid': True, 'error': None}
            
            response = self.customers_table.get_item(Key={'customer_id': customer_id})
            customer = response.get('Item')
            if not customer:
                return {'valid': False, 'error': 'Customer not found'}
            
            available_points = customer.get('loyalty_points', 0)
            if available_points < points_to_redeem:
                return {'valid': False, 'error': f'Insufficient points. Available: {available_points}'}
            
            return {'valid': True, 'error': None}
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    def deduct_customer_points(self, customer_id, points_to_deduct, sale_id):
        try:
            # This should be a transactional update in a real scenario
            self.customers_table.update_item(
                Key={'customer_id': customer_id},
                UpdateExpression="SET loyalty_points = loyalty_points - :pts",
                ExpressionAttributeValues={':pts': Decimal(str(points_to_deduct))}
            )
        except Exception as e:
            logger.error(f"Error deducting points: {str(e)}")
            raise

    def award_loyalty_points(self, customer_id, points_to_award, sale_id, sale_amount):
        try:
            self.customers_table.update_item(
                Key={'customer_id': customer_id},
                UpdateExpression="SET loyalty_points = loyalty_points + :pts, last_purchase = :dt",
                ExpressionAttributeValues={
                    ':pts': Decimal(str(points_to_award)),
                    ':dt': datetime.utcnow().isoformat() + "Z"
                }
            )
        except Exception as e:
            logger.error(f"Error awarding points: {str(e)}")
            raise

    def create_enhanced_pos_sale(self, sale_data, cashier_id):
        try:
            sale_id = self.generate_sale_id()
            transaction_date = datetime.utcnow()
            
            customer_id = sale_data.get('customer_id')
            customer = None
            if customer_id:
                response = self.customers_table.get_item(Key={'customer_id': customer_id})
                customer = response.get('Item')
                if not customer:
                    raise ValueError(f"Customer {customer_id} not found")
            
            subtotal = 0
            items_with_prices = []
            for item in sale_data.get('items', []):
                response = self.products_table.get_item(Key={'product_id': item['product_id']})
                product = response.get('Item')
                if not product:
                    raise ValueError(f"Product {item['product_id']} not found")
                
                # ... (rest of the logic is complex and depends on other services)
            
            # This is a placeholder for the complex logic
            return {'success': False, 'message': 'create_enhanced_pos_sale not fully implemented for DynamoDB'}
            
        except Exception as e:
            raise Exception(f"Error creating enhanced POS sale: {str(e)}")

    def void_enhanced_sale(self, sale_id, voided_by, reason):
        try:
            # This is also a very complex method that needs careful refactoring.
            # It involves restoring stock, refunding points, and updating the sale status.
            # All of these are update operations on different tables.
            return {'success': False, 'message': 'void_enhanced_sale not fully implemented for DynamoDB'}
        except Exception as e:
            raise Exception(f"Error voiding sale: {str(e)}")
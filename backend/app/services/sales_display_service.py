from ..database import db_manager 
from ..models import SalesLog
import bcrypt
from notifications.services import notification_service
from .pos.SalesService import SalesService
from collections import defaultdict
from datetime import datetime, timedelta

class SalesDisplayService():
    def __init__(self):
        self.db = db_manager.get_database()  
        self.sales_collection = self.db.sales  
        self.online_transactions_collection = self.db.online_transactions 

    def get_sales_by_item_with_date_filter(self, start_date=None, end_date=None, include_voided=False):
        """
        Get sales by item with proper date filtering using transaction_date
        Includes option to filter out voided transactions
        """
        try:
            # Build query filter
            query_filter = {}
            
            # Date filtering
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    # Convert string to datetime if needed
                    if isinstance(start_date, str):
                        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    date_filter['$gte'] = start_date
                if end_date:
                    if isinstance(end_date, str):
                        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    # Include entire end date by setting to end of day
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    date_filter['$lte'] = end_date
                
                if date_filter:
                    query_filter['transaction_date'] = date_filter
            
            # Exclude voided transactions unless specifically included
            if not include_voided:
                query_filter['status'] = {'$ne': 'voided'}
            
            print(f"🔍 Query filter: {query_filter}")
            
            # Fetch sales data with the filter
            sales = list(self.sales_collection.find(query_filter))
            print(f"📊 Found {len(sales)} sales records")
            
            # Process products, categories, batches (keep your existing logic)
            products = self.fetch_all_products()
            categories = self.fetch_all_categories()
            batches = self.fetch_all_batches()

            # Map category_id -> category_name
            category_id_to_name = {}
            for cat in categories:
                category_id_to_name[cat.get('category_id') or cat.get('_id')] = cat.get('name') or cat.get('category_name')

            # Group batches by product_id and sum quantity_remaining
            product_id_to_stock_remaining = defaultdict(int)
            for batch in batches:
                product_id = batch.get('product_id')
                qty_remaining = batch.get('quantity_remaining', 0)
                if product_id:
                    product_id_to_stock_remaining[product_id] += qty_remaining

            # Aggregate sales items for the filtered period
            product_id_to_sold_qty = defaultdict(int)
            product_id_to_total_sales = defaultdict(float)

            def accumulate_items(container):
                for doc in container:
                    # Skip voided transactions unless included
                    if not include_voided and doc.get('status') == 'voided':
                        continue
                    
                    for item in doc.get('items', []):
                        pid = item.get('product_id')
                        if not pid:
                            continue
                        product_id_to_sold_qty[pid] += item.get('quantity', 0)
                        product_id_to_total_sales[pid] += item.get('subtotal', 0.0)

            accumulate_items(sales)

            # Build display list per product
            display_rows = []
            for p in products:
                product_id = p.get('product_id') or p.get('_id')
                category_name = category_id_to_name.get(p.get('category_id'))
                
                display_rows.append({
                    'product_id': product_id,
                    'product_name': p.get('product_name'),
                    'category_name': category_name,
                    'sku': p.get('sku') or p.get('SKU') or p.get('Sku'),
                    'unit': p.get('unit'),
                    'stock': product_id_to_stock_remaining.get(product_id, 0),
                    'items_sold': product_id_to_sold_qty.get(product_id, 0),
                    'total_sales': round(product_id_to_total_sales.get(product_id, 0.0), 2),
                    'selling_price': p.get('selling_price'),
                    'is_taxable': p.get('is_taxable'),
                })

            # Sort by total_sales desc by default
            display_rows.sort(key=lambda r: r['total_sales'], reverse=True)
            
            print(f"🎯 Final result: {len(display_rows)} products with sales data")
            return display_rows

        except Exception as e:
            print(f"❌ Error in get_sales_by_item_with_date_filter: {str(e)}")
            raise e

    def get_sales_summary_by_date_range(self, start_date, end_date):
        """
        Get summary statistics for a date range
        """
        try:
            query_filter = {
                'transaction_date': {
                    '$gte': datetime.fromisoformat(start_date.replace('Z', '+00:00')),
                    '$lte': datetime.fromisoformat(end_date.replace('Z', '+00:00')).replace(hour=23, minute=59, second=59, microsecond=999999)
                },
                'status': {'$ne': 'voided'}
            }
            
            sales = list(self.sales_collection.find(query_filter))
            
            summary = {
                'total_sales_count': len(sales),
                'total_revenue': 0,
                'total_items_sold': 0,
                'average_transaction_value': 0,
                'voided_transactions': 0
            }
            
            for sale in sales:
                summary['total_revenue'] += sale.get('total_amount', 0)
                for item in sale.get('items', []):
                    summary['total_items_sold'] += item.get('quantity', 0)
            
            if summary['total_sales_count'] > 0:
                summary['average_transaction_value'] = round(summary['total_revenue'] / summary['total_sales_count'], 2)
            
            # Count voided transactions in the period
            voided_query = {
                'transaction_date': query_filter['transaction_date'],
                'status': 'voided'
            }
            voided_count = self.sales_collection.count_documents(voided_query)
            summary['voided_transactions'] = voided_count
            
            return summary
            
        except Exception as e:
            print(f"❌ Error in get_sales_summary_by_date_range: {str(e)}")
            raise e

    # Keep your existing methods but update them to use transaction_date
    def top_selling_items(self, start_date=None, end_date=None, limit=10):
        """Updated to use transaction_date and exclude voided by default"""
        try:
            query_filter = {'status': {'$ne': 'voided'}}
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    if isinstance(start_date, str):
                        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    date_filter['$gte'] = start_date
                if end_date:
                    if isinstance(end_date, str):
                        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    date_filter['$lte'] = end_date
                
                if date_filter:
                    query_filter['transaction_date'] = date_filter
            
            sales = list(self.sales_collection.find(query_filter))
            online_transactions = list(self.online_transactions_collection.find(query_filter))
            
            # Rest of your existing logic...
            item_totals = defaultdict(lambda: {"product_name": "", "total_quantity": 0, "total_sales": 0.0})
            for sale in sales + online_transactions:
                for item in sale.get("items", []):
                    pid = item["product_id"]
                    item_totals[pid]["product_name"] = item.get("product_name", "")
                    item_totals[pid]["total_quantity"] += item.get("quantity", 0)
                    item_totals[pid]["total_sales"] += item.get("subtotal", 0)
            
            result = sorted([
                {"product_id": pid, **data}
                for pid, data in item_totals.items()
            ], key=lambda x: x["total_sales"], reverse=True)
            return result[:limit]
            
        except Exception as e:
            print(f"❌ Error in top_selling_items: {str(e)}")
            return []

    # Keep your existing helper methods
    def fetch_all_products(self):
        products = list(self.db.products.find({}))
        for p in products:
            p['_id'] = str(p['_id'])
        return products

    def fetch_all_categories(self):
        categories = list(self.db.category.find({}))
        for c in categories:
            c['_id'] = str(c['_id'])
        return categories

    def fetch_all_batches(self):
        batches = list(self.db.batches.find({}))
        for b in batches:
            b['_id'] = str(b['_id'])
        return batches

    # You can deprecate the old build_sales_by_item_display or update it to use the new method
    def build_sales_by_item_display(self, start_date=None, end_date=None):
        """Legacy method - now uses the new implementation"""
        return self.get_sales_by_item_with_date_filter(start_date, end_date)
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

# PynamoDB models – import using the exact module paths from your project
from ...models.Batches import Batch
from ...models.Categories import Category
from ...models.Product import Product
from ...models.Sales import Sale

logger = logging.getLogger(__name__)


class SalesDisplayService:
    """
    Sales Display Service – uses DynamoDB models (PynamoDB).
    Provides sales reporting and aggregation by item with date filtering.
    """

    def __init__(self):
        # No database manager – models encapsulate table access
        pass

    # -------------------------------------------------------------------------
    # Helper methods for fetching reference data
    # -------------------------------------------------------------------------

    def _fetch_all_products(self) -> List[Dict[str, Any]]:
        """Return all products as dictionaries."""
        try:
            products = []
            # Use query on the primary key "products" to get all products efficiently
            for p in Product.query("products"):
                products.append(p.to_dict())
            return products
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            return []

    def _fetch_all_categories(self) -> List[Dict[str, Any]]:
        """Return all categories as dictionaries."""
        try:
            categories = []
            for c in Category.query("categories"):
                categories.append(c.to_dict())
            return categories
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []

    def _fetch_all_batches(self) -> List[Dict[str, Any]]:
        """Return all batches as dictionaries."""
        try:
            batches = []
            for b in Batch.query("batches"):
                batches.append(b.to_dict())
            return batches
        except Exception as e:
            logger.error(f"Error fetching batches: {e}")
            return []

    # -------------------------------------------------------------------------
    # Core reporting methods
    # -------------------------------------------------------------------------

    def get_sales_by_item_with_date_filter(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        include_voided: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get sales by item with proper date filtering using transaction_date.
        Includes option to filter out voided transactions.
        """
        try:
            # Build date range condition for the GSI
            range_condition = None
            if start_date or end_date:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

                # For the GSI we need a condition on transaction_date
                if start_date and end_date:
                    # Include entire end date
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    range_condition = (Sale.transaction_date >= start_date) & (Sale.transaction_date <= end_date)
                elif start_date:
                    range_condition = Sale.transaction_date >= start_date
                elif end_date:
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    range_condition = Sale.transaction_date <= end_date

            # Fetch sales using the DateIndex GSI
            sales = []
            if range_condition:
                # Query the GSI with fixed partition key 'sales'
                for sale in Sale.date_index.query("sales", range_key_condition=range_condition):
                    if not include_voided and sale.is_voided:
                        continue
                    sales.append(sale)
            else:
                # No date filter – scan all sales (potentially expensive)
                for sale in Sale.query("sales"):
                    if not include_voided and sale.is_voided:
                        continue
                    sales.append(sale)

            logger.info(f"Found {len(sales)} sales records")

            # Fetch reference data
            products = self._fetch_all_products()
            categories = self._fetch_all_categories()
            batches = self._fetch_all_batches()

            # Map category_id -> category_name
            category_id_to_name = {}
            for cat in categories:
                cat_id = cat.get('category_id') or cat.get('id')
                cat_name = cat.get('name') or cat.get('category_name')
                if cat_id:
                    category_id_to_name[cat_id] = cat_name

            # Sum remaining stock per product from batches
            product_stock = defaultdict(int)
            for batch in batches:
                pid = batch.get('product_id')
                qty = batch.get('quantity_remaining', 0)
                if pid:
                    product_stock[pid] += qty

            # Aggregate sold quantities and revenue per product
            sold_qty = defaultdict(int)
            sold_total = defaultdict(float)

            for sale in sales:
                for item in sale.items or []:
                    pid = item.get('product_id')
                    if not pid:
                        continue
                    sold_qty[pid] += item.get('quantity', 0)
                    sold_total[pid] += item.get('subtotal', 0.0)

            # Build display rows
            display_rows = []
            for prod in products:
                pid = prod.get('product_id') or prod.get('id')
                cat_name = category_id_to_name.get(prod.get('category_id'))

                display_rows.append({
                    'product_id': pid,
                    'product_name': prod.get('product_name'),
                    'category_name': cat_name,
                    'sku': prod.get('sku') or prod.get('SKU') or prod.get('Sku'),
                    'unit': prod.get('unit'),
                    'stock': product_stock.get(pid, 0),
                    'items_sold': sold_qty.get(pid, 0),
                    'total_sales': round(sold_total.get(pid, 0.0), 2),
                    'selling_price': prod.get('selling_price'),
                    'is_taxable': prod.get('is_taxable'),
                })

            # Sort by total sales descending
            display_rows.sort(key=lambda r: r['total_sales'], reverse=True)

            logger.info(f"Returning {len(display_rows)} product sales rows")
            return display_rows

        except Exception as e:
            logger.error(f"Error in get_sales_by_item_with_date_filter: {e}")
            raise

    def get_sales_summary_by_date_range(
        self,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime]
    ) -> Dict[str, Any]:
        """
        Get summary statistics for a date range.
        """
        try:
            # Parse dates
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Query sales in the date range (exclude voided)
            range_condition = (Sale.transaction_date >= start_date) & (Sale.transaction_date <= end_date)
            sales = []
            for sale in Sale.date_index.query("sales", range_key_condition=range_condition):
                if not sale.is_voided:
                    sales.append(sale)

            summary = {
                'total_sales_count': len(sales),
                'total_revenue': 0.0,
                'total_items_sold': 0,
                'average_transaction_value': 0.0,
                'voided_transactions': 0
            }

            for sale in sales:
                summary['total_revenue'] += sale.total_amount or 0.0
                for item in sale.items or []:
                    summary['total_items_sold'] += item.get('quantity', 0)

            if summary['total_sales_count'] > 0:
                summary['average_transaction_value'] = round(
                    summary['total_revenue'] / summary['total_sales_count'], 2
                )

            # Count voided transactions separately
            voided_count = 0
            for sale in Sale.date_index.query("sales", range_key_condition=range_condition):
                if sale.is_voided:
                    voided_count += 1
            summary['voided_transactions'] = voided_count

            return summary

        except Exception as e:
            logger.error(f"Error in get_sales_summary_by_date_range: {e}")
            raise

    def top_selling_items(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Return top selling items (by revenue) within an optional date range.
        Excludes voided transactions by default.
        """
        try:
            # Build date condition if provided
            range_condition = None
            if start_date or end_date:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if start_date and end_date:
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    range_condition = (Sale.transaction_date >= start_date) & (Sale.transaction_date <= end_date)
                elif start_date:
                    range_condition = Sale.transaction_date >= start_date
                elif end_date:
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    range_condition = Sale.transaction_date <= end_date

            # Fetch sales (using index if possible)
            sales = []
            if range_condition:
                for sale in Sale.date_index.query("sales", range_key_condition=range_condition):
                    if not sale.is_voided:
                        sales.append(sale)
            else:
                for sale in Sale.query("sales"):
                    if not sale.is_voided:
                        sales.append(sale)

            # Aggregate item totals
            item_totals = defaultdict(lambda: {"product_name": "", "total_quantity": 0, "total_sales": 0.0})
            for sale in sales:
                for item in sale.items or []:
                    pid = item.get('product_id')
                    if not pid:
                        continue
                    item_totals[pid]["product_name"] = item.get('product_name', "")
                    item_totals[pid]["total_quantity"] += item.get('quantity', 0)
                    item_totals[pid]["total_sales"] += item.get('subtotal', 0.0)

            # Sort and limit
            result = sorted(
                [{"product_id": pid, **data} for pid, data in item_totals.items()],
                key=lambda x: x["total_sales"],
                reverse=True
            )
            return result[:limit]

        except Exception as e:
            logger.error(f"Error in top_selling_items: {e}")
            return []

    # -------------------------------------------------------------------------
    # Legacy method – kept for compatibility
    # -------------------------------------------------------------------------

    def build_sales_by_item_display(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """Legacy method – now uses the new implementation."""
        return self.get_sales_by_item_with_date_filter(start_date, end_date)
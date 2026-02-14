# app/services/sales_by_category_service.py
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union

from ...models.Sales import Sale
from ...models.Product import Product
from ...models.Categories import Category

logger = logging.getLogger(__name__)


class SalesByCategoryService:
    """
    Sales By Category Service – uses DynamoDB models (PynamoDB).
    Aggregates sales by category with date filtering and trend analysis.
    """

    def __init__(self):
        # No direct database client; all operations go through PynamoDB models.
        pass

    # -------------------------------------------------------------------------
    # Helper methods to fetch reference data
    # -------------------------------------------------------------------------

    def _fetch_all_products(self) -> List[Product]:
        """Return all Product objects (excluding soft‑deleted)."""
        try:
            # Query the primary key "products" to get all products
            return list(Product.query("products"))
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            return []

    def _fetch_all_categories(self) -> List[Category]:
        """Return all Category objects (excluding soft‑deleted)."""
        try:
            return list(Category.query("categories"))
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []

    # -------------------------------------------------------------------------
    # Core aggregation method
    # -------------------------------------------------------------------------

    def get_sales_by_category_with_date_filter(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        include_voided: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch total sales and quantities grouped by category.
        Supports date filtering and optional inclusion of voided transactions.
        Returns a list of category aggregates sorted by total sales descending.
        """
        try:
            # Parse dates if provided as strings
            if start_date and isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date and isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                # Include the entire end day
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Build range condition for the GSI
            range_condition = None
            if start_date and end_date:
                range_condition = (Sale.transaction_date >= start_date) & (Sale.transaction_date <= end_date)
            elif start_date:
                range_condition = Sale.transaction_date >= start_date
            elif end_date:
                range_condition = Sale.transaction_date <= end_date

            # Fetch sales using the DateIndex GSI (hash key = "sales")
            sales = []
            if range_condition:
                for sale in Sale.date_index.query("sales", range_key_condition=range_condition):
                    if not include_voided and sale.is_voided:
                        continue
                    sales.append(sale)
            else:
                # No date filter – scan all sales (can be large; consider adding a default time window)
                for sale in Sale.query("sales"):
                    if not include_voided and sale.is_voided:
                        continue
                    sales.append(sale)

            logger.info(f"Found {len(sales)} sales records")

            # Fetch all products and categories
            products = self._fetch_all_products()
            categories = self._fetch_all_categories()

            # Build lookup maps using full SKs (e.g., "PROD-00001", "CAT-0001")
            product_to_category = {}
            for prod in products:
                product_to_category[prod.sk] = prod.category_id   # category_id is the full category SK

            category_id_to_name = {}
            for cat in categories:
                category_id_to_name[cat.sk] = cat.category_name

            # Aggregators: per category we track total sales, total items, sets of product IDs and transaction IDs
            category_totals = defaultdict(lambda: {
                "total_sales": 0.0,
                "total_items": 0,
                "products": set(),
                "transactions": set()
            })

            for sale in sales:
                transaction_id = sale.sk   # e.g., "SALE-00001"
                for item in sale.items or []:
                    product_id = item.get('product_id')
                    if not product_id:
                        continue

                    quantity = item.get('quantity', 0)
                    subtotal = item.get('subtotal', 0.0)

                    cat_id = product_to_category.get(product_id)
                    if not cat_id:
                        continue

                    data = category_totals[cat_id]
                    data["total_sales"] += subtotal
                    data["total_items"] += quantity
                    data["products"].add(product_id)
                    data["transactions"].add(transaction_id)

            # Build final result list
            results = []
            for cat_id, data in category_totals.items():
                cat_name = category_id_to_name.get(cat_id, "Unknown Category")
                total_sales = round(data["total_sales"], 2)
                total_items = data["total_items"]
                product_count = len(data["products"])
                transaction_count = len(data["transactions"])

                avg_sale_per_transaction = round(total_sales / transaction_count, 2) if transaction_count > 0 else 0
                avg_items_per_transaction = round(total_items / transaction_count, 2) if transaction_count > 0 else 0

                results.append({
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "total_sales": total_sales,
                    "total_items_sold": total_items,
                    "product_count": product_count,
                    "transaction_count": transaction_count,
                    "avg_sale_per_transaction": avg_sale_per_transaction,
                    "avg_items_per_transaction": avg_items_per_transaction
                })

            # Sort by total sales descending
            results.sort(key=lambda x: x["total_sales"], reverse=True)

            logger.info(f"Aggregated {len(results)} categories")
            return results

        except Exception as e:
            logger.error(f"Error in get_sales_by_category_with_date_filter: {e}")
            raise

    # -------------------------------------------------------------------------
    # Convenience methods
    # -------------------------------------------------------------------------

    def get_top_categories(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Return only the top N categories sorted by total sales.
        """
        try:
            all_categories = self.get_sales_by_category_with_date_filter(start_date, end_date)
            return all_categories[:limit]
        except Exception as e:
            logger.error(f"Error in get_top_categories: {e}")
            return []

    def get_category_performance_trends(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get category performance with trend analysis (growth compared to previous period).
        If both start_date and end_date are provided, computes growth vs. the preceding period of same length.
        """
        try:
            # Parse dates
            if start_date and isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date and isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

            # Get current period data
            current_data = self.get_sales_by_category_with_date_filter(start_date, end_date, include_voided=False)

            # Compute previous period if both dates are given
            if start_date and end_date:
                period_days = (end_date - start_date).days
                prev_start = start_date - timedelta(days=period_days)
                prev_end = start_date - timedelta(seconds=1)   # exclusive of start_date

                previous_data = self.get_sales_by_category_with_date_filter(prev_start, prev_end, include_voided=False)

                # Map previous data by category_id
                prev_map = {item['category_id']: item for item in previous_data}

                # Add trend info to current data
                for cat in current_data:
                    cat_id = cat['category_id']
                    prev = prev_map.get(cat_id)
                    if prev:
                        current_sales = cat['total_sales']
                        prev_sales = prev['total_sales']
                        if prev_sales > 0:
                            growth = ((current_sales - prev_sales) / prev_sales) * 100
                        else:
                            growth = 100.0 if current_sales > 0 else 0.0
                        cat['sales_growth_percent'] = round(growth, 2)
                        cat['trend'] = 'up' if growth > 0 else 'down' if growth < 0 else 'stable'
                    else:
                        cat['sales_growth_percent'] = 100.0
                        cat['trend'] = 'new'

            return current_data

        except Exception as e:
            logger.error(f"Error in get_category_performance_trends: {e}")
            # Fallback to basic data without trends
            return self.get_sales_by_category_with_date_filter(start_date, end_date, include_voided=False)
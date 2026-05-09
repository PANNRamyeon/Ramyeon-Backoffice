"""
Sales Analytics Service (v5 — DynamoDB)
Replaces legacy MongoDB analytics: salesReport.py, sales_display_service.py, sales_by_category.py
"""
from datetime import datetime, date, time, timedelta
from collections import defaultdict
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SalesAnalyticsService:
    """
    DynamoDB-based sales analytics.  All queries go through the Sale PynamoDB model.
    Products and categories are fetched once per call and cached in local dicts.
    """

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _get_sales(self, start_date: Optional[datetime], end_date: Optional[datetime],
                   include_voided: bool = False) -> List:
        from models.Sales import Sale
        try:
            all_sales = list(Sale.query("sales"))
            if start_date and end_date:
                sales = [
                    s for s in all_sales
                    if getattr(s, "transaction_date", None)
                    and start_date <= s.transaction_date <= end_date
                ]
            else:
                sales = all_sales
            if not include_voided:
                sales = [
                    s for s in sales
                    if not getattr(s, "is_voided", False) and getattr(s, "status", "") != "cancelled"
                ]
            return sales
        except Exception as e:
            logger.error("_get_sales error: %s", e)
            return []

    def _get_product_map(self) -> Dict[str, Dict]:
        """Return {product_id: product_dict} for all non-deleted products."""
        from models.Product import Product
        try:
            product_map = {}
            for p in Product.query("products"):
                if p.isDeleted:
                    continue
                pid = p.sk
                product_map[pid] = {
                    "product_id": pid,
                    "product_name": p.product_name,
                    "category_id": p.category_id if hasattr(p, "category_id") else None,
                    "sku": p.sku if hasattr(p, "sku") else "",
                    "selling_price": float(p.selling_price) if hasattr(p, "selling_price") and p.selling_price else 0.0,
                    "cost_price": float(p.cost_price) if hasattr(p, "cost_price") and p.cost_price else 0.0,
                    "unit": p.unit if hasattr(p, "unit") else "",
                    "total_stock": float(p.total_stock) if hasattr(p, "total_stock") and p.total_stock else 0,
                    "status": p.status if hasattr(p, "status") else "active",
                    "is_taxable": bool(p.is_taxable) if hasattr(p, "is_taxable") else True,
                }
            return product_map
        except Exception as e:
            logger.error("_get_product_map error: %s", e)
            return {}

    def _get_category_map(self) -> Dict[str, str]:
        """Return {category_id: category_name} for all non-deleted categories."""
        from models.Categories import Category
        try:
            cat_map = {}
            for c in Category.query("category"):
                if not c.isDeleted:
                    cat_map[c.sk] = c.category_name
            return cat_map
        except Exception as e:
            logger.error("_get_category_map error: %s", e)
            return {}

    def _dates_for_frequency(self, frequency: str):
        """Convert frequency shorthand to (start_datetime, end_datetime)."""
        today = date.today()
        if frequency == "daily":
            return (datetime.combine(today, time.min), datetime.combine(today, time.max))
        elif frequency == "weekly":
            monday = today - timedelta(days=today.weekday())
            return (datetime.combine(monday, time.min),
                    datetime.combine(monday + timedelta(days=6), time.max))
        elif frequency == "monthly":
            start = date(today.year, today.month, 1)
            if today.month == 12:
                end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(today.year, today.month + 1, 1) - timedelta(days=1)
            return (datetime.combine(start, time.min), datetime.combine(end, time.max))
        else:  # yearly
            return (datetime.combine(date(today.year, 1, 1), time.min),
                    datetime.combine(date(today.year, 12, 31), time.max))

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def get_sales_summary(self, start_date=None, end_date=None, frequency=None) -> Dict:
        """
        Aggregate totals: revenue, transactions, discounts, by payment method.

        Args:
            start_date: datetime or None
            end_date: datetime or None
            frequency: 'daily'|'weekly'|'monthly'|'yearly' (overrides dates)

        Returns:
            dict with total_transactions, total_revenue, average_transaction,
            by_payment_method, and period info.
        """
        if frequency:
            start_date, end_date = self._dates_for_frequency(frequency)

        sales = self._get_sales(start_date, end_date)

        total_revenue = 0.0
        total_discount = 0.0
        total_tax = 0.0
        payment_breakdown: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "amount": 0.0})

        for sale in sales:
            rev = float(sale.total_amount) if sale.total_amount else 0.0
            total_revenue += rev
            total_discount += float(sale.discount_amount) if sale.discount_amount else 0.0
            total_tax += float(sale.tax_amount) if sale.tax_amount else 0.0
            method = (sale.payment_method or "unknown").lower()
            payment_breakdown[method]["count"] += 1
            payment_breakdown[method]["amount"] += rev

        count = len(sales)
        return {
            "total_transactions": count,
            "total_revenue": round(total_revenue, 2),
            "total_discount": round(total_discount, 2),
            "total_tax": round(total_tax, 2),
            "average_transaction": round(total_revenue / count, 2) if count else 0.0,
            "by_payment_method": {k: {"count": v["count"], "amount": round(v["amount"], 2)}
                                  for k, v in payment_breakdown.items()},
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
                "frequency": frequency,
            },
        }

    def get_sales_by_item(self, start_date=None, end_date=None, frequency=None,
                          include_voided=False) -> List[Dict]:
        """
        Per-product sales totals joined with current stock info.

        Returns list sorted by total_sales descending.
        Every active product appears (items_sold = 0 if no sales in range).
        """
        if frequency:
            start_date, end_date = self._dates_for_frequency(frequency)

        sales = self._get_sales(start_date, end_date, include_voided)
        product_map = self._get_product_map()
        category_map = self._get_category_map()

        qty_by_product: Dict[str, int] = defaultdict(int)
        rev_by_product: Dict[str, float] = defaultdict(float)

        for sale in sales:
            for item in (sale.items or []):
                pid = item.product_id
                if not pid:
                    continue
                qty_by_product[pid] += int(float(item.quantity))
                rev_by_product[pid] += float(item.subtotal) if item.subtotal else 0.0

        rows = []
        for pid, product in product_map.items():
            cat_name = category_map.get(product["category_id"] or "", "Uncategorized")
            rows.append({
                "product_id": pid,
                "product_name": product["product_name"],
                "category_name": cat_name,
                "sku": product["sku"],
                "unit": product["unit"],
                "selling_price": product["selling_price"],
                "stock": product["total_stock"],
                "is_taxable": product["is_taxable"],
                "items_sold": qty_by_product.get(pid, 0),
                "total_sales": round(rev_by_product.get(pid, 0.0), 2),
            })

        rows.sort(key=lambda r: r["total_sales"], reverse=True)
        return rows

    def get_top_items(self, start_date=None, end_date=None, frequency=None,
                      limit: int = 5) -> List[Dict]:
        """Return top N items by total_sales."""
        if frequency:
            start_date, end_date = self._dates_for_frequency(frequency)
        return self.get_sales_by_item(start_date, end_date)[:limit]

    def get_sales_by_category(self, start_date=None, end_date=None, frequency=None,
                               include_voided=False, include_trends=False) -> List[Dict]:
        """
        Per-category sales aggregation with optional trend vs. prior period.

        Returns list sorted by total_sales descending.
        """
        if frequency:
            start_date, end_date = self._dates_for_frequency(frequency)

        sales = self._get_sales(start_date, end_date, include_voided)
        product_map = self._get_product_map()
        category_map = self._get_category_map()

        cat_agg: Dict[str, Dict] = defaultdict(lambda: {
            "total_sales": 0.0,
            "total_items_sold": 0,
            "product_ids": set(),
            "transaction_ids": set(),
        })

        for sale in sales:
            sid = sale.sk
            for item in (sale.items or []):
                pid = item.product_id
                product = product_map.get(pid)
                if not product:
                    continue
                cid = product.get("category_id") or ""
                if not cid:
                    continue
                subtotal = float(item.subtotal) if item.subtotal else 0.0
                cat_agg[cid]["total_sales"] += subtotal
                cat_agg[cid]["total_items_sold"] += int(float(item.quantity))
                cat_agg[cid]["product_ids"].add(pid)
                cat_agg[cid]["transaction_ids"].add(sid)

        results = []
        for cid, data in cat_agg.items():
            tc = len(data["transaction_ids"])
            ts = round(data["total_sales"], 2)
            ti = data["total_items_sold"]
            results.append({
                "category_id": cid,
                "category_name": category_map.get(cid, "Unknown Category"),
                "total_sales": ts,
                "total_items_sold": ti,
                "product_count": len(data["product_ids"]),
                "transaction_count": tc,
                "avg_sale_per_transaction": round(ts / tc, 2) if tc else 0.0,
                "avg_items_per_transaction": round(ti / tc, 2) if tc else 0.0,
            })

        results.sort(key=lambda x: x["total_sales"], reverse=True)

        if include_trends and start_date and end_date:
            period_days = max((end_date - start_date).days, 1)
            prev_end = start_date - timedelta(seconds=1)
            prev_start = prev_end - timedelta(days=period_days)
            prev_results = self.get_sales_by_category(prev_start, prev_end)
            prev_map = {r["category_id"]: r["total_sales"] for r in prev_results}

            for r in results:
                prev_sales = prev_map.get(r["category_id"], 0)
                if prev_sales > 0:
                    growth = ((r["total_sales"] - prev_sales) / prev_sales) * 100
                    r["sales_growth_percent"] = round(growth, 2)
                    r["trend"] = "up" if growth > 0 else "down" if growth < 0 else "stable"
                elif r["total_sales"] > 0:
                    r["sales_growth_percent"] = 100.0
                    r["trend"] = "new"
                else:
                    r["sales_growth_percent"] = 0.0
                    r["trend"] = "stable"

        return results

    def get_top_categories(self, start_date=None, end_date=None, frequency=None,
                           limit: int = 5) -> List[Dict]:
        """Return top N categories by total_sales."""
        if frequency:
            start_date, end_date = self._dates_for_frequency(frequency)
        return self.get_sales_by_category(start_date, end_date)[:limit]

    def get_sales_by_period(self, start_date: datetime, end_date: datetime,
                            period_type: str = "daily") -> Dict:
        """
        Group sales totals into daily / weekly / monthly buckets for chart data.

        Args:
            start_date: datetime (required)
            end_date: datetime (required)
            period_type: 'daily' | 'weekly' | 'monthly'

        Returns:
            {period_type, breakdown: [...], period_summary: {...}}

        Raises:
            ValueError: if period_type is invalid
        """
        if period_type == "daily":
            return self._daily_breakdown(start_date, end_date)
        elif period_type == "weekly":
            return self._weekly_breakdown(start_date, end_date)
        elif period_type == "monthly":
            return self._monthly_breakdown(start_date, end_date)
        else:
            raise ValueError(f"period_type must be 'daily', 'weekly', or 'monthly' — got '{period_type}'")

    # ------------------------------------------------------------------ #
    # Period breakdown helpers                                             #
    # ------------------------------------------------------------------ #

    def _daily_breakdown(self, start_date: datetime, end_date: datetime) -> Dict:
        cur = start_date.date()
        end = end_date.date()
        breakdown = []
        while cur <= end:
            ds = datetime.combine(cur, time.min)
            de = datetime.combine(cur, time.max)
            summary = self.get_sales_summary(ds, de)
            breakdown.append({
                "date": cur.isoformat(),
                "day_name": cur.strftime("%A"),
                "total_transactions": summary["total_transactions"],
                "total_revenue": summary["total_revenue"],
            })
            cur += timedelta(days=1)

        total_rev = sum(d["total_revenue"] for d in breakdown)
        total_tx = sum(d["total_transactions"] for d in breakdown)
        n = len(breakdown)
        return {
            "period_type": "daily",
            "breakdown": breakdown,
            "period_summary": {
                "total_revenue": round(total_rev, 2),
                "total_transactions": total_tx,
                "total_days": n,
                "average_daily_revenue": round(total_rev / n, 2) if n else 0.0,
            },
        }

    def _weekly_breakdown(self, start_date: datetime, end_date: datetime) -> Dict:
        cur = start_date.date()
        cur -= timedelta(days=cur.weekday())  # snap to Monday
        end = end_date.date()
        breakdown = []
        while cur <= end:
            week_end = cur + timedelta(days=6)
            ws = datetime.combine(cur, time.min)
            we = datetime.combine(min(week_end, end), time.max)
            summary = self.get_sales_summary(ws, we)
            breakdown.append({
                "week_start": cur.isoformat(),
                "week_end": min(week_end, end).isoformat(),
                "week_number": cur.isocalendar()[1],
                "total_transactions": summary["total_transactions"],
                "total_revenue": summary["total_revenue"],
            })
            cur += timedelta(days=7)

        total_rev = sum(d["total_revenue"] for d in breakdown)
        total_tx = sum(d["total_transactions"] for d in breakdown)
        n = len(breakdown)
        return {
            "period_type": "weekly",
            "breakdown": breakdown,
            "period_summary": {
                "total_revenue": round(total_rev, 2),
                "total_transactions": total_tx,
                "total_weeks": n,
                "average_weekly_revenue": round(total_rev / n, 2) if n else 0.0,
            },
        }

    def _monthly_breakdown(self, start_date: datetime, end_date: datetime) -> Dict:
        cur_year, cur_month = start_date.year, start_date.month
        end_year, end_month = end_date.year, end_date.month
        breakdown = []
        while (cur_year, cur_month) <= (end_year, end_month):
            month_start = datetime(cur_year, cur_month, 1, 0, 0, 0)
            if cur_month == 12:
                month_end = datetime(cur_year + 1, 1, 1) - timedelta(seconds=1)
            else:
                month_end = datetime(cur_year, cur_month + 1, 1) - timedelta(seconds=1)
            month_end = min(month_end, end_date)
            summary = self.get_sales_summary(month_start, month_end)
            breakdown.append({
                "year": cur_year,
                "month": cur_month,
                "month_name": month_start.strftime("%B"),
                "period_label": month_start.strftime("%b %Y"),
                "total_transactions": summary["total_transactions"],
                "total_revenue": summary["total_revenue"],
            })
            if cur_month == 12:
                cur_year += 1
                cur_month = 1
            else:
                cur_month += 1

        total_rev = sum(d["total_revenue"] for d in breakdown)
        total_tx = sum(d["total_transactions"] for d in breakdown)
        n = len(breakdown)
        return {
            "period_type": "monthly",
            "breakdown": breakdown,
            "period_summary": {
                "total_revenue": round(total_rev, 2),
                "total_transactions": total_tx,
                "total_months": n,
                "average_monthly_revenue": round(total_rev / n, 2) if n else 0.0,
            },
        }

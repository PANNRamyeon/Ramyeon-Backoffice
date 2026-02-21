from datetime import date, time, timedelta, datetime

from ...database import db_manager
from ..marketing.promotionCon import PromoConnection

class SalesReport:
    """
    Clean Sales Report API - No redundant methods
    Three core methods handle all reporting needs
    """
    def __init__(self):
       # self.db = db_manager.get_database()
        if db_manager.connect_to_cloud():
            client = db_manager.current_client
            self.db = client['pos_system']  # pos_system might be on cloud
        else:
            raise Exception("Could not connect to the database")
        # 🐛 DEBUG: Check what database we're connected to
        print(f"🔍 Connected to database: {self.db.name}")
        print(f"🔍 Available collections: {self.db.list_collection_names()}")
        
        self.sales_collection = self.db.sales 
        self.sales_log_collection = self.db.sales_log  
        self.products_collection = self.db.products
        self.promotions_collection = self.db.promotions
        self.promo_connection = PromoConnection()

    def convert_object_id(self, document):
        """Convert ObjectId to string for JSON serialization"""
        if document and '_id' in document:
            document['_id'] = str(document['_id'])
        return document

    # ================================================================
    # CORE API - 3 ESSENTIAL METHODS ONLY
    # ================================================================

    def get_sales_summary(self, date_range=None, include_source=None):
        """
        🎯 MAIN METHOD: Get aggregated sales summary
        
        Args:
            date_range: {'start': datetime, 'end': datetime} or None for all time
            include_source: ['pos', 'manual', 'csv'] or None for all sources
        
        Returns:
            Summary with totals, averages, source breakdown, and recent transactions preview
        
        Examples:
            # All sales ever
            get_sales_summary()
            
            # All sales today
            today_range = {'start': datetime.combine(date.today(), time.min), 
                          'end': datetime.combine(date.today(), time.max)}
            get_sales_summary(today_range)
            
            # Only POS sales this month
            month_range = {'start': datetime(2024, 3, 1), 'end': datetime(2024, 3, 31)}
            get_sales_summary(month_range, ['pos'])
            
            # Only manual/CSV sales
            get_sales_summary(None, ['manual', 'csv'])
        """
        try:
            # Build date filter
            date_filter = {}
            if date_range:
                date_filter = {
                    'transaction_date': {
                        '$gte': date_range['start'],
                        '$lte': date_range['end']
                    }
                }
            
            # Build source filter
            source_filter = {}
            if include_source:
                source_filter = {'source': {'$in': include_source}}
            
            # Combine filters
            query = {}
            if date_filter and source_filter:
                query = {'$and': [date_filter, source_filter]}
            elif date_filter:
                query = date_filter
            elif source_filter:
                query = source_filter
    
            # 🐛 DEBUG: Add these lines to see what's happening
            print(f"🔍 DEBUG - Query being used: {query}")
            print(f"🔍 DEBUG - Date range: {date_range}")
            print(f"🔍 DEBUG - Include source: {include_source}")

            # Get data from both collections
            pos_sales = list(self.sales_collection.find(query))
            log_sales = list(self.sales_log_collection.find(query))

            # 🐛 DEBUG: Check what we found
            print(f"🔍 DEBUG - POS sales found: {len(pos_sales)}")
            print(f"🔍 DEBUG - Log sales found: {len(log_sales)}")
            print(f"🔍 DEBUG - Sales collection name: {self.sales_collection.name}")
            print(f"🔍 DEBUG - Log collection name: {self.sales_log_collection.name}")

            if log_sales:
                print(f"🔍 DEBUG - First log sale: {log_sales[0]}")
            else:
                print("🔍 DEBUG - No log sales found, checking raw query...")
                # Test raw query
                raw_count = self.sales_log_collection.count_documents(query)
                print(f"🔍 DEBUG - Raw count from sales_log: {raw_count}")
                
                # Test with empty query
                total_count = self.sales_log_collection.count_documents({})
                print(f"🔍 DEBUG - Total documents in sales_log: {total_count}")

            # Get data from both collections
            pos_sales = list(self.sales_collection.find(query))
            log_sales = list(self.sales_log_collection.find(query))
            
            # Calculate totals
            pos_totals = self._calculate_pos_totals(pos_sales)
            log_totals = self._calculate_log_totals(log_sales)
            
            # Combine totals
            combined_totals = {
                'total_transactions': pos_totals['count'] + log_totals['count'],
                'total_revenue': round(pos_totals['revenue'] + log_totals['revenue'], 2),
                'gross_revenue': round(pos_totals['gross'] + log_totals['gross'], 2),
                'total_discounts': round(pos_totals['discounts'], 2),
                'average_transaction': 0
            }
            
            # Calculate average
            if combined_totals['total_transactions'] > 0:
                combined_totals['average_transaction'] = round(
                    combined_totals['total_revenue'] / combined_totals['total_transactions'], 2
                )
            
            # Source breakdown
            source_breakdown = {
                'pos': {
                    'count': pos_totals['count'],
                    'revenue': round(pos_totals['revenue'], 2),
                    'percentage': 0
                },
                'manual_csv': {
                    'count': log_totals['count'],
                    'revenue': round(log_totals['revenue'], 2),
                    'percentage': 0
                }
            }
            
            # Calculate percentages
            if combined_totals['total_revenue'] > 0:
                source_breakdown['pos']['percentage'] = round(
                    (pos_totals['revenue'] / combined_totals['total_revenue']) * 100, 1
                )
                source_breakdown['manual_csv']['percentage'] = round(
                    (log_totals['revenue'] / combined_totals['total_revenue']) * 100, 1
                )
            
            # Recent transactions preview
            recent_transactions = []
            for sale in pos_sales[-10:]:
                recent_transactions.append(self._normalize_pos_transaction(sale))
            for sale in log_sales[-10:]:
                recent_transactions.append(self._normalize_log_transaction(sale))
            
            recent_transactions.sort(key=lambda x: x['transaction_date'], reverse=True)
            
            return {
                'summary': combined_totals,
                'source_breakdown': source_breakdown,
                'transactions_preview': recent_transactions[:20],
                'filters_applied': {
                    'date_range': date_range,
                    'include_source': include_source
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting sales summary: {str(e)}")

    def get_sales_transactions(self, date_range=None, include_source=None, limit=100):
        """
        📋 Get individual transaction records (not summary)
        
        Args:
            date_range: {'start': datetime, 'end': datetime} or None for all time
            include_source: ['pos', 'manual', 'csv'] or None for all sources
            limit: Maximum number of transactions to return
        
        Returns:
            List of individual transaction records + basic summary
        
        Use for:
            - Export to Excel/CSV
            - Transaction history tables
            - Detailed transaction lists
        """
        try:
            # Get all transactions
            all_transactions = self._get_all_transactions(date_range, include_source)
            
            # Apply limit
            if limit:
                all_transactions = all_transactions[:limit]
            
            # Calculate basic stats
            total_count = len(all_transactions)
            total_revenue = sum(txn['total_amount'] for txn in all_transactions)
            
            return {
                'transactions': all_transactions,
                'summary': {
                    'total_transactions': total_count,
                    'total_revenue': round(total_revenue, 2),
                    'average_transaction': round(total_revenue / total_count, 2) if total_count > 0 else 0,
                    'limited_to': limit
                },
                'filters_applied': {
                    'date_range': date_range,
                    'include_source': include_source
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting sales transactions: {str(e)}")

    def get_sales_by_period(self, start_date, end_date, period_type='daily', include_source=None):
        """
        📊 Get sales grouped by time periods for charts/trends
        
        Args:
            start_date: Start date (date or datetime)
            end_date: End date (date or datetime)
            period_type: 'daily', 'weekly', or 'monthly'
            include_source: ['pos', 'manual', 'csv'] or None for all sources
        
        Returns:
            Data grouped by periods + period summary
        
        Use for:
            - Charts and graphs
            - Trend analysis
            - Period comparisons
        """
        try:
            if period_type == 'daily':
                return self._get_daily_breakdown(start_date, end_date, include_source)
            elif period_type == 'weekly':
                return self._get_weekly_breakdown(start_date, end_date, include_source)
            elif period_type == 'monthly':
                return self._get_monthly_breakdown(start_date, end_date, include_source)
            else:
                raise ValueError("period_type must be 'daily', 'weekly', or 'monthly'")
                
        except Exception as e:
            raise Exception(f"Error getting sales by period: {str(e)}")

    # ================================================================
    # CONVENIENCE METHODS (Built on top of core API)
    # ================================================================

    def get_todays_sales(self):
        """Get today's sales summary"""
        today = date.today()
        date_range = {
            'start': datetime.combine(today, time.min),
            'end': datetime.combine(today, time.max)
        }
        return self.get_sales_summary(date_range)

    def get_weekly_sales(self):
        """Get this week's sales summary (Monday to Sunday)"""
        today = date.today()
        days_since_monday = today.weekday()
        start_of_week = today - timedelta(days=days_since_monday)
        end_of_week = start_of_week + timedelta(days=6)
        
        date_range = {
            'start': datetime.combine(start_of_week, time.min),
            'end': datetime.combine(end_of_week, time.max)
        }
        
        result = self.get_sales_summary(date_range)
        result['week_info'] = {
            'start_date': start_of_week.isoformat(),
            'end_date': end_of_week.isoformat(),
            'week_number': start_of_week.isocalendar()[1]
        }
        return result

    def get_monthly_sales(self):
        """Get current month's sales summary"""
        today = date.today()
        start_of_month = date(today.year, today.month, 1)
        
        if today.month == 12:
            end_of_month = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)
        
        date_range = {
            'start': datetime.combine(start_of_month, time.min),
            'end': datetime.combine(end_of_month, time.max)
        }
        
        result = self.get_sales_summary(date_range)
        result['month_info'] = {
            'year': today.year,
            'month': today.month,
            'month_name': today.strftime('%B'),
            'start_date': start_of_month.isoformat(),
            'end_date': end_of_month.isoformat()
        }
        return result

    def get_yearly_sales(self):
        """Get current year's sales summary"""
        today = date.today()
        start_of_year = date(today.year, 1, 1)
        end_of_year = date(today.year, 12, 31)
        
        date_range = {
            'start': datetime.combine(start_of_year, time.min),
            'end': datetime.combine(end_of_year, time.max)
        }
        
        result = self.get_sales_summary(date_range)
        result['year_info'] = {
            'year': today.year,
            'start_date': start_of_year.isoformat(),
            'end_date': end_of_year.isoformat()
        }
        return result

    def get_sales_comparison(self, period='week'):
        """Compare current vs previous period"""
        try:
            if period == 'week':
                current = self.get_weekly_sales()
                previous = self.get_previous_week_sales()
            elif period == 'month':
                current = self.get_monthly_sales()
                previous = self.get_previous_month_sales()
            else:
                raise ValueError("Period must be 'week' or 'month'")
            
            current_revenue = current['summary']['total_revenue']
            previous_revenue = previous['summary']['total_revenue']
            
            change = current_revenue - previous_revenue
            change_percent = 0
            if previous_revenue > 0:
                change_percent = (change / previous_revenue) * 100
            
            return {
                'current_period': current,
                'previous_period': previous,
                'comparison': {
                    'revenue_change': round(change, 2),
                    'revenue_change_percent': round(change_percent, 2),
                    'performance': 'improved' if change > 0 else 'declined' if change < 0 else 'same'
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting sales comparison: {str(e)}")

    def get_previous_week_sales(self):
        """Get previous week's sales summary"""
        today = date.today()
        days_since_monday = today.weekday()
        start_of_current_week = today - timedelta(days=days_since_monday)
        
        start_of_previous_week = start_of_current_week - timedelta(days=7)
        end_of_previous_week = start_of_previous_week + timedelta(days=6)
        
        date_range = {
            'start': datetime.combine(start_of_previous_week, time.min),
            'end': datetime.combine(end_of_previous_week, time.max)
        }
        
        result = self.get_sales_summary(date_range)
        result['week_info'] = {
            'start_date': start_of_previous_week.isoformat(),
            'end_date': end_of_previous_week.isoformat(),
            'week_number': start_of_previous_week.isocalendar()[1],
            'week_type': 'previous_week'
        }
        return result

    def get_previous_month_sales(self):
        """Get previous month's sales summary"""
        today = date.today()
        
        if today.month == 1:
            prev_year = today.year - 1
            prev_month = 12
        else:
            prev_year = today.year
            prev_month = today.month - 1
        
        start_of_prev_month = date(prev_year, prev_month, 1)
        
        if prev_month == 12:
            end_of_prev_month = date(prev_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_prev_month = date(prev_year, prev_month + 1, 1) - timedelta(days=1)
        
        date_range = {
            'start': datetime.combine(start_of_prev_month, time.min),
            'end': datetime.combine(end_of_prev_month, time.max)
        }
        
        result = self.get_sales_summary(date_range)
        result['month_info'] = {
            'year': prev_year,
            'month': prev_month,
            'month_name': start_of_prev_month.strftime('%B'),
            'start_date': start_of_prev_month.isoformat(),
            'end_date': end_of_prev_month.isoformat(),
            'month_type': 'previous_month'
        }
        return result

    def get_dashboard_summary(self):
        """Get comprehensive dashboard data"""
        try:
            today_sales = self.get_todays_sales()
            week_sales = self.get_weekly_sales()
            month_sales = self.get_monthly_sales()
            week_comparison = self.get_sales_comparison('week')
            
            return {
                'today': today_sales['summary'],
                'this_week': week_sales['summary'],
                'this_month': month_sales['summary'],
                'week_vs_last_week': week_comparison['comparison'],
                'source_breakdown_today': today_sales['source_breakdown'],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error getting dashboard summary: {str(e)}")

    # ================================================================
    # HELPER METHODS (Internal use only)
    # ================================================================

    def _get_all_transactions(self, date_range=None, include_source=None):
        """Get all individual transactions from both collections"""
        match_conditions = []
        
        if date_range:
            date_filter = {
                "transaction_date": {
                    "$gte": date_range['start'],
                    "$lte": date_range['end']
                }
            }
            match_conditions.append(date_filter)

        if include_source:
            source_filter = {"source": {"$in": include_source}}
            match_conditions.append(source_filter)

        match_stage = {"$and": match_conditions} if match_conditions else {}

        # Get from both collections
        pos_sales = list(self.sales_collection.find(match_stage))
        sales_log_entries = list(self.sales_log_collection.find(match_stage))

        # Normalize formats
        unified_sales = []
        
        for sale in pos_sales:
            unified_sales.append(self._normalize_pos_sale(sale))

        for sale in sales_log_entries:
            unified_sales.append(self._normalize_sales_log(sale))

        # Sort by date
        unified_sales.sort(key=lambda x: x['transaction_date'], reverse=True)
        return unified_sales

    def _get_daily_breakdown(self, start_date, end_date, include_source=None):
        """Get day-by-day breakdown"""
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        
        daily_breakdown = []
        current_date = start_date
        
        while current_date <= end_date:
            day_range = {
                'start': datetime.combine(current_date, time.min),
                'end': datetime.combine(current_date, time.max)
            }
            
            day_summary = self.get_sales_summary(day_range, include_source)
            
            daily_data = {
                'date': current_date.isoformat(),
                'day_name': current_date.strftime('%A'),
                'summary': day_summary['summary'],
                'source_breakdown': day_summary['source_breakdown']
            }
            
            daily_breakdown.append(daily_data)
            current_date += timedelta(days=1)
        
        total_revenue = sum(day['summary']['total_revenue'] for day in daily_breakdown)
        total_transactions = sum(day['summary']['total_transactions'] for day in daily_breakdown)
        
        return {
            'period_type': 'daily',
            'breakdown': daily_breakdown,
            'period_summary': {
                'total_revenue': round(total_revenue, 2),
                'total_transactions': total_transactions,
                'total_days': len(daily_breakdown),
                'average_daily_revenue': round(total_revenue / len(daily_breakdown), 2) if daily_breakdown else 0
            }
        }

    def _get_weekly_breakdown(self, start_date, end_date, include_source=None):
        """Get week-by-week breakdown"""
        # Implementation for weekly grouping
        return {'period_type': 'weekly', 'breakdown': [], 'period_summary': {}}

    def _get_monthly_breakdown(self, start_date, end_date, include_source=None):
        """Get month-by-month breakdown"""
        # Implementation for monthly grouping
        return {'period_type': 'monthly', 'breakdown': [], 'period_summary': {}}

    def _calculate_pos_totals(self, pos_sales):
        """Calculate totals from POS sales"""
        count = len(pos_sales)
        revenue = sum(sale.get('final_amount', 0) for sale in pos_sales)
        gross = sum(sale.get('total_amount', 0) for sale in pos_sales)
        discounts = sum(sale.get('total_discount', 0) for sale in pos_sales)
        
        return {
            'count': count,
            'revenue': revenue,
            'gross': gross,
            'discounts': discounts
        }
    
    def _calculate_log_totals(self, log_sales):
        """Calculate totals from sales_log"""
        count = len(log_sales)
        revenue = sum(sale.get('total_amount', 0) for sale in log_sales)
        gross = revenue
        
        return {
            'count': count,
            'revenue': revenue,
            'gross': gross
        }
    
    def _normalize_pos_transaction(self, sale):
        """Convert POS transaction to standard format"""
        return {
            '_id': str(sale['_id']),
            'transaction_date': sale['transaction_date'],
            'total_amount': sale.get('final_amount', 0),
            'source': 'pos',
            'payment_method': sale.get('payment_method', 'cash'),
            'items_count': len(sale.get('items', [])),
            'cashier_id': sale.get('cashier_id'),
            'promotion_applied': sale.get('promotion_applied')
        }
    
    def _normalize_log_transaction(self, sale):
        """Convert sales_log transaction to standard format"""
        return {
            '_id': str(sale['_id']),
            'transaction_date': sale['transaction_date'],
            'total_amount': sale.get('total_amount', 0),
            'source': sale.get('source', 'manual'),
            'payment_method': sale.get('payment_method', 'cash'),
            'items_count': len(sale.get('item_list', [])),
            'user_id': str(sale['user_id']) if sale.get('user_id') else None,
            'sales_type': sale.get('sales_type', 'retail')
        }

    def _normalize_pos_sale(self, pos_sale):
        """Convert POS sale to unified format"""
        return {
            '_id': str(pos_sale['_id']),
            'transaction_date': pos_sale['transaction_date'],
            'total_amount': pos_sale.get('final_amount', pos_sale.get('total_amount', 0)),
            'gross_amount': pos_sale.get('total_amount', pos_sale.get('final_amount', 0)),
            'discount_amount': pos_sale.get('total_discount', 0),
            'payment_method': pos_sale.get('payment_method', 'cash'),
            'customer_id': pos_sale.get('customer_id'),
            'cashier_id': pos_sale.get('cashier_id'),
            'user_id': pos_sale.get('cashier_id'),
            'promotion_applied': pos_sale.get('promotion_applied'),
            'items': pos_sale.get('items', []),
            'source': 'pos',
            'status': pos_sale.get('status', 'completed'),
            'collection': 'sales'
        }

    def _normalize_sales_log(self, sales_log):
        """Convert sales log to unified format"""
        return {
            '_id': str(sales_log['_id']),
            'transaction_date': sales_log['transaction_date'],
            'total_amount': sales_log['total_amount'],
            'gross_amount': sales_log['total_amount'],
            'discount_amount': 0,
            'payment_method': sales_log.get('payment_method', 'cash'),
            'customer_id': str(sales_log['customer_id']) if sales_log.get('customer_id') else None,
            'cashier_id': str(sales_log['user_id']) if sales_log.get('user_id') else None,
            'user_id': str(sales_log['user_id']) if sales_log.get('user_id') else None,
            'promotion_applied': None,
            'items': self._convert_item_list_to_items(sales_log.get('item_list', [])),
            'source': sales_log.get('source', 'manual'),
            'status': sales_log.get('status', 'completed'),
            'collection': 'sales_log'
        }

    def _convert_item_list_to_items(self, item_list):
        """Convert sales log item_list to POS items format"""
        items = []
        for item in item_list:
            items.append({
                'product_id': item.get('item_code', ''),
                'product_name': item.get('item_name', ''),
                'quantity': item.get('quantity', 0),
                'price': item.get('unit_price', 0),
                'total': item.get('total_price', 0),
                'unit': item.get('unit_of_measure', 'pc')
            })
        return items

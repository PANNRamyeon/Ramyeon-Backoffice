"""
Online Transaction Model - Following ERD Specification
PK = "online_transactions", SK = "ONLINE-########" (8-digit format)
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST
from datetime import datetime, timezone, timedelta
import logging
import pytz
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# ============= NESTED MAP ATTRIBUTES =============
class OnlineSaleItem(MapAttribute):
    """MapAttribute for items in an online transaction"""
    product_id = UnicodeAttribute()
    product_name = UnicodeAttribute()
    quantity = NumberAttribute()  # integer
    price = NumberAttribute()  # float
    subtotal = NumberAttribute()  # float


class ServiceFeeBreakdownItem(MapAttribute):
    """MapAttribute for service_fee_breakdown items"""
    platform = NumberAttribute(default=0)  # Platform fee amount (float)


class StatusHistoryItem(MapAttribute):
    """MapAttribute for status_history items"""
    status = UnicodeAttribute()
    timestamp = UTCDateTimeAttribute()


# ============= GLOBAL SECONDARY INDEXES =============
class CustomerIdIndex(GlobalSecondaryIndex):
    """
    GSI for querying transactions by customer_id
    Essential for customer order history
    """
    class Meta:
        index_name = 'online-transaction-customer-id-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    customer_id = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class OrderStatusIndex(GlobalSecondaryIndex):
    """
    GSI for querying transactions by order_status
    Essential for order management dashboard
    """
    class Meta:
        index_name = 'online-transaction-order-status-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    order_status = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class PaymentStatusIndex(GlobalSecondaryIndex):
    """
    GSI for querying transactions by payment_status
    Essential for payment monitoring and reconciliation
    """
    class Meta:
        index_name = 'online-transaction-payment-status-index'
        projection = AllProjection()
        read_capacity_units = 10
        write_capacity_units = 10
    
    payment_status = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


# ============= MAIN ONLINE TRANSACTION MODEL =============
class OnlineTransaction(Model):
    """
    ONLINE TRANSACTION MODEL - Following ERD with Enhanced Validation
    
    ERD Fields (following exactly including field name typos):
    - PK = online_transactions
    - SK = ONLINE-######## (8-digit)
    - customer_id (string)
    - customer_name (string)
    - customer_email (string)
    - customer_phone (string)
    - transaction_date (ISODATE)
    - transaction_date_local (ISODATE)
    - Timezone (string) - Note: Capital T as per ERD
    - utc_offset_minutes (integer)
    - delivery_address (string)
    - delivery_type (string)
    - items (array)
    - subtotal (float)
    - points_rdeemed (float) - ERD typo, we follow exactly
    - ponts_discount (float) - ERD typo, we follow exactly
    - subtotal_after_discount (float)
    - delivery_fee (float)
    - service_fee (float) - Changed from ERD's "integer" to float for practicality
    - service_fee_breakdown (array)
    - total_amount (float) - Changed from ERD's "integer" to float for practicality
    - payment_method (string)
    - payment_status (string)
    - payment_reference (string)
    - order_status (string)
    - status (string)
    - notes (string)
    - status_history (array)
    - loyalty_points_earned (float)
    - created_at (ISODATE)
    - updated_at (ISODATE)
    - cancellation_reason (string)
    - cancelled_by (string)
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        #if DYNAMODB_LOCAL:
        #    host = DYNAMODB_LOCAL_HOST
        
        # Higher capacity for transaction processing
        read_capacity_units = 15
        write_capacity_units = 20
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="online_transactions")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "ONLINE-00000001" (8-digit)
    
    # ============= GSI DEFINITIONS =============
    customer_id_index = CustomerIdIndex()
    order_status_index = OrderStatusIndex()
    payment_status_index = PaymentStatusIndex()
    
    # ============= CUSTOMER INFORMATION =============
    customer_id = UnicodeAttribute()
    customer_name = UnicodeAttribute()
    customer_email = UnicodeAttribute()
    customer_phone = UnicodeAttribute()
    
    # ============= TRANSACTION TIMING =============
    transaction_date = UTCDateTimeAttribute()  # UTC time
    transaction_date_local = UTCDateTimeAttribute()  # Local time
    Timezone = UnicodeAttribute()  # Capital T as per ERD
    utc_offset_minutes = NumberAttribute()
    
    # ============= DELIVERY INFORMATION =============
    delivery_address = UnicodeAttribute()
    delivery_type = UnicodeAttribute()  # delivery, pickup, curbside
    
    # ============= ITEMS IN THE ORDER =============
    items = ListAttribute(of=OnlineSaleItem)
    
    # ============= FINANCIAL BREAKDOWN =============
    subtotal = NumberAttribute()  # float
    points_rdeemed = NumberAttribute(default=0.0)  # ERD typo: points_rdeemed
    ponts_discount = NumberAttribute(default=0.0)   # ERD typo: ponts_discount
    subtotal_after_discount = NumberAttribute()  # float
    delivery_fee = NumberAttribute(default=0.0)  # float
    service_fee = NumberAttribute(default=0.0)   # float (changed from ERD's integer)
    
    # ============= SERVICE FEE BREAKDOWN =============
    service_fee_breakdown = ListAttribute(of=ServiceFeeBreakdownItem, default=list)
    
    # ============= TOTALS =============
    total_amount = NumberAttribute()  # float (changed from ERD's integer)
    
    # ============= PAYMENT INFORMATION =============
    payment_method = UnicodeAttribute()  # credit_card, paypal, apple_pay, google_pay, cash
    payment_status = UnicodeAttribute()  # pending, paid, failed, refunded, refund_pending
    payment_reference = UnicodeAttribute(null=True)
    
    # ============= ORDER STATUS =============
    order_status = UnicodeAttribute(default="pending")  # pending, confirmed, processing, shipped, delivered, cancelled
    status = UnicodeAttribute(default="active")  # active, cancelled, archived
    
    # ============= NOTES AND HISTORY =============
    notes = UnicodeAttribute(null=True)
    status_history = ListAttribute(of=StatusHistoryItem, default=list)
    
    # ============= LOYALTY POINTS =============
    loyalty_points_earned = NumberAttribute(default=0.0)
    
    # ============= TIMESTAMPS =============
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    
    # ============= CANCELLATION INFORMATION =============
    cancellation_reason = UnicodeAttribute(null=True)
    cancelled_by = UnicodeAttribute(null=True)
    
    # ============= VALIDATION METHODS =============
    
    @staticmethod
    def validate_financial_consistency(subtotal: float, points_discount: float,
                                      delivery_fee: float, service_fee: float,
                                      subtotal_after_discount: float, total_amount: float) -> tuple[bool, str]:
        """
        Validate financial calculations for consistency
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Check subtotal_after_discount calculation
            calculated_subtotal_after_discount = subtotal - points_discount
            if abs(calculated_subtotal_after_discount - subtotal_after_discount) > 0.01:  # Allow small rounding difference
                return False, f"subtotal_after_discount mismatch. Expected: {calculated_subtotal_after_discount}, Got: {subtotal_after_discount}"
            
            # Check total_amount calculation
            calculated_total = subtotal_after_discount + delivery_fee + service_fee
            if abs(calculated_total - total_amount) > 0.01:  # Allow small rounding difference
                return False, f"total_amount mismatch. Expected: {calculated_total}, Got: {total_amount}"
            
            # Check non-negative values
            if subtotal < 0 or points_discount < 0 or delivery_fee < 0 or service_fee < 0:
                return False, "Financial values cannot be negative"
            
            # Check discount doesn't exceed subtotal
            if points_discount > subtotal:
                return False, f"Discount ({points_discount}) cannot exceed subtotal ({subtotal})"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def validate_timezone(timezone_str: str) -> tuple[bool, int]:
        """
        Validate timezone and get UTC offset
        
        Returns:
            tuple: (is_valid, utc_offset_minutes)
        """
        try:
            # Try to get timezone from pytz
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            offset = now.utcoffset()
            
            if offset:
                offset_minutes = int(offset.total_seconds() / 60)
                return True, offset_minutes
            else:
                return False, 0
                
        except pytz.exceptions.UnknownTimeZoneError:
            # Check common timezone formats
            common_timezones = {
                "UTC": 0,
                "UTC+0": 0,
                "GMT": 0,
                "EST": -300,  # Eastern Standard Time: UTC-5
                "PST": -480,  # Pacific Standard Time: UTC-8
                "CST": -360,  # Central Standard Time: UTC-6
                "MST": -420,  # Mountain Standard Time: UTC-7
                "AEDT": 660,  # Australian Eastern Daylight Time: UTC+11
                "JST": 540,   # Japan Standard Time: UTC+9
                "CET": 60,    # Central European Time: UTC+1
                "EET": 120,   # Eastern European Time: UTC+2
            }
            
            if timezone_str in common_timezones:
                return True, common_timezones[timezone_str]
            else:
                return False, 0
    
    @staticmethod
    def validate_items(items: List[Dict]) -> tuple[bool, str, List[OnlineSaleItem], float]:
        """
        Validate items and calculate subtotal
        
        Returns:
            tuple: (is_valid, error_message, parsed_items, subtotal)
        """
        try:
            parsed_items = []
            subtotal = 0.0
            
            for i, item in enumerate(items):
                # Check required fields
                required_fields = ['product_id', 'product_name', 'quantity', 'price']
                for field in required_fields:
                    if field not in item:
                        return False, f"Item {i+1} missing required field: {field}", [], 0.0
                
                # Validate data types
                try:
                    quantity = float(item['quantity'])
                    price = float(item['price'])
                    
                    if quantity <= 0:
                        return False, f"Item {i+1} quantity must be positive", [], 0.0
                    if price < 0:
                        return False, f"Item {i+1} price cannot be negative", [], 0.0
                    
                    item_subtotal = quantity * price
                    
                    # Create OnlineSaleItem
                    parsed_item = OnlineSaleItem(
                        product_id=str(item['product_id']),
                        product_name=str(item['product_name']),
                        quantity=quantity,
                        price=price,
                        subtotal=item_subtotal
                    )
                    parsed_items.append(parsed_item)
                    subtotal += item_subtotal
                    
                except (ValueError, TypeError) as e:
                    return False, f"Item {i+1} invalid numeric value: {str(e)}", [], 0.0
            
            if len(parsed_items) == 0:
                return False, "At least one item is required", [], 0.0
            
            return True, "", parsed_items, subtotal
            
        except Exception as e:
            return False, f"Items validation error: {str(e)}", [], 0.0
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_transaction(cls, customer_id: str, customer_name: str, customer_email: str,
                          customer_phone: str, delivery_address: str, delivery_type: str,
                          items: List[Dict], timezone_str: str = "UTC",
                          payment_method: str = "credit_card",
                          points_redeemed: float = 0.0, points_discount: float = 0.0,
                          delivery_fee: float = 0.0, service_fee: float = 0.0,
                          service_fee_breakdown: List[Dict] = None,
                          notes: str = None) -> 'OnlineTransaction':
        """
        Create a new online transaction with comprehensive validation
        
        Args:
            customer_id: Customer ID (required)
            customer_name: Customer name (required)
            customer_email: Customer email (required)
            customer_phone: Customer phone (required)
            delivery_address: Delivery address (required)
            delivery_type: Delivery type (delivery, pickup, curbside)
            items: List of item dictionaries
            timezone_str: Customer timezone (default: UTC)
            payment_method: Payment method
            points_redeemed: Points redeemed (ERD: points_rdeemed)
            points_discount: Points discount (ERD: ponts_discount)
            delivery_fee: Delivery fee
            service_fee: Service fee
            service_fee_breakdown: List of platform fee breakdowns
            notes: Order notes
        
        Returns:
            OnlineTransaction: Created and saved transaction
        """
        try:
            # ============= VALIDATE INPUTS =============
            
            # Validate required fields
            required_fields = {
                'customer_id': customer_id,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
                'delivery_address': delivery_address,
                'delivery_type': delivery_type,
            }
            
            for field_name, value in required_fields.items():
                if not value or not str(value).strip():
                    raise ValueError(f"Required field missing or empty: {field_name}")
            
            # Validate timezone
            timezone_valid, utc_offset = cls.validate_timezone(timezone_str)
            if not timezone_valid:
                raise ValueError(f"Invalid timezone: {timezone_str}")
            
            # Validate items
            items_valid, items_error, parsed_items, subtotal = cls.validate_items(items)
            if not items_valid:
                raise ValueError(items_error)
            
            # Validate financial values
            if points_redeemed < 0 or points_discount < 0 or delivery_fee < 0 or service_fee < 0:
                raise ValueError("Financial values cannot be negative")
            
            # Calculate financials
            subtotal_after_discount = subtotal - points_discount
            if subtotal_after_discount < 0:
                raise ValueError(f"Discount ({points_discount}) cannot exceed subtotal ({subtotal})")
            
            total_amount = subtotal_after_discount + delivery_fee + service_fee
            
            # Validate financial consistency
            valid, error_msg = cls.validate_financial_consistency(
                subtotal=subtotal,
                points_discount=points_discount,
                delivery_fee=delivery_fee,
                service_fee=service_fee,
                subtotal_after_discount=subtotal_after_discount,
                total_amount=total_amount
            )
            if not valid:
                raise ValueError(error_msg)
            
            # ============= CREATE TRANSACTION =============
            
            # Generate 8-digit SK using utils.py
            sk = generate_sk('ONLINE-', 'online_transaction_seq')
            
            # Get current time in UTC and local
            now_utc = datetime.utcnow()
            tz = pytz.timezone(timezone_str)
            now_local = datetime.now(tz)
            
            # Parse service fee breakdown
            parsed_service_fee_breakdown = []
            if service_fee_breakdown:
                for breakdown in service_fee_breakdown:
                    if 'platform' in breakdown:
                        parsed_service_fee_breakdown.append(
                            ServiceFeeBreakdownItem(platform=float(breakdown['platform']))
                        )
            
            # Create transaction
            transaction = cls(
                pk="online_transactions",
                sk=sk,
                customer_id=customer_id,
                customer_name=customer_name.strip(),
                customer_email=customer_email.strip().lower(),
                customer_phone=customer_phone.strip(),
                transaction_date=now_utc,
                transaction_date_local=now_local,
                Timezone=timezone_str,
                utc_offset_minutes=utc_offset,
                delivery_address=delivery_address.strip(),
                delivery_type=delivery_type.strip().lower(),
                items=parsed_items,
                subtotal=subtotal,
                points_rdeemed=points_redeemed,  # ERD typo
                ponts_discount=points_discount,   # ERD typo
                subtotal_after_discount=subtotal_after_discount,
                delivery_fee=delivery_fee,
                service_fee=service_fee,
                service_fee_breakdown=parsed_service_fee_breakdown,
                total_amount=total_amount,
                payment_method=payment_method.strip().lower(),
                payment_status="pending",
                payment_reference=None,
                order_status="pending",
                status="active",
                notes=notes.strip() if notes else None,
                loyalty_points_earned=0.0,  # Will be calculated later
                created_at=now_utc,
                updated_at=now_utc
            )
            
            # Add initial status to history
            transaction.add_status_history("pending", now_utc)
            
            # Save transaction
            transaction.save()
            
            logger.info(f"Online transaction created: {sk} for customer {customer_id}, Total: ${total_amount:.2f}")
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to create online transaction: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, transaction_id: str) -> 'OnlineTransaction | None':
        """
        Get transaction by ID
        
        Args:
            transaction_id: Format "ONLINE-00000001" or just "00000001"
        
        Returns:
            OnlineTransaction or None if not found
        """
        try:
            # Ensure proper format
            if not transaction_id.startswith('ONLINE-'):
                transaction_id = f"ONLINE-{transaction_id.zfill(8)}"  # Pad to 8 digits
            
            return cls.get("online_transactions", transaction_id)
        except cls.DoesNotExist:
            logger.warning(f"Online transaction not found: {transaction_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching transaction {transaction_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_customer_id(cls, customer_id: str, limit: int = 50,
                          start_date: datetime = None, end_date: datetime = None) -> list:
        """
        Get transactions by customer ID using GSI
        
        Args:
            customer_id: Customer ID to search
            limit: Maximum number of transactions to return
            start_date: Start date for filtering (inclusive)
            end_date: End date for filtering (inclusive)
        
        Returns:
            list: List of customer transactions
        """
        try:
            if start_date and end_date:
                # Date range query
                return list(cls.customer_id_index.query(
                    customer_id,
                    cls.created_at.between(start_date, end_date),
                    scan_index_forward=False,  # Newest first
                    limit=limit
                ))
            else:
                # All transactions for customer
                return list(cls.customer_id_index.query(
                    customer_id,
                    scan_index_forward=False,  # Newest first
                    limit=limit
                ))
        except Exception as e:
            logger.error(f"Error getting transactions for customer {customer_id}: {str(e)}")
            return []
    
    @classmethod
    def get_by_order_status(cls, order_status: str, limit: int = 100,
                           start_date: datetime = None, end_date: datetime = None) -> list:
        """
        Get transactions by order status using GSI
        
        Args:
            order_status: Order status to filter by
            limit: Maximum number of transactions to return
            start_date: Start date for filtering (inclusive)
            end_date: End date for filtering (inclusive)
        
        Returns:
            list: List of transactions with specified status
        """
        try:
            if start_date and end_date:
                # Date range query
                return list(cls.order_status_index.query(
                    order_status,
                    cls.created_at.between(start_date, end_date),
                    scan_index_forward=False,  # Newest first
                    limit=limit
                ))
            else:
                # All transactions with this status
                return list(cls.order_status_index.query(
                    order_status,
                    scan_index_forward=False,  # Newest first
                    limit=limit
                ))
        except Exception as e:
            logger.error(f"Error getting transactions by order status {order_status}: {str(e)}")
            return []
    
    @classmethod
    def get_by_payment_status(cls, payment_status: str, limit: int = 100,
                             start_date: datetime = None, end_date: datetime = None) -> list:
        """
        Get transactions by payment status using GSI
        
        Args:
            payment_status: Payment status to filter by
            limit: Maximum number of transactions to return
            start_date: Start date for filtering (inclusive)
            end_date: End date for filtering (inclusive)
        
        Returns:
            list: List of transactions with specified payment status
        """
        try:
            if start_date and end_date:
                # Date range query
                return list(cls.payment_status_index.query(
                    payment_status,
                    cls.created_at.between(start_date, end_date),
                    scan_index_forward=False,  # Newest first
                    limit=limit
                ))
            else:
                # All transactions with this payment status
                return list(cls.payment_status_index.query(
                    payment_status,
                    scan_index_forward=False,  # Newest first
                    limit=limit
                ))
        except Exception as e:
            logger.error(f"Error getting transactions by payment status {payment_status}: {str(e)}")
            return []
    
    @classmethod
    def get_pending_orders(cls, limit: int = 100) -> list:
        """
        Get all pending orders (both order_status='pending' and payment_status='pending')
        
        Args:
            limit: Maximum number of transactions to return
        
        Returns:
            list: List of pending orders
        """
        try:
            pending_orders = []
            
            # Get orders with pending order status
            order_pending = cls.get_by_order_status("pending", limit=limit//2)
            pending_orders.extend(order_pending)
            
            # Get orders with pending payment status
            payment_pending = cls.get_by_payment_status("pending", limit=limit//2)
            
            # Combine and deduplicate
            seen_ids = {order.sk for order in pending_orders}
            for order in payment_pending:
                if order.sk not in seen_ids:
                    pending_orders.append(order)
                    seen_ids.add(order.sk)
            
            # Sort by created_at (newest first)
            pending_orders.sort(key=lambda x: x.created_at, reverse=True)
            
            return pending_orders[:limit]
        except Exception as e:
            logger.error(f"Error getting pending orders: {str(e)}")
            return []
    
    @classmethod
    def get_recent_transactions(cls, hours: int = 24, limit: int = 100) -> list:
        """
        Get recent transactions
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of transactions to return
        
        Returns:
            list: List of recent transactions
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            transactions = []
            
            for transaction in cls.query(
                "online_transactions",
                cls.created_at >= cutoff,
                scan_index_forward=False,  # Newest first
                limit=limit
            ):
                transactions.append(transaction)
            
            return transactions
        except Exception as e:
            logger.error(f"Error getting recent transactions: {str(e)}")
            return []
    
    @classmethod
    def get_dashboard_statistics(cls, days: int = 30) -> dict:
        """
        Get dashboard statistics for online transactions
        
        Args:
            days: Number of days to analyze
        
        Returns:
            dict: Dashboard statistics
        """
        try:
            from collections import defaultdict
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Initialize counters
            stats = {
                "period_days": days,
                "total_transactions": 0,
                "total_revenue": 0.0,
                "total_items": 0,
                "unique_customers": set(),
                "status_counts": defaultdict(int),
                "payment_method_counts": defaultdict(int),
                "delivery_type_counts": defaultdict(int),
                "daily_revenue": defaultdict(float),
                "hourly_volume": defaultdict(int)
            }
            
            # Scan recent transactions
            for transaction in cls.query(
                "online_transactions",
                cls.created_at >= cutoff,
                limit=10000  # Safety limit
            ):
                stats["total_transactions"] += 1
                stats["total_revenue"] += float(transaction.total_amount)
                stats["unique_customers"].add(transaction.customer_id)
                
                # Count items
                for item in transaction.items:
                    stats["total_items"] += int(item.quantity)
                
                # Count by status
                stats["status_counts"][transaction.order_status] += 1
                stats["payment_method_counts"][transaction.payment_method] += 1
                stats["delivery_type_counts"][transaction.delivery_type] += 1
                
                # Aggregate by date
                date_key = transaction.created_at.date().isoformat()
                stats["daily_revenue"][date_key] += float(transaction.total_amount)
                
                # Aggregate by hour
                hour_key = transaction.created_at.strftime("%H:00")
                stats["hourly_volume"][hour_key] += 1
            
            # Calculate derived metrics
            avg_order_value = stats["total_revenue"] / stats["total_transactions"] if stats["total_transactions"] > 0 else 0
            avg_items_per_order = stats["total_items"] / stats["total_transactions"] if stats["total_transactions"] > 0 else 0
            
            return {
                "period": {
                    "days": stats["period_days"],
                    "start_date": cutoff.date().isoformat(),
                    "end_date": datetime.utcnow().date().isoformat()
                },
                "overall": {
                    "total_transactions": stats["total_transactions"],
                    "total_revenue": round(stats["total_revenue"], 2),
                    "total_items": stats["total_items"],
                    "unique_customers": len(stats["unique_customers"]),
                    "avg_order_value": round(avg_order_value, 2),
                    "avg_items_per_order": round(avg_items_per_order, 1)
                },
                "breakdowns": {
                    "by_status": dict(stats["status_counts"]),
                    "by_payment_method": dict(stats["payment_method_counts"]),
                    "by_delivery_type": dict(stats["delivery_type_counts"])
                },
                "time_series": {
                    "daily_revenue": dict(stats["daily_revenue"]),
                    "hourly_volume": dict(stats["hourly_volume"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard statistics: {str(e)}")
            return {}
    
    # ============= INSTANCE METHODS =============
    
    def add_status_history(self, status: str, timestamp: datetime = None):
        """
        Add status to history
        
        Args:
            status: Status to add
            timestamp: Timestamp (defaults to now)
        """
        try:
            status_item = StatusHistoryItem(
                status=status,
                timestamp=timestamp or datetime.utcnow()
            )
            self.status_history.append(status_item)
            self.updated_at = datetime.utcnow()
            return self
        except Exception as e:
            logger.error(f"Failed to add status history to transaction {self.sk}: {str(e)}")
            raise
    
    def update_order_status(self, new_status: str, notes: str = None):
        """
        Update order status with validation
        
        Args:
            new_status: New order status
            notes: Optional notes about the status change
        
        Returns:
            OnlineTransaction: Updated transaction
        """
        try:
            valid_statuses = {"pending", "confirmed", "processing", "shipped", "delivered", "cancelled"}
            if new_status not in valid_statuses:
                raise ValueError(f"Invalid order status: {new_status}. Must be one of: {valid_statuses}")
            
            old_status = self.order_status
            self.order_status = new_status
            self.add_status_history(new_status)
            
            if notes:
                self.notes = (self.notes + "\n" + notes) if self.notes else notes
            
            # Auto-update payment status for certain order statuses
            if new_status == "cancelled":
                if self.payment_status == "paid":
                    self.payment_status = "refund_pending"
                self.status = "cancelled"
            elif new_status == "delivered" and self.payment_status == "pending":
                self.payment_status = "paid"
            
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Transaction {self.sk} order status updated: {old_status} -> {new_status}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to update order status for transaction {self.sk}: {str(e)}")
            raise
    
    def update_payment_status(self, new_status: str, payment_reference: str = None):
        """
        Update payment status with validation
        
        Args:
            new_status: New payment status
            payment_reference: Payment reference/transaction ID
        
        Returns:
            OnlineTransaction: Updated transaction
        """
        try:
            valid_statuses = {"pending", "paid", "failed", "refunded", "refund_pending"}
            if new_status not in valid_statuses:
                raise ValueError(f"Invalid payment status: {new_status}. Must be one of: {valid_statuses}")
            
            old_status = self.payment_status
            self.payment_status = new_status
            
            if payment_reference:
                self.payment_reference = payment_reference
            
            # Auto-update order status for certain payment statuses
            if new_status == "paid" and self.order_status == "pending":
                self.update_order_status("confirmed")
            elif new_status == "failed" and self.order_status == "pending":
                self.update_order_status("payment_failed")
            elif new_status == "refunded" and self.order_status != "cancelled":
                self.update_order_status("cancelled")
            
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Transaction {self.sk} payment status updated: {old_status} -> {new_status}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to update payment status for transaction {self.sk}: {str(e)}")
            raise
    
    def apply_points_discount(self, points_redeemed: float, discount_amount: float):
        """
        Apply loyalty points discount to the order
        
        Args:
            points_redeemed: Points redeemed (ERD: points_rdeemed)
            discount_amount: Discount amount in currency (ERD: ponts_discount)
        
        Returns:
            OnlineTransaction: Updated transaction
        """
        try:
            # Validate
            if points_redeemed < 0 or discount_amount < 0:
                raise ValueError("Points redeemed and discount amount cannot be negative")
            
            if discount_amount > self.subtotal:
                raise ValueError(f"Discount ({discount_amount}) cannot exceed subtotal ({self.subtotal})")
            
            # Update points fields (with ERD typo field names)
            self.points_rdeemed = points_redeemed
            self.ponts_discount = discount_amount
            
            # Recalculate financials
            self.subtotal_after_discount = self.subtotal - discount_amount
            self.total_amount = self.subtotal_after_discount + self.delivery_fee + self.service_fee
            
            # Validate financial consistency
            valid, error_msg = self.validate_financial_consistency(
                subtotal=self.subtotal,
                points_discount=discount_amount,
                delivery_fee=self.delivery_fee,
                service_fee=self.service_fee,
                subtotal_after_discount=self.subtotal_after_discount,
                total_amount=self.total_amount
            )
            if not valid:
                raise ValueError(error_msg)
            
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Applied points discount to transaction {self.sk}: {points_redeemed} points = ${discount_amount:.2f}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to apply points discount to transaction {self.sk}: {str(e)}")
            raise
    
    def calculate_loyalty_points(self, points_per_dollar: float = 1.0):
        """
        Calculate loyalty points earned from this transaction
        
        Args:
            points_per_dollar: Points earned per dollar spent (default: 1)
        
        Returns:
            OnlineTransaction: Updated transaction
        """
        try:
            # Points are typically earned on the subtotal after discounts
            self.loyalty_points_earned = self.subtotal_after_discount * points_per_dollar
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Calculated loyalty points for transaction {self.sk}: {self.loyalty_points_earned} points")
            return self
            
        except Exception as e:
            logger.error(f"Failed to calculate loyalty points for transaction {self.sk}: {str(e)}")
            raise
    
    def cancel_order(self, reason: str, cancelled_by: str, notes: str = None):
        """
        Cancel the order
        
        Args:
            reason: Reason for cancellation
            cancelled_by: Who cancelled the order
            notes: Additional notes
        
        Returns:
            OnlineTransaction: Updated transaction
        """
        try:
            self.cancellation_reason = reason
            self.cancelled_by = cancelled_by
            
            # Update order status
            self.update_order_status("cancelled", notes)
            
            # Update payment status if needed
            if self.payment_status == "paid":
                self.payment_status = "refund_pending"
            
            self.updated_at = datetime.utcnow()
            self.save()
            
            logger.info(f"Transaction {self.sk} cancelled by {cancelled_by}: {reason}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to cancel transaction {self.sk}: {str(e)}")
            raise
    
    def get_financial_summary(self) -> dict:
        """
        Get financial summary of the transaction
        
        Returns:
            dict: Financial summary
        """
        return {
            "subtotal": float(self.subtotal) if self.subtotal else 0.0,
            "points_redeemed": float(self.points_rdeemed) if self.points_rdeemed else 0.0,
            "points_discount": float(self.ponts_discount) if self.ponts_discount else 0.0,
            "subtotal_after_discount": float(self.subtotal_after_discount) if self.subtotal_after_discount else 0.0,
            "delivery_fee": float(self.delivery_fee) if self.delivery_fee else 0.0,
            "service_fee": float(self.service_fee) if self.service_fee else 0.0,
            "total_amount": float(self.total_amount) if self.total_amount else 0.0,
            "loyalty_points_earned": float(self.loyalty_points_earned) if self.loyalty_points_earned else 0.0,
            "net_revenue": float(self.total_amount - self.delivery_fee - self.service_fee) if self.total_amount else 0.0
        }
    
    def get_items_summary(self) -> dict:
        """
        Get summary of items in the order
        
        Returns:
            dict: Items summary
        """
        total_quantity = 0
        for item in self.items:
            total_quantity += int(item.quantity)
        
        return {
            "total_items": len(self.items),
            "total_quantity": total_quantity,
            "average_item_price": float(self.subtotal / len(self.items)) if self.items else 0.0
        }
    
    def get_status_timeline(self) -> list:
        """
        Get chronological status timeline
        
        Returns:
            list: Status timeline
        """
        timeline = []
        for history in self.status_history:
            timeline.append({
                "status": history.status,
                "timestamp": history.timestamp.isoformat() if history.timestamp else None,
                "time_ago": self._get_time_ago(history.timestamp) if history.timestamp else None
            })
        return sorted(timeline, key=lambda x: x["timestamp"] if x["timestamp"] else "")
    
    def _get_time_ago(self, timestamp: datetime) -> str:
        """Get human-readable time ago string"""
        delta = datetime.utcnow() - timestamp
        
        if delta.days > 365:
            years = delta.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
        elif delta.days > 30:
            months = delta.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        elif delta.days > 0:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "just now"
    
    def to_dict(self) -> dict:
        """
        Convert transaction to dictionary for API response
        
        Returns:
            dict: Complete transaction information
        """
        try:
            transaction_dict = {
                "transaction_id": self.sk,
                "customer": {
                    "customer_id": self.customer_id,
                    "customer_name": self.customer_name,
                    "customer_email": self.customer_email,
                    "customer_phone": self.customer_phone
                },
                "timing": {
                    "transaction_date_utc": self.transaction_date.isoformat() if self.transaction_date else None,
                    "transaction_date_local": self.transaction_date_local.isoformat() if self.transaction_date_local else None,
                    "timezone": self.Timezone,
                    "utc_offset_minutes": self.utc_offset_minutes,
                    "created_at": self.created_at.isoformat() if self.created_at else None,
                    "updated_at": self.updated_at.isoformat() if self.updated_at else None
                },
                "delivery": {
                    "address": self.delivery_address,
                    "type": self.delivery_type,
                    "fee": float(self.delivery_fee) if self.delivery_fee else 0.0
                },
                "items": [
                    {
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": int(item.quantity),
                        "price": float(item.price) if item.price else 0.0,
                        "subtotal": float(item.subtotal) if item.subtotal else 0.0
                    }
                    for item in self.items
                ],
                "financials": self.get_financial_summary(),
                "payment": {
                    "method": self.payment_method,
                    "status": self.payment_status,
                    "reference": self.payment_reference
                },
                "order": {
                    "status": self.order_status,
                    "overall_status": self.status,
                    "notes": self.notes,
                    "status_timeline": self.get_status_timeline()
                },
                "loyalty": {
                    "points_redeemed": float(self.points_rdeemed) if self.points_rdeemed else 0.0,
                    "points_earned": float(self.loyalty_points_earned) if self.loyalty_points_earned else 0.0
                }
            }
            
            # Add service fee breakdown if available
            if self.service_fee_breakdown:
                transaction_dict["service_fee_breakdown"] = [
                    {"platform": float(item.platform) if item.platform else 0.0}
                    for item in self.service_fee_breakdown
                ]
            
            # Add cancellation info if cancelled
            if self.cancellation_reason or self.cancelled_by:
                transaction_dict["cancellation"] = {
                    "reason": self.cancellation_reason,
                    "cancelled_by": self.cancelled_by
                }
            
            # Add items summary
            transaction_dict["items_summary"] = self.get_items_summary()
            
            return transaction_dict
            
        except Exception as e:
            logger.error(f"Error converting transaction to dict: {str(e)}")
            return {}
    
    def to_summary_dict(self) -> dict:
        """
        Get summary representation of the transaction
        
        Returns:
            dict: Summary information
        """
        try:
            return {
                "transaction_id": self.sk,
                "customer_name": self.customer_name,
                "customer_email": self.customer_email,
                "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
                "order_status": self.order_status,
                "payment_status": self.payment_status,
                "payment_method": self.payment_method,
                "total_amount": float(self.total_amount) if self.total_amount else 0.0,
                "item_count": len(self.items),
                "total_quantity": sum(int(item.quantity) for item in self.items),
                "delivery_type": self.delivery_type,
                "status": self.status,
                "created_at": self.created_at.isoformat() if self.created_at else None
            }
        except Exception as e:
            logger.error(f"Error converting transaction to summary dict: {str(e)}")
            return {}
    
    def save(self, condition=None, **kwargs):
        """Override save to update updated_at timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(condition=condition, **kwargs)


# ============= ONLINE TRANSACTION MANAGER =============
class OnlineTransactionManager:
    """
    Manager class for online transaction operations
    """
    
    @staticmethod
    def reconcile_daily_transactions(date: datetime) -> dict:
        """
        Reconcile transactions for a specific day
        
        Args:
            date: Date to reconcile
        
        Returns:
            dict: Reconciliation results
        """
        try:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            
            # Get all transactions for the day
            transactions = []
            for status in ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]:
                transactions.extend(OnlineTransaction.get_by_order_status(
                    status,
                    start_date=start_date,
                    end_date=end_date,
                    limit=1000
                ))
            
            # Deduplicate
            unique_transactions = {}
            for transaction in transactions:
                if transaction.sk not in unique_transactions:
                    unique_transactions[transaction.sk] = transaction
            
            transactions = list(unique_transactions.values())
            
            # Calculate totals
            reconciliation = {
                "date": date.date().isoformat(),
                "total_transactions": len(transactions),
                "total_revenue": 0.0,
                "by_status": {},
                "by_payment_method": {},
                "failed_payments": [],
                "cancelled_orders": []
            }
            
            for transaction in transactions:
                revenue = float(transaction.total_amount) if transaction.total_amount else 0.0
                reconciliation["total_revenue"] += revenue
                
                # Count by status
                status = transaction.order_status
                reconciliation["by_status"][status] = reconciliation["by_status"].get(status, 0) + 1
                
                # Count by payment method
                method = transaction.payment_method
                reconciliation["by_payment_method"][method] = reconciliation["by_payment_method"].get(method, 0) + 1
                
                # Track failed payments
                if transaction.payment_status == "failed":
                    reconciliation["failed_payments"].append({
                        "transaction_id": transaction.sk,
                        "customer_email": transaction.customer_email,
                        "amount": revenue
                    })
                
                # Track cancelled orders
                if transaction.order_status == "cancelled":
                    reconciliation["cancelled_orders"].append({
                        "transaction_id": transaction.sk,
                        "customer_email": transaction.customer_email,
                        "amount": revenue,
                        "reason": transaction.cancellation_reason
                    })
            
            logger.info(f"Daily reconciliation for {date.date()}: {len(transactions)} transactions, ${reconciliation['total_revenue']:.2f}")
            return reconciliation
            
        except Exception as e:
            logger.error(f"Error reconciling daily transactions: {str(e)}")
            return {}
    
    @staticmethod
    def export_transactions_to_csv(start_date: datetime, end_date: datetime) -> list:
        """
        Export transactions to CSV format
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            list: List of dictionaries for CSV export
        """
        try:
            csv_data = []
            
            # Get transactions by status and combine
            all_transactions = []
            for status in ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]:
                transactions = OnlineTransaction.get_by_order_status(
                    status,
                    start_date=start_date,
                    end_date=end_date,
                    limit=10000
                )
                all_transactions.extend(transactions)
            
            # Deduplicate
            seen_ids = set()
            for transaction in all_transactions:
                if transaction.sk not in seen_ids:
                    seen_ids.add(transaction.sk)
                    
                    # Format for CSV
                    csv_row = {
                        "transaction_id": transaction.sk,
                        "customer_id": transaction.customer_id,
                        "customer_name": transaction.customer_name,
                        "customer_email": transaction.customer_email,
                        "customer_phone": transaction.customer_phone,
                        "transaction_date_utc": transaction.transaction_date.isoformat() if transaction.transaction_date else "",
                        "transaction_date_local": transaction.transaction_date_local.isoformat() if transaction.transaction_date_local else "",
                        "timezone": transaction.Timezone,
                        "delivery_address": transaction.delivery_address,
                        "delivery_type": transaction.delivery_type,
                        "order_status": transaction.order_status,
                        "payment_status": transaction.payment_status,
                        "payment_method": transaction.payment_method,
                        "payment_reference": transaction.payment_reference or "",
                        "subtotal": f"{float(transaction.subtotal):.2f}" if transaction.subtotal else "0.00",
                        "points_redeemed": f"{float(transaction.points_rdeemed):.2f}" if transaction.points_rdeemed else "0.00",
                        "points_discount": f"{float(transaction.ponts_discount):.2f}" if transaction.ponts_discount else "0.00",
                        "delivery_fee": f"{float(transaction.delivery_fee):.2f}" if transaction.delivery_fee else "0.00",
                        "service_fee": f"{float(transaction.service_fee):.2f}" if transaction.service_fee else "0.00",
                        "total_amount": f"{float(transaction.total_amount):.2f}" if transaction.total_amount else "0.00",
                        "loyalty_points_earned": f"{float(transaction.loyalty_points_earned):.2f}" if transaction.loyalty_points_earned else "0.00",
                        "item_count": len(transaction.items),
                        "total_quantity": sum(int(item.quantity) for item in transaction.items),
                        "cancellation_reason": transaction.cancellation_reason or "",
                        "cancelled_by": transaction.cancelled_by or "",
                        "notes": transaction.notes or "",
                        "created_at": transaction.created_at.isoformat() if transaction.created_at else "",
                        "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else ""
                    }
                    
                    csv_data.append(csv_row)
            
            logger.info(f"Exported {len(csv_data)} transactions to CSV format")
            return csv_data
            
        except Exception as e:
            logger.error(f"Error exporting transactions to CSV: {str(e)}")
            return []
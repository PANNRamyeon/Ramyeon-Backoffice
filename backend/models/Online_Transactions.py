from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any


class OnlineSaleItem(MapAttribute):
    """MapAttribute for items in an online transaction"""
    product_id = UnicodeAttribute()
    product_name = UnicodeAttribute()
    quantity = NumberAttribute()
    price = NumberAttribute()
    subtotal = NumberAttribute()


class ServiceFeeBreakdownItem(MapAttribute):
    """MapAttribute for service_fee_breakdown items"""
    platform = NumberAttribute(default=0)


class StatusHistoryItem(MapAttribute):
    """MapAttribute for status_history items"""
    status = UnicodeAttribute()
    timestamp = UTCDateTimeAttribute()


class OnlineTransaction(Model):
    """
    Online Transaction model for DynamoDB
    PK = online_transactions (partition key)
    SK = ONLTRAN-##### (sort key)
    """
    class Meta:
        table_name = "your-table-name"  # Replace with your table name
        region = "your-region"  # Replace with your AWS region
        # Add billing_mode, read_capacity_units, write_capacity_units if needed

    # Primary Key Attributes
    PK = UnicodeAttribute(hash_key=True, default="online_transactions")
    SK = UnicodeAttribute(range_key=True)

    # Customer Information
    customer_id = UnicodeAttribute()
    customer_name = UnicodeAttribute()
    customer_email = UnicodeAttribute()
    customer_phone = UnicodeAttribute()
    
    # Transaction Timing
    transaction_date = UTCDateTimeAttribute()
    transaction_date_local = UTCDateTimeAttribute()
    Timezone = UnicodeAttribute()  # Note: Capital T as per schema
    utc_offset_minutes = NumberAttribute()
    
    # Delivery Information
    delivery_address = UnicodeAttribute()
    delivery_type = UnicodeAttribute()  # e.g., 'delivery', 'pickup', 'curbside'
    
    # Items in the Order
    items = ListAttribute(of=OnlineSaleItem)
    
    # Financial Breakdown
    subtotal = NumberAttribute()
    points_redeemed = NumberAttribute(default=0.0)  # Schema says 'points_rdeemed' but we'll use correct spelling
    points_discount = NumberAttribute(default=0.0)  # Schema says 'ponts_discount' but we'll use correct spelling
    subtotal_after_discount = NumberAttribute()
    delivery_fee = NumberAttribute(default=0.0)
    service_fee = NumberAttribute(default=0.0)
    
    # Service Fee Breakdown
    service_fee_breakdown = ListAttribute(of=ServiceFeeBreakdownItem, default=list)
    
    # Totals
    total_amount = NumberAttribute()  # Schema says 'total_amount (integer)' but we'll use NumberAttribute for float
    
    # Payment Information
    payment_method = UnicodeAttribute()  # e.g., 'credit_card', 'paypal', 'apple_pay', 'google_pay'
    payment_status = UnicodeAttribute()  # e.g., 'pending', 'paid', 'failed', 'refunded'
    payment_reference = UnicodeAttribute(null=True)
    
    # Order Status
    order_status = UnicodeAttribute(default="pending")  # e.g., 'pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled'
    status = UnicodeAttribute(default="active")  # Overall status
    
    # Notes and History
    notes = UnicodeAttribute(null=True)
    status_history = ListAttribute(of=StatusHistoryItem, default=list)
    
    # Loyalty Points
    loyalty_points_earned = NumberAttribute(default=0.0)
    
    # Timestamps
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    
    # Cancellation Information
    cancellation_reason = UnicodeAttribute(null=True)
    cancelled_by = UnicodeAttribute(null=True)

    @classmethod
    def create_online_transaction(cls, transaction_id: str, **kwargs):
        """Helper method to create a new online transaction with proper SK format"""
        sk = f"ONLTRAN-{transaction_id}"
        return cls(SK=sk, **kwargs)

    @classmethod
    def get_transaction(cls, transaction_id: str):
        """Helper method to retrieve a transaction by ID"""
        sk = f"ONLTRAN-{transaction_id}"
        return cls.get("online_transactions", sk)

    @classmethod
    def query_by_customer(cls, customer_id: str, days: int = 90):
        """Query transactions by customer within the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # This requires a GSI on customer_id
        return [
            transaction for transaction in cls.query(
                customer_id,
                cls.SK.startswith("ONLTRAN-"),
                index_name="CustomerIdIndex"  # You'll need to create this GSI
            )
            if transaction.transaction_date >= cutoff_date
        ]

    @classmethod
    def query_by_status(cls, order_status: str):
        """Query transactions by order status"""
        # This requires a GSI on order_status
        return cls.query(
            order_status,
            cls.SK.startswith("ONLTRAN-"),
            index_name="OrderStatusIndex"  # You'll need to create this GSI
        )

    @classmethod
    def query_by_payment_status(cls, payment_status: str):
        """Query transactions by payment status"""
        # This requires a GSI on payment_status
        return cls.query(
            payment_status,
            cls.SK.startswith("ONLTRAN-"),
            index_name="PaymentStatusIndex"  # You'll need to create this GSI
        )

    @classmethod
    def query_by_date_range(cls, start_date: datetime, end_date: datetime):
        """Query transactions within a date range"""
        # This requires a GSI with transaction_date as sort key
        # For now, we'll scan (inefficient for large datasets)
        return [
            transaction for transaction in cls.query("online_transactions", cls.SK.startswith("ONLTRAN-"))
            if start_date <= transaction.transaction_date <= end_date
        ]

    @classmethod
    def create_online_order(cls, transaction_id: str, customer_info: Dict, 
                           items: List[Dict], delivery_info: Dict, 
                           payment_method: str, timezone_str: str = "UTC"):
        """
        Create a new online order
        
        Args:
            transaction_id: Unique transaction ID
            customer_info: Dictionary with customer details
            items: List of item dictionaries
            delivery_info: Dictionary with delivery details
            payment_method: Payment method used
            timezone_str: Customer's timezone
        """
        now_utc = datetime.utcnow()
        
        # Calculate local time based on timezone (simplified)
        # In production, you'd use pytz or zoneinfo
        transaction_date_local = now_utc  # Simplified - use actual conversion
        
        # Parse items
        parsed_items = []
        subtotal = 0.0
        
        for item in items:
            parsed_item = OnlineSaleItem(
                product_id=item["product_id"],
                product_name=item["product_name"],
                quantity=item["quantity"],
                price=item["price"],
                subtotal=item["price"] * item["quantity"]
            )
            parsed_items.append(parsed_item)
            subtotal += parsed_item.subtotal
        
        # Calculate totals
        subtotal_after_discount = subtotal - 0.0  # No discount initially
        total_amount = subtotal_after_discount + delivery_info.get("delivery_fee", 0.0)
        
        # Create transaction
        transaction = cls.create_online_transaction(
            transaction_id=transaction_id,
            customer_id=customer_info["customer_id"],
            customer_name=customer_info["customer_name"],
            customer_email=customer_info["customer_email"],
            customer_phone=customer_info["customer_phone"],
            transaction_date=now_utc,
            transaction_date_local=transaction_date_local,
            Timezone=timezone_str,
            utc_offset_minutes=self._get_utc_offset(timezone_str),
            delivery_address=delivery_info["address"],
            delivery_type=delivery_info["type"],
            items=parsed_items,
            subtotal=subtotal,
            subtotal_after_discount=subtotal_after_discount,
            delivery_fee=delivery_info.get("delivery_fee", 0.0),
            service_fee=delivery_info.get("service_fee", 0.0),
            total_amount=total_amount,
            payment_method=payment_method,
            payment_status="pending",
            order_status="pending",
            status="active"
        )
        
        # Add initial status to history
        transaction.add_status_history("pending", now_utc)
        
        return transaction

    def _get_utc_offset(self, timezone_str: str) -> int:
        """
        Get UTC offset in minutes for a given timezone
        Simplified - in production use pytz/zoneinfo
        """
        # This is a simplified implementation
        # In production, use: pytz.timezone(timezone_str).utcoffset(datetime.utcnow()).total_seconds() / 60
        timezone_offsets = {
            "UTC": 0,
            "UTC+1": 60,
            "UTC-5": -300,
            "UTC+8": 480,
            "EST": -300,
            "PST": -480,
        }
        return timezone_offsets.get(timezone_str, 0)

    def add_status_history(self, status: str, timestamp: Optional[datetime] = None):
        """Add a status change to the history"""
        status_item = StatusHistoryItem(
            status=status,
            timestamp=timestamp or datetime.utcnow()
        )
        self.status_history.append(status_item)
        self.updated_at = datetime.utcnow()
        return self

    def update_order_status(self, new_status: str, notes: Optional[str] = None):
        """
        Update the order status and add to history
        
        Args:
            new_status: New order status
            notes: Optional notes about the status change
        """
        self.order_status = new_status
        self.add_status_history(new_status)
        
        if notes:
            self.notes = notes
        
        # Auto-update payment status for certain order statuses
        if new_status == "cancelled":
            self.payment_status = "refund_pending"
            self.status = "cancelled"
        elif new_status == "delivered":
            if self.payment_status == "pending":
                self.payment_status = "completed"
        
        self.updated_at = datetime.utcnow()
        self.save()
        
        return self

    def update_payment_status(self, new_status: str, payment_reference: Optional[str] = None):
        """
        Update payment status
        
        Args:
            new_status: New payment status
            payment_reference: Payment reference/transaction ID
        """
        self.payment_status = new_status
        
        if payment_reference:
            self.payment_reference = payment_reference
        
        # Auto-update order status for certain payment statuses
        if new_status == "paid" and self.order_status == "pending":
            self.update_order_status("confirmed")
        elif new_status == "failed" and self.order_status == "pending":
            self.update_order_status("payment_failed")
        
        self.updated_at = datetime.utcnow()
        self.save()
        
        return self

    def apply_points_discount(self, points_redeemed: float, discount_amount: float):
        """
        Apply loyalty points discount to the order
        
        Args:
            points_redeemed: Points redeemed
            discount_amount: Discount amount in currency
        """
        self.points_redeemed = points_redeemed
        self.points_discount = discount_amount
        self.subtotal_after_discount = self.subtotal - discount_amount
        self.calculate_total()
        
        self.updated_at = datetime.utcnow()
        self.save()
        
        return self

    def calculate_total(self):
        """Calculate and update total amount"""
        self.total_amount = self.subtotal_after_discount + self.delivery_fee + self.service_fee
        return self

    def cancel_order(self, reason: str, cancelled_by: str, notes: Optional[str] = None):
        """
        Cancel the order
        
        Args:
            reason: Reason for cancellation
            cancelled_by: Who cancelled the order
            notes: Additional notes
        """
        self.cancellation_reason = reason
        self.cancelled_by = cancelled_by
        self.status = "cancelled"
        
        # Update order status
        self.update_order_status("cancelled", notes)
        
        # Update payment status if needed
        if self.payment_status == "paid":
            self.payment_status = "refund_pending"
        
        self.updated_at = datetime.utcnow()
        self.save()
        
        return self

    def calculate_loyalty_points(self, points_per_dollar: float = 1.0):
        """
        Calculate loyalty points earned from this transaction
        
        Args:
            points_per_dollar: Points earned per dollar spent
        """
        # Points are typically earned on the subtotal after discounts
        self.loyalty_points_earned = self.subtotal_after_discount * points_per_dollar
        self.updated_at = datetime.utcnow()
        self.save()
        
        return self

    def get_item_summary(self) -> Dict[str, Any]:
        """Get summary of items in the order"""
        return {
            "total_items": len(self.items),
            "total_quantity": sum(item.quantity for item in self.items),
            "total_value": self.subtotal,
            "average_item_price": self.subtotal / len(self.items) if self.items else 0
        }

    def get_status_timeline(self) -> List[Dict[str, Any]]:
        """Get chronological status timeline"""
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
        
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "just now"

    def get_financial_summary(self) -> Dict[str, Any]:
        """Get financial summary of the order"""
        return {
            "subtotal": self.subtotal,
            "points_discount": self.points_discount,
            "subtotal_after_discount": self.subtotal_after_discount,
            "delivery_fee": self.delivery_fee,
            "service_fee": self.service_fee,
            "total_amount": self.total_amount,
            "points_redeemed": self.points_redeemed,
            "loyalty_points_earned": self.loyalty_points_earned,
            "net_revenue": self.total_amount - self.delivery_fee - self.service_fee
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Get summary representation of the transaction"""
        return {
            "transaction_id": self.SK.replace("ONLTRAN-", ""),
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "transaction_date_local": self.transaction_date_local.isoformat() if self.transaction_date_local else None,
            "order_status": self.order_status,
            "payment_status": self.payment_status,
            "payment_method": self.payment_method,
            "total_amount": self.total_amount,
            "item_count": len(self.items),
            "total_items": sum(item.quantity for item in self.items),
            "delivery_type": self.delivery_type,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "current_status_duration": self._get_current_status_duration()
        }

    def _get_current_status_duration(self) -> Optional[str]:
        """Get how long the order has been in current status"""
        if not self.status_history:
            return None
        
        latest_status = sorted(self.status_history, key=lambda x: x.timestamp, reverse=True)[0]
        if latest_status.timestamp:
            delta = datetime.utcnow() - latest_status.timestamp
            if delta.days > 0:
                return f"{delta.days} days"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600} hours"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60} minutes"
        
        return None

    def to_full_dict(self) -> Dict[str, Any]:
        """Get full representation of the transaction"""
        transaction_dict = {
            "transaction_id": self.SK.replace("ONLTRAN-", ""),
            "customer_details": {
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
                "fee": self.delivery_fee
            },
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "subtotal": item.subtotal
                }
                for item in self.items
            ],
            "financial_summary": self.get_financial_summary(),
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
                "points_redeemed": self.points_redeemed,
                "points_earned": self.loyalty_points_earned
            }
        }
        
        # Add cancellation info if cancelled
        if self.cancellation_reason or self.cancelled_by:
            transaction_dict["cancellation"] = {
                "reason": self.cancellation_reason,
                "cancelled_by": self.cancelled_by
            }
        
        # Add service fee breakdown if available
        if self.service_fee_breakdown:
            transaction_dict["service_fee_breakdown"] = [
                {"platform": item.platform}
                for item in self.service_fee_breakdown
            ]
        
        return transaction_dict

    @classmethod
    def get_dashboard_stats(cls, days: int = 30) -> Dict[str, Any]:
        """Get dashboard statistics for online transactions"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        total_orders = 0
        total_revenue = 0.0
        status_counts = {
            "pending": 0,
            "confirmed": 0,
            "processing": 0,
            "shipped": 0,
            "delivered": 0,
            "cancelled": 0
        }
        
        # Note: This scans the table - for production, consider using DynamoDB Streams
        # to maintain aggregated statistics in a separate table
        for transaction in cls.scan(cls.transaction_date >= cutoff_date):
            total_orders += 1
            total_revenue += transaction.total_amount
            status = transaction.order_status
            if status in status_counts:
                status_counts[status] += 1
        
        return {
            "period_days": days,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "average_order_value": total_revenue / total_orders if total_orders > 0 else 0,
            "status_distribution": status_counts,
            "cancellation_rate": (status_counts["cancelled"] / total_orders * 100) if total_orders > 0 else 0
        }
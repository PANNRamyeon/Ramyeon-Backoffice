from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


class BatchUsedItem(MapAttribute):
    """MapAttribute for batches_used items"""
    batch_id = UnicodeAttribute()
    batch_number = UnicodeAttribute()
    quantity_deducted = NumberAttribute()
    expiry_date = UTCDateTimeAttribute()
    cost_price = NumberAttribute()


class SaleItem(MapAttribute):
    """MapAttribute for items in a sale"""
    product_id = UnicodeAttribute()
    product_name = UnicodeAttribute()
    sku = UnicodeAttribute()
    quantity = NumberAttribute()
    unit_price = NumberAttribute()
    subtotal = NumberAttribute()
    is_taxable = BooleanAttribute()
    batches_used = ListAttribute(of=BatchUsedItem, default=list)


class DiscountBreakdownItem(MapAttribute):
    """MapAttribute for discount_breakdown items"""
    promotion_discount = NumberAttribute(default=0.0)
    points_discount = NumberAttribute(default=0.0)
    total_discount = NumberAttribute(default=0.0)


class PaymentDetail(MapAttribute):
    """MapAttribute for payment_details items"""
    method = UnicodeAttribute()  # e.g., 'cash', 'credit_card', 'debit_card', 'digital_wallet'
    amount_paid = NumberAttribute()
    change = NumberAttribute(default=0.0)
    status = UnicodeAttribute()  # e.g., 'completed', 'pending', 'failed'
    transaction_id = UnicodeAttribute(null=True)
    timestamp = UTCDateTimeAttribute()


class Sale(Model):
    """
    Sale/Transaction model for DynamoDB
    PK = sales (partition key)
    SK = SALE-##### (sort key)
    """
    class Meta:
        table_name = "your-table-name"  # Replace with your table name
        region = "your-region"  # Replace with your AWS region
        # Add billing_mode, read_capacity_units, write_capacity_units if needed

    # Primary Key Attributes
    PK = UnicodeAttribute(hash_key=True, default="sales")
    SK = UnicodeAttribute(range_key=True)

    # Transaction Information
    transaction_date = UTCDateTimeAttribute()
    cashier_id = UnicodeAttribute()
    shift_id = UnicodeAttribute()
    shift_seq = NumberAttribute()
    customer_id = UnicodeAttribute(null=True)
    
    # Items in the Sale
    items = ListAttribute(of=SaleItem)
    
    # Financial Totals
    subtotal = NumberAttribute()
    tax_amount = NumberAttribute(default=0.0)
    discount_amount = NumberAttribute(default=0.0)
    
    # Discount Breakdown
    discount_breakdown = ListAttribute(of=DiscountBreakdownItem, default=list)
    
    # Total Amount (note: schema has typo 'toatl_amount' but we'll use correct spelling)
    total_amount = NumberAttribute()  # Schema says 'toatl_amount', we'll use correct spelling
    
    # Payment Information
    payment_method = UnicodeAttribute()  # Primary payment method
    payment_details = ListAttribute(of=PaymentDetail)
    
    # Promotions and Loyalty
    promotion_id = UnicodeAttribute(null=True)
    promotion_discount = NumberAttribute(default=0.0)
    loyalty_points = NumberAttribute(default=0.0)
    
    # Status and Metadata
    status = UnicodeAttribute(default="completed")  # e.g., 'completed', 'pending', 'cancelled', 'refunded'
    source = UnicodeAttribute(default="pos")  # e.g., 'pos', 'online', 'mobile'
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    is_voided = BooleanAttribute(default=False)
    points_awarded = BooleanAttribute(default=False)
    
    # Synchronization
    sync_state = UnicodeAttribute(default="pending")  # e.g., 'pending', 'synced', 'failed'
    event_id = UnicodeAttribute(null=True)  # For event sourcing/change tracking

    @classmethod
    def create_sale(cls, sale_id: str, **kwargs):
        """Helper method to create a new sale with proper SK format"""
        sk = f"SALE-{sale_id}"
        return cls(SK=sk, **kwargs)

    @classmethod
    def get_sale(cls, sale_id: str):
        """Helper method to retrieve a sale by ID"""
        sk = f"SALE-{sale_id}"
        return cls.get("sales", sk)

    @classmethod
    def query_by_shift(cls, shift_id: str):
        """Query all sales for a specific shift"""
        # This requires a GSI on shift_id
        return cls.query(
            shift_id,
            cls.SK.startswith("SALE-"),
            index_name="ShiftIndex"  # You'll need to create this GSI
        )

    @classmethod
    def query_by_cashier(cls, cashier_id: str, days: int = 7):
        """Query sales by cashier within the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # This requires a GSI on cashier_id
        return [
            sale for sale in cls.query(
                cashier_id,
                cls.SK.startswith("SALE-"),
                index_name="CashierIndex"  # You'll need to create this GSI
            )
            if sale.transaction_date >= cutoff_date
        ]

    @classmethod
    def query_by_customer(cls, customer_id: str, days: int = 30):
        """Query sales by customer within the last N days"""
        # This requires a GSI on customer_id
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return [
            sale for sale in cls.query(
                customer_id,
                cls.SK.startswith("SALE-"),
                index_name="CustomerIndex"  # You'll need to create this GSI
            )
            if sale.transaction_date >= cutoff_date
        ]

    @classmethod
    def query_by_date_range(cls, start_date: datetime, end_date: datetime):
        """Query sales within a date range"""
        # This requires a GSI with transaction_date as sort key
        # For now, we'll scan (inefficient for large datasets)
        return [
            sale for sale in cls.query("sales", cls.SK.startswith("SALE-"))
            if start_date <= sale.transaction_date <= end_date
        ]

    def calculate_totals(self):
        """Calculate and update sale totals"""
        # Calculate subtotal from items
        subtotal = sum(item.subtotal for item in self.items)
        
        # Calculate tax (assuming simple tax calculation)
        taxable_items = sum(
            item.subtotal for item in self.items 
            if hasattr(item, 'is_taxable') and item.is_taxable
        )
        # This is a simple tax calculation - adjust as needed
        self.tax_amount = taxable_items * 0.1  # Example: 10% tax
        
        # Apply discount
        discount_total = self.discount_amount
        
        # Calculate final total
        self.total_amount = subtotal + self.tax_amount - discount_total
        
        self.updated_at = datetime.utcnow()
        return self

    def add_item(self, product_id: str, product_name: str, sku: str, 
                quantity: int, unit_price: float, is_taxable: bool = True,
                batches_used: Optional[List[Dict]] = None):
        """
        Add an item to the sale
        
        Args:
            product_id: Product ID
            product_name: Product name
            sku: Product SKU
            quantity: Quantity sold
            unit_price: Unit price
            is_taxable: Whether the item is taxable
            batches_used: List of batches used for this item
        """
        subtotal = unit_price * quantity
        
        # Create batches_used list
        batch_items = []
        if batches_used:
            for batch in batches_used:
                batch_item = BatchUsedItem(
                    batch_id=batch.get('batch_id'),
                    batch_number=batch.get('batch_number'),
                    quantity_deducted=batch.get('quantity_deducted'),
                    expiry_date=batch.get('expiry_date'),
                    cost_price=batch.get('cost_price')
                )
                batch_items.append(batch_item)
        
        item = SaleItem(
            product_id=product_id,
            product_name=product_name,
            sku=sku,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
            is_taxable=is_taxable,
            batches_used=batch_items
        )
        
        self.items.append(item)
        
        # Recalculate totals
        self.calculate_totals()
        
        return self

    def add_payment(self, method: str, amount_paid: float, 
                   transaction_id: Optional[str] = None, 
                   status: str = "completed"):
        """
        Add payment to the sale
        
        Args:
            method: Payment method (cash, credit_card, etc.)
            amount_paid: Amount paid
            transaction_id: External transaction ID (for cards, etc.)
            status: Payment status
        """
        # Calculate change if paying with cash
        change = 0.0
        if method.lower() == "cash" and amount_paid > self.total_amount:
            change = amount_paid - self.total_amount
        
        payment = PaymentDetail(
            method=method,
            amount_paid=amount_paid,
            change=change,
            status=status,
            transaction_id=transaction_id,
            timestamp=datetime.utcnow()
        )
        
        self.payment_details.append(payment)
        self.payment_method = method
        self.updated_at = datetime.utcnow()
        
        return self

    def apply_discount(self, discount_type: str, amount: float, 
                      promotion_id: Optional[str] = None):
        """
        Apply discount to the sale
        
        Args:
            discount_type: Type of discount ('promotion', 'points', 'manual')
            amount: Discount amount
            promotion_id: Promotion ID if applicable
        """
        if discount_type == "promotion":
            self.promotion_discount = amount
            if promotion_id:
                self.promotion_id = promotion_id
        elif discount_type == "points":
            # This would be points discount
            pass
        
        # Update discount breakdown
        if not self.discount_breakdown:
            self.discount_breakdown = [DiscountBreakdownItem()]
        
        breakdown = self.discount_breakdown[0]
        
        if discount_type == "promotion":
            breakdown.promotion_discount = amount
        elif discount_type == "points":
            breakdown.points_discount = amount
        
        # Calculate total discount
        breakdown.total_discount = (
            breakdown.promotion_discount + 
            breakdown.points_discount
        )
        
        self.discount_amount = breakdown.total_discount
        
        # Recalculate totals
        self.calculate_totals()
        
        return self

    def void_sale(self, reason: Optional[str] = None):
        """
        Void the sale (mark as cancelled/refunded)
        
        Args:
            reason: Reason for voiding
        """
        self.status = "voided"
        self.is_voided = True
        self.updated_at = datetime.utcnow()
        
        # Update sync state
        self.sync_state = "pending"
        
        # Add event ID for tracking
        self.event_id = f"void_{datetime.utcnow().timestamp()}"
        
        self.save()
        
        # Add void to sync logs or create a separate void record
        return self

    def calculate_cogs(self) -> float:
        """
        Calculate Cost of Goods Sold based on batches used
        """
        cogs = 0.0
        
        for item in self.items:
            for batch in item.batches_used:
                cogs += batch.quantity_deducted * batch.cost_price
        
        return cogs

    def calculate_profit(self) -> float:
        """
        Calculate profit for the sale
        """
        cogs = self.calculate_cogs()
        revenue = self.total_amount
        return revenue - cogs

    def calculate_margin(self) -> float:
        """
        Calculate profit margin percentage
        """
        revenue = self.total_amount
        if revenue == 0:
            return 0.0
        
        profit = self.calculate_profit()
        return (profit / revenue) * 100

    def get_item_summary(self) -> Dict[str, Any]:
        """Get summary of items in the sale"""
        item_summary = {
            "total_items": len(self.items),
            "total_quantity": sum(item.quantity for item in self.items),
            "items_by_product": {},
            "top_items": []
        }
        
        # Group items by product
        for item in self.items:
            if item.product_id not in item_summary["items_by_product"]:
                item_summary["items_by_product"][item.product_id] = {
                    "name": item.product_name,
                    "sku": item.sku,
                    "total_quantity": 0,
                    "total_value": 0.0
                }
            
            product_data = item_summary["items_by_product"][item.product_id]
            product_data["total_quantity"] += item.quantity
            product_data["total_value"] += item.subtotal
        
        # Get top items by value
        top_items = sorted(
            item_summary["items_by_product"].items(),
            key=lambda x: x[1]["total_value"],
            reverse=True
        )[:5]
        
        item_summary["top_items"] = [
            {
                "product_id": product_id,
                **data
            }
            for product_id, data in top_items
        ]
        
        return item_summary

    def get_payment_summary(self) -> Dict[str, Any]:
        """Get summary of payments"""
        summary = {
            "total_paid": sum(payment.amount_paid for payment in self.payment_details),
            "total_change": sum(payment.change for payment in self.payment_details),
            "payment_methods": {},
            "primary_method": self.payment_method
        }
        
        # Group by payment method
        for payment in self.payment_details:
            method = payment.method
            if method not in summary["payment_methods"]:
                summary["payment_methods"][method] = {
                    "count": 0,
                    "total_amount": 0.0
                }
            
            summary["payment_methods"][method]["count"] += 1
            summary["payment_methods"][method]["total_amount"] += payment.amount_paid
        
        return summary

    def to_summary_dict(self) -> Dict[str, Any]:
        """Get summary representation of the sale"""
        return {
            "sale_id": self.SK.replace("SALE-", ""),
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "cashier_id": self.cashier_id,
            "shift_id": self.shift_id,
            "shift_seq": self.shift_seq,
            "customer_id": self.customer_id,
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "discount_amount": self.discount_amount,
            "total_amount": self.total_amount,
            "status": self.status,
            "is_voided": self.is_voided,
            "payment_method": self.payment_method,
            "item_count": len(self.items),
            "total_items": sum(item.quantity for item in self.items),
            "cogs": self.calculate_cogs(),
            "profit": self.calculate_profit(),
            "margin": round(self.calculate_margin(), 2)
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Get full representation of the sale"""
        sale_dict = self.to_summary_dict()
        
        # Add items details
        sale_dict["items"] = []
        for item in self.items:
            item_dict = {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
                "is_taxable": item.is_taxable,
                "batches_used": []
            }
            
            for batch in item.batches_used:
                batch_dict = {
                    "batch_id": batch.batch_id,
                    "batch_number": batch.batch_number,
                    "quantity_deducted": batch.quantity_deducted,
                    "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
                    "cost_price": batch.cost_price
                }
                item_dict["batches_used"].append(batch_dict)
            
            sale_dict["items"].append(item_dict)
        
        # Add payment details
        sale_dict["payment_details"] = []
        for payment in self.payment_details:
            payment_dict = {
                "method": payment.method,
                "amount_paid": payment.amount_paid,
                "change": payment.change,
                "status": payment.status,
                "transaction_id": payment.transaction_id,
                "timestamp": payment.timestamp.isoformat() if payment.timestamp else None
            }
            sale_dict["payment_details"].append(payment_dict)
        
        # Add discount breakdown
        if self.discount_breakdown:
            sale_dict["discount_breakdown"] = []
            for breakdown in self.discount_breakdown:
                sale_dict["discount_breakdown"].append({
                    "promotion_discount": breakdown.promotion_discount,
                    "points_discount": breakdown.points_discount,
                    "total_discount": breakdown.total_discount
                })
        
        # Add additional metadata
        sale_dict.update({
            "promotion_id": self.promotion_id,
            "promotion_discount": self.promotion_discount,
            "loyalty_points": self.loyalty_points,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "points_awarded": self.points_awarded,
            "sync_state": self.sync_state,
            "event_id": self.event_id
        })
        
        return sale_dict

    @classmethod
    def create_pos_sale(cls, sale_id: str, cashier_id: str, shift_id: str, 
                       shift_seq: int, items: List[Dict], 
                       payment_method: str, customer_id: Optional[str] = None):
        """
        Create a POS sale with standard configuration
        
        Args:
            sale_id: Unique sale ID
            cashier_id: Cashier ID
            shift_id: Shift ID
            shift_seq: Shift sequence number
            items: List of item dictionaries
            payment_method: Primary payment method
            customer_id: Customer ID (optional)
        """
        sale = cls.create_sale(
            sale_id=sale_id,
            transaction_date=datetime.utcnow(),
            cashier_id=cashier_id,
            shift_id=shift_id,
            shift_seq=shift_seq,
            customer_id=customer_id,
            items=[],  # Will be populated below
            payment_method=payment_method,
            source="pos"
        )
        
        # Add items
        for item_data in items:
            sale.add_item(**item_data)
        
        # Calculate initial totals
        sale.calculate_totals()
        
        return sale
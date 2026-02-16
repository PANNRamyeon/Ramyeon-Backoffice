"""
Sale Model - Following ERD Specification
PK = "sales", SK = "SALE-#####" (5-digit format)
Single Table Design using RamyeonCornerDB
"""
import os
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

# Import existing utils for consistency
from app.utils import generate_sk, get_dynamo_table, DYNAMO_TABLE_NAME, AWS_REGION

logger = logging.getLogger(__name__)


# ============= MAP ATTRIBUTES FOR COMPLEX FIELDS =============

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


# ============= SALE MODEL =============

class Sale(Model):
    """
    SALE MODEL - Following ERD Specification
    
    ERD Fields:
    - PK = sales
    - SK = SALE-#####
    - transaction_date (ISODATE)
    - cashier_id (string)
    - shift_id (string)
    - shift_seq (integer)
    - customer_id (string)
    - items (array)
    - subtotal (float)
    - tax_amount (float)
    - discount_amount (float)
    - discount_breakdown (array)
    - total_amount (float)
    - payment_method (string)
    - payment_details (array)
    - promotion_id (string)
    - promotion_discount
    - loyalty_points (float)
    - status (string)
    - source (string)
    - created_at (ISODATE)
    - updated_at (ISODATE)
    - is_voided (boolean)
    - points_awarded (boolean)
    - sync_state (string)
    - event_id (object(ID))
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        # Capacity settings
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, default="sales")
    sk = UnicodeAttribute(range_key=True)  # "SALE-00001" (5-digit)
    
    # ============= TRANSACTION INFORMATION =============
    transaction_date = UTCDateTimeAttribute()
    cashier_id = UnicodeAttribute()
    shift_id = UnicodeAttribute()
    shift_seq = NumberAttribute()
    customer_id = UnicodeAttribute(null=True)
    
    # ============= ITEMS IN THE SALE =============
    items = ListAttribute(of=SaleItem)
    
    # ============= FINANCIAL TOTALS =============
    subtotal = NumberAttribute()
    tax_amount = NumberAttribute(default=0.0)
    discount_amount = NumberAttribute(default=0.0)
    
    # ============= DISCOUNT BREAKDOWN =============
    discount_breakdown = ListAttribute(of=DiscountBreakdownItem, default=list)
    
    # ============= TOTAL AMOUNT =============
    total_amount = NumberAttribute()  # Note: ERD has typo 'total_amount'
    
    # ============= PAYMENT INFORMATION =============
    payment_method = UnicodeAttribute()  # Primary payment method
    payment_details = ListAttribute(of=PaymentDetail)
    
    # ============= PROMOTIONS AND LOYALTY =============
    promotion_id = UnicodeAttribute(null=True)
    promotion_discount = NumberAttribute(default=0.0)
    loyalty_points = NumberAttribute(default=0.0)
    
    # ============= STATUS AND METADATA =============
    status = UnicodeAttribute(default="completed")  # e.g., 'completed', 'pending', 'cancelled', 'refunded'
    source = UnicodeAttribute(default="pos")  # e.g., 'pos', 'online', 'mobile'
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default=datetime.utcnow)
    is_voided = BooleanAttribute(default=False)
    points_awarded = BooleanAttribute(default=False)
    
    # ============= SYNCHRONIZATION =============
    sync_state = UnicodeAttribute(default="pending")  # e.g., 'pending', 'synced', 'failed'
    event_id = UnicodeAttribute(null=True)  # For event sourcing/change tracking
    
    # ============= INDEXES FOR COMMON QUERIES =============
    
    class ShiftIndex(GlobalSecondaryIndex):
        """GSI for querying by shift"""
        class Meta:
            index_name = 'SaleShiftIndex'
            read_capacity_units = 3
            write_capacity_units = 2
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True)  # Will be set to 'sales'
        shift_id = UnicodeAttribute(range_key=True)
    
    class CashierIndex(GlobalSecondaryIndex):
        """GSI for querying by cashier"""
        class Meta:
            index_name = 'SaleCashierIndex'
            read_capacity_units = 3
            write_capacity_units = 2
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True)  # Will be set to 'sales'
        cashier_id = UnicodeAttribute(range_key=True)
    
    class CustomerIndex(GlobalSecondaryIndex):
        """GSI for querying by customer"""
        class Meta:
            index_name = 'SaleCustomerIndex'
            read_capacity_units = 3
            write_capacity_units = 2
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True)  # Will be set to 'sales'
        customer_id = UnicodeAttribute(range_key=True)
    
    class DateIndex(GlobalSecondaryIndex):
        """GSI for querying by date range"""
        class Meta:
            index_name = 'SaleDateIndex'
            read_capacity_units = 3
            write_capacity_units = 2
            projection = AllProjection()
        
        pk = UnicodeAttribute(hash_key=True)  # Will be set to 'sales'
        transaction_date = UTCDateTimeAttribute(range_key=True)
    
    # Index instances
    shift_index = ShiftIndex()
    cashier_index = CashierIndex()
    customer_index = CustomerIndex()
    date_index = DateIndex()
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_sale(cls, cashier_id: str, shift_id: str, shift_seq: int,
                   payment_method: str, **kwargs) -> 'Sale':
        """
        Create a new sale with auto-generated 5-digit SK
        
        Args:
            cashier_id: ID of the cashier (required)
            shift_id: Current shift ID (required)
            shift_seq: Shift sequence number (required)
            payment_method: Primary payment method (required)
            **kwargs: Additional sale attributes
        
        Returns:
            Sale: Created and saved sale instance
        
        Raises:
            ValueError: If required fields are missing
        """
        try:
            # Validate required fields
            if not cashier_id:
                raise ValueError("Cashier ID is required")
            if not shift_id:
                raise ValueError("Shift ID is required")
            if shift_seq is None:
                raise ValueError("Shift sequence is required")
            if not payment_method:
                raise ValueError("Payment method is required")
            
            # Generate 5-digit SK using utils.py
            sk_value = generate_sk('SALE-', 'sale_seq')
            
            # Create and save sale
            sale = cls(
                pk="sales",
                sk=sk_value,
                transaction_date=datetime.utcnow(),
                cashier_id=cashier_id,
                shift_id=shift_id,
                shift_seq=shift_seq,
                payment_method=payment_method,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **kwargs
            )
            
            sale.save()
            
            logger.info(f"Sale created: {sk_value} - Cashier: {cashier_id}, Shift: {shift_id}")
            return sale
            
        except Exception as e:
            logger.error(f"Failed to create sale: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, sale_id: str) -> 'Sale | None':
        """
        Get sale by ID
        
        Args:
            sale_id: Format "SALE-00001" or just "00001"
        
        Returns:
            Sale or None if not found
        """
        try:
            # Ensure proper format
            if not sale_id.startswith('SALE-'):
                sale_id = f"SALE-{sale_id.zfill(5)}"  # Pad to 5 digits if needed
            
            return cls.get("sales", sale_id)
        except cls.DoesNotExist:
            logger.warning(f"Sale not found: {sale_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching sale {sale_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_shift(cls, shift_id: str) -> List['Sale']:
        """
        Get all sales for a specific shift
        
        Args:
            shift_id: Shift ID
        
        Returns:
            list: List of sales in the shift
        """
        try:
            return list(cls.shift_index.query("sales", cls.shift_id == shift_id))
        except Exception as e:
            logger.error(f"Error getting sales for shift {shift_id}: {str(e)}")
            return []
    
    @classmethod
    def get_by_cashier(cls, cashier_id: str, days: int = 7) -> List['Sale']:
        """
        Get sales by cashier within the last N days
        
        Args:
            cashier_id: Cashier ID
            days: Number of days to look back
        
        Returns:
            list: List of sales by the cashier
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            sales = []
            
            for sale in cls.cashier_index.query("sales", cls.cashier_id == cashier_id):
                if sale.transaction_date >= cutoff_date:
                    sales.append(sale)
            
            return sales
        except Exception as e:
            logger.error(f"Error getting sales for cashier {cashier_id}: {str(e)}")
            return []
    
    @classmethod
    def get_by_customer(cls, customer_id: str) -> List['Sale']:
        """
        Get all sales for a specific customer
        
        Args:
            customer_id: Customer ID
        
        Returns:
            list: List of sales for the customer
        """
        try:
            return list(cls.customer_index.query("sales", cls.customer_id == customer_id))
        except Exception as e:
            logger.error(f"Error getting sales for customer {customer_id}: {str(e)}")
            return []
    
    @classmethod
    def get_by_date_range(cls, start_date: datetime, end_date: datetime) -> List['Sale']:
        """
        Get sales within a date range
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            list: List of sales in the date range
        """
        try:
            # Use date index with filter for end date
            sales = []
            for sale in cls.date_index.query(
                "sales",
                cls.transaction_date >= start_date,
                filter_condition=cls.transaction_date <= end_date
            ):
                sales.append(sale)
            
            return sales
        except Exception as e:
            logger.error(f"Error getting sales by date range: {str(e)}")
            return []
    
    @classmethod
    def get_today_sales(cls) -> List['Sale']:
        """
        Get today's sales
        
        Returns:
            list: List of today's sales
        """
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            return cls.get_by_date_range(today_start, today_end)
        except Exception as e:
            logger.error(f"Error getting today's sales: {str(e)}")
            return []
    
    @classmethod
    def get_sale_count(cls, status: str = None) -> int:
        """
        Get count of sales
        
        Args:
            status: Filter by status
        
        Returns:
            int: Number of sales
        """
        try:
            count = 0
            
            if status:
                for sale in cls.query("sales", filter_condition=cls.status == status):
                    count += 1
            else:
                for _ in cls.query("sales"):
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"Error counting sales: {str(e)}")
            return 0
    
    @classmethod
    def get_total_revenue(cls, start_date: datetime = None, end_date: datetime = None) -> float:
        """
        Get total revenue from sales
        
        Args:
            start_date: Start date (optional)
            end_date: End date (optional)
        
        Returns:
            float: Total revenue
        """
        try:
            total = 0.0
            
            if start_date and end_date:
                sales = cls.get_by_date_range(start_date, end_date)
            else:
                sales = cls.get_all_sales()
            
            for sale in sales:
                if sale.status == "completed" and not sale.is_voided:
                    total += float(sale.total_amount)
            
            return round(total, 2)
        except Exception as e:
            logger.error(f"Error calculating total revenue: {str(e)}")
            return 0.0
    
    @classmethod
    def get_all_sales(cls) -> List['Sale']:
        """
        Get all sales
        
        Returns:
            list: List of all sales
        """
        try:
            return list(cls.query("sales"))
        except Exception as e:
            logger.error(f"Error getting all sales: {str(e)}")
            return []
    
    # ============= INSTANCE METHODS =============
    
    def add_item(self, product_id: str, product_name: str, sku: str, 
                quantity: int, unit_price: float, is_taxable: bool = True,
                batches_used: Optional[List[Dict]] = None) -> 'Sale':
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
        
        Returns:
            Sale: Updated sale instance
        """
        try:
            if quantity <= 0:
                raise ValueError("Quantity must be greater than 0")
            if unit_price <= 0:
                raise ValueError("Unit price must be greater than 0")
            
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
            self._calculate_totals()
            self.updated_at = datetime.utcnow()
            self.save()
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to add item to sale {self.sk}: {str(e)}")
            raise
    
    def add_payment(self, method: str, amount_paid: float, 
                   transaction_id: Optional[str] = None, 
                   status: str = "completed") -> 'Sale':
        """
        Add payment to the sale
        
        Args:
            method: Payment method (cash, credit_card, etc.)
            amount_paid: Amount paid
            transaction_id: External transaction ID (for cards, etc.)
            status: Payment status
        
        Returns:
            Sale: Updated sale instance
        """
        try:
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
            
            # Update status to completed if payment successful
            if status == "completed":
                self.status = "completed"
                self.sync_state = "pending"  # Flag for sync
            
            self.save()
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to add payment to sale {self.sk}: {str(e)}")
            raise
    
    def apply_discount(self, discount_amount: float, 
                      promotion_id: Optional[str] = None) -> 'Sale':
        """
        Apply discount to the sale
        
        Args:
            discount_amount: Discount amount
            promotion_id: Promotion ID if applicable
        
        Returns:
            Sale: Updated sale instance
        """
        try:
            if discount_amount < 0:
                raise ValueError("Discount amount cannot be negative")
            
            # Check discount doesn't exceed subtotal
            if discount_amount > self.subtotal:
                raise ValueError("Discount cannot exceed subtotal")
            
            # Apply 20% maximum discount rule
            max_discount = self.subtotal * 0.2  # 20% maximum
            if discount_amount > max_discount:
                discount_amount = max_discount
            
            self.discount_amount = discount_amount
            
            # Update discount breakdown
            if promotion_id:
                self.promotion_id = promotion_id
                self.promotion_discount = discount_amount
            
            # Create or update discount breakdown
            if not self.discount_breakdown:
                self.discount_breakdown = [DiscountBreakdownItem()]
            
            breakdown = self.discount_breakdown[0]
            
            if promotion_id:
                breakdown.promotion_discount = discount_amount
            
            breakdown.total_discount = (
                breakdown.promotion_discount + 
                breakdown.points_discount
            )
            
            self._calculate_totals()
            self.updated_at = datetime.utcnow()
            self.save()
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to apply discount to sale {self.sk}: {str(e)}")
            raise
    
    def apply_points_discount(self, points_amount: float) -> 'Sale':
        """
        Apply loyalty points discount
        
        Args:
            points_amount: Points discount amount
        
        Returns:
            Sale: Updated sale instance
        """
        try:
            if points_amount < 0:
                raise ValueError("Points discount cannot be negative")
            
            self.loyalty_points = points_amount
            
            # Update discount breakdown
            if not self.discount_breakdown:
                self.discount_breakdown = [DiscountBreakdownItem()]
            
            breakdown = self.discount_breakdown[0]
            breakdown.points_discount = points_amount
            breakdown.total_discount = (
                breakdown.promotion_discount + 
                breakdown.points_discount
            )
            
            self.discount_amount = breakdown.total_discount
            self._calculate_totals()
            self.updated_at = datetime.utcnow()
            self.save()
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to apply points discount to sale {self.sk}: {str(e)}")
            raise
    
    def void_sale(self, reason: Optional[str] = None) -> 'Sale':
        """
        Void the sale (mark as cancelled/refunded)
        
        Args:
            reason: Reason for voiding
        
        Returns:
            Sale: Updated sale instance
        """
        try:
            self.status = "cancelled"
            self.is_voided = True
            self.updated_at = datetime.utcnow()
            self.sync_state = "pending"  # Flag for sync
            
            # Add event ID for tracking
            self.event_id = f"void_{datetime.utcnow().timestamp()}"
            
            self.save()
            
            logger.info(f"Sale {self.sk} voided. Reason: {reason or 'No reason provided'}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to void sale {self.sk}: {str(e)}")
            raise
    
    def mark_synced(self) -> 'Sale':
        """
        Mark sale as synced
        
        Returns:
            Sale: Updated sale instance
        """
        try:
            self.sync_state = "synced"
            self.updated_at = datetime.utcnow()
            self.save()
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to mark sale as synced: {str(e)}")
            raise
    
    def mark_sync_failed(self) -> 'Sale':
        """
        Mark sale sync as failed
        
        Returns:
            Sale: Updated sale instance
        """
        try:
            self.sync_state = "failed"
            self.updated_at = datetime.utcnow()
            self.save()
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to mark sale sync as failed: {str(e)}")
            raise
    
    def _calculate_totals(self) -> None:
        """
        Calculate and update sale totals
        """
        try:
            # Calculate subtotal from items
            if self.items:
                self.subtotal = sum(float(item.subtotal) for item in self.items)
            else:
                self.subtotal = 0.0
            
            # Calculate tax (simple 10% tax on taxable items)
            taxable_items = sum(
                float(item.subtotal) for item in self.items 
                if item.is_taxable
            )
            self.tax_amount = taxable_items * 0.1  # 10% tax
            
            # Calculate final total
            self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
            
            # Ensure total is not negative
            if self.total_amount < 0:
                self.total_amount = 0.0
            
        except Exception as e:
            logger.error(f"Error calculating totals for sale {self.sk}: {str(e)}")
            raise
    
    def calculate_cogs(self) -> float:
        """
        Calculate Cost of Goods Sold based on batches used
        
        Returns:
            float: COGS amount
        """
        try:
            cogs = 0.0
            
            for item in self.items:
                for batch in item.batches_used:
                    cogs += float(batch.quantity_deducted) * float(batch.cost_price)
            
            return round(cogs, 2)
        except Exception as e:
            logger.error(f"Error calculating COGS for sale {self.sk}: {str(e)}")
            return 0.0
    
    def calculate_profit(self) -> float:
        """
        Calculate profit for the sale
        
        Returns:
            float: Profit amount
        """
        try:
            cogs = self.calculate_cogs()
            revenue = float(self.total_amount)
            profit = revenue - cogs
            
            return round(profit, 2)
        except Exception as e:
            logger.error(f"Error calculating profit for sale {self.sk}: {str(e)}")
            return 0.0
    
    def calculate_margin(self) -> float:
        """
        Calculate profit margin percentage
        
        Returns:
            float: Margin percentage
        """
        try:
            revenue = float(self.total_amount)
            if revenue == 0:
                return 0.0
            
            profit = self.calculate_profit()
            margin = (profit / revenue) * 100
            
            return round(margin, 2)
        except Exception as e:
            logger.error(f"Error calculating margin for sale {self.sk}: {str(e)}")
            return 0.0
    
    def get_item_summary(self) -> Dict[str, Any]:
        """
        Get summary of items in the sale
        
        Returns:
            dict: Item summary
        """
        try:
            item_summary = {
                "total_items": len(self.items),
                "total_quantity": sum(float(item.quantity) for item in self.items),
                "items_by_product": {}
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
                product_data["total_quantity"] += float(item.quantity)
                product_data["total_value"] += float(item.subtotal)
            
            return item_summary
            
        except Exception as e:
            logger.error(f"Error getting item summary for sale {self.sk}: {str(e)}")
            return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert sale to dictionary for API response
        
        Returns:
            dict: Dictionary representation
        """
        try:
            sale_dict = {
                "sale_id": self.sk.replace("SALE-", ""),
                "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
                "cashier_id": self.cashier_id,
                "shift_id": self.shift_id,
                "shift_seq": self.shift_seq,
                "customer_id": self.customer_id,
                "subtotal": float(self.subtotal) if self.subtotal else 0.0,
                "tax_amount": float(self.tax_amount) if self.tax_amount else 0.0,
                "discount_amount": float(self.discount_amount) if self.discount_amount else 0.0,
                "total_amount": float(self.total_amount) if self.total_amount else 0.0,
                "payment_method": self.payment_method,
                "promotion_id": self.promotion_id,
                "promotion_discount": float(self.promotion_discount) if self.promotion_discount else 0.0,
                "loyalty_points": float(self.loyalty_points) if self.loyalty_points else 0.0,
                "status": self.status,
                "source": self.source,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "is_voided": self.is_voided,
                "points_awarded": self.points_awarded,
                "sync_state": self.sync_state,
                "event_id": self.event_id,
                "cogs": self.calculate_cogs(),
                "profit": self.calculate_profit(),
                "margin": self.calculate_margin(),
                "item_count": len(self.items),
                "total_quantity": sum(float(item.quantity) for item in self.items) if self.items else 0
            }
            
            # Add items
            sale_dict["items"] = []
            for item in self.items:
                item_dict = {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "sku": item.sku,
                    "quantity": float(item.quantity) if item.quantity else 0,
                    "unit_price": float(item.unit_price) if item.unit_price else 0.0,
                    "subtotal": float(item.subtotal) if item.subtotal else 0.0,
                    "is_taxable": item.is_taxable,
                    "batches_used": []
                }
                
                for batch in item.batches_used:
                    batch_dict = {
                        "batch_id": batch.batch_id,
                        "batch_number": batch.batch_number,
                        "quantity_deducted": float(batch.quantity_deducted) if batch.quantity_deducted else 0,
                        "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
                        "cost_price": float(batch.cost_price) if batch.cost_price else 0.0
                    }
                    item_dict["batches_used"].append(batch_dict)
                
                sale_dict["items"].append(item_dict)
            
            # Add payment details
            sale_dict["payment_details"] = []
            for payment in self.payment_details:
                payment_dict = {
                    "method": payment.method,
                    "amount_paid": float(payment.amount_paid) if payment.amount_paid else 0.0,
                    "change": float(payment.change) if payment.change else 0.0,
                    "status": payment.status,
                    "transaction_id": payment.transaction_id,
                    "timestamp": payment.timestamp.isoformat() if payment.timestamp else None
                }
                sale_dict["payment_details"].append(payment_dict)
            
            # Add discount breakdown
            sale_dict["discount_breakdown"] = []
            for breakdown in self.discount_breakdown:
                sale_dict["discount_breakdown"].append({
                    "promotion_discount": float(breakdown.promotion_discount) if breakdown.promotion_discount else 0.0,
                    "points_discount": float(breakdown.points_discount) if breakdown.points_discount else 0.0,
                    "total_discount": float(breakdown.total_discount) if breakdown.total_discount else 0.0
                })
            
            return sale_dict
            
        except Exception as e:
            logger.error(f"Error converting sale to dict: {str(e)}")
            return {}
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """
        Minimal dictionary representation (for listings)
        
        Returns:
            dict: Basic sale info
        """
        try:
            return {
                "id": self.sk.replace("SALE-", ""),
                "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
                "cashier_id": self.cashier_id,
                "shift_id": self.shift_id,
                "customer_id": self.customer_id,
                "total_amount": float(self.total_amount) if self.total_amount else 0.0,
                "status": self.status,
                "payment_method": self.payment_method,
                "item_count": len(self.items),
                "is_voided": self.is_voided
            }
        except Exception as e:
            logger.error(f"Error converting sale to simple dict: {str(e)}")
            return {}


# ============= SALE VALIDATION =============

def validate_sale_id(sale_id: str) -> bool:
    """
    Validate if a sale ID is in correct format
    
    Args:
        sale_id: Sale ID to validate
    
    Returns:
        bool: True if valid format, False otherwise
    """
    try:
        if not sale_id:
            return False
        
        # Check format: SALE-##### where ##### are exactly 5 digits
        if not sale_id.startswith('SALE-'):
            return False
        
        number_part = sale_id[5:]  # Remove "SALE-"
        if len(number_part) != 5:
            return False
        
        # Check if it's a valid number (00001-99999)
        number = int(number_part)
        return 1 <= number <= 99999
        
    except (ValueError, IndexError):
        return False


def validate_sale_data(cashier_id: str, shift_id: str, shift_seq: int,
                      payment_method: str) -> tuple[bool, str]:
    """
    Validate sale data before creation
    
    Args:
        cashier_id: Cashier ID to validate
        shift_id: Shift ID to validate
        shift_seq: Shift sequence to validate
        payment_method: Payment method to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not cashier_id:
        return False, "Cashier ID is required"
    
    if not shift_id:
        return False, "Shift ID is required"
    
    if shift_seq is None:
        return False, "Shift sequence is required"
    
    if shift_seq < 0:
        return False, "Shift sequence must be non-negative"
    
    if not payment_method:
        return False, "Payment method is required"
    
    # Validate payment method
    valid_methods = ['cash', 'credit_card', 'debit_card', 'digital_wallet']
    if payment_method.lower() not in valid_methods:
        return False, f"Payment method must be one of: {', '.join(valid_methods)}"
    
    return True, ""


# ============= BULK OPERATIONS =============

def batch_void_sales(sale_ids: List[str], reason: str = None) -> Dict:
    """
    Void multiple sales at once
    
    Args:
        sale_ids: List of sale IDs to void
        reason: Reason for voiding
    
    Returns:
        dict: Summary of void results
    """
    voided = []
    errors = []
    
    for sale_id in sale_ids:
        try:
            sale = Sale.get_by_id(sale_id)
            if not sale:
                errors.append(f"Sale not found: {sale_id}")
                continue
            
            if sale.is_voided:
                errors.append(f"Sale already voided: {sale_id}")
                continue
            
            sale.void_sale(reason)
            voided.append(sale_id)
            
        except Exception as e:
            errors.append(f"Failed to void sale {sale_id}: {str(e)}")
    
    return {
        "voided": voided,
        "total_voided": len(voided),
        "errors": errors,
        "success": len(errors) == 0
    }


# ============= SALE MANAGER =============

class SaleManager:
    """
    Manager class for sale-related operations
    """
    
    @staticmethod
    def get_sales_summary(start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        Get sales summary for a period
        
        Args:
            start_date: Start date (default: today)
            end_date: End date (default: today)
        
        Returns:
            dict: Sales summary
        """
        try:
            if not start_date:
                start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            if not end_date:
                end_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            sales = Sale.get_by_date_range(start_date, end_date)
            completed_sales = [s for s in sales if s.status == "completed" and not s.is_voided]
            
            total_revenue = sum(float(s.total_amount) for s in completed_sales)
            total_items = sum(len(s.items) for s in completed_sales)
            total_quantity = sum(sum(float(item.quantity) for item in s.items) for s in completed_sales)
            total_discount = sum(float(s.discount_amount) for s in completed_sales)
            total_tax = sum(float(s.tax_amount) for s in completed_sales)
            
            # Group by payment method
            payment_methods = {}
            for sale in completed_sales:
                method = sale.payment_method
                if method not in payment_methods:
                    payment_methods[method] = {
                        "count": 0,
                        "amount": 0.0
                    }
                payment_methods[method]["count"] += 1
                payment_methods[method]["amount"] += float(sale.total_amount)
            
            # Group by cashier
            cashiers = {}
            for sale in completed_sales:
                cashier_id = sale.cashier_id
                if cashier_id not in cashiers:
                    cashiers[cashier_id] = {
                        "count": 0,
                        "amount": 0.0
                    }
                cashiers[cashier_id]["count"] += 1
                cashiers[cashier_id]["amount"] += float(sale.total_amount)
            
            # Calculate average transaction value
            avg_transaction = total_revenue / len(completed_sales) if completed_sales else 0
            
            # Calculate voided sales
            voided_sales = [s for s in sales if s.is_voided]
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_sales": len(sales),
                "completed_sales": len(completed_sales),
                "voided_sales": len(voided_sales),
                "total_revenue": round(total_revenue, 2),
                "total_items": total_items,
                "total_quantity": total_quantity,
                "total_discount": round(total_discount, 2),
                "total_tax": round(total_tax, 2),
                "average_transaction": round(avg_transaction, 2),
                "by_payment_method": payment_methods,
                "by_cashier": cashiers,
                "voided_revenue": sum(float(s.total_amount) for s in voided_sales)
            }
            
        except Exception as e:
            logger.error(f"Error getting sales summary: {str(e)}")
            return {}
    
    @staticmethod
    def get_daily_sales_report(days: int = 30) -> List[Dict]:
        """
        Get daily sales report for the last N days
        
        Args:
            days: Number of days to include
        
        Returns:
            list: Daily sales report
        """
        try:
            daily_reports = []
            
            for i in range(days):
                date = datetime.utcnow() - timedelta(days=i)
                start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                summary = SaleManager.get_sales_summary(start_date, end_date)
                
                daily_reports.append({
                    "date": date.date().isoformat(),
                    "total_sales": summary.get("total_sales", 0),
                    "completed_sales": summary.get("completed_sales", 0),
                    "total_revenue": summary.get("total_revenue", 0),
                    "voided_sales": summary.get("voided_sales", 0)
                })
            
            return daily_reports
            
        except Exception as e:
            logger.error(f"Error getting daily sales report: {str(e)}")
            return []
    
    @staticmethod
    def get_top_products(start_date: datetime = None, end_date: datetime = None, 
                        limit: int = 10) -> List[Dict]:
        """
        Get top selling products by revenue
        
        Args:
            start_date: Start date
            end_date: End date
            limit: Number of top products to return
        
        Returns:
            list: Top products
        """
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            sales = Sale.get_by_date_range(start_date, end_date)
            completed_sales = [s for s in sales if s.status == "completed" and not s.is_voided]
            
            product_stats = {}
            
            for sale in completed_sales:
                for item in sale.items:
                    product_id = item.product_id
                    if product_id not in product_stats:
                        product_stats[product_id] = {
                            "product_id": product_id,
                            "product_name": item.product_name,
                            "sku": item.sku,
                            "total_quantity": 0,
                            "total_revenue": 0.0,
                            "total_items": 0
                        }
                    
                    stats = product_stats[product_id]
                    stats["total_quantity"] += float(item.quantity)
                    stats["total_revenue"] += float(item.subtotal)
                    stats["total_items"] += 1
            
            # Sort by revenue and limit
            top_products = sorted(
                product_stats.values(),
                key=lambda x: x["total_revenue"],
                reverse=True
            )[:limit]
            
            return top_products
            
        except Exception as e:
            logger.error(f"Error getting top products: {str(e)}")
            return []
    
    @staticmethod
    def sync_sales_to_pos(sale_ids: List[str] = None) -> Dict:
        """
        Sync sales to POS system
        
        Args:
            sale_ids: Specific sale IDs to sync (all pending if None)
        
        Returns:
            dict: Sync operation results
        """
        try:
            sales_to_sync = []
            
            if sale_ids:
                for sale_id in sale_ids:
                    sale = Sale.get_by_id(sale_id)
                    if sale:
                        sales_to_sync.append(sale)
            else:
                # Sync all sales with pending sync state
                for sale in Sale.get_all_sales():
                    if sale.sync_state == "pending":
                        sales_to_sync.append(sale)
            
            synced = []
            failed = []
            
            for sale in sales_to_sync:
                try:
                    # In a real implementation, this would call the POS API
                    # For now, simulate successful sync
                    sale.mark_synced()
                    synced.append(sale.sk.replace("SALE-", ""))
                    
                except Exception as e:
                    logger.error(f"Failed to sync sale {sale.sk}: {str(e)}")
                    sale.mark_sync_failed()
                    failed.append({
                        "sale_id": sale.sk.replace("SALE-", ""),
                        "error": str(e)
                    })
            
            return {
                "synced": synced,
                "failed": failed,
                "total_synced": len(synced),
                "total_failed": len(failed),
                "success_rate": len(synced) / len(sales_to_sync) if sales_to_sync else 0
            }
            
        except Exception as e:
            logger.error(f"Error syncing sales to POS: {str(e)}")
            return {"error": str(e)}
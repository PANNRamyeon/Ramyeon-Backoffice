"""
Cart Model — POS session cart
PK = "carts", SK = "CART-{uuid4}"
Single Table Design using RamyeonCornerDB
"""
import uuid
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute, BooleanAttribute,
)
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION

logger = logging.getLogger(__name__)


class CartItem(MapAttribute):
    product_id = UnicodeAttribute()
    product_name = UnicodeAttribute(default='')
    sku = UnicodeAttribute(default='')
    quantity = NumberAttribute(default=1)
    unit_price = NumberAttribute(default=0.0)
    subtotal = NumberAttribute(default=0.0)


class Cart(Model):
    """
    Transient POS cart — created at start of transaction, deleted/expired after sale.
    PK = "carts", SK = "CART-{uuid4}"
    """

    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION
        read_capacity_units = 5
        write_capacity_units = 5

    pk = UnicodeAttribute(hash_key=True, attr_name='PK', default='carts')
    sk = UnicodeAttribute(range_key=True, attr_name='SK')

    cashier_id = UnicodeAttribute()
    items = ListAttribute(of=CartItem, default=list)
    promotion_id = UnicodeAttribute(null=True)
    discount_amount = NumberAttribute(default=0.0)
    subtotal = NumberAttribute(default=0.0)
    total = NumberAttribute(default=0.0)
    created_at = UTCDateTimeAttribute()
    expires_at = UTCDateTimeAttribute()

    # ------------------------------------------------------------------ class

    @classmethod
    def create_cart(cls, cashier_id: str) -> 'Cart':
        if not cashier_id or not cashier_id.strip():
            raise ValueError('cashier_id is required')
        now = datetime.utcnow()
        cart = cls(
            pk='carts',
            sk=f'CART-{uuid.uuid4()}',
            cashier_id=cashier_id.strip(),
            items=[],
            promotion_id=None,
            discount_amount=0.0,
            subtotal=0.0,
            total=0.0,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        cart.save()
        return cart

    @classmethod
    def get_by_id(cls, cart_id: str) -> Optional['Cart']:
        try:
            if not cart_id.startswith('CART-'):
                cart_id = f'CART-{cart_id}'
            return cls.get('carts', cart_id)
        except cls.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f'Error fetching cart {cart_id}: {e}')
            return None

    # ------------------------------------------------------------------ instance

    def add_item(self, product_id: str, product_name: str, sku: str, unit_price: float, qty: int = 1) -> 'Cart':
        for item in self.items:
            if item.product_id == product_id:
                item.quantity = int(item.quantity) + qty
                item.subtotal = float(item.unit_price) * int(item.quantity)
                self.recalculate()
                self.save()
                return self
        self.items.append(CartItem(
            product_id=product_id,
            product_name=product_name,
            sku=sku,
            quantity=qty,
            unit_price=unit_price,
            subtotal=unit_price * qty,
        ))
        self.recalculate()
        self.save()
        return self

    def update_item_qty(self, product_id: str, qty: int) -> 'Cart':
        for item in self.items:
            if item.product_id == product_id:
                if qty <= 0:
                    return self.remove_item(product_id)
                item.quantity = qty
                item.subtotal = float(item.unit_price) * qty
                self.recalculate()
                self.save()
                return self
        raise ValueError(f'Product {product_id} not in cart')

    def remove_item(self, product_id: str) -> 'Cart':
        self.items = [i for i in self.items if i.product_id != product_id]
        self.recalculate()
        self.save()
        return self

    def clear(self) -> 'Cart':
        self.items = []
        self.subtotal = 0.0
        self.discount_amount = 0.0
        self.total = 0.0
        self.promotion_id = None
        self.save()
        return self

    def apply_promotion(self, promotion_id: str, discount_amount: float) -> 'Cart':
        self.promotion_id = promotion_id
        self.discount_amount = float(discount_amount)
        self.total = max(0.0, self.subtotal - self.discount_amount)
        self.save()
        return self

    def remove_promotion(self) -> 'Cart':
        self.promotion_id = None
        self.discount_amount = 0.0
        self.total = self.subtotal
        self.save()
        return self

    def recalculate(self) -> None:
        self.subtotal = sum(float(i.subtotal) for i in self.items)
        self.total = max(0.0, self.subtotal - float(self.discount_amount))

    def item_count(self) -> int:
        return sum(int(i.quantity) for i in self.items)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cart_id': self.sk,
            'cashier_id': self.cashier_id,
            'items': [
                {
                    'product_id': i.product_id,
                    'product_name': i.product_name,
                    'sku': i.sku,
                    'quantity': int(i.quantity),
                    'unit_price': float(i.unit_price),
                    'subtotal': float(i.subtotal),
                }
                for i in self.items
            ],
            'promotion_id': self.promotion_id,
            'discount_amount': float(self.discount_amount),
            'subtotal': float(self.subtotal),
            'total': float(self.total),
            'item_count': self.item_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
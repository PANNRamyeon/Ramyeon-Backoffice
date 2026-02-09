from datetime import datetime, timedelta
import uuid
from decimal import Decimal
from ..services.database_service import DatabaseService

# Helper to convert floats to Decimals for DynamoDB to avoid precision loss.
def floats_to_decimals(obj):
    if isinstance(obj, list):
        return [floats_to_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: floats_to_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        # Using string representation is safer for precision.
        return Decimal(str(obj))
    return obj

class OnlineTransactionService:
    """
    Service for creating customer web orders, adapted for DynamoDB.
    """

    def __init__(self):
        db_service = DatabaseService()
        # These names should match your DynamoDB tables.
        self.customers_table = db_service.get_table('customers')
        self.online_transactions_table = db_service.get_table('online_transactions')

    # ------------------------- Helpers -------------------------
    def _generate_order_id(self) -> str:
        """Generates a unique, non-sequential order ID."""
        return f"ONLINE-{uuid.uuid4()}"

    def _compute_items(self, items):
        computed = []
        subtotal = 0.0
        for item in items or []:
            price = float(item.get('price', 0))
            qty = int(item.get('quantity', 1))
            line_subtotal = round(price * qty, 2)
            computed.append({
                'product_id': item.get('product_id') or item.get('id') or item.get('productId'),
                'product_name': item.get('name') or item.get('product_name'),
                'quantity': qty,
                'price': price,
                'subtotal': line_subtotal,
            })
            subtotal += line_subtotal
        return computed, round(subtotal, 2)

    def _compute_fees(self, delivery_type: str):
        delivery_fee = 50.0 if (delivery_type or '').lower() == 'delivery' else 0.0
        service_fee = 15.0
        return round(delivery_fee, 2), round(service_fee, 2)

    def _compute_points_discount(self, points_to_redeem: int, subtotal: float):
        try:
            pts = int(points_to_redeem or 0)
        except (ValueError, TypeError):
            pts = 0
        discount = round(pts / 4.0, 2)  # 4 points = ₱1
        return float(min(discount, subtotal)), pts

    def _compute_points_earned(self, subtotal_after_discount: float) -> int:
        return int(round(subtotal_after_discount * 0.20))

    # ------------------------- Public API -------------------------
    def create_online_order(self, order_data: dict, customer_id: str):
        if not customer_id:
            raise ValueError("customer_id is required")

        items_in = order_data.get('items', [])
        delivery_address = order_data.get('delivery_address', {})
        payment_method = order_data.get('payment_method', 'cod')
        delivery_type = order_data.get('delivery_type', 'delivery')
        points_to_redeem = int(order_data.get('points_to_redeem', 0) or 0)
        notes = order_data.get('notes') or order_data.get('special_instructions') or ''

        # Lookup customer in DynamoDB
        customer = None
        if customer_id and customer_id != 'GUEST':
            try:
                # Assumes 'customer_id' is the primary key of the customers table.
                response = self.customers_table.get_item(Key={'customer_id': customer_id})
                customer = response.get('Item')
            except Exception as e:
                # It's good practice to log this error.
                print(f"Could not fetch customer {customer_id}: {e}")
                customer = None
        
        # Computation logic remains the same
        items, subtotal = self._compute_items(items_in)
        points_discount, pts_used = self._compute_points_discount(points_to_redeem, subtotal)
        subtotal_after_discount = round(subtotal - points_discount, 2)
        delivery_fee, service_fee = self._compute_fees(delivery_type)
        total_amount = round(subtotal_after_discount + delivery_fee + service_fee, 2)

        order_id = self._generate_order_id()

        # Prepare order record for DynamoDB.
        now_utc = datetime.utcnow()
        now_utc_iso = now_utc.isoformat() + "Z"  # ISO 8601 format (UTC)
        now_local_iso = (now_utc + timedelta(hours=8)).isoformat()

        order_record = {
            'order_id': order_id,  # Use 'order_id' as the primary key.
            'customer_id': customer_id or 'GUEST',
            'customer_name': (customer.get('full_name') if customer else 'Guest'),
            'customer_email': customer.get('email') if customer else None,
            'customer_phone': customer.get('phone') if customer else None,
            'transaction_date': now_utc_iso,
            'transaction_date_local': now_local_iso,
            'delivery_address': delivery_address,
            'delivery_type': delivery_type,
            'items': items,
            'subtotal': subtotal,
            'points_redeemed': pts_used,
            'points_discount': points_discount,
            'subtotal_after_discount': subtotal_after_discount,
            'delivery_fee': delivery_fee,
            'service_fee': service_fee,
            'total_amount': total_amount,
            'payment_method': payment_method,
            'payment_status': 'pending',
            'order_status': 'pending',
            'notes': notes,
            'status_history': [{'status': 'pending', 'timestamp': now_utc_iso}],
            'loyalty_points_earned': self._compute_points_earned(subtotal_after_discount),
            'created_at': now_utc_iso,
            'updated_at': now_utc_iso,
        }

        # Convert floats to Decimals and remove empty strings for DynamoDB compatibility.
        order_record_ddb = floats_to_decimals(order_record)
        order_record_ddb = {k: v for k, v in order_record_ddb.items() if v not in [None, '']}
        
        self.online_transactions_table.put_item(Item=order_record_ddb)

        return {
            'success': True,
            'data': {
                'order_id': order_id,
                'order': order_record,  # Return the original record with floats
            }
        }

from datetime import datetime
from ..database import db_manager
from .product_service import ProductService

class POSPromotionService:
    """
    POS-specific promotion service
    READ-ONLY: Applies promotions created by back office
    """
    
    def __init__(self):
        self.db = db_manager.get_database()
        self.collection = self.db.promotions
        self.product_service = ProductService()
    
    # ============================================
    # CORE POS METHODS (Keep these)
    # ============================================
    
    def get_active_promotions(self):
        """Get all currently active promotions for POS"""
        try:
            now = datetime.utcnow()
            promotions = list(self.collection.find({
                'is_active': True,
                'status': 'active',
                'start_date': {'$lte': now},
                'end_date': {'$gte': now}
            }))
            return {
                'success': True,
                'promotions': promotions
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting active promotions: {str(e)}'
            }
    
    def apply_best_promotion_to_cart(self, cart_items):
        """
        Find and apply the best promotion for cart items
        Returns promotion details and discount amount
        """
        try:
            active_result = self.get_active_promotions()
            if not active_result['success'] or not active_result['promotions']:
                return {
                    'success': True,
                    'discount_amount': 0,
                    'promotion_applied': None,
                    'affected_items': []
                }
            
            best_promotion = None
            best_discount = 0
            best_affected_items = []
            
            # Test each active promotion
            for promotion in active_result['promotions']:
                result = self.calculate_promotion_discount(promotion, cart_items)
                
                if result['discount_amount'] > best_discount:
                    best_discount = result['discount_amount']
                    best_promotion = promotion
                    best_affected_items = result['affected_items']
            
            return {
                'success': True,
                'discount_amount': best_discount,
                'promotion_applied': best_promotion,
                'affected_items': best_affected_items
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error applying promotion: {str(e)}'
            }
    
    def calculate_promotion_discount(self, promotion, cart_items):
        """
        Calculate discount for specific promotion
        
        Args:
            promotion: Promotion document from database
            cart_items: List of items from cart with product_id, quantity, unit_price
        
        Returns:
            {
                'discount_amount': float,
                'affected_items': list,
                'promotion_details': dict
            }
        """
        try:
            if not self._check_usage_limit(promotion):
                return {
                    'discount_amount': 0,
                    'affected_items': [],
                    'message': 'Promotion usage limit reached'
                }
            
            # Get eligible items
            eligible_items = self._get_eligible_items(promotion, cart_items)
            
            if not eligible_items:
                return {
                    'discount_amount': 0,
                    'affected_items': []
                }
            
            # Calculate discount based on type
            if promotion['type'] == 'percentage':
                discount = self._calculate_percentage_discount(
                    promotion, eligible_items
                )
            elif promotion['type'] == 'fixed_amount':
                discount = self._calculate_fixed_discount(
                    promotion, eligible_items
                )
            elif promotion['type'] == 'buy_x_get_y':
                discount = self._calculate_bxgy_discount(
                    promotion, eligible_items
                )
            else:
                discount = 0
            
            return {
                'discount_amount': round(discount, 2),
                'affected_items': eligible_items,
                'promotion_details': {
                    'id': promotion['promotion_id'],
                    'name': promotion['name'],
                    'type': promotion['type']
                }
            }
            
        except Exception as e:
            return {
                'discount_amount': 0,
                'affected_items': [],
                'error': str(e)
            }
    
    # ============================================
    # HELPER METHODS (Keep these)
    # ============================================
    
    def _get_eligible_items(self, promotion, cart_items):
        """Determine which cart items qualify for promotion"""
        eligible = []
        
        target_type = promotion['target_type']
        target_ids = promotion.get('target_ids', [])
        
        for item in cart_items:
            product = self.product_service.get_product_by_id(item['product_id'])
            if not product or not product.get('success'):
                continue
            
            product_data = product['product']
            is_eligible = False
            
            if target_type == 'all':
                is_eligible = True
            elif target_type == 'products':
                is_eligible = item['product_id'] in target_ids
            elif target_type == 'categories':
                # Check if product's category matches
                product_category = product_data.get('category_id')
                is_eligible = product_category in target_ids
            
            if is_eligible:
                eligible.append({
                    'product_id': item['product_id'],
                    'product_name': product_data.get('product_name', 'Unknown'),
                    'quantity': item['quantity'],
                    'unit_price': item['unit_price'],
                    'subtotal': item['quantity'] * item['unit_price']
                })
        
        return eligible
    
    def _calculate_percentage_discount(self, promotion, eligible_items):
        """Calculate percentage-based discount"""
        total_eligible = sum(item['subtotal'] for item in eligible_items)
        discount_percent = promotion['discount_value']
        return total_eligible * (discount_percent / 100)
    
    def _calculate_fixed_discount(self, promotion, eligible_items):
        """Calculate fixed amount discount"""
        total_eligible = sum(item['subtotal'] for item in eligible_items)
        fixed_amount = promotion['discount_value']
        return min(fixed_amount, total_eligible)
    
    def _calculate_bxgy_discount(self, promotion, eligible_items):
        """Calculate Buy X Get Y discount"""
        discount_config = promotion.get('discount_config', {})
        buy_qty = discount_config.get('buy_quantity', 2)
        get_qty = discount_config.get('get_quantity', 1)
        
        # Flatten items to individual units
        all_units = []
        for item in eligible_items:
            for _ in range(item['quantity']):
                all_units.append(item['unit_price'])
        
        if len(all_units) < buy_qty:
            return 0
        
        # Sort by price (cheapest first)
        all_units.sort()
        
        # Calculate free items
        sets = len(all_units) // (buy_qty + get_qty)
        free_items_count = sets * get_qty
        
        # Sum cheapest items that become free
        return sum(all_units[:free_items_count])
    
    def _check_usage_limit(self, promotion):
        """Check if promotion can still be used"""
        usage_limit = promotion.get('usage_limit')
        if not usage_limit:
            return True
        
        current_usage = promotion.get('current_usage', 0)
        return current_usage < usage_limit
    
    # ============================================
    # TRACKING METHOD (For usage statistics)
    # ============================================
    
    def record_promotion_usage(self, promotion_id, sale_data):
        """
        Record that promotion was used in a sale
        Called AFTER sale is completed in POSSalesService
        """
        try:
            discount_amount = sale_data.get('discount_amount', 0)
            
            self.collection.update_one(
                {'promotion_id': promotion_id},
                {
                    '$inc': {
                        'current_usage': 1,
                        'total_revenue_impact': discount_amount
                    },
                    '$push': {
                        'usage_history': {
                            'sale_id': sale_data.get('sale_id'),
                            'customer_id': sale_data.get('customer_id'),
                            'discount_amount': discount_amount,
                            'used_at': datetime.utcnow()
                        }
                    },
                    '$set': {
                        'last_used_at': datetime.utcnow()
                    }
                }
            )
            
            return {'success': True}
            
        except Exception as e:
            # Log but don't fail the sale
            return {'success': False, 'error': str(e)}

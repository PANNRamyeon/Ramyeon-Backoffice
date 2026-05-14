"""
POS Cart Views
Base URL: /api/v1/pos/carts/
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from models.Carts import Cart
from models.Product import Product
from models.Promotions import Promotion
import logging

logger = logging.getLogger(__name__)


def _get_cart_or_404(cart_id):
    cart = Cart.get_by_id(cart_id)
    if not cart:
        return None, Response(
            {'error': f'Cart {cart_id} not found'},
            status=status.HTTP_404_NOT_FOUND,
        )
    return cart, None


class CartCreateView(APIView):
    """POST /carts/"""

    def post(self, request):
        try:
            cashier_id = request.data.get('cashier_id')
            if not cashier_id:
                return Response({'error': 'cashier_id is required'}, status=status.HTTP_400_BAD_REQUEST)

            cart = Cart.create_cart(cashier_id=cashier_id)
            return Response(
                {'success': True, 'message': 'Cart created', 'data': cart.to_dict()},
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Error creating cart: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartDetailView(APIView):
    """GET/DELETE /carts/<cart_id>/"""

    def get(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err
            return Response({'success': True, 'data': cart.to_dict()}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error fetching cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err
            cart.delete()
            return Response({'success': True, 'message': f'Cart {cart_id} deleted'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error deleting cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartClearView(APIView):
    """POST /carts/<cart_id>/clear/"""

    def post(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err
            cart.clear()
            return Response(
                {'success': True, 'message': 'Cart cleared', 'data': cart.to_dict()},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f'Error clearing cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartItemsView(APIView):
    """POST /carts/<cart_id>/items/ — add item by product_id"""

    def post(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err

            product_id = request.data.get('product_id')
            quantity = int(request.data.get('quantity', 1))

            if not product_id:
                return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            if quantity <= 0:
                return Response({'error': 'quantity must be positive'}, status=status.HTTP_400_BAD_REQUEST)

            product = Product.get_by_id(product_id)
            if not product:
                return Response({'error': f'Product {product_id} not found'}, status=status.HTTP_404_NOT_FOUND)

            cart.add_item(
                product_id=product.sk,
                product_name=product.product_name or '',
                sku=product.SKU or '',
                unit_price=float(product.selling_price or 0),
                qty=quantity,
            )
            return Response({'success': True, 'data': cart.to_dict()}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Error adding item to cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartItemDetailView(APIView):
    """PUT/DELETE /carts/<cart_id>/items/<product_id>/"""

    def put(self, request, cart_id, product_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err

            quantity = request.data.get('quantity')
            if quantity is None:
                return Response({'error': 'quantity is required'}, status=status.HTTP_400_BAD_REQUEST)

            cart.update_item_qty(product_id, int(quantity))
            return Response({'success': True, 'data': cart.to_dict()}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Error updating item {product_id} in cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, cart_id, product_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err

            cart.remove_item(product_id)
            return Response({'success': True, 'data': cart.to_dict()}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Error removing item {product_id} from cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartScanView(APIView):
    """POST /carts/<cart_id>/scan/ — add item by barcode"""

    def post(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err

            barcode = request.data.get('barcode')
            if not barcode:
                return Response({'error': 'barcode is required'}, status=status.HTTP_400_BAD_REQUEST)

            product = Product.get_by_barcode(barcode)
            if not product:
                return Response(
                    {'error': f'No product found for barcode {barcode}'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            cart.add_item(
                product_id=product.sk,
                product_name=product.product_name or '',
                sku=product.SKU or '',
                unit_price=float(product.selling_price or 0),
                qty=1,
            )
            return Response({'success': True, 'data': cart.to_dict()}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error scanning barcode in cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartPromoView(APIView):
    """POST/DELETE /carts/<cart_id>/promotion/"""

    def post(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err

            promotion_id = request.data.get('promotion_id')
            if not promotion_id:
                return Response({'error': 'promotion_id is required'}, status=status.HTTP_400_BAD_REQUEST)

            promo = Promotion.get_by_id(promotion_id)
            if not promo:
                return Response({'error': f'Promotion {promotion_id} not found'}, status=status.HTTP_404_NOT_FOUND)
            if not promo.is_active():
                return Response({'error': 'Promotion is not active'}, status=status.HTTP_400_BAD_REQUEST)

            discount = promo.calculate_discount_amount(float(cart.subtotal))
            cart.apply_promotion(promotion_id=promo.sk, discount_amount=discount)
            return Response({'success': True, 'data': cart.to_dict()}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error applying promotion to cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err

            cart.remove_promotion()
            return Response({'success': True, 'data': cart.to_dict()}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error removing promotion from cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartAvailablePromosView(APIView):
    """GET /carts/<cart_id>/promotions/available/"""

    def get(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err

            active_promos = Promotion.get_active_promotions()
            applicable = []
            for promo in active_promos:
                if promo.is_active():
                    discount = promo.calculate_discount_amount(float(cart.subtotal))
                    applicable.append({
                        'promotion_id': promo.sk,
                        'name': promo.name,
                        'discount_type': promo.promotion_type,
                        'discount_value': promo.discount_value,
                        'discount_amount': discount,
                    })

            return Response(
                {'success': True, 'promotions': applicable, 'count': len(applicable)},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f'Error getting available promotions for cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartPrepareCheckoutView(APIView):
    """POST /carts/<cart_id>/prepare-checkout/ — validate cart and return sale_data"""

    def post(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err

            if not cart.items:
                return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

            sale_data = {
                'cart_id': cart.sk,
                'cashier_id': cart.cashier_id,
                'items': [
                    {
                        'product_id': i.product_id,
                        'product_name': i.product_name,
                        'sku': i.sku,
                        'quantity': int(i.quantity),
                        'unit_price': float(i.unit_price),
                        'subtotal': float(i.subtotal),
                    }
                    for i in cart.items
                ],
                'promotion_id': cart.promotion_id,
                'discount_amount': float(cart.discount_amount),
                'subtotal': float(cart.subtotal),
                'total_amount': float(cart.total),
            }

            return Response({'success': True, 'sale_data': sale_data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error preparing checkout for cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartItemCountView(APIView):
    """GET /carts/<cart_id>/item-count/"""

    def get(self, request, cart_id):
        try:
            cart, err = _get_cart_or_404(cart_id)
            if err:
                return err

            return Response(
                {'success': True, 'item_count': cart.item_count()},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f'Error getting item count for cart {cart_id}: {e}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

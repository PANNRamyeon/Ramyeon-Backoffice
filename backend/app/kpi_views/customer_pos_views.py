from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from ..services.customer_service import CustomerService
from ..services.promotions_service import PromotionService
from ..kpi_views.customer_loyalty_views import loyalty_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def scan_user_qr(request):
    """
    Scan user QR code to retrieve customer information - matches ramyeonsite backend API
    Used by cashiers to identify customers at checkout
    
    POST /api/pos/scan-user/
    Body: {"qr_code": "USER_QR_CODE_HERE"}
    """
    try:
        qr_code = request.data.get('qr_code')
        
        if not qr_code:
            return Response(
                {'error': 'QR code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer_service = CustomerService()
        customer = customer_service.get_customer_by_qr_code(qr_code)
        
        if not customer:
            return Response(
                {'error': 'Invalid QR code. Customer not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Format customer data for POS display
        customer_data = {
            '_id': str(customer['_id']),
            'customer_id': customer.get('customer_id', ''),
            'full_name': customer.get('full_name', ''),
            'email': customer.get('email', ''),
            'phone': customer.get('phone', ''),
            'loyalty_points': customer.get('loyalty_points', 0),
            'status': customer.get('status', 'active')
        }
        
        return Response({
            'success': True,
            'customer': customer_data,
            'message': f'Customer {customer.get("full_name", "Unknown")} identified successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error scanning user QR: {e}")
        return Response(
            {'error': 'An error occurred while scanning QR code'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def scan_promotion_qr(request):
    """
    Scan promotion QR code to retrieve promotion details - matches ramyeonsite backend API
    Used by cashiers to apply promotions at checkout
    
    POST /api/pos/scan-promotion/
    Body: {"qr_code": "PROMO_QR_CODE_HERE"}
    """
    try:
        qr_code = request.data.get('qr_code')
        
        if not qr_code:
            return Response(
                {'error': 'QR code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        promotion_service = PromotionService()
        promotion = promotion_service.collection.find_one({
            'qr_code': qr_code,
            'status': 'active',
            'isDeleted': {'$ne': True}
        })
        
        if not promotion:
            return Response(
                {'error': 'Invalid promotion QR code'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if promotion is valid (date range)
        now = datetime.utcnow()
        if promotion.get('start_date') and promotion['start_date'] > now:
            return Response(
                {'error': 'This promotion is not yet active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if promotion.get('end_date') and promotion['end_date'] < now:
            return Response(
                {'error': 'This promotion has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Format promotion data for POS display
        promotion_data = {
            '_id': str(promotion['_id']),
            'promotion_name': promotion.get('promotion_name', ''),
            'description': promotion.get('description', ''),
            'discount_type': promotion.get('discount_type', ''),
            'discount_value': promotion.get('discount_value', 0),
            'applicable_products': promotion.get('applicable_products', [])
        }
        
        return Response({
            'success': True,
            'promotion': promotion_data,
            'message': f'Promotion "{promotion.get("promotion_name", "Unknown")}" scanned successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error scanning promotion QR: {e}")
        return Response(
            {'error': 'An error occurred while scanning promotion QR code'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def redeem_promotion(request):
    """
    Redeem a promotion for a customer - matches ramyeonsite backend API
    POST /api/pos/redeem-promotion/
    Body: {
        "customer_id": "customer_id",
        "promotion_id": "promotion_id",
        "scanned_by": "cashier_name"
    }
    """
    try:
        customer_id = request.data.get('customer_id')
        promotion_id = request.data.get('promotion_id')
        scanned_by = request.data.get('scanned_by', 'Unknown Cashier')
        
        if not customer_id or not promotion_id:
            return Response(
                {'error': 'Customer ID and Promotion ID are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # This would need to be implemented based on your promotion redemption schema
        # For now, return a basic success response
        return Response({
            'success': True,
            'message': 'Promotion redeemed successfully',
            'scanned_by': scanned_by
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error redeeming promotion: {e}")
        return Response(
            {'error': 'An error occurred while redeeming promotion'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def award_points_manual(request):
    """
    Award points to customer manually - matches ramyeonsite backend API
    POST /api/pos/award-points/
    Body: {
        "customer_id": "customer_id",
        "points": 100,
        "description": "Manual award by cashier"
    }
    """
    try:
        customer_id = request.data.get('customer_id')
        points = request.data.get('points')
        description = request.data.get('description', 'Manual award by POS')
        
        if not customer_id or not points:
            return Response(
                {'error': 'Customer ID and points are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = loyalty_service.award_points(customer_id, int(points), description)
        
        return Response({
            'success': success,
            'message': message
        }, status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error awarding points: {e}")
        return Response(
            {'error': 'An error occurred while awarding points'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def process_order_points(request):
    """
    Process order and award points based on order amount - matches ramyeonsite backend API
    POST /api/pos/process-order-points/
    Body: {
        "customer_id": "customer_id",
        "order_amount": 100.00
    }
    """
    try:
        customer_id = request.data.get('customer_id')
        order_amount = request.data.get('order_amount')
        
        if not customer_id or not order_amount:
            return Response(
                {'error': 'Customer ID and order amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate points based on order amount (you may want to adjust this logic)
        # For example: 1 point per dollar spent
        points_to_award = int(float(order_amount))
        
        success, message = loyalty_service.award_points(
            customer_id, 
            points_to_award, 
            f'Points for order amount: {order_amount}'
        )
        
        return Response({
            'success': success,
            'message': message,
            'points_awarded': points_to_award if success else 0
        }, status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error processing order points: {e}")
        return Response(
            {'error': 'An error occurred while processing order points'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_by_qr(request, qr_code):
    """
    Get user information by QR code - matches ramyeonsite backend API
    GET /api/pos/user/<qr_code>/
    """
    try:
        if not qr_code:
            return Response(
                {'error': 'QR code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer_service = CustomerService()
        customer = customer_service.get_customer_by_qr_code(qr_code)
        
        if not customer:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        customer_data = {
            '_id': str(customer['_id']),
            'customer_id': customer.get('customer_id', ''),
            'full_name': customer.get('full_name', ''),
            'email': customer.get('email', ''),
            'phone': customer.get('phone', ''),
            'loyalty_points': customer.get('loyalty_points', 0),
            'status': customer.get('status', 'active')
        }
        
        return Response({
            'success': True,
            'customer': customer_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting user by QR: {e}")
        return Response(
            {'error': 'An error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_promotion_by_qr(request, qr_code):
    """
    Get promotion information by QR code - matches ramyeonsite backend API
    GET /api/pos/promotion/<qr_code>/
    """
    try:
        if not qr_code:
            return Response(
                {'error': 'QR code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        promotion_service = PromotionService()
        promotion = promotion_service.collection.find_one({
            'qr_code': qr_code,
            'status': 'active',
            'isDeleted': {'$ne': True}
        })
        
        if not promotion:
            return Response(
                {'error': 'Promotion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if promotion is valid
        now = datetime.utcnow()
        if promotion.get('start_date') and promotion['start_date'] > now:
            return Response(
                {'error': 'Promotion not yet active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if promotion.get('end_date') and promotion['end_date'] < now:
            return Response(
                {'error': 'Promotion has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        promotion_data = {
            '_id': str(promotion['_id']),
            'promotion_name': promotion.get('promotion_name', ''),
            'description': promotion.get('description', ''),
            'discount_type': promotion.get('discount_type', ''),
            'discount_value': promotion.get('discount_value', 0)
        }
        
        return Response({
            'success': True,
            'promotion': promotion_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting promotion by QR: {e}")
        return Response(
            {'error': 'An error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def pos_dashboard(request):
    """
    POS dashboard endpoint - matches ramyeonsite backend API
    GET /api/pos/dashboard/
    """
    try:
        # This could return POS dashboard statistics
        # For now, return a basic status
        return Response({
            'success': True,
            'service': 'POS System',
            'status': 'active',
            'timestamp': datetime.utcnow().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in POS dashboard: {e}")
        return Response(
            {'error': 'An error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

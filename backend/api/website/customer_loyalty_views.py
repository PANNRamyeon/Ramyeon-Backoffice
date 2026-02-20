from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from app.services.identity.customer_service import CustomerService
from app.decorators.authenticationDecorator import jwt_required

from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CustomerLoyaltyService:
    """Customer-facing loyalty service - uses existing PANN_POS customer service"""
    
    def __init__(self):
        self.customer_service = CustomerService()
        # TODO: Refactor to use PynamoDB models instead of MongoDB-style collections
        # self.db = self.customer_service.db
        # self.customer_collection = self.customer_service.customer_collection
    
    def get_customer_points(self, customer_id):
        """Get customer's loyalty points balance"""
        try:
            # Try to find by string
            customer = self.customer_collection.find_one({
                '_id': customer_id,
                'isDeleted': {'$ne': True}
            })
            
            if not customer:
                return None
            
            return customer.get('loyalty_points', 0)
            
        except Exception as e:
            logger.error(f"Error getting customer points: {e}")
            return None
    
    def get_points_history(self, customer_id, limit=50):
        """Get customer's loyalty points transaction history"""
        try:
            # This would need to be implemented based on your transaction history schema
            # For now, return a basic response
            return {
                'transactions': [],
                'total_count': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting points history: {e}")
            return {
                'transactions': [],
                'total_count': 0
            }
    
    def validate_points_redemption(self, customer_id, points_to_redeem):
        """Validate if customer can redeem points"""
        try:
            current_points = self.get_customer_points(customer_id)
            
            if current_points is None:
                return False, "Customer not found"
            
            if current_points < points_to_redeem:
                return False, "Insufficient points"
            
            if points_to_redeem <= 0:
                return False, "Invalid points amount"
            
            return True, "Valid redemption"
            
        except Exception as e:
            logger.error(f"Error validating points redemption: {e}")
            return False, "Error validating redemption"
    
    def redeem_points(self, customer_id, points_to_redeem, description="Points redeemed"):
        """Redeem customer points"""
        try:
            # Validate first
            is_valid, message = self.validate_points_redemption(customer_id, points_to_redeem)
            if not is_valid:
                return False, message
            
            # Get current customer
            customer = self.customer_collection.find_one({
                '_id': customer_id,
                'isDeleted': {'$ne': True}
            })
            
            if not customer:
                return False, "Customer not found"
            
            new_points = customer.get('loyalty_points', 0) - points_to_redeem
            
            # Update customer points
            result = self.customer_collection.update_one(
                {'_id': customer['_id']},
                {
                    '$set': {
                        'loyalty_points': new_points,
                        'last_updated': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                return True, f"Successfully redeemed {points_to_redeem} points"
            else:
                return False, "Failed to update points"
                
        except Exception as e:
            logger.error(f"Error redeeming points: {e}")
            return False, "Error redeeming points"
    
    def award_points(self, customer_id, points, description="Points awarded"):
        """Award points to customer"""
        try:
            # Get current customer
            customer = self.customer_collection.find_one({
                '_id': customer_id,
                'isDeleted': {'$ne': True}
            })
            
            if not customer:
                return False, "Customer not found"
            
            current_points = customer.get('loyalty_points', 0)
            new_points = current_points + points
            
            # Update customer points
            result = self.customer_collection.update_one(
                {'_id': customer['_id']},
                {
                    '$set': {
                        'loyalty_points': new_points,
                        'last_updated': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                return True, f"Successfully awarded {points} points"
            else:
                return False, "Failed to update points"
                
        except Exception as e:
            logger.error(f"Error awarding points: {e}")
            return False, "Error awarding points"

# Initialize loyalty service
loyalty_service = CustomerLoyaltyService()

@api_view(['GET'])
@jwt_required
def get_loyalty_balance(request):
    """Get customer's loyalty points balance - matches ramyeonsite backend API"""
    try:
        customer_id = request.customer['customer_id']
        
        balance = loyalty_service.get_customer_points(customer_id)
        
        if balance is None:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            'success': True,
            'balance': balance
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get loyalty balance error: {str(e)}")
        return Response(
            {'error': 'An error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@jwt_required
def get_loyalty_history(request):
    """Get customer's loyalty points transaction history - matches ramyeonsite backend API"""
    try:
        customer_id = request.customer['customer_id']
        limit = int(request.GET.get('limit', 50))
        
        history = loyalty_service.get_points_history(customer_id, limit)
        
        return Response({
            'success': True,
            'history': history
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get loyalty history error: {str(e)}")
        return Response(
            {'error': 'An error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@jwt_required
@csrf_exempt
def validate_points_redemption(request):
    """Validate if customer can redeem points - matches ramyeonsite backend API"""
    try:
        customer_id = request.customer['customer_id']
        points_to_redeem = request.data.get('points_to_redeem')
        
        if not points_to_redeem:
            return Response(
                {'error': 'Points to redeem is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_valid, message = loyalty_service.validate_points_redemption(
            customer_id, int(points_to_redeem)
        )
        
        return Response({
            'success': is_valid,
            'message': message,
            'can_redeem': is_valid
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Validate points redemption error: {str(e)}")
        return Response(
            {'error': 'An error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@jwt_required
@csrf_exempt
def redeem_points(request):
    """Redeem customer points - matches ramyeonsite backend API"""
    try:
        customer_id = request.customer['customer_id']
        points_to_redeem = request.data.get('points_to_redeem')
        description = request.data.get('description', 'Points redeemed')
        
        if not points_to_redeem:
            return Response(
                {'error': 'Points to redeem is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = loyalty_service.redeem_points(
            customer_id, int(points_to_redeem), description
        )
        
        return Response({
            'success': success,
            'message': message
        }, status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Redeem points error: {str(e)}")
        return Response(
            {'error': 'An error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@jwt_required
@csrf_exempt
def award_points(request):
    """Award points to customer - matches ramyeonsite backend API"""
    try:
        customer_id = request.customer['customer_id']
        points = request.data.get('points')
        description = request.data.get('description', 'Points awarded')
        
        if not points:
            return Response(
                {'error': 'Points amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = loyalty_service.award_points(
            customer_id, int(points), description
        )
        
        return Response({
            'success': success,
            'message': message
        }, status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Award points error: {str(e)}")
        return Response(
            {'error': 'An error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def loyalty_health_check(request):
    """Loyalty service health check - matches ramyeonsite backend API"""
    return Response({
        "service": "Customer Loyalty Points",
        "status": "active",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }, status=status.HTTP_200_OK)

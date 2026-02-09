from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from ..services.promotions_service import PromotionService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CustomerPromotionService:
    """Customer-facing promotion service (READ-ONLY) - uses existing PANN_POS promotion service"""
    
    def __init__(self):
        self.promotion_service = PromotionService()
        self.db = self.promotion_service.db
        self.promotion_collection = self.promotion_service.collection
    
    def get_all_active_promotions(self, filters=None, page=1, limit=20):
        """Get all active promotions available for customers"""
        try:
            # Base query for active, non-deleted promotions
            query = {
                'status': 'active',
                'isDeleted': {'$ne': True}
            }
            
            # Add date range filter to only show currently valid promotions
            now = datetime.utcnow()
            query['start_date'] = {'$lte': now}
            query['$or'] = [
                {'end_date': {'$gte': now}},
                {'end_date': {'$exists': False}}
            ]
            
            # Apply additional filters
            if filters:
                if filters.get('type'):
                    query['type'] = filters['type']
                if filters.get('target_type'):
                    query['target_type'] = filters['target_type']
                if filters.get('search_query'):
                    search_term = filters['search_query']
                    query['$and'] = [
                        query,
                        {
                            '$or': [
                                {'promotion_name': {'$regex': search_term, '$options': 'i'}},
                                {'description': {'$regex': search_term, '$options': 'i'}}
                            ]
                        }
                    ]
            
            # Count total
            total = self.promotion_collection.count_documents(query)
            
            # Get promotions with pagination
            skip = (page - 1) * limit
            promotions_cursor = self.promotion_collection.find(query).sort('created_at', -1).skip(skip).limit(limit)
            
            promotions = []
            for promotion in promotions_cursor:
                promotion_data = self._format_promotion_for_customer(promotion)
                promotions.append(promotion_data)
            
            # Calculate pagination
            total_pages = (total + limit - 1) // limit
            pagination = {
                'current_page': page,
                'total_pages': total_pages,
                'total_items': total,
                'items_per_page': limit,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
            
            return {
                'success': True,
                'promotions': promotions,
                'pagination': pagination
            }
            
        except Exception as e:
            logger.error(f"Error getting active promotions: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_promotion_by_id(self, promotion_id):
        """Get single promotion by ID"""
        try:
            promotion = self.promotion_collection.find_one({
                '_id': promotion_id,
                'status': 'active',
                'isDeleted': {'$ne': True}
            })
            
            if not promotion:
                return {
                    'success': False,
                    'message': 'Promotion not found'
                }
            
            # Check if promotion is currently valid
            now = datetime.utcnow()
            if promotion.get('start_date') and promotion['start_date'] > now:
                return {
                    'success': False,
                    'message': 'Promotion not yet started'
                }
            
            if promotion.get('end_date') and promotion['end_date'] < now:
                return {
                    'success': False,
                    'message': 'Promotion has expired'
                }
            
            promotion_data = self._format_promotion_for_customer(promotion)
            
            return {
                'success': True,
                'promotion': promotion_data
            }
            
        except Exception as e:
            logger.error(f"Error getting promotion by ID: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_promotions_by_product(self, product_id, page=1, limit=20):
        """Get promotions for specific product"""
        try:
            now = datetime.utcnow()
            query = {
                'status': 'active',
                'isDeleted': {'$ne': True},
                'start_date': {'$lte': now},
                '$or': [
                    {'end_date': {'$gte': now}},
                    {'end_date': {'$exists': False}}
                ],
                '$or': [
                    {'applicable_products': product_id},
                    {'applicable_products': {'$elemMatch': {'$eq': product_id}}}
                ]
            }
            
            total = self.promotion_collection.count_documents(query)
            skip = (page - 1) * limit
            
            promotions_cursor = self.promotion_collection.find(query).sort('created_at', -1).skip(skip).limit(limit)
            
            promotions = []
            for promotion in promotions_cursor:
                promotion_data = self._format_promotion_for_customer(promotion)
                promotions.append(promotion_data)
            
            total_pages = (total + limit - 1) // limit
            pagination = {
                'current_page': page,
                'total_pages': total_pages,
                'total_items': total,
                'items_per_page': limit,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
            
            return {
                'success': True,
                'promotions': promotions,
                'pagination': pagination
            }
            
        except Exception as e:
            logger.error(f"Error getting promotions by product: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def search_promotions(self, search_term, page=1, limit=20):
        """Search promotions"""
        try:
            if not search_term:
                return self.get_all_active_promotions(page=page, limit=limit)
            
            filters = {'search_query': search_term}
            return self.get_all_active_promotions(filters=filters, page=page, limit=limit)
            
        except Exception as e:
            logger.error(f"Error searching promotions: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def calculate_discount(self, promotion_id, amount, product_id=None):
        """Calculate discount for a promotion"""
        try:
            promotion_result = self.get_promotion_by_id(promotion_id)
            if not promotion_result['success']:
                return promotion_result
            
            promotion = promotion_result['promotion']
            
            # Basic discount calculation - you may need to adjust based on your promotion schema
            discount_type = promotion.get('discount_type', 'percentage')
            discount_value = float(promotion.get('discount_value', 0))
            
            if discount_type == 'percentage':
                discount_amount = amount * (discount_value / 100)
            else:  # fixed amount
                discount_amount = min(discount_value, amount)
            
            return {
                'success': True,
                'discount_amount': round(discount_amount, 2),
                'discount_type': discount_type,
                'discount_value': discount_value,
                'original_amount': amount,
                'final_amount': round(amount - discount_amount, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating discount: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def _format_promotion_for_customer(self, promotion):
        """Format promotion data for customer consumption - remove sensitive fields"""
        try:
            return {
                '_id': str(promotion['_id']),
                'promotion_name': promotion.get('promotion_name', ''),
                'description': promotion.get('description', ''),
                'discount_type': promotion.get('discount_type', ''),
                'discount_value': float(promotion.get('discount_value', 0)),
                'applicable_products': promotion.get('applicable_products', []),
                'start_date': promotion.get('start_date').isoformat() if promotion.get('start_date') else None,
                'end_date': promotion.get('end_date').isoformat() if promotion.get('end_date') else None,
                'status': promotion.get('status', 'active'),
                'created_at': promotion.get('created_at').isoformat() if promotion.get('created_at') else None,
                'updated_at': promotion.get('last_updated').isoformat() if promotion.get('last_updated') else None
            }
        except Exception as e:
            logger.error(f"Error formatting promotion: {e}")
            return {}

@method_decorator(csrf_exempt, name='dispatch')
class CustomerPromotionHealthCheckView(APIView):
    """Customer promotion health check - matches ramyeonsite backend API"""
    
    def get(self, request):
        return Response({
            "service": "Customer Promotions",
            "status": "active",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerPromotionListView(APIView):
    """Customer promotion list view - matches ramyeonsite backend API"""
    
    def get(self, request):
        try:
            service = CustomerPromotionService()
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            filters = {}
            if request.GET.get('type'):
                filters['type'] = request.GET.get('type')
            if request.GET.get('target_type'):
                filters['target_type'] = request.GET.get('target_type')
            if request.GET.get('q'):
                filters['search_query'] = request.GET.get('q')
            
            result = service.get_all_active_promotions(filters=filters, page=page, limit=limit)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'promotions': result['promotions'],
                        'pagination': result['pagination']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Error retrieving promotions')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in CustomerPromotionListView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerActivePromotionsView(APIView):
    """Customer active promotions view - matches ramyeonsite backend API"""
    
    def get(self, request):
        try:
            service = CustomerPromotionService()
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            result = service.get_all_active_promotions(page=page, limit=limit)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'promotions': result['promotions'],
                        'pagination': result['pagination']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Error retrieving active promotions')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in CustomerActivePromotionsView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerPromotionSearchView(APIView):
    """Customer promotion search view - matches ramyeonsite backend API"""
    
    def get(self, request):
        try:
            service = CustomerPromotionService()
            
            search_term = request.GET.get('q', '')
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            result = service.search_promotions(search_term, page=page, limit=limit)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'promotions': result['promotions'],
                        'pagination': result['pagination'],
                        'search_term': search_term
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Search failed')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in CustomerPromotionSearchView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerPromotionDetailView(APIView):
    """Customer promotion detail view - matches ramyeonsite backend API"""
    
    def get(self, request, promotion_id):
        try:
            service = CustomerPromotionService()
            
            result = service.get_promotion_by_id(promotion_id)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'promotion': result['promotion']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Promotion not found')
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error in CustomerPromotionDetailView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerPromotionsByProductView(APIView):
    """Customer promotions by product view - matches ramyeonsite backend API"""
    
    def get(self, request, product_id):
        try:
            service = CustomerPromotionService()
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            result = service.get_promotions_by_product(product_id, page=page, limit=limit)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'promotions': result['promotions'],
                        'pagination': result['pagination']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'No promotions found for product')
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error in CustomerPromotionsByProductView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerPromotionsByCategoryView(APIView):
    """Customer promotions by category view - matches ramyeonsite backend API"""
    
    def get(self, request, category_id):
        try:
            service = CustomerPromotionService()
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            # You may need to implement this based on your promotion schema
            # For now, return a basic response
            result = service.get_all_active_promotions(page=page, limit=limit)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'promotions': result['promotions'],
                        'pagination': result['pagination']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'No promotions found for category')
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error in CustomerPromotionsByCategoryView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerPromotionDiscountCalculatorView(APIView):
    """Customer promotion discount calculator - matches ramyeonsite backend API"""
    
    def post(self, request):
        try:
            service = CustomerPromotionService()
            
            promotion_id = request.data.get('promotion_id')
            amount = float(request.data.get('amount', 0))
            product_id = request.data.get('product_id')
            
            if not promotion_id or not amount:
                return Response({
                    'success': False,
                    'message': 'Promotion ID and amount are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = service.calculate_discount(promotion_id, amount, product_id)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': result
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Failed to calculate discount')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error in CustomerPromotionDiscountCalculatorView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

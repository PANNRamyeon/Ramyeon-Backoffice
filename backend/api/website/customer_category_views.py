from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from app.services.inventory.category_service import CategoryService
from app.services.inventory.product_service import ProductService

import logging

logger = logging.getLogger(__name__)

class CustomerCategoryService:
    """Customer-facing category service (READ-ONLY) - uses existing PANN_POS services"""
    
    def __init__(self):
        self.category_service = CategoryService()
        self.product_service = ProductService()
        self.db = self.category_service.db
        self.category_collection = self.category_service.collection
        self.product_collection = self.product_service.product_collection
    
    def get_all_active_categories(self):
        """Get all active categories available for customers"""
        try:
            query = {
                'status': 'active',
                'isDeleted': {'$ne': True}
            }
            
            categories_cursor = self.category_collection.find(query).sort('category_name', 1)
            
            categories = []
            for category in categories_cursor:
                category_data = self._format_category_for_customer(category)
                
                # Count active products in this category
                product_count = self.product_collection.count_documents({
                    'category_id': category['_id'],
                    'status': 'active',
                    'isDeleted': {'$ne': True},
                    'stock': {'$gt': 0}
                })
                
                category_data['product_count'] = product_count
                categories.append(category_data)
            
            return {
                'success': True,
                'categories': categories,
                'count': len(categories)
            }
            
        except Exception as e:
            logger.error(f"Error getting active categories: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_category_by_id(self, category_id):
        """Get single category by ID"""
        try:
            # Try to find by string
            category = self.category_collection.find_one({
                '_id': category_id,
                'status': 'active',
                'isDeleted': {'$ne': True}
            })
            
            if not category:
                return {
                    'success': False,
                    'message': 'Category not found'
                }
            
            category_data = self._format_category_for_customer(category)
            
            return {
                'success': True,
                'category': category_data
            }
            
        except Exception as e:
            logger.error(f"Error getting category by ID: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_category_with_products(self, category_id, subcategory_name=None, page=1, limit=20):
        """Get category with its products"""
        try:
            # Get category first
            category_result = self.get_category_by_id(category_id)
            if not category_result['success']:
                return category_result
            
            category_data = category_result['category']
            
            # Build product query
            query = {
                'category_id': category_id,
                'status': 'active',
                'isDeleted': {'$ne': True},
                'stock': {'$gt': 0}
            }
            
            # Add subcategory filter if specified
            if subcategory_name:
                query['sub_categories'] = {'$elemMatch': {'name': subcategory_name}}
            
            # Count total products
            total = self.product_collection.count_documents(query)
            
            # Get products with pagination
            skip = (page - 1) * limit
            products_cursor = self.product_collection.find(query).sort('product_name', 1).skip(skip).limit(limit)
            
            products = []
            for product in products_cursor:
                product_data = self._format_product_for_customer(product)
                products.append(product_data)
            
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
                'category': category_data,
                'products': products,
                'pagination': pagination
            }
            
        except Exception as e:
            logger.error(f"Error getting category with products: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def _format_category_for_customer(self, category):
        """Format category data for customer consumption"""
        try:
            return {
                '_id': str(category['_id']),
                'category_name': category.get('category_name', ''),
                'description': category.get('description', ''),
                'status': category.get('status', 'active'),
                'sub_categories': category.get('sub_categories', []),
                'image_url': category.get('image_url', ''),
                'date_created': category.get('date_created').isoformat() if category.get('date_created') else None,
                'last_updated': category.get('last_updated').isoformat() if category.get('last_updated') else None
            }
        except Exception as e:
            logger.error(f"Error formatting category: {e}")
            return {}
    
    def _format_product_for_customer(self, product):
        """Format product data for customer consumption"""
        try:
            return {
                '_id': str(product['_id']),
                'product_name': product.get('product_name', ''),
                'category_id': product.get('category_id', ''),
                'SKU': product.get('SKU', ''),
                'selling_price': float(product.get('selling_price', 0)),
                'stock': int(product.get('stock', 0)),
                'unit': product.get('unit', 'pcs'),
                'is_taxable': product.get('is_taxable', True),
                'status': product.get('status', 'active'),
                'date_received': product.get('date_received').isoformat() if product.get('date_received') else None,
                'low_stock_threshold': product.get('low_stock_threshold', 10)
            }
        except Exception as e:
            logger.error(f"Error formatting product: {e}")
            return {}

@method_decorator(csrf_exempt, name='dispatch')
class CustomerCategoryListView(APIView):
    """Customer category list view - matches ramyeonsite backend API"""
    
    def get(self, request):
        try:
            service = CustomerCategoryService()
            
            result = service.get_all_active_categories()
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'categories': result['categories'],
                        'count': result['count']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Error retrieving categories')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in CustomerCategoryListView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerCategoryDetailView(APIView):
    """Customer category detail view - matches ramyeonsite backend API"""
    
    def get(self, request, category_id):
        try:
            service = CustomerCategoryService()
            
            result = service.get_category_by_id(category_id)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': result['category']
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Category not found')
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error in CustomerCategoryDetailView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerCategoryWithProductsView(APIView):
    """Customer category with products view - matches ramyeonsite backend API"""
    
    def get(self, request, category_id):
        try:
            service = CustomerCategoryService()
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            subcategory_name = request.GET.get('subcategory_name')
            
            result = service.get_category_with_products(
                category_id=category_id,
                subcategory_name=subcategory_name,
                page=page,
                limit=limit
            )
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'category': result['category'],
                        'products': result['products'],
                        'pagination': result['pagination']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Category not found')
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error in CustomerCategoryWithProductsView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

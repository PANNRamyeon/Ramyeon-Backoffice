from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from ..services.product_service import ProductService
from ..services.category_service import CategoryService

import logging

logger = logging.getLogger(__name__)

class CustomerProductService:
    """Customer-facing product service (READ-ONLY) - uses existing PANN_POS services"""
    
    def __init__(self):
        self.product_service = ProductService()
        self.category_service = CategoryService()
        self.db = self.product_service.db
        self.product_collection = self.product_service.product_collection
        self.category_collection = self.product_service.category_collection
    
    def get_all_active_products(self, filters=None, page=1, limit=20, sort_by='product_name', sort_order='asc'):
        """Get all active products available for customers"""
        try:
            # Base query - only active, in-stock, non-deleted products
            # ✅ FIXED: Use total_stock instead of stock (total_stock has correct batch values)
            query = {
                'status': 'active',
                'isDeleted': {'$ne': True},
                'total_stock': {'$gt': 0}  # Use total_stock which has batch calculations
            }
            
            # Apply filters
            if filters:
                if filters.get('category_id'):
                    query['category_id'] = filters['category_id']
                if filters.get('subcategory_name'):
                    query['sub_categories'] = {'$elemMatch': {'name': filters['subcategory_name']}}
                if filters.get('search'):
                    search_term = filters['search']
                    query['$or'] = [
                        {'product_name': {'$regex': search_term, '$options': 'i'}},
                        {'SKU': {'$regex': search_term, '$options': 'i'}}
                    ]
                if filters.get('min_price'):
                    query['selling_price'] = {'$gte': float(filters['min_price'])}
                if filters.get('max_price'):
                    if 'selling_price' in query:
                        query['selling_price']['$lte'] = float(filters['max_price'])
                    else:
                        query['selling_price'] = {'$lte': float(filters['max_price'])}
            
            # Build sort
            sort_direction = 1 if sort_order == 'asc' else -1
            sort_field = sort_by if sort_by in ['product_name', 'selling_price', 'date_received'] else 'product_name'
            
            # Count total
            total = self.product_collection.count_documents(query)
            
            # Get products with pagination
            skip = (page - 1) * limit
            products_cursor = self.product_collection.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
            
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
                'products': products,
                'pagination': pagination
            }
            
        except Exception as e:
            logger.error(f"Error getting active products: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_product_by_id(self, product_id):
        """Get single product by ID"""
        try:
            # Try to find by string
            product = self.product_collection.find_one({
                '_id': product_id,
                'status': 'active',
                'isDeleted': {'$ne': True}
            })
            
            if not product:
                return {
                    'success': False,
                    'message': 'Product not found'
                }
            
            product_data = self._format_product_for_customer(product)
            
            # Add promotions if any (you'll need to implement this based on your promotions system)
            # product_data['promotions'] = self._get_product_promotions(product_id)
            
            return {
                'success': True,
                'product': product_data
            }
            
        except Exception as e:
            logger.error(f"Error getting product by ID: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_products_by_category(self, category_id, page=1, limit=20):
        """Get products by category"""
        try:
            # ✅ FIXED: Use total_stock instead of stock
            query = {
                'category_id': category_id,
                'status': 'active',
                'isDeleted': {'$ne': True},
                'total_stock': {'$gt': 0}
            }
            
            total = self.product_collection.count_documents(query)
            skip = (page - 1) * limit
            
            products_cursor = self.product_collection.find(query).sort('product_name', 1).skip(skip).limit(limit)
            
            products = []
            for product in products_cursor:
                product_data = self._format_product_for_customer(product)
                products.append(product_data)
            
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
                'products': products,
                'pagination': pagination
            }
            
        except Exception as e:
            logger.error(f"Error getting products by category: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def search_products(self, search_term, page=1, limit=20):
        """Search products by name or SKU"""
        try:
            if not search_term:
                return self.get_all_active_products(page=page, limit=limit)
            
            # ✅ FIXED: Use total_stock instead of stock
            query = {
                '$or': [
                    {'product_name': {'$regex': search_term, '$options': 'i'}},
                    {'SKU': {'$regex': search_term, '$options': 'i'}}
                ],
                'status': 'active',
                'isDeleted': {'$ne': True},
                'total_stock': {'$gt': 0}
            }
            
            total = self.product_collection.count_documents(query)
            skip = (page - 1) * limit
            
            products_cursor = self.product_collection.find(query).sort('product_name', 1).skip(skip).limit(limit)
            
            products = []
            for product in products_cursor:
                product_data = self._format_product_for_customer(product)
                products.append(product_data)
            
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
                'products': products,
                'pagination': pagination,
                'search_term': search_term
            }
            
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_featured_products(self, limit=10):
        """Get featured products - you may need to adjust this based on your schema"""
        try:
            # ✅ FIXED: Use total_stock instead of stock
            # Adjust this query based on how you mark featured products in your schema
            query = {
                'status': 'active',
                'isDeleted': {'$ne': True},
                'total_stock': {'$gt': 0}
            }
            
            products_cursor = self.product_collection.find(query).sort('date_received', -1).limit(limit)
            
            products = []
            for product in products_cursor:
                product_data = self._format_product_for_customer(product)
                products.append(product_data)
            
            return {
                'success': True,
                'products': products
            }
            
        except Exception as e:
            logger.error(f"Error getting featured products: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def _format_product_for_customer(self, product):
        """Format product data for customer consumption - remove sensitive fields"""
        try:
            # Get category name
            category_name = "Unknown"
            if product.get('category_id'):
                category = self.category_collection.find_one({'_id': product['category_id']})
                if category:
                    category_name = category.get('category_name', 'Unknown')
            
            # ✅ FIXED: Use total_stock as primary stock value (has correct batch calculations)
            stock_value = product.get('total_stock', product.get('stock', 0))
            
            formatted_product = {
                '_id': str(product['_id']),
                'product_name': product.get('product_name', ''),
                'category_id': product.get('category_id', ''),
                'category_name': category_name,
                'SKU': product.get('SKU', ''),
                'selling_price': float(product.get('selling_price', 0)),
                'stock': int(stock_value) if stock_value is not None else 0,
                'unit': product.get('unit', 'pcs'),
                'is_taxable': product.get('is_taxable', True),
                'status': product.get('status', 'active'),
                'date_received': product.get('date_received').isoformat() if product.get('date_received') else None,
                'low_stock_threshold': product.get('low_stock_threshold', 10)
            }
            
            # ✅ Add image fields for customer menu display
            image_fields = ['image', 'image_url', 'image_filename', 'image_size', 'image_type', 'image_uploaded_at']
            for field in image_fields:
                if field in product and product[field] is not None:
                    formatted_product[field] = product[field]
            
            # ✅ Add description if available
            if product.get('description'):
                formatted_product['description'] = product.get('description')
            
            return formatted_product
        except Exception as e:
            logger.error(f"Error formatting product: {e}")
            return {}

@method_decorator(csrf_exempt, name='dispatch')
class CustomerProductListView(APIView):
    """Customer product list view - matches ramyeonsite backend API"""
    
    def get(self, request):
        try:
            service = CustomerProductService()
            
            # Extract query parameters
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            sort_by = request.GET.get('sort_by', 'product_name')
            sort_order = request.GET.get('sort_order', 'asc')
            
            # Build filters
            filters = {}
            if request.GET.get('category_id'):
                filters['category_id'] = request.GET.get('category_id')
            if request.GET.get('subcategory_name'):
                filters['subcategory_name'] = request.GET.get('subcategory_name')
            if request.GET.get('search'):
                filters['search'] = request.GET.get('search')
            if request.GET.get('min_price'):
                filters['min_price'] = request.GET.get('min_price')
            if request.GET.get('max_price'):
                filters['max_price'] = request.GET.get('max_price')
            
            # Get products
            result = service.get_all_active_products(
                filters=filters if filters else None,
                page=page,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'products': result['products'],
                        'pagination': result['pagination']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Error retrieving products')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except ValueError as ve:
            logger.error(f"Invalid query parameters: {ve}")
            return Response({
                'success': False,
                'message': 'Invalid query parameters'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in CustomerProductListView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerProductDetailView(APIView):
    """Customer product detail view - matches ramyeonsite backend API"""
    
    def get(self, request, product_id):
        try:
            service = CustomerProductService()
            
            result = service.get_product_by_id(product_id)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'product': result['product']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Product not found')
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error in CustomerProductDetailView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerProductSearchView(APIView):
    """Customer product search view - matches ramyeonsite backend API"""
    
    def get(self, request):
        try:
            service = CustomerProductService()
            
            search_term = request.GET.get('q', '')
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            result = service.search_products(search_term, page=page, limit=limit)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'products': result['products'],
                        'pagination': result['pagination'],
                        'search_term': result.get('search_term', search_term)
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Search failed')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in CustomerProductSearchView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerProductByCategoryView(APIView):
    """Customer products by category view - matches ramyeonsite backend API"""
    
    def get(self, request, category_id):
        try:
            service = CustomerProductService()
            
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            result = service.get_products_by_category(category_id, page=page, limit=limit)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
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
            logger.error(f"Error in CustomerProductByCategoryView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CustomerFeaturedProductsView(APIView):
    """Customer featured products view - matches ramyeonsite backend API"""
    
    def get(self, request):
        try:
            service = CustomerProductService()
            
            limit = int(request.GET.get('limit', 10))
            
            result = service.get_featured_products(limit=limit)
            
            if result['success']:
                return Response({
                    'success': True,
                    'data': {
                        'products': result['products']
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Error retrieving featured products')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in CustomerFeaturedProductsView: {e}")
            return Response({
                'success': False,
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

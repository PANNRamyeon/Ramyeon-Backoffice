from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from ..services.category_service import CategoryService
import logging
import csv
import json
from io import StringIO
from datetime import datetime

logger = logging.getLogger(__name__)

# ================ DISPLAY AND EXPORT VIEWS ================

class CategoryDataView(APIView):
    """Get categories with product data"""
    
    def get(self, request):
        """Get all categories with product counts and data"""
        try:
            category_service = CategoryService()
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            
            # Use the refactored method that includes product counts
            categories = category_service.get_all_categories(include_deleted=include_deleted)
            
            return Response({
                "success": True,
                "message": "Categories retrieved successfully",
                "categories": categories,
                "count": len(categories),
                "include_deleted": include_deleted
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.error(f"Invalid parameter in CategoryDataView: {e}")
            return Response({
                "success": False,
                "error": f"Invalid parameter: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in CategoryDataView: {e}")
            return Response({
                "success": False,
                "error": "Internal server error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryExportView(APIView):
    """Export categories in CSV or JSON format"""
    
    def get(self, request):
        """Export categories with optional filters"""
        try:
            category_service = CategoryService()
            
            format_type = request.GET.get('format', 'csv').lower()
            include_deleted = request.GET.get('include_deleted', 'false').lower() == 'true'
            
            if format_type not in ['csv', 'json']:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid format. Use csv or json.'
                }, status=400)
            
            # Get categories with product counts
            categories = category_service.get_all_categories(include_deleted=include_deleted)
            
            if format_type == 'csv':
                # Generate CSV
                output = StringIO()
                fieldnames = [
                    'category_id', 'category_name', 'description', 'status', 
                    'subcategories_count', 'total_products', 'date_created', 'last_updated'
                ]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for category in categories:
                    row = {
                        'category_id': category.get('_id', ''),
                        'category_name': category.get('category_name', ''),
                        'description': category.get('description', ''),
                        'status': category.get('status', ''),
                        'subcategories_count': len(category.get('sub_categories', [])),
                        'total_products': category.get('product_count', 0),
                        'date_created': category.get('date_created', ''),
                        'last_updated': category.get('last_updated', '')
                    }
                    writer.writerow(row)
                
                response = HttpResponse(output.getvalue(), content_type='text/csv')
                filename = f"categories_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                return response
                
            else:  # JSON format
                # Prepare data for JSON export
                export_data = {
                    'export_timestamp': datetime.now().isoformat(),
                    'total_categories': len(categories),
                    'include_deleted': include_deleted,
                    'categories': []
                }
                
                for category in categories:
                    export_category = {
                        'category_id': category.get('_id'),
                        'category_name': category.get('category_name'),
                        'description': category.get('description'),
                        'status': category.get('status'),
                        'subcategories_count': len(category.get('sub_categories', [])),
                        'total_products': category.get('product_count', 0),
                        'subcategories': category.get('sub_categories', []),
                        'date_created': category.get('date_created'),
                        'last_updated': category.get('last_updated'),
                        'is_deleted': category.get('isDeleted', False)
                    }
                    export_data['categories'].append(export_category)
                
                response = HttpResponse(
                    json.dumps(export_data, indent=2, default=str),
                    content_type='application/json'
                )
                filename = f"categories_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                return response
            
        except ValueError as e:
            logger.error(f"Invalid parameter in CategoryExportView: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Invalid parameter: {str(e)}'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in CategoryExportView: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Export failed: {str(e)}'
            }, status=500)


class CategoryStatsView(APIView):
    """Get category statistics"""
    
    def get(self, request):
        """Get comprehensive category statistics"""
        try:
            category_service = CategoryService()
            
            # Use the refactored stats method
            stats = category_service.get_category_stats()
            
            return Response({
                'success': True,
                'message': 'Category statistics retrieved successfully',
                'stats': stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting category stats: {e}")
            return Response({
                "success": False,
                "error": "Failed to retrieve category statistics"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryWithProductsView(APIView):
    """Get specific category with all its products organized by subcategory"""
    
    def get(self, request, category_id):
        """Get category with products organized by subcategory"""
        try:
            category_service = CategoryService()
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            
            # Use the new method that organizes products by subcategory
            category_with_products = category_service.get_category_with_products(
                category_id, 
                include_deleted=include_deleted
            )
            
            if not category_with_products:
                return Response({
                    'success': False,
                    'error': 'Category not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'message': 'Category with products retrieved successfully',
                'data': category_with_products
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in CategoryWithProductsView: {e}")
            return Response({
                "success": False,
                "error": "Failed to retrieve category with products"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryProductCountsView(APIView):
    """Get product counts for all categories and subcategories"""
    
    def get(self, request):
        """Get detailed product counts for categories and subcategories"""
        try:
            category_service = CategoryService()
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            
            categories = category_service.get_all_categories(include_deleted=include_deleted)
            
            # Build detailed count structure
            count_data = {
                'total_categories': len(categories),
                'categories': []
            }
            
            for category in categories:
                category_data = {
                    'category_id': category.get('_id'),
                    'category_name': category.get('category_name'),
                    'total_products': category.get('product_count', 0),
                    'subcategories': []
                }
                
                for subcategory in category.get('sub_categories', []):
                    subcategory_data = {
                        'subcategory_name': subcategory.get('name'),
                        'product_count': subcategory.get('product_count', 0)
                    }
                    category_data['subcategories'].append(subcategory_data)
                
                count_data['categories'].append(category_data)
            
            return Response({
                'success': True,
                'message': 'Product counts retrieved successfully',
                'data': count_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in CategoryProductCountsView: {e}")
            return Response({
                "success": False,
                "error": "Failed to retrieve product counts"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
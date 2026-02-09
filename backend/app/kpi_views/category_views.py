from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.category_service import CategoryService
from ..decorators.authenticationDecorator import require_authentication, require_admin
import logging

logger = logging.getLogger(__name__)

class CategoryKPIView(APIView):
    
    def _serialize_objectids(self, obj):
        """Convert ObjectIds and datetime objects to strings recursively"""
        from datetime import datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_objectids(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_objectids(item) for item in obj]
        else:
            return obj

    @require_authentication
    def post(self, request):
        """Create a new category"""
        try:
            category_service = CategoryService()
            
            category_data = {
                'category_name': request.data.get('category_name'),
                'description': request.data.get('description', ''),
                'status': request.data.get('status', 'active'),
                'sub_categories': request.data.get('sub_categories', [])
            }
            
            # Add image fields if they exist
            image_fields = ['image_url', 'image_filename', 'image_size', 'image_type', 'image_uploaded_at']
            for field in image_fields:
                if field in request.data and request.data[field] is not None:
                    category_data[field] = request.data[field]
            
            result = category_service.create_category(category_data, request.current_user)
            
            return Response({
                "message": "Category created successfully",
                "category": result
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """Get all categories or search categories"""
        try:
            category_service = CategoryService()
            
            search_term = request.query_params.get('search')
            active_only = request.query_params.get('active_only', 'false').lower() == 'true'
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            limit = int(request.query_params.get('limit', 100))
            skip = int(request.query_params.get('skip', 0))
            
            if search_term:
                categories = category_service.search_categories(search_term, include_deleted=include_deleted, limit=limit)
            elif active_only:
                categories = category_service.get_active_categories(include_deleted=include_deleted)
            else:
                categories = category_service.get_all_categories(include_deleted=include_deleted, limit=limit, skip=skip)
            
            # Serialize any remaining non-JSON-serializable objects
            clean_categories = self._serialize_objectids(categories)
            
            return Response({
                "message": "Categories retrieved successfully",
                "categories": clean_categories,
                "count": len(clean_categories)
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryDetailView(APIView):
    
    def get(self, request, category_id):
        """Get a specific category by ID"""
        try:
            category_service = CategoryService()
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            category = category_service.get_category_by_id(category_id, include_deleted=include_deleted)
            
            if not category:
                return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({"message": "Category retrieved successfully", "category": category}, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error getting category {category_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @require_authentication
    def put(self, request, category_id):
        """Update a category"""
        try:
            category_service = CategoryService()
            
            logger.info(f"Updating category {category_id} by user: {request.current_user['username']}")
            
            allowed_fields = ['category_name', 'description', 'status', 'sub_categories', 
                            'image_url', 'image_filename', 'image_size', 'image_type', 'image_uploaded_at']
            
            update_data = {field: request.data[field] for field in allowed_fields if field in request.data}
            
            if not update_data:
                return Response({"error": "No valid fields to update"}, status=status.HTTP_400_BAD_REQUEST)
            
            result = category_service.update_category(category_id, update_data, request.current_user)
            
            if not result:
                return Response({"error": "Category not found or no changes made"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                "message": "Category updated successfully",
                "category": result,
                "updated_by": request.current_user['username']
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating category {category_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategorySoftDeleteView(APIView):
    
    @require_authentication
    def delete(self, request, category_id):
        """Soft delete a category"""
        try:
            category_service = CategoryService()
            result = category_service.soft_delete_category(category_id, request.current_user)
            
            if not result:
                return Response({"error": "Category not found or already deleted"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                "message": "Category soft deleted successfully",
                "category_id": category_id,
                "deleted_by": request.current_user['username']
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error soft deleting category {category_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryHardDeleteView(APIView):
    
    @require_admin
    def delete(self, request, category_id):
        """Hard delete a category (Admin only)"""
        try:
            category_service = CategoryService()
            result = category_service.hard_delete_category(category_id, request.current_user)
            
            if not result:
                return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                "message": "Category permanently deleted",
                "category_id": category_id,
                "deleted_by": request.current_user['username']
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error hard deleting category {category_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryRestoreView(APIView):
    
    @require_admin
    def post(self, request, category_id):
        """Restore a soft-deleted category (Admin only)"""
        try:
            category_service = CategoryService()
            result = category_service.restore_category(category_id, request.current_user)
            
            if not result:
                return Response({"error": "Category not found or not deleted"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                "message": "Category restored successfully",
                "category_id": category_id,
                "restored_by": request.current_user['username']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryDeletedListView(APIView):
    
    @require_admin
    def get(self, request):
        """Get list of soft-deleted categories (Admin only)"""
        try:
            category_service = CategoryService()
            deleted_categories = category_service.get_deleted_categories()
            
            return Response({
                "message": "Deleted categories retrieved successfully",
                "categories": deleted_categories,
                "count": len(deleted_categories)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryBulkOperationsView(APIView):
    
    @require_authentication
    def post(self, request):
        """Bulk operations on categories"""
        try:
            category_service = CategoryService()
            operation = request.data.get('operation')
            category_ids = request.data.get('category_ids', [])
            
            if not operation or not category_ids:
                return Response({"error": "Operation and category_ids are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if operation == 'soft_delete':
                result = category_service.bulk_soft_delete_categories(category_ids, request.current_user)
            elif operation == 'update_status':
                new_status = request.data.get('new_status')
                if not new_status:
                    return Response({"error": "new_status is required"}, status=status.HTTP_400_BAD_REQUEST)
                result = category_service.bulk_update_categories_status(category_ids, new_status, request.current_user)
            else:
                return Response({"error": f"Unknown operation: {operation}"}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                "message": f"Bulk {operation} completed",
                "result": result,
                "performed_by": request.current_user['username']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryDeleteInfoView(APIView):
    
    def get(self, request, category_id):
        """Get information about category before deletion"""
        try:
            category_service = CategoryService()
            delete_info = category_service.get_category_delete_info(category_id)
            
            if not delete_info:
                return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                "message": "Category delete information retrieved successfully",
                "delete_info": delete_info
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategorySubcategoryView(APIView):
    
    @require_authentication
    def post(self, request, category_id):
        """Add a subcategory to a category"""
        try:
            category_service = CategoryService()
            subcategory_data = request.data.get('subcategory')
            
            if not subcategory_data:
                return Response({"error": "Subcategory data is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            result = category_service.add_subcategory(category_id, subcategory_data, request.current_user)
            
            if not result:
                return Response({"error": "Failed to add subcategory"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                "message": "Subcategory added successfully",
                "added_by": request.current_user['username']
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @require_authentication
    def delete(self, request, category_id):
        """Remove a subcategory from a category"""
        try:
            category_service = CategoryService()
            subcategory_name = request.data.get('subcategory_name')
            
            if not subcategory_name:
                return Response({"error": "Subcategory name is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            result = category_service.remove_subcategory(category_id, subcategory_name, request.current_user)
            
            if not result:
                return Response({"error": "Failed to remove subcategory"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                "message": "Subcategory removed successfully",
                "removed_by": request.current_user['username']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request, category_id):
        """Get all subcategories for a category"""
        try:
            category_service = CategoryService()
            subcategories = category_service.get_subcategories(category_id)
            
            return Response({
                "message": "Subcategories retrieved successfully",
                "subcategories": subcategories,
                "count": len(subcategories)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UncategorizedCategoryView(APIView):
    
    def get(self, request):
        """Get information about the Uncategorized category"""
        try:
            category_service = CategoryService()
            uncategorized_category = category_service.ensure_uncategorized_category_exists()
            
            return Response({
                "message": "Uncategorized category information retrieved successfully",
                "uncategorized_category": uncategorized_category
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @require_admin
    def post(self, request):
        """Create/ensure the Uncategorized category exists (Admin only)"""
        try:
            category_service = CategoryService()
            category = category_service.ensure_uncategorized_category_exists()
            
            return Response({
                "message": "Uncategorized category ensured successfully",
                "category": category,
                "ensured_by": request.current_user['username']
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubcategoryProductsView(APIView):
    
    def get(self, request, category_id, subcategory_name):
        """Get all products in a subcategory"""
        try:
            category_service = CategoryService()
            
            # Use the refactored method to get products in subcategory
            products = category_service.get_products_in_subcategory(
                category_id, 
                subcategory_name, 
                include_deleted=False
            )
            
            return Response({
                "message": "Subcategory products retrieved successfully",
                "category_id": category_id,
                "subcategory_name": subcategory_name,
                "products": products,
                "count": len(products)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryProductManagementView(APIView):
    """New view for managing products within categories using proxy methods"""
    
    @require_authentication
    def put(self, request):
        """Move product to different category or subcategory"""
        try:
            category_service = CategoryService()
            
            product_id = request.data.get('product_id')
            new_category_id = request.data.get('new_category_id')
            new_subcategory_name = request.data.get('new_subcategory_name')
            
            if not product_id:
                return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not new_category_id:
                return Response({"error": "new_category_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Use the proxy method to move product
            result = category_service.move_product_to_category(
                product_id, 
                new_category_id, 
                new_subcategory_name, 
                request.current_user
            )
            
            if not result:
                return Response({"error": "Failed to move product"}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                "message": "Product moved successfully",
                "product": result,
                "moved_by": request.current_user['username']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error moving product: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @require_authentication  
    def post(self, request):
        """Bulk move products to category/subcategory"""
        try:
            category_service = CategoryService()
            
            product_ids = request.data.get('product_ids', [])
            new_category_id = request.data.get('new_category_id')
            new_subcategory_name = request.data.get('new_subcategory_name')
            
            if not product_ids:
                return Response({"error": "product_ids is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not new_category_id:
                return Response({"error": "new_category_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Use the bulk proxy method
            moved_count = category_service.bulk_move_products_to_category(
                product_ids, 
                new_category_id, 
                new_subcategory_name, 
                request.current_user
            )
            
            return Response({
                "message": f"Bulk move completed: {moved_count} products moved",
                "moved_count": moved_count,
                "total_requested": len(product_ids),
                "moved_by": request.current_user['username']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error bulk moving products: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
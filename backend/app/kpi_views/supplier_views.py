from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.supplier_service import SupplierService
from ..services.batch_service import BatchService
from ..decorators.authenticationDecorator import require_admin, require_authentication, require_permission, get_authenticated_user_from_jwt
import logging

logger = logging.getLogger(__name__)

# ================================================================
# SUPPLIER VIEW CLASSES
# ================================================================

class SupplierHealthCheckView(APIView):
    def get(self, request):
        return Response({
            "message": "Supplier Management API is running!",
            "status": "active",
            "version": "2.0.0",
            "features": ["supplier_management", "batch_integration"]
        }, status=status.HTTP_200_OK)

class SupplierListView(APIView):
    def __init__(self):
        self.supplier_service = SupplierService()
    
    @require_authentication
    def get(self, request):
        """Get suppliers with pagination and filters"""
        try:
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 50))
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            
            # Only admins can view deleted suppliers
            if include_deleted and request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required to view deleted suppliers"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Build filters
            filters = {}
            if request.query_params.get('search'):
                filters['search'] = request.query_params.get('search')
            if request.query_params.get('status'):
                filters['status'] = request.query_params.get('status')
            if request.query_params.get('type'):
                filters['type'] = request.query_params.get('type')
            
            result = self.supplier_service.get_suppliers(
                filters=filters if filters else None,
                include_deleted=include_deleted,
                page=page,
                per_page=per_page
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting suppliers: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @require_authentication
    def post(self, request):
        """Create new supplier - Requires authentication"""
        try:
            # Basic validation
            if not request.data.get('supplier_name'):
                return Response(
                    {"error": "Supplier name is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user ID from authenticated user
            user_id = request.current_user.get('_id', 'system')
            
            new_supplier = self.supplier_service.create_supplier(request.data, user_id=user_id)
            return Response(new_supplier, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating supplier: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class SupplierDetailView(APIView):
    def __init__(self):
        super().__init__()
        self.supplier_service = SupplierService()

    @require_authentication
    def get(self, request, supplier_id):
        """Get supplier by ID with batch statistics"""
        try:
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            include_batch_stats = request.query_params.get('include_batch_stats', 'true').lower() == 'true'
            
            # Only admins can view deleted suppliers
            if include_deleted:
                current_user = request.current_user 
                if not current_user or current_user.get('role', '').lower() != 'admin':
                    return Response(
                        {"error": "Admin permissions required to view deleted suppliers"}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            supplier = self.supplier_service.get_supplier_by_id(
                supplier_id, 
                include_deleted=include_deleted,
                include_batch_stats=include_batch_stats
            )
            
            if not supplier:
                return Response(
                    {"error": "Supplier not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(supplier, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting supplier {supplier_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @require_authentication
    def put(self, request, supplier_id):
        """Update supplier - Requires authentication"""
        try:
            # Get user ID from authenticated user
            user_id = request.current_user.get('_id', 'system')
            
            updated_supplier = self.supplier_service.update_supplier(
                supplier_id, 
                request.data,
                user_id=user_id
            )
            
            if not updated_supplier:
                return Response(
                    {"error": "Supplier not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(updated_supplier, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating supplier {supplier_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @require_authentication
    def delete(self, request, supplier_id):
        """Soft delete supplier - Requires authentication"""
        try:
            # Get user ID from authenticated user
            user_id = request.current_user.get('_id', 'system')
            
            deleted = self.supplier_service.delete_supplier(
                supplier_id, 
                hard_delete=False,
                user_id=user_id
            )
            
            if not deleted:
                return Response(
                    {"error": "Supplier not found or already deleted"},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"message": "Supplier deleted successfully"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error deleting supplier {supplier_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SupplierRestoreView(APIView):
    """View for restoring soft-deleted suppliers"""
    def __init__(self):
        super().__init__()
        self.supplier_service = SupplierService()

    @require_authentication
    def post(self, request, supplier_id):
        """Restore a soft-deleted supplier - Admin only"""
        try:
            current_user = request.current_user
            if not current_user or current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user_id = current_user.get('_id', 'system')
            
            restored = self.supplier_service.restore_supplier(
                supplier_id,
                user_id=user_id
            )
            
            if not restored:
                return Response(
                    {"error": "Supplier not found or not deleted"},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"message": "Supplier restored successfully"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error restoring supplier {supplier_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SupplierHardDeleteView(APIView):
    """View for permanently deleting suppliers (DANGEROUS)"""
    def __init__(self):
        super().__init__()
        self.supplier_service = SupplierService()

    @require_authentication
    def delete(self, request, supplier_id):
        """PERMANENTLY delete supplier - Requires admin authentication"""
        try:
            current_user = request.current_user
            if not current_user or current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            confirm = request.query_params.get('confirm', '').lower()
            if confirm != 'yes':
                return Response({
                    "error": "Permanent deletion requires confirmation", 
                    "message": "Add ?confirm=yes to permanently delete this supplier"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user_id = current_user.get('_id', 'system')
            
            deleted = self.supplier_service.delete_supplier(
                supplier_id, 
                hard_delete=True,
                user_id=user_id
            )
            
            if not deleted:
                return Response(
                    {"error": "Supplier not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                "message": "Supplier permanently deleted"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error permanently deleting supplier {supplier_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeletedSuppliersView(APIView):
    """View for getting all soft-deleted suppliers"""
    def __init__(self):
        super().__init__()
        self.supplier_service = SupplierService()

    @require_authentication
    def get(self, request):
        """Get soft-deleted suppliers - Admin only"""
        try:
            current_user = request.current_user
            if not current_user or current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 50))
            
            result = self.supplier_service.get_deleted_suppliers(page=page, per_page=per_page)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting deleted suppliers: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================================================================
# SUPPLIER BATCH INTEGRATION VIEWS
# ================================================================

class SupplierBatchesView(APIView):
    """View for getting all batches associated with a supplier"""
    def __init__(self):
        super().__init__()
        self.supplier_service = SupplierService()

    @require_authentication
    def get(self, request, supplier_id):
        """Get all batches for a supplier with optional filters"""
        try:
            # Build filters from query parameters
            filters = {}
            
            if request.query_params.get('status'):
                filters['status'] = request.query_params.get('status')
            
            if request.query_params.get('product_id'):
                filters['product_id'] = request.query_params.get('product_id')
            
            if request.query_params.get('expiring_soon', 'false').lower() == 'true':
                filters['expiring_soon'] = True
                filters['days_ahead'] = int(request.query_params.get('days_ahead', 30))
            
            batches = self.supplier_service.get_supplier_batches(
                supplier_id, 
                filters=filters if filters else None
            )
            
            return Response({
                'data': batches,
                'count': len(batches),
                'supplier_id': supplier_id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting supplier batches for {supplier_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SupplierStatisticsView(APIView):
    """View for getting comprehensive statistics for a supplier"""
    def __init__(self):
        super().__init__()
        self.supplier_service = SupplierService()

    @require_authentication
    def get(self, request, supplier_id):
        """Get comprehensive statistics for a supplier"""
        try:
            stats = self.supplier_service.get_supplier_statistics(supplier_id)
            
            return Response({
                'data': stats,
                'supplier_id': supplier_id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting supplier statistics for {supplier_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CreateBatchForSupplierView(APIView):
    """Convenience view for creating a batch directly through a supplier endpoint"""
    def __init__(self):
        super().__init__()
        self.batch_service = BatchService()
        self.supplier_service = SupplierService()

    @require_authentication
    def post(self, request, supplier_id):
        """Create a new batch for a supplier"""
        try:
            # Verify supplier exists
            supplier = self.supplier_service.get_supplier_by_id(
                supplier_id, 
                include_deleted=False,
                include_batch_stats=False
            )
            
            if not supplier:
                return Response(
                    {"error": f"Supplier with ID {supplier_id} not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate required batch fields
            if not request.data.get('product_id'):
                return Response(
                    {"error": "product_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not request.data.get('quantity_received'):
                return Response(
                    {"error": "quantity_received is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set supplier_id in the batch data
            batch_data = request.data.copy()
            batch_data['supplier_id'] = supplier_id
            
            # Create the batch
            new_batch = self.batch_service.create_batch(batch_data)
            
            return Response({
                "message": "Batch created successfully for supplier",
                "data": new_batch
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating batch for supplier {supplier_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================================================================
# LEGACY ENDPOINT REDIRECTS (Optional - for backwards compatibility)
# ================================================================

class LegacyPurchaseOrderRedirectView(APIView):
    """
    Optional: Redirect old purchase order endpoints to batch endpoints
    This helps with backwards compatibility during migration
    """
    @require_authentication
    def get(self, request, supplier_id):
        """Redirect to batches endpoint"""
        return Response({
            "message": "Purchase orders have been replaced with batch management",
            "redirect_to": f"/api/suppliers/{supplier_id}/batches/",
            "info": "Please use the batches endpoint for stock management"
        }, status=status.HTTP_301_MOVED_PERMANENTLY)
    
    @require_authentication
    def post(self, request, supplier_id):
        """Redirect to batch creation endpoint"""
        return Response({
            "message": "Purchase orders have been replaced with batch management",
            "redirect_to": f"/api/suppliers/{supplier_id}/batches/create/",
            "info": "Please use the batch creation endpoint for receiving new stock"
        }, status=status.HTTP_301_MOVED_PERMANENTLY)
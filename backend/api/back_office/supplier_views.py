from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.decorators.authenticationDecorator import require_authentication
from app.services.inventory.supplier_service import SupplierService
from app.utils.singleton import get_singleton
import logging

logger = logging.getLogger(__name__)


def _get_service():
    return get_singleton(SupplierService)


class SupplierHealthCheckView(APIView):
    def get(self, request):
        return Response({
            "message": "Supplier Management API is running!",
            "status": "active",
            "version": "4.0.0",
            "backend": "DynamoDB"
        }, status=status.HTTP_200_OK)


class SupplierListView(APIView):
    @require_authentication
    def get(self, request):
        try:
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            filters = {}
            if request.query_params.get('search'):
                filters['search'] = request.query_params['search']
            if request.query_params.get('type'):
                filters['type'] = request.query_params['type']

            suppliers = _get_service().get_suppliers(
                filters=filters or None,
                include_deleted=include_deleted
            )
            return Response({'suppliers': suppliers}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting suppliers: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @require_authentication
    def post(self, request):
        try:
            user_id = request.current_user.get('user_id', 'system')
            result = _get_service().create_supplier(request.data, user_id=user_id)
            return Response(result, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating supplier: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupplierDetailView(APIView):
    @require_authentication
    def get(self, request, supplier_id):
        try:
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            include_stats = request.query_params.get('include_stats', 'false').lower() == 'true'

            supplier = _get_service().get_supplier_by_id(
                supplier_id,
                include_deleted=include_deleted,
                include_batch_stats=include_stats
            )
            if not supplier:
                return Response({"error": "Supplier not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(supplier, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting supplier {supplier_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @require_authentication
    def put(self, request, supplier_id):
        try:
            user_id = request.current_user.get('user_id', 'system')
            result = _get_service().update_supplier(supplier_id, dict(request.data), user_id=user_id)
            return Response(result, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating supplier {supplier_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @require_authentication
    def delete(self, request, supplier_id):
        try:
            user_id = request.current_user.get('user_id', 'system')
            deleted = _get_service().delete_supplier(supplier_id, hard_delete=False, user_id=user_id)
            if not deleted:
                return Response({"error": "Supplier not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Supplier deleted successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error deleting supplier {supplier_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupplierRestoreView(APIView):
    @require_authentication
    def post(self, request, supplier_id):
        try:
            user_id = request.current_user.get('user_id', 'system')
            restored = _get_service().restore_supplier(supplier_id, user_id=user_id)
            if not restored:
                return Response({"error": "Supplier not found or not deleted"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Supplier restored successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error restoring supplier {supplier_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupplierHardDeleteView(APIView):
    @require_authentication
    def delete(self, request, supplier_id):
        try:
            current_user = request.current_user
            if current_user.get('role', '').lower() != 'admin':
                return Response({"error": "Admin permissions required"}, status=status.HTTP_403_FORBIDDEN)

            confirm = request.query_params.get('confirm', '').lower()
            if confirm != 'yes':
                return Response(
                    {"error": "Add ?confirm=yes to permanently delete this supplier"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user_id = current_user.get('user_id', 'system')
            deleted = _get_service().delete_supplier(supplier_id, hard_delete=True, user_id=user_id)
            if not deleted:
                return Response({"error": "Supplier not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Supplier permanently deleted"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error hard deleting supplier {supplier_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeletedSuppliersView(APIView):
    @require_authentication
    def get(self, request):
        try:
            if request.current_user.get('role', '').lower() != 'admin':
                return Response({"error": "Admin permissions required"}, status=status.HTTP_403_FORBIDDEN)

            suppliers = _get_service().get_deleted_suppliers()
            return Response({'suppliers': suppliers}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting deleted suppliers: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupplierStatisticsView(APIView):
    @require_authentication
    def get(self, request, supplier_id):
        try:
            supplier = _get_service().get_supplier_by_id(supplier_id, include_batch_stats=True)
            if not supplier:
                return Response({"error": "Supplier not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(supplier, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting stats for supplier {supplier_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupplierBatchesView(APIView):
    @require_authentication
    def get(self, request, supplier_id):
        try:
            filters = {}
            if request.query_params.get('status'):
                filters['status'] = request.query_params['status']
            if request.query_params.get('product_id'):
                filters['product_id'] = request.query_params['product_id']

            batches = _get_service().get_supplier_batches(supplier_id, filters=filters or None)
            return Response({
                'data': batches,
                'count': len(batches),
                'supplier_id': supplier_id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting batches for supplier {supplier_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateBatchForSupplierView(APIView):
    @require_authentication
    def post(self, request, supplier_id):
        try:
            from app.services.inventory.batch_service import BatchService

            if not _get_service().get_supplier_by_id(supplier_id):
                return Response({"error": f"Supplier {supplier_id} not found"}, status=status.HTTP_404_NOT_FOUND)

            if not request.data.get('product_id'):
                return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not request.data.get('quantity_received'):
                return Response({"error": "quantity_received is required"}, status=status.HTTP_400_BAD_REQUEST)

            batch_data = dict(request.data)
            batch_data['supplier_id'] = supplier_id

            new_batch = get_singleton(BatchService).create_batch(batch_data)
            return Response({"message": "Batch created successfully", "data": new_batch}, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating batch for supplier {supplier_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LegacyPurchaseOrderRedirectView(APIView):
    @require_authentication
    def get(self, request, supplier_id):
        return Response({
            "message": "Purchase orders have been replaced with batch management",
            "redirect_to": f"/api/suppliers/{supplier_id}/batches/"
        }, status=status.HTTP_301_MOVED_PERMANENTLY)

    @require_authentication
    def post(self, request, supplier_id):
        return Response({
            "message": "Purchase orders have been replaced with batch management",
            "redirect_to": f"/api/suppliers/{supplier_id}/batches/create/"
        }, status=status.HTTP_301_MOVED_PERMANENTLY)

"""
Back Office API views for Shipments.
Base URL: /api/v1/admin/shipments/
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from app.utils.singleton import get_singleton
from app.services.inventory.shipment_service import ShipmentService
from app.services.inventory.supplier_service import SupplierService

logger = logging.getLogger(__name__)


class ShipmentView(View):
    def __init__(self):
        super().__init__()
        self.shipment_service = get_singleton(ShipmentService)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


# ==================== LIST & CREATE ====================

@method_decorator(csrf_exempt, name='dispatch')
class ShipmentListView(ShipmentView):
    def get(self, request):
        """List shipments. Query params: supplier_id, limit, enrich_with_supplier_name=true"""
        try:
            supplier_id = request.GET.get('supplier_id')
            limit = int(request.GET.get('limit', 100))
            enrich = request.GET.get('enrich_with_supplier_name', 'false').lower() == 'true'
            shipments = self.shipment_service.get_all_shipments(
                supplier_id=supplier_id,
                limit=limit,
                enrich_with_supplier_name=enrich,
            )
            return JsonResponse({
                'success': True,
                'data': shipments,
                'count': len(shipments),
            })
        except Exception as e:
            logger.error(f"Error listing shipments: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def post(self, request):
        """Create a shipment. Body: supplier_id, batch_number; optional: shipment_date, invoice_number, status, freight_cost, notes, received_by."""
        try:
            data = json.loads(request.body) if request.body else {}
            required = ['supplier_id', 'batch_number']
            for field in required:
                if not data.get(field):
                    return JsonResponse({
                        'success': False,
                        'error': f'Missing required field: {field}',
                    }, status=400)
            if data.get('supplier_id'):
                supplier = get_singleton(SupplierService).get_supplier_by_id(data['supplier_id'])
                if not supplier:
                    return JsonResponse({
                        'success': False,
                        'error': f"Supplier with ID {data['supplier_id']} not found",
                    }, status=400)
            shipment = self.shipment_service.create_shipment(data)
            return JsonResponse({
                'success': True,
                'message': 'Shipment created successfully',
                'data': shipment,
            })
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error creating shipment: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== DETAIL & UPDATE ====================

@method_decorator(csrf_exempt, name='dispatch')
class ShipmentDetailView(ShipmentView):
    def get(self, request, shipment_id):
        """Get shipment by ID. Query: include_batches=true, enrich_with_product=true"""
        try:
            include_batches = request.GET.get('include_batches', 'false').lower() == 'true'
            enrich_with_product = request.GET.get('enrich_with_product', 'false').lower() == 'true'
            if include_batches:
                data = self.shipment_service.get_shipment_with_batches(
                    shipment_id,
                    enrich_with_product=enrich_with_product,
                )
            else:
                data = self.shipment_service.get_shipment_by_id(shipment_id)
            if not data:
                return JsonResponse({
                    'success': False,
                    'error': 'Shipment not found',
                }, status=404)
            return JsonResponse({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Error getting shipment: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def put(self, request, shipment_id):
        """Update shipment. Allowed fields: status, invoice_number, freight_cost, notes, received_by, total_products."""
        try:
            data = json.loads(request.body) if request.body else {}
            updated = self.shipment_service.update_shipment(shipment_id, data)
            if not updated:
                return JsonResponse({
                    'success': False,
                    'error': 'Shipment not found',
                }, status=404)
            return JsonResponse({
                'success': True,
                'message': 'Shipment updated successfully',
                'data': updated,
            })
        except Exception as e:
            logger.error(f"Error updating shipment: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== SHIPMENT WITH BATCHES ====================

@method_decorator(csrf_exempt, name='dispatch')
class ShipmentWithBatchesView(ShipmentView):
    def get(self, request, shipment_id):
        """Get shipment with its batches. Query: enrich_with_product=true"""
        try:
            enrich = request.GET.get('enrich_with_product', 'false').lower() == 'true'
            data = self.shipment_service.get_shipment_with_batches(shipment_id, enrich_with_product=enrich)
            if not data:
                return JsonResponse({
                    'success': False,
                    'error': 'Shipment not found',
                }, status=404)
            return JsonResponse({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Error getting shipment with batches: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== BY SUPPLIER ====================

@method_decorator(csrf_exempt, name='dispatch')
class ShipmentsBySupplierView(ShipmentView):
    def get(self, request, supplier_id):
        """List shipments for a supplier. Query: limit"""
        try:
            limit = int(request.GET.get('limit', 100))
            shipments = self.shipment_service.get_shipments_by_supplier(supplier_id, limit=limit)
            return JsonResponse({
                'success': True,
                'data': shipments,
                'count': len(shipments),
                'supplier_id': supplier_id,
            })
        except Exception as e:
            logger.error(f"Error listing shipments for supplier: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

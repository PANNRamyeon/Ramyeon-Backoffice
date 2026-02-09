from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from datetime import datetime, timedelta

from ..services.batch_service import BatchService
from ..services.product_service import ProductService
from ..services.supplier_service import SupplierService

logger = logging.getLogger(__name__)

class BatchView(View):
    def __init__(self):
        super().__init__()
        self.batch_service = BatchService()
        self.product_service = ProductService()
        self.supplier_service = SupplierService()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

# ================================================================
# BATCH CRUD OPERATIONS
# ================================================================

@method_decorator(csrf_exempt, name='dispatch')
class CreateBatchView(BatchView):
    def post(self, request):
        """Create a new batch when receiving stock"""
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['product_id', 'quantity_received']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Validate supplier_id if provided
            if data.get('supplier_id'):
                supplier = self.supplier_service.get_supplier_by_id(
                    data['supplier_id'], 
                    include_deleted=False,
                    include_batch_stats=False
                )
                if not supplier:
                    return JsonResponse({
                        'success': False,
                        'error': f"Supplier with ID {data['supplier_id']} not found"
                    }, status=400)
            
            # Create batch
            batch = self.batch_service.create_batch(data)
            
            return JsonResponse({
                'success': True,
                'message': 'Batch created successfully',
                'data': batch
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error creating batch: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch') 
class BatchListView(BatchView):
    def get(self, request):
        """Get all batches with optional filters"""
        try:
            # Get query parameters for filtering
            filters = {}
            
            product_id = request.GET.get('product_id')
            if product_id:
                filters['product_id'] = product_id
            
            status_filter = request.GET.get('status')
            if status_filter:
                filters['status'] = status_filter
                
            supplier_id = request.GET.get('supplier_id')
            if supplier_id:
                filters['supplier_id'] = supplier_id
                
            # Check for expiring soon filter
            expiring_soon = request.GET.get('expiring_soon')
            if expiring_soon == 'true':
                days_ahead = int(request.GET.get('days_ahead', 30))
                filters['expiring_soon'] = True
                filters['days_ahead'] = days_ahead
            
            batches = self.batch_service.get_all_batches(filters)
            
            return JsonResponse({
                'success': True,
                'data': batches,
                'count': len(batches)
            })
            
        except Exception as e:
            logger.error(f"Error getting batches: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class BatchDetailView(BatchView):
    def get(self, request, batch_id):
        """Get batch details by ID with supplier information"""
        try:
            batch = self.batch_service.get_batch_by_id(batch_id)
            
            if not batch:
                return JsonResponse({
                    'success': False,
                    'error': 'Batch not found'
                }, status=404)
            
            # Optionally include supplier information
            include_supplier = request.GET.get('include_supplier', 'false').lower() == 'true'
            
            if include_supplier and batch.get('supplier_id'):
                supplier = self.supplier_service.get_supplier_by_id(
                    batch['supplier_id'],
                    include_deleted=False,
                    include_batch_stats=False
                )
                if supplier:
                    batch['supplier_info'] = supplier
            
            return JsonResponse({
                'success': True,
                'data': batch
            })
            
        except Exception as e:
            logger.error(f"Error getting batch details: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def put(self, request, batch_id):
        """Update batch details"""
        try:
            data = json.loads(request.body)
            
            # Update the batch
            updated_batch = self.batch_service.update_batch(batch_id, data)
            
            if not updated_batch:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to update batch or batch not found'
                }, status=404)
            
            return JsonResponse({
                'success': True,
                'message': 'Batch updated successfully',
                'data': updated_batch
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating batch: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class UpdateBatchQuantityView(BatchView):
    def put(self, request, batch_id):
        """Update batch quantity when stock is used/sold"""
        try:
            data = json.loads(request.body)
            
            quantity_used = data.get('quantity_used')
            adjustment_type = data.get('adjustment_type', 'correction')
            adjusted_by = data.get('adjusted_by')
            notes = data.get('notes')
            
            if quantity_used is None:
                return JsonResponse({
                    'success': False,
                    'error': 'quantity_used is required'
                }, status=400)
            
            if quantity_used <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'quantity_used must be greater than 0'
                }, status=400)
            
            updated_batch = self.batch_service.update_batch_quantity(
                batch_id,
                quantity_used,
                adjustment_type=adjustment_type,
                adjusted_by=adjusted_by,
                notes=notes
            )
            
            if not updated_batch:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to update batch or batch not found'
                }, status=404)
            
            return JsonResponse({
                'success': True,
                'message': 'Batch quantity updated successfully',
                'data': updated_batch
            })
            
        except Exception as e:
            logger.error(f"Error updating batch quantity: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

# ================================================================
# BATCH QUERIES AND REPORTS
# ================================================================

@method_decorator(csrf_exempt, name='dispatch')
class ProductBatchesView(BatchView):
    def get(self, request, product_id):
        """Get all batches for a specific product with supplier information"""
        try:
            status_filter = request.GET.get('status')  # Optional status filter
            include_supplier = request.GET.get('include_supplier', 'false').lower() == 'true'
            
            batches = self.batch_service.get_batches_by_product(product_id, status_filter)
            
            # Optionally include supplier information for each batch
            if include_supplier:
                for batch in batches:
                    if batch.get('supplier_id'):
                        supplier = self.supplier_service.get_supplier_by_id(
                            batch['supplier_id'],
                            include_deleted=False,
                            include_batch_stats=False
                        )
                        if supplier:
                            batch['supplier_info'] = {
                                '_id': supplier['_id'],
                                'supplier_name': supplier['supplier_name'],
                                'contact_person': supplier.get('contact_person'),
                                'phone_number': supplier.get('phone_number')
                            }
            
            return JsonResponse({
                'success': True,
                'data': batches,
                'count': len(batches),
                'product_id': product_id
            })
            
        except Exception as e:
            logger.error(f"Error getting product batches: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class SupplierBatchesView(BatchView):
    def get(self, request, supplier_id):
        """Get all batches for a specific supplier"""
        try:
            # Verify supplier exists
            supplier = self.supplier_service.get_supplier_by_id(
                supplier_id,
                include_deleted=False,
                include_batch_stats=False
            )
            
            if not supplier:
                return JsonResponse({
                    'success': False,
                    'error': f'Supplier with ID {supplier_id} not found'
                }, status=404)
            
            # Build filters
            filters = {}
            
            status_filter = request.GET.get('status')
            if status_filter:
                filters['status'] = status_filter
            
            product_id = request.GET.get('product_id')
            if product_id:
                filters['product_id'] = product_id
            
            if request.GET.get('expiring_soon', 'false').lower() == 'true':
                filters['expiring_soon'] = True
                filters['days_ahead'] = int(request.GET.get('days_ahead', 30))
            
            # Add supplier_id to filters
            filters['supplier_id'] = supplier_id
            
            batches = self.batch_service.get_all_batches(filters)
            
            # Enrich batches with product information
            enriched_batches = []
            for batch in batches:
                batch_data = batch.copy() if isinstance(batch, dict) else dict(batch)
                
                # Get product name if not already present
                if 'product_name' not in batch_data:
                    try:
                        product = self.batch_service.product_collection.find_one(
                            {'_id': batch_data.get('product_id')}
                        )
                        if product:
                            batch_data['product_name'] = product.get('product_name', 'Unknown Product')
                        else:
                            batch_data['product_name'] = batch_data.get('product_id', 'Unknown Product')
                    except Exception:
                        batch_data['product_name'] = batch_data.get('product_id', 'Unknown Product')
                
                enriched_batches.append(batch_data)
            
            return JsonResponse({
                'success': True,
                'data': enriched_batches,
                'count': len(enriched_batches),
                'supplier_id': supplier_id,
                'supplier_name': supplier['supplier_name']
            })
            
        except Exception as e:
            logger.error(f"Error getting supplier batches: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ExpiringBatchesView(BatchView):
    def get(self, request):
        """Get batches expiring within specified days"""
        try:
            days_ahead = int(request.GET.get('days_ahead', 30))
            
            expiring_batches = self.batch_service.get_expiring_batches(days_ahead)
            
            # Group by supplier if requested
            group_by_supplier = request.GET.get('group_by_supplier', 'false').lower() == 'true'
            
            if group_by_supplier:
                supplier_groups = {}
                for batch in expiring_batches:
                    supplier_id = batch.get('supplier_id', 'unknown')
                    if supplier_id not in supplier_groups:
                        supplier_groups[supplier_id] = []
                    supplier_groups[supplier_id].append(batch)
                
                return JsonResponse({
                    'success': True,
                    'data': supplier_groups,
                    'total_batches': len(expiring_batches),
                    'days_ahead': days_ahead
                })
            
            return JsonResponse({
                'success': True,
                'data': expiring_batches,
                'count': len(expiring_batches),
                'days_ahead': days_ahead
            })
            
        except Exception as e:
            logger.error(f"Error getting expiring batches: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ProductsWithExpirySummaryView(BatchView):
    def get(self, request):
        """Get products with their expiry summary information"""
        try:
            products = self.batch_service.get_products_with_expiry_summary()
            
            return JsonResponse({
                'success': True,
                'data': products,
                'count': len(products)
            })
            
        except Exception as e:
            logger.error(f"Error getting products with expiry summary: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

# ================================================================
# BATCH OPERATIONS FOR SALES
# ================================================================

@method_decorator(csrf_exempt, name='dispatch')
class ProcessSaleFIFOView(BatchView):
    def post(self, request):
        """Process a sale using FIFO logic"""
        try:
            data = json.loads(request.body)
            
            product_id = data.get('product_id')
            quantity_sold = data.get('quantity_sold')
            
            if not product_id or quantity_sold is None:
                return JsonResponse({
                    'success': False,
                    'error': 'product_id and quantity_sold are required'
                }, status=400)
            
            if quantity_sold <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'quantity_sold must be greater than 0'
                }, status=400)
            
            batches_used = self.batch_service.process_sale_fifo(product_id, quantity_sold)
            
            return JsonResponse({
                'success': True,
                'message': 'Sale processed successfully using FIFO',
                'data': {
                    'product_id': product_id,
                    'quantity_sold': quantity_sold,
                    'batches_used': batches_used
                }
            })
            
        except Exception as e:
            logger.error(f"Error processing FIFO sale: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ProcessBatchAdjustmentView(BatchView):
    def post(self, request):
        """Process a batch adjustment using FIFO logic"""
        try:
            data = json.loads(request.body)
            
            product_id = data.get('product_id')
            quantity_used = data.get('quantity_used')
            adjustment_type = data.get('adjustment_type', 'correction')
            adjusted_by = data.get('adjusted_by')
            notes = data.get('notes')
            
            # Validate required fields
            if not product_id or quantity_used is None:
                return JsonResponse({
                    'success': False,
                    'error': 'product_id and quantity_used are required'
                }, status=400)
            
            if quantity_used <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'quantity_used must be greater than 0'
                }, status=400)
            
            # Process the adjustment
            result = self.batch_service.process_batch_adjustment(
                product_id, 
                quantity_used,
                adjustment_type,
                adjusted_by,
                notes
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully adjusted {quantity_used} units using FIFO',
                'data': result
            })
            
        except Exception as e:
            logger.error(f"Error processing batch adjustment: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

# ================================================================
# BATCH MAINTENANCE AND ALERTS
# ================================================================

@method_decorator(csrf_exempt, name='dispatch')
class CheckExpiryAlertsView(BatchView):
    def post(self, request):
        """Check for expiring batches and send alerts"""
        try:
            data = json.loads(request.body) if request.body else {}
            days_ahead = data.get('days_ahead', 7)
            
            alert_count = self.batch_service.check_and_alert_expiring_batches(days_ahead)
            
            return JsonResponse({
                'success': True,
                'message': f'Expiry check completed',
                'data': {
                    'alerts_sent': alert_count,
                    'days_ahead': days_ahead
                }
            })
            
        except Exception as e:
            logger.error(f"Error checking expiry alerts: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class MarkExpiredBatchesView(BatchView):
    def post(self, request):
        """Mark expired batches as expired"""
        try:
            expired_count = self.batch_service.mark_expired_batches()
            
            return JsonResponse({
                'success': True,
                'message': 'Expired batches marked successfully',
                'data': {
                    'batches_marked_expired': expired_count
                }
            })
            
        except Exception as e:
            logger.error(f"Error marking expired batches: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

# ================================================================
# INTEGRATION WITH PRODUCTS
# ================================================================

@method_decorator(csrf_exempt, name='dispatch')
class ProductWithBatchSummaryView(BatchView):
    def get(self, request, product_id):
        """Get product with its batch summary"""
        try:
            product_with_batches = self.product_service.get_product_with_batch_summary(product_id)
            
            if not product_with_batches:
                return JsonResponse({
                    'success': False,
                    'error': 'Product not found'
                }, status=404)
            
            return JsonResponse({
                'success': True,
                'data': product_with_batches
            })
            
        except Exception as e:
            logger.error(f"Error getting product with batch summary: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RestockWithBatchView(BatchView):
    def post(self, request, product_id):
        """Restock product and create batch"""
        try:
            data = json.loads(request.body)
            
            quantity_received = data.get('quantity_received')
            if quantity_received is None or quantity_received <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'quantity_received is required and must be greater than 0'
                }, status=400)
            
            supplier_info = data.get('supplier_info')
            batch_info = data.get('batch_info')
            
            result = self.product_service.restock_product(
                product_id,
                quantity_received,
                supplier_info,
                batch_info
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Product restocked and batch created successfully',
                'data': result
            })
            
        except Exception as e:
            logger.error(f"Error restocking with batch: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

# ================================================================
# BATCH STATISTICS AND ANALYTICS
# ================================================================

@method_decorator(csrf_exempt, name='dispatch')
class BatchStatisticsView(BatchView):
    def get(self, request):
        """Get batch statistics and analytics with optional supplier breakdown"""
        try:
            # Get all batches for analysis
            all_batches = self.batch_service.get_all_batches()
            
            # Calculate statistics
            total_batches = len(all_batches)
            active_batches = len([b for b in all_batches if b.get('status') == 'active'])
            depleted_batches = len([b for b in all_batches if b.get('status') == 'depleted'])
            expired_batches = len([b for b in all_batches if b.get('status') == 'expired'])
            
            # Get expiring soon (within 7 days)
            expiring_soon = self.batch_service.get_expiring_batches(7)
            
            # Calculate total stock from active batches (excluding expired)
            now = datetime.now()
            total_stock = sum(
                b.get('quantity_remaining', 0) 
                for b in all_batches 
                if b.get('status') == 'active' and (
                    not b.get('expiry_date') or 
                    b.get('expiry_date') >= now
                )
            )
            
            statistics = {
                'total_batches': total_batches,
                'active_batches': active_batches,
                'depleted_batches': depleted_batches,
                'expired_batches': expired_batches,
                'expiring_within_7_days': len(expiring_soon),
                'total_active_stock': total_stock,
                'batch_status_breakdown': {
                    'active': active_batches,
                    'depleted': depleted_batches,
                    'expired': expired_batches
                }
            }
            
            # Optional: Group by supplier
            group_by_supplier = request.GET.get('group_by_supplier', 'false').lower() == 'true'
            
            if group_by_supplier:
                supplier_stats = {}
                for batch in all_batches:
                    supplier_id = batch.get('supplier_id', 'unknown')
                    if supplier_id not in supplier_stats:
                        supplier_stats[supplier_id] = {
                            'total_batches': 0,
                            'active_batches': 0,
                            'depleted_batches': 0,
                            'expired_batches': 0,
                            'total_stock': 0
                        }
                    
                    supplier_stats[supplier_id]['total_batches'] += 1
                    if batch.get('status') == 'active':
                        # Only count stock if not expired by date
                        is_expired_by_date = (
                            batch.get('expiry_date') and 
                            batch.get('expiry_date') < now
                        )
                        if not is_expired_by_date:
                            supplier_stats[supplier_id]['active_batches'] += 1
                            supplier_stats[supplier_id]['total_stock'] += batch.get('quantity_remaining', 0)
                    elif batch.get('status') == 'depleted':
                        supplier_stats[supplier_id]['depleted_batches'] += 1
                    elif batch.get('status') == 'expired':
                        supplier_stats[supplier_id]['expired_batches'] += 1
                
                statistics['by_supplier'] = supplier_stats
            
            return JsonResponse({
                'success': True,
                'data': statistics
            })
            
        except Exception as e:
            logger.error(f"Error getting batch statistics: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ActivateBatchView(BatchView):
    def post(self, request):
        """Activate a pending batch (change status from pending to active)"""
        try:
            data = json.loads(request.body)
            
            batch_number = data.get('batch_number')
            product_id = data.get('product_id')
            supplier_id = data.get('supplier_id')
            
            if not all([batch_number, product_id, supplier_id]):
                return JsonResponse({
                    'success': False,
                    'error': 'batch_number, product_id, and supplier_id are required'
                }, status=400)
            
            # Optional fields
            quantity_received = data.get('quantity_received')
            cost_price = data.get('cost_price')
            expiry_date = data.get('expiry_date')
            date_received = data.get('date_received')
            notes = data.get('notes')
            
            activated_batch = self.batch_service.activate_batch(
                batch_number=batch_number,
                product_id=product_id,
                supplier_id=supplier_id,
                quantity_received=quantity_received,
                cost_price=cost_price,
                expiry_date=expiry_date,
                date_received=date_received,
                notes=notes
            )
            
            if not activated_batch:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to activate batch'
                }, status=500)
            
            return JsonResponse({
                'success': True,
                'message': 'Batch activated successfully',
                'data': activated_batch
            })
            
        except Exception as e:
            logger.error(f"Error activating batch: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
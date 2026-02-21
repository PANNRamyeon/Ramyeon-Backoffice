from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from app.services.sales.saleslog_service import SalesLogService

from datetime import datetime
import logging
from django.utils.dateparse import parse_date

logger = logging.getLogger(__name__)

class SalesLogView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sales_service = SalesLogService()

    def post(self, request, invoice_id=None):
        """Create a new invoice/sales log"""
        # Note: invoice_id should be None for POST requests to /invoices/
        if invoice_id is not None:
            return Response(
                {'error': 'POST method not allowed for specific invoice'}, 
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
            
        try:
            invoice_data = request.data.copy()
            
            # Validate required fields
            required_fields = ['total_amount']
            for field in required_fields:
                if field not in invoice_data:
                    return Response(
                        {'error': f'Missing required field: {field}'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Convert string IDs to ObjectId if provided
            if 'customer_id' in invoice_data and isinstance(invoice_data['customer_id'], str):
                try:
                    invoice_data['customer_id'] = invoice_data['customer_id']
                except Exception:
                    return Response(
                        {'error': 'Invalid customer_id format'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if 'user_id' in invoice_data and isinstance(invoice_data['user_id'], str):
                try:
                    invoice_data['user_id'] = invoice_data['user_id']
                except Exception:
                    return Response(
                        {'error': 'Invalid user_id format'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Set transaction_date if not provided
            if 'transaction_date' not in invoice_data:
                invoice_data['transaction_date'] = datetime.utcnow()
            
            # Create the invoice
            created_invoice = self.sales_service.create_invoice(invoice_data)
            
            logger.info(f"Invoice created successfully with ID: {created_invoice['_id']}")
            
            return Response(
                {
                    'message': 'Invoice created successfully',
                    'invoice': created_invoice
                }, 
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            return Response(
                {'error': f'Failed to create invoice: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, invoice_id=None):
        """Get invoice(s) - single invoice by ID or all invoices"""
        try:
            if invoice_id:
                # Get single invoice
                invoice = self.sales_service.get_invoice_by_id(invoice_id)
                
                if invoice:
                    return Response(
                        {'invoice': invoice}, 
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {'error': 'Invoice not found'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Get all invoices with pagination
                page = int(request.GET.get('page', 1))
                limit = int(request.GET.get('limit', 20))
                skip = (page - 1) * limit
                
                # Optional filters
                customer_id = request.GET.get('customer_id')
                sales_type = request.GET.get('sales_type')
                status_filter = request.GET.get('status')
                
                # Get invoices
                invoices = self.sales_service.get_all_invoices(limit=limit, skip=skip)
                
                # Apply filters if provided (basic filtering)
                if customer_id:
                    invoices = [inv for inv in invoices if inv.get('customer_id') == customer_id]
                
                if sales_type:
                    invoices = [inv for inv in invoices if inv.get('sales_type') == sales_type]
                
                if status_filter:
                    invoices = [inv for inv in invoices if inv.get('status') == status_filter]
                
                return Response(
                    {
                        'invoices': invoices,
                        'page': page,
                        'limit': limit,
                        'total': len(invoices)
                    }, 
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            logger.error(f"Error retrieving invoice(s): {str(e)}")
            return Response(
                {'error': f'Failed to retrieve invoice(s): {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, invoice_id=None):
        """Update an existing invoice"""
        try:
            if not invoice_id:
                return Response(
                    {'error': 'Invoice ID is required for PUT method'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            update_data = request.data.copy()
            
            # Remove fields that shouldn't be updated
            protected_fields = ['_id', 'transaction_date']
            for field in protected_fields:
                update_data.pop(field, None)
            
            # Convert ObjectId fields if needed
            if 'customer_id' in update_data and isinstance(update_data['customer_id'], str):
                try:
                    update_data['customer_id'] = update_data['customer_id']
                except Exception:
                    return Response(
                        {'error': 'Invalid customer_id format'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if 'user_id' in update_data and isinstance(update_data['user_id'], str):
                try:
                    update_data['user_id'] = update_data['user_id']
                except Exception:
                    return Response(
                        {'error': 'Invalid user_id format'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Update the invoice
            updated_invoice = self.sales_service.update_invoice(invoice_id, update_data)
            
            if updated_invoice:
                logger.info(f"Invoice updated successfully: {invoice_id}")
                return Response(
                    {
                        'message': 'Invoice updated successfully',
                        'invoice': updated_invoice
                    }, 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'Invoice not found or no changes made'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error updating invoice {invoice_id}: {str(e)}")
            return Response(
                {'error': f'Failed to update invoice: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, invoice_id=None):
        """Delete an invoice"""
        try:
            if not invoice_id:
                return Response(
                    {'error': 'Invoice ID is required for DELETE method'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            deleted = self.sales_service.delete_invoice(invoice_id)
            
            if deleted:
                logger.info(f"Invoice deleted successfully: {invoice_id}")
                return Response(
                    {'message': 'Invoice deleted successfully'}, 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'Invoice not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error deleting invoice {invoice_id}: {str(e)}")
            return Response(
                {'error': f'Failed to delete invoice: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class SalesLogStatsView(APIView):
    """View for sales statistics and reports"""
    
    def __init__(self):
        super().__init__()
        self.sales_service = SalesLogService()
    
    def get(self, request):
        """Get sales statistics"""
        try:
            # Get query parameters
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            sales_type = request.GET.get('sales_type')
            
            # Basic stats (you'll need to implement these methods in your service)
            stats = {
                'total_sales': 0,
                'total_transactions': 0,
                'average_transaction': 0,
                'sales_by_type': {},
                'sales_by_payment_method': {}
            }
            
            # Get all invoices for stats calculation
            all_invoices = self.sales_service.get_all_invoices(limit=1000)  # Adjust as needed
            
            if all_invoices:
                # Calculate basic statistics
                stats['total_transactions'] = len(all_invoices)
                stats['total_sales'] = sum(float(inv.get('total_amount', 0)) for inv in all_invoices)
                stats['average_transaction'] = stats['total_sales'] / stats['total_transactions'] if stats['total_transactions'] > 0 else 0
                
                # Group by sales type
                sales_by_type = {}
                payment_methods = {}
                
                for invoice in all_invoices:
                    # Sales by type
                    inv_sales_type = invoice.get('sales_type', 'unknown')
                    if inv_sales_type not in sales_by_type:
                        sales_by_type[inv_sales_type] = {'count': 0, 'total': 0}
                    sales_by_type[inv_sales_type]['count'] += 1
                    sales_by_type[inv_sales_type]['total'] += float(invoice.get('total_amount', 0))
                    
                    # Payment methods
                    payment_method = invoice.get('payment_method', 'unknown')
                    if payment_method not in payment_methods:
                        payment_methods[payment_method] = {'count': 0, 'total': 0}
                    payment_methods[payment_method]['count'] += 1
                    payment_methods[payment_method]['total'] += float(invoice.get('total_amount', 0))
                
                stats['sales_by_type'] = sales_by_type
                stats['sales_by_payment_method'] = payment_methods
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting sales stats: {str(e)}")
            return Response(
                {'error': f'Failed to get sales statistics: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

# class SalesItemHistoryView(APIView):
#     """
#     API View to get sales item history with pagination
#     """
    
#     def get(self, request):
#         try:
#             # Get pagination parameters from query params
#             page = int(request.GET.get('page', 1))
#             page_size = int(request.GET.get('page_size', 10))
            
#             # Validate pagination parameters
#             if page < 1:
#                 page = 1
#             if page_size < 1 or page_size > 100:  # Limit max page size
#                 page_size = 10
            
#             # Create service instance
#             Report= SalesItemHistory()
            
#             # Fetch item history data
#             result = Report.fetch_item_history(page=page, page_size=page_size)
            
#             return Response({
#                 'success': True,
#                 'message': 'Item history retrieved successfully',
#                 'data': result
#             }, status=status.HTTP_200_OK)
            
#         except ValueError as e:
#             return Response({
#                 'success': False,
#                 'message': 'Invalid page or page_size parameter'
#             }, status=status.HTTP_400_BAD_REQUEST)
            
#         except Exception as e:
#             return Response({
#                 'success': False,
#                 'message': f'Error retrieving item history: {str(e)}'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class SalesTopItemView(APIView):
#     def get(self, request):
#         try:
#             # Get limit parameter from query params
#             limit = int(request.GET.get('limit', 5))
            
#             # Initialize your Report class (assuming SalesTopItem is a class)
#             report = SalesTopItem()  # Create an instance
            
#             # Call the method (note the parentheses to actually call it)
#             result = report.fetch_top_item(limit=limit)
            
#             # Return proper Response format
#             return Response({
#                 'success': True,
#                 'data': result.get('items', []),
#                 'total_invoices': result.get('total_invoices', 0),
#                 'showing_top': result.get('showing_top', 0)
#             }, status=status.HTTP_200_OK)
            
#         except Exception as e:
#             return Response({
#                 'success': False,
#                 'message': f'Error retrieving top items: {str(e)}',
#                 'data': []
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# class SalesTopItemChartView(APIView):
#     def get(self, request):
#         try:
#             # Get parameters from query params
#             limit = request.GET.get('limit', None)
#             if limit:
#                 limit = int(limit)
            
#             # Get date filtering parameters
#             start_date = request.GET.get('start_date', None)
#             end_date = request.GET.get('end_date', None)
#             frequency = request.GET.get('frequency', 'monthly')
            
#             # Debug logging
#             print(f"Chart API called with: limit={limit}, start_date={start_date}, end_date={end_date}, frequency={frequency}")
            
#             # Parse dates if provided
#             start_date_obj = None
#             end_date_obj = None
            
#             if start_date:
#                 start_date_obj = parse_date(start_date)
#                 if not start_date_obj:
#                     return Response({
#                         'success': False,
#                         'message': 'Invalid start_date format. Use YYYY-MM-DD.',
#                         'data': []
#                     }, status=status.HTTP_400_BAD_REQUEST)
            
#             if end_date:
#                 end_date_obj = parse_date(end_date)
#                 if not end_date_obj:
#                     return Response({
#                         'success': False,
#                         'message': 'Invalid end_date format. Use YYYY-MM-DD.',
#                         'data': []
#                     }, status=status.HTTP_400_BAD_REQUEST)
            
#             # Initialize your Report class
#             report = SalesTopItem()
            
#             # ✅ FIXED: Use the correct method name
#             result = report.fetch_all_top_item(
#                 start_date=start_date_obj,
#                 end_date=end_date_obj,
#                 frequency=frequency
#             )
            
#             # Apply limit if provided
#             items = result.get('items', [])
#             if limit and limit > 0:
#                 items = items[:limit]
            
#             print(f"Returning {len(items)} items after date filtering")  # Debug log
            
#             # Return proper Response format
#             return Response({
#                 'success': True,
#                 'data': items,
#                 'total_invoices': result.get('total_invoices', 0),
#                 'showing_top': len(items),
#                 'date_filter_applied': result.get('date_filter_applied', False),
#                 'frequency': frequency,
#                 'date_range': result.get('date_range', {
#                     'start_date': start_date,
#                     'end_date': end_date
#                 })
#             }, status=status.HTTP_200_OK)
            
#         except ValueError as e:
#             return Response({
#                 'success': False,
#                 'message': 'Invalid limit parameter. Must be a valid integer.',
#                 'data': []
#             }, status=status.HTTP_400_BAD_REQUEST)
            
#         except Exception as e:
#             print(f"Error in SalesTopItemChartView: {str(e)}")  # Debug log
#             return Response({
#                 'success': False,
#                 'message': f'Error retrieving top items: {str(e)}',
#                 'data': []
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
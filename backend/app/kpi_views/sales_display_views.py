from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.sales_display_service import SalesDisplayService
from datetime import datetime

# POS item summary
class SalesDisplayPOSItemSummaryView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        try:
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response({"error": "Invalid date format, use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        service = SalesDisplayService()
        items = service.top_selling_pos_items(start_date=start_date, end_date=end_date)
        return Response(items, status=status.HTTP_200_OK)

# Online item summary
class SalesDisplayOnlineItemSummaryView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        try:
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response({"error": "Invalid date format, use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        service = SalesDisplayService()
        items = service.top_selling_online_items(start_date=start_date, end_date=end_date)
        return Response(items, status=status.HTTP_200_OK)

# POS sales listing
class SalesDisplayAllSalesView(APIView):
    def get(self, request):
        service = SalesDisplayService()
        sales = service.fetch_all_sales()
        return Response(sales, status=status.HTTP_200_OK)

# Online transaction listing
class SalesDisplayAllOnlineTransactionsView(APIView):
    def get(self, request):
        service = SalesDisplayService()
        transactions = service.fetch_all_online_transactions()
        return Response(transactions, status=status.HTTP_200_OK)

# Combined per-product display (category name, stock left, items sold, total sales)
class SalesDisplayByItemView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        include_voided = request.query_params.get('include_voided', 'false').lower() == 'true'
        
        try:
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response({"error": "Invalid date format, use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        
        service = SalesDisplayService()
        # Use the new method with proper date filtering
        rows = service.get_sales_by_item_with_date_filter(
            start_date=start_date, 
            end_date=end_date,
            include_voided=include_voided
        )
        return Response(rows, status=status.HTTP_200_OK)

# New view for sales summary statistics
class SalesDisplaySummaryView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        try:
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response({"error": "Invalid date format, use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        
        service = SalesDisplayService()
        summary = service.get_sales_summary_by_date_range(
            start_date=start_date, 
            end_date=end_date
        )
        return Response(summary, status=status.HTTP_200_OK)
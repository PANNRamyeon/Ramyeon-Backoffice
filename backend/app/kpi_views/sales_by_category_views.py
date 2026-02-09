from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from ..services.sales_by_category import SalesByCategoryService


class SalesByCategoryView(APIView):
    """
    Fetches all sales data grouped by category.
    Supports date filtering and optional voided inclusion.
    Returns enhanced metrics including averages and trends.
    """

    def get(self, request):
        # Extract query parameters
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        include_voided = request.query_params.get("include_voided", "false").lower() == "true"
        include_trends = request.query_params.get("include_trends", "false").lower() == "true"

        # Validate date format
        try:
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response(
                {"error": "Invalid date format, use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Call service
        try:
            service = SalesByCategoryService()
            
            if include_trends:
                category_sales = service.get_category_performance_trends(
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                category_sales = service.get_sales_by_category_with_date_filter(
                    start_date=start_date,
                    end_date=end_date,
                    include_voided=include_voided
                )
            
            return Response(category_sales, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"❌ Error in SalesByCategoryView: {str(e)}")
            return Response(
                {"error": "Failed to fetch category sales data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TopCategoriesView(APIView):
    """
    Returns the top N categories based on total sales.
    Enhanced with performance metrics.
    """

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        limit = int(request.query_params.get("limit", 5))

        # Validate date format
        try:
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response(
                {"error": "Invalid date format, use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = SalesByCategoryService()
            top_categories = service.get_top_categories(
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            return Response(top_categories, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"❌ Error in TopCategoriesView: {str(e)}")
            return Response(
                {"error": "Failed to fetch top categories."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CategoryPerformanceDetailView(APIView):
    """
    Detailed performance view for a specific category
    """
    
    def get(self, request, category_id):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        
        try:
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response(
                {"error": "Invalid date format, use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            service = SalesByCategoryService()
            all_categories = service.get_category_performance_trends(
                start_date=start_date,
                end_date=end_date
            )
            
            # Find the specific category
            category_data = next(
                (cat for cat in all_categories if cat['category_id'] == category_id), 
                None
            )
            
            if not category_data:
                return Response(
                    {"error": "Category not found or has no sales data in the specified period."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            return Response(category_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ Error in CategoryPerformanceDetailView: {str(e)}")
            return Response(
                {"error": "Failed to fetch category performance data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
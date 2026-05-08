"""
Sales Analytics API Views (v5 — DynamoDB)
Base: /api/v1/admin/reports/
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
import logging

from app.services.analytics.sales_analytics_service import SalesAnalyticsService

logger = logging.getLogger(__name__)

# Module-level singleton — instantiated once per worker process
_service: SalesAnalyticsService | None = None


def _svc() -> SalesAnalyticsService:
    global _service
    if _service is None:
        _service = SalesAnalyticsService()
    return _service


def _parse_dates(query_params):
    """
    Parse start_date and end_date from query params.
    Returns (start_date, end_date, error_response).
    error_response is None if parsing succeeded.
    """
    start_date = query_params.get("start_date")
    end_date = query_params.get("end_date")
    try:
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return None, None, Response(
            {"error": "Invalid date format, use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return start_date, end_date, None


# --------------------------------------------------------------------------- #
# Summary                                                                      #
# --------------------------------------------------------------------------- #

class SalesSummaryView(APIView):
    """
    GET /reports/sales-summary/

    Query params:
        start_date  YYYY-MM-DD
        end_date    YYYY-MM-DD
        frequency   daily|weekly|monthly|yearly  (overrides dates)
    """

    def get(self, request):
        start_date, end_date, err = _parse_dates(request.query_params)
        if err:
            return err
        frequency = request.query_params.get("frequency")
        try:
            result = _svc().get_sales_summary(start_date, end_date, frequency)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("SalesSummaryView: %s", e)
            return Response({"error": "Failed to fetch sales summary."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --------------------------------------------------------------------------- #
# Sales by Item                                                                #
# --------------------------------------------------------------------------- #

class SalesByItemView(APIView):
    """
    GET /reports/sales-by-item/

    Query params:
        start_date     YYYY-MM-DD
        end_date       YYYY-MM-DD
        frequency      daily|weekly|monthly|yearly
        include_voided true|false  (default false)
    """

    def get(self, request):
        start_date, end_date, err = _parse_dates(request.query_params)
        if err:
            return err
        frequency = request.query_params.get("frequency")
        include_voided = request.query_params.get("include_voided", "false").lower() == "true"
        try:
            result = _svc().get_sales_by_item(start_date, end_date, frequency, include_voided)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("SalesByItemView: %s", e)
            return Response({"error": "Failed to fetch sales by item."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TopItemsView(APIView):
    """
    GET /reports/top-items/

    Query params:
        start_date  YYYY-MM-DD
        end_date    YYYY-MM-DD
        frequency   daily|weekly|monthly|yearly
        limit       int (default 5)
    """

    def get(self, request):
        start_date, end_date, err = _parse_dates(request.query_params)
        if err:
            return err
        frequency = request.query_params.get("frequency")
        try:
            limit = int(request.query_params.get("limit", 5))
        except ValueError:
            limit = 5
        try:
            result = _svc().get_top_items(start_date, end_date, frequency, limit)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("TopItemsView: %s", e)
            return Response({"error": "Failed to fetch top items."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --------------------------------------------------------------------------- #
# Sales by Category                                                            #
# --------------------------------------------------------------------------- #

class SalesByCategoryView(APIView):
    """
    GET /reports/sales-by-category/

    Query params:
        start_date      YYYY-MM-DD
        end_date        YYYY-MM-DD
        frequency       daily|weekly|monthly|yearly
        include_voided  true|false  (default false)
        include_trends  true|false  (default false)
    """

    def get(self, request):
        start_date, end_date, err = _parse_dates(request.query_params)
        if err:
            return err
        frequency = request.query_params.get("frequency")
        include_voided = request.query_params.get("include_voided", "false").lower() == "true"
        include_trends = request.query_params.get("include_trends", "false").lower() == "true"
        try:
            result = _svc().get_sales_by_category(
                start_date, end_date, frequency, include_voided, include_trends
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("SalesByCategoryView: %s", e)
            return Response({"error": "Failed to fetch sales by category."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TopCategoriesView(APIView):
    """
    GET /reports/top-categories/

    Query params:
        start_date  YYYY-MM-DD
        end_date    YYYY-MM-DD
        frequency   daily|weekly|monthly|yearly
        limit       int (default 5)
    """

    def get(self, request):
        start_date, end_date, err = _parse_dates(request.query_params)
        if err:
            return err
        frequency = request.query_params.get("frequency")
        try:
            limit = int(request.query_params.get("limit", 5))
        except ValueError:
            limit = 5
        try:
            result = _svc().get_top_categories(start_date, end_date, frequency, limit)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("TopCategoriesView: %s", e)
            return Response({"error": "Failed to fetch top categories."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryPerformanceDetailView(APIView):
    """
    GET /reports/category-performance/<category_id>/

    Query params:
        start_date  YYYY-MM-DD
        end_date    YYYY-MM-DD
    """

    def get(self, request, category_id):
        start_date, end_date, err = _parse_dates(request.query_params)
        if err:
            return err
        try:
            all_categories = _svc().get_sales_by_category(
                start_date, end_date, include_trends=True
            )
            category_data = next(
                (c for c in all_categories if c["category_id"] == category_id), None
            )
            if not category_data:
                return Response(
                    {"error": "Category not found or has no sales data in the specified period."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(category_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("CategoryPerformanceDetailView: %s", e)
            return Response({"error": "Failed to fetch category performance data."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --------------------------------------------------------------------------- #
# Period breakdown (chart data)                                                #
# --------------------------------------------------------------------------- #

class SalesByPeriodView(APIView):
    """
    GET /reports/sales-by-period/

    Query params (all required):
        start_date   YYYY-MM-DD
        end_date     YYYY-MM-DD
        period_type  daily|weekly|monthly  (default daily)
    """

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        period_type = request.query_params.get("period_type", "daily")

        if not start_date or not end_date:
            return Response({"error": "start_date and end_date are required."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return Response({"error": "Invalid date format, use YYYY-MM-DD."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            result = _svc().get_sales_by_period(start_date, end_date, period_type)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("SalesByPeriodView: %s", e)
            return Response({"error": "Failed to fetch sales by period."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

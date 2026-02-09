from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse
from ..services.customer_service import CustomerService
from ..decorators.authenticationDecorator import require_admin
import logging
import os

logger = logging.getLogger(__name__)

class CustomerImportExportView(APIView):
    """
    Handles import and export of customers (CSV format).
    - GET  → Export all customers to CSV
    - POST → Import customers from uploaded CSV
    """
    parser_classes = [MultiPartParser, FormParser]

    def __init__(self):
        self.customer_service = CustomerService()

    # ======================================================
    # EXPORT CUSTOMERS TO CSV
    # ======================================================
    @require_admin
    def get(self, request):
        """Export customers as CSV (Admin only)."""
        try:
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'

            # Call service method (safe user handling)
            csv_data = self.customer_service.export_customers_to_csv(
                include_deleted=include_deleted
            )

            if not csv_data:
                return Response(
                    {"message": "No customers found to export."},
                    status=status.HTTP_204_NO_CONTENT
                )

            response = HttpResponse(csv_data, content_type="text/csv")
            response['Content-Disposition'] = 'attachment; filename="customers_export.csv"'
            return response

        except Exception as e:
            logger.error(f"Error exporting customers: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ======================================================
    # IMPORT CUSTOMERS FROM CSV
    # ======================================================
    @require_admin
    def post(self, request):
        """Import customers from uploaded CSV (Admin only)."""
        try:
            file = request.FILES.get('file')
            if not file:
                return Response(
                    {"error": "CSV file is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Save file temporarily
            temp_path = f"/tmp/{file.name}"
            with open(temp_path, "wb+") as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # Import customers using service (safe current_user)
            result = self.customer_service.import_customers_from_csv(
                temp_path,
                getattr(request, "current_user", None)
            )

            # Clean up file (optional but recommended)
            try:
                os.remove(temp_path)
            except Exception:
                pass

            imported_count = result.get("imported_count", 0) if isinstance(result, dict) else 0

            return Response(
                {
                    "message": f"Import completed successfully. {imported_count} customers imported.",
                    "imported_count": imported_count
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error importing customers: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

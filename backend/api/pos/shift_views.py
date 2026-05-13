import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.decorators.authenticationDecorator import require_authentication
from app.services.pos.shift_service import ShiftService

logger = logging.getLogger(__name__)

_service = ShiftService()


class ShiftActiveView(APIView):
    """GET pos/shifts/active/?cashier_id=USER-00001"""

    @require_authentication
    def get(self, request):
        cashier_id = request.query_params.get('cashier_id', '').strip()
        if not cashier_id:
            return Response(
                {"success": False, "error": "cashier_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            shift = _service.get_active_shift(cashier_id)
            if not shift:
                return Response(
                    {"success": False, "error": "No active shift found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response({"success": True, "shift": shift}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting active shift for {cashier_id}: {e}")
            return Response(
                {"success": False, "error": "Failed to retrieve active shift"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ShiftStartView(APIView):
    """POST pos/shifts/start/"""

    @require_authentication
    def post(self, request):
        cashier_id = request.data.get('cashier_id', '').strip()
        opening_cash_raw = request.data.get('opening_cash')

        if not cashier_id:
            return Response(
                {"success": False, "error": "cashier_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if opening_cash_raw is None:
            return Response(
                {"success": False, "error": "opening_cash is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            opening_cash = float(opening_cash_raw)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "error": "opening_cash must be a number"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if opening_cash < 0:
            return Response(
                {"success": False, "error": "opening_cash cannot be negative"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            shift = _service.start_shift(cashier_id, opening_cash)
            return Response(
                {"success": True, "message": "Shift started successfully", "shift": shift},
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error starting shift for {cashier_id}: {e}")
            return Response(
                {"success": False, "error": "Failed to start shift"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ShiftCloseView(APIView):
    """POST pos/shifts/<shift_id>/close/"""

    @require_authentication
    def post(self, request, shift_id: str):
        closing_cash_raw = request.data.get('closing_cash')

        if closing_cash_raw is None:
            return Response(
                {"success": False, "error": "closing_cash is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            closing_cash = float(closing_cash_raw)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "error": "closing_cash must be a number"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if closing_cash < 0:
            return Response(
                {"success": False, "error": "closing_cash cannot be negative"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            shift = _service.end_shift(shift_id, closing_cash)
            return Response(
                {"success": True, "message": "Shift closed successfully", "shift": shift},
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error closing shift {shift_id}: {e}")
            return Response(
                {"success": False, "error": "Failed to close shift"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ShiftDetailView(APIView):
    """GET pos/shifts/<shift_id>/"""

    @require_authentication
    def get(self, request, shift_id: str):
        try:
            shift = _service.get_shift_by_id(shift_id)
            if not shift:
                return Response(
                    {"success": False, "error": "Shift not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response({"success": True, "shift": shift}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching shift {shift_id}: {e}")
            return Response(
                {"success": False, "error": "Failed to retrieve shift"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ShiftListView(APIView):
    """GET pos/shifts/?cashier_id=&status=&limit="""

    @require_authentication
    def get(self, request):
        cashier_id = request.query_params.get('cashier_id', '').strip() or None
        status_filter = request.query_params.get('status', '').strip() or None
        try:
            limit = int(request.query_params.get('limit', 50))
            limit = max(1, min(limit, 200))
        except (TypeError, ValueError):
            limit = 50

        if status_filter and status_filter not in ('open', 'closed'):
            return Response(
                {"success": False, "error": "status must be 'open' or 'closed'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            shifts = _service.get_all_shifts(
                cashier_id=cashier_id,
                status=status_filter,
                limit=limit,
            )
            return Response(
                {"success": True, "shifts": shifts, "count": len(shifts)},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error listing shifts: {e}")
            return Response(
                {"success": False, "error": "Failed to retrieve shifts"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

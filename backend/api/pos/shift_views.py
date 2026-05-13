"""
POS Shift Management Views
Base URL: /api/v1/pos/shifts/
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from models.Shifts import Shift, validate_shift_data
import logging

logger = logging.getLogger(__name__)


class ShiftListView(APIView):
    """GET shifts/ — list all shifts"""

    def get(self, request):
        try:
            shifts = Shift.get_all_shifts()
            return Response(
                {'success': True, 'data': [s.to_simple_dict() for s in shifts], 'count': len(shifts)},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error listing shifts: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StartShiftView(APIView):
    """POST shifts/start/ — create a new shift"""

    def post(self, request):
        try:
            cashier_id = request.data.get('cashier_id')
            opening_cash = request.data.get('opening_cash', 0.0)

            is_valid, error_msg = validate_shift_data(cashier_id, opening_cash)
            if not is_valid:
                return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

            shift = Shift.create_shift(cashier_id=cashier_id, expected_cash=float(opening_cash))
            return Response(
                {'success': True, 'message': 'Shift started', 'data': shift.to_dict()},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error starting shift: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ActiveShiftView(APIView):
    """GET shifts/active/?cashier_id=X — get the open shift for a cashier"""

    def get(self, request):
        try:
            cashier_id = request.query_params.get('cashier_id')
            if not cashier_id:
                return Response({'error': 'cashier_id query param is required'}, status=status.HTTP_400_BAD_REQUEST)

            shift = Shift.get_active_shift_by_cashier(cashier_id)
            if not shift:
                return Response({'error': 'No active shift found for this cashier'}, status=status.HTTP_404_NOT_FOUND)

            return Response({'success': True, 'data': shift.to_dict()}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching active shift: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ShiftDetailView(APIView):
    """GET shifts/<shift_id>/ — get a shift by ID"""

    def get(self, request, shift_id):
        try:
            shift = Shift.get_by_id(shift_id)
            if not shift:
                return Response({'error': f'Shift {shift_id} not found'}, status=status.HTTP_404_NOT_FOUND)

            return Response({'success': True, 'data': shift.to_dict()}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching shift {shift_id}: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CloseShiftView(APIView):
    """POST shifts/<shift_id>/close/ — close a shift"""

    def post(self, request, shift_id):
        try:
            closing_cash = request.data.get('closing_cash')
            if closing_cash is None:
                return Response({'error': 'closing_cash is required'}, status=status.HTTP_400_BAD_REQUEST)

            shift = Shift.get_by_id(shift_id)
            if not shift:
                return Response({'error': f'Shift {shift_id} not found'}, status=status.HTTP_404_NOT_FOUND)

            shift.close_shift(closing_cash=float(closing_cash))
            return Response(
                {'success': True, 'message': f'Shift {shift_id} closed', 'data': shift.to_dict()},
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error closing shift {shift_id}: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
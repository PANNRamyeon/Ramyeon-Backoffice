from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timezone
from app.services.marketing.promotions_service import PromotionService
# from app.decorators.authenticationDecorator import require_admin, require_authentication  # COMMENTED FOR TESTING
import logging
import json
import qrcode
from io import BytesIO
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

# Helper to convert a date string to a UTC datetime
def parse_date_string(date_str: str) -> datetime:
    """Convert an ISO date string to a timezone-aware UTC datetime."""
    if not date_str:
        return None
    date_str = date_str.replace('Z', '+00:00')
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class PromotionHealthCheckView(APIView):
    def get(self, request):
        return Response({
            "service": "Promotion Management",
            "status": "active",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }, status=status.HTTP_200_OK)


class PromotionListView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            filters = {}
            for param in ['status', 'type', 'target_type', 'created_by']:
                val = request.GET.get(param)
                if val:
                    filters[param] = val

            search = request.GET.get('search') or request.GET.get('q')
            if search:
                filters['search_query'] = search

            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')
            if date_from or date_to:
                try:
                    if date_from:
                        filters['date_from'] = parse_date_string(date_from)
                    if date_to:
                        filters['date_to'] = parse_date_string(date_to)
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use ISO (YYYY-MM-DD)"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))

            result = service.get_all_promotions(filters=filters, page=page, limit=limit)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"PromotionListView get error: {e}")
            return Response({"error": f"Error retrieving promotions: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # @require_authentication   # COMMENTED FOR TESTING
    def post(self, request):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            promo_data = request.data.copy()
            promo_data['created_by'] = user_id

            for field in ['start_date', 'end_date']:
                if field in promo_data and isinstance(promo_data[field], str):
                    try:
                        promo_data[field] = parse_date_string(promo_data[field])
                    except ValueError as e:
                        return Response({"error": f"Invalid {field}: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

            result = service.create_promotion(promo_data)
            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"PromotionListView post error: {e}")
            return Response({"error": f"Error creating promotion: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class PromotionDetailView(APIView):
    # @require_authentication   # COMMENTED FOR TESTING
    def get(self, request, promotion_id):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            result = service.get_promotion_by_id(promotion_id)
            if result.get('success'):
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Detail get error: {e}")
            return Response({"error": f"Error retrieving promotion: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # @require_admin   # COMMENTED FOR TESTING
    def put(self, request, promotion_id):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            update_data = request.data.copy()
            for field in ['start_date', 'end_date']:
                if field in update_data and isinstance(update_data[field], str):
                    try:
                        update_data[field] = parse_date_string(update_data[field])
                    except ValueError as e:
                        return Response({"error": f"Invalid {field}: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

            result = service.update_promotion(promotion_id, update_data)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Detail put error: {e}")
            return Response({"error": f"Error updating promotion: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # @require_admin   # COMMENTED FOR TESTING
    def delete(self, request, promotion_id):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            reason = request.data.get('reason') or request.GET.get('reason', 'Deleted via API')
            result = service.delete_promotion(promotion_id, reason)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return Response({"error": f"Error deleting promotion: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ActivePromotionsView(APIView):
    def get(self, request):
        try:
            user_id = request.current_user.get('user_id') if hasattr(request, 'current_user') else "system"
            service = PromotionService(current_user=user_id)
            result = service.get_active_promotions()
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Active promotions error: {e}")
            return Response({"error": f"Error retrieving active promotions: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromotionActivationView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def post(self, request, promotion_id):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            reason = request.data.get('reason')
            result = service.activate_promotion(promotion_id, reason)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Activation error: {e}")
            return Response({"error": f"Error activating promotion: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromotionDeactivationView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def post(self, request, promotion_id):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            reason = request.data.get('reason', 'Deactivated via API')
            result = service.deactivate_promotion(promotion_id, reason)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Deactivation error: {e}")
            return Response({"error": f"Error deactivating promotion: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromotionExpirationView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def post(self, request, promotion_id):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            result = service.expire_promotion(promotion_id)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Expiration error: {e}")
            return Response({"error": f"Error expiring promotion: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromotionApplicationView(APIView):
    def post(self, request):
        try:
            customer_id = request.data.get('customer_id', 'test_admin')
            service = PromotionService(current_user=customer_id)
            order_data = request.data
            if not order_data.get('items') or not order_data.get('total_amount'):
                return Response({"error": "Order must include items and total_amount"}, status=status.HTTP_400_BAD_REQUEST)
            result = service.apply_promotion_to_order(order_data, customer_id)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PromotionStatisticsView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            start_date = None
            end_date = None
            if request.GET.get('start_date'):
                start_date = parse_date_string(request.GET['start_date'])
            if request.GET.get('end_date'):
                end_date = parse_date_string(request.GET['end_date'])
            result = service.get_promotion_statistics(start_date, end_date)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ValueError:
            return Response({"error": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Statistics error: {e}")
            return Response({"error": f"Error retrieving statistics: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromotionAuditView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request, promotion_id):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            limit = int(request.GET.get('limit', 50))
            result = service.get_promotion_audit_history(promotion_id, limit)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Audit error: {e}")
            return Response({"error": f"Error retrieving audit history: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromotionSearchView(APIView):
    # @require_authentication   # COMMENTED FOR TESTING
    def get(self, request):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            query = request.GET.get('q', '')
            if not query:
                return Response({"error": "Query parameter 'q' is required"}, status=status.HTTP_400_BAD_REQUEST)
            filters = {'search_query': query}
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            result = service.get_all_promotions(filters=filters, page=page, limit=limit)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return Response({"error": f"Error searching promotions: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromotionReportView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request, promotion_id):
        return Response({"error": "Report generation not yet implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)


class PromotionByNameView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request):
        promotion_name = request.GET.get('name')
        if not promotion_name:
            return Response({"success": False, "error": "Missing 'name' query parameter"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            all_promos, _ = service.get_promotions(limit=1000)
            for promo in all_promos:
                if promo.get('name', '').strip().lower() == promotion_name.strip().lower():
                    return Response({'success': True, 'promotion': promo}, status=status.HTTP_200_OK)
            return Response({"success": False, "error": "Promotion not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"ByName error: {e}")
            return Response({"error": f"Error retrieving promotion: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromotionRestoreView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def post(self, request, promotion_id):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            result = service.restore_promotion(promotion_id)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Restore error: {e}")
            return Response({"error": f"Error restoring promotion: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PromotionHardDeleteView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def delete(self, request, promotion_id):
        try:
            confirm = request.GET.get('confirm', '').lower()
            if confirm != 'yes':
                return Response({"error": "Permanent deletion requires confirmation", "message": "Add ?confirm=yes"}, status=status.HTTP_400_BAD_REQUEST)
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            result = service.hard_delete_promotion(promotion_id, confirmation_token="PERMANENT_DELETE_CONFIRMED")
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Hard delete error: {e}")
            return Response({"error": f"Error permanently deleting promotion: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeletedPromotionsView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request):
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            result = service.get_deleted_promotions_paginated(page=page, limit=limit)
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Deleted promotions error: {e}")
            return Response({"error": f"Error retrieving deleted promotions: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(cache_page(60 * 15), name='dispatch')
class PromotionQRView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, promotion_id):
        service = PromotionService(current_user="system")
        result = service.get_promotion_by_id(promotion_id)
        if not result.get('success'):
            return Response({"error": "Promotion not found"}, status=status.HTTP_404_NOT_FOUND)

        base_url = request.build_absolute_uri('/').rstrip('/')
        apply_url = f"{base_url}/apply?promo={promotion_id}"
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(apply_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return HttpResponse(buffer.getvalue(), content_type="image/png")
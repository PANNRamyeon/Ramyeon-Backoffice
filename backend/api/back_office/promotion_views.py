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

# ================================================================
# VIEW CLASSES
# ================================================================

class PromotionHealthCheckView(APIView):
    """Health check endpoint"""
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
        """Get all promotions with filtering and pagination (token‑based)"""
        try:
            # For testing – hardcoded user
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            filters = {}

            # Map frontend filters
            if request.GET.get('status'):
                filters['status'] = request.GET.get('status')
            if request.GET.get('type'):
                filters['type'] = request.GET.get('type')
            if request.GET.get('target_type'):
                filters['target_type'] = request.GET.get('target_type')
            if request.GET.get('created_by'):
                filters['created_by'] = request.GET.get('created_by')
            search = request.GET.get('search') or request.GET.get('q')
            if search:
                filters['search_query'] = search

            # Date range
            if request.GET.get('date_from') and request.GET.get('date_to'):
                try:
                    filters['date_from'] = datetime.fromisoformat(request.GET.get('date_from'))
                    filters['date_to'] = datetime.fromisoformat(request.GET.get('date_to'))
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use ISO (YYYY-MM-DD)"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Pagination token
            last_token = request.GET.get('next_page_token')
            last_evaluated_key = json.loads(last_token) if last_token else None
            limit = int(request.GET.get('limit', 20))

            result = service.get_all_promotions(
                filters=filters,
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error in PromotionListView.get: {e}")
            return Response(
                {"error": f"Error retrieving promotions: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # @require_authentication   # COMMENTED FOR TESTING
    def post(self, request):
        """Create new promotion"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            promotion_data = request.data.copy()
            promotion_data['created_by'] = user_id

            # Convert date strings to timezone-aware UTC datetime objects
            for date_field in ['start_date', 'end_date']:
                if date_field in promotion_data and isinstance(promotion_data[date_field], str):
                    try:
                        date_str = promotion_data[date_field]
                        if date_str.endswith('Z'):
                            date_str = date_str.replace('Z', '+00:00')
                        elif '+' not in date_str and date_str.count('-') >= 3:
                            if 'T' in date_str:
                                date_str = date_str + '+00:00'
                            else:
                                date_str = date_str + 'T00:00:00+00:00'

                        dt = datetime.fromisoformat(date_str)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = dt.astimezone(timezone.utc)

                        promotion_data[date_field] = dt
                    except (ValueError, AttributeError) as e:
                        logger.error(f"Error parsing {date_field}: {e}")
                        return Response(
                            {"error": f"Invalid {date_field} format. Use ISO format: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            result = service.create_promotion(promotion_data)

            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionListView.post: {e}")
            return Response(
                {"error": f"Error creating promotion: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class PromotionDetailView(APIView):
    # @require_authentication   # COMMENTED FOR TESTING
    def get(self, request, promotion_id):
        """Get promotion by ID"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            result = service.get_promotion_by_id(promotion_id)

            if result.get('success'):
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error in PromotionDetailView.get: {e}")
            return Response(
                {"error": f"Error retrieving promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    # @require_admin   # COMMENTED FOR TESTING
    def put(self, request, promotion_id):
        """Update promotion"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            update_data = request.data.copy()

            # Convert date strings if provided
            for date_field in ['start_date', 'end_date']:
                if date_field in update_data and isinstance(update_data[date_field], str):
                    try:
                        date_str = update_data[date_field]
                        if date_str.endswith('Z'):
                            date_str = date_str.replace('Z', '+00:00')
                        elif '+' not in date_str and date_str.count('-') >= 3:
                            if 'T' in date_str:
                                date_str = date_str + '+00:00'
                            else:
                                date_str = date_str + 'T00:00:00+00:00'

                        dt = datetime.fromisoformat(date_str)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = dt.astimezone(timezone.utc)

                        update_data[date_field] = dt
                    except (ValueError, AttributeError) as e:
                        logger.error(f"Error parsing {date_field}: {e}")
                        return Response(
                            {"error": f"Invalid {date_field} format: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            result = service.update_promotion(promotion_id, update_data)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionDetailView.put: {e}")
            return Response(
                {"error": f"Error updating promotion: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    # @require_admin   # COMMENTED FOR TESTING
    def delete(self, request, promotion_id):
        """Soft delete promotion (default)"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            reason = request.data.get('reason') or request.GET.get('reason', 'Deleted via API')

            result = service.delete_promotion(promotion_id, reason)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionDetailView.delete: {e}")
            return Response(
                {"error": f"Error deleting promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ActivePromotionsView(APIView):
    def get(self, request):
        """Get all currently active promotions"""
        try:
            # Already has fallback
            user_id = request.current_user.get('user_id') if hasattr(request, 'current_user') else "system"
            service = PromotionService(current_user=user_id)

            result = service.get_active_promotions()

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error in ActivePromotionsView.get: {e}")
            return Response(
                {"error": f"Error retrieving active promotions: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionActivationView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def post(self, request, promotion_id):
        """Activate a promotion"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            reason = request.data.get('reason')
            result = service.activate_promotion(promotion_id, reason)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionActivationView.post: {e}")
            return Response(
                {"error": f"Error activating promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionDeactivationView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def post(self, request, promotion_id):
        """Deactivate a promotion"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            reason = request.data.get('reason', 'Deactivated via API')
            result = service.deactivate_promotion(promotion_id, reason)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionDeactivationView.post: {e}")
            return Response(
                {"error": f"Error deactivating promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionExpirationView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def post(self, request, promotion_id):
        """Manually expire a promotion (deactivate with reason 'Expired manually')"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            result = service.expire_promotion(promotion_id)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionExpirationView.post: {e}")
            return Response(
                {"error": f"Error expiring promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionApplicationView(APIView):
    # @require_authentication   # COMMENTED FOR TESTING
    def post(self, request):
        """Apply best available promotion to an order"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            order_data = request.data
            customer_id = user_id

            if not order_data.get('items') or not order_data.get('total_amount'):
                return Response(
                    {"error": "Order must include items and total_amount"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            result = service.apply_promotion_to_order(order_data, customer_id)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionApplicationView.post: {e}")
            return Response(
                {"error": f"Error applying promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionStatisticsView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request):
        """Get promotion statistics and analytics"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            start_date = None
            end_date = None

            if request.GET.get('start_date'):
                try:
                    start_date = datetime.fromisoformat(request.GET.get('start_date'))
                except ValueError:
                    return Response(
                        {"error": "Invalid start_date format"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if request.GET.get('end_date'):
                try:
                    end_date = datetime.fromisoformat(request.GET.get('end_date'))
                except ValueError:
                    return Response(
                        {"error": "Invalid end_date format"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            result = service.get_promotion_statistics(start_date, end_date)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error in PromotionStatisticsView.get: {e}")
            return Response(
                {"error": f"Error retrieving statistics: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionAuditView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request, promotion_id):
        """Get audit history for a specific promotion"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            limit = int(request.GET.get('limit', 50))

            result = service.get_promotion_audit_history(promotion_id, limit)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionAuditView.get: {e}")
            return Response(
                {"error": f"Error retrieving audit history: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionSearchView(APIView):
    # @require_authentication   # COMMENTED FOR TESTING
    def get(self, request):
        """Search promotions by name or description"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            query = request.GET.get('q', '')
            if not query:
                return Response(
                    {"error": "Query parameter 'q' is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            filters = {'search_query': query}
            last_token = request.GET.get('next_page_token')
            last_evaluated_key = json.loads(last_token) if last_token else None
            limit = int(request.GET.get('limit', 20))

            result = service.get_all_promotions(
                filters=filters,
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error in PromotionSearchView.get: {e}")
            return Response(
                {"error": f"Error searching promotions: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionReportView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request, promotion_id):
        """Generate detailed usage report for a promotion (placeholder)"""
        return Response(
            {"error": "Report generation not yet implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class PromotionByNameView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request):
        """Get promotion by exact name (case‑insensitive) via query parameter `name`."""
        promotion_name = request.GET.get('name')
        if not promotion_name:
            return Response(
                {"success": False, "error": "Missing 'name' query parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            # Use a scan with case‑insensitive filter
            # Note: DynamoDB does not support case‑insensitive queries natively.
            # We'll fetch all promotions and filter in Python (since total promotions is small).
            # For large datasets, consider adding a lowercased name attribute and GSI.
            all_promos, _ = service.get_promotions(limit=1000)  # Adjust limit as needed
            for promo in all_promos:
                if promo.get('name', '').strip().lower() == promotion_name.strip().lower():
                    return Response({
                        'success': True,
                        'data': promo
                    }, status=status.HTTP_200_OK)

            return Response(
                {"success": False, "error": "Promotion not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Error in PromotionByNameView: {e}")
            return Response(
                {"error": f"Error retrieving promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionRestoreView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def post(self, request, promotion_id):
        """Restore soft‑deleted promotion"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            result = service.restore_promotion(promotion_id)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionRestoreView.post: {e}")
            return Response(
                {"error": f"Error restoring promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionHardDeleteView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def delete(self, request, promotion_id):
        """Permanently delete promotion - DANGEROUS"""
        try:
            confirm = request.GET.get('confirm', '').lower()
            if confirm != 'yes':
                return Response({
                    "error": "Permanent deletion requires confirmation",
                    "message": "Add ?confirm=yes to permanently delete this promotion"
                }, status=status.HTTP_400_BAD_REQUEST)

            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            result = service.hard_delete_promotion(
                promotion_id,
                confirmation_token="PERMANENT_DELETE_CONFIRMED"
            )

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in PromotionHardDeleteView.delete: {e}")
            return Response(
                {"error": f"Error permanently deleting promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeletedPromotionsView(APIView):
    # @require_admin   # COMMENTED FOR TESTING
    def get(self, request):
        """Get all soft‑deleted promotions - Admin only"""
        try:
            user_id = "test_admin"
            service = PromotionService(current_user=user_id)

            last_token = request.GET.get('next_page_token')
            last_evaluated_key = json.loads(last_token) if last_token else None
            limit = int(request.GET.get('limit', 20))

            result = service.get_deleted_promotions(
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error in DeletedPromotionsView.get: {e}")
            return Response(
                {"error": f"Error retrieving deleted promotions: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(cache_page(60 * 15), name='dispatch')
class PromotionQRView(APIView):
    """
    Generate a QR code for a promotion.
    The QR code contains a deep-link URL to apply the promotion.
    """
    permission_classes = [AllowAny]  # QR codes may be public (e.g., on flyers)

    def get(self, request, promotion_id):
        # Validate promotion exists
        service = PromotionService(current_user="system")
        result = service.get_promotion_by_id(promotion_id)
        if not result.get('success'):
            return Response(
                {"error": "Promotion not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        promotion = result['data']

        # Build the content to encode
        # Option A: Deep-link URL to your frontend/web app
        base_url = request.build_absolute_uri('/').rstrip('/')
        # Adjust path to match your frontend route
        apply_url = f"{base_url}/apply?promo={promotion_id}"

        # Option B: Just the promotion ID or a custom promo code
        # qr_content = promotion.get('promo_code', promotion_id)

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(apply_url)   # or qr_content
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Save to in-memory bytes buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Return as PNG response
        return HttpResponse(buffer.getvalue(), content_type="image/png")
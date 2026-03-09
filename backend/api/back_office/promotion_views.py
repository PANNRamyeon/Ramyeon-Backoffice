from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timezone
from app.services.marketing.promotions_service import PromotionService
from app.decorators.authenticationDecorator import require_admin, require_authentication
import logging
import json

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
    def get(self, request):
        """Get all promotions with filtering and pagination (token‑based)"""
        try:
            # Initialize service with current user
            user_id = request.current_user.get('user_id')
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

            # Date range – note: these are not directly supported by get_all_promotions yet
            # (could be added later via filter conditions)
            if request.GET.get('date_from') and request.GET.get('date_to'):
                try:
                    filters['date_from'] = datetime.fromisoformat(request.GET.get('date_from'))
                    filters['date_to'] = datetime.fromisoformat(request.GET.get('date_to'))
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use ISO (YYYY-MM-DD)"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Pagination token (if any)
            last_token = request.GET.get('next_page_token')
            # last_token may be a JSON string; service expects a dict or None
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

    @require_authentication
    def post(self, request):
        """Create new promotion"""
        try:
            user_id = request.current_user.get('user_id')
            service = PromotionService(current_user=user_id)

            promotion_data = request.data.copy()
            promotion_data['created_by'] = user_id  # service already sets it, but keep for clarity

            # Convert date strings to timezone-aware UTC datetime objects
            for date_field in ['start_date', 'end_date']:
                if date_field in promotion_data and isinstance(promotion_data[date_field], str):
                    try:
                        date_str = promotion_data[date_field]
                        # Handle ISO format with or without timezone
                        if date_str.endswith('Z'):
                            date_str = date_str.replace('Z', '+00:00')
                        elif '+' not in date_str and date_str.count('-') >= 3:
                            # If no timezone info, assume UTC
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
    @require_authentication
    def get(self, request, promotion_id):
        """Get promotion by PROM-##### ID"""
        try:
            user_id = request.current_user.get('user_id')
            service = PromotionService(current_user=user_id)

            result = service.get_promotion_by_id(promotion_id)

            if result and result.get('success'):
                return Response(result, status=status.HTTP_200_OK)
            else:
                # If result is None or success=False, treat as 404
                return Response(
                    {"success": False, "error": "Promotion not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            logger.error(f"Error in PromotionDetailView.get: {e}")
            return Response(
                {"error": f"Error retrieving promotion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @require_admin
    def put(self, request, promotion_id):
        """Update promotion"""
        try:
            user_id = request.current_user.get('user_id')
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

    @require_admin
    def delete(self, request, promotion_id):
        """Soft delete promotion (default)"""
        try:
            user_id = request.current_user.get('user_id')
            service = PromotionService(current_user=user_id)

            # Reason can be provided in request body or query param
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
    @require_admin
    def post(self, request, promotion_id):
        """Activate a promotion"""
        try:
            user_id = request.current_user.get('user_id')
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
    @require_admin
    def post(self, request, promotion_id):
        """Deactivate a promotion"""
        try:
            user_id = request.current_user.get('user_id')
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
    @require_admin
    def post(self, request, promotion_id):
        """Manually expire a promotion (deactivate with reason 'Expired manually')"""
        try:
            user_id = request.current_user.get('user_id')
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
    @require_authentication
    def post(self, request):
        """Apply best available promotion to an order"""
        try:
            user_id = request.current_user.get('user_id')
            service = PromotionService(current_user=user_id)

            order_data = request.data
            customer_id = user_id

            # Validate order data
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
    @require_admin
    def get(self, request):
        """Get promotion statistics and analytics"""
        try:
            user_id = request.current_user.get('user_id')
            service = PromotionService(current_user=user_id)

            # Get date range if provided
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
    @require_admin
    def get(self, request, promotion_id):
        """Get audit history for a specific promotion"""
        try:
            user_id = request.current_user.get('user_id')
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
    @require_authentication
    def get(self, request):
        """Search promotions by name or description"""
        try:
            user_id = request.current_user.get('user_id')
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
    @require_admin
    def get(self, request, promotion_id):
        """Generate detailed usage report for a promotion (placeholder)"""
        # This view previously called a private method _generate_usage_report
        # which is not part of the updated service. For now, return 501.
        return Response(
            {"error": "Report generation not yet implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class PromotionByNameView(APIView):
    @require_authentication
    def get(self, request, promotion_name):
        """Get promotion by exact name (case‑insensitive)"""
        try:
            user_id = request.current_user.get('user_id')
            service = PromotionService(current_user=user_id)

            filters = {'search_query': promotion_name}
            result = service.get_all_promotions(filters=filters)

            if result['success'] and result['data']['promotions']:
                # Find exact match
                for promo in result['data']['promotions']:
                    if promo.get('name', '').lower() == promotion_name.lower():
                        return Response({
                            'success': True,
                            'data': promo
                        }, status=status.HTTP_200_OK)

            return Response(
                {"success": False, "error": "Promotion not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Error getting promotion by name {promotion_name}: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromotionRestoreView(APIView):
    @require_admin
    def post(self, request, promotion_id):
        """Restore soft‑deleted promotion"""
        try:
            user_id = request.current_user.get('user_id')
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
    @require_admin
    def delete(self, request, promotion_id):
        """Permanently delete promotion - DANGEROUS"""
        try:
            # Require confirmation
            confirm = request.GET.get('confirm', '').lower()
            if confirm != 'yes':
                return Response({
                    "error": "Permanent deletion requires confirmation",
                    "message": "Add ?confirm=yes to permanently delete this promotion"
                }, status=status.HTTP_400_BAD_REQUEST)

            user_id = request.current_user.get('user_id')
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
    @require_admin
    def get(self, request):
        """Get all soft‑deleted promotions - Admin only"""
        try:
            user_id = request.current_user.get('user_id')
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
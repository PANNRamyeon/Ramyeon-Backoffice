# views/promotion_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timezone
from ..services.promotions_service import PromotionService
from ..decorators.authenticationDecorator import require_admin, require_authentication, get_authenticated_user_from_jwt
import logging

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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_authentication
    def get(self, request):
        """Get all promotions with filtering and pagination"""
        try:
            filters = {}

            # Mapping frontend → backend filters
            if request.GET.get('status'):
                filters['status'] = request.GET.get('status')

            if request.GET.get('type'):
                filters['type'] = request.GET.get('type')

            if request.GET.get('target_type'):
                filters['target_type'] = request.GET.get('target_type')

            if request.GET.get('created_by'):
                filters['created_by'] = request.GET.get('created_by')

            # Search should support ?search=
            search_value = request.GET.get('search') or request.GET.get('q')
            if search_value:
                filters['search_query'] = search_value

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

            # Pagination
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))

            # Sorting
            sort_by = request.GET.get('sort_by', 'created_at')
            sort_order = request.GET.get('sort_order', 'desc')

            result = self.promotion_service.get_all_promotions(
                filters=filters,
                page=page,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order
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
            promotion_data = request.data.copy()
            
            # Add creator information
            promotion_data['created_by'] = request.current_user.get('user_id')
            
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
                        # Ensure timezone-aware (convert to UTC)
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
            
            result = self.promotion_service.create_promotion(promotion_data)
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_authentication
    def get(self, request, promotion_id):
        """Get promotion by PROM-#### ID"""
        try:
            result = self.promotion_service.get_promotion_by_id(promotion_id)
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
                
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
            logger.info(f"[VIEW] Promotion update request for {promotion_id}")
            update_data = request.data.copy()
            logger.debug(f"[VIEW] Raw update_data: {update_data}")
            
            # Convert date strings if provided - ensure timezone-aware UTC
            for date_field in ['start_date', 'end_date']:
                if date_field in update_data:
                    logger.debug(f"[VIEW] Processing {date_field}: {update_data[date_field]} (type: {type(update_data[date_field])})")
                    if isinstance(update_data[date_field], str):
                        try:
                            date_str = update_data[date_field]
                            logger.debug(f"[VIEW] {date_field} is string: '{date_str}'")
                            # Handle ISO format with or without timezone
                            if date_str.endswith('Z'):
                                date_str = date_str.replace('Z', '+00:00')
                                logger.debug(f"[VIEW] {date_field} had 'Z', converted to: '{date_str}'")
                            elif '+' not in date_str and date_str.count('-') >= 3:
                                # If no timezone info, assume UTC
                                if 'T' in date_str:
                                    date_str = date_str + '+00:00'
                                else:
                                    date_str = date_str + 'T00:00:00+00:00'
                                logger.debug(f"[VIEW] {date_field} had no timezone, added UTC: '{date_str}'")
                            
                            dt = datetime.fromisoformat(date_str)
                            logger.debug(f"[VIEW] {date_field} parsed to datetime: {dt} (tzinfo: {dt.tzinfo})")
                            
                            # Ensure timezone-aware (convert to UTC)
                            if dt.tzinfo is None:
                                logger.debug(f"[VIEW] {date_field} is NAIVE, adding UTC timezone")
                                dt = dt.replace(tzinfo=timezone.utc)
                            else:
                                logger.debug(f"[VIEW] {date_field} is AWARE, converting to UTC")
                                dt = dt.astimezone(timezone.utc)
                            
                            logger.debug(f"[VIEW] {date_field} final: {dt} (tzinfo: {dt.tzinfo})")
                            update_data[date_field] = dt
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.error(f"[VIEW] Error parsing {date_field}: {e}")
                            import traceback
                            logger.error(f"[VIEW] Traceback: {traceback.format_exc()}")
                            return Response(
                                {"error": f"Invalid {date_field} format: {str(e)}"},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    elif isinstance(update_data[date_field], datetime):
                        logger.debug(f"[VIEW] {date_field} is already datetime: {update_data[date_field]} (tzinfo: {update_data[date_field].tzinfo})")
                        # Ensure it's timezone-aware UTC
                        dt = update_data[date_field]
                        if dt.tzinfo is None:
                            logger.debug(f"[VIEW] {date_field} datetime is NAIVE, adding UTC")
                            update_data[date_field] = dt.replace(tzinfo=timezone.utc)
                        else:
                            logger.debug(f"[VIEW] {date_field} datetime is AWARE, converting to UTC")
                            update_data[date_field] = dt.astimezone(timezone.utc)
                        logger.debug(f"[VIEW] {date_field} after normalization: {update_data[date_field]} (tzinfo: {update_data[date_field].tzinfo})")
            
            logger.info(f"[VIEW] Calling promotion_service.update_promotion with normalized data")
            logger.debug(f"[VIEW] Final update_data: {update_data}")
            result = self.promotion_service.update_promotion(
                promotion_id, 
                update_data, 
                request.current_user.get('user_id')
            )
            
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
        """Soft delete promotion"""
        try:
            # Check if hard delete is requested
            hard_delete = request.GET.get('hard', 'false').lower() == 'true'
            
            result = self.promotion_service.delete_promotion(
                promotion_id, 
                request.current_user.get('user_id'),
                soft_delete=not hard_delete
            )
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    def get(self, request):
        """Get all currently active promotions"""
        try:
            result = self.promotion_service.get_active_promotions()
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_admin
    def post(self, request, promotion_id):
        """Activate a promotion"""
        try:
            result = self.promotion_service.activate_promotion(
                promotion_id, 
                request.current_user.get('user_id')
            )
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_admin
    def post(self, request, promotion_id):
        """Deactivate a promotion"""
        try:
            result = self.promotion_service.deactivate_promotion(
                promotion_id, 
                request.current_user.get('user_id')
            )
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_admin
    def post(self, request, promotion_id):
        """Manually expire a promotion"""
        try:
            result = self.promotion_service.expire_promotion(
                promotion_id, 
                request.current_user.get('user_id')
            )
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_authentication
    def post(self, request):
        """Apply best available promotion to an order"""
        try:
            order_data = request.data
            customer_id = request.current_user.get('user_id')
            
            # Validate order data
            if not order_data.get('items') or not order_data.get('total_amount'):
                return Response(
                    {"error": "Order must include items and total_amount"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = self.promotion_service.apply_promotion_to_order(order_data, customer_id)
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_admin
    def get(self, request):
        """Get promotion statistics and analytics"""
        try:
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
            
            result = self.promotion_service.get_promotion_statistics(start_date, end_date)
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_admin
    def get(self, request, promotion_id):
        """Get audit history for a specific promotion"""
        try:
            limit = int(request.GET.get('limit', 50))
            
            result = self.promotion_service.get_promotion_audit_history(promotion_id, limit)
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_authentication
    def get(self, request):
        """Search promotions by name or description"""
        try:
            query = request.GET.get('q', '')
            if not query:
                return Response(
                    {"error": "Query parameter 'q' is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Build search filter
            filters = {'search_query': query}
            
            # Add pagination
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            result = self.promotion_service.get_all_promotions(
                filters=filters,
                page=page,
                limit=limit
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_admin
    def get(self, request, promotion_id):
        """Generate detailed usage report for a promotion"""
        try:
            report = self.promotion_service._generate_usage_report(promotion_id)
            
            if report:
                return Response({
                    "success": True,
                    "report": report
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "Promotion not found or report unavailable"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error in PromotionReportView.get: {e}")
            return Response(
                {"error": f"Error generating report: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PromotionByNameView(APIView):
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()
    
    @require_authentication
    def get(self, request, promotion_name):
        """Get promotion by name"""
        try:
            # Search for promotions with matching name
            filters = {'search_query': promotion_name}
            result = self.promotion_service.get_all_promotions(filters=filters)
            
            if result['success'] and result['promotions']:
                # Find exact match
                exact_match = None
                for promotion in result['promotions']:
                    if promotion.get('name', '').lower() == promotion_name.lower():
                        exact_match = promotion
                        break
                
                if exact_match:
                    return Response({
                        'success': True,
                        'promotion': exact_match
                    }, status=status.HTTP_200_OK)
            
            return Response(
                {"error": "Promotion not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"Error getting promotion by name {promotion_name}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PromotionRestoreView(APIView):
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()

    @require_admin
    def post(self, request, promotion_id):
        """Restore soft-deleted promotion"""
        try:
            result = self.promotion_service.restore_promotion(
                promotion_id, 
                request.current_user.get('user_id')
            )
            
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()

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
            
            result = self.promotion_service.hard_delete_promotion(
                promotion_id, 
                request.current_user.get('user_id'),
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
    def __init__(self):
        super().__init__()
        self.promotion_service = PromotionService()

    @require_admin
    def get(self, request):
        """Get all soft-deleted promotions - Admin only"""
        try:
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            
            result = self.promotion_service.get_deleted_promotions(
                page=page, 
                limit=limit
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
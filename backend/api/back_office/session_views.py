from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from app.services.identity.session_services import SessionLogService, SessionDisplayService
from app.services.identity.customer_service import CustomerService
from app.services.inventory.product_service import ProductService
from app.services.identity.user_service import UserService
import logging
import csv
import io
from datetime import datetime

logger = logging.getLogger(__name__)

# ================ CORE SESSION VIEWS ================

class SessionLogsView(APIView):
    """Get session logs with filtering options"""

    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 100))
            status_filter = request.query_params.get('status', None)
            user_filter = request.query_params.get('user', None)

            display_service = SessionDisplayService()
            result = display_service.get_session_logs(
                limit=limit,
                status_filter=status_filter,
                user_filter=user_filter
            )
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in SessionLogsView: {e}")
            return Response(
                {'success': False, 'error': str(e), 'data': []},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SessionDetailView(APIView):
    """Get specific session details"""

    def get(self, request, session_id):
        try:
            session_service = SessionLogService()
            session = session_service.get_session_by_id(session_id)

            if not session:
                return Response(
                    {'success': False, 'error': f'Session {session_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response({'success': True, 'data': session}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in SessionDetailView: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ActiveSessionsView(APIView):
    """Get all currently active sessions"""

    def get(self, request):
        try:
            session_service = SessionLogService()
            sessions = session_service.get_active_sessions()
            return Response(
                {'success': True, 'data': sessions, 'count': len(sessions)},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error in ActiveSessionsView: {e}")
            return Response(
                {'success': False, 'error': str(e), 'data': []},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserSessionsView(APIView):
    """Get session history for a specific user"""

    def get(self, request, username):
        try:
            session_service = SessionLogService()
            limit = int(request.query_params.get('limit', 50))

            sessions = session_service.get_user_sessions(username, limit=limit)
            return Response(
                {'success': True, 'data': sessions, 'count': len(sessions), 'username': username},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error in UserSessionsView: {e}")
            return Response(
                {'success': False, 'error': str(e), 'data': []},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SessionStatisticsView(APIView):
    """Get session statistics"""

    def get(self, request):
        try:
            session_service = SessionLogService()
            stats = session_service.get_session_statistics()
            return Response({'success': True, 'data': stats}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in SessionStatisticsView: {e}")
            return Response(
                {'success': False, 'error': str(e),
                 'data': {'active_sessions': 0, 'today_sessions': 0, 'avg_session_duration': 0}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ================ CLEANUP AND ADMIN VIEWS ================

class SessionCleanupView(APIView):
    """Manual session cleanup by date range"""

    def post(self, request):
        try:
            session_service = SessionLogService()
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            dry_run = request.data.get('dry_run', False)

            if start_date:
                try:
                    datetime.fromisoformat(start_date)
                except ValueError:
                    return Response(
                        {'success': False, 'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DD)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if end_date:
                try:
                    datetime.fromisoformat(end_date)
                except ValueError:
                    return Response(
                        {'success': False, 'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DD)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            result = session_service.manual_cleanup_with_date_range(
                start_date=start_date,
                end_date=end_date,
                dry_run=dry_run
            )
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in SessionCleanupView: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CleanupStatusView(APIView):
    """Get cleanup status and retention stats"""

    def get(self, request):
        try:
            session_service = SessionLogService()
            status_data = session_service.get_cleanup_status()
            return Response(
                {'success': True, 'status': status_data},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error in CleanupStatusView: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AutoCleanupControlView(APIView):
    """Start or stop the automated cleanup thread"""

    def post(self, request):
        try:
            session_service = SessionLogService()
            action = request.data.get('action', 'start')
            cleanup_interval_hours = int(request.data.get('cleanup_interval_hours', 720))
            months_old = int(request.data.get('months_old', 6))

            if action == 'start':
                result = session_service.start_automated_cleanup(
                    cleanup_interval_hours=cleanup_interval_hours,
                    months_old=months_old
                )
            elif action == 'stop':
                result = session_service.stop_automated_cleanup()
            else:
                return Response(
                    {'success': False, 'error': 'Invalid action. Use "start" or "stop"'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {'success': False, 'error': 'Invalid parameter values'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in AutoCleanupControlView: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SessionExportView(APIView):
    """Export session data"""

    def post(self, request):
        try:
            display_service = SessionDisplayService()
            export_format = request.data.get('format', 'csv')
            date_filter = request.data.get('date_filter')
            status_filter = request.data.get('status_filter')

            if date_filter:
                try:
                    if 'start_date' in date_filter:
                        datetime.fromisoformat(date_filter['start_date'])
                    if 'end_date' in date_filter:
                        datetime.fromisoformat(date_filter['end_date'])
                except ValueError:
                    return Response(
                        {'success': False, 'error': 'Invalid date format in date_filter'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            result = display_service.export_session_logs(
                export_format=export_format,
                date_filter=date_filter,
                status_filter=status_filter
            )

            if not result['success']:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if export_format == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = (
                    f'attachment; filename="session_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
                )
                fieldnames = [
                    'session_id', 'username', 'employee_name', 'branch_id',
                    'login_time', 'logout_time', 'session_duration', 'work_hours',
                    'status', 'source', 'role', 'logout_reason'
                ]
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                for row in result['data']:
                    writer.writerow(row)
                response.write(output.getvalue())
                return response

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in SessionExportView: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ================ ADMIN CONTROL VIEWS ================

class ForceLogoutView(APIView):
    """Force logout a specific session"""

    def post(self, request, session_id):
        try:
            session_service = SessionLogService()

            # Look up the session to get the username
            session = session_service.get_session_by_id(session_id)
            if not session:
                return Response(
                    {'success': False, 'message': f'Session {session_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            username = session.get('username')
            result = session_service.log_logout(username, reason="admin_forced")

            if result.get('success'):
                return Response({
                    'success': True,
                    'message': f'Session {session_id} (user: {username}) logged out successfully',
                    'duration': result.get('duration', 0),
                    'session_id': result.get('session_id')
                }, status=status.HTTP_200_OK)

            return Response(
                {'success': False, 'message': result.get('message', 'Failed to logout session')},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Error in ForceLogoutView: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkSessionControlView(APIView):
    """Bulk session operations"""

    def post(self, request):
        try:
            session_service = SessionLogService()
            action = request.data.get('action', 'expire')
            usernames = request.data.get('usernames', [])

            if not usernames or not isinstance(usernames, list):
                return Response(
                    {'success': False, 'error': 'usernames must be a non-empty list'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if action == 'expire':
                result = session_service.bulk_expire_user_sessions(usernames)
                return Response(result, status=status.HTTP_200_OK)

            return Response(
                {'success': False, 'error': 'Invalid action. Only "expire" is supported'},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Error in BulkSessionControlView: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ================ DISPLAY AND LOGGING VIEWS ================

class SessionDisplayView(APIView):
    """Get formatted session logs for display (alias for SessionLogsView)"""

    def get(self, request):
        try:
            display_service = SessionDisplayService()
            limit = int(request.query_params.get('limit', 100))
            status_filter = request.query_params.get('status', None)
            user_filter = request.query_params.get('user', None)

            result = display_service.get_session_logs(
                limit=limit,
                status_filter=status_filter,
                user_filter=user_filter
            )
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in SessionDisplayView: {e}")
            return Response(
                {'success': False, 'error': str(e), 'data': []},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CombinedLogsView(APIView):
    """Get both session and audit logs combined"""

    def get(self, request):
        try:
            display_service = SessionDisplayService()
            limit = min(int(request.query_params.get('limit', 100)), 500)
            log_type = request.query_params.get('type', 'all')

            if log_type not in ['all', 'session', 'audit']:
                return Response(
                    {'success': False, 'error': 'Invalid log type. Must be: all, session, or audit'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            result = display_service.get_combined_logs(limit=limit, log_type=log_type)
            return Response(result, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {'success': False, 'error': 'Invalid parameters provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in CombinedLogsView: {e}")
            return Response(
                {'success': False, 'error': str(e), 'data': []},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ================ SYSTEM STATUS VIEW ================

class SystemStatusView(APIView):
    """Get comprehensive system status"""

    def get(self, request):
        try:
            user_service = UserService()
            customer_service = CustomerService()
            product_service = ProductService()
            session_service = SessionLogService()

            session_stats = session_service.get_session_statistics()
            cleanup_status = session_service.get_cleanup_status()

            users = user_service.get_all_users()
            customers = customer_service.get_all_customers()
            products = product_service.get_all_products(include_images=False)

            return Response({
                "system": "PANN User Management System",
                "status": "operational",
                "version": "2.0.0",
                "timestamp": datetime.utcnow().isoformat(),
                "statistics": {
                    "total_users": len(users),
                    "total_customers": len(customers),
                    "total_products": len(products),
                    "active_sessions": session_stats.get('active_sessions', 0),
                    "today_sessions": session_stats.get('today_sessions', 0),
                    "avg_session_duration": session_stats.get('avg_session_duration', 0)
                },
                "cleanup_status": {
                    "automated_cleanup_running": cleanup_status.get('automated_cleanup_running', False),
                    "sessions_older_than_6_months": cleanup_status.get('sessions_older_than_6_months', 0),
                    "cleanup_schedule": cleanup_status.get('cleanup_schedule', 'Not scheduled')
                },
                "endpoints": {
                    "session_logs": "/api/v1/admin/sessions/",
                    "active_sessions": "/api/v1/admin/sessions/active/",
                    "session_cleanup": "/api/v1/admin/sessions/cleanup/",
                    "cleanup_status": "/api/v1/admin/sessions/cleanup/status/",
                    "session_export": "/api/v1/admin/sessions/export/",
                    "combined_logs": "/api/v1/admin/sessions/combined-logs/"
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in SystemStatusView: {e}")
            return Response({
                "system": "PANN User Management System",
                "status": "error",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

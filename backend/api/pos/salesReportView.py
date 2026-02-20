from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from app.services.analytics.salesReport import SalesReport
from datetime import datetime, date, timedelta, time
import logging

def get_authenticated_user_from_jwt(request):
    """Helper function to get authenticated user with proper username from JWT token"""
    try:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization.split(" ")[1]
        
        from app.services.identity.auth_services import AuthService
        
        
        auth_service = AuthService()
        user_data = auth_service.get_current_user(token)
        
        if not user_data:
            return None
        
        user_id = user_data.get('user_id')
        user_doc = auth_service.user_collection.find_one({"_id": user_id})
        
        if not user_doc:
            return None
        
        actual_username = user_doc.get('username')
        if actual_username and actual_username.strip():
            display_username = actual_username
        else:
            display_username = user_doc.get('email', 'unknown')
        
        return {
            "user_id": user_id,
            "username": display_username,
            "email": user_doc.get('email'),
            "branch_id": 1,
            "role": user_doc.get('role', 'employee'),
            "ip_address": request.META.get('REMOTE_ADDR'),
            "user_agent": request.META.get('HTTP_USER_AGENT')
        }
        
    except Exception as e:
        print(f"JWT Auth helper error: {e}")
        return None

# ================================================================
# CORE API VIEWS 
# ================================================================

class SalesSummaryView(APIView):
    """
    🎯 MAIN VIEW: Get sales summary with flexible filtering
    Replaces: DailyReports, WeeklyReports, MonthlyReports, etc.
    """
    def get(self,request):
        try:
            #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            sales_report = SalesReport()

            period = request.GET.get('period')
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            source = request.GET.get('source')

            date_range = None
            today = date.today()

            if period == 'today':
    
                date_range = {
                    'start': datetime.combine(today, datetime.min.time()),
                    'end':datetime.combine(today,datetime.max.time())
                }

            elif period == 'week':
                since_monday = today.weekday()
                start_of_week = today - timedelta(days = since_monday)
                end_of_week = start_of_week + timedelta(days=6)
                date_range = {
                    'start':datetime.combine(start_of_week,datetime.min.time()),
                    'end': datetime.combine(end_of_week,datetime.max.time())
                }

            elif period == 'month':
                start_of_month = date(today.year, today.month,1)
                if today.month == 12:
                    end_of_month = date(today.year + 1, 1, 1) - timedelta(days = 1)
                else:
                    end_of_month = date(today.year, today.month + 1, 1) - timedelta(days = 1)
                
                date_range = {
                    'start': datetime.combine(start_of_month, datetime.min.time()),
                    'end': datetime.combine(end_of_month, datetime.max.time())
                }

            elif period == 'year':
                start_of_year = date(today.year, 1, 1)
                end_of_year = date(today.year, 12, 31)
                date_range = {
                    'start': datetime.combine(start_of_year, datetime.min.time()),
                    'end': datetime.combine(end_of_year, datetime.max.time())
                }

            elif period == 'custom' and start_date and end_date:
                try:
                    # Parse the dates
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    
                    # If end_date is just a date (no time), set it to end of day
                    if end_dt.time() == time.min:  # If time is 00:00:00
                        end_dt = datetime.combine(end_dt.date(), time.max)  # Set to 23:59:59.999999
                        
                    date_range = {
                        'start': start_dt,
                        'end': end_dt
                    }
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use ISO format (YYYY-MM-DD)"},
                        status = status.HTTP_400_BAD_REQUEST
                    )
            include_source = None
            if source and source != 'all':
                if source == 'pos':
                    include_source =['pos']
                elif source == 'manual':
                    include_source = ['manual', 'csv']
                elif source in ['csv', 'manual', 'pos']:
                    include_source = [source]

            result = sales_report.get_sales_summary(date_range,include_source)

            return Response(result, status = status.HTTP_200_OK)
        
        except Exception as e:
            logging.error(f"Error getting the sales summary: {str(e)}")
            return Response(
                {"error": f"Error getting the sales summary: {str(e)}"},
                status = status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SalesByPeriodView(APIView):
    """
    📊 Get sales grouped by time periods
    For charts, trends, period analysis
    """

    def get(self,request):
        try:
            #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            sales_report = SalesReport()

            
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            period = request.GET.get('period', 'daily')
            source = request.GET.get('source')

            if not start_date or not end_date:
                return Response(
                    {"error": "start_date and end_date are required"},
                    status = status.HTTP_400_BAD_REQUEST
                )
            
            if period not in ['daily', 'weekly', 'monthly']:
                return Response(
                    {"error": "start_date and end_date are required"},
                    status = status.HTTP_400_BAD_REQUEST
                )

            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return Response(
                        {"error": "Invalid date format. Use ISO format (YYYY-MM-DD)"},
                        status = status.HTTP_400_BAD_REQUEST
                    )

            include_source = None
            if source and source != 'all':
                if source == 'pos':
                    include_source =['pos']
                elif source == 'manual':
                    include_source = ['manual', 'csv']
                elif source in ['csv', 'manual', 'pos']:
                    include_source = [source]

            result = sales_report.get_sales_by_period(start_dt, end_dt, period, include_source)

            return Response(result, status=status.HTTP_200_OK)
           
        except Exception as e:
            logging.error(f"Error getting sales by period: {str(e)}")
            return Response(
                {"error": f"Error getting sales by period: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DashboardSummaryView(APIView):
    """Get comprehensive dashboard data"""
    def get(self, request):
        try:
             #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            sales_report = SalesReport()
            result = sales_report.get_dashboard_summary()

            return Response(result, status = status.HTTP_200_OK)
        
        except Exception as e:
            logging.error(f"Error getting dashboard summary: {str(e)}")
            return Response(
                {"error": f"Error getting dashboard summary: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SalesComparisonView(APIView):
    """Get sales comparison between periods"""
    def get(self, request):
        try:
             #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            # ✅ FIXED: Get period from query params, not request.period
            period = request.GET.get('period', 'week')
            
            if period not in ['week', 'month']:
                return Response(
                    {"error": "Period must be 'week' or 'month'"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            sales_report = SalesReport()
            result = sales_report.get_sales_comparison(period)
                
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Error getting comparison report: {str(e)}")
            return Response(
                {"error": f"Error getting comparison report: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )    

class SalesTransactionsView(APIView):
    """
    📋 Get individual transaction records
    For exports, transaction lists, detailed data
    """
    def get(self, request):
        try:
             #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            sales_report = SalesReport()
            
            # Get parameters
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            source = request.GET.get('source')
            limit = int(request.GET.get('limit', 100))
            
            # Build date range
            date_range = None
            if start_date and end_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    date_range = {'start': start_dt, 'end': end_dt}
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use ISO format"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Build source filter
            include_source = None
            if source and source != 'all':
                if source == 'pos':
                    include_source = ['pos']
                elif source == 'manual':
                    include_source = ['manual', 'csv']
                elif source in ['csv', 'manual', 'pos']:
                    include_source = [source]
            
            # Get transactions using clean API
            result = sales_report.get_sales_transactions(date_range, include_source, limit)
            
            return Response(result, status=status.HTTP_200_OK)
           
        except Exception as e:
            logging.error(f"Error getting sales transactions: {str(e)}")
            return Response(
                {"error": f"Error getting sales transactions: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
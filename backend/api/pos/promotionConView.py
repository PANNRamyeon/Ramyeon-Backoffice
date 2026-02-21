from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from app.services.marketing.promotionCon import PromoConnection
from app.services.analytics.salesReport import SalesReport
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
# CORE POS TRANSACTION VIEWS
# ================================================================

class POSTransactionView(APIView):
    """Handle complete POS transactions with promotions and inventory management"""
    
    def post(self, request):
        """Process a complete POS transaction"""
        try:
            # Get authenticated user from JWT
            current_user = get_authenticated_user_from_jwt(request)
            
            if not current_user:
                return Response(
                    {"error": "Authentication required"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            promo_service = PromoConnection()
            
            # Extract required data
            checkout_data = request.data.get('checkout_data', [])
            promotion_name = request.data.get('promotion_name')
            cashier_id = current_user.get('user_id')  # Use authenticated user ID
            
            # Validate required fields
            if not checkout_data:
                return Response(
                    {"error": "Checkout data is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate checkout items
            for i, item in enumerate(checkout_data):
                if not all(key in item for key in ['product_id', 'quantity', 'price']):
                    return Response(
                        {"error": f"Item {i+1} missing required fields: product_id, quantity, price"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Process the transaction
            result = promo_service.pos_transaction(
                checkout_data=checkout_data,
                promotion_name=promotion_name,
                cashier_id=cashier_id
            )
            
            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logging.error(f"Error processing POS transaction: {str(e)}")
            return Response(
                {"error": f"Error processing transaction: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================================================================
# STOCK VALIDATION AND WARNING VIEWS
# ================================================================

class StockValidationView(APIView):
    """Validate stock availability before transaction"""
    
    def post(self, request):
        """Check if sufficient stock is available for checkout items"""
        try:
            promo_service = PromoConnection()
            checkout_data = request.data.get('checkout_data', [])
            
            if not checkout_data:
                return Response(
                    {"error": "Checkout data is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate stock
            validation_result = promo_service.validate_stock_availability(checkout_data)
            
            return Response({
                "success": True,
                "validation": validation_result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Error validating stock: {str(e)}")
            return Response(
                {"error": f"Error validating stock: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StockWarningsView(APIView):
    """Check for low stock warnings"""
    
    def post(self, request):
        """Get low stock warnings for checkout items"""
        try:
            # Get authenticated user from JWT
            current_user = get_authenticated_user_from_jwt(request)
            
            promo_service = PromoConnection()
            checkout_data = request.data.get('checkout_data', [])
            
            if not checkout_data:
                return Response(
                    {"error": "Checkout data is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get warnings
            warnings = promo_service.check_low_stock_warnings(checkout_data, current_user)
            
            return Response({
                "success": True,
                "warnings": warnings,
                "warnings_count": len(warnings)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Error checking stock warnings: {str(e)}")
            return Response(
                {"error": f"Error checking stock warnings: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get(self, request):
        """Get all products with low stock"""
        try:
            promo_service = PromoConnection()
            low_stock_products = promo_service.check_all_low_stock_products()
            
            return Response({
                "success": True,
                "low_stock_products": low_stock_products,
                "count": len(low_stock_products)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Error getting low stock products: {str(e)}")
            return Response(
                {"error": f"Error getting low stock products: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================================================================
# PROMOTION VIEWS
# ================================================================

class PromotionCheckoutView(APIView):
    """Handle promotion application to checkout - For preview only"""
    
    def post(self, request):
        """Apply promotion to checkout and calculate discounts (preview only)"""
        try:
            promo_service = PromoConnection()
            checkout_data = request.data.get('checkout_data', [])
            promotion_name = request.data.get('promotion_name')
            
            if not checkout_data:
                return Response(
                    {"error": "Checkout data is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not promotion_name:
                return Response(
                    {"error": "Promotion name is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Apply promotion (preview only - doesn't save transaction)
            result = promo_service.checkout_list(checkout_data, promotion_name)
            
            return Response({
                "success": True,
                "promotion_preview": result,
                "note": "This is a preview only. Use POSTransactionView to complete the transaction."
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Error applying promotion: {str(e)}")
            return Response(
                {"error": f"Error applying promotion: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================================================================
# KPI AND ANALYTICS VIEWS
# ================================================================

class POSTransactionKPIView(APIView):
    """Get POS transaction statistics using SalesReport service"""
    
    def get(self, request):
        try:
            sales_report = SalesReport()
            
            # Get comprehensive dashboard data
            dashboard = sales_report.get_dashboard_summary()
            today_data = sales_report.get_todays_sales()
            week_data = sales_report.get_weekly_sales()
            month_data = sales_report.get_monthly_sales()
            
            return Response({
                "success": True,
                "kpis": {
                    "today": {
                        "transactions": dashboard['today']['total_transactions'],
                        "revenue": dashboard['today']['total_revenue'],
                        "average_transaction": dashboard['today']['average_transaction']
                    },
                    "this_week": {
                        "transactions": dashboard['this_week']['total_transactions'],
                        "revenue": dashboard['this_week']['total_revenue'],
                        "average_transaction": dashboard['this_week']['average_transaction']
                    },
                    "this_month": {
                        "transactions": dashboard['this_month']['total_transactions'],
                        "revenue": dashboard['this_month']['total_revenue'],
                        "average_transaction": dashboard['this_month']['average_transaction']
                    },
                    "week_comparison": dashboard['week_vs_last_week'],
                    "source_breakdown": dashboard['source_breakdown_today']
                },
                "generated_at": dashboard['generated_at']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"POS Transaction KPI error: {str(e)}")
            return Response(
                {"error": f"Error getting POS KPIs: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class InventoryKPIView(APIView):
    """Get inventory statistics"""
    
    def get(self, request):
        try:
            promo_service = PromoConnection()
            low_stock_products = promo_service.check_all_low_stock_products()
            
            return Response({
                "success": True,
                "low_stock_count": len(low_stock_products),
                "low_stock_products": low_stock_products
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Inventory KPI error: {str(e)}")
            return Response(
                {"error": f"Error getting inventory KPIs: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StockAlertKPIView(APIView):
    """Get stock alert statistics"""
    
    def get(self, request):
        try:
            promo_service = PromoConnection()
            low_stock_products = promo_service.check_all_low_stock_products()
            
            # Calculate KPIs
            total_products = promo_service.products_collection.count_documents({"isDeleted": {"$ne": True}})
            out_of_stock = promo_service.products_collection.count_documents({
                "stock": {"$lte": 0},
                "isDeleted": {"$ne": True}
            })
            low_stock_count = len(low_stock_products)
            
            return Response({
                "success": True,
                "stock_health": {
                    "total_products": total_products,
                    "out_of_stock": out_of_stock,
                    "low_stock": low_stock_count,
                    "healthy_stock": total_products - low_stock_count - out_of_stock,
                    "stock_health_percentage": round(((total_products - low_stock_count) / total_products * 100), 2) if total_products > 0 else 0
                },
                "alerts": {
                    "critical": out_of_stock,
                    "warning": low_stock_count,
                    "total_alerts": out_of_stock + low_stock_count
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Stock Alert KPI error: {str(e)}")
            return Response(
                {"error": f"Error getting stock alert KPIs: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================================================================
# UTILITY VIEWS
# ================================================================

class POSHealthCheckView(APIView):
    """Check POS system health and database connections"""
    
    def get(self, request):
        try:
            # Test PromoConnection (inventory/products)
            promo_service = PromoConnection()
            product_count = promo_service.products_collection.count_documents({"isDeleted": {"$ne": True}})
            
            # Test SalesReport (sales data)
            sales_report = SalesReport()
            today_summary = sales_report.get_todays_sales()
            
            return Response({
                "success": True,
                "system_health": "healthy",
                "connections": {
                    "inventory_db": "connected",
                    "sales_db": "connected"
                },
                "stats": {
                    "total_products": product_count,
                    "today_transactions": today_summary['summary']['total_transactions'],
                    "today_revenue": today_summary['summary']['total_revenue']
                },
                "timestamp": today_summary.get('generated_at')
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"POS Health Check error: {str(e)}")
            return Response({
                "success": False,
                "system_health": "unhealthy",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
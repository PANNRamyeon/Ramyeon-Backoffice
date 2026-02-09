from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import logging

from ..services.pos.SalesService import SalesService

logger = logging.getLogger(__name__)

class CreateEnhancedPOSSaleView(APIView):
    """
    Create a new enhanced POS sale with FIFO batch deduction and loyalty points
    """
    def post(self, request):
        try:
            service = SalesService()
            sale_data = request.data
            cashier_id = sale_data.get('cashier_id')
            
            if not cashier_id:
                return Response(
                    {"error": "cashier_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = service.create_enhanced_pos_sale(sale_data, cashier_id)
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating enhanced POS sale: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetEnhancedSaleView(APIView):
    """
    Get enhanced sale details by sale ID
    """
    def get(self, request, sale_id):
        try:
            service = SalesService()
            sale = service.sales_collection.find_one({'_id': sale_id})
            
            if not sale:
                return Response(
                    {"error": "Sale not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Convert ObjectId to string for JSON serialization
            sale = service.convert_object_id(sale)
            
            return Response(sale, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting enhanced sale: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VoidEnhancedSaleView(APIView):
    """
    Void an enhanced POS sale and restore stock to batches
    """
    def post(self, request, sale_id):
        try:
            service = SalesService()
            voided_by = request.data.get('voided_by')
            reason = request.data.get('reason', 'Sale voided')
            
            if not voided_by:
                return Response(
                    {"error": "voided_by is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = service.void_enhanced_sale(sale_id, voided_by, reason)
            
            # Convert ObjectId to string for JSON serialization
            result = service.convert_object_id(result)
            
            return Response({
                "success": True,
                "message": "Sale voided successfully",
                "data": result
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error voiding enhanced sale: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ValidatePointsRedemptionView(APIView):
    """
    Validate loyalty points redemption before sale
    """
    def post(self, request):
        try:
            service = SalesService()
            customer_id = request.data.get('customer_id')
            points_to_redeem = request.data.get('points_to_redeem', 0)
            subtotal = request.data.get('subtotal')
            
            if not customer_id:
                return Response(
                    {"error": "customer_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if subtotal is None:
                return Response(
                    {"error": "subtotal is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = service.validate_points_redemption(
                customer_id, 
                points_to_redeem, 
                subtotal
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error validating points redemption: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CalculateLoyaltyPointsView(APIView):
    """
    Calculate loyalty points earned for a sale
    """
    def post(self, request):
        try:
            service = SalesService()
            subtotal_after_discount = request.data.get('subtotal_after_discount')
            
            if subtotal_after_discount is None:
                return Response(
                    {"error": "subtotal_after_discount is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            points = service.calculate_loyalty_points_earned(subtotal_after_discount)
            
            return Response({
                "loyalty_points_earned": points,
                "subtotal_after_discount": subtotal_after_discount
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error calculating loyalty points: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CalculatePointsDiscountView(APIView):
    """
    Calculate discount amount from loyalty points
    """
    def post(self, request):
        try:
            service = SalesService()
            points_to_redeem = request.data.get('points_to_redeem', 0)
            
            discount_amount = service.calculate_points_discount(points_to_redeem)
            
            return Response({
                "points_to_redeem": points_to_redeem,
                "discount_amount": round(discount_amount, 2)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error calculating points discount: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetCustomerEnhancedSalesView(APIView):
    """
    Get enhanced sales for a specific customer
    """
    def get(self, request, customer_id):
        try:
            service = SalesService()
            
            # Get enhanced sales for customer
            sales = list(service.sales_collection.find({
                'customer_id': customer_id,
                'source': 'pos'
            }).sort('transaction_date', -1))
            
            # Convert ObjectIds to strings
            sales = [service.convert_object_id(sale) for sale in sales]
            
            return Response({
                "customer_id": customer_id,
                "sales_count": len(sales),
                "sales": sales
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting customer enhanced sales: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetEnhancedSalesByDateRangeView(APIView):
    """
    Get enhanced sales within a date range
    """
    def get(self, request):
        try:
            service = SalesService()
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            
            if not start_date or not end_date:
                return Response(
                    {"error": "start_date and end_date are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse dates
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use ISO format"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            sales = service.get_sales_by_date_range(start_date, end_date, source='pos')
            
            return Response({
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "sales_count": len(sales),
                "sales": sales
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting enhanced sales by date range: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetEnhancedSalesSummaryView(APIView):
    """
    Get summary statistics for enhanced sales
    """
    def get(self, request):
        try:
            service = SalesService()
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            
            # Build date filter
            date_filter = {}
            if start_date and end_date:
                try:
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    date_filter = {
                        'transaction_date': {
                            '$gte': start_date,
                            '$lte': end_date
                        }
                    }
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use ISO format"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get sales with date filter
            query = {'source': 'pos', **date_filter}
            sales = list(service.sales_collection.find(query))
            
            # Calculate summary statistics
            total_sales = len(sales)
            total_amount = sum(sale.get('total_amount', 0) for sale in sales)
            total_points_earned = sum(sale.get('loyalty_points_earned', 0) for sale in sales)
            total_points_used = sum(sale.get('loyalty_points_used', 0) for sale in sales)
            voided_sales = len([s for s in sales if s.get('is_voided', False)])
            
            # Payment method breakdown
            payment_methods = {}
            for sale in sales:
                method = sale.get('payment_method', 'unknown')
                payment_methods[method] = payment_methods.get(method, 0) + 1
            
            return Response({
                "summary": {
                    "total_sales": total_sales,
                    "total_amount": round(total_amount, 2),
                    "average_sale_amount": round(total_amount / total_sales, 2) if total_sales > 0 else 0,
                    "total_loyalty_points_earned": total_points_earned,
                    "total_loyalty_points_used": total_points_used,
                    "voided_sales": voided_sales,
                    "void_rate": round((voided_sales / total_sales) * 100, 2) if total_sales > 0 else 0
                },
                "payment_methods": payment_methods,
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting enhanced sales summary: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetRecentEnhancedSalesView(APIView):
    """
    Get recent enhanced sales with pagination
    """
    def get(self, request):
        try:
            service = SalesService()
            limit = int(request.GET.get('limit', 10))
            offset = int(request.GET.get('offset', 0))
            
            # Get recent enhanced sales
            sales = list(service.sales_collection.find({
                'source': 'pos'
            }).sort('transaction_date', -1).skip(offset).limit(limit))
            
            # Convert ObjectIds to strings
            sales = [service.convert_object_id(sale) for sale in sales]
            
            # Get total count
            total_count = service.sales_collection.count_documents({'source': 'pos'})
            
            return Response({
                "sales": sales,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total_count": total_count,
                    "has_more": (offset + limit) < total_count
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting recent enhanced sales: {e}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

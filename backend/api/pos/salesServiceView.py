from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from app.services.sales.SalesService import SalesService
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
            "role": user_doc.get('role', 'dmina'),
            "ip_address": request.META.get('REMOTE_ADDR'),
            "user_agent": request.META.get('HTTP_USER_AGENT')
        }
        
    except Exception as e:
        print(f"JWT Auth helper error: {e}")
        return None

class SalesServiceView(APIView):
    
    def post(self,request):
        try:

            #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            sale_data = request.data.get('sale_data',{})
            source = request.data.get("source",'pos') 

            if not sale_data:
                return Response(
                    {"error": "Sale Data is required"},
                    status = status.HTTP_400_BAD_REQUEST
                )

            if 'total_amount' not in sale_data:
                return Response(
                    {"error": "Sale Data is required"},
                    status = status.HTTP_400_BAD_REQUEST
                )

            sales_service = SalesService()
            result = sales_service.create_unified_sale(sale_data,source)

            return Response(result, status = status.HTTP_201_CREATED)

        except Exception as e:
            logging.error(f"Error creating the sale: {str(e)}")
            return Response(
                {"error": f"Error creating the sale: {str(e)}"},
                status = status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CreatePOSSale(APIView):

    def post(self, request):
        try: 

            #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            sale_data = request.data

            if not sale_data:
                return Response(
                    {"error": "Sale Data is required"},
                    status = status.HTTP_400_BAD_REQUEST
                )

            required_fields = ['items','total_amount']
            for field in required_fields:
                if field not in sale_data:
                    return Response(
                        {"error": f"{field} is required"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            sales_service = SalesService()
            result = sales_service._create_pos_sale(sale_data)

            return Response(result, status = status.HTTP_200_OK)
        
        except Exception as e:
            logging.error(f"Error creating the sale: {str(e)}")
            return Response(
                {"error": f"Error creating the sale: {str(e)}"},
                status = status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class CreateSalesLog(APIView):
    
    def post(self,request):
        try: 

            #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            sale_data = request.data.get('sale_data',{})
            source = request.data.get("source",'pos') 

            if not sale_data:
                return Response(
                    {"error": "Sale Data is required"},
                    status = status.HTTP_400_BAD_REQUEST
                )

            sales_service = SalesService()
            result = sales_service._create_sales_log(sale_data,source)

            return Response(result, status = status.HTTP_200_OK)
        
        except Exception as e:
            logging.error(f"Error creating the sales log: {str(e)}")
            return Response(
                {"error": f"Error creating the sales log: {str(e)}"},
                status = status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetSaleID(APIView):

    def get(self, request, sale_id):
        try:
            #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            if not sale_id:
                return Response(
                    {"error": "Sale Data is required"},
                    status = status.HTTP_400_BAD_REQUEST
                )

            sales_service = SalesService()
            result = sales_service.get_pos_sale_by_id(sale_id)

            if result:
                return Response(result, status = status.HTTP_200_OK)
            else:
                return Response(result, status = status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logging.error(f"Error fetching data of ${sale_id}: {str(e)}")
            return Response(
                {"error": f"Error fetching data of ${sale_id}: {str(e)}"},
                status = status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FetchRecentSales(APIView):

    def get(self,request):
        try: 

            #current_user = get_authenticated_user_from_jwt(request)

           # if not current_user:
           #     return Response(
            #        {"error": "Authentication required"}, 
            #        status=status.HTTP_401_UNAUTHORIZED
            #    )

            limit = min(int(request.GET.get('limit', 10)), 50)  # Max 50 for safety
            
            sales_service = SalesService()
            result = sales_service.get_recent_sales(limit)
            
            return Response({
                "success": True,
                "data": result,
                "count": len(result),
                "limit_applied": limit
            }, status=status.HTTP_200_OK)
            
        except ValueError:  # Handle invalid limit values
            limit = 10
            sales_service = SalesService()
            result = sales_service.get_recent_sales(limit)
            

            return Response(result, status = status.HTTP_200_OK)
        
        except Exception as e:
            logging.error(f"Error Fetching recent sales: {str(e)}")
            return Response(
                {"error": f"Error Fetching recent sales: {str(e)}"},
                status = status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VoidSale(APIView):

    def post(self, request, sale_id):
        try:
            if not sale_id:
                return Response(
                    {"error": "Sale ID is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            sales_service = SalesService()
            result = sales_service.void_sale(sale_id)

            if result:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": f"Sale {sale_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            logging.error(f"Error voiding sale {sale_id}: {str(e)}")
            return Response(
                {"error": f"Error voiding sale: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetSaleReceipt(APIView):

    def get(self, request, sale_id):
        try:
            if not sale_id:
                return Response(
                    {"error": "Sale ID is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            sales_service = SalesService()
            result = sales_service.get_sale_receipt(sale_id)

            if result:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": f"Sale {sale_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            logging.error(f"Error fetching receipt for sale {sale_id}: {str(e)}")
            return Response(
                {"error": f"Error fetching receipt: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
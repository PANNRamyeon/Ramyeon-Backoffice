from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.customer_service import CustomerService
from ..services.auth_services import AuthService
from ..decorators.authenticationDecorator import require_admin, require_authentication, get_authenticated_user_from_jwt
import logging

logger = logging.getLogger(__name__)

class CustomerRegisterView(APIView):
    """Public endpoint for customer self-registration."""

    def __init__(self):
        self.customer_service = CustomerService()
        self.auth_service = AuthService()

    def post(self, request):
        try:
            data = request.data or {}
            email = (data.get('email') or '').strip().lower()
            password = data.get('password') or ''
            if not email or not password:
                return Response(
                    {'error': 'Email and password are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            customer = self.customer_service.register_customer({
                'email': email,
                'password': password,
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
                'phone': data.get('phone', ''),
                'delivery_address': data.get('delivery_address', {}),
                'source': data.get('source', 'web')
            })

            customer_id = customer.get('_id')
            token_data = {
                'sub': str(customer_id),
                'email': customer.get('email'),
                'role': 'customer'
            }
            access_token = self.auth_service.create_access_token(token_data)
            refresh_token = self.auth_service.create_refresh_token(token_data)

            sanitized = {
                'id': str(customer_id),
                'email': customer.get('email'),
                'username': customer.get('username'),
                'full_name': customer.get('full_name'),
                'first_name': (data.get('first_name') or '').strip(),
                'last_name': (data.get('last_name') or '').strip(),
                'phone': customer.get('phone', ''),
                'loyalty_points': customer.get('loyalty_points', 0),
                'email_verified': customer.get('email_verified', False),
                'auth_mode': customer.get('auth_mode', 'password'),
            }

            return Response(
                {
                    'message': 'Account created successfully. Please verify your email address.',
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'bearer',
                    'user': sanitized,
                    'customer': sanitized,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            logger.warning(f"Customer registration validation error: {exc}")
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"Customer registration error: {exc}")
            return Response({'error': 'Registration failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerLoginView(APIView):
    """Customer login using email/password; returns JWT compatible with auth decorator."""
    def __init__(self):
        self.customer_service = CustomerService()
        self.auth_service = AuthService()

    def post(self, request):
        try:
            email = request.data.get('email')
            password = request.data.get('password')

            if not email or not password:
                return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

            customer = self.customer_service.authenticate_customer(email, password)
            if not customer:
                return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

            customer_id = str(customer.get('_id'))
            token_data = {"sub": customer_id, "email": customer.get('email'), "role": "customer"}
            access_token = self.auth_service.create_access_token(token_data)
            refresh_token = self.auth_service.create_refresh_token(token_data)

            sanitized = {
                "id": customer_id,
                "email": customer.get('email'),
                "username": customer.get('username'),
                "full_name": customer.get('full_name'),
                "loyalty_points": customer.get('loyalty_points', 0),
                "role": "customer",
            }

            return Response({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": sanitized
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Customer login error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomerRegisterView(APIView):
    """Public endpoint to register a new customer"""
    def __init__(self):
        self.customer_service = CustomerService()

    def post(self, request):
        try:
            payload = request.data or {}
            customer = self.customer_service.register_customer(payload)

            customer_sanitized = dict(customer)
            customer_sanitized.pop("password", None)

            return Response(
                {
                    "success": True,
                    "customer": customer_sanitized,
                    "message": "Account created successfully. Please verify your email to activate loyalty benefits.",
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as validation_error:
            return Response(
                {"error": str(validation_error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"Customer registration error: {exc}")
            return Response(
                {"error": "Unable to complete registration at this time."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class CustomerCurrentUserView(APIView):
    """Return current authenticated customer profile using JWT"""
    def __init__(self):
        self.customer_service = CustomerService()

    @require_authentication
    def get(self, request):
        try:
            user_ctx = getattr(request, 'current_user', None) or {}
            customer_id = user_ctx.get('user_id')
            if not customer_id:
                return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

            customer = self.customer_service.get_customer_by_id(customer_id)
            if not customer:
                return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

            # Sanitize
            customer_data = dict(customer)
            customer_data.pop('password', None)

            return Response({
                "success": True,
                "customer": customer_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Customer me error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomerListView(APIView):
    def __init__(self):
        self.customer_service = CustomerService()

     
    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            limit = int(request.query_params.get('limit', 50))
            status_filter = request.query_params.get('status')
            min_loyalty_points = request.query_params.get('min_loyalty_points')
            max_loyalty_points = request.query_params.get('max_loyalty_points')  # NEW
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            sort_by = request.query_params.get('sort_by')
            search = request.query_params.get('search')

            if min_loyalty_points:
                min_loyalty_points = int(min_loyalty_points)

            if max_loyalty_points:
                max_loyalty_points = int(max_loyalty_points)  # NEW

            result = self.customer_service.get_customers(
                page=page,
                limit=limit,
                status=status_filter,
                min_loyalty_points=min_loyalty_points,
                max_loyalty_points=max_loyalty_points,  # NEW
                include_deleted=include_deleted,
                sort_by=sort_by,
                search=search
            )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting customers: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    @require_authentication
    def post(self, request):
        """Create new customer - Authenticated users can create customers"""
        try:
            customer_data = request.data
            new_customer = self.customer_service.create_customer(
                customer_data, 
                request.current_user  # Set by decorator
            )
            
            return Response(new_customer, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class CustomerDetailView(APIView):
    def __init__(self):
        self.customer_service = CustomerService()

    @require_authentication
    def get(self, request, customer_id):
        """Get customer by ID - Authentication required"""
        try:
            customer = self.customer_service.get_customer_by_id(customer_id)
            if customer:
                return Response(customer, status=status.HTTP_200_OK)
            return Response(
                {"error": "Customer not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting customer {customer_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @require_authentication
    def put(self, request, customer_id):
        """Update customer - Authentication required"""
        try:
            customer_data = request.data
            updated_customer = self.customer_service.update_customer(
                customer_id, 
                customer_data, 
                request.current_user  # Set by decorator
            )
            
            if updated_customer:
                return Response(updated_customer, status=status.HTTP_200_OK)
            return Response(
                {"error": "Customer not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating customer {customer_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @require_authentication
    def delete(self, request, customer_id):
        """Delete customer - Admin only"""
        try:
            deleted = self.customer_service.soft_delete_customer(
                customer_id, 
                request.current_user
            )
            
            print(f"Delete result: {deleted}")
            
            if deleted:
                return Response(
                    {"message": "Customer deleted successfully"}, 
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": "Customer not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Exception in delete: {e}")
            logger.error(f"Error deleting customer {customer_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomerRestoreView(APIView):
    """View for restoring soft-deleted customers"""
    def __init__(self):
        self.customer_service = CustomerService()

    @require_admin
    def post(self, request, customer_id):
        """Restore a soft-deleted customer - Admin only"""
        try:
            restored = self.customer_service.restore_customer(
                customer_id, 
                request.current_user
            )
            
            if restored:
                return Response(
                    {"message": "Customer restored successfully"},
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": "Customer not found or not deleted"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Error restoring customer {customer_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomerHardDeleteView(APIView):
    """View for permanently deleting customers"""
    def __init__(self):
        self.customer_service = CustomerService()

    @require_admin
    def delete(self, request, customer_id):
        """PERMANENTLY delete customer - Admin only with confirmation"""
        try:
            confirm = request.query_params.get('confirm', '').lower()
            if confirm != 'yes':
                return Response({
                    "error": "Permanent deletion requires confirmation", 
                    "message": "Add ?confirm=yes to permanently delete this customer"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            deleted = self.customer_service.hard_delete_customer(
                customer_id, 
                request.current_user,
                confirmation_token="PERMANENT_DELETE_CONFIRMED"  # Add this
            )
            
            if deleted:
                return Response({
                    "message": "Customer permanently deleted"
                }, status=status.HTTP_200_OK)
            return Response(
                {"error": "Customer not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Error permanently deleting customer {customer_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomerSearchView(APIView):
    """View for searching customers"""
    def __init__(self):
        self.customer_service = CustomerService()

    @require_authentication
    def get(self, request):
        """Search customers by name, email, or phone"""
        try:
            search_term = request.query_params.get('q', '').strip()
            if not search_term:
                return Response(
                    {"error": "Search term 'q' parameter is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            customers = self.customer_service.search_customers(search_term)
            return Response(customers, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error searching customers: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomerByEmailView(APIView):
    """View for getting customer by email"""
    def __init__(self):
        self.customer_service = CustomerService()
        
    @require_authentication
    def get(self, request, email):
        """Get customer by email"""
        try:
            customer = self.customer_service.get_customer_by_email(email)
            if customer:
                return Response(customer, status=status.HTTP_200_OK)
            return Response(
                {"error": "Customer not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting customer by email {email}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomerStatisticsView(APIView):
    """View for customer statistics and analytics"""
    def __init__(self):
        self.customer_service = CustomerService()

    @require_authentication
    def get(self, request):
        """Get customer statistics"""
        try:
            stats = self.customer_service.get_customer_statistics()
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting customer statistics: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomerLoyaltyView(APIView):
    """View for managing customer loyalty points"""
    def __init__(self):
        self.customer_service = CustomerService()

    @require_authentication
    def post(self, request, customer_id):
        """Update customer loyalty points"""
        try:
            points_to_add = request.data.get('points', 0)
            reason = request.data.get('reason', 'Manual adjustment')
            
            if not isinstance(points_to_add, (int, float)) or points_to_add <= 0:
                return Response(
                    {"error": "Points must be a positive number"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            updated_customer = self.customer_service.update_loyalty_points(
                customer_id, 
                points_to_add, 
                reason, 
                request.current_user
            )
            
            if updated_customer:
                return Response(updated_customer, status=status.HTTP_200_OK)
            return Response(
                {"error": "Customer not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"Error updating loyalty points for customer {customer_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


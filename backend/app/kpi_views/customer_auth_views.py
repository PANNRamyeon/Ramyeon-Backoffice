# Customer Authentication Views
# Provides customer login, registration, and authentication endpoints
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
import jwt
from datetime import datetime, timedelta
import logging

from ..services.customer_service import CustomerService
from ..services.session_services import SessionLogService

logger = logging.getLogger(__name__)

class CustomerLoginView(APIView):
    """Customer login endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            email = request.data.get('email', '').strip().lower()
            password = request.data.get('password', '')
            
            if not email or not password:
                return Response({
                    'success': False,
                    'error': 'Email and password are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Authenticate customer using CustomerService
            customer_service = CustomerService()
            customer = customer_service.authenticate_customer(email, password)
            
            if not customer:
                return Response({
                    'success': False,
                    'error': 'Invalid email or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Generate JWT token
            token_payload = {
                'customer_id': customer['_id'],
                'email': customer['email'],
                'username': customer['username'],
                'exp': datetime.utcnow() + timedelta(days=7)
            }
            
            token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm='HS256')
            
            # Create session
            session_service = SessionLogService()
            session_data = {
                'user_id': customer['_id'],
                'username': customer['username'],
                'email': customer['email'],
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT')
            }
            session = session_service.log_login(session_data)
            
            # Return success response
            return Response({
                'success': True,
                'message': 'Login successful',
                'token': token,
                'customer': {
                    'id': customer['_id'],
                    'email': customer['email'],
                    'username': customer['username'],
                    'full_name': customer['full_name'],
                    'loyalty_points': customer.get('loyalty_points', 0),
                    'phone': customer.get('phone', ''),
                    'delivery_address': customer.get('delivery_address', {})
                },
                'session_id': session.get('_id') if session else None
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Customer login error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Login failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomerRegisterView(APIView):
    """Customer registration endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Extract registration data
            customer_data = {
                'email': request.data.get('email', '').strip().lower(),
                'password': request.data.get('password', ''),
                'username': request.data.get('username', '').strip(),
                'full_name': request.data.get('full_name', '').strip(),
                'phone': request.data.get('phone', '').strip(),
                'delivery_address': request.data.get('delivery_address', {})
            }
            
            # Validate required fields
            required_fields = ['email', 'password', 'username', 'full_name']
            for field in required_fields:
                if not customer_data.get(field):
                    return Response({
                        'success': False,
                        'error': f'{field.replace("_", " ").title()} is required'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate password strength
            if len(customer_data['password']) < 6:
                return Response({
                    'success': False,
                    'error': 'Password must be at least 6 characters long'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create customer using CustomerService
            customer_service = CustomerService()
            customer = customer_service.create_customer(customer_data)
            
            # Generate JWT token
            token_payload = {
                'customer_id': customer['_id'],
                'email': customer['email'],
                'username': customer['username'],
                'exp': datetime.utcnow() + timedelta(days=7)
            }
            
            token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm='HS256')
            
            # Create session
            session_service = SessionLogService()
            session_data = {
                'user_id': customer['_id'],
                'username': customer['username'],
                'email': customer['email'],
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT')
            }
            session = session_service.log_login(session_data)
            
            # Return success response
            return Response({
                'success': True,
                'message': 'Registration successful',
                'token': token,
                'customer': {
                    'id': customer['_id'],
                    'email': customer['email'],
                    'username': customer['username'],
                    'full_name': customer['full_name'],
                    'loyalty_points': customer.get('loyalty_points', 0),
                    'phone': customer.get('phone', ''),
                    'delivery_address': customer.get('delivery_address', {})
                },
                'session_id': session.get('_id') if session else None
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Customer registration error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Registration failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomerLogoutView(APIView):
    """Customer logout endpoint"""
    
    def post(self, request):
        try:
            # Extract customer ID from JWT token
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return Response({
                    'success': False,
                    'error': 'Authorization token required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                # Support both 'customer_id' (regular login) and 'sub' (OAuth login)
                customer_id = payload.get('customer_id') or payload.get('sub')
            except jwt.ExpiredSignatureError:
                return Response({
                    'success': False,
                    'error': 'Token expired'
                }, status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({
                    'success': False,
                    'error': 'Invalid token'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Log logout
            session_service = SessionLogService()
            session_service.log_logout(customer_id, "user_logout")
            
            return Response({
                'success': True,
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Customer logout error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Logout failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomerProfileView(APIView):
    """Get customer profile endpoint"""
    
    def get(self, request):
        try:
            # Extract customer ID from JWT token
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return Response({
                    'success': False,
                    'error': 'Authorization token required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                # Support both 'customer_id' (regular login) and 'sub' (OAuth login)
                customer_id = payload.get('customer_id') or payload.get('sub')
            except jwt.ExpiredSignatureError:
                return Response({
                    'success': False,
                    'error': 'Token expired'
                }, status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({
                    'success': False,
                    'error': 'Invalid token'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get customer data
            customer_service = CustomerService()
            customer = customer_service.get_customer_by_id(customer_id)
            
            if not customer:
                return Response({
                    'success': False,
                    'error': 'Customer not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Return customer profile (without password)
            return Response({
                'success': True,
                'customer': {
                    'id': customer['_id'],
                    'email': customer['email'],
                    'username': customer['username'],
                    'full_name': customer['full_name'],
                    'loyalty_points': customer.get('loyalty_points', 0),
                    'phone': customer.get('phone', ''),
                    'delivery_address': customer.get('delivery_address', {}),
                    'status': customer.get('status', 'active'),
                    'date_created': customer.get('date_created'),
                    'last_updated': customer.get('last_updated')
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Get customer profile error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to get profile'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomerUpdateProfileView(APIView):
    """Update customer profile endpoint"""
    
    def put(self, request):
        try:
            # Extract customer ID from JWT token
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return Response({
                    'success': False,
                    'error': 'Authorization token required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                # Support both 'customer_id' (regular login) and 'sub' (OAuth login)
                customer_id = payload.get('customer_id') or payload.get('sub')
            except jwt.ExpiredSignatureError:
                return Response({
                    'success': False,
                    'error': 'Token expired'
                }, status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({
                    'success': False,
                    'error': 'Invalid token'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Update customer data
            customer_service = CustomerService()
            update_data = {
                'full_name': request.data.get('full_name', '').strip(),
                'phone': request.data.get('phone', '').strip(),
                'delivery_address': request.data.get('delivery_address', {})
            }
            
            # Remove empty fields
            update_data = {k: v for k, v in update_data.items() if v}
            
            if not update_data:
                return Response({
                    'success': False,
                    'error': 'No data to update'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            updated_customer = customer_service.update_customer(customer_id, update_data)
            
            if not updated_customer:
                return Response({
                    'success': False,
                    'error': 'Customer not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Return updated customer profile
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'customer': {
                    'id': updated_customer['_id'],
                    'email': updated_customer['email'],
                    'username': updated_customer['username'],
                    'full_name': updated_customer['full_name'],
                    'loyalty_points': updated_customer.get('loyalty_points', 0),
                    'phone': updated_customer.get('phone', ''),
                    'delivery_address': updated_customer.get('delivery_address', {}),
                    'status': updated_customer.get('status', 'active'),
                    'last_updated': updated_customer.get('last_updated')
                }
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Update customer profile error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to update profile'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomerChangePasswordView(APIView):
    """Change customer password endpoint"""
    
    def post(self, request):
        try:
            # Extract customer ID from JWT token
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return Response({
                    'success': False,
                    'error': 'Authorization token required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                # Support both 'customer_id' (regular login) and 'sub' (OAuth login)
                customer_id = payload.get('customer_id') or payload.get('sub')
            except jwt.ExpiredSignatureError:
                return Response({
                    'success': False,
                    'error': 'Token expired'
                }, status=status.HTTP_401_UNAUTHORIZED)
            except jwt.InvalidTokenError:
                return Response({
                    'success': False,
                    'error': 'Invalid token'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get password data
            old_password = request.data.get('old_password', '')
            new_password = request.data.get('new_password', '')
            
            if not old_password or not new_password:
                return Response({
                    'success': False,
                    'error': 'Old password and new password are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if len(new_password) < 6:
                return Response({
                    'success': False,
                    'error': 'New password must be at least 6 characters long'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Change password
            customer_service = CustomerService()
            success = customer_service.change_customer_password(customer_id, old_password, new_password)
            
            if not success:
                return Response({
                    'success': False,
                    'error': 'Failed to change password'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Change password error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to change password'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

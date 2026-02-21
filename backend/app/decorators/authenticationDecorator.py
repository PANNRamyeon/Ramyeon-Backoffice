from rest_framework.response import Response
from rest_framework import status
from ..services.identity.auth_services import AuthService
from models.Users import User
from models.Customers import Customer
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def get_authenticated_user_from_jwt(request):
    """Unified JWT authentication helper for all systems (users and customers)."""
    try:
        if not hasattr(request, 'headers'):
            logger.error(f"Request object missing headers attribute: {type(request)}")
            return None

        authorization = request.headers.get("Authorization", "")
        logger.info(f"Authorization header received: {authorization[:50]}..." if len(authorization) > 50 else f"Authorization header: {authorization}")
        
        if not authorization.startswith("Bearer "):
            logger.warning(f"Authorization header does not start with 'Bearer ': {authorization[:30]}")
            return None

        token = authorization.split(" ", 1)[1]
        
        # Clean up any accidental "Bearer " prefix in the token itself
        if token.startswith("Bearer "):
            logger.warning("Token has extra 'Bearer ' prefix, removing it")
            token = token.replace("Bearer ", "", 1)
        
        logger.info(f"Token extracted, length: {len(token)}")

        auth_service = AuthService()
        payload = auth_service.verify_token(token)
        
        if not payload:
            logger.warning("Token verification failed - payload is None")
            return None
        
        # Check if it's an access token (not refresh token)
        if payload.get("type") != "access":
            logger.warning(f"Invalid token type: {payload.get('type')} (expected 'access')")
            return None

        logger.info(f"Token verified successfully, payload: {payload}")
        
        user_id = payload.get('sub')
        role = (payload.get('role') or '').lower()

        logger.info(f"Attempting to fetch user: {user_id}, role: {role}")

        # Try to get user from DynamoDB
        user_doc = None
        try:
            # Try admin/user first using PynamoDB
            logger.info(f"Looking up user in users table: {user_id}")
            user = User.get("users", user_id)
            if user:
                user_doc = user.to_dict()
                logger.info(f"User found in users table: {user_doc.get('email')}")
        except User.DoesNotExist:
            logger.info(f"User {user_id} not found in users table, trying customers")
        except Exception as e:
            logger.error(f"User lookup error: {e}", exc_info=True)

        if not user_doc:
            # Fallback to customers for customer tokens
            try:
                logger.info(f"Looking up customer: {user_id}")
                customer = Customer.get_by_id(user_id)
                if customer:
                    user_doc = customer.to_dict()
                    logger.info(f"Customer found: {user_doc.get('email')}")
            except Exception as e:
                logger.error(f"Customer lookup failed: {e}", exc_info=True)
                user_doc = None

        if not user_doc:
            logger.warning(f"User/Customer not found in database: {user_id}")
            return None

        username = (user_doc.get('username') or '').strip()
        display_username = username or user_doc.get('email', 'unknown')

        result = {
            "user_id": user_id,
            "username": display_username,
            "email": user_doc.get('email'),
            "branch_id": user_doc.get('branch_id', 1),
            "role": user_doc.get('role', role or 'customer')
        }
        
        logger.info(f"Authentication successful for user: {display_username}")
        return result

    except Exception as e:
        logger.error(f"JWT authentication error: {e}", exc_info=True)
        return None

def require_authentication(view_func):
    """Unified authentication decorator"""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # Handle both function-based and class-based views
        if len(args) >= 2:
            request = args[1]  # Class-based view
        elif len(args) == 1:
            request = args[0]  # Function-based view
        else:
            request = kwargs.get('request')
            
        if not request or not hasattr(request, 'headers'):
            return Response(
                {"error": "Invalid request"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        current_user = get_authenticated_user_from_jwt(request)
        if not current_user:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Set user data in multiple formats for compatibility
        request.current_user = current_user
        request.user_context = current_user  # For new promotion system
        
        return view_func(*args, **kwargs)
    return wrapper

def require_admin(view_func):
    """Unified admin authentication decorator"""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if len(args) >= 2:
            request = args[1]
        elif len(args) == 1:
            request = args[0]
        else:
            request = kwargs.get('request')
            
        if not request or not hasattr(request, 'headers'):
            return Response(
                {"error": "Invalid request"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        current_user = get_authenticated_user_from_jwt(request)
        if not current_user:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if current_user.get('role', '').lower() != 'admin':
            return Response(
                {"error": "Admin permissions required"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Set user data in multiple formats for compatibility
        request.current_user = current_user
        request.user_context = current_user
        
        return view_func(*args, **kwargs)
    return wrapper

def require_permission(*allowed_roles):
    """Unified permission-based authentication decorator"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if len(args) >= 2:
                request = args[1]
            elif len(args) == 1:
                request = args[0]
            else:
                request = kwargs.get('request')
                
            if not request or not hasattr(request, 'headers'):
                return Response(
                    {"error": "Invalid request"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            current_user = get_authenticated_user_from_jwt(request)
            if not current_user:
                return Response(
                    {"error": "Authentication required"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            user_role = current_user.get('role', '').lower()
            allowed = [role.lower() for role in allowed_roles]
            
            if user_role not in allowed:
                return Response(
                    {"error": f"Requires one of: {', '.join(allowed_roles)}"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Set user data in multiple formats for compatibility
            request.current_user = current_user
            request.user_context = current_user
            
            return view_func(*args, **kwargs)
        return wrapper
    return decorator

# Convenience aliases for different naming conventions
jwt_required = require_authentication
admin_required = require_admin
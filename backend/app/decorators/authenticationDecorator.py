from rest_framework.response import Response
from rest_framework import status
from ..services.auth_services import AuthService
from ..database import db_manager
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
        if not authorization.startswith("Bearer "):
            return None

        token = authorization.split(" ", 1)[1]

        auth_service = AuthService()
        payload = auth_service.verify_token(token)
        if not payload:
            return None

        user_id = payload.get('sub')
        role = (payload.get('role') or '').lower()

        # Try admin/user collection first
        user_doc = auth_service.user_collection.find_one({"_id": user_id}) if user_id else None

        if not user_doc:
            # Fallback to customers collection for customer tokens
            try:
                db = db_manager.get_database()
                customers = db.customers
                user_doc = customers.find_one({"_id": user_id}) if user_id else None
            except Exception as e:
                logger.error(f"Customer lookup failed: {e}")
                user_doc = None

        if not user_doc:
            return None

        username = (user_doc.get('username') or '').strip()
        display_username = username or user_doc.get('email', 'unknown')

        return {
            "user_id": user_id,
            "username": display_username,
            "email": user_doc.get('email'),
            "branch_id": user_doc.get('branch_id', 1),
            "role": user_doc.get('role', role or 'customer')
        }

    except Exception as e:
        logger.error(f"JWT authentication error: {e}")
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
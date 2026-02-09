from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .services.auth_services import AuthService
import json

class JWTAuthenticationMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.auth_service = AuthService()
        
        # Define protected paths
        self.protected_paths = [
            '/api/v1/auth/me/',
            '/api/v1/auth/logout/',
            '/api/v1/users/',  # Protect user management
            '/api/v1/session-logs/', # Protect session logs
            '/api/v1/category/',  
        ]
        
        # Define public paths (allowed without authentication)
        self.public_paths = [
            '/api/v1/',  # System status
            '/api/v1/health/',
            '/api/v1/auth/login/',
            '/api/v1/auth/refresh/',
            '/api/v1/auth/verify-token/',
            '/api/v1/customers/',
            '/api/v1/products/import/template/',
        ]

    def process_request(self, request):
        # Skip authentication for public paths
        if any(request.path.startswith(path) for path in self.public_paths):
            return None
        
        # Skip authentication for non-protected paths
        if not any(request.path.startswith(path) for path in self.protected_paths):
            return None
        
        # Get authorization header
        authorization = request.META.get('HTTP_AUTHORIZATION')
        
        if not authorization or not authorization.startswith('Bearer '):
            return JsonResponse({
                'error': 'Missing or invalid authorization header',
                'code': 'UNAUTHORIZED'
            }, status=401)
        
        try:
            token = authorization.split(' ')[1]
            payload = self.auth_service.verify_token(token)
            
            if not payload:
                return JsonResponse({
                    'error': 'Invalid or expired token',
                    'code': 'INVALID_TOKEN'
                }, status=401)
            
            # Add user info to request
            request.user_id = payload.get('sub')
            request.user_email = payload.get('email')
            request.user_role = payload.get('role')
            
        except Exception as e:
            return JsonResponse({
                'error': 'Token verification failed',
                'code': 'TOKEN_ERROR'
            }, status=401)
        
        return None

class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all API requests for audit purposes"""
    
    def process_request(self, request):
        # Log API requests (you can save to database)
        if request.path.startswith('/api/v1/'):
            print(f"API Request: {request.method} {request.path} from {request.META.get('REMOTE_ADDR')}")
        return None

class ErrorHandlingMiddleware(MiddlewareMixin):
    """Handle errors gracefully"""
    
    def process_exception(self, request, exception):
        if request.path.startswith('/api/v1/'):
            return JsonResponse({
                'error': 'Internal server error',
                'message': str(exception),
                'code': 'INTERNAL_ERROR'
            }, status=500)
        return None
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services.identity.user_service import UserService
from app.decorators.authenticationDecorator import require_admin, require_authentication, require_permission, get_authenticated_user_from_jwt
from app.serializers import UserCreateSerializer
import logging

logger = logging.getLogger(__name__)

# ================================================================
# VIEW CLASSES
# ================================================================

class HealthCheckView(APIView):
    def get(self, request):
        return Response({
            "message": "User Management API is running!",
            "status": "active",
            "version": "1.0.0"
        }, status=status.HTTP_200_OK)

class UserListView(APIView):
    def __init__(self):
        self.user_service = UserService()
    
    
    def get(self, request):
        """Get users with pagination and filters"""
        try:
            page = int(request.query_params.get('page', 1))
            limit = int(request.query_params.get('limit', 50))

            status_filter = request.query_params.get('status')
            role_filter = request.query_params.get('role')
            search_query = request.query_params.get('search')
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'

            # Only admins can view deleted users
            if include_deleted and request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required to view deleted users"},
                    status=status.HTTP_403_FORBIDDEN
                )

            result = self.user_service.get_users(
                page=page,
                limit=limit,
                status=status_filter,
                role=role_filter,
                search=search_query,
                include_deleted=include_deleted
            )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    
    def post(self, request):
        """Create new user – Admin only"""
        try:
            # Only admins can create users
            if request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required to create users"},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = UserCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Validation failed", "details": serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            current_user = getattr(request, 'current_user', None)
            new_user = self.user_service.create_user(serializer.validated_data, current_user)
            return Response(new_user, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class UserDetailView(APIView):
    def __init__(self):
        super().__init__()
        self.user_service = UserService()

    
    def get(self, request, user_id):
        """Get user by ID (with optional deleted users for admin)"""
        try:
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            
            # Only admins can view deleted users
            if include_deleted and request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required to view deleted users"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user = self.user_service.get_user_by_id(user_id, include_deleted=include_deleted)
            if not user:
                return Response(
                    {"error": "User not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(user, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    def put(self, request, user_id):
        """Update user – Admin only OR self‑service password change"""
        try:
            current_user = request.current_user
            
            # Determine role context
            if current_user.get('user_id') == user_id:
                # Self-service: only password changes
                if set(request.data.keys()) - {'password'}:
                    return Response(
                        {"error": "You can only update your own password"}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
                role_context = 'self_service'
            else:
                # Admin updating another user
                if current_user.get('role', '').lower() != 'admin':
                    return Response(
                        {"error": "Admin permissions required"}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
                role_context = 'admin'
            
            updated_user = self.user_service.update_user_profile(
                user_id, 
                request.data, 
                current_user, 
                role_context
            )
            
            if not updated_user:
                return Response(
                    {"error": "User not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(updated_user, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    
    def delete(self, request, user_id):
        """Soft delete user – Admin only"""
        try:
            # Only admins can soft delete users
            if request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required to delete users"},
                    status=status.HTTP_403_FORBIDDEN
                )

            deleted = self.user_service.soft_delete_user(user_id, request.current_user)
            
            if not deleted:
                return Response(
                    {"error": "User not found or already deleted"},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"message": "User deleted successfully"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserRestoreView(APIView):
    """View for restoring soft-deleted users"""
    def __init__(self):
        super().__init__()
        self.user_service = UserService()

    
    def post(self, request, user_id):
        """Restore a soft‑deleted user – Admin only"""
        try:
            # Only admins can restore users
            if request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required to restore users"},
                    status=status.HTTP_403_FORBIDDEN
                )

            restored = self.user_service.restore_user(user_id, request.current_user)
            
            if not restored:
                return Response(
                    {"error": "User not found or not deleted"},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"message": "User restored successfully"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error restoring user {user_id}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserHardDeleteView(APIView):
    """View for permanently deleting users (DANGEROUS) – Admin only"""
    def __init__(self):
        super().__init__()
        self.user_service = UserService()

    
    def delete(self, request, user_id):
        """PERMANENTLY delete user – Admin only with confirmation"""
        try:
            # Only admins can permanently delete users
            if request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required"},
                    status=status.HTTP_403_FORBIDDEN
                )

            confirm = request.query_params.get('confirm', '').lower()
            if confirm != 'yes':
                return Response({
                    "error": "Permanent deletion requires confirmation", 
                    "message": "Add ?confirm=yes to permanently delete this user"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            deleted = self.user_service.hard_delete_user(
                user_id, 
                request.current_user, 
                confirmation_token="PERMANENT_DELETE_CONFIRMED"
            )
            
            if not deleted:
                return Response(
                    {"error": "User not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                "message": "User permanently deleted"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeletedUsersView(APIView):
    def __init__(self):
        super().__init__()
        self.user_service = UserService()

    
    def get(self, request):
        """Get soft‑deleted users – Admin only"""
        try:
            # Only admins can view deleted users
            if request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required"},
                    status=status.HTTP_403_FORBIDDEN
                )

            page = int(request.query_params.get('page', 1))
            limit = int(request.query_params.get('limit', 50))
            
            result = self.user_service.get_deleted_users(page=page, limit=limit)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting deleted users: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserByEmailView(APIView):
    def __init__(self):
        super().__init__()
        self.user_service = UserService()

        
    def get(self, request, email):
        """Get user by email (excludes deleted by default)"""
        try:
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            
            # Only admins can view deleted users
            if include_deleted and request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required to view deleted users"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user = self.user_service.get_user_by_email(email, include_deleted=include_deleted)
            if not user:
                return Response(
                    {"error": "User not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(user, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserByUsernameView(APIView):
    def __init__(self):
        super().__init__()
        self.user_service = UserService()

        
    def get(self, request, username):
        """Get user by username (excludes deleted by default)"""
        try:
            include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
            
            # Only admins can view deleted users
            if include_deleted and request.current_user.get('role', '').lower() != 'admin':
                return Response(
                    {"error": "Admin permissions required to view deleted users"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user = self.user_service.get_user_by_username(username, include_deleted=include_deleted)
            if not user:
                return Response(
                    {"error": "User not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(user, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
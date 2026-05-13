from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from app.services.identity.auth_services import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from models.Users import User
import logging

logger = logging.getLogger(__name__)

POS_ALLOWED_ROLES = {"admin", "manager", "staff", "cashier"}


class POSLoginView(APIView):
    def post(self, request):
        """Employee login for POS terminal"""
        try:
            email = request.data.get('email')
            password = request.data.get('password')

            if not email or not password:
                return Response(
                    {"error": "Email and password are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            auth_service = AuthService()

            user = User.get_by_email(email)
            if not user or not auth_service.verify_password(password, user.password):
                return Response(
                    {"error": "Invalid email or password"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if user.isDeleted or user.status != "active":
                return Response(
                    {"error": "Account is not active"},
                    status=status.HTTP_403_FORBIDDEN
                )

            if user.role.lower() not in POS_ALLOWED_ROLES:
                return Response(
                    {"error": "Access denied. Insufficient permissions for POS access."},
                    status=status.HTTP_403_FORBIDDEN
                )

            user.last_login = datetime.utcnow()
            user.save()

            user_id = user.sk
            token_data = {"sub": user_id, "email": user.email, "role": user.role}
            access_token = auth_service.create_access_token(token_data)
            refresh_token = auth_service.create_refresh_token(token_data)

            try:
                from app.services.identity.session_services import SessionLogService
                SessionLogService().log_login({
                    "user_id": user_id,
                    "username": user.username or user.email,
                    "email": user.email,
                    "branch_id": 1,
                    "role": user.role,
                })
            except Exception as session_error:
                logger.debug(f"Session logging unavailable: {session_error}")

            logger.info(f"POS login successful: {email}")

            return Response({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": user_id,
                    "email": user.email,
                    "role": user.role,
                    "name": user.full_name or "",
                    "username": user.username or "",
                    "status": user.status,
                },
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"POS login failed for {request.data.get('email')}: {e}")
            return Response(
                {"error": "Login failed"},
                status=status.HTTP_401_UNAUTHORIZED
            )


class POSLogoutView(APIView):
    def post(self, request):
        """Employee logout from POS terminal"""
        try:
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return Response(
                    {"error": "Missing or invalid authorization header"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            token = authorization.replace("Bearer ", "").strip()
            result = AuthService().logout(token)
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"POS logout error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class POSRefreshTokenView(APIView):
    def post(self, request):
        """Refresh POS access token"""
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            result = AuthService().refresh_access_token(refresh_token)
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )


class POSCurrentUserView(APIView):
    def get(self, request):
        """Get currently authenticated POS employee"""
        try:
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return Response(
                    {"error": "Missing or invalid authorization header"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            token = authorization.split(" ")[1]
            user = AuthService().get_current_user(token)

            if user:
                return Response(user, status=status.HTTP_200_OK)

            return Response(
                {"error": "Invalid token"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class POSVerifyTokenView(APIView):
    def post(self, request):
        """Verify POS token validity"""
        try:
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
            else:
                token = request.data.get('token')

            if not token:
                return Response(
                    {"error": "Token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payload = AuthService().verify_token(token)

            if payload:
                return Response({
                    "valid": True,
                    "user_id": payload.get("sub"),
                    "email": payload.get("email"),
                    "role": payload.get("role"),
                }, status=status.HTTP_200_OK)

            return Response(
                {"valid": False, "error": "Invalid token"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

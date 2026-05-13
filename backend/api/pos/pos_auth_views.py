import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.services.identity.auth_services import AuthService

logger = logging.getLogger(__name__)

_auth_service = AuthService()


class PosLoginView(APIView):
    """
    POST /api/v1/pos/auth/login/
    Authenticates any active user (admin, manager, staff, cashier).
    Returns JWT access + refresh tokens.
    """

    def post(self, request):
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        if not email or not password:
            return Response(
                {"success": False, "error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = _auth_service.pos_login(email, password)
            return Response({"success": True, **result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class PosLogoutView(APIView):
    """
    POST /api/v1/pos/auth/logout/
    Blacklists the current token and closes the active POS session.
    Requires Authorization: Bearer <token>
    """

    def post(self, request):
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return Response(
                {"success": False, "error": "Missing or invalid authorization header"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token = authorization.split(" ", 1)[1].strip()

        try:
            result = _auth_service.logout(token)
            return Response({"success": True, **result}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"POS logout error: {e}")
            return Response(
                {"success": False, "error": "Logout failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

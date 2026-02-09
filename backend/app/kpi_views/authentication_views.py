from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from ..services.auth_services import AuthService
from ..services.session_services import SessionLogService 
from notifications.email_service import email_service
from datetime import datetime, timedelta
import secrets
import logging

# ================ AUTHENTICATION VIEWS ================

class LoginView(APIView):
    def post(self, request):
        """User login"""
        try:
            auth_service = AuthService()
            email = request.data.get('email')
            password = request.data.get('password')
            
            if not email or not password:
                return Response(
                    {"error": "Email and password are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = auth_service.login(email, password)
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

class LogoutView(APIView):
    def post(self, request):
        """User logout"""
        try:
            auth_service = AuthService()
            
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return Response(
                    {"error": "Missing or invalid authorization header"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Let AuthService handle everything including session logout
            token = authorization.replace("Bearer ", "").strip()
            result = auth_service.logout(token)
            
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RefreshTokenView(APIView):
    def post(self, request):
        """Refresh access token"""
        try:
            auth_service = AuthService()
            refresh_token = request.data.get('refresh_token')
            
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = auth_service.refresh_access_token(refresh_token)
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

class CurrentUserView(APIView):
    def get(self, request):
        """Get current authenticated user"""
        try:
            auth_service = AuthService()
            
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return Response(
                    {"error": "Missing or invalid authorization header"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            token = authorization.split(" ")[1]
            user = auth_service.get_current_user(token)
            
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

class VerifyTokenView(APIView):
    def post(self, request):
        """Verify if token is valid"""
        try:
            auth_service = AuthService()
            
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
            
            payload = auth_service.verify_token(token)
            
            if payload:
                return Response({
                    "valid": True,
                    "user_id": payload.get("sub"),
                    "email": payload.get("email"),
                    "role": payload.get("role")
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

class RequestPasswordResetView(APIView):
    """Request password reset - sends email with reset link"""
    def post(self, request):
        try:
            logging.info("Password reset request received")
            email = request.data.get('email')
            
            if not email:
                return Response(
                    {"error": "Email is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logging.info(f"Processing password reset for email: {email}")
            auth_service = AuthService()
            
            # Find user by email
            user = auth_service.user_collection.find_one({"email": email})
            
            # Always return success message (security best practice - don't reveal if email exists)
            success_message = "If an account exists with this email, you will receive password reset instructions."
            
            if not user:
                return Response({
                    "success": True,
                    "message": success_message
                }, status=status.HTTP_200_OK)
            
            # Generate secure reset token
            reset_token = secrets.token_urlsafe(32)
            
            # Set expiration to 1 hour from now
            reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            
            # Update user with reset token
            auth_service.user_collection.update_one(
                {"_id": user['_id']},
                {
                    "$set": {
                        "reset_token": reset_token,
                        "reset_token_expires": reset_token_expires
                    }
                }
            )
            
            # Send password reset email
            email_result = email_service.send_password_reset_email(
                to_email=email,
                reset_token=reset_token,
                user_name=user.get('full_name')
            )
            
            if not email_result.get('success'):
                logging.error(f"Failed to send password reset email: {email_result.get('error')}")
                # Still return success to user for security
            
            return Response({
                "success": True,
                "message": success_message
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Error in RequestPasswordResetView: {str(e)}", exc_info=True)
            return Response(
                {"error": f"An error occurred processing your request: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ResetPasswordView(APIView):
    """Reset password with valid token"""
    def post(self, request):
        try:
            token = request.data.get('token')
            new_password = request.data.get('new_password')
            
            if not token or not new_password:
                return Response(
                    {"error": "Token and new password are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate password strength
            if len(new_password) < 8:
                return Response(
                    {"error": "Password must be at least 8 characters long"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            auth_service = AuthService()
            
            # Find user by reset token
            user = auth_service.user_collection.find_one({
                "reset_token": token
            })
            
            if not user:
                return Response(
                    {"error": "Invalid or expired reset token"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if token has expired
            if user.get('reset_token_expires'):
                if datetime.utcnow() > user['reset_token_expires']:
                    return Response(
                        {"error": "Reset token has expired. Please request a new password reset."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Hash the new password
            import bcrypt
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update user password and clear reset token
            auth_service.user_collection.update_one(
                {"_id": user['_id']},
                {
                    "$set": {
                        "password": hashed_password,
                        "last_updated": datetime.utcnow()
                    },
                    "$unset": {
                        "reset_token": "",
                        "reset_token_expires": ""
                    }
                }
            )
            
            return Response({
                "success": True,
                "message": "Password reset successfully. You can now log in with your new password."
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Error in ResetPasswordView: {str(e)}")
            return Response(
                {"error": "An error occurred resetting your password"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyResetTokenView(APIView):
    """Verify if a reset token is valid (for frontend validation)"""
    def post(self, request):
        try:
            token = request.data.get('token')
            
            if not token:
                return Response(
                    {"error": "Token is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            auth_service = AuthService()
            
            # Find user by reset token
            user = auth_service.user_collection.find_one({
                "reset_token": token
            })
            
            if not user:
                return Response({
                    "valid": False,
                    "error": "Invalid reset token"
                }, status=status.HTTP_200_OK)
            
            # Check if token has expired
            if user.get('reset_token_expires'):
                if datetime.utcnow() > user['reset_token_expires']:
                    return Response({
                        "valid": False,
                        "error": "Reset token has expired"
                    }, status=status.HTTP_200_OK)
            
            return Response({
                "valid": True,
                "email": user.get('email')
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logging.error(f"Error in VerifyResetTokenView: {str(e)}")
            return Response(
                {"error": "An error occurred verifying the token"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
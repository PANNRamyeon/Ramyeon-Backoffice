from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from decouple import config
from django.conf import settings
from models.Users import User
from models.TokenBlacklist import TokenBlacklist
import logging

logger = logging.getLogger(__name__)


def _resolve_secret_key():
    """
    Determine the JWT secret key.

    Precedence:
    1. AUTH_JWT_SECRET env (explicit override)
    2. Django settings.SECRET_KEY
    3. Fallback to legacy hard-coded default
    """
    explicit_secret = config('AUTH_JWT_SECRET', default=None)
    if explicit_secret:
        return explicit_secret
    return getattr(settings, 'SECRET_KEY', None) or "your-secret-key-here-change-in-production"


# JWT settings
SECRET_KEY = _resolve_secret_key()
ALGORITHM = config('AUTH_JWT_ALGORITHM', default='HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = config('AUTH_ACCESS_TOKEN_EXPIRE_MINUTES', default=10000, cast=int)
REFRESH_TOKEN_EXPIRE_DAYS = config('AUTH_REFRESH_TOKEN_EXPIRE_DAYS', default=7, cast=int)

class AuthService:
    def __init__(self):
        """Initialize AuthService using DynamoDB models"""
        pass  # No initialization needed - using PynamoDB models directly
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            result = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            return result
        except Exception as e:
            logger.error(f"Password verification exception: {e}")
            return False
    
    def create_access_token(self, data: dict, expires_delta: timedelta = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict):
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str):
        """Verify JWT token"""
        try:
            # Check if token is blacklisted (O(1) lookup)
            if TokenBlacklist.is_blacklisted(token):
                logger.info("Token is blacklisted")
                return None
            
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                return None
            return payload
        except JWTError as e:
            logger.error(f"JWT verification error: {e}")
            return None
    
    def login(self, email: str, password: str):
        """Authenticate user and return JWT tokens"""
        try:
            # Find user by email
            user = User.get_by_email(email)
            
            if not user:
                logger.warning(f"Login attempt with non-existent email: {email}")
                raise Exception("Invalid email or password")
            
            # Password verification
            password_valid = self.verify_password(password, user.password)
            
            if not password_valid:
                logger.warning(f"Invalid password for user: {email}")
                raise Exception("Invalid email or password")
            
            # Status checks
            if user.status != "active":
                logger.warning(f"Inactive account login attempt: {email}")
                raise Exception("Account is not active")
            
            # Role checks
            user_role = user.role.lower() if user.role else ""
            if user_role != "admin":
                logger.warning(f"Non-admin login attempt: {email} (role: {user_role})")
                raise Exception("Access denied. This system is restricted to administrators only.")
            
            # Deleted check
            if user.isDeleted:
                logger.warning(f"Deleted user login attempt: {email}")
                raise Exception("Account is not active")
            
            # Update last login
            user.last_login = datetime.utcnow()
            user.save()
            
            # Create tokens
            user_id = user.sk
            token_data = {"sub": user_id, "email": user.email, "role": user.role}
            access_token = self.create_access_token(token_data)
            refresh_token = self.create_refresh_token(token_data)
            
            # Prepare user data for response
            user_response_data = {
                "id": user_id,
                "email": user.email,
                "role": user.role,
                "name": user.full_name or "",
                "username": user.username or "",
                "status": user.status
            }
            
            # Session logging
            try:
                from .session_services import SessionLogService
                session_service = SessionLogService()
                session_user = {
                    "user_id": user_id,
                    "username": user.username or user.email,
                    "email": user.email,
                    "branch_id": 1,
                    "role": "admin"
                }
                session_service.log_login(session_user)
            except Exception as session_error:
                logger.debug(f"Session logging not available: {session_error}")
            
            logger.info(f"Successful login: {email}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": user_response_data
            }
            
        except Exception as e:
            logger.error(f"Login failed for {email}: {str(e)}")
            raise e
    
    def logout(self, token: str):
        """Logout user by blacklisting their token"""
        try:
            clean_token = token.replace("Bearer ", "").strip()
            
            user_id = None
            
            # Get user info and log session logout
            try:
                current_user = self.get_current_user(clean_token)
                if current_user and current_user.get('user_id'):
                    user_id = current_user.get('user_id')
                    
                    # Log session logout
                    try:
                        from .session_services import SessionLogService
                        session_service = SessionLogService()
                        session_service.log_logout(user_id)
                    except Exception as session_error:
                        logger.error(f"Session logout failed: {session_error}")
                        
            except Exception as user_error:
                logger.error(f"Could not get current user: {user_error}")
            
            # Decode token to get expiration time
            try:
                payload = jwt.decode(clean_token, SECRET_KEY, algorithms=[ALGORITHM])
                expires_timestamp = payload.get('exp')
                expires_at = datetime.fromtimestamp(expires_timestamp) if expires_timestamp else datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            except:
                # If we can't decode, use default expiration
                expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            
            # Blacklist token using TokenBlacklist model
            TokenBlacklist.blacklist_token(
                token=clean_token,
                expires_at=expires_at,
                reason="logout",
                user_id=user_id
            )
            
            logger.info(f"Token blacklisted successfully for user: {user_id}")
            
            return {"message": "Successfully logged out"}
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise e
    
    def get_current_user(self, token: str):
        """Get current user from token"""
        try:
            payload = self.verify_token(token)
            if not payload or payload.get("type") != "access":
                return None
            
            user_id = payload["sub"]  # This is USER-### format
            
            # Get user using PynamoDB
            user = User.get("users", user_id)
            
            if user:
                # Get email_verified field (defaults to False if not set)
                email_verified_bool = bool(user.email_verified) if user.email_verified is not None else False
                
                # Log for debugging
                logger.info(f"get_current_user - User: {user.email}, email_verified in DB: {email_verified_bool}, type: {type(email_verified_bool)}")
                
                # Convert to dict using model's to_dict method
                user_data = user.to_dict()
                user_data['email_verified'] = email_verified_bool
                
                response_data = {
                    "user_id": user.sk,  # USER-###
                    "email": user.email,
                    "role": user.role,
                    "email_verified": email_verified_bool,
                    "user_data": user_data
                }
                
                logger.info(f"get_current_user response - email_verified: {response_data.get('email_verified')}")
                
                return response_data
            return None
        
        except User.DoesNotExist:
            logger.warning(f"User not found: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            raise Exception(f"Error getting current user: {str(e)}")
    
    def refresh_access_token(self, refresh_token: str):
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "refresh":
                raise Exception("Invalid token type")
            
            user_id = payload["sub"]  # USER-###
            
            # Get user using PynamoDB
            user = User.get("users", user_id)
            
            if not user:
                raise Exception("User not found")
            
            # Check if user is active and not deleted
            if user.status != "active" or user.isDeleted:
                raise Exception("User account is not active")
            
            # Create new access token
            token_data = {"sub": user_id, "email": user.email, "role": user.role}
            new_access_token = self.create_access_token(token_data)
            
            logger.info(f"Access token refreshed for user: {user_id}")
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
        except User.DoesNotExist:
            logger.error("User not found during token refresh")
            raise Exception("User not found")
        except JWTError as e:
            logger.error(f"Invalid refresh token: {str(e)}")
            raise Exception("Invalid refresh token")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            raise Exception("Token refresh failed due to a server error")
"""
Email Verification Service
Handles email verification using verification codes (no database storage needed)
"""
import logging
import random
import hashlib
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from decouple import config
from notifications.email_service import email_service
from app.database import db_manager

logger = logging.getLogger(__name__)

# JWT settings for email verification
VERIFICATION_SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here-change-in-production')
VERIFICATION_ALGORITHM = "HS256"
VERIFICATION_CODE_EXPIRE_MINUTES = 10  # Code expires in 10 minutes
VERIFICATION_CODE_LENGTH = 6  # 6-digit code

class EmailVerificationService:
    """Service for email verification using JWT tokens"""
    
    def __init__(self):
        self.db = db_manager.get_database()
        self.user_collection = self.db.users
    
    def generate_verification_code(self):
        """
        Generate a random 6-digit verification code
        
        Returns:
            str: 6-digit verification code
        """
        return str(random.randint(100000, 999999))
    
    def hash_code(self, code):
        """
        Hash verification code for storage in JWT
        
        Args:
            code (str): Verification code
        
        Returns:
            str: Hashed code
        """
        return hashlib.sha256(code.encode()).hexdigest()
    
    def generate_verification_token(self, email, code, user_id=None):
        """
        Generate JWT token containing verification code hash
        
        Args:
            email (str): User's email address
            code (str): Verification code
            user_id (str, optional): User ID
        
        Returns:
            str: JWT verification token
        """
        try:
            # Create token payload with timestamps
            # Use timezone-aware datetime for consistency
            now = datetime.now(timezone.utc)
            exp = now + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)
            
            # Hash the code before storing in token
            code_hash = self.hash_code(code)
            
            # Log token generation for debugging
            logger.info(f"Generating token - Now (UTC): {now}, Exp (UTC): {exp}, Exp timestamp: {int(exp.timestamp())}, Minutes: {VERIFICATION_CODE_EXPIRE_MINUTES}")
            
            # JWT library expects integer timestamps, not datetime objects
            # Convert to timestamps for consistency
            iat_timestamp = int(now.timestamp())
            exp_timestamp = int(exp.timestamp())
            
            payload = {
                "email": email,
                "code_hash": code_hash,
                "type": "email_verification_code",
                "iat": iat_timestamp,
                "exp": exp_timestamp
            }
            
            if user_id:
                payload["user_id"] = user_id
            
            # Generate token
            token = jwt.encode(payload, VERIFICATION_SECRET_KEY, algorithm=VERIFICATION_ALGORITHM)
            logger.info(f"Generated verification token for email: {email}")
            return token
        
        except Exception as e:
            logger.error(f"Error generating verification token: {e}")
            raise Exception(f"Failed to generate verification token: {str(e)}")
    
    def verify_token(self, token):
        """
        Verify JWT verification token
        
        Args:
            token (str): JWT verification token
        
        Returns:
            dict: Token payload if valid, None if invalid
        """
        try:
            # First decode without expiration check to get token info
            try:
                unverified_payload = jwt.decode(
                    token, 
                    VERIFICATION_SECRET_KEY, 
                    algorithms=[VERIFICATION_ALGORITHM],
                    options={"verify_signature": True, "verify_exp": False}
                )
                
                # Check expiration manually with detailed logging
                exp_timestamp = unverified_payload.get("exp")
                iat_timestamp = unverified_payload.get("iat")
                now = datetime.now(timezone.utc)
                now_timestamp = int(now.timestamp())
                
                if exp_timestamp:
                    exp_time = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                    time_remaining = exp_timestamp - now_timestamp
                    logger.info(f"Token expiration check - Now: {now} (ts: {now_timestamp}), Exp: {exp_time} (ts: {exp_timestamp}), Remaining: {time_remaining}s, Valid: {now_timestamp < exp_timestamp}")
                    
                    if now_timestamp >= exp_timestamp:
                        logger.warning(f"Token expired - Current ({now_timestamp}) >= Exp ({exp_timestamp}), Over by: {now_timestamp - exp_timestamp}s")
                        return None
                
                # Now verify with expiration check and increased leeway
                payload = jwt.decode(
                    token, 
                    VERIFICATION_SECRET_KEY, 
                    algorithms=[VERIFICATION_ALGORITHM],
                    options={"leeway": 120}  # Allow 2 minutes of clock skew
                )
                
            except jwt.ExpiredSignatureError:
                # Log detailed expiration info
                try:
                    unverified = jwt.decode(token, VERIFICATION_SECRET_KEY, algorithms=[VERIFICATION_ALGORITHM], options={"verify_exp": False})
                    exp_ts = unverified.get("exp")
                    now_ts = int(datetime.now(timezone.utc).timestamp())
                    logger.error(f"Token expired during decode - EXP: {exp_ts}, Now: {now_ts}, Over by: {now_ts - exp_ts}s")
                except Exception as decode_err:
                    logger.error(f"Could not decode expired token: {decode_err}")
                raise
            
            # Check token type
            if payload.get("type") != "email_verification_code":
                logger.warning("Invalid token type for email verification")
                return None
            
            logger.info(f"Token verified successfully for email: {payload.get('email')}")
            return payload
        
        except jwt.ExpiredSignatureError as e:
            logger.warning(f"Verification token has expired: {e}")
            return None
        except jwt.JWTError as e:
            logger.error(f"JWT verification error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def send_verification_code(self, email, user_id=None, user_name=None):
        """
        Generate and send verification code to user
        
        Args:
            email (str): User's email address
            user_id (str, optional): User ID
            user_name (str, optional): User's name
        
        Returns:
            dict: Result with success status and token
        """
        try:
            # Generate verification code
            code = self.generate_verification_code()
            
            # Generate verification token with code hash
            token = self.generate_verification_token(email, code, user_id)
            
            # Send email with code
            result = email_service.send_verification_code_email(email, code, user_name)
            
            if result.get('success'):
                logger.info(f"Verification code sent successfully to {email}")
                return {
                    'success': True,
                    'message': 'Verification code sent successfully',
                    'token': token  # Return token for frontend to use when verifying
                }
            else:
                logger.error(f"Failed to send verification code to {email}: {result.get('error')}")
                return result
        
        except Exception as e:
            logger.error(f"Error sending verification code: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_verification_email(self, email, user_id=None, user_name=None):
        """
        Legacy method - sends verification code (for backward compatibility)
        """
        return self.send_verification_code(email, user_id, user_name)
    
    def verify_code(self, token, code):
        """
        Verify user's email address using verification code
        
        Args:
            token (str): JWT verification token (returned from send_verification_code)
            code (str): Verification code entered by user
        
        Returns:
            dict: Result with success status and user info
        """
        try:
            # Verify token
            payload = self.verify_token(token)
            
            if not payload:
                return {
                    'success': False,
                    'error': 'Invalid or expired verification token'
                }
            
            email = payload.get('email')
            user_id = payload.get('user_id')
            code_hash = payload.get('code_hash')
            
            if not email:
                return {
                    'success': False,
                    'error': 'Email not found in token'
                }
            
            if not code_hash:
                return {
                    'success': False,
                    'error': 'Code hash not found in token'
                }
            
            # Verify the code matches
            submitted_code_hash = self.hash_code(code)
            if submitted_code_hash != code_hash:
                logger.warning(f"Invalid verification code for email: {email}")
                return {
                    'success': False,
                    'error': 'Invalid verification code'
                }
            
            # Find user by email or user_id
            user = None
            if user_id:
                # Try to find by user_id (could be string like "USER-0039" or ObjectId)
                try:
                    # from bson import ObjectId
                    # Try as ObjectId first if it's a valid ObjectId string (24 hex chars)
                    if isinstance(user_id, str) and len(user_id) == 24:
                        try:
                            user = self.user_collection.find_one({"_id": user_id})
                        except:
                            pass
                    # If not found or not ObjectId format, try as string (e.g., "USER-0039")
                    if not user:
                        user = self.user_collection.find_one({"_id": user_id})
                except Exception as e:
                    logger.warning(f"Error finding user by user_id: {e}")
            
            # Fallback to email lookup if user_id lookup failed
            if not user:
                user = self.user_collection.find_one({"email": email})
                logger.info(f"User not found by user_id, found by email: {email}")
            
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            logger.info(f"Found user for verification: {email}, _id: {user.get('_id')}, _id type: {type(user.get('_id'))}")
            
            # Update email_verified status in database for all users
            email_verified_status = user.get('email_verified', False)
            
            try:
                # Update email_verified status for the user
                user_id_for_update = user.get('_id')
                logger.info(f"Attempting to update email_verified for user_id: {user_id_for_update}, email: {email}")
                
                update_result = self.user_collection.update_one(
                    {'_id': user_id_for_update},
                    {
                        '$set': {
                            'email_verified': True,
                            'email_verified_at': datetime.now(timezone.utc),
                            'last_updated': datetime.now(timezone.utc)
                        }
                    }
                )
                
                logger.info(f"Update result - matched: {update_result.matched_count}, modified: {update_result.modified_count}")
                
                if update_result.modified_count > 0:
                    logger.info(f"✅ Successfully updated email_verified=True for user: {email} (ID: {user_id_for_update})")
                    email_verified_status = True
                elif update_result.matched_count > 0:
                    # User already verified
                    logger.info(f"✅ User already verified (no change needed): {email} (ID: {user_id_for_update})")
                    email_verified_status = True
                else:
                    logger.warning(f"⚠️ Update failed - no document matched for user_id: {user_id_for_update}, email: {email}")
                    
            except Exception as update_error:
                logger.error(f"❌ Exception updating email_verified for user {email}: {update_error}", exc_info=True)
            
            logger.info(f"Email verified successfully for: {email}")
            
            return {
                'success': True,
                'message': 'Email verified successfully',
                'email': email,
                'user_id': str(user.get('_id', '')),
                'username': user.get('username', ''),
                'email_verified': email_verified_status
            }
        
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_email(self, token):
        """
        Legacy method - for backward compatibility with link-based verification
        """
        try:
            payload = self.verify_token(token)
            
            if not payload:
                return {
                    'success': False,
                    'error': 'Invalid or expired verification token'
                }
            
            email = payload.get('email')
            user_id = payload.get('user_id')
            
            if not email:
                return {
                    'success': False,
                    'error': 'Email not found in token'
                }
            
            # Find user by email or user_id
            user = None
            if user_id:
                user = self.user_collection.find_one({"_id": user_id})
            
            if not user:
                user = self.user_collection.find_one({"email": email})
            
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            logger.info(f"Email verified successfully for: {email}")
            
            return {
                'success': True,
                'message': 'Email verified successfully',
                'email': email,
                'user_id': str(user.get('_id', '')),
                'username': user.get('username', '')
            }
        
        except Exception as e:
            logger.error(f"Error verifying email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def resend_verification_code(self, email):
        """
        Resend verification code to user
        
        Args:
            email (str): User's email address
        
        Returns:
            dict: Result with success status and token
        """
        try:
            # Find user by email
            user = self.user_collection.find_one({"email": email})
            
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            user_id = str(user.get('_id', ''))
            user_name = user.get('full_name') or user.get('username', '')
            
            # Send verification code
            return self.send_verification_code(email, user_id, user_name)
        
        except Exception as e:
            logger.error(f"Error resending verification code: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def resend_verification_email(self, email):
        """
        Legacy method - for backward compatibility
        """
        return self.resend_verification_code(email)

# Singleton instance
email_verification_service = EmailVerificationService()


import logging
import random
import hashlib
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from decouple import config
from notifications.email_service import email_service
from app.database import db_manager
from app.utils import DYNAMO_TABLE_NAME
from boto3.dynamodb.conditions import Attr

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
        self.user_collection = self.db.Table(DYNAMO_TABLE_NAME)
    
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
            now = datetime.now(timezone.utc)
            exp = now + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)
            code_hash = self.hash_code(code)
            
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
            payload = jwt.decode(
                token, 
                VERIFICATION_SECRET_KEY, 
                algorithms=[VERIFICATION_ALGORITHM],
                options={"leeway": 120}  # Allow 2 minutes of clock skew
            )
            
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
            return None

    def send_verification_code(self, email, user_id=None, user_name=None):
        """
        Generate and send verification code to user
        """
        try:
            code = self.generate_verification_code()
            token = self.generate_verification_token(email, code, user_id)
            result = email_service.send_verification_code_email(email, code, user_name)
            
            if result.get('success'):
                logger.info(f"Verification code sent successfully to {email}")
                return {
                    'success': True,
                    'message': 'Verification code sent successfully',
                    'token': token
                }
            else:
                logger.error(f"Failed to send verification code to {email}: {result.get('error')}")
                return result
        
        except Exception as e:
            logger.error(f"Error sending verification code: {e}")
            return {'success': False, 'error': str(e)}

    def verify_code(self, token, code):
        """
        Verify user's email address using verification code
        """
        try:
            payload = self.verify_token(token)
            if not payload:
                return {'success': False, 'error': 'Invalid or expired verification token'}
            
            email = payload.get('email')
            user_id = payload.get('user_id')
            code_hash = payload.get('code_hash')
            
            if not email or not code_hash:
                return {'success': False, 'error': 'Token is missing required data'}

            if self.hash_code(code) != code_hash:
                logger.warning(f"Invalid verification code for email: {email}")
                return {'success': False, 'error': 'Invalid verification code'}

            user = None
            if user_id:
                try:
                    response = self.user_collection.get_item(Key={'pk': 'users', 'sk': user_id})
                    user = response.get('Item')
                except Exception as e:
                    logger.warning(f"Error finding user by user_id {user_id}: {e}")

            if not user:
                response = self.user_collection.scan(FilterExpression=Attr('email').eq(email))
                items = response.get('Items', [])
                if items:
                    user = items[0]
                logger.info(f"User not found by user_id, found by email: {email}")

            if not user:
                return {'success': False, 'error': 'User not found'}
            
            user_sk = user.get('sk')
            if not user_sk:
                return {'success': False, 'error': 'User SK not found'}


            try:
                self.user_collection.update_item(
                    Key={'pk': 'users', 'sk': user_sk},
                    UpdateExpression='SET email_verified = :verified, email_verified_at = :verified_at, last_updated = :updated_at',
                    ExpressionAttributeValues={
                        ':verified': True,
                        ':verified_at': datetime.now(timezone.utc).isoformat(),
                        ':updated_at': datetime.now(timezone.utc).isoformat()
                    }
                )
                logger.info(f"✅ Successfully updated email_verified=True for user: {email} (SK: {user_sk})")
                email_verified_status = True
            except Exception as update_error:
                logger.error(f"❌ Exception updating email_verified for user {email}: {update_error}", exc_info=True)
                email_verified_status = user.get('email_verified', False)


            return {
                'success': True,
                'message': 'Email verified successfully',
                'email': email,
                'user_id': user_sk,
                'username': user.get('username', ''),
                'email_verified': email_verified_status
            }
        
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            return {'success': False, 'error': str(e)}

    def verify_email(self, token):
        """
        Legacy method - for backward compatibility with link-based verification
        """
        try:
            payload = self.verify_token(token)
            if not payload:
                return {'success': False, 'error': 'Invalid or expired verification token'}

            email = payload.get('email')
            user_id = payload.get('user_id')

            if not email:
                return {'success': False, 'error': 'Email not found in token'}

            user = None
            if user_id:
                try:
                    response = self.user_collection.get_item(Key={'pk': 'users', 'sk': user_id})
                    user = response.get('Item')
                except Exception:
                    pass
            
            if not user:
                response = self.user_collection.scan(FilterExpression=Attr('email').eq(email))
                items = response.get('Items', [])
                if items:
                    user = items[0]

            if not user:
                return {'success': False, 'error': 'User not found'}

            logger.info(f"Email verified successfully for: {email}")
            
            return {
                'success': True,
                'message': 'Email verified successfully',
                'email': email,
                'user_id': user.get('sk', ''),
                'username': user.get('username', '')
            }
        
        except Exception as e:
            logger.error(f"Error verifying email: {e}")
            return {'success': False, 'error': str(e)}

    def resend_verification_code(self, email):
        """
        Resend verification code to user
        """
        try:
            response = self.user_collection.scan(FilterExpression=Attr('email').eq(email))
            items = response.get('Items', [])
            if not items:
                return {'success': False, 'error': 'User not found'}
            
            user = items[0]
            user_id = user.get('sk', '')
            user_name = user.get('full_name') or user.get('username', '')
            
            return self.send_verification_code(email, user_id, user_name)
        
        except Exception as e:
            logger.error(f"Error resending verification code: {e}")
            return {'success': False, 'error': str(e)}

    def send_verification_email(self, email, user_id=None, user_name=None):
        return self.send_verification_code(email, user_id, user_name)

    def resend_verification_email(self, email):
        return self.resend_verification_code(email)

# Singleton instance
email_verification_service = EmailVerificationService()
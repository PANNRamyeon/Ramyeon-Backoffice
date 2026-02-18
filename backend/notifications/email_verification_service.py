"""
Email Verification Service
Handles email verification using verification codes.
Now fully adapted for PynamoDB (DynamoDB) with a single-table design.
"""
import logging
import random
import hashlib
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from decouple import config
from notifications.email_service import email_service
from notifications.models import Notification

# PynamoDB imports
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, UTCDateTimeAttribute,
    JSONAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST

logger = logging.getLogger(__name__)

# JWT settings for email verification
VERIFICATION_SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here-change-in-production')
VERIFICATION_ALGORITHM = "HS256"
VERIFICATION_CODE_EXPIRE_MINUTES = 10
VERIFICATION_CODE_LENGTH = 6


# ============= USER MODEL (Single Table with Notifications) =============
class UserEmailIndex(GlobalSecondaryIndex):
    """GSI for querying users by email address."""
    class Meta:
        index_name = 'user-email-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    email = UnicodeAttribute(hash_key=True)


class User(Model):
    """
    User model stored in the same DynamoDB table as Notification.
    PK format: "USER#<user_id>"   (e.g., "USER#USER-0039")
    SK format: "PROFILE"
    """
    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION
        if DYNAMODB_LOCAL:
            host = DYNAMODB_LOCAL_HOST
        read_capacity_units = 10
        write_capacity_units = 20

    # Primary key: composite hash+range key
    pk = UnicodeAttribute(hash_key=True)           # e.g., "USER#USER-0039"
    sk = UnicodeAttribute(range_key=True, default="PROFILE")

    # Attributes
    user_id = UnicodeAttribute()                    # plain id (duplicated for convenience)
    email = UnicodeAttribute()
    username = UnicodeAttribute(null=True)
    full_name = UnicodeAttribute(null=True)
    email_verified = BooleanAttribute(default=False)
    email_verified_at = UTCDateTimeAttribute(null=True)
    last_updated = UTCDateTimeAttribute(default_for_new=datetime.utcnow)

    # GSI for email lookups
    email_index = UserEmailIndex()

    @classmethod
    def create_user(cls, user_id: str, email: str, username: str = None, full_name: str = None):
        """Factory method to create a new user."""
        user = cls(
            pk=f"USER#{user_id}",
            sk="PROFILE",
            user_id=user_id,
            email=email,
            username=username,
            full_name=full_name,
            email_verified=False,
            last_updated=datetime.utcnow()
        )
        user.save()
        return user

    @classmethod
    def get_by_id(cls, user_id: str):
        """Retrieve user by its plain ID."""
        try:
            return cls.get(f"USER#{user_id}", "PROFILE")
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_email(cls, email: str):
        """Retrieve user by email using the GSI."""
        try:
            results = list(cls.email_index.query(email, limit=1))
            return results[0] if results else None
        except Exception:
            return None

    def update_email_verified(self):
        """Atomically mark email as verified."""
        now = datetime.now(timezone.utc)
        self.update(actions=[
            User.email_verified.set(True),
            User.email_verified_at.set(now),
            User.last_updated.set(now)
        ])
        self.refresh()   # reload to get updated values


# ============= EMAIL VERIFICATION SERVICE =============
class EmailVerificationService:
    """Service for email verification using JWT tokens and PynamoDB."""

    def __init__(self):
        # No explicit database connection needed; PynamoDB handles it.
        pass

    def generate_verification_code(self):
        """Generate a random 6-digit verification code."""
        return str(random.randint(100000, 999999))

    def hash_code(self, code):
        """Hash verification code for storage in JWT."""
        return hashlib.sha256(code.encode()).hexdigest()

    def generate_verification_token(self, email, code, user_id=None):
        """Generate JWT token containing verification code hash."""
        try:
            now = datetime.now(timezone.utc)
            exp = now + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)
            code_hash = self.hash_code(code)

            logger.info(f"Generating token - Now (UTC): {now}, Exp (UTC): {exp}")

            payload = {
                "email": email,
                "code_hash": code_hash,
                "type": "email_verification_code",
                "iat": int(now.timestamp()),
                "exp": int(exp.timestamp())
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
        """Verify JWT verification token."""
        try:
            # First decode without expiration check to inspect
            unverified_payload = jwt.decode(
                token,
                VERIFICATION_SECRET_KEY,
                algorithms=[VERIFICATION_ALGORITHM],
                options={"verify_signature": True, "verify_exp": False}
            )

            exp_timestamp = unverified_payload.get("exp")
            now_timestamp = int(datetime.now(timezone.utc).timestamp())
            if exp_timestamp and now_timestamp >= exp_timestamp:
                logger.warning(f"Token expired - Current ({now_timestamp}) >= Exp ({exp_timestamp})")
                return None

            # Now verify with expiration and leeway
            payload = jwt.decode(
                token,
                VERIFICATION_SECRET_KEY,
                algorithms=[VERIFICATION_ALGORITHM],
                options={"leeway": 120}  # 2 minutes clock skew
            )

            if payload.get("type") != "email_verification_code":
                logger.warning("Invalid token type for email verification")
                return None

            logger.info(f"Token verified successfully for email: {payload.get('email')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Verification token has expired")
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
        """Generate and send verification code to user."""
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

    def send_verification_email(self, email, user_id=None, user_name=None):
        """Legacy alias."""
        return self.send_verification_code(email, user_id, user_name)

    def _create_verification_notification(self, user_id, email):
        """Create an in-app notification for the user after successful email verification."""
        try:
            if not user_id:
                logger.warning("No user_id provided; skipping verification notification.")
                return False

            Notification.create_system_notification(
                title="Email Verified",
                message=f"Your email address {email} has been successfully verified.",
                recipient_id=user_id,
                priority="low",
                metadata={
                    "event": "email_verified",
                    "email": email,
                    "verified_at": datetime.utcnow().isoformat()
                }
            )
            logger.info(f"Verification notification created for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create verification notification for user {user_id}: {e}")
            return False

    def verify_code(self, token, code):
        """Verify user's email address using verification code."""
        try:
            # Verify token
            payload = self.verify_token(token)
            if not payload:
                return {'success': False, 'error': 'Invalid or expired verification token'}

            email = payload.get('email')
            user_id = payload.get('user_id')
            code_hash = payload.get('code_hash')

            if not email:
                return {'success': False, 'error': 'Email not found in token'}
            if not code_hash:
                return {'success': False, 'error': 'Code hash not found in token'}

            # Verify the code matches
            submitted_code_hash = self.hash_code(code)
            if submitted_code_hash != code_hash:
                logger.warning(f"Invalid verification code for email: {email}")
                return {'success': False, 'error': 'Invalid verification code'}

            # Find user
            user = None
            if user_id:
                user = User.get_by_id(user_id)
            if not user:
                user = User.get_by_email(email)
                if user:
                    logger.info(f"User found by email: {email}, ID: {user.user_id}")

            if not user:
                return {'success': False, 'error': 'User not found'}

            # Update email_verified status (atomically)
            user.update_email_verified()
            logger.info(f"Email verified successfully for: {email}")

            # Create in-app notification
            self._create_verification_notification(user.user_id, email)

            return {
                'success': True,
                'message': 'Email verified successfully',
                'email': email,
                'user_id': user.user_id,
                'username': user.username or '',
                'email_verified': True
            }

        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            return {'success': False, 'error': str(e)}

    def verify_email(self, token):
        """Legacy method – kept for backward compatibility with link‑based verification."""
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
                user = User.get_by_id(user_id)
            if not user:
                user = User.get_by_email(email)

            if not user:
                return {'success': False, 'error': 'User not found'}

            # Mark as verified (if not already)
            if not user.email_verified:
                user.update_email_verified()

            logger.info(f"Email verified successfully via link for: {email}")
            return {
                'success': True,
                'message': 'Email verified successfully',
                'email': email,
                'user_id': user.user_id,
                'username': user.username or ''
            }

        except Exception as e:
            logger.error(f"Error verifying email: {e}")
            return {'success': False, 'error': str(e)}

    def resend_verification_code(self, email):
        """Resend verification code to user."""
        try:
            user = User.get_by_email(email)
            if not user:
                return {'success': False, 'error': 'User not found'}

            user_id = user.user_id
            user_name = user.full_name or user.username or ''
            return self.send_verification_code(email, user_id, user_name)

        except Exception as e:
            logger.error(f"Error resending verification code: {e}")
            return {'success': False, 'error': str(e)}

    def resend_verification_email(self, email):
        """Legacy alias."""
        return self.resend_verification_code(email)


# Singleton instance
email_verification_service = EmailVerificationService()
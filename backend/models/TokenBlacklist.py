"""
TokenBlacklist Model - For JWT Token Revocation
PK = "token_blacklist", SK = token (JWT string)
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

from app.utils import DYNAMO_TABLE_NAME, AWS_REGION

logger = logging.getLogger(__name__)


# ============= GLOBAL SECONDARY INDEX =============

class TokenExpirationGSI(GlobalSecondaryIndex):
    """
    GSI for querying tokens by expiration date (for cleanup operations)
    Query pattern: Find all expired tokens to remove them
    """
    class Meta:
        index_name = 'TokenBlacklistExpirationIndex'
        projection = AllProjection()
        read_capacity_units = 1
        write_capacity_units = 1
    
    pk = UnicodeAttribute(hash_key=True)  # Will be set to 'token_blacklist'
    expires_at = UTCDateTimeAttribute(range_key=True)


# ============= TOKEN BLACKLIST MODEL =============

class TokenBlacklist(Model):
    """
    TOKEN BLACKLIST MODEL - For Revoking JWT Tokens
    
    Purpose:
    - Store revoked JWT tokens that should no longer be accepted
    - Enable immediate logout functionality
    - Support token revocation on password change, security breach, etc.
    
    Schema:
    - PK = "token_blacklist"
    - SK = token (the actual JWT string - ensures O(1) lookup)
    - blacklisted_at: When the token was revoked
    - expires_at: When the token naturally expires (for cleanup)
    - reason: Why the token was revoked (logout, password_change, security, etc.)
    - user_id: User who owned the token (for audit trail)
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        # Low capacity - blacklist operations are infrequent
        read_capacity_units = 2
        write_capacity_units = 2
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="token_blacklist")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # The actual JWT token
    
    # ============= GSI KEYS =============
    expires_at = UTCDateTimeAttribute()  # For cleanup queries
    
    # ============= GSI REFERENCE =============
    expiration_gsi = TokenExpirationGSI()
    
    # ============= TOKEN BLACKLIST DATA =============
    blacklisted_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    reason = UnicodeAttribute(default="logout")  # logout, password_change, security_breach, admin_revoke
    user_id = UnicodeAttribute(null=True)  # User who owned the token (for audit)
    revoked_by = UnicodeAttribute(null=True)  # Who revoked it (for admin actions)
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def blacklist_token(cls, token: str, expires_at: datetime, reason: str = "logout",
                       user_id: str = None, revoked_by: str = None) -> 'TokenBlacklist':
        """
        Add a token to the blacklist (revoke it)
        
        Args:
            token: The JWT token to blacklist
            expires_at: When the token naturally expires (for cleanup)
            reason: Why the token is being revoked
            user_id: User who owned the token (optional)
            revoked_by: Who revoked the token (optional, for admin actions)
        
        Returns:
            TokenBlacklist: Created blacklist entry
        
        Raises:
            ValueError: If required fields are missing
        """
        try:
            if not token or not token.strip():
                raise ValueError("Token is required")
            if not expires_at:
                raise ValueError("Expiration time is required")
            
            # Clean the token (remove "Bearer " prefix if present)
            clean_token = token.replace("Bearer ", "").strip()
            
            # Create blacklist entry
            blacklist_entry = cls(
                pk="token_blacklist",
                sk=clean_token,
                blacklisted_at=datetime.utcnow(),
                expires_at=expires_at,
                reason=reason,
                user_id=user_id,
                revoked_by=revoked_by
            )
            
            blacklist_entry.save()
            
            logger.info(f"Token blacklisted - User: {user_id or 'unknown'}, Reason: {reason}")
            return blacklist_entry
            
        except Exception as e:
            logger.error(f"Failed to blacklist token: {str(e)}")
            raise
    
    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """
        Check if a token is blacklisted (O(1) lookup)
        
        Args:
            token: The JWT token to check
        
        Returns:
            bool: True if token is blacklisted, False otherwise
        """
        try:
            if not token or not token.strip():
                return False
            
            # Clean the token
            clean_token = token.replace("Bearer ", "").strip()
            
            # Direct lookup by PK and SK (O(1) operation)
            blacklist_entry = cls.get("token_blacklist", clean_token)
            
            # If found, check if it has expired naturally
            if blacklist_entry.expires_at and blacklist_entry.expires_at < datetime.utcnow():
                # Token has naturally expired, can be removed from blacklist
                logger.info(f"Found expired token in blacklist, scheduling cleanup")
                return True  # Still return True (it's revoked), but mark for cleanup
            
            return True
            
        except cls.DoesNotExist:
            # Token not in blacklist (good!)
            return False
        except Exception as e:
            logger.error(f"Error checking token blacklist: {str(e)}")
            # Fail open: the JWT signature is still validated separately.
            # Treating a DynamoDB error as "blacklisted" logs out every user
            # during any transient DB hiccup, which is worse than briefly
            # allowing a revoked token through.
            return False
    
    @classmethod
    def revoke_user_tokens(cls, user_id: str, reason: str = "security",
                          revoked_by: str = None) -> int:
        """
        Revoke all tokens for a specific user
        (Use when password is changed, account is compromised, etc.)
        
        Note: This requires tracking user_id in blacklist entries.
        For a more complete solution, you'd need to track all issued tokens per user,
        or use token versioning.
        
        Args:
            user_id: User whose tokens should be revoked
            reason: Reason for revocation
            revoked_by: Who initiated the revocation
        
        Returns:
            int: Number of tokens revoked
        """
        try:
            # This is a simplified implementation
            # In a production system, you'd want to:
            # 1. Track all issued tokens per user, OR
            # 2. Use token versioning (increment version on password change)
            
            logger.warning(f"Token revocation requested for user {user_id}")
            logger.warning(f"Note: Only logout-blacklisted tokens will be revoked.")
            logger.warning(f"Consider implementing token versioning for complete revocation.")
            
            count = 0
            # Scan for tokens belonging to this user (inefficient, but works for small scale)
            for entry in cls.query("token_blacklist"):
                if entry.user_id == user_id:
                    entry.reason = reason
                    entry.revoked_by = revoked_by
                    entry.save()
                    count += 1
            
            logger.info(f"Revoked {count} tokens for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error revoking user tokens: {str(e)}")
            return 0
    
    @classmethod
    def cleanup_expired_tokens(cls, batch_size: int = 100) -> Dict[str, Any]:
        """
        Remove expired tokens from blacklist (cleanup operation)
        Should be run periodically (e.g., daily cron job)
        
        Args:
            batch_size: Number of tokens to cleanup per batch
        
        Returns:
            dict: Cleanup statistics
        """
        try:
            now = datetime.utcnow()
            deleted_count = 0
            error_count = 0
            
            logger.info(f"Starting token blacklist cleanup - Removing tokens expired before {now}")
            
            # Query expired tokens using GSI
            expired_tokens = []
            for entry in cls.expiration_gsi.query(
                "token_blacklist",
                cls.expires_at < now,
                limit=batch_size
            ):
                expired_tokens.append(entry)
            
            # Delete expired tokens
            for entry in expired_tokens:
                try:
                    entry.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete token: {str(e)}")
                    error_count += 1
            
            result = {
                "deleted_count": deleted_count,
                "error_count": error_count,
                "cleanup_timestamp": now.isoformat(),
                "success": error_count == 0
            }
            
            logger.info(f"Token cleanup complete - Deleted: {deleted_count}, Errors: {error_count}")
            return result
            
        except Exception as e:
            logger.error(f"Error during token cleanup: {str(e)}")
            return {
                "deleted_count": 0,
                "error_count": 0,
                "error": str(e),
                "success": False
            }
    
    @classmethod
    def get_blacklist_stats(cls) -> Dict[str, Any]:
        """
        Get statistics about the token blacklist
        
        Returns:
            dict: Blacklist statistics
        """
        try:
            now = datetime.utcnow()
            
            stats = {
                "total_tokens": 0,
                "expired_tokens": 0,
                "active_tokens": 0,
                "by_reason": {},
                "oldest_entry": None,
                "newest_entry": None
            }
            
            # Scan all blacklist entries (OK for small scale)
            for entry in cls.query("token_blacklist"):
                stats["total_tokens"] += 1
                
                # Check if expired
                if entry.expires_at and entry.expires_at < now:
                    stats["expired_tokens"] += 1
                else:
                    stats["active_tokens"] += 1
                
                # Count by reason
                reason = entry.reason or "unknown"
                stats["by_reason"][reason] = stats["by_reason"].get(reason, 0) + 1
                
                # Track oldest and newest
                if not stats["oldest_entry"] or entry.blacklisted_at < stats["oldest_entry"]:
                    stats["oldest_entry"] = entry.blacklisted_at
                
                if not stats["newest_entry"] or entry.blacklisted_at > stats["newest_entry"]:
                    stats["newest_entry"] = entry.blacklisted_at
            
            # Format timestamps
            if stats["oldest_entry"]:
                stats["oldest_entry"] = stats["oldest_entry"].isoformat()
            if stats["newest_entry"]:
                stats["newest_entry"] = stats["newest_entry"].isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting blacklist stats: {str(e)}")
            return {}
    
    # ============= INSTANCE METHODS =============
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert blacklist entry to dictionary
        
        Returns:
            dict: Dictionary representation (without exposing full token)
        """
        try:
            return {
                "token_preview": self.sk[:20] + "..." if len(self.sk) > 20 else self.sk,
                "blacklisted_at": self.blacklisted_at.isoformat() if self.blacklisted_at else None,
                "expires_at": self.expires_at.isoformat() if self.expires_at else None,
                "reason": self.reason,
                "user_id": self.user_id,
                "revoked_by": self.revoked_by,
                "is_expired": self.expires_at < datetime.utcnow() if self.expires_at else False
            }
        except Exception as e:
            logger.error(f"Error converting blacklist entry to dict: {str(e)}")
            return {}


# ============= UTILITY FUNCTIONS =============

def cleanup_expired_tokens_job():
    """
    Convenience function for running cleanup as a scheduled job
    
    Example usage in Django management command:
    from models.TokenBlacklist import cleanup_expired_tokens_job
    cleanup_expired_tokens_job()
    """
    try:
        result = TokenBlacklist.cleanup_expired_tokens(batch_size=500)
        
        if result.get("success"):
            logger.info(f"Token cleanup successful: {result.get('deleted_count')} tokens removed")
        else:
            logger.error(f"Token cleanup failed: {result.get('error', 'Unknown error')}")
        
        return result
    except Exception as e:
        logger.error(f"Token cleanup job failed: {str(e)}")
        return {"success": False, "error": str(e)}


def check_token_revoked(token: str) -> bool:
    """
    Simple helper function to check if a token is revoked
    
    Args:
        token: JWT token to check
    
    Returns:
        bool: True if revoked, False if valid
    """
    return TokenBlacklist.is_blacklisted(token)

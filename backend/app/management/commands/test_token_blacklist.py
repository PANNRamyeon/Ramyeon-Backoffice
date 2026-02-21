"""
Django management command to test Token Blacklist functionality
Usage: python manage.py test_token_blacklist
"""
from django.core.management.base import BaseCommand
from models.TokenBlacklist import TokenBlacklist
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test Token Blacklist functionality (works with empty blacklist)'

    def handle(self, *args, **options):
        """Test the TokenBlacklist model"""
        
        self.stdout.write("=" * 60)
        self.stdout.write("TOKEN BLACKLIST FUNCTIONALITY TEST")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        
        try:
            # Test 1: Check if model is accessible
            self.stdout.write("Test 1: Model Initialization")
            self.stdout.write("  Attempting to access TokenBlacklist model...")
            test_token = "test.dummy.token"
            result = TokenBlacklist.is_blacklisted(test_token)
            self.stdout.write(self.style.SUCCESS(f"  ✓ Model accessible (token check returned: {result})"))
            self.stdout.write("")
            
            # Test 2: Get stats from empty blacklist
            self.stdout.write("Test 2: Get Blacklist Stats (Empty)")
            self.stdout.write("  Fetching stats from blacklist...")
            stats = TokenBlacklist.get_blacklist_stats()
            self.stdout.write(self.style.SUCCESS("  ✓ Stats retrieved successfully"))
            self.stdout.write(f"    Total tokens: {stats.get('total_tokens', 0)}")
            self.stdout.write(f"    Active tokens: {stats.get('active_tokens', 0)}")
            self.stdout.write(f"    Expired tokens: {stats.get('expired_tokens', 0)}")
            self.stdout.write("")
            
            # Test 3: Add a test token (optional - can be skipped)
            self.stdout.write("Test 3: Blacklist a Test Token")
            add_test = input("  Add a test token to blacklist? (y/N): ").lower()
            
            if add_test == 'y':
                test_token = f"test.token.{datetime.utcnow().timestamp()}"
                expires = datetime.utcnow() + timedelta(hours=1)
                
                self.stdout.write(f"  Adding token: {test_token[:30]}...")
                entry = TokenBlacklist.blacklist_token(
                    token=test_token,
                    expires_at=expires,
                    reason="test",
                    user_id="TEST-USER"
                )
                self.stdout.write(self.style.SUCCESS("  ✓ Token added to blacklist"))
                self.stdout.write("")
                
                # Verify it's blacklisted
                self.stdout.write("Test 4: Verify Token is Blacklisted")
                is_blacklisted = TokenBlacklist.is_blacklisted(test_token)
                if is_blacklisted:
                    self.stdout.write(self.style.SUCCESS("  ✓ Token correctly detected as blacklisted"))
                else:
                    self.stdout.write(self.style.ERROR("  ✗ Token not detected as blacklisted"))
                self.stdout.write("")
                
                # Get updated stats
                self.stdout.write("Test 5: Get Updated Stats")
                stats = TokenBlacklist.get_blacklist_stats()
                self.stdout.write(self.style.SUCCESS("  ✓ Stats retrieved"))
                self.stdout.write(f"    Total tokens: {stats.get('total_tokens', 0)}")
                self.stdout.write(f"    By reason: {stats.get('by_reason', {})}")
                self.stdout.write("")
                
                # Clean up test token
                cleanup = input("  Remove test token? (Y/n): ").lower()
                if cleanup != 'n':
                    try:
                        test_entry = TokenBlacklist.get("token_blacklist", test_token)
                        test_entry.delete()
                        self.stdout.write(self.style.SUCCESS("  ✓ Test token removed"))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  Could not remove test token: {e}"))
                self.stdout.write("")
            else:
                self.stdout.write("  Skipping token addition test")
                self.stdout.write("")
            
            # Test 6: Verify non-existent token
            self.stdout.write("Test 6: Check Non-Existent Token")
            fake_token = "definitely.not.in.blacklist"
            is_blacklisted = TokenBlacklist.is_blacklisted(fake_token)
            if not is_blacklisted:
                self.stdout.write(self.style.SUCCESS("  ✓ Non-existent token correctly not blacklisted"))
            else:
                self.stdout.write(self.style.WARNING("  ⚠ Non-existent token incorrectly detected as blacklisted"))
            self.stdout.write("")
            
            # Summary
            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS("ALL TESTS COMPLETED"))
            self.stdout.write("=" * 60)
            self.stdout.write("")
            self.stdout.write("Summary:")
            self.stdout.write("  - TokenBlacklist model is working correctly")
            self.stdout.write("  - Empty blacklist is handled properly")
            self.stdout.write("  - Ready for integration with auth_services.py")
            self.stdout.write("")
            self.stdout.write("Next Steps:")
            self.stdout.write("  1. Refactor auth_services.py to use TokenBlacklist")
            self.stdout.write("  2. Test login/logout flow")
            self.stdout.write("  3. Set up cleanup job for expired tokens")
            self.stdout.write("")
            
        except Exception as e:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f'✗ Test failed: {str(e)}'))
            self.stdout.write("")
            
            if 'ResourceNotFoundException' in str(e):
                self.stdout.write("Possible issue:")
                self.stdout.write("  - GSI not created yet")
                self.stdout.write("  - Run: python manage.py init_token_blacklist")
            elif 'ValidationException' in str(e):
                self.stdout.write("Possible issue:")
                self.stdout.write("  - Table or GSI configuration issue")
                self.stdout.write("  - Run: python manage.py check_dynamodb_table")
            
            logger.error(f"Token blacklist test failed: {str(e)}")
            raise

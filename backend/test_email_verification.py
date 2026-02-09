"""
Test script for email verification
Run this from the backend directory: python test_email_verification.py
"""
import os
import sys
import django
import time

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'posbackend.settings')
django.setup()

from notifications.email_verification_service import email_verification_service
from app.database import db_manager

def test_email_verification_send():
    """Test sending verification email"""
    from decouple import config
    
    test_email = "ngjameswinston@gmail.com"
    
    print(f"\n{'='*60}")
    print(f"TEST 1: Sending Verification Email")
    print(f"{'='*60}")
    print(f"Testing email verification for: {test_email}")
    print("-" * 60)
    
    # Check configuration
    print("\nConfiguration Check:")
    api_key = config('SENDGRID_API_KEY', default='')
    from_email = config('SENDGRID_FROM_EMAIL', default='')
    from_name = config('SENDGRID_FROM_NAME', default='')
    
    print(f"  API Key: {'Set' if api_key else 'NOT SET'}")
    print(f"  From Email: {from_email}")
    print(f"  From Name: {from_name}")
    
    if not api_key:
        print("\n[ERROR] SENDGRID_API_KEY is not set in .env file!")
        return None, None
    
    if not from_email:
        print("\n[ERROR] SENDGRID_FROM_EMAIL is not set in .env file!")
        return None, None
    
    print("\nSending test email...")
    print("-" * 60)
    
    try:
        # MongoDB-specific user lookup. This needs to be refactored for DynamoDB.
        # For now, we'll mock the user data to allow the email sending test to proceed.
        # db = db_manager.get_database()
        user = {"_id": "mock-user-id", "username": "Test User", "email": test_email} # Mock user
        user_id = str(user.get('_id')) if user else None
        user_name = user.get('username') or user.get('full_name') or "Test User" if user else "Test User"
        
        # Send verification email
        result = email_verification_service.send_verification_code(
            email=test_email,
            user_id=user_id,
            user_name=user_name
        )
        
        if result.get('success'):
            print("\n[SUCCESS] Verification email sent successfully!")
            print(f"Message: {result.get('message', 'N/A')}")
            token = result.get('token')
            if token:
                print(f"Token received: {token[:50]}...")
                print("\nPlease check your email inbox (and spam folder) for the verification code.")
                return token, test_email
            else:
                print("\n[WARNING] No token returned!")
                return None, test_email
        else:
            print("\n[FAILED] Could not send verification email")
            print(f"Error: {result.get('error', 'Unknown error')}")
            if result.get('error_details'):
                print(f"Error Details: {result.get('error_details')}")
            print("\nTroubleshooting:")
            print("1. Make sure your Single Sender email is verified in SendGrid")
            print("2. Check that your API key has 'Mail Send' permissions")
            print("3. Verify the API key is correct in your .env file")
            return None, None
    
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


def test_token_verification(token, test_email):
    """Test token verification (without code)"""
    print(f"\n{'='*60}")
    print(f"TEST 2: Token Verification")
    print(f"{'='*60}")
    
    if not token:
        print("[SKIPPED] No token available from previous test")
        return False
    
    try:
        payload = email_verification_service.verify_token(token)
        
        if payload:
            print("\n[SUCCESS] Token is valid!")
            print(f"  Email: {payload.get('email')}")
            print(f"  User ID: {payload.get('user_id', 'N/A')}")
            print(f"  Token Type: {payload.get('type')}")
            return True
        else:
            print("\n[FAILED] Token verification failed - token is invalid or expired")
            return False
    
    except Exception as e:
        print(f"\n[ERROR] Token verification error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_invalid_code_verification(token, test_email):
    """Test verifying with invalid code"""
    print(f"\n{'='*60}")
    print(f"TEST 3: Invalid Code Verification")
    print(f"{'='*60}")
    
    if not token:
        print("[SKIPPED] No token available from previous test")
        return False
    
    try:
        invalid_code = "000000"
        result = email_verification_service.verify_code(token, invalid_code)
        
        if not result.get('success'):
            print("\n[SUCCESS] Invalid code correctly rejected!")
            print(f"  Error: {result.get('error', 'N/A')}")
            return True
        else:
            print("\n[FAILED] Invalid code was accepted (this should not happen)")
            return False
    
    except Exception as e:
        print(f"\n[ERROR] Invalid code test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_expired_token_handling():
    """Test that expired tokens are handled correctly"""
    print(f"\n{'='*60}")
    print(f"TEST 4: Expired Token Handling")
    print(f"{'='*60}")
    
    try:
        # Create an expired token manually (this is a mock test)
        from jose import jwt
        from decouple import config
        from datetime import datetime, timedelta, timezone
        
        secret = config('SECRET_KEY', default='your-secret-key-here-change-in-production')
        
        # Create a token that expired 1 minute ago
        expired_payload = {
            "email": "test@example.com",
            "code_hash": "test_hash",
            "type": "email_verification_code",
            "iat": int((datetime.now(timezone.utc) - timedelta(minutes=11)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
        }
        
        expired_token = jwt.encode(expired_payload, secret, algorithm="HS256")
        
        # Try to verify expired token
        result = email_verification_service.verify_token(expired_token)
        
        if result is None:
            print("\n[SUCCESS] Expired token correctly rejected!")
            return True
        else:
            print("\n[FAILED] Expired token was accepted (this should not happen)")
            return False
    
    except Exception as e:
        print(f"\n[ERROR] Expired token test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_email_verification():
    """Run all email verification tests"""
    print("\n" + "="*60)
    print("EMAIL VERIFICATION COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 1: Send verification email
    token, test_email = test_email_verification_send()
    results['send_email'] = token is not None
    
    # Test 2: Verify token (if we got one)
    if token:
        results['token_verification'] = test_token_verification(token, test_email)
        time.sleep(1)  # Small delay between tests
    else:
        results['token_verification'] = False
    
    # Test 3: Test invalid code
    if token:
        results['invalid_code'] = test_invalid_code_verification(token, test_email)
        time.sleep(1)
    else:
        results['invalid_code'] = False
    
    # Test 4: Test expired token handling
    results['expired_token'] = test_expired_token_handling()
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    for test_name, passed in results.items():
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\n  Total: {passed_tests}/{total_tests} tests passed")
    print(f"{'='*60}\n")
    
    # Note about code verification
    if token:
        print("NOTE: To fully test code verification, you need to:")
        print("  1. Check your email for the verification code")
        print("  2. Use the verify_code method with the actual code from email")
        print("  3. The token from this test can be used to verify the code")
        print(f"  Token: {token[:50]}...")
        print()
    
    return all(results.values())

if __name__ == "__main__":
    print("=" * 50)
    print("Email Verification Test")
    print("=" * 50)
    print()
    
    success = test_email_verification()
    
    print()
    print("=" * 50)
    if success:
        print("Test completed successfully!")
    else:
        print("Test failed. Please check the error messages above.")
    print("=" * 50)

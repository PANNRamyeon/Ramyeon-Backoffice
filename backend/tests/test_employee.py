import requests
import sys

BASE = "http://127.0.0.1:8000"
STAFF_EMAIL = "LBJ@gmail.com"          # Replace with actual staff email
STAFF_PASSWORD = "password1234"        # Replace with actual staff password

session = requests.Session()
session.headers.update({"Content-Type": "application/json"})

def login(email, password):
    """Login as staff and store token"""
    resp = session.post(f"{BASE}/api/v1/admin/auth/login/", json={
        "email": email,
        "password": password
    })
    if resp.status_code != 200:
        print(f"Staff login failed: {resp.text}")
        sys.exit(1)
    data = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        print("No access_token in login response")
        sys.exit(1)
    session.headers.update({"Authorization": f"Bearer {access_token}"})
    print("✓ Staff login successful")
    return access_token

def test_health():
    """Public health check (no auth needed)"""
    resp = session.get(f"{BASE}/api/v1/admin/users/health/")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print("✓ Health check passed (public)")

def test_current_user():
    """Any authenticated user can see their own profile"""
    resp = session.get(f"{BASE}/api/v1/admin/auth/me/")
    assert resp.status_code == 200, f"Current user failed: {resp.text}"
    user = resp.json()
    print(f"✓ Current user: {user.get('email')} (role: {user.get('role')})")

if __name__ == "__main__":
    # 1. Authenticate as staff
    login(STAFF_EMAIL, STAFF_PASSWORD)

    # 2. Public endpoint
    test_health()

    # 3. Authenticated self-profile
    test_current_user()

    print("\n=== Staff login test passed ===")
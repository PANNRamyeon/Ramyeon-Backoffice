import re
import requests
import time

BASE = "http://127.0.0.1:8000"

def api_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"

headers = {"Content-Type": "application/json"}

ADMIN_EMAIL = "jlin@gmail.com"
ADMIN_PASSWORD = "password1234"

# Unique suffix prevents name/email collisions across test runs.
UNIQUE_SUFFIX = str(int(time.time()))[-6:]
TEST_USERNAME = f"testuser_{UNIQUE_SUFFIX}"
TEST_EMAIL = f"testuser_{UNIQUE_SUFFIX}@example.com"


# ==================== AUTH ====================

def login():
    resp = requests.post(
        f"{BASE}/api/v1/admin/auth/login/",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, \
        f"Login failed ({resp.status_code}). Check ADMIN_EMAIL/ADMIN_PASSWORD.\n{resp.text}"
    token = resp.json().get("access_token")
    assert token, f"No access_token in login response: {resp.json()}"
    headers["Authorization"] = f"Bearer {token}"
    print(f"  ✓ Logged in as {ADMIN_EMAIL}")


# ==================== HELPERS ====================

def create_user(data):
    resp = requests.post(api_url("/users/"), json=data, headers=headers)
    assert resp.status_code == 201, f"Create user failed: {resp.text}"
    user = resp.json()
    print(f"  ✓ User created: {user['user_id']} ({user['username']})")
    return user

def get_user(user_id):
    resp = requests.get(api_url(f"/users/{user_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get user failed: {resp.text}"
    return resp.json()

def update_user(user_id, data):
    resp = requests.put(api_url(f"/users/{user_id}/"), json=data, headers=headers)
    assert resp.status_code == 200, f"Update user failed: {resp.text}"
    return resp.json()

def soft_delete_user(user_id):
    resp = requests.delete(api_url(f"/users/{user_id}/"), headers=headers)
    assert resp.status_code == 200, f"Soft delete failed: {resp.text}"

def hard_delete_user(user_id):
    resp = requests.delete(
        api_url(f"/users/{user_id}/hard-delete/"),
        params={"confirm": "yes"},
        headers=headers,
    )
    assert resp.status_code == 200, f"Hard delete failed: {resp.text}"

def restore_user(user_id):
    resp = requests.post(api_url(f"/users/{user_id}/restore/"), headers=headers)
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

def list_users(**params):
    resp = requests.get(api_url("/users/"), params=params, headers=headers)
    assert resp.status_code == 200, f"List users failed: {resp.text}"
    return resp.json()

def list_deleted_users(**params):
    resp = requests.get(api_url("/users/deleted/list/"), params=params, headers=headers)
    assert resp.status_code == 200, f"List deleted users failed: {resp.text}"
    return resp.json()

def cleanup_test_user(username):
    """Remove a test user by username if it exists — keeps runs idempotent."""
    body = list_users(search=username)
    for u in body.get("users", []):
        if u.get("username") == username:
            uid = u["user_id"]
            try:
                soft_delete_user(uid)
            except Exception:
                pass
            try:
                hard_delete_user(uid)
            except Exception:
                pass
            print(f"  ✓ Cleaned up existing user: {uid}")
            return

    del_body = list_deleted_users()
    for u in del_body.get("users", []):
        if u.get("username") == username:
            uid = u["user_id"]
            try:
                hard_delete_user(uid)
            except Exception:
                pass
            print(f"  ✓ Cleaned up deleted user: {uid}")
            return


# ==================== TESTS ====================

def test_health():
    print("\n[Health Check]")
    resp = requests.get(api_url("/users/health/"), headers=headers)
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    body = resp.json()
    assert body.get("status") == "active", f"Unexpected status: {body}"
    print(f"  ✓ Health check OK: {body.get('message')}")


def test_create_and_id_format():
    print("\n[Create & ID Format]")
    user = create_user({
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": "Secret123!",
        "full_name": "Test User",
        "role": "staff",
        "status": "active",
    })

    assert user["username"] == TEST_USERNAME
    assert user["email"] == TEST_EMAIL
    assert user["isDeleted"] is False

    uid = user["user_id"]
    assert re.match(r'^USER-\d+$', uid), \
        f"user_id should be USER-##### format, got: {uid}"
    print(f"  ✓ ID format correct: {uid}")

    return user


def test_list():
    print("\n[List Users]")
    body = list_users(page=1, limit=10)
    assert "users" in body, "Response missing 'users' key"
    assert "total" in body, "Response missing 'total' key"
    assert isinstance(body["users"], list), "'users' should be a list"
    print(f"  ✓ Listed {len(body['users'])} users (total {body['total']})")


def test_get_detail(user_id):
    print("\n[Get Detail]")
    user = get_user(user_id)
    assert user["user_id"] == user_id
    assert user["username"] == TEST_USERNAME
    print(f"  ✓ Detail fetched for {user_id}")


def test_404_on_unknown_id():
    print("\n[404 on Unknown ID]")
    resp = requests.get(api_url("/users/USER-999/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for unknown user, got {resp.status_code}"
    print("  ✓ 404 returned for non-existent user")


def test_update(user_id):
    print("\n[Update]")
    updated = update_user(user_id, {"full_name": "Updated Test User"})
    assert updated["full_name"] == "Updated Test User", "Update not applied"

    # Revert
    update_user(user_id, {"full_name": "Test User"})
    print("  ✓ Update applied and verified")


def test_search(user_id):
    print("\n[Search Filter]")
    body = list_users(search=UNIQUE_SUFFIX)
    users = body.get("users", [])
    assert any(u["user_id"] == user_id for u in users), \
        f"Test user not found in search results for '{UNIQUE_SUFFIX}'"
    print(f"  ✓ Search returned {len(users)} result(s) matching '{UNIQUE_SUFFIX}'")


def test_role_filter():
    print("\n[Role Filter]")
    body = list_users(role="staff")
    users = body.get("users", [])
    for u in users:
        assert u.get("role") == "staff", \
            f"Non-staff user in role=staff results: {u}"
    print(f"  ✓ Role filter returned {len(users)} staff user(s), all correct role")


def test_status_filter():
    print("\n[Status Filter]")
    body = list_users(status="active")
    users = body.get("users", [])
    for u in users:
        assert u.get("status") == "active", \
            f"Non-active user in status=active results: {u}"
    print(f"  ✓ Status filter returned {len(users)} active user(s)")


def test_search_by_email(email):
    print("\n[Search by Email]")
    resp = requests.get(api_url(f"/users/search/by-email/{email}/"), headers=headers)
    assert resp.status_code == 200, f"Search by email failed: {resp.text}"
    user = resp.json()
    assert user["email"] == email, f"Email mismatch: {user['email']}"
    print(f"  ✓ Found by email: {user['username']}")


def test_search_by_username(username):
    print("\n[Search by Username]")
    resp = requests.get(api_url(f"/users/search/by-username/{username}/"), headers=headers)
    assert resp.status_code == 200, f"Search by username failed: {resp.text}"
    user = resp.json()
    assert user["username"] == username, f"Username mismatch: {user['username']}"
    print(f"  ✓ Found by username: {user['username']}")


def test_search_by_email_404():
    print("\n[Search by Email — 404 on Unknown]")
    resp = requests.get(
        api_url("/users/search/by-email/nobody_999@nowhere.invalid/"),
        headers=headers,
    )
    assert resp.status_code == 404, \
        f"Expected 404 for unknown email, got {resp.status_code}"
    print("  ✓ 404 returned for unknown email")


def test_search_by_username_404():
    print("\n[Search by Username — 404 on Unknown]")
    resp = requests.get(
        api_url("/users/search/by-username/nobody_xyz_999/"),
        headers=headers,
    )
    assert resp.status_code == 404, \
        f"Expected 404 for unknown username, got {resp.status_code}"
    print("  ✓ 404 returned for unknown username")


def test_missing_required_fields_rejected():
    print("\n[Missing Required Fields Rejected]")

    # No username
    resp = requests.post(
        api_url("/users/"),
        json={"email": "nousername@test.com", "password": "Secret123!"},
        headers=headers,
    )
    assert resp.status_code in (400, 422), \
        f"Expected 400/422 for missing username, got {resp.status_code}"
    print(f"  ✓ Missing username rejected with {resp.status_code}")

    # No email
    resp = requests.post(
        api_url("/users/"),
        json={"username": "noemail_user", "password": "Secret123!"},
        headers=headers,
    )
    assert resp.status_code in (400, 422), \
        f"Expected 400/422 for missing email, got {resp.status_code}"
    print(f"  ✓ Missing email rejected with {resp.status_code}")

    # No password
    resp = requests.post(
        api_url("/users/"),
        json={"username": "nopassword_user", "email": "nopassword@test.com"},
        headers=headers,
    )
    assert resp.status_code in (400, 422), \
        f"Expected 400/422 for missing password, got {resp.status_code}"
    print(f"  ✓ Missing password rejected with {resp.status_code}")


def test_hard_delete_requires_confirm(user_id):
    print("\n[Hard Delete — confirm=yes Required]")
    resp = requests.delete(
        api_url(f"/users/{user_id}/hard-delete/"),
        headers=headers,
    )
    assert resp.status_code == 400, \
        f"Expected 400 without ?confirm=yes, got {resp.status_code}"
    print("  ✓ 400 returned when confirm param is missing")


def test_soft_delete_and_restore(user_id):
    print("\n[Soft Delete & Restore]")
    soft_delete_user(user_id)

    del_body = list_deleted_users()
    deleted_ids = [u["user_id"] for u in del_body.get("users", [])]
    assert user_id in deleted_ids, \
        f"{user_id} not found in deleted users list"
    print(f"  ✓ {user_id} appears in deleted list")

    body = list_users()
    active_ids = [u["user_id"] for u in body.get("users", [])]
    assert user_id not in active_ids, \
        f"{user_id} still appears in active list after soft delete"
    print("  ✓ Not in active list after soft delete")

    restore_user(user_id)
    user = get_user(user_id)
    assert user["isDeleted"] is False
    print(f"  ✓ {user_id} restored successfully")


def test_hard_delete(user_id):
    print("\n[Hard Delete]")
    # Soft-delete first so the user is in a known deleted state, then hard-delete.
    soft_delete_user(user_id)
    hard_delete_user(user_id)

    resp = requests.get(api_url(f"/users/{user_id}/"), headers=headers)
    assert resp.status_code == 404, \
        f"User should be gone after hard delete, got {resp.status_code}"
    print(f"  ✓ {user_id} permanently deleted and confirmed gone")


if __name__ == "__main__":
    print("=== Login ===")
    login()

    print("\n=== Pre-run cleanup ===")
    cleanup_test_user(TEST_USERNAME)
    print("  ✓ Cleanup done")

    # 1. Health check (no auth required)
    test_health()

    # 2. Create
    user = test_create_and_id_format()
    uid = user["user_id"]

    # 3. List
    test_list()

    # 4. Get detail
    test_get_detail(uid)

    # 5. 404 on unknown ID
    test_404_on_unknown_id()

    # 6. Update
    test_update(uid)

    # 7. Search filter
    test_search(uid)

    # 8. Role filter
    test_role_filter()

    # 9. Status filter
    test_status_filter()

    # 10. Search by email
    test_search_by_email(TEST_EMAIL)

    # 11. Search by username
    test_search_by_username(TEST_USERNAME)

    # 12. Search by email — 404
    test_search_by_email_404()

    # 13. Search by username — 404
    test_search_by_username_404()

    # 14. Missing required fields rejected
    test_missing_required_fields_rejected()

    # 15. Hard delete requires confirm param
    test_hard_delete_requires_confirm(uid)

    # 16. Soft delete + restore
    test_soft_delete_and_restore(uid)

    # 17. Hard delete (user is active again after restore)
    test_hard_delete(uid)

    print("\n=== All user tests passed ===")

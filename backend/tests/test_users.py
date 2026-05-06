import requests
import sys

BASE = "http://127.0.0.1:8000"

def api_url(path):
    """Full URL for a user endpoint under api/v1/admin/"""
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"

# No authentication headers
headers = {"Content-Type": "application/json"}

def test_health():
    resp = requests.get(api_url("/users/health/"), headers=headers)
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print("✓ Health check passed")

def create_user(data):
    resp = requests.post(api_url("/users/"), json=data, headers=headers)
    assert resp.status_code == 201, f"Create user failed: {resp.text}"
    user = resp.json()
    print(f"✓ User created: {user['user_id']} ({user['username']})")
    return user

def list_users(params=None):
    resp = requests.get(api_url("/users/"), params=params, headers=headers)
    assert resp.status_code == 200, f"List users failed: {resp.text}"
    return resp.json()

def get_user(user_id):
    resp = requests.get(api_url(f"/users/{user_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get user failed: {resp.text}"
    return resp.json()

def update_user(user_id, data):
    resp = requests.put(api_url(f"/users/{user_id}/"), json=data, headers=headers)
    assert resp.status_code == 200, f"Update user failed: {resp.text}"
    return resp.json()

def search_by_email(email):
    resp = requests.get(api_url(f"/users/search/by-email/{email}/"), headers=headers)
    assert resp.status_code == 200, f"Search by email failed: {resp.text}"
    return resp.json()

def search_by_username(username):
    resp = requests.get(api_url(f"/users/search/by-username/{username}/"), headers=headers)
    assert resp.status_code == 200, f"Search by username failed: {resp.text}"
    return resp.json()

def soft_delete_user(user_id):
    resp = requests.delete(api_url(f"/users/{user_id}/"), headers=headers)
    assert resp.status_code == 200, f"Soft delete failed: {resp.text}"
    print("✓ User soft deleted")

def get_deleted_users(params=None):
    resp = requests.get(api_url("/users/deleted/list/"), params=params, headers=headers)
    assert resp.status_code == 200, f"Get deleted users failed: {resp.text}"
    return resp.json()

def restore_user(user_id):
    resp = requests.post(api_url(f"/users/{user_id}/restore/"), headers=headers)
    assert resp.status_code == 200, f"Restore failed: {resp.text}"
    print("✓ User restored")

def hard_delete_user(user_id):
    resp = requests.delete(api_url(f"/users/{user_id}/hard-delete/?confirm=yes"), headers=headers)
    assert resp.status_code == 200, f"Hard delete failed: {resp.text}"
    print("✓ User permanently deleted")


if __name__ == "__main__":
    # 1. Health check
    test_health()

    # 2. Create a test user
    new_user = create_user({
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "Secret123!",
        "full_name": "Test User",
        "role": "staff",
        "status": "active"
    })
    user_id = new_user["user_id"]

    # 3. List users
    users_list = list_users({"page": 1, "limit": 5})
    print(f"✓ Listed {len(users_list['users'])} users (total {users_list['total']})")

    # 4. Get user detail
    user_detail = get_user(user_id)
    print(f"✓ User detail: {user_detail['username']}")

    # 5. Update user
    updated = update_user(user_id, {"full_name": "Updated Test User"})
    assert updated["full_name"] == "Updated Test User", "Update not applied"
    print("✓ User updated")

    # 6. Search by email (URL pattern must be fixed)
    found = search_by_email(new_user["email"])
    assert found["email"] == new_user["email"], "Email mismatch"
    print(f"✓ Found by email: {found['username']}")

    # 7. Search by username
    found = search_by_username(new_user["username"])
    assert found["username"] == new_user["username"], "Username mismatch"
    print(f"✓ Found by username: {found['username']}")

    # 8. Soft delete
    soft_delete_user(user_id)

    # 9. Check deleted list
    deleted = get_deleted_users({"page": 1, "limit": 10})
    assert any(u["user_id"] == user_id for u in deleted["users"]), "Not in deleted list"
    print("✓ User appears in deleted list")

    # 10. Restore user
    restore_user(user_id)

    # Verify restored
    restored = get_user(user_id)
    assert not restored["isDeleted"], "User still deleted"
    print("✓ User active after restore")

    # 11. Hard delete (permanent)
    hard_delete_user(user_id)

    # Verify gone
    resp = requests.get(api_url(f"/users/{user_id}/"), headers=headers)
    assert resp.status_code == 404, "User still exists after hard delete"
    print("✓ Hard delete verified")

    print("\n=== All tests passed ===")
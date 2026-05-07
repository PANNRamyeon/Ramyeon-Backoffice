import re
import requests

BASE = "http://127.0.0.1:8000"

def api_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"

headers = {"Content-Type": "application/json"}

# ==================== HELPERS ====================

def register_customer(email, password, extra=None):
    data = {"email": email, "password": password}
    if extra:
        data.update(extra)
    resp = requests.post(api_url("/customers/register/"), json=data, headers=headers)
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    customer = resp.json()["customer"]
    print(f"  ✓ Registered: {customer['id']} ({customer['email']})")
    return customer

def login_customer(email, password):
    resp = requests.post(api_url("/customers/login/"), json={"email": email, "password": password}, headers=headers)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()

def get_customer(customer_id):
    resp = requests.get(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get failed: {resp.text}"
    return resp.json()

def update_customer(customer_id, data):
    resp = requests.put(api_url(f"/customers/{customer_id}/"), json=data, headers=headers)
    assert resp.status_code == 200, f"Update failed: {resp.text}"
    return resp.json()

def soft_delete_customer(customer_id):
    resp = requests.delete(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 200, f"Soft delete failed: {resp.text}"

def restore_customer(customer_id):
    resp = requests.post(api_url(f"/customers/{customer_id}/restore/"), headers=headers)
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

def hard_delete_customer(customer_id):
    resp = requests.delete(api_url(f"/customers/{customer_id}/hard-delete/?confirm=yes"), headers=headers)
    assert resp.status_code == 200, f"Hard delete failed: {resp.text}"

def cleanup_test_customer(email):
    """Remove a test customer if it already exists — keeps runs idempotent."""
    resp = requests.get(api_url("/customers/by-email/"), params={"email": email}, headers=headers)
    if resp.status_code == 200:
        cid = resp.json().get("customer_id")
        if cid:
            try:
                soft_delete_customer(cid)
                hard_delete_customer(cid)
            except Exception:
                pass

# ==================== TESTS ====================

def test_registration_and_id_format():
    print("\n[Registration & ID Format]")
    cust = register_customer("test_cust1@example.com", "securepass123", {
        "first_name": "Test", "last_name": "User1",
        "phone": "09123456789", "source": "web"
    })
    assert cust["email"] == "test_cust1@example.com"
    assert cust["loyalty_points"] == 0
    assert cust["auth_mode"] == "email_password"

    # 5-digit ID format: CUST-00001
    assert re.match(r'^CUST-\d{5}$', cust["id"]), \
        f"ID format wrong (expected CUST-#####, got {cust['id']})"
    print(f"  ✓ ID format correct: {cust['id']}")
    return cust

def test_duplicate_registration_rejected():
    print("\n[Duplicate Registration]")
    resp = requests.post(api_url("/customers/register/"), json={
        "email": "test_cust1@example.com", "password": "other"
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    print("  ✓ Duplicate email rejected with 400")

def test_login(email, password):
    print("\n[Login]")
    tokens = login_customer(email, password)
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    print("  ✓ Login returned access and refresh tokens")

    wrong = requests.post(api_url("/customers/login/"), json={
        "email": email, "password": "wrongpassword"
    }, headers=headers)
    assert wrong.status_code == 401, f"Expected 401, got {wrong.status_code}"
    print("  ✓ Wrong password rejected with 401")
    return tokens

def test_get_and_update(customer_id):
    print("\n[Get & Update]")
    detail = get_customer(customer_id)
    assert detail["email"] == "test_cust1@example.com"
    print("  ✓ Customer detail retrieved")

    updated = update_customer(customer_id, {
        "full_name": "Test User One Updated",
        "phone_number": "09987654321"
    })
    assert updated["full_name"] == "Test User One Updated"
    assert updated["phone_number"] == "09987654321"
    print("  ✓ Profile update applied")

    # Disallowed field should be silently ignored
    resp = requests.put(api_url(f"/customers/{customer_id}/"), json={
        "status": "banned"
    }, headers=headers)
    assert resp.status_code == 200
    detail_after = get_customer(customer_id)
    assert detail_after["status"] == "active", "Disallowed field 'status' should be ignored"
    print("  ✓ Disallowed field ignored on update")

def test_password_change(customer_id):
    print("\n[Password Change]")
    resp = requests.put(api_url(f"/customers/{customer_id}/"), json={
        "password": "newpass456"
    }, headers=headers)
    assert resp.status_code == 200

    tokens = login_customer("test_cust1@example.com", "newpass456")
    assert "access_token" in tokens
    print("  ✓ Password changed and new login confirmed")

    # Reset to original for remaining tests
    requests.put(api_url(f"/customers/{customer_id}/"), json={
        "password": "securepass123"
    }, headers=headers)

def test_loyalty_points(customer_id):
    print("\n[Loyalty Points]")
    resp = requests.post(api_url(f"/customers/{customer_id}/loyalty/"), json={
        "points": 50, "reason": "Test bonus"
    }, headers=headers)
    assert resp.status_code == 200
    assert get_customer(customer_id)["loyalty_points"] == 50
    print("  ✓ 50 points added")

    resp = requests.post(api_url(f"/customers/{customer_id}/loyalty/"), json={
        "points": 30, "reason": "Second bonus"
    }, headers=headers)
    assert resp.status_code == 200
    assert get_customer(customer_id)["loyalty_points"] == 80
    print("  ✓ 30 more points added (total 80)")

    # Zero/negative points rejected
    for bad_points in [0, -10]:
        resp = requests.post(api_url(f"/customers/{customer_id}/loyalty/"), json={
            "points": bad_points
        }, headers=headers)
        assert resp.status_code == 400, f"Expected 400 for points={bad_points}"
    print("  ✓ Zero/negative points rejected with 400")

def test_list_and_pagination():
    print("\n[List & Pagination]")
    page1 = requests.get(api_url("/customers/"), params={"limit": 2}, headers=headers)
    assert page1.status_code == 200
    body = page1.json()
    assert len(body["customers"]) <= 2
    assert "next_key" in body
    assert "has_more" in body
    print(f"  ✓ Page 1: {len(body['customers'])} customers, has_more={body['has_more']}")

    if body["has_more"] and body["next_key"]:
        page2 = requests.get(api_url("/customers/"), params={
            "limit": 2, "start_key": body["next_key"]
        }, headers=headers)
        assert page2.status_code == 200
        assert len(page2.json()["customers"]) > 0
        print(f"  ✓ Page 2: {len(page2.json()['customers'])} customers")

def test_search(customer_id):
    print("\n[Search]")
    resp = requests.get(api_url("/customers/search/"), params={"q": "test_cust1"}, headers=headers)
    assert resp.status_code == 200
    results = resp.json()
    assert any(c["customer_id"] == customer_id for c in results), \
        "Created customer not found in search results"
    print(f"  ✓ Search returned {len(results)} results, target customer found")

    # Empty search term rejected
    resp = requests.get(api_url("/customers/search/"), params={"q": ""}, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for empty search, got {resp.status_code}"
    print("  ✓ Empty search term rejected with 400")

def test_get_by_email(customer_id):
    print("\n[Get by Email]")
    resp = requests.get(api_url("/customers/by-email/"), params={
        "email": "test_cust1@example.com"
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["customer_id"] == customer_id
    print("  ✓ Found by email")

    resp = requests.get(api_url("/customers/by-email/"), params={
        "email": "nonexistent@nowhere.com"
    }, headers=headers)
    assert resp.status_code == 404
    print("  ✓ Unknown email returns 404")

    # Missing email param
    resp = requests.get(api_url("/customers/by-email/"), headers=headers)
    assert resp.status_code == 400
    print("  ✓ Missing email param returns 400")

def test_statistics():
    print("\n[Statistics]")
    resp = requests.get(api_url("/customers/statistics/"), headers=headers)
    assert resp.status_code == 200
    stats = resp.json()
    assert "total_customers" in stats
    assert stats["total_customers"] > 0
    assert "status_distribution" in stats
    assert "auth_mode_distribution" in stats
    assert "total_loyalty_points" in stats
    print(f"  ✓ Statistics: {stats['total_customers']} total customers")

def test_qr_generate_and_verify(customer_id):
    print("\n[QR Code]")

    # Default expiry (720h / 30 days)
    resp = requests.get(api_url(f"/customers/{customer_id}/qr/"), headers=headers)
    assert resp.status_code == 200, f"QR generate failed: {resp.text}"
    body = resp.json()
    assert "qr_token" in body
    assert body["expires_in_hours"] == 720
    token = body["qr_token"]
    print(f"  ✓ Default QR token generated (expires_in_hours={body['expires_in_hours']})")

    # Explicit 720h (30 days) — previously would have been rejected by the old 168h cap
    resp = requests.get(api_url(f"/customers/{customer_id}/qr/"), params={
        "expiry_hours": 720
    }, headers=headers)
    assert resp.status_code == 200, f"720h QR rejected: {resp.text}"
    print("  ✓ 720h (30-day) expiry accepted")

    # Short-lived token accepted
    resp = requests.get(api_url(f"/customers/{customer_id}/qr/"), params={
        "expiry_hours": 1
    }, headers=headers)
    assert resp.status_code == 200
    print("  ✓ 1h expiry accepted")

    # Out-of-range expiry rejected
    resp = requests.get(api_url(f"/customers/{customer_id}/qr/"), params={
        "expiry_hours": 721
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for 721h, got {resp.status_code}"
    print("  ✓ 721h expiry rejected with 400")

    resp = requests.get(api_url(f"/customers/{customer_id}/qr/"), params={
        "expiry_hours": 0
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for 0h, got {resp.status_code}"
    print("  ✓ 0h expiry rejected with 400")

    # Verify valid token
    resp = requests.post(api_url("/qr/verify/"), json={"token": token}, headers=headers)
    assert resp.status_code == 200, f"QR verify failed: {resp.text}"
    verified = resp.json()
    assert verified["valid"] is True
    assert verified["customer"]["customer_id"] == customer_id
    print(f"  ✓ Token verified — resolves to {customer_id}")

    # Verify invalid token returns 401
    resp = requests.post(api_url("/qr/verify/"), json={"token": "this.is.not.valid"}, headers=headers)
    assert resp.status_code == 401, f"Expected 401 for bad token, got {resp.status_code}"
    print("  ✓ Invalid token returns 401")

    # Missing token body returns 400
    resp = requests.post(api_url("/qr/verify/"), json={}, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for missing token, got {resp.status_code}"
    print("  ✓ Missing token body returns 400")

    # QR for non-existent customer returns 404
    resp = requests.get(api_url("/customers/CUST-99999/qr/"), headers=headers)
    assert resp.status_code == 404, f"Expected 404 for unknown customer, got {resp.status_code}"
    print("  ✓ QR for non-existent customer returns 404")

def test_soft_delete_and_restore(customer_id):
    print("\n[Soft Delete & Restore]")
    soft_delete_customer(customer_id)

    resp = requests.get(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 404, "Soft-deleted customer should return 404"
    print("  ✓ Soft-deleted customer not accessible (404)")

    restore_customer(customer_id)
    restored = get_customer(customer_id)
    assert restored["isDeleted"] is False
    assert restored["status"] == "active"
    print("  ✓ Restored customer is active")

def test_hard_delete(customer_id):
    print("\n[Hard Delete]")

    # Confirm required
    resp = requests.delete(api_url(f"/customers/{customer_id}/hard-delete/"), headers=headers)
    assert resp.status_code == 400, f"Expected 400 without confirm, got {resp.status_code}"
    print("  ✓ Hard delete without confirm=yes rejected")

    hard_delete_customer(customer_id)
    resp = requests.get(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 404, "Customer should be permanently gone after hard delete"
    print("  ✓ Customer permanently deleted and confirmed gone")


if __name__ == "__main__":
    TEST_EMAIL = "test_cust1@example.com"
    TEST_PASS = "securepass123"

    print("=== Pre-run cleanup ===")
    cleanup_test_customer(TEST_EMAIL)
    print("  ✓ Pre-run cleanup done")

    # Run all tests in sequence
    cust = test_registration_and_id_format()
    cid = cust["id"]

    test_duplicate_registration_rejected()
    test_login(TEST_EMAIL, TEST_PASS)
    test_get_and_update(cid)
    test_password_change(cid)
    test_loyalty_points(cid)
    test_list_and_pagination()
    test_search(cid)
    test_get_by_email(cid)
    test_statistics()
    test_qr_generate_and_verify(cid)
    test_soft_delete_and_restore(cid)
    test_hard_delete(cid)

    print("\n=== All customer tests passed ===")

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

# Unique suffix prevents email/username collisions across test runs.
UNIQUE_SUFFIX = str(int(time.time()))[-6:]
TEST_EMAIL = f"test_cust_{UNIQUE_SUFFIX}@example.com"
TEST_PASS = "securepass123"


# ==================== AUTH ====================
# NOTE: Customer views currently have no @require_authentication decorators.
# login() is included so tests continue to work when auth is re-enabled.

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
    resp = requests.post(
        api_url("/customers/login/"),
        json={"email": email, "password": password},
        headers=headers,
    )
    assert resp.status_code == 200, f"Customer login failed: {resp.text}"
    return resp.json()

def get_customer(customer_id):
    resp = requests.get(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get customer failed: {resp.text}"
    return resp.json()

def update_customer(customer_id, data):
    resp = requests.put(api_url(f"/customers/{customer_id}/"), json=data, headers=headers)
    assert resp.status_code == 200, f"Update customer failed: {resp.text}"
    return resp.json()

def soft_delete_customer(customer_id):
    resp = requests.delete(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 200, f"Soft delete failed: {resp.text}"

def restore_customer(customer_id):
    resp = requests.post(api_url(f"/customers/{customer_id}/restore/"), headers=headers)
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

def hard_delete_customer(customer_id):
    resp = requests.delete(
        api_url(f"/customers/{customer_id}/hard-delete/"),
        params={"confirm": "yes"},
        headers=headers,
    )
    assert resp.status_code == 200, f"Hard delete failed: {resp.text}"

def cleanup_test_customer(email):
    """Remove a test customer by email if it exists — keeps runs idempotent."""
    resp = requests.get(api_url("/customers/by-email/"), params={"email": email}, headers=headers)
    if resp.status_code == 200:
        cid = resp.json().get("customer_id")
        if cid:
            try:
                soft_delete_customer(cid)
            except Exception:
                pass
            try:
                hard_delete_customer(cid)
            except Exception:
                pass
            print(f"  ✓ Cleaned up existing customer: {cid}")


# ==================== TESTS ====================

def test_registration_and_id_format():
    print("\n[Registration & ID Format]")
    cust = register_customer(TEST_EMAIL, TEST_PASS, {
        "first_name": "Test",
        "last_name": "Customer",
        "phone": "09123456789",
        "source": "web",
    })
    assert cust["email"] == TEST_EMAIL
    assert cust["loyalty_points"] == 0
    assert cust["auth_mode"] == "email_password"

    cid = cust["id"]
    assert re.match(r'^CUST-\d+$', cid), \
        f"ID format wrong (expected CUST-#####, got {cid})"
    print(f"  ✓ ID format correct: {cid}")
    return cust


def test_duplicate_registration_rejected():
    print("\n[Duplicate Registration Rejected]")
    resp = requests.post(
        api_url("/customers/register/"),
        json={"email": TEST_EMAIL, "password": "other"},
        headers=headers,
    )
    assert resp.status_code == 400, \
        f"Expected 400 for duplicate email, got {resp.status_code}"
    print("  ✓ Duplicate email rejected with 400")


def test_missing_credentials_rejected():
    print("\n[Missing Credentials Rejected]")
    resp = requests.post(api_url("/customers/register/"), json={"email": TEST_EMAIL}, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for missing password, got {resp.status_code}"
    print("  ✓ Missing password rejected with 400")

    resp = requests.post(api_url("/customers/register/"), json={"password": TEST_PASS}, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for missing email, got {resp.status_code}"
    print("  ✓ Missing email rejected with 400")


def test_login(email, password):
    print("\n[Customer Login]")
    tokens = login_customer(email, password)
    assert "access_token" in tokens, "Missing access_token in login response"
    assert "refresh_token" in tokens, "Missing refresh_token in login response"
    print("  ✓ Login returned access and refresh tokens")

    wrong = requests.post(
        api_url("/customers/login/"),
        json={"email": email, "password": "wrongpassword"},
        headers=headers,
    )
    assert wrong.status_code == 401, \
        f"Expected 401 for wrong password, got {wrong.status_code}"
    print("  ✓ Wrong password rejected with 401")
    return tokens


def test_get_detail(customer_id):
    print("\n[Get Detail]")
    detail = get_customer(customer_id)
    assert detail["email"] == TEST_EMAIL
    assert "customer_id" in detail
    assert "loyalty_points" in detail
    assert detail["isDeleted"] is False
    print(f"  ✓ Detail retrieved for {customer_id}")


def test_404_on_unknown_id():
    print("\n[404 on Unknown ID]")
    resp = requests.get(api_url("/customers/CUST-99999/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for unknown customer, got {resp.status_code}"
    print("  ✓ 404 returned for non-existent customer")


def test_update(customer_id):
    print("\n[Update]")
    updated = update_customer(customer_id, {
        "full_name": "Test Customer Updated",
        "phone_number": "09987654321",
    })
    assert updated["full_name"] == "Test Customer Updated"
    assert updated["phone_number"] == "09987654321"
    print("  ✓ Profile update applied")

    # Disallowed field (status) should be silently ignored
    resp = requests.put(
        api_url(f"/customers/{customer_id}/"),
        json={"status": "banned"},
        headers=headers,
    )
    assert resp.status_code == 200
    detail_after = get_customer(customer_id)
    assert detail_after["status"] == "active", \
        "Disallowed field 'status' should be ignored"
    print("  ✓ Disallowed field 'status' silently ignored on update")


def test_password_change(customer_id):
    print("\n[Password Change]")
    resp = requests.put(
        api_url(f"/customers/{customer_id}/"),
        json={"password": "newpass456"},
        headers=headers,
    )
    assert resp.status_code == 200

    tokens = login_customer(TEST_EMAIL, "newpass456")
    assert "access_token" in tokens
    print("  ✓ Password changed and new login confirmed")

    # Reset to original for remaining tests
    requests.put(
        api_url(f"/customers/{customer_id}/"),
        json={"password": TEST_PASS},
        headers=headers,
    )
    print("  ✓ Password reset to original")


def test_loyalty_points(customer_id):
    print("\n[Loyalty Points]")
    resp = requests.post(
        api_url(f"/customers/{customer_id}/loyalty/"),
        json={"points": 50, "reason": "Test bonus"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert get_customer(customer_id)["loyalty_points"] == 50
    print("  ✓ 50 points added (total 50)")

    resp = requests.post(
        api_url(f"/customers/{customer_id}/loyalty/"),
        json={"points": 30, "reason": "Second bonus"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert get_customer(customer_id)["loyalty_points"] == 80
    print("  ✓ 30 more points added (total 80)")

    for bad_points in [0, -10]:
        resp = requests.post(
            api_url(f"/customers/{customer_id}/loyalty/"),
            json={"points": bad_points},
            headers=headers,
        )
        assert resp.status_code == 400, \
            f"Expected 400 for points={bad_points}, got {resp.status_code}"
    print("  ✓ Zero/negative points rejected with 400")


def test_list_and_pagination():
    print("\n[List & Pagination]")
    page1 = requests.get(api_url("/customers/"), params={"limit": 2}, headers=headers)
    assert page1.status_code == 200
    body = page1.json()
    assert "customers" in body, "Response missing 'customers' key"
    assert "next_key" in body, "Response missing 'next_key' key"
    assert "has_more" in body, "Response missing 'has_more' key"
    assert len(body["customers"]) <= 2
    print(f"  ✓ Page 1: {len(body['customers'])} customers, has_more={body['has_more']}")

    if body["has_more"] and body["next_key"]:
        page2 = requests.get(api_url("/customers/"), params={
            "limit": 2,
            "start_key": body["next_key"],
        }, headers=headers)
        assert page2.status_code == 200
        assert len(page2.json()["customers"]) > 0
        print(f"  ✓ Page 2: {len(page2.json()['customers'])} customers via cursor")


def test_list_status_filter():
    print("\n[List — Status Filter]")
    resp = requests.get(api_url("/customers/"), params={"status": "active"}, headers=headers)
    assert resp.status_code == 200
    customers = resp.json()["customers"]
    for c in customers:
        assert c.get("status") == "active", \
            f"Non-active customer in status=active results: {c}"
    print(f"  ✓ Status filter returned {len(customers)} active customer(s)")


def test_list_loyalty_filter(customer_id):
    print("\n[List — Loyalty Points Filter]")
    resp = requests.get(
        api_url("/customers/"),
        params={"min_loyalty_points": 50, "max_loyalty_points": 100},
        headers=headers,
    )
    assert resp.status_code == 200
    customers = resp.json()["customers"]
    assert any(c["customer_id"] == customer_id for c in customers), \
        f"Test customer (80 pts) not found in 50–100 range filter"
    print(f"  ✓ Loyalty range filter returned {len(customers)} customer(s), test customer included")


def test_search(customer_id):
    print("\n[Search]")
    resp = requests.get(api_url("/customers/search/"), params={"q": UNIQUE_SUFFIX}, headers=headers)
    assert resp.status_code == 200
    results = resp.json()
    assert any(c["customer_id"] == customer_id for c in results), \
        f"Test customer not found in search results for '{UNIQUE_SUFFIX}'"
    print(f"  ✓ Search returned {len(results)} result(s), test customer found")

    resp = requests.get(api_url("/customers/search/"), params={"q": ""}, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for empty search term, got {resp.status_code}"
    print("  ✓ Empty search term rejected with 400")


def test_get_by_email(customer_id):
    print("\n[Get by Email]")
    resp = requests.get(
        api_url("/customers/by-email/"),
        params={"email": TEST_EMAIL},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["customer_id"] == customer_id
    print("  ✓ Found by email, customer_id matches")

    resp = requests.get(
        api_url("/customers/by-email/"),
        params={"email": "nonexistent@nowhere.invalid"},
        headers=headers,
    )
    assert resp.status_code == 404
    print("  ✓ Unknown email returns 404")

    resp = requests.get(api_url("/customers/by-email/"), headers=headers)
    assert resp.status_code == 400
    print("  ✓ Missing email param returns 400")


def test_statistics():
    print("\n[Statistics]")
    resp = requests.get(api_url("/customers/statistics/"), headers=headers)
    assert resp.status_code == 200
    stats = resp.json()
    assert "total_customers" in stats, "Response missing 'total_customers'"
    assert stats["total_customers"] > 0
    assert "status_distribution" in stats, "Response missing 'status_distribution'"
    assert "auth_mode_distribution" in stats, "Response missing 'auth_mode_distribution'"
    assert "total_loyalty_points" in stats, "Response missing 'total_loyalty_points'"
    print(f"  ✓ Statistics: {stats['total_customers']} total customers")


def test_export_endpoint():
    print("\n[Export Endpoint]")
    resp = requests.get(api_url("/customers/export/"), headers=headers)
    assert resp.status_code in (200, 404), \
        f"Expected 200 or 404 from export endpoint, got {resp.status_code}"
    if resp.status_code == 200:
        ct = resp.headers.get("Content-Type", "")
        assert "csv" in ct or "json" in ct or "application" in ct, \
            f"Unexpected Content-Type for export: {ct}"
        print(f"  ✓ Export returned 200 (Content-Type: {ct})")
    else:
        print("  ~ Export endpoint returned 404 (not yet implemented)")


def test_qr_generate_and_verify(customer_id):
    print("\n[QR Code]")

    # Default expiry
    resp = requests.get(api_url(f"/customers/{customer_id}/qr/"), headers=headers)
    assert resp.status_code == 200, f"QR generate failed: {resp.text}"
    body = resp.json()
    assert "qr_token" in body, "Response missing 'qr_token'"
    assert body["expires_in_hours"] == 720
    token = body["qr_token"]
    print(f"  ✓ Default QR token generated (expires_in_hours={body['expires_in_hours']})")

    # Explicit 720h accepted
    resp = requests.get(
        api_url(f"/customers/{customer_id}/qr/"),
        params={"expiry_hours": 720},
        headers=headers,
    )
    assert resp.status_code == 200, f"720h QR rejected: {resp.text}"
    print("  ✓ 720h (30-day) expiry accepted")

    # Short-lived token accepted
    resp = requests.get(
        api_url(f"/customers/{customer_id}/qr/"),
        params={"expiry_hours": 1},
        headers=headers,
    )
    assert resp.status_code == 200
    print("  ✓ 1h expiry accepted")

    # Out-of-range expiry rejected
    resp = requests.get(
        api_url(f"/customers/{customer_id}/qr/"),
        params={"expiry_hours": 721},
        headers=headers,
    )
    assert resp.status_code == 400, f"Expected 400 for 721h, got {resp.status_code}"
    print("  ✓ 721h expiry rejected with 400")

    resp = requests.get(
        api_url(f"/customers/{customer_id}/qr/"),
        params={"expiry_hours": 0},
        headers=headers,
    )
    assert resp.status_code == 400, f"Expected 400 for 0h, got {resp.status_code}"
    print("  ✓ 0h expiry rejected with 400")

    # Verify valid token
    resp = requests.post(api_url("/qr/verify/"), json={"token": token}, headers=headers)
    assert resp.status_code == 200, f"QR verify failed: {resp.text}"
    verified = resp.json()
    assert verified["valid"] is True
    assert verified["customer"]["customer_id"] == customer_id
    print(f"  ✓ Token verified — resolves to {customer_id}")

    # Invalid token returns 401
    resp = requests.post(api_url("/qr/verify/"), json={"token": "this.is.not.valid"}, headers=headers)
    assert resp.status_code == 401, \
        f"Expected 401 for bad token, got {resp.status_code}"
    print("  ✓ Invalid token returns 401")

    # Missing token body returns 400
    resp = requests.post(api_url("/qr/verify/"), json={}, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for missing token, got {resp.status_code}"
    print("  ✓ Missing token body returns 400")

    # QR for non-existent customer returns 404
    resp = requests.get(api_url("/customers/CUST-99999/qr/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for unknown customer QR, got {resp.status_code}"
    print("  ✓ QR for non-existent customer returns 404")


def test_soft_delete_and_restore(customer_id):
    print("\n[Soft Delete & Restore]")
    soft_delete_customer(customer_id)

    resp = requests.get(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 404, \
        "Soft-deleted customer should return 404"
    print("  ✓ Soft-deleted customer not accessible (404)")

    restore_customer(customer_id)
    restored = get_customer(customer_id)
    assert restored["isDeleted"] is False
    assert restored["status"] == "active"
    print("  ✓ Restored customer is active")


def test_hard_delete(customer_id):
    print("\n[Hard Delete]")

    # Confirm required
    resp = requests.delete(
        api_url(f"/customers/{customer_id}/hard-delete/"),
        headers=headers,
    )
    assert resp.status_code == 400, \
        f"Expected 400 without ?confirm=yes, got {resp.status_code}"
    print("  ✓ Hard delete without confirm=yes rejected with 400")

    hard_delete_customer(customer_id)
    resp = requests.get(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 404, \
        "Customer should be permanently gone after hard delete"
    print(f"  ✓ {customer_id} permanently deleted and confirmed gone")


if __name__ == "__main__":
    print("=== Login ===")
    login()

    print("\n=== Pre-run cleanup ===")
    cleanup_test_customer(TEST_EMAIL)
    print("  ✓ Cleanup done")

    # 1. Register
    cust = test_registration_and_id_format()
    cid = cust["id"]

    # 2. Duplicate registration rejected
    test_duplicate_registration_rejected()

    # 3. Missing credentials rejected
    test_missing_credentials_rejected()

    # 4. Customer login
    test_login(TEST_EMAIL, TEST_PASS)

    # 5. Get detail
    test_get_detail(cid)

    # 6. 404 on unknown ID
    test_404_on_unknown_id()

    # 7. Update profile
    test_update(cid)

    # 8. Password change
    test_password_change(cid)

    # 9. Loyalty points
    test_loyalty_points(cid)

    # 10. List & pagination
    test_list_and_pagination()

    # 11. List — status filter
    test_list_status_filter()

    # 12. List — loyalty points range filter
    test_list_loyalty_filter(cid)

    # 13. Search
    test_search(cid)

    # 14. Get by email
    test_get_by_email(cid)

    # 15. Statistics
    test_statistics()

    # 16. Export endpoint
    test_export_endpoint()

    # 17. QR code generate + verify
    test_qr_generate_and_verify(cid)

    # 18. Soft delete + restore
    test_soft_delete_and_restore(cid)

    # 19. Hard delete
    test_hard_delete(cid)

    print("\n=== All customer tests passed ===")

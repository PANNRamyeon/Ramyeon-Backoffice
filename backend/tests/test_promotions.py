import re
import requests
import time
from datetime import datetime, timezone, timedelta

BASE = "http://127.0.0.1:8000"

def api_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"

headers = {"Content-Type": "application/json"}

ADMIN_EMAIL = "jlin@gmail.com"
ADMIN_PASSWORD = "password1234"

# Unique suffix prevents name collisions across test runs.
UNIQUE_SUFFIX = str(int(time.time()))[-6:]
TEST_PROMO_STD_NAME = f"Standard 10% Off {UNIQUE_SUFFIX}"
TEST_PROMO_REC_NAME = f"Sweldo Sale 5% {UNIQUE_SUFFIX}"


# ==================== AUTH ====================
# NOTE: All promotion view auth decorators are currently commented out (# COMMENTED FOR TESTING).
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

def create_promotion(data):
    resp = requests.post(api_url("/promotions/"), json=data, headers=headers)
    assert resp.status_code == 201, f"Create promotion failed: {resp.text}"
    promo = resp.json()["promotion"]
    print(f"  ✓ Promotion created: {promo['promotion_id']} ({promo['name']})")
    return promo

def get_promotion(promo_id):
    resp = requests.get(api_url(f"/promotions/{promo_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get promotion failed: {resp.text}"
    return resp.json()["promotion"]

def update_promotion(promo_id, data):
    resp = requests.put(api_url(f"/promotions/{promo_id}/"), json=data, headers=headers)
    assert resp.status_code == 200, f"Update promotion failed: {resp.text}"
    return resp.json()["promotion"]

def activate_promotion(promo_id, reason=None):
    payload = {"reason": reason} if reason else {}
    resp = requests.post(api_url(f"/promotions/{promo_id}/activate/"), json=payload, headers=headers)
    assert resp.status_code == 200, f"Activate promotion failed: {resp.text}"
    return resp.json()["promotion"]

def deactivate_promotion(promo_id, reason="Testing"):
    resp = requests.post(
        api_url(f"/promotions/{promo_id}/deactivate/"),
        json={"reason": reason},
        headers=headers,
    )
    assert resp.status_code == 200, f"Deactivate promotion failed: {resp.text}"

def expire_promotion(promo_id):
    resp = requests.post(api_url(f"/promotions/{promo_id}/expire/"), headers=headers)
    assert resp.status_code == 200, f"Expire promotion failed: {resp.text}"

def soft_delete_promotion(promo_id, reason="Testing"):
    resp = requests.delete(
        api_url(f"/promotions/{promo_id}/"),
        json={"reason": reason},
        headers=headers,
    )
    assert resp.status_code == 200, f"Soft delete failed: {resp.text}"

def hard_delete_promotion(promo_id):
    resp = requests.delete(
        api_url(f"/promotions/{promo_id}/hard-delete/"),
        params={"confirm": "yes"},
        headers=headers,
    )
    assert resp.status_code == 200, f"Hard delete failed: {resp.text}"

def restore_promotion(promo_id):
    resp = requests.post(api_url(f"/promotions/{promo_id}/restore/"), headers=headers)
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

def list_promotions(**params):
    resp = requests.get(api_url("/promotions/"), params=params, headers=headers)
    assert resp.status_code == 200, f"List promotions failed: {resp.text}"
    return resp.json()

def get_active_promotions():
    resp = requests.get(api_url("/promotions/active/"), headers=headers)
    assert resp.status_code == 200, f"Active promotions failed: {resp.text}"
    return resp.json()["promotions"]

def get_deleted_promotions(**params):
    params.setdefault("limit", 500)
    resp = requests.get(api_url("/promotions/deleted/"), params=params, headers=headers)
    assert resp.status_code == 200, f"Deleted promotions failed: {resp.text}"
    return resp.json()["promotions"]

def apply_promotion(order_data, customer_id="test_user"):
    payload = {**order_data, "customer_id": customer_id}
    resp = requests.post(api_url("/promotions/apply/"), json=payload, headers=headers)
    assert resp.status_code == 200, f"Apply promotion failed: {resp.text}"
    return resp.json()["data"]

def cleanup_test_promotion(name):
    """Remove a test promotion by name — keeps runs idempotent."""
    body = list_promotions()
    for p in body.get("promotions", []):
        if p.get("name") == name:
            pid = p["promotion_id"]
            try:
                soft_delete_promotion(pid)
            except Exception:
                pass
            try:
                hard_delete_promotion(pid)
            except Exception:
                pass
            print(f"  ✓ Cleaned up active promotion: {pid} ({name})")
            return

    for p in get_deleted_promotions():
        if p.get("name") == name:
            pid = p["promotion_id"]
            try:
                hard_delete_promotion(pid)
            except Exception:
                pass
            print(f"  ✓ Cleaned up deleted promotion: {pid} ({name})")
            return


# ==================== TESTS ====================

def test_health():
    print("\n[Health Check]")
    resp = requests.get(api_url("/promotions/health/"), headers=headers)
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print("  ✓ Health check passed")


def test_create_and_id_format():
    print("\n[Create & ID Format]")
    std_start = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    std_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    promo = create_promotion({
        "name": TEST_PROMO_STD_NAME,
        "description": "10% discount",
        "type": "discount",
        "discount_value": "10%",
        "target_type": "all",
        "start_date": std_start,
        "end_date": std_end,
        "promotion_type": "percentage",
        "priority": 2,
        "stackable": False,
        "min_purchase_amount": 150,
        "per_customer_limit": 3,
    })

    assert promo["name"] == TEST_PROMO_STD_NAME
    assert promo["isDeleted"] is False

    pid = promo["promotion_id"]
    # promotion_id in to_dict() is the numeric part only (sk with "PROMO-" stripped)
    assert re.match(r'^\d+$', pid), \
        f"promotion_id should be numeric string, got: {pid}"
    print(f"  ✓ ID format correct: {pid}")

    return promo


def test_create_recurrence():
    print("\n[Create Recurrence Promotion]")
    rec_start = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rec_end = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()

    promo = create_promotion({
        "name": TEST_PROMO_REC_NAME,
        "description": "5% off on 15th & 30th",
        "type": "discount",
        "discount_value": "5%",
        "target_type": "all",
        "start_date": rec_start,
        "end_date": rec_end,
        "recurrence_rule": "monthly:15,30",
        "promotion_type": "percentage",
        "priority": 1,
        "stackable": True,
    })
    assert promo["name"] == TEST_PROMO_REC_NAME
    print(f"  ✓ Recurrence promotion created: {promo['promotion_id']}")
    return promo


def test_list():
    print("\n[List Promotions]")
    body = list_promotions()
    assert "promotions" in body, "Response missing 'promotions' key"
    assert isinstance(body["promotions"], list), "'promotions' should be a list"
    print(f"  ✓ Listed {len(body['promotions'])} promotions")


def test_get_detail(promo_id, expected_name):
    print("\n[Get Detail]")
    promo = get_promotion(promo_id)
    assert promo["promotion_id"] == promo_id
    assert promo["name"] == expected_name
    print(f"  ✓ Detail fetched for {promo_id}")


def test_404_on_unknown_id():
    print("\n[404 on Unknown ID]")
    resp = requests.get(api_url("/promotions/99999/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for unknown promotion, got {resp.status_code}"
    print("  ✓ 404 returned for non-existent promotion")


def test_defaults(promo_std, promo_rec):
    print("\n[Default Field Values]")
    detail = get_promotion(promo_std["promotion_id"])
    assert detail["min_purchase_amount"] == 150, \
        f"Expected min_purchase_amount=150, got {detail['min_purchase_amount']}"
    assert detail["per_customer_limit"] == 3, \
        f"Expected per_customer_limit=3, got {detail['per_customer_limit']}"

    detail_rec = get_promotion(promo_rec["promotion_id"])
    assert detail_rec["min_purchase_amount"] == 100, \
        f"Expected default min_purchase_amount=100, got {detail_rec['min_purchase_amount']}"
    assert detail_rec["per_customer_limit"] is None, \
        f"Expected per_customer_limit=None, got {detail_rec['per_customer_limit']}"
    print("  ✓ Default values correct")


def test_update(promo_id):
    print("\n[Update]")
    updated = update_promotion(promo_id, {"description": "Updated description"})
    assert updated["description"] == "Updated description"
    # Revert
    update_promotion(promo_id, {"description": "10% discount"})
    print("  ✓ Update applied and verified")


def test_activate_and_active_list(promo_std_id, promo_rec_id):
    print("\n[Activate & Active List]")
    activate_promotion(promo_std_id)
    activate_promotion(promo_rec_id)

    active_ids = {p["promotion_id"] for p in get_active_promotions()}
    assert promo_std_id in active_ids, \
        f"{promo_std_id} should be in active list after activation"
    print(f"  ✓ Standard promotion appears in active list")
    print(f"  ~ Recurrence promotion active visibility depends on recurrence date (not asserted)")


def test_minimum_purchase_enforcement(promo_std_id):
    print("\n[Minimum Purchase Enforcement]")
    # Order below min_purchase_amount (150) should yield no discount
    result = apply_promotion(
        {"items": [{"product_id": "p1", "quantity": 1, "price": 50}], "total_amount": 50},
        "cust_min_test",
    )
    assert result["total_discount"] == 0, \
        f"Expected 0 discount below min purchase, got {result['total_discount']}"
    print("  ✓ Minimum purchase enforced (no discount below threshold)")


def test_per_customer_limit(promo_std_id):
    print("\n[Per-Customer Limit]")
    order = {"items": [{"product_id": "p1", "quantity": 2, "price": 200}], "total_amount": 200}
    customer = f"cust_limit_{UNIQUE_SUFFIX}"

    for i in range(3):
        result = apply_promotion(order, customer)
        print(f"    Use {i + 1}: discount={result['total_discount']}")

    # 4th attempt should yield no discount
    fourth = apply_promotion(order, customer)
    assert fourth["total_discount"] == 0, \
        f"Expected 0 discount after per-customer limit, got {fourth['total_discount']}"
    print("  ✓ Per-customer limit enforced after 3 uses")


def test_search():
    print("\n[Search]")
    resp = requests.get(
        api_url("/promotions/search/"),
        params={"q": UNIQUE_SUFFIX},
        headers=headers,
    )
    assert resp.status_code == 200, f"Search failed: {resp.text}"
    data = resp.json()
    assert "promotions" in data, "Response missing 'promotions' key"
    promos = data["promotions"]
    assert any(p["name"] == TEST_PROMO_STD_NAME for p in promos), \
        f"Test promotion not found in search results"
    print(f"  ✓ Search returned {len(promos)} result(s) matching '{UNIQUE_SUFFIX}'")


def test_search_missing_q_returns_400():
    print("\n[Search — Missing q Returns 400]")
    resp = requests.get(api_url("/promotions/search/"), headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 when q param is missing, got {resp.status_code}"
    print("  ✓ 400 returned when search query param is absent")


def test_by_name():
    print("\n[By Name]")
    resp = requests.get(
        api_url("/promotions/by-name/"),
        params={"name": TEST_PROMO_STD_NAME},
        headers=headers,
    )
    assert resp.status_code == 200, f"By-name lookup failed: {resp.text}"
    promo = resp.json()["promotion"]
    assert promo["name"] == TEST_PROMO_STD_NAME, \
        f"Name mismatch: {promo['name']}"
    print(f"  ✓ Found by name: {promo['name']}")


def test_by_name_404():
    print("\n[By Name — 404 on Unknown]")
    resp = requests.get(
        api_url("/promotions/by-name/"),
        params={"name": "does_not_exist_xyz_999"},
        headers=headers,
    )
    assert resp.status_code == 404, \
        f"Expected 404 for unknown name, got {resp.status_code}"
    print("  ✓ 404 returned for unknown promotion name")


def test_statistics():
    print("\n[Statistics]")
    resp = requests.get(api_url("/promotions/statistics/"), headers=headers)
    assert resp.status_code == 200, f"Statistics failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True, f"Response not successful: {body}"
    print("  ✓ Statistics endpoint returned successfully")


def test_audit_history(promo_id):
    print("\n[Audit History]")
    resp = requests.get(
        api_url(f"/promotions/{promo_id}/audit/"),
        params={"limit": 50},
        headers=headers,
    )
    assert resp.status_code == 200, f"Audit history failed: {resp.text}"
    body = resp.json()
    assert "audit" in body, "Response missing 'audit' key"
    history = body["audit"]
    assert isinstance(history, list), "'audit' should be a list"
    assert len(history) >= 1, "Expected at least 1 audit entry after create + activate"
    print(f"  ✓ Audit entries: {len(history)}")


def test_qr_code(promo_id):
    print("\n[QR Code]")
    resp = requests.get(api_url(f"/promotions/{promo_id}/qr/"), headers=headers)
    assert resp.status_code == 200, f"QR code failed: {resp.text}"
    assert "image/png" in resp.headers.get("Content-Type", ""), \
        f"Expected image/png content-type, got: {resp.headers.get('Content-Type')}"
    print("  ✓ QR code generated (image/png)")


def test_report_returns_501(promo_id):
    print("\n[Report Endpoint — 501 Not Implemented]")
    resp = requests.get(api_url(f"/promotions/{promo_id}/report/"), headers=headers)
    assert resp.status_code == 501, \
        f"Expected 501 for unimplemented report endpoint, got {resp.status_code}"
    print("  ✓ 501 returned for unimplemented report endpoint")


def test_missing_name_rejected():
    print("\n[Missing Name Rejected]")
    resp = requests.post(
        api_url("/promotions/"),
        json={"type": "discount", "discount_value": "10%"},
        headers=headers,
    )
    assert resp.status_code in (400, 422), \
        f"Expected 400/422 for missing name, got {resp.status_code}"
    print(f"  ✓ Missing name rejected with {resp.status_code}")


def test_hard_delete_requires_confirm(promo_id):
    print("\n[Hard Delete — confirm=yes Required]")
    resp = requests.delete(
        api_url(f"/promotions/{promo_id}/hard-delete/"),
        headers=headers,
    )
    assert resp.status_code == 400, \
        f"Expected 400 without ?confirm=yes, got {resp.status_code}"
    print("  ✓ 400 returned when confirm param is missing")


def test_soft_delete_and_restore(promo_id):
    print("\n[Soft Delete & Restore]")
    soft_delete_promotion(promo_id, "Test soft delete")

    deleted = get_deleted_promotions()
    deleted_ids = [p["promotion_id"] for p in deleted]
    assert promo_id in deleted_ids, \
        f"{promo_id} not found in deleted list"
    print(f"  ✓ {promo_id} appears in deleted list")

    body = list_promotions()
    active_ids = [p["promotion_id"] for p in body.get("promotions", [])]
    assert promo_id not in active_ids, \
        f"{promo_id} still in active list after soft delete"
    print("  ✓ Not in active list after soft delete")

    restore_promotion(promo_id)
    restored = get_promotion(promo_id)
    assert restored["isDeleted"] is False
    assert restored["status"] == "draft", \
        f"Expected status='draft' after restore, got '{restored['status']}'"
    print(f"  ✓ {promo_id} restored; status='draft'")


def test_expire_and_hard_delete(promo_id):
    print("\n[Expire & Hard Delete]")
    # Re-activate so we can expire it
    activate_promotion(promo_id)
    expire_promotion(promo_id)

    expired = get_promotion(promo_id)
    assert expired["status"] in ("inactive", "expired", "deactivated"), \
        f"Expected inactive/expired/deactivated after expire, got '{expired['status']}'"
    print(f"  ✓ Status after expire: '{expired['status']}'")

    hard_delete_promotion(promo_id)
    resp = requests.get(api_url(f"/promotions/{promo_id}/"), headers=headers)
    assert resp.status_code == 404, \
        f"Promotion should be gone after hard delete, got {resp.status_code}"
    print(f"  ✓ {promo_id} permanently deleted and confirmed gone")


if __name__ == "__main__":
    print("=== Login ===")
    login()

    print("\n=== Pre-run cleanup ===")
    cleanup_test_promotion(TEST_PROMO_STD_NAME)
    cleanup_test_promotion(TEST_PROMO_REC_NAME)
    print("  ✓ Cleanup done")

    # 1. Health check
    test_health()

    # 2. Create standard promotion
    promo_std = test_create_and_id_format()
    promo_std_id = promo_std["promotion_id"]

    # 3. Create recurrence promotion
    promo_rec = test_create_recurrence()
    promo_rec_id = promo_rec["promotion_id"]

    # 4. List
    test_list()

    # 5. Get detail
    test_get_detail(promo_std_id, TEST_PROMO_STD_NAME)

    # 6. 404 on unknown ID
    test_404_on_unknown_id()

    # 7. Verify default field values
    test_defaults(promo_std, promo_rec)

    # 8. Update
    test_update(promo_std_id)

    # 9. Activate both; assert standard appears in active list
    test_activate_and_active_list(promo_std_id, promo_rec_id)

    # 10. Minimum purchase enforcement
    test_minimum_purchase_enforcement(promo_std_id)

    # 11. Per-customer limit
    test_per_customer_limit(promo_std_id)

    # 12. Search
    test_search()

    # 13. Search missing q param returns 400
    test_search_missing_q_returns_400()

    # 14. By-name lookup
    test_by_name()

    # 15. By-name 404
    test_by_name_404()

    # 16. Statistics
    test_statistics()

    # 17. Audit history
    test_audit_history(promo_std_id)

    # 18. QR code
    test_qr_code(promo_std_id)

    # 19. Report returns 501
    test_report_returns_501(promo_std_id)

    # 20. Missing name rejected
    test_missing_name_rejected()

    # 21. Hard delete requires confirm
    test_hard_delete_requires_confirm(promo_std_id)

    # 22. Soft delete + restore (promo_rec — not needed beyond this point)
    deactivate_promotion(promo_rec_id, "No longer needed")
    soft_delete_promotion(promo_rec_id, "Cleanup")
    hard_delete_promotion(promo_rec_id)

    # 23. Soft delete + restore (promo_std)
    test_soft_delete_and_restore(promo_std_id)

    # 24. Expire + hard delete (promo_std is active=draft after restore, re-activate inside)
    test_expire_and_hard_delete(promo_std_id)

    print("\n=== All promotion tests passed ===")

import re
import requests
import time

BASE = "http://127.0.0.1:8000"

def api_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"

headers = {"Content-Type": "application/json"}

# Admin credentials — update if your dev account differs.
ADMIN_EMAIL = "jlin@gmail.com"
ADMIN_PASSWORD = "password1234"

# Unique suffix prevents name collisions across test runs.
UNIQUE_SUFFIX = str(int(time.time()))[-6:]
TEST_CATEGORY_NAME = f"Test Category {UNIQUE_SUFFIX}"
TEST_SUBCATEGORY_NAME = f"Test Sub {UNIQUE_SUFFIX}"


# ==================== AUTH ====================

def login():
    """Log in and inject the JWT token into the shared headers dict."""
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

def create_category(data):
    resp = requests.post(api_url("/categories/"), json=data, headers=headers)
    assert resp.status_code == 201, f"Create category failed: {resp.text}"
    category = resp.json()["category"]
    print(f"  ✓ Category created: {category['category_id']} ({category['category_name']})")
    return category

def get_category(category_id):
    resp = requests.get(api_url(f"/categories/{category_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get category failed: {resp.text}"
    return resp.json()["category"]

def update_category(category_id, data):
    resp = requests.put(api_url(f"/categories/{category_id}/"), json=data, headers=headers)
    assert resp.status_code == 200, f"Update category failed: {resp.text}"
    return resp.json()["category"]

def soft_delete_category(category_id):
    resp = requests.delete(api_url(f"/categories/{category_id}/soft-delete/"), headers=headers)
    assert resp.status_code == 200, f"Soft delete failed: {resp.text}"

def hard_delete_category(category_id):
    resp = requests.delete(api_url(f"/categories/{category_id}/hard-delete/"), headers=headers)
    assert resp.status_code == 200, f"Hard delete failed: {resp.text}"

def restore_category(category_id):
    resp = requests.post(api_url(f"/categories/{category_id}/restore/"), headers=headers)
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

def list_categories(**params):
    resp = requests.get(api_url("/categories/"), params=params, headers=headers)
    assert resp.status_code == 200, f"List categories failed: {resp.text}"
    return resp.json()

def list_deleted_categories():
    resp = requests.get(api_url("/categories/deleted/"), headers=headers)
    assert resp.status_code == 200, f"List deleted categories failed: {resp.text}"
    return resp.json()

def cleanup_test_category(name):
    """Remove a test category by name if it exists — keeps runs idempotent."""
    body = list_categories()
    all_cats = body.get("categories", [])
    for cat in all_cats:
        if cat.get("category_name") == name:
            cid = cat["category_id"]
            try:
                soft_delete_category(cid)
            except Exception:
                pass
            try:
                hard_delete_category(cid)
            except Exception:
                pass
            print(f"  ✓ Cleaned up existing category: {cid}")
            return

    # Also check deleted list
    del_body = list_deleted_categories()
    for cat in del_body.get("categories", []):
        if cat.get("category_name") == name:
            cid = cat["category_id"]
            try:
                hard_delete_category(cid)
            except Exception:
                pass
            print(f"  ✓ Cleaned up deleted category: {cid}")
            return


# ==================== TESTS ====================

def test_create_and_id_format():
    print("\n[Create & ID Format]")
    category = create_category({
        "category_name": TEST_CATEGORY_NAME,
        "description": "Automated test category",
        "status": "active",
    })

    assert category["category_name"] == TEST_CATEGORY_NAME
    assert category["status"] == "active"
    assert category["isDeleted"] is False

    cid = category["category_id"]
    assert re.match(r'^CTGY-\d{3}$', cid), \
        f"category_id should be CTGY-### format, got: {cid}"
    print(f"  ✓ ID format correct: {cid}")

    return category


def test_list():
    print("\n[List Categories]")
    body = list_categories()
    assert "categories" in body, "Response missing 'categories' key"
    assert "count" in body, "Response missing 'count' key"
    assert isinstance(body["categories"], list), "'categories' should be a list"
    assert body["count"] == len(body["categories"]), "count mismatch"
    print(f"  ✓ Listed {body['count']} categories")


def test_get_detail(category_id):
    print("\n[Get Detail]")
    cat = get_category(category_id)
    assert cat["category_id"] == category_id
    assert cat["category_name"] == TEST_CATEGORY_NAME
    assert "sub_categories" in cat
    print(f"  ✓ Detail fetched for {category_id}")


def test_404_on_unknown_id():
    print("\n[404 on Unknown ID]")
    resp = requests.get(api_url("/categories/CTGY-99999/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for unknown category, got {resp.status_code}"
    print("  ✓ 404 returned for non-existent category")


def test_update(category_id):
    print("\n[Update]")
    updated = update_category(category_id, {
        "category_name": f"{TEST_CATEGORY_NAME} Updated",
        "description": "Updated description",
    })
    assert updated["category_name"] == f"{TEST_CATEGORY_NAME} Updated"
    assert updated["description"] == "Updated description"

    # Revert name so later tests still match
    update_category(category_id, {"category_name": TEST_CATEGORY_NAME})
    print("  ✓ Update applied and verified")


def test_update_no_valid_fields(category_id):
    print("\n[Update — No Valid Fields Rejected]")
    resp = requests.put(
        api_url(f"/categories/{category_id}/"),
        json={"unknown_field": "value"},
        headers=headers,
    )
    assert resp.status_code == 400, \
        f"Expected 400 for empty update payload, got {resp.status_code}"
    print("  ✓ 400 returned when no valid fields supplied")


def test_search():
    print("\n[Search]")
    body = list_categories(search=UNIQUE_SUFFIX)
    cats = body.get("categories", [])
    assert any(c["category_name"] == TEST_CATEGORY_NAME for c in cats), \
        f"Test category not found in search results: {[c['category_name'] for c in cats]}"
    print(f"  ✓ Search returned {len(cats)} result(s) matching '{UNIQUE_SUFFIX}'")


def test_active_only_filter():
    print("\n[Active-Only Filter]")
    body = list_categories(active_only="true")
    cats = body.get("categories", [])
    for cat in cats:
        assert cat.get("status") == "active" or not cat.get("isDeleted"), \
            f"Non-active category in active_only results: {cat}"
    print(f"  ✓ Active-only filter returned {len(cats)} categories, all active")


def test_delete_info(category_id):
    print("\n[Delete Info]")
    resp = requests.get(api_url(f"/categories/{category_id}/delete-info/"), headers=headers)
    assert resp.status_code == 200, f"Delete info failed: {resp.text}"
    info = resp.json().get("delete_info")
    assert info is not None, "delete_info key missing from response"
    print(f"  ✓ Delete info retrieved: {list(info.keys())}")


def test_subcategory_add_and_remove(category_id):
    print("\n[Subcategory Add & Remove]")

    # Add
    resp = requests.post(
        api_url(f"/categories/{category_id}/subcategories/"),
        json={"subcategory": {"name": TEST_SUBCATEGORY_NAME, "description": "Test sub"}},
        headers=headers,
    )
    assert resp.status_code == 201, f"Add subcategory failed: {resp.text}"
    print(f"  ✓ Subcategory '{TEST_SUBCATEGORY_NAME}' added")

    # Verify it appears
    resp = requests.get(api_url(f"/categories/{category_id}/subcategories/"), headers=headers)
    assert resp.status_code == 200
    subs = resp.json().get("subcategories", [])
    assert any(s["name"] == TEST_SUBCATEGORY_NAME for s in subs), \
        f"Subcategory not found in list: {[s['name'] for s in subs]}"
    print(f"  ✓ Subcategory appears in list ({len(subs)} total)")

    # Remove
    resp = requests.delete(
        api_url(f"/categories/{category_id}/subcategories/"),
        json={"subcategory_name": TEST_SUBCATEGORY_NAME},
        headers=headers,
    )
    assert resp.status_code == 200, f"Remove subcategory failed: {resp.text}"
    print(f"  ✓ Subcategory '{TEST_SUBCATEGORY_NAME}' removed")

    # Verify it's gone
    resp = requests.get(api_url(f"/categories/{category_id}/subcategories/"), headers=headers)
    subs = resp.json().get("subcategories", [])
    assert not any(s["name"] == TEST_SUBCATEGORY_NAME for s in subs), \
        "Subcategory still present after removal"
    print("  ✓ Subcategory no longer in list")


def test_soft_delete_and_restore(category_id):
    print("\n[Soft Delete & Restore]")
    soft_delete_category(category_id)

    # Should appear in deleted list
    del_body = list_deleted_categories()
    deleted_ids = [c["category_id"] for c in del_body.get("categories", [])]
    assert category_id in deleted_ids, \
        f"{category_id} not found in deleted categories list"
    print(f"  ✓ {category_id} appears in deleted list")

    # Should NOT appear in normal list
    body = list_categories()
    active_ids = [c["category_id"] for c in body.get("categories", [])]
    assert category_id not in active_ids, \
        f"{category_id} still appears in active list after soft delete"
    print("  ✓ Not in active list after soft delete")

    # Restore
    restore_category(category_id)
    cat = get_category(category_id)
    assert cat["isDeleted"] is False
    assert cat["status"] == "active"
    print(f"  ✓ {category_id} restored and active again")


def test_hard_delete(category_id):
    print("\n[Hard Delete]")
    soft_delete_category(category_id)
    hard_delete_category(category_id)

    resp = requests.get(api_url(f"/categories/{category_id}/"), headers=headers)
    assert resp.status_code == 404, \
        f"Category should be gone after hard delete, got {resp.status_code}"
    print(f"  ✓ {category_id} permanently deleted and confirmed gone")


def test_missing_name_rejected():
    print("\n[Missing Name Rejected]")
    resp = requests.post(
        api_url("/categories/"),
        json={"description": "No name supplied"},
        headers=headers,
    )
    assert resp.status_code in (400, 422, 500), \
        f"Expected error for missing category_name, got {resp.status_code}"
    print(f"  ✓ Missing category_name rejected with {resp.status_code}")


def test_uncategorized_endpoint():
    print("\n[Uncategorized Category]")
    resp = requests.get(api_url("/categories/uncategorized/"), headers=headers)
    assert resp.status_code == 200, f"Uncategorized endpoint failed: {resp.text}"
    cat = resp.json().get("uncategorized_category")
    assert cat is not None, "uncategorized_category key missing"
    print(f"  ✓ Uncategorized category: {cat.get('category_id')} — {cat.get('category_name')}")


if __name__ == "__main__":
    print("=== Login ===")
    login()

    print("\n=== Pre-run cleanup ===")
    cleanup_test_category(TEST_CATEGORY_NAME)
    cleanup_test_category(f"{TEST_CATEGORY_NAME} Updated")
    print("  ✓ Cleanup done")

    # 1. Create
    category = test_create_and_id_format()
    cid = category["category_id"]

    # 2. List
    test_list()

    # 3. Get detail
    test_get_detail(cid)

    # 4. 404 on unknown ID
    test_404_on_unknown_id()

    # 5. Update
    test_update(cid)

    # 6. Update with no valid fields
    test_update_no_valid_fields(cid)

    # 7. Search
    test_search()

    # 8. Active-only filter
    test_active_only_filter()

    # 9. Delete info
    test_delete_info(cid)

    # 10. Subcategory add & remove
    test_subcategory_add_and_remove(cid)

    # 11. Soft delete + restore
    test_soft_delete_and_restore(cid)

    # 12. Hard delete (category is active again after restore)
    test_hard_delete(cid)

    # 13. Missing name rejected
    test_missing_name_rejected()

    # 14. Uncategorized endpoint
    test_uncategorized_endpoint()

    print("\n=== All category tests passed ===")

import re
import requests
import time

BASE = "http://127.0.0.1:8000"

def api_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"

headers = {"Content-Type": "application/json"}

# Admin credentials used to obtain a JWT token for authenticated endpoints.
# Override these if your dev account differs.
ADMIN_EMAIL = "jlin@gmail.com"
ADMIN_PASSWORD = "password1234"

# Unique suffix keeps multiple test runs from colliding on SKU/barcode
UNIQUE_SUFFIX = str(int(time.time()))[-6:]
TEST_SKU = f"TEST-SKU-{UNIQUE_SUFFIX}"
TEST_BARCODE = f"7890000{UNIQUE_SUFFIX}"

# Override with a known category ID (e.g. "CTGY-001") if auto-detect fails.
CATEGORY_ID_OVERRIDE = ""


# ==================== AUTH ====================

def login():
    """Log in and inject the JWT token into the shared headers dict."""
    resp = requests.post(
        f"{BASE}/api/v1/admin/auth/login/",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, \
        f"Login failed ({resp.status_code}). Check ADMIN_EMAIL/ADMIN_PASSWORD at the top of this file.\n{resp.text}"
    token = resp.json().get("access_token")
    assert token, f"No access_token in login response: {resp.json()}"
    headers["Authorization"] = f"Bearer {token}"
    print(f"  ✓ Logged in as {ADMIN_EMAIL}")


# ==================== HELPERS ====================

def get_test_category_id():
    """Return the first available category ID from the API."""
    if CATEGORY_ID_OVERRIDE:
        return CATEGORY_ID_OVERRIDE
    resp = requests.get(api_url("/categories/"), headers=headers)
    assert resp.status_code == 200, \
        f"Could not fetch categories ({resp.status_code}). Set CATEGORY_ID_OVERRIDE manually."
    body = resp.json()
    categories = (
        body.get("categories")
        or body.get("data")
        or (body if isinstance(body, list) else [])
    )
    assert categories, \
        "No categories found. Create a category first or set CATEGORY_ID_OVERRIDE at the top of this file."
    cat = categories[0]
    cid = cat.get("category_id") or cat.get("sk") or cat.get("id")
    assert cid, f"Could not extract category_id from category: {cat}"
    return cid

def create_product(data):
    resp = requests.post(api_url("/products/"), json=data, headers=headers)
    assert resp.status_code == 201, f"Create product failed: {resp.text}"
    product = resp.json()["data"]
    print(f"  ✓ Product created: PROD-{product['product_id']} ({product['product_name']})")
    return product

def get_product(product_id):
    resp = requests.get(api_url(f"/products/{product_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get product failed: {resp.text}"
    return resp.json()["data"]

def update_product(product_id, data):
    resp = requests.put(api_url(f"/products/{product_id}/"), json=data, headers=headers)
    assert resp.status_code == 200, f"Update product failed: {resp.text}"
    return resp.json()["data"]

def soft_delete_product(product_id):
    resp = requests.delete(api_url(f"/products/{product_id}/"), headers=headers)
    assert resp.status_code == 200, f"Soft delete failed: {resp.text}"

def hard_delete_product(product_id):
    resp = requests.delete(
        api_url(f"/products/{product_id}/"), params={"hard_delete": "true"}, headers=headers
    )
    assert resp.status_code == 200, f"Hard delete failed: {resp.text}"

def restore_product(product_id):
    resp = requests.post(api_url(f"/products/{product_id}/restore/"), headers=headers)
    assert resp.status_code == 200, f"Restore failed: {resp.text}"

def cleanup_test_product(sku):
    """Remove a test product if it already exists — keeps runs idempotent."""
    resp = requests.get(api_url(f"/products/by-sku/{sku}/"), headers=headers)
    if resp.status_code == 200:
        pid = resp.json().get("data", {}).get("product_id")
        if pid:
            try:
                soft_delete_product(pid)
            except Exception:
                pass
            try:
                hard_delete_product(pid)
            except Exception:
                pass


# ==================== TESTS ====================

def test_create_and_id_format(category_id):
    print("\n[Create & ID Format]")
    product = create_product({
        "product_name": f"Test Noodles {UNIQUE_SUFFIX}",
        "SKU": TEST_SKU,
        "category_id": category_id,
        "cost_price": 25.00,
        "selling_price": 35.00,
        "unit": "pack",
        "barcode": TEST_BARCODE,
        "description": "Automated test product",
        "low_stock_threshold": 5,
    })

    assert product["product_name"] == f"Test Noodles {UNIQUE_SUFFIX}"
    assert product["sku"] == TEST_SKU
    assert float(product["cost_price"]) == 25.00
    assert float(product["selling_price"]) == 35.00
    assert product["status"] == "active"
    assert product["isDeleted"] is False
    assert product["category_id"] == category_id

    # to_dict() strips "PROD-" — expect a 5-digit zero-padded string
    assert re.match(r'^\d{5}$', product["product_id"]), \
        f"product_id should be 5 digits (PROD- prefix stripped), got: {product['product_id']}"
    print(f"  ✓ ID format correct: PROD-{product['product_id']}")

    return product


def test_duplicate_sku_rejected(category_id):
    print("\n[Duplicate SKU Rejected]")
    resp = requests.post(api_url("/products/"), json={
        "product_name": "Duplicate Product",
        "SKU": TEST_SKU,
        "category_id": category_id,
        "cost_price": 10.00,
        "selling_price": 15.00,
        "unit": "piece",
    }, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for duplicate SKU, got {resp.status_code}: {resp.text}"
    print("  ✓ Duplicate SKU rejected with 400")


def test_required_fields_validation(category_id):
    print("\n[Required Fields Validation]")

    # Missing product_name
    resp = requests.post(api_url("/products/"), json={
        "SKU": f"VALID-{UNIQUE_SUFFIX}X",
        "category_id": category_id,
        "cost_price": 10.00,
        "selling_price": 15.00,
        "unit": "piece",
    }, headers=headers)
    assert resp.status_code in (400, 422), \
        f"Expected 4xx for missing product_name, got {resp.status_code}"
    print("  ✓ Missing product_name rejected")

    # Missing SKU
    resp = requests.post(api_url("/products/"), json={
        "product_name": "No SKU",
        "category_id": category_id,
        "cost_price": 10.00,
        "selling_price": 15.00,
        "unit": "piece",
    }, headers=headers)
    assert resp.status_code in (400, 422), \
        f"Expected 4xx for missing SKU, got {resp.status_code}"
    print("  ✓ Missing SKU rejected")

    # Non-existent category
    resp = requests.post(api_url("/products/"), json={
        "product_name": "Bad Category Product",
        "SKU": f"BAD-CAT-{UNIQUE_SUFFIX}",
        "category_id": "CTGY-99999",
        "cost_price": 10.00,
        "selling_price": 15.00,
        "unit": "piece",
    }, headers=headers)
    assert resp.status_code in (400, 422), \
        f"Expected 4xx for invalid category_id, got {resp.status_code}"
    print("  ✓ Invalid category_id rejected")

    # Negative cost price
    resp = requests.post(api_url("/products/"), json={
        "product_name": "Negative Price",
        "SKU": f"NEG-{UNIQUE_SUFFIX}",
        "category_id": category_id,
        "cost_price": -5.00,
        "selling_price": 15.00,
        "unit": "piece",
    }, headers=headers)
    assert resp.status_code in (400, 422), \
        f"Expected 4xx for negative cost_price, got {resp.status_code}"
    print("  ✓ Negative cost_price rejected")


def test_get_detail(product_id):
    print("\n[Get Detail]")
    product = get_product(product_id)
    assert product["product_id"] == product_id
    assert "product_name" in product
    assert "sku" in product
    assert "cost_price" in product
    assert "selling_price" in product
    assert "total_stock" in product
    assert "status" in product
    assert "margin_percentage" in product
    assert "markup_percentage" in product
    print(f"  ✓ Detail retrieved: {product['product_name']}")

    # Non-existent product
    resp = requests.get(api_url("/products/PROD-00000/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for unknown product, got {resp.status_code}"
    print("  ✓ Unknown product returns 404")


def test_update(product_id):
    print("\n[Update]")
    updated = update_product(product_id, {
        "product_name": f"Updated Noodles {UNIQUE_SUFFIX}",
        "description": "Updated via test",
        "selling_price": 40.00,
    })
    assert updated["product_name"] == f"Updated Noodles {UNIQUE_SUFFIX}"
    assert float(updated["selling_price"]) == 40.00
    print("  ✓ Name and price updated")

    # Verify persisted in DynamoDB
    fetched = get_product(product_id)
    assert fetched["product_name"] == f"Updated Noodles {UNIQUE_SUFFIX}"
    assert float(fetched["selling_price"]) == 40.00
    print("  ✓ Update persisted to DynamoDB")


def test_list_and_pagination():
    print("\n[List & Pagination]")
    resp = requests.get(api_url("/products/"), params={"page_size": 2}, headers=headers)
    assert resp.status_code == 200, f"Product list failed: {resp.text}"
    body = resp.json()
    assert "data" in body, "Response missing 'data' key"
    assert isinstance(body["data"], list)
    assert len(body["data"]) <= 2
    print(f"  ✓ First page: {len(body['data'])} products")

    if body.get("next_page_token"):
        resp2 = requests.get(api_url("/products/"), params={
            "page_size": 2,
            "page_token": body["next_page_token"],
        }, headers=headers)
        assert resp2.status_code == 200
        print(f"  ✓ Second page: {len(resp2.json()['data'])} products")


def test_search_by_name():
    print("\n[Search by Name]")
    resp = requests.get(api_url("/products/"), params={
        "search": f"Updated Noodles {UNIQUE_SUFFIX}"
    }, headers=headers)
    assert resp.status_code == 200, f"Search failed: {resp.text}"
    results = resp.json()["data"]
    assert len(results) > 0, "Search returned no results for known product name"
    print(f"  ✓ Search returned {len(results)} result(s)")


def test_get_by_sku():
    print("\n[Get by SKU]")
    resp = requests.get(api_url(f"/products/by-sku/{TEST_SKU}/"), headers=headers)
    assert resp.status_code == 200, f"Get by SKU failed: {resp.text}"
    assert resp.json()["data"]["sku"] == TEST_SKU
    print(f"  ✓ Found by SKU: {TEST_SKU}")

    resp = requests.get(api_url("/products/by-sku/NONEXISTENT-SKU-XYZ999/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for unknown SKU, got {resp.status_code}"
    print("  ✓ Unknown SKU returns 404")


def test_get_by_barcode():
    print("\n[Get by Barcode]")
    resp = requests.get(api_url(f"/products/by-barcode/{TEST_BARCODE}/"), headers=headers)
    assert resp.status_code == 200, f"Get by barcode failed: {resp.text}"
    assert resp.json()["data"].get("barcode") == TEST_BARCODE
    print(f"  ✓ Found by barcode: {TEST_BARCODE}")

    resp = requests.get(api_url("/products/by-barcode/0000000000000/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for unknown barcode, got {resp.status_code}"
    print("  ✓ Unknown barcode returns 404")


def test_filter_by_category(category_id):
    print("\n[Filter by Category]")
    resp = requests.get(api_url(f"/products/category/{category_id}/"), headers=headers)
    assert resp.status_code == 200, f"Filter by category failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    # All returned products should belong to this category
    for p in data:
        assert p["category_id"] == category_id, \
            f"Product {p['product_id']} has wrong category: {p['category_id']}"
    print(f"  ✓ Category filter returned {len(data)} products, all in category {category_id}")


def test_low_stock_and_expiring():
    print("\n[Low Stock & Expiring Endpoints]")
    resp = requests.get(api_url("/products/low-stock/"), headers=headers)
    assert resp.status_code == 200, f"Low stock endpoint failed: {resp.text}"
    assert "data" in resp.json()
    print(f"  ✓ Low stock endpoint: {len(resp.json()['data'])} products")

    resp = requests.get(api_url("/products/expiring/"), headers=headers)
    assert resp.status_code == 200, f"Expiring endpoint failed: {resp.text}"
    assert "data" in resp.json()
    print(f"  ✓ Expiring endpoint: {len(resp.json()['data'])} products")

    resp = requests.get(api_url("/products/expiring/"), params={"days_ahead": 60}, headers=headers)
    assert resp.status_code == 200
    print(f"  ✓ Expiring (60 days) endpoint: {len(resp.json()['data'])} products")


def test_stock_history(product_id):
    print("\n[Stock History]")
    resp = requests.get(api_url(f"/products/{product_id}/stock/history/"), headers=headers)
    assert resp.status_code == 200, f"Stock history failed: {resp.text}"
    body = resp.json()
    assert body["product_id"] == product_id
    assert "current_stock" in body
    assert "stock_history" in body
    assert isinstance(body["stock_history"], list)
    print(f"  ✓ Stock history: {len(body['stock_history'])} entries, current_stock={body['current_stock']}")


def test_soft_delete_and_restore(product_id):
    print("\n[Soft Delete & Restore]")
    soft_delete_product(product_id)

    # Should return 404 when queried directly
    resp = requests.get(api_url(f"/products/{product_id}/"), headers=headers)
    assert resp.status_code == 404, \
        f"Soft-deleted product should return 404, got {resp.status_code}"
    print("  ✓ Soft-deleted product returns 404")

    # Should appear in the deleted list
    resp = requests.get(api_url("/products/deleted/"), headers=headers)
    assert resp.status_code == 200
    deleted_ids = [p["product_id"] for p in resp.json().get("data", [])]
    assert product_id in deleted_ids, \
        f"Product {product_id} not found in deleted list"
    print("  ✓ Product appears in deleted list")

    # Restore
    restore_product(product_id)
    restored = get_product(product_id)
    assert restored["isDeleted"] is False
    assert restored["status"] == "active"
    print("  ✓ Product restored and active again")


def test_hard_delete(product_id):
    print("\n[Hard Delete]")
    soft_delete_product(product_id)
    hard_delete_product(product_id)

    resp = requests.get(api_url(f"/products/{product_id}/"), headers=headers)
    assert resp.status_code == 404, \
        f"Product should be gone after hard delete, got {resp.status_code}"
    print("  ✓ Product permanently deleted and confirmed gone")


if __name__ == "__main__":
    print("=== Login ===")
    login()

    print("\n=== Pre-run cleanup ===")
    cleanup_test_product(TEST_SKU)
    print("  ✓ Cleanup done")

    category_id = get_test_category_id()
    print(f"  ✓ Using category: {category_id}")

    # 1. Create
    product = test_create_and_id_format(category_id)
    pid = product["product_id"]

    # 2. Duplicate SKU
    test_duplicate_sku_rejected(category_id)

    # 3. Field validation
    test_required_fields_validation(category_id)

    # 4. Get detail + 404
    test_get_detail(pid)

    # 5. Update
    test_update(pid)

    # 6. List + pagination
    test_list_and_pagination()

    # 7. Search
    test_search_by_name()

    # 8. By SKU
    test_get_by_sku()

    # 9. By barcode
    test_get_by_barcode()

    # 10. By category
    test_filter_by_category(category_id)

    # 11. Low stock + expiring
    test_low_stock_and_expiring()

    # 12. Stock history
    test_stock_history(pid)

    # 13. Soft delete + restore
    test_soft_delete_and_restore(pid)

    # 14. Hard delete (product is active again after restore)
    test_hard_delete(pid)

    print("\n=== All product tests passed ===")

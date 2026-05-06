import requests
import json
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8000"

def api_url(path):
    if not path.startswith('/'):
        path = '/' + path
    # Adjust if your customer endpoints live under a different prefix
    return f"{BASE}/api/v1/admin{path}"

headers = {"Content-Type": "application/json"}

created_ids = []

def test_register_customer(email, password, extra=None):
    data = {
        "email": email,
        "password": password
    }
    if extra:
        data.update(extra)
    resp = requests.post(api_url("/customers/register/"), json=data, headers=headers)
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    customer = resp.json()["customer"]
    print(f"✓ Registered customer: {customer['id']} ({customer['email']})")
    created_ids.append(customer['id'])
    return customer

def login_customer(email, password):
    data = {"email": email, "password": password}
    resp = requests.post(api_url("/customers/login/"), json=data, headers=headers)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    tokens = resp.json()
    print(f"✓ Logged in as {email}")
    return tokens

def get_customer_by_id(customer_id):
    resp = requests.get(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get customer failed: {resp.text}"
    return resp.json()

def update_customer(customer_id, data):
    resp = requests.put(api_url(f"/customers/{customer_id}/"), json=data, headers=headers)
    assert resp.status_code == 200, f"Update failed: {resp.text}"
    return resp.json()

def soft_delete_customer(customer_id):
    resp = requests.delete(api_url(f"/customers/{customer_id}/"), headers=headers)
    assert resp.status_code == 200, f"Soft delete failed: {resp.text}"
    print(f"✓ Soft deleted customer {customer_id}")

def restore_customer(customer_id):
    resp = requests.post(api_url(f"/customers/{customer_id}/restore/"), headers=headers)
    assert resp.status_code == 200, f"Restore failed: {resp.text}"
    print(f"✓ Restored customer {customer_id}")

def hard_delete_customer(customer_id):
    resp = requests.delete(api_url(f"/customers/{customer_id}/hard-delete/?confirm=yes"), headers=headers)
    assert resp.status_code == 200, f"Hard delete failed: {resp.text}"
    print(f"✓ Permanently deleted customer {customer_id}")

def search_customers(query, limit=20):
    resp = requests.get(api_url("/customers/search/"), params={"q": query, "limit": limit}, headers=headers)
    assert resp.status_code == 200, f"Search failed: {resp.text}"
    data = resp.json()
    print(f"✓ Search for '{query}' returned {len(data)} results")
    return data

def get_customer_by_email(email):
    resp = requests.get(api_url("/customers/by-email/"), params={"email": email}, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 404:
        return None
    else:
        resp.raise_for_status()

def get_statistics():
    resp = requests.get(api_url("/customers/statistics/"), headers=headers)
    assert resp.status_code == 200, f"Stats failed: {resp.text}"
    print("✓ Got customer statistics")
    return resp.json()

def list_customers(params=None, start_key=None):
    if params is None:
        params = {}
    if start_key:
        params["start_key"] = start_key
    resp = requests.get(api_url("/customers/"), params=params, headers=headers)
    assert resp.status_code == 200, f"List failed: {resp.text}"
    return resp.json()

def add_loyalty(customer_id, points, reason="Test bonus"):
    resp = requests.post(api_url(f"/customers/{customer_id}/loyalty/"), json={
        "points": points,
        "reason": reason
    }, headers=headers)
    assert resp.status_code == 200, f"Loyalty add failed: {resp.text}"
    return resp.json()

def test_qr_generate(customer_id, expiry_hours=24):
    resp = requests.get(api_url(f"/customers/{customer_id}/qr"), params={"expiry_hours": expiry_hours}, headers=headers)
    assert resp.status_code == 200, f"QR generate failed: {resp.text}"
    print(f"✓ Generated QR token for {customer_id}")
    return resp.json()["qr_token"]

def test_qr_verify(token):
    resp = requests.post(api_url("/qr/verify"), json={"token": token}, headers=headers)
    assert resp.status_code == 200, f"QR verify failed: {resp.text}"
    print("✓ QR token verified successfully")
    return resp.json()


if __name__ == "__main__":
    # ---------------------------
    # CLEANUP (COMMENTED OUT TO AVOID AUTH ERRORS)
    # ---------------------------
    # print("Cleaning up previously created test customers...")
    # data = list_customers({"limit": 100})
    # for cust in data.get("customers", []):
    #     if cust["email"].startswith("test_"):
    #         try:
    #             soft_delete_customer(cust["customer_id"])
    #             hard_delete_customer(cust["customer_id"])
    #         except:
    #             pass
    # print("✓ Cleanup done")

    # --- Registration ---
    cust1 = test_register_customer("test_cust1@example.com", "securepass123", {
        "first_name": "Test",
        "last_name": "User1",
        "phone": "09123456789",
        "source": "web"
    })
    cust1_id = cust1["id"]
    assert cust1["email"] == "test_cust1@example.com"
    assert cust1["loyalty_points"] == 0
    assert cust1["auth_mode"] == "email_password"

    # Test duplicate registration fails
    resp = requests.post(api_url("/customers/register/"), json={
        "email": "test_cust1@example.com", "password": "other"
    }, headers=headers)
    assert resp.status_code == 400
    print("✓ Duplicate registration rejected")

    # --- Login ---
    tokens = login_customer("test_cust1@example.com", "securepass123")
    assert "access_token" in tokens

    # --- Get customer by ID ---
    cust_detail = get_customer_by_id(cust1_id)
    assert cust_detail["email"] == "test_cust1@example.com"
    print("✓ Customer detail retrieved")

    # --- Update customer ---
    updated = update_customer(cust1_id, {
        "full_name": "Test User One Updated",
        "phone_number": "09987654321"
    })
    assert updated["full_name"] == "Test User One Updated"
    assert updated["phone_number"] == "09987654321"
    print("✓ Customer updated")

    # --- Change password ---
    resp = requests.put(api_url(f"/customers/{cust1_id}/"), json={
        "password": "newsecurepass456"
    }, headers=headers)
    assert resp.status_code == 200
    tokens2 = login_customer("test_cust1@example.com", "newsecurepass456")
    assert "access_token" in tokens2
    print("✓ Password changed and login with new password successful")

    # --- Loyalty points ---
    add_loyalty(cust1_id, 50)
    detail = get_customer_by_id(cust1_id)
    assert detail["loyalty_points"] == 50
    add_loyalty(cust1_id, 30)
    detail = get_customer_by_id(cust1_id)
    assert detail["loyalty_points"] == 80
    print("✓ Loyalty points added")

    # --- List customers (first page) ---
    page1 = list_customers({"limit": 2})
    assert len(page1["customers"]) <= 2
    assert "next_key" in page1
    print(f"✓ First page: {len(page1['customers'])} customers, has_more={page1['has_more']}")

    if page1["has_more"]:
        page2 = list_customers({"limit": 2}, start_key=page1["next_key"])
        assert len(page2["customers"]) > 0
        print(f"✓ Second page: {len(page2['customers'])} customers")

    # --- Search ---
    results = search_customers("Test User")
    assert any(c["customer_id"] == cust1_id for c in results), "Customer not found in search"
    print("✓ Search works")

    # --- Get by email ---
    cust_by_email = get_customer_by_email("test_cust1@example.com")
    assert cust_by_email is not None
    assert cust_by_email["customer_id"] == cust1_id
    print("✓ Get by email works")

    # --- Statistics ---
    stats = get_statistics()
    assert stats["total_customers"] > 0
    print("✓ Statistics retrieved")

    # --- QR code ---
    qr_token = test_qr_generate(cust1_id)
    qr_data = test_qr_verify(qr_token)
    assert qr_data["valid"] == True
    assert qr_data["customer"]["customer_id"] == cust1_id
    print("✓ QR flow works")

    # --- Soft delete and restore ---
    soft_delete_customer(cust1_id)
    resp = requests.get(api_url(f"/customers/{cust1_id}/"), headers=headers)
    assert resp.status_code == 404, "Should not be found after soft delete"
    restore_customer(cust1_id)
    restored = get_customer_by_id(cust1_id)
    assert restored["isDeleted"] == False
    assert restored["status"] == "active"
    print("✓ Soft delete/restore cycle passed")

    # --- Hard delete ---
    hard_delete_customer(cust1_id)
    resp = requests.get(api_url(f"/customers/{cust1_id}/"), headers=headers)
    assert resp.status_code == 404, "Customer should be permanently gone"

    print("\n=== All customer tests passed ===")
import requests
import json
from datetime import datetime, timezone, timedelta

BASE = "http://127.0.0.1:8000"

def api_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"

headers = {"Content-Type": "application/json"}

def test_health():
    resp = requests.get(api_url("/promotions/health/"), headers=headers)
    assert resp.status_code == 200
    print("✓ Health check passed")

def create_promotion(data):
    resp = requests.post(api_url("/promotions/"), json=data, headers=headers)
    assert resp.status_code == 201, resp.text
    promo = resp.json()
    print(f"✓ Promotion created: {promo['promotion']['promotion_id']} ({promo['promotion']['name']})")
    return promo["promotion"]

def list_promotions(params=None):
    resp = requests.get(api_url("/promotions/"), params=params, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    print(f"✓ Listed {len(data['promotions'])} promotions")
    return data

def get_promotion(promo_id):
    resp = requests.get(api_url(f"/promotions/{promo_id}/"), headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["promotion"]

def update_promotion(promo_id, data):
    resp = requests.put(api_url(f"/promotions/{promo_id}/"), json=data, headers=headers)
    assert resp.status_code == 200, resp.text
    print("✓ Promotion updated")
    return resp.json()["promotion"]

def activate_promotion(promo_id, reason=None):
    payload = {"reason": reason} if reason else {}
    resp = requests.post(api_url(f"/promotions/{promo_id}/activate/"), json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    print("✓ Promotion activated")
    return resp.json()["promotion"]

def deactivate_promotion(promo_id, reason="Testing"):
    resp = requests.post(api_url(f"/promotions/{promo_id}/deactivate/"), json={"reason": reason}, headers=headers)
    assert resp.status_code == 200, resp.text
    print(f"✓ Promotion {promo_id} deactivated")

def expire_promotion(promo_id):
    resp = requests.post(api_url(f"/promotions/{promo_id}/expire/"), headers=headers)
    assert resp.status_code == 200, resp.text
    print("✓ Promotion expired")

def apply_promotion(order_data, customer_id="test_user"):
    payload = {**order_data, "customer_id": customer_id}
    resp = requests.post(api_url("/promotions/apply/"), json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    print(f"✓ Applied: discount {result['data']['total_discount']}")
    return result["data"]

def search_promotions(query, limit=20):
    resp = requests.get(api_url("/promotions/search/"), params={"q": query, "limit": limit}, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    print(f"✓ Search for '{query}' returned {len(data['promotions'])} results")
    return data

def get_statistics(start=None, end=None):
    params = {}
    if start: params["start_date"] = start
    if end: params["end_date"] = end
    resp = requests.get(api_url("/promotions/statistics/"), params=params, headers=headers)
    assert resp.status_code == 200, resp.text
    print("✓ Got statistics")
    return resp.json()

def get_by_name(name):
    resp = requests.get(api_url("/promotions/by-name/"), params={"name": name}, headers=headers)
    if resp.status_code == 200:
        print(f"✓ Found by name: {name}")
        return resp.json()["promotion"]
    else:
        assert resp.status_code == 404
        print(f"✓ Name '{name}' not found")
        return None

def get_active_promotions():
    resp = requests.get(api_url("/promotions/active/"), headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    print(f"✓ Active promotions: {len(data['promotions'])}")
    return data['promotions']

def get_active_promo_ids():
    return {p["promotion_id"] for p in get_active_promotions()}

def soft_delete_promotion(promo_id, reason="Testing"):
    resp = requests.delete(api_url(f"/promotions/{promo_id}/"), json={"reason": reason}, headers=headers)
    assert resp.status_code == 200, resp.text
    print("✓ Promotion soft deleted")

def get_deleted_promotions():
    resp = requests.get(api_url("/promotions/deleted/"), headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    print(f"✓ Deleted promotions: {len(data['promotions'])}")
    return data["promotions"]

def restore_promotion(promo_id):
    resp = requests.post(api_url(f"/promotions/{promo_id}/restore/"), headers=headers)
    assert resp.status_code == 200, resp.text
    print("✓ Promotion restored")

def hard_delete_promotion(promo_id):
    resp = requests.delete(api_url(f"/promotions/{promo_id}/hard-delete/?confirm=yes"), headers=headers)
    assert resp.status_code == 200, resp.text
    print("✓ Promotion permanently deleted")

def get_audit_history(promo_id, limit=50):
    resp = requests.get(api_url(f"/promotions/{promo_id}/audit/"), params={"limit": limit}, headers=headers)
    assert resp.status_code == 200, resp.text
    history = resp.json()["audit"]
    print(f"✓ Audit entries: {len(history)}")
    return history

def get_qr_code(promo_id):
    resp = requests.get(api_url(f"/promotions/{promo_id}/qr/"), headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("Content-Type") == "image/png"
    print("✓ QR code generated")


if __name__ == "__main__":
    test_health()

    # Cleanup
    print("Cleaning up active promotions...")
    data = list_promotions({"status": "active"})
    for promo in data.get("promotions", []):
        deactivate_promotion(promo["promotion_id"], "Test cleanup")
    data = list_promotions({"status": "active"})
    assert len(data["promotions"]) == 0
    print("✓ Cleanup done")

    # Create test promotions
    std_start = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    std_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    promo_std = create_promotion({
        "name": "Standard 10% Off",
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
        "per_customer_limit": 3
    })
    promo_std_id = promo_std["promotion_id"]

    rec_start = "2026-01-01T00:00:00+00:00"
    rec_end = "2026-12-31T23:59:59+00:00"
    promo_rec = create_promotion({
        "name": "Sweldo Sale 5%",
        "description": "5% off on 15th & 30th",
        "type": "discount",
        "discount_value": "5%",
        "target_type": "all",
        "start_date": rec_start,
        "end_date": rec_end,
        "recurrence_rule": "monthly:15,30",
        "promotion_type": "percentage",
        "priority": 1,
        "stackable": True
    })
    promo_rec_id = promo_rec["promotion_id"]

    # Verify defaults
    detail = get_promotion(promo_std_id)
    assert detail["min_purchase_amount"] == 150
    assert detail["per_customer_limit"] == 3
    detail_rec = get_promotion(promo_rec_id)
    assert detail_rec["min_purchase_amount"] == 100
    assert detail_rec["per_customer_limit"] is None
    print("✓ Default values correct")

    # Activate
    activate_promotion(promo_std_id)
    activate_promotion(promo_rec_id)

    # Only standard is active
    active_ids = get_active_promo_ids()
    assert promo_std_id in active_ids and promo_rec_id not in active_ids
    print("✓ Active set correct")

    # Test minimum purchase enforcement
    apply_promotion({"items": [{"product_id":"p1","quantity":1,"price":50}], "total_amount":50}, "cust1")
    applied = apply_promotion({"items": [{"product_id":"p1","quantity":1,"price":50}], "total_amount":50}, "cust1")
    assert applied["total_discount"] == 0, "Should be 0 when below min purchase"
    print("✓ Minimum purchase enforced")

    # Per‑customer limit: use 3 times successfully
    order = {"items": [{"product_id":"p1","quantity":2,"price":200}], "total_amount":200}
    for i in range(3):
        apply_promotion(order, "cust1")
        print(f"  → Use {i+1} successful")
    # 4th attempt should fail
    fourth = apply_promotion(order, "cust1")
    assert fourth["total_discount"] == 0, f"Expected 0 after limit, got {fourth['total_discount']}"
    print("✓ Per‑customer limit enforced")

    # Rest of the tests (search, audit, QR, delete, restore, hard delete)
    search_promotions("Sweldo")
    get_statistics()
    audit = get_audit_history(promo_std_id)
    assert len(audit) >= 2
    get_qr_code(promo_std_id)
    soft_delete_promotion(promo_std_id, "Test")
    assert promo_std_id not in get_active_promo_ids()
    deleted = get_deleted_promotions()
    assert any(p["promotion_id"] == promo_std_id for p in deleted)
    restore_promotion(promo_std_id)
    restored = get_promotion(promo_std_id)
    assert not restored["isDeleted"] and restored["status"] == "draft"
    activate_promotion(promo_std_id)
    deactivate_promotion(promo_rec_id, "No longer needed")
    expire_promotion(promo_std_id)
    hard_delete_promotion(promo_std_id)
    resp = requests.get(api_url(f"/promotions/{promo_std_id}/"), headers=headers)
    assert resp.status_code == 404

    print("\n=== All promotion tests passed ===")
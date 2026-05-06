#!/usr/bin/env python
"""
test_notifs.py - Integration test for Notifications API (no auth).
Deletes ALL notifications first, then exercises every endpoint.
"""
import json, sys, requests
from cleanup_notifs import delete_all_notifications

BASE = "http://localhost:8000/api/v1/notifications"

def print_result(name, success, extra=""):
    print(f"{'✅ PASS' if success else '❌ FAIL'} - {name}" + (f" | {extra}" if extra else ""))

def print_failure(res):
    try:
        print(f"  → Status: {res.status_code}, Body: {json.dumps(res.json(), indent=2)}")
    except:
        print(f"  → Status: {res.status_code}, Raw: {res.text}")

def assert_status(res, expected):
    if res.status_code != expected:
        print_failure(res)
        return False, f"expected {expected} got {res.status_code}"
    return True, ""

# ---------- Test functions ----------
def test_create_notification():
    payload = {"title":"Test","message":"Hello","notification_type":"system","priority":"high","action_type":"system_alert","metadata":{}}
    res = requests.post(f"{BASE}/create/", json=payload)
    ok, msg = assert_status(res, 201)
    if not ok: return False, msg, None
    d = res.json().get("data", {})
    nid = d.get("notification_id")
    return (True, nid, d) if nid else (False, "no notification_id", None)

def test_create_inventory_alert():
    payload = {"product_id":"PROD-00001","current_stock":5,"product_name":"Test Product"}
    res = requests.post(f"{BASE}/create-inventory-alert/", json=payload)
    ok, msg = assert_status(res, 201)
    return ok, msg, res.json().get("data", {})

def test_list_notifications():
    res = requests.get(f"{BASE}/list/")
    ok, msg = assert_status(res, 200)
    if not ok: return False, msg
    data = res.json()
    return data.get("success") is True, f"count={data.get('count',0)}"

def test_list_archived():
    res = requests.get(f"{BASE}/list/?include_archived=true")
    return assert_status(res, 200)

def test_get_notification(nid):
    res = requests.get(f"{BASE}/get/{nid}/")
    return assert_status(res, 200)

def test_get_with_archived(nid):
    res = requests.get(f"{BASE}/get/{nid}/?include_archived=true")
    return assert_status(res, 200)

def test_recent():
    res = requests.get(f"{BASE}/recent/?hours=24&limit=5")
    return assert_status(res, 200)

def test_mark_read(nid):
    res = requests.patch(f"{BASE}/mark-read/{nid}/")
    return assert_status(res, 200)

def test_mark_unread(nid):
    res = requests.patch(f"{BASE}/mark-unread/{nid}/")
    return assert_status(res, 200)

def test_mark_all_read():
    res = requests.patch(f"{BASE}/mark-all-read/")
    return assert_status(res, 200)

def test_archive(nid):
    res = requests.patch(f"{BASE}/archive/{nid}/")
    return assert_status(res, 200)

def test_unarchive(nid):
    res = requests.patch(f"{BASE}/unarchive/{nid}/")
    return assert_status(res, 200)

def test_delete(nid):
    res = requests.delete(f"{BASE}/delete/{nid}/")
    return assert_status(res, 200)

def test_unread_count():
    res = requests.get(f"{BASE}/unread-count/")
    ok, msg = assert_status(res, 200)
    if not ok: return False, msg
    return "data" in res.json() and "unread_count" in res.json()["data"], "unread_count present"

def test_stats():
    res = requests.get(f"{BASE}/stats/")
    return assert_status(res, 200)

# ---------- Main ----------
def main():
    print("=" * 60)
    print("Notifications API Test Suite (no auth)")
    print("=" * 60)

    # Cleanup
    delete_all_notifications()
    print("Cleaned up existing notifications.\n")

    tests = []
    ok, nid, data = test_create_notification()
    tests.append(("Create Notification", ok, nid))
    if not ok:
        print("Cannot proceed without valid notification ID.")
        sys.exit(1)
    # nid is guaranteed to be the string ID, e.g., "NOTIF-00019"
    print(f"Created notification with ID: {nid}")

    ok2, msg2, _ = test_create_inventory_alert()
    tests.append(("Create Inventory Alert", ok2, msg2))

    # Retrieval
    tests.append(("List Notifications", *test_list_notifications()))
    tests.append(("Get Notification", *test_get_notification(nid)))
    tests.append(("Get Notification (include archived)", *test_get_with_archived(nid)))
    tests.append(("Recent Notifications", *test_recent()))
    tests.append(("List Archived", *test_list_archived()))

    # Status updates
    tests.append(("Mark Read", *test_mark_read(nid)))
    tests.append(("Mark Unread", *test_mark_unread(nid)))
    tests.append(("Mark All Read", *test_mark_all_read()))

    # Archive
    tests.append(("Archive", *test_archive(nid)))
    tests.append(("Unarchive", *test_unarchive(nid)))

    # Delete
    tests.append(("Delete", *test_delete(nid)))

    # Count & Stats
    tests.append(("Unread Count", *test_unread_count()))
    tests.append(("Stats", *test_stats()))

    # Summary
    print("\n" + "-" * 60)
    passed = 0
    for name, ok, detail in tests:
        print_result(name, ok, detail)
        if ok: passed += 1
    print("-" * 60)
    print(f"Results: {passed}/{len(tests)} passed")
    print("All tests passed! 🚀" if passed == len(tests) else "Some tests failed.")

if __name__ == "__main__":
    main()
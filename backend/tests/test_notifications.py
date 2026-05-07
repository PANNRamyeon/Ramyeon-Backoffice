import re
import requests

BASE = "http://127.0.0.1:8000"

def notif_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/notifications{path}"

headers = {"Content-Type": "application/json"}

# Tracks every notification ID created so cleanup can hard-delete them all
_created_ids = []


# ==================== HELPERS ====================

def create_notification(data):
    resp = requests.post(notif_url("/create/"), json=data, headers=headers)
    assert resp.status_code == 201, f"Create failed: {resp.text}"
    notif = resp.json()["data"]
    _created_ids.append(notif["notification_id"])
    return notif

def get_notification(notification_id, include_archived=False):
    params = {"include_archived": "true"} if include_archived else {}
    return requests.get(notif_url(f"/get/{notification_id}/"), params=params, headers=headers)

def delete_notification(notification_id):
    return requests.delete(notif_url(f"/delete/{notification_id}/"), headers=headers)

def cleanup_test_notifications():
    """Delete every notification created during the test run."""
    if not _created_ids:
        return
    print(f"\n=== Cleaning up {len(_created_ids)} test notification(s) ===")
    for nid in _created_ids[:]:
        try:
            resp = delete_notification(nid)
            status = "✓ deleted" if resp.status_code == 200 else f"~ already gone ({resp.status_code})"
            print(f"  {status}: {nid}")
        except Exception as e:
            print(f"  ! Failed to delete {nid}: {e}")


# ==================== TESTS ====================

def test_create_and_id_format():
    print("\n[Create & ID Format]")
    notif = create_notification({
        "title": "Test System Notification",
        "message": "This is a test notification",
        "notification_type": "system",
        "priority": "medium",
        "action_type": "system_alert",
        "metadata": {"test_key": "test_value"}
    })

    assert re.match(r'^NOTIF-\d{5}$', notif["notification_id"]), \
        f"ID format wrong (expected NOTIF-#####, got {notif['notification_id']})"
    print(f"  ✓ ID format correct: {notif['notification_id']}")

    assert notif["title"] == "Test System Notification"
    assert notif["message"] == "This is a test notification"
    assert notif["notification_type"] == "system"
    assert notif["priority"] == "medium"
    assert notif["action_type"] == "system_alert"
    assert notif["metadata"] == {"test_key": "test_value"}
    assert notif["is_read"] is False
    assert notif["archived"] is False
    assert notif["is_urgent"] is False       # medium priority
    assert notif["is_actionable"] is True    # has action_type
    assert "created_at" in notif
    assert "age_days" in notif
    print("  ✓ All response fields correct")

    return notif


def test_create_validation():
    print("\n[Create Validation]")

    # Missing title
    resp = requests.post(notif_url("/create/"), json={"message": "no title"}, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for missing title, got {resp.status_code}"
    print("  ✓ Missing title rejected with 400")

    # Missing message
    resp = requests.post(notif_url("/create/"), json={"title": "no message"}, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for missing message, got {resp.status_code}"
    print("  ✓ Missing message rejected with 400")

    # Invalid notification_type
    resp = requests.post(notif_url("/create/"), json={
        "title": "Bad Type", "message": "test", "notification_type": "invalid_type"
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for invalid type, got {resp.status_code}"
    print("  ✓ Invalid notification_type rejected with 400")

    # Invalid priority
    resp = requests.post(notif_url("/create/"), json={
        "title": "Bad Priority", "message": "test", "priority": "urgent"
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for invalid priority, got {resp.status_code}"
    print("  ✓ Invalid priority rejected with 400")


def test_urgent_flags():
    print("\n[Urgent Flags]")

    high = create_notification({
        "title": "High Priority Test", "message": "high urgency",
        "notification_type": "alert", "priority": "high"
    })
    assert high["is_urgent"] is True
    print(f"  ✓ priority=high sets is_urgent=True: {high['notification_id']}")

    critical = create_notification({
        "title": "Critical Priority Test", "message": "critical urgency",
        "notification_type": "security", "priority": "critical"
    })
    assert critical["is_urgent"] is True
    print(f"  ✓ priority=critical sets is_urgent=True: {critical['notification_id']}")

    low = create_notification({
        "title": "Low Priority Test", "message": "low urgency",
        "notification_type": "update", "priority": "low"
    })
    assert low["is_urgent"] is False
    print(f"  ✓ priority=low sets is_urgent=False: {low['notification_id']}")

    return high["notification_id"], critical["notification_id"]


def test_create_inventory_alert():
    print("\n[Inventory Alert]")

    # With threshold — model uses it in the message body
    resp = requests.post(notif_url("/create-inventory-alert/"), json={
        "product_id": "PROD-00001",
        "product_name": "Test Ramen",
        "current_stock": 5,
        "threshold": 10
    }, headers=headers)
    assert resp.status_code == 201, f"Inventory alert failed: {resp.text}"
    notif = resp.json()["data"]
    _created_ids.append(notif["notification_id"])
    assert notif["notification_type"] == "inventory"
    assert notif["priority"] == "high"
    assert notif["is_urgent"] is True
    assert "Test Ramen" in notif["title"]
    assert "5" in notif["message"]   # current_quantity in message
    assert "10" in notif["message"]  # threshold in message
    assert notif["metadata"]["product_id"] == "PROD-00001"
    assert notif["metadata"]["event"] == "inventory_change"
    assert notif["metadata"]["change_type"] == "low_stock"
    print(f"  ✓ Alert with threshold=10 created: {notif['notification_id']}")

    # Without threshold — defaults to 0, message shows 'Threshold: 0'
    resp = requests.post(notif_url("/create-inventory-alert/"), json={
        "product_id": "PROD-00002",
        "product_name": "Test Noodles",
        "current_stock": 3
    }, headers=headers)
    assert resp.status_code == 201, f"Inventory alert (no threshold) failed: {resp.text}"
    notif_no_thresh = resp.json()["data"]
    _created_ids.append(notif_no_thresh["notification_id"])
    assert "0" in notif_no_thresh["message"]  # threshold defaults to 0
    print(f"  ✓ Alert without threshold defaults to 0: {notif_no_thresh['notification_id']}")

    # Missing required field
    resp = requests.post(notif_url("/create-inventory-alert/"), json={
        "product_name": "Missing product_id and stock"
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for missing fields, got {resp.status_code}"
    print("  ✓ Missing required fields rejected with 400")


def test_get_notification(notification_id):
    print("\n[Get Notification]")

    resp = get_notification(notification_id)
    assert resp.status_code == 200, f"Get failed: {resp.text}"
    data = resp.json()["data"]
    assert data["notification_id"] == notification_id
    print(f"  ✓ Retrieved: {notification_id}")

    # Non-existent ID
    resp = get_notification("NOTIF-99999")
    assert resp.status_code == 404, f"Expected 404 for non-existent, got {resp.status_code}"
    print("  ✓ Non-existent ID returns 404")

    # Invalid format — validate_notification_id should reject
    resp = requests.get(notif_url("/get/NOT-AN-ID/"), headers=headers)
    assert resp.status_code == 400, f"Expected 400 for invalid format, got {resp.status_code}"
    print("  ✓ Invalid ID format returns 400")


def test_list_notifications():
    print("\n[List Notifications]")

    # Default list
    resp = requests.get(notif_url("/list/"), headers=headers)
    assert resp.status_code == 200, f"List failed: {resp.text}"
    body = resp.json()
    assert "count" in body and "data" in body
    print(f"  ✓ Default list: {body['count']} notifications")

    # Filter by notification_type
    resp = requests.get(notif_url("/list/"), params={"type": "system"}, headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["data"]:
        assert item["notification_type"] == "system", \
            f"Expected type=system, got {item['notification_type']}"
    print(f"  ✓ type=system filter: {resp.json()['count']} notifications")

    # Filter unread only
    resp = requests.get(notif_url("/list/"), params={"is_read": "false"}, headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["data"]:
        assert item["is_read"] is False, f"Expected unread, got is_read={item['is_read']}"
    print(f"  ✓ is_read=false filter: {resp.json()['count']} unread notifications")

    # Filter by action_type
    resp = requests.get(notif_url("/list/"), params={"action_type": "system_alert"}, headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["data"]:
        assert item["action_type"] == "system_alert"
    print(f"  ✓ action_type=system_alert filter: {resp.json()['count']} notifications")

    # Limit param
    resp = requests.get(notif_url("/list/"), params={"limit": 2}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) <= 2
    print("  ✓ limit=2 respected")


def test_recent_notifications():
    print("\n[Recent Notifications]")

    resp = requests.get(notif_url("/recent/"), headers=headers)
    assert resp.status_code == 200, f"Recent failed: {resp.text}"
    body = resp.json()
    assert "count" in body and "data" in body
    print(f"  ✓ Default (24h): {body['count']} notifications")

    # Custom window
    resp = requests.get(notif_url("/recent/"), params={"hours": 1, "limit": 5}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) <= 5
    print(f"  ✓ 1h window with limit=5: {resp.json()['count']} notifications")


def test_all_notifications():
    print("\n[All Notifications]")

    resp = requests.get(notif_url("/all/"), headers=headers)
    assert resp.status_code == 200, f"All failed: {resp.text}"
    body = resp.json()
    assert "count" in body and "data" in body
    print(f"  ✓ All notifications: {body['count']} returned")

    # Limit param
    resp = requests.get(notif_url("/all/"), params={"limit": 3}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) <= 3
    print("  ✓ limit=3 respected")

    # last_key is no longer supported (cursor pagination removed) — extra param is ignored safely
    resp = requests.get(notif_url("/all/"), params={"limit": 5, "last_key": "ignored"}, headers=headers)
    assert resp.status_code == 200, f"Unexpected error with stale last_key param: {resp.text}"
    print("  ✓ Stale last_key param is safely ignored")


def test_unread_count_and_stats():
    print("\n[Unread Count & Stats]")

    resp = requests.get(notif_url("/unread-count/"), headers=headers)
    assert resp.status_code == 200, f"Unread count failed: {resp.text}"
    body = resp.json()
    assert "unread_count" in body["data"]
    assert isinstance(body["data"]["unread_count"], int)
    print(f"  ✓ unread-count: {body['data']['unread_count']}")

    # stats/ is a separate URL but returns the same data
    resp = requests.get(notif_url("/stats/"), headers=headers)
    assert resp.status_code == 200, f"Stats failed: {resp.text}"
    stats = resp.json()
    assert "unread_count" in stats["data"]
    assert isinstance(stats["data"]["unread_count"], int)
    print(f"  ✓ stats: unread_count={stats['data']['unread_count']}")


def test_mark_read_and_unread(notification_id):
    print("\n[Mark Read / Unread]")

    # Starts unread
    data = get_notification(notification_id).json()["data"]
    assert data["is_read"] is False
    print("  ✓ Notification starts as unread")

    # Mark as read
    resp = requests.patch(notif_url(f"/mark-read/{notification_id}/"), headers=headers)
    assert resp.status_code == 200, f"Mark read failed: {resp.text}"
    assert get_notification(notification_id).json()["data"]["is_read"] is True
    print("  ✓ Marked as read")

    # Idempotent: mark read again
    resp = requests.patch(notif_url(f"/mark-read/{notification_id}/"), headers=headers)
    assert resp.status_code == 200, "Marking already-read notification should still return 200"
    print("  ✓ Marking already-read notification is idempotent (200)")

    # Mark back as unread
    resp = requests.patch(notif_url(f"/mark-unread/{notification_id}/"), headers=headers)
    assert resp.status_code == 200, f"Mark unread failed: {resp.text}"
    assert get_notification(notification_id).json()["data"]["is_read"] is False
    print("  ✓ Marked back as unread")

    # Non-existent notification
    resp = requests.patch(notif_url("/mark-read/NOTIF-99999/"), headers=headers)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    print("  ✓ Non-existent notification returns 404")

    # Invalid format
    resp = requests.patch(notif_url("/mark-read/NOT-AN-ID/"), headers=headers)
    assert resp.status_code == 400, f"Expected 400 for invalid ID format, got {resp.status_code}"
    print("  ✓ Invalid ID format returns 400")


def test_mark_all_read():
    print("\n[Mark All Read]")

    # Create two fresh unread notifications
    n1 = create_notification({
        "title": "Bulk Test 1", "message": "bulk test",
        "notification_type": "reminder", "priority": "low"
    })
    n2 = create_notification({
        "title": "Bulk Test 2", "message": "bulk test",
        "notification_type": "reminder", "priority": "low"
    })
    assert get_notification(n1["notification_id"]).json()["data"]["is_read"] is False
    assert get_notification(n2["notification_id"]).json()["data"]["is_read"] is False
    print("  ✓ Two unread notifications created")

    resp = requests.patch(notif_url("/mark-all-read/"), headers=headers)
    assert resp.status_code == 200, f"Mark all read failed: {resp.text}"
    body = resp.json()
    assert "modified_count" in body
    assert body["modified_count"] >= 2, \
        f"Expected at least 2 marked, got {body['modified_count']}"
    print(f"  ✓ Mark all read: {body['modified_count']} notifications marked")

    # Confirm both are now read
    assert get_notification(n1["notification_id"]).json()["data"]["is_read"] is True
    assert get_notification(n2["notification_id"]).json()["data"]["is_read"] is True
    print("  ✓ Both bulk-test notifications confirmed as read")


def test_archive_and_unarchive(notification_id):
    print("\n[Archive & Unarchive]")

    # Archive
    resp = requests.patch(notif_url(f"/archive/{notification_id}/"), headers=headers)
    assert resp.status_code == 200, f"Archive failed: {resp.text}"
    print(f"  ✓ Archived: {notification_id}")

    # Hidden from default get (include_archived defaults to false)
    resp = get_notification(notification_id)
    assert resp.status_code == 404, "Archived notification should return 404 without include_archived"
    print("  ✓ Archived notification is hidden by default (404)")

    # Visible with include_archived=true
    resp = get_notification(notification_id, include_archived=True)
    assert resp.status_code == 200, "Archived notification should be retrievable with include_archived=true"
    assert resp.json()["data"]["archived"] is True
    print("  ✓ Archived notification visible with include_archived=true")

    # Unarchive
    resp = requests.patch(notif_url(f"/unarchive/{notification_id}/"), headers=headers)
    assert resp.status_code == 200, f"Unarchive failed: {resp.text}"
    resp = get_notification(notification_id)
    assert resp.status_code == 200
    assert resp.json()["data"]["archived"] is False
    print(f"  ✓ Unarchived: {notification_id}")

    # Non-existent
    resp = requests.patch(notif_url("/archive/NOTIF-99999/"), headers=headers)
    assert resp.status_code == 404, f"Expected 404 for non-existent, got {resp.status_code}"
    print("  ✓ Archiving non-existent notification returns 404")

    # Unarchive a notification that is not archived
    resp = requests.patch(notif_url(f"/unarchive/{notification_id}/"), headers=headers)
    assert resp.status_code == 404, "Unarchiving a non-archived notification should return 404"
    print("  ✓ Unarchiving a non-archived notification returns 404")


def test_delete_notification():
    print("\n[Delete]")

    # Create a notification specifically for deletion
    temp = create_notification({
        "title": "To Be Deleted", "message": "deletion test",
        "notification_type": "system", "priority": "low"
    })
    temp_id = temp["notification_id"]
    _created_ids.remove(temp_id)   # we're deleting it manually; remove from cleanup list

    resp = delete_notification(temp_id)
    assert resp.status_code == 200, f"Delete failed: {resp.text}"
    print(f"  ✓ Deleted: {temp_id}")

    # Confirm permanently gone
    resp = get_notification(temp_id)
    assert resp.status_code == 404, "Deleted notification should return 404"
    print("  ✓ Deleted notification confirmed gone (404)")

    # Non-existent
    resp = delete_notification("NOTIF-99999")
    assert resp.status_code == 404, f"Expected 404 for non-existent, got {resp.status_code}"
    print("  ✓ Deleting non-existent notification returns 404")

    # Invalid format
    resp = requests.delete(notif_url("/delete/NOT-AN-ID/"), headers=headers)
    assert resp.status_code == 400, f"Expected 400 for invalid ID format, got {resp.status_code}"
    print("  ✓ Invalid ID format returns 400")


if __name__ == "__main__":
    print("=== Notification Tests ===")

    notif = test_create_and_id_format()
    notif_id = notif["notification_id"]

    test_create_validation()
    test_urgent_flags()
    test_create_inventory_alert()
    test_get_notification(notif_id)
    test_list_notifications()
    test_recent_notifications()
    test_all_notifications()
    test_unread_count_and_stats()
    test_mark_read_and_unread(notif_id)
    test_mark_all_read()
    test_archive_and_unarchive(notif_id)
    test_delete_notification()

    cleanup_test_notifications()

    print("\n=== All notification tests passed ===")

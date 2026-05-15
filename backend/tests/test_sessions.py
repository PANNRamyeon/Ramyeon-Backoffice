import re
import requests
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:8000"

# ==================== URL HELPERS ====================

def sess_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin/sessions{path}"

def admin_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"

headers = {"Content-Type": "application/json"}

# Admin credentials — must be an existing admin account
_test_username = "jeremylin"
_test_email    = "jlin@gmail.com"
_test_password = "password1234"
_test_user_id  = "USER-0005"
_test_session_id = None   # SESS-##### of the session created by login


# ==================== SETUP / TEARDOWN HELPERS ====================

def find_active_session(username):
    """Return the most recent active session dict for a username, or None."""
    resp = requests.get(sess_url(f"/user/{username}/"), headers=headers)
    if resp.status_code != 200:
        return None
    sessions = resp.json().get("data", [])
    active = [s for s in sessions if s.get("status") == "active"]
    if not active:
        return None
    return max(active, key=lambda s: s.get("login_time") or "")


def cleanup_test_data():
    """Expire any active sessions left over from this test run."""
    print(f"\n=== Cleanup: expiring leftover sessions for '{_test_username}' ===")
    try:
        resp = requests.post(sess_url("/bulk-control/"), json={
            "action": "expire", "usernames": [_test_username]
        }, headers=headers)
        count = resp.json().get("expired_count", 0) if resp.status_code == 200 else "?"
        print(f"  ✓ Expired {count} leftover session(s)")
    except Exception as e:
        print(f"  ! Cleanup failed: {e}")


# ==================== TESTS ====================

def test_setup():
    """Login as the admin account to acquire a JWT token and create a session."""
    global _test_session_id
    print("\n[Setup: Login & Acquire Token]")

    resp = requests.post(admin_url("/auth/login/"), json={
        "email": _test_email,
        "password": _test_password
    }, headers=headers)
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"

    token = resp.json().get("access_token")
    assert token, "access_token missing from login response"

    # Patch shared headers so every subsequent request carries the JWT
    headers["Authorization"] = f"Bearer {token}"
    print(f"  ✓ Logged in as {_test_email}, token acquired")

    # Try active session first
    session = find_active_session(_test_username)

    if not session:
        # log_login() may have failed silently — check for ANY session (any status)
        r = requests.get(sess_url(f"/user/{_test_username}/"), headers=headers)
        if r.status_code == 200:
            all_sessions = r.json().get("data", [])
            if all_sessions:
                session = max(all_sessions, key=lambda s: s.get("login_time") or "")
                print(f"  ~ No active session found; using most recent (status='{session.get('status')}')")

    if not session:
        # Nothing found at all — print recent sessions to help debug
        r = requests.get(sess_url("/"), params={"limit": 10}, headers=headers)
        if r.status_code == 200 and r.json()["data"]:
            print("  ! Recent sessions in DB (last 10):")
            for s in r.json()["data"]:
                print(f"      {s.get('log_id')} | {s.get('username')} | {s.get('status')} | {s.get('timestamp')}")
        else:
            print("  ! No sessions found in DB at all — session_logs counter may not be initialized.")
            print("    Run:  python init_counters.py  then restart the server and retry.")
        assert False, (
            f"No session record found for '{_test_username}' after login. "
            "Check server logs for errors from session_services.log_login()."
        )

    _test_session_id = session.get("log_id") or session.get("session_id")
    assert _test_session_id, "Session ID missing from session record"
    print(f"  ✓ Session located: {_test_session_id} (status='{session.get('status')}')")


def test_session_id_format():
    """Verify SESS-##### ID format on the active session."""
    print("\n[Session ID Format]")
    assert _test_session_id, "No session ID — run test_setup() first"

    # The session_id from to_dict() strips the prefix; the log_id from
    # SessionDisplayService uses the full SK.  Accept either form.
    raw = _test_session_id
    full_id = raw if raw.startswith("SESS-") else f"SESS-{raw}"

    assert re.match(r'^SESS-\d+$', full_id), \
        f"Expected SESS-##### format, got '{full_id}'"
    print(f"  ✓ ID format correct: {full_id}")


def test_get_session_logs():
    """GET /sessions/ returns list with expected fields."""
    print("\n[Get Session Logs]")

    resp = requests.get(sess_url("/"), headers=headers)
    assert resp.status_code == 200, f"List failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert "data" in body and "count" in body
    assert isinstance(body["data"], list)
    print(f"  ✓ Default list: {body['count']} session(s)")

    # Limit param
    resp = requests.get(sess_url("/"), params={"limit": 5}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) <= 5
    print("  ✓ limit=5 respected")

    if body["data"]:
        record = body["data"][0]
        for field in ("log_id", "username", "status", "timestamp", "log_source"):
            assert field in record, f"Missing field '{field}' in session log record"
        print("  ✓ Response fields present: log_id, username, status, timestamp, log_source")


def test_status_filter():
    """?status filter returns only matching sessions."""
    print("\n[Status Filter]")

    for status_val in ("active", "ended"):
        resp = requests.get(sess_url("/"), params={"status": status_val}, headers=headers)
        assert resp.status_code == 200, f"Filter by status={status_val} failed: {resp.text}"
        for item in resp.json()["data"]:
            assert item["status"].lower() == status_val, \
                f"Expected status={status_val}, got {item['status']}"
        print(f"  ✓ status={status_val}: {resp.json()['count']} session(s)")


def test_user_filter():
    """?user filter returns only sessions for that username."""
    print("\n[User Filter]")

    resp = requests.get(sess_url("/"), params={"user": _test_username}, headers=headers)
    assert resp.status_code == 200, f"User filter failed: {resp.text}"
    for item in resp.json()["data"]:
        assert item["username"] == _test_username, \
            f"Expected username={_test_username}, got {item['username']}"
    print(f"  ✓ user={_test_username}: {resp.json()['count']} session(s) returned")


def test_get_active_sessions():
    """GET /sessions/active/ includes our test session."""
    print("\n[Active Sessions]")

    resp = requests.get(sess_url("/active/"), headers=headers)
    assert resp.status_code == 200, f"Active sessions failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert "data" in body and "count" in body
    assert body["count"] >= 1, "Expected at least 1 active session (our test session)"

    usernames = [s.get("username") for s in body["data"]]
    assert _test_username in usernames, \
        f"Test user '{_test_username}' not in active sessions: {usernames}"
    print(f"  ✓ {body['count']} active session(s), test user present")


def test_session_statistics():
    """GET /sessions/statistics/ returns correct shape."""
    print("\n[Session Statistics]")

    resp = requests.get(sess_url("/statistics/"), headers=headers)
    assert resp.status_code == 200, f"Statistics failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    data = body["data"]

    for key in ("active_sessions", "today_sessions", "avg_session_duration"):
        assert key in data, f"Missing key '{key}' in statistics"
        assert isinstance(data[key], (int, float)), f"'{key}' should be numeric"

    assert data["active_sessions"] >= 1, "active_sessions should be >= 1"
    assert data["today_sessions"] >= 1, "today_sessions should be >= 1 (we just logged in)"
    print(f"  ✓ active={data['active_sessions']}, today={data['today_sessions']}, avg_duration={data['avg_session_duration']}s")


def test_get_user_sessions():
    """GET /sessions/user/<username>/ returns sessions for that user."""
    print("\n[User Sessions]")

    resp = requests.get(sess_url(f"/user/{_test_username}/"), headers=headers)
    assert resp.status_code == 200, f"User sessions failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert body.get("username") == _test_username
    assert body["count"] >= 1, f"Expected >= 1 session for {_test_username}"
    for session in body["data"]:
        assert session.get("username") == _test_username
    print(f"  ✓ {body['count']} session(s) for '{_test_username}'")

    # Non-existent username returns empty list, not an error
    resp = requests.get(sess_url("/user/nobody_exists_xyz/"), headers=headers)
    assert resp.status_code == 200, f"Expected 200 for unknown user, got {resp.status_code}"
    assert resp.json()["count"] == 0
    print("  ✓ Unknown username returns 200 with empty list")


def test_get_session_by_id():
    """GET /sessions/<session_id>/ retrieves the session correctly."""
    print("\n[Get Session by ID]")
    assert _test_session_id

    # Normalise to full SESS-##### form for the URL
    full_id = _test_session_id if _test_session_id.startswith("SESS-") \
        else f"SESS-{_test_session_id.zfill(5)}"

    resp = requests.get(sess_url(f"/{full_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get by ID failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    data = body["data"]
    assert data.get("username") == _test_username
    assert data.get("status") == "active"
    for field in ("session_id", "branch_id", "login_time", "status", "source"):
        assert field in data, f"Missing field '{field}' in session detail"
    print(f"  ✓ Retrieved session {full_id}: status={data['status']}, user={data['username']}")

    # Non-existent session ID
    resp = requests.get(sess_url("/SESS-99999/"), headers=headers)
    assert resp.status_code == 404, f"Expected 404 for non-existent session, got {resp.status_code}"
    print("  ✓ Non-existent session returns 404")


def test_session_display():
    """GET /sessions/display/ is equivalent to /sessions/ (alias)."""
    print("\n[Session Display]")

    resp = requests.get(sess_url("/display/"), headers=headers)
    assert resp.status_code == 200, f"Display failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert "data" in body
    print(f"  ✓ Display endpoint returns {body['count']} session(s)")


def test_combined_logs():
    """GET /sessions/combined-logs/ returns merged session and audit records."""
    print("\n[Combined Logs]")

    resp = requests.get(sess_url("/combined-logs/"), headers=headers)
    assert resp.status_code == 200, f"Combined logs failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert "data" in body and "total_count" in body
    print(f"  ✓ Combined (all): {body['total_count']} record(s)")

    # type=session filter
    resp = requests.get(sess_url("/combined-logs/"), params={"type": "session"}, headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["data"]:
        assert item.get("log_source") == "session", \
            f"Expected log_source=session, got {item.get('log_source')}"
    print(f"  ✓ type=session filter: {resp.json()['total_count']} record(s)")

    # type=audit filter
    resp = requests.get(sess_url("/combined-logs/"), params={"type": "audit"}, headers=headers)
    assert resp.status_code == 200
    print(f"  ✓ type=audit filter: {resp.json()['total_count']} record(s)")

    # Invalid type
    resp = requests.get(sess_url("/combined-logs/"), params={"type": "invalid"}, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for invalid type, got {resp.status_code}"
    print("  ✓ Invalid type returns 400")

    # Limit is capped at 500
    resp = requests.get(sess_url("/combined-logs/"), params={"limit": 1000}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) <= 500
    print("  ✓ limit=1000 is capped at 500")


def test_system_status():
    """GET /sessions/system-status/ returns operational status with all sections."""
    print("\n[System Status]")

    resp = requests.get(sess_url("/system-status/"), headers=headers)
    assert resp.status_code == 200, f"System status failed: {resp.text}"
    body = resp.json()

    assert body.get("status") == "operational"
    assert body.get("system") == "PANN User Management System"
    assert "statistics" in body
    assert "cleanup_status" in body
    assert "endpoints" in body
    assert "timestamp" in body

    stats = body["statistics"]
    for key in ("total_users", "total_customers", "total_products",
                "active_sessions", "today_sessions"):
        assert key in stats, f"Missing '{key}' in statistics"

    print(f"  ✓ System operational: {stats['total_users']} users, "
          f"{stats['active_sessions']} active sessions")


def test_cleanup_status():
    """GET /sessions/cleanup/status/ returns retention stats."""
    print("\n[Cleanup Status]")

    resp = requests.get(sess_url("/cleanup/status/"), headers=headers)
    assert resp.status_code == 200, f"Cleanup status failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    s = body["status"]

    for key in ("automated_cleanup_running", "cleanup_schedule",
                "sessions_older_than_6_months", "retention_policy"):
        assert key in s, f"Missing key '{key}' in cleanup status"

    assert isinstance(s["automated_cleanup_running"], bool)
    assert isinstance(s["sessions_older_than_6_months"], int)
    print(f"  ✓ Cleanup status: running={s['automated_cleanup_running']}, "
          f"old_sessions={s['sessions_older_than_6_months']}")


def test_cleanup_dry_run():
    """POST /sessions/cleanup/ with dry_run=True reports count without deleting."""
    print("\n[Cleanup Dry Run]")

    # Use a date range far in the past — our new test session won't be affected
    past_start = "2020-01-01"
    past_end   = (datetime.utcnow() - timedelta(days=200)).date().isoformat()

    resp = requests.post(sess_url("/cleanup/"), json={
        "start_date": past_start,
        "end_date": past_end,
        "dry_run": True
    }, headers=headers)
    assert resp.status_code == 200, f"Cleanup dry run failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert body.get("dry_run") is True
    assert body.get("deleted_count") == 0, "dry_run must not delete anything"
    assert "sessions_found" in body
    print(f"  ✓ Dry run: {body['sessions_found']} session(s) found, 0 deleted")

    # Invalid date format
    resp = requests.post(sess_url("/cleanup/"), json={
        "start_date": "not-a-date", "dry_run": True
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for bad date, got {resp.status_code}"
    print("  ✓ Invalid date format rejected with 400")


def test_export_json():
    """POST /sessions/export/ with format=json returns data payload."""
    print("\n[Export JSON]")

    resp = requests.post(sess_url("/export/"), json={
        "format": "json"
    }, headers=headers)
    assert resp.status_code == 200, f"JSON export failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert "data" in body and "count" in body
    assert body.get("format") == "json"
    assert isinstance(body["data"], list)
    print(f"  ✓ JSON export: {body['count']} session(s)")

    if body["data"]:
        record = body["data"][0]
        for field in ("session_id", "username", "status", "login_time"):
            assert field in record, f"Missing field '{field}' in export record"
        print("  ✓ Export record fields present")


def test_export_csv():
    """POST /sessions/export/ with format=csv returns a CSV file download."""
    print("\n[Export CSV]")

    today = datetime.utcnow().date().isoformat()
    resp = requests.post(sess_url("/export/"), json={
        "format": "csv",
        "date_filter": {"start_date": f"{today}T00:00:00", "end_date": f"{today}T23:59:59"}
    }, headers=headers)
    assert resp.status_code == 200, f"CSV export failed: {resp.text}"
    assert "text/csv" in resp.headers.get("Content-Type", ""), \
        f"Expected text/csv, got {resp.headers.get('Content-Type')}"
    assert "Content-Disposition" in resp.headers
    assert "session_export" in resp.headers["Content-Disposition"]
    assert len(resp.content) > 0

    # Verify CSV has header row
    first_line = resp.text.split("\n")[0]
    assert "username" in first_line, f"CSV header missing 'username': {first_line}"
    assert "status" in first_line, f"CSV header missing 'status': {first_line}"
    print(f"  ✓ CSV downloaded ({len(resp.content)} bytes), headers correct")

    # Invalid date format in date_filter
    resp = requests.post(sess_url("/export/"), json={
        "format": "csv",
        "date_filter": {"start_date": "bad-date", "end_date": today}
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for bad date_filter, got {resp.status_code}"
    print("  ✓ Invalid date_filter rejected with 400")


def test_auto_cleanup_control():
    """POST /sessions/cleanup/auto-control/ can start and stop the cleanup thread."""
    print("\n[Auto Cleanup Control]")

    # Start
    resp = requests.post(sess_url("/cleanup/auto-control/"), json={
        "action": "start",
        "cleanup_interval_hours": 720,
        "months_old": 6
    }, headers=headers)
    assert resp.status_code == 200, f"Start cleanup failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert body.get("interval_hours") == 720
    assert body.get("retention_months") == 6
    print(f"  ✓ Cleanup thread started (interval={body['interval_hours']}h)")

    # Starting again returns failure (already running)
    resp = requests.post(sess_url("/cleanup/auto-control/"), json={"action": "start"},
                         headers=headers)
    assert resp.status_code == 200
    assert resp.json().get("success") is False
    print("  ✓ Starting again returns success=False (already running)")

    # Stop
    resp = requests.post(sess_url("/cleanup/auto-control/"), json={"action": "stop"},
                         headers=headers)
    assert resp.status_code == 200, f"Stop cleanup failed: {resp.text}"
    assert resp.json().get("success") is True
    print("  ✓ Cleanup thread stopped")

    # Invalid action
    resp = requests.post(sess_url("/cleanup/auto-control/"), json={"action": "restart"},
                         headers=headers)
    assert resp.status_code == 400, f"Expected 400 for invalid action, got {resp.status_code}"
    print("  ✓ Invalid action rejected with 400")


def test_bulk_expire():
    """POST /sessions/bulk-control/ expires sessions for a list of usernames."""
    print("\n[Bulk Expire]")

    # Missing/invalid body
    resp = requests.post(sess_url("/bulk-control/"), json={
        "action": "expire", "usernames": []
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for empty list, got {resp.status_code}"
    print("  ✓ Empty usernames list rejected with 400")

    # Non-existent username — should succeed with expired_count=0
    resp = requests.post(sess_url("/bulk-control/"), json={
        "action": "expire", "usernames": ["ghost_user_xyz"]
    }, headers=headers)
    assert resp.status_code == 200, f"Bulk expire (no sessions) failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert body.get("expired_count") == 0
    print("  ✓ Unknown username returns success=True, expired_count=0")

    # Invalid action
    resp = requests.post(sess_url("/bulk-control/"), json={
        "action": "terminate", "usernames": [_test_username]
    }, headers=headers)
    assert resp.status_code == 400, f"Expected 400 for invalid action, got {resp.status_code}"
    print("  ✓ Invalid action rejected with 400")


def test_force_logout():
    """POST /sessions/<session_id>/force-logout/ ends the session."""
    print("\n[Force Logout]")
    assert _test_session_id

    full_id = _test_session_id if _test_session_id.startswith("SESS-") \
        else f"SESS-{_test_session_id.zfill(5)}"

    resp = requests.post(sess_url(f"/{full_id}/force-logout/"), headers=headers)
    assert resp.status_code == 200, f"Force logout failed: {resp.text}"
    body = resp.json()
    assert body.get("success") is True
    assert _test_username in body.get("message", "")
    assert "session_id" in body
    print(f"  ✓ Force logout succeeded: {body['message']}")

    # Non-existent session
    resp = requests.post(sess_url("/SESS-99999/force-logout/"), headers=headers)
    assert resp.status_code == 404, f"Expected 404 for non-existent session, got {resp.status_code}"
    print("  ✓ Force logout on non-existent session returns 404")


def test_session_ended_after_force_logout():
    """After force logout, the session should be retrievable with status='ended'."""
    print("\n[Session State After Force Logout]")
    assert _test_session_id

    full_id = _test_session_id if _test_session_id.startswith("SESS-") \
        else f"SESS-{_test_session_id.zfill(5)}"

    resp = requests.get(sess_url(f"/{full_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get ended session failed: {resp.text}"
    data = resp.json()["data"]

    assert data.get("status") == "ended", \
        f"Expected status='ended' after force logout, got '{data.get('status')}'"
    assert data.get("logout_time") is not None, "logout_time should be set"
    assert data.get("logout_reason") == "admin_forced"
    print(f"  ✓ Session status='ended', logout_reason='admin_forced'")

    # Should no longer appear in active sessions list
    resp = requests.get(sess_url("/active/"), headers=headers)
    assert resp.status_code == 200
    active_usernames = [s.get("username") for s in resp.json().get("data", [])]
    assert _test_username not in active_usernames, \
        "Force-logged-out user should not appear in active sessions"
    print(f"  ✓ User '{_test_username}' no longer in active sessions list")


# ==================== ENTRYPOINT ====================

if __name__ == "__main__":
    print("=== Session Tests ===")

    test_setup()
    test_session_id_format()
    test_get_session_logs()
    test_status_filter()
    test_user_filter()
    test_get_active_sessions()
    test_session_statistics()
    test_get_user_sessions()
    test_get_session_by_id()
    test_session_display()
    test_combined_logs()
    test_system_status()
    test_cleanup_status()
    test_cleanup_dry_run()
    test_export_json()
    test_export_csv()
    test_auto_cleanup_control()
    test_bulk_expire()

    # These two must run last — force_logout ends the active session
    test_force_logout()
    test_session_ended_after_force_logout()

    cleanup_test_data()

    print("\n=== All session tests passed ===")

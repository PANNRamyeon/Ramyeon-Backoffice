"""
System Logs Tests — Back Office
Runs against a live server at http://127.0.0.1:8000

Coverage:
  Session logs    — GET /api/v1/admin/sessions/
  Active sessions — GET /api/v1/admin/sessions/active/
  Statistics      — GET /api/v1/admin/sessions/statistics/
  Session detail  — GET /api/v1/admin/sessions/<id>/
  User sessions   — GET /api/v1/admin/sessions/user/<username>/
  Combined logs   — GET /api/v1/admin/sessions/combined-logs/

Run:
  cd backend
  python tests/test_system_logs.py
"""

import re
import requests

BASE = "http://127.0.0.1:8000"


def api_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"


headers = {"Content-Type": "application/json"}

ADMIN_EMAIL = "jlin@gmail.com"
ADMIN_PASSWORD = "password1234"


# =============================================================================
# AUTH
# =============================================================================

def login():
    resp = requests.post(
        f"{BASE}/api/v1/admin/auth/login/",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, \
        f"Login failed ({resp.status_code}). Check credentials.\n{resp.text}"
    token = resp.json().get("access_token")
    assert token, f"No access_token in login response: {resp.json()}"
    headers["Authorization"] = f"Bearer {token}"
    print(f"  ✓ Logged in as {ADMIN_EMAIL}")


# =============================================================================
# HELPERS
# =============================================================================

def _get_combined_logs(**params):
    resp = requests.get(api_url("/sessions/combined-logs/"), params=params, headers=headers)
    assert resp.status_code == 200, \
        f"Combined logs failed ({resp.status_code}): {resp.text}"
    body = resp.json()
    assert body.get("success") is True, f"success=False: {body}"
    assert "data" in body, "Response missing 'data' key"
    assert isinstance(body["data"], list), "'data' should be a list"
    return body


def _get_session_logs(**params):
    resp = requests.get(api_url("/sessions/"), params=params, headers=headers)
    assert resp.status_code == 200, \
        f"Session logs failed ({resp.status_code}): {resp.text}"
    body = resp.json()
    assert body.get("success") is True, f"success=False: {body}"
    assert "data" in body, "Response missing 'data' key"
    assert isinstance(body["data"], list), "'data' should be a list"
    return body


# =============================================================================
# TESTS — SESSION LOGS
# =============================================================================

def test_session_logs_structure():
    print("\n[Session Logs — Structure]")
    body = _get_session_logs(limit=20)
    assert "count" in body, "Response missing 'count' key"
    assert isinstance(body["count"], int), "'count' should be an integer"
    assert body["count"] == len(body["data"]), "count does not match len(data)"
    print(f"  ✓ Returned {body['count']} session log(s), structure OK")


def test_session_logs_required_fields():
    print("\n[Session Logs — Required Fields]")
    body = _get_session_logs(limit=10)
    entries = body["data"]
    if not entries:
        print("  ~ No session logs present — skipping field check")
        return

    required = {"log_id", "username", "event_type", "timestamp", "log_source"}
    for entry in entries:
        missing = required - entry.keys()
        assert not missing, f"Session log entry missing fields {missing}: {entry}"
        assert entry.get("log_source") == "session", \
            f"Expected log_source='session', got '{entry.get('log_source')}'"

    print(f"  ✓ All {len(entries)} entries have required fields and log_source='session'")


def test_session_logs_limit():
    print("\n[Session Logs — Limit Param]")
    body_5 = _get_session_logs(limit=5)
    body_2 = _get_session_logs(limit=2)
    assert len(body_5["data"]) <= 5, "Limit=5 returned more than 5 entries"
    assert len(body_2["data"]) <= 2, "Limit=2 returned more than 2 entries"
    print(f"  ✓ limit=5 → {len(body_5['data'])} entries, limit=2 → {len(body_2['data'])} entries")


def test_session_logs_status_filter():
    print("\n[Session Logs — Status Filter]")
    for s in ("active", "ended"):
        body = _get_session_logs(status=s, limit=20)
        entries = body["data"]
        for entry in entries:
            actual = (entry.get("status") or "").lower()
            assert actual == s, \
                f"Status filter '{s}' returned entry with status='{actual}'"
        print(f"  ✓ status={s} → {len(entries)} entries, all correct")


def test_session_logs_user_filter():
    print("\n[Session Logs — User Filter]")
    # Use the admin's username (jlin) derived from the email prefix
    username = ADMIN_EMAIL.split("@")[0]
    body = _get_session_logs(user=username, limit=20)
    entries = body["data"]
    for entry in entries:
        assert entry.get("username") == username, \
            f"User filter returned entry for '{entry.get('username')}', expected '{username}'"
    print(f"  ✓ user={username} → {len(entries)} entry/entries, all match")


# =============================================================================
# TESTS — ACTIVE SESSIONS
# =============================================================================

def test_active_sessions():
    print("\n[Active Sessions]")
    resp = requests.get(api_url("/sessions/active/"), headers=headers)
    assert resp.status_code == 200, \
        f"Active sessions failed ({resp.status_code}): {resp.text}"
    body = resp.json()
    assert body.get("success") is True, f"success=False: {body}"
    assert "data" in body, "Response missing 'data' key"
    assert "count" in body, "Response missing 'count' key"
    assert isinstance(body["data"], list), "'data' should be a list"
    assert body["count"] == len(body["data"]), "count does not match len(data)"
    print(f"  ✓ {body['count']} active session(s) returned, structure OK")


# =============================================================================
# TESTS — SESSION STATISTICS
# =============================================================================

def test_session_statistics():
    print("\n[Session Statistics]")
    resp = requests.get(api_url("/sessions/statistics/"), headers=headers)
    assert resp.status_code == 200, \
        f"Statistics failed ({resp.status_code}): {resp.text}"
    body = resp.json()
    assert body.get("success") is True, f"success=False: {body}"
    data = body.get("data", {})
    assert "active_sessions" in data, "'active_sessions' key missing"
    assert "today_sessions" in data, "'today_sessions' key missing"
    assert "avg_session_duration" in data, "'avg_session_duration' key missing"
    assert isinstance(data["active_sessions"], int), "'active_sessions' should be int"
    assert isinstance(data["today_sessions"], int), "'today_sessions' should be int"
    print(
        f"  ✓ active={data['active_sessions']}, today={data['today_sessions']}, "
        f"avg_duration={data['avg_session_duration']}s"
    )


# =============================================================================
# TESTS — SESSION DETAIL
# =============================================================================

def test_session_detail_404():
    print("\n[Session Detail — 404 on Unknown ID]")
    resp = requests.get(api_url("/sessions/SESS-99999/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for unknown session, got {resp.status_code}"
    print("  ✓ 404 returned for non-existent session ID")


def test_session_detail_valid():
    print("\n[Session Detail — Valid ID]")
    body = _get_session_logs(limit=1)
    entries = body["data"]
    if not entries:
        print("  ~ No session logs present — skipping detail check")
        return

    session_id = entries[0]["log_id"]
    resp = requests.get(api_url(f"/sessions/{session_id}/"), headers=headers)
    assert resp.status_code == 200, \
        f"Session detail failed ({resp.status_code}): {resp.text}"
    detail = resp.json()
    assert detail.get("success") is True, f"success=False: {detail}"
    assert "data" in detail, "Response missing 'data' key"
    print(f"  ✓ Detail fetched for {session_id}")


# =============================================================================
# TESTS — USER SESSIONS
# =============================================================================

def test_user_sessions():
    print("\n[User Sessions — by Username]")
    username = ADMIN_EMAIL.split("@")[0]
    resp = requests.get(api_url(f"/sessions/user/{username}/"), headers=headers)
    assert resp.status_code == 200, \
        f"User sessions failed ({resp.status_code}): {resp.text}"
    body = resp.json()
    assert body.get("success") is True, f"success=False: {body}"
    assert "data" in body, "Response missing 'data' key"
    assert "count" in body, "Response missing 'count' key"
    assert body.get("username") == username, \
        f"username echo mismatch: {body.get('username')}"
    print(f"  ✓ {body['count']} session(s) found for '{username}'")


# =============================================================================
# TESTS — COMBINED LOGS
# =============================================================================

def test_combined_logs_type_all():
    print("\n[Combined Logs — type=all]")
    body = _get_combined_logs(limit=50, type="all")
    assert "total_count" in body, "Response missing 'total_count' key"
    print(f"  ✓ type=all returned {len(body['data'])} log(s) (total_count={body['total_count']})")


def test_combined_logs_type_session():
    print("\n[Combined Logs — type=session]")
    body = _get_combined_logs(limit=20, type="session")
    entries = body["data"]
    for entry in entries:
        assert entry.get("log_source") == "session", \
            f"type=session returned non-session entry: {entry.get('log_source')}"
    print(f"  ✓ type=session returned {len(entries)} session-only log(s)")


def test_combined_logs_type_audit():
    print("\n[Combined Logs — type=audit]")
    body = _get_combined_logs(limit=20, type="audit")
    entries = body["data"]
    for entry in entries:
        assert entry.get("log_source") == "audit", \
            f"type=audit returned non-audit entry: {entry.get('log_source')}"
    print(f"  ✓ type=audit returned {len(entries)} audit-only log(s)")


def test_combined_logs_invalid_type():
    print("\n[Combined Logs — Invalid Type → 400]")
    resp = requests.get(
        api_url("/sessions/combined-logs/"),
        params={"type": "unknown"},
        headers=headers,
    )
    assert resp.status_code == 400, \
        f"Expected 400 for invalid type, got {resp.status_code}"
    print("  ✓ 400 returned for invalid type param")


def test_combined_logs_limit():
    print("\n[Combined Logs — Limit Param]")
    body_10 = _get_combined_logs(limit=10)
    body_3 = _get_combined_logs(limit=3)
    assert len(body_10["data"]) <= 10, "limit=10 returned more than 10 entries"
    assert len(body_3["data"]) <= 3, "limit=3 returned more than 3 entries"
    print(f"  ✓ limit=10 → {len(body_10['data'])}, limit=3 → {len(body_3['data'])}")


def test_combined_logs_required_fields():
    print("\n[Combined Logs — Required Fields on All Entries]")
    body = _get_combined_logs(limit=50, type="all")
    entries = body["data"]
    if not entries:
        print("  ~ No log entries present — skipping field check")
        return

    required = {"log_id", "username", "event_type", "timestamp", "log_source"}
    for entry in entries:
        missing = required - entry.keys()
        assert not missing, f"Log entry missing fields {missing}: {entry}"
        assert entry.get("log_source") in ("session", "audit"), \
            f"Unexpected log_source '{entry.get('log_source')}'"

    sources = {e["log_source"] for e in entries}
    print(
        f"  ✓ {len(entries)} entries checked — all have required fields "
        f"(sources present: {', '.join(sorted(sources))})"
    )


def test_combined_logs_sorted_descending():
    print("\n[Combined Logs — Sorted Newest-First]")
    body = _get_combined_logs(limit=50, type="all")
    entries = body["data"]
    timestamps = [e.get("timestamp") for e in entries if e.get("timestamp")]
    if len(timestamps) < 2:
        print("  ~ Fewer than 2 timestamped entries — skipping sort check")
        return

    # Convert to comparable strings (ISO or datetime)
    def to_str(ts):
        if hasattr(ts, 'isoformat'):
            return ts.isoformat()
        return str(ts)

    ts_strings = [to_str(t) for t in timestamps]
    for i in range(len(ts_strings) - 1):
        assert ts_strings[i] >= ts_strings[i + 1], (
            f"Entries not sorted descending at index {i}: "
            f"{ts_strings[i]} < {ts_strings[i + 1]}"
        )
    print(f"  ✓ {len(ts_strings)} timestamps verified as descending")


def test_combined_logs_log_id_format():
    print("\n[Combined Logs — Log ID Format]")
    body = _get_combined_logs(limit=50, type="all")
    entries = body["data"]
    if not entries:
        print("  ~ No entries — skipping ID format check")
        return

    sess_ids = [e["log_id"] for e in entries if e.get("log_source") == "session"]
    audit_ids = [e["log_id"] for e in entries if e.get("log_source") == "audit"]

    for sid in sess_ids:
        assert re.match(r'^SESS-\d+$', sid), \
            f"Session log_id '{sid}' does not match SESS-##### format"
    for aid in audit_ids:
        assert re.match(r'^AUD-\d+$', aid), \
            f"Audit log_id '{aid}' does not match AUD-##### format"

    print(
        f"  ✓ {len(sess_ids)} session ID(s) and {len(audit_ids)} audit ID(s) "
        f"match expected formats"
    )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=== Login ===")
    login()

    print("\n=== Session Logs ===")
    test_session_logs_structure()
    test_session_logs_required_fields()
    test_session_logs_limit()
    test_session_logs_status_filter()
    test_session_logs_user_filter()

    print("\n=== Active Sessions & Statistics ===")
    test_active_sessions()
    test_session_statistics()

    print("\n=== Session Detail ===")
    test_session_detail_404()
    test_session_detail_valid()

    print("\n=== User Sessions ===")
    test_user_sessions()

    print("\n=== Combined Logs ===")
    test_combined_logs_type_all()
    test_combined_logs_type_session()
    test_combined_logs_type_audit()
    test_combined_logs_invalid_type()
    test_combined_logs_limit()
    test_combined_logs_required_fields()
    test_combined_logs_sorted_descending()
    test_combined_logs_log_id_format()

    print("\n=== All system logs tests passed ===")

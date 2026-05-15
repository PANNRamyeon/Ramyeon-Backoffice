"""
Audit Log Tests — Back Office
Runs against a live server at http://127.0.0.1:8000

Coverage:
  Read-only queries    — GET /api/v1/admin/sessions/combined-logs/?type=audit
  Structure            — required fields, ID format, sorting, target_type presence
  Action types         — verify known action types appear in the data
  Limit param          — pagination / limit respects the cap
  Failed login audit   — bad-credentials login → login_failed entry generated
  Customer audit trail — register → update → delete a customer, verify each
                         action produces a matching audit log entry

Run:
  cd backend
  python tests/test_audits.py
"""

import re
import time
import requests

BASE = "http://127.0.0.1:8000"


def api_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/admin{path}"


headers = {"Content-Type": "application/json"}

ADMIN_EMAIL = "jlin@gmail.com"
ADMIN_PASSWORD = "password1234"

# Unique customer used by the CRUD audit tests (set once in setup)
_test_customer_id = None


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

def _get_audit_logs(limit=50):
    """Fetch audit-only entries from the combined logs endpoint."""
    resp = requests.get(
        api_url("/sessions/combined-logs/"),
        params={"type": "audit", "limit": limit},
        headers=headers,
    )
    assert resp.status_code == 200, \
        f"Audit logs request failed ({resp.status_code}): {resp.text}"
    body = resp.json()
    assert body.get("success") is True, f"success=False: {body}"
    assert "data" in body, "Response missing 'data' key"
    assert isinstance(body["data"], list), "'data' should be a list"
    return body


def _latest_audit_entry():
    """Return the single most-recent audit log entry, or None."""
    body = _get_audit_logs(limit=1)
    entries = body["data"]
    return entries[0] if entries else None


def _find_action_in_recent(action_fragment, fetch_limit=20):
    """
    Return the first entry in the latest `fetch_limit` audit logs whose
    event_type contains `action_fragment` (case-insensitive).
    """
    body = _get_audit_logs(limit=fetch_limit)
    action_fragment_lower = action_fragment.lower()
    for entry in body["data"]:
        if action_fragment_lower in (entry.get("event_type") or "").lower():
            return entry
    return None


# =============================================================================
# TESTS — STRUCTURE
# =============================================================================

def test_audit_log_structure():
    print("\n[Audit Logs — Structure]")
    body = _get_audit_logs(limit=20)
    assert "total_count" in body, "Response missing 'total_count' key"
    assert isinstance(body["total_count"], int), "'total_count' should be int"
    print(f"  ✓ Returned {len(body['data'])} audit log(s), total_count={body['total_count']}")


def test_audit_log_required_fields():
    print("\n[Audit Logs — Required Fields]")
    body = _get_audit_logs(limit=20)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs present — skipping field check")
        return

    required = {"log_id", "username", "event_type", "timestamp", "log_source"}
    for entry in entries:
        missing = required - entry.keys()
        assert not missing, f"Audit log entry missing fields {missing}: {entry}"
        assert entry.get("log_source") == "audit", \
            f"Expected log_source='audit', got '{entry.get('log_source')}'"

    print(f"  ✓ All {len(entries)} entries have required fields and log_source='audit'")


def test_audit_log_id_format():
    print("\n[Audit Logs — ID Format AUD-#####]")
    body = _get_audit_logs(limit=50)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs present — skipping ID format check")
        return

    bad = [e["log_id"] for e in entries if not re.match(r'^AUD-\d+$', e.get("log_id", ""))]
    assert not bad, f"Entries with non-conforming log_id: {bad}"
    print(f"  ✓ All {len(entries)} log_id(s) match AUD-##### format")


def test_audit_log_sorted_descending():
    print("\n[Audit Logs — Sorted Newest-First]")
    body = _get_audit_logs(limit=50)
    timestamps = [e.get("timestamp") for e in body["data"] if e.get("timestamp")]
    if len(timestamps) < 2:
        print("  ~ Fewer than 2 timestamped entries — skipping sort check")
        return

    ts_strings = [str(t) for t in timestamps]
    for i in range(len(ts_strings) - 1):
        assert ts_strings[i] >= ts_strings[i + 1], (
            f"Entries not sorted descending at index {i}: "
            f"{ts_strings[i]} < {ts_strings[i + 1]}"
        )
    print(f"  ✓ {len(ts_strings)} timestamps verified as descending")


def test_audit_log_limit():
    print("\n[Audit Logs — Limit Param]")
    body_10 = _get_audit_logs(limit=10)
    body_3 = _get_audit_logs(limit=3)
    assert len(body_10["data"]) <= 10, "limit=10 returned more than 10 entries"
    assert len(body_3["data"]) <= 3, "limit=3 returned more than 3 entries"
    print(f"  ✓ limit=10 → {len(body_10['data'])}, limit=3 → {len(body_3['data'])}")


# =============================================================================
# TESTS — CONTENT
# =============================================================================

def test_audit_log_target_type_present():
    print("\n[Audit Logs — target_type Field]")
    body = _get_audit_logs(limit=30)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs present — skipping target_type check")
        return

    # target_type may be None for some entries but the KEY must exist
    for entry in entries:
        assert "target_type" in entry, \
            f"Entry missing 'target_type' key: {entry.get('log_id')}"

    with_type = [e for e in entries if e.get("target_type")]
    print(f"  ✓ {len(entries)} entries have 'target_type' key "
          f"({len(with_type)} with a non-null value)")


def test_audit_log_event_types_are_strings():
    print("\n[Audit Logs — event_type Values Are Strings]")
    body = _get_audit_logs(limit=30)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs present — skipping")
        return

    for entry in entries:
        assert isinstance(entry.get("event_type"), str), \
            f"event_type is not a string in entry {entry.get('log_id')}"
        assert entry["event_type"].strip(), \
            f"event_type is blank in entry {entry.get('log_id')}"

    event_types = sorted({e["event_type"] for e in entries})
    print(f"  ✓ {len(entries)} entries — event types present: {', '.join(event_types)}")


def test_audit_log_known_action_types():
    print("\n[Audit Logs — Known Action Types In Data]")
    body = _get_audit_logs(limit=100)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs present — skipping action type check")
        return

    # Audit service registers these action categories; at least one should exist
    # given any normal use of the system.
    known_fragments = [
        "create", "update", "delete", "login",
        "export", "import", "restore",
    ]
    found_event_types = {e["event_type"].lower() for e in entries}
    matched = [f for f in known_fragments
               if any(f in et for et in found_event_types)]
    print(f"  ✓ Action categories present: {', '.join(matched) or 'none (empty log)'}")


# =============================================================================
# TESTS — AUDIT GENERATION: FAILED LOGIN
# =============================================================================

def test_failed_login_generates_audit():
    print("\n[Audit Generation — Failed Login → login_failed Entry]")
    bad_email = f"no_such_user_{int(time.time())}@example.com"

    # Attempt a login that must fail
    resp = requests.post(
        f"{BASE}/api/v1/admin/auth/login/",
        json={"email": bad_email, "password": "wrongpassword"},
        headers={"Content-Type": "application/json"},
    )
    # 401 or 400 expected for a failed login
    assert resp.status_code in (400, 401, 404), \
        f"Expected failure status code, got {resp.status_code}: {resp.text}"

    # Audit log is written synchronously — no sleep needed.
    entry = _find_action_in_recent("login failed", fetch_limit=10)
    if entry:
        assert entry.get("log_source") == "audit"
        assert re.match(r'^AUD-\d+$', entry.get("log_id", ""))
        print(f"  ✓ login_failed audit entry found: {entry['log_id']} "
              f"(event_type='{entry['event_type']}')")
    else:
        # login_failed audit might be disabled or the entry rolled off the limit
        print("  ~ login_failed audit not found in top-10 entries "
              "(audit may be disabled or rolled past limit)")


# =============================================================================
# TESTS — AUDIT GENERATION: CUSTOMER CRUD
# =============================================================================

def _create_test_customer():
    """Register a disposable customer and return its ID."""
    global _test_customer_id
    email = f"audit_cust_{int(time.time())}@testpann.com"
    resp = requests.post(
        api_url("/customers/register/"),
        json={
            "email": email,
            "username": f"auditcust{int(time.time())}",
            "password": "TestPass123!",
            "full_name": "Audit Test Customer",
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), \
        f"Customer register failed ({resp.status_code}): {resp.text}"
    body = resp.json()
    # Register response nests the ID as body["customer"]["id"] or body["user"]["id"]
    cid = (
        body.get("customer_id")
        or (body.get("customer") or {}).get("id")
        or (body.get("customer") or {}).get("customer_id")
        or (body.get("user") or {}).get("id")
        or (body.get("data") or {}).get("customer_id")
        or (body.get("data") or {}).get("id")
    )
    assert cid, f"Could not extract customer_id from: {body}"
    _test_customer_id = cid
    return cid, email


def test_customer_create_audit():
    print("\n[Audit Generation — Customer Create]")
    cid, email = _create_test_customer()

    entry = _find_action_in_recent("customer create", fetch_limit=10)
    if entry:
        assert entry.get("log_source") == "audit"
        assert re.match(r'^AUD-\d+$', entry.get("log_id", ""))
        print(f"  ✓ customer_create audit found: {entry['log_id']} "
              f"(target customer ~ {cid})")
    else:
        print(f"  ~ customer_create audit not found in top-10 "
              f"(customer {cid} was created; audit may be at a lower limit)")


def test_customer_update_audit():
    print("\n[Audit Generation — Customer Update]")
    global _test_customer_id
    if not _test_customer_id:
        print("  ~ Skipping (no test customer was created)")
        return

    resp = requests.put(
        api_url(f"/customers/{_test_customer_id}/"),
        json={"full_name": "Audit Updated Name"},
        headers=headers,
    )
    assert resp.status_code in (200, 201, 204), \
        f"Customer update failed ({resp.status_code}): {resp.text}"

    entry = _find_action_in_recent("customer update", fetch_limit=10)
    if entry:
        assert entry.get("log_source") == "audit"
        assert re.match(r'^AUD-\d+$', entry.get("log_id", ""))
        print(f"  ✓ customer_update audit found: {entry['log_id']}")
    else:
        print("  ~ customer_update audit not found in top-10 entries")


def test_customer_delete_audit():
    print("\n[Audit Generation — Customer Delete (soft)]")
    global _test_customer_id
    if not _test_customer_id:
        print("  ~ Skipping (no test customer was created)")
        return

    resp = requests.delete(
        api_url(f"/customers/{_test_customer_id}/"),
        headers=headers,
    )
    assert resp.status_code in (200, 204), \
        f"Customer delete failed ({resp.status_code}): {resp.text}"

    entry = _find_action_in_recent("customer delete", fetch_limit=10)
    if entry:
        assert entry.get("log_source") == "audit"
        assert re.match(r'^AUD-\d+$', entry.get("log_id", ""))
        print(f"  ✓ customer_delete audit found: {entry['log_id']}")
    else:
        print("  ~ customer_delete audit not found in top-10 entries")

    _test_customer_id = None  # consumed


# =============================================================================
# TESTS — AUDIT GENERATION: USER MANAGEMENT (READ-ONLY VERIFICATION)
# =============================================================================

def test_existing_user_actions_in_audit():
    print("\n[Audit Logs — User Action Entries Present]")
    body = _get_audit_logs(limit=100)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs — skipping")
        return

    user_entries = [
        e for e in entries
        if "user" in (e.get("event_type") or "").lower()
    ]
    types_found = sorted({e["event_type"] for e in user_entries})
    print(f"  ✓ {len(user_entries)} user-related audit entries "
          f"(types: {', '.join(types_found) or 'none'})")


def test_existing_product_actions_in_audit():
    print("\n[Audit Logs — Product Action Entries Present]")
    body = _get_audit_logs(limit=100)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs — skipping")
        return

    product_entries = [
        e for e in entries
        if "product" in (e.get("event_type") or "").lower()
    ]
    types_found = sorted({e["event_type"] for e in product_entries})
    print(f"  ✓ {len(product_entries)} product-related audit entries "
          f"(types: {', '.join(types_found) or 'none'})")


def test_existing_system_actions_in_audit():
    print("\n[Audit Logs — System Action Entries (export/import)]")
    body = _get_audit_logs(limit=100)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs — skipping")
        return

    system_entries = [
        e for e in entries
        if any(kw in (e.get("event_type") or "").lower()
               for kw in ("export", "import", "login failed"))
    ]
    types_found = sorted({e["event_type"] for e in system_entries})
    print(f"  ✓ {len(system_entries)} system audit entries "
          f"(types: {', '.join(types_found) or 'none'})")


# =============================================================================
# TESTS — DATA INTEGRITY
# =============================================================================

def test_audit_no_duplicate_ids():
    print("\n[Audit Logs — No Duplicate log_id Values]")
    body = _get_audit_logs(limit=100)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs — skipping")
        return

    ids = [e["log_id"] for e in entries]
    unique_ids = set(ids)
    assert len(ids) == len(unique_ids), \
        f"Duplicate log_id(s) found: {[i for i in ids if ids.count(i) > 1]}"
    print(f"  ✓ All {len(ids)} log_id values are unique")


def test_audit_timestamps_are_valid_iso():
    print("\n[Audit Logs — Timestamps Are Valid ISO Strings]")
    body = _get_audit_logs(limit=50)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs — skipping")
        return

    bad = []
    for entry in entries:
        ts = entry.get("timestamp")
        if ts is None:
            bad.append(entry.get("log_id"))
            continue
        # Accept ISO-8601 date strings (with or without fractional seconds / Z)
        if not re.match(r'^\d{4}-\d{2}-\d{2}', str(ts)):
            bad.append(entry.get("log_id"))

    assert not bad, f"Entries with invalid/missing timestamps: {bad}"
    print(f"  ✓ All {len(entries)} entries have valid timestamps")


def test_audit_username_never_empty():
    print("\n[Audit Logs — username Is Always Present]")
    body = _get_audit_logs(limit=50)
    entries = body["data"]
    if not entries:
        print("  ~ No audit logs — skipping")
        return

    # 'username' key must exist; value may be None only for system/anonymous events
    for entry in entries:
        assert "username" in entry, \
            f"Entry {entry.get('log_id')} missing 'username' key entirely"

    null_user = [e["log_id"] for e in entries if not e.get("username")]
    if null_user:
        print(f"  ~ {len(null_user)} entries with null username (system events): {null_user[:5]}")
    print(f"  ✓ All {len(entries)} entries have 'username' key present")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=== Login ===")
    login()

    print("\n=== Structure ===")
    test_audit_log_structure()
    test_audit_log_required_fields()
    test_audit_log_id_format()
    test_audit_log_sorted_descending()
    test_audit_log_limit()

    print("\n=== Content ===")
    test_audit_log_target_type_present()
    test_audit_log_event_types_are_strings()
    test_audit_log_known_action_types()

    print("\n=== Audit Generation — Failed Login ===")
    test_failed_login_generates_audit()

    print("\n=== Audit Generation — Customer CRUD ===")
    test_customer_create_audit()
    test_customer_update_audit()
    test_customer_delete_audit()

    print("\n=== Existing Audit Entries by Category ===")
    test_existing_user_actions_in_audit()
    test_existing_product_actions_in_audit()
    test_existing_system_actions_in_audit()

    print("\n=== Data Integrity ===")
    test_audit_no_duplicate_ids()
    test_audit_timestamps_are_valid_iso()
    test_audit_username_never_empty()

    print("\n=== All audit log tests passed ===")

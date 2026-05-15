"""
Shift Tests — POS flow
Runs against a live server at http://127.0.0.1:8000

Flow:
  1. POS login as dhoward@gmail.com
  2. Start a shift
  3. Verify active shift, detail, list, and filters
  4. Validate bad-input rejection
  5. Close the shift and verify final stats
  6. POS logout

Run:
  cd backend
  python tests/test_shifts.py
"""

import re
import requests

BASE = "http://127.0.0.1:8000"


def pos_url(path):
    if not path.startswith('/'):
        path = '/' + path
    return f"{BASE}/api/v1/pos{path}"


# Shared state populated by test_login
headers       = {"Content-Type": "application/json"}
_token        = None
_cashier_id   = None   # USER-##### extracted from login response
_shift_id     = None   # SHIFT-##### created in test_start_shift

_test_email    = "KT@gmail.com"
_test_password = "password1234"
_opening_cash  = 500.00
_closing_cash  = 650.00


# =============================================================================
# 1. AUTH
# =============================================================================

def test_login():
    """POST /pos/auth/login/ — authenticates the employee and returns JWT."""
    global _token, _cashier_id
    print("\n[POS Login]")

    resp = requests.post(pos_url("/auth/login/"), json={
        "email": _test_email,
        "password": _test_password,
    }, headers=headers)

    assert resp.status_code == 200, \
        f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body.get("success") is True, f"success=False: {body}"
    assert "access_token" in body, "access_token missing from login response"
    assert "user" in body, "user object missing from login response"

    _token = body["access_token"]
    _cashier_id = body["user"]["id"]
    headers["Authorization"] = f"Bearer {_token}"

    print(f"  ✓ Logged in — user: {_cashier_id}, role: {body['user']['role']}")

    # Verify token structure contains expected keys
    assert body.get("token_type") == "bearer"
    assert isinstance(body.get("expires_in"), int) and body["expires_in"] > 0
    print(f"  ✓ Token type=bearer, expires_in={body['expires_in']}s")


def test_login_wrong_password():
    """POST /pos/auth/login/ — rejects bad credentials with 401."""
    print("\n[POS Login — Wrong Password]")

    resp = requests.post(pos_url("/auth/login/"), json={
        "email": _test_email,
        "password": "wrong_password",
    }, headers={"Content-Type": "application/json"})

    assert resp.status_code == 401, \
        f"Expected 401 for wrong password, got {resp.status_code}"
    assert resp.json().get("success") is False
    print("  ✓ Wrong password rejected with 401")


def test_login_missing_fields():
    """POST /pos/auth/login/ — rejects missing email or password with 400."""
    print("\n[POS Login — Missing Fields]")

    base = {"Content-Type": "application/json"}

    resp = requests.post(pos_url("/auth/login/"), json={"email": _test_email}, headers=base)
    assert resp.status_code == 400, f"Expected 400 for missing password, got {resp.status_code}"
    print("  ✓ Missing password → 400")

    resp = requests.post(pos_url("/auth/login/"), json={"password": _test_password}, headers=base)
    assert resp.status_code == 400, f"Expected 400 for missing email, got {resp.status_code}"
    print("  ✓ Missing email → 400")


# =============================================================================
# 2. SHIFTS — Validation (before creating a shift)
# =============================================================================

def test_start_shift_validation():
    """POST /pos/shifts/start/ — rejects bad inputs before creating a real shift."""
    print("\n[Start Shift — Validation]")
    assert _cashier_id, "Run test_login first"

    # Missing cashier_id
    resp = requests.post(pos_url("/shifts/start/"), json={
        "opening_cash": _opening_cash
    }, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for missing cashier_id, got {resp.status_code}"
    print("  ✓ Missing cashier_id → 400")

    # Missing opening_cash
    resp = requests.post(pos_url("/shifts/start/"), json={
        "cashier_id": _cashier_id
    }, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for missing opening_cash, got {resp.status_code}"
    print("  ✓ Missing opening_cash → 400")

    # Negative opening_cash
    resp = requests.post(pos_url("/shifts/start/"), json={
        "cashier_id": _cashier_id,
        "opening_cash": -100
    }, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for negative opening_cash, got {resp.status_code}"
    print("  ✓ Negative opening_cash → 400")

    # Non-numeric opening_cash
    resp = requests.post(pos_url("/shifts/start/"), json={
        "cashier_id": _cashier_id,
        "opening_cash": "five hundred"
    }, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for non-numeric opening_cash, got {resp.status_code}"
    print("  ✓ Non-numeric opening_cash → 400")


# =============================================================================
# 3. SHIFTS — No active shift yet
# =============================================================================

def test_no_active_shift_before_start():
    """GET /pos/shifts/active/ — returns 404 before any shift is started."""
    print("\n[Active Shift — Before Start]")
    assert _cashier_id, "Run test_login first"

    resp = requests.get(pos_url("/shifts/active/"), params={
        "cashier_id": _cashier_id
    }, headers=headers)

    assert resp.status_code == 404, \
        f"Expected 404 (no active shift yet), got {resp.status_code}: {resp.text}"
    assert resp.json().get("success") is False
    print(f"  ✓ No active shift found for {_cashier_id} before start — correct")


# =============================================================================
# 4. SHIFTS — Start
# =============================================================================

def test_start_shift():
    """POST /pos/shifts/start/ — opens a new shift for the cashier."""
    global _shift_id
    print("\n[Start Shift]")
    assert _cashier_id, "Run test_login first"

    resp = requests.post(pos_url("/shifts/start/"), json={
        "cashier_id": _cashier_id,
        "opening_cash": _opening_cash,
    }, headers=headers)

    assert resp.status_code == 201, \
        f"Expected 201, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body.get("success") is True
    assert "shift" in body

    shift = body["shift"]
    _shift_id = shift.get("shift_id")
    assert _shift_id, "shift_id missing from response"
    assert re.match(r'^SHIFT-\d+$', _shift_id), \
        f"Expected SHIFT-##### format, got '{_shift_id}'"

    assert shift.get("status") == "open"
    assert shift.get("cashier_id") == _cashier_id
    assert shift.get("opening_cash") == _opening_cash
    assert shift.get("total_sales") == 0.0
    assert shift.get("total_transactions") == 0
    assert shift.get("cash_sales") == 0.0
    assert shift.get("end_time") is None

    print(f"  ✓ Shift started: {_shift_id}")
    print(f"  ✓ opening_cash={shift['opening_cash']}, status={shift['status']}")


def test_start_duplicate_shift():
    """POST /pos/shifts/start/ — rejects a second open shift for the same cashier."""
    print("\n[Start Shift — Duplicate Rejected]")
    assert _cashier_id and _shift_id, "Run test_start_shift first"

    resp = requests.post(pos_url("/shifts/start/"), json={
        "cashier_id": _cashier_id,
        "opening_cash": 200.00,
    }, headers=headers)

    assert resp.status_code == 400, \
        f"Expected 400 (duplicate shift), got {resp.status_code}: {resp.text}"
    assert resp.json().get("success") is False
    print(f"  ✓ Duplicate shift rejected with 400 — only one open shift allowed per cashier")


# =============================================================================
# 5. SHIFTS — Read operations
# =============================================================================

def test_get_active_shift():
    """GET /pos/shifts/active/ — returns the currently open shift."""
    print("\n[Get Active Shift]")
    assert _cashier_id and _shift_id, "Run test_start_shift first"

    resp = requests.get(pos_url("/shifts/active/"), params={
        "cashier_id": _cashier_id
    }, headers=headers)

    assert resp.status_code == 200, \
        f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body.get("success") is True
    shift = body["shift"]

    assert shift.get("shift_id") == _shift_id
    assert shift.get("status") == "open"
    assert shift.get("cashier_id") == _cashier_id

    print(f"  ✓ Active shift confirmed: {_shift_id}, status=open")

    # Missing cashier_id param
    resp = requests.get(pos_url("/shifts/active/"), headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for missing cashier_id, got {resp.status_code}"
    print("  ✓ Missing cashier_id param → 400")


def test_get_shift_by_id():
    """GET /pos/shifts/<shift_id>/ — retrieves the shift by its ID."""
    print("\n[Get Shift by ID]")
    assert _shift_id, "Run test_start_shift first"

    resp = requests.get(pos_url(f"/shifts/{_shift_id}/"), headers=headers)
    assert resp.status_code == 200, \
        f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body.get("success") is True
    shift = body["shift"]

    assert shift.get("shift_id") == _shift_id
    assert shift.get("cashier_id") == _cashier_id
    assert shift.get("status") == "open"
    assert shift.get("start_time") is not None

    for field in ("shift_id", "cashier_id", "status", "opening_cash",
                  "total_sales", "total_transactions", "cash_sales",
                  "payment_breakdown", "start_time"):
        assert field in shift, f"Missing field '{field}' in shift detail"

    print(f"  ✓ Shift {_shift_id} retrieved, all expected fields present")

    # Non-existent shift
    resp = requests.get(pos_url("/shifts/SHIFT-99999/"), headers=headers)
    assert resp.status_code == 404, \
        f"Expected 404 for non-existent shift, got {resp.status_code}"
    print("  ✓ Non-existent shift → 404")


def test_list_shifts():
    """GET /pos/shifts/ — returns a list of shifts with count."""
    print("\n[List Shifts]")

    resp = requests.get(pos_url("/shifts/"), headers=headers)
    assert resp.status_code == 200, \
        f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body.get("success") is True
    assert "shifts" in body and "count" in body
    assert isinstance(body["shifts"], list)
    assert body["count"] >= 1
    print(f"  ✓ Default list: {body['count']} shift(s)")


def test_list_shifts_cashier_filter():
    """GET /pos/shifts/?cashier_id= — filters to one cashier's shifts."""
    print("\n[List Shifts — Cashier Filter]")
    assert _cashier_id, "Run test_login first"

    resp = requests.get(pos_url("/shifts/"), params={
        "cashier_id": _cashier_id
    }, headers=headers)
    assert resp.status_code == 200, f"Cashier filter failed: {resp.text}"

    body = resp.json()
    for s in body["shifts"]:
        assert s.get("cashier_id") == _cashier_id, \
            f"Expected cashier_id={_cashier_id}, got {s.get('cashier_id')}"
    assert body["count"] >= 1
    print(f"  ✓ cashier_id filter: {body['count']} shift(s), all belong to {_cashier_id}")


def test_list_shifts_status_filter():
    """GET /pos/shifts/?status=open — filters to open shifts only."""
    print("\n[List Shifts — Status Filter]")

    resp = requests.get(pos_url("/shifts/"), params={"status": "open"}, headers=headers)
    assert resp.status_code == 200, f"Status filter failed: {resp.text}"

    body = resp.json()
    for s in body["shifts"]:
        assert s.get("status") == "open", \
            f"Expected status=open, got {s.get('status')}"
    print(f"  ✓ status=open: {body['count']} shift(s), all open")

    # Invalid status value
    resp = requests.get(pos_url("/shifts/"), params={"status": "paused"}, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for invalid status 'paused', got {resp.status_code}"
    print("  ✓ Invalid status value → 400")


# =============================================================================
# 6. SHIFTS — Close
# =============================================================================

def test_close_shift_validation():
    """POST /pos/shifts/<shift_id>/close/ — rejects bad closing_cash inputs."""
    print("\n[Close Shift — Validation]")
    assert _shift_id, "Run test_start_shift first"

    # Missing closing_cash
    resp = requests.post(pos_url(f"/shifts/{_shift_id}/close/"), json={},
                         headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for missing closing_cash, got {resp.status_code}"
    print("  ✓ Missing closing_cash → 400")

    # Negative closing_cash
    resp = requests.post(pos_url(f"/shifts/{_shift_id}/close/"), json={
        "closing_cash": -50
    }, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for negative closing_cash, got {resp.status_code}"
    print("  ✓ Negative closing_cash → 400")

    # Non-numeric closing_cash
    resp = requests.post(pos_url(f"/shifts/{_shift_id}/close/"), json={
        "closing_cash": "six hundred"
    }, headers=headers)
    assert resp.status_code == 400, \
        f"Expected 400 for non-numeric closing_cash, got {resp.status_code}"
    print("  ✓ Non-numeric closing_cash → 400")


def test_close_shift():
    """POST /pos/shifts/<shift_id>/close/ — closes the shift and computes variance."""
    print("\n[Close Shift]")
    assert _shift_id, "Run test_start_shift first"

    resp = requests.post(pos_url(f"/shifts/{_shift_id}/close/"), json={
        "closing_cash": _closing_cash,
    }, headers=headers)

    assert resp.status_code == 200, \
        f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body.get("success") is True
    assert body.get("message") == "Shift closed successfully"

    shift = body["shift"]
    assert shift.get("status") == "closed"
    assert shift.get("closing_cash") == _closing_cash
    assert shift.get("end_time") is not None

    # expected_cash = opening_cash + cash_sales (0 sales, so = opening_cash)
    expected_expected_cash = _opening_cash + 0.0
    assert shift.get("expected_cash") == expected_expected_cash, \
        f"expected_cash mismatch: got {shift.get('expected_cash')}, want {expected_expected_cash}"

    expected_variance = _closing_cash - expected_expected_cash
    assert shift.get("cash_variance") == expected_variance, \
        f"cash_variance mismatch: got {shift.get('cash_variance')}, want {expected_variance}"

    print(f"  ✓ Shift closed: {_shift_id}")
    print(f"  ✓ expected_cash={shift['expected_cash']}, "
          f"closing_cash={shift['closing_cash']}, "
          f"cash_variance={shift['cash_variance']}")


def test_close_already_closed_shift():
    """POST /pos/shifts/<shift_id>/close/ — rejects closing an already-closed shift."""
    print("\n[Close Shift — Already Closed]")
    assert _shift_id, "Run test_close_shift first"

    resp = requests.post(pos_url(f"/shifts/{_shift_id}/close/"), json={
        "closing_cash": _closing_cash,
    }, headers=headers)

    assert resp.status_code == 400, \
        f"Expected 400 for already-closed shift, got {resp.status_code}: {resp.text}"
    assert resp.json().get("success") is False
    print(f"  ✓ Re-closing an already-closed shift rejected with 400")


def test_shift_closed_state():
    """GET /pos/shifts/<shift_id>/ — confirms shift is fully closed after close."""
    print("\n[Shift State After Close]")
    assert _shift_id, "Run test_close_shift first"

    resp = requests.get(pos_url(f"/shifts/{_shift_id}/"), headers=headers)
    assert resp.status_code == 200, f"Get closed shift failed: {resp.text}"

    shift = resp.json()["shift"]
    assert shift.get("status") == "closed", \
        f"Expected status=closed, got '{shift.get('status')}'"
    assert shift.get("end_time") is not None, "end_time should be set"
    assert shift.get("closing_cash") is not None
    assert shift.get("expected_cash") is not None
    assert shift.get("cash_variance") is not None
    print(f"  ✓ status=closed, end_time set, all financial fields present")

    # Should not appear in active shifts anymore
    resp = requests.get(pos_url("/shifts/active/"), params={
        "cashier_id": _cashier_id
    }, headers=headers)
    assert resp.status_code == 404, \
        f"Closed shift should not show as active (expected 404), got {resp.status_code}"
    print(f"  ✓ Cashier has no active shift after close — correct")


def test_list_closed_shifts():
    """GET /pos/shifts/?status=closed — our shift appears in the closed list."""
    print("\n[List Closed Shifts]")
    assert _shift_id, "Run test_close_shift first"

    resp = requests.get(pos_url("/shifts/"), params={
        "cashier_id": _cashier_id,
        "status": "closed",
    }, headers=headers)
    assert resp.status_code == 200, f"List closed shifts failed: {resp.text}"

    body = resp.json()
    shift_ids = [s.get("shift_id") for s in body["shifts"]]
    assert _shift_id in shift_ids, \
        f"Closed shift {_shift_id} not found in closed shifts list: {shift_ids}"
    print(f"  ✓ Closed shift {_shift_id} present in closed list ({body['count']} total)")


# =============================================================================
# 7. AUTH — Logout
# =============================================================================

def test_logout():
    """POST /pos/auth/logout/ — blacklists the token and ends the session."""
    print("\n[POS Logout]")
    assert _token, "Run test_login first"

    resp = requests.post(pos_url("/auth/logout/"), headers=headers)
    assert resp.status_code == 200, \
        f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body.get("success") is True
    print("  ✓ Logged out successfully")

    # Token should be blacklisted — protected endpoints must now reject it
    resp = requests.get(pos_url(f"/shifts/{_shift_id}/"), headers=headers)
    assert resp.status_code == 401, \
        f"Expected 401 after logout (token should be blacklisted), got {resp.status_code}"
    print("  ✓ Blacklisted token correctly rejected with 401 on subsequent request")


# =============================================================================
# ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    print("=== Shift Tests (POS) ===")
    print(f"Server : {BASE}")
    print(f"User   : {_test_email}")

    test_login()
    test_login_wrong_password()
    test_login_missing_fields()

    test_start_shift_validation()
    test_no_active_shift_before_start()

    test_start_shift()
    test_start_duplicate_shift()

    test_get_active_shift()
    test_get_shift_by_id()
    test_list_shifts()
    test_list_shifts_cashier_filter()
    test_list_shifts_status_filter()

    test_close_shift_validation()
    test_close_shift()
    test_close_already_closed_shift()
    test_shift_closed_state()
    test_list_closed_shifts()

    test_logout()

    print("\n=== All shift tests passed ===")

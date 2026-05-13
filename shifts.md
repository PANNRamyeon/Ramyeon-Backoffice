# Shifts — Code Reference

**Base URL:** `http://localhost:8000/api/v1/`
**Auth:** All endpoints require a valid JWT (`Authorization: Bearer <token>`)

---

## Endpoints

### GET `pos/shifts/active/`
Get the currently open shift for a cashier.

**Query params:**
- `cashier_id` (required) — e.g. `USER-00001`

**Success (200):**
```json
{
  "success": true,
  "shift": {
    "_id": "SHIFT-00001",
    "cashier_id": "USER-00001",
    "status": "open",
    "opening_cash": 500.00,
    "start_time": "2026-05-13T08:00:00Z",
    "total_sales": 1200.00,
    "total_transactions": 5,
    "cash_sales": 800.00,
    "payment_breakdown": { "cash": 800.00, "gcash": 400.00 },
    "last_transaction_time": "2026-05-13T10:30:00Z"
  }
}
```

**No active shift (404):**
```json
{ "success": false, "error": "No active shift found" }
```

**View:** `ShiftActiveView.get` → `ShiftService.get_active_shift(cashier_id)`

---

### POST `pos/shifts/start/`
Open a new shift for a cashier.

**Request body:**
```json
{
  "cashier_id": "USER-00001",
  "opening_cash": 500.00
}
```

**Success (201):**
```json
{
  "success": true,
  "message": "Shift started successfully",
  "shift": {
    "_id": "SHIFT-00001",
    "cashier_id": "USER-00001",
    "status": "open",
    "opening_cash": 500.00,
    "start_time": "2026-05-13T08:00:00Z",
    "total_sales": 0,
    "total_transactions": 0,
    "cash_sales": 0,
    "payment_breakdown": {},
    "last_transaction_time": null
  }
}
```

**Errors:**
- `400` — `cashier_id` missing, `opening_cash` missing/non-numeric/negative
- `400` — cashier already has an open shift

**View:** `ShiftStartView.post` → `ShiftService.start_shift(cashier_id, opening_cash)`

---

### POST `pos/shifts/<shift_id>/close/`
Close an open shift and finalize its statistics.

**URL param:** `shift_id` — e.g. `SHIFT-00001`

**Request body:**
```json
{
  "closing_cash": 1234.56
}
```

**Success (200):**
```json
{
  "success": true,
  "message": "Shift closed successfully",
  "shift": {
    "_id": "SHIFT-00001",
    "status": "closed",
    "opening_cash": 500.00,
    "closing_cash": 1234.56,
    "start_time": "2026-05-13T08:00:00Z",
    "end_time": "2026-05-13T16:00:00Z",
    "total_sales": 734.56,
    "total_transactions": 12,
    "cash_sales": 500.00,
    "payment_breakdown": { "cash": 500.00, "gcash": 234.56 },
    "expected_cash": 1000.00,
    "cash_variance": 234.56
  }
}
```

**Errors:**
- `400` — `closing_cash` missing/non-numeric/negative
- `400` — shift not found or already closed
- `500` — DB write failed

**On close, the service:**
1. Recalculates stats by querying all `completed`, non-voided sales for that `shift_id`
2. Computes `expected_cash = opening_cash + cash_sales`, then `cash_variance = closing_cash - expected_cash`
3. Writes final stats + `status: "closed"` + `end_time` to the shift document
4. Sends a shift summary email to verified admins via SendGrid

**View:** `ShiftCloseView.post` → `ShiftService.end_shift(shift_id, closing_cash, recalculate=True)`

---

### GET `pos/shifts/<shift_id>/`
Get a single shift by its ID.

**URL param:** `shift_id` — e.g. `SHIFT-00001`

**Success (200):**
```json
{
  "success": true,
  "shift": { ... }
}
```

**Not found (404):**
```json
{ "success": false, "error": "Shift not found" }
```

**View:** `ShiftDetailView.get` → `ShiftService.get_shift_by_id(shift_id)`

---

### GET `pos/shifts/`
List shifts. Returns up to 50 by default, sorted newest first.

**Query params:**
- `cashier_id` (optional) — filter to one cashier's shifts
- `status` (optional) — `open` or `closed`
- `limit` (optional) — max results (default `50`)

**Success (200):**
```json
{
  "success": true,
  "shifts": [ { ... }, { ... } ],
  "count": 2
}
```

**View:** `ShiftListView.get` → `ShiftService.get_cashier_shifts()` or `ShiftService.get_all_shifts()`

---

## Shift Document Schema

| Field | Type | Description |
|---|---|---|
| `_id` | string | `SHIFT-#####` (5-digit, from atomic counter) |
| `cashier_id` | string | References the cashier user |
| `status` | string | `"open"` or `"closed"` |
| `opening_cash` | float | Cash in drawer at shift start |
| `closing_cash` | float | Cash in drawer at shift end |
| `start_time` | datetime | UTC timestamp of shift open |
| `end_time` | datetime | UTC timestamp of shift close |
| `total_sales` | float | Sum of all completed sale amounts |
| `total_transactions` | int | Count of completed, non-voided sales |
| `cash_sales` | float | Subset of `total_sales` paid in cash |
| `payment_breakdown` | object | Amount per payment method e.g. `{"cash": 500, "gcash": 200}` |
| `expected_cash` | float | `opening_cash + cash_sales` |
| `cash_variance` | float | `closing_cash - expected_cash` (negative = short) |
| `last_transaction_time` | datetime | UTC timestamp of most recent sale (updated in real-time) |

---

## Files

| File | Purpose |
|---|---|
| `backend/app/kpi_views/POS/shift_views.py` | API views — request validation, HTTP responses |
| `backend/app/services/POS/shift_service.py` | Business logic — DB queries, stats calculation, email trigger |
| `backend/app/urls.py` (lines 436–443) | URL routing |

---

## Rules

- Only one shift can be open per cashier at a time — starting a second raises a `400`.
- A sale cannot be created without a valid open shift.
- Shifts are never deleted — `status` moves from `"open"` to `"closed"` only.
- Stats (`total_sales`, `total_transactions`, etc.) are updated in real-time as sales are recorded, then **recalculated from source** on close to ensure accuracy.

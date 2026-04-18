# Batch API Sample Requests (Postman / curl)

Essential batch endpoints only. For product-level stock movements (add, remove, set, restock), use the **Product** stock endpoints in `PRODUCT_API_SAMPLES.md`.

Base URL for all batch endpoints: **`/api/v1/admin/`**

Replace `{{baseURL}}` with your server (e.g. `http://localhost:8000`) and add auth headers if required.

**Batch activation:** Batches linked to a shipment (`shipment_id`) become usable automatically when that shipment is set as **received** (on shipment create with status `received` or when the shipment is updated to status `received`). There is no separate activate-batch endpoint.

---

## 1. List batches

### GET – List all batches (with optional filters)

**URL:** `{{baseURL}}/api/v1/admin/batches/`

**Query parameters:**

| Parameter             | Type   | Description                                      |
|-----------------------|--------|--------------------------------------------------|
| `product_id`          | string | Filter by product ID                             |
| `status`              | string | Filter by status: `active`, `exhausted`, `expired` |
| `supplier_id`         | string | Filter by supplier ID                            |
| `shipment_id`         | string | Filter by shipment ID                            |
| `expiring_soon`       | string | `true` to only return batches expiring soon      |
| `days_ahead`          | number | With `expiring_soon`: days ahead (default 30)    |
| `enrich_with_product` | string | `true` to include product info on each batch    |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/batches/
GET {{baseURL}}/api/v1/admin/batches/?product_id=prod-123
GET {{baseURL}}/api/v1/admin/batches/?status=active
GET {{baseURL}}/api/v1/admin/batches/?supplier_id=supp-456
GET {{baseURL}}/api/v1/admin/batches/?shipment_id=SHIP-00001
GET {{baseURL}}/api/v1/admin/batches/?expiring_soon=true&days_ahead=14
GET {{baseURL}}/api/v1/admin/batches/?enrich_with_product=true
```

---

## 2. Create batch

### POST – Create a batch (receive stock)

**URL:** `{{baseURL}}/api/v1/admin/batches/create/`

**Request body (required + optional):**

| Field               | Type   | Required | Description                    |
|---------------------|--------|----------|--------------------------------|
| `product_id`        | string | Yes      | Product ID                     |
| `quantity_received` | number | Yes      | Quantity received              |
| `supplier_id`       | string | No       | Supplier ID (validated if set) |
| `shipment_id`       | string | No       | Shipment ID                    |
| `batch_number`      | string | No       | Custom batch number            |
| `cost_price`        | number | No       | Cost per unit                  |
| `expiry_date`       | string | No       | ISO date                       |
| `date_received`     | string | No       | ISO date                       |

**Example (minimal):**

```json
{
  "product_id": "prod-123",
  "quantity_received": 100
}
```

**Example (full):**

```json
{
  "product_id": "prod-00014",
  "quantity_received": 100,
  "supplier_id": "SUPP-007",
  "shipment_id": "SHIP-00002",
  "batch_number": "BATCH-2025-001",
  "cost_price": 2.50,
  "expiry_date": "2025-12-31T23:59:59Z",
  "date_received": "2025-02-22T10:00:00Z"
}
```

**Postman:** Method **POST**, URL `{{baseURL}}/api/v1/admin/batches/create/`, Body → raw → JSON, paste one of the above.

---

## 3. Batch detail

### GET – Get batch by ID

**URL:** `{{baseURL}}/api/v1/admin/batches/{{batch_id}}/`

**Path:** Replace `{{batch_id}}` with the batch ID (e.g. `BATCH-00001` or the DynamoDB composite key value).

**Query parameters:**

| Parameter          | Type   | Description                    |
|--------------------|--------|--------------------------------|
| `include_supplier` | string | `true` to add `supplier_info`  |
| `include_shipment` | string | `true` to add `shipment_info`  |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/batches/BATCH-00001/
GET {{baseURL}}/api/v1/admin/batches/BATCH-00001/?include_supplier=true
GET {{baseURL}}/api/v1/admin/batches/BATCH-00001/?include_shipment=true
```

### PUT – Update batch (metadata only; use quantity endpoint for quantity changes)

**URL:** `{{baseURL}}/api/v1/admin/batches/{{batch_id}}/`

**Request body (all optional):** Any updatable fields (e.g. `cost_price`, `expiry_date`). Read-only: `pk`, `sk`.

**Example:**

```json
{
  "cost_price": 2.75
}
```

---

## 4. Update batch quantity

### PUT – Reduce quantity (sales / usage)

**URL:** `{{baseURL}}/api/v1/admin/batches/{{batch_id}}/quantity/`

**Request body:**

| Field             | Type   | Required | Description                          |
|-------------------|--------|----------|--------------------------------------|
| `quantity_used`  | number | Yes      | Amount to deduct (must be &gt; 0)    |
| `adjustment_type`| string | No       | e.g. `sale`, `correction` (default)  |
| `adjusted_by`    | string | No       | User or system identifier            |

**Example:**

```json
{
  "quantity_used": 10,
  "adjustment_type": "sale",
  "adjusted_by": "user-123"
}
```

---

## 5. Batches by product

### GET – List batches for a product

**URL:** `{{baseURL}}/api/v1/admin/batches/product/{{product_id}}/`

**Query parameters:**

| Parameter          | Type   | Description                   |
|--------------------|--------|-------------------------------|
| `status`           | string | Filter by status              |
| `include_supplier` | string | `true` to add supplier info   |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/batches/product/prod-123/
GET {{baseURL}}/api/v1/admin/batches/product/prod-123/?status=active
GET {{baseURL}}/api/v1/admin/batches/product/prod-123/?include_supplier=true
```

### GET – Product with batch summary

**URL:** `{{baseURL}}/api/v1/admin/batches/product/{{product_id}}/summary/`

**Example:**

```
GET {{baseURL}}/api/v1/admin/batches/product/prod-123/summary/
```

---

## 6. Batches by supplier

### GET – List batches for a supplier

**URL:** `{{baseURL}}/api/v1/admin/batches/supplier/{{supplier_id}}/`

**Query parameters:**

| Parameter          | Type   | Description                                   |
|--------------------|--------|-----------------------------------------------|
| `status`           | string | Filter by status                              |
| `product_id`       | string | Filter by product                             |
| `expiring_soon`    | string | `true` for batches expiring soon              |
| `days_ahead`       | number | With `expiring_soon` (default 30)             |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/batches/supplier/supp-456/
GET {{baseURL}}/api/v1/admin/batches/supplier/supp-456/?status=active
GET {{baseURL}}/api/v1/admin/batches/supplier/supp-456/?expiring_soon=true&days_ahead=7
```

---

## 7. Expiring batches and expiry summary

### GET – Batches expiring within N days

**URL:** `{{baseURL}}/api/v1/admin/batches/expiring/`

**Query parameters:**

| Parameter           | Type   | Description                          |
|---------------------|--------|--------------------------------------|
| `days_ahead`        | number | Days ahead (default 30)              |
| `group_by_supplier` | string | `true` to group results by supplier  |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/batches/expiring/
GET {{baseURL}}/api/v1/admin/batches/expiring/?days_ahead=14
GET {{baseURL}}/api/v1/admin/batches/expiring/?days_ahead=7&group_by_supplier=true
```

### GET – Products with expiry summary

**URL:** `{{baseURL}}/api/v1/admin/batches/expiry-summary/`

**Query parameters:**

| Parameter    | Type   | Description           |
|--------------|--------|-----------------------|
| `days_ahead` | number | Days ahead (default 30) |

**Example:**

```
GET {{baseURL}}/api/v1/admin/batches/expiry-summary/
GET {{baseURL}}/api/v1/admin/batches/expiry-summary/?days_ahead=14
```

---

## 8. Batch statistics

### GET – Batch statistics and analytics

**URL:** `{{baseURL}}/api/v1/admin/batches/statistics/`

**Query parameters:**

| Parameter           | Type   | Description                    |
|---------------------|--------|--------------------------------|
| `group_by_supplier` | string | `true` to add `by_supplier`   |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/batches/statistics/
GET {{baseURL}}/api/v1/admin/batches/statistics/?group_by_supplier=true
```

**Response (concept):** `total_batches`, `active_batches`, `exhausted_batches`, `expired_batches`, `expiring_within_7_days`, `total_active_stock`, `batch_status_breakdown`, and optionally `by_supplier`.

---

## 9. Check expiry alerts / mark expired

### POST – Check expiring batches and run alerts

**URL:** `{{baseURL}}/api/v1/admin/batches/check-expiry/`

**Request body (optional):**

```json
{
  "days_ahead": 7
}
```

**Example:** `POST {{baseURL}}/api/v1/admin/batches/check-expiry/` with body above or empty `{}`.

### POST – Mark expired batches as expired

**URL:** `{{baseURL}}/api/v1/admin/batches/mark-expired/`

**Request body:** None (or empty `{}`).

**Example:** `POST {{baseURL}}/api/v1/admin/batches/mark-expired/`

---

## Quick reference (copy into Postman)

| Method | Endpoint | Purpose |
|--------|----------|--------|
| GET    | `/api/v1/admin/batches/` | List batches (optional filters) |
| POST   | `/api/v1/admin/batches/create/` | Create batch |
| GET    | `/api/v1/admin/batches/{{batch_id}}/` | Batch detail |
| PUT    | `/api/v1/admin/batches/{{batch_id}}/` | Update batch metadata |
| PUT    | `/api/v1/admin/batches/{{batch_id}}/quantity/` | Update quantity on this batch |
| GET    | `/api/v1/admin/batches/product/{{product_id}}/` | Batches by product |
| GET    | `/api/v1/admin/batches/product/{{product_id}}/summary/` | Product + batch summary |
| GET    | `/api/v1/admin/batches/supplier/{{supplier_id}}/` | Batches by supplier |
| GET    | `/api/v1/admin/batches/expiring/` | Expiring batches |
| GET    | `/api/v1/admin/batches/expiry-summary/` | Products expiry summary |
| GET    | `/api/v1/admin/batches/statistics/` | Batch statistics |
| POST   | `/api/v1/admin/batches/check-expiry/` | Check expiry alerts |
| POST   | `/api/v1/admin/batches/mark-expired/` | Mark expired batches |

---

## Suggested test order

1. **GET** `batches/` – confirm list works.
2. **POST** `batches/create/` – create a batch (use a valid `product_id` and optionally `supplier_id` from your DB).
3. **GET** `batches/{{batch_id}}/` – use the returned batch ID.
4. **PUT** `batches/{{batch_id}}/` – update batch metadata (e.g. cost_price).
5. **PUT** `batches/{{batch_id}}/quantity/` – reduce quantity on this batch once.
6. **GET** `batches/product/{{product_id}}/` – list batches for that product.
7. **GET** `batches/product/{{product_id}}/summary/` – product + batch summary.
8. **GET** `batches/statistics/` – check totals.
9. **GET** `batches/expiring/` and **GET** `batches/expiry-summary/` – if you set expiry dates.
10. **POST** `batches/mark-expired/` – run once to mark any already-expired batches.

For product-level stock movements (add/remove/set/restock), use the **Product** stock endpoints (see `PRODUCT_API_SAMPLES.md`).

Use this file in Postman (e.g. as a collection description or separate requests) and with curl to verify that the batch API behaves as expected.

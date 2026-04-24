# Product API Sample Requests (Postman / curl)

Base URL for all product endpoints: **`/api/v1/admin/`**

Replace `{{baseURL}}` with your server (e.g. `http://localhost:8000`).

**Authentication:** All product endpoints require a valid JWT. Send the token in the header:
- **Header:** `Authorization: Bearer <access_token>`
- **Get token:** `POST {{baseURL}}/api/v1/admin/auth/login/` with body `{"email": "...", "password": "..."}`. Use the `access_token` from the response.

Without a valid token, requests return `401 Unauthorized` with `{"error": "Authentication required"}`.

---

## Seeded test data (shipments + batches)

These are **actual IDs and values** created by `python manage.py seed_shipments_and_batches --yes-i-am-sure` in your DynamoDB table (`RamyeonCornerDB`, region `ap-southeast-1`).

### Products used (same 5 products in every shipment)

Use these product IDs when testing product + inventory endpoints:

```
PROD-00014
PROD-00015
PROD-00016
PROD-00017
PROD-00018
```

### Products that currently have stock (from batch `quantity_remaining`)

These product IDs **definitely have stock** right now based on DynamoDB batch totals (sum of `quantity_remaining` across all 50 seeded batches):

```
PROD-00014  total_remaining=725
PROD-00015  total_remaining=745
PROD-00016  total_remaining=765
PROD-00017  total_remaining=785
PROD-00018  total_remaining=805
```

### Shipments created (10)

```
SHIP-00002  supplier=SUPP-007  batch_number=LOT-20260306-001  shipment_date=2026-03-06T06:58:01.393943+0000
SHIP-00003  supplier=SUPP-008  batch_number=LOT-20260306-002  shipment_date=2026-03-05T06:58:01.393943+0000
SHIP-00004  supplier=SUPP-009  batch_number=LOT-20260306-003  shipment_date=2026-03-04T06:58:01.393943+0000
SHIP-00005  supplier=SUPP-011  batch_number=LOT-20260306-004  shipment_date=2026-03-03T06:58:01.393943+0000
SHIP-00006  supplier=SUPP-014  batch_number=LOT-20260306-005  shipment_date=2026-03-02T06:58:01.393943+0000
SHIP-00007  supplier=SUPP-015  batch_number=LOT-20260306-006  shipment_date=2026-03-01T06:58:01.393943+0000
SHIP-00008  supplier=SUPP-016  batch_number=LOT-20260306-007  shipment_date=2026-02-28T06:58:01.393943+0000
SHIP-00009  supplier=SUPP-007  batch_number=LOT-20260306-008  shipment_date=2026-02-27T06:58:01.393943+0000
SHIP-00010  supplier=SUPP-008  batch_number=LOT-20260306-009  shipment_date=2026-02-26T06:58:01.393943+0000
SHIP-00011  supplier=SUPP-009  batch_number=LOT-20260306-010  shipment_date=2026-02-25T06:58:01.393943+0000
```

### Batches created (50)

Each shipment has **5 batches** (one per product). Here’s **Shipment 1** (`SHIP-00002`) fully expanded so you can copy exact batch IDs:

```
SHIP-00002
  BATCH-00014-00002  product=PROD-00014  qty=50  cost=41     expiry=2026-06-04T06:58:01.393943+0000  batch_number=LOT-20260306-001-01
  BATCH-00015-00001  product=PROD-00015  qty=52  cost=41     expiry=2026-06-09T06:58:01.393943+0000  batch_number=LOT-20260306-001-02
  BATCH-00016-00001  product=PROD-00016  qty=54  cost=38.75  expiry=2026-06-14T06:58:01.393943+0000  batch_number=LOT-20260306-001-03
  BATCH-00017-00001  product=PROD-00017  qty=56  cost=75.5   expiry=2026-06-19T06:58:01.393943+0000  batch_number=LOT-20260306-001-04
  BATCH-00018-00001  product=PROD-00018  qty=58  cost=50     expiry=2026-06-24T06:58:01.393943+0000  batch_number=LOT-20260306-001-05
```

Quick sanity checks to run after seeding:

```
GET {{baseURL}}/api/v1/admin/products/PROD-00014/
GET {{baseURL}}/api/v1/admin/products/PROD-00015/
GET {{baseURL}}/api/v1/admin/products/PROD-00016/
GET {{baseURL}}/api/v1/admin/products/PROD-00017/
GET {{baseURL}}/api/v1/admin/products/PROD-00018/
```

---

## 1. Test endpoint

### GET – Health check for product API

**URL:** `{{baseURL}}/api/v1/admin/products/test/`

**Example:**

```
GET {{baseURL}}/api/v1/admin/products/test/
```

**Response:** `{"message": "TEST ENDPOINT WORKS!"}`

---

## 2. List products

### GET – List all products (paginated, 50 per page by default)

**URL:** `{{baseURL}}/api/v1/admin/products/`

**Query parameters:**

| Parameter         | Type   | Description                                              |
|-------------------|--------|----------------------------------------------------------|
| `page_size`       | int    | Items per page (default `50`, max `100`)                 |
| `page_token`      | string | Token for next page (from previous response)             |
| `search`          | string | Partial, case-insensitive search by product name        |
| `category_id`     | string | Filter by category ID                                    |
| `status`          | string | Filter by status: `active`, `inactive`, `low_stock`, etc. |
| `subcategory_name`| string | Filter by subcategory (applied in addition to category)  |
| `offset`          | int    | When using filters, offset for next page (e.g. 50, 100)  |

**Pagination (no filters):** Use `page_size` and `page_token`. First request omits `page_token`; subsequent pages use `next_page_token` from the previous response. Only 50 items are loaded per request.

**Examples:**

```
GET {{baseURL}}/api/v1/admin/products/
GET {{baseURL}}/api/v1/admin/products/?page_size=50
GET {{baseURL}}/api/v1/admin/products/?page_size=50&page_token=<token from previous response>
GET {{baseURL}}/api/v1/admin/products/?search=rice
GET {{baseURL}}/api/v1/admin/products/?category_id=CAT-001
GET {{baseURL}}/api/v1/admin/products/?status=active
GET {{baseURL}}/api/v1/admin/products/?category_id=CAT-001&subcategory_name=Grains
```

**Response (paginated):** `{"message": "Found N products", "data": [ {...}, ... ], "page_size": 50, "next_page_token": "..." }` — omit `next_page_token` when there are no more pages. Each item is a product object (see Product detail response shape).

### Search by name

Use the same list endpoint with the `search` query parameter for **partial, case-insensitive search by product name**. Results are paginated.

**Examples:**

```
GET {{baseURL}}/api/v1/admin/products/?search=rice
GET {{baseURL}}/api/v1/admin/products/?search=organic&page_size=20
GET {{baseURL}}/api/v1/admin/products/?search=milk&page_token=<next_page_token>
```

**Response:** Same as list products — `{"message": "Found N products", "data": [...], "page_size": ..., "next_page_token": "..." }`.

---

## 3. Create product

### POST – Create a new product

**URL:** `{{baseURL}}/api/v1/admin/products/`

**Request body (required + optional):**

| Field               | Type    | Required | Description                          |
|---------------------|--------|----------|--------------------------------------|
| `product_name`      | string | Yes      | Product name                         |
| `sku`               | string | Yes      | Unique SKU                           |
| `category_id`       | string | Yes      | Category ID                          |
| `cost_price`        | number | Yes      | Cost price                           |
| `selling_price`     | number | Yes      | Selling price                        |
| `unit`              | string | Yes      | Unit (e.g. `piece`, `kg`, `liter`)   |
| `date_received`     | string | No       | ISO date (defaults to now)           |
| `subcategory_name`  | string | No       | Subcategory (default `General`)      |
| `low_stock_threshold`| number | No       | Low stock threshold                  |
| `barcode`           | string | No       | Barcode                              |
| `description`       | string | No       | Description                          |
| `is_taxable`        | boolean| No       | Default `true`                       |
| `status`            | string | No       | Default `active`                     |

**Example (minimal):**

```json
{
  "product_name": "Organic Rice 1kg",
  "sku": "RICE-001",
  "category_id": "CAT-001",
  "cost_price": 2.50,
  "selling_price": 3.99,
  "unit": "piece"
}
```

**Example (full):**

```json
{
  "product_name": "Organic Rice 1kg",
  "sku": "RICE-001",
  "category_id": "CAT-001",
  "cost_price": 2.50,
  "selling_price": 3.99,
  "unit": "piece",
  "subcategory_name": "Grains",
  "low_stock_threshold": 10,
  "barcode": "1234567890123",
  "description": "Premium organic rice",
  "is_taxable": true,
  "status": "active"
}
```

**Response:** `201 Created` — `{"message": "Product created successfully", "data": {...}}`

---

## 4. Product detail

### GET – Get product by ID

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/`

**Path:** Replace `{{product_id}}` with product ID (e.g. `PROD-00001` or `00001`).

**Query parameters:**

| Parameter        | Type   | Description                              |
|------------------|--------|------------------------------------------|
| `include_deleted`| string | `true` to include soft-deleted product   |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/products/PROD-00001/
GET {{baseURL}}/api/v1/admin/products/00001/
GET {{baseURL}}/api/v1/admin/products/PROD-00001/?include_deleted=true
```

**Response:** `{"data": {...}}` — full product object (product_id, product_name, sku, barcode, category_id, subcategory_name, unit, cost_price, selling_price, total_stock, status, stock_status, margin_percentage, markup_percentage, sync_logs_count, last_sync, etc.).

### PUT – Update product (full update)

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/`

**Request body:** Any product fields to update (all optional). Examples: `product_name`, `sku`, `category_id`, `subcategory_name`, `cost_price`, `selling_price`, `unit`, `low_stock_threshold`, `barcode`, `description`, `status`, `is_taxable`.

**Example:**

```json
{
  "product_name": "Organic Rice 1kg (Updated)",
  "selling_price": 4.25,
  "low_stock_threshold": 15
}
```

**Response:** `200 OK` — `{"message": "Product updated successfully", "data": {...}}`

### PATCH – Partial update product

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/`

**Request body:** Same as PUT; only send fields you want to change.

**Example:**

```json
{
  "selling_price": 4.50
}
```

**Response:** `200 OK` — `{"message": "Product updated successfully", "data": {...}}`

### DELETE – Delete product

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/`

**Query parameters:**

| Parameter   | Type   | Description                                    |
|-------------|--------|------------------------------------------------|
| `hard_delete` | string | `true` to permanently delete; default soft-delete |

**Examples:**

```
DELETE {{baseURL}}/api/v1/admin/products/PROD-00001/
DELETE {{baseURL}}/api/v1/admin/products/PROD-00001/?hard_delete=true
```

**Response:** `200 OK` — `{"message": "Product moved to trash successfully"}` or `{"message": "Product permanently deleted successfully"}`

---

## 5. Restore product

### POST – Restore a soft-deleted product

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/restore/`

**Example:**

```
POST {{baseURL}}/api/v1/admin/products/PROD-00001/restore/
```

**Response:** `200 OK` — `{"message": "Product restored successfully"}`

---

## 6. Get product by SKU

### GET – Get product by SKU

**URL:** `{{baseURL}}/api/v1/admin/products/by-sku/{{sku}}/`

**Path:** Replace `{{sku}}` with the product SKU.

**Query parameters:**

| Parameter        | Type   | Description                            |
|------------------|--------|----------------------------------------|
| `include_deleted`| string | `true` to include soft-deleted product |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/products/by-sku/RICE-001/
GET {{baseURL}}/api/v1/admin/products/by-sku/RICE-001/?include_deleted=true
```

**Response:** `{"data": {...}}` — full product object.

---

## 6b. Get product by barcode

### GET – Get product by barcode

**URL:** `{{baseURL}}/api/v1/admin/products/by-barcode/{{barcode}}/`

**Path:** Replace `{{barcode}}` with the product barcode (e.g. EAN-13, UPC).

**Query parameters:**

| Parameter        | Type   | Description                            |
|------------------|--------|----------------------------------------|
| `include_deleted`| string | `true` to include soft-deleted product |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/products/by-barcode/1234567890123/
GET {{baseURL}}/api/v1/admin/products/by-barcode/5901234123457/?include_deleted=true
```

**Response:** `{"data": {...}}` — full product object. `404` if no product has that barcode.

---

## 7. Stock management

All stock changes are **batch-aware**: product `total_stock` is derived from non-expired batches. Adding stock creates a batch; removing stock deducts from batches (FEFO); setting stock reconciles with existing batches.

### How stock works (FAQ)

1. **When manually adding stock, does it create a new batch? A new shipment?**  
   **Yes, it creates a new batch.** Every "add" creates a batch so expiry, cost, and supplier are tracked. **No shipment is created** unless you pass `shipment_id` to link the batch to an existing shipment. Use the shipments API to create shipments; use stock "add" or restock for receiving into batches.

2. **What about expiry, cost, and other attributes when adding?**  
   You can (and should) pass optional fields so the new batch is correct:
   - `cost_price` – default: product’s `cost_price`
   - `expiry_date` – ISO date/datetime (e.g. `2026-12-31` or `2026-12-31T23:59:59`); default: 365 days from now
   - `supplier_id` – default: `"MANUAL"`
   - `batch_number` – default: `MANUAL-YYYY-MM-DD-HHMM` or similar
   - `shipment_id` – optional; link to an existing shipment

3. **When subtracting stock, does it follow FIFO or nearest expiry?**  
   **FEFO (first-expired-first-out):** deduction is taken from the batch with the **nearest expiry** first, then the next, and so on. So we use the batch that expires soonest first, not strictly “oldest received.”

4. **How does "set" work with existing batches?**  
   **"Set" reconciles with batches**, it does not overwrite blindly:
   - Current stock = sum of `quantity_remaining` of all non-expired, non-exhausted batches.
   - If target **equals** current → no change.
   - If target **>** current → an **adjustment batch** is created for `(target - current)` (optional `cost_price`, `expiry_date`, `supplier_id`, `batch_number` apply).
   - If target **<** current → **FEFO deduction** of `(current - target)` from batches.  
   So you can safely "set" after a stock count; existing batches stay the source of truth and we only add or deduct as needed.

---

### PUT – Update product stock (add / remove / set)

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/stock/`

**Request body:**

| Field            | Type   | Required | Description                                                                 |
|------------------|--------|----------|-----------------------------------------------------------------------------|
| `quantity`       | number | Yes      | Quantity to add, remove, or set (see operation_type)                        |
| `operation_type` | string | No       | `add` \| `remove` \| `set` (default `set`)                                |
| `reason`         | string | No       | Reason for adjustment (default "Manual adjustment")                        |
| `cost_price`     | number | No       | For **add** / **set** (when adding): cost per unit; default: product cost   |
| `expiry_date`    | string | No       | For **add** / **set** (when adding): ISO date/datetime; default: +365 days  |
| `supplier_id`    | string | No       | For **add** / **set** (when adding): default `"MANUAL"`                     |
| `batch_number`   | string | No       | For **add** / **set** (when adding): optional batch ref                     |
| `shipment_id`    | string | No       | For **add** only: link new batch to existing shipment (e.g. `SHIP-00001`)   |

**Example (add 50 units with expiry and cost):**

```json
{
  "operation_type": "add",
  "quantity": 50,
  "reason": "Received delivery",
  "cost_price": 12.50,
  "expiry_date": "2026-06-30",
  "supplier_id": "SUPP-001"
}
```

**Example (set stock to 100 – reconciles with batches):**

```json
{
  "operation_type": "set",
  "quantity": 100,
  "reason": "Stock count correction"
}
```

**Example (remove 10 units – FEFO deduction):**

```json
{
  "operation_type": "remove",
  "quantity": 10,
  "reason": "Damaged goods"
}
```

**Response (add):** `200 OK` — `{"message": "Stock added via new batch", "batch": {...}, "data": {...}}` (created batch + updated product).

**Response (remove):** `200 OK` — `{"message": "Stock removed from batches (FEFO)", "deductions": [...], "data": {...}}` (list of batches deducted + updated product).

**Response (set):** `200 OK` — `{"message": "..." , "data": {...}}` (description of add/deduct applied + updated product).

### PATCH – Same as PUT for stock update

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/stock/`

Use the same body as PUT above.

---

## 8. Stock adjustment for sale

### POST – Deduct stock (e.g. after a sale)

Deduction is taken from batches using **FEFO** (first-expired-first-out). Product `total_stock` is updated from batches after the deduction.

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/stock/adjust/`

**Request body:**

| Field           | Type   | Required | Description        |
|-----------------|--------|----------|--------------------|
| `quantity_sold` | number | Yes      | Units to deduct    |

**Example:**

```json
{
  "quantity_sold": 5
}
```

**Response:** `200 OK` — `{"message": "Stock adjusted for sale (FEFO deduction)", "deductions": [...], "data": {...}}` (batches used + updated product).

---

## 9. Restock product

### POST – Restock product (creates a batch)

Creates a **new batch** and syncs product `total_stock`. Use this for receiving from a supplier (with optional `supplier_info` and `batch_info`).

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/stock/restock/`

**Request body:**

| Field               | Type   | Required | Description                                                                 |
|---------------------|--------|----------|-----------------------------------------------------------------------------|
| `quantity_received` | number | Yes      | Quantity received                                                          |
| `supplier_info`     | object | No       | e.g. `{"supplier_id": "SUPP-001"}`; used for the new batch                 |
| `batch_info`        | object | No       | `batch_number`, `cost_price`, `expiry_date` (ISO), `date_received` (ISO)   |

**Example:**

```json
{
  "quantity_received": 100,
  "supplier_info": { "supplier_id": "SUPP-001" },
  "batch_info": {
    "batch_number": "LOT-2025-001",
    "cost_price": 8.50,
    "expiry_date": "2026-12-31"
  }
}
```

**Response:** `200 OK` — `{"message": "Product restocked (batch created)", "batch": {...}, "data": {...}}` (created batch + updated product).

---

## 10. Bulk stock update

### POST – Update stock for multiple products (by SKU)

**URL:** `{{baseURL}}/api/v1/admin/products/stock/bulk-update/`

**Request body:**

| Field     | Type  | Required | Description                                                                 |
|-----------|-------|----------|-----------------------------------------------------------------------------|
| `updates` | array | Yes      | List of objects: `sku`, `quantity_change` (required); `source`, `reason` (optional) |

**Example:**

```json
{
  "updates": [
    { "sku": "RICE-001", "quantity_change": 20, "source": "manual", "reason": "Stock count" },
    { "sku": "BEAN-002", "quantity_change": -5, "reason": "Damaged" }
  ]
}
```

**Response:** `200 OK` — `{"message": "Bulk stock update completed", "results": {"updated": [...], "total_updated": N, "errors": [...], "success": true}}`

---

## 11. Stock history

### GET – Get stock change history for a product

**URL:** `{{baseURL}}/api/v1/admin/products/{{product_id}}/stock/history/`

**Example:**

```
GET {{baseURL}}/api/v1/admin/products/PROD-00014/stock/history/
```

**Response:** `200 OK` — `{"product_id": "...", "product_name": "...", "current_stock": N, "stock_history": [{"timestamp": "...", "old_stock": "...", "new_stock": "...", "source": "...", "status": "..."}, ...]}`

---

## 12. Reports – Low stock

### GET – Get products with low stock

**URL:** `{{baseURL}}/api/v1/admin/products/low-stock/`

**Example:**

```
GET {{baseURL}}/api/v1/admin/products/low-stock/
```

**Response:** `{"message": "Found N products with low stock", "data": [ {...}, ... ]}`

---

## 13. Reports – Expiring products

### GET – Get products with batches expiring within N days

**URL:** `{{baseURL}}/api/v1/admin/products/expiring/`

**Query parameters:**

| Parameter    | Type   | Description                    |
|--------------|--------|--------------------------------|
| `days_ahead` | number | Days ahead (default 30)        |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/products/expiring/
GET {{baseURL}}/api/v1/admin/products/expiring/?days_ahead=14
```

**Response:** `{"message": "Found N products expiring within X days", "data": [ {...}, ... ]}`

---

## 14. Reports – Products by category

### GET – Get products by category

**URL:** `{{baseURL}}/api/v1/admin/products/category/{{category_id}}/`

**Query parameters:**

| Parameter          | Type   | Description              |
|--------------------|--------|--------------------------|
| `subcategory_name` | string | Filter by subcategory   |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/products/category/CAT-001/
GET {{baseURL}}/api/v1/admin/products/category/CAT-001/?subcategory_name=Grains
```

**Response:** `{"message": "Found N products in category ...", "data": [ {...}, ... ]}`

---

## 15. Reports – Deleted products

### GET – Get all soft-deleted products

**URL:** `{{baseURL}}/api/v1/admin/products/deleted/`

**Example:**

```
GET {{baseURL}}/api/v1/admin/products/deleted/
```

**Response:** `{"message": "Found N deleted products", "data": [ {...}, ... ]}`

---

## 16. Product sync (POS / cloud)

### POST – Sync products (direction: to_cloud / to_local)

**URL:** `{{baseURL}}/api/v1/admin/products/sync/`

**Request body:**

| Field     | Type   | Required | Description                                    |
|-----------|--------|----------|------------------------------------------------|
| `direction` | string | No     | `to_cloud` (default) or `to_local`             |
| `products` | array  | If to_cloud | List of product payloads to push to cloud  |

**Example (to_cloud):**

```json
{
  "direction": "to_cloud",
  "products": [
    { "product_id": "PROD-00014", "product_name": "Example Seeded Product", "sku": "SEEDED-SKU-00014", "..." }
  ]
}
```

**Example (to_local):**

```json
{
  "direction": "to_local"
}
```

**Response:** `200 OK` — `{"message": "Sync to_cloud completed", "results": {...}}`

**Note:** Implementation may depend on backend sync service availability.

---

## 17. Bulk create products

### POST – Create multiple products in batch

**URL:** `{{baseURL}}/api/v1/admin/products/bulk-create/`

**Request body:** Either a JSON array of product objects, or an object with a `products` array. Each product must include required create fields: `product_name`, `sku`, `category_id`, `cost_price`, `selling_price`, `unit`.

**Example (array):**

```json
[
  {
    "product_name": "Product A",
    "sku": "SKU-A",
    "category_id": "CAT-001",
    "cost_price": 1.00,
    "selling_price": 1.50,
    "unit": "piece"
  },
  {
    "product_name": "Product B",
    "sku": "SKU-B",
    "category_id": "CAT-001",
    "cost_price": 2.00,
    "selling_price": 3.00,
    "unit": "piece"
  }
]
```

**Example (object with products key):**

```json
{
  "products": [
    {
      "product_name": "Product A",
      "sku": "SKU-A",
      "category_id": "CAT-001",
      "cost_price": 1.00,
      "selling_price": 1.50,
      "unit": "piece"
    }
  ]
}
```

**Response:** `200 OK` — `{"message": "Bulk product creation completed", "results": {...}}`

**Note:** Backend must implement `ProductService.bulk_create_products` for this to work.

---

## 18. Bulk delete products

### POST – Delete multiple products

**URL:** `{{baseURL}}/api/v1/admin/products/bulk-delete/`

**Request body:**

| Field         | Type   | Required | Description                          |
|---------------|--------|----------|--------------------------------------|
| `product_ids` | array  | Yes      | List of product IDs to delete        |
| `hard_delete` | boolean| No       | If true, permanently delete (default false) |

**Example:**

```json
{
  "product_ids": ["PROD-00001", "PROD-00002", "00003"],
  "hard_delete": false
}
```

**Response:** `200 OK` — `{"message": "N products deleted successfully", "details": {...}}`

**Note:** Backend must implement `ProductService.bulk_delete_products` for this to work.

---

## 19. Import products from file

### POST – Import products from CSV/Excel

**URL:** `{{baseURL}}/api/v1/admin/products/import/`

**Request:** `multipart/form-data` with a file field named `file` (e.g. `.csv` or `.xlsx`). Optional form field: `validate_only` = `true` to validate without importing.

**Example (curl):**

```bash
curl -X POST "{{baseURL}}/api/v1/admin/products/import/" \
  -F "file=@products.csv" \
  -F "validate_only=false"
```

**Response:** `200 OK` — `{"message": "Import completed successfully", "results": {...}}`

**Note:** Backend must implement `ProductService.import_products_from_file` for this to work.

---

## 20. Export products

### GET – Export products to CSV or Excel

**URL:** `{{baseURL}}/api/v1/admin/products/export/`

**Query parameters:**

| Parameter          | Type   | Description                              |
|--------------------|--------|------------------------------------------|
| `format`           | string | `csv` (default) or `xlsx`                |
| `category_id`      | string | Filter by category                       |
| `subcategory_name` | string | Filter by subcategory                    |
| `status`           | string | Filter by status                         |
| `stock_level`      | string | Filter by stock level                    |
| `search`           | string | Search term                              |
| `include_deleted`  | string | Include deleted products                 |
| `uncategorized_only` | string | `true` to export only uncategorized   |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/products/export/?format=csv
GET {{baseURL}}/api/v1/admin/products/export/?format=xlsx&category_id=CAT-001
GET {{baseURL}}/api/v1/admin/products/export/?format=csv&uncategorized_only=true
```

**Response:** File download (CSV or XLSX). Headers include `Content-Disposition: attachment; filename="products_export.csv"` (or `.xlsx`).

---

## 21. Import template

### GET – Download product import template (CSV or Excel)

**URL:** `{{baseURL}}/api/v1/admin/products/import/template/`

**Query parameters:**

| Parameter | Type   | Description              |
|-----------|--------|--------------------------|
| `format`  | string | `csv` (default) or `xlsx` |

**Examples:**

```
GET {{baseURL}}/api/v1/admin/products/import/template/?format=csv
GET {{baseURL}}/api/v1/admin/products/import/template/?format=xlsx
```

**Response:** File download (template CSV or XLSX).

**Note:** Backend must implement `ProductService.generate_import_template` for this to work.

---

## 22. Export product details (single product CSV)

### GET – Export a single product’s details as CSV

**URL:** `{{baseURL}}/api/v1/admin/products/export/details/`

The view expects a `product_id`; the route is currently defined without a path parameter, so the backend may need to accept `product_id` as a query parameter or the URL may be extended to `products/export/details/{{product_id}}/`. Use the form that matches your backend.

**Example (if product_id is added to path):**

```
GET {{baseURL}}/api/v1/admin/products/export/details/PROD-00001/
```

**Example (if product_id is query param):**

```
GET {{baseURL}}/api/v1/admin/products/export/details/?product_id=PROD-00001
```

**Response:** CSV file download with product details.

**Note:** Backend must implement `ProductService.export_product_details_csv` for this to work.

---

## Quick reference (copy into Postman)

| Method | Endpoint | Purpose |
|--------|----------|--------|
| GET    | `/api/v1/admin/products/test/` | Test endpoint |
| GET    | `/api/v1/admin/products/` | List products (optional filters) |
| GET    | `/api/v1/admin/products/?search={{term}}` | Search by product name |
| GET    | `/api/v1/admin/products/by-barcode/{{barcode}}/` | Get by barcode |
| POST   | `/api/v1/admin/products/` | Create product |
| GET    | `/api/v1/admin/products/{{product_id}}/` | Product detail |
| PUT    | `/api/v1/admin/products/{{product_id}}/` | Update product |
| PATCH  | `/api/v1/admin/products/{{product_id}}/` | Partial update |
| DELETE | `/api/v1/admin/products/{{product_id}}/` | Delete (soft/hard) |
| POST   | `/api/v1/admin/products/{{product_id}}/restore/` | Restore product |
| GET    | `/api/v1/admin/products/by-sku/{{sku}}/` | Get by SKU |
| PUT    | `/api/v1/admin/products/{{product_id}}/stock/` | Update stock (add/remove/set) |
| PATCH  | `/api/v1/admin/products/{{product_id}}/stock/` | Same as PUT stock |
| POST   | `/api/v1/admin/products/{{product_id}}/stock/adjust/` | Adjust for sale |
| POST   | `/api/v1/admin/products/{{product_id}}/stock/restock/` | Restock |
| GET    | `/api/v1/admin/products/{{product_id}}/stock/history/` | Stock history |
| POST   | `/api/v1/admin/products/stock/bulk-update/` | Bulk stock update |
| GET    | `/api/v1/admin/products/low-stock/` | Low stock report |
| GET    | `/api/v1/admin/products/expiring/` | Expiring products |
| GET    | `/api/v1/admin/products/category/{{category_id}}/` | By category |
| GET    | `/api/v1/admin/products/deleted/` | Deleted products |
| POST   | `/api/v1/admin/products/sync/` | Sync (to_cloud / to_local) |
| POST   | `/api/v1/admin/products/bulk-create/` | Bulk create |
| POST   | `/api/v1/admin/products/bulk-delete/` | Bulk delete |
| POST   | `/api/v1/admin/products/import/` | Import from file |
| GET    | `/api/v1/admin/products/export/` | Export CSV/Excel |
| GET    | `/api/v1/admin/products/import/template/` | Download import template |
| GET    | `/api/v1/admin/products/export/details/` | Export single product CSV |

---

## Suggested test order

1. **GET** `products/test/` – confirm API is up.
2. **GET** `products/` – list all products.
3. **POST** `products/` – create one product (use unique SKU).
4. **GET** `products/{{product_id}}/` – get the created product.
5. **GET** `products/by-sku/{{sku}}/` – get by SKU.
6. **GET** `products/by-barcode/{{barcode}}/` – get by barcode.
7. **GET** `products/?search=rice` – search by name.
8. **PUT** `products/{{product_id}}/` – update product.
9. **PUT** `products/{{product_id}}/stock/` – update stock (e.g. add 50).
10. **GET** `products/{{product_id}}/stock/history/` – check history.
11. **GET** `products/low-stock/` and **GET** `products/expiring/` – reports.
12. **POST** `products/{{product_id}}/stock/adjust/` – deduct for sale.
13. **POST** `products/stock/bulk-update/` – bulk stock update by SKU.
14. **DELETE** `products/{{product_id}}/` – soft-delete (no query param).
15. **GET** `products/deleted/` – list deleted.
16. **POST** `products/{{product_id}}/restore/` – restore.
17. **GET** `products/export/?format=csv` – export CSV.

Use this file in Postman (e.g. as a collection description or separate requests) and with curl to verify that the product API behaves as expected.

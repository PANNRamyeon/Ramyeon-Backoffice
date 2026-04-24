# Category API Sample Requests

Base URL: `/api/v1/admin/categories/`

## 1. List/Create Categories

### GET - Get All Categories
**URL:** `/api/v1/admin/categories/`

**Query Parameters:**
- `search` - Search term
- `active_only` - true/false
- `include_deleted` - true/false
- `include_product_counts` - true/false
- `limit` - Number (default: 100)
- `skip` - Number (default: 0)

**Examples:**
```
GET /api/v1/admin/categories/
GET /api/v1/admin/categories/?search=Electronics
GET /api/v1/admin/categories/?active_only=true
GET /api/v1/admin/categories/?include_product_counts=true
```

### POST - Create Category
**URL:** `/api/v1/admin/categories/`

**Request Body (simple subcategories):**
```json
{
  "category_name": "Electronics",
  "description": "Electronic devices and accessories",
  "status": "active",
  "sub_categories": ["Phones", "Laptops", "Tablets"]
}
```

**Request Body (detailed subcategories):**
```json
{
  "category_name": "Electronics",
  "description": "Electronic devices and accessories",
  "status": "active",
  "sub_categories": [
    {"name": "Phones", "description": "Mobile phones"},
    {"name": "Laptops", "description": "Portable computers", "icon": "https://example.com/laptop.jpg"},
    {"name": "Tablets"}
  ]
}
```

**Minimal Request:**
```json
{
  "category_name": "Electronics"
}
```

---

## 2. Category Detail

### GET - Get Category by ID
**URL:** `/api/v1/admin/categories/{category_id}/`

**Query Parameters:**
- `include_deleted` - true/false
- `include_product_counts` - true/false (default: true)

**Example:**
```
GET /api/v1/admin/categories/507f1f77bcf86cd799439011/
GET /api/v1/admin/categories/507f1f77bcf86cd799439011/?include_product_counts=true
```

### PUT - Update Category
**URL:** `/api/v1/admin/categories/{category_id}/`

**Request Body (all fields optional):**
```json
{
  "category_name": "Updated Electronics",
  "description": "Updated description",
  "status": "inactive",
  "sub_categories": ["Phones", "Laptops", "Tablets", "Accessories"],
  "image_url": "https://example.com/new-image.jpg"
}
```

---

## 3. Soft Delete Category

### DELETE - Soft Delete
**URL:** `/api/v1/admin/categories/{category_id}/soft-delete/`

**Example:**
```
DELETE /api/v1/admin/categories/507f1f77bcf86cd799439011/soft-delete/
```

---

## 4. Restore Category (Admin Only)

### POST - Restore Soft-Deleted Category
**URL:** `/api/v1/admin/categories/{category_id}/restore/`

**Note:** Only restores soft-deleted categories. Cannot restore hard-deleted categories.

**Example:**
```
POST /api/v1/admin/categories/507f1f77bcf86cd799439011/restore/
```

---

## 5. Deleted Categories List (Admin Only)

### GET - Get Deleted Categories
**URL:** `/api/v1/admin/categories/deleted/`

**Query Parameters:**
- `include_product_counts` - true/false

**Example:**
```
GET /api/v1/admin/categories/deleted/
GET /api/v1/admin/categories/deleted/?include_product_counts=true
```

---

## 6. Hard Delete Category (Admin Only)

### DELETE - Permanently Delete
**URL:** `/api/v1/admin/categories/{category_id}/hard-delete/`

**Warning:** This is PERMANENT and cannot be undone. The category cannot be restored.

**Example:**
```
DELETE /api/v1/admin/categories/507f1f77bcf86cd799439011/hard-delete/
```

---

## 7. Bulk Operations

### POST - Bulk Operations
**URL:** `/api/v1/admin/categories/bulk/`

**Soft Delete Multiple:**
```json
{
  "operation": "soft_delete",
  "category_ids": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"]
}
```

**Update Status Multiple:**
```json
{
  "operation": "update_status",
  "category_ids": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"],
  "new_status": "inactive"
}
```

---

## 8. Category Delete Info

### GET - Get Delete Impact Info
**URL:** `/api/v1/admin/categories/{category_id}/delete-info/`

**Example:**
```
GET /api/v1/admin/categories/507f1f77bcf86cd799439011/delete-info/
```

---

## 9. Subcategory Management

### GET - Get Subcategories
**URL:** `/api/v1/admin/categories/{category_id}/subcategories/`

**Example:**
```
GET /api/v1/admin/categories/507f1f77bcf86cd799439011/subcategories/
```

### POST - Add Subcategory
**URL:** `/api/v1/admin/categories/{category_id}/subcategories/`

**Request Body:**
```json
{
  "subcategory": {
    "name": "Smartwatches",
    "description": "Smart wearable devices",
    "icon": "https://example.com/smartwatch.jpg",
    "status": "active",
    "sort_order": 0
  }
}
```

**Minimal Request:**
```json
{
  "subcategory": {
    "name": "Smartwatches"
  }
}
```

### DELETE - Remove Subcategory
**URL:** `/api/v1/admin/categories/{category_id}/subcategories/`

**Request Body:**
```json
{
  "subcategory_name": "Smartwatches"
}
```

---

## 10. Uncategorized Category

### GET - Get Uncategorized Category Info
**URL:** `/api/v1/admin/categories/uncategorized/`

**Example:**
```
GET /api/v1/admin/categories/uncategorized/
```

### POST - Create/Ensure Uncategorized Exists (Admin Only)
**URL:** `/api/v1/admin/categories/uncategorized/`

**Example:**
```
POST /api/v1/admin/categories/uncategorized/
```

---

## 11. Subcategory Products

### GET - Get Products in Subcategory
**URL:** `/api/v1/admin/categories/subcategories/{subcategory_name}/products/`

**Note:** This endpoint appears incomplete in the URLs file. Check implementation.

---

## 12. Product Management within Categories

### PUT - Move Single Product
**URL:** `/api/v1/admin/categories/{category_id}/products/`

**Request Body:**
```json
{
  "product_id": "507f1f77bcf86cd799439013",
  "new_category_id": "507f1f77bcf86cd799439011",
  "new_subcategory_name": "Laptops"
}
```

### POST - Bulk Move Products
**URL:** `/api/v1/admin/categories/{category_id}/products/`

**Request Body:**
```json
{
  "product_ids": ["507f1f77bcf86cd799439013", "507f1f77bcf86cd799439014"],
  "new_category_id": "507f1f77bcf86cd799439011",
  "new_subcategory_name": "Laptops"
}
```

---

## Authentication

All endpoints require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

Admin-only endpoints:
- Hard Delete
- Restore
- Deleted Categories List
- Create Uncategorized Category

---

## Common Response Format

**Success Response:**
```json
{
  "message": "Operation completed successfully",
  "category": { ... },
  "count": 1
}
```

**Error Response:**
```json
{
  "error": "Error message description"
}
```

---

## Notes

**Category Fields:**
- `category_name` - Required (2-100 characters)
- `description` - Optional
- `status` - Optional (default: "active", values: "active" or "inactive")
- `sub_categories` - Optional array (accepts both string array `["Name"]` or object array `[{"name": "Name"}]`)
- `image_url` - Optional (maps to `icon` field in database, null=True)
- `sort_order` - Optional (default: 0)

**Subcategory Fields:**
- `name` - Required
- `description` - Optional
- `icon` - Optional (null=True)
- `status` - Optional (default: "active")
- `sort_order` - Optional (default: 0)

**Image Handling:**
- `image_url` can be blank/null without errors
- No image metadata fields (filename, size, type) are stored
- Images are optional for both categories and subcategories

---

## Troubleshooting

**Issue: Category created with `UNKNOWN-00001` SK format**

This happens when the DynamoDB counter isn't initialized. 

**Solution:**
1. Hard delete the incorrectly created category
2. Run the counter initialization script:
```bash
cd backend
python init_counters.py
```
3. Verify counters are initialized (should see "✅ Counter set to start from: X")
4. Try creating the category again - SK should now be `CAT-0001` format

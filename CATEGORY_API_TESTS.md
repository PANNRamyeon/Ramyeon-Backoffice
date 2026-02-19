# Category API Test Requests

## Base URL
```
http://localhost:8000/api/v1
```

---

## ⚡ Performance Optimization

**Product Counts are Optional!**

By default, list endpoints do NOT include product counts for performance:
- **Fast (default)**: `GET /category/` - Returns categories with `product_count: null`
- **With counts**: `GET /category/?include_product_counts=true` - Calculates actual counts (slower)

**Response Times:**
- Without counts: ~0.5s ⚡
- With counts: ~9-10s 🐌

**When to use `include_product_counts=true`:**
- When you need exact product counts for dashboard/reports
- When viewing a single category detail (already default for detail views)
- Not recommended for list/search operations

---

## 1. Core Category Operations

### GET - List All Categories
```
GET /category/
```

**Query Parameters (optional):**
- `search` - Search term
- `active_only` - true/false
- `include_deleted` - true/false
- `include_product_counts` - true/false (default: false for performance)
- `limit` - 100
- `skip` - 0

**Examples:**
```
GET /category/
GET /category/?search=drinks&limit=10
GET /category/?include_product_counts=true
```

**Performance Note:**
- Without `include_product_counts`: ~0.5s response time
- With `include_product_counts=true`: ~9-10s response time (counts all products in all subcategories)

---

### POST - Create Category
```
POST /category/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "category_name": "Beverages",
  "description": "Hot and cold drinks",
  "status": "active",
  "image_url": "https://example.com/beverages.jpg",
  "sub_categories": [
    {
      "name": "Hot Drinks",
      "description": "Coffee, Tea, etc.",
      "status": "active"
    },
    {
      "name": "Cold Drinks",
      "description": "Sodas, Juices, etc.",
      "status": "active"
    }
  ]
}
```

---

### GET - Category Statistics
```
GET /category/stats/
```

---

### GET - Category Display Data
```
GET /category/display/
```

---

### GET - Export Categories
```
GET /category/export/
```

---

### POST - Bulk Operations
```
POST /category/bulk/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "operation": "soft_delete",
  "category_ids": ["CAT-0001", "CAT-0002"]
}
```

**For status update:**
```json
{
  "operation": "update_status",
  "category_ids": ["CAT-0001", "CAT-0002"],
  "new_status": "inactive"
}
```

---

## 2. Individual Category Operations

### GET - Get Category by ID
```
GET /category/CAT-0001/
```

**Query Parameters (optional):**
- `include_deleted` - true/false
- `include_product_counts` - true/false (default: true for detail views)

**Note:** Product counts are enabled by default for detail views since you're viewing a single category.

---

### PUT - Update Category
```
PUT /category/CAT-0001/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "category_name": "Beverages Updated",
  "description": "Updated description",
  "status": "active",
  "image_url": "https://example.com/new-image.jpg"
}
```

---

### GET - Category Delete Info
```
GET /category/CAT-0001/delete-info/
```

---

### DELETE - Soft Delete Category
```
DELETE /category/CAT-0001/soft-delete/
Authorization: Bearer YOUR_TOKEN
```

---

### DELETE - Hard Delete Category (Admin Only)
```
DELETE /category/CAT-0001/hard-delete/
Authorization: Bearer YOUR_ADMIN_TOKEN
```

---

### POST - Restore Category (Admin Only)
```
POST /category/CAT-0001/restore/
Authorization: Bearer YOUR_ADMIN_TOKEN
```

---

## 3. Subcategory Management

### GET - List Subcategories
```
GET /category/CAT-0001/subcategories/
```

---

### POST - Add Subcategory
```
POST /category/CAT-0001/subcategories/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "subcategory": {
    "name": "Energy Drinks",
    "description": "High caffeine beverages",
    "status": "active",
    "icon": "https://example.com/energy.jpg"
  }
}
```

---

### DELETE - Remove Subcategory
```
DELETE /category/CAT-0001/subcategories/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "subcategory_name": "Energy Drinks"
}
```

---

### GET - Products in Subcategory
```
GET /category/CAT-0001/subcategories/Hot Drinks/products/
```

---

## 4. Admin-Only Operations

### GET - List Deleted Categories (Admin Only)
```
GET /category/deleted/
Authorization: Bearer YOUR_ADMIN_TOKEN
```

**Query Parameters (optional):**
- `include_product_counts` - true/false (default: false for performance)

---

### GET - Uncategorized Category Info
```
GET /category/uncategorized/
```

---

### POST - Ensure Uncategorized Exists (Admin Only)
```
POST /category/uncategorized/
Authorization: Bearer YOUR_ADMIN_TOKEN
```

---

## 5. Product Management

### PUT - Move Single Product to Category
```
PUT /category/product-management/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "product_id": "PROD-00001",
  "new_category_id": "CAT-0002",
  "new_subcategory_name": "Hot Drinks"
}
```

---

### POST - Bulk Move Products
```
POST /category/product-management/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "product_ids": ["PROD-00001", "PROD-00002", "PROD-00003"],
  "new_category_id": "CAT-0002",
  "new_subcategory_name": "Cold Drinks"
}
```

---

## 6. Testing Scenarios

### Test 1: Create Category with Null Image
```
POST /category/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "category_name": "Test Category",
  "description": "Testing null image",
  "image_url": null,
  "status": "active"
}
```

---

### Test 2: Create Category with Empty Image
```
POST /category/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "category_name": "Test Category 2",
  "description": "Testing empty image",
  "image_url": "",
  "status": "active"
}
```

---

### Test 3: Search Categories
```
GET /category/?search=drinks
```

---

### Test 4: Get Active Categories Only
```
GET /category/?active_only=true
```

---

### Test 5: Pagination
```
GET /category/?limit=5&skip=0
```

---

## Quick Test Sequence

**Step 1: Create a category**
```
POST /category/
Body: {"category_name": "Snacks", "description": "Quick bites"}
```

**Step 2: Get the category ID from response (e.g., CAT-0005)**

**Step 3: Add subcategory**
```
POST /category/CAT-0005/subcategories/
Body: {"subcategory": {"name": "Chips", "description": "Potato chips"}}
```

**Step 4: Update category**
```
PUT /category/CAT-0005/
Body: {"description": "Updated snacks description"}
```

**Step 5: Get category details**
```
GET /category/CAT-0005/
```

**Step 6: Soft delete**
```
DELETE /category/CAT-0005/soft-delete/
```

**Step 7: Restore (admin)**
```
POST /category/CAT-0005/restore/
```

---

## Expected Response Formats

### Success Response (List Categories)
```json
{
  "message": "Categories retrieved successfully",
  "categories": [
    {
      "category_id": "CAT-0001",
      "category_name": "Drinks",
      "description": "Beverages",
      "status": "active",
      "isDeleted": false,
      "icon": null,
      "sort_order": 0,
      "date_created": "2025-10-08T11:27:37.690",
      "last_updated": "2025-10-08T11:27:37.690",
      "sub_categories": [
        {
          "subcategory_id": "SUB-00001",
          "name": "Hot Drinks",
          "description": "Coffee, Tea",
          "icon": null,
          "sort_order": 0,
          "status": "active",
          "created_at": "2025-10-08T11:27:37.690",
          "product_count": 5
        }
      ]
    }
  ],
  "count": 5
}
```

### Error Response
```json
{
  "error": "Category not found"
}
```

---

## Notes

- Replace `YOUR_TOKEN` with actual authentication token
- Replace `YOUR_ADMIN_TOKEN` with admin authentication token
- Category IDs follow format: `CAT-####` (4 digits)
- Product IDs follow format: `PROD-#####` (5 digits)
- Subcategory names can contain spaces
- All timestamps are in ISO format

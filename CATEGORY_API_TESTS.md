# Category API Test Requests

## Base URL (UPDATED!)
```
http://localhost:8000/api/v1/admin
```

**⚠️ IMPORTANT: URL Structure Changed!**
- **Old:** `http://localhost:8000/api/v1/category/`
- **New:** `http://localhost:8000/api/v1/admin/categories/`

All category endpoints now use the `/admin/` prefix since they are administrative operations.

---

## ⚡ Performance Optimization

**Product Counts are Optional!**

By default, list endpoints do NOT include product counts for performance:
- **Fast (default)**: `GET /api/v1/admin/categories/` - Returns categories with `product_count: null`
- **With counts**: `GET /api/v1/admin/categories/?include_product_counts=true` - Calculates actual counts (slower)

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
GET /api/v1/admin/categories/
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
GET /api/v1/admin/categories/
GET /api/v1/admin/categories/?search=drinks&limit=10
GET /api/v1/admin/categories/?include_product_counts=true
```

**Performance Note:**
- Without `include_product_counts`: ~0.5s response time
- With `include_product_counts=true`: ~9-10s response time (counts all products in all subcategories)

---

### POST - Create Category
```
POST /api/v1/admin/categories/
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
GET /api/v1/admin/categories/stats/
```

---

### GET - Category Display Data
```
GET /api/v1/admin/categories/display/
```

---

### GET - Export Categories
```
GET /api/v1/admin/categories/export/
```

---

### POST - Bulk Operations
```
POST /api/v1/admin/categories/bulk/
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
GET /api/v1/admin/categories/CAT-0001/
```

**Query Parameters (optional):**
- `include_deleted` - true/false
- `include_product_counts` - true/false (default: true for detail views)

**Note:** Product counts are enabled by default for detail views since you're viewing a single category.

---

### PUT - Update Category
```
PUT /api/v1/admin/categories/CAT-0001/
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
GET /api/v1/admin/categories/CAT-0001/delete-info/
```

---

### DELETE - Soft Delete Category
```
DELETE /api/v1/admin/categories/CAT-0001/soft-delete/
Authorization: Bearer YOUR_TOKEN
```

---

### DELETE - Hard Delete Category (Admin Only)
```
DELETE /api/v1/admin/categories/CAT-0001/hard-delete/
Authorization: Bearer YOUR_ADMIN_TOKEN
```

---

### POST - Restore Category (Admin Only)
```
POST /api/v1/admin/categories/CAT-0001/restore/
Authorization: Bearer YOUR_ADMIN_TOKEN
```

---

## 3. Subcategory Management

### GET - List Subcategories
```
GET /api/v1/admin/categories/CAT-0001/subcategories/
```

---

### POST - Add Subcategory
```
POST /api/v1/admin/categories/CAT-0001/subcategories/
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
DELETE /api/v1/admin/categories/CAT-0001/subcategories/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "subcategory_name": "Energy Drinks"
}
```

---

### GET - Products in Subcategory
```
GET /api/v1/admin/categories/subcategories/Hot Drinks/products/
```

---

## 4. Admin-Only Operations

### GET - List Deleted Categories (Admin Only)
```
GET /api/v1/admin/categories/deleted/
Authorization: Bearer YOUR_ADMIN_TOKEN
```

**Query Parameters (optional):**
- `include_product_counts` - true/false (default: false for performance)

---

### GET - Uncategorized Category Info
```
GET /api/v1/admin/categories/uncategorized/
```

---

### POST - Ensure Uncategorized Exists (Admin Only)
```
POST /api/v1/admin/categories/uncategorized/
Authorization: Bearer YOUR_ADMIN_TOKEN
```

---

## 5. Product Management

### PUT - Move Single Product to Category
```
PUT /api/v1/admin/categories/CAT-0001/products/
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
POST /api/v1/admin/categories/CAT-0001/products/
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
POST /api/v1/admin/categories/
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
POST /api/v1/admin/categories/
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
GET /api/v1/admin/categories/?search=drinks
```

---

### Test 4: Get Active Categories Only
```
GET /api/v1/admin/categories/?active_only=true
```

---

### Test 5: Pagination
```
GET /api/v1/admin/categories/?limit=5&skip=0
```

---

## Quick Test Sequence

**Step 1: Create a category**
```
POST /api/v1/admin/categories/
Body: {"category_name": "Snacks", "description": "Quick bites"}
```

**Step 2: Get the category ID from response (e.g., CAT-0005)**

**Step 3: Add subcategory**
```
POST /api/v1/admin/categories/CAT-0005/subcategories/
Body: {"subcategory": {"name": "Chips", "description": "Potato chips"}}
```

**Step 4: Update category**
```
PUT /api/v1/admin/categories/CAT-0005/
Body: {"description": "Updated snacks description"}
```

**Step 5: Get category details**
```
GET /api/v1/admin/categories/CAT-0005/
```

**Step 6: Soft delete**
```
DELETE /api/v1/admin/categories/CAT-0005/soft-delete/
```

**Step 7: Restore (admin)**
```
POST /api/v1/admin/categories/CAT-0005/restore/
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

---

## 🚀 Quick Postman Setup

### Environment Variables (Recommended)
Set these in Postman environment:
```
BASE_URL = http://localhost:8000
AUTH_TOKEN = your_jwt_token_here
ADMIN_TOKEN = your_admin_token_here
```

Then use in requests:
```
{{BASE_URL}}/api/v1/admin/categories/
Authorization: Bearer {{AUTH_TOKEN}}
```

### Testing Checklist
- [ ] List all categories
- [ ] Create new category
- [ ] Get category by ID
- [ ] Update category
- [ ] Add subcategory
- [ ] List subcategories
- [ ] Search categories
- [ ] Soft delete category
- [ ] List deleted categories (admin)
- [ ] Restore category (admin)
- [ ] Hard delete category (admin)

---

## 🔍 Quick Verification

**Test the new URL structure works:**

1. **Old URL (should fail):**
   ```
   GET http://localhost:8000/api/v1/category/
   ```
   Expected: 404 Not Found

2. **New URL (should work):**
   ```
   GET http://localhost:8000/api/v1/admin/categories/
   ```
   Expected: 200 OK with categories list

If both responses match expectations, your migration is successful! ✅

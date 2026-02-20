# Category API Tests - URL Update Summary

## What Changed

The `CATEGORY_API_TESTS.md` file has been updated to reflect the new URL structure after the API reorganization.

---

## URL Changes

### Base URL
| Before | After |
|--------|-------|
| `http://localhost:8000/api/v1` | `http://localhost:8000/api/v1/admin` |

### All Endpoints Updated

Every category endpoint now includes the `/admin/` prefix:

| Old URL | New URL |
|---------|---------|
| `GET /api/v1/category/` | `GET /api/v1/admin/categories/` |
| `POST /api/v1/category/` | `POST /api/v1/admin/categories/` |
| `GET /api/v1/category/CAT-0001/` | `GET /api/v1/admin/categories/CAT-0001/` |
| `PUT /api/v1/category/CAT-0001/` | `PUT /api/v1/admin/categories/CAT-0001/` |
| `DELETE /api/v1/category/CAT-0001/soft-delete/` | `DELETE /api/v1/admin/categories/CAT-0001/soft-delete/` |
| ... and all other endpoints | ... with `/admin/` prefix |

---

## Why This Change?

The API was reorganized for better structure:
- `/api/v1/admin/` → Back office/admin operations
- `/api/v1/pos/` → Point of sale operations
- `/api/v1/web/` → Customer-facing operations

Since category management is an administrative function, all category endpoints are now under `/api/v1/admin/`.

---

## Testing Your Postman Requests

### Quick Verification

**1. Test old URL fails:**
```
GET http://localhost:8000/api/v1/category/
```
Expected: **404 Not Found** ❌

**2. Test new URL works:**
```
GET http://localhost:8000/api/v1/admin/categories/
```
Expected: **200 OK** ✅

---

## Update Your Postman Collection

### Option 1: Global Replace (Recommended)
1. Open your Postman collection
2. Use Find & Replace (Ctrl+H or Cmd+H)
3. Find: `/api/v1/category/`
4. Replace with: `/api/v1/admin/categories/`
5. Replace All

### Option 2: Environment Variables (Best Practice)
Set up Postman environment variables:
```
BASE_URL = http://localhost:8000
AUTH_TOKEN = your_jwt_token
ADMIN_TOKEN = your_admin_token
```

Then update all requests to:
```
{{BASE_URL}}/api/v1/admin/categories/
Authorization: Bearer {{AUTH_TOKEN}}
```

---

## What Didn't Change

✅ **Request Bodies** - Same as before  
✅ **Query Parameters** - Same as before  
✅ **Response Format** - Same as before  
✅ **Authentication** - Same JWT tokens  
✅ **Business Logic** - Exact same functionality

Only the URL paths changed!

---

## Updated Endpoints List

### Core Operations
- `GET /api/v1/admin/categories/` - List all categories
- `POST /api/v1/admin/categories/` - Create category
- `GET /api/v1/admin/categories/stats/` - Statistics
- `GET /api/v1/admin/categories/display/` - Display data
- `GET /api/v1/admin/categories/export/` - Export
- `POST /api/v1/admin/categories/bulk/` - Bulk operations

### Individual Category
- `GET /api/v1/admin/categories/{id}/` - Get by ID
- `PUT /api/v1/admin/categories/{id}/` - Update
- `DELETE /api/v1/admin/categories/{id}/soft-delete/` - Soft delete
- `DELETE /api/v1/admin/categories/{id}/hard-delete/` - Hard delete
- `POST /api/v1/admin/categories/{id}/restore/` - Restore
- `GET /api/v1/admin/categories/{id}/delete-info/` - Delete info

### Subcategories
- `GET /api/v1/admin/categories/{id}/subcategories/` - List
- `POST /api/v1/admin/categories/{id}/subcategories/` - Add
- `DELETE /api/v1/admin/categories/{id}/subcategories/` - Remove
- `GET /api/v1/admin/categories/subcategories/{name}/products/` - Products in subcategory

### Admin Only
- `GET /api/v1/admin/categories/deleted/` - List deleted
- `GET /api/v1/admin/categories/uncategorized/` - Uncategorized info
- `POST /api/v1/admin/categories/uncategorized/` - Ensure exists

### Product Management
- `PUT /api/v1/admin/categories/{id}/products/` - Move single product
- `POST /api/v1/admin/categories/{id}/products/` - Bulk move products

---

## Testing Checklist

After updating your Postman requests, test these key scenarios:

- [ ] List all categories works
- [ ] Create new category works
- [ ] Get specific category works
- [ ] Update category works
- [ ] Add subcategory works
- [ ] Delete operations work
- [ ] Search/filter works
- [ ] Old URLs return 404

---

## Need Help?

If you encounter issues:
1. Check the base URL is correct: `http://localhost:8000/api/v1/admin`
2. Verify authentication token is valid
3. Ensure you're using `/categories/` (plural) not `/category/`
4. Check the server is running and the new URL routing is active

For full endpoint documentation, see: `CATEGORY_API_TESTS.md`

# Admin/Back Office API Endpoints

Base URL: `/api/v1/admin/`

Example: `https://api.myapp.com/api/v1/admin/`

---

## Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/auth/login/` | User login |
| POST | `/api/v1/admin/auth/logout/` | User logout |
| POST | `/api/v1/admin/auth/refresh/` | Refresh access token |
| GET | `/api/v1/admin/auth/me/` | Get current authenticated user |
| POST | `/api/v1/admin/auth/verify/` | Verify JWT token |
| POST | `/api/v1/admin/auth/password-reset/request/` | Request password reset |
| POST | `/api/v1/admin/auth/password-reset/reset/` | Reset password with token |
| POST | `/api/v1/admin/auth/password-reset/verify/` | Verify reset token |

---

## User Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/users/health/` | Health check for users API |
| GET | `/api/v1/admin/users/` | List all users (with pagination & filters) |
| POST | `/api/v1/admin/users/` | Create new user |
| GET | `/api/v1/admin/users/{user_id}/` | Get user details |
| PUT | `/api/v1/admin/users/{user_id}/` | Update user |
| DELETE | `/api/v1/admin/users/{user_id}/` | Soft delete user |
| POST | `/api/v1/admin/users/{user_id}/restore/` | Restore deleted user |
| DELETE | `/api/v1/admin/users/{user_id}/hard-delete/` | Permanently delete user |
| GET | `/api/v1/admin/users/deleted/list/` | List all deleted users |
| GET | `/api/v1/admin/users/search/by-email/` | Search user by email |
| GET | `/api/v1/admin/users/search/by-username/` | Search user by username |

---

## Customer Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/customers/` | List all customers |
| POST | `/api/v1/admin/customers/` | Create new customer |
| POST | `/api/v1/admin/customers/register/` | Customer registration |
| POST | `/api/v1/admin/customers/login/` | Customer login |
| GET | `/api/v1/admin/customers/me/` | Get current customer |
| GET | `/api/v1/admin/customers/statistics/` | Customer statistics |
| GET | `/api/v1/admin/customers/search/` | Search customers |
| GET | `/api/v1/admin/customers/by-email/` | Get customer by email |
| GET | `/api/v1/admin/customers/{customer_id}/` | Get customer details |
| PUT | `/api/v1/admin/customers/{customer_id}/` | Update customer |
| DELETE | `/api/v1/admin/customers/{customer_id}/` | Soft delete customer |
| POST | `/api/v1/admin/customers/{customer_id}/restore/` | Restore deleted customer |
| DELETE | `/api/v1/admin/customers/{customer_id}/hard-delete/` | Permanently delete customer |
| GET | `/api/v1/admin/customers/{customer_id}/loyalty/` | Get customer loyalty info |

---

## Product Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/products/test/` | Test endpoint |
| GET | `/api/v1/admin/products/` | List all products |
| POST | `/api/v1/admin/products/` | Create new product |
| GET | `/api/v1/admin/products/low-stock/` | List low stock products |
| GET | `/api/v1/admin/products/expiring/` | List expiring products |
| GET | `/api/v1/admin/products/deleted/` | List deleted products |
| POST | `/api/v1/admin/products/sync/` | Sync products |
| POST | `/api/v1/admin/products/bulk-create/` | Bulk create products |
| DELETE | `/api/v1/admin/products/bulk-delete/` | Bulk delete products |
| POST | `/api/v1/admin/products/import/` | Import products from CSV |
| GET | `/api/v1/admin/products/import/template/` | Download import template |
| GET | `/api/v1/admin/products/export/` | Export products to CSV |
| GET | `/api/v1/admin/products/export/details/` | Export product details |
| GET | `/api/v1/admin/products/by-sku/{sku}/` | Get product by SKU |
| GET | `/api/v1/admin/products/category/{category_id}/` | List products by category |
| GET | `/api/v1/admin/products/{product_id}/` | Get product details |
| PUT | `/api/v1/admin/products/{product_id}/` | Update product |
| DELETE | `/api/v1/admin/products/{product_id}/` | Soft delete product |
| POST | `/api/v1/admin/products/{product_id}/restore/` | Restore deleted product |
| PUT | `/api/v1/admin/products/{product_id}/stock/` | Update product stock |
| POST | `/api/v1/admin/products/{product_id}/stock/adjust/` | Adjust stock (with reason) |
| POST | `/api/v1/admin/products/{product_id}/stock/restock/` | Restock product |
| GET | `/api/v1/admin/products/{product_id}/stock/history/` | View stock history |
| POST | `/api/v1/admin/products/stock/bulk-update/` | Bulk update stock levels |

---

## Category Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/categories/` | List all categories |
| POST | `/api/v1/admin/categories/` | Create new category |
| GET | `/api/v1/admin/categories/deleted/` | List deleted categories |
| GET | `/api/v1/admin/categories/uncategorized/` | Get uncategorized category |
| POST | `/api/v1/admin/categories/bulk/` | Bulk operations on categories |
| GET | `/api/v1/admin/categories/{category_id}/` | Get category details |
| PUT | `/api/v1/admin/categories/{category_id}/` | Update category |
| DELETE | `/api/v1/admin/categories/{category_id}/soft-delete/` | Soft delete category |
| DELETE | `/api/v1/admin/categories/{category_id}/hard-delete/` | Permanently delete category |
| POST | `/api/v1/admin/categories/{category_id}/restore/` | Restore deleted category |
| GET | `/api/v1/admin/categories/{category_id}/delete-info/` | Get delete impact info |
| GET | `/api/v1/admin/categories/{category_id}/subcategories/` | List subcategories |
| POST | `/api/v1/admin/categories/{category_id}/subcategories/` | Create subcategory |
| GET | `/api/v1/admin/categories/{category_id}/products/` | List products in category |
| POST | `/api/v1/admin/categories/{category_id}/products/` | Add product to category |
| GET | `/api/v1/admin/categories/subcategories/{subcategory_name}/products/` | List products in subcategory |

---

## Supplier Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/suppliers/health/` | Health check for suppliers API |
| GET | `/api/v1/admin/suppliers/` | List all suppliers |
| POST | `/api/v1/admin/suppliers/` | Create new supplier |
| GET | `/api/v1/admin/suppliers/deleted/` | List deleted suppliers |
| GET | `/api/v1/admin/suppliers/statistics/` | Get supplier statistics |
| GET | `/api/v1/admin/suppliers/{supplier_id}/` | Get supplier details |
| PUT | `/api/v1/admin/suppliers/{supplier_id}/` | Update supplier |
| DELETE | `/api/v1/admin/suppliers/{supplier_id}/` | Soft delete supplier |
| POST | `/api/v1/admin/suppliers/{supplier_id}/restore/` | Restore deleted supplier |
| DELETE | `/api/v1/admin/suppliers/{supplier_id}/hard-delete/` | Permanently delete supplier |
| GET | `/api/v1/admin/suppliers/{supplier_id}/batches/` | List batches from supplier |
| POST | `/api/v1/admin/suppliers/{supplier_id}/batches/create/` | Create batch for supplier |
| GET | `/api/v1/admin/suppliers/legacy/purchase-orders/` | Legacy purchase orders redirect |

---

## Batch Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/batches/` | List all batches |
| POST | `/api/v1/admin/batches/create/` | Create new batch |
| GET | `/api/v1/admin/batches/expiring/` | List expiring batches |
| GET | `/api/v1/admin/batches/expiry-summary/` | Products with expiry summary |
| GET | `/api/v1/admin/batches/check-expiry/` | Check expiry alerts |
| POST | `/api/v1/admin/batches/mark-expired/` | Mark expired batches |
| GET | `/api/v1/admin/batches/statistics/` | Batch statistics |
| GET | `/api/v1/admin/batches/{batch_id}/` | Get batch details |
| PUT | `/api/v1/admin/batches/{batch_id}/` | Update batch |
| DELETE | `/api/v1/admin/batches/{batch_id}/` | Delete batch |
| PUT | `/api/v1/admin/batches/{batch_id}/quantity/` | Update batch quantity |
| POST | `/api/v1/admin/batches/{batch_id}/activate/` | Activate batch |
| GET | `/api/v1/admin/batches/product/{product_id}/` | List batches for product |
| GET | `/api/v1/admin/batches/product/{product_id}/summary/` | Product batch summary |
| GET | `/api/v1/admin/batches/supplier/{supplier_id}/` | List batches from supplier |
| POST | `/api/v1/admin/batches/process/sale/` | Process sale with FIFO |
| POST | `/api/v1/admin/batches/process/adjustment/` | Process batch adjustment |
| POST | `/api/v1/admin/batches/restock/` | Restock with batch |

---

## Promotion Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/promotions/health/` | Health check for promotions API |
| GET | `/api/v1/admin/promotions/` | List all promotions |
| POST | `/api/v1/admin/promotions/` | Create new promotion |
| GET | `/api/v1/admin/promotions/active/` | List active promotions |
| GET | `/api/v1/admin/promotions/deleted/` | List deleted promotions |
| GET | `/api/v1/admin/promotions/statistics/` | Promotion statistics |
| GET | `/api/v1/admin/promotions/audit/` | Promotion audit log |
| GET | `/api/v1/admin/promotions/search/` | Search promotions |
| GET | `/api/v1/admin/promotions/report/` | Promotion report |
| GET | `/api/v1/admin/promotions/by-name/` | Get promotion by name |
| GET | `/api/v1/admin/promotions/{promotion_id}/` | Get promotion details |
| PUT | `/api/v1/admin/promotions/{promotion_id}/` | Update promotion |
| DELETE | `/api/v1/admin/promotions/{promotion_id}/` | Soft delete promotion |
| POST | `/api/v1/admin/promotions/{promotion_id}/activate/` | Activate promotion |
| POST | `/api/v1/admin/promotions/{promotion_id}/deactivate/` | Deactivate promotion |
| POST | `/api/v1/admin/promotions/{promotion_id}/expire/` | Expire promotion |
| POST | `/api/v1/admin/promotions/{promotion_id}/apply/` | Apply promotion |
| POST | `/api/v1/admin/promotions/{promotion_id}/restore/` | Restore deleted promotion |
| DELETE | `/api/v1/admin/promotions/{promotion_id}/hard-delete/` | Permanently delete promotion |

---

## Session Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/sessions/` | List all session logs |
| GET | `/api/v1/admin/sessions/active/` | List active sessions |
| GET | `/api/v1/admin/sessions/statistics/` | Session statistics |
| POST | `/api/v1/admin/sessions/cleanup/` | Cleanup old sessions |
| GET | `/api/v1/admin/sessions/cleanup/status/` | Get cleanup status |
| POST | `/api/v1/admin/sessions/cleanup/auto-control/` | Control auto cleanup |
| GET | `/api/v1/admin/sessions/export/` | Export sessions to CSV |
| GET | `/api/v1/admin/sessions/display/` | Display session info |
| GET | `/api/v1/admin/sessions/combined-logs/` | Get combined logs |
| GET | `/api/v1/admin/sessions/system-status/` | Get system status |
| POST | `/api/v1/admin/sessions/bulk-control/` | Bulk session control |
| GET | `/api/v1/admin/sessions/{session_id}/` | Get session details |
| POST | `/api/v1/admin/sessions/{session_id}/force-logout/` | Force logout session |
| GET | `/api/v1/admin/sessions/user/{user_id}/` | List user's sessions |

---

## Sales Log Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/sales-logs/` | List all sales logs |
| POST | `/api/v1/admin/sales-logs/` | Create sales log |
| GET | `/api/v1/admin/sales-logs/statistics/` | Sales log statistics |

---

## Sales Reports Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/reports/sales-by-category/` | Sales grouped by category |
| GET | `/api/v1/admin/reports/top-categories/` | Top performing categories |
| GET | `/api/v1/admin/reports/category-performance/{category_id}/` | Detailed category performance |

---

## URL Summary

Total endpoints: **150+**

All endpoints follow the pattern:
```
https://api.myapp.com/api/v1/admin/{resource}/{action}
```

Example URLs:
- `https://api.myapp.com/api/v1/admin/auth/login/`
- `https://api.myapp.com/api/v1/admin/users/`
- `https://api.myapp.com/api/v1/admin/products/123/`
- `https://api.myapp.com/api/v1/admin/products/123/stock/`
- `https://api.myapp.com/api/v1/admin/reports/sales-by-category/`

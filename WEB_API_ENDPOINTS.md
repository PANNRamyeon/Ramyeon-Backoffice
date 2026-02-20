# Website/Customer-Facing API Endpoints

Base URL: `/api/v1/web/`

Example: `https://api.myapp.com/api/v1/web/`

---

## Customer Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/web/auth/login/` | Customer login |
| POST | `/api/v1/web/auth/register/` | Customer registration |
| POST | `/api/v1/web/auth/logout/` | Customer logout |
| GET | `/api/v1/web/auth/profile/` | Get customer profile |
| PUT/PATCH | `/api/v1/web/auth/profile/update/` | Update customer profile |
| POST | `/api/v1/web/auth/password/change/` | Change customer password |

---

## OAuth Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/web/oauth/authorize/` | OAuth authorization |
| GET | `/api/v1/web/oauth/callback/` | OAuth callback handler |

---

## Customer Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/web/products/` | List all products (customer view) |
| GET | `/api/v1/web/products/search/` | Search products |
| GET | `/api/v1/web/products/featured/` | Get featured products |
| GET | `/api/v1/web/products/{product_id}/` | Get product details |
| GET | `/api/v1/web/products/category/{category_id}/` | Get products by category |

---

## Customer Categories

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/web/categories/` | List all categories (customer view) |
| GET | `/api/v1/web/categories/{category_id}/` | Get category details |
| GET | `/api/v1/web/categories/{category_id}/products/` | Get category with products |

---

## Customer Promotions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/web/promotions/health/` | Promotions health check |
| GET | `/api/v1/web/promotions/` | List all promotions (customer view) |
| GET | `/api/v1/web/promotions/active/` | Get active promotions |
| GET | `/api/v1/web/promotions/search/` | Search promotions |
| GET | `/api/v1/web/promotions/{promotion_id}/` | Get promotion details |
| GET | `/api/v1/web/promotions/product/{product_id}/` | Get promotions for product |
| GET | `/api/v1/web/promotions/category/{category_id}/` | Get promotions for category |
| POST | `/api/v1/web/promotions/calculate/discount/` | Calculate promotion discount |

---

## Customer Loyalty Program

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/web/loyalty/health/` | Loyalty system health check |
| GET | `/api/v1/web/loyalty/balance/` | Get customer loyalty points balance |
| GET | `/api/v1/web/loyalty/history/` | Get loyalty points history |
| POST | `/api/v1/web/loyalty/validate-redemption/` | Validate points redemption |
| POST | `/api/v1/web/loyalty/redeem/` | Redeem loyalty points |
| POST | `/api/v1/web/loyalty/award/` | Award loyalty points |

---

## Customer POS Interactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/web/pos/qr/scan-user/` | Scan customer QR code |
| POST | `/api/v1/web/pos/qr/scan-promotion/` | Scan promotion QR code |
| GET | `/api/v1/web/pos/qr/user/{qr_code}/` | Get user by QR code |
| GET | `/api/v1/web/pos/qr/promotion/{qr_code}/` | Get promotion by QR code |
| POST | `/api/v1/web/pos/promotion/redeem/` | Redeem promotion at POS |
| POST | `/api/v1/web/pos/points/award/` | Award points manually at POS |
| POST | `/api/v1/web/pos/points/process-order/` | Process order points at POS |
| GET | `/api/v1/web/pos/dashboard/` | Get POS dashboard data |

---

## Category Data & Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/web/category-data/` | Get category data |
| GET | `/api/v1/web/category-data/export/` | Export category data |
| GET | `/api/v1/web/category-data/stats/` | Get category statistics |
| GET | `/api/v1/web/category-data/with-products/` | Get categories with products |
| GET | `/api/v1/web/category-data/product-counts/` | Get product counts by category |

---

## POS Catalog & Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/web/pos-catalog/` | Get POS catalog view |
| GET | `/api/v1/web/pos-catalog/product-batches/` | Get product batches for POS |
| GET | `/api/v1/web/pos-catalog/barcode/` | Search by barcode |
| GET | `/api/v1/web/pos-catalog/search/` | Search POS catalog |
| GET | `/api/v1/web/pos-catalog/subcategory/{subcategory_name}/products/` | Get products by subcategory |
| GET | `/api/v1/web/pos-catalog/stock/check/` | Check stock levels |
| GET | `/api/v1/web/pos-catalog/stock/low/` | Get low stock items |

---

## Customer Import/Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/web/customers/import-export/` | Import or export customer data |

---

## URL Summary

Total endpoints: **57**

All endpoints follow the pattern:
```
https://api.myapp.com/api/v1/web/{resource}/{action}
```

## Example URLs:

### Customer Operations
- `https://api.myapp.com/api/v1/web/auth/login/`
- `https://api.myapp.com/api/v1/web/auth/register/`
- `https://api.myapp.com/api/v1/web/auth/profile/`

### Product Browsing
- `https://api.myapp.com/api/v1/web/products/`
- `https://api.myapp.com/api/v1/web/products/search/`
- `https://api.myapp.com/api/v1/web/products/featured/`
- `https://api.myapp.com/api/v1/web/products/PROD123/`

### Categories & Navigation
- `https://api.myapp.com/api/v1/web/categories/`
- `https://api.myapp.com/api/v1/web/categories/CAT123/products/`

### Promotions & Deals
- `https://api.myapp.com/api/v1/web/promotions/active/`
- `https://api.myapp.com/api/v1/web/promotions/product/PROD123/`
- `https://api.myapp.com/api/v1/web/promotions/calculate/discount/`

### Loyalty Program
- `https://api.myapp.com/api/v1/web/loyalty/balance/`
- `https://api.myapp.com/api/v1/web/loyalty/history/`
- `https://api.myapp.com/api/v1/web/loyalty/redeem/`

### POS Integration
- `https://api.myapp.com/api/v1/web/pos/qr/scan-user/`
- `https://api.myapp.com/api/v1/web/pos/qr/user/QR123/`
- `https://api.myapp.com/api/v1/web/pos/dashboard/`

### Catalog & Stock
- `https://api.myapp.com/api/v1/web/pos-catalog/`
- `https://api.myapp.com/api/v1/web/pos-catalog/barcode/`
- `https://api.myapp.com/api/v1/web/pos-catalog/stock/check/`

---

## Common Query Parameters

### Products
- `search` - Search query string
- `category_id` - Filter by category
- `min_price` / `max_price` - Price range filter
- `in_stock` - Show only in-stock items (boolean)
- `page` - Page number for pagination
- `per_page` - Items per page

### Categories
- `include_products` - Include product list (boolean)
- `active_only` - Show only active categories (boolean)

### Promotions
- `active_only` - Show only active promotions (boolean)
- `product_id` - Filter by product
- `category_id` - Filter by category
- `promotion_type` - Type of promotion (percentage, fixed, bogo, etc.)

### Loyalty
- `start_date` / `end_date` - Date range for history
- `transaction_type` - Filter by earned/redeemed
- `points` - Points amount for validation

### POS Catalog
- `barcode` - Search by barcode
- `sku` - Search by SKU
- `subcategory` - Filter by subcategory
- `low_stock_only` - Show only low stock items (boolean)

---

## Authentication

Most endpoints require JWT authentication via the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

Public endpoints (no authentication required):
- Product listings and details
- Category listings
- Active promotions (read-only)
- OAuth endpoints

---

## Response Format

All endpoints return JSON responses in the following format:

### Success Response
```json
{
  "message": "Success message",
  "data": { ... },
  "status": 200
}
```

### Error Response
```json
{
  "error": "Error message",
  "status": 400
}
```

### Paginated Response
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  }
}
```

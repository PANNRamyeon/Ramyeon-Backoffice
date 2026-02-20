# POS (Point of Sale) API Endpoints

Base URL: `/api/v1/pos/`

Example: `https://api.myapp.com/api/v1/pos/`

---

## Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/pos/health/` | POS system health check |

---

## POS Transactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/pos/transactions/` | Get or create POS transactions |
| POST | `/api/v1/pos/transactions/checkout/` | Process checkout with promotions |
| GET | `/api/v1/pos/transactions/kpi/` | Get POS transaction KPIs |

---

## Stock & Inventory Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pos/stock/validate/` | Validate stock availability |
| GET | `/api/v1/pos/stock/warnings/` | Get stock warnings and alerts |
| GET | `/api/v1/pos/inventory/kpi/` | Get inventory KPIs |
| GET | `/api/v1/pos/inventory/alerts/` | Get stock alert KPIs |

---

## Sales Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/pos/sales/` | Sales service operations |

---

## Sales Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/pos/reports/summary/` | Get sales summary report |
| GET | `/api/v1/pos/reports/by-period/` | Get sales by time period |
| GET | `/api/v1/pos/reports/dashboard/` | Get dashboard summary |
| GET | `/api/v1/pos/reports/comparison/` | Compare sales across periods |
| GET | `/api/v1/pos/reports/transactions/` | Get detailed sales transactions |

---

## Online Orders - Creation & Retrieval

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pos/orders/online/create/` | Create new online order |
| GET | `/api/v1/pos/orders/online/{order_id}/` | Get specific online order |
| GET | `/api/v1/pos/orders/online/customer/{customer_id}/` | Get customer's orders |
| GET | `/api/v1/pos/orders/online/` | Get all online orders |
| GET | `/api/v1/pos/orders/online/pending/` | Get pending orders |
| GET | `/api/v1/pos/orders/online/processing/` | Get processing orders |
| GET | `/api/v1/pos/orders/online/status/{status}/` | Get orders by status |
| GET | `/api/v1/pos/orders/online/summary/` | Get order summary statistics |

---

## Order Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| PUT/PATCH | `/api/v1/pos/orders/{order_id}/status/` | Update order status |
| PUT/PATCH | `/api/v1/pos/orders/{order_id}/payment/` | Update payment status |
| POST | `/api/v1/pos/orders/{order_id}/ready/` | Mark order ready for delivery |
| POST | `/api/v1/pos/orders/{order_id}/complete/` | Complete order |
| POST | `/api/v1/pos/orders/{order_id}/cancel/` | Cancel order |

---

## Order Automation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pos/orders/auto-cancel/run/` | Run auto-cancel for expired orders |
| PUT/PATCH | `/api/v1/pos/orders/auto-cancel/settings/` | Update auto-cancel settings |
| GET | `/api/v1/pos/orders/auto-cancel/status/` | Get auto-cancel status |

---

## Order Validation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pos/orders/validate/stock/` | Validate stock for order |
| POST | `/api/v1/pos/orders/validate/points/` | Validate loyalty points redemption |

---

## Order Calculations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pos/orders/calculate/service-fee/` | Calculate service fee for order |
| POST | `/api/v1/pos/orders/calculate/loyalty-points/` | Calculate loyalty points earned |

---

## URL Summary

Total endpoints: **38**

All endpoints follow the pattern:
```
https://api.myapp.com/api/v1/pos/{resource}/{action}
```

## Example URLs:

### POS Operations
- `https://api.myapp.com/api/v1/pos/health/`
- `https://api.myapp.com/api/v1/pos/transactions/checkout/`
- `https://api.myapp.com/api/v1/pos/stock/validate/`

### Sales Reports
- `https://api.myapp.com/api/v1/pos/reports/summary/`
- `https://api.myapp.com/api/v1/pos/reports/dashboard/`
- `https://api.myapp.com/api/v1/pos/reports/comparison/`

### Online Orders
- `https://api.myapp.com/api/v1/pos/orders/online/create/`
- `https://api.myapp.com/api/v1/pos/orders/online/ORD123/`
- `https://api.myapp.com/api/v1/pos/orders/ORD123/status/`
- `https://api.myapp.com/api/v1/pos/orders/ORD123/complete/`

### Order Management
- `https://api.myapp.com/api/v1/pos/orders/online/pending/`
- `https://api.myapp.com/api/v1/pos/orders/auto-cancel/run/`
- `https://api.myapp.com/api/v1/pos/orders/validate/stock/`

---

## Common Query Parameters

### Sales Reports
- `start_date` - Start date for report (YYYY-MM-DD)
- `end_date` - End date for report (YYYY-MM-DD)
- `period` - Time period (daily, weekly, monthly, yearly)
- `branch_id` - Filter by branch

### Orders
- `status` - Filter by order status (pending, processing, ready, completed, cancelled)
- `customer_id` - Filter by customer
- `start_date` / `end_date` - Date range filter
- `page` - Page number for pagination
- `per_page` - Items per page

### Stock & Inventory
- `product_id` - Specific product
- `low_stock` - Filter low stock items (boolean)
- `category_id` - Filter by category

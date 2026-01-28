from rest_framework.views import APIView
from rest_framework.response import Response

# ================ API DOCUMENTATION VIEW ================
        
class APIDocumentationView(APIView):
    def get(self, request):
        """Complete API Documentation"""
        return Response({
            "title": "PANN User Management System API",
            "version": "1.0.0",
            "description": "Complete user management system with authentication, session logging, customer management, and comprehensive product management",
            "base_url": "http://localhost:8000/api/v1/",
            
            "authentication": {
                "type": "JWT Bearer Token",
                "header": "Authorization: Bearer <token>",
                "login_endpoint": "/auth/login/",
                "refresh_endpoint": "/auth/refresh/"
            },
            
            "endpoints": {
                "system": {
                    "GET /": "System status and statistics",
                    "GET /health/": "Health check",
                    "GET /docs/": "This documentation"
                },
                
                "authentication": {
                    "POST /auth/login/": "User login",
                    "POST /auth/logout/": "User logout (requires auth)",
                    "POST /auth/refresh/": "Refresh access token",
                    "GET /auth/me/": "Get current user (requires auth)",
                    "POST /auth/verify-token/": "Verify token validity"
                },
                
                "users": {
                    "GET /users/": "List all users (requires auth)",
                    "POST /users/": "Create new user",
                    "GET /users/{id}/": "Get specific user (requires auth)",
                    "PUT /users/{id}/": "Update user (requires auth)",
                    "DELETE /users/{id}/": "Delete user (requires auth)",
                    "GET /users/email/{email}/": "Get user by email",
                    "GET /users/username/{username}/": "Get user by username"
                },
                
                "customers": {
                    "GET /customers/": "List all customers",
                    "POST /customers/": "Create new customer",
                    "GET /customers/{id}/": "Get specific customer",
                    "PUT /customers/{id}/": "Update customer",
                    "DELETE /customers/{id}/": "Delete customer"
                },
                
                "products": {
                    "GET /products/": "List all products with filters",
                    "POST /products/": "Create new product",
                    "POST /products/create/": "Create product (dedicated endpoint)",
                    "GET /products/{id}/": "Get specific product",
                    "PUT /products/{id}/": "Update product",
                    "PUT /products/{id}/update/": "Update product (dedicated endpoint)",
                    "DELETE /products/{id}/": "Delete product (soft delete)",
                    "DELETE /products/{id}/delete/": "Delete product (dedicated endpoint)",
                    "POST /products/{id}/restore/": "Restore soft-deleted product",
                    "GET /products/sku/{sku}/": "Get product by SKU",
                    "GET /products/category/{category_id}/": "Get products by category",
                    "GET /products/deleted/": "Get soft-deleted products"
                },
                
                "stock_management": {
                    "PUT /products/{id}/stock/": "Update product stock",
                    "POST /products/{id}/stock/adjust/": "Adjust stock for sales",
                    "POST /products/{id}/restock/": "Restock from supplier",
                    "GET /products/{id}/stock/history/": "Get stock history",
                    "POST /products/stock/bulk-update/": "Bulk stock update"
                },
                
                "product_reports": {
                    "GET /products/reports/low-stock/": "Get low stock products",
                    "GET /products/reports/expiring/": "Get expiring products"
                },
                
                "product_sync": {
                    "POST /products/sync/": "Sync products local/cloud",
                    "GET /products/sync/unsynced/": "Get unsynced products",
                    "GET /products/{id}/sync/status/": "Get sync status",
                    "PUT /products/{id}/sync/status/": "Update sync status"
                },
                
                "product_import_export": {
                    "POST /products/import/": "Import from CSV/Excel",
                    "GET /products/export/": "Export to CSV/Excel",
                    "POST /products/bulk-create/": "Bulk create products",
                    "GET /products/import/template/": "Download import template"
                },
                
                "sessions": {
                    "GET /sessions/": "Session management info",
                    "GET /sessions/active/": "Get active sessions",
                    "GET /sessions/user/{user_id}/": "Get user sessions",
                    "GET /sessions/statistics/": "Session statistics",
                    "GET /session-logs/": "All session logs"
                }
            },
            
            "example_requests": {
                "login": {
                    "method": "POST",
                    "url": "/auth/login/",
                    "body": {
                        "email": "admin@pannpos.com",
                        "password": "admin123"
                    }
                },
                "create_product": {
                    "method": "POST",
                    "url": "/products/",
                    "body": {
                        "product_name": "Samyang Buldak Cheese Hot Chicken Flavor Ramen",
                        "category_id": "noodles",
                        "unit": "pack",
                        "stock": 50,
                        "expiry_date": "2025-12-31T00:00:00.000Z",
                        "low_stock_threshold": 10,
                        "cost_price": 45.50,
                        "selling_price": 65.00,
                        "status": "active",
                        "is_taxable": True,
                        "SKU": "SAM-BDK-CHZ-001"
                    }
                },
                "bulk_create_products": {
                    "method": "POST",
                    "url": "/products/bulk-create/",
                    "body": {
                        "products": [
                            {
                                "product_name": "Samyang Buldak Cheese Hot Chicken Flavor Ramen",
                                "category_id": "noodles",
                                "unit": "pack",
                                "stock": 50,
                                "low_stock_threshold": 10,
                                "cost_price": 45.50,
                                "selling_price": 65.00,
                                "status": "active",
                                "is_taxable": True,
                                "SKU": "SAM-BDK-CHZ-001"
                            }
                        ]
                    }
                },
                "update_stock": {
                    "method": "PUT",
                    "url": "/products/{id}/stock/",
                    "body": {
                        "operation_type": "add",
                        "quantity": 25,
                        "reason": "New shipment received"
                    }
                },
                "bulk_stock_update": {
                    "method": "POST",
                    "url": "/products/stock/bulk-update/",
                    "body": {
                        "updates": [
                            {
                                "product_id": "product_id_1",
                                "operation_type": "set",
                                "quantity": 100,
                                "reason": "Inventory count"
                            },
                            {
                                "product_id": "product_id_2",
                                "operation_type": "remove",
                                "quantity": 5,
                                "reason": "Damaged items"
                            }
                        ]
                    }
                }
            },
            
            "features": [
                "JWT Authentication with refresh tokens",
                "Role-based access control (admin/employee/customer)",
                "Comprehensive product management with inventory tracking",
                "Stock management with operation types (add/remove/set)",
                "Soft delete functionality for products",
                "Product synchronization between local and cloud",
                "Bulk operations for products and stock updates",
                "Import/Export functionality for products (CSV/Excel)",
                "Product reports (low stock, expiring products)",
                "Session logging and tracking",
                "Password hashing with bcrypt",
                "Input validation with serializers",
                "DynamoDB integration",
                "Real-time session statistics",
                "Token blacklisting on logout",
                "Comprehensive error handling",
                "Stock history tracking",
                "Category-based product filtering",
                "SKU-based product lookup",
                "Supplier integration for restocking"
            ]
        })
    



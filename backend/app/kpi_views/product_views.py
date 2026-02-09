from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from django.views import View  # ← ADD THIS LINE
from ..services.product_service import ProductService
import logging
import json  # ← ADD THIS LINE

logger = logging.getLogger(__name__)

# ================ PRODUCT VIEWS ================

class TestTemplateView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({"message": "TEST ENDPOINT WORKS!"}, status=200)

class ProductListView(APIView):
    def get(self, request):
        """Get all products with optional filters and pagination"""
        try:
            product_service = ProductService()
            
            # Get query parameters for filtering
            filters = {}
            if request.GET.get('category_id'):
                filters['category_id'] = request.GET.get('category_id')
            if request.GET.get('subcategory_name'):  # ADDED subcategory filtering
                filters['subcategory_name'] = request.GET.get('subcategory_name')
            if request.GET.get('status'):
                filters['status'] = request.GET.get('status')
            if request.GET.get('stock_level'):
                filters['stock_level'] = request.GET.get('stock_level')
            if request.GET.get('search'):
                filters['search'] = request.GET.get('search')
            
            include_deleted = request.GET.get('include_deleted', 'false').lower() == 'true'
            
            products = product_service.get_all_products(
                filters=filters if filters else None, 
                include_deleted=include_deleted,
                include_images=False  # Exclude images for faster loading in product list
            )
            
            return Response({
                'message': f'Found {len(products)} products',
                'data': products
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in ProductListView.get: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create a new product"""
        try:
            product_service = ProductService()
            
            # Convert to plain dict
            product_data = dict(request.data)
            
            new_product = product_service.create_product(product_data)
            return Response({
                'message': 'Product created successfully', 
                'data': new_product
            }, status=status.HTTP_201_CREATED)
        except ValueError as ve:
            return Response(
                {"error": str(ve)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in ProductListView.post: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProductDetailView(APIView):
    def get(self, request, product_id):
        """Get product by ID"""
        try:
            product_service = ProductService()
            include_deleted = request.GET.get('include_deleted', 'false').lower() == 'true'
            product = product_service.get_product_by_id(product_id, include_deleted)
            if not product:
                return Response(
                    {"error": "Product not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response({
                'data': product
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in ProductDetailView.get: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, product_id):
        """Update product - SIMPLIFIED (no complex category sync)"""
        try:
            product_service = ProductService()
            product_data = request.data
            
            updated_product = product_service.update_product(product_id, product_data)
            if not updated_product:
                return Response(
                    {"error": "Product not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response({
                'message': 'Product updated successfully', 
                'data': updated_product
            }, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response(
                {"error": str(ve)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in ProductDetailView.put: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, product_id):
        """Delete product (soft delete by default)"""
        try:
            product_service = ProductService()
            hard_delete = request.GET.get('hard_delete', 'false').lower() == 'true'
            deleted = product_service.delete_product(product_id, hard_delete)
            if not deleted:
                return Response(
                    {"error": "Product not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            delete_type = "permanently deleted" if hard_delete else "moved to trash"
            return Response(
                {"message": f"Product {delete_type} successfully"}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error in ProductDetailView.delete: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def patch(self, request, product_id):
        """Partial update product - SIMPLIFIED"""
        try:
            product_service = ProductService()
            product_data = request.data
            
            # Note: Removed partial_update parameter since the refactored service doesn't need it
            updated_product = product_service.update_product(product_id, product_data)
            if not updated_product:
                return Response(
                    {"error": "Product not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response({
                'message': 'Product updated successfully', 
                'data': updated_product
            }, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response(
                {"error": str(ve)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in ProductDetailView.patch: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProductRestoreView(APIView):
    def post(self, request, product_id):
        """Restore a soft-deleted product"""
        try:
            product_service = ProductService()
            restored = product_service.restore_product(product_id)
            if not restored:
                return Response(
                    {"error": "Product not found or not deleted"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(
                {"message": "Product restored successfully"}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error in ProductRestoreView.post: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProductBySkuView(APIView):
    def get(self, request, sku):
        """Get product by SKU"""
        try:
            product_service = ProductService()
            include_deleted = request.GET.get('include_deleted', 'false').lower() == 'true'
            product = product_service.get_product_by_sku(sku, include_deleted)
            if not product:
                return Response(
                    {"error": "Product not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response({
                'data': product
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in ProductBySkuView.get: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================ STOCK MANAGEMENT VIEWS ================

class ProductStockUpdateView(APIView):
    def put(self, request, product_id):
        """Update product stock with operation types"""
        try:
            product_service = ProductService()
            
            stock_data = {
                'operation_type': request.data.get('operation_type', 'set'),
                'quantity': request.data.get('quantity'),
                'reason': request.data.get('reason', 'Manual adjustment')
            }
            
            if stock_data['quantity'] is None:
                return Response(
                    {"error": "Quantity is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            valid_operations = ['add', 'remove', 'set']
            if stock_data['operation_type'] not in valid_operations:
                return Response(
                    {"error": f"Invalid operation_type. Must be one of: {valid_operations}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            updated_product = product_service.update_stock(product_id, stock_data)
            
            if not updated_product:
                return Response(
                    {"error": "Product not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            return Response({
                'message': 'Stock updated successfully', 
                'data': updated_product
            }, status=status.HTTP_200_OK)
            
        except ValueError as ve:
            return Response(
                {"error": str(ve)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in ProductStockUpdateView.put: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, product_id):
        """Alternative PATCH method for stock updates"""
        return self.put(request, product_id)

class StockAdjustmentView(APIView):
    def post(self, request, product_id):
        """Adjust stock for sales (remove stock)"""
        try:
            product_service = ProductService()
            quantity_sold = request.data.get('quantity_sold')
            
            if quantity_sold is None:
                return Response(
                    {"error": "quantity_sold is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            updated_product = product_service.adjust_stock_for_sale(product_id, quantity_sold)
            
            if not updated_product:
                return Response(
                    {"error": "Product not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            return Response({
                'message': 'Stock adjusted for sale successfully', 
                'data': updated_product
            }, status=status.HTTP_200_OK)
            
        except ValueError as ve:
            return Response(
                {"error": str(ve)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in StockAdjustmentView.post: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RestockProductView(APIView):
    def post(self, request, product_id):
        """Restock product from supplier"""
        try:
            product_service = ProductService()
            quantity_received = request.data.get('quantity_received')
            supplier_info = request.data.get('supplier_info')
            
            if quantity_received is None:
                return Response(
                    {"error": "quantity_received is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            updated_product = product_service.restock_product(product_id, quantity_received, supplier_info)
            
            if not updated_product:
                return Response(
                    {"error": "Product not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            return Response({
                'message': 'Product restocked successfully', 
                'data': updated_product
            }, status=status.HTTP_200_OK)
            
        except ValueError as ve:
            return Response(
                {"error": str(ve)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in RestockProductView.post: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BulkStockUpdateView(APIView):
    def post(self, request):
        """Handle bulk stock updates for multiple products"""
        try:
            stock_updates = request.data.get('updates', [])
            
            if not stock_updates:
                return Response(
                    {'error': 'No updates provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            product_service = ProductService()
            results = product_service.bulk_update_stock(stock_updates)
            
            return Response({
                'message': 'Bulk stock update completed',
                'results': results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in BulkStockUpdateView.post: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class StockHistoryView(APIView):
    def get(self, request, product_id):
        """Get stock change history for a specific product"""
        try:
            product_service = ProductService()
            
            product = product_service.get_product_by_id(product_id)
            
            if not product:
                return Response(
                    {'error': 'Product not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            stock_history = product.get('stock_history', [])
            
            # Sort by most recent first
            stock_history.sort(
                key=lambda x: x.get('timestamp', ''), 
                reverse=True
            )
            
            return Response({
                'product_id': product_id,
                'product_name': product.get('product_name'),
                'current_stock': product.get('stock'),
                'stock_history': stock_history
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in StockHistoryView.get: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================ PRODUCT REPORTS VIEWS ================

class LowStockProductsView(APIView):
    def get(self, request):
        """Get products with low stock"""
        try:
            product_service = ProductService()
            branch_id = request.GET.get('branch_id')
            products = product_service.get_low_stock_products(branch_id)
            return Response({
                'message': f'Found {len(products)} products with low stock',
                'data': products
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in LowStockProductsView.get: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ExpiringProductsView(APIView):
    def get(self, request):
        """Get products expiring within specified days"""
        try:
            product_service = ProductService()
            days_ahead = int(request.GET.get('days_ahead', 30))
            products = product_service.get_expiring_products(days_ahead)
            return Response({
                'message': f'Found {len(products)} products expiring within {days_ahead} days',
                'data': products
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in ExpiringProductsView.get: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProductsByCategoryView(APIView):
    def get(self, request, category_id):
        """Get products by category with optional subcategory filter"""
        try:
            product_service = ProductService()
            subcategory_name = request.GET.get('subcategory_name')  # ADDED subcategory filtering
            
            products = product_service.get_products_by_category(category_id, subcategory_name)
            
            message = f'Found {len(products)} products in category'
            if subcategory_name:
                message += f' > {subcategory_name}'
                
            return Response({
                'message': message,
                'data': products
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in ProductsByCategoryView.get: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeletedProductsView(APIView):
    def get(self, request):
        """Get all soft-deleted products"""
        try:
            product_service = ProductService()
            products = product_service.get_deleted_products()
            return Response({
                'message': f'Found {len(products)} deleted products',
                'data': products
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in DeletedProductsView.get: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================ PRODUCT SYNC VIEWS ================

class ProductSyncView(APIView):
    def post(self, request):
        """Sync products between local and cloud"""
        try:
            product_service = ProductService()
            sync_direction = request.data.get('direction', 'to_cloud')
            
            if sync_direction == 'to_cloud':
                local_products = request.data.get('products', [])
                results = product_service.sync_from_local(local_products)
            elif sync_direction == 'to_local':
                results = product_service.sync_to_local()
            else:
                return Response(
                    {"error": "Invalid sync direction. Use 'to_cloud' or 'to_local'"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'message': f'Sync {sync_direction} completed',
                'results': results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in ProductSyncView.post: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ================ PRODUCT IMPORT/EXPORT VIEWS ================

class BulkCreateProductsView(APIView):
    def post(self, request):
        """Create multiple products in batch"""
        try:
            product_service = ProductService()
            
            # Handle different payload structures
            products_data = None
            
            if isinstance(request.data, list):
                products_data = request.data
            elif isinstance(request.data, dict):
                if 'products' in request.data:
                    products_data = request.data.get('products', [])
                else:
                    # Check if it's a single product object
                    if any(key in request.data for key in ['product_name', 'SKU', 'cost_price']):
                        products_data = [request.data]
                    else:
                        products_data = request.data.get('products', [])
            
            # Validation
            if not products_data or not isinstance(products_data, list) or len(products_data) == 0:
                return Response(
                    {"error": "No valid products provided. Expected 'products' array in request body."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service method
            results = product_service.bulk_create_products(products_data)
            
            return Response({
                'message': 'Bulk product creation completed',
                'results': results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in BulkCreateProductsView.post: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProductImportView(APIView):
    def post(self, request):
        """Import products from CSV/Excel file"""
        try:
            product_service = ProductService()
            
            if 'file' not in request.FILES:
                return Response(
                    {"error": "No file provided"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            uploaded_file = request.FILES['file']
            file_type = uploaded_file.name.split('.')[-1].lower()
            validate_only = request.data.get('validate_only', 'false').lower() == 'true'
            
            # Save file temporarily
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            try:
                results = product_service.import_products_from_file(
                    temp_file_path, 
                    file_type, 
                    validate_only
                )
                
                return Response({
                    'message': 'Import completed successfully' if not validate_only else 'Validation completed',
                    'results': results
                }, status=status.HTTP_200_OK)
                
            finally:
                os.unlink(temp_file_path)
            
        except Exception as e:
            logger.error(f"Error in ProductImportView.post: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        
class ProductExportView(APIView):
    def get(self, request):
        """Export products to CSV/Excel (with uncategorized filter support)"""
        try:
            product_service = ProductService()
            file_type = request.GET.get('format', 'csv').lower()
            
            # ===============================
            # 🔹 Collect filters
            # ===============================
            filters = {}
            if request.GET.get('category_id'):
                filters['category_id'] = request.GET.get('category_id')
            if request.GET.get('subcategory_name'):
                filters['subcategory_name'] = request.GET.get('subcategory_name')
            if request.GET.get('status'):
                filters['status'] = request.GET.get('status')
            if request.GET.get('stock_level'):
                filters['stock_level'] = request.GET.get('stock_level')
            if request.GET.get('search'):
                filters['search'] = request.GET.get('search')
            if request.GET.get('include_deleted'):
                filters['include_deleted'] = request.GET.get('include_deleted')
            
            # ✅ NEW: support for uncategorized export
            uncategorized_only = request.GET.get('uncategorized_only', 'false').lower() == 'true'
            if uncategorized_only:
                filters['uncategorized_only'] = True

            print(f"🔍 Export filters: {filters}")
            print(f"🔍 Export format: {file_type}")
            
            # ===============================
            # 🔹 Get products with filters
            # ===============================
            products = product_service.get_all_products(
                filters=filters if filters else None, 
                include_deleted=filters.get('include_deleted', False),
                include_images=False  # Exclude images from export
            )
            
            # ✅ Filter uncategorized in Python (fallback if DB filtering not yet added)
            if uncategorized_only:
                products = [
                    p for p in products
                    if not p.get('category_id') or p.get('category_id') == 'UNCTGRY-001'
                ]

            print(f"🔍 Found {len(products)} products for export")
            
            # ===============================
            # 🔹 Handle Empty Export
            # ===============================
            if not products:
                content_type = (
                    "text/csv"
                    if file_type == "csv"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                filename = f"products_export.{file_type}"
                response = HttpResponse("", content_type=content_type)
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return response
            
            # ===============================
            # 🔹 Export to CSV
            # ===============================
            if file_type == "csv":
                import csv
                from io import StringIO
                
                output = StringIO()
                fieldnames = [
                    "ID", "Product Name", "SKU", "Barcode", "Category", "Subcategory",
                    "Price", "Cost Price", "Stock", "Total Stock", "Low Stock Threshold",
                    "Status", "Supplier", "Description", "Unit", "Created At", "Updated At",
                ]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()

                for product in products:
                    writer.writerow({
                        "ID": product.get("_id", ""),
                        "Product Name": product.get("product_name", ""),
                        "SKU": product.get("SKU", ""),
                        "Barcode": product.get("barcode", ""),
                        "Category": product.get("category_name", product.get("category_id", "")),
                        "Subcategory": product.get("subcategory_name", ""),
                        "Price": product.get("selling_price", product.get("price", "")),
                        "Cost Price": product.get("cost_price", ""),
                        "Stock": product.get("stock", ""),
                        "Total Stock": product.get("total_stock", product.get("stock", "")),
                        "Low Stock Threshold": product.get("low_stock_threshold", ""),
                        "Status": product.get("status", ""),
                        "Supplier": product.get("supplier", product.get("supplier_id", "")),
                        "Description": product.get("description", ""),
                        "Unit": product.get("unit", ""),
                        "Created At": product.get("created_at", ""),
                        "Updated At": product.get("updated_at", ""),
                    })

                response = HttpResponse(output.getvalue(), content_type="text/csv")
                response["Content-Disposition"] = 'attachment; filename="products_export.csv"'
                return response

            # ===============================
            # 🔹 Export to Excel
            # ===============================
            elif file_type == "xlsx":
                import pandas as pd
                from io import BytesIO

                df = pd.DataFrame([
                    {
                        "ID": p.get("_id", ""),
                        "Product Name": p.get("product_name", ""),
                        "SKU": p.get("SKU", ""),
                        "Barcode": p.get("barcode", ""),
                        "Category": p.get("category_name", p.get("category_id", "")),
                        "Subcategory": p.get("subcategory_name", ""),
                        "Price": p.get("selling_price", p.get("price", "")),
                        "Cost Price": p.get("cost_price", ""),
                        "Stock": p.get("stock", ""),
                        "Total Stock": p.get("total_stock", p.get("stock", "")),
                        "Low Stock Threshold": p.get("low_stock_threshold", ""),
                        "Status": p.get("status", ""),
                        "Supplier": p.get("supplier", p.get("supplier_id", "")),
                        "Description": p.get("description", ""),
                        "Unit": p.get("unit", ""),
                        "Created At": p.get("created_at", ""),
                        "Updated At": p.get("updated_at", ""),
                    }
                    for p in products
                ])

                output = BytesIO()
                df.to_excel(output, index=False, engine="openpyxl")
                output.seek(0)
                response = HttpResponse(
                    output.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                response["Content-Disposition"] = 'attachment; filename="products_export.xlsx"'
                return response

            # Default fallback
            return Response({"error": "Invalid format. Use 'csv' or 'xlsx'."},
                            status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in ProductExportView.get: {e}")
            import traceback
            traceback.print_exc()
            return Response({"error": f"Export failed: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """Export products to CSV/Excel - FIXED VERSION"""
        try:
            product_service = ProductService()
            file_type = request.GET.get('format', 'csv').lower()
            
            # Get ALL filters that your frontend might send
            filters = {}
            if request.GET.get('category_id'):
                filters['category_id'] = request.GET.get('category_id')
            if request.GET.get('subcategory_name'):
                filters['subcategory_name'] = request.GET.get('subcategory_name')
            if request.GET.get('status'):
                filters['status'] = request.GET.get('status')
            if request.GET.get('stock_level'):
                filters['stock_level'] = request.GET.get('stock_level')
            if request.GET.get('search'):
                filters['search'] = request.GET.get('search')
            if request.GET.get('include_deleted'):
                filters['include_deleted'] = request.GET.get('include_deleted')
            
            print(f"🔍 Export filters: {filters}")
            print(f"🔍 Export format: {file_type}")
            
            # Get products with filters
            products = product_service.get_all_products(
                filters=filters if filters else None, 
                include_deleted=filters.get('include_deleted', False),
                include_images=False  # Exclude images from export
            )
            
            print(f"🔍 Found {len(products)} products for export")
            
            if not products:
                # Return empty file instead of error response
                if file_type == 'csv':
                    response = HttpResponse("", content_type='text/csv')
                    response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
                    return response
                else:
                    response = HttpResponse("", content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename="products_export.xlsx"'
                    return response
            
            if file_type == 'csv':
                import csv
                from io import StringIO
                
                output = StringIO()
                
                # Use comprehensive field names that match your frontend expectations
                fieldnames = [
                    'ID', 'Product Name', 'SKU', 'Barcode', 'Category', 'Subcategory',
                    'Price', 'Cost Price', 'Stock', 'Total Stock', 'Low Stock Threshold',
                    'Status', 'Supplier', 'Description', 'Unit', 'Created At', 'Updated At'
                ]
                
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for product in products:
                    # Map product fields to CSV columns
                    row = {
                        'ID': product.get('_id', ''),
                        'Product Name': product.get('product_name', ''),
                        'SKU': product.get('SKU', ''),
                        'Barcode': product.get('barcode', ''),
                        'Category': product.get('category_name', product.get('category_id', '')),
                        'Subcategory': product.get('subcategory_name', ''),
                        'Price': product.get('selling_price', product.get('price', '')),
                        'Cost Price': product.get('cost_price', ''),
                        'Stock': product.get('stock', ''),
                        'Total Stock': product.get('total_stock', product.get('stock', '')),
                        'Low Stock Threshold': product.get('low_stock_threshold', ''),
                        'Status': product.get('status', ''),
                        'Supplier': product.get('supplier', product.get('supplier_id', '')),
                        'Description': product.get('description', ''),
                        'Unit': product.get('unit', ''),
                        'Created At': product.get('created_at', ''),
                        'Updated At': product.get('updated_at', '')
                    }
                    writer.writerow(row)
                
                response = HttpResponse(output.getvalue(), content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
                return response
                
            elif file_type == 'xlsx':
                import pandas as pd
                from io import BytesIO
                
                # Convert products to DataFrame
                data = []
                for product in products:
                    data.append({
                        'ID': product.get('_id', ''),
                        'Product Name': product.get('product_name', ''),
                        'SKU': product.get('SKU', ''),
                        'Barcode': product.get('barcode', ''),
                        'Category': product.get('category_name', product.get('category_id', '')),
                        'Subcategory': product.get('subcategory_name', ''),
                        'Price': product.get('selling_price', product.get('price', '')),
                        'Cost Price': product.get('cost_price', ''),
                        'Stock': product.get('stock', ''),
                        'Total Stock': product.get('total_stock', product.get('stock', '')),
                        'Low Stock Threshold': product.get('low_stock_threshold', ''),
                        'Status': product.get('status', ''),
                        'Supplier': product.get('supplier', product.get('supplier_id', '')),
                        'Description': product.get('description', ''),
                        'Unit': product.get('unit', ''),
                        'Created At': product.get('created_at', ''),
                        'Updated At': product.get('updated_at', '')
                    })
                
                df = pd.DataFrame(data)
                output = BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                
                response = HttpResponse(
                    output.getvalue(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = 'attachment; filename="products_export.xlsx"'
                return response
            
            else:
                # For unsupported formats, return CSV by default
                return Response(
                    {"error": "Invalid format. Use 'csv' or 'xlsx'"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except Exception as e:
            logger.error(f"Error in ProductExportView.get: {e}")
            import traceback
            traceback.print_exc()
            
            # Return error response that frontend can handle
            return Response(
                {"error": f"Export failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ImportTemplateView(View):  # ← Inherit from View, not APIView!
    """Generate import template file - Using Django View instead of DRF APIView"""
   
    def get(self, request):
        """Generate import template file"""
        print("=" * 100)
        print("🔥 GET METHOD CALLED IN DJANGO VIEW!")
        print("=" * 100)
        
        try:
            product_service = ProductService()
            file_type = request.GET.get('format', 'csv').lower()
       
            template_path = product_service.generate_import_template(file_type)
       
            if file_type == 'csv':
                with open(template_path, 'r') as f:
                    response = HttpResponse(f.read(), content_type='text/csv')
                    response['Content-Disposition'] = 'attachment; filename="product_import_template.csv"'
            else:
                with open(template_path, 'rb') as f:
                    response = HttpResponse(
                        f.read(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = 'attachment; filename="product_import_template.xlsx"'
       
            import os
            os.unlink(template_path)
       
            return response
       
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Error in ImportTemplateView.get: {e}")
            
            # Return plain Django response
            return HttpResponse(
                json.dumps({"error": str(e)}),
                content_type='application/json',
                status=500
            )
        
class BulkDeleteProductsView(APIView):
    def post(self, request):
        try:
            product_ids = request.data.get('product_ids', [])
            hard_delete = request.data.get('hard_delete', False)
        
            if not product_ids:
                return Response({'error': 'No product IDs provided'}, status=400)
        
            # Call static method directly on the class
            result = ProductService.bulk_delete_products(product_ids, hard_delete)
        
            if result['success']:
                return Response({
                    'message': f"{result['deleted_count']} products deleted successfully",
                    'details': result
                }, status=200)
            else:
                return Response({
                    'error': 'Bulk deletion failed',
                    'details': result
                }, status=400)
            
        except Exception as e:
            logger.error(f"Error in BulkDeleteProductsView.post: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProductDetailsExportCSVView(APIView):
    """Export a single product and related data as a CSV"""

    def get(self, request, product_id):
        try:
            product_service = ProductService()
            csv_data = product_service.export_product_details_csv(product_id)

            response = HttpResponse(csv_data, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename=product_{product_id}_details.csv'
            return response

        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in ProductDetailsExportCSVView.get: {e}")
            return Response(
                {"error": f"Failed to export product details: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

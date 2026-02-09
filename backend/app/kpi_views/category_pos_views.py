from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.category_service import CategoryService
from ..services.product_service import ProductService
import logging

logger = logging.getLogger(__name__)

# ================ POS CATEGORY VIEWS ================

class POSCatalogView(APIView):
    """Lightweight POS catalog for product selection"""
    
    def get(self, request):
        """Get POS catalog structure"""
        try:
            category_service = CategoryService()
            
            # Get all active categories with product counts
            categories = category_service.get_all_categories(include_deleted=False)
            
            # Filter only active categories and format for POS
            pos_catalog = []
            for category in categories:
                if category.get('status') == 'active':
                    catalog_item = {
                        'category_id': category.get('_id'),
                        'category_name': category.get('category_name'),
                        'subcategories': [],
                        'total_products': category.get('product_count', 0)
                    }
                    
                    # Add subcategories with product counts
                    for subcategory in category.get('sub_categories', []):
                        if subcategory.get('product_count', 0) > 0:  # Only include subcategories with products
                            catalog_item['subcategories'].append({
                                'name': subcategory.get('name'),
                                'product_count': subcategory.get('product_count', 0)
                            })
                    
                    # Only include categories that have products
                    if catalog_item['total_products'] > 0:
                        pos_catalog.append(catalog_item)
            
            return Response({
                "message": "POS catalog retrieved successfully",
                "catalog": pos_catalog,
                "count": len(pos_catalog)
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error getting POS catalog: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class POSProductBatchView(APIView):
    """Batch fetch products for POS cart"""
    
    def post(self, request):
        """Batch fetch multiple products by IDs for POS cart"""
        try:
            product_service = ProductService()
            product_ids = request.data.get('product_ids', [])
            
            if not product_ids or not isinstance(product_ids, list):
                return Response({"error": "product_ids array is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            products = []
            for product_id in product_ids:
                product = product_service.get_product_by_id(product_id, include_deleted=False)
                if product and product.get('status') == 'active':
                    # Format for POS cart
                    pos_product = {
                        'product_id': product.get('_id'),
                        'product_name': product.get('product_name'),
                        'SKU': product.get('SKU'),
                        'selling_price': product.get('selling_price', 0),
                        'stock': product.get('stock', 0),
                        'low_stock_threshold': product.get('low_stock_threshold', 0),
                        'unit': product.get('unit', ''),
                        'barcode': product.get('barcode'),
                        'category_id': product.get('category_id'),
                        'subcategory_name': product.get('subcategory_name'),
                        'is_taxable': product.get('is_taxable', True)
                    }
                    products.append(pos_product)
            
            return Response({
                "message": "Products retrieved successfully",
                "products": products,
                "count": len(products)
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error batch fetching products: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class POSBarcodeView(APIView):
    """POS barcode scanning"""
    
    def get(self, request, barcode):
        """Get product by barcode for POS scanner"""
        try:
            product_service = ProductService()
            
            # Find product by barcode using ProductService filter
            products = product_service.get_all_products(
                filters={'search': barcode},  # This will search barcode field
                include_deleted=False,
                include_images=False  # Exclude images for POS performance
            )
            
            # Find exact barcode match
            product = None
            for p in products:
                if p.get('barcode') == barcode and p.get('status') == 'active':
                    product = p
                    break
            
            if not product:
                return Response({"error": "Product not found for barcode"}, status=status.HTTP_404_NOT_FOUND)
            
            # Format for POS
            pos_product = {
                'product_id': product.get('_id'),
                'product_name': product.get('product_name'),
                'SKU': product.get('SKU'),
                'selling_price': product.get('selling_price', 0),
                'stock': product.get('stock', 0),
                'low_stock_threshold': product.get('low_stock_threshold', 0),
                'unit': product.get('unit', ''),
                'barcode': product.get('barcode'),
                'category_id': product.get('category_id'),
                'subcategory_name': product.get('subcategory_name'),
                'is_taxable': product.get('is_taxable', True)
            }
            
            return Response({
                "message": "Product found",
                "product": pos_product,
                "barcode": barcode
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error barcode lookup: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class POSSearchView(APIView):
    """POS product search"""
    
    def get(self, request):
        """Search products for POS by name or code"""
        try:
            product_service = ProductService()
            search_term = request.query_params.get('q')
            limit = int(request.query_params.get('limit', 20))
            
            if not search_term or not search_term.strip():
                return Response({"error": "Search term 'q' is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Search products using ProductService
            products = product_service.get_all_products(
                filters={'search': search_term.strip()},
                include_deleted=False,
                include_images=False  # Exclude images for POS performance
            )
            
            # Filter active products and format for POS
            pos_products = []
            for product in products[:limit]:  # Limit results
                if product.get('status') == 'active':
                    pos_product = {
                        'product_id': product.get('_id'),
                        'product_name': product.get('product_name'),
                        'SKU': product.get('SKU'),
                        'selling_price': product.get('selling_price', 0),
                        'stock': product.get('stock', 0),
                        'low_stock_threshold': product.get('low_stock_threshold', 0),
                        'unit': product.get('unit', ''),
                        'barcode': product.get('barcode'),
                        'category_id': product.get('category_id'),
                        'subcategory_name': product.get('subcategory_name'),
                        'is_taxable': product.get('is_taxable', True)
                    }
                    pos_products.append(pos_product)
            
            return Response({
                "message": "Search completed",
                "search_term": search_term,
                "products": pos_products,
                "count": len(pos_products)
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error POS search: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class POSSubcategoryProductsView(APIView):
    
    def get(self, request, category_id, subcategory_name):
        """Get all products in subcategory for POS"""
        try:
            category_service = CategoryService()
            
            # Use CategoryService to get products in subcategory
            products = category_service.get_products_in_subcategory(
                category_id, 
                subcategory_name, 
                include_deleted=False
            )
            
            # Format products for POS
            pos_products = []
            for product in products:
                if product.get('status') == 'active':
                    pos_product = {
                        'product_id': product.get('_id'),
                        'product_name': product.get('product_name'),
                        'SKU': product.get('SKU'),
                        'selling_price': product.get('selling_price', 0),
                        'stock': product.get('stock', 0),
                        'low_stock_threshold': product.get('low_stock_threshold', 0),
                        'unit': product.get('unit', ''),
                        'barcode': product.get('barcode'),
                        'category_id': product.get('category_id'),
                        'subcategory_name': product.get('subcategory_name'),
                        'is_taxable': product.get('is_taxable', True)
                    }
                    pos_products.append(pos_product)
            
            return Response({
                "message": "Subcategory products retrieved successfully",
                "category_id": category_id,
                "subcategory_name": subcategory_name,
                "products": pos_products,
                "count": len(pos_products)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting subcategory products: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class POSStockCheckView(APIView):
    
    def post(self, request):
        """Check product stock before adding to cart"""
        try:
            product_service = ProductService()
            product_id = request.data.get('product_id')
            requested_quantity = int(request.data.get('quantity', 1))
            
            if not product_id:
                return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            product = product_service.get_product_by_id(product_id, include_deleted=False)
            
            if not product:
                return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
            
            current_stock = product.get('stock', 0)
            low_stock_threshold = product.get('low_stock_threshold', 0)
            
            stock_status = {
                'product_id': product_id,
                'product_name': product.get('product_name'),
                'current_stock': current_stock,
                'requested_quantity': requested_quantity,
                'available': current_stock >= requested_quantity,
                'is_low_stock': current_stock <= low_stock_threshold,
                'is_out_of_stock': current_stock == 0,
                'max_available': current_stock
            }
            
            return Response({
                "message": "Stock check completed",
                "stock_status": stock_status
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error checking stock: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class POSLowStockView(APIView):
    
    def get(self, request):
        """Get products with low stock for POS alerts"""
        try:
            product_service = ProductService()
            threshold = int(request.query_params.get('threshold', 10))
            
            # Get low stock products using ProductService
            low_stock_products = product_service.get_low_stock_products()
            
            # Format for POS and apply custom threshold if provided
            pos_low_stock_products = []
            for product in low_stock_products:
                product_threshold = product.get('low_stock_threshold', 0)
                current_stock = product.get('stock', 0)
                
                # Use custom threshold if provided, otherwise use product's threshold
                effective_threshold = max(threshold, product_threshold)
                
                if current_stock <= effective_threshold and product.get('status') == 'active':
                    pos_product = {
                        'product_id': product.get('_id'),
                        'product_name': product.get('product_name'),
                        'SKU': product.get('SKU'),
                        'current_stock': current_stock,
                        'low_stock_threshold': product_threshold,
                        'effective_threshold': effective_threshold,
                        'category_id': product.get('category_id'),
                        'subcategory_name': product.get('subcategory_name'),
                        'is_out_of_stock': current_stock == 0
                    }
                    pos_low_stock_products.append(pos_product)
            
            return Response({
                "message": "Low stock products retrieved",
                "threshold": threshold,
                "products": pos_low_stock_products,
                "count": len(pos_low_stock_products)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting low stock products: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
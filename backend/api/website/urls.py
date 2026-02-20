"""
Website/Customer-Facing API URLs
Base URL: /api/v1/web/
"""
from django.urls import path
from . import (
    customer_auth_views,
    customer_product_views,
    customer_category_views,
    customer_promotion_views,
    customer_loyalty_views,
    customer_pos_views,
    customer_exportimport_views,
    category_display_views,
    category_pos_views,
    oauth_views,
)

app_name = 'web'

urlpatterns = [
    # ==================== CUSTOMER AUTHENTICATION ====================
    path('auth/login/', customer_auth_views.CustomerLoginView.as_view(), name='customer-login'),
    path('auth/register/', customer_auth_views.CustomerRegisterView.as_view(), name='customer-register'),
    path('auth/logout/', customer_auth_views.CustomerLogoutView.as_view(), name='customer-logout'),
    path('auth/profile/', customer_auth_views.CustomerProfileView.as_view(), name='customer-profile'),
    path('auth/profile/update/', customer_auth_views.CustomerUpdateProfileView.as_view(), name='customer-update-profile'),
    path('auth/password/change/', customer_auth_views.CustomerChangePasswordView.as_view(), name='customer-change-password'),
    
    # ==================== OAUTH ====================
    path('oauth/authorize/', oauth_views.OAuthAuthorizeView.as_view(), name='oauth-authorize'),
    path('oauth/callback/', oauth_views.OAuthCallbackView.as_view(), name='oauth-callback'),
    
    # ==================== CUSTOMER PRODUCTS ====================
    path('products/', customer_product_views.CustomerProductListView.as_view(), name='customer-products-list'),
    path('products/search/', customer_product_views.CustomerProductSearchView.as_view(), name='customer-products-search'),
    path('products/featured/', customer_product_views.CustomerFeaturedProductsView.as_view(), name='customer-products-featured'),
    path('products/<str:product_id>/', customer_product_views.CustomerProductDetailView.as_view(), name='customer-product-detail'),
    path('products/category/<str:category_id>/', customer_product_views.CustomerProductByCategoryView.as_view(), name='customer-products-by-category'),
    
    # ==================== CUSTOMER CATEGORIES ====================
    path('categories/', customer_category_views.CustomerCategoryListView.as_view(), name='customer-categories-list'),
    path('categories/<str:category_id>/', customer_category_views.CustomerCategoryDetailView.as_view(), name='customer-category-detail'),
    path('categories/<str:category_id>/products/', customer_category_views.CustomerCategoryWithProductsView.as_view(), name='customer-category-with-products'),
    
    # ==================== CUSTOMER PROMOTIONS ====================
    path('promotions/health/', customer_promotion_views.CustomerPromotionHealthCheckView.as_view(), name='customer-promotions-health'),
    path('promotions/', customer_promotion_views.CustomerPromotionListView.as_view(), name='customer-promotions-list'),
    path('promotions/active/', customer_promotion_views.CustomerActivePromotionsView.as_view(), name='customer-promotions-active'),
    path('promotions/search/', customer_promotion_views.CustomerPromotionSearchView.as_view(), name='customer-promotions-search'),
    path('promotions/<str:promotion_id>/', customer_promotion_views.CustomerPromotionDetailView.as_view(), name='customer-promotion-detail'),
    path('promotions/product/<str:product_id>/', customer_promotion_views.CustomerPromotionsByProductView.as_view(), name='customer-promotions-by-product'),
    path('promotions/category/<str:category_id>/', customer_promotion_views.CustomerPromotionsByCategoryView.as_view(), name='customer-promotions-by-category'),
    path('promotions/calculate/discount/', customer_promotion_views.CustomerPromotionDiscountCalculatorView.as_view(), name='customer-promotion-calculate-discount'),
    
    # ==================== CUSTOMER LOYALTY ====================
    path('loyalty/health/', customer_loyalty_views.loyalty_health_check, name='customer-loyalty-health'),
    path('loyalty/balance/', customer_loyalty_views.get_loyalty_balance, name='customer-loyalty-balance'),
    path('loyalty/history/', customer_loyalty_views.get_loyalty_history, name='customer-loyalty-history'),
    path('loyalty/validate-redemption/', customer_loyalty_views.validate_points_redemption, name='customer-loyalty-validate'),
    path('loyalty/redeem/', customer_loyalty_views.redeem_points, name='customer-loyalty-redeem'),
    path('loyalty/award/', customer_loyalty_views.award_points, name='customer-loyalty-award'),
    
    # ==================== CUSTOMER POS INTERACTIONS ====================
    path('pos/qr/scan-user/', customer_pos_views.scan_user_qr, name='pos-scan-user-qr'),
    path('pos/qr/scan-promotion/', customer_pos_views.scan_promotion_qr, name='pos-scan-promotion-qr'),
    path('pos/qr/user/<str:qr_code>/', customer_pos_views.get_user_by_qr, name='pos-get-user-by-qr'),
    path('pos/qr/promotion/<str:qr_code>/', customer_pos_views.get_promotion_by_qr, name='pos-get-promotion-by-qr'),
    path('pos/promotion/redeem/', customer_pos_views.redeem_promotion, name='pos-redeem-promotion'),
    path('pos/points/award/', customer_pos_views.award_points_manual, name='pos-award-points'),
    path('pos/points/process-order/', customer_pos_views.process_order_points, name='pos-process-order-points'),
    path('pos/dashboard/', customer_pos_views.pos_dashboard, name='pos-dashboard'),
    
    # ==================== CATEGORY DATA & EXPORTS ====================
    path('category-data/', category_display_views.CategoryDataView.as_view(), name='category-data'),
    path('category-data/export/', category_display_views.CategoryExportView.as_view(), name='category-export'),
    path('category-data/stats/', category_display_views.CategoryStatsView.as_view(), name='category-stats'),
    path('category-data/with-products/', category_display_views.CategoryWithProductsView.as_view(), name='category-with-products'),
    path('category-data/product-counts/', category_display_views.CategoryProductCountsView.as_view(), name='category-product-counts'),
    
    # ==================== POS CATALOG & OPERATIONS ====================
    path('pos-catalog/', category_pos_views.POSCatalogView.as_view(), name='pos-catalog'),
    path('pos-catalog/product-batches/', category_pos_views.POSProductBatchView.as_view(), name='pos-product-batches'),
    path('pos-catalog/barcode/', category_pos_views.POSBarcodeView.as_view(), name='pos-barcode'),
    path('pos-catalog/search/', category_pos_views.POSSearchView.as_view(), name='pos-search'),
    path('pos-catalog/subcategory/<str:subcategory_name>/products/', category_pos_views.POSSubcategoryProductsView.as_view(), name='pos-subcategory-products'),
    path('pos-catalog/stock/check/', category_pos_views.POSStockCheckView.as_view(), name='pos-stock-check'),
    path('pos-catalog/stock/low/', category_pos_views.POSLowStockView.as_view(), name='pos-low-stock'),
    
    # ==================== CUSTOMER IMPORT/EXPORT ====================
    path('customers/import-export/', customer_exportimport_views.CustomerImportExportView.as_view(), name='customer-import-export'),
]

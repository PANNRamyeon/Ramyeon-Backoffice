from django.urls import path

from .kpi_views.session_views import (
    SessionLogsView,
    SessionDetailView,  
    SessionDisplayView, 
    CombinedLogsView,
    ActiveSessionsView,
    UserSessionsView,
    SessionStatisticsView,
    SessionCleanupView,
    CleanupStatusView,  
    AutoCleanupControlView,  
    SessionExportView,  
    ForceLogoutView,
    BulkSessionControlView, 
    SystemStatusView
)

from .kpi_views.user_views import (
    HealthCheckView, 
    UserListView, 
    UserDetailView, 
    UserByEmailView, 
    UserByUsernameView,
    UserRestoreView,       
    UserHardDeleteView,     
    DeletedUsersView,       
)

from .kpi_views.customer_views import (
    CustomerListView,
    CustomerDetailView,
    CustomerRestoreView,
    CustomerHardDeleteView,
    CustomerSearchView,
    CustomerByEmailView,
    CustomerStatisticsView,
    CustomerLoyaltyView,
)

from .kpi_views.supplier_views import (
    SupplierHealthCheckView,
    SupplierListView, 
    SupplierDetailView,
    SupplierRestoreView,
    SupplierHardDeleteView,
    DeletedSuppliersView,
    # NEW: Batch integration endpoints
    SupplierBatchesView,
    SupplierStatisticsView,
    CreateBatchForSupplierView,
    # OPTIONAL: Legacy redirects for backwards compatibility
    # LegacyPurchaseOrderRedirectView,
)

from .kpi_views.authentication_views import (
    LoginView,
    LogoutView,
    RefreshTokenView,
    CurrentUserView,
    VerifyTokenView,
    RequestPasswordResetView,
    ResetPasswordView,
    VerifyResetTokenView,
)

from .kpi_views.oauth_views import (
    OAuthAuthorizeView,
    OAuthCallbackView,
)

from .kpi_views.product_views import (
    # Product CRUD views
    ProductListView,
    ProductDetailView,
    ProductBySkuView,
    ProductRestoreView,
    
    # Stock management views
    ProductStockUpdateView,
    BulkStockUpdateView,
    StockHistoryView,
    StockAdjustmentView,
    RestockProductView,
    
    # Product reports views
    LowStockProductsView,
    ExpiringProductsView,
    ProductsByCategoryView,
    DeletedProductsView,
    BulkDeleteProductsView, 
    
    # Product sync views
    ProductSyncView,
    
    # Product import/export views
    ProductImportView,
    ProductExportView,
    BulkCreateProductsView,
    ImportTemplateView,
    TestTemplateView,
    ProductDetailsExportCSVView
)

# BATCH VIEWS
from .kpi_views.batch_views import (
    # Batch CRUD
    BatchListView,
    CreateBatchView,
    BatchDetailView,
    UpdateBatchQuantityView,
    
    # Batch queries
    ProductBatchesView,
    SupplierBatchesView,  # NEW: Get batches by supplier
    ExpiringBatchesView,
    ProductsWithExpirySummaryView,
    
    # Batch operations
    ProcessSaleFIFOView,
    CheckExpiryAlertsView,
    MarkExpiredBatchesView,
    ProcessBatchAdjustmentView,
    ActivateBatchView,  # NEW: Activate pending batches
    
    # Integration
    ProductWithBatchSummaryView,
    RestockWithBatchView,
    
    # Analytics
    BatchStatisticsView,
)

from .kpi_views.category_views import (
     CategoryKPIView,
    CategoryDetailView,
    CategorySoftDeleteView,
    CategoryHardDeleteView,
    CategoryRestoreView,                  
    CategoryDeletedListView,               
    CategoryBulkOperationsView,         
    CategoryDeleteInfoView,               
    CategorySubcategoryView,              
    UncategorizedCategoryView,              
    SubcategoryProductsView,
    CategoryProductManagementView,  
)

# POS Operations
from .kpi_views.category_pos_views import (
    POSCatalogView,
    POSProductBatchView,
    POSBarcodeView,
    POSSearchView,
    POSStockCheckView,
    POSLowStockView,
    POSSubcategoryProductsView,  
)

# Display/Export Operations
from .kpi_views.category_display_views import (
    CategoryDataView,
    CategoryExportView,
    CategoryStatsView,
)

from .kpi_views.saleslog_views import (
    SalesLogView,
    SalesLogStatsView,
    SalesItemHistoryView,
    SalesTopItemView,
    SalesTopItemChartView,
)

from .kpi_views.sales_bulk_views import (
    SalesLogBulkImportView,
    SalesLogTemplateView,
    SalesLogExportView,
)

from .kpi_views.promotion_views import (
     PromotionHealthCheckView,
    PromotionListView,
    PromotionDetailView,
    PromotionByNameView,
    PromotionRestoreView,
    DeletedPromotionsView,  
    PromotionHardDeleteView,
    ActivePromotionsView,
    PromotionActivationView,
    PromotionDeactivationView,
    PromotionExpirationView,
    PromotionApplicationView,
    PromotionStatisticsView,
    PromotionAuditView,
    PromotionSearchView,
    PromotionReportView,
)

from .kpi_views.pos.salesReportView import (
    SalesSummaryView,
    SalesTransactionsView,
    SalesByPeriodView,
    DashboardSummaryView,
    SalesComparisonView,
)

from .kpi_views.pos.promotionConView import (
    POSTransactionView,
    StockValidationView,
    StockWarningsView,
    PromotionCheckoutView,
    POSTransactionKPIView,
    InventoryKPIView,
    StockAlertKPIView,
    POSHealthCheckView
)

from .kpi_views.pos.salesServiceView import (
    SalesServiceView,
    CreatePOSSale,
    CreateSalesLog,
    GetSaleID,
    FetchRecentSales,
)

from .kpi_views.enhanced_pos_sales_views import (
    CreateEnhancedPOSSaleView,
    GetEnhancedSaleView,
    VoidEnhancedSaleView,
    ValidatePointsRedemptionView,
    CalculateLoyaltyPointsView,
    CalculatePointsDiscountView,
    GetCustomerEnhancedSalesView,
    GetEnhancedSalesByDateRangeView,
    GetEnhancedSalesSummaryView,
    GetRecentEnhancedSalesView,
)

from .kpi_views.sales_display_views import (
    SalesDisplayPOSItemSummaryView,
    SalesDisplayOnlineItemSummaryView,
    SalesDisplayAllSalesView,
    SalesDisplayAllOnlineTransactionsView,
    SalesDisplayByItemView,
    SalesDisplaySummaryView 
)

from .kpi_views.online_transaction_views import (
    CreateOnlineOrderView,
    GetOnlineOrderView,
    GetCustomerOrdersView,
    GetAllOrdersView,
    UpdateOrderStatusView,
    UpdatePaymentStatusView,
    MarkReadyForDeliveryView,
    CompleteOrderView,
    CancelOrderView,
    AutoCancelExpiredOrdersView,
    UpdateAutoCancellationSettingsView,
    GetAutoCancellationStatusView,
    GetPendingOrdersView,
    GetProcessingOrdersView,
    GetOrdersByStatusView,
    GetOrderSummaryView,
    ValidateOrderStockView,
    ValidatePointsRedemptionView,
    CalculateServiceFeeView,
    CalculateLoyaltyPointsView,
)

from .kpi_views.sales_by_category_views import (
    SalesByCategoryView, 
    TopCategoriesView, 
    CategoryPerformanceDetailView
)

from .views import (
    APIDocumentationView,
)

from .kpi_views.customer_auth_views import (
    CustomerLoginView,
    CustomerRegisterView,
    CustomerLogoutView,
    CustomerProfileView,
    CustomerUpdateProfileView,
    CustomerChangePasswordView,
)

from .kpi_views.customer_exportimport_views import (
     CustomerImportExportView,
)

urlpatterns = [
    # ========== SYSTEM & HEALTH ==========
    path('', SystemStatusView.as_view(), name='system-status'),  # Root endpoint
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('docs/', APIDocumentationView.as_view(), name='api-documentation'),
    
    # ========== AUTHENTICATION ==========
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='refresh-token'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),
    path('auth/verify-token/', VerifyTokenView.as_view(), name='verify-token'),
    
    # Password Reset
    path('auth/forgot-password/', RequestPasswordResetView.as_view(), name='request-password-reset'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('auth/verify-reset-token/', VerifyResetTokenView.as_view(), name='verify-reset-token'),
    
    # OAuth Authentication
    path('auth/oauth/<str:provider>/authorize/', OAuthAuthorizeView.as_view(), name='oauth-authorize'),
    path('auth/oauth/<str:provider>/callback/', OAuthCallbackView.as_view(), name='oauth-callback'),
    
    # ========== CUSTOMER AUTHENTICATION ==========
    path('auth/customer/login/', CustomerLoginView.as_view(), name='customer-login'),
    path('auth/customer/register/', CustomerRegisterView.as_view(), name='customer-register'),
    path('auth/customer/logout/', CustomerLogoutView.as_view(), name='customer-logout'),
    path('auth/customer/profile/', CustomerProfileView.as_view(), name='customer-profile'),
    path('auth/customer/profile/update/', CustomerUpdateProfileView.as_view(), name='customer-update-profile'),
    path('auth/customer/change-password/', CustomerChangePasswordView.as_view(), name='customer-change-password'),
    
    # ========== USER MANAGEMENT ==========
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/deleted/', DeletedUsersView.as_view(), name='deleted-users'),
    path('users/email/<str:email>/', UserByEmailView.as_view(), name='user-by-email'),
    path('users/username/<str:username>/', UserByUsernameView.as_view(), name='user-by-username'),
    path('users/<str:user_id>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<str:user_id>/restore/', UserRestoreView.as_view(), name='user-restore'),
    path('users/<str:user_id>/hard-delete/', UserHardDeleteView.as_view(), name='user-hard-delete'),
    
    # ========== CUSTOMER MANAGEMENT ==========
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('customers/search/', CustomerSearchView.as_view(), name='customer-search'),
    path('customers/statistics/', CustomerStatisticsView.as_view(), name='customer-statistics'),
    path('customers/import-export/', CustomerImportExportView.as_view(), name='customer-import-export'),
    path('customers/email/<str:email>/', CustomerByEmailView.as_view(), name='customer-by-email'),
    path('customers/<str:customer_id>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/<str:customer_id>/restore/', CustomerRestoreView.as_view(), name='customer-restore'),
    path('customers/<str:customer_id>/hard-delete/', CustomerHardDeleteView.as_view(), name='customer-hard-delete'),
    path('customers/<str:customer_id>/loyalty/', CustomerLoyaltyView.as_view(), name='customer-loyalty'),
    

    # ========== SUPPLIER MANAGEMENT ==========
    path('suppliers/health/', SupplierHealthCheckView.as_view(), name='supplier-health-check'),

    # === SPECIFIC PATHS FIRST (no parameters) ===
    path('suppliers/deleted/', DeletedSuppliersView.as_view(), name='deleted-suppliers'),

    # === SUPPLIER CRUD ===
    path('suppliers/', SupplierListView.as_view(), name='supplier-list'),
    path('suppliers/<str:supplier_id>/', SupplierDetailView.as_view(), name='supplier-detail'),

    # === SUPPLIER MANAGEMENT ===
    path('suppliers/<str:supplier_id>/restore/', SupplierRestoreView.as_view(), name='supplier-restore'),
    path('suppliers/<str:supplier_id>/hard-delete/', SupplierHardDeleteView.as_view(), name='supplier-hard-delete'),

    # === SUPPLIER-BATCH INTEGRATION (NEW) ===
    path('suppliers/<str:supplier_id>/batches/', SupplierBatchesView.as_view(), name='supplier-batches'),
    path('suppliers/<str:supplier_id>/batches/create/', CreateBatchForSupplierView.as_view(), name='create-batch-for-supplier'),
    path('suppliers/<str:supplier_id>/statistics/', SupplierStatisticsView.as_view(), name='supplier-statistics'),

    # === OPTIONAL: LEGACY PURCHASE ORDER REDIRECTS (for backwards compatibility) ===
    # Uncomment these if you want to provide migration guidance for old endpoints
    # path('suppliers/<str:supplier_id>/orders/', LegacyPurchaseOrderRedirectView.as_view(), name='legacy-purchase-orders'),
    # path('suppliers/<str:supplier_id>/orders/<str:order_id>/', LegacyPurchaseOrderRedirectView.as_view(), name='legacy-purchase-order-detail'),
        
    # ========== SESSION MANAGEMENT ==========
    path('session-logs/', SessionLogsView.as_view(), name='session-logs'),
    path('session-logs/display/', SessionDisplayView.as_view(), name='session-logs-display'),
    path('session-logs/combined/', CombinedLogsView.as_view(), name='combined-logs'),
    path('session-logs/<str:session_id>/', SessionDetailView.as_view(), name='session-detail'),
    # Session management
    path('sessions/active/', ActiveSessionsView.as_view(), name='active-sessions'),
    path('sessions/user/<str:user_id>/', UserSessionsView.as_view(), name='user-sessions'),
    path('sessions/statistics/', SessionStatisticsView.as_view(), name='session-statistics'),
    # Cleanup and maintenance (Admin only)
    path('sessions/cleanup/', SessionCleanupView.as_view(), name='session-cleanup'),
    path('sessions/cleanup/status/', CleanupStatusView.as_view(), name='cleanup-status'),
    path('sessions/cleanup/auto/', AutoCleanupControlView.as_view(), name='auto-cleanup-control'),
    # Export functionality (Admin only)
    path('sessions/export/', SessionExportView.as_view(), name='session-export'),
    # Admin control endpoints
    path('sessions/force-logout/<str:user_id>/', ForceLogoutView.as_view(), name='force-logout'),
    path('sessions/bulk-control/', BulkSessionControlView.as_view(), name='bulk-session-control'),
    
    # ========== PRODUCT MANAGEMENT ==========
    # Product CRUD (static paths first)
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/sku/<str:sku>/', ProductBySkuView.as_view(), name='product-by-sku'),
    path('products/deleted/', DeletedProductsView.as_view(), name='deleted-products'),
    path('products/bulk-delete/', BulkDeleteProductsView.as_view(), name='bulk-delete-products'),
    
    # Product import/export
    path('products/import/', ProductImportView.as_view(), name='product-import'),
    path('products/test-template/', TestTemplateView.as_view(), name='test-template'),
    path('products/import/template/', ImportTemplateView.as_view(), name='import-template'),
    path('products/export/', ProductExportView.as_view(), name='product-export'),
    path('products/bulk-create/', BulkCreateProductsView.as_view(), name='bulk-create-products'),
    
    # Product reports
    path('products/reports/low-stock/', LowStockProductsView.as_view(), name='low-stock-products'),
    path('products/reports/expiring/', ExpiringProductsView.as_view(), name='expiring-products'),
    path('products/reports/by-category/<str:category_id>/', ProductsByCategoryView.as_view(), name='products-by-category'),
    
    # Product synchronization
    path('products/sync/', ProductSyncView.as_view(), name='product-sync'),
    
    # Bulk stock management
    path('products/stock/bulk-update/', BulkStockUpdateView.as_view(), name='bulk-stock-update'),
    
    # Product detail operations (parameterized paths last)
    path('products/<str:product_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<str:product_id>/restore/', ProductRestoreView.as_view(), name='product-restore'),
    path('products/<str:product_id>/stock/', ProductStockUpdateView.as_view(), name='product-stock-update'),
    path('products/<str:product_id>/stock/adjust/', StockAdjustmentView.as_view(), name='stock-adjustment'),
    path('products/<str:product_id>/stock/history/', StockHistoryView.as_view(), name='stock-history'),
    path('products/<str:product_id>/restock/', RestockProductView.as_view(), name='restock-product'),
    path('products/<str:product_id>/export/details/', ProductDetailsExportCSVView.as_view(), name='product-details-export-csv'),

    # ========== BATCH MANAGEMENT ==========
    # Batch CRUD (static paths first)
    path('batches/', BatchListView.as_view(), name='batch-list'),
    path('batches/create/', CreateBatchView.as_view(), name='batch-create'),
    path('batches/expiring/', ExpiringBatchesView.as_view(), name='expiring-batches'),
    path('batches/statistics/', BatchStatisticsView.as_view(), name='batch-statistics'),

    # Batch operations
    path('batches/process-sale/', ProcessSaleFIFOView.as_view(), name='process-sale-fifo'),
    path('batches/check-expiry-alerts/', CheckExpiryAlertsView.as_view(), name='check-expiry-alerts'),
    path('batches/mark-expired/', MarkExpiredBatchesView.as_view(), name='mark-expired-batches'),
    path('batches/adjust/', ProcessBatchAdjustmentView.as_view(), name='process-batch-adjustment'),
    path('batches/activate/', ActivateBatchView.as_view(), name='activate-batch'),

    # Batch detail operations (parameterized paths last)
    path('batches/<str:batch_id>/', BatchDetailView.as_view(), name='batch-detail'),
    path('batches/<str:batch_id>/update-quantity/', UpdateBatchQuantityView.as_view(), name='batch-update-quantity'),
    
    # Product-batch integration
    path('products/<str:product_id>/batches/', ProductBatchesView.as_view(), name='product-batches'),
    path('products/<str:product_id>/with-batches/', ProductWithBatchSummaryView.as_view(), name='product-with-batches'),
    path('products/<str:product_id>/restock-batch/', RestockWithBatchView.as_view(), name='restock-with-batch'),
    path('products/expiry-summary/', ProductsWithExpirySummaryView.as_view(), name='products-expiry-summary'),
    
    # Supplier-batch integration (NEW)
    path('batches/by-supplier/<str:supplier_id>/', SupplierBatchesView.as_view(), name='batches-by-supplier'),
    
    # ========== CATEGORY MANAGEMENT ==========
    # Core Category Operations
    path('category/', CategoryKPIView.as_view(), name='category-operations'),
    path('category/stats/', CategoryStatsView.as_view(), name='category-stats'),
    path('category/display/', CategoryDataView.as_view(), name='category-display'),
    path('category/export/', CategoryExportView.as_view(), name='category-export'),
    path('category/bulk/', CategoryBulkOperationsView.as_view(), name='category-bulk-operations'),
    path('category/product-management/', CategoryProductManagementView.as_view(), name='category-product-management'),

    # Admin-only Category Operations
    path('category/deleted/', CategoryDeletedListView.as_view(), name='category-deleted-list'),
    path('category/uncategorized/', UncategorizedCategoryView.as_view(), name='uncategorized-category'),

    # Individual Category Operations
    path('category/<str:category_id>/', CategoryDetailView.as_view(), name='category-detail'),
    path('category/<str:category_id>/delete-info/', CategoryDeleteInfoView.as_view(), name='category-delete-info'),
    path('category/<str:category_id>/soft-delete/', CategorySoftDeleteView.as_view(), name='category-soft-delete'),
    path('category/<str:category_id>/hard-delete/', CategoryHardDeleteView.as_view(), name='category-hard-delete'),
    path('category/<str:category_id>/restore/', CategoryRestoreView.as_view(), name='category-restore'),
    path('category/<str:category_id>/subcategories/', CategorySubcategoryView.as_view(), name='category-subcategories'),
    path('category/<str:category_id>/subcategories/<str:subcategory_name>/products/', SubcategoryProductsView.as_view(), name='subcategory-products'),

    # ========== POS OPERATIONS ==========
    path('pos/catalog/', POSCatalogView.as_view(), name='pos-catalog'),
    path('pos/products/batch/', POSProductBatchView.as_view(), name='pos-product-batch'),
    path('pos/search/', POSSearchView.as_view(), name='pos-search'),
    path('pos/barcode/<str:barcode>/', POSBarcodeView.as_view(), name='pos-barcode'),
    path('pos/stock/check/', POSStockCheckView.as_view(), name='pos-stock-check'),
    path('pos/stock/low/', POSLowStockView.as_view(), name='pos-low-stock'),
    path('pos/category/<str:category_id>/subcategory/<str:subcategory_name>/products/', POSSubcategoryProductsView.as_view(), name='pos-subcategory-products'),
    
    # ========== SALES & INVOICES ==========
    # Sales log operations
    path('invoices/', SalesLogView.as_view(), name='invoice-list-create'),
    path('invoices/bulk-import/', SalesLogBulkImportView.as_view(), name='invoice-bulk-import'),
    path('invoices/export/', SalesLogExportView.as_view(), name='invoice-export'),
    path('invoices/stats/', SalesLogStatsView.as_view(), name='invoice-stats'),
    path('invoices/<str:invoice_id>/', SalesLogView.as_view(), name='invoice-detail'),
    
    # Sales reports
    path('reports/top-item/', SalesTopItemView.as_view(), name='top-items'),
    path('reports/top-chart-item/', SalesTopItemChartView.as_view(), name='top-chart-items'), 
    path('reports/item-history/', SalesItemHistoryView.as_view(), name='item-history'),
    
    # Sales report API endpoints
    path('sales-report/summary/', SalesSummaryView.as_view(), name='sales_summary'),
    path('sales-report/transactions/', SalesTransactionsView.as_view(), name='sales_transactions'), 
    path('sales-report/by-period/', SalesByPeriodView.as_view(), name='sales_by_period'),
    path('sales-report/dashboard/', DashboardSummaryView.as_view(), name='dashboard_summary'),
    path('sales-report/comparison/', SalesComparisonView.as_view(), name='sales_comparison'),
    
    # Sales services
    path('sales/create/', SalesServiceView.as_view(), name='create_unified_sale'),
    path('sales/pos/create/', CreatePOSSale.as_view(), name='create_pos_sale'),
    path('sales/log/create/', CreateSalesLog.as_view(), name='create_sales_log'),
    path('sales/recent/', FetchRecentSales.as_view(), name='recent_sales'),
    path('sales/get/<str:sale_id>/', GetSaleID.as_view(), name='get_sale_by_id'),
    
    # ========== ENHANCED POS SALES ==========
    # Enhanced POS Sales Management
    path('pos-sales/enhanced/', CreateEnhancedPOSSaleView.as_view(), name='create-enhanced-pos-sale'),
    path('pos-sales/enhanced/<str:sale_id>/', GetEnhancedSaleView.as_view(), name='get-enhanced-sale'),
    path('pos-sales/enhanced/<str:sale_id>/void/', VoidEnhancedSaleView.as_view(), name='void-enhanced-sale'),
    path('pos-sales/enhanced/customer/<str:customer_id>/', GetCustomerEnhancedSalesView.as_view(), name='get-customer-enhanced-sales'),
    path('pos-sales/enhanced/recent/', GetRecentEnhancedSalesView.as_view(), name='get-recent-enhanced-sales'),
    path('pos-sales/enhanced/by-date/', GetEnhancedSalesByDateRangeView.as_view(), name='get-enhanced-sales-by-date'),
    path('pos-sales/enhanced/summary/', GetEnhancedSalesSummaryView.as_view(), name='get-enhanced-sales-summary'),
    
    # Enhanced POS Sales Utilities
    path('pos-sales/validate-points/', ValidatePointsRedemptionView.as_view(), name='validate-points-redemption'),
    path('pos-sales/calculate-points/', CalculateLoyaltyPointsView.as_view(), name='calculate-loyalty-points'),
    path('pos-sales/calculate-discount/', CalculatePointsDiscountView.as_view(), name='calculate-points-discount'),
    
    # ========== PROMOTIONS ==========
    path('promotions/', PromotionListView.as_view(), name='promotion-list'),
    path('promotions/health/', PromotionHealthCheckView.as_view(), name='promotion-health'),
    path('promotions/active/', ActivePromotionsView.as_view(), name='active-promotions'),
    path('promotions/deleted/', DeletedPromotionsView.as_view(), name='promotion-deleted-list'),
    path('promotions/search/', PromotionSearchView.as_view(), name='promotion-search'),
    path('promotions/statistics/', PromotionStatisticsView.as_view(), name='promotion-statistics'),
    path('promotions/apply/', PromotionApplicationView.as_view(), name='promotion-apply'),
    path('promotions/by-name/<str:promotion_name>/', PromotionByNameView.as_view(), name='promotion-by-name'),
    path('promotions/<str:promotion_id>/', PromotionDetailView.as_view(), name='promotion-detail'),
    path('promotions/<str:promotion_id>/activate/', PromotionActivationView.as_view(), name='promotion-activate'),
    path('promotions/<str:promotion_id>/deactivate/', PromotionDeactivationView.as_view(), name='promotion-deactivate'),
    path('promotions/<str:promotion_id>/expire/', PromotionExpirationView.as_view(), name='promotion-expire'),
    path('promotions/<str:promotion_id>/restore/', PromotionRestoreView.as_view(), name='promotion-restore'),
    path('promotions/<str:promotion_id>/hard-delete/', PromotionHardDeleteView.as_view(), name='promotion-hard-delete'),
    path('promotions/<str:promotion_id>/audit/', PromotionAuditView.as_view(), name='promotion-audit'),
    path('promotions/<str:promotion_id>/report/', PromotionReportView.as_view(), name='promotion-report'),

    # ========== POS OPERATIONS (Additional) ==========
    # POS health and core functionality
    path('pos/health/', POSHealthCheckView.as_view(), name='pos_health_check'),
    path('pos/catalog/', POSCatalogView.as_view(), name='pos_catalog'),
    path('pos/products/batch/', POSProductBatchView.as_view(), name='pos_product_batch'),
    path('pos/search/', POSSearchView.as_view(), name='pos_search'),
    path('pos/stock-check/', POSStockCheckView.as_view(), name='pos_stock_check'),
    path('pos/low-stock/', POSLowStockView.as_view(), name='pos_low_stock'),
    path('pos/barcode/<str:barcode>/', POSBarcodeView.as_view(), name='pos_barcode'),
    path('pos/subcategory/<str:category_id>/<str:subcategory_name>/', POSSubcategoryProductsView.as_view(), name='pos_subcategory_products'),
    
    # POS transactions and operations
    path('pos/transaction/', POSTransactionView.as_view(), name='pos_transaction'),
    path('pos/stock-validation/', StockValidationView.as_view(), name='stock_validation'),
    path('pos/stock-warnings/', StockWarningsView.as_view(), name='stock_warnings'),
    path('pos/promotion-preview/', PromotionCheckoutView.as_view(), name='promotion_preview'),
    
    # POS KPIs
    path('pos/kpi/transactions/', POSTransactionKPIView.as_view(), name='pos_transaction_kpi'),
    path('pos/kpi/inventory/', InventoryKPIView.as_view(), name='inventory_kpi'),
    path('pos/kpi/stock-alerts/', StockAlertKPIView.as_view(), name='stock_alert_kpi'),
   
    path('sales-display/pos-item-summary/', SalesDisplayPOSItemSummaryView.as_view(), name='sales-display-pos-item-summary'),
    path('sales-display/online-item-summary/', SalesDisplayOnlineItemSummaryView.as_view(), name='sales-display-online-item-summary'),
    path('sales-display/pos-sales/', SalesDisplayAllSalesView.as_view(), name='sales-display-all-pos-sales'),
    path('sales-display/online-transactions/', SalesDisplayAllOnlineTransactionsView.as_view(), name='sales-display-all-online-transactions'),
    path('sales-display/by-item/', SalesDisplayByItemView.as_view(), name='sales-display-by-item'),
    path('sales-display/summary/', SalesDisplaySummaryView.as_view(), name='sales-display-summary'),  
    
    # ========== ONLINE TRANSACTIONS ==========
    # Order Management
    path('online-orders/', CreateOnlineOrderView.as_view(), name='create-online-order'),
    path('online-orders/<str:order_id>/', GetOnlineOrderView.as_view(), name='get-online-order'),
    path('online-orders/customer/<str:customer_id>/', GetCustomerOrdersView.as_view(), name='get-customer-orders'),
    path('online-orders/all/', GetAllOrdersView.as_view(), name='get-all-orders'),
    
    # Order Status Management
    path('online-orders/<str:order_id>/status/', UpdateOrderStatusView.as_view(), name='update-order-status'),
    path('online-orders/<str:order_id>/payment/', UpdatePaymentStatusView.as_view(), name='update-payment-status'),
    path('online-orders/<str:order_id>/ready/', MarkReadyForDeliveryView.as_view(), name='mark-ready-for-delivery'),
    path('online-orders/<str:order_id>/complete/', CompleteOrderView.as_view(), name='complete-order'),
    path('online-orders/<str:order_id>/cancel/', CancelOrderView.as_view(), name='cancel-order'),
    
    # Auto-Cancellation Management
    path('online-orders/auto-cancel/', AutoCancelExpiredOrdersView.as_view(), name='auto-cancel-expired-orders'),
    path('online-orders/auto-cancel/settings/', UpdateAutoCancellationSettingsView.as_view(), name='update-auto-cancel-settings'),
    path('online-orders/auto-cancel/status/', GetAutoCancellationStatusView.as_view(), name='get-auto-cancel-status'),
    
    # Order Filtering
    path('online-orders/pending/', GetPendingOrdersView.as_view(), name='get-pending-orders'),
    path('online-orders/processing/', GetProcessingOrdersView.as_view(), name='get-processing-orders'),
    path('online-orders/status/<str:status>/', GetOrdersByStatusView.as_view(), name='get-orders-by-status'),
    
    # Reporting and Analytics
    path('online-orders/summary/', GetOrderSummaryView.as_view(), name='get-order-summary'),
    
    # Utility Functions
    path('online-orders/validate-stock/', ValidateOrderStockView.as_view(), name='validate-order-stock'),
    path('online-orders/validate-points/', ValidatePointsRedemptionView.as_view(), name='validate-points-redemption'),
    path('online-orders/calculate-fee/', CalculateServiceFeeView.as_view(), name='calculate-service-fee'),
    path('online-orders/calculate-points/', CalculateLoyaltyPointsView.as_view(), name='calculate-loyalty-points'),
    path('sales-display/summary/', SalesDisplaySummaryView.as_view(), name='sales-display-summary'),

    path("sales/category/", SalesByCategoryView.as_view(), name="sales-by-category"),
    path("sales/category/top/", TopCategoriesView.as_view(), name="top-categories"),
    path("sales/category/<str:category_id>/", CategoryPerformanceDetailView.as_view(), name="category-performance-detail"),
]
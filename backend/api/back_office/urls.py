"""
Admin/Back Office API URLs
Base URL: /api/v1/admin/
"""
from django.urls import path
from . import (
    authentication_views,
    user_views,
    customer_views,
    product_views,
    category_views,
    supplier_views,
    batch_views,
    promotion_views,
    session_views,
    saleslog_views,
    sales_by_category_views,
)

app_name = 'office'

urlpatterns = [
    # ==================== AUTHENTICATION ====================
    path('auth/login/', authentication_views.LoginView.as_view(), name='login'),
    path('auth/logout/', authentication_views.LogoutView.as_view(), name='logout'),
    path('auth/refresh/', authentication_views.RefreshTokenView.as_view(), name='refresh-token'),
    path('auth/me/', authentication_views.CurrentUserView.as_view(), name='current-user'),
    path('auth/verify/', authentication_views.VerifyTokenView.as_view(), name='verify-token'),
    path('auth/password-reset/request/', authentication_views.RequestPasswordResetView.as_view(), name='password-reset-request'),
    path('auth/password-reset/reset/', authentication_views.ResetPasswordView.as_view(), name='password-reset'),
    path('auth/password-reset/verify/', authentication_views.VerifyResetTokenView.as_view(), name='password-reset-verify'),
    
    # ==================== USERS ====================
    path('users/health/', user_views.HealthCheckView.as_view(), name='users-health'),
    path('users/', user_views.UserListView.as_view(), name='users-list'),
    path('users/<str:user_id>/', user_views.UserDetailView.as_view(), name='users-detail'),
    path('users/<str:user_id>/restore/', user_views.UserRestoreView.as_view(), name='users-restore'),
    path('users/<str:user_id>/hard-delete/', user_views.UserHardDeleteView.as_view(), name='users-hard-delete'),
    path('users/deleted/list/', user_views.DeletedUsersView.as_view(), name='users-deleted'),
    path('users/search/by-email/', user_views.UserByEmailView.as_view(), name='users-by-email'),
    path('users/search/by-username/', user_views.UserByUsernameView.as_view(), name='users-by-username'),
    
    # ==================== CUSTOMERS ====================
    path('customers/', customer_views.CustomerListView.as_view(), name='customers-list'),
    path('customers/register/', customer_views.CustomerRegisterView.as_view(), name='customers-register'),
    path('customers/login/', customer_views.CustomerLoginView.as_view(), name='customers-login'),
    path('customers/me/', customer_views.CustomerCurrentUserView.as_view(), name='customers-current-user'),
    path('customers/statistics/', customer_views.CustomerStatisticsView.as_view(), name='customers-statistics'),
    path('customers/search/', customer_views.CustomerSearchView.as_view(), name='customers-search'),
    path('customers/by-email/', customer_views.CustomerByEmailView.as_view(), name='customers-by-email'),
    path('customers/<str:customer_id>/', customer_views.CustomerDetailView.as_view(), name='customers-detail'),
    path('customers/<str:customer_id>/restore/', customer_views.CustomerRestoreView.as_view(), name='customers-restore'),
    path('customers/<str:customer_id>/hard-delete/', customer_views.CustomerHardDeleteView.as_view(), name='customers-hard-delete'),
    path('customers/<str:customer_id>/loyalty/', customer_views.CustomerLoyaltyView.as_view(), name='customers-loyalty'),
    
    # ==================== PRODUCTS ====================
    path('products/test/', product_views.TestTemplateView.as_view(), name='products-test'),
    path('products/', product_views.ProductListView.as_view(), name='products-list'),
    path('products/low-stock/', product_views.LowStockProductsView.as_view(), name='products-low-stock'),
    path('products/expiring/', product_views.ExpiringProductsView.as_view(), name='products-expiring'),
    path('products/deleted/', product_views.DeletedProductsView.as_view(), name='products-deleted'),
    path('products/sync/', product_views.ProductSyncView.as_view(), name='products-sync'),
    path('products/bulk-create/', product_views.BulkCreateProductsView.as_view(), name='products-bulk-create'),
    path('products/bulk-delete/', product_views.BulkDeleteProductsView.as_view(), name='products-bulk-delete'),
    path('products/import/', product_views.ProductImportView.as_view(), name='products-import'),
    path('products/import/template/', product_views.ImportTemplateView.as_view(), name='products-import-template'),
    path('products/export/', product_views.ProductExportView.as_view(), name='products-export'),
    path('products/export/details/', product_views.ProductDetailsExportCSVView.as_view(), name='products-export-details'),
    path('products/by-sku/<str:sku>/', product_views.ProductBySkuView.as_view(), name='products-by-sku'),
    path('products/category/<str:category_id>/', product_views.ProductsByCategoryView.as_view(), name='products-by-category'),
    path('products/<str:product_id>/', product_views.ProductDetailView.as_view(), name='products-detail'),
    path('products/<str:product_id>/restore/', product_views.ProductRestoreView.as_view(), name='products-restore'),
    path('products/<str:product_id>/stock/', product_views.ProductStockUpdateView.as_view(), name='products-stock-update'),
    path('products/<str:product_id>/stock/adjust/', product_views.StockAdjustmentView.as_view(), name='products-stock-adjust'),
    path('products/<str:product_id>/stock/restock/', product_views.RestockProductView.as_view(), name='products-restock'),
    path('products/<str:product_id>/stock/history/', product_views.StockHistoryView.as_view(), name='products-stock-history'),
    path('products/stock/bulk-update/', product_views.BulkStockUpdateView.as_view(), name='products-bulk-stock-update'),
    
    # ==================== CATEGORIES ====================
    path('categories/', category_views.CategoryKPIView.as_view(), name='categories-list'),
    path('categories/deleted/', category_views.CategoryDeletedListView.as_view(), name='categories-deleted'),
    path('categories/uncategorized/', category_views.UncategorizedCategoryView.as_view(), name='categories-uncategorized'),
    path('categories/bulk/', category_views.CategoryBulkOperationsView.as_view(), name='categories-bulk'),
    path('categories/<str:category_id>/', category_views.CategoryDetailView.as_view(), name='categories-detail'),
    path('categories/<str:category_id>/soft-delete/', category_views.CategorySoftDeleteView.as_view(), name='categories-soft-delete'),
    path('categories/<str:category_id>/hard-delete/', category_views.CategoryHardDeleteView.as_view(), name='categories-hard-delete'),
    path('categories/<str:category_id>/restore/', category_views.CategoryRestoreView.as_view(), name='categories-restore'),
    path('categories/<str:category_id>/delete-info/', category_views.CategoryDeleteInfoView.as_view(), name='categories-delete-info'),
    path('categories/<str:category_id>/subcategories/', category_views.CategorySubcategoryView.as_view(), name='categories-subcategories'),
    path('categories/<str:category_id>/products/', category_views.CategoryProductManagementView.as_view(), name='categories-products'),
    path('categories/subcategories/<str:subcategory_name>/products/', category_views.SubcategoryProductsView.as_view(), name='subcategory-products'),
    
    # ==================== SUPPLIERS ====================
    path('suppliers/health/', supplier_views.SupplierHealthCheckView.as_view(), name='suppliers-health'),
    path('suppliers/', supplier_views.SupplierListView.as_view(), name='suppliers-list'),
    path('suppliers/deleted/', supplier_views.DeletedSuppliersView.as_view(), name='suppliers-deleted'),
    path('suppliers/statistics/', supplier_views.SupplierStatisticsView.as_view(), name='suppliers-statistics'),
    path('suppliers/<str:supplier_id>/', supplier_views.SupplierDetailView.as_view(), name='suppliers-detail'),
    path('suppliers/<str:supplier_id>/restore/', supplier_views.SupplierRestoreView.as_view(), name='suppliers-restore'),
    path('suppliers/<str:supplier_id>/hard-delete/', supplier_views.SupplierHardDeleteView.as_view(), name='suppliers-hard-delete'),
    path('suppliers/<str:supplier_id>/batches/', supplier_views.SupplierBatchesView.as_view(), name='suppliers-batches'),
    path('suppliers/<str:supplier_id>/batches/create/', supplier_views.CreateBatchForSupplierView.as_view(), name='suppliers-create-batch'),
    path('suppliers/legacy/purchase-orders/', supplier_views.LegacyPurchaseOrderRedirectView.as_view(), name='suppliers-legacy-po'),
    
    # ==================== BATCHES ====================
    path('batches/', batch_views.BatchListView.as_view(), name='batches-list'),
    path('batches/create/', batch_views.CreateBatchView.as_view(), name='batches-create'),
    path('batches/expiring/', batch_views.ExpiringBatchesView.as_view(), name='batches-expiring'),
    path('batches/expiry-summary/', batch_views.ProductsWithExpirySummaryView.as_view(), name='batches-expiry-summary'),
    path('batches/check-expiry/', batch_views.CheckExpiryAlertsView.as_view(), name='batches-check-expiry'),
    path('batches/mark-expired/', batch_views.MarkExpiredBatchesView.as_view(), name='batches-mark-expired'),
    path('batches/statistics/', batch_views.BatchStatisticsView.as_view(), name='batches-statistics'),
    path('batches/<str:batch_id>/', batch_views.BatchDetailView.as_view(), name='batches-detail'),
    path('batches/<str:batch_id>/quantity/', batch_views.UpdateBatchQuantityView.as_view(), name='batches-update-quantity'),
    path('batches/<str:batch_id>/activate/', batch_views.ActivateBatchView.as_view(), name='batches-activate'),
    path('batches/product/<str:product_id>/', batch_views.ProductBatchesView.as_view(), name='batches-by-product'),
    path('batches/product/<str:product_id>/summary/', batch_views.ProductWithBatchSummaryView.as_view(), name='batches-product-summary'),
    path('batches/supplier/<str:supplier_id>/', batch_views.SupplierBatchesView.as_view(), name='batches-by-supplier'),
    path('batches/process/sale/', batch_views.ProcessSaleFIFOView.as_view(), name='batches-process-sale'),
    path('batches/process/adjustment/', batch_views.ProcessBatchAdjustmentView.as_view(), name='batches-process-adjustment'),
    path('batches/restock/', batch_views.RestockWithBatchView.as_view(), name='batches-restock'),
    
    # ==================== PROMOTIONS ====================
    path('promotions/health/', promotion_views.PromotionHealthCheckView.as_view(), name='promotions-health'),
    path('promotions/', promotion_views.PromotionListView.as_view(), name='promotions-list'),
    path('promotions/active/', promotion_views.ActivePromotionsView.as_view(), name='promotions-active'),
    path('promotions/deleted/', promotion_views.DeletedPromotionsView.as_view(), name='promotions-deleted'),
    path('promotions/statistics/', promotion_views.PromotionStatisticsView.as_view(), name='promotions-statistics'),
    path('promotions/audit/', promotion_views.PromotionAuditView.as_view(), name='promotions-audit'),
    path('promotions/search/', promotion_views.PromotionSearchView.as_view(), name='promotions-search'),
    path('promotions/report/', promotion_views.PromotionReportView.as_view(), name='promotions-report'),
    path('promotions/by-name/', promotion_views.PromotionByNameView.as_view(), name='promotions-by-name'),
    path('promotions/<str:promotion_id>/', promotion_views.PromotionDetailView.as_view(), name='promotions-detail'),
    path('promotions/<str:promotion_id>/activate/', promotion_views.PromotionActivationView.as_view(), name='promotions-activate'),
    path('promotions/<str:promotion_id>/deactivate/', promotion_views.PromotionDeactivationView.as_view(), name='promotions-deactivate'),
    path('promotions/<str:promotion_id>/expire/', promotion_views.PromotionExpirationView.as_view(), name='promotions-expire'),
    path('promotions/<str:promotion_id>/apply/', promotion_views.PromotionApplicationView.as_view(), name='promotions-apply'),
    path('promotions/<str:promotion_id>/restore/', promotion_views.PromotionRestoreView.as_view(), name='promotions-restore'),
    path('promotions/<str:promotion_id>/hard-delete/', promotion_views.PromotionHardDeleteView.as_view(), name='promotions-hard-delete'),
    
    # ==================== SESSIONS ====================
    path('sessions/', session_views.SessionLogsView.as_view(), name='sessions-list'),
    path('sessions/active/', session_views.ActiveSessionsView.as_view(), name='sessions-active'),
    path('sessions/statistics/', session_views.SessionStatisticsView.as_view(), name='sessions-statistics'),
    path('sessions/cleanup/', session_views.SessionCleanupView.as_view(), name='sessions-cleanup'),
    path('sessions/cleanup/status/', session_views.CleanupStatusView.as_view(), name='sessions-cleanup-status'),
    path('sessions/cleanup/auto-control/', session_views.AutoCleanupControlView.as_view(), name='sessions-auto-cleanup'),
    path('sessions/export/', session_views.SessionExportView.as_view(), name='sessions-export'),
    path('sessions/display/', session_views.SessionDisplayView.as_view(), name='sessions-display'),
    path('sessions/combined-logs/', session_views.CombinedLogsView.as_view(), name='sessions-combined-logs'),
    path('sessions/system-status/', session_views.SystemStatusView.as_view(), name='sessions-system-status'),
    path('sessions/bulk-control/', session_views.BulkSessionControlView.as_view(), name='sessions-bulk-control'),
    path('sessions/<str:session_id>/', session_views.SessionDetailView.as_view(), name='sessions-detail'),
    path('sessions/<str:session_id>/force-logout/', session_views.ForceLogoutView.as_view(), name='sessions-force-logout'),
    path('sessions/user/<str:user_id>/', session_views.UserSessionsView.as_view(), name='sessions-by-user'),
    
    # ==================== SALES LOGS ====================
    path('sales-logs/', saleslog_views.SalesLogView.as_view(), name='sales-logs-list'),
    path('sales-logs/statistics/', saleslog_views.SalesLogStatsView.as_view(), name='sales-logs-stats'),
    
    # ==================== SALES BY CATEGORY ====================
    path('reports/sales-by-category/', sales_by_category_views.SalesByCategoryView.as_view(), name='sales-by-category'),
    path('reports/top-categories/', sales_by_category_views.TopCategoriesView.as_view(), name='top-categories'),
    path('reports/category-performance/<str:category_id>/', sales_by_category_views.CategoryPerformanceDetailView.as_view(), name='category-performance'),
]

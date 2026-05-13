"""
POS (Point of Sale) API URLs
Base URL: /api/v1/pos/
"""
from django.urls import path
from . import (
    promotionConView,
    salesReportView,
    salesServiceView,
    online_transaction_views,
    shift_views,
    pos_auth_views,
)

app_name = 'pos'

urlpatterns = [
    # ==================== POS AUTH ====================
    path('auth/login/', pos_auth_views.PosLoginView.as_view(), name='pos-login'),
    path('auth/logout/', pos_auth_views.PosLogoutView.as_view(), name='pos-logout'),

    # ==================== SHIFTS ====================
    path('shifts/active/', shift_views.ShiftActiveView.as_view(), name='shift-active'),
    path('shifts/start/', shift_views.ShiftStartView.as_view(), name='shift-start'),
    path('shifts/<str:shift_id>/close/', shift_views.ShiftCloseView.as_view(), name='shift-close'),
    path('shifts/<str:shift_id>/', shift_views.ShiftDetailView.as_view(), name='shift-detail'),
    path('shifts/', shift_views.ShiftListView.as_view(), name='shift-list'),

    # ==================== POS HEALTH & STATUS ====================
    path('health/', promotionConView.POSHealthCheckView.as_view(), name='pos-health'),
    
    # ==================== POS TRANSACTIONS ====================
    path('transactions/', promotionConView.POSTransactionView.as_view(), name='pos-transactions'),
    path('transactions/checkout/', promotionConView.PromotionCheckoutView.as_view(), name='pos-checkout'),
    path('transactions/kpi/', promotionConView.POSTransactionKPIView.as_view(), name='pos-transactions-kpi'),
    
    # ==================== STOCK & INVENTORY ====================
    path('stock/validate/', promotionConView.StockValidationView.as_view(), name='stock-validate'),
    path('stock/warnings/', promotionConView.StockWarningsView.as_view(), name='stock-warnings'),
    path('inventory/kpi/', promotionConView.InventoryKPIView.as_view(), name='inventory-kpi'),
    path('inventory/alerts/', promotionConView.StockAlertKPIView.as_view(), name='stock-alerts'),
    
    # ==================== SALES SERVICE ====================
    path('sales/', salesServiceView.SalesServiceView.as_view(), name='sales-service'),
    
    # ==================== SALES REPORTS ====================
    path('reports/summary/', salesReportView.SalesSummaryView.as_view(), name='sales-summary'),
    path('reports/by-period/', salesReportView.SalesByPeriodView.as_view(), name='sales-by-period'),
    path('reports/dashboard/', salesReportView.DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('reports/comparison/', salesReportView.SalesComparisonView.as_view(), name='sales-comparison'),
    path('reports/transactions/', salesReportView.SalesTransactionsView.as_view(), name='sales-transactions'),
    
    # ==================== ONLINE ORDERS ====================
    path('orders/online/create/', online_transaction_views.CreateOnlineOrderView.as_view(), name='create-online-order'),
    path('orders/online/<str:order_id>/', online_transaction_views.GetOnlineOrderView.as_view(), name='get-online-order'),
    path('orders/online/customer/<str:customer_id>/', online_transaction_views.GetCustomerOrdersView.as_view(), name='customer-orders'),
    path('orders/online/', online_transaction_views.GetAllOrdersView.as_view(), name='all-orders'),
    path('orders/online/pending/', online_transaction_views.GetPendingOrdersView.as_view(), name='pending-orders'),
    path('orders/online/processing/', online_transaction_views.GetProcessingOrdersView.as_view(), name='processing-orders'),
    path('orders/online/status/<str:status>/', online_transaction_views.GetOrdersByStatusView.as_view(), name='orders-by-status'),
    path('orders/online/summary/', online_transaction_views.GetOrderSummaryView.as_view(), name='order-summary'),
    
    # ==================== ORDER MANAGEMENT ====================
    path('orders/<str:order_id>/status/', online_transaction_views.UpdateOrderStatusView.as_view(), name='update-order-status'),
    path('orders/<str:order_id>/payment/', online_transaction_views.UpdatePaymentStatusView.as_view(), name='update-payment-status'),
    path('orders/<str:order_id>/ready/', online_transaction_views.MarkReadyForDeliveryView.as_view(), name='mark-ready-for-delivery'),
    path('orders/<str:order_id>/complete/', online_transaction_views.CompleteOrderView.as_view(), name='complete-order'),
    path('orders/<str:order_id>/cancel/', online_transaction_views.CancelOrderView.as_view(), name='cancel-order'),
    
    # ==================== ORDER AUTOMATION ====================
    path('orders/auto-cancel/run/', online_transaction_views.AutoCancelExpiredOrdersView.as_view(), name='auto-cancel-orders'),
    path('orders/auto-cancel/settings/', online_transaction_views.UpdateAutoCancellationSettingsView.as_view(), name='auto-cancel-settings'),
    path('orders/auto-cancel/status/', online_transaction_views.GetAutoCancellationStatusView.as_view(), name='auto-cancel-status'),
    
    # ==================== ORDER VALIDATION ====================
    path('orders/validate/stock/', online_transaction_views.ValidateOrderStockView.as_view(), name='validate-order-stock'),
    path('orders/validate/points/', online_transaction_views.ValidatePointsRedemptionView.as_view(), name='validate-points-redemption'),
    
    # ==================== ORDER CALCULATIONS ====================
    path('orders/calculate/service-fee/', online_transaction_views.CalculateServiceFeeView.as_view(), name='calculate-service-fee'),
    path('orders/calculate/loyalty-points/', online_transaction_views.CalculateLoyaltyPointsView.as_view(), name='calculate-loyalty-points'),
]

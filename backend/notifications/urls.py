from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # ================================================================
    # BULK OPERATIONS - PUT THESE FIRST (most specific)
    # ================================================================
    path('mark-all-read/', views.mark_all_notifications_read, name='mark_all_read'),
    path('mark-all-unread/', views.mark_all_notifications_unread, name='mark_all_unread'),
    path('archive-all-read/', views.archive_all_read_notifications, name='archive_all_read'),
    
    # ================================================================
    # SPECIAL ENDPOINTS - BEFORE GENERIC PATTERNS
    # ================================================================
    path('recent/', views.recent_notifications, name='recent'),
    path('all/', views.all_notifications, name='all'),
    path('archived/', views.get_archived_notifications, name='archived'),
    path('stats/', views.notification_stats, name='stats'),
    
    # ================================================================
    # EMAIL VERIFICATION ENDPOINTS
    # ================================================================
    path('email/verify/', views.verify_email, name='verify_email'),  # Legacy link-based
    path('email/verify-code/', views.verify_code, name='verify_code'),  # Code-based verification
    path('email/send-code/', views.send_verification_code, name='send_verification_code'),
    path('email/resend-verification/', views.resend_verification_email, name='resend_verification'),  # Legacy (now sends code)
    
    # ================================================================
    # CREATION ENDPOINTS
    # ================================================================
    path('create/', views.create_notification, name='create'),
    path('create/inventory-alert/', views.create_inventory_alert, name='inventory_alert'),
    
    # ================================================================
    # LIST/FILTER ENDPOINTS
    # ================================================================
    path('list/', views.list_notifications, name='list'),
    path('<str:notification_id>/mark-read/', views.mark_notification_read, name='mark_read'),
    path('<str:notification_id>/archive/', views.archive_notification, name='archive'),
    path('<str:notification_id>/unarchive/', views.unarchive_notification, name='unarchive'),
    path('<str:notification_id>/delete/', views.delete_notification, name='delete'),
]
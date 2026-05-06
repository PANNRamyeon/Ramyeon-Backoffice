from django.urls import path
from . import views

urlpatterns = [
    # Creation
    path('create/', views.create_notification, name='create_notification'),
    path('create-inventory-alert/', views.create_inventory_alert, name='create_inventory_alert'),

    # Retrieval
    path('list/', views.list_notifications, name='list_notifications'),
    path('get/<str:notification_id>/', views.get_notification, name='get_notification'),
    path('recent/', views.recent_notifications, name='recent_notifications'),
    path('all/', views.all_notifications, name='all_notifications'),
    path('unread-count/', views.unread_count, name='unread_count'),

    # Status updates
    path('mark-read/<str:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-unread/<str:notification_id>/', views.mark_notification_unread, name='mark_notification_unread'),
    path('mark-all-read/', views.mark_all_notifications_read, name='mark_all_read'),

    # Archive
    path('archive/<str:notification_id>/', views.archive_notification, name='archive_notification'),
    path('unarchive/<str:notification_id>/', views.unarchive_notification, name='unarchive_notification'),

    # Deletion
    path('delete/<str:notification_id>/', views.delete_notification, name='delete_notification'),

    # Statistics
    path('stats/', views.notification_stats, name='notification_stats'),
]
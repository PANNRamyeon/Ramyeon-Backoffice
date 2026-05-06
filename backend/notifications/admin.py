# notifications/admin.py
# from django.contrib import admin
# from .models import Notification
#
# @admin.register(Notification)
# class NotificationAdmin(admin.ModelAdmin):
#     list_display = ['title', 'recipient', 'priority', 'notification_type', 'is_read', 'created_at']
#     list_filter = ['priority', 'notification_type', 'is_read', 'created_at']
#     search_fields = ['title', 'message', 'recipient__username']
#     readonly_fields = ['id', 'created_at', 'updated_at']
#     list_editable = ['is_read']
#     ordering = ['-created_at']
#    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('title', 'message', 'recipient')
#         }),
#         ('Classification', {
#             'fields': ('priority', 'notification_type')
#         }),
#         ('Status', {
#             'fields': ('is_read',)
#         }),
#         ('Metadata', {
#             'fields': ('metadata',),
#             'classes': ('collapse',)
#         }),
#         ('Timestamps', {
#             'fields': ('id', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
#    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('recipient')
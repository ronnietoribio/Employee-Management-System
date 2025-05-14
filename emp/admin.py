from django.contrib import admin
from .models import Emp, Settings

@admin.register(Emp)
class EmpAdmin(admin.ModelAdmin):
    list_display = ('name', 'emp_id', 'department', 'phone', 'working', 'created_at', 'last_modified')
    list_filter = ('working', 'department')
    search_fields = ('name', 'emp_id', 'phone', 'department')
    ordering = ('-last_modified',)
    list_per_page = 20

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'emp_id', 'phone')
        }),
        ('Work Details', {
            'fields': ('department', 'working')
        }),
        ('Additional Information', {
            'fields': ('address',)
        }),
    )

@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'company_address', 'company_contact', 'company_email'),
            'classes': ('wide',)
        }),
        ('Department Configuration', {
            'fields': ('department_choices',),
            'classes': ('wide',),
            'description': 'Enter department names separated by commas (e.g., "HR, IT, Finance")'
        }),
        ('Email Notifications', {
            'fields': ('enable_email_notifications', 'notification_email'),
            'classes': ('wide',),
            'description': 'Configure email notification settings'
        }),
        ('System Settings', {
            'fields': ('items_per_page', 'enable_audit_trail'),
            'classes': ('wide',),
            'description': 'General system configuration'
        }),
        ('Theme Customization', {
            'fields': ('primary_color', 'secondary_color'),
            'classes': ('wide',),
            'description': 'Customize the application theme colors (use hex color codes)'
        }),
    )

    def has_add_permission(self, request):
        # Prevent creating multiple settings instances
        return not Settings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the settings instance
        return False

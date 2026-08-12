from django.contrib import admin

from src.backoffice.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "module", "object_type", "object_repr", "ip_address")
    list_filter = ("action", "module", "timestamp")
    search_fields = ("actor__username", "module", "object_type", "object_id", "object_repr", "ip_address")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False if obj else super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False

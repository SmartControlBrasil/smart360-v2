from django.contrib import admin

from src.backoffice.models import AuditLog
from src.backoffice.models import BusinessUnit
from src.backoffice.models import BusinessUnitMembership
from src.backoffice.models import Department
from src.backoffice.models import Team


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


@admin.register(BusinessUnit)
class BusinessUnitAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "business_unit", "is_active", "updated_at")
    list_filter = ("business_unit", "is_active")
    search_fields = ("name", "code", "slug", "business_unit__name")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "department", "business_unit", "is_active", "updated_at")
    list_filter = ("department__business_unit", "department", "is_active")
    search_fields = ("name", "code", "slug", "department__name", "department__business_unit__name")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Business Unit")
    def business_unit(self, obj):
        return obj.department.business_unit


@admin.register(BusinessUnitMembership)
class BusinessUnitMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "business_unit", "department", "team", "scope", "is_active", "updated_at")
    list_filter = ("scope", "is_active", "business_unit")
    search_fields = ("user__username", "user__email", "business_unit__code", "business_unit__name")

from django.contrib import admin

from src.customers.models import Customer
from src.customers.models import CustomerBusinessRelationship
from src.customers.models import CustomerAssignmentTransfer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "customer_type", "document", "city", "state", "assigned_salesperson", "status", "updated_at")
    list_filter = ("status", "customer_type", "state")
    search_fields = ("legal_name", "trade_name", "document", "email", "phone", "whatsapp")


@admin.register(CustomerBusinessRelationship)
class CustomerBusinessRelationshipAdmin(admin.ModelAdmin):
    list_display = ("customer", "business_unit", "assigned_salesperson", "status", "updated_at")
    list_filter = ("business_unit", "status")
    search_fields = ("customer__legal_name", "customer__trade_name", "business_unit__code", "assigned_salesperson__name")


@admin.register(CustomerAssignmentTransfer)
class CustomerAssignmentTransferAdmin(admin.ModelAdmin):
    list_display = ("relationship", "previous_salesperson", "new_salesperson", "transferred_by", "transferred_at")
    list_filter = ("relationship__business_unit", "transferred_at")
    search_fields = ("relationship__customer__legal_name", "previous_salesperson__name", "new_salesperson__name", "reason")
    readonly_fields = ("relationship", "previous_salesperson", "new_salesperson", "transferred_by", "reason", "transferred_at", "metadata")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

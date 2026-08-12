from django.contrib import admin

from src.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "customer_type", "document", "city", "state", "assigned_salesperson", "status", "updated_at")
    list_filter = ("status", "customer_type", "state")
    search_fields = ("legal_name", "trade_name", "document", "email", "phone", "whatsapp")

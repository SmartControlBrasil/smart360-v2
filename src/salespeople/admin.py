from django.contrib import admin

from src.salespeople.models import Salesperson


@admin.register(Salesperson)
class SalespersonAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "user", "email", "phone", "active", "updated_at")
    list_filter = ("active",)
    search_fields = ("code", "name", "email", "phone", "user__username")

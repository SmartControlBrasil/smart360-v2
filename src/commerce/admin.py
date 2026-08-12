from django.contrib import admin
from django.utils.html import format_html

from .models import Brand
from .models import Category
from .models import Product
from .models import ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active", "updated_at")
    list_filter = ("active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "logo_preview", "active", "updated_at")
    readonly_fields = ("logo_preview",)
    list_filter = ("active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Logo")
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height:48px; max-width:120px;" alt="" />', obj.logo.url)
        return "-"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("image_preview",)

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:64px; max-width:96px;" alt="" />', obj.image.url)
        return "-"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "category",
        "brand",
        "sale_mode",
        "availability",
        "featured",
        "show_price",
        "price",
        "active",
    )
    list_filter = ("active", "featured", "sale_mode", "availability", "category", "brand")
    search_fields = ("name", "sku", "short_description", "description", "brand__name", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        ("Identificação", {"fields": ("name", "slug", "sku", "category", "brand")}),
        ("Vitrine comercial", {"fields": ("sale_mode", "availability", "featured", "active")}),
        ("Preço", {"fields": ("show_price", "price")}),
        ("Conteúdo", {"fields": ("short_description", "description")}),
        ("SEO", {"fields": ("seo_title", "seo_description")}),
    )
    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "position", "is_primary", "image_preview")
    readonly_fields = ("image_preview",)
    list_filter = ("is_primary",)
    search_fields = ("product__name", "alt_text")

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:64px; max-width:96px;" alt="" />', obj.image.url)
        return "-"

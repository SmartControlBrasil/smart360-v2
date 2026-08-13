from django.db import transaction

from src.backoffice.audit.services import AuditService
from src.backoffice.models import AuditLog
from src.backoffice.services.audit_helpers import model_snapshot
from src.commerce.models import Brand
from src.commerce.models import Category
from src.commerce.models import Product
from src.commerce.models import ProductImage

PRODUCT_AUDIT_FIELDS = [
    "name", "slug", "sku", "category", "brand", "sale_mode", "show_price", "price",
    "availability", "short_description", "description", "featured", "active",
    "seo_title", "seo_description",
]
CATEGORY_AUDIT_FIELDS = ["name", "slug", "description", "active"]
BRAND_AUDIT_FIELDS = ["name", "slug", "description", "logo", "active"]
IMAGE_AUDIT_FIELDS = ["product", "image", "alt_text", "position", "is_primary"]


def _action_for_active_change(before, after):
    if before.get("active") == after.get("active"):
        return AuditLog.Action.UPDATE
    return AuditLog.Action.ACTIVATE if after.get("active") else AuditLog.Action.DEACTIVATE


def create_product(*, form, request):
    with transaction.atomic():
        product = form.save()
        AuditService.record(
            action=AuditLog.Action.CREATE, module="commerce.products", request=request, actor=request.user,
            object_type="Product", object_id=product.pk, object_repr=str(product),
            after_data=model_snapshot(product, PRODUCT_AUDIT_FIELDS),
        )
    return product


def update_product(*, product, form, request):
    before = model_snapshot(Product.objects.get(pk=product.pk), PRODUCT_AUDIT_FIELDS)
    with transaction.atomic():
        product = form.save()
        after = model_snapshot(product, PRODUCT_AUDIT_FIELDS)
        AuditService.record(
            action=_action_for_active_change(before, after), module="commerce.products", request=request, actor=request.user,
            object_type="Product", object_id=product.pk, object_repr=str(product), before_data=before, after_data=after,
        )
    return product


def set_product_active(*, product, active, request):
    before = model_snapshot(product, PRODUCT_AUDIT_FIELDS)
    with transaction.atomic():
        product.active = active
        product.save(update_fields=["active", "updated_at"])
        after = model_snapshot(product, PRODUCT_AUDIT_FIELDS)
        AuditService.record(
            action=AuditLog.Action.ACTIVATE if active else AuditLog.Action.DEACTIVATE,
            module="commerce.products", request=request, actor=request.user, object_type="Product",
            object_id=product.pk, object_repr=str(product), before_data=before, after_data=after,
        )
    return product


def set_product_featured(*, product, featured, request):
    before = model_snapshot(product, PRODUCT_AUDIT_FIELDS)
    with transaction.atomic():
        product.featured = featured
        product.save(update_fields=["featured", "updated_at"])
        after = model_snapshot(product, PRODUCT_AUDIT_FIELDS)
        AuditService.record(
            action=AuditLog.Action.UPDATE, module="commerce.products", request=request, actor=request.user,
            object_type="Product", object_id=product.pk, object_repr=str(product), before_data=before, after_data=after,
        )
    return product


def create_category(*, form, request):
    with transaction.atomic():
        category = form.save()
        AuditService.record(
            action=AuditLog.Action.CREATE, module="commerce.categories", request=request, actor=request.user,
            object_type="Category", object_id=category.pk, object_repr=str(category),
            after_data=model_snapshot(category, CATEGORY_AUDIT_FIELDS),
        )
    return category


def update_category(*, category, form, request):
    before = model_snapshot(Category.objects.get(pk=category.pk), CATEGORY_AUDIT_FIELDS)
    with transaction.atomic():
        category = form.save()
        after = model_snapshot(category, CATEGORY_AUDIT_FIELDS)
        AuditService.record(
            action=_action_for_active_change(before, after), module="commerce.categories", request=request, actor=request.user,
            object_type="Category", object_id=category.pk, object_repr=str(category), before_data=before, after_data=after,
        )
    return category


def create_brand(*, form, request):
    with transaction.atomic():
        brand = form.save()
        AuditService.record(
            action=AuditLog.Action.CREATE, module="commerce.brands", request=request, actor=request.user,
            object_type="Brand", object_id=brand.pk, object_repr=str(brand), after_data=model_snapshot(brand, BRAND_AUDIT_FIELDS),
        )
    return brand


def update_brand(*, brand, form, request):
    before = model_snapshot(Brand.objects.get(pk=brand.pk), BRAND_AUDIT_FIELDS)
    with transaction.atomic():
        brand = form.save()
        after = model_snapshot(brand, BRAND_AUDIT_FIELDS)
        AuditService.record(
            action=_action_for_active_change(before, after), module="commerce.brands", request=request, actor=request.user,
            object_type="Brand", object_id=brand.pk, object_repr=str(brand), before_data=before, after_data=after,
        )
    return brand


def create_product_image(*, product, form, request):
    with transaction.atomic():
        image = form.save(commit=False)
        image.product = product
        image.save()
        AuditService.record(
            action=AuditLog.Action.CREATE, module="commerce.product_images", request=request, actor=request.user,
            object_type="ProductImage", object_id=image.pk, object_repr=str(image), after_data=model_snapshot(image, IMAGE_AUDIT_FIELDS),
        )
    return image


def delete_product_image(*, image, request):
    before = model_snapshot(image, IMAGE_AUDIT_FIELDS)
    product = image.product
    with transaction.atomic():
        image_file = image.image
        image.delete()
        if image_file:
            image_file.delete(save=False)
        AuditService.record(
            action=AuditLog.Action.DELETE, module="commerce.product_images", request=request, actor=request.user,
            object_type="ProductImage", object_id=before.get("id", ""), object_repr=before.get("image", ""), before_data=before,
            metadata={"product_id": product.pk, "product": str(product)},
        )
    return product

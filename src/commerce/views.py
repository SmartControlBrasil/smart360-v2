from django.shortcuts import get_object_or_404
from django.shortcuts import render

from .models import Category
from .models import Product


def _active_products():
    return (
        Product.objects.filter(active=True, category__active=True)
        .select_related("category", "brand")
        .prefetch_related("images")
    )


def product_list(request):
    products = _active_products()
    categories = Category.objects.filter(active=True).order_by("name")
    return render(
        request,
        "commerce/shop.html",
        {
            "products": products,
            "categories": categories,
            "page_heading": "Loja",
        },
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, active=True)
    products = _active_products().filter(category=category)
    categories = Category.objects.filter(active=True).order_by("name")
    return render(
        request,
        "commerce/shop.html",
        {
            "products": products,
            "categories": categories,
            "category": category,
            "page_heading": category.name,
        },
    )


def legacy_shop_details(request):
    return render(request, "institutional/pages/shop_details.html")


def product_detail(request, slug):
    product = get_object_or_404(_active_products(), slug=slug)
    related_products = _active_products().filter(category=product.category).exclude(pk=product.pk)[:4]
    return render(
        request,
        "commerce/product_detail.html",
        {
            "product": product,
            "related_products": related_products,
            "canonical_path": product.get_absolute_url(),
        },
    )

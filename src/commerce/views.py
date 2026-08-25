from types import SimpleNamespace

from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse

from .models import Category
from .models import Product
from .seo import CANONICAL_PRODUCT_ROUTE_BY_SLUG
from .seo import NOINDEX_CATEGORY_SLUGS


def _active_products():
    return (
        Product.objects.filter(active=True, category__active=True)
        .select_related("category", "brand")
        .prefetch_related("images")
    )


def _metadata(title, description, canonical_path=None, robots=None):
    return SimpleNamespace(
        title=title,
        description=description,
        canonical_path=canonical_path,
        robots=robots,
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
            "page": SimpleNamespace(
                metadata=_metadata(
                    "Loja de Automação, Robótica e Tecnologia | Smart Control Brasil",
                    "Conheça soluções em automação industrial, robótica Xyron, refrigeração e equipamentos tecnológicos com atendimento técnico especializado.",
                    reverse("commerce:shop"),
                )
            ),
        },
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, active=True)
    products = _active_products().filter(category=category)
    categories = Category.objects.filter(active=True).order_by("name")
    robots = "noindex,follow" if category.slug in NOINDEX_CATEGORY_SLUGS else None
    return render(
        request,
        "commerce/shop.html",
        {
            "products": products,
            "categories": categories,
            "category": category,
            "page_heading": category.name,
            "page": SimpleNamespace(
                metadata=_metadata(
                    f"{category.name} na Loja | Smart Control Brasil",
                    category.description or f"Produtos e soluções de {category.name.lower()} disponíveis na loja Smart Control Brasil.",
                    category.get_absolute_url(),
                    robots,
                )
            ),
        },
    )


def legacy_shop_details(request):
    return render(request, "institutional/pages/shop_details.html")


def _permanent_redirect_to_route(request, route_name):
    url = reverse(route_name)
    query_string = request.META.get("QUERY_STRING")
    if query_string:
        url = f"{url}?{query_string}"
    return redirect(url, permanent=True)


def product_detail(request, slug):
    route_name = CANONICAL_PRODUCT_ROUTE_BY_SLUG.get(slug)
    if route_name:
        return _permanent_redirect_to_route(request, route_name)

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

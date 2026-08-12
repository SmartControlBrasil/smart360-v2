from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from src.institutional.presentation.sitemaps import BlogPostSitemap
from src.institutional.presentation.sitemaps import CommerceCategorySitemap
from src.institutional.presentation.sitemaps import CommerceProductSitemap
from src.institutional.presentation.sitemaps import CommerceStaticSitemap
from src.institutional.presentation.sitemaps import StaticViewSitemap


sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogPostSitemap,
    "commerce_static": CommerceStaticSitemap,
    "commerce_categories": CommerceCategorySitemap,
    "commerce_products": CommerceProductSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("loja/", include("src.commerce.urls", namespace="commerce")),
    path("", include("src.institutional.presentation.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

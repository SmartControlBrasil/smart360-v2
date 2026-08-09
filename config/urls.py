from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from src.institutional.presentation.sitemaps import BlogPostSitemap
from src.institutional.presentation.sitemaps import StaticViewSitemap


sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogPostSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("", include("src.institutional.presentation.urls")),
]

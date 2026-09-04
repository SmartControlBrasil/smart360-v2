from django.contrib.sitemaps import Sitemap
from django.conf import settings
from django.urls import reverse
from datetime import date

from src.institutional.presentation.blog_posts import BLOG_POSTS
from src.institutional.presentation.blog_editorial import BLOG_POST_EDITORIAL
from src.institutional.presentation.authors import AUTHORS
from src.commerce.models import Category
from src.commerce.models import Product
from src.commerce.seo import CANONICAL_PRODUCT_ROUTE_BY_SLUG
from src.commerce.seo import NOINDEX_CATEGORY_SLUGS


STATIC_PUBLIC_ROUTES = (
    {
        "name": "institutional:home",
        "changefreq": "weekly",
        "priority": 1.0,
    },
    {
        "name": "institutional:xyron",
        "changefreq": "weekly",
        "priority": 0.9,
    },
    {
        "name": "institutional:robotica_educacional",
        "changefreq": "weekly",
        "priority": 0.88,
    },
    {
        "name": "institutional:robos_limpeza_profissional",
        "changefreq": "weekly",
        "priority": 0.88,
    },
    {
        "name": "institutional:robos_seguranca_patrimonial",
        "changefreq": "weekly",
        "priority": 0.88,
    },
    {
        "name": "institutional:xyron_littlebot",
        "changefreq": "weekly",
        "priority": 0.85,
    },
    {
        "name": "institutional:xyron_orbit",
        "changefreq": "weekly",
        "priority": 0.85,
    },
    {
        "name": "institutional:xyron_neo_bot",
        "changefreq": "weekly",
        "priority": 0.85,
    },
    {
        "name": "institutional:xyron_waiter_bot",
        "changefreq": "weekly",
        "priority": 0.85,
    },
    {
        "name": "institutional:xyron_hygibot_dune_bot",
        "changefreq": "weekly",
        "priority": 0.85,
    },
    {
        "name": "institutional:xyron_buddy_bot",
        "changefreq": "weekly",
        "priority": 0.85,
    },
    {
        "name": "institutional:xyron_carebot",
        "changefreq": "weekly",
        "priority": 0.85,
    },
    {
        "name": "institutional:xyron_connect_bot",
        "changefreq": "weekly",
        "priority": 0.85,
    },
    {
        "name": "institutional:xyron_mowerbot",
        "changefreq": "weekly",
        "priority": 0.85,
    },
    {
        "name": "institutional:mitsubishi_automacao_industrial",
        "changefreq": "weekly",
        "priority": 0.9,
    },
    {
        "name": "institutional:manutencao_industrial_campo",
        "changefreq": "weekly",
        "priority": 0.9,
    },
    {
        "name": "institutional:sistemas_websites_python",
        "changefreq": "weekly",
        "priority": 0.9,
    },
    {
        "name": "institutional:services",
        "changefreq": "weekly",
        "priority": 0.9,
    },
    {
        "name": "institutional:blog",
        "changefreq": "weekly",
        "priority": 0.8,
    },
    {
        "name": "institutional:about",
        "changefreq": "monthly",
        "priority": 0.7,
    },
    {
        "name": "institutional:contact",
        "changefreq": "monthly",
        "priority": 0.7,
    },
)


class StaticViewSitemap(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        return settings.PUBLIC_SITE_URL.removeprefix("https://").removeprefix("http://")

    def items(self):
        return STATIC_PUBLIC_ROUTES

    def location(self, item):
        return reverse(item["name"])

    def changefreq(self, item):
        return item["changefreq"]

    def priority(self, item):
        return item["priority"]



class BlogPostSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8
    protocol = "https"

    def get_domain(self, site=None):
        return settings.PUBLIC_SITE_URL.removeprefix("https://").removeprefix("http://")

    def items(self):
        return list(BLOG_POSTS)

    def location(self, slug):
        return reverse("institutional:blog_detail", kwargs={"slug": slug})

    def lastmod(self, slug):
        return date.fromisoformat(BLOG_POST_EDITORIAL[slug]["date_modified"])


class AuthorSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7
    protocol = "https"

    def get_domain(self, site=None):
        return settings.PUBLIC_SITE_URL.removeprefix("https://").removeprefix("http://")

    def items(self):
        return list(AUTHORS)

    def location(self, slug):
        return reverse("institutional:author_detail", kwargs={"slug": slug})

    def lastmod(self, slug):
        modified_dates = [
            BLOG_POST_EDITORIAL[post_slug]["date_modified"]
            for post_slug, editorial in BLOG_POST_EDITORIAL.items()
            if editorial["author_slug"] == slug
        ]
        return max(date.fromisoformat(value) for value in modified_dates)


class CommerceStaticSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def get_domain(self, site=None):
        return settings.PUBLIC_SITE_URL.removeprefix("https://").removeprefix("http://")

    def items(self):
        return ["commerce:shop"]

    def location(self, item):
        return reverse(item)


class CommerceCategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7
    protocol = "https"

    def get_domain(self, site=None):
        return settings.PUBLIC_SITE_URL.removeprefix("https://").removeprefix("http://")

    def items(self):
        return (
            Category.objects.filter(active=True)
            .exclude(slug__in=NOINDEX_CATEGORY_SLUGS)
            .order_by("slug")
        )

    def location(self, item):
        return item.get_absolute_url()

    def lastmod(self, item):
        return item.updated_at


class CommerceProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def get_domain(self, site=None):
        return settings.PUBLIC_SITE_URL.removeprefix("https://").removeprefix("http://")

    def items(self):
        return (
            Product.objects.filter(active=True, category__active=True)
            .exclude(slug__in=CANONICAL_PRODUCT_ROUTE_BY_SLUG)
            .order_by("slug")
        )

    def location(self, item):
        return item.get_absolute_url()

    def lastmod(self, item):
        return item.updated_at

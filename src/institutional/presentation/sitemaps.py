from django.contrib.sitemaps import Sitemap
from django.conf import settings
from django.urls import reverse

from src.institutional.presentation.blog_posts import BLOG_POSTS
from src.commerce.models import Category
from src.commerce.models import Product


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
        "priority": 0.85,
    },
    {
        "name": "institutional:robo_seguranca_condominios",
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
        "name": "institutional:projects",
        "changefreq": "monthly",
        "priority": 0.8,
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
        "name": "institutional:testimonials",
        "changefreq": "monthly",
        "priority": 0.7,
    },
    {
        "name": "institutional:faq",
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
        return Category.objects.filter(active=True).order_by("slug")

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
        return Product.objects.filter(active=True, category__active=True).order_by("slug")

    def location(self, item):
        return item.get_absolute_url()

    def lastmod(self, item):
        return item.updated_at

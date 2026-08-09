from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from src.institutional.presentation.blog_posts import BLOG_POSTS


STATIC_PUBLIC_ROUTES = (
    {
        "name": "institutional:home",
        "changefreq": "weekly",
        "priority": 1.0,
    },
    {
        "name": "institutional:engenharia_serralheria_industrial",
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

    def items(self):
        return list(BLOG_POSTS)

    def location(self, slug):
        return reverse("institutional:blog_detail", kwargs={"slug": slug})

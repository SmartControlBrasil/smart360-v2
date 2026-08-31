from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe

register = template.Library()

VENDOR_STYLES = {
    "swiper": "institutional/css/plugins/swiper.min.css",
    "wow": "institutional/css/vendor/animate.min.css",
    "odometer": "institutional/css/vendor/odometer.min.css",
}

VENDOR_SCRIPTS = {
    "swiper": ("institutional/js/plugins/swiper.min.js",),
    "wow": ("institutional/js/plugins/wow.js",),
    "odometer": (
        "institutional/js/plugins/waypoints.min.js",
        "institutional/js/vendor/odometer.min.js",
    ),
    "vanilla_tilt": ("institutional/js/vendor/vanilla-tilt.js",),
}


def _render_links(paths):
    tags = []
    for path in paths:
        href = static(path)
        tags.append(f'<link rel="stylesheet" href="{href}">')
    return mark_safe("\n    ".join(tags))


def _render_deferred_links(paths):
    tags = []
    for path in paths:
        href = static(path)
        tags.append(
            f'<link rel="preload" href="{href}" as="style" '
            f"onload=\"this.onload=null;this.rel='stylesheet'\">"
        )
        tags.append(f'<noscript><link rel="stylesheet" href="{href}"></noscript>')
    return mark_safe("\n    ".join(tags))


def _render_scripts(paths):
    tags = []
    for path in paths:
        src = static(path)
        tags.append(f'<script defer src="{src}"></script>')
    return mark_safe("\n    ".join(tags))


@register.simple_tag
def vendor_styles(*names):
    paths = []
    for name in names:
        path = VENDOR_STYLES.get(name)
        if path:
            paths.append(path)
    return _render_links(paths)


@register.simple_tag
def deferred_stylesheet(*paths):
    return _render_deferred_links(paths)


@register.simple_tag
def vendor_scripts(*names):
    paths = []
    for name in names:
        paths.extend(VENDOR_SCRIPTS.get(name, ()))
    return _render_scripts(paths)

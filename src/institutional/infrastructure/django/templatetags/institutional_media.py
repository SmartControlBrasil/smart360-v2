from django import template
from django.templatetags.static import static

from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

from src.institutional.presentation.static_image_registry import STATIC_IMAGE_DIMENSIONS

register = template.Library()

INSTITUTIONAL_ICON_NAMES = {
    "brain",
    "calendar",
    "check",
    "close",
    "database",
    "down-arrow",
    "email",
    "eye",
    "facebook",
    "growth",
    "home-button",
    "instagram",
    "minus",
    "monitor",
    "next",
    "paper-plane",
    "pause",
    "phone-call",
    "play",
    "programming",
    "settings",
    "sign",
    "star",
    "tag",
    "top",
    "trolley",
    "web",
    "youtube",
}



@register.simple_tag
def image_dimensions(image_path):
    dimensions = STATIC_IMAGE_DIMENSIONS.get(image_path)
    if not dimensions:
        return ""
    width, height = dimensions
    return mark_safe(f'width="{width}" height="{height}"')


@register.simple_tag
def image_size(image_path):
    return STATIC_IMAGE_DIMENSIONS.get(image_path, (None, None))

@register.simple_tag
def institutional_icon(name, class_name="", **attrs):
    if name not in INSTITUTIONAL_ICON_NAMES:
        return ""

    css_class = attrs.pop("class", "")
    classes = " ".join(
        class_part
        for class_part in ("site-icon", class_name, css_class)
        if class_part
    )
    src = static(f"institutional/icons/{name}.svg")
    attr_html = "".join(
        f' {conditional_escape(key).replace("_", "-")}="{conditional_escape(value)}"'
        for key, value in attrs.items()
        if value is not None
    )

    return format_html(
        '<img src="{}" alt="" aria-hidden="true" class="{}"{}>',
        src,
        classes,
        mark_safe(attr_html),
    )

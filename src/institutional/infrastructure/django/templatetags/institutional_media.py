from django import template
from django.templatetags.static import static

from django.utils.safestring import mark_safe

from src.institutional.presentation.static_image_registry import STATIC_IMAGE_DIMENSIONS

register = template.Library()


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

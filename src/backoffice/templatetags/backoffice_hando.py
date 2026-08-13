from django import forms
from django import template

register = template.Library()


def _apply_hando_classes(form):
    for field in form.visible_fields():
        widget = field.field.widget
        existing = widget.attrs.get("class", "")
        if isinstance(widget, forms.CheckboxInput):
            css_class = "form-check-input"
        elif isinstance(widget, forms.FileInput):
            css_class = "form-control"
        elif isinstance(widget, forms.Select):
            css_class = "form-select"
        else:
            css_class = "form-control"
        if css_class not in existing.split():
            widget.attrs["class"] = f"{existing} {css_class}".strip()


@register.inclusion_tag("backoffice/erp/partials/form_fields.html")
def backoffice_form_fields(form):
    _apply_hando_classes(form)
    widths = getattr(form, "field_widths", None) or {}
    get_width = getattr(form, "get_field_width", None)
    items = []
    for field in form.visible_fields():
        if callable(get_width):
            col = get_width(field.name)
        else:
            col = widths.get(field.name, "col-12")
        items.append({"field": field, "col": col or "col-12"})
    return {
        "form": form,
        "items": items,
        "hidden_fields": form.hidden_fields(),
    }

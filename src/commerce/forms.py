from django import forms

from src.commerce.models import Brand
from src.commerce.models import Category
from src.commerce.models import Product
from src.commerce.models import ProductImage


def apply_hando_class(fields):
    for field in fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            css = "form-check-input"
        elif isinstance(widget, forms.Select):
            css = "form-select"
        else:
            css = "form-control"
        existing = widget.attrs.get("class", "")
        widget.attrs["class"] = f"{existing} {css}".strip()


class ProductBackofficeForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name", "slug", "sku", "category", "brand",
            "sale_mode", "show_price", "price", "availability",
            "short_description", "description", "featured", "active",
            "seo_title", "seo_description",
        ]
        widgets = {
            "short_description": forms.Textarea(attrs={"rows": 3}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_hando_class(self.fields)


class CategoryBackofficeForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "description", "active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_hando_class(self.fields)


class BrandBackofficeForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "slug", "description", "logo", "active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_hando_class(self.fields)


class ProductImageBackofficeForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "position", "is_primary"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_hando_class(self.fields)

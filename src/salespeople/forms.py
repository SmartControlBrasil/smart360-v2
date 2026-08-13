from django import forms
from django.contrib.auth import get_user_model

from src.salespeople.models import Salesperson


class SalespersonForm(forms.ModelForm):
    class Meta:
        model = Salesperson
        fields = ["user", "code", "name", "email", "phone", "whatsapp", "active", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        linked_users = Salesperson.objects.exclude(user__isnull=True)
        if self.instance.pk and self.instance.user_id:
            linked_users = linked_users.exclude(pk=self.instance.pk)
        self.fields["user"].queryset = user_model.objects.exclude(
            pk__in=linked_users.values_list("user_id", flat=True),
        ).order_by("username")
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css}".strip()

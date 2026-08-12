from django import forms

from src.customers.models import Customer
from src.customers.models import only_digits
from src.salespeople.models import Salesperson


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "customer_type", "legal_name", "trade_name", "document", "state_registration",
            "email", "phone", "whatsapp", "website",
            "postal_code", "address_line", "address_number", "address_extra", "district", "city", "state",
            "assigned_salesperson", "status", "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, lock_salesperson=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.lock_salesperson = lock_salesperson
        self.fields["assigned_salesperson"].queryset = Salesperson.objects.order_by("name")
        if lock_salesperson:
            try:
                salesperson = user.salesperson_profile
            except Exception:
                salesperson = None
            self.fields["assigned_salesperson"].queryset = Salesperson.objects.filter(pk=getattr(salesperson, "pk", None))
            self.fields["assigned_salesperson"].initial = salesperson
            self.fields["assigned_salesperson"].disabled = True
        for field in self.fields.values():
            css = "bo-input"
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {css}".strip()

    def clean_document(self):
        value = only_digits(self.cleaned_data.get("document") or "")
        return value or None

    def clean(self):
        cleaned = super().clean()
        if self.lock_salesperson:
            try:
                cleaned["assigned_salesperson"] = self.user.salesperson_profile
            except Exception:
                cleaned["assigned_salesperson"] = None
        return cleaned

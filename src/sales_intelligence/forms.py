from django import forms

from src.sales_intelligence.models import ProspectingCampaign
from src.sales_intelligence.models import SearchRun


class ProspectingCampaignForm(forms.ModelForm):
    class Meta:
        model = ProspectingCampaign
        fields = ["name", "product", "market_segment", "location_description", "objective", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()


class SearchRunForm(forms.Form):
    query = forms.CharField(label="Query", max_length=180)
    location = forms.CharField(label="Localização", max_length=180, required=False)
    source = forms.ChoiceField(label="Fonte", choices=SearchRun.Source.choices, initial=SearchRun.Source.GOOGLE_MAPS)
    requested_limit = forms.IntegerField(label="Limite desejado", min_value=1, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

from django import forms


class ContactForm(forms.Form):
    nome = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    telefone = forms.CharField(required=True)
    empresa = forms.CharField(required=False)
    assunto = forms.CharField(required=True)
    mensagem = forms.CharField(required=True)
    aceite_privacidade = forms.BooleanField(required=True)
    website = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        for field in ("nome", "telefone", "empresa", "assunto", "mensagem", "website"):
            value = cleaned_data.get(field)
            if isinstance(value, str):
                cleaned_data[field] = value.strip()
        return cleaned_data

    def clean_website(self):
        website = self.cleaned_data.get("website", "").strip()
        if website:
            raise forms.ValidationError("Mensagem nao enviada.")
        return website


class NewsletterSubscribeForm(forms.Form):
    email = forms.EmailField(required=True)
    website = forms.CharField(required=False)

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise forms.ValidationError("E-mail obrigatorio.")
        return email

    def clean_website(self):
        website = self.cleaned_data.get("website", "").strip()
        if website:
            raise forms.ValidationError("Solicitacao invalida.")
        return website


from django import forms
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import get_password_validators
from django.contrib.auth.views import PasswordChangeView
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils import translation
from django.utils.html import format_html, format_html_join

from src.backoffice.models import TemporaryCredential


class TemporaryCredentialMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            credential = TemporaryCredential.objects.filter(user=request.user, must_change=True).first()
            if credential:
                if credential.expires_at <= timezone.now():
                    logout(request)
                    return HttpResponseForbidden("Senha temporária expirada. Solicite uma nova credencial.")
                if request.path not in (str(reverse_lazy("backoffice:password_change")), str(reverse_lazy("institutional:logout"))):
                    return redirect("backoffice:password_change")
        return self.get_response(request)


class SellerPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        with translation.override("pt-br"):
            super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Senha atual"
        self.fields["new_password1"].label = "Nova senha"
        self.fields["new_password2"].label = "Confirmar nova senha"
        self.fields["old_password"].error_messages.update(
            {
                "required": "Informe a senha atual.",
            }
        )
        self.fields["new_password1"].error_messages.update(
            {
                "required": "Informe a nova senha.",
            }
        )
        self.fields["new_password2"].error_messages.update(
            {
                "required": "Confirme a nova senha.",
            }
        )
        with translation.override("pt-br"):
            help_lines = [
                validator.get_help_text()
                for validator in get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)
            ]
        self.fields["new_password1"].help_text = format_html(
            "<ul>{}</ul>",
            format_html_join("", "<li>{}</li>", ((line,) for line in help_lines)),
        )
        self.fields["new_password2"].help_text = "Digite a mesma senha novamente, para confirmação."
        self.field_widths = {
            "old_password": "col-12 col-lg-6",
            "new_password1": "col-12 col-md-6",
            "new_password2": "col-12 col-md-6",
        }

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if old_password and not self.user.check_password(old_password):
            raise forms.ValidationError(
                "A senha atual está incorreta. Informe-a novamente.",
                code="password_incorrect",
            )
        return old_password

    def clean(self):
        password = self.cleaned_data.get("new_password1")
        if password and self.user.check_password(password):
            self.add_error("new_password1", "Escolha uma senha diferente da senha atual.")
            return self.cleaned_data
        with translation.override("pt-br"):
            return PasswordChangeForm.clean(self)


class SellerPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    login_url = reverse_lazy("institutional:login")
    form_class = SellerPasswordChangeForm
    template_name = "backoffice/password_change.html"
    success_url = reverse_lazy("backoffice:dashboard")

    def render_to_response(self, context, **response_kwargs):
        with translation.override("pt-br"):
            return super().render_to_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Defina sua senha pessoal",
                "submit_label": "Salvar senha",
                "hide_cancel": True,
            }
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        TemporaryCredential.objects.filter(user=self.request.user).update(must_change=False)
        return response

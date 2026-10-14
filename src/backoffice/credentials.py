from django import forms
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import get_password_validators
from django.contrib.auth.views import PasswordChangeView
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse_lazy
from django.utils import timezone
from django.utils import translation
from django.utils.html import format_html, format_html_join

from src.backoffice.models import TemporaryCredential

MANDATORY_PASSWORD_CHANGE_VIEWS = frozenset(
    {
        "backoffice:password_change",
        "institutional:logout",
    }
)


def _allows_mandatory_password_change_navigation(request):
    try:
        return resolve(request.path_info).view_name in MANDATORY_PASSWORD_CHANGE_VIEWS
    except Resolver404:
        return False


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
                if not _allows_mandatory_password_change_navigation(request):
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
            '<details class="password-requirements"><summary>Requisitos da nova senha</summary><ul class="mb-0 mt-2">{}</ul></details>',
            format_html_join("", "<li>{}</li>", ((line,) for line in help_lines)),
        )
        self.fields["new_password2"].help_text = "Digite a mesma senha novamente, para confirmação."
        self.field_widths = {
            "old_password": "col-12 col-lg-6",
            "new_password1": "col-12 col-md-6",
            "new_password2": "col-12 col-md-6",
        }

    def clean_old_password(self):
        try:
            with translation.override("pt-br"):
                return super().clean_old_password()
        except forms.ValidationError as exc:
            if exc.code == "password_incorrect":
                raise forms.ValidationError(
                    "A senha atual está incorreta. Informe-a novamente.",
                    code="password_incorrect",
                ) from exc
            raise

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
                "password_change_layout": True,
            }
        )
        return context

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Não foi possível salvar a senha. Confira os avisos abaixo e tente novamente.",
        )
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        TemporaryCredential.objects.filter(user=self.request.user).update(must_change=False)
        messages.success(self.request, "Senha atualizada com sucesso. Bem-vindo ao painel comercial.")
        return response

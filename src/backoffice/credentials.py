from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import logout
from django.contrib.auth.views import PasswordChangeView
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone

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
    def clean_new_password1(self):
        password = self.cleaned_data["new_password1"]
        if self.user.check_password(password):
            raise forms.ValidationError("Escolha uma senha diferente da senha atual.")
        return password


class SellerPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    login_url = reverse_lazy("institutional:login")
    form_class = SellerPasswordChangeForm
    template_name = "backoffice/password_change.html"
    success_url = reverse_lazy("backoffice:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        TemporaryCredential.objects.filter(user=self.request.user).update(must_change=False)
        return response

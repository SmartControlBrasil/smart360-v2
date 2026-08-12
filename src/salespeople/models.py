from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Salesperson(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="salesperson_profile",
    )
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "vendedor"
        verbose_name_plural = "vendedores"

    def __str__(self):
        return self.name

    def clean(self):
        if self.user_id and self.active:
            duplicate = Salesperson.objects.filter(user_id=self.user_id, active=True)
            if self.pk:
                duplicate = duplicate.exclude(pk=self.pk)
            if duplicate.exists():
                raise ValidationError({"user": "Este usuário já possui um vendedor ativo vinculado."})

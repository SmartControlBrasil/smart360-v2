from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


DEFAULT_BUSINESS_UNIT_CODE = "SMART_CONTROL"
DEFAULT_BUSINESS_UNIT_NAME = "Smart Control Brasil"
DEFAULT_BUSINESS_UNIT_SLUG = "smart-control"


class AccessScope(models.TextChoices):
    ALL = "ALL", "Todos"
    DEPARTMENT = "DEPARTMENT", "Departamento"
    TEAM = "TEAM", "Equipe"
    OWN = "OWN", "Próprios"
    NONE = "NONE", "Nenhum"


class BusinessUnit(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "unidade de negócio"
        verbose_name_plural = "unidades de negócio"

    def __str__(self):
        return self.name


class Department(models.Model):
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT,
        related_name="departments",
    )
    name = models.CharField(max_length=140)
    code = models.CharField(max_length=40)
    slug = models.SlugField(max_length=160)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["business_unit__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["business_unit", "code"], name="unique_department_code_per_business_unit"),
            models.UniqueConstraint(fields=["business_unit", "slug"], name="unique_department_slug_per_business_unit"),
        ]
        verbose_name = "departamento"
        verbose_name_plural = "departamentos"

    def __str__(self):
        return f"{self.name} · {self.business_unit}"


class Team(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="teams",
    )
    name = models.CharField(max_length=140)
    code = models.CharField(max_length=40)
    slug = models.SlugField(max_length=160)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department__business_unit__name", "department__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["department", "code"], name="unique_team_code_per_department"),
            models.UniqueConstraint(fields=["department", "slug"], name="unique_team_slug_per_department"),
        ]
        verbose_name = "equipe"
        verbose_name_plural = "equipes"

    def __str__(self):
        return f"{self.name} · {self.department}"


class BusinessUnitMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_unit_memberships",
    )
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    team = models.ForeignKey(
        Team,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    scope = models.CharField(max_length=20, choices=AccessScope.choices, default=AccessScope.OWN)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["business_unit__name", "user__username"]
        constraints = [
            models.UniqueConstraint(fields=["user", "business_unit"], name="unique_business_unit_membership"),
        ]
        verbose_name = "membership de unidade de negócio"
        verbose_name_plural = "memberships de unidades de negócio"

    def __str__(self):
        return f"{self.user} · {self.business_unit} · {self.scope}"

    def clean(self):
        errors = {}
        if self.department_id and self.business_unit_id and self.department.business_unit_id != self.business_unit_id:
            errors["department"] = "O departamento precisa pertencer à mesma unidade de negócio."
        if self.team_id:
            if self.department_id and self.team.department_id != self.department_id:
                errors["team"] = "A equipe precisa pertencer ao departamento selecionado."
            if self.business_unit_id and self.team.department.business_unit_id != self.business_unit_id:
                errors["team"] = "A equipe precisa pertencer à mesma unidade de negócio."
        if self.scope == AccessScope.DEPARTMENT and not self.department_id:
            errors["department"] = "Membership com escopo Departamento exige departamento."
        if self.scope == AccessScope.TEAM and not self.team_id:
            errors["team"] = "Membership com escopo Equipe exige equipe."
        if self.scope == AccessScope.TEAM and self.team_id and not self.department_id:
            errors["department"] = "Membership com escopo Equipe exige departamento."
        if errors:
            raise ValidationError(errors)


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN_SUCCESS = "LOGIN_SUCCESS", "Login realizado"
        LOGIN_FAILED = "LOGIN_FAILED", "Falha de login"
        LOGOUT = "LOGOUT", "Logout"
        CREATE = "CREATE", "Criação"
        UPDATE = "UPDATE", "Atualização"
        DELETE = "DELETE", "Exclusão"
        ACTIVATE = "ACTIVATE", "Ativação"
        DEACTIVATE = "DEACTIVATE", "Desativação"
        PUBLISH = "PUBLISH", "Publicação"
        UNPUBLISH = "UNPUBLISH", "Despublicação"
        PERMISSION_CHANGED = "PERMISSION_CHANGED", "Permissão alterada"
        ROLE_CHANGED = "ROLE_CHANGED", "Papel alterado"

    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="backoffice_audit_logs",
    )
    action = models.CharField(max_length=40, choices=Action.choices, db_index=True)
    module = models.CharField(max_length=80, db_index=True)
    object_type = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=120, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp", "-id"]
        verbose_name = "registro de auditoria"
        verbose_name_plural = "registros de auditoria"

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} {self.module}.{self.action}"

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("Registros de auditoria são append-only e não podem ser alterados.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Registros de auditoria não podem ser excluídos pela aplicação.")

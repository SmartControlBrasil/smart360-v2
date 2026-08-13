from django import forms
from django.contrib.auth import get_user_model

from src.backoffice.models import AccessScope
from src.backoffice.models import BusinessUnit
from src.backoffice.models import BusinessUnitMembership
from src.backoffice.models import Department
from src.backoffice.models import Team


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


class RestrictedScopeChoiceField(forms.ChoiceField):
    def valid_value(self, value):
        return value in {choice[0] for choice in AccessScope.choices}


class BusinessUnitForm(forms.ModelForm):
    class Meta:
        model = BusinessUnit
        fields = ["name", "code", "slug", "is_active"]
        labels = {
            "name": "Nome",
            "code": "Código",
            "slug": "Slug",
            "is_active": "Ativa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_hando_class(self.fields)
        self.fields["code"].help_text = "Identificador interno único da unidade."
        self.fields["slug"].help_text = "Usado em integrações e relatórios internos."

    def clean_code(self):
        return (self.cleaned_data.get("code") or "").strip().upper()

    def clean_slug(self):
        return (self.cleaned_data.get("slug") or "").strip().lower()

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get("code")
        slug = cleaned.get("slug")
        if code:
            duplicate_code = BusinessUnit.objects.filter(code=code)
            if self.instance.pk:
                duplicate_code = duplicate_code.exclude(pk=self.instance.pk)
            if duplicate_code.exists():
                self.add_error("code", "Já existe uma unidade com este código.")
        if slug:
            duplicate_slug = BusinessUnit.objects.filter(slug=slug)
            if self.instance.pk:
                duplicate_slug = duplicate_slug.exclude(pk=self.instance.pk)
            if duplicate_slug.exists():
                self.add_error("slug", "Já existe uma unidade com este slug.")
        return cleaned


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["business_unit", "name", "code", "slug", "is_active"]
        labels = {
            "business_unit": "Unidade de negócio",
            "name": "Nome",
            "code": "Código",
            "slug": "Slug",
            "is_active": "Ativo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["business_unit"].queryset = BusinessUnit.objects.order_by("name")
        apply_hando_class(self.fields)

    def clean_code(self):
        return (self.cleaned_data.get("code") or "").strip().upper()

    def clean_slug(self):
        return (self.cleaned_data.get("slug") or "").strip().lower()

    def clean(self):
        cleaned = super().clean()
        business_unit = cleaned.get("business_unit")
        code = cleaned.get("code")
        slug = cleaned.get("slug")
        if business_unit and code:
            duplicate_code = Department.objects.filter(business_unit=business_unit, code=code)
            if self.instance.pk:
                duplicate_code = duplicate_code.exclude(pk=self.instance.pk)
            if duplicate_code.exists():
                self.add_error("code", "Já existe um departamento com este código nesta unidade.")
        if business_unit and slug:
            duplicate_slug = Department.objects.filter(business_unit=business_unit, slug=slug)
            if self.instance.pk:
                duplicate_slug = duplicate_slug.exclude(pk=self.instance.pk)
            if duplicate_slug.exists():
                self.add_error("slug", "Já existe um departamento com este slug nesta unidade.")
        return cleaned


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["department", "name", "code", "slug", "is_active"]
        labels = {
            "department": "Departamento",
            "name": "Nome",
            "code": "Código",
            "slug": "Slug",
            "is_active": "Ativo",
        }

    def __init__(self, *args, business_unit=None, **kwargs):
        super().__init__(*args, **kwargs)
        departments = Department.objects.select_related("business_unit").order_by("business_unit__name", "name")
        if business_unit:
            departments = departments.filter(business_unit=business_unit)
        self.fields["department"].queryset = departments
        apply_hando_class(self.fields)

    def clean_code(self):
        return (self.cleaned_data.get("code") or "").strip().upper()

    def clean_slug(self):
        return (self.cleaned_data.get("slug") or "").strip().lower()

    def clean(self):
        cleaned = super().clean()
        department = cleaned.get("department")
        code = cleaned.get("code")
        slug = cleaned.get("slug")
        if department and code:
            duplicate_code = Team.objects.filter(department=department, code=code)
            if self.instance.pk:
                duplicate_code = duplicate_code.exclude(pk=self.instance.pk)
            if duplicate_code.exists():
                self.add_error("code", "Já existe uma equipe com este código neste departamento.")
        if department and slug:
            duplicate_slug = Team.objects.filter(department=department, slug=slug)
            if self.instance.pk:
                duplicate_slug = duplicate_slug.exclude(pk=self.instance.pk)
            if duplicate_slug.exists():
                self.add_error("slug", "Já existe uma equipe com este slug neste departamento.")
        return cleaned


class BusinessUnitMembershipForm(forms.ModelForm):
    SUPPORTED_SCOPE_CHOICES = (
        (AccessScope.ALL, "Todos da unidade"),
        (AccessScope.DEPARTMENT, "Departamento"),
        (AccessScope.TEAM, "Equipe"),
        (AccessScope.OWN, "Somente próprios"),
        (AccessScope.NONE, "Sem acesso"),
    )

    scope = RestrictedScopeChoiceField(choices=SUPPORTED_SCOPE_CHOICES)

    class Meta:
        model = BusinessUnitMembership
        fields = ["user", "business_unit", "department", "team", "scope", "is_active"]
        labels = {
            "user": "Usuário",
            "business_unit": "Unidade de negócio",
            "department": "Departamento",
            "team": "Equipe",
            "scope": "Acesso aos dados",
            "is_active": "Ativo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        self.fields["user"].queryset = user_model.objects.filter(is_active=True).order_by("username")
        self.fields["business_unit"].queryset = BusinessUnit.objects.order_by("name")
        business_unit_id = self.data.get("business_unit") or getattr(self.instance, "business_unit_id", None)
        departments = Department.objects.select_related("business_unit").order_by("business_unit__name", "name")
        if business_unit_id:
            departments = departments.filter(business_unit_id=business_unit_id)
        self.fields["department"].queryset = departments
        department_id = self.data.get("department") or getattr(self.instance, "department_id", None)
        teams = Team.objects.select_related("department", "department__business_unit").order_by("department__business_unit__name", "department__name", "name")
        if department_id:
            teams = teams.filter(department_id=department_id)
        elif business_unit_id:
            teams = teams.filter(department__business_unit_id=business_unit_id)
        self.fields["team"].queryset = teams
        self.fields["scope"].choices = self.SUPPORTED_SCOPE_CHOICES
        apply_hando_class(self.fields)

    def clean_scope(self):
        scope = self.cleaned_data.get("scope")
        supported = {choice[0] for choice in self.SUPPORTED_SCOPE_CHOICES}
        if scope not in supported:
            raise forms.ValidationError("Selecione um escopo disponível para esta fase.")
        return scope

    def clean(self):
        cleaned = super().clean()
        user = cleaned.get("user")
        business_unit = cleaned.get("business_unit")
        department = cleaned.get("department")
        team = cleaned.get("team")
        scope = cleaned.get("scope")
        if scope in {AccessScope.ALL, AccessScope.OWN, AccessScope.NONE}:
            cleaned["department"] = None
            cleaned["team"] = None
            department = None
            team = None
        if scope == AccessScope.DEPARTMENT and not department:
            self.add_error("department", "Membership com escopo Departamento exige departamento.")
        if scope == AccessScope.TEAM and not team:
            self.add_error("team", "Membership com escopo Equipe exige equipe.")
        if scope == AccessScope.TEAM and not department:
            self.add_error("department", "Membership com escopo Equipe exige departamento.")
        if department and business_unit and department.business_unit_id != business_unit.pk:
            self.add_error("department", "O departamento precisa pertencer à unidade selecionada.")
        if team and department and team.department_id != department.pk:
            self.add_error("team", "A equipe precisa pertencer ao departamento selecionado.")
        if team and business_unit and team.department.business_unit_id != business_unit.pk:
            self.add_error("team", "A equipe precisa pertencer à unidade selecionada.")
        if user and business_unit:
            duplicate = BusinessUnitMembership.objects.filter(user=user, business_unit=business_unit)
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise forms.ValidationError("Este usuário já possui acesso configurado para esta unidade.")
        return cleaned

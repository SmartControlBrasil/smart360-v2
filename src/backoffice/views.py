from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from src.backoffice.forms import BusinessUnitForm
from src.backoffice.forms import BusinessUnitMembershipForm
from src.backoffice.forms import DepartmentForm
from src.backoffice.forms import TeamForm
from src.backoffice.models import AuditLog
from src.backoffice.models import BusinessUnit
from src.backoffice.models import BusinessUnitMembership
from src.backoffice.models import Department
from src.backoffice.models import Team
from src.backoffice.permissions.registry import BackofficePermission
from src.backoffice.permissions.services import user_has_backoffice_permission
from src.backoffice.services.scopes import apply_customer_scope
from src.backoffice.services.scopes import has_active_business_unit_memberships
from src.backoffice.services.scopes import user_can_manage_customers
from src.backoffice.services.scopes import user_can_manage_salespeople
from src.backoffice.services.scopes import user_is_salesperson_role
from src.backoffice.services.governance import create_business_unit
from src.backoffice.services.governance import create_department
from src.backoffice.services.governance import create_membership
from src.backoffice.services.governance import create_team
from src.backoffice.services.governance import update_business_unit
from src.backoffice.services.governance import update_department
from src.backoffice.services.governance import update_membership
from src.backoffice.services.governance import update_team
from src.backoffice.services.governance import visible_customer_relationships_for_user
from src.commerce.forms import BrandBackofficeForm
from src.commerce.forms import CategoryBackofficeForm
from src.commerce.forms import ProductBackofficeForm
from src.commerce.forms import ProductImageBackofficeForm
from src.commerce.models import Brand
from src.commerce.models import Category
from src.commerce.models import Product
from src.commerce.models import ProductImage
from src.commerce.services import create_brand
from src.commerce.services import create_category
from src.commerce.services import create_product
from src.commerce.services import create_product_image
from src.commerce.services import delete_product_image
from src.commerce.services import set_product_active
from src.commerce.services import set_product_featured
from src.commerce.services import update_brand
from src.commerce.services import update_category
from src.commerce.services import update_product
from src.customers.forms import CustomerAssignmentTransferForm
from src.customers.forms import CustomerForm
from src.customers.models import Customer
from src.customers.models import CustomerAssignmentTransfer
from src.customers.models import CustomerBusinessRelationship
from src.customers.services import create_customer
from src.customers.services import transfer_customer_relationship
from src.customers.services import user_can_transfer_customer_relationship
from src.customers.services import valid_salespeople_for_relationship
from src.customers.services import update_customer
from src.salespeople.forms import SalespersonForm
from src.salespeople.models import Salesperson
from src.salespeople.services import create_salesperson
from src.salespeople.services import update_salesperson


def backoffice_permission_required(permission):
    def decorator(view_func):
        @login_required(login_url="institutional:login")
        def wrapper(request, *args, **kwargs):
            if not user_has_backoffice_permission(request.user, permission):
                return render(request, "backoffice/403.html", status=403)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


@backoffice_permission_required(BackofficePermission.DASHBOARD_VIEW)
def dashboard(request):
    scoped_customers = apply_customer_scope(Customer.objects.all(), request.user)
    cards = [
        {"label": "Clientes cadastrados", "value": scoped_customers.count(), "icon": "users", "color": "primary"},
        {"label": "Clientes ativos", "value": scoped_customers.filter(status=Customer.Status.ACTIVE).count(), "icon": "user-check", "color": "success"},
        {"label": "Vendedores ativos", "value": Salesperson.objects.filter(active=True).count(), "icon": "briefcase", "color": "info"},
        {"label": "Produtos cadastrados", "value": Product.objects.count(), "icon": "box", "color": "warning"},
        {"label": "Produtos publicados", "value": Product.objects.filter(active=True, category__active=True).count(), "icon": "shopping-bag", "color": "success"},
        {"label": "Categorias", "value": Category.objects.count(), "icon": "grid", "color": "secondary"},
        {"label": "Marcas", "value": Brand.objects.count(), "icon": "tag", "color": "primary"},
    ]
    recent_logins = AuditLog.objects.filter(
        action__in=[AuditLog.Action.LOGIN_SUCCESS, AuditLog.Action.LOGIN_FAILED, AuditLog.Action.LOGOUT],
    )[:6]
    recent_activities = AuditLog.objects.all()[:8]
    return render(
        request,
        "backoffice/dashboard.html",
        {
            "cards": cards,
            "recent_logins": recent_logins,
            "recent_activities": recent_activities,
        },
    )


@backoffice_permission_required(BackofficePermission.CUSTOMERS_VIEW)
def customer_list(request):
    customers = apply_customer_scope(
        Customer.objects.select_related("assigned_salesperson").order_by("legal_name"),
        request.user,
    )
    query = request.GET.get("q", "").strip()
    if query:
        customers = customers.filter(
            Q(legal_name__icontains=query)
            | Q(trade_name__icontains=query)
            | Q(document__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(whatsapp__icontains=query),
        )
    status = request.GET.get("status", "")
    if status:
        customers = customers.filter(status=status)
    customer_type = request.GET.get("type", "")
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
    salesperson_id = request.GET.get("salesperson", "")
    if salesperson_id:
        customers = customers.filter(business_relationships__assigned_salesperson_id=salesperson_id).distinct()
    business_unit_id = request.GET.get("business_unit", "")
    if business_unit_id:
        customers = customers.filter(business_relationships__business_unit_id=business_unit_id).distinct()
    active_business_units = BusinessUnit.objects.filter(is_active=True).order_by("name")
    show_business_unit_filter = active_business_units.count() > 1 or bool(business_unit_id)
    return render(
        request,
        "backoffice/customers/list.html",
        {
            "customers": customers,
            "query": query,
            "status": status,
            "customer_type": customer_type,
            "salesperson_id": salesperson_id,
            "salespeople": Salesperson.objects.order_by("name"),
            "business_units": active_business_units,
            "business_unit_id": business_unit_id,
            "show_business_unit_filter": show_business_unit_filter,
            "customer_statuses": Customer.Status.choices,
            "customer_types": Customer.CustomerType.choices,
            "can_manage": user_can_manage_customers(request.user),
        },
    )


@backoffice_permission_required(BackofficePermission.CUSTOMERS_VIEW)
def customer_detail(request, pk):
    customer = get_object_or_404(
        apply_customer_scope(Customer.objects.select_related("assigned_salesperson", "created_by", "updated_by"), request.user),
        pk=pk,
    )
    history = AuditLog.objects.filter(module="customers", object_type="Customer", object_id=str(customer.pk))[:20]
    relationships = visible_customer_relationships_for_user(customer=customer, user=request.user)
    transfer_history = CustomerAssignmentTransfer.objects.select_related(
        "relationship",
        "relationship__business_unit",
        "previous_salesperson",
        "new_salesperson",
        "transferred_by",
    ).filter(relationship__customer=customer, relationship__in=relationships)[:20]
    return render(
        request,
        "backoffice/customers/detail.html",
        {
            "customer": customer,
            "history": history,
            "relationships": relationships,
            "transfer_history": transfer_history,
            "can_transfer_assignment": user_has_backoffice_permission(request.user, BackofficePermission.CUSTOMERS_TRANSFER_ASSIGNMENT),
            "can_manage": user_can_manage_customers(request.user),
        },
    )


@backoffice_permission_required(BackofficePermission.CUSTOMERS_TRANSFER_ASSIGNMENT)
def customer_relationship_transfer(request, pk, relationship_pk):
    customer = get_object_or_404(apply_customer_scope(Customer.objects.all(), request.user), pk=pk)
    relationship = get_object_or_404(
        visible_customer_relationships_for_user(customer=customer, user=request.user),
        pk=relationship_pk,
    )
    if not user_can_transfer_customer_relationship(user=request.user, relationship=relationship):
        return render(request, "backoffice/403.html", status=403)
    valid_salespeople = valid_salespeople_for_relationship(relationship).exclude(pk=relationship.assigned_salesperson_id)
    form = CustomerAssignmentTransferForm(request.POST or None, valid_salespeople=valid_salespeople)
    if request.method == "POST" and form.is_valid():
        try:
            transfer_customer_relationship(
                relationship=relationship,
                new_salesperson=form.cleaned_data["new_salesperson"],
                actor=request.user,
                reason=form.cleaned_data["reason"],
                request=request,
            )
        except PermissionDenied:
            return render(request, "backoffice/403.html", status=403)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Responsável transferido com sucesso.")
            return redirect("backoffice:customer_detail", pk=customer.pk)
    return render(
        request,
        "backoffice/customers/transfer.html",
        {
            "form": form,
            "customer": customer,
            "relationship": relationship,
            "title": "Transferir responsável",
        },
    )


@backoffice_permission_required(BackofficePermission.CUSTOMERS_CREATE)
def customer_create(request):
    if user_is_salesperson_role(request.user) and not has_active_business_unit_memberships(request.user):
        return render(request, "backoffice/403.html", status=403)
    form = CustomerForm(
        request.POST or None,
        user=request.user,
        lock_salesperson=user_is_salesperson_role(request.user),
    )
    if request.method == "POST" and form.is_valid():
        customer = create_customer(form=form, request=request)
        return redirect("backoffice:customer_detail", pk=customer.pk)
    return render(request, "backoffice/customers/form.html", {"form": form, "title": "Novo cliente"})


@backoffice_permission_required(BackofficePermission.CUSTOMERS_UPDATE)
def customer_update(request, pk):
    customer = get_object_or_404(apply_customer_scope(Customer.objects.all(), request.user), pk=pk)
    form = CustomerForm(
        request.POST or None,
        instance=customer,
        user=request.user,
        lock_salesperson=user_is_salesperson_role(request.user),
    )
    if request.method == "POST" and form.is_valid():
        customer = update_customer(customer=customer, form=form, request=request)
        return redirect("backoffice:customer_detail", pk=customer.pk)
    return render(request, "backoffice/customers/form.html", {"form": form, "customer": customer, "title": "Editar cliente"})


@backoffice_permission_required(BackofficePermission.SALESPEOPLE_VIEW)
def salesperson_list(request):
    salespeople = Salesperson.objects.select_related("user").annotate(customer_count=Count("customers")).order_by("name")
    query = request.GET.get("q", "").strip()
    if query:
        salespeople = salespeople.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(email__icontains=query))
    active = request.GET.get("active", "")
    if active == "1":
        salespeople = salespeople.filter(active=True)
    elif active == "0":
        salespeople = salespeople.filter(active=False)
    return render(
        request,
        "backoffice/salespeople/list.html",
        {
            "salespeople": salespeople,
            "query": query,
            "active": active,
            "can_manage": user_can_manage_salespeople(request.user),
        },
    )


@backoffice_permission_required(BackofficePermission.SALESPEOPLE_VIEW)
def salesperson_detail(request, pk):
    salesperson = get_object_or_404(
        Salesperson.objects.select_related("user").annotate(customer_count=Count("customers")),
        pk=pk,
    )
    history = AuditLog.objects.filter(module="salespeople", object_type="Salesperson", object_id=str(salesperson.pk))[:20]
    return render(
        request,
        "backoffice/salespeople/detail.html",
        {"salesperson": salesperson, "history": history, "can_manage": user_can_manage_salespeople(request.user)},
    )


@backoffice_permission_required(BackofficePermission.SALESPEOPLE_MANAGE)
def salesperson_create(request):
    form = SalespersonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        salesperson = create_salesperson(form=form, request=request)
        return redirect("backoffice:salesperson_detail", pk=salesperson.pk)
    return render(request, "backoffice/salespeople/form.html", {"form": form, "title": "Novo vendedor"})


@backoffice_permission_required(BackofficePermission.SALESPEOPLE_MANAGE)
def salesperson_update(request, pk):
    salesperson = get_object_or_404(Salesperson, pk=pk)
    form = SalespersonForm(request.POST or None, instance=salesperson)
    if request.method == "POST" and form.is_valid():
        salesperson = update_salesperson(salesperson=salesperson, form=form, request=request)
        return redirect("backoffice:salesperson_detail", pk=salesperson.pk)
    return render(request, "backoffice/salespeople/form.html", {"form": form, "salesperson": salesperson, "title": "Editar vendedor"})


@backoffice_permission_required(BackofficePermission.COMMERCE_PRODUCTS_VIEW)
def product_list(request):
    products = Product.objects.select_related("category", "brand").prefetch_related("images").order_by("-updated_at")
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(slug__icontains=query))
    category_id = request.GET.get("category", "")
    if category_id:
        products = products.filter(category_id=category_id)
    brand_id = request.GET.get("brand", "")
    if brand_id:
        products = products.filter(brand_id=brand_id)
    sale_mode = request.GET.get("sale_mode", "")
    if sale_mode:
        products = products.filter(sale_mode=sale_mode)
    availability = request.GET.get("availability", "")
    if availability:
        products = products.filter(availability=availability)
    active = request.GET.get("active", "")
    if active == "1":
        products = products.filter(active=True)
    elif active == "0":
        products = products.filter(active=False)
    featured = request.GET.get("featured", "")
    if featured == "1":
        products = products.filter(featured=True)
    elif featured == "0":
        products = products.filter(featured=False)
    return render(request, "backoffice/catalog/products/list.html", {
        "products": products, "query": query, "categories": Category.objects.order_by("name"),
        "brands": Brand.objects.order_by("name"), "sale_modes": Product.SaleMode.choices,
        "availabilities": Product.Availability.choices, "can_manage": user_has_backoffice_permission(request.user, BackofficePermission.COMMERCE_PRODUCTS_UPDATE),
        "can_create": user_has_backoffice_permission(request.user, BackofficePermission.COMMERCE_PRODUCTS_CREATE),
    })


@backoffice_permission_required(BackofficePermission.COMMERCE_PRODUCTS_VIEW)
def product_detail_admin(request, pk):
    product = get_object_or_404(Product.objects.select_related("category", "brand").prefetch_related("images"), pk=pk)
    history = AuditLog.objects.filter(module__startswith="commerce.", object_type="Product", object_id=str(product.pk))[:20]
    image_form = ProductImageBackofficeForm()
    return render(request, "backoffice/catalog/products/detail.html", {
        "product": product, "history": history, "image_form": image_form,
        "can_manage": user_has_backoffice_permission(request.user, BackofficePermission.COMMERCE_PRODUCTS_UPDATE),
        "can_manage_images": user_has_backoffice_permission(request.user, BackofficePermission.COMMERCE_IMAGES_CREATE),
    })


@backoffice_permission_required(BackofficePermission.COMMERCE_PRODUCTS_CREATE)
def product_create(request):
    form = ProductBackofficeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        product = create_product(form=form, request=request)
        messages.success(request, "Produto cadastrado com sucesso.")
        return redirect("backoffice:product_detail", pk=product.pk)
    return render(request, "backoffice/catalog/products/form.html", {"form": form, "title": "Novo produto"})


@backoffice_permission_required(BackofficePermission.COMMERCE_PRODUCTS_UPDATE)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductBackofficeForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        product = update_product(product=product, form=form, request=request)
        messages.success(request, "Produto atualizado com sucesso.")
        return redirect("backoffice:product_detail", pk=product.pk)
    return render(request, "backoffice/catalog/products/form.html", {"form": form, "product": product, "title": "Editar produto"})


@require_POST
@backoffice_permission_required(BackofficePermission.COMMERCE_PRODUCTS_UPDATE)
def product_activate(request, pk):
    product = set_product_active(product=get_object_or_404(Product, pk=pk), active=True, request=request)
    messages.success(request, "Produto ativado com sucesso.")
    return redirect("backoffice:product_detail", pk=product.pk)


@require_POST
@backoffice_permission_required(BackofficePermission.COMMERCE_PRODUCTS_UPDATE)
def product_deactivate(request, pk):
    product = set_product_active(product=get_object_or_404(Product, pk=pk), active=False, request=request)
    messages.success(request, "Produto desativado com sucesso.")
    return redirect("backoffice:product_detail", pk=product.pk)


@require_POST
@backoffice_permission_required(BackofficePermission.COMMERCE_PRODUCTS_UPDATE)
def product_feature(request, pk):
    product = set_product_featured(product=get_object_or_404(Product, pk=pk), featured=True, request=request)
    messages.success(request, "Produto destacado com sucesso.")
    return redirect("backoffice:product_detail", pk=product.pk)


@require_POST
@backoffice_permission_required(BackofficePermission.COMMERCE_PRODUCTS_UPDATE)
def product_unfeature(request, pk):
    product = set_product_featured(product=get_object_or_404(Product, pk=pk), featured=False, request=request)
    messages.success(request, "Destaque removido com sucesso.")
    return redirect("backoffice:product_detail", pk=product.pk)


@require_POST
@backoffice_permission_required(BackofficePermission.COMMERCE_IMAGES_CREATE)
def product_image_create(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductImageBackofficeForm(request.POST, request.FILES)
    if form.is_valid():
        create_product_image(product=product, form=form, request=request)
        messages.success(request, "Imagem enviada com sucesso.")
    else:
        messages.error(request, "Não foi possível enviar a imagem. Verifique o arquivo e tente novamente.")
    return redirect("backoffice:product_detail", pk=product.pk)


@require_POST
@backoffice_permission_required(BackofficePermission.COMMERCE_IMAGES_DELETE)
def product_image_delete(request, pk):
    image = get_object_or_404(ProductImage.objects.select_related("product"), pk=pk)
    product = delete_product_image(image=image, request=request)
    messages.success(request, "Imagem removida com sucesso.")
    return redirect("backoffice:product_detail", pk=product.pk)


@backoffice_permission_required(BackofficePermission.COMMERCE_CATEGORIES_VIEW)
def category_list_admin(request):
    categories = Category.objects.annotate(product_count=Count("products")).order_by("name")
    return render(request, "backoffice/catalog/categories/list.html", {
        "categories": categories, "can_create": user_has_backoffice_permission(request.user, BackofficePermission.COMMERCE_CATEGORIES_CREATE),
        "can_manage": user_has_backoffice_permission(request.user, BackofficePermission.COMMERCE_CATEGORIES_UPDATE),
    })


@backoffice_permission_required(BackofficePermission.COMMERCE_CATEGORIES_CREATE)
def category_create(request):
    form = CategoryBackofficeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        create_category(form=form, request=request)
        messages.success(request, "Categoria cadastrada.")
        return redirect("backoffice:category_list")
    return render(request, "backoffice/catalog/categories/form.html", {"form": form, "title": "Nova categoria"})


@backoffice_permission_required(BackofficePermission.COMMERCE_CATEGORIES_UPDATE)
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryBackofficeForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        update_category(category=category, form=form, request=request)
        messages.success(request, "Categoria atualizada.")
        return redirect("backoffice:category_list")
    return render(request, "backoffice/catalog/categories/form.html", {"form": form, "category": category, "title": "Editar categoria"})


@backoffice_permission_required(BackofficePermission.COMMERCE_BRANDS_VIEW)
def brand_list_admin(request):
    brands = Brand.objects.annotate(product_count=Count("products")).order_by("name")
    return render(request, "backoffice/catalog/brands/list.html", {
        "brands": brands, "can_create": user_has_backoffice_permission(request.user, BackofficePermission.COMMERCE_BRANDS_CREATE),
        "can_manage": user_has_backoffice_permission(request.user, BackofficePermission.COMMERCE_BRANDS_UPDATE),
    })


@backoffice_permission_required(BackofficePermission.COMMERCE_BRANDS_CREATE)
def brand_create(request):
    form = BrandBackofficeForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        create_brand(form=form, request=request)
        messages.success(request, "Marca cadastrada.")
        return redirect("backoffice:brand_list")
    return render(request, "backoffice/catalog/brands/form.html", {"form": form, "title": "Nova marca"})


@backoffice_permission_required(BackofficePermission.COMMERCE_BRANDS_UPDATE)
def brand_update(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    form = BrandBackofficeForm(request.POST or None, request.FILES or None, instance=brand)
    if request.method == "POST" and form.is_valid():
        update_brand(brand=brand, form=form, request=request)
        messages.success(request, "Marca atualizada.")
        return redirect("backoffice:brand_list")
    return render(request, "backoffice/catalog/brands/form.html", {"form": form, "brand": brand, "title": "Editar marca"})


@backoffice_permission_required(BackofficePermission.BUSINESS_UNITS_VIEW)
def business_unit_list(request):
    business_units = BusinessUnit.objects.annotate(
        membership_count=Count("memberships", distinct=True),
        customer_relationship_count=Count("customer_relationships", distinct=True),
    ).order_by("name")
    active = request.GET.get("active", "")
    if active == "1":
        business_units = business_units.filter(is_active=True)
    elif active == "0":
        business_units = business_units.filter(is_active=False)
    query = request.GET.get("q", "").strip()
    if query:
        business_units = business_units.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(slug__icontains=query))
    return render(
        request,
        "backoffice/administration/business_units/list.html",
        {
            "business_units": business_units,
            "query": query,
            "active": active,
            "can_create": user_has_backoffice_permission(request.user, BackofficePermission.BUSINESS_UNITS_CREATE),
            "can_manage": user_has_backoffice_permission(request.user, BackofficePermission.BUSINESS_UNITS_UPDATE),
        },
    )


@backoffice_permission_required(BackofficePermission.BUSINESS_UNITS_VIEW)
def business_unit_detail(request, pk):
    business_unit = get_object_or_404(
        BusinessUnit.objects.annotate(
            membership_count=Count("memberships", distinct=True),
            customer_relationship_count=Count("customer_relationships", distinct=True),
        ),
        pk=pk,
    )
    memberships = business_unit.memberships.select_related("user").order_by("user__username")
    history = AuditLog.objects.filter(module="backoffice.business_units", object_type="BusinessUnit", object_id=str(business_unit.pk))[:20]
    return render(
        request,
        "backoffice/administration/business_units/detail.html",
        {
            "business_unit": business_unit,
            "memberships": memberships,
            "history": history,
            "can_manage": user_has_backoffice_permission(request.user, BackofficePermission.BUSINESS_UNITS_UPDATE),
        },
    )


@backoffice_permission_required(BackofficePermission.BUSINESS_UNITS_CREATE)
def business_unit_create(request):
    form = BusinessUnitForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        business_unit = create_business_unit(form=form, request=request)
        messages.success(request, "Unidade de negócio cadastrada com sucesso.")
        return redirect("backoffice:business_unit_detail", pk=business_unit.pk)
    return render(request, "backoffice/administration/business_units/form.html", {"form": form, "title": "Nova unidade de negócio"})


@backoffice_permission_required(BackofficePermission.BUSINESS_UNITS_UPDATE)
def business_unit_update(request, pk):
    business_unit = get_object_or_404(BusinessUnit, pk=pk)
    form = BusinessUnitForm(request.POST or None, instance=business_unit)
    if request.method == "POST" and form.is_valid():
        business_unit = update_business_unit(business_unit=business_unit, form=form, request=request)
        messages.success(request, "Unidade de negócio atualizada com sucesso.")
        return redirect("backoffice:business_unit_detail", pk=business_unit.pk)
    return render(
        request,
        "backoffice/administration/business_units/form.html",
        {"form": form, "business_unit": business_unit, "title": "Editar unidade de negócio"},
    )


@backoffice_permission_required(BackofficePermission.DEPARTMENTS_VIEW)
def department_list(request):
    departments = Department.objects.select_related("business_unit").annotate(team_count=Count("teams", distinct=True)).order_by("business_unit__name", "name")
    business_unit_id = request.GET.get("business_unit", "")
    if business_unit_id:
        departments = departments.filter(business_unit_id=business_unit_id)
    active = request.GET.get("active", "")
    if active == "1":
        departments = departments.filter(is_active=True)
    elif active == "0":
        departments = departments.filter(is_active=False)
    query = request.GET.get("q", "").strip()
    if query:
        departments = departments.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(slug__icontains=query) | Q(business_unit__name__icontains=query))
    return render(
        request,
        "backoffice/administration/departments/list.html",
        {
            "departments": departments,
            "business_units": BusinessUnit.objects.order_by("name"),
            "business_unit_id": business_unit_id,
            "query": query,
            "active": active,
            "can_create": user_has_backoffice_permission(request.user, BackofficePermission.DEPARTMENTS_CREATE),
            "can_manage": user_has_backoffice_permission(request.user, BackofficePermission.DEPARTMENTS_UPDATE),
        },
    )


@backoffice_permission_required(BackofficePermission.DEPARTMENTS_CREATE)
def department_create(request):
    form = DepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        department = create_department(form=form, request=request)
        messages.success(request, "Departamento cadastrado com sucesso.")
        return redirect("backoffice:department_list")
    return render(request, "backoffice/administration/departments/form.html", {"form": form, "title": "Novo departamento"})


@backoffice_permission_required(BackofficePermission.DEPARTMENTS_UPDATE)
def department_update(request, pk):
    department = get_object_or_404(Department.objects.select_related("business_unit"), pk=pk)
    form = DepartmentForm(request.POST or None, instance=department)
    if request.method == "POST" and form.is_valid():
        update_department(department=department, form=form, request=request)
        messages.success(request, "Departamento atualizado com sucesso.")
        return redirect("backoffice:department_list")
    return render(
        request,
        "backoffice/administration/departments/form.html",
        {"form": form, "department": department, "title": "Editar departamento"},
    )


@backoffice_permission_required(BackofficePermission.TEAMS_VIEW)
def team_list(request):
    teams = Team.objects.select_related("department", "department__business_unit").order_by("department__business_unit__name", "department__name", "name")
    business_unit_id = request.GET.get("business_unit", "")
    if business_unit_id:
        teams = teams.filter(department__business_unit_id=business_unit_id)
    department_id = request.GET.get("department", "")
    if department_id:
        teams = teams.filter(department_id=department_id)
    active = request.GET.get("active", "")
    if active == "1":
        teams = teams.filter(is_active=True)
    elif active == "0":
        teams = teams.filter(is_active=False)
    query = request.GET.get("q", "").strip()
    if query:
        teams = teams.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(slug__icontains=query) | Q(department__name__icontains=query))
    departments = Department.objects.select_related("business_unit").order_by("business_unit__name", "name")
    if business_unit_id:
        departments = departments.filter(business_unit_id=business_unit_id)
    return render(
        request,
        "backoffice/administration/teams/list.html",
        {
            "teams": teams,
            "business_units": BusinessUnit.objects.order_by("name"),
            "departments": departments,
            "business_unit_id": business_unit_id,
            "department_id": department_id,
            "query": query,
            "active": active,
            "can_create": user_has_backoffice_permission(request.user, BackofficePermission.TEAMS_CREATE),
            "can_manage": user_has_backoffice_permission(request.user, BackofficePermission.TEAMS_UPDATE),
        },
    )


@backoffice_permission_required(BackofficePermission.TEAMS_CREATE)
def team_create(request):
    business_unit_id = request.POST.get("business_unit") or request.GET.get("business_unit")
    business_unit = BusinessUnit.objects.filter(pk=business_unit_id).first() if business_unit_id else None
    form = TeamForm(request.POST or None, business_unit=business_unit)
    if request.method == "POST" and form.is_valid():
        team = create_team(form=form, request=request)
        messages.success(request, "Equipe cadastrada com sucesso.")
        return redirect("backoffice:team_list")
    return render(
        request,
        "backoffice/administration/teams/form.html",
        {"form": form, "title": "Nova equipe", "business_units": BusinessUnit.objects.order_by("name"), "business_unit_id": business_unit_id or ""},
    )


@backoffice_permission_required(BackofficePermission.TEAMS_UPDATE)
def team_update(request, pk):
    team = get_object_or_404(Team.objects.select_related("department", "department__business_unit"), pk=pk)
    business_unit_id = request.POST.get("business_unit") or request.GET.get("business_unit") or team.department.business_unit_id
    business_unit = BusinessUnit.objects.filter(pk=business_unit_id).first() if business_unit_id else None
    form = TeamForm(request.POST or None, instance=team, business_unit=business_unit)
    if request.method == "POST" and form.is_valid():
        update_team(team=team, form=form, request=request)
        messages.success(request, "Equipe atualizada com sucesso.")
        return redirect("backoffice:team_list")
    return render(
        request,
        "backoffice/administration/teams/form.html",
        {"form": form, "team": team, "title": "Editar equipe", "business_units": BusinessUnit.objects.order_by("name"), "business_unit_id": str(business_unit_id or "")},
    )


@backoffice_permission_required(BackofficePermission.BUSINESS_UNIT_MEMBERSHIPS_VIEW)
def business_unit_membership_list(request):
    memberships = BusinessUnitMembership.objects.select_related("user", "business_unit").order_by("business_unit__name", "user__username")
    business_unit_id = request.GET.get("business_unit", "")
    if business_unit_id:
        memberships = memberships.filter(business_unit_id=business_unit_id)
    user_query = request.GET.get("user", "").strip()
    if user_query:
        memberships = memberships.filter(
            Q(user__username__icontains=user_query)
            | Q(user__first_name__icontains=user_query)
            | Q(user__last_name__icontains=user_query)
            | Q(user__email__icontains=user_query)
        )
    scope = request.GET.get("scope", "")
    if scope:
        memberships = memberships.filter(scope=scope)
    active = request.GET.get("active", "")
    if active == "1":
        memberships = memberships.filter(is_active=True)
    elif active == "0":
        memberships = memberships.filter(is_active=False)
    return render(
        request,
        "backoffice/administration/memberships/list.html",
        {
            "memberships": memberships,
            "business_units": BusinessUnit.objects.order_by("name"),
            "business_unit_id": business_unit_id,
            "user_query": user_query,
            "scope": scope,
            "active": active,
            "departments": Department.objects.select_related("business_unit").order_by("business_unit__name", "name"),
            "teams": Team.objects.select_related("department", "department__business_unit").order_by("department__business_unit__name", "department__name", "name"),
            "scope_choices": BusinessUnitMembershipForm.SUPPORTED_SCOPE_CHOICES,
            "can_create": user_has_backoffice_permission(request.user, BackofficePermission.BUSINESS_UNIT_MEMBERSHIPS_CREATE),
            "can_manage": user_has_backoffice_permission(request.user, BackofficePermission.BUSINESS_UNIT_MEMBERSHIPS_UPDATE),
        },
    )


@backoffice_permission_required(BackofficePermission.BUSINESS_UNIT_MEMBERSHIPS_CREATE)
def business_unit_membership_create(request):
    form = BusinessUnitMembershipForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        membership = create_membership(form=form, request=request)
        messages.success(request, "Acesso por unidade cadastrado com sucesso.")
        return redirect("backoffice:business_unit_membership_list")
    return render(request, "backoffice/administration/memberships/form.html", {"form": form, "title": "Novo acesso por unidade"})


@backoffice_permission_required(BackofficePermission.BUSINESS_UNIT_MEMBERSHIPS_UPDATE)
def business_unit_membership_update(request, pk):
    membership = get_object_or_404(BusinessUnitMembership.objects.select_related("user", "business_unit"), pk=pk)
    form = BusinessUnitMembershipForm(request.POST or None, instance=membership)
    if request.method == "POST" and form.is_valid():
        update_membership(membership=membership, form=form, request=request)
        messages.success(request, "Acesso por unidade atualizado com sucesso.")
        return redirect("backoffice:business_unit_membership_list")
    return render(
        request,
        "backoffice/administration/memberships/form.html",
        {"form": form, "membership": membership, "title": "Editar acesso por unidade"},
    )

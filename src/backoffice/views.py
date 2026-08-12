from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from src.backoffice.models import AuditLog
from src.backoffice.permissions.registry import BackofficePermission
from src.backoffice.permissions.services import user_has_backoffice_permission
from src.backoffice.services.scopes import apply_customer_scope
from src.backoffice.services.scopes import user_can_manage_customers
from src.backoffice.services.scopes import user_can_manage_salespeople
from src.backoffice.services.scopes import user_is_salesperson_role
from src.commerce.models import Brand
from src.commerce.models import Category
from src.commerce.models import Product
from src.customers.forms import CustomerForm
from src.customers.models import Customer
from src.customers.services import create_customer
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
        {"label": "Clientes cadastrados", "value": scoped_customers.count()},
        {"label": "Clientes ativos", "value": scoped_customers.filter(status=Customer.Status.ACTIVE).count()},
        {"label": "Vendedores ativos", "value": Salesperson.objects.filter(active=True).count()},
        {"label": "Produtos cadastrados", "value": Product.objects.count()},
        {"label": "Produtos publicados", "value": Product.objects.filter(active=True, category__active=True).count()},
        {"label": "Categorias", "value": Category.objects.count()},
        {"label": "Marcas", "value": Brand.objects.count()},
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
        customers = customers.filter(assigned_salesperson_id=salesperson_id)
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
    return render(
        request,
        "backoffice/customers/detail.html",
        {"customer": customer, "history": history, "can_manage": user_can_manage_customers(request.user)},
    )


@backoffice_permission_required(BackofficePermission.CUSTOMERS_CREATE)
def customer_create(request):
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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
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

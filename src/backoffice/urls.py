from django.urls import path

from . import views


app_name = "backoffice"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("clientes/", views.customer_list, name="customer_list"),
    path("clientes/novo/", views.customer_create, name="customer_create"),
    path("clientes/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("clientes/<int:pk>/editar/", views.customer_update, name="customer_update"),
    path("vendedores/", views.salesperson_list, name="salesperson_list"),
    path("vendedores/novo/", views.salesperson_create, name="salesperson_create"),
    path("vendedores/<int:pk>/", views.salesperson_detail, name="salesperson_detail"),
    path("vendedores/<int:pk>/editar/", views.salesperson_update, name="salesperson_update"),
]

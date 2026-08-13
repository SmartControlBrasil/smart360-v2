from django.urls import path

from . import views


app_name = "backoffice"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("produtos/", views.product_list, name="product_list"),
    path("produtos/novo/", views.product_create, name="product_create"),
    path("produtos/<int:pk>/", views.product_detail_admin, name="product_detail"),
    path("produtos/<int:pk>/editar/", views.product_update, name="product_update"),
    path("produtos/<int:pk>/ativar/", views.product_activate, name="product_activate"),
    path("produtos/<int:pk>/desativar/", views.product_deactivate, name="product_deactivate"),
    path("produtos/<int:pk>/destacar/", views.product_feature, name="product_feature"),
    path("produtos/<int:pk>/remover-destaque/", views.product_unfeature, name="product_unfeature"),
    path("produtos/<int:pk>/imagens/", views.product_image_create, name="product_image_create"),
    path("produtos/imagens/<int:pk>/remover/", views.product_image_delete, name="product_image_delete"),
    path("categorias/", views.category_list_admin, name="category_list"),
    path("categorias/nova/", views.category_create, name="category_create"),
    path("categorias/<int:pk>/editar/", views.category_update, name="category_update"),
    path("marcas/", views.brand_list_admin, name="brand_list"),
    path("marcas/nova/", views.brand_create, name="brand_create"),
    path("marcas/<int:pk>/editar/", views.brand_update, name="brand_update"),
    path("clientes/", views.customer_list, name="customer_list"),
    path("clientes/novo/", views.customer_create, name="customer_create"),
    path("clientes/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("clientes/<int:pk>/editar/", views.customer_update, name="customer_update"),
    path("clientes/<int:pk>/relacionamentos/<int:relationship_pk>/transferir/", views.customer_relationship_transfer, name="customer_relationship_transfer"),
    path("vendedores/", views.salesperson_list, name="salesperson_list"),
    path("vendedores/novo/", views.salesperson_create, name="salesperson_create"),
    path("vendedores/<int:pk>/", views.salesperson_detail, name="salesperson_detail"),
    path("vendedores/<int:pk>/editar/", views.salesperson_update, name="salesperson_update"),
    path("administracao/unidades/", views.business_unit_list, name="business_unit_list"),
    path("administracao/unidades/nova/", views.business_unit_create, name="business_unit_create"),
    path("administracao/unidades/<int:pk>/", views.business_unit_detail, name="business_unit_detail"),
    path("administracao/unidades/<int:pk>/editar/", views.business_unit_update, name="business_unit_update"),
    path("administracao/departamentos/", views.department_list, name="department_list"),
    path("administracao/departamentos/novo/", views.department_create, name="department_create"),
    path("administracao/departamentos/<int:pk>/editar/", views.department_update, name="department_update"),
    path("administracao/equipes/", views.team_list, name="team_list"),
    path("administracao/equipes/nova/", views.team_create, name="team_create"),
    path("administracao/equipes/<int:pk>/editar/", views.team_update, name="team_update"),
    path("administracao/acessos/", views.business_unit_membership_list, name="business_unit_membership_list"),
    path("administracao/acessos/novo/", views.business_unit_membership_create, name="business_unit_membership_create"),
    path("administracao/acessos/<int:pk>/editar/", views.business_unit_membership_update, name="business_unit_membership_update"),
]

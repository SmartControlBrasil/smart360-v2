from django.urls import path

from . import views


app_name = "commerce"

urlpatterns = [
    path("", views.product_list, name="shop"),
    path("detalhes/", views.legacy_shop_details, name="legacy_shop_details"),
    path("categoria/<slug:slug>/", views.category_detail, name="category"),
    path("produto/<slug:slug>/", views.product_detail, name="product_detail"),
]

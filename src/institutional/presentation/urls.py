from django.urls import path

from . import views


app_name = "institutional"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.InstitutionalLoginView.as_view(), name="login"),
    path("logout/", views.InstitutionalLogoutView.as_view(), name="logout"),
    path("cadastro/", views.signup, name="signup"),
    path("modelos/index-2/", views.home_02, name="home_02"),
    path("modelos/index-3/", views.home_03, name="home_03"),
    path("modelos/index-4/", views.home_04, name="home_04"),
    path("modelos/index-5/", views.home_05, name="home_05"),
    path("modelos/index-6/", views.home_06, name="home_06"),
    path("modelos/index-7/", views.home_07, name="home_07"),
    path("modelos/index-8/", views.home_08, name="home_08"),
    path("modelos/index-9/", views.home_09, name="home_09"),
    path(
        "solucoes/engenharia-serralheria-industrial/",
        views.engenharia_serralheria_industrial,
        name="engenharia_serralheria_industrial",
    ),
    path("modelos/index-10/", views.home_10, name="home_10"),
    path("empresa/", views.about, name="about"),
    path("servicos/", views.services, name="services"),
    path("servicos/detalhes/", views.service_details, name="service_details"),
    path("blog/", views.blog, name="blog"),
    path("blog/lista/", views.blog_list, name="blog_list"),
    path("blog/detalhes/", views.blog_details, name="blog_details"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    path("equipe/", views.team, name="team"),
    path("equipe/detalhes/", views.team_details, name="team_details"),
    path("projetos/", views.projects, name="projects"),
    path("projetos/detalhes/", views.project_details, name="project_details"),
    path("depoimentos/", views.testimonials, name="testimonials"),
    path("planos/", views.pricing, name="pricing"),
    path("experience-center/", views.experience_center, name="experience_center"),
    path("experience-center/play/", views.experience_center_play, name="experience_center_play"),
    path("carrinho/", views.cart, name="cart"),
    path("lista-de-desejos/", views.wishlist, name="wishlist"),
    path("checkout/", views.checkout, name="checkout"),
    path("loja/", views.shop, name="shop"),
    path("loja/detalhes/", views.shop_details, name="shop_details"),
    path("faq/", views.faq, name="faq"),
    path("contato/", views.contact, name="contact"),
    path("modelos/404/", views.error_404_preview, name="error_404_preview"),
]

from django.urls import path

from . import views


app_name = "institutional"

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("", views.home, name="home"),
    path("login/", views.InstitutionalLoginView.as_view(), name="login"),
    path("logout/", views.InstitutionalLogoutView.as_view(), name="logout"),
    path("cadastro/", views.signup, name="signup"),
    path("smart-control-brasil/", views.smart_control_brasil, name="smart_control_brasil"),
    path(
        "sistemas-websites-python/",
        views.sistemas_websites_python,
        name="sistemas_websites_python",
    ),
    path("livia/", views.livia, name="livia"),
    path("camaras-climaticas/", views.camaras_climaticas, name="camaras_climaticas"),
    path(
        "manutencao-industrial-campo/",
        views.manutencao_industrial_campo,
        name="manutencao_industrial_campo",
    ),
    path(
        "ai-video-interaction-platform/",
        views.ai_video_interaction_platform,
        name="ai_video_interaction_platform",
    ),
    path("xyron/", views.xyron, name="xyron"),
    path(
        "ai-web-solutions-startups/",
        views.ai_web_solutions_startups,
        name="ai_web_solutions_startups",
    ),
    path(
        "engenharia-serralheria-industrial/",
        views.engenharia_serralheria_industrial,
        name="engenharia_serralheria_industrial",
    ),
    path(
        "mitsubishi-automacao-industrial/",
        views.mitsubishi_automacao_industrial,
        name="mitsubishi_automacao_industrial",
    ),
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
    path("carrinho/", views.cart, name="cart"),
    path("lista-de-desejos/", views.wishlist, name="wishlist"),
    path("checkout/", views.checkout, name="checkout"),
    path("loja/", views.shop, name="shop"),
    path("loja/detalhes/", views.shop_details, name="shop_details"),
    path("faq/", views.faq, name="faq"),
    path("contato/", views.contact, name="contact"),
    path("modelos/404/", views.error_404_preview, name="error_404_preview"),
]

from django.urls import path
from django.views.generic import RedirectView

from . import views


app_name = "institutional"

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("", views.home, name="home"),
    path("sobre/", views.legacy_about, name="legacy_about"),
    path("login/", views.InstitutionalLoginView.as_view(), name="login"),
    path("logout/", views.InstitutionalLogoutView.as_view(), name="logout"),
    path("cadastro/", views.signup, name="signup"),
    path(
        "smart-control-brasil/",
        RedirectView.as_view(pattern_name="institutional:home", permanent=True),
        name="smart_control_brasil",
    ),
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
    path("xyron/littlebot/", views.xyron_littlebot, name="xyron_littlebot"),
    path("xyron/orbit/", views.xyron_orbit, name="xyron_orbit"),
    path("xyron/neo-bot/", views.xyron_neo_bot, name="xyron_neo_bot"),
    path("xyron/waiter-bot/", views.xyron_waiter_bot, name="xyron_waiter_bot"),
    path("xyron/hygibot-dune-bot/", views.xyron_hygibot_dune_bot, name="xyron_hygibot_dune_bot"),
    path("xyron/buddy-bot/", views.xyron_buddy_bot, name="xyron_buddy_bot"),
    path("xyron/carebot/", views.xyron_carebot, name="xyron_carebot"),
    path("xyron/hostbot/", views.xyron_hostbot, name="xyron_hostbot"),
    path("xyron/mowerbot/", views.xyron_mowerbot, name="xyron_mowerbot"),
    path(
        "robotica-educacional/",
        views.disabled_commercial_landing,
        name="robotica_educacional",
    ),
    path(
        "robo-seguranca-condominios/",
        views.disabled_commercial_landing,
        name="robo_seguranca_condominios",
    ),
    path("camara-climatica/", views.disabled_commercial_landing, name="camara_climatica"),
    path(
        "ai-web-solutions-startups/",
        views.ai_web_solutions_startups,
        name="ai_web_solutions_startups",
    ),
    path(
        "engenharia-serralheria-industrial/",
        views.disabled_commercial_landing,
        name="engenharia_serralheria_industrial",
    ),
    path(
        "mitsubishi-automacao-industrial/",
        views.mitsubishi_automacao_industrial,
        name="mitsubishi_automacao_industrial",
    ),
    path(
        "parceiros/mitsubishi-automacao/",
        views.legacy_mitsubishi_automation,
        name="legacy_parceiros_mitsubishi_automacao",
    ),
    path(
        "parceiros/automacao-industrial-clps/",
        views.legacy_mitsubishi_automation,
        name="legacy_parceiros_automacao_industrial_clps",
    ),
    path(
        "parceiros/xyron-robotics/",
        views.legacy_xyron_robotics,
        name="legacy_parceiros_xyron_robotics",
    ),
    path("empresa/", views.about, name="about"),
    path("servicos/", views.services, name="services"),
    path("blog/", views.blog, name="blog"),
    path("blog/lista/", views.blog_list, name="blog_list"),
    path("blog/detalhes/", views.blog_details, name="blog_details"),
    path(
        "blog/automacao-industrial-conectada-gestao/",
        views.legacy_automacao_industrial_conectada_gestao,
        name="legacy_automacao_industrial_conectada_gestao",
    ),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    path("contato/", views.contact, name="contact"),
]

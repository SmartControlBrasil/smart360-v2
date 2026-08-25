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
    path(
        "manutencao-industrial-campo/",
        views.manutencao_industrial_campo,
        name="manutencao_industrial_campo",
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
    path("projetos/", views.legacy_projects, name="legacy_projects"),
    path("projetos/detalhes/", views.legacy_projects, name="legacy_project_details"),
    path("parceiros/agraz/", views.legacy_agraz, name="legacy_parceiros_agraz"),
    path("blog/", views.blog, name="blog"),
    path("blog/lista/", views.blog_list, name="blog_list"),
    path("blog/detalhes/", views.blog_details, name="blog_details"),
    path(
        "blog/automacao-industrial-conectada-gestao/",
        views.legacy_automacao_industrial_conectada_gestao,
        name="legacy_automacao_industrial_conectada_gestao",
    ),
    path(
        "blog/dashboards-decisoes-melhores/",
        views.legacy_blog_dashboards_decisoes_melhores,
        name="legacy_blog_dashboards_decisoes_melhores",
    ),
    path(
        "blog/iot-mudando-negocios/",
        views.legacy_blog_iot_mudando_negocios,
        name="legacy_blog_iot_mudando_negocios",
    ),
    path(
        "blog/manutencao-tpm-confiabilidade-sistemas-automatizados/",
        views.legacy_blog_manutencao_tpm,
        name="legacy_blog_manutencao_tpm",
    ),
    path(
        "blog/paineis-eletricos-automacao/",
        views.legacy_blog_paineis_eletricos_automacao,
        name="legacy_blog_paineis_eletricos_automacao",
    ),
    path(
        "blog/aplicacoes-reais-robos-brasil/",
        views.legacy_blog_aplicacoes_reais_robos_brasil,
        name="legacy_blog_aplicacoes_reais_robos_brasil",
    ),
    path(
        "blog/robotica-escolas-empresas-cidades/",
        views.legacy_blog_robotica_escolas_empresas_cidades,
        name="legacy_blog_robotica_escolas_empresas_cidades",
    ),
    path(
        "blog/integrar-sensores-maquinas-sistemas/",
        views.legacy_blog_integrar_sensores_maquinas_sistemas,
        name="legacy_blog_integrar_sensores_maquinas_sistemas",
    ),
    path(
        "blog/automacao-conectada-maquinas-sensores-sistemas/",
        views.legacy_blog_automacao_conectada_maquinas_sensores_sistemas,
        name="legacy_blog_automacao_conectada_maquinas_sensores_sistemas",
    ),
    path(
        "blog/dados-operacionais-empresa-inteligente/",
        views.legacy_blog_dados_operacionais_empresa_inteligente,
        name="legacy_blog_dados_operacionais_empresa_inteligente",
    ),
    path("blog/pagina/2/", views.legacy_blog_pagina_2, name="legacy_blog_pagina_2"),
    path("faq/", views.legacy_faq, name="legacy_faq"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    path("autor/<slug:slug>/", views.author_detail, name="author_detail"),
    path("contato/", views.contact, name="contact"),
]

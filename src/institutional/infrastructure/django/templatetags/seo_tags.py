from urllib.parse import urlsplit

from django import template
from django.conf import settings


register = template.Library()

DEFAULT_TITLE = "MC Automation | Automação Industrial, Robótica e Sistemas"
DEFAULT_DESCRIPTION = (
    "Soluções em automação industrial, robótica, engenharia embarcada, "
    "manutenção técnica e sistemas web."
)

ROUTE_METADATA = {
    "home": {
        "title": "MC Automation | Automação Industrial, Robótica e Sistemas",
        "description": (
            "Soluções em automação industrial, robótica, manutenção técnica, "
            "integração de sistemas e desenvolvimento de software para empresas e indústrias."
        ),
    },
    "services": {
        "title": "Serviços de Automação Industrial, Robótica e Software | MC Automation",
        "description": (
            "Conheça os serviços da MC Automation em automação industrial, robótica, "
            "manutenção técnica, retrofit, integração de sistemas e desenvolvimento web."
        ),
    },
    "projects": {
        "title": "Projetos de Automação, Robótica e Sistemas | MC Automation",
        "description": (
            "Veja projetos e aplicações da MC Automation em engenharia, automação "
            "industrial, robótica, sistemas inteligentes e modernização técnica."
        ),
    },
    "blog": {
        "title": "Blog de Automação Industrial, Robótica e Tecnologia | MC Automation",
        "description": (
            "Artigos técnicos sobre automação industrial, robótica, manutenção, "
            "integração de dados, sistemas web e engenharia aplicada."
        ),
    },
    "about": {
        "title": "Empresa de Automação, Robótica e Sistemas | MC Automation",
        "description": (
            "Conheça a MC Automation, empresa especializada em automação industrial, "
            "robótica, engenharia, manutenção técnica e desenvolvimento de sistemas."
        ),
    },
    "testimonials": {
        "title": "Depoimentos e Resultados em Tecnologia | MC Automation",
        "description": (
            "Veja percepções sobre a atuação da MC Automation em projetos de "
            "automação, robótica, engenharia e tecnologia aplicada a negócios."
        ),
    },
    "faq": {
        "title": "Perguntas Frequentes sobre Automação e Robótica | MC Automation",
        "description": (
            "Tire dúvidas sobre projetos de automação industrial, robótica, sistemas, "
            "manutenção técnica, suporte e atendimento da MC Automation."
        ),
    },
    "contact": {
        "title": "Contato e Orçamento em Automação Industrial | MC Automation",
        "description": (
            "Fale com a MC Automation para solicitar orçamento, diagnóstico técnico "
            "ou atendimento comercial em automação, robótica e sistemas."
        ),
    },
    "engenharia_serralheria_industrial": {
        "title": "Engenharia e Serralheria Industrial | MC Automation",
        "description": (
            "Soluções de engenharia e serralheria industrial para estruturas, proteções, "
            "adequações, dispositivos especiais e apoio a projetos industriais."
        ),
    },
}

NOINDEX_ROUTE_NAMES = {
    "home_02",
    "home_03",
    "home_04",
    "home_05",
    "home_06",
    "home_07",
    "home_08",
    "home_09",
    "home_10",
    "service_details",
    "blog_list",
    "blog_details",
    "team",
    "team_details",
    "project_details",
    "pricing",
    "experience_center",
    "cart",
    "wishlist",
    "checkout",
    "shop",
    "shop_details",
    "error_404_preview",
    "login",
    "signup",
}


def _normalize_path(path):
    if not path:
        return "/"

    normalized = urlsplit(str(path)).path or "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def _metadata(context):
    page = context.get("page")
    return getattr(page, "metadata", None)


def _route_name(context):
    request = context.get("request")
    resolver_match = getattr(request, "resolver_match", None)
    return getattr(resolver_match, "url_name", None)


def _route_metadata(context):
    return ROUTE_METADATA.get(_route_name(context), {})


def _metadata_canonical_path(context):
    metadata = _metadata(context)
    return getattr(metadata, "canonical_path", None) or context.get("canonical_path")


def _post(context):
    return context.get("post")


@register.simple_tag(takes_context=True)
def canonical_url(context):
    path = _metadata_canonical_path(context)
    request = context.get("request")
    if not path and request is not None:
        path = request.path

    return f"{settings.PUBLIC_SITE_URL}{_normalize_path(path)}"


@register.simple_tag(takes_context=True)
def page_title(context):
    post = _post(context)
    if post:
        return f"{post.get('title', DEFAULT_TITLE)} | MC Automation"

    metadata = _metadata(context)
    if metadata and getattr(metadata, "title", None):
        return metadata.title

    return _route_metadata(context).get("title", DEFAULT_TITLE)


@register.simple_tag(takes_context=True)
def meta_description(context):
    post = _post(context)
    if post and post.get("meta_description"):
        return post["meta_description"]

    metadata = _metadata(context)
    if metadata and getattr(metadata, "description", None):
        return metadata.description

    return _route_metadata(context).get("description", DEFAULT_DESCRIPTION)


@register.simple_tag(takes_context=True)
def robots_directives(context):
    if _route_name(context) in NOINDEX_ROUTE_NAMES:
        return "noindex,follow"
    return ""

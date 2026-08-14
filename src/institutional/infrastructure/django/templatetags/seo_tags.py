from urllib.parse import urlsplit

from django import template
from django.conf import settings
from django.templatetags.static import static


register = template.Library()

DEFAULT_TITLE = "Smart Control Brasil | Automação Industrial, Robótica e Sistemas"
DEFAULT_DESCRIPTION = (
    "Soluções em automação industrial, robótica, engenharia embarcada, "
    "manutenção técnica e sistemas web."
)
DEFAULT_SOCIAL_IMAGE = "institutional/imgs/images/banner-6-img-1.png"
SOCIAL_SITE_NAME = "Smart Control Brasil"

ROUTE_METADATA = {
    "home": {
        "title": "Smart Control Brasil | Automação Industrial, Robótica e Sistemas",
        "description": (
            "Soluções em automação industrial, robótica, manutenção técnica, "
            "integração de sistemas e desenvolvimento de software para empresas e indústrias."
        ),
    },
    "services": {
        "title": "Serviços de Automação Industrial, Robótica e Software | Smart Control Brasil",
        "description": (
            "Conheça os serviços da Smart Control Brasil em automação industrial, robótica, "
            "manutenção técnica, retrofit, integração de sistemas e desenvolvimento web."
        ),
    },
    "projects": {
        "title": "Projetos de Automação, Robótica e Sistemas | Smart Control Brasil",
        "description": (
            "Veja projetos e aplicações da Smart Control Brasil em engenharia, automação "
            "industrial, robótica, sistemas inteligentes e modernização técnica."
        ),
    },
    "blog": {
        "title": "Blog de Automação Industrial, Robótica e Tecnologia | Smart Control Brasil",
        "description": (
            "Artigos técnicos sobre automação industrial, robótica, manutenção, "
            "integração de dados, sistemas web e engenharia aplicada."
        ),
    },
    "about": {
        "title": "Empresa de Automação, Robótica e Sistemas | Smart Control Brasil",
        "description": (
            "Conheça a Smart Control Brasil, empresa especializada em automação industrial, "
            "robótica, engenharia, manutenção técnica e desenvolvimento de sistemas."
        ),
    },
    "testimonials": {
        "title": "Depoimentos e Resultados em Tecnologia | Smart Control Brasil",
        "description": (
            "Veja percepções sobre a atuação da Smart Control Brasil em projetos de "
            "automação, robótica, engenharia e tecnologia aplicada a negócios."
        ),
    },
    "faq": {
        "title": "Perguntas Frequentes sobre Automação e Robótica | Smart Control Brasil",
        "description": (
            "Tire dúvidas sobre projetos de automação industrial, robótica, sistemas, "
            "manutenção técnica, suporte e atendimento da Smart Control Brasil."
        ),
    },
    "contact": {
        "title": "Contato e Orçamento em Automação Industrial | Smart Control Brasil",
        "description": (
            "Fale com a Smart Control Brasil para solicitar orçamento, diagnóstico técnico "
            "ou atendimento comercial em automação, robótica e sistemas."
        ),
    },
    "smart_control_brasil": {
        "title": "Smart Control Brasil | Automação Industrial, Robótica e Sistemas",
        "description": (
            "Soluções em automação industrial, robótica, manutenção técnica, "
            "integração de sistemas e desenvolvimento de software para empresas e indústrias."
        ),
    },
    "sistemas_websites_python": {
        "title": "Sistemas Web e Desenvolvimento Python | Smart Control Brasil",
        "description": (
            "Desenvolvimento de sistemas web, plataformas empresariais, automações e soluções "
            "em Python e Django para digitalização de processos."
        ),
    },
    "manutencao_industrial_campo": {
        "title": "Manutenção Industrial e Assistência Técnica | Smart Control Brasil",
        "description": (
            "Manutenção industrial, diagnóstico, assistência técnica em campo, automação, "
            "eletrônica e suporte especializado para máquinas e equipamentos."
        ),
    },
    "xyron": {
        "title": "Robôs Inteligentes Xyron Robotics | Smart Control Brasil",
        "description": (
            "Conheça as soluções de robótica inteligente da Xyron Robotics para educação, "
            "atendimento, interação e aplicações profissionais com a Smart Control Brasil."
        ),
    },
    "engenharia_serralheria_industrial": {
        "title": "Engenharia e Serralheria Industrial | Smart Control Brasil",
        "description": (
            "Soluções de engenharia e serralheria industrial para estruturas, proteções, "
            "adequações, dispositivos especiais e apoio a projetos industriais."
        ),
    },
    "mitsubishi_automacao_industrial": {
        "title": "Automação Industrial Mitsubishi Electric | Smart Control Brasil",
        "description": (
            "Soluções de automação industrial Mitsubishi Electric com CLPs, IHMs, inversores, "
            "integração, engenharia e suporte técnico especializado."
        ),
    },
}

NOINDEX_ROUTE_NAMES = {
    "smart_control_brasil",
    "livia",
    "camaras_climaticas",
    "ai_video_interaction_platform",
    "ai_web_solutions_startups",
    "service_details",
    "blog_list",
    "blog_details",
    "team",
    "team_details",
    "project_details",
    "pricing",
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


def _resolver_match(context):
    request = context.get("request")
    return getattr(request, "resolver_match", None)


def _route_name(context):
    resolver_match = _resolver_match(context)
    return getattr(resolver_match, "url_name", None)


def _app_name(context):
    resolver_match = _resolver_match(context)
    return getattr(resolver_match, "app_name", None)


def _route_metadata(context):
    return ROUTE_METADATA.get(_route_name(context), {})


def _metadata_canonical_path(context):
    metadata = _metadata(context)
    return getattr(metadata, "canonical_path", None) or context.get("canonical_path")


def _post(context):
    return context.get("post")


def _product(context):
    return context.get("product")


def _absolute_public_url(path):
    if not path:
        return ""

    candidate = str(path)
    if candidate.startswith(("http://", "https://")):
        return candidate
    return f"{settings.PUBLIC_SITE_URL}{_normalize_path(candidate)}"


def _static_public_url(path):
    return _absolute_public_url(static(path))


def _post_image_url(context):
    post = _post(context)
    if post and post.get("image"):
        return _static_public_url(post["image"])
    return ""


def _product_image_url(context):
    product = _product(context)
    primary_image = getattr(product, "primary_image", None) if product else None
    image = getattr(primary_image, "image", None)
    if image:
        try:
            return _absolute_public_url(image.url)
        except ValueError:
            return ""
    return ""


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
        return f"{post.get('title', DEFAULT_TITLE)} | Smart Control Brasil"

    product = _product(context)
    if product:
        return f"{product.seo_title or product.name} | Smart Control Brasil"

    metadata = _metadata(context)
    if metadata and getattr(metadata, "title", None):
        return metadata.title

    return _route_metadata(context).get("title", DEFAULT_TITLE)


@register.simple_tag(takes_context=True)
def meta_description(context):
    post = _post(context)
    if post and post.get("meta_description"):
        return post["meta_description"]

    product = _product(context)
    if product:
        return product.seo_description or product.short_description or DEFAULT_DESCRIPTION

    metadata = _metadata(context)
    if metadata and getattr(metadata, "description", None):
        return metadata.description

    return _route_metadata(context).get("description", DEFAULT_DESCRIPTION)


@register.simple_tag(takes_context=True)
def social_type(context):
    if _post(context):
        return "article"
    return "website"


@register.simple_tag(takes_context=True)
def social_image_url(context):
    return _post_image_url(context) or _product_image_url(context) or _static_public_url(DEFAULT_SOCIAL_IMAGE)


@register.simple_tag(takes_context=True)
def robots_directives(context):
    if _app_name(context) == "commerce":
        return ""
    if _route_name(context) in NOINDEX_ROUTE_NAMES:
        return "noindex,follow"
    return ""

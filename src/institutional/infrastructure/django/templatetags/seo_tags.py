import json
from decimal import Decimal
from urllib.parse import urlsplit

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe


register = template.Library()

DEFAULT_TITLE = "Smart Control Brasil | Automação Industrial, Robótica e Sistemas"
DEFAULT_DESCRIPTION = (
    "Soluções em automação industrial, robótica, engenharia embarcada, "
    "manutenção técnica e sistemas web."
)
DEFAULT_SOCIAL_IMAGE = "institutional/imgs/images/banner-6-img-1.png"
ORGANIZATION_LOGO = "institutional/imgs/images/header/logo-cores-03.webp"
SOCIAL_SITE_NAME = "Smart Control Brasil"
ORGANIZATION_EMAIL = "comercial@smartcontrolbrasil.com.br"
ORGANIZATION_TELEPHONE = "+551151968525"

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
    "robotica_educacional": {
        "title": "Robótica Educacional para Escolas | Smart Control Brasil",
        "description": (
            "Robôs educacionais e soluções interativas para escolas, projetos pedagógicos e "
            "experiências de tecnologia com alunos."
        ),
    },
    "robo_seguranca_condominios": {
        "title": "Robô de Segurança para Condomínios | Smart Control Brasil",
        "description": (
            "Soluções com robô Orbit para patrulhamento, vigilância assistida e apoio à "
            "segurança em condomínios e operações corporativas."
        ),
    },
    "camara_climatica": {
        "title": "Câmara Climática Sob Medida | Smart Control Brasil",
        "description": (
            "Projeto, instalação, retrofit e manutenção de câmaras climáticas sob medida para "
            "testes ambientais, temperatura e umidade."
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


def _site_url(path="/"):
    return _absolute_public_url(path)


def _organization_schema():
    return {
        "@type": "Organization",
        "name": SOCIAL_SITE_NAME,
        "url": settings.PUBLIC_SITE_URL,
        "logo": _static_public_url(ORGANIZATION_LOGO),
        "email": getattr(settings, "CONTACT_RECIPIENT_EMAIL", ORGANIZATION_EMAIL),
        "telephone": ORGANIZATION_TELEPHONE,
    }


def _website_schema():
    return {
        "@type": "WebSite",
        "name": SOCIAL_SITE_NAME,
        "url": settings.PUBLIC_SITE_URL,
    }


def _list_item(position, name, item):
    return {
        "@type": "ListItem",
        "position": position,
        "name": name,
        "item": item,
    }


def _breadcrumb_schema(items):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            _list_item(position, name, item)
            for position, (name, item) in enumerate(items, start=1)
        ],
    }


def _breadcrumb_items(context):
    route_name = _route_name(context)
    post = _post(context)
    product = _product(context)
    home = ("Início", _site_url(reverse("institutional:home")))

    solution_names = {
        "xyron": "Xyron Robotics",
        "robotica_educacional": "Robótica Educacional",
        "robo_seguranca_condominios": "Robô de Segurança para Condomínios",
        "camara_climatica": "Câmara Climática Sob Medida",
        "mitsubishi_automacao_industrial": "Mitsubishi Automação Industrial",
        "manutencao_industrial_campo": "Manutenção Industrial",
        "engenharia_serralheria_industrial": "Engenharia e Serralheria Industrial",
        "sistemas_websites_python": "Sistemas Web e Desenvolvimento Python",
    }
    if route_name in solution_names:
        return [home, (solution_names[route_name], canonical_url(context))]

    if post:
        return [
            home,
            ("Blog", _site_url(reverse("institutional:blog"))),
            (post.get("title", "Artigo"), canonical_url(context)),
        ]

    if product:
        items = [home, ("Loja", _site_url(reverse("commerce:shop")))]
        category = getattr(product, "category", None)
        if category:
            items.append((category.name, _site_url(category.get_absolute_url())))
        items.append((product.name, canonical_url(context)))
        return items

    return []


def _article_schema(context):
    post = _post(context)
    if not post:
        return None

    schema = {
        "@type": "Article",
        "headline": post.get("title", ""),
        "description": post.get("meta_description", ""),
        "url": canonical_url(context),
        "image": _post_image_url(context) or social_image_url(context),
        "author": {
            "@type": "Organization",
            "name": SOCIAL_SITE_NAME,
        },
        "publisher": {
            "@type": "Organization",
            "name": SOCIAL_SITE_NAME,
            "logo": {
                "@type": "ImageObject",
                "url": _static_public_url(ORGANIZATION_LOGO),
            },
        },
    }
    return {key: value for key, value in schema.items() if value}


def _product_description(product):
    return product.seo_description or product.short_description or DEFAULT_DESCRIPTION


def _product_offer(product, url):
    if not (product.show_price and product.price and product.price > Decimal("0")):
        return None
    direct_modes = {product.SaleMode.DIRECT, product.SaleMode.DIRECT_AND_QUOTE}
    if product.sale_mode not in direct_modes:
        return None
    return {
        "@type": "Offer",
        "price": str(product.price),
        "priceCurrency": "BRL",
        "url": url,
    }


def _product_schema(context):
    product = _product(context)
    if not product:
        return None

    url = canonical_url(context)
    schema = {
        "@type": "Product",
        "name": product.name,
        "description": _product_description(product),
        "image": _product_image_url(context) or social_image_url(context),
        "url": url,
    }
    if getattr(product, "brand", None):
        schema["brand"] = {
            "@type": "Brand",
            "name": product.brand.name,
        }
    if getattr(product, "category", None):
        schema["category"] = product.category.name
    offer = _product_offer(product, url)
    if offer:
        schema["offers"] = offer
    return schema


def _structured_data_graph(context):
    if robots_directives(context):
        return []

    graph = []
    if _route_name(context) == "home":
        graph.extend([_organization_schema(), _website_schema()])

    breadcrumbs = _breadcrumb_items(context)
    if breadcrumbs:
        graph.append(_breadcrumb_schema(breadcrumbs))

    article = _article_schema(context)
    if article:
        graph.append(article)

    product = _product_schema(context)
    if product:
        graph.append(product)

    return graph


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


@register.simple_tag(takes_context=True)
def structured_data_jsonld(context):
    graph = _structured_data_graph(context)
    if not graph:
        return ""

    payload = {
        "@context": "https://schema.org",
        "@graph": graph,
    }
    return mark_safe(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

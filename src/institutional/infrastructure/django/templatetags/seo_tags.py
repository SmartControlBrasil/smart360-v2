import json
from decimal import Decimal
from urllib.parse import urlsplit

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe

from src.institutional.presentation.blog_posts import BLOG_POSTS
from src.institutional.presentation.xyron_robot_pages import XYRON_ROBOT_PAGES


register = template.Library()

DEFAULT_TITLE = "Smart Control Brasil | Automação Industrial, Robótica e Sistemas"
DEFAULT_DESCRIPTION = (
    "Soluções em automação industrial, robótica, engenharia embarcada, "
    "manutenção técnica e sistemas web."
)
DEFAULT_SOCIAL_IMAGE = "institutional/imgs/images/banner-6-img-1.png"
DEFAULT_SOCIAL_IMAGE_WIDTH = 1290
DEFAULT_SOCIAL_IMAGE_HEIGHT = 670
DEFAULT_SOCIAL_IMAGE_ALT = "Robótica, automação e sistemas inteligentes da Smart Control Brasil"
ORGANIZATION_LOGO = "institutional/imgs/images/header/logo-cores-03.webp"
SOCIAL_SITE_NAME = "Smart Control Brasil"
ORGANIZATION_EMAIL = "comercial@smartcontrolbrasil.com.br"
ORGANIZATION_TELEPHONE = "+551151968525"
ORGANIZATION_ID = "https://www.smartcontrolbrasil.com.br/#organization"
ORGANIZATION_ADDRESS = {
    "@type": "PostalAddress",
    "streetAddress": "R. Agnaldo Alves Silva - Jardim Maristela",
    "addressLocality": "Itapevi",
    "addressRegion": "SP",
    "postalCode": "06663-160",
    "addressCountry": "BR",
}

CONTACT_PAGE_FAQS = [
    (
        "Quais serviços posso solicitar pelo formulário?",
        "O formulário pode ser usado para assuntos relacionados a automação industrial, robótica, manutenção industrial e sistemas web, conforme as soluções apresentadas no site.",
    ),
    (
        "Posso solicitar atendimento para manutenção e retrofit?",
        "Sim. Você pode descrever necessidades de manutenção industrial, diagnóstico técnico, retrofit, comissionamento ou apoio em equipamentos e sistemas existentes.",
    ),
    (
        "Posso falar sobre projetos de automação Mitsubishi Electric ou robótica Xyron?",
        "Sim. O formulário pode ser usado para contato comercial ou técnico sobre soluções de automação Mitsubishi Electric e robótica Xyron apresentadas pela Smart Control Brasil.",
    ),
    (
        "Quais informações ajudam na análise de uma solicitação técnica?",
        "Descreva o tipo de equipamento ou projeto, a necessidade principal, sintomas observados em casos de manutenção, localização da aplicação e documentos ou fotos que possam ser descritos na mensagem.",
    ),
]

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
            "Conheça os serviços da Smart Control Brasil em automação industrial, robótica Xyron, "
            "manutenção industrial e desenvolvimento de sistemas sob medida."
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
        "title": "Sistemas Web, Websites e Desenvolvimento Python | Smart Control Brasil",
        "description": (
            "Desenvolvimento de sistemas web, websites empresariais, plataformas, integrações "
            "e soluções em Python e Django para digitalização de processos."
        ),
    },
    "manutencao_industrial_campo": {
        "title": "Manutenção Industrial e Assistência Técnica | Smart Control Brasil",
        "description": (
            "Manutenção industrial e assistência técnica em campo com diagnóstico, "
            "preventiva, corretiva, comissionamento, retrofit, automação e painéis elétricos."
        ),
        "social_image": "institutional/imgs/images/retrofite-painel-eletronico.webp",
        "social_image_width": 930,
        "social_image_height": 470,
        "social_image_alt": "Retrofit de painel eletrônico industrial",
    },
    "xyron": {
        "title": "Robôs Inteligentes Xyron Robotics | Smart Control Brasil",
        "description": (
            "Conheça as soluções de robótica inteligente da Xyron Robotics para educação, "
            "atendimento, interação e aplicações profissionais com a Smart Control Brasil."
        ),
    },
    "mitsubishi_automacao_industrial": {
        "title": "Automação Industrial Mitsubishi Electric | Smart Control Brasil",
        "description": (
            "Automação industrial Mitsubishi Electric com CLPs, IHMs, inversores, "
            "servoacionamentos, integração, retrofit, comissionamento e suporte técnico."
        ),
        "social_image": "institutional/imgs/images/clp-e-acionanentos.webp",
        "social_image_width": 220,
        "social_image_height": 260,
        "social_image_alt": "CLP Mitsubishi Electric em aplicação de automação",
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


def _robot(context):
    return context.get("robot")


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


def _robot_image_url(context):
    robot = _robot(context)
    if robot and robot.get("image"):
        return _static_public_url(robot["image"])
    return ""


def _route_social_image_url(context):
    image = _route_metadata(context).get("social_image")
    if image:
        return _static_public_url(image)
    return ""


def _site_url(path="/"):
    return _absolute_public_url(path)


def _organization_schema():
    return {
        "@id": ORGANIZATION_ID,
        "@type": "Organization",
        "name": SOCIAL_SITE_NAME,
        "url": settings.PUBLIC_SITE_URL,
        "logo": _static_public_url(ORGANIZATION_LOGO),
        "email": getattr(settings, "CONTACT_RECIPIENT_EMAIL", ORGANIZATION_EMAIL),
        "telephone": ORGANIZATION_TELEPHONE,
        "address": ORGANIZATION_ADDRESS,
        "areaServed": "Brasil",
        "knowsAbout": [
            "Automação Industrial",
            "Robótica",
            "Manutenção Industrial",
            "Sistemas Web",
            "Inteligência Artificial aplicada",
        ],
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
    robot = _robot(context)
    home = ("Início", _site_url(reverse("institutional:home")))

    if robot:
        return [
            home,
            ("Xyron Robotics", _site_url(reverse("institutional:xyron"))),
            (robot.get("name", "Robô Xyron"), canonical_url(context)),
        ]

    solution_names = {
        "xyron": "Xyron Robotics",
        "mitsubishi_automacao_industrial": "Mitsubishi Automação Industrial",
        "manutencao_industrial_campo": "Manutenção Industrial",
        "sistemas_websites_python": "Sistemas Web e Desenvolvimento Python",
    }
    if route_name in solution_names:
        return [home, (solution_names[route_name], canonical_url(context))]

    page_names = {
        "about": "Sobre",
        "services": "Serviços",
        "blog": "Blog",
        "contact": "Contato",
    }
    if route_name in page_names:
        return [home, (page_names[route_name], canonical_url(context))]

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
        "@type": "BlogPosting",
        "headline": post.get("title", ""),
        "description": post.get("meta_description", ""),
        "url": canonical_url(context),
        "mainEntityOfPage": canonical_url(context),
        "articleSection": post.get("category", ""),
        "image": _post_image_url(context) or social_image_url(context),
        "author": {
            "@type": "Organization",
            "name": "Equipe Smart Control Brasil",
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


def _blog_schema(context):
    if _route_name(context) != "blog":
        return None

    return {
        "@type": "Blog",
        "name": _route_metadata(context).get("title", "Blog Smart Control Brasil"),
        "description": _route_metadata(context).get("description", DEFAULT_DESCRIPTION),
        "url": canonical_url(context),
        "publisher": {
            "@type": "Organization",
            "name": SOCIAL_SITE_NAME,
            "url": settings.PUBLIC_SITE_URL,
        },
    }


def _blog_item_list_schema(context):
    if _route_name(context) != "blog":
        return None

    return {
        "@type": "ItemList",
        "name": "Artigos técnicos Smart Control Brasil",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": post["title"],
                "url": _site_url(reverse("institutional:blog_detail", kwargs={"slug": slug})),
                "description": post.get("meta_description", ""),
            }
            for position, (slug, post) in enumerate(BLOG_POSTS.items(), start=1)
        ],
    }


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


def _xyron_robot_product_schema(context):
    robot = _robot(context)
    if not robot:
        return None

    return {
        "@type": "Product",
        "name": robot.get("name", "Robô Xyron"),
        "brand": {
            "@type": "Brand",
            "name": "Xyron Robotics",
        },
        "description": robot.get("description", DEFAULT_DESCRIPTION),
        "url": canonical_url(context),
        "image": _robot_image_url(context),
    }


def _xyron_robot_item_list_schema(context):
    if _route_name(context) != "xyron":
        return None

    return {
        "@type": "ItemList",
        "name": "Robôs Xyron Robotics",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": robot["name"],
                "url": _site_url(reverse(f"institutional:{robot['view']}")),
            }
            for position, robot in enumerate(XYRON_ROBOT_PAGES, start=1)
        ],
    }


def _about_page_schema(context):
    if _route_name(context) != "about":
        return None

    return {
        "@type": "AboutPage",
        "name": _route_metadata(context).get("title", "Empresa Smart Control Brasil"),
        "description": _route_metadata(context).get("description", DEFAULT_DESCRIPTION),
        "url": canonical_url(context),
        "about": {
            "@type": "Organization",
            "name": SOCIAL_SITE_NAME,
            "url": settings.PUBLIC_SITE_URL,
        },
        "mainEntity": {
            "@type": "Organization",
            "name": SOCIAL_SITE_NAME,
            "url": settings.PUBLIC_SITE_URL,
        },
    }


def _contact_page_schema(context):
    if _route_name(context) != "contact":
        return None

    return {
        "@type": "ContactPage",
        "name": _route_metadata(context).get("title", "Contato Smart Control Brasil"),
        "url": canonical_url(context),
        "description": _route_metadata(context).get("description", DEFAULT_DESCRIPTION),
        "about": {"@id": ORGANIZATION_ID},
        "provider": {"@id": ORGANIZATION_ID},
    }


def _service_schema(context):
    route_name = _route_name(context)
    if route_name == "xyron":
        return {
            "@type": "Service",
            "name": "Soluções de Robótica Xyron Robotics",
            "description": _route_metadata(context).get("description", DEFAULT_DESCRIPTION),
            "url": canonical_url(context),
            "provider": {
                "@type": "Organization",
                "name": SOCIAL_SITE_NAME,
                "url": settings.PUBLIC_SITE_URL,
            },
            "brand": {
                "@type": "Brand",
                "name": "Xyron Robotics",
            },
            "serviceType": [
                "Robótica educacional",
                "Robótica para atendimento",
                "Robótica para segurança e monitoramento",
                "Robótica para serviços e aplicações profissionais",
            ],
        }

    if route_name == "sistemas_websites_python":
        return {
            "@type": "Service",
            "name": "Desenvolvimento de Sistemas Web e Soluções em Python",
            "description": _route_metadata(context).get("description", DEFAULT_DESCRIPTION),
            "url": canonical_url(context),
            "provider": {
                "@type": "Organization",
                "name": SOCIAL_SITE_NAME,
                "url": settings.PUBLIC_SITE_URL,
            },
            "serviceType": [
                "Desenvolvimento de sistemas web",
                "Websites empresariais",
                "Aplicações Python",
                "Aplicações Django",
                "APIs e integrações",
                "Dashboards e portais empresariais",
            ],
        }

    if route_name == "mitsubishi_automacao_industrial":
        return {
            "@type": "Service",
            "name": "Automação Industrial Mitsubishi Electric",
            "description": _route_metadata(context).get("description", DEFAULT_DESCRIPTION),
            "url": canonical_url(context),
            "provider": {
                "@type": "Organization",
                "name": SOCIAL_SITE_NAME,
                "url": settings.PUBLIC_SITE_URL,
            },
            "serviceType": [
                "Integração de automação industrial",
                "Programação de CLP",
                "Integração de IHM",
                "Parametrização de inversores",
                "Retrofit de automação",
                "Comissionamento",
            ],
        }

    if route_name == "manutencao_industrial_campo":
        return {
            "@type": "Service",
            "name": "Manutenção Industrial e Assistência Técnica em Campo",
            "description": _route_metadata(context).get("description", DEFAULT_DESCRIPTION),
            "url": canonical_url(context),
            "provider": {
                "@type": "Organization",
                "name": SOCIAL_SITE_NAME,
                "url": settings.PUBLIC_SITE_URL,
            },
            "serviceType": [
                "Manutenção preventiva",
                "Manutenção corretiva",
                "Diagnóstico técnico",
                "Comissionamento",
                "Retrofit",
            ],
        }

    if route_name != "services":
        return None

    return {
        "@type": "Service",
        "name": "Serviços de Automação, Robótica, Manutenção e Sistemas",
        "description": _route_metadata(context).get("description", DEFAULT_DESCRIPTION),
        "url": canonical_url(context),
        "provider": {
            "@type": "Organization",
            "name": SOCIAL_SITE_NAME,
            "url": settings.PUBLIC_SITE_URL,
        },
        "serviceType": [
            "Automação Industrial",
            "Robótica Inteligente",
            "Manutenção Industrial",
            "Sistemas e Soluções Digitais",
        ],
    }


def _faq_page_schema(context):
    post = _post(context)
    if post and post.get("faq"):
        return {
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item["answer"],
                    },
                }
                for item in post["faq"]
            ],
        }

    route_name = _route_name(context)
    robot = _robot(context)
    if route_name == "home":
        faqs = [
            (
                "Como começa um projeto com a Smart Control Brasil?",
                "Começamos com uma análise detalhada do cenário atual, dos gargalos da operação e das metas de retorno do projeto. A partir desse diagnóstico, definimos a melhor arquitetura técnica para atender às necessidades reais da empresa.",
            ),
            (
                "Quais soluções de automação industrial são desenvolvidas?",
                "Desenvolvemos programação de CLPs Mitsubishi Electric, integração de inversores e servoacionamentos, sistemas SCADA, interfaces IHM e redes industriais com foco em eficiência, continuidade e alta disponibilidade.",
            ),
            (
                "Onde os robôs Xyron podem ser aplicados?",
                "Os robôs móveis autônomos podem atuar em recepção corporativa, segurança, demonstrações tecnológicas, ações promocionais, educação, transporte logístico e experiências interativas em diferentes ambientes.",
            ),
            (
                "A Smart Control Brasil oferece suporte após a implantação?",
                "Sim. Oferecemos sustentação técnica, manutenção preventiva, diagnóstico de falhas, suporte especializado e expansões programadas para preservar a confiabilidade e acompanhar a evolução do sistema implantado.",
            ),
        ]
    elif robot and robot.get("key") == "carebot":
        faqs = [
            (
                "O que é o CareBot?",
                "É o robô da linha Xyron Robotics direcionado a apoio assistivo e interação em ambientes de saúde, atendimento e cuidado.",
            ),
            (
                "O CareBot substitui profissionais de saúde?",
                "Não. O CareBot não substitui médicos, enfermeiros, farmacêuticos ou outros profissionais de saúde; sua aplicação deve ser tratada como apoio assistivo e tecnológico.",
            ),
            (
                "Em quais tipos de ambiente o CareBot pode ser avaliado?",
                "Ele pode ser avaliado para residências, clínicas, hospitais, farmácias e ambientes de saúde e atendimento, conforme objetivo assistivo, infraestrutura e responsáveis locais.",
            ),
            (
                "O que deve ser considerado antes de implantar uma solução robótica em saúde?",
                "É importante avaliar finalidade, ambiente, fluxo, pessoas envolvidas, privacidade, infraestrutura, responsabilidades e integração à rotina de atendimento.",
            ),
        ]
    elif robot and robot.get("key") == "hostbot":
        faqs = [
            (
                "O que é o HostBot?",
                "É o robô host da linha Xyron Robotics para recepção, eventos e comunicação visual com visitantes.",
            ),
            (
                "Para quais tipos de ambiente o HostBot pode ser utilizado?",
                "Ele pode ser avaliado para recepção, eventos, empresas, museus, galerias e bancos, conforme objetivo da experiência, fluxo de visitantes e conteúdo a apresentar.",
            ),
            (
                "Qual a diferença entre HostBot e Neo Bot?",
                "O HostBot enfatiza função host, duas telas e comunicação visual para recepção e eventos; o Neo Bot é apresentado como robô de recepção e atendimento, com diálogo multilíngue, IA e apoio à apresentação de produtos.",
            ),
            (
                "O que deve ser avaliado antes de implantar um robô de recepção ou eventos?",
                "É importante avaliar objetivo, ambiente, fluxo de pessoas, conteúdo, interação esperada, infraestrutura, responsáveis e critérios para medir a experiência.",
            ),
        ]
    elif robot and robot.get("key") == "buddy_bot":
        faqs = [
            (
                "O que é o Buddy Bot?",
                "O Buddy Bot é um robô quadrúpede voltado a inspeção, segurança patrimonial, engenharia, obras e áreas de difícil acesso.",
            ),
            (
                "Em quais tipos de aplicação o Buddy Bot pode ser utilizado?",
                "Ele pode ser avaliado para inspeção, segurança patrimonial, engenharia, obras e áreas em que o acesso exige análise cuidadosa de mobilidade, ambiente e operação.",
            ),
            (
                "Como um robô quadrúpede pode apoiar uma inspeção?",
                "Ele pode servir como plataforma móvel de apoio para observação e acompanhamento de áreas compatíveis, desde que a tarefa, o ambiente e os responsáveis estejam definidos.",
            ),
            (
                "O que deve ser avaliado antes de implantar um robô para inspeção?",
                "É importante avaliar superfície, obstáculos, acesso, risco, tarefa, infraestrutura, rotina de operação e equipe responsável pelo acompanhamento.",
            ),
        ]
    elif robot and robot.get("key") == "hygibot_dune_bot":
        faqs = [
            (
                "O que é o HygiBot / Dune Bot?",
                "O HygiBot / Dune Bot é uma solução de limpeza autônoma para grandes áreas, com funções de lavar, varrer, aspirar e passar pano conforme a aplicação avaliada.",
            ),
            (
                "Quais tipos de limpeza o HygiBot / Dune Bot pode realizar?",
                "A solução reúne modos de lavar, varrer, aspirar e passar pano. A escolha do modo depende do piso, do tipo de sujeira, da rotina e do ambiente.",
            ),
            (
                "Em quais ambientes ele pode ser utilizado?",
                "Ele pode ser avaliado para shoppings, indústrias, hospitais e grandes áreas. Em hospitais, a aplicação deve respeitar áreas compatíveis, protocolos locais e restrições da instituição.",
            ),
            (
                "O que deve ser avaliado antes de implantar um robô de limpeza autônoma?",
                "É importante avaliar área, piso, fluxo de pessoas, horários, obstáculos, responsáveis, frequência de limpeza e objetivo operacional. Indicadores e rotina devem orientar a decisão.",
            ),
        ]
    elif robot and robot.get("key") == "waiter_bot":
        faqs = [
            (
                "O que é o Waiter Bot?",
                "O Waiter Bot é uma solução robótica para apoiar entregas internas, deslocamentos e rotinas operacionais em locais de serviço e atendimento.",
            ),
            (
                "Em quais ambientes o Waiter Bot pode ser utilizado?",
                "Ele pode ser avaliado para restaurantes, hotéis, supermercados e outros ambientes de atendimento que tenham rotinas de entrega, deslocamento interno ou apoio operacional.",
            ),
            (
                "Como um robô de entrega pode apoiar uma operação de atendimento?",
                "Ele pode apoiar o transporte de itens e a organização de deslocamentos repetitivos dentro de um fluxo definido, sem substituir a equipe responsável pelo serviço e pela interação com as pessoas.",
            ),
            (
                "O que deve ser avaliado antes de implantar um Waiter Bot?",
                "É importante avaliar o fluxo, o ambiente, o tipo de item movimentado, os pontos de origem e entrega, a circulação de pessoas e os responsáveis operacionais pelo processo.",
            ),
        ]
    elif robot and robot.get("key") == "mowerbot":
        faqs = [
            (
                "O que é o MowerBot?",
                "É uma solução da linha Xyron Robotics voltada a corte de grama por controle remoto em aplicações externas compatíveis.",
            ),
            (
                "O MowerBot é autônomo ou operado por controle remoto?",
                "O posicionamento atual descreve operação por controle remoto, com um responsável conduzindo a atividade. A aplicação não deve ser tratada como promessa de operação autônoma sem acompanhamento.",
            ),
            (
                "Em quais tipos de terreno o MowerBot pode ser avaliado?",
                "O conteúdo atual cita terrenos irregulares, taludes, praças e grandes áreas externas. Cada cenário precisa de avaliação técnica de acesso, inclinação, obstáculos e rotina operacional.",
            ),
            (
                "O que deve ser avaliado antes de utilizar um robô cortador de grama?",
                "É importante avaliar tipo de terreno, inclinação, obstáculos, circulação de pessoas, área total, condições do ambiente, plano de operação e responsável pela condução remota.",
            ),
        ]
    elif robot and robot.get("key") == "neo_bot":
        faqs = [
            (
                "O que é o Neo Bot?",
                "O Neo Bot é um robô de recepção e atendimento voltado a interação com visitantes, diálogo multilíngue, IA e apoio à apresentação de produtos.",
            ),
            (
                "Em quais ambientes o Neo Bot pode ser usado?",
                "Ele pode ser avaliado para recepção corporativa, atendimento, eventos, showrooms e apresentação de produtos, conforme objetivo da experiência e infraestrutura disponível.",
            ),
            (
                "Como o Neo Bot pode apoiar uma recepção?",
                "Ele pode atuar como interface tecnológica para orientar o primeiro contato, apresentar informações e apoiar a experiência do visitante, sem substituir a equipe responsável pelo atendimento.",
            ),
            (
                "O Neo Bot pode ser integrado a um projeto de atendimento?",
                "A avaliação deve começar pelo fluxo de atendimento, objetivo da interação, informações a apresentar e responsabilidades da equipe. Quando houver integração digital no projeto, ela deve ser especificada tecnicamente antes da implantação.",
            ),
        ]
    elif robot and robot.get("key") == "orbit":
        faqs = [
            (
                "O que é o Orbit Bot / Patrol Bot?",
                "O Orbit Bot / Patrol Bot é um robô Xyron voltado a apoiar patrulhamento, segurança e monitoramento em grandes áreas, combinando deslocamento autônomo, visão inteligente e acompanhamento em tempo real.",
            ),
            (
                "Onde o Orbit pode ser aplicado?",
                "Ele pode ser avaliado para condomínios, empresas, áreas corporativas e ambientes extensos que precisem de apoio a rondas, presença operacional e monitoramento.",
            ),
            (
                "O Orbit substitui uma equipe de segurança?",
                "Não. O Orbit deve ser avaliado como apoio tecnológico para patrulhamento e monitoramento, e não como substituto de planejamento, protocolos ou atuação humana.",
            ),
            (
                "Como avaliar uma aplicação do Orbit?",
                "Entre em contato com a Smart Control Brasil para apresentar o ambiente, a rotina de segurança, os pontos de circulação e o objetivo da aplicação.",
            ),
        ]
    elif robot and robot.get("key") == "littlebot":
        faqs = [
            (
                "O que é o LIRO / Little Bot?",
                "O LIRO / Little Bot é um robô interativo que permite criar experiências envolvendo robótica, tecnologia, comunicação e interação com pessoas.",
            ),
            (
                "O LIRO / Little Bot pode ser utilizado em escolas?",
                "Sim. O ambiente educacional é uma das aplicações mais interessantes para o LIRO / Little Bot, especialmente em iniciativas relacionadas à robótica, tecnologia, inovação e experiências STEM.",
            ),
            (
                "É possível realizar uma demonstração?",
                "Entre em contato com a Smart Control Brasil para apresentar sua instituição e sua aplicação. Nossa equipe poderá avaliar as possibilidades de demonstração do LIRO / Little Bot.",
            ),
            (
                "Como posso levar o LIRO / Little Bot para minha instituição?",
                "Envie uma mensagem para nossa equipe informando o tipo de instituição, objetivo da aplicação e cidade. A Smart Control Brasil entrará em contato para avaliar a melhor solução.",
            ),
        ]
    elif route_name == "xyron":
        faqs = [
            (
                "Quais tipos de robôs a Xyron oferece?",
                "A linha inclui robôs educacionais, recepção, patrulhamento, segurança, limpeza, entrega, saúde e robôs quadrúpedes para inspeção.",
            ),
            (
                "Os robôs podem ser usados em escolas?",
                "Sim. O LIRO / Little Bot foi criado para educação, interação, aprendizagem e apoio em ambientes escolares e experiências de tecnologia.",
            ),
            (
                "A Smart Control Brasil faz a implantação?",
                "A Smart Control Brasil atua na análise da aplicação, indicação da solução, integração, infraestrutura e acompanhamento do projeto.",
            ),
            (
                "É possível integrar robôs com sistemas existentes?",
                "Sim. Dependendo da aplicação, é possível integrar robôs, câmeras, sensores, controle de acesso, software, monitoramento e relatórios.",
            ),
            (
                "Como solicitar uma demonstração ou proposta?",
                "Entre em contato com a Smart Control Brasil para avaliar o ambiente, o objetivo da operação e a solução Xyron mais adequada.",
            ),
        ]
    elif route_name == "contact":
        faqs = CONTACT_PAGE_FAQS
    elif route_name == "services":
        faqs = [
            (
                "Quais serviços a Smart Control Brasil oferece?",
                "Atuamos com automação industrial, robótica inteligente, manutenção industrial e desenvolvimento de sistemas e soluções digitais, integrando engenharia e tecnologia conforme a necessidade de cada projeto.",
            ),
            (
                "Vocês desenvolvem soluções personalizadas?",
                "Sim. Avaliamos cada aplicação para definir a arquitetura, equipamentos, integração e suporte mais adequados às necessidades técnicas e operacionais do cliente.",
            ),
            (
                "A Smart Control Brasil realiza atendimento técnico em campo?",
                "Sim. Prestamos suporte técnico e manutenção em campo, incluindo diagnóstico de falhas, intervenções em equipamentos e apoio à confiabilidade operacional.",
            ),
            (
                "Como solicitar uma avaliação ou proposta?",
                "Entre em contato com nossa equipe e descreva sua necessidade. A partir das informações iniciais, avaliamos o escopo e orientamos os próximos passos técnicos e comerciais.",
            ),
        ]
    elif route_name == "sistemas_websites_python":
        faqs = [
            (
                "Vocês desenvolvem sistemas totalmente personalizados?",
                "Sim. Analisamos os processos, usuários, dados e objetivos da empresa para desenvolver um sistema alinhado à operação, sem limitar o projeto a uma solução genérica.",
            ),
            (
                "Quais tecnologias podem ser utilizadas no projeto?",
                "Trabalhamos com Python, Django, bancos de dados relacionais, APIs, interfaces web responsivas e serviços de inteligência artificial conforme a necessidade da aplicação.",
            ),
            (
                "É possível integrar inteligência artificial ao sistema?",
                "Sim. A IA pode apoiar atendimento, busca de informações, classificação, geração de conteúdo, análise de dados e automação, desde que faça sentido para o processo.",
            ),
            (
                "O sistema pode se integrar a outras plataformas?",
                "Sim. Podemos criar integrações por API com serviços externos, sistemas internos, ferramentas de comunicação, meios de pagamento e outras fontes de dados.",
            ),
        ]
    elif route_name == "mitsubishi_automacao_industrial":
        faqs = [
            (
                "A Smart Control Brasil vende componentes Mitsubishi Electric?",
                "A Smart Control Brasil atua no apoio técnico, aplicação, especificação, integração e direcionamento das soluções Mitsubishi Electric conforme a necessidade do projeto.",
            ),
            (
                "Vocês ajudam a escolher CLP, IHM, inversor ou servo?",
                "Sim. Avaliamos sinais, comunicação, potência, movimento, operação, manutenção e expansão futura para orientar a melhor arquitetura técnica.",
            ),
            (
                "É possível modernizar máquinas antigas?",
                "Sim. O retrofit pode atualizar CLP, IHM, inversores, servos, painéis, redes, segurança, documentação e diagnóstico para prolongar o ciclo de vida da máquina.",
            ),
            (
                "Vocês trabalham com robôs industriais?",
                "Sim. Apoiamos aplicações de robôs industriais em manipulação, montagem, embalagem, pick and place e integração com máquinas e células automatizadas.",
            ),
            (
                "Preciso saber qual produto Mitsubishi utilizar?",
                "Não. O ideal é começar pelo diagnóstico. A partir dele, definimos a necessidade de CLP, IHM, inversor, servo, robô, supervisório, rede ou integração de dados.",
            ),
        ]
    elif route_name == "manutencao_industrial_campo":
        faqs = [
            (
                "Vocês fazem manutenção de robôs Xyron?",
                "Não executamos manutenção de campo dos robôs Xyron Robotics. Atuamos na comercialização e integração; o suporte e a manutenção oficial permanecem com a Xyron e sua rede autorizada.",
            ),
            (
                "Minha empresa precisa de TPM mesmo sendo pequena?",
                "Sim, desde que aplicado com bom senso. A empresa pode começar organizando ativos, rotinas, inspeções, responsabilidades e as principais perdas, sem criar uma estrutura excessivamente complexa.",
            ),
            (
                "Qual a diferença entre preventiva e confiabilidade?",
                "A preventiva estabelece rotinas planejadas para reduzir falhas. A confiabilidade analisa o comportamento dos ativos, recorrências, histórico e indicadores para melhorar as decisões técnicas.",
            ),
            (
                "Vocês ajudam a estruturar indicadores técnicos?",
                "Sim. Podemos apoiar na organização de MTTR, MTBF, disponibilidade, backlog, preventivas, corretivas e recorrência de falhas, conforme a maturidade e a necessidade da operação.",
            ),
        ]
    else:
        return None
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": answer,
                },
            }
            for question, answer in faqs
        ],
    }


def _structured_data_graph(context):
    if robots_directives(context):
        return []

    graph = []
    if _route_name(context) == "home":
        graph.extend([_organization_schema(), _website_schema()])
        faq_page = _faq_page_schema(context)
        if faq_page:
            graph.append(faq_page)

    if _route_name(context) == "contact":
        graph.append(_organization_schema())
        contact_page = _contact_page_schema(context)
        if contact_page:
            graph.append(contact_page)

    breadcrumbs = _breadcrumb_items(context)
    if breadcrumbs:
        graph.append(_breadcrumb_schema(breadcrumbs))

    about_page = _about_page_schema(context)
    if about_page:
        graph.append(about_page)

    blog_schema = _blog_schema(context)
    if blog_schema:
        graph.append(blog_schema)

    blog_item_list = _blog_item_list_schema(context)
    if blog_item_list:
        graph.append(blog_item_list)

    service = _service_schema(context)
    if service:
        graph.append(service)

    xyron_item_list = _xyron_robot_item_list_schema(context)
    if xyron_item_list:
        graph.append(xyron_item_list)

    if _route_name(context) in {
        "contact",
        "services",
        "xyron",
        "manutencao_industrial_campo",
        "mitsubishi_automacao_industrial",
        "sistemas_websites_python",
    }:
        faq_page = _faq_page_schema(context)
        if faq_page:
            graph.append(faq_page)

    article = _article_schema(context)
    if article:
        graph.append(article)
        faq_page = _faq_page_schema(context)
        if faq_page:
            graph.append(faq_page)

    product = _product_schema(context)
    if product:
        graph.append(product)

    robot_product = _xyron_robot_product_schema(context)
    if robot_product:
        graph.append(robot_product)
        faq_page = _faq_page_schema(context)
        if faq_page:
            graph.append(faq_page)

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
        return post.get("seo_title") or f"{post.get('title', DEFAULT_TITLE)} | Smart Control Brasil"

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
    return (
        _post_image_url(context)
        or _product_image_url(context)
        or _robot_image_url(context)
        or _route_social_image_url(context)
        or _static_public_url(DEFAULT_SOCIAL_IMAGE)
    )


@register.simple_tag(takes_context=True)
def social_image_width(context):
    if _post(context) or _product(context) or _robot(context):
        return ""
    return _route_metadata(context).get("social_image_width", DEFAULT_SOCIAL_IMAGE_WIDTH)


@register.simple_tag(takes_context=True)
def social_image_height(context):
    if _post(context) or _product(context) or _robot(context):
        return ""
    return _route_metadata(context).get("social_image_height", DEFAULT_SOCIAL_IMAGE_HEIGHT)


@register.simple_tag(takes_context=True)
def social_image_alt(context):
    if _post(context):
        return _post(context).get("alt", "")
    if _product(context):
        return getattr(_product(context), "name", "")
    if _robot(context):
        return _robot(context).get("alt", "")
    return _route_metadata(context).get("social_image_alt", DEFAULT_SOCIAL_IMAGE_ALT)


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

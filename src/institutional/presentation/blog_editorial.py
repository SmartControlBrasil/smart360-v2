from src.institutional.presentation.authors import DEFAULT_AUTHOR_SLUG
from src.institutional.presentation.authors import get_author


BLOG_POST_EDITORIAL = {
    "selecao-controladores-ativos-alta-severidade": {
        "author_slug": DEFAULT_AUTHOR_SLUG,
        "date_published": "2026-08-01",
        "date_modified": "2026-08-24",
        "intro_commit": "35b13e6bbeb1e9175e7ff98e13e3fbddae6970da",
        "last_edit_commit": "9e516d9b8890e63c22f3c2577e46b167f7921df7",
        "last_edit_evidence": "seo: deepen controller selection article",
    },
    "convergencia-robotica-ia-firmwares-dedicados": {
        "author_slug": DEFAULT_AUTHOR_SLUG,
        "date_published": "2026-08-01",
        "date_modified": "2026-08-24",
        "intro_commit": "35b13e6bbeb1e9175e7ff98e13e3fbddae6970da",
        "last_edit_commit": "e294ef73fdfc04e61aec4256ceb7fe2290a2aa00",
        "last_edit_evidence": "seo: deepen robotics ai firmware article",
    },
    "eliminar-gargalos-autonomia-previsibilidade": {
        "author_slug": DEFAULT_AUTHOR_SLUG,
        "date_published": "2026-08-01",
        "date_modified": "2026-08-24",
        "intro_commit": "35b13e6bbeb1e9175e7ff98e13e3fbddae6970da",
        "last_edit_commit": "658ad14b7661a95b4eafd05351472b8edc955a79",
        "last_edit_evidence": "seo: deepen operational bottlenecks article",
    },
    "informacao-precisa-para-agir-melhor": {
        "author_slug": DEFAULT_AUTHOR_SLUG,
        "date_published": "2026-08-01",
        "date_modified": "2026-08-24",
        "intro_commit": "35b13e6bbeb1e9175e7ff98e13e3fbddae6970da",
        "last_edit_commit": "612f7dae4750518cd0d4db9ff6946d02c93d8ab4",
        "last_edit_evidence": "seo: deepen industrial data integration article",
    },
    "equipamentos-sistemas-para-evoluir": {
        "author_slug": DEFAULT_AUTHOR_SLUG,
        "date_published": "2026-08-01",
        "date_modified": "2026-08-24",
        "intro_commit": "35b13e6bbeb1e9175e7ff98e13e3fbddae6970da",
        "last_edit_commit": "e78c51154e3f61706d44d484b9148ff096e5efd1",
        "last_edit_evidence": "seo: deepen industrial modernization article",
    },
    "inovacao-que-aparece-e-gera-valor": {
        "author_slug": DEFAULT_AUTHOR_SLUG,
        "date_published": "2026-08-01",
        "date_modified": "2026-08-24",
        "intro_commit": "35b13e6bbeb1e9175e7ff98e13e3fbddae6970da",
        "last_edit_commit": "9a3ab61fe7cbf2d694a19404e22c89378ccf3648",
        "last_edit_evidence": "seo: strengthen xyron product pages and content clusters",
    },
    "reducao-paradas-inesperadas-planejamento-tecnico": {
        "author_slug": DEFAULT_AUTHOR_SLUG,
        "date_published": "2026-08-01",
        "date_modified": "2026-08-24",
        "intro_commit": "35b13e6bbeb1e9175e7ff98e13e3fbddae6970da",
        "last_edit_commit": "0ea845b237e3f393dc372656f40cdb7291489eb0",
        "last_edit_evidence": "seo: deepen maintenance planning article",
    },
    "historico-indicadores-decisoes-consistentes": {
        "author_slug": DEFAULT_AUTHOR_SLUG,
        "date_published": "2026-08-01",
        "date_modified": "2026-08-24",
        "intro_commit": "35b13e6bbeb1e9175e7ff98e13e3fbddae6970da",
        "last_edit_commit": "9a3ab61fe7cbf2d694a19404e22c89378ccf3648",
        "last_edit_evidence": "seo: strengthen xyron product pages and content clusters",
    },
    "menos-retrabalho-rastreabilidade-retrofit": {
        "author_slug": DEFAULT_AUTHOR_SLUG,
        "date_published": "2026-08-01",
        "date_modified": "2026-08-24",
        "intro_commit": "35b13e6bbeb1e9175e7ff98e13e3fbddae6970da",
        "last_edit_commit": "9a3ab61fe7cbf2d694a19404e22c89378ccf3648",
        "last_edit_evidence": "seo: strengthen xyron product pages and content clusters",
    },
}


def format_date_br(iso_date: str) -> str:
    year, month, day = iso_date.split("-")
    return f"{day}/{month}/{year}"


def enrich_blog_post(slug, post):
    editorial = BLOG_POST_EDITORIAL[slug]
    author = get_author(editorial["author_slug"])
    date_published = editorial["date_published"]
    date_modified = editorial["date_modified"]
    return {
        "slug": slug,
        **post,
        **editorial,
        "author_name": author.name,
        "author_job_title": author.job_title,
        "author_short_bio": author.short_bio,
        "author_url_name": "institutional:author_detail",
        "author_url_kwargs": {"slug": author.slug},
        "date_published_display": format_date_br(date_published),
        "date_modified_display": format_date_br(date_modified),
        "dates_differ": date_published != date_modified,
    }


def posts_for_author(author_slug):
    from src.institutional.presentation.blog_posts import BLOG_POSTS

    return [
        enrich_blog_post(slug, post)
        for slug, post in BLOG_POSTS.items()
        if BLOG_POST_EDITORIAL[slug]["author_slug"] == author_slug
    ]

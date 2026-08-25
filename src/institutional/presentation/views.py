import logging
from types import SimpleNamespace
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from django.core.mail import EmailMessage
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from src.institutional.application.get_home_page import GetHomePage
from src.institutional.presentation.blog_posts import BLOG_POSTS, BLOG_POSTS_LIST
from src.institutional.presentation.forms import ContactForm
from src.institutional.presentation.xyron_robot_pages import XYRON_ROBOT_PAGE_BY_KEY


logger = logging.getLogger(__name__)



BLOG_SOLUTION_LINKS = {
    "selecao-controladores-ativos-alta-severidade": {
        "url_name": "institutional:mitsubishi_automacao_industrial",
        "label": "automação industrial Mitsubishi",
        "summary": "Veja soluções Mitsubishi Electric para CLPs, IHMs, inversores e integração industrial.",
    },
    "convergencia-robotica-ia-firmwares-dedicados": {
        "url_name": "institutional:xyron",
        "label": "robótica inteligente Xyron",
        "summary": "Veja como a Smart Control Brasil aplica robótica inteligente em soluções Xyron.",
    },
    "eliminar-gargalos-autonomia-previsibilidade": {
        "url_name": "institutional:manutencao_industrial_campo",
        "label": "manutenção industrial e confiabilidade",
        "summary": "Conecte gargalos, previsibilidade e rotina técnica a uma estratégia de manutenção industrial.",
    },
    "informacao-precisa-para-agir-melhor": {
        "url_name": "institutional:sistemas_websites_python",
        "label": "sistemas web, APIs e dashboards",
        "summary": "Transforme dados operacionais em sistemas, integrações e dashboards sob medida.",
    },
    "equipamentos-sistemas-para-evoluir": {
        "url_name": "institutional:sistemas_websites_python",
        "label": "sistemas Python e Django",
        "summary": "Conheça sistemas empresariais e integrações digitais sob medida.",
    },
    "inovacao-que-aparece-e-gera-valor": {
        "url_name": "institutional:xyron",
        "label": "soluções robóticas Xyron",
        "summary": "Conheça aplicações comerciais de robótica para atendimento, segurança e interação.",
    },
    "reducao-paradas-inesperadas-planejamento-tecnico": {
        "url_name": "institutional:manutencao_industrial_campo",
        "label": "manutenção industrial em campo",
        "summary": "Conecte o planejamento técnico a um atendimento de manutenção industrial.",
    },
    "historico-indicadores-decisoes-consistentes": {
        "url_name": "institutional:manutencao_industrial_campo",
        "label": "manutenção orientada por indicadores",
        "summary": "Organize histórico, indicadores e prioridades dentro de uma estratégia de manutenção industrial.",
    },
    "menos-retrabalho-rastreabilidade-retrofit": {
        "url_name": "institutional:manutencao_industrial_campo",
        "label": "manutenção, retrofit e levantamento técnico",
        "summary": "Use documentação, rastreabilidade e diagnóstico para preparar intervenções e retrofit com menor risco.",
    },
}


def _post_terms(post):
    text = " ".join(
        [
            post.get("title", ""),
            post.get("category", ""),
            post.get("meta_description", ""),
            post.get("intro", ""),
        ]
        + [section.get("heading", "") for section in post.get("sections", [])]
    ).lower()
    punctuation = ".,;:!?()[]{}\"'"
    terms = [term.strip(punctuation) for term in text.split()]
    return {term for term in terms if len(term) > 4}


def _related_blog_posts(slug, limit=3):
    current = BLOG_POSTS[slug]
    current_terms = _post_terms(current)
    current_solution = BLOG_SOLUTION_LINKS.get(slug, {}).get("url_name")
    scored_posts = []

    for position, (related_slug, related_post) in enumerate(BLOG_POSTS.items()):
        if related_slug == slug:
            continue

        score = 0
        if related_post.get("category") == current.get("category"):
            score += 100
        if BLOG_SOLUTION_LINKS.get(related_slug, {}).get("url_name") == current_solution:
            score += 50
        score += len(current_terms & _post_terms(related_post))
        scored_posts.append((-score, position, {"slug": related_slug, **related_post}))

    scored_posts.sort()
    return [post for _, _, post in scored_posts[:limit]]



def _safe_next_url(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse("institutional:home")


def _permanent_redirect_to_route(request, route_name, **kwargs):
    url = reverse(route_name, kwargs=kwargs)
    query_string = request.META.get("QUERY_STRING")
    if query_string:
        url = f"{url}?{query_string}"
    return redirect(url, permanent=True)


def legacy_about(request):
    return _permanent_redirect_to_route(request, "institutional:about")


def legacy_mitsubishi_automation(request):
    return _permanent_redirect_to_route(request, "institutional:mitsubishi_automacao_industrial")


def legacy_xyron_robotics(request):
    return _permanent_redirect_to_route(request, "institutional:xyron")


def legacy_automacao_industrial_conectada_gestao(request):
    return _permanent_redirect_to_route(
        request,
        "institutional:blog_detail",
        slug="informacao-precisa-para-agir-melhor",
    )


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /painel/",
        "Disallow: /login/",
        "Disallow: /logout/",
        "Disallow: /cadastro/",
        "Disallow: /api/",
        "",
        f"Sitemap: {settings.PUBLIC_SITE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


class InstitutionalLoginView(LoginView):
    template_name = "institutional/auth/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return _safe_next_url(self.request)


class InstitutionalLogoutView(LogoutView):
    next_page = "institutional:home"


def signup(request):
    if request.user.is_authenticated:
        return redirect(_safe_next_url(request))

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(_safe_next_url(request))
    else:
        form = UserCreationForm()

    return render(
        request,
        "institutional/auth/signup.html",
        {
            "form": form,
            "next": request.POST.get("next") or request.GET.get("next", ""),
        },
    )


def home(request):
    page = GetHomePage().execute()
    return render(
        request,
        "institutional/demos/smart-control-brasil.html",
        {"page": page},
    )


def smart_control_brasil(request):
    page = GetHomePage().execute()
    return render(
        request,
        "institutional/demos/smart-control-brasil.html",
        {"page": page},
    )


def sistemas_websites_python(request):
    return render(request, "institutional/demos/sistemas-websites-python.html")


def livia(request):
    return render(request, "institutional/demos/livia.html")


def camaras_climaticas(request):
    return render(request, "institutional/demos/camaras-climaticas.html")


def manutencao_industrial_campo(request):
    return render(request, "institutional/demos/manutencao-industrial-campo.html")


def ai_video_interaction_platform(request):
    return render(request, "institutional/demos/ai-video-interaction-platform.html")


def xyron(request):
    return render(request, "institutional/demos/xyron.html")


def _render_xyron_robot(request, key):
    robot = XYRON_ROBOT_PAGE_BY_KEY[key]
    page = SimpleNamespace(
        metadata=SimpleNamespace(
            title=robot["title"],
            description=robot["description"],
            canonical_path=f"/xyron/{robot['slug']}/",
        )
    )
    return render(request, robot["template"], {"page": page, "robot": robot})


def xyron_littlebot(request):
    return _render_xyron_robot(request, "littlebot")


def xyron_orbit(request):
    return _render_xyron_robot(request, "orbit")


def xyron_neo_bot(request):
    return _render_xyron_robot(request, "neo_bot")


def xyron_waiter_bot(request):
    return _render_xyron_robot(request, "waiter_bot")


def xyron_hygibot_dune_bot(request):
    return _render_xyron_robot(request, "hygibot_dune_bot")


def xyron_buddy_bot(request):
    return _render_xyron_robot(request, "buddy_bot")


def xyron_carebot(request):
    return _render_xyron_robot(request, "carebot")


def xyron_hostbot(request):
    return _render_xyron_robot(request, "hostbot")


def xyron_mowerbot(request):
    return _render_xyron_robot(request, "mowerbot")


def robotica_educacional(request):
    return render(request, "institutional/landing/robotica-educacional.html")


def robo_seguranca_condominios(request):
    return render(request, "institutional/landing/robo-seguranca-condominios.html")


def disabled_commercial_landing(request):
    raise Http404("Landing page temporariamente desabilitada.")


def camara_climatica(request):
    return render(request, "institutional/landing/camara-climatica.html")


def ai_web_solutions_startups(request):
    return render(request, "institutional/demos/ai-web-solutions-startups.html")


def engenharia_serralheria_industrial(request):
    return render(request, "institutional/demos/engenharia-serralheria-industrial.html")


def mitsubishi_automacao_industrial(request):
    return render(request, "institutional/demos/mitsubishi-automacao-industrial.html")


def about(request):
    return render(request, "institutional/pages/about.html")


def services(request):
    return render(request, "institutional/pages/service.html")


def blog(request):
    return render(
        request,
        "institutional/pages/blog.html",
        {"blog_posts": BLOG_POSTS_LIST},
    )


def blog_list(request):
    return redirect("institutional:blog", permanent=True)


def blog_detail(request, slug):
    post = BLOG_POSTS.get(slug)
    if post is None:
        raise Http404("Artigo tecnico nao encontrado.")

    related_posts = _related_blog_posts(slug)

    solution_link = BLOG_SOLUTION_LINKS.get(slug)

    return render(
        request,
        "institutional/pages/blog_detail.html",
        {
            "post": {"slug": slug, **post},
            "related_posts": related_posts,
            "solution_link": solution_link,
        },
    )


def blog_details(request):
    return redirect(
        "institutional:blog_detail",
        slug="selecao-controladores-ativos-alta-severidade",
        permanent=True,
    )


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            recipient_email = getattr(
                settings,
                "CONTACT_RECIPIENT_EMAIL",
                "comercial@smartcontrolbrasil.com.br",
            )
            subject = f"[Site Smart Control Brasil] {data['assunto']}"
            body = "\n".join(
                [
                    "Nova solicitacao recebida pelo site Smart Control Brasil",
                    "",
                    "Nome:",
                    data["nome"],
                    "",
                    "E-mail:",
                    data["email"],
                    "",
                    "Telefone / WhatsApp:",
                    data["telefone"],
                    "",
                    "Empresa:",
                    data["empresa"] or "Nao informado",
                    "",
                    "Assunto:",
                    data["assunto"],
                    "",
                    "Mensagem:",
                    data["mensagem"],
                    "",
                    "Consentimento de privacidade:",
                    "Autorizado",
                ]
            )

            try:
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient_email],
                    reply_to=[data["email"]],
                )
                email.send()
            except Exception:
                logger.exception("Falha ao enviar formulario de contato do site.")
                messages.error(
                    request,
                    "Não foi possível enviar sua solicitação agora. Tente novamente em alguns instantes.",
                )
            else:
                messages.success(
                    request,
                    "Solicitação enviada com sucesso. Nossa equipe entrará em contato.",
                )
                return redirect("institutional:contact")
        else:
            messages.error(
                request,
                "Revise os dados informados e tente novamente.",
            )
    else:
        form = ContactForm()

    return render(
        request,
        "institutional/pages/contact.html",
        {"form": form},
    )

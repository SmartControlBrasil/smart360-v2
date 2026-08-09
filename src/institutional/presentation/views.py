import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
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


logger = logging.getLogger(__name__)


def _safe_next_url(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse("institutional:experience_center_play")


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /login/",
        "Disallow: /logout/",
        "Disallow: /cadastro/",
        "Disallow: /experience-center/play/",
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
    next_page = "institutional:experience_center"


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
        "institutional/demos/index_01.html",
        {"page": page},
    )


def home_02(request):
    return render(request, "institutional/demos/index_02.html")


def home_03(request):
    return render(request, "institutional/demos/index_03.html")


def home_04(request):
    return render(request, "institutional/demos/index_04.html")


def home_05(request):
    return render(request, "institutional/demos/index_05.html")


def home_06(request):
    return render(request, "institutional/demos/index_06.html")


def home_07(request):
    return render(request, "institutional/demos/index_07.html")


def home_08(request):
    return render(request, "institutional/demos/index_08.html")


def home_09(request):
    return render(request, "institutional/demos/index_09.html")


def engenharia_serralheria_industrial(request):
    return render(request, "institutional/demos/index_09.html")


def home_10(request):
    return render(request, "institutional/demos/index_10.html")


def about(request):
    return render(request, "institutional/pages/about.html")


def services(request):
    return render(request, "institutional/pages/service.html")


def service_details(request):
    return render(request, "institutional/pages/service_details.html")


def blog(request):
    return render(
        request,
        "institutional/pages/blog.html",
        {"blog_posts": BLOG_POSTS_LIST},
    )


def blog_list(request):
    return render(request, "institutional/pages/blog_list.html")


def blog_detail(request, slug):
    post = BLOG_POSTS.get(slug)
    if post is None:
        raise Http404("Artigo tecnico nao encontrado.")

    related_posts = [
        {"slug": related_slug, **related_post}
        for related_slug, related_post in BLOG_POSTS.items()
        if related_slug != slug
    ][:3]

    return render(
        request,
        "institutional/pages/blog_detail.html",
        {
            "post": {"slug": slug, **post},
            "related_posts": related_posts,
        },
    )


def blog_details(request):
    return blog_detail(request, "selecao-controladores-ativos-alta-severidade")


def team(request):
    return render(request, "institutional/pages/team.html")


def team_details(request):
    return render(request, "institutional/pages/team_details.html")


def projects(request):
    return render(request, "institutional/pages/project.html")


def project_details(request):
    return render(request, "institutional/pages/project_details.html")


def testimonials(request):
    return render(request, "institutional/pages/testimonial.html")


def pricing(request):
    return render(request, "institutional/pages/pricing.html")


def experience_center(request):
    return render(
        request,
        "institutional/pages/experience_center.html",
        {"play_mode": False},
    )


@login_required(login_url="institutional:login")
def experience_center_play(request):
    return render(
        request,
        "institutional/pages/experience_center.html",
        {"play_mode": True},
    )


def cart(request):
    return render(request, "institutional/pages/cart.html")


def wishlist(request):
    return render(request, "institutional/pages/wishlist.html")


def checkout(request):
    return render(request, "institutional/pages/checkout.html")


def shop(request):
    return render(request, "institutional/pages/shop.html")


def shop_details(request):
    return render(request, "institutional/pages/shop_details.html")


def faq(request):
    return render(request, "institutional/pages/faq.html")


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            recipient_email = getattr(
                settings,
                "CONTACT_RECIPIENT_EMAIL",
                "contato@mcautomation.com.br",
            )
            subject = f"[Site MC Automation] {data['assunto']}"
            body = "\n".join(
                [
                    "Nova solicitacao recebida pelo site MC Automation",
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


def error_404_preview(request):
    return render(request, "institutional/pages/error_404.html")

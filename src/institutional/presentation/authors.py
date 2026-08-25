from dataclasses import dataclass


@dataclass(frozen=True)
class Author:
    slug: str
    name: str
    job_title: str
    post_graduation: str
    short_bio: str
    full_bio: str
    knows_about: tuple[str, ...]
    seo_title: str
    seo_description: str
    json_ld_id: str

    @property
    def public_path(self) -> str:
        return f"/autor/{self.slug}/"


MARCELO_CUSTODIO = Author(
    slug="marcelo-custodio",
    name="Marcelo Custodio",
    job_title="Engenheiro de Controle e Automação",
    post_graduation="Pós-graduado em TPM e Inteligência Artificial",
    short_bio=(
        "Marcelo Custodio é engenheiro de Controle e Automação, pós-graduado em TPM e "
        "Inteligência Artificial. Atua na integração entre automação industrial, manutenção, "
        "confiabilidade, sistemas e tecnologias aplicadas à operação."
    ),
    full_bio=(
        "Marcelo Custodio é engenheiro de Controle e Automação, pós-graduado em TPM e "
        "Inteligência Artificial. Atua na integração entre automação industrial, manutenção, "
        "confiabilidade, sistemas e tecnologias aplicadas à operação."
    ),
    knows_about=(
        "Automação industrial",
        "Controle e integração de sistemas",
        "Manutenção e confiabilidade",
        "TPM e gestão de ativos",
        "Desenvolvimento de sistemas",
        "Aplicação prática de tecnologia e inteligência artificial",
    ),
    seo_title="Marcelo Custodio | Engenheiro de Controle e Automação",
    seo_description=(
        "Conheça Marcelo Custodio, engenheiro de Controle e Automação, pós-graduado em TPM "
        "e Inteligência Artificial e autor técnico da Smart Control Brasil."
    ),
    json_ld_id="https://www.smartcontrolbrasil.com.br/autor/marcelo-custodio/#person",
)

AUTHORS = {
    MARCELO_CUSTODIO.slug: MARCELO_CUSTODIO,
}

DEFAULT_AUTHOR_SLUG = MARCELO_CUSTODIO.slug


def get_author(slug=None):
    resolved_slug = slug or DEFAULT_AUTHOR_SLUG
    try:
        return AUTHORS[resolved_slug]
    except KeyError as exc:
        raise KeyError(f"Autor nao encontrado: {resolved_slug}") from exc

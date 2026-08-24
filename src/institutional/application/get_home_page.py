from dataclasses import dataclass

from src.institutional.domain.page import PageMetadata


@dataclass(frozen=True, slots=True)
class HomePageData:
    metadata: PageMetadata
    heading: str
    introduction: str


class GetHomePage:
    def execute(self) -> HomePageData:
        return HomePageData(
            metadata=PageMetadata(
                title="Smart Control Brasil | Automação Industrial, Robótica e Sistemas",
                description=(
                    "Soluções em automação industrial, robótica, manutenção técnica, "
                    "integração de sistemas e desenvolvimento de software para empresas e indústrias."
                ),
                canonical_path="/",
            ),
            heading="Automação Industrial, Robótica e Sistemas para Transformar sua Operação",
            introduction=(
                "Integramos engenharia, automação Mitsubishi Electric, robótica inteligente "
                "Xyron, manutenção industrial e sistemas sob medida para aumentar "
                "produtividade, confiabilidade e eficiência operacional."
            ),
        )

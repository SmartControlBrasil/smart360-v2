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
                title="Smart Control Brasil | Automação, Robótica e Sistemas",
                description=(
                    "Soluções em automação industrial, robótica de serviços, "
                    "manutenção técnica e desenvolvimento de sistemas web."
                ),
                canonical_path="/",
            ),
            heading="Tecnologia aplicada a resultados reais",
            introduction=(
                "Automação industrial, robótica e sistemas inteligentes "
                "desenvolvidos para aumentar eficiência e produtividade."
            ),
        )

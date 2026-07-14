from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageMetadata:
    title: str
    description: str
    canonical_path: str

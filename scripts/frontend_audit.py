#!/usr/bin/env python3
"""Auditoria estática do HTML renderizado (scripts, CSS, imagens)."""

from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import django

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

from django.test import Client, override_settings  # noqa: E402


PAGES = [
    ("Home", "/"),
    ("Empresa", "/empresa/"),
    ("Serviços", "/servicos/"),
    ("Manutenção", "/manutencao-industrial-campo/"),
    ("Mitsubishi", "/mitsubishi-automacao-industrial/"),
    ("Sistemas Python", "/sistemas-websites-python/"),
    ("Xyron", "/xyron/"),
    ("LittleBot", "/xyron/littlebot/"),
    ("Blog", "/blog/"),
    (
        "Artigo",
        "/blog/selecao-controladores-ativos-alta-severidade/",
    ),
    ("Autor", "/autor/marcelo-custodio/"),
    ("Contato", "/contato/"),
    ("Loja", "/loja/"),
]


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts: list[dict] = []
        self.stylesheets: list[str] = []
        self.images: list[dict] = []

    def handle_starttag(self, tag, attrs):
        attrs_map = dict(attrs)
        if tag == "script":
            self.scripts.append(
                {
                    "src": attrs_map.get("src", ""),
                    "defer": "defer" in attrs,
                    "async": "async" in attrs,
                }
            )
        elif tag == "link" and attrs_map.get("rel") == "stylesheet":
            self.stylesheets.append(attrs_map.get("href", ""))
        elif tag == "img":
            self.images.append(
                {
                    "src": attrs_map.get("src", ""),
                    "alt": attrs_map.get("alt"),
                    "width": attrs_map.get("width"),
                    "height": attrs_map.get("height"),
                    "loading": attrs_map.get("loading"),
                    "fetchpriority": attrs_map.get("fetchpriority"),
                }
            )


def audit_page(client: Client, path: str) -> dict:
    response = client.get(path)
    html = response.content.decode("utf-8", errors="replace")
    parser = AssetParser()
    parser.feed(html)
    external_scripts = [s for s in parser.scripts if s["src"]]
    images_missing_dims = [
        img for img in parser.images if not (img["width"] and img["height"])
    ]
    images_missing_alt = [img for img in parser.images if img["alt"] is None]
    eager = [img for img in parser.images if img["loading"] == "eager"]
    lazy = [img for img in parser.images if img["loading"] == "lazy"]
    high_priority = [img for img in parser.images if img["fetchpriority"] == "high"]
    return {
        "status": response.status_code,
        "html_bytes": len(response.content),
        "scripts": len(external_scripts),
        "stylesheets": len(parser.stylesheets),
        "images": len(parser.images),
        "images_missing_dims": len(images_missing_dims),
        "images_missing_alt": len(images_missing_alt),
        "eager": len(eager),
        "lazy": len(lazy),
        "high_priority": len(high_priority),
    }


def main():
    client = Client()
    print("page\tstatus\tscripts\tcss\timages\tno_dims\tno_alt\teager\tlazy\thigh_pri\thtml_kb")
    with override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"]):
        for label, path in PAGES:
            data = audit_page(client, path)
            print(
                f"{label}\t{data['status']}\t{data['scripts']}\t{data['stylesheets']}\t"
                f"{data['images']}\t{data['images_missing_dims']}\t{data['images_missing_alt']}\t"
                f"{data['eager']}\t{data['lazy']}\t{data['high_priority']}\t"
                f"{data['html_bytes'] // 1024}"
            )


if __name__ == "__main__":
    main()

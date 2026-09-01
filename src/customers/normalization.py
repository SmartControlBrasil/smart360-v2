"""Normalização comercial para matching conservador entre leads e clientes.

As funções são puras, determinísticas e não tentam “consertar” dados inválidos.
Um valor incompleto ou malformado vira string vazia; nunca vira um identificador inventado.

Telefone
--------
Compara máscaras diferentes do mesmo número brasileiro:

    +55 11 99999-9999
    55 11 99999 9999
    (11) 99999-9999
    11999999999

Regras:

- mantém somente dígitos;
- remove o prefixo internacional 55 quando o número tem 12 ou 13 dígitos
  (55 + telefone nacional de 10 ou 11 dígitos);
- não inventa DDD;
- não completa dígitos faltantes;
- não promove um valor inválido a um telefone válido.

Domínio
-------
Compara websites pelo host canônico:

    https://www.empresa.com.br/contato?x=1  → empresa.com.br
    http://empresa.com.br                   → empresa.com.br
    empresa.com.br/                         → empresa.com.br
    www.empresa.com.br                      → empresa.com.br
    loja.empresa.com.br                     → loja.empresa.com.br

Regras:

- lowercase;
- remove scheme, www., path, query, fragment e porta;
- preserva subdomínio que não seja www;
- valor vazio ou malformado vira string vazia;
- não tenta corrigir domínio inválido de forma agressiva.
"""

import re
from urllib.parse import urlsplit


def normalize_phone_for_match(value):
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("55") and len(digits) in {12, 13}:
        digits = digits[2:]
    return digits


def normalize_domain_for_match(value):
    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    try:
        parsed = urlsplit(value)
    except ValueError:
        return ""
    domain = (parsed.netloc or "").split("@")[-1].lower()
    if ":" in domain:
        domain = domain.split(":", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def apply_customer_match_normalization(customer):
    customer.normalized_phone = normalize_phone_for_match(customer.phone)
    customer.normalized_whatsapp = normalize_phone_for_match(customer.whatsapp)
    customer.normalized_domain = normalize_domain_for_match(customer.website)
    return customer

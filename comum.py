#!/usr/bin/env python3
"""
comum.py — utilitários minúsculos compartilhados pelo pipeline.

Existe pela mesma razão da taxonomia: pequenas funções idênticas estavam
começando a nascer copiadas em 3-4 módulos (vazio, pastas ignoradas do
vault, regex de wikilink) — exatamente o mecanismo que gerou os quatro
parsers divergentes que a Fase 1 matou. Aqui mora a cópia única.

Regras deste módulo: só utilitários SEM dependência (não importa taxonomia
nem frontmatter) e sem I/O. Se a função precisa de vocabulário, o lugar
dela é a taxonomia; se precisa ler arquivo, é do chamador.
"""

import re

# Um campo de frontmatter "vazio" para fins de validação: ausente, string
# em branco (inclusive só espaços), lista vazia ou o literal null.
def vazio(v) -> bool:
    return v is None or v == [] or str(v).strip() in ("", "null")


# Pastas do vault que NÃO são notas do acervo: templates (placeholders),
# a fila do radar, e metadados do Obsidian. Todo scanner de vault
# (auditor de grafo, radar, contadores do app) usa este conjunto.
IGNORAR_PASTAS = frozenset({"99-Templates", "Radar", ".obsidian", ".trash"})


# [[alvo]] · [[alvo|alias]] · [[alvo#seção]] — o grupo 1 é só o alvo.
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def alvo_wikilink(texto) -> str:
    """Primeiro alvo de wikilink num texto (ex.: campo `obra:`), ou ''. """
    m = WIKILINK.search(str(texto or ""))
    return m.group(1).strip() if m else ""

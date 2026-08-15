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
import unicodedata

# Um campo de frontmatter "vazio" para fins de validação: ausente, string
# em branco (inclusive só espaços), lista vazia ou o literal null.
def vazio(v) -> bool:
    return v is None or v == [] or str(v).strip() in ("", "null")


def sem_acento(s: str) -> str:
    """'Tributário' → 'Tributario'. Base de todo slug e de toda busca
    por substring que não pode depender de o usuário digitar o acento."""
    n = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in n if not unicodedata.combining(c))


def tag_valida(s: str) -> str:
    """'Hugo de Brito Machado' → 'hugo-de-brito-machado'.

    A forma que o Obsidian aceita em `tags:` do frontmatter: minúscula, sem
    acento, sem espaço. A BARRA sobrevive de propósito — é ela que dá a tag
    hierárquica (`planejamento/holding`), que o Obsidian aninha sozinho no
    painel de tags. Morava no normalizar_yaml.py; subiu porque o vocabulário,
    o conectar e o painel precisam da MESMA regra (tag que difere por um
    acento é uma segunda tag, e o acervo se fragmenta em silêncio).
    """
    s = sem_acento(s).lower()
    s = re.sub(r"[^a-z0-9/]+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    # Cada nível é limpo por si: "Planejamento / Holding" tem espaços em
    # volta da barra, e sem isto viraria "planejamento-/-holding" — três
    # níveis quebrados no painel de tags do Obsidian em vez de dois.
    return "/".join(p for p in (x.strip("-") for x in s.split("/")) if p)


# Pastas do vault que NÃO são notas do acervo: templates (placeholders),
# a fila do radar, e metadados do Obsidian. Todo scanner de vault
# (auditor de grafo, radar, contadores do app) usa este conjunto.
IGNORAR_PASTAS = frozenset({"99-Templates", "Radar", ".obsidian", ".trash"})


# Extensões de ARQUIVO-FONTE aceitas na entrada do acervo. Duas famílias,
# porque são duas rotas de conversão que não se misturam:
#   PDF   → aplicar_ocr.sh (OCR quando precisa) → injetar_paginas.py → {{p.NN}}
#   EBOOK → converter_ebook.py (sem OCR: já é texto) → {{p.NN}} ou {{loc.NN}}
# Consumidores: acervo_app.py (navegador de pastas, contadores, expansão das
# fontes, roteamento das etapas 1/2/3) e triagem.py (coluna `formato`).
# O OCR só se aplica a PDF — e-book na lista do aplicar_ocr.sh vira ocrmypdf
# rc=2 e uma linha "FALHOU" eterna no controle.csv.
EXTENSOES_PDF = frozenset({".pdf"})
EXTENSOES_EBOOK = frozenset({".epub", ".mobi", ".azw3", ".azw"})
EXTENSOES_FONTE = EXTENSOES_PDF | EXTENSOES_EBOOK
# Sem o ponto — é a forma que vai para a coluna `formato` do controle.csv.
EXTENSOES_EBOOK_SEM_PONTO = frozenset(e.lstrip(".") for e in EXTENSOES_EBOOK)


def eh_ebook(caminho) -> bool:
    """O arquivo é e-book (não precisa de OCR, converte por converter_ebook.py)?"""
    return str(caminho).lower().endswith(tuple(EXTENSOES_EBOOK))


def eh_fonte(caminho) -> bool:
    """O arquivo é fonte aceita pelo acervo (PDF ou e-book)?"""
    return str(caminho).lower().endswith(tuple(EXTENSOES_FONTE))


# [[alvo]] · [[alvo|alias]] · [[alvo#seção]] — o grupo 1 é só o alvo.
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def alvo_wikilink(texto) -> str:
    """Primeiro alvo de wikilink num texto (ex.: campo `obra:`), ou ''. """
    m = WIKILINK.search(str(texto or ""))
    return m.group(1).strip() if m else ""


def prefixo_fatia(stem: str) -> str:
    """Slug do nome-base das fatias/índice de uma obra — fonte única: o
    fatiar GERA com ele; quem procura fatias no disco usa O MESMO slug."""
    return re.sub(r"[^\w\-]+", "-", stem)[:60].strip("-")


# Bloco "Relações (auto)" que o conectar.py grava nos índices do vault.
# Mora aqui (e não no conectar) porque o publicar.py também precisa
# reconhecê-lo: ao comparar origem×vault ele ignora/reinjeta o bloco —
# regenerável por contrato, não é curadoria (mesmo pacto do moc:auto).
CONECTAR_INI = ("<!-- conectar:auto:inicio — gerado por conectar.py; "
                "edite FORA deste bloco -->")
CONECTAR_FIM = "<!-- conectar:auto:fim -->"
RE_BLOCO_CONECTAR = re.compile(
    r"<!-- conectar:auto:inicio[^>]*-->.*?<!-- conectar:auto:fim -->",
    re.DOTALL)

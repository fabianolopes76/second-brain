#!/usr/bin/env python3
"""
frontmatter.py — PARSER ÚNICO de frontmatter YAML do Acervo.

Este módulo substitui os quatro parsers que existiam espalhados pelo
pipeline (validar_yaml_abnt, auditar_acervo, fatiar, normalizar_yaml) —
a divergência entre eles é o que fazia metadados sumirem em silêncio
(ex.: `area:` em bloco multi-linha era destruída pelo parser fraco do
fatiar.py, e a fatia ficava invisível nos MOCs do Obsidian).

Só mecânica: ler e serializar. Vocabulário (quais palavras são legais)
mora em taxonomia.py — e este módulo NÃO o importa, de propósito:
misturar as duas coisas foi o que gerou quatro parsers.

Entende (sem PyYAML, stdlib pura):
  - escalares com/sem aspas, true/false, null/~
  - blocos dobrados (>) e literais (|), com variantes -/+
  - listas inline:      area: [Tributário, Civil]
  - listas multi-linha: tags:\\n  [\\n   "a",\\n   "b",\\n  ]
Não entende (e o Acervo não usa): aninhamento, âncoras YAML, multi-doc.
"""

import re
from typing import NamedTuple


class Frontmatter(NamedTuple):
    campos: dict     # os pares chave→valor parseados
    corpo: str       # o texto APÓS o fechamento `---`
    bruto: str       # o bloco interno VERBATIM (sem os delimitadores)
    presente: bool   # havia frontmatter?


_ABERTURA = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def ler(texto: str) -> Frontmatter:
    """Lê o frontmatter de um documento markdown.

    Sem frontmatter → Frontmatter({}, texto, "", False): o documento
    inteiro é `corpo`, preservando o comportamento histórico dos
    consumidores.
    """
    m = _ABERTURA.match(texto)
    if not m:
        return Frontmatter({}, texto, "", False)

    bruto = m.group(1)
    corpo = texto[m.end():]
    linhas = bruto.splitlines()
    dados, i = {}, 0
    while i < len(linhas):
        linha = linhas[i]
        if not linha.strip() or linha.strip().startswith("#") or ":" not in linha:
            i += 1
            continue
        chave, _, valor = linha.partition(":")
        chave = chave.strip()
        valor = valor.split(" #")[0].strip()

        # bloco dobrado (>) ou literal (|): o valor vem nas linhas indentadas
        if valor in (">", "|", ">-", "|-", ">+", "|+"):
            corpo_bloco, i = [], i + 1
            while i < len(linhas) and (not linhas[i].strip()
                                       or linhas[i][:1] in (" ", "\t")):
                corpo_bloco.append(linhas[i].strip())
                i += 1
            sep = " " if valor.startswith(">") else "\n"
            dados[chave] = sep.join(c for c in corpo_bloco if c).strip()
            continue

        # lista em várias linhas:  tags:\n  [\n   "a",\n   "b",\n  ]
        if valor == "" and i + 1 < len(linhas) and linhas[i + 1].strip().startswith("["):
            bloco, i = "", i + 1
            while i < len(linhas):
                bloco += linhas[i].strip()
                if "]" in linhas[i]:
                    i += 1
                    break
                i += 1
            itens = re.findall(r'"([^"]*)"|\'([^\']*)\'', bloco)
            dados[chave] = [a or b for a, b in itens]
            continue

        # lista em linha:  area: [Tributário, Civil]
        if valor.startswith("[") and valor.endswith("]"):
            interno = valor[1:-1].strip()
            citados = re.findall(r'"([^"]*)"|\'([^\']*)\'', interno)
            dados[chave] = ([a or b for a, b in citados] if citados
                            else [x.strip() for x in interno.split(",") if x.strip()])
            i += 1
            continue

        valor = valor.strip('"').strip("'")
        if valor.lower() in ("true", "false"):
            dados[chave] = valor.lower() == "true"
        elif valor.lower() in ("", "null", "~"):
            dados[chave] = None
        else:
            dados[chave] = valor
        i += 1
    return Frontmatter(dados, corpo, bruto, True)


# ═══════════════════════════════════════════════════════════════════════════
# Serialização — o caminho de VOLTA, que nenhum script tinha.
# Interpolar valores parseados num f-string gera repr de Python
# (`area: ['Tributário']`) e um `"` solto quebra o YAML da nota inteira
# em silêncio. Todo campo escrito em frontmatter passa por aqui.
# ═══════════════════════════════════════════════════════════════════════════

# Um escalar precisa de aspas quando contém sintaxe YAML ativa, espaços nas
# bordas, ou quando seria lido como outro tipo (true/null/números com risco).
_PRECISA_ASPAS = re.compile(r'[:#\[\]{}>|&*!?@`"\']|^[\s-]|\s$')
_PALAVRAS_RESERVADAS = {"true", "false", "null", "~", "yes", "no", "on", "off"}


def escalar(v) -> str:
    """Serializa um valor escalar com aspas apenas quando necessário."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "" or s.lower() in _PALAVRAS_RESERVADAS or _PRECISA_ASPAS.search(s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def lista_inline(itens, aspas=True) -> str:
    """Serializa lista inline. Com aspas por padrão — nomes ABNT contêm
    vírgula ("MACHADO, Hugo"), e sem aspas o item se parte em dois."""
    if aspas:
        return "[" + ", ".join(
            '"' + str(i).replace("\\", "\\\\").replace('"', '\\"') + '"'
            for i in itens) + "]"
    return "[" + ", ".join(str(i) for i in itens) + "]"


def emitir(chave, valor) -> str:
    """Linha completa `chave: valor` com serialização segura por tipo."""
    if isinstance(valor, (list, tuple)):
        return f"{chave}: {lista_inline(valor)}"
    return f"{chave}: {escalar(valor)}"

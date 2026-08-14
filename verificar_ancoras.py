#!/usr/bin/env python3
"""
verificar_ancoras.py — Valida a integridade das âncoras de página num Markdown.

Roda ANTES e DEPOIS do refino pelo Claude, para garantir que nenhuma âncora
foi perdida, duplicada ou reordenada durante a edição. Sem dependências.

Uso:
    python verificar_ancoras.py arquivo.md
    python verificar_ancoras.py pasta/            # valida todos os .md da pasta
    python verificar_ancoras.py antes.md --comparar depois.md
"""

import argparse
import re
import sys
from pathlib import Path

# Duas famílias de âncora, porque há duas famílias de fonte: PDF e e-book com
# page-list citam por PÁGINA ({{p.NN}}); e-book sem paginação da edição impressa
# cita por POSIÇÃO ({{loc.NN}}), o localizador que a taxonomia.py:49 define para
# `livro_ebook_leitor`. Antes daqui só existia `p.`, e um único e-book no lote
# reprovava a validação de TODOS os arquivos (o rc=1 do final).
PADRAO = re.compile(r"\{\{(p|loc)\.([0-9ivxlcdm]+)\}\}"
                    r"|<!--\s*(p|loc)\.([0-9ivxlcdm]+)\s*-->",
                    re.IGNORECASE)

ROMANOS = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


def romano_para_int(s: str) -> int:
    s = s.lower()
    total, anterior = 0, 0
    for ch in reversed(s):
        val = ROMANOS.get(ch, 0)
        total = total - val if val < anterior else total + val
        anterior = max(anterior, val)
    return total


def extrair(caminho: Path):
    """→ (rótulos, texto, tipo) — tipo é 'p' ou 'loc', conforme o documento.

    Documento misturando os dois é erro de conversão, não caso de uso: avisamos
    e tratamos pelo predominante."""
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    achados, tipos = [], []
    for m in PADRAO.finditer(texto):
        kind = (m.group(1) or m.group(3) or "p").lower()
        rot = m.group(2) or m.group(4)
        achados.append(rot.lower())
        tipos.append(kind)
    tipo = max(set(tipos), key=tipos.count) if tipos else "p"
    if tipos and len(set(tipos)) > 1:
        print(f"  ⚠ {caminho.name}: mistura âncora de página e de posição — "
              "verifique a conversão.")
    return achados, texto, tipo


def eh_romano(rot: str) -> bool:
    return not rot.isdigit()


def validar(caminho: Path) -> bool:
    achados, texto, tipo = extrair(caminho)
    nome = "página" if tipo == "p" else "posição"
    print(f"\n=== {caminho.name} ===")

    if not achados:
        print("  ✗ NENHUMA âncora de localização encontrada.")
        print("    → Este arquivo NÃO serve para citação ABNT.")
        print("    → Se a fonte é PDF:     python injetar_paginas.py <pdf> -o <saida.md>")
        print("    → Se é ePUB/MOBI/AZW:   python3 converter_ebook.py <ebook> -o <saida.md>")
        return False

    print(f"  • Âncoras de {nome} encontradas: {len(achados)}")
    print(f"  • Primeira: {tipo}.{achados[0]}   Última: {tipo}.{achados[-1]}")

    ok = True

    # duplicadas
    vistos, dups = set(), []
    for a in achados:
        if a in vistos:
            dups.append(a)
        vistos.add(a)
    if dups:
        print(f"  ✗ Âncoras DUPLICADAS: {sorted(set(dups))}")
        ok = False

    # ordem e lacunas (só entre as arábicas)
    arabicas = [int(a) for a in achados if not eh_romano(a)]
    if arabicas:
        fora_ordem = [(a, b) for a, b in zip(arabicas, arabicas[1:]) if b < a]
        if fora_ordem:
            print(f"  ✗ Fora de ordem em: {fora_ordem[:5]}")
            ok = False

        faltando = [n for n in range(min(arabicas), max(arabicas) + 1)
                    if n not in set(arabicas)]
        if faltando:
            amostra = faltando[:10]
            print(f"  ⚠ Lacunas ({len(faltando)}): {tipo}.{amostra}"
                  f"{' ...' if len(faltando) > 10 else ''}")
            # Posição é ORDINAL e contínua por construção: lacuna ali não é
            # página em branco, é âncora perdida em alguma etapa.
            print("    (pode ser normal: páginas em branco, ilustrações)"
                  if tipo == "p" else
                  "    (em POSIÇÃO isto NÃO é normal — a numeração é contínua)")

    # âncoras dentro de blocos de código (erro comum)
    if re.search(r"```[^`]*\{\{(?:p|loc)\.", texto, re.DOTALL):
        print("  ⚠ Há âncora dentro de bloco de código — verifique.")

    if ok:
        print("  ✓ Integridade OK")
    return ok


def comparar(a: Path, b: Path) -> bool:
    ant, _, tipo = extrair(a)
    dep, _, _ = extrair(b)
    print(f"\n=== COMPARAÇÃO: {a.name} → {b.name} ===")
    print(f"  Antes: {len(ant)} âncoras | Depois: {len(dep)} âncoras")

    perdidas = [x for x in ant if x not in set(dep)]
    novas = [x for x in dep if x not in set(ant)]

    if perdidas:
        print(f"  ✗ PERDIDAS no refino ({len(perdidas)}): {tipo}.{perdidas[:10]}")
    if novas:
        print(f"  ✗ INVENTADAS no refino ({len(novas)}): {tipo}.{novas[:10]}")
        print("    → Âncora nova = localizador fabricado. GRAVE. Refaça.")
    if not perdidas and not novas:
        print("  ✓ Nenhuma âncora perdida ou inventada.")
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Valida âncoras de página em Markdown")
    ap.add_argument("alvo", help="arquivo .md ou pasta")
    ap.add_argument("--comparar", help="arquivo .md posterior, para comparar")
    args = ap.parse_args()

    alvo = Path(args.alvo)
    if not alvo.exists():
        sys.exit(f"ERRO: não encontrei {alvo}")

    if args.comparar:
        outro = Path(args.comparar)
        if not outro.exists():
            sys.exit(f"ERRO: não encontrei {outro}")
        sys.exit(0 if comparar(alvo, outro) else 1)

    # Relatórios (RELATORIO-*.md) e auxiliares (_*.md) são PRODUTO do pipeline,
    # não documento-fonte: não têm nem devem ter âncora. Sem este filtro — que o
    # limpar_ocr.py:234 já aplicava e este script não —, um RELATORIO-AUDITORIA.md
    # na pasta reprovava a validação e fazia o job da etapa 3 sair com rc=1,
    # como se a conversão tivesse falhado.
    arquivos = (sorted(f for f in alvo.glob("*.md")
                       if not f.name.startswith(("RELATORIO", "_")))
                if alvo.is_dir() else [alvo])
    if not arquivos:
        sys.exit("Nenhum .md encontrado.")

    resultados = [validar(f) for f in arquivos]
    total, bons = len(resultados), sum(resultados)
    print(f"\n{'='*40}\nResumo: {bons}/{total} arquivo(s) com âncoras íntegras.")
    sys.exit(0 if bons == total else 1)


if __name__ == "__main__":
    main()

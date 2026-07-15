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

PADRAO = re.compile(r"\{\{p\.([0-9ivxlcdm]+)\}\}|<!--\s*p\.([0-9ivxlcdm]+)\s*-->",
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
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    achados = []
    for m in PADRAO.finditer(texto):
        rot = m.group(1) or m.group(2)
        achados.append(rot.lower())
    return achados, texto


def eh_romano(rot: str) -> bool:
    return not rot.isdigit()


def validar(caminho: Path) -> bool:
    achados, texto = extrair(caminho)
    print(f"\n=== {caminho.name} ===")

    if not achados:
        print("  ✗ NENHUMA âncora de página encontrada.")
        print("    → Este arquivo NÃO serve para citação ABNT.")
        print("    → Reinjete a paginação: python injetar_paginas.py <pdf-fonte> -o <saida.md>")
        return False

    print(f"  • Âncoras encontradas: {len(achados)}")
    print(f"  • Primeira: p.{achados[0]}   Última: p.{achados[-1]}")

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
            print(f"  ⚠ Lacunas ({len(faltando)}): p.{amostra}"
                  f"{' ...' if len(faltando) > 10 else ''}")
            print("    (pode ser normal: páginas em branco, ilustrações)")

    # âncoras dentro de blocos de código (erro comum)
    if re.search(r"```[^`]*\{\{p\.", texto, re.DOTALL):
        print("  ⚠ Há âncora dentro de bloco de código — verifique.")

    if ok:
        print("  ✓ Integridade OK")
    return ok


def comparar(a: Path, b: Path) -> bool:
    ant, _ = extrair(a)
    dep, _ = extrair(b)
    print(f"\n=== COMPARAÇÃO: {a.name} → {b.name} ===")
    print(f"  Antes: {len(ant)} âncoras | Depois: {len(dep)} âncoras")

    perdidas = [x for x in ant if x not in set(dep)]
    novas = [x for x in dep if x not in set(ant)]

    if perdidas:
        print(f"  ✗ PERDIDAS no refino ({len(perdidas)}): p.{perdidas[:10]}")
    if novas:
        print(f"  ✗ INVENTADAS no refino ({len(novas)}): p.{novas[:10]}")
        print("    → Âncora nova = número de página fabricado. GRAVE. Refaça.")
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

    arquivos = sorted(alvo.glob("*.md")) if alvo.is_dir() else [alvo]
    if not arquivos:
        sys.exit("Nenhum .md encontrado.")

    resultados = [validar(f) for f in arquivos]
    total, bons = len(resultados), sum(resultados)
    print(f"\n{'='*40}\nResumo: {bons}/{total} arquivo(s) com âncoras íntegras.")
    sys.exit(0 if bons == total else 1)


if __name__ == "__main__":
    main()

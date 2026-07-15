#!/usr/bin/env python3
"""
corrigir_idioma.py — Conserta o campo `idioma` de markdowns já gerados.

Por que existe
--------------
A primeira versão do detector lia só as 12 páginas iniciais do PDF — que num
livro são capa, folha de rosto, ficha catalográfica (frequentemente em inglês:
"Copyright... All rights reserved") e sumário. Quase sem palavras funcionais.
Resultado: obras estrangeiras caíam no idioma padrão (por+eng). Um livro
italiano foi catalogado como português.

Este script REDETECTA o idioma a partir do PDF-fonte (agora amostrando o miolo)
e corrige o YAML — SEM reconverter nada, SEM tocar no texto nem nas âncoras.

Uso:
    python3 corrigir_idioma.py 2-MARKDOWN-BRUTO/ --pdfs 0-ENTRADA/
    python3 corrigir_idioma.py livro.md --pdf livro.pdf
    python3 corrigir_idioma.py 2-MARKDOWN-BRUTO/ --pdfs . --dry
"""

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import taxonomia

NOMES = taxonomia.IDIOMAS          # fonte única do vocabulário de idiomas
EDICAO = taxonomia.IDIOMA_EDICAO

AQUI = Path(__file__).resolve().parent


def detectar(pdf: Path) -> str:
    det = AQUI / "detectar_idioma.py"
    if not det.exists():
        return ""
    try:
        r = subprocess.run([sys.executable, str(det), str(pdf), "--csv"],
                           capture_output=True, text=True, timeout=180)
        linhas = r.stdout.strip().splitlines()
        if len(linhas) > 1:
            partes = linhas[1].split(",")
            return partes[1] if len(partes) > 1 else ""
    except Exception:
        pass
    return ""


def chave(nome: str) -> str:
    """Nome comparável, imune às armadilhas de nome de arquivo do mundo real.

    Três problemas que quebravam a busca:
      1. UNICODE NFC × NFD — o Dropbox/Windows grava "Tributário" com o acento
         DECOMPOSTO (a + ´), enquanto o Python escreveu o COMPOSTO (á). Mesmos
         caracteres na tela, bytes diferentes: exists() e glob() falham.
      2. glob() trata [ ] como curinga — nomes com colchetes nunca casam.
      3. Diferenças de caixa, espaços e sufixos (_OCR, (Z-Library)).
    Solução: comparar por uma chave normalizada, sem acento e só alfanumérica.
    """
    n = unicodedata.normalize("NFKD", nome)
    n = "".join(c for c in n if not unicodedata.combining(c))   # tira acentos
    n = n.lower()
    n = re.sub(r"_ocr\b", "", n)
    n = re.sub(r"[^a-z0-9]+", "", n)                            # só alfanumérico
    return n


def achar_pdf(md: Path, pastas):
    """Localiza o PDF-fonte por comparação normalizada (NFC/NFD, caixa, símbolos)."""
    txt = md.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^origem_pdf:\s*"?([^"\n]+)"?', txt, re.M)

    alvos = set()
    if m:
        alvos.add(chave(Path(m.group(1).strip()).stem))
    alvos.add(chave(md.stem))
    alvos.add(chave(md.stem.replace(".limpo", "")))
    alvos.discard("")

    # os.walk não usa glob → imune a [ ] ( ) nos nomes
    for pasta in pastas:
        for raiz, _dirs, arqs in os.walk(pasta):
            for a in arqs:
                if not a.lower().endswith(".pdf"):
                    continue
                if chave(Path(a).stem) in alvos:
                    return Path(raiz) / a
    return None


def aplicar(md: Path, idioma: str, dry: bool) -> str:
    txt = md.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", txt, re.DOTALL)
    if not m:
        return "sem frontmatter"

    fm, resto = m.group(1), txt[m.end():]
    atual = ""
    ma = re.search(r"^idioma:\s*(\S+)", fm, re.M)
    if ma:
        atual = ma.group(1).strip().strip('"')

    if atual == idioma:
        return f"já correto ({idioma})"

    nome = NOMES.get(idioma, idioma)
    bloco = (f"idioma: {idioma}\n"
             f'idioma_nome: "{nome}"\n'
             f"traducao: original\n"
             f'# ATENCAO: obra em {nome} — NAO traduzir nem "corrigir" o texto.\n'
             f"# Edicao segue a lingua do documento: {EDICAO.get(idioma, 'N. ed.')}\n")

    # remove as linhas antigas de idioma/aviso e insere o bloco novo
    fm2 = re.sub(r"^(idioma|idioma_nome|traducao):.*\n?", "", fm + "\n", flags=re.M)
    fm2 = re.sub(r"^# (ATENCAO: obra em|Edicao segue a lingua).*\n?", "", fm2, flags=re.M)
    novo = "---\n" + fm2.rstrip("\n") + "\n" + bloco + "---\n" + resto

    if not dry:
        md.write_text(novo, encoding="utf-8")
    return f"{atual or '(vazio)'} → {idioma}" + ("  [dry]" if dry else "  ✓ corrigido")


def main():
    ap = argparse.ArgumentParser(description="Corrige o idioma no YAML de markdowns já gerados")
    ap.add_argument("alvo", help="arquivo .md ou pasta")
    ap.add_argument("--pdf", help="PDF-fonte (para arquivo único)")
    ap.add_argument("--pdfs", nargs="*", default=[],
                    help="pasta(s) onde procurar os PDFs-fonte")
    ap.add_argument("--dry", action="store_true", help="só mostra, não grava")
    a = ap.parse_args()

    alvo = Path(a.alvo)
    if not alvo.exists():
        sys.exit(f"ERRO: não encontrei {alvo}")

    arquivos = ([f for f in sorted(alvo.rglob("*.md"))
                 if not f.name.startswith(("RELATORIO", "_"))]
                if alvo.is_dir() else [alvo])
    pastas = [Path(p) for p in a.pdfs] or [alvo if alvo.is_dir() else alvo.parent]

    print(f"\n{len(arquivos)} markdown(s). Procurando PDFs em: "
          f"{', '.join(str(p) for p in pastas)}\n")

    mudou = 0
    for md in arquivos:
        pdf = Path(a.pdf) if a.pdf else achar_pdf(md, pastas)
        if not pdf or not pdf.exists():
            print(f"?  {md.name[:52]:54} PDF-fonte não encontrado — pulado")
            continue
        idi = detectar(pdf)
        if not idi:
            print(f"!  {md.name[:52]:54} não deu para detectar "
                  f"(PDF escaneado? rode OCR antes)")
            continue
        r = aplicar(md, idi, a.dry)
        marca = "✓" if "corrigido" in r or "dry" in r else "—"
        print(f"{marca}  {md.name[:52]:54} {r}")
        if "→" in r:
            mudou += 1

    print(f"\n{'='*66}\n{mudou} arquivo(s) com idioma corrigido"
          f"{' (dry-run: nada gravado)' if a.dry else ''}.")
    if mudou and not a.dry:
        print("As âncoras e o texto NÃO foram tocados — só o YAML.")


if __name__ == "__main__":
    main()

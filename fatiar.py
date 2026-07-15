#!/usr/bin/env python3
"""
fatiar.py — Divide um markdown grande em NOTA-ÍNDICE + FATIAS (arquitetura de
duas camadas do segundo cérebro).

Por que existe
--------------
A auditoria acusou arquivos de 42.601 e 183.717 palavras. O segundo é ~250 mil
tokens: não cabe num chat de refino de forma útil, custa caro e a IA "se perde"
num contexto tão longo (a recuperação piora). Fatiar não é organização: é
requisito de performance.

Como fatia
----------
1. Prefere cortar em TÍTULOS (## / ###) — cortes semânticos, respeitam capítulos.
2. Sem títulos, corta em ÂNCORAS DE PÁGINA, agrupando até o alvo de tamanho.
3. NUNCA parte uma citação em bloco (>), um artigo de lei ou o meio de um parágrafo.
4. Cada fatia leva TODAS as suas âncoras {{p.NN}} e registra pagina_inicio/fim.
5. Gera a nota-índice (camada 1) com o sumário e links [[wikilink]] para as fatias.

Uso:
    python3 fatiar.py livro.md                       # alvo padrão: ~1200 palavras
    python3 fatiar.py livro.md --palavras 900
    python3 fatiar.py livro.md -o pasta_saida/
    python3 fatiar.py pasta/ --min-palavras 4000     # só fatia os grandes
"""

import argparse
import re
import sys
from pathlib import Path

ANCORA = re.compile(r"\{\{p\.([0-9ivxlcdm]+)\}\}", re.I)
TITULO = re.compile(r"^(#{1,4})\s+(.+)$")

ALVO_PALAVRAS = 1200      # ~1.500 tokens
MAX_PALAVRAS = 2000       # teto por fatia
MIN_PALAVRAS_FATIAR = 4000  # abaixo disso, não vale fatiar


def ler_frontmatter(texto):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", texto, re.DOTALL)
    if not m:
        return {}, texto, ""
    bruto = m.group(1)
    d = {}
    for linha in bruto.splitlines():
        if ":" in linha and not linha.strip().startswith("#"):
            k, _, v = linha.partition(":")
            d[k.strip()] = v.split(" #")[0].strip().strip('"').strip("'")
    return d, texto[m.end():], bruto


def blocos(corpo):
    """Quebra o corpo em blocos atômicos que NUNCA devem ser partidos:
    parágrafo, bloco de citação, lista, título, âncora."""
    out, buf, dentro_quote = [], [], False
    for linha in corpo.split("\n"):
        eh_titulo = bool(TITULO.match(linha))
        eh_ancora = bool(ANCORA.fullmatch(linha.strip()))
        eh_quote = linha.strip().startswith(">")

        if eh_titulo or eh_ancora:
            if buf:
                out.append("\n".join(buf)); buf = []
            out.append(linha)
            dentro_quote = False
            continue
        if eh_quote:
            dentro_quote = True
            buf.append(linha)
            continue
        if not linha.strip():
            if buf and not dentro_quote:
                out.append("\n".join(buf)); buf = []
            elif buf:
                buf.append(linha)
            dentro_quote = False
            continue
        buf.append(linha)
    if buf:
        out.append("\n".join(buf))
    return [b for b in out if b.strip() or True]


def fatiar(corpo, alvo=ALVO_PALAVRAS, maxi=MAX_PALAVRAS):
    """Agrupa blocos em fatias, cortando preferencialmente em títulos."""
    bs = blocos(corpo)
    fatias, atual, n_pal = [], [], 0

    def fechar():
        nonlocal atual, n_pal
        if atual and any(b.strip() for b in atual):
            fatias.append("\n".join(atual).strip())
        atual, n_pal = [], 0

    for b in bs:
        m = TITULO.match(b)
        pal = len(b.split())
        # Título de nível 1-2 e já temos conteúdo suficiente → corte semântico
        if m and len(m.group(1)) <= 2 and n_pal >= alvo * 0.4:
            fechar()
        # Excedeu o teto → corta aqui (mas nunca no meio de um bloco)
        elif n_pal + pal > maxi and n_pal >= alvo * 0.5:
            fechar()
        atual.append(b)
        n_pal += pal
    fechar()
    return fatias


def paginas_da_fatia(fatia):
    achadas = ANCORA.findall(fatia)
    if not achadas:
        return None, None
    return achadas[0], achadas[-1]


def titulo_da_fatia(fatia, i):
    for linha in fatia.split("\n"):
        m = TITULO.match(linha)
        if m:
            return m.group(2).strip()[:70]
    return f"Parte {i:02d}"


def processar(arq: Path, destino: Path, alvo: int, minimo: int):
    # O teto acompanha o alvo. Antes era fixo (2000) e ignorava --palavras: pedir
    # fatias de 1.200 devolvia fatias de 1.845. Agora o teto é 1,3× o alvo.
    teto = int(alvo * 1.3)
    texto = arq.read_text(encoding="utf-8", errors="replace")
    fm, corpo, fm_bruto = ler_frontmatter(texto)
    n_pal = len(corpo.split())

    if n_pal < minimo:
        print(f"— {arq.name}: {n_pal:,} palavras (abaixo de {minimo:,}) — não fatiado")
        return 0

    fatias = fatiar(corpo, alvo, teto)
    if len(fatias) < 2:
        print(f"— {arq.name}: não foi possível fatiar (sem títulos/âncoras úteis)")
        return 0

    destino.mkdir(parents=True, exist_ok=True)
    prefixo = re.sub(r"[^\w\-]+", "-", arq.stem)[:60].strip("-")

    n_anc_orig = len(ANCORA.findall(corpo))
    n_anc_fat = 0
    itens = []

    for i, f in enumerate(fatias, 1):
        p_ini, p_fim = paginas_da_fatia(f)
        tit = titulo_da_fatia(f, i)
        n_anc_fat += len(ANCORA.findall(f))
        nome = f"{prefixo}_p{i:02d}.md"

        cab = ["---",
               f'titulo: "{fm.get("titulo", arq.stem)} — {tit}"',
               f'obra: "[[{prefixo}_INDICE]]"',
               f"parte: {i:02d}"]
        for campo in ("area", "tipo_fonte", "idioma", "autoria_citacao",
                      "ano", "localizador_abrev", "status"):
            if fm.get(campo):
                cab.append(f"{campo}: {fm[campo]}")
        if p_ini:
            cab += [f"pagina_inicio: {p_ini}", f"pagina_fim: {p_fim}"]
        cab.append("---")

        pag_txt = f", **p. {p_ini}–{p_fim}**" if p_ini else ""
        entrada = (f"> **{fm.get('titulo', arq.stem)}** · {tit}{pag_txt} — fatia {i:02d}. "
                   f"Ficha: [[{prefixo}_INDICE]].\n\n---\n\n")
        nav = (f"\n\n---\n\n◀ [[{prefixo}_p{i-1:02d}]] · "
               f"▲ [[{prefixo}_INDICE]] · [[{prefixo}_p{i+1:02d}]] ▶\n"
               if 1 < i < len(fatias) else
               f"\n\n---\n\n▲ [[{prefixo}_INDICE]]"
               + (f" · [[{prefixo}_p02]] ▶\n" if i == 1 and len(fatias) > 1 else "\n"))

        (destino / nome).write_text("\n".join(cab) + "\n\n" + entrada + f + nav,
                                    encoding="utf-8")
        itens.append((i, tit, p_ini, p_fim, f"{prefixo}_p{i:02d}"))

    # TRAVA: nenhuma âncora pode se perder no fatiamento
    if n_anc_orig != n_anc_fat:
        print(f"✗ {arq.name}: ÂNCORAS PERDIDAS ({n_anc_orig} → {n_anc_fat})",
              file=sys.stderr)
        return 0

    # ---- nota-índice (camada 1) ----
    idx = ["---"]
    idx.append(fm_bruto if fm_bruto else "")
    idx.append(f"partes: {len(fatias)}")
    idx.append("---\n")
    idx.append(f"# {fm.get('titulo', arq.stem)}\n")
    idx.append("> [!warning] Metadados incompletos")
    idx.append("> Preencha no Projeto Claude (Etapa 3): `autoria`, `titulo`, "
               "`edicao`, `local_publicacao`, `editora`, `ano`, `referencia_abnt`, `resumo`.\n")
    idx.append("## Resumo para consulta\n")
    idx.append("<!-- 3–8 linhas. É o que a IA lê primeiro para decidir se abre uma fatia. -->\n")
    idx.append(f"## Sumário — {len(fatias)} fatias\n")
    for i, tit, pi, pf, link in itens:
        pag = f" — p. {pi}–{pf}" if pi else ""
        idx.append(f"- [[{link} | {i:02d} — {tit}]]{pag}")
    idx.append("\n## Conferência")
    idx.append("- [ ] Metadados ABNT preenchidos")
    idx.append("- [ ] Resumo escrito")
    idx.append("- [ ] 3 páginas conferidas contra o PDF")
    idx.append("- [ ] `confiabilidade: Conferida`")

    (destino / f"{prefixo}_INDICE.md").write_text("\n".join(idx), encoding="utf-8")

    print(f"✓ {arq.name}")
    print(f"    {n_pal:,} palavras → {len(fatias)} fatias "
          f"(~{n_pal//len(fatias):,} palavras cada)")
    print(f"    âncoras: {n_anc_orig} preservadas ✓")
    print(f"    saída: {destino}/{prefixo}_INDICE.md + {len(fatias)} fatias")
    return len(fatias)


def main():
    ap = argparse.ArgumentParser(description="Fatia markdown grande em índice + fatias")
    ap.add_argument("alvo", help="arquivo .md ou pasta")
    ap.add_argument("-o", "--saida", help="pasta de saída (padrão: <alvo>/fatias)")
    ap.add_argument("--palavras", type=int, default=ALVO_PALAVRAS,
                    help=f"alvo por fatia (padrão {ALVO_PALAVRAS})")
    ap.add_argument("--min-palavras", type=int, default=MIN_PALAVRAS_FATIAR,
                    help="abaixo disso, não fatia")
    a = ap.parse_args()

    alvo = Path(a.alvo)
    if not alvo.exists():
        sys.exit(f"ERRO: não encontrei {alvo}")

    arquivos = ([f for f in sorted(alvo.glob("*.md"))
                 if not f.name.startswith(("RELATORIO", "_"))
                 and "_p0" not in f.name and "_INDICE" not in f.name]
                if alvo.is_dir() else [alvo])
    base = alvo if alvo.is_dir() else alvo.parent
    destino = Path(a.saida) if a.saida else base / "fatias"

    total = sum(processar(f, destino, a.palavras, a.min_palavras) for f in arquivos)
    print(f"\n{'='*54}\n{total} fatias geradas em {destino}")
    print("Próximo passo: abra a NOTA-ÍNDICE no Projeto Claude e peça os metadados "
          "ABNT + resumo (Etapa 3 do CHECKLIST_Refino_OCR.md).")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
limpar_ocr.py — Limpeza MECÂNICA do markdown de OCR (sem IA, sem tokens).

Por que existe
--------------
A auditoria acusou, nos livros convertidos:
  - hifenização quebrada       ("compe-\\ntência")
  - números de página / cabeçalhos soltos no corpo
  - ruído de caractere (OCR sujo)
  - muitas linhas curtíssimas (coluna/layout quebrado)

Nada disso precisa de LLM: são padrões determinísticos. Corrigi-los aqui é
gratuito e instantâneo — e deixa para a IA só o que ela faz melhor (metadados,
resumo, julgamento editorial).

REGRA DE OURO (não negociável)
------------------------------
  * NUNCA remove ou renumera âncoras {{p.NN}} — são a base da citação ABNT.
  * NUNCA reescreve o texto do autor. Só desfaz o que o OCR quebrou.
  * Preserva numeração de artigos/incisos, notas de rodapé e citações.
  * Em dúvida, PRESERVA.

Uso:
    python3 limpar_ocr.py livro.md                    # gera livro.limpo.md
    python3 limpar_ocr.py livro.md -o saida.md
    python3 limpar_ocr.py pasta/ --inplace            # limpa todos (faz .bak)
    python3 limpar_ocr.py livro.md --dry              # só relata, não grava
"""

import argparse
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

# As duas famílias (página/posição) nas DUAS formas (chaves/comentário). A forma
# comentário nunca foi protegida aqui: `--ancora comentario` gerava <!-- p.45 -->
# que a limpeza podia tratar como texto comum e a trava de contagem do fim
# (n_antes × n_depois) então reprovava o arquivo inteiro.
ANCORA = re.compile(r"\{\{(?:p|loc)\.[0-9ivxlcdm]+\}\}"
                    r"|<!--\s*(?:p|loc)\.[0-9ivxlcdm]+\s*-->", re.I)

# Linhas que são claramente cabeçalho/rodapé/lixo de OCR
LIXO = [
    re.compile(r"^\s*p[áa]gina\s+\d+\s*(de\s+\d+)?\s*$", re.I),
    re.compile(r"^\s*\d{1,4}\s*$"),                       # número de página solto
    re.compile(r"^\s*[-–—_=~*.]{3,}\s*$"),                 # linhas de traços
    re.compile(r"^\s*[|¦]+\s*$"),
    re.compile(r"^\s*(scanned|digitalizado|www\.|http)", re.I),
]


def proteger_ancoras(texto):
    """Troca âncoras por sentinelas, para nenhuma regex tocá-las."""
    achadas = []

    def sub(m):
        achadas.append(m.group(0))
        return f"\x00ANC{len(achadas)-1}\x00"

    return ANCORA.sub(sub, texto), achadas


def restaurar_ancoras(texto, achadas):
    for i, a in enumerate(achadas):
        texto = texto.replace(f"\x00ANC{i}\x00", a)
    return texto


def detectar_cabecalhos(linhas, min_rep=4):
    """Cabeçalho/rodapé = linha curta, repetida, E colada à quebra de página.

    A repetição sozinha NÃO basta: um livro pode repetir uma frase, e apagá-la
    seria destruir o texto do autor. O sinal decisivo é a POSIÇÃO — cabeçalho e
    rodapé aparecem sempre junto à âncora de página. Só removemos quando a
    maioria das ocorrências está a até 2 linhas de uma âncora.
    """
    pos_ancora = {i for i, l in enumerate(linhas) if "\x00ANC" in l}
    if not pos_ancora:
        return set()

    ocorr = {}
    for i, l in enumerate(linhas):
        s = l.strip()
        if 3 <= len(s) <= 70 and not s.startswith(("#", ">", "-", "*")) \
                and "\x00ANC" not in s:
            ocorr.setdefault(s, []).append(i)

    def perto_de_ancora(i):
        return any(abs(i - a) <= 2 for a in pos_ancora)

    cabecalhos = set()
    for s, idxs in ocorr.items():
        if len(idxs) < min_rep:
            continue
        perto = sum(1 for i in idxs if perto_de_ancora(i))
        # >=70% das ocorrências junto à quebra de página → é cabeçalho/rodapé
        if perto / len(idxs) >= 0.7:
            cabecalhos.add(s)
    return cabecalhos


def eh_de_ebook(fm: str) -> bool:
    """O documento veio de e-book (converter_ebook.py) e não de OCR?

    Importa porque este script é LIMPEZA DE OCR: hifenização de fim de linha,
    cabeçalho/rodapé de digitalização e coluna partida são artefatos do
    scanner. Num e-book o texto vem da marcação do editor — não há esses
    artefatos, e aplicar as heurísticas ali só produz falso positivo. E falso
    positivo em `detectar_cabecalhos` APAGA texto do autor."""
    return bool(re.search(r"^(?:motor_conversao|paginacao_origem):", fm, re.M)
                or re.search(r"^formato:\s*(epub|mobi|azw3?|azw)\s*$", fm, re.M))


def limpar(texto):
    rel = Counter()
    texto, ancoras = proteger_ancoras(texto)

    # separa frontmatter (não se mexe nele)
    m = re.match(r"^(---\s*\n.*?\n---\s*\n)", texto, re.DOTALL)
    fm, corpo = (m.group(1), texto[m.end():]) if m else ("", texto)
    ebook = eh_de_ebook(fm)
    if ebook:
        rel["modo e-book (limpeza de OCR não se aplica)"] = 1

    # 1) hifenização de fim de linha: "respon-\nsabilidade" -> "responsabilidade"
    #    Cuidado: só quando a 2ª parte começa em minúscula (evita "jurídico-\nTributário")
    if not ebook:
        corpo, n = re.subn(r"(\w)-\n(?=[a-záàâãéêíóôõúüçñäöüß])", r"\1", corpo)
        rel["hifenizações unidas"] = n

    # 2) remove cabeçalhos/rodapés repetidos e lixo
    linhas = corpo.split("\n")
    repetidos = set() if ebook else detectar_cabecalhos(linhas)
    saida, n_lixo, n_cab = [], 0, 0
    for l in linhas:
        s = l.strip()
        if "\x00ANC" in l:              # linha de âncora: passa intacta
            saida.append(l)
            continue
        if s in repetidos:
            n_cab += 1
            continue
        if any(p.match(l) for p in LIXO):
            n_lixo += 1
            continue
        saida.append(l)
    corpo = "\n".join(saida)
    rel["cabeçalhos repetidos removidos"] = n_cab
    rel["linhas de lixo removidas"] = n_lixo

    # 3) ruído de caractere isolado (barras, til duplo etc. fora de palavra)
    corpo, n = re.subn(r"(?<=\s)[|¦¬~^`]{1,3}(?=\s)", " ", corpo)
    rel["ruído de caractere"] = n

    # 4) junta linhas quebradas no meio da frase (coluna partida).
    #    Só quando a linha NÃO termina em pontuação e a próxima começa em minúscula.
    if not ebook:
        corpo, n = re.subn(
            r"(?<![.:;!?—\-])\n(?=[a-záàâãéêíóôõúüçñäöüß])(?![ \t]*[-*•])",
            " ", corpo)
        rel["linhas religadas"] = n

    # 5) espaços e quebras
    corpo = re.sub(r"[ \t]{2,}", " ", corpo)
    corpo = re.sub(r"[ \t]+\n", "\n", corpo)
    corpo = re.sub(r"\n{4,}", "\n\n\n", corpo)

    # 6) linha em branco ao redor das âncoras que JÁ ESTÃO SOZINHAS na linha.
    #    O `\n*` de antes casava ZERO newlines: numa âncora INLINE — o caso do
    #    e-book com page-list, em que a página impressa vira no meio do
    #    parágrafo — ele inseria \n\n ao redor e PARTIA a frase do autor em
    #    duas. Pior: os fragmentos curtos resultantes ficavam a ≤2 linhas de
    #    uma âncora e passavam a ser candidatos de `detectar_cabecalhos`.
    #    Âncora inline agora fica intacta. E NÃO se "empurra" a âncora para o
    #    início do parágrafo: isso deslocaria a fronteira de página e faria
    #    citar a p. 147 um trecho que está na 148.
    corpo = re.sub(r"(?m)^[ \t]*(\x00ANC\d+\x00)[ \t]*$", r"\n\1\n", corpo)
    corpo = re.sub(r"\n{3,}", "\n\n", corpo)

    resultado = restaurar_ancoras(fm + corpo.strip() + "\n", ancoras)
    return resultado, rel, len(ancoras)


def processar(arq: Path, saida: Path, dry: bool, inplace: bool):
    original = arq.read_text(encoding="utf-8", errors="replace")
    n_antes = len(ANCORA.findall(original))
    limpo, rel, n_depois = limpar(original)

    # TRAVA DE SEGURANÇA: nenhuma âncora pode sumir
    if n_antes != n_depois:
        print(f"✗ {arq.name}: ÂNCORAS PERDIDAS ({n_antes} → {n_depois}). "
              "Nada foi gravado.", file=sys.stderr)
        return False

    p_antes = len(original.split())
    p_depois = len(limpo.split())
    print(f"\n{arq.name}")
    print(f"  âncoras: {n_antes} preservadas ✓")
    for k, v in rel.items():
        if v:
            print(f"  {k}: {v}")
    print(f"  palavras: {p_antes:,} → {p_depois:,}")

    if dry:
        print("  (dry-run: nada gravado)")
        return True

    if inplace:
        shutil.copy2(arq, arq.with_suffix(arq.suffix + ".bak"))
        arq.write_text(limpo, encoding="utf-8")
        print(f"  gravado (backup em {arq.name}.bak)")
    else:
        saida.write_text(limpo, encoding="utf-8")
        print(f"  gravado: {saida.name}")
    return True


def main():
    ap = argparse.ArgumentParser(description="Limpeza mecânica de markdown OCR")
    ap.add_argument("alvo", help="arquivo .md ou pasta")
    ap.add_argument("-o", "--saida")
    ap.add_argument("--inplace", action="store_true", help="sobrescreve (cria .bak)")
    ap.add_argument("--dry", action="store_true", help="só relata")
    a = ap.parse_args()

    alvo = Path(a.alvo)
    if not alvo.exists():
        sys.exit(f"ERRO: não encontrei {alvo}")

    arquivos = ([f for f in sorted(alvo.glob("*.md"))
                 if not f.name.startswith(("RELATORIO", "_"))
                 and ".limpo" not in f.name]
                if alvo.is_dir() else [alvo])
    if not arquivos:
        sys.exit("Nenhum .md encontrado.")

    ok = 0
    for f in arquivos:
        s = Path(a.saida) if a.saida else f.with_suffix(".limpo.md")
        if processar(f, s, a.dry, a.inplace):
            ok += 1
    print(f"\n{'='*50}\n{ok}/{len(arquivos)} arquivo(s) limpos.")
    print("Próximo passo: fatiar.py (arquivos grandes) → Projeto Claude (metadados).")


if __name__ == "__main__":
    main()

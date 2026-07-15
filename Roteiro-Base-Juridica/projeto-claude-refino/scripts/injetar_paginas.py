#!/usr/bin/env python3
"""
injetar_paginas.py — Converte um PDF em Markdown PRESERVANDO a paginação.

Por que este script existe
--------------------------
Markdown não tem páginas; PDF tem. Quase todo conversor descarta essa
informação, e sem ela é IMPOSSÍVEL citar conforme a ABNT (que exige a página
na citação direta). Este script extrai o texto página a página e insere uma
âncora {{p.NN}} no início de cada uma.

IMPORTANTE: o PDF precisa ter CAMADA DE TEXTO. Se for escaneado (imagem),
rode antes o OCR:
    ocrmypdf -l por --deskew --rotate-pages entrada.pdf com_texto.pdf

Instalação da dependência:
    pip install pymupdf

Uso:
    python injetar_paginas.py livro.pdf -o livro.md
    python injetar_paginas.py livro.pdf -o livro.md --offset 12
    python injetar_paginas.py livro.pdf -o livro.md --ancora comentario
    python injetar_paginas.py livro.pdf -o livro.md --romanas-ate 14

Parâmetros importantes
----------------------
--offset N     Diferença entre a página FÍSICA do PDF e a página IMPRESSA no
               rodapé. Ex.: se a página impressa "1" é a 13ª folha do PDF,
               use --offset 12. Descubra abrindo o PDF e comparando.
--romanas-ate N  As N primeiras páginas físicas são numeradas em romano
               (prefácio etc.) e serão marcadas como {{p.i}}, {{p.ii}}...
--ancora       'chaves' (padrão) => {{p.45}}   |  'comentario' => <!-- p.45 -->
"""

import argparse
import re
import sys
from pathlib import Path

import taxonomia

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("ERRO: falta a dependência. Rode:  pip install pymupdf")


def int_para_romano(n: int) -> str:
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"),
            (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"),
            (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def limpar_basico(texto: str) -> str:
    """Limpeza conservadora. NÃO reescreve conteúdo — só conserta o que o
    extrator quebrou. Correções semânticas ficam para o Claude (ver checklist)."""
    # junta hifenização de fim de linha: "respon-\nsabilidade" -> "responsabilidade"
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    # remove espaços à direita
    texto = re.sub(r"[ \t]+\n", "\n", texto)
    # colapsa 3+ quebras em 2
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def rotulo_pagina(fisica: int, offset: int, romanas_ate: int) -> str:
    """fisica = índice 1-based da folha no PDF."""
    if romanas_ate and fisica <= romanas_ate:
        return int_para_romano(fisica)
    return str(fisica - offset)


def main():
    ap = argparse.ArgumentParser(description="PDF -> Markdown com âncoras de página")
    ap.add_argument("pdf", help="arquivo PDF de entrada (precisa ter camada de texto)")
    ap.add_argument("-o", "--saida", help="arquivo .md de saída")
    ap.add_argument("--offset", type=int, default=0,
                    help="página física - página impressa (padrão: 0)")
    ap.add_argument("--romanas-ate", type=int, default=0,
                    help="numerar as N primeiras páginas em romano")
    ap.add_argument("--ancora", choices=["chaves", "comentario"], default="chaves",
                    help="formato da âncora (padrão: chaves)")
    ap.add_argument("--tipo-fonte", default="",
                    help="pré-preenche tipo_fonte no YAML (ex.: livro, legislacao). "
                         "Vem do controle.csv da triagem; SEMPRE revise.")
    ap.add_argument("--idioma", default="",
                    help="idioma da obra (por/eng/deu/fra/ita/spa). Vem da triagem. "
                         "Avisa a IA para NAO 'corrigir' texto estrangeiro.")
    args = ap.parse_args()

    entrada = Path(args.pdf)
    if not entrada.exists():
        sys.exit(f"ERRO: não encontrei {entrada}")
    saida = Path(args.saida) if args.saida else entrada.with_suffix(".md")

    doc = fitz.open(entrada)
    total = len(doc)
    partes = []
    vazias = 0

    for i, page in enumerate(doc, start=1):
        texto = page.get_text("text")
        if not texto.strip():
            vazias += 1
        rot = rotulo_pagina(i, args.offset, args.romanas_ate)
        anc = f"{{{{p.{rot}}}}}" if args.ancora == "chaves" else f"<!-- p.{rot} -->"
        partes.append(f"{anc}\n\n{limpar_basico(texto)}")

    corpo = "\n\n".join(partes)

    # Localizador conforme o tipo — fonte única: taxonomia.py.
    # Tipo desconhecido ou de localizador variável NÃO ganha localizador
    # inferido: carimbar "pagina" num tipo errado fazia o validador rejeitar
    # o arquivo depois. Melhor admitir a dúvida do que inventar.
    tf = args.tipo_fonte.strip()
    _regra = taxonomia.TIPOS_FONTE.get(tf)
    loc_tipo, loc_ab = _regra.localizador if _regra else (None, None)

    # Fonte única do vocabulário de idiomas (NBR 6023: edição na língua do doc.)
    NOMES = taxonomia.IDIOMAS
    EDICAO = taxonomia.IDIOMA_EDICAO
    idi = args.idioma.strip().split("+")[0]
    extra = ""
    if idi in NOMES:
        extra += (f"idioma: {idi}\n"
                  f'idioma_nome: "{NOMES[idi]}"\n'
                  f'traducao: original\n'
                  f'# ATENCAO: obra em {NOMES[idi]} — NAO traduzir nem "corrigir" o texto.\n'
                  f'# Edicao segue a lingua do documento: {EDICAO[idi]}\n')
    if tf:
        extra += f'tipo_fonte: {tf}                 # palpite da triagem — REVISE\n'
        if loc_tipo is not None:
            extra += (f"localizador_tipo: {loc_tipo}\n"
                      f'localizador_abrev: "{loc_ab}"\n')
        elif _regra is None:
            extra += ('# tipo_fonte desconhecido pela taxonomia — localizador '
                      'NAO inferido; defina manualmente\n')
        extra += ('sistema_chamada: ambos\n'
                  'norma_citacao: "NBR 10520:2023"\n')

    cabecalho = (
        "---\n"
        f'origem_pdf: "{entrada.name}"\n'
        f"paginas_total: {total}\n"
        f"offset_pagina: {args.offset}\n"
        f'ancora: "{args.ancora}"\n'
        "paginacao: true\n"
        + extra +
        "confiabilidade: A-conferir\n"
        "---\n\n"
        "<!-- Gerado por injetar_paginas.py. As âncoras de página são OBRIGATÓRIAS\n"
        "     para citação ABNT (NBR 10520:2023). NÃO as remova nem renumere.\n"
        "     Próximo passo: refinar com o Projeto Claude (CHECKLIST_Refino_OCR.md). -->\n\n"
    )

    saida.write_text(cabecalho + corpo, encoding="utf-8")

    print(f"OK  {saida}  ({total} páginas)")
    if vazias:
        print(f"AVISO: {vazias} página(s) sem texto extraível.")
        print("       Provavelmente o PDF é escaneado. Rode OCR antes:")
        print("       ocrmypdf -l por --deskew --rotate-pages entrada.pdf com_texto.pdf")
    if args.offset == 0 and args.romanas_ate == 0:
        print("DICA: confira se a página impressa bate com a âncora. Se não bater,")
        print("      reprocesse usando --offset N (e --romanas-ate N, se houver prefácio).")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
triagem.py — classificação de tipo_fonte e geração do controle.csv.

Substitui a camada de vocabulário que vivia duplicada em bash
(aplicar_ocr.sh: inferir_tipo/exige_ancora/rota_de/csv_add) e no app
(acervo_app.py: _tipo_do_nome). O laço de OCR continua no bash — ele chama
este script por arquivo para classificar e emitir a linha do CSV.

O que mudou em relação à heurística antiga:
  1. Classifica também pelo CONTEÚDO (1ª/2ª página via pdftotext), não só
     pelo nome — a primeira página de uma lei é altamente diagnóstica
     ("LEI Nº", "Art. 1º", ementa), o nome do arquivo muitas vezes não é.
  2. SEM fallback cego para "livro". Quando nada pontua, o tipo sai VAZIO
     (indeterminado) e o próximo passo pede revisão humana — era exatamente
     assim que legislação virava "livro" em silêncio.
  3. Devolve confiança (alta/media/baixa) e as evidências que pontuaram.

As heurísticas são conhecimento do DOMÍNIO e moram no perfil ativo da
taxonomia (taxonomia.HEURISTICAS_TIPO / HEURISTICAS_CONTEUDO).

Uso (pelo aplicar_ocr.sh e pelo app; também funciona à mão):
    python3 triagem.py --cabecalho                      # header do controle.csv
    printf '%s' "$AMOSTRA" | python3 triagem.py --linha \
        ARQ CAMINHO PGS VAZIAS TEM_TXT PRECISOU STATUS SAIDA [IDIOMA]
    printf '%s' "$AMOSTRA" | python3 triagem.py --inferir NOME
"""

import csv
import io
import os
import re
import sys

import comum
import taxonomia


def _score_nome(nome: str) -> dict:
    """Pontua tipos pelo nome do arquivo (palavra-chave achada = +2)."""
    n = nome.lower()
    pontos = {}
    for chaves, tf in taxonomia.HEURISTICAS_TIPO:
        for k in chaves:
            if k in n:
                pontos[tf] = pontos.get(tf, 0) + 2
                break
    return pontos


def _score_conteudo(amostra: str) -> tuple:
    """Pontua tipos pelos sinais no texto. → (pontos, evidencias)"""
    pontos, evidencias = {}, []
    if not amostra:
        return pontos, evidencias
    for rx, tf, peso in taxonomia.HEURISTICAS_CONTEUDO:
        m = re.search(rx, amostra, re.I)
        if m:
            pontos[tf] = pontos.get(tf, 0) + peso
            evidencias.append(f"{tf}: «{m.group(0)[:40]}»")
    return pontos, evidencias


def inferir_tipo(nome: str, amostra: str = ""):
    """Infere o tipo_fonte de um arquivo. → (tipo, confianca, evidencias)

    confianca: "alta"  = nome e conteúdo concordam, ou sinal de conteúdo forte;
               "media" = só uma das fontes pontuou;
               "baixa" = nada pontuou → tipo VAZIO (indeterminado). REVISE.
    """
    p_nome = _score_nome(nome)
    p_cont, evidencias = _score_conteudo(amostra)

    total = dict(p_nome)
    for tf, v in p_cont.items():
        total[tf] = total.get(tf, 0) + v
    if not total:
        return "", "baixa", []

    tipo = max(total, key=total.get)
    if total[tipo] < 2:
        return "", "baixa", evidencias

    concordam = tipo in p_nome and tipo in p_cont
    forte_conteudo = p_cont.get(tipo, 0) >= 4
    conf = "alta" if (concordam or forte_conteudo) else "media"
    if p_nome and p_cont and tipo not in p_nome:
        # conteúdo contradiz o nome — conteúdo vence, mas com cautela
        conf = "media"
        evidencias.append(f"(nome sugeria: {max(p_nome, key=p_nome.get)})")
    return tipo, conf, evidencias


def exige_ancora_rotulo(tipo: str) -> str:
    """'SIM'/'nao' como o CSV histórico; '?' quando o tipo é indeterminado."""
    if not tipo:
        return "?"
    return "SIM" if taxonomia.exige_ancora(tipo) else "nao"


def formato_de(nome: str) -> str:
    """Extensão sem o ponto ('pdf', 'epub', 'mobi'…), em minúsculas.

    É a coluna que faltava: sem ela o `controle.csv` não sabia dizer de que
    FORMATO era cada fonte, e a etapa 3 tinha de reinferir pela extensão do
    caminho. CSV antigo (16 colunas) não tem esta coluna — quem lê deve tratar
    ausência como "pdf", que era o único formato possível antes."""
    return os.path.splitext(nome or "")[1].lower().lstrip(".") or "pdf"


def rota(tem_texto: str, formato: str = "pdf") -> str:
    """Rota do WORKFLOW: A = e-book (Calibre/pandoc, sem OCR);
    B = PDF nativo com texto; C = PDF que precisa de OCR.

    A rota A era citada num comentário do acervo_app.py e nunca existiu aqui —
    e-book não tem camada de texto a inspecionar: ele JÁ é texto."""
    if formato in comum.EXTENSOES_EBOOK_SEM_PONTO:
        return "A"
    return "C" if str(tem_texto).lower() in ("nao", "não", "no", "0") else "B"


def proximo_passo(anc: str, formato: str = "pdf") -> str:
    if formato in comum.EXTENSOES_EBOOK_SEM_PONTO:
        return "converter_ebook.py"
    if anc == "SIM":
        return "injetar_paginas.py"
    if anc == "?":
        return "classificar tipo (indeterminado) e revisar"
    return "converter (sem ancora de pagina)"


CABECALHO = ("arquivo,caminho,idioma,paginas,pgs_sem_texto,tem_camada_texto,"
             "precisou_ocr,ocr_status,arquivo_ocr,tipo_fonte_provavel,"
             "exige_ancora_pagina,rota,proximo_passo,area,status,confiabilidade,"
             "formato")


def linha_csv(arq, caminho, pgs, vazias, tem_txt, precisou, status, saida,
              idioma="", amostra=""):
    tipo, conf, _ = inferir_tipo(arq, amostra)
    anc = exige_ancora_rotulo(tipo)
    fmt = formato_de(arq)
    campos = [arq, caminho, idioma, pgs, vazias, tem_txt, precisou, status,
              saida, tipo, anc, rota(tem_txt, fmt), proximo_passo(anc, fmt),
              "", "A-conferir",
              # confiabilidade do PALPITE de triagem — revisão humana decide
              f"A-conferir (palpite: {conf})" if tipo else "A-conferir (indeterminado)",
              fmt]
    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="").writerow(campos)
    return buf.getvalue()


def linha_ebook(caminho: str) -> str:
    """A linha do controle.csv de UM e-book. → texto CSV (com \\n)

    E-book não passa pelo aplicar_ocr.sh — aquele script é PDF por dentro
    (pdfinfo/pdftotext/pdfimages) e um ePUB na fila dele viraria `ocrmypdf`
    rc=2 e uma linha "FALHOU" eterna. Então a linha nasce aqui, já com:
      tem_camada_texto=sim, precisou_ocr=nao, ocr_status=nao_necessario
    — que é a verdade (e-book JÁ é texto) e é o que faz o arquivo passar no
    gate `pesquisavel` da etapa 3 sem afrouxar aquele gate para PDF.

    A AMOSTRA para classificar o tipo vem do título/autoria do próprio OPF —
    grátis (uma leitura de ZIP) e mais diagnóstica que o nome do arquivo, que
    em acervo baixado costuma vir com ruído de origem."""
    p = os.path.basename(caminho)
    dados = {"titulo": "", "autoria": "", "idioma": "", "paginas": ""}
    try:
        import converter_ebook
        from pathlib import Path as _P
        dados = converter_ebook.sondar(_P(caminho))
    except Exception:
        pass                       # sondagem é bônus; a linha sai de todo jeito
    amostra = " ".join(x for x in (dados.get("titulo"), dados.get("autoria")) if x)
    return linha_csv(p, caminho, dados.get("paginas", ""), "", "sim", "nao",
                     "nao_necessario", caminho, dados.get("idioma", ""),
                     amostra) + "\n"


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="Classifica tipo_fonte (nome + conteúdo, com confiança) "
                    "e emite linhas do controle.csv. Amostra de texto entra "
                    "pela entrada padrão (stdin).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--cabecalho", action="store_true",
                   help="imprime o cabeçalho do controle.csv")
    g.add_argument("--inferir", metavar="NOME",
                   help="classifica um arquivo pelo nome (+ amostra via stdin)")
    g.add_argument("--linha", nargs="+", metavar="CAMPO",
                   help="emite uma linha do CSV: ARQ CAMINHO PGS VAZIAS "
                        "TEM_TXT PRECISOU STATUS SAIDA [IDIOMA]")
    g.add_argument("--ebooks", metavar="LISTA",
                   help="lista NUL-separada de e-books; emite uma linha do CSV "
                        "para cada (usar com >> controle.csv)")
    ap.add_argument("--com-cabecalho", action="store_true",
                    help="com --ebooks: emite o cabeçalho antes (use quando o "
                         "aplicar_ocr.sh NÃO rodou e ninguém criou o CSV)")
    a = ap.parse_args()

    if a.cabecalho:
        print(CABECALHO)
        return 0
    if a.ebooks:
        try:
            bruto = open(a.ebooks, "rb").read().decode("utf-8", "replace")
        except OSError as e:
            print(f"ERRO: nao li a lista {a.ebooks}: {e}", file=sys.stderr)
            return 1
        caminhos = [c for c in bruto.split("\0") if c.strip()]
        if a.com_cabecalho:
            print(CABECALHO)
        for c in caminhos:
            sys.stdout.write(linha_ebook(c))
        print(f"{len(caminhos)} e-book(s) na planilha de triagem (rota A).",
              file=sys.stderr)
        return 0
    amostra = "" if sys.stdin.isatty() else sys.stdin.read()
    if a.inferir:
        tipo, conf, evid = inferir_tipo(a.inferir, amostra)
        print(tipo or "(indeterminado)")
        print(f"confianca: {conf}", file=sys.stderr)
        for e in evid:
            print(f"  {e}", file=sys.stderr)
        return 0
    if len(a.linha) < 8:
        ap.error("--linha exige 8 campos: ARQ CAMINHO PGS VAZIAS TEM_TXT "
                 "PRECISOU STATUS SAIDA [IDIOMA]")
    pos = a.linha
    idioma = pos[8] if len(pos) > 8 else ""
    print(linha_csv(pos[0], pos[1], pos[2], pos[3], pos[4], pos[5],
                    pos[6], pos[7], idioma, amostra))
    return 0


if __name__ == "__main__":
    sys.exit(main())

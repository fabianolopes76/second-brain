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
import re
import sys

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


def rota(tem_texto: str) -> str:
    """Rota do WORKFLOW para PDFs: B = nativo com texto; C = precisa OCR."""
    return "C" if str(tem_texto).lower() in ("nao", "não", "no", "0") else "B"


def proximo_passo(anc: str) -> str:
    if anc == "SIM":
        return "injetar_paginas.py"
    if anc == "?":
        return "classificar tipo (indeterminado) e revisar"
    return "converter (sem ancora de pagina)"


CABECALHO = ("arquivo,caminho,idioma,paginas,pgs_sem_texto,tem_camada_texto,"
             "precisou_ocr,ocr_status,arquivo_ocr,tipo_fonte_provavel,"
             "exige_ancora_pagina,rota,proximo_passo,area,status,confiabilidade")


def linha_csv(arq, caminho, pgs, vazias, tem_txt, precisou, status, saida,
              idioma="", amostra=""):
    tipo, conf, _ = inferir_tipo(arq, amostra)
    anc = exige_ancora_rotulo(tipo)
    campos = [arq, caminho, idioma, pgs, vazias, tem_txt, precisou, status,
              saida, tipo, anc, rota(tem_txt), proximo_passo(anc),
              "", "A-conferir",
              # confiabilidade do PALPITE de triagem — revisão humana decide
              f"A-conferir (palpite: {conf})" if tipo else "A-conferir (indeterminado)"]
    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="").writerow(campos)
    return buf.getvalue()


def main():
    args = sys.argv[1:]
    if "--cabecalho" in args:
        print(CABECALHO)
        return 0
    if "--inferir" in args:
        nome = args[args.index("--inferir") + 1]
        amostra = "" if sys.stdin.isatty() else sys.stdin.read()
        tipo, conf, evid = inferir_tipo(nome, amostra)
        print(tipo or "(indeterminado)")
        print(f"confianca: {conf}", file=sys.stderr)
        for e in evid:
            print(f"  {e}", file=sys.stderr)
        return 0
    if "--linha" in args:
        pos = args[args.index("--linha") + 1:]
        if len(pos) < 8:
            print("uso: triagem.py --linha ARQ CAMINHO PGS VAZIAS TEM_TXT "
                  "PRECISOU STATUS SAIDA [IDIOMA]  (amostra via stdin)",
                  file=sys.stderr)
            return 2
        idioma = pos[8] if len(pos) > 8 else ""
        amostra = "" if sys.stdin.isatty() else sys.stdin.read()
        print(linha_csv(pos[0], pos[1], pos[2], pos[3], pos[4], pos[5],
                        pos[6], pos[7], idioma, amostra))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())

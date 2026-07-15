#!/usr/bin/env python3
"""
detectar_idioma.py — Identifica o idioma de um PDF (ou texto) do acervo.

Por que existe
--------------
O acervo tem obras em PORTUGUÊS, INGLÊS, ALEMÃO, FRANCÊS, ITALIANO e ESPANHOL.
O idioma muda três coisas no pipeline:
  1. OCR      → tesseract precisa do pacote certo (-l deu, -l fra…). OCRizar um
                livro alemão como português produz lixo.
  2. Refino   → a IA precisa saber a língua para NÃO "corrigir" o texto
                estrangeiro achando que é erro de OCR.
  3. ABNT     → a NBR 6023:2018 manda usar a língua DO DOCUMENTO em elementos
                como edição ("5th ed." em inglês; "5. ed." em português) e na
                abreviatura de mês.

Método: contagem de palavras funcionais (stopwords). Sem dependências externas,
roda em qualquer Python 3. Testado nas 6 línguas, inclusive no par difícil
português/espanhol.

Uso:
    python3 detectar_idioma.py arquivo.pdf
    python3 detectar_idioma.py arquivo.pdf --json
    python3 detectar_idioma.py pasta/ --csv       # varre e imprime CSV
    python3 detectar_idioma.py texto.txt

Requer 'pdftotext' (poppler-utils) para ler PDFs.
"""

import argparse
import collections
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import taxonomia

# Palavras funcionais por idioma. Bastam para textos com 30+ palavras.
STOPWORDS = {
    "por": ("de a o que e do da em um para com nao uma os no se na por mais as dos como mas ao "
            "ele das seu sua ou quando muito nos ja esta eu tambem so pelo pela ate isso entre "
            "depois sem mesmo aos seus quem nas me esse eles voce essa num nem suas meu minha "
            "numa pelos elas qual lhe deles essas esses pelas este dele lhes meus minhas nosso "
            "nossa sobre direito lei artigo ser tem foi sao"),
    "eng": ("the of and to in a is that it for as with was on be by this are or an not from at "
            "which have has had but they we you all can will one would there their been more "
            "when who its such shall may any upon these than"),
    "deu": ("der die und in den von zu das mit sich des auf fur ist im dem nicht ein eine als "
            "auch es an werden aus er hat dass sie nach wird bei einer um am sind noch wie einem "
            "uber einen so zum haben nur oder aber vor zur bis mehr durch man doch was wenn "
            "recht gesetz nicht diese dieser"),
    "fra": ("le de un et a les des en du est que dans qui pour pas au sur ce il une sont avec "
            "par plus ne se sa on son ou mais comme tout nous leur si ces deux meme lui bien "
            "encore aussi peut apres etre entre sans dont cette aux ses droit loi"),
    "ita": ("di che e la il un a per non in una sono mi si ho ma ha le con lo cosa se io ci "
            "questo qui hai da come quando anche solo tutto piu essere della delle degli nel "
            "nella alla dei sul suo alle gli diritto legge sia"),
    "spa": ("de la que el en y a los se del las un por con no una su para es al lo como mas "
            "pero sus le ya o este si porque esta entre cuando muy sin sobre tambien me hasta "
            "hay donde quien desde todo nos durante derecho ley articulo ser"),
}
STOPSETS = {lg: set(s.split()) for lg, s in STOPWORDS.items()}

NOMES = taxonomia.IDIOMAS   # fonte única do vocabulário de idiomas

# Limiar mínimo de confiança. Abaixo disso, devolvemos "" (indefinido) em vez de
# chutar — chutar o idioma errado no OCR é pior do que admitir a dúvida.
LIMIAR = 0.02
MIN_PALAVRAS = 30


def total_paginas(caminho: Path) -> int:
    try:
        r = subprocess.run(["pdfinfo", str(caminho)], capture_output=True,
                           text=True, timeout=30)
        for l in r.stdout.splitlines():
            if l.startswith("Pages:"):
                return int(l.split()[1])
    except Exception:
        pass
    return 0


def _extrair(caminho: Path, ini: int, fim: int) -> str:
    try:
        r = subprocess.run(
            ["pdftotext", "-q", "-f", str(ini), "-l", str(fim), str(caminho), "-"],
            capture_output=True, text=True, errors="replace", timeout=60,
        )
        return r.stdout or ""
    except Exception:
        return ""


def texto_do_pdf(caminho: Path) -> str:
    """Amostra o MIOLO do livro, não a frente.

    Por que: as primeiras páginas de um livro são capa, folha de rosto, ficha
    catalográfica (muitas vezes em inglês: "Copyright... All rights reserved"),
    sumário e abreviaturas — quase sem palavras funcionais. Ler só isso fazia a
    detecção falhar em obras estrangeiras e cair no idioma padrão.
    Solução: colher 3 amostras em ~25%, ~50% e ~75% do volume.
    """
    n = total_paginas(caminho)
    if n <= 0:
        return _extrair(caminho, 1, 12)          # não sabemos o tamanho: tenta o começo
    if n <= 8:
        return _extrair(caminho, 1, n)           # documento curto: lê tudo

    janela = 4
    pontos = [max(1, int(n * f)) for f in (0.25, 0.5, 0.75)]
    partes = []
    for ini in pontos:
        fim = min(n, ini + janela - 1)
        partes.append(_extrair(caminho, ini, fim))
    texto = "\n".join(partes)

    # Se o miolo veio vazio (escaneado sem OCR), tenta o começo antes de desistir.
    if len(texto.split()) < MIN_PALAVRAS:
        texto += "\n" + _extrair(caminho, 1, min(12, n))
    return texto


# Marcadores EXCLUSIVOS: palavras/padrões que praticamente só existem numa língua.
# Servem de desempate quando o placar de stopwords fica apertado — o caso clássico
# é português × italiano × espanhol, que compartilham muitas palavras curtas.
EXCLUSIVOS = {
    "por": ["não", "são", "está", "então", "também", "já", "pelo", "pela", "muito",
            "ção", "ções", "ã", "õ", "ç"],
    "ita": ["della", "degli", "gli", "nella", "sulla", "perché", "anche", "essere",
            "questo", "quale", "che", "è", "più", "cui"],
    "spa": ["ñ", "los", "las", "del", "pero", "porque", "también", "está", "así",
            "hacia", "según"],
    "fra": ["qu'", "d'", "l'", "être", "cette", "où", "aussi", "ainsi", "dont",
            "français", "ç", "è", "é"],
    "deu": ["ß", "ung", "keit", "der", "die", "das", "und", "nicht", "werden",
            "über", "für", "ä", "ö", "ü"],
    "eng": ["the", "of", "and", "which", "shall", "would", "been", "there",
            "through", "'s"],
}


def detectar(texto: str):
    """Devolve (idioma, confianca, placar). idioma = '' se indefinido.

    Duas correções importantes:
      1. NORMALIZA pelo tamanho da lista — antes, a língua com mais stopwords
         cadastradas levava vantagem artificial (o português vencia o italiano).
      2. Usa MARCADORES EXCLUSIVOS como desempate (ç/ã/õ → pt; gli/della → it).
    """
    baixo = texto.lower()
    palavras = re.findall(r"[a-záàâãéêíóôõúüçñäöüßùìòèœ']+", baixo)
    if len(palavras) < MIN_PALAVRAS:
        return "", 0.0, {}

    cont = collections.Counter(palavras)
    total = sum(cont.values())

    placar = {}
    for lg, s in STOPSETS.items():
        # cobertura: quanto do texto é feito de palavras funcionais DESTA língua,
        # dividido pelo tamanho da lista (evita o viés de lista grande)
        acertos = sum(c for w, c in cont.items() if w in s)
        placar[lg] = (acertos / total) * (60 / max(len(s), 20))

    # bônus por marcadores exclusivos
    for lg, marcas in EXCLUSIVOS.items():
        b = 0.0
        for m in marcas:
            if len(m) <= 2 or not m.isalpha():      # sinal gráfico (ç, ã, ß…)
                b += min(baixo.count(m) / max(len(baixo), 1) * 40, 0.05)
            else:                                    # palavra inteira
                b += min(cont.get(m, 0) / total * 6, 0.05)
        placar[lg] = placar.get(lg, 0) + b

    melhor = max(placar, key=placar.get)
    conf = placar[melhor]
    return (melhor if conf >= LIMIAR else ""), conf, placar


def analisar(caminho: Path):
    texto = texto_do_pdf(caminho) if caminho.suffix.lower() == ".pdf" \
        else caminho.read_text(encoding="utf-8", errors="replace")
    lg, conf, placar = detectar(texto)
    ordenado = sorted(placar.items(), key=lambda x: -x[1])
    segundo = ordenado[1][1] if len(ordenado) > 1 else 0.0
    # Margem baixa entre 1º e 2º = par ambíguo (típico: por × spa). Sinaliza.
    ambiguo = bool(lg) and conf > 0 and (conf - segundo) < 0.05
    return {
        "arquivo": caminho.name,
        "idioma": lg,
        "idioma_nome": NOMES.get(lg, "indefinido"),
        "confianca": round(conf, 3),
        "ambiguo": ambiguo,
        "sem_texto": len(texto.strip()) < 50,
        "placar": {k: round(v, 3) for k, v in ordenado[:3]},
    }


def main():
    ap = argparse.ArgumentParser(description="Detecta o idioma de PDFs do acervo")
    ap.add_argument("alvo", help="arquivo .pdf/.txt ou pasta")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args()

    alvo = Path(a.alvo)
    if not alvo.exists():
        sys.exit(f"ERRO: não encontrei {alvo}")

    arquivos = sorted(alvo.rglob("*.pdf")) if alvo.is_dir() else [alvo]
    res = [analisar(f) for f in arquivos]

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if a.csv:
        w = csv.DictWriter(sys.stdout,
                           fieldnames=["arquivo", "idioma", "idioma_nome",
                                       "confianca", "ambiguo", "sem_texto"])
        w.writeheader()
        for r in res:
            w.writerow({k: r[k] for k in w.fieldnames})
        return

    for r in res:
        if r["sem_texto"]:
            print(f"{r['arquivo'][:44]:46} SEM TEXTO (escaneado → OCR antes de detectar)")
            continue
        marca = "  ⚠ ambíguo" if r["ambiguo"] else ""
        idi = r["idioma"] or "indefinido"
        print(f"{r['arquivo'][:44]:46} {idi:4} ({r['idioma_nome']:10}) "
              f"conf={r['confianca']:.2f}{marca}")
        if r["ambiguo"] or not r["idioma"]:
            print(f"{'':46} placar: {r['placar']}  ← confira manualmente")


if __name__ == "__main__":
    main()

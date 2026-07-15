#!/usr/bin/env bash
#
# corrigir_acervo.sh — Executa, em ordem, TUDO que a auditoria pediu.
# -----------------------------------------------------------------------------
# A auditoria apenas DIAGNOSTICA. Este script é quem CORRIGE:
#
#   1. Idioma      → redetecta no PDF-fonte (amostrando o miolo) e conserta o YAML
#   2. Limpeza     → hifenização, cabeçalhos repetidos, ruído de OCR
#   3. Fatiamento  → livro gigante vira nota-índice + fatias
#   4. Reauditoria → mostra o que sobrou (deve ser só metadado ABNT)
#
# Âncoras e texto do autor NUNCA são tocados — os scripts abortam se perderem
# qualquer âncora.
#
# Uso:
#   bash corrigir_acervo.sh "/mnt/c/Users/.../_Analise"
#   DRY=1 bash corrigir_acervo.sh "/mnt/c/.../_Analise"    # simula, não grava
#   PALAVRAS=1500 bash corrigir_acervo.sh "..."            # fatias maiores
# -----------------------------------------------------------------------------
set -u

ACERVO="${1:-}"
DRY="${DRY:-0}"
PALAVRAS="${PALAVRAS:-1200}"
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "$ACERVO" ]]; then
    echo "Uso: bash corrigir_acervo.sh \"/caminho/para/_Analise\"" >&2
    exit 1
fi
if [[ ! -d "$ACERVO" ]]; then
    echo "ERRO: pasta nao encontrada: $ACERVO" >&2
    exit 1
fi

BRUTO="$ACERVO/2-MARKDOWN-BRUTO"
if [[ ! -d "$BRUTO" ]]; then
    echo "ERRO: nao achei $BRUTO" >&2
    echo "      (voce ja converteu os PDFs com injetar_paginas.py?)" >&2
    exit 1
fi

# Precisamos do Python do venv? Nao: estes 4 scripts usam so a biblioteca padrao.
PY="python3"

# Confere se os scripts sao da versao atual (evita rodar um auditor antigo,
# que reprovava as notas-indice por "falta de ancoras").
for s in corrigir_idioma.py limpar_ocr.py fatiar.py auditar_acervo.py; do
    if [[ ! -f "$SCRIPTS/$s" ]]; then
        echo "ERRO: falta $SCRIPTS/$s" >&2; exit 1
    fi
done
if ! grep -q "eh_indice" "$SCRIPTS/auditar_acervo.py" 2>/dev/null; then
    echo "AVISO: seu auditar_acervo.py e ANTIGO." >&2
    echo "       Ele vai reprovar as notas-indice por 'SEM ancoras' (falso positivo)." >&2
    echo "       Atualize o pacote e rode: python3 preparar.py" >&2
    echo >&2
fi
if ! grep -q "NFKD" "$SCRIPTS/corrigir_idioma.py" 2>/dev/null; then
    echo "AVISO: seu corrigir_idioma.py e ANTIGO." >&2
    echo "       Ele nao acha PDFs com acento (problema NFC/NFD do Dropbox)." >&2
    echo "       Atualize o pacote e rode: python3 preparar.py" >&2
    echo >&2
fi

echo "============================================================"
echo "Acervo   : $ACERVO"
echo "Markdown : $BRUTO"
echo "Fatias   : ~$PALAVRAS palavras"
[[ "$DRY" == 1 ]] && echo "Modo     : DRY-RUN (nada sera gravado)"
echo "============================================================"

# ---------------------------------------------------------------- 1. IDIOMA
echo
echo ">>> [1/5] Corrigindo o idioma (redetecta no PDF-fonte)"
if [[ "$DRY" == 1 ]]; then
    $PY "$SCRIPTS/corrigir_idioma.py" "$BRUTO" --pdfs "$ACERVO" --dry
else
    $PY "$SCRIPTS/corrigir_idioma.py" "$BRUTO" --pdfs "$ACERVO"
fi

# ---------------------------------------------------------------- 2. LIMPEZA
echo
echo ">>> [2/5] Limpeza mecanica do OCR"
if [[ "$DRY" == 1 ]]; then
    $PY "$SCRIPTS/limpar_ocr.py" "$BRUTO" --dry
else
    $PY "$SCRIPTS/limpar_ocr.py" "$BRUTO" --inplace
fi

# ---------------------------------------------------------------- 3. FATIAR
echo
echo ">>> [3/5] Fatiando os livros grandes"
if [[ "$DRY" == 1 ]]; then
    echo "    (dry-run: pulado — o fatiamento cria arquivos novos)"
else
    $PY "$SCRIPTS/fatiar.py" "$BRUTO" -o "$BRUTO/fatias" --palavras "$PALAVRAS"
fi

# ------------------------------------------------------------- 4. NORMALIZAR
echo
echo ">>> [4/5] Normalizando o YAML para o Obsidian (area/tags/autoria)"
ALVO_N="$BRUTO"
[[ -d "$BRUTO/fatias" ]] && ALVO_N="$BRUTO/fatias"
if [[ "$DRY" == 1 ]]; then
    $PY "$SCRIPTS/normalizar_yaml.py" "$ALVO_N" --dry | tail -20
else
    $PY "$SCRIPTS/normalizar_yaml.py" "$ALVO_N" | tail -5
fi

# ---------------------------------------------------------------- 5. AUDITAR
echo
echo ">>> [5/5] Reauditando"
if [[ "$DRY" == 1 ]]; then
    echo "    (dry-run: pulado)"
elif [[ -d "$BRUTO/fatias" ]]; then
    $PY "$SCRIPTS/auditar_acervo.py" "$BRUTO/fatias"
else
    $PY "$SCRIPTS/auditar_acervo.py" "$BRUTO"
fi

echo
echo "============================================================"
if [[ "$DRY" == 1 ]]; then
    echo "DRY-RUN concluido. Rode sem DRY=1 para aplicar."
else
    echo "Concluido."
    echo
    echo "O que deve ter SUMIDO do relatorio:"
    echo "  - arquivo gigante          (agora sao fatias)"
    echo "  - idioma errado            (redetectado no miolo do PDF)"
    echo "  - hifenizacao / ruido OCR  (limpeza mecanica)"
    echo "  - area em prosa / tags com acento (normalizadas p/ o Obsidian)"
    echo
    echo "O que deve SOBRAR (e normal — e o trabalho da IA):"
    echo "  - campos ABNT vazios: autoria, titulo, editora, ano"
    echo "  - referencia_abnt vazia"
    echo "  - sem resumo"
    echo
    echo "PROXIMO PASSO: leve as NOTAS-INDICE (arquivos *_INDICE.md, curtas)"
    echo "ao Projeto Claude e peca os metadados ABNT + resumo."
    echo "NAO leve o texto integral — as fatias existem justamente para isso."
fi
echo "============================================================"

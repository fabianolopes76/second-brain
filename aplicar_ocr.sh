#!/usr/bin/env bash
#
# aplicar_ocr.sh — FASE 2 do WORKFLOW (rota C)
# -----------------------------------------------------------------------------
# Percorre a pasta do processo, identifica os PDFs que NAO sao pesquisaveis e
# aplica OCR com o ocrmypdf. Detecta paginas escaneadas (mesmo com carimbo dos
# tribunais), mantem os arquivos pequenos e registra o tempo por arquivo.
#
# >>> INTEGRACAO COM O PIPELINE DA BASE DE CONHECIMENTO <<<
#   Este script entrega PDFs PESQUISAVEIS. Ele NAO gera markdown e NAO cria as
#   ancoras de pagina. O passo seguinte e OBRIGATORIO para doutrina citavel:
#
#       source ~/venvs/acervo/bin/activate
#       python _scripts/injetar_paginas.py arquivo_OCR.pdf -o 2-MARKDOWN-BRUTO/arquivo.md
#
#   IMPORTANTE: use MODE=manter (padrao recomendado). O PDF ORIGINAL e a fonte
#   de verdade para conferir a pagina da citacao antes de a peca sair. Nao o
#   destrua. MODE=substituir e adequado a pecas de processo, NAO ao acervo
#   doutrinario.
#
#   OCR nao altera a quantidade nem a ordem das paginas -> as ancoras {{p.NN}}
#   geradas depois continuam validas.
#
# Uso:
#   bash aplicar_ocr.sh                     # detecta e OCRa os escaneados
#   FORCE_ALL=1 bash aplicar_ocr.sh         # OCR em TODOS, sem excecao
#   MODE=manter bash aplicar_ocr.sh         # nao pergunta; mantem original + _OCR
#   MODE=substituir bash aplicar_ocr.sh     # nao pergunta; substitui o original
#   DRYRUN=1 bash aplicar_ocr.sh            # so lista, nao grava  <-- COMECE POR AQUI
#   ROOT="/mnt/c/..." bash aplicar_ocr.sh   # define a pasta raiz
#   OCR_STRATEGY=force-ocr bash aplicar_ocr.sh   # forca rasterizar (maior)
#   OUTPUT_TYPE=pdf bash aplicar_ocr.sh     # PDF comum (menor) em vez de PDF/A
#
# Pre-requisitos (SISTEMA, nao venv):
#   sudo apt install -y ocrmypdf tesseract-ocr-por poppler-utils
#   sudo apt install -y unpaper          # necessario para a flag --clean
# Compressao extra (opcional): sudo apt install -y pngquant
#   (jbig2enc NAO existe no apt do Ubuntu; so ajuda em scans preto-e-branco.
#    Se precisar, compile de https://github.com/agl/jbig2enc)
# -----------------------------------------------------------------------------

set -u

# === CONFIGURACAO ============================================================
ROOT="${ROOT:-/mnt/c/Users/FabianoLopes/OneDrive/Documents/drive}"
SUFFIX="${SUFFIX:-_OCR}"

# Planilha de triagem (FASE 1 do WORKFLOW). O script ja analisa cada PDF pagina
# a pagina; aproveitamos essa analise para emitir o controle.csv, que alimenta a
# triagem e o refino no Projeto Claude. Use CSV=0 para nao gerar.
CSV="${CSV:-1}"
# A planilha mora JUNTO do acervo ($ROOT) — e onde o painel a procura.
# (Antes o default era $PWD: rodar o script de outra pasta espalhava
# controle.csv pelo diretorio corrente, inclusive dentro do repo.)
CSV_FILE="${CSV_FILE:-$ROOT/controle.csv}"

# Deteccao pagina a pagina: pagina precisa de OCR se tem pouco texto de corpo,
# OU tem imagem grande (escaneada) com pouco texto (so o carimbo).
PAGE_TEXT_MIN="${PAGE_TEXT_MIN:-10}"
TEXT_FULLPAGE_MIN="${TEXT_FULLPAGE_MIN:-300}"
IMG_MIN_DIM="${IMG_MIN_DIM:-1000}"
MIN_EMPTY_PAGES="${MIN_EMPTY_PAGES:-1}"

# FORCE_ALL=1 desliga a deteccao e OCRa todos os arquivos.
FORCE_ALL="${FORCE_ALL:-0}"

# --- IDIOMAS -----------------------------------------------------------------
# O acervo tem obras em pt, en, de, fr, it, es. OCRizar um livro alemao como
# portugues produz lixo. Por isso detectamos o idioma de cada arquivo.
#
#   OCR_LANG=auto (padrao) -> detecta por arquivo (detectar_idioma.py) e usa o
#                             pacote certo do tesseract. Se nao detectar (PDF
#                             escaneado, sem texto p/ analisar), usa OCR_LANG_FALLBACK.
#   OCR_LANG=por           -> forca um idioma para todo o lote.
#   OCR_LANG=por+eng       -> multi-idioma (mais lento; use so em obras bilingues).
OCR_LANG="${OCR_LANG:-auto}"
OCR_LANG_FALLBACK="${OCR_LANG_FALLBACK:-por+eng}"
DETECTOR="${DETECTOR:-$(dirname "${BASH_SOURCE[0]}")/detectar_idioma.py}"

# Confere se os pacotes de idioma estao instalados.
checar_idiomas() {
    local instalados faltando=()
    instalados=$(tesseract --list-langs 2>/dev/null | tail -n +2)
    for lg in por eng deu fra ita spa; do
        grep -qx "$lg" <<< "$instalados" || faltando+=("$lg")
    done
    if (( ${#faltando[@]} )); then
        echo "AVISO: pacotes de idioma do Tesseract ausentes: ${faltando[*]}" >&2
        echo "       sudo apt install -y $(printf 'tesseract-ocr-%s ' "${faltando[@]}")" >&2
        echo "       (sem eles, obras nessas linguas serao OCRizadas errado)" >&2
    fi
}

# detectar_lang ARQUIVO : ecoa o codigo do tesseract (por/eng/deu/fra/ita/spa).
detectar_lang() {
    local f="$1" lg=""
    if [[ "$OCR_LANG" != auto ]]; then echo "$OCR_LANG"; return; fi
    if [[ -f "$DETECTOR" ]]; then
        # --codigo imprime SO o codigo (por/eng/...) — nunca parsear o CSV
        # aqui: virgula no NOME do arquivo vira coluna e o "idioma" sai lixo
        # (ex.: " 1lib.sk" -> ocrmypdf rc=3 fingindo dependencia ausente).
        lg=$(python3 "$DETECTOR" "$f" --codigo 2>/dev/null | head -n1 | tr -d '[:space:]')
    fi
    [[ -z "$lg" ]] && lg="$OCR_LANG_FALLBACK"   # escaneado: sem texto p/ detectar
    echo "$lg"
}

# Estrategia do ocrmypdf:
#   redo-ocr (padrao): NAO rasteriza texto nativo -> arquivos menores e melhor
#     qualidade; OCRa o corpo escaneado mesmo sob carimbo. Remove --deskew
#     (incompativel com redo-ocr).
#   force-ocr: rasteriza tudo (funciona sempre, mas incha os arquivos e a
#     qualidade do texto passa a depender 100% do OCR).
#   skip-text / none.
OCR_STRATEGY="${OCR_STRATEGY:-redo-ocr}"

# Tipo de saida: pdfa (arquivamento) ou pdf (menor, sem conversao Ghostscript).
OUTPUT_TYPE="${OUTPUT_TYPE:-pdfa}"

# Otimizacao/compressao pos-OCR.
OPTIMIZE="${OPTIMIZE:-3}"
JPEG_QUALITY="${JPEG_QUALITY:-75}"
PNG_QUALITY="${PNG_QUALITY:-75}"

# montar_flags IDIOMA : monta as flags do ocrmypdf ja com o idioma do arquivo.
montar_flags() {
    local lg="$1"
    case "$OCR_STRATEGY" in
        redo-ocr)  OCR_FLAGS=(-l "$lg" --rotate-pages --clean --output-type "$OUTPUT_TYPE" --redo-ocr) ;;
        force-ocr) OCR_FLAGS=(-l "$lg" --deskew --rotate-pages --clean --output-type "$OUTPUT_TYPE" --force-ocr) ;;
        skip-text) OCR_FLAGS=(-l "$lg" --deskew --rotate-pages --clean --output-type "$OUTPUT_TYPE" --skip-text) ;;
        none)      OCR_FLAGS=(-l "$lg" --deskew --rotate-pages --clean --output-type "$OUTPUT_TYPE") ;;
        *) echo "ERRO: OCR_STRATEGY invalido: $OCR_STRATEGY" >&2; exit 1 ;;
    esac
    OCR_FLAGS+=(--optimize "$OPTIMIZE" --jpeg-quality "$JPEG_QUALITY" --png-quality "$PNG_QUALITY")
    FALLBACK_FLAGS=(-l "$lg" --deskew --rotate-pages --clean --output-type "$OUTPUT_TYPE" --force-ocr --optimize "$OPTIMIZE" --jpeg-quality "$JPEG_QUALITY" --png-quality "$PNG_QUALITY")
}
montar_flags "${OCR_LANG_FALLBACK}"   # valores iniciais (sobrescritos por arquivo)

# Codigos de saida do ocrmypdf que significam "PDF valido gerado":
#   0  = ok ; 10 = PDF valido criado, mas conversao PDF/A falhou (comum em PDFs
#   iText do tribunal). O arquivo esta OK e pesquisavel; NAO e motivo p/ fallback.
ocr_ok_rc() { [[ "$1" -eq 0 || "$1" -eq 10 ]]; }

# rc_motivo RC : traduz o codigo de saida do ocrmypdf. "FALHOU" seco nao diz
# nada; o motivo vai para o log e para o controle.csv.
rc_motivo() {
    case "$1" in
        0)  echo "ok" ;;
        1)  echo "erro de argumentos/uso" ;;
        2)  echo "arquivo de entrada invalido" ;;
        3)  echo "dependencia ausente (tesseract/ghostscript ou pacote de idioma?)" ;;
        4)  echo "saida invalida" ;;
        5)  echo "sem permissao de leitura/escrita" ;;
        6)  echo "PDF de entrada corrompido" ;;
        7)  echo "erro em processo filho (tesseract/ghostscript)" ;;
        8)  echo "PDF criptografado" ;;
        9)  echo "configuracao invalida" ;;
        10) echo "PDF valido; so a conversao PDF/A falhou" ;;
        15) echo "outro erro do ocrmypdf" ;;
        130) echo "interrompido (Ctrl+C)" ;;
        *)  echo "erro desconhecido" ;;
    esac
}

# ocr_exec ARGS... : ocrmypdf com o stderr anotado. A mensagem "Some input
# metadata could not be copied because it is not permitted in PDF/A" e um
# AVISO BENIGNO (XMP malformado da origem nao cabe no PDF/A; o PDF gerado
# esta valido e pesquisavel) — mas no log do painel ela parecia um erro.
#
# SINAL DE VIDA: o ocrmypdf so mostra barra de progresso em terminal
# interativo; pelo painel (pipe) um livro escaneado de 800 pgs fica 1h em
# silencio e parece CONGELADO. Enquanto o OCR roda, um vigia imprime o tempo
# decorrido a cada BATIMENTO_S segundos (padrao 60).
BATIMENTO_S="${BATIMENTO_S:-60}"
ocr_exec() {
    local t0=$SECONDS rc pid vigia
    ocrmypdf "$@" 2> >(sed \
      's|.*metadata could not be copied because it is not permitted in PDF/A.*|AVISO (inofensivo): metadados XMP da origem nao cabem no PDF/A — o PDF gerado esta valido e pesquisavel.|' >&2) &
    pid=$!
    (
        while sleep "$BATIMENTO_S"; do
            kill -0 "$pid" 2>/dev/null || exit 0
            echo "    ... OCR em andamento ha $(fmt_dur $((SECONDS - t0))) (sinal de vida — arquivo escaneado grande demora, nao travou)" >&2
        done
    ) &
    vigia=$!
    wait "$pid"; rc=$?
    kill "$vigia" 2>/dev/null
    wait "$vigia" 2>/dev/null
    return "$rc"
}

# run_ocr ENTRADA SAIDA : estrategia principal; se a falha for na conversao
# PDF/A (nao no OCR), tenta saida "pdf" comum SO para este arquivo; por fim,
# fallback force-ocr. Deixa o rc final em RUN_OCR_RC para o chamador logar.
RUN_OCR_RC=0
run_ocr() {
    local rc
    ocr_exec "${OCR_FLAGS[@]}" "$1" "$2"; rc=$?
    if ocr_ok_rc "$rc"; then RUN_OCR_RC=$rc; return 0; fi
    echo "    (estrategia $OCR_STRATEGY falhou rc=$rc: $(rc_motivo "$rc"))" >&2
    if [[ "$OUTPUT_TYPE" == pdfa ]]; then
        echo "    (tentando novamente este arquivo com --output-type pdf)" >&2
        ocr_exec "${OCR_FLAGS[@]/#pdfa/pdf}" "$1" "$2"; rc=$?
        if ocr_ok_rc "$rc"; then RUN_OCR_RC=$rc; return 0; fi
    fi
    if [[ "$OCR_STRATEGY" != force-ocr ]]; then
        echo "    (tentando fallback force-ocr)" >&2
        ocr_exec "${FALLBACK_FLAGS[@]}" "$1" "$2"; rc=$?
        if ocr_ok_rc "$rc"; then RUN_OCR_RC=$rc; return 0; fi
    fi
    RUN_OCR_RC=$rc
    return 1
}

# -----------------------------------------------------------------------
# Triagem (tipo_fonte, ancora, rota, linha do CSV): agora em triagem.py,
# que le o vocabulario da FONTE UNICA (taxonomia.py). Este script deixou
# de manter copia propria das heuristicas — era a 5a copia divergente.
# A classificacao usa nome do arquivo + AMOSTRA do conteudo (1a/2a pagina
# via pdftotext), e nao tem mais fallback cego para "livro".
# -----------------------------------------------------------------------
TRIAGEM="${TRIAGEM:-$(dirname "${BASH_SOURCE[0]}")/triagem.py}"

csv_init() {
    [[ "$CSV" != 1 ]] && return 0
    python3 "$TRIAGEM" --cabecalho > "$CSV_FILE"
    echo "Planilha    : $CSV_FILE"
}

# csv_add ARQ CAMINHO PGS VAZIAS TEM_TEXTO PRECISOU STATUS SAIDA [IDIOMA]
csv_add() {
    [[ "$CSV" != 1 ]] && return 0
    local amostra=""
    if [[ -n "${2:-}" && -f "$2" ]]; then
        amostra=$(pdftotext -l 2 "$2" - 2>/dev/null | head -c 3000 || true)
    fi
    printf '%s' "$amostra" | python3 "$TRIAGEM" --linha \
        "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "${9:-}" >> "$CSV_FILE"
}

# fmt_dur SEGUNDOS : formata duracao como XhYYmZZs / YmZZs / Zs.
fmt_dur() {
    local s=$1 h m
    h=$((s/3600)); m=$(((s%3600)/60)); s=$((s%60))
    if   (( h > 0 )); then printf '%dh%02dm%02ds' "$h" "$m" "$s"
    elif (( m > 0 )); then printf '%dm%02ds' "$m" "$s"
    else                   printf '%ds' "$s"
    fi
}

DRYRUN="${DRYRUN:-0}"
MODE="${MODE:-}"

# === DEPENDENCIAS ============================================================
for bin in ocrmypdf pdftotext pdfinfo pdfimages; do
    if ! command -v "$bin" >/dev/null 2>&1; then
        echo "ERRO: '$bin' nao encontrado. Instale:" >&2
        echo "  sudo apt install -y ocrmypdf tesseract-ocr-por poppler-utils" >&2
        exit 1
    fi
done

# --clean depende do unpaper; avisa cedo em vez de falhar no meio do lote.
if [[ " ${OCR_FLAGS[*]} " == *" --clean "* ]] && ! command -v unpaper >/dev/null 2>&1; then
    echo "AVISO: a flag --clean exige o 'unpaper', que nao foi encontrado." >&2
    echo "       Instale:  sudo apt install -y unpaper" >&2
    echo "       (ou rode sem --clean editando OCR_FLAGS)" >&2
fi

checar_idiomas

if [[ ! -d "$ROOT" ]]; then
    echo "ERRO: pasta raiz nao encontrada: $ROOT" >&2
    exit 1
fi

# === MODO (substituir x manter) =============================================
normalize_mode() {
    case "${1,,}" in
        s|sub|substituir|substitui|replace|r) echo "substituir" ;;
        m|manter|mantem|keep|k)               echo "manter" ;;
        *)                                     echo "" ;;
    esac
}
MODE="$(normalize_mode "$MODE")"
while [[ "$MODE" != "substituir" && "$MODE" != "manter" ]]; do
    echo
    echo "O que fazer com os PDFs apos aplicar o OCR?"
    echo "  [S] Substituir o arquivo original"
    echo "  [M] Manter o original e criar uma copia com sufixo \"${SUFFIX}\"  <-- recomendado p/ acervo"
    printf "Escolha [S/M]: "
    if ! read -r resp < /dev/tty; then
        echo "ERRO: use MODE=manter ou MODE=substituir." >&2
        exit 1
    fi
    MODE="$(normalize_mode "$resp")"
    [[ -z "$MODE" ]] && echo "Resposta invalida. Digite S ou M."
done

if [[ "$MODE" == substituir ]]; then
    echo
    echo "ATENCAO: MODE=substituir DESTROI o PDF original."
    echo "         Para o acervo doutrinario, o original e a fonte de verdade da"
    echo "         pagina citada. Prefira MODE=manter. (Ctrl+C para abortar)"
    sleep 3
fi

echo "============================================================"
echo "Pasta raiz : $ROOT"
if [[ "$MODE" == substituir ]]; then
    echo "Modo       : SUBSTITUIR o original"
else
    echo "Modo       : MANTER original + copia com sufixo ${SUFFIX}"
fi
if [[ "$DRYRUN" == 1 ]]; then
    echo "Dry-run    : SIM (nada sera gravado)"
else
    echo "Dry-run    : nao"
fi
if [[ "$FORCE_ALL" == 1 ]]; then
    echo "Deteccao   : DESLIGADA (FORCE_ALL=1 -> OCR em TODOS)"
else
    echo "Deteccao   : pagina a pagina (texto de corpo + imagem grande)"
fi
echo "Estrategia : $OCR_STRATEGY (fallback: force-ocr) | saida $OUTPUT_TYPE | optimize $OPTIMIZE"
if [[ "$OCR_LANG" == auto ]]; then
    echo "Idioma     : AUTO por arquivo (pt/en/de/fr/it/es) | fallback: $OCR_LANG_FALLBACK"
else
    echo "Idioma     : $OCR_LANG (fixo para todo o lote)"
fi
echo "Inicio     : $(date '+%Y-%m-%d %H:%M:%S')"
csv_init
echo "============================================================"

total=0; ocr_ok=0; ocr_fail=0; skipped=0; exists=0
PG_TOTAL=0; PG_EMPTY=0
RUN_START=$SECONDS

# analisar_pdf ARQUIVO : define PG_TOTAL/PG_EMPTY; retorna 0 se ja pesquisavel.
analisar_pdf() {
    local f="$1" pages p empty=0 t
    pages=$(pdfinfo "$f" 2>/dev/null | awk '/^Pages:/ {print $2}')
    [[ -z "$pages" || "$pages" -lt 1 ]] && pages=1
    PG_TOTAL=$pages
    local txt
    mapfile -t txt < <(pdftotext -q "$f" - 2>/dev/null | awk 'BEGIN{RS="\f"}{gsub(/[[:space:]]/,"");print length($0)}')
    local -A big=()
    while read -r pg; do
        [[ -n "$pg" ]] && big[$pg]=1
    done < <(pdfimages -list "$f" 2>/dev/null | awk -v d="$IMG_MIN_DIM" 'NR>2 && ($4+0>=d || $5+0>=d){print $1}' | sort -u)
    for (( p=1; p<=pages; p++ )); do
        t=${txt[p-1]:-0}
        if (( t < PAGE_TEXT_MIN )); then
            empty=$((empty+1))
        elif [[ -n "${big[$p]:-}" ]] && (( t < TEXT_FULLPAGE_MIN )); then
            empty=$((empty+1))
        fi
    done
    PG_EMPTY=$empty
    (( PG_EMPTY < MIN_EMPTY_PAGES ))
}

# Coleta a lista de PDFs (ignorando saidas _OCR).
files=()
while IFS= read -r -d '' f; do
    case "$(basename "$f")" in
        *"${SUFFIX}".pdf|*"${SUFFIX}".PDF) continue ;;
    esac
    files+=("$f")
done < <(find "$ROOT" -type f -iname '*.pdf' -print0)

N=${#files[@]}
echo "Encontrados $N PDF(s)."
echo

idx=0
for f in "${files[@]}"; do
    idx=$((idx+1)); total=$((total+1))
    printf '[%d/%d] %s ... ' "$idx" "$N" "$(basename "$f")"
    base_f="$(basename "$f")"
    LANG_F="$(detectar_lang "$f")"
    montar_flags "$LANG_F"
    if [[ "$FORCE_ALL" == 1 ]]; then
        analisar_pdf "$f" || true
        echo "OCR FORCADO"
        TEM_TXT="forcado"; PRECISOU="sim"
    elif analisar_pdf "$f"; then
        echo "JA PESQUISAVEL ($PG_TOTAL pgs, idioma: $LANG_F) - pulado"
        skipped=$((skipped+1))
        # Ja pesquisavel: entra no CSV como rota B, pronto p/ injetar_paginas.py
        csv_add "$base_f" "$f" "$PG_TOTAL" "$PG_EMPTY" "sim" "nao" "nao_necessario" "$f" "$LANG_F"
        continue
    else
        echo "PRECISA OCR ($PG_EMPTY de $PG_TOTAL pgs | idioma: $LANG_F)"
        TEM_TXT="nao"; PRECISOU="sim"
    fi

    if [[ "$MODE" == substituir ]]; then
        out="$f"
    else
        dir="$(dirname "$f")"; base="$(basename "$f")"
        out="$dir/${base%.[pP][dD][fF]}${SUFFIX}.pdf"
        if [[ -e "$out" ]]; then
            echo "    ja existe: $out (pulado)"; exists=$((exists+1))
            csv_add "$base_f" "$f" "$PG_TOTAL" "$PG_EMPTY" "$TEM_TXT" "$PRECISOU" "ja_existia" "$out" "$LANG_F"
            continue
        fi
    fi

    if [[ "$DRYRUN" == 1 ]]; then
        echo "    (dry-run) ocrmypdf ${OCR_FLAGS[*]} \"$f\" \"$out\""
        csv_add "$base_f" "$f" "$PG_TOTAL" "$PG_EMPTY" "$TEM_TXT" "$PRECISOU" "dry_run" "$out" "$LANG_F"
        continue
    fi

    file_start=$SECONDS
    echo "    inicio: $(date '+%H:%M:%S')"
    if [[ "$MODE" == substituir ]]; then
        tmp="$(mktemp --suffix=.pdf)"
        if run_ocr "$f" "$tmp"; then
            mv -f "$tmp" "$f"
            echo "    OK -> original substituido | tempo: $(fmt_dur $((SECONDS-file_start)))"
            ocr_ok=$((ocr_ok+1))
            csv_add "$base_f" "$f" "$PG_TOTAL" "$PG_EMPTY" "$TEM_TXT" "$PRECISOU" "ok" "$f" "$LANG_F"
        else
            rm -f "$tmp"
            echo "    FALHOU (rc=$RUN_OCR_RC: $(rc_motivo "$RUN_OCR_RC")): $f | tempo: $(fmt_dur $((SECONDS-file_start)))" >&2
            ocr_fail=$((ocr_fail+1))
            csv_add "$base_f" "$f" "$PG_TOTAL" "$PG_EMPTY" "$TEM_TXT" "$PRECISOU" "FALHOU: $(rc_motivo "$RUN_OCR_RC")" "" "$LANG_F"
        fi
    else
        if run_ocr "$f" "$out"; then
            echo "    OK -> $out | tempo: $(fmt_dur $((SECONDS-file_start)))"
            ocr_ok=$((ocr_ok+1))
            csv_add "$base_f" "$f" "$PG_TOTAL" "$PG_EMPTY" "$TEM_TXT" "$PRECISOU" "ok" "$out" "$LANG_F"
        else
            rm -f "$out" 2>/dev/null
            echo "    FALHOU (rc=$RUN_OCR_RC: $(rc_motivo "$RUN_OCR_RC")): $f | tempo: $(fmt_dur $((SECONDS-file_start)))" >&2
            ocr_fail=$((ocr_fail+1))
            csv_add "$base_f" "$f" "$PG_TOTAL" "$PG_EMPTY" "$TEM_TXT" "$PRECISOU" "FALHOU: $(rc_motivo "$RUN_OCR_RC")" "" "$LANG_F"
        fi
    fi
done

echo "============================================================"
echo "Total analisados          : $total"
echo "Ja pesquisaveis (pulados) : $skipped"
[[ "$exists" -gt 0 ]] && echo "Ja tinham _OCR (pulados)  : $exists"
echo "OCR com sucesso           : $ocr_ok"
echo "Falhas                    : $ocr_fail"
echo "Tempo total               : $(fmt_dur $((SECONDS-RUN_START)))"
echo "Fim                       : $(date '+%Y-%m-%d %H:%M:%S')"
[[ "$CSV" == 1 ]] && echo "Planilha de triagem       : $CSV_FILE"
echo
echo "------------------------------------------------------------"
echo "PROXIMO PASSO (obrigatorio p/ doutrina citavel):"
echo "  source ~/venvs/acervo/bin/activate"
echo "  python _scripts/injetar_paginas.py <arquivo>_OCR.pdf -o 2-MARKDOWN-BRUTO/<arquivo>.md"
echo "  python _scripts/verificar_ancoras.py 2-MARKDOWN-BRUTO/"
echo "Sem esse passo o PDF esta pesquisavel, mas o markdown NAO tera as ancoras"
echo "de pagina -> a fonte nao servira para citacao ABNT."
echo "------------------------------------------------------------"

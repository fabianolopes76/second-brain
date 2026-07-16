#!/usr/bin/env bash
# ============================================================
#  iniciar-acervo.sh — abre o painel do Acervo SEM terminal.
#  Linux: duplo-clique → "Executar". WSL2: ./iniciar-acervo.sh
#  O navegador abre sozinho (no WSL2, o navegador do WINDOWS).
# ============================================================
cd "$(dirname "$0")"

URL="http://localhost:8765"

abrir_navegador() {
    # No WSL o navegador mora no WINDOWS — xdg-open só olharia o Linux
    # (e, sem navegador Linux instalado, falha com ruído "not found").
    if grep -qi microsoft /proc/version 2>/dev/null || [ -n "${WSL_DISTRO_NAME:-}" ]; then
        local ps=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
        local ex=/mnt/c/Windows/explorer.exe
        if command -v wslview >/dev/null 2>&1; then
            wslview "$URL" >/dev/null 2>&1; return
        fi
        if command -v powershell.exe >/dev/null 2>&1; then
            powershell.exe -NoProfile -Command "Start-Process '$URL'" >/dev/null 2>&1; return
        fi
        if [ -x "$ps" ]; then
            "$ps" -NoProfile -Command "Start-Process '$URL'" >/dev/null 2>&1; return
        fi
        if command -v explorer.exe >/dev/null 2>&1; then
            explorer.exe "$URL" >/dev/null 2>&1; return   # rc≠0 mesmo abrindo — ignorar
        fi
        if [ -x "$ex" ]; then
            "$ex" "$URL" >/dev/null 2>&1; return
        fi
    elif command -v xdg-open >/dev/null 2>&1 && xdg-open "$URL" >/dev/null 2>&1; then
        return
    fi
    echo "  (não achei navegador para abrir sozinho — abra manualmente: $URL)"
}

# Painel JA no ar? (janela anterior aberta, ou inicializador rodado 2x)
# Nao derruba nem morre com "Address already in use": so abre o navegador.
if python3 -c "
import urllib.request, sys
try:
    sys.exit(0 if urllib.request.urlopen('$URL/api/estado', timeout=2).status == 200 else 1)
except Exception:
    sys.exit(1)" 2>/dev/null; then
    echo "O painel JA esta no ar — abrindo o navegador em $URL"
    echo "(para reiniciar, ex. apos atualizar: feche a janela anterior ou rode"
    echo "   pkill -f acervo_app.py"
    echo " e execute este inicializador de novo)"
    abrir_navegador
    exit 0
fi

( sleep 2; abrir_navegador ) &

exec python3 acervo_app.py

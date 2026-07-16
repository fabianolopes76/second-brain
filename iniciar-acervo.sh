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

( sleep 2; abrir_navegador ) &

exec python3 acervo_app.py

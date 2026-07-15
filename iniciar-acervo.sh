#!/usr/bin/env bash
# ============================================================
#  iniciar-acervo.sh — abre o painel do Acervo SEM terminal.
#  No Linux (ou WSL com gerenciador de arquivos): duplo-clique
#  neste arquivo e escolha "Executar". O navegador abre sozinho.
# ============================================================
cd "$(dirname "$0")"

# abre o navegador assim que o servidor subir
( sleep 2
  if command -v xdg-open >/dev/null 2>&1; then xdg-open http://localhost:8765
  elif command -v wslview >/dev/null 2>&1; then wslview http://localhost:8765
  elif command -v explorer.exe >/dev/null 2>&1; then explorer.exe "http://localhost:8765"
  fi ) &

exec python3 acervo_app.py

@echo off
REM ============================================================
REM  Iniciar-Acervo.bat - abre o painel do Acervo SEM terminal.
REM  Duplo-clique neste arquivo (no Windows): ele sobe o servidor
REM  dentro do WSL2 e abre o navegador sozinho.
REM
REM  Requisitos (uma vez): WSL2 instalado e o projeto em
REM  ~/projects/second-brain (veja o GUIA-VISUAL.md).
REM ============================================================
title Acervo - Painel de Controle

REM 1) sobe o servidor no WSL2 (a janela fica aberta mostrando o log;
REM    minimize-a — fechar essa janela DESLIGA o painel)
start "Acervo (servidor - nao feche; minimize)" wsl -e bash -lc "cd ~/projects/second-brain && python3 acervo_app.py"

REM 2) espera o servidor subir e abre o navegador
timeout /t 3 /nobreak >nul
start "" http://localhost:8765

exit

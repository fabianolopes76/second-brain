#!/usr/bin/env python3
"""
preparar.py — Conserta os scripts depois de baixá-los pelo Windows.

POR QUE ESTE ARQUIVO É PYTHON, E NÃO .sh
----------------------------------------
Arquivos que passam pelo Windows chegam ao WSL2 com quebras de linha CRLF
(\\r\\n). Num script bash isso é fatal: o \\r gruda no shebang e o Linux passa a
procurar um interpretador chamado "bash\\r".

  Sintomas:  "command not found"  ·  "/usr/bin/env: 'bash\\r': No such file"
             "Permission denied"  (falta o +x)

Um .sh não consegue se autoconsertar: o bash analisa o arquivo inteiro antes de
executar e aborta no primeiro erro de sintaxe causado pelo \\r. Python, ao
contrário, lê CRLF sem reclamar. Por isso o preparador é .py.

USO (uma vez, depois de copiar o pacote para o WSL2):

    python3 preparar.py
"""

import os
import py_compile
import stat
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def tem_crlf(f: Path) -> bool:
    try:
        return b"\r\n" in f.read_bytes()
    except Exception:
        return False


def main():
    print(f"Preparando scripts em: {AQUI}\n")

    # 1) lixo do Windows (metadado "veio da internet")
    zonas = list(AQUI.glob("*Zone.Identifier*"))
    for z in zonas:
        try:
            z.unlink()
        except Exception:
            pass
    print(f"  {'✓' if zonas else '—'} :Zone.Identifier removidos: {len(zonas)}")

    # 2) CRLF -> LF
    alvos = sorted(list(AQUI.glob("*.sh")) + list(AQUI.glob("*.py")))
    n = 0
    for f in alvos:
        if tem_crlf(f):
            f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
            n += 1
    print(f"  {'✓' if n else '—'} convertidos de CRLF (Windows) para LF (Linux): {n}")

    # 3) permissão de execução nos .sh
    shs = sorted(AQUI.glob("*.sh"))
    for f in shs:
        f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  ✓ permissão de execução aplicada a {len(shs)} script(s) .sh")

    # 4) verificação
    print("\nVerificação:")
    erros = 0
    for f in shs:
        if tem_crlf(f):
            print(f"  ✗ {f.name} — ainda com CRLF"); erros += 1
        elif not os.access(f, os.X_OK):
            print(f"  ✗ {f.name} — não executável"); erros += 1
        else:
            print(f"  ✓ {f.name}")
    for f in sorted(AQUI.glob("*.py")):
        if f.name == Path(__file__).name:
            continue
        try:
            py_compile.compile(str(f), doraise=True, quiet=1)
            print(f"  ✓ {f.name}")
        except Exception as e:
            print(f"  ✗ {f.name} — não compila: {e}"); erros += 1

    cache = AQUI / "__pycache__"
    if cache.is_dir():
        for c in cache.iterdir():
            c.unlink()
        cache.rmdir()

    print()
    if erros:
        print(f"{erros} problema(s) acima. Revise antes de continuar.")
        sys.exit(1)

    print("=" * 62)
    print("Tudo pronto. Próximo passo:\n")
    print('  bash corrigir_acervo.sh "/mnt/c/Users/SeuUsuario/.../_Analise"\n')
    print("NÃO use sudo. Os scripts não precisam de root — e rodar como root")
    print("cria arquivos que depois só o root consegue alterar.")
    print("=" * 62)


if __name__ == "__main__":
    main()

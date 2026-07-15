#!/usr/bin/env python3
"""
acervo_app.py — Painel de Gerenciamento do Acervo
==========================================================
Servidor local que roda no WSL2 e é acessado pelo navegador do Windows.
Orquestra o pipeline: Triagem → OCR → Paginação → Validação.

POR QUE ASSIM (WSL2 + Windows)
------------------------------
- Seus arquivos estão no Windows (C:\\Users\\...\\drive).
- As ferramentas (ocrmypdf, tesseract) rodam bem no Linux/WSL2.
- O WSL2 enxerga o disco do Windows em /mnt/c/...
- O Windows enxerga o localhost do WSL2 automaticamente.
=> Servidor no WSL2, interface no navegador do Windows. Sem instalar nada no Windows.

REQUISITOS
----------
Só a biblioteca padrão do Python 3 (nenhum pip install para o app em si).
As ferramentas do pipeline continuam sendo:
    sudo apt install -y ocrmypdf tesseract-ocr-por poppler-utils unpaper
    python3 -m venv ~/venvs/acervo && source ~/venvs/acervo/bin/activate && pip install pymupdf

COMO USAR
---------
    # no WSL2:
    python3 acervo_app.py
    # depois, no navegador do WINDOWS:
    http://localhost:8765

Opções:
    python3 acervo_app.py --port 8765 --scripts /caminho/para/_scripts
"""

import argparse
import csv
import html
import io
import json
import os
import re
import shlex
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import taxonomia
import triagem

# ---------------------------------------------------------------------------
# Estado global de execução (um job por vez — simples e previsível)
# ---------------------------------------------------------------------------
class Job:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.name = ""
        self.log = []
        self.rc = None
        self.started = None

    def start(self, name, cmd, cwd=None, env=None):
        with self.lock:
            if self.running:
                return False, "Já há uma tarefa em execução."
            self.running = True
            self.name = name
            self.log = [f"$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}\n"]
            self.rc = None
            self.started = time.time()
        threading.Thread(target=self._run, args=(cmd, cwd, env), daemon=True).start()
        return True, "iniciado"

    def _run(self, cmd, cwd, env):
        try:
            e = os.environ.copy()
            if env:
                e.update(env)
            p = subprocess.Popen(
                cmd, cwd=cwd, env=e, shell=isinstance(cmd, str),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, errors="replace",
            )
            for line in p.stdout:
                with self.lock:
                    self.log.append(line)
                    if len(self.log) > 4000:
                        del self.log[:1000]
            p.wait()
            with self.lock:
                self.rc = p.returncode
                dur = int(time.time() - self.started)
                self.log.append(f"\n--- fim (código {p.returncode}) em {dur}s ---\n")
        except Exception as ex:
            with self.lock:
                self.rc = -1
                self.log.append(f"\nERRO: {ex}\n")
        finally:
            with self.lock:
                self.running = False

    def snapshot(self):
        with self.lock:
            return {
                "running": self.running,
                "name": self.name,
                "rc": self.rc,
                "log": "".join(self.log),
            }


JOB = Job()
CFG = {"root": "", "scripts": "", "venv": str(Path.home() / "venvs/acervo"),
       "lang": "auto", "lang_fallback": "por+eng"}


# ---------------------------------------------------------------------------
# Utilitários WSL2
# ---------------------------------------------------------------------------
def win_para_wsl(caminho: str) -> str:
    """C:\\Users\\Fulano\\drive  ->  /mnt/c/Users/Fulano/drive  (e expande ~)"""
    c = caminho.strip().strip('"').strip("'")
    if c.startswith("~"):
        return str(Path(c).expanduser())
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", c)
    if m:
        letra, resto = m.group(1).lower(), m.group(2).replace("\\", "/")
        return f"/mnt/{letra}/{resto}"
    return c.replace("\\", "/")


def diagnostico():
    """Confere o ambiente e devolve a lista de checagens."""
    itens = []

    def check(nome, cmd, dica):
        ok = subprocess.run(f"command -v {cmd}", shell=True,
                            capture_output=True).returncode == 0
        itens.append({"nome": nome, "ok": ok, "dica": "" if ok else dica})

    check("ocrmypdf", "ocrmypdf", "sudo apt install -y ocrmypdf")
    check("tesseract (por)", "tesseract", "sudo apt install -y tesseract-ocr-por")
    check("poppler (pdftotext)", "pdftotext", "sudo apt install -y poppler-utils")
    check("unpaper (flag --clean)", "unpaper", "sudo apt install -y unpaper")

    # Idiomas do Tesseract (acervo multilíngue: pt/en/de/fr/it/es)
    try:
        r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
        instalados = set(r.stdout.split()[1:]) if r.returncode == 0 else set()
    except Exception:
        instalados = set()
    faltando = [l for l in ["por", "eng", "deu", "fra", "ita", "spa"]
                if l not in instalados]
    itens.append({
        "nome": "idiomas Tesseract (pt/en/de/fr/it/es)",
        "ok": not faltando,
        "dica": "" if not faltando else
                "sudo apt install -y " + " ".join(f"tesseract-ocr-{l}" for l in faltando),
    })

    # venv + pymupdf
    # ATENÇÃO: caminhos SEMPRE entre aspas. Sem isso, um caminho com espaços
    # ("/mnt/c/.../_Prof. Fabiano Lopes/...") é quebrado pelo bash e o
    # `python3 -m venv` — que aceita VÁRIOS diretórios — cria venvs em lugares
    # errados, inclusive dentro da pasta do acervo.
    v = CFG["venv"]
    vq = shlex.quote(v)
    raiz = CFG.get("root") or ""
    invalido = ""
    if str(Path(v)).startswith("/mnt/"):
        invalido = "venv no disco do Windows (/mnt/...) — Dropbox/OneDrive"
    elif raiz and (Path(v) == Path(raiz)
                   or str(Path(v)).startswith(str(Path(raiz)) + os.sep)):
        invalido = "venv dentro da pasta do acervo"
    if invalido:
        itens.append({
            "nome": f"venv em local INVÁLIDO ({invalido})",
            "ok": False,
            "dica": "python3 -m venv ~/venvs/acervo && "
                    "source ~/venvs/acervo/bin/activate && pip install pymupdf",
        })
        return itens
    vpy = Path(v) / "bin" / "python"
    if vpy.exists():
        r = subprocess.run([str(vpy), "-c", "import fitz"], capture_output=True)
        itens.append({"nome": "venv + PyMuPDF", "ok": r.returncode == 0,
                      "dica": "" if r.returncode == 0
                      else f"source {vq}/bin/activate && pip install pymupdf"})
    else:
        itens.append({"nome": "venv + PyMuPDF", "ok": False,
                      "dica": f"python3 -m venv {vq} && "
                              f"source {vq}/bin/activate && pip install pymupdf"})

    # scripts
    for s in ["aplicar_ocr.sh", "injetar_paginas.py", "verificar_ancoras.py",
              "validar_yaml_abnt.py", "taxonomia.py", "frontmatter.py",
              "triagem.py", "auditar_vault.py", "publicar.py"]:
        p = Path(CFG["scripts"]) / s
        itens.append({"nome": f"script {s}", "ok": p.exists(),
                      "dica": "" if p.exists() else f"não encontrado em {CFG['scripts']}"})

    # pasta raiz
    r = CFG["root"]
    itens.append({"nome": "pasta do acervo", "ok": bool(r) and Path(r).is_dir(),
                  "dica": "" if r and Path(r).is_dir() else "defina a pasta acima"})
    return itens


def ler_csv():
    """Lê o controle.csv da pasta raiz, se existir."""
    if not CFG["root"]:
        return []
    f = Path(CFG["root"]) / "controle.csv"
    if not f.exists():
        return []
    try:
        with open(f, newline="", encoding="utf-8", errors="replace") as fh:
            return list(csv.DictReader(fh))
    except Exception:
        return []


def atalhos():
    """Locais úteis: discos do Windows (via /mnt) + pastas do WSL2."""
    lista = []
    # Discos do Windows montados pelo WSL2 (/mnt/c, /mnt/d, ...)
    mnt = Path("/mnt")
    if mnt.is_dir():
        for d in sorted(mnt.iterdir()):
            if d.is_dir() and len(d.name) == 1 and d.name.isalpha():
                # só lista se estiver realmente acessível
                try:
                    next(d.iterdir(), None)
                    lista.append({"nome": f"Windows {d.name.upper()}:", "path": str(d),
                                  "tipo": "windows"})
                except (PermissionError, OSError):
                    pass
    # Pastas típicas do usuário no Windows
    for base in list(Path("/mnt/c/Users").iterdir()) if Path("/mnt/c/Users").is_dir() else []:
        if base.is_dir() and base.name not in ("Public", "Default", "All Users"):
            for sub in ("OneDrive/Documents", "Documents", "Downloads", "Desktop"):
                alvo = base / sub
                if alvo.is_dir():
                    lista.append({"nome": f"{base.name} · {sub.split('/')[-1]}",
                                  "path": str(alvo), "tipo": "windows"})
            break  # só o primeiro usuário, para não poluir
    # WSL2
    lista.append({"nome": "Home (WSL2)", "path": str(Path.home()), "tipo": "wsl"})
    if CFG.get("scripts"):
        lista.append({"nome": "Scripts", "path": CFG["scripts"], "tipo": "wsl"})
    if CFG.get("root"):
        lista.append({"nome": "Acervo atual", "path": CFG["root"], "tipo": "wsl"})
    return lista


def listar_pasta(caminho: str, modo: str = "dir"):
    """Lista subpastas (e arquivos, se modo='file') de um diretório.
    modo: 'dir' = só pastas | 'file' = pastas + PDFs."""
    p = Path(caminho) if caminho else Path.home()
    if not p.is_dir():
        p = p.parent if p.parent.is_dir() else Path.home()

    pastas, arquivos = [], []
    try:
        for item in sorted(p.iterdir(), key=lambda x: x.name.lower()):
            if item.name.startswith("."):
                continue
            try:
                if item.is_dir():
                    n_pdf = 0
                    try:  # contagem rasa, só para orientar o usuário
                        n_pdf = sum(1 for f in item.iterdir()
                                    if f.suffix.lower() == ".pdf")
                    except (PermissionError, OSError):
                        pass
                    pastas.append({"nome": item.name, "path": str(item), "pdfs": n_pdf})
                elif modo == "file" and item.suffix.lower() in (".pdf", ".epub", ".mobi"):
                    arquivos.append({"nome": item.name, "path": str(item),
                                     "tam": item.stat().st_size})
            except (PermissionError, OSError):
                continue
    except PermissionError:
        return {"erro": f"Sem permissão para ler {p}", "path": str(p),
                "pai": str(p.parent), "pastas": [], "arquivos": []}
    except OSError as e:
        return {"erro": str(e), "path": str(p), "pai": str(p.parent),
                "pastas": [], "arquivos": []}

    # migalhas de pão (breadcrumb)
    partes, acc = [], Path(p.anchor or "/")
    partes.append({"nome": "/", "path": str(acc)})
    for parte in p.parts[1:]:
        acc = acc / parte
        partes.append({"nome": parte, "path": str(acc)})

    return {
        "path": str(p),
        "pai": str(p.parent) if p.parent != p else str(p),
        "breadcrumb": partes,
        "pastas": pastas,
        "arquivos": arquivos,
        "n_pdfs_aqui": sum(1 for f in p.glob("*.pdf")),
    }


def progresso():
    """Em que ponto do workflow o acervo está? Guia a UI e libera os passos."""
    r = {"pdfs": 0, "csv": 0, "ocr_pend": 0, "bruto": 0, "limpo": 0,
         "fatias": 0, "auditado": False, "vault": 0, "vault_auditado": False}
    if not CFG["root"] or not Path(CFG["root"]).is_dir():
        return r
    base = Path(CFG["root"])
    r["pdfs"] = contar_pdfs()

    linhas = ler_csv()
    r["csv"] = len(linhas)
    r["ocr_pend"] = sum(1 for l in linhas
                        if l.get("precisou_ocr") == "sim"
                        and (l.get("ocr_status") in ("dry_run", "")
                             or str(l.get("ocr_status", "")).startswith("FALHOU")))

    bruto = base / "2-MARKDOWN-BRUTO"
    if bruto.is_dir():
        mds = [f for f in bruto.glob("*.md") if not f.name.startswith("RELATORIO")]
        r["bruto"] = len(mds)
        r["limpo"] = sum(1 for f in bruto.glob("*.md.bak"))

    limpo = base / "3-MARKDOWN-LIMPO"
    if limpo.is_dir():
        r["fatias"] = len([f for f in limpo.rglob("*_p*.md")])

    for pasta in (bruto, limpo, base):
        if (pasta / "RELATORIO-AUDITORIA.md").exists():
            r["auditado"] = True
            break

    r["limpo_md"] = 0
    if limpo.is_dir():
        r["limpo_md"] = sum(1 for f in limpo.rglob("*.md")
                            if not f.name.startswith(("RELATORIO", "_")))

    vault = base / "4-OBSIDIAN-VAULT"
    r["publicado"] = False
    if vault.is_dir():
        # mesmo critério do auditar_vault.py: templates/radar não são notas
        _fora = {"99-Templates", "Radar", ".obsidian", ".trash"}
        r["vault"] = sum(1 for f in vault.rglob("*.md")
                         if not f.name.startswith(("RELATORIO", "_"))
                         and not any(p in _fora for p in f.parts))
        r["publicado"] = (vault / "RELATORIO-PUBLICACAO.md").exists()
        r["vault_auditado"] = (vault / "RELATORIO-VAULT.md").exists()

    # Carimbos de data das etapas concluídas (derivados do disco, como tudo).
    def _mt(p):
        try:
            return time.strftime("%d/%m %H:%M", time.localtime(p.stat().st_mtime))
        except OSError:
            return ""
    r["datas"] = {}
    if r["csv"]:
        r["datas"]["csv"] = _mt(base / "controle.csv")
    for nome, arq in (("auditado", "RELATORIO-AUDITORIA.md"),):
        for pasta in (bruto, limpo, base):
            if (pasta / arq).exists():
                r["datas"][nome] = _mt(pasta / arq)
                break
    if vault.is_dir():
        if r["publicado"]:
            r["datas"]["publicado"] = _mt(vault / "RELATORIO-PUBLICACAO.md")
        if r["vault_auditado"]:
            r["datas"]["vault_auditado"] = _mt(vault / "RELATORIO-VAULT.md")
    return r


def contar_pdfs():
    if not CFG["root"] or not Path(CFG["root"]).is_dir():
        return 0
    n = 0
    for p in Path(CFG["root"]).rglob("*"):
        if p.suffix.lower() == ".pdf" and not p.stem.endswith("_OCR"):
            n += 1
    return n


# ---------------------------------------------------------------------------
# Ações do pipeline
# ---------------------------------------------------------------------------
def acao_triagem(dry=True, force=False, modo="manter"):
    sh = Path(CFG["scripts"]) / "aplicar_ocr.sh"
    env = {
        "ROOT": CFG["root"],
        "MODE": modo,
        "DRYRUN": "1" if dry else "0",
        "FORCE_ALL": "1" if force else "0",
        "CSV": "1",
        "CSV_FILE": str(Path(CFG["root"]) / "controle.csv"),
        # Acervo multilíngue: 'auto' detecta por arquivo; ou force um idioma.
        "OCR_LANG": CFG.get("lang", "auto"),
        "OCR_LANG_FALLBACK": CFG.get("lang_fallback", "por+eng"),
        "DETECTOR": str(Path(CFG["scripts"]) / "detectar_idioma.py"),
    }
    nome = "Triagem (dry-run)" if dry else f"OCR em lote (modo={modo})"
    return JOB.start(nome, ["bash", str(sh)], cwd=CFG["root"], env=env)


def acao_paginar(offset=0, romanas=0):
    """Roda injetar_paginas.py em todos os PDFs que exigem âncora, conforme o CSV."""
    linhas = ler_csv()
    alvos = [l for l in linhas if l.get("exige_ancora_pagina", "").upper() == "SIM"]
    if not alvos:
        return False, "Nenhum arquivo exige âncora de página (rode a triagem antes)."

    vpy = Path(CFG["venv"]) / "bin" / "python"
    script = Path(CFG["scripts"]) / "injetar_paginas.py"
    saida = Path(CFG["root"]) / "2-MARKDOWN-BRUTO"
    saida.mkdir(exist_ok=True)

    cmds = []
    for l in alvos:
        # prefere o _OCR quando existe; senão, o original
        src = l.get("arquivo_ocr") or l.get("caminho")
        if not src or not Path(src).exists():
            src = l.get("caminho")
        if not src or not Path(src).exists():
            continue
        dst = saida / (Path(src).stem.replace("_OCR", "") + ".md")
        c = [str(vpy), str(script), src, "-o", str(dst)]
        if offset:
            c += ["--offset", str(offset)]
        if romanas:
            c += ["--romanas-ate", str(romanas)]
        # Aproveita o palpite de tipo_fonte da triagem para pré-preencher o YAML.
        tf = (l.get("tipo_fonte_provavel") or "").strip()
        if tf and taxonomia.eh_abnt(tf):
            c += ["--tipo-fonte", tf]
        idi = (l.get("idioma") or "").strip()
        if idi:
            c += ["--idioma", idi]
        cmds.append(" ".join(shlex.quote(x) for x in c))

    if not cmds:
        return False, "Nenhum arquivo encontrado no disco."
    script_sh = " ; ".join(f'echo ">> {i+1}/{len(cmds)}" ; {c}' for i, c in enumerate(cmds))
    return JOB.start(f"Injetar paginação ({len(cmds)} arquivo(s))", script_sh)


def _detectar_idioma_de(src: Path) -> str:
    det = Path(CFG["scripts"]) / "detectar_idioma.py"
    if not det.exists():
        return ""
    try:
        r = subprocess.run(["python3", str(det), str(src), "--csv"],
                           capture_output=True, text=True, timeout=90)
        linhas = r.stdout.strip().splitlines()
        if len(linhas) > 1:
            return linhas[1].split(",")[1]
    except Exception:
        pass
    return ""


def _tipo_do_nome(nome: str) -> str:
    """Palpite de tipo_fonte — delega a triagem.py (fonte única de heurística).

    Sem fallback cego para "livro": quando nada pontua, devolve "" e o YAML
    sai sem tipo_fonte — o validador cobra de forma visível, em vez de a
    legislação virar "livro" em silêncio.
    """
    tipo, _conf, _evid = triagem.inferir_tipo(nome)
    return tipo


def acao_lote(arquivos, offset=0, romanas=0, tipo="", idioma=""):
    """Processa 1..N arquivos escolhidos no navegador → Markdown com âncoras.

    Para cada arquivo: detecta o idioma (se não informado), infere o tipo_fonte
    pelo nome, converte e valida. Um comando encadeado, log ao vivo.
    """
    if isinstance(arquivos, str):
        arquivos = [arquivos]
    arquivos = [a for a in (arquivos or []) if a]
    if not arquivos:
        return False, "Nenhum arquivo selecionado."

    vpy = Path(CFG["venv"]) / "bin" / "python"
    script = Path(CFG["scripts"]) / "injetar_paginas.py"
    va = Path(CFG["scripts"]) / "verificar_ancoras.py"

    base = CFG["root"] or str(Path(arquivos[0]).parent)
    saida = Path(base) / "2-MARKDOWN-BRUTO"
    saida.mkdir(parents=True, exist_ok=True)

    partes, n_ok = [], 0
    for i, caminho in enumerate(arquivos, 1):
        src = Path(caminho)
        if not src.exists():
            partes.append(f'echo ">> [{i}/{len(arquivos)}] {shlex.quote(src.name)}: '
                          f'ARQUIVO NAO ENCONTRADO"')
            continue
        n_ok += 1
        dst = saida / (src.stem.replace("_OCR", "") + ".md")
        cab = f'echo "" ; echo ">> [{i}/{len(arquivos)}] {src.name}"'

        if src.suffix.lower() in (".epub", ".mobi", ".azw3"):
            # Rota A (Calibre). ePUB/MOBI não têm paginação fixa — avisa.
            tmp = dst.with_suffix(".txt")
            partes.append(
                f'{cab} ; ebook-convert {shlex.quote(str(src))} {shlex.quote(str(tmp))} '
                f'--txt-output-formatting=markdown --enable-heuristics --keep-links '
                f'--txt-output-encoding=utf-8 --chapter "//h:h1" && '
                f'mv {shlex.quote(str(tmp))} {shlex.quote(str(dst))} && '
                f'echo "   AVISO: ePUB/MOBI nao tem paginacao fixa -> nao serve para '
                f'citacao ABNT com pagina. Use o PDF paginado."'
            )
            continue

        idi = idioma or _detectar_idioma_de(src)
        tf = tipo or _tipo_do_nome(src.name)

        c = [str(vpy), str(script), str(src), "-o", str(dst)]
        if offset:
            c += ["--offset", str(offset)]
        if romanas:
            c += ["--romanas-ate", str(romanas)]
        if tf and taxonomia.eh_abnt(tf):
            c += ["--tipo-fonte", tf]
        if idi:
            c += ["--idioma", idi]
        partes.append(
            f'{cab} ; echo "   tipo={tf} idioma={idi or "?"}" ; '
            + " ".join(shlex.quote(x) for x in c)
        )

    # Validação final de tudo que foi gerado
    partes.append(f'echo "" ; echo "=== VALIDACAO ===" ; '
                  f'{shlex.quote(str(vpy))} {shlex.quote(str(va))} {shlex.quote(str(saida))}')

    nome = (f"Converter {n_ok} arquivo(s)" if n_ok != 1
            else f"Converter {Path(arquivos[0]).name}")
    return JOB.start(nome, " ; ".join(partes))


def acao_limpar(pasta=""):
    """Limpeza mecânica do OCR — sem IA, sem custo de token."""
    alvo = Path(pasta) if pasta else (Path(CFG["root"]) / "2-MARKDOWN-BRUTO")
    if not alvo.exists():
        return False, "Pasta não encontrada. Converta os PDFs antes."
    s = Path(CFG["scripts"]) / "limpar_ocr.py"
    return JOB.start("Limpar OCR (mecânico)",
                     f'python3 {shlex.quote(str(s))} {shlex.quote(str(alvo))} --inplace')


def acao_fatiar(pasta="", palavras=1200):
    """Fatia arquivos grandes em nota-índice + fatias (duas camadas)."""
    alvo = Path(pasta) if pasta else (Path(CFG["root"]) / "2-MARKDOWN-BRUTO")
    if not alvo.exists():
        return False, "Pasta não encontrada."
    s = Path(CFG["scripts"]) / "fatiar.py"
    saida = Path(CFG["root"]) / "3-MARKDOWN-LIMPO"
    return JOB.start("Fatiar (duas camadas)",
                     f'python3 {shlex.quote(str(s))} {shlex.quote(str(alvo))} '
                     f'-o {shlex.quote(str(saida))} --palavras {int(palavras)}')


def acao_corrigir_idioma():
    """Redetecta o idioma a partir do PDF-fonte e corrige o YAML já gerado."""
    base = Path(CFG["root"])
    bruto = base / "2-MARKDOWN-BRUTO"
    if not bruto.is_dir():
        return False, "Não há 2-MARKDOWN-BRUTO. Converta antes."
    s = Path(CFG["scripts"]) / "corrigir_idioma.py"
    return JOB.start("Corrigir idioma (redetecta no PDF)",
                     f'python3 {shlex.quote(str(s))} {shlex.quote(str(bruto))} '
                     f'--pdfs {shlex.quote(str(base))}')


def acao_normalizar():
    """Deixa area/tags/autoria no formato que o Obsidian e o Dataview exigem."""
    base = Path(CFG["root"])
    alvo = base / "2-MARKDOWN-BRUTO" / "fatias"
    if not alvo.is_dir():
        alvo = base / "2-MARKDOWN-BRUTO"
    if not alvo.is_dir():
        return False, "Converta e fatie antes."
    s = Path(CFG["scripts"]) / "normalizar_yaml.py"
    return JOB.start("Normalizar YAML (Obsidian)",
                     f'python3 {shlex.quote(str(s))} {shlex.quote(str(alvo))}')


def acao_auditar(pasta=""):
    """Audita se o conteúdo gerado atende aos requisitos do segundo cérebro."""
    alvo = Path(pasta) if pasta else (Path(CFG["root"]) / "2-MARKDOWN-BRUTO")
    if not alvo.is_dir():
        # cai para a raiz do acervo, se ali houver .md
        alvo = Path(CFG["root"])
    if not alvo.is_dir():
        return False, "Defina a pasta do acervo."
    aud = Path(CFG["scripts"]) / "auditar_acervo.py"
    if not aud.exists():
        return False, "auditar_acervo.py não encontrado na pasta de scripts."
    cmd = f'python3 {shlex.quote(str(aud))} {shlex.quote(str(alvo))}'
    return JOB.start(f"Auditar {alvo.name}", cmd)


def acao_validar():
    vpy = Path(CFG["venv"]) / "bin" / "python"
    va = Path(CFG["scripts"]) / "verificar_ancoras.py"
    vy = Path(CFG["scripts"]) / "validar_yaml_abnt.py"
    pasta = Path(CFG["root"]) / "2-MARKDOWN-BRUTO"
    if not pasta.is_dir():
        return False, "Pasta 2-MARKDOWN-BRUTO não existe. Rode a paginação antes."
    cmd = (f'{shlex.quote(str(vpy))} {shlex.quote(str(va))} {shlex.quote(str(pasta))} ; '
           f'echo "" ; echo "=== YAML ===" ; '
           f'{shlex.quote(str(vpy))} {shlex.quote(str(vy))} {shlex.quote(str(pasta))} --gerar')
    return JOB.start("Validação (âncoras + YAML)", cmd)


def acao_publicar(pasta="", dry=True, force=False):
    """FASE 5 determinística: distribui 3-MARKDOWN-LIMPO no vault por regra
    (tipo→pasta do perfil), com trava de validação e vault vencendo conflito."""
    origem = Path(CFG["root"]) / "3-MARKDOWN-LIMPO"
    if not origem.is_dir():
        return False, ("Pasta 3-MARKDOWN-LIMPO não existe — o que se publica "
                       "é o produto FINAL (Fases 3-4). Fatie/valide antes.")
    alvo = Path(pasta) if pasta else (Path(CFG["root"]) / "4-OBSIDIAN-VAULT")
    pub = Path(CFG["scripts"]) / "publicar.py"
    if not pub.exists():
        return False, "publicar.py não encontrado na pasta de scripts."
    flags = (" --dry" if dry else "") + (" --force" if force else "")
    cmd = (f'python3 {shlex.quote(str(pub))} {shlex.quote(str(origem))} '
           f'{shlex.quote(str(alvo))}{flags}')
    nome = "Publicar (dry-run)" if dry else "Publicar no vault"
    return JOB.start(nome, cmd)


def acao_auditar_vault(pasta=""):
    """Audita o GRAFO do vault: fatias órfãs, partes inconsistentes, wikilinks
    quebrados, vocabulário que esconde notas dos painéis, áreas sem MOC."""
    alvo = Path(pasta) if pasta else (Path(CFG["root"]) / "4-OBSIDIAN-VAULT")
    if not alvo.is_dir():
        return False, (f"Pasta do vault não encontrada: {alvo}. "
                       "Publique o conteúdo no vault antes (Fase 5), ou "
                       "informe o caminho no campo da etapa.")
    av = Path(CFG["scripts"]) / "auditar_vault.py"
    if not av.exists():
        return False, "auditar_vault.py não encontrado na pasta de scripts."
    cmd = f'python3 {shlex.quote(str(av))} {shlex.quote(str(alvo))} --detalhado'
    return JOB.start(f"Auditar vault {alvo.name}", cmd)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silencia o log padrão

    def _send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self._send(200, PAGINA, "text/html")
        if u.path == "/api/navegar":
            q = parse_qs(u.query)
            caminho = q.get("path", [""])[0]
            modo = q.get("modo", ["dir"])[0]
            return self._send(200, json.dumps(listar_pasta(caminho, modo),
                                              ensure_ascii=False))
        if u.path == "/api/atalhos":
            return self._send(200, json.dumps(atalhos(), ensure_ascii=False))
        if u.path == "/api/estado":
            return self._send(200, json.dumps({
                "cfg": CFG,
                "job": JOB.snapshot(),
                "diag": diagnostico(),
                "csv": ler_csv(),
                "n_pdfs": contar_pdfs(),
                "prog": progresso(),
            }))
        self._send(404, "{}")

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n) or "{}")

        if u.path == "/api/config":
            # Cada campo é tratado de forma INDEPENDENTE. Antes, um venv inválido
            # fazia o POST inteiro falhar — e a pasta do acervo nunca era salva.
            avisos = []

            if data.get("root"):
                r = win_para_wsl(data["root"])
                if Path(r).is_dir():
                    CFG["root"] = r
                else:
                    avisos.append(f"Pasta do acervo não encontrada: {r}")

            if data.get("scripts"):
                CFG["scripts"] = win_para_wsl(data["scripts"])

            if data.get("venv"):
                novo_venv = win_para_wsl(data["venv"])
                raiz = CFG.get("root") or ""

                # TRAVA 1 (absoluta): venv jamais no disco do Windows (/mnt/...).
                # Ali ficam Dropbox/OneDrive; um venv lá sincroniza milhares de
                # arquivos e fica lentíssimo. Vale mesmo com o acervo em branco —
                # era a brecha que deixava o app sugerir o comando destrutivo.
                if str(Path(novo_venv)).startswith("/mnt/"):
                    avisos.append(
                        "O venv NÃO pode ficar no disco do Windows (/mnt/...). "
                        "Ali estão Dropbox/OneDrive: o venv sincronizaria milhares de "
                        "arquivos e ficaria lentíssimo.\n\n"
                        "Use ~/venvs/acervo (disco do Linux). "
                        "Mantido o valor anterior: " + CFG["venv"])
                    return self._send(200, json.dumps(
                        {"ok": False, "avisos": avisos, "cfg": CFG}, ensure_ascii=False))

                # TRAVA 2: venv dentro da pasta do acervo
                dentro = bool(raiz) and (
                    Path(novo_venv) == Path(raiz)
                    or str(Path(novo_venv)).startswith(str(Path(raiz)) + os.sep))
                if dentro:
                    # TRAVA: um venv dentro do acervo enche a pasta dos livros de
                    # arquivos do Python — e o Dropbox sincroniza tudo.
                    avisos.append(
                        "O venv NÃO pode ficar dentro da pasta do acervo — isso encheria "
                        "a pasta dos livros de arquivos do Python (e o Dropbox "
                        "sincronizaria tudo). Mantido o valor anterior: "
                        + CFG["venv"])
                else:
                    CFG["venv"] = novo_venv

            if data.get("lang"):
                CFG["lang"] = data["lang"]
            if data.get("lang_fallback"):
                CFG["lang_fallback"] = data["lang_fallback"]

            return self._send(200, json.dumps(
                {"ok": not avisos, "avisos": avisos, "cfg": CFG}, ensure_ascii=False))

        if u.path == "/api/acao":
            a = data.get("acao")
            if a != "arquivo" and (not CFG["root"] or not Path(CFG["root"]).is_dir()):
                return self._send(200, json.dumps(
                    {"ok": False, "msg": "Defina uma pasta válida do acervo."}))
            if a == "triagem":
                ok, msg = acao_triagem(dry=True)
            elif a == "ocr":
                ok, msg = acao_triagem(dry=False, modo=data.get("modo", "manter"),
                                       force=bool(data.get("force")))
            elif a == "paginar":
                ok, msg = acao_paginar(int(data.get("offset") or 0),
                                       int(data.get("romanas") or 0))
            elif a == "arquivo":
                ok, msg = acao_lote(data.get("arquivos") or data.get("arquivo") or [],
                                    int(data.get("offset") or 0),
                                    int(data.get("romanas") or 0),
                                    data.get("tipo", ""), data.get("idioma", ""))
            elif a == "limpar":
                ok, msg = acao_limpar(data.get("pasta", ""))
            elif a == "fatiar":
                ok, msg = acao_fatiar(data.get("pasta", ""),
                                      data.get("palavras") or 1200)
            elif a == "corrigir_idioma":
                ok, msg = acao_corrigir_idioma()
            elif a == "normalizar":
                ok, msg = acao_normalizar()
            elif a == "auditar":
                ok, msg = acao_auditar(data.get("pasta", ""))
            elif a == "validar":
                ok, msg = acao_validar()
            elif a == "publicar":
                ok, msg = acao_publicar(data.get("pasta", ""),
                                        dry=bool(data.get("dry", True)),
                                        force=bool(data.get("force", False)))
            elif a == "auditar_vault":
                ok, msg = acao_auditar_vault(data.get("pasta", ""))
            else:
                ok, msg = False, "Ação desconhecida."
            return self._send(200, json.dumps({"ok": ok, "msg": msg}))

        self._send(404, "{}")


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
PAGINA = r"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Acervo</title>
<style>
:root{
  --ink:#1b2a41; --ink-2:#43506a; --muted:#6b7280; --paper:#f2f1ec; --surf:#fff;
  --surf2:#faf9f5; --line:#dedbd2; --burg:#7a2e3a; --brass:#a9863f;
  --ok:#3f7a5a; --warn:#a9772a; --err:#9a3b34;
  --serif:"Iowan Old Style",Palatino,Georgia,serif;
  --sans:-apple-system,"Segoe UI",Roboto,Ubuntu,sans-serif;
  --mono:"Cascadia Code",Consolas,"Roboto Mono",monospace;
  --sh:0 1px 2px rgba(27,42,65,.06),0 8px 24px rgba(27,42,65,.06);
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 var(--sans)}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 70px}
header{position:sticky;top:0;z-index:20;background:rgba(242,241,236,.92);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line);margin-bottom:22px}
header .wrap{display:flex;align-items:center;gap:14px;padding:11px 20px}
h1{font:600 19px/1.15 var(--serif);margin:0}
h1 small{display:block;font:400 11px/1.3 var(--sans);color:var(--muted);
  text-transform:uppercase;letter-spacing:.4px}
.sp{flex:1}
.badge{font-size:12px;padding:4px 10px;border-radius:20px;border:1px solid var(--line);
  background:var(--surf);white-space:nowrap}
.badge.on{border-color:var(--ok);color:var(--ok)}
.badge.run{border-color:var(--burg);color:var(--burg)}
section{margin-bottom:24px}
.head{display:flex;align-items:baseline;gap:10px;margin-bottom:11px}
.head .n{font:600 13px var(--serif);color:var(--burg)}
.head h2{font:600 17px var(--serif);margin:0}
.head p{margin:0;font-size:12.5px;color:var(--muted)}
.card{background:var(--surf);border:1px solid var(--line);border-radius:12px;padding:16px;box-shadow:var(--sh)}
label{display:block;font-size:11.5px;color:var(--muted);margin-bottom:4px}
input[type=text],input[type=number],select{width:100%;border:1px solid var(--line);border-radius:8px;
  padding:8px 10px;font:13px var(--mono);background:var(--surf2);color:var(--ink)}
select{font-family:var(--sans)}
/* Configuração: linha principal + 3 colunas iguais. O problema antigo era um
   grid de 4 colunas com rótulo longo quebrando em 2 linhas — a fileira inteira
   desalinhava e os inputs ficavam com 6 caracteres visíveis. */
.row{display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:end}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:14px}
.campo{min-width:0}
.campo label{display:block;font-size:11.5px;color:var(--muted);margin-bottom:5px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.campo .inrow{display:flex;gap:5px;align-items:stretch}
.campo input,.campo select{height:38px;min-width:0}
.campo .bnav{height:38px;padding:0 10px;display:flex;align-items:center;justify-content:center}
.eco{margin-top:8px;font:11.5px var(--mono);color:var(--muted);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;direction:rtl;text-align:left}
.eco:empty{display:none}
button{font:500 13px var(--sans);border:1px solid var(--line);background:var(--surf);
  color:var(--ink);padding:9px 14px;border-radius:8px;cursor:pointer;white-space:nowrap}
button:hover:not(:disabled){border-color:var(--burg);color:var(--burg)}
button.primary{background:var(--ink);color:#fff;border-color:var(--ink)}
button.primary:hover:not(:disabled){background:var(--burg);border-color:var(--burg);color:#fff}
button:disabled{opacity:.4;cursor:not-allowed}
.inrow{display:flex;gap:6px}
.inrow input{flex:1;min-width:0}
.bnav{flex-shrink:0;padding:8px 11px}

/* ================= PIPELINE — trilho guiado ================= */
.trilho{display:flex;flex-direction:column;gap:0}
.et{display:grid;grid-template-columns:44px 1fr;gap:0;position:relative}
.et .bar{display:flex;flex-direction:column;align-items:center}
.et .dot{width:26px;height:26px;border-radius:50%;border:2px solid var(--line);
  background:var(--surf);display:flex;align-items:center;justify-content:center;
  font:600 11px var(--sans);color:var(--muted);flex-shrink:0;z-index:2;transition:.2s}
.et .linha{width:2px;flex:1;background:var(--line);min-height:14px}
.et:last-child .linha{display:none}
.et.feito .dot{border-color:var(--ok);background:var(--ok);color:#fff}
.et.ativa .dot{border-color:var(--burg);background:var(--burg);color:#fff;
  box-shadow:0 0 0 4px rgba(122,46,58,.12)}
.et.bloq .dot{opacity:.45}
.et.feito .linha{background:var(--ok)}
.et .conteudo{background:var(--surf);border:1px solid var(--line);border-radius:12px;
  padding:13px 15px;margin:0 0 10px 12px;box-shadow:var(--sh);transition:.2s}
.et.ativa .conteudo{border-color:var(--burg);box-shadow:0 2px 14px rgba(122,46,58,.10)}
.et.bloq .conteudo{opacity:.55}
.et .topo{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.et h3{font:600 15px var(--serif);margin:0;flex-shrink:0}
.et .desc{font-size:12.5px;color:var(--muted);flex:1;min-width:180px}
.et .acoes{display:flex;gap:6px;align-items:center;flex-shrink:0}
.et .st{font-size:11.5px;padding:2px 8px;border-radius:12px;border:1px solid var(--line);
  color:var(--muted);white-space:nowrap}
.et .st.ok{border-color:var(--ok);color:var(--ok)}
.et .st.pend{border-color:var(--warn);color:var(--warn)}
.et .extra{margin-top:9px;padding-top:9px;border-top:1px dashed var(--line);display:none}
.et.ativa .extra,.et .extra.show{display:block}
.dica{font-size:11.5px;color:var(--muted);margin-top:6px}
.dica b{color:var(--ink-2)}
.fase{font:600 10px var(--sans);letter-spacing:.1em;text-transform:uppercase;
  color:var(--brass);margin:14px 0 6px 56px}
.fase:first-child{margin-top:0}

/* ---- fila ---- */
.fila{max-height:120px;overflow:auto;border:1px solid var(--line);border-radius:8px;
  background:var(--surf2);margin-bottom:8px}
.fila:empty{display:none}
.fi{display:flex;align-items:center;gap:7px;padding:5px 8px;font-size:11.5px;
  border-bottom:1px solid var(--line)}
.fi:last-child{border-bottom:none}
.fi .n{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;direction:rtl;text-align:left}
.fi .rm{background:none;border:none;color:var(--muted);cursor:pointer;padding:0 3px;font-size:14px}
.fi .rm:hover{color:var(--err)}

/* ---- diagnóstico ---- */
.diag{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.d{display:flex;gap:8px;align-items:flex-start;font-size:12.5px;padding:5px 8px;border-radius:6px}
.d:hover{background:var(--surf2)}
.d .i{font-weight:700;width:14px;flex-shrink:0}
.d.ok .i{color:var(--ok)} .d.no .i{color:var(--err)}
.d .dicatxt{display:block;font:11.5px var(--mono);color:var(--muted);margin-top:2px}
.cmd{display:flex;align-items:center;gap:6px;margin-top:4px;background:var(--ink);
  border-radius:7px;padding:6px 6px 6px 10px}
.cmd code{flex:1;font:11.5px/1.5 var(--mono);color:#eef1f6;word-break:break-all;user-select:all}
.cp{background:#2b3a54;border:1px solid #3a4a66;color:#cdd6e6;font:11px var(--sans);
  padding:3px 9px;border-radius:5px;cursor:pointer;flex-shrink:0}
.cp:hover{background:#354564}
.cp.ok{background:var(--ok);border-color:var(--ok);color:#fff}
.pend{background:#fff6f4;border:1px solid var(--err);border-radius:10px;padding:12px 14px;margin-bottom:12px}
.pend h4{margin:0 0 6px;font:600 13.5px var(--sans);color:var(--err)}
.tudo-ok{display:flex;align-items:center;gap:8px;color:var(--ok);font-size:13px;
  background:#f2f8f4;border:1px solid var(--ok);border-radius:10px;padding:10px 14px;margin-bottom:12px}

/* ---- log ---- */
pre{margin:0;background:var(--ink);color:#eef1f6;border-radius:9px;padding:12px;
  font:12.5px/1.6 var(--mono);max-height:320px;overflow:auto;white-space:pre-wrap;word-break:break-word}

/* ---- tabela ---- */
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--muted);border-bottom:1px solid var(--line);padding:8px 6px;position:sticky;top:0;background:var(--surf)}
td{padding:7px 6px;border-bottom:1px solid var(--line)}
tr:hover td{background:var(--surf2)}
.tw{max-height:320px;overflow:auto;border:1px solid var(--line);border-radius:10px;background:var(--surf);resize:vertical}
.pill{font-size:11px;padding:2px 7px;border-radius:12px;border:1px solid var(--line);white-space:nowrap}
.pill.sim{border-color:var(--burg);color:var(--burg)}
.pill.ok{border-color:var(--ok);color:var(--ok)}
.pill.no{border-color:var(--warn);color:var(--warn)}
.stat{display:flex;gap:18px;margin-top:10px;font-size:12.5px;color:var(--muted);flex-wrap:wrap}
.stat b{color:var(--ink);font:600 16px var(--serif)}
.nota{background:var(--surf2);border:1px solid var(--line);border-left:3px solid var(--brass);
  border-radius:8px;padding:11px 13px;font-size:12.5px;color:var(--ink-2);margin-top:12px}

/* ================= MODAL arrastável + redimensionável ================= */
.ov{position:fixed;inset:0;background:rgba(27,42,65,.4);display:none;z-index:100}
.ov.on{display:block}
.mod{position:fixed;background:var(--paper);border-radius:12px;display:flex;flex-direction:column;
  box-shadow:0 24px 70px rgba(27,42,65,.35);overflow:hidden;
  min-width:420px;min-height:280px;width:860px;height:600px;
  top:60px;left:calc(50% - 430px)}
.mod .mh{display:flex;align-items:center;gap:10px;padding:11px 14px;background:var(--surf);
  border-bottom:1px solid var(--line);cursor:move;user-select:none;flex-shrink:0}
.mod .mh h3{font:600 14.5px var(--serif);margin:0;flex:1}
.mod .mh .hint{font-size:11px;color:var(--muted)}
.mod .x{background:none;border:none;font-size:20px;color:var(--muted);cursor:pointer;padding:0 6px}
.mod .x:hover{color:var(--err)}
.mbody{display:flex;flex:1;min-height:0}
.side{width:200px;border-right:1px solid var(--line);background:var(--surf2);overflow:auto;padding:8px;flex-shrink:0}
.side .t{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
  padding:6px 8px 3px;font-weight:600}
.side a{display:block;padding:6px 8px;border-radius:6px;font-size:12.5px;color:var(--ink);
  cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.side a:hover{background:var(--surf)}
.side a.win{color:var(--burg)}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.bc{display:flex;flex-wrap:wrap;gap:2px;align-items:center;padding:8px 12px;
  border-bottom:1px solid var(--line);background:var(--surf);font-size:12px;flex-shrink:0}
.bc a{color:var(--burg);cursor:pointer;padding:2px 5px;border-radius:4px}
.bc a:hover{background:var(--surf2)}
.bc span{color:var(--muted)}
.selbar{display:flex;align-items:center;gap:8px;padding:7px 12px;background:var(--surf2);
  border-bottom:1px solid var(--line);font-size:12px;flex-shrink:0}
.selbar .c{color:var(--burg);font-weight:600}
.selbar button{padding:4px 9px;font-size:11.5px}
.lista{flex:1;overflow:auto;padding:6px}
.it{display:flex;align-items:center;gap:9px;padding:8px 10px;border-radius:7px;cursor:pointer;font-size:13.5px}
.it:hover{background:var(--surf)}
.it .ic{width:16px;text-align:center;flex-shrink:0}
/* nomes longos: mostra o FIM do nome (mais informativo) e o todo no title */
.it .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.it .ct{font-size:11px;color:var(--muted);flex-shrink:0}
.it.sel{background:var(--ink);color:#fff}
.it.sel .ct{color:#b9c4d6}
.it input[type=checkbox]{width:16px;height:16px;accent-color:var(--burg);cursor:pointer;flex-shrink:0}
.mfoot{display:flex;align-items:center;gap:10px;padding:11px 14px;border-top:1px solid var(--line);
  background:var(--surf);flex-shrink:0}
.mfoot code{flex:1;font:11.5px var(--mono);color:var(--muted);overflow-x:auto;white-space:nowrap;
  padding:4px 6px;background:var(--surf2);border-radius:5px;border:1px solid var(--line)}
/* alça de redimensionamento */
.rz{position:absolute;background:transparent}
.rz.e{right:0;top:0;width:6px;height:100%;cursor:ew-resize}
.rz.s{bottom:0;left:0;height:6px;width:100%;cursor:ns-resize}
.rz.se{right:0;bottom:0;width:16px;height:16px;cursor:nwse-resize}
.rz.se::after{content:"";position:absolute;right:3px;bottom:3px;width:8px;height:8px;
  border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);opacity:.6}
.rz.w{left:0;top:0;width:6px;height:100%;cursor:ew-resize}

@media(max-width:900px){
  .grid3,.diag{grid-template-columns:1fr}
  .mod{width:calc(100vw - 24px)!important;height:calc(100vh - 90px)!important;
    left:12px!important;top:70px!important}
  .side{display:none}
}
</style>

<header><div class="wrap">
  <div><h1>⚖ Acervo<small>Pipeline do segundo cérebro · WSL2</small></h1></div>
  <div class="sp"></div>
  <span class="badge" id="bJob">ocioso</span>
  <span class="badge" id="bPdf">— PDFs</span>
</div></header>

<div class="wrap">

<!-- 01 CONFIG -->
<section>
  <div class="head"><span class="n">01</span><h2>Configuração</h2>
    <p>clique em Procurar — não precisa digitar caminho</p></div>
  <div class="card">
    <div class="row">
      <div class="campo">
        <label>Pasta do acervo — onde estão os PDFs</label>
        <input type="text" id="root" placeholder="clique em Procurar…">
      </div>
      <button class="bnav" style="height:38px" onclick="abrirNav('root','dir')">📁 Procurar…</button>
      <button class="primary" style="height:38px" onclick="salvar()">Definir</button>
    </div>
    <div class="eco" id="rootWsl"></div>

    <div class="grid3">
      <div class="campo">
        <label>Scripts</label>
        <div class="inrow">
          <input type="text" id="scripts">
          <button class="bnav" onclick="abrirNav('scripts','dir')">📁</button>
        </div>
      </div>
      <div class="campo">
        <label title="O venv fica no disco do Linux — nunca no Dropbox">venv — sempre ~/venvs/acervo</label>
        <div class="inrow">
          <input type="text" id="venv">
          <button class="bnav" onclick="abrirNav('venv','dir')">📁</button>
          <button class="bnav" onclick="venvPadrao()" title="restaurar ~/venvs/acervo">↺</button>
        </div>
      </div>
      <div class="campo">
        <label>Idioma do OCR</label>
        <select id="lang" onchange="salvar({lang:lang.value})">
          <option value="auto">auto — detecta por arquivo</option>
          <option value="por">português (fixo)</option>
          <option value="eng">inglês (fixo)</option>
          <option value="deu">alemão (fixo)</option>
          <option value="fra">francês (fixo)</option>
          <option value="ita">italiano (fixo)</option>
          <option value="spa">espanhol (fixo)</option>
          <option value="por+eng">português + inglês</option>
        </select>
      </div>
    </div>
  </div>
</section>

<!-- 02 DEPENDÊNCIAS -->
<section>
  <div class="head"><span class="n">02</span><h2>Ambiente</h2>
    <p>pendências viram um comando único, pronto para colar</p></div>
  <div class="card">
    <div id="pend"></div>
    <div class="diag" id="diag"></div>
  </div>
</section>

<!-- 03 PIPELINE -->
<section>
  <div class="head"><span class="n">03</span><h2>Pipeline</h2>
    <p>siga o trilho — cada etapa libera a seguinte</p></div>

  <div class="fase">Entrada</div>
  <div class="trilho">
    <div class="et" id="e1">
      <div class="bar"><div class="dot">1</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Triagem</h3>
          <span class="desc">Detecta idioma e quem precisa de OCR. Gera <code>controle.csv</code>. Não grava nada.</span>
          <span class="st" id="s1">—</span>
          <div class="acoes"><button data-a class="primary" onclick="acao('triagem')">Analisar</button></div>
        </div>
      </div>
    </div>

    <div class="et" id="e2">
      <div class="bar"><div class="dot">2</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>OCR</h3>
          <span class="desc">Torna os escaneados pesquisáveis. Preserva o original (<code>_OCR.pdf</code>).</span>
          <span class="st" id="s2">—</span>
          <div class="acoes"><button data-a onclick="acao('ocr',{modo:'manter'})">Aplicar OCR</button></div>
        </div>
      </div>
    </div>
  </div>

  <div class="fase">Conversão — o markdown nasce aqui, com as âncoras de página</div>
  <div class="trilho">
    <div class="et" id="e3">
      <div class="bar"><div class="dot">3</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Paginação</h3>
          <span class="desc">PDF → Markdown com âncoras <code>{{p.NN}}</code>. Só nos tipos que exigem página.</span>
          <span class="st" id="s3">—</span>
          <div class="acoes">
            <button data-a class="primary" onclick="acao('paginar',{offset:+offset.value,romanas:+romanas.value})">Converter pasta</button>
          </div>
        </div>
        <div class="extra">
          <div style="display:flex;gap:10px;align-items:end;flex-wrap:wrap">
            <div style="width:120px"><label>offset</label><input type="number" id="offset" value="0"></div>
            <div style="width:120px"><label>romanas até</label><input type="number" id="romanas" value="0"></div>
            <div style="flex:1;min-width:240px">
              <label>ou converta só alguns arquivos</label>
              <div class="fila" id="fila"></div>
              <div style="display:flex;gap:6px">
                <button class="bnav" onclick="abrirNav('fila','file')" style="flex:1">📄 Escolher arquivos…</button>
                <button data-a onclick="converterFila()" id="btnFila" disabled>Converter seleção</button>
              </div>
            </div>
          </div>
          <div class="dica"><b>offset</b>: se a página impressa “1” é a 13ª folha do PDF, use 12. <b>romanas até</b>: nº de páginas do prefácio em algarismo romano.</div>
        </div>
      </div>
    </div>
  </div>

  <div class="fase">Preparo — mecânico, sem IA e sem custo de token</div>
  <div class="trilho">
    <div class="et" id="e4">
      <div class="bar"><div class="dot">4</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Limpar OCR</h3>
          <span class="desc">Hifenização, cabeçalhos repetidos, ruído. Âncoras preservadas.</span>
          <span class="st" id="s4">—</span>
          <div class="acoes">
            <button data-a onclick="acao('corrigir_idioma')" title="Redetecta o idioma no PDF-fonte e corrige o YAML">Corrigir idioma</button>
            <button data-a onclick="acao('limpar',{})">Limpar</button>
          </div>
        </div>
      </div>
    </div>

    <div class="et" id="e5">
      <div class="bar"><div class="dot">5</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Fatiar</h3>
          <span class="desc">Livro grande → nota-índice + fatias. <b>Faça antes de levar ao Claude.</b></span>
          <span class="st" id="s5">—</span>
          <div class="acoes">
            <input type="number" id="palavras" value="1200" style="width:90px" title="palavras por fatia">
            <button data-a onclick="acao('fatiar',{palavras:+palavras.value})">Fatiar</button>
            <button data-a onclick="acao('normalizar')" title="area/tags/autoria no formato do Obsidian">Normalizar</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="fase">Qualidade</div>
  <div class="trilho">
    <div class="et" id="e6">
      <div class="bar"><div class="dot">6</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Validar</h3>
          <span class="desc">Âncoras íntegras · YAML coerente com o tipo de fonte.</span>
          <span class="st" id="s6">—</span>
          <div class="acoes"><button data-a onclick="acao('validar')">Validar</button></div>
        </div>
      </div>
    </div>

    <div class="et" id="e7">
      <div class="bar"><div class="dot">7</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Auditar</h3>
          <span class="desc">O gerado <b>serve</b> ao segundo cérebro? Relatório com pendências.</span>
          <span class="st" id="s7">—</span>
          <div class="acoes">
            <button class="bnav" onclick="abrirNav('audp','dir')">📁</button>
            <button data-a class="primary" onclick="acao('auditar',{pasta:audp.value})">Auditar</button>
          </div>
        </div>
        <div class="extra">
          <input type="text" id="audp" placeholder="(padrão: 2-MARKDOWN-BRUTO)">
          <div class="dica">O que sobrar de pendência aqui — autor, título, editora, ano, resumo — é o trabalho do <b>Projeto Claude</b> (Fase 3c do WORKFLOW).</div>
        </div>
      </div>
    </div>
  </div>

  <div class="fase">Publicação — o segundo cérebro no Obsidian</div>
  <div class="trilho">
    <div class="et" id="e8">
      <div class="bar"><div class="dot">8</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Publicar</h3>
          <span class="desc">Distribui <b>3-MARKDOWN-LIMPO</b> no vault por regra (tipo→pasta). Nota reprovada não entra; em conflito, o vault vence.</span>
          <span class="st" id="s8">—</span>
          <div class="acoes">
            <button class="bnav" onclick="abrirNav('vaultp','dir')">📁</button>
            <button data-a onclick="acao('publicar',{pasta:vaultp.value,dry:true})">Simular</button>
            <button data-a class="primary" onclick="acao('publicar',{pasta:vaultp.value,dry:false})">Publicar</button>
          </div>
        </div>
        <div class="extra">
          <input type="text" id="vaultp" placeholder="(padrão: 4-OBSIDIAN-VAULT)">
          <div class="dica"><b>Simule primeiro.</b> Publicar é COPIAR — o 3-MARKDOWN-LIMPO segue como estágio de trabalho. Se uma nota do vault foi editada à mão (curadoria), ela <b>não</b> é sobrescrita. Relatório: <b>RELATORIO-PUBLICACAO.md</b>.</div>
        </div>
      </div>
    </div>

    <div class="et" id="e9">
      <div class="bar"><div class="dot">9</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Auditar vault</h3>
          <span class="desc">O <b>grafo</b> está íntegro? Fatias órfãs, links quebrados, notas invisíveis nos MOCs.</span>
          <span class="st" id="s9">—</span>
          <div class="acoes">
            <button data-a class="primary" onclick="acao('auditar_vault',{pasta:vaultp.value})">Auditar vault</button>
          </div>
        </div>
        <div class="extra">
          <div class="dica">Metadado fora do vocabulário não gera erro no Obsidian — a nota simplesmente <b>some dos painéis</b>. Esta auditoria torna esse silêncio visível. Relatório: <b>RELATORIO-VAULT.md</b> no vault.</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- 04 LOG -->
<section>
  <div class="head"><span class="n">04</span><h2>Execução</h2><p id="jobName">nenhuma tarefa</p></div>
  <pre id="log">Aguardando…</pre>
</section>

<!-- 05 TRIAGEM -->
<section>
  <div class="head"><span class="n">05</span><h2>Triagem</h2>
    <p>o tipo é um palpite automático — <b>revise</b></p></div>
  <div class="tw"><table>
    <thead><tr><th>Arquivo</th><th>Idioma</th><th>Pgs</th><th>Texto?</th><th>OCR</th>
      <th>Tipo (palpite)</th><th>Âncora?</th><th>Rota</th></tr></thead>
    <tbody id="tb"><tr><td colspan="8" style="color:var(--muted);padding:14px">Rode a triagem para popular.</td></tr></tbody>
  </table></div>
  <div class="stat" id="stat"></div>
</section>

<div class="nota">
<b>Sigilo.</b> Tudo roda na sua máquina (WSL2) — nada vai para a internet.
<b>Desempenho:</b> ler <code>/mnt/c/</code> do WSL2 é mais lento que o disco Linux; em acervos grandes, copie o lote para <code>~/acervo</code>, processe e devolva.
</div>
</div>

<!-- ============ MODAL: navegador (arrastável e redimensionável) ============ -->
<div class="ov" id="ov" onclick="if(event.target===this)fecharNav()">
  <div class="mod" id="mod">
    <div class="mh" id="mh">
      <h3 id="navTit">Selecionar pasta</h3>
      <span class="hint">arraste o título · redimensione pelas bordas</span>
      <button class="x" onclick="fecharNav()">×</button>
    </div>
    <div class="mbody">
      <div class="side" id="navSide"></div>
      <div class="main">
        <div class="bc" id="navBc"></div>
        <div class="selbar" id="navSelBar" style="display:none">
          <span class="c" id="navSelN">0 selecionados</span>
          <div style="flex:1"></div>
          <button onclick="navMarcarTodos(true)">Marcar todos</button>
          <button onclick="navMarcarTodos(false)">Limpar</button>
        </div>
        <div class="lista" id="navLista"></div>
      </div>
    </div>
    <div class="mfoot">
      <code id="navPath">—</code>
      <button onclick="navSubir()">↑ Acima</button>
      <button class="primary" id="navOk" onclick="navSelecionar()">Selecionar</button>
    </div>
    <div class="rz w" data-rz="w"></div>
    <div class="rz e" data-rz="e"></div>
    <div class="rz s" data-rz="s"></div>
    <div class="rz se" data-rz="se"></div>
  </div>
</div>

<script>
let ultimoLog = "";
let navAlvo = "root", navModo = "dir", navAtual = "", navSel = new Set(), FILA = [];

function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
const q = s => JSON.stringify(s).replace(/"/g,'&quot;');

/* ---------- MODAL: arrastar e redimensionar ---------- */
(function(){
  const mod = document.getElementById('mod'), mh = document.getElementById('mh');
  let ar = null, rz = null;

  mh.addEventListener('mousedown', e=>{
    if(e.target.closest('.x')) return;
    const r = mod.getBoundingClientRect();
    ar = {dx: e.clientX - r.left, dy: e.clientY - r.top};
    e.preventDefault();
  });
  mod.querySelectorAll('.rz').forEach(h=>{
    h.addEventListener('mousedown', e=>{
      const r = mod.getBoundingClientRect();
      rz = {dir: h.dataset.rz, x: e.clientX, y: e.clientY,
            w: r.width, h: r.height, l: r.left};
      e.preventDefault(); e.stopPropagation();
    });
  });
  document.addEventListener('mousemove', e=>{
    if(ar){
      // mantém a janela dentro da tela (senão o usuário "perde" o modal)
      const x = Math.min(Math.max(0, e.clientX - ar.dx), innerWidth - 120);
      const y = Math.min(Math.max(0, e.clientY - ar.dy), innerHeight - 60);
      mod.style.left = x + 'px'; mod.style.top = y + 'px';
    } else if(rz){
      const dx = e.clientX - rz.x, dy = e.clientY - rz.y;
      if(rz.dir.includes('e')) mod.style.width  = Math.max(420, rz.w + dx) + 'px';
      if(rz.dir.includes('s')) mod.style.height = Math.max(280, rz.h + dy) + 'px';
      if(rz.dir === 'w'){
        const w = Math.max(420, rz.w - dx);
        mod.style.width = w + 'px';
        mod.style.left  = (rz.l + (rz.w - w)) + 'px';
      }
    }
  });
  document.addEventListener('mouseup', ()=>{
    // guarda tamanho/posição para a próxima abertura
    if(ar || rz){
      try{ MODST = {l:mod.style.left, t:mod.style.top,
                    w:mod.style.width, h:mod.style.height}; }catch(e){}
    }
    ar = rz = null;
  });
  // duplo clique no cabeçalho = maximiza / restaura
  mh.addEventListener('dblclick', ()=>{
    if(mod.dataset.max === '1'){
      Object.assign(mod.style, {left:'calc(50% - 430px)', top:'60px',
        width:'860px', height:'600px'});
      mod.dataset.max = '0';
    } else {
      Object.assign(mod.style, {left:'12px', top:'12px',
        width:(innerWidth-24)+'px', height:(innerHeight-24)+'px'});
      mod.dataset.max = '1';
    }
  });
})();
let MODST = null;

/* ---------- navegador ---------- */
async function abrirNav(alvo, modo){
  navAlvo = alvo; navModo = modo || 'dir';
  navSel = new Set(navAlvo === 'fila' ? FILA.map(f=>f.path) : []);
  navTit.textContent = modo === 'file' ? 'Selecionar arquivos (1 ou mais)' : 'Selecionar pasta';
  navOk.textContent  = modo === 'file' ? 'Adicionar selecionados' : 'Selecionar esta pasta';
  navSelBar.style.display = modo === 'file' ? 'flex' : 'none';
  if(MODST) Object.assign(mod.style, {left:MODST.l, top:MODST.t, width:MODST.w, height:MODST.h});
  ov.classList.add('on');

  const at = await (await fetch('/api/atalhos')).json();
  navSide.innerHTML =
    '<div class="t">Windows</div>' +
    at.filter(a=>a.tipo==='windows').map(a=>
      `<a class="win" title="${esc(a.path)}" onclick="navIr(${q(a.path)})">💾 ${esc(a.nome)}</a>`).join('') +
    '<div class="t">WSL2</div>' +
    at.filter(a=>a.tipo==='wsl').map(a=>
      `<a title="${esc(a.path)}" onclick="navIr(${q(a.path)})">🐧 ${esc(a.nome)}</a>`).join('');
  const inicial = (document.getElementById(alvo)||{}).value ||
                  (at.find(a=>a.tipo==='windows')||{}).path || '';
  navIr(inicial);
}
function fecharNav(){ ov.classList.remove('on'); }

async function navIr(caminho){
  const d = await (await fetch('/api/navegar?path=' + encodeURIComponent(caminho||'') +
                               '&modo=' + navModo)).json();
  navAtual = d.path;
  navPath.textContent = d.path + (d.n_pdfs_aqui ? `   (${d.n_pdfs_aqui} PDFs)` : '');
  navBc.innerHTML = (d.breadcrumb||[]).map((b,i,a)=>
    `<a onclick="navIr(${q(b.path)})">${esc(b.nome)}</a>` + (i<a.length-1?'<span>/</span>':'')).join('');
  let html = '';
  if(d.erro) html += `<div style="padding:14px;color:var(--err);font-size:13px">${esc(d.erro)}</div>`;
  html += (d.pastas||[]).map(f=>
    `<div class="it" title="${esc(f.path)}" onclick="navIr(${q(f.path)})">
       <span class="ic">📁</span><span class="nm">${esc(f.nome)}</span>
       ${f.pdfs?`<span class="ct">${f.pdfs} PDF</span>`:''}</div>`).join('');
  html += (d.arquivos||[]).map(f=>{
    const on = navSel.has(f.path);
    return `<div class="it${on?' sel':''}" data-f="${esc(f.path)}" title="${esc(f.path)}"
                 onclick="navToggle(${q(f.path)})">
       <input type="checkbox" ${on?'checked':''} onclick="event.stopPropagation();navToggle(${q(f.path)})">
       <span class="ic">📄</span><span class="nm">${esc(f.nome)}</span>
       <span class="ct">${(f.tam/1048576).toFixed(1)} MB</span></div>`;
  }).join('');
  navLista.innerHTML = html || '<div style="padding:14px;color:var(--muted);font-size:13px">Pasta vazia.</div>';
  navContar();
}
function navSubir(){ const p = navAtual.split('/').filter(Boolean); p.pop(); navIr('/'+p.join('/')); }
function navToggle(caminho){
  if(navModo !== 'file') return;
  navSel.has(caminho) ? navSel.delete(caminho) : navSel.add(caminho);
  const el = navLista.querySelector(`.it[data-f="${CSS.escape(caminho)}"]`);
  if(el){ el.classList.toggle('sel', navSel.has(caminho));
          const cb = el.querySelector('input'); if(cb) cb.checked = navSel.has(caminho); }
  navContar();
}
function navMarcarTodos(m){
  navLista.querySelectorAll('.it[data-f]').forEach(el=>{
    const p = el.getAttribute('data-f');
    m ? navSel.add(p) : navSel.delete(p);
    el.classList.toggle('sel', m);
    const cb = el.querySelector('input'); if(cb) cb.checked = m;
  });
  navContar();
}
function navContar(){
  if(navModo !== 'file') return;
  navSelN.textContent = navSel.size + (navSel.size===1?' selecionado':' selecionados');
}
function navSelecionar(){
  if(navModo === 'file'){
    navSel.forEach(p=>{ if(!FILA.some(f=>f.path===p)) FILA.push({path:p, nome:p.split('/').pop()}); });
    renderFila();
  } else {
    document.getElementById(navAlvo).value = navAtual;
    if(navAlvo !== 'audp'){
      const c = {}; c[navAlvo] = navAtual; salvar(c);   // só o campo escolhido
    }
  }
  fecharNav();
}

/* ---------- fila ---------- */
function renderFila(){
  const el = document.getElementById('fila');
  el.innerHTML = FILA.map((f,i)=>
    `<div class="fi"><span class="ic">📄</span>
       <span class="n" title="${esc(f.path)}">${esc(f.nome)}</span>
       <button class="rm" onclick="tirarFila(${i})">×</button></div>`).join('');
  btnFila.disabled = !FILA.length;
  btnFila.textContent = FILA.length ? `Converter ${FILA.length}` : 'Converter seleção';
}
function tirarFila(i){ FILA.splice(i,1); renderFila(); }
function converterFila(){
  if(!FILA.length){ alert('Escolha ao menos um arquivo.'); return; }
  acao('arquivo',{arquivos:FILA.map(f=>f.path), offset:+offset.value, romanas:+romanas.value});
}

/* ---------- comandos copiáveis ---------- */
function ehComando(s){return /^(sudo|apt|python3|pip|source|bash|dos2unix|export)\b/.test(s.trim());}
function juntarApt(cmds){
  const pac = [], out = [];
  cmds.forEach(c=>{
    const m = c.match(/^sudo apt install -y (.+)$/);
    if(m){ m[1].split(/\s+/).forEach(p=>{ if(p && !pac.includes(p)) pac.push(p); }); }
    else if(!out.includes(c)) out.push(c);
  });
  const partes = [];
  if(pac.length) partes.push('sudo apt install -y ' + pac.join(' '));
  return partes.concat(out).join(' && ');
}
function copiar(btn, txt){
  const feito = ()=>{ const o=btn.textContent; btn.textContent='Copiado ✓'; btn.classList.add('ok');
    setTimeout(()=>{btn.textContent=o; btn.classList.remove('ok');},1500); };
  if(navigator.clipboard && window.isSecureContext)
    navigator.clipboard.writeText(txt).then(feito, ()=>fb(txt,feito));
  else fb(txt,feito);
}
function fb(txt, cb){
  const ta=document.createElement('textarea'); ta.value=txt;
  ta.style.position='fixed'; ta.style.opacity='0';
  document.body.appendChild(ta); ta.select();
  try{document.execCommand('copy');}catch(e){alert('Copie manualmente:\n\n'+txt);}
  document.body.removeChild(ta); cb&&cb();
}

/* ---------- ações ---------- */
async function salvar(campos){
  // Envia só os campos preenchidos. Antes mandava os três juntos: se o venv
  // estivesse errado, o POST falhava e a PASTA DO ACERVO nunca era salva.
  const corpo = campos || {};
  if(!campos){
    if(root.value)    corpo.root    = root.value;
    if(scripts.value) corpo.scripts = scripts.value;
    if(venv.value)    corpo.venv    = venv.value;
    if(lang.value)    corpo.lang    = lang.value;
  }
  const r = await fetch('/api/config',{method:'POST',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify(corpo)});
  const j = await r.json();
  if(j.avisos && j.avisos.length) alert(j.avisos.join('\n\n'));
  if(j.cfg && j.cfg.venv) venv.value = j.cfg.venv;   // reflete o valor que ficou
  estado();
}
function venvPadrao(){ venv.value = '~/venvs/acervo'; salvar({venv:'~/venvs/acervo'}); }
/* Trava de reexecução: refazer uma etapa CONCLUÍDA reprocessa e pode
   sobrescrever — só com confirmação consciente. (Simular/dry não pede.) */
const ETAPA_DA_ACAO = {triagem:'e1', ocr:'e2', paginar:'e3', limpar:'e4',
                       fatiar:'e5', validar:'e6', auditar:'e7',
                       publicar:'e8', auditar_vault:'e9'};
async function acao(a,extra){
  const et = document.getElementById(ETAPA_DA_ACAO[a]||'');
  const ehDry = extra && extra.dry === true;
  if(et && et.className.includes('feito') && !ehDry){
    const st = document.getElementById('s'+ETAPA_DA_ACAO[a].slice(1));
    if(!confirm('Esta etapa já foi concluída ('+(st?st.textContent:'')+').\n'+
                'Reexecutar vai reprocessar e pode sobrescrever o resultado.\n\n'+
                'Continuar mesmo assim?')) return;
  }
  const r = await fetch('/api/acao',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(Object.assign({acao:a},extra||{}))});
  const j = await r.json();
  if(!j.ok) alert(j.msg);
  estado();
}

/* ---------- trilho: estado de cada etapa ---------- */
function marcar(id, estadoEt, texto, classe){
  const et = document.getElementById(id);
  et.className = 'et ' + estadoEt;
  const st = document.getElementById('s' + id.slice(1));
  st.textContent = texto;
  st.className = 'st ' + (classe||'');
}
function atualizarTrilho(p, temRoot){
  if(!temRoot){
    for(let i=1;i<=9;i++) marcar('e'+i,'bloq','defina a pasta','');
    return;
  }
  const dt = (k) => (p.datas && p.datas[k]) ? ' · '+p.datas[k] : '';
  // 1 triagem
  p.csv ? marcar('e1','feito', p.csv+' arquivos'+dt('csv'), 'ok')
        : marcar('e1','ativa','pendente','pend');
  // 2 OCR
  if(!p.csv)            marcar('e2','bloq','faça a triagem','');
  else if(p.ocr_pend)   marcar('e2','ativa', p.ocr_pend+' a OCRizar','pend');
  else                  marcar('e2','feito','nada pendente','ok');
  // 3 paginação
  if(!p.csv)            marcar('e3','bloq','faça a triagem','');
  else if(p.bruto)      marcar('e3','feito', p.bruto+' markdown','ok');
  else                  marcar('e3','ativa','pendente','pend');
  // 4 limpar
  if(!p.bruto)          marcar('e4','bloq','converta antes','');
  else if(p.limpo)      marcar('e4','feito', p.limpo+' limpos','ok');
  else                  marcar('e4','ativa','recomendado','pend');
  // 5 fatiar
  if(!p.bruto)          marcar('e5','bloq','converta antes','');
  else if(p.fatias)     marcar('e5','feito', p.fatias+' fatias','ok');
  else                  marcar('e5','ativa','livros grandes','pend');
  // 6 validar
  if(!p.bruto)          marcar('e6','bloq','converta antes','');
  else                  marcar('e6','ativa','pronto','');
  // 7 auditar
  if(!p.bruto)          marcar('e7','bloq','converta antes','');
  else if(p.auditado)   marcar('e7','feito','relatório gerado'+dt('auditado'),'ok');
  else                  marcar('e7','ativa','pronto','pend');
  // 8 publicar (Fase 5 determinística)
  if(!p.limpo_md)       marcar('e8','bloq','prepare 3-MARKDOWN-LIMPO','');
  else if(p.publicado)  marcar('e8','feito', p.vault+' notas'+dt('publicado'),'ok');
  else                  marcar('e8','ativa', p.limpo_md+' prontos p/ publicar','pend');
  // 9 auditar vault (grafo)
  if(!p.vault)              marcar('e9','bloq','publique o vault antes','');
  else if(p.vault_auditado) marcar('e9','feito','grafo auditado'+dt('vault_auditado'),'ok');
  else                      marcar('e9','ativa', p.vault+' notas no vault','pend');
}

/* ---------- estado ---------- */
async function estado(){
  const s = await (await fetch('/api/estado')).json();
  if(document.activeElement.id !== 'root' && s.cfg.root && !root.value) root.value = s.cfg.root;
  if(!scripts.value) scripts.value = s.cfg.scripts || '';
  if(!venv.value) venv.value = s.cfg.venv || '';
  if(s.cfg.lang && lang.value !== s.cfg.lang) lang.value = s.cfg.lang;
  rootWsl.textContent = s.cfg.root || '';
  rootWsl.title = s.cfg.root || '';
  bPdf.textContent = s.n_pdfs + ' PDFs';

  const j = s.job;
  bJob.textContent = j.running ? '⏳ ' + j.name : (j.rc===null?'ocioso':'concluído');
  bJob.className = 'badge ' + (j.running ? 'run' : (j.rc===null?'':'on'));
  jobName.textContent = j.name || 'nenhuma tarefa';
  document.querySelectorAll('[data-a]').forEach(b=>b.disabled = j.running);
  if(!j.running) btnFila.disabled = !FILA.length;
  if(j.log && j.log !== ultimoLog){
    ultimoLog = j.log; log.textContent = j.log; log.scrollTop = log.scrollHeight;
  }

  atualizarTrilho(s.prog || {}, !!s.cfg.root);

  diag.innerHTML = s.diag.map(d=>{
    const bloco = (!d.ok && d.dica && ehComando(d.dica))
      ? `<div class="cmd"><code>${esc(d.dica)}</code>
           <button class="cp" onclick="copiar(this,${q(d.dica)})">Copiar</button></div>`
      : (d.dica ? `<span class="dicatxt">${esc(d.dica)}</span>` : '');
    return `<div class="d ${d.ok?'ok':'no'}"><span class="i">${d.ok?'✓':'✗'}</span>
      <div style="flex:1;min-width:0"><b>${esc(d.nome)}</b>${bloco}</div></div>`;
  }).join('');

  const cmds = s.diag.filter(d=>!d.ok && d.dica && ehComando(d.dica)).map(d=>d.dica);
  if(cmds.length){
    const tudo = juntarApt(cmds);
    pend.innerHTML = `<div class="pend"><h4>⚠ ${cmds.length} dependência(s) pendente(s)</h4>
      <div class="cmd"><code>${esc(tudo)}</code>
        <button class="cp" onclick="copiar(this,${q(tudo)})">Copiar tudo</button></div></div>`;
  } else {
    pend.innerHTML = `<div class="tudo-ok"><b>✓</b> Ambiente pronto — todas as dependências instaladas.</div>`;
  }

  if(s.csv.length){
    tb.innerHTML = s.csv.map(r=>{
      const anc = (r.exige_ancora_pagina||'').toUpperCase()==='SIM';
      const ocr = (r.precisou_ocr||'')==='sim';
      return `<tr>
        <td title="${esc(r.caminho||'')}">${esc(r.arquivo||'')}</td>
        <td><span class="pill">${esc(r.idioma||'?')}</span></td>
        <td>${esc(r.paginas||'')}</td>
        <td><span class="pill ${r.tem_camada_texto==='sim'?'ok':'no'}">${esc(r.tem_camada_texto||'')}</span></td>
        <td><span class="pill ${ocr?'sim':'ok'}">${esc(r.ocr_status||'')}</span></td>
        <td>${esc(r.tipo_fonte_provavel||'')}</td>
        <td><span class="pill ${anc?'sim':'no'}">${anc?'SIM':'não'}</span></td>
        <td>${esc(r.rota||'')}</td></tr>`;
    }).join('');
    const nOcr = s.csv.filter(r=>r.precisou_ocr==='sim').length;
    const nAnc = s.csv.filter(r=>(r.exige_ancora_pagina||'').toUpperCase()==='SIM').length;
    stat.innerHTML = `<span><b>${s.csv.length}</b> arquivos</span>
      <span><b>${nOcr}</b> precisam de OCR</span>
      <span><b>${nAnc}</b> exigem âncora de página</span>`;
  }
}
renderFila();
estado(); setInterval(estado, 1500);
</script>
"""


def main():
    ap = argparse.ArgumentParser(description="Painel do Acervo (WSL2)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--root", default="", help="pasta do acervo (Windows ou WSL)")
    ap.add_argument("--scripts", default=str(Path(__file__).resolve().parent),
                    help="pasta com aplicar_ocr.sh e os .py")
    ap.add_argument("--venv", default=str(Path.home() / "venvs/acervo"))
    a = ap.parse_args()

    CFG["root"] = win_para_wsl(a.root) if a.root else ""
    CFG["scripts"] = win_para_wsl(a.scripts)
    CFG["venv"] = win_para_wsl(a.venv)

    srv = ThreadingHTTPServer(("0.0.0.0", a.port), Handler)
    print("=" * 62)
    print("  Acervo — pipeline do segundo cérebro (WSL2)")
    print("=" * 62)
    print(f"  Abra no navegador do WINDOWS:  http://localhost:{a.port}")
    print(f"  Scripts : {CFG['scripts']}")
    print(f"  venv    : {CFG['venv']}")
    if CFG["root"]:
        print(f"  Acervo  : {CFG['root']}")
    print("\n  Ctrl+C para encerrar.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")


if __name__ == "__main__":
    main()

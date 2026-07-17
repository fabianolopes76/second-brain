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
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import comum
import frontmatter
import taxonomia
import triagem
from auditar_acervo import (CODS_FICHA as _CODS_FICHA,
                            auditar as _auditar_arquivo,
                            nota as _nota_auditoria,
                            nota_ficha as _nota_ficha)

# ---------------------------------------------------------------------------
# Estado global de execução (um job por vez — simples e previsível)
# ---------------------------------------------------------------------------
class Job:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.name = ""
        self.action = ""      # qual etapa disparou (ocr/paginar/...) — ancora o progresso no card
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
                "action": self.action,
                "rc": self.rc,
                "log": "".join(self.log),
            }


JOB = Job()
CFG = {"root": "", "scripts": "", "venv": str(Path.home() / "venvs/acervo"),
       "lang": "auto", "lang_fallback": "por+eng"}


# ---------------------------------------------------------------------------
# Configuração persistente — reabrir o painel RETOMA de onde parou.
# Precedência: args da CLI > config.json > defaults embutidos.
# ---------------------------------------------------------------------------
def _config_path() -> Path:
    return Path.home() / ".config" / "acervo" / "config.json"


def carregar_config() -> dict:
    """Lê o config salvo; nunca levanta, filtra chaves/tipos conhecidos."""
    try:
        dados = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    cfg = {k: v for k, v in dados.items()
           if k in CFG and isinstance(v, str)}
    # a trava do /api/config não pode ser burlada por um config editado à mão
    if str(cfg.get("venv", "")).startswith("/mnt/"):
        cfg.pop("venv")
    return cfg


def salvar_config() -> None:
    """Grava o CFG atual; falha de escrita nunca derruba o handler."""
    try:
        p = _config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(CFG, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    except OSError:
        pass


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


_JBIG2_TEM_APT = None


def _dica_jbig2():
    """Comando de instalação do jbig2enc que FUNCIONA nesta distro.

    'sudo apt install jbig2enc' só existe no Ubuntu 23.04+/Debian 12+;
    no 22.04 dava "Unable to locate package". A disponibilidade é checada
    uma única vez (o diagnóstico roda a cada poll de 1,5 s)."""
    global _JBIG2_TEM_APT
    if _JBIG2_TEM_APT is None:
        r = subprocess.run(
            ["bash", "-c",
             "apt-cache policy jbig2enc 2>/dev/null | grep -q 'Candidate: [0-9]'"],
            capture_output=True)
        _JBIG2_TEM_APT = (r.returncode == 0)
    if _JBIG2_TEM_APT:
        return "sudo apt install -y jbig2enc"
    return f"bash {shlex.quote(str(Path(CFG['scripts']) / 'instalar-jbig2enc.sh'))}"


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
    # opcional, mas o padrao OPTIMIZE=3 o recomenda: sem ele o PDF sai maior.
    # Ubuntu <= 22.04 NAO tem o pacote apt — a dica vira o instalador do
    # projeto (tenta apt; sem pacote, compila de github.com/agl/jbig2enc).
    check("jbig2enc (compressão do PDF)", "jbig2", _dica_jbig2())

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
              "triagem.py", "auditar_vault.py", "publicar.py", "radar.py",
              "comum.py"]:
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
         "fatias": 0, "auditado": False, "vault": 0, "vault_auditado": False,
         "radar": 0, "radar_novos": 0}
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
    r["fichas"] = resumo_fichas()   # cacheado: só reaudita quando um md muda
    r["pub"] = resumo_publicacao()  # idem: prontidão real da publicação

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
        r["vault"] = sum(1 for f in vault.rglob("*.md")
                         if not f.name.startswith(("RELATORIO", "_"))
                         and not any(p in comum.IGNORAR_PASTAS for p in f.parts))
        r["publicado"] = (vault / "RELATORIO-PUBLICACAO.md").exists()
        r["vault_auditado"] = (vault / "RELATORIO-VAULT.md").exists()
        radar_dir = vault / "00-Indices-MOCs" / "Radar"
        if radar_dir.is_dir():
            achados = [f for f in radar_dir.rglob("*.md")
                       if not f.name.startswith(("RELATORIO", "_", "."))]
            r["radar"] = len(achados)
            try:
                estado_radar = json.loads(
                    (radar_dir / ".radar_estado.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                estado_radar = {}
            r["radar_novos"] = sum(
                1 for f in achados
                if estado_radar.get(str(f.relative_to(radar_dir))) is None)

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
        if (vault / "RELATORIO-RADAR.md").exists():
            r["datas"]["radar"] = _mt(vault / "RELATORIO-RADAR.md")
    return r


def contar_pdfs():
    if not CFG["root"] or not Path(CFG["root"]).is_dir():
        return 0
    n = 0
    for p in Path(CFG["root"]).rglob("*"):
        if p.suffix.lower() != ".pdf":
            continue
        if p.stem.endswith("_OCR"):
            # copia _OCR só é "saída" se o original ainda existe ao lado;
            # órfã (original apagado) conta como fonte, igual à triagem
            if p.with_name(p.stem[:-4] + p.suffix).exists():
                continue
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


def acao_paginar(offset=0, romanas=0, reconverter=False):
    """Converte a pasta: TODOS os PDFs pesquisáveis do CSV → markdown com âncoras.

    Antes só convertia quem exige âncora de página — legislação/jurisprudência
    (que não exigem) ficavam de fora e o botão parecia quebrado. A âncora extra
    não reprova ninguém; escaneado ainda sem OCR não é convertível e é listado
    no log com a instrução de voltar à etapa 2.

    RETOMADA SEM PERDA: markdown de destino que JÁ EXISTE é pulado por padrão
    — reconverter sobrescreveria a ficha corrigida à mão no 2-MARKDOWN-BRUTO.
    `reconverter=True` (checkbox no card) refaz conscientemente.
    """
    linhas = ler_csv()
    if not linhas:
        return False, "Rode a triagem antes (etapa 1) — ela gera o controle.csv."

    vpy = Path(CFG["venv"]) / "bin" / "python"
    script = Path(CFG["scripts"]) / "injetar_paginas.py"
    saida = Path(CFG["root"]) / "2-MARKDOWN-BRUTO"
    saida.mkdir(exist_ok=True)

    cmds, nomes, sem_ocr, ja_convertidos = [], [], [], []
    for l in linhas:
        # prefere o _OCR quando existe; senão, o original
        src = l.get("arquivo_ocr") or l.get("caminho")
        if not src or not Path(src).exists():
            src = l.get("caminho")
        if not src or not Path(src).exists():
            continue
        # pesquisável = já tinha texto, ou o OCR produziu a cópia _OCR
        pesquisavel = (l.get("tem_camada_texto") == "sim"
                       or Path(src).stem.endswith("_OCR"))
        if not pesquisavel:
            sem_ocr.append(Path(src).name)
            continue
        dst = saida / (Path(src).stem.replace("_OCR", "") + ".md")
        if dst.exists() and not reconverter:
            ja_convertidos.append(dst.name)
            continue
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
        nomes.append(Path(src).name)

    if not cmds:
        if ja_convertidos:
            return False, (f"{len(ja_convertidos)} arquivo(s) já convertidos — "
                           "nada a fazer. As fichas do 2-MARKDOWN-BRUTO foram "
                           "preservadas; marque \"reconverter existentes\" para refazer.")
        if sem_ocr:
            return False, (f"Nenhum PDF pesquisável ainda — {len(sem_ocr)} "
                           "arquivo(s) precisam de OCR (etapa 2) antes de converter.")
        return False, "Nenhum arquivo encontrado no disco."

    partes = [f'echo "=== {len(cmds)} PDF(s) pesquisáveis -> 2-MARKDOWN-BRUTO ==="']
    partes += [f'echo {shlex.quote("    " + n)}' for n in nomes]
    partes += [f'echo {shlex.quote("    PULADO (já convertido — ficha preservada): " + n)}'
               for n in ja_convertidos]
    partes += [f'echo {shlex.quote("    PULADO (precisa de OCR — etapa 2): " + n)}'
               for n in sem_ocr]
    partes += ['echo ' + shlex.quote(f">> [{i+1}/{len(cmds)}] {nomes[i]}") + f' ; {c}'
               for i, c in enumerate(cmds)]
    return JOB.start(f"Converter pasta ({len(cmds)} arquivo(s))", " ; ".join(partes))


def _detectar_idioma_de(src: Path) -> str:
    det = Path(CFG["scripts"]) / "detectar_idioma.py"
    if not det.exists():
        return ""
    try:
        r = subprocess.run(["python3", str(det), str(src), "--codigo"],
                           capture_output=True, text=True, timeout=90)
        return r.stdout.strip().splitlines()[0].strip() if r.stdout.strip() else ""
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
        if dst.exists():
            # seleção explícita sobrescreve, mas avisa (ficha anterior se vai)
            cab += " ; echo " + shlex.quote(
                f"   AVISO: sobrescrevendo {dst.name} existente — a ficha "
                "anterior será substituída")

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
    """Deixa area/tags/autoria no formato que o Obsidian e o Dataview exigem.

    Cobre o 2-MARKDOWN-BRUTO e TAMBÉM o 3-MARKDOWN-LIMPO (é dele que o
    Publicar consome — normalizar só o bruto deixava as fatias já geradas
    sem o `tipo` derivado)."""
    base = Path(CFG["root"])
    s = Path(CFG["scripts"]) / "normalizar_yaml.py"
    alvos = [base / "2-MARKDOWN-BRUTO", base / "3-MARKDOWN-LIMPO"]
    alvos = [a for a in alvos if a.is_dir()]
    if not alvos:
        return False, "Converta antes (não há 2-MARKDOWN-BRUTO nem 3-MARKDOWN-LIMPO)."
    cmd = " ; ".join(
        f'echo "=== {a.name} ===" ; python3 {shlex.quote(str(s))} {shlex.quote(str(a))}'
        for a in alvos)
    return JOB.start("Normalizar YAML (Obsidian)", cmd)


def acao_qualidade(pasta=""):
    """Etapa 6 unificada (v3.16): integridade técnica das âncoras + auditoria
    com nota, num job só — o relatório-triagem abre ao terminar. (O antigo
    "Validar" foi absorvido: as checagens exclusivas dele viraram avisos do
    próprio auditor.)"""
    alvo = Path(pasta) if pasta else (Path(CFG["root"]) / "2-MARKDOWN-BRUTO")
    if not alvo.is_dir():
        return False, "Pasta não encontrada. Converta antes (etapa 3)."
    vpy = Path(CFG["venv"]) / "bin" / "python"
    va = Path(CFG["scripts"]) / "verificar_ancoras.py"
    aud = Path(CFG["scripts"]) / "auditar_acervo.py"
    cmd = (f'echo "=== ANCORAS — integridade tecnica ===" ; '
           f'{shlex.quote(str(vpy))} {shlex.quote(str(va))} {shlex.quote(str(alvo))} ; '
           f'echo "" ; echo "=== AUDITORIA — nota por arquivo ===" ; '
           f'python3 {shlex.quote(str(aud))} {shlex.quote(str(alvo))} --detalhado')
    return JOB.start(f"Qualidade — {alvo.name}", cmd)


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


def acao_radar(pasta="", aplicar=False):
    """FASE 6: correlaciona os achados de Radar/ às notas do vault por
    identificador (lei/tema/súmula/processo) e monta a fila de revisão.
    Com aplicar=True, sinaliza as afetadas com status: A-conferir."""
    alvo = Path(pasta) if pasta else (Path(CFG["root"]) / "4-OBSIDIAN-VAULT")
    if not alvo.is_dir():
        return False, f"Pasta do vault não encontrada: {alvo}."
    rd = Path(CFG["scripts"]) / "radar.py"
    if not rd.exists():
        return False, "radar.py não encontrado na pasta de scripts."
    cmd = (f'python3 {shlex.quote(str(rd))} {shlex.quote(str(alvo))}'
           + (" --aplicar" if aplicar else ""))
    nome = "Radar (sinalizar A-conferir)" if aplicar else "Radar (fila de revisão)"
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
# Fichas — correção MANUAL do YAML pelo painel (quando a automação não
# resolve: tipo_fonte que a triagem não inferiu, autoria/ementa/ano vazios).
# O mestre é o 2-MARKDOWN-BRUTO: fatias herdam a ficha ao refatiar (etapa 5).
# ---------------------------------------------------------------------------
_CAMPOS_LISTA = ("area", "autoria", "tags")   # no formulário: separar com ";"


def _vocab():
    """Vocabulário para o formulário — tudo da fonte única (taxonomia)."""
    return {
        "tipos_fonte": sorted(taxonomia.TIPOS_FONTE),
        "obrigatorios": {tf: list(taxonomia.campos_obrigatorios(tf))
                         for tf in taxonomia.TIPOS_FONTE},
        # a régua que de fato REPROVA (obrigatórios − dívida tolerada):
        # é por ela que o formulário marca o asterisco e o destaque
        "bloqueantes": {tf: list(taxonomia.campos_bloqueantes(tf))
                        for tf in taxonomia.TIPOS_FONTE},
        "tipo_unico": {tf: taxonomia.tipo_unico_de(tf)
                       for tf in taxonomia.TIPOS_FONTE},
        "tipos": list(taxonomia.TIPOS),
        "areas": sorted(set(taxonomia.AREAS.values())),
        "status": list(taxonomia.STATUS),
        "confiabilidade": list(taxonomia.CONFIABILIDADE),
        "listas": list(_CAMPOS_LISTA),
    }


def _ficha_path(nome: str):
    """Caminho seguro dentro de 2-MARKDOWN-BRUTO (sem traversal)."""
    base = (Path(CFG["root"]) / "2-MARKDOWN-BRUTO").resolve()
    p = (base / Path(nome).name).resolve()
    if p.parent != base or not p.name.endswith(".md"):
        return None
    return p


def _ja_fatiado(stem: str) -> bool:
    """As fatias desta obra já existem no 3-MARKDOWN-LIMPO?"""
    if not CFG["root"]:
        return False
    limpo = Path(CFG["root"]) / "3-MARKDOWN-LIMPO"
    pref = comum.prefixo_fatia(stem)
    return ((limpo / f"{pref}_INDICE.md").exists()
            or (limpo / f"{pref}_p01.md").exists())


# Erro ESTRUTURAL não se conserta no formulário — a orientação diz ONDE.
# (etapa, texto quando pendente) por código do auditor.
ORIENTACAO = {
    "gigante": "resolve-se na etapa 5 — Fatiar (o mestre não cabe na IA inteiro)",
    "sem_ancoras": "resolve-se na etapa 3 — reconverter o PDF-fonte "
                   "(injetar_paginas recria as âncoras)",
    "sem_frontmatter": "resolve-se na etapa 3 — reconverter (o arquivo "
                       "não tem YAML nenhum)",
}


def _classificar_ficha(f: Path) -> dict:
    """FONTE ÚNICA da situação de uma ficha — usada pela lista, pelo salvar
    e pelos contadores do trilho. Separa o que se corrige NA ficha do que
    se resolve em outra etapa (com orientação, e 'resolvida' quando o disco
    prova que já foi — ex.: gigante com as fatias já geradas)."""
    texto = f.read_text(encoding="utf-8", errors="replace")
    fm = frontmatter.ler(texto).campos
    r = _auditar_arquivo(f)

    tf = str(fm.get("tipo_fonte") or "")
    faltam = []
    if tf in taxonomia.TIPOS_FONTE:
        faltam = [c for c in taxonomia.campos_bloqueantes(tf)
                  if comum.vazio(fm.get(c))]

    erros_ficha, pendencias = [], []
    estruturais_pendentes = False
    for msg, cod in zip(r.get("erros", []), r.get("erros_cod", [])):
        if cod in _CODS_FICHA:
            erros_ficha.append(msg)
            continue
        resolvida = (cod == "gigante" and _ja_fatiado(f.stem))
        pendencias.append({
            "msg": msg,
            "orientacao": ("resolvido: as fatias já existem em 3-MARKDOWN-LIMPO "
                           "— o mestre fica inteiro por design"
                           if resolvida else ORIENTACAO.get(cod, "")),
            "resolvida": resolvida,
        })
        estruturais_pendentes = estruturais_pendentes or not resolvida

    nota = _nota_ficha(r, estruturais_pendentes)

    # o que a AUTOMAÇÃO atribuiu e pede confirmação humana
    revisar = []
    if "# palpite da triagem" in texto:
        revisar.append("tipo_fonte é palpite da triagem")
    if "# derivado do tipo_fonte" in texto:
        revisar.append("tipo derivado automaticamente")
    if str(fm.get("status") or "") == "A-conferir":
        revisar.append("status A-conferir")
    if str(fm.get("confiabilidade") or "") == "A-conferir":
        revisar.append("confiabilidade A-conferir")

    # Avisos genéricos NÃO seguram a ficha em "conferir": "hifenização
    # quebrada" é do TEXTO, não da ficha — prendê-la por isso deixaria
    # obras OCRizadas eternamente fora de "Prontas". O que exige o humano
    # aqui é: erro de ficha, marca de revisão ou pendência não resolvida.
    if nota == "REPROVADO":
        grupo = "corrigir"
    elif revisar or estruturais_pendentes:
        grupo = "conferir"
    else:
        grupo = "pronta"

    aut = fm.get("autoria")
    return {
        "arquivo": f.name,
        "tipo_fonte": tf,
        "tipo": str(fm.get("tipo") or ""),
        "ano": str(fm.get("ano") or ""),
        "autoria": "; ".join(aut) if isinstance(aut, list) else str(aut or ""),
        "nota": nota,
        "faltam_campos": faltam,
        "erros_ficha": erros_ficha,
        "pendencias_outras_etapas": pendencias,
        "avisos": r.get("avisos", [])[:3],
        "n_avisos": len(r.get("avisos", [])),
        "revisar": revisar,
        "grupo": grupo,
    }


def listar_fichas():
    """Cada .md do bruto, já classificado (situação/grupo/orientações)."""
    if not CFG["root"]:
        return []
    base = Path(CFG["root"]) / "2-MARKDOWN-BRUTO"
    if not base.is_dir():
        return []
    out = []
    for f in sorted(base.glob("*.md")):
        if f.name.startswith(("RELATORIO", "_")):
            continue
        try:
            out.append(_classificar_ficha(f))
        except Exception:
            continue
    return out


def relatorio_auditoria(pasta: str = "") -> dict:
    """Auditoria em forma de TRIAGEM para o slideover: do mais grave ao
    irrelevante, cada item com a ação que o usuário deve tomar. Arquivos-
    mestre saem classificados (fonte única: _classificar_ficha); fatias
    são AGREGADAS por obra — 640 linhas iguais ninguém lê."""
    alvo = Path(pasta) if pasta else Path(CFG["root"]) / "2-MARKDOWN-BRUTO"
    if not CFG["root"] or not alvo.is_dir():
        return {"pasta": str(alvo), "itens": [], "fatias": [], "eh_bruto": False}
    eh_bruto = (alvo.resolve()
                == (Path(CFG["root"]) / "2-MARKDOWN-BRUTO").resolve())
    itens, fatias = [], {}
    for f in sorted(alvo.rglob("*.md")):
        if f.name.startswith(("RELATORIO", "_")):
            continue
        try:
            fm = frontmatter.ler(
                f.read_text(encoding="utf-8", errors="replace")).campos
            if not comum.vazio(fm.get("parte")) and not comum.vazio(fm.get("obra")):
                # fatia: agrega por obra (nota da auditoria, não da ficha —
                # fatia herda os metadados, o que pesa é âncora/estrutura)
                r = _auditar_arquivo(f)
                obra = comum.alvo_wikilink(fm.get("obra")) or f.stem.split("_p")[0]
                g = fatias.setdefault(obra, {"obra": obra, "total": 0,
                                             "reprovadas": 0, "parciais": 0,
                                             "exemplo": ""})
                g["total"] += 1
                nt = _nota_auditoria(r)
                if nt == "REPROVADO":
                    g["reprovadas"] += 1
                    g["exemplo"] = g["exemplo"] or (r.get("erros") or [""])[0]
                elif nt == "PARCIAL":
                    g["parciais"] += 1
            else:
                itens.append(_classificar_ficha(f))
        except Exception:
            continue
    return {"pasta": str(alvo), "eh_bruto": eh_bruto, "itens": itens,
            "fatias": sorted(fatias.values(),
                             key=lambda g: -g["reprovadas"])}


# Resumo das fichas para o card ✎ do trilho. O poll de /api/estado roda a
# cada 1,5 s — auditar todos os md a cada poll seria caro (OneDrive/mnt).
# Cache: chave barata (glob+stat, custo que o progresso() já paga); a
# auditoria só recomputa quando algum md do bruto muda.
_FICHAS_CACHE = {"chave": None, "resumo": None}
_FICHAS_LOCK = threading.Lock()


def resumo_fichas():
    """{'total','corrigir','conferir','prontas'} — barato no poll."""
    if not CFG["root"]:
        return {"total": 0, "corrigir": 0, "conferir": 0, "prontas": 0}
    base = Path(CFG["root"]) / "2-MARKDOWN-BRUTO"
    if not base.is_dir():
        return {"total": 0, "corrigir": 0, "conferir": 0, "prontas": 0}
    try:
        chave = tuple(sorted(
            (f.name, f.stat().st_mtime_ns, f.stat().st_size)
            for f in base.glob("*.md")
            if not f.name.startswith(("RELATORIO", "_"))))
    except OSError:
        chave = None
    with _FICHAS_LOCK:
        if chave is not None and chave == _FICHAS_CACHE["chave"]:
            return _FICHAS_CACHE["resumo"]
    fichas = listar_fichas()
    resumo = {
        "total": len(fichas),
        "corrigir": sum(1 for f in fichas if f["grupo"] == "corrigir"),
        "conferir": sum(1 for f in fichas if f["grupo"] == "conferir"),
        "prontas": sum(1 for f in fichas if f["grupo"] == "pronta"),
    }
    with _FICHAS_LOCK:
        _FICHAS_CACHE["chave"] = chave
        _FICHAS_CACHE["resumo"] = resumo
    return resumo


# ---------------------------------------------------------------------------
# Preenchimento assistido por IA (etapa Qualidade): gera um prompt com as
# fichas PENDENTES (+ trecho do documento) para o usuário colar em qualquer
# IA; a resposta volta em JSON e é aplicada com VALIDAÇÃO (vocabulários,
# arquivos, campos) e REVERSÍVEL (backup .antes-ia, um nível de undo).
# ---------------------------------------------------------------------------
_CAMPOS_IA = ("autoria", "titulo", "subtitulo", "local_publicacao", "editora",
              "ano", "edicao", "ementa", "norma_numero", "norma_data",
              "tipo_fonte", "tipo", "area", "status", "resumo")


def gerar_prompt_ia():
    """Prompt autossuficiente: instrução + vocabulários + formato de saída
    rígido + cada ficha pendente com os campos atuais, os FALTANTES e um
    trecho do início do documento (é dele que a IA tira autor/título/ano)."""
    pendentes = [f for f in listar_fichas()
                 if f["grupo"] == "corrigir" or f["faltam_campos"]]
    if not pendentes:
        return {"pendentes": 0, "prompt": ""}
    base = Path(CFG["root"]) / "2-MARKDOWN-BRUTO"
    blocos = []
    for i, f in enumerate(pendentes, 1):
        p = base / f["arquivo"]
        try:
            fm = frontmatter.ler(
                p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        atuais = {k: fm.campos.get(k) for k in _CAMPOS_IA
                  if not comum.vazio(fm.campos.get(k))}
        faltam = f["faltam_campos"] or ["(defina primeiro o tipo_fonte)"]
        trecho = " ".join(fm.corpo.split())[:2200]
        blocos.append(
            f"=== DOCUMENTO {i}/{len(pendentes)}: {f['arquivo']} ===\n"
            f"Campos já preenchidos: "
            f"{json.dumps(atuais, ensure_ascii=False) or '{}'}\n"
            f"Campos FALTANTES: {', '.join(faltam)}\n"
            f"Trecho do início do documento:\n\"\"\"\n{trecho}\n\"\"\"")
    v = _vocab()
    prompt = (
        "Você é um bibliotecário especialista em catalogação ABNT (NBR 6023).\n"
        f"Abaixo estão {len(blocos)} documento(s) com a ficha catalográfica "
        "incompleta. Para cada um: o nome do arquivo, os campos já "
        "preenchidos, os campos FALTANTES e um trecho do início do texto.\n\n"
        "TAREFA: preencha os campos faltantes de cada documento com base no "
        "trecho e no seu conhecimento. NÃO INVENTE: se não houver como saber "
        "um campo com segurança, omita-o. Autoria no formato ABNT "
        "(SOBRENOME, Nome; para órgão público, o nome do ente). Datas e anos "
        "como aparecem no documento.\n\n"
        "VOCABULÁRIOS FECHADOS (use exatamente um destes valores):\n"
        f"- tipo_fonte: {', '.join(v['tipos_fonte'])}\n"
        f"- tipo: {', '.join(v['tipos'])}\n"
        f"- area: {', '.join(v['areas'])}\n"
        f"- status: {', '.join(v['status'])}\n\n"
        "FORMATO DE SAÍDA (obrigatório: responda APENAS este JSON, sem "
        "comentários nem texto fora dele):\n"
        '{"fichas": [{"arquivo": "<nome exato do arquivo>.md", '
        '"campos": {"autoria": "SOBRENOME, Nome", "titulo": "...", '
        '"ano": "...", "resumo": "3 a 8 linhas"}}]}\n'
        f"Campos aceitos em \"campos\": {', '.join(_CAMPOS_IA)}. "
        "Para autoria/area com múltiplos valores, separe com \"; \".\n\n"
        + "\n\n".join(blocos))
    return {"pendentes": len(blocos), "prompt": prompt}


def _reparar_json(texto: str) -> str:
    """Conserta defeitos CLÁSSICOS de JSON emitido por IA, sem tocar no
    conteúdo válido: aspas internas sem escape (ex.: "the "Laffer curve"")
    e quebras de linha cruas dentro de strings. Máquina de estados: dentro
    de uma string, um `"` só FECHA se o próximo char útil for , } ] ou : —
    senão é aspa interna e ganha escape."""
    saida, dentro, i, n = [], False, 0, len(texto)
    while i < n:
        c = texto[i]
        if not dentro:
            if c == '"':
                dentro = True
            saida.append(c)
        elif c == "\\" and i + 1 < n:
            saida.append(c)
            saida.append(texto[i + 1])
            i += 1
        elif c == "\n":
            saida.append("\\n")
        elif c == '"':
            # FECHA só se o que vem depois é ESTRUTURA JSON de verdade:
            #   "}  "]           → fecha sempre
            #   ",  seguido de " { [ dígito t f n → próximo item/chave
            #   ":  seguido de " { [ dígito t f n → valor de chave
            # Senão é aspa interna de prosa (ex.: `o termo "Laffer", cunhado`)
            # e ganha escape — antes, `",` fechava sempre e mutilava o resto.
            j = i + 1
            while j < n and texto[j] in " \t\r\n":
                j += 1
            fecha = False
            if j >= n or texto[j] in "}]":
                fecha = True
            elif texto[j] in ",:":
                k2 = j + 1
                while k2 < n and texto[k2] in " \t\r\n":
                    k2 += 1
                if k2 >= n or texto[k2] in '"{[-0123456789tfn':
                    fecha = True
            if fecha:
                dentro = False
                saida.append(c)
            else:
                saida.append('\\"')      # aspa interna sem escape
        else:
            saida.append(c)
        i += 1
    return "".join(saida)


def _extrair_json_ia(texto: str) -> dict:
    """Aceita a resposta como vier: JSON puro, com cerca ```json```, com
    prosa em volta — e com os defeitos comuns de IA (aspas internas sem
    escape, quebras de linha em strings), reparados em 2ª tentativa."""
    texto = texto.strip()
    candidatos = [
        texto,
        re.sub(r"^```(?:json)?\s*|\s*```$", "", texto, flags=re.M),
        texto[texto.find("{"): texto.rfind("}") + 1],
    ]
    candidatos += [_reparar_json(c) for c in list(candidatos)]
    for candidato in candidatos:
        try:
            d = json.loads(candidato)
            if isinstance(d, dict):
                return d
        except (ValueError, TypeError):
            continue
    raise ValueError("não encontrei JSON válido na resposta")


def aplicar_lote_ia(resposta: str):
    """Valida e aplica a resposta da IA. Reversível: um nível de undo por
    backup .antes-ia (a leva anterior é descartada a cada nova aplicação)."""
    try:
        dados = _extrair_json_ia(resposta or "")
    except ValueError as e:
        return {"ok": False, "msg": f"Resposta inválida: {e}. Cole o JSON "
                                    "que a IA devolveu (com ou sem ```)."}
    fichas = dados.get("fichas")
    if not isinstance(fichas, list) or not fichas:
        return {"ok": False, "msg": 'JSON sem a lista "fichas".'}

    v = _vocab()
    vocab_de = {"tipo_fonte": set(v["tipos_fonte"]), "tipo": set(v["tipos"]),
                "area": set(v["areas"]), "status": set(v["status"]),
                "confiabilidade": set(v["confiabilidade"])}
    base = Path(CFG["root"]) / "2-MARKDOWN-BRUTO"
    aplicadas, rejeitadas, avisos, prontos = [], [], [], []
    for item in fichas:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("arquivo") or "")
        p = _ficha_path(nome)
        if p is None or not p.exists():
            rejeitadas.append({"arquivo": nome or "(sem nome)",
                               "motivo": "arquivo não existe no 2-MARKDOWN-BRUTO"})
            continue
        campos_in = item.get("campos")
        if not isinstance(campos_in, dict):
            rejeitadas.append({"arquivo": nome, "motivo": 'sem o objeto "campos"'})
            continue
        campos, descartes = {}, []
        for k, val in campos_in.items():
            k = str(k).strip()
            if k not in _CAMPOS_IA and k != "confiabilidade":
                avisos.append(f"{nome}: campo '{k}' não é aceito — ignorado")
                descartes.append(f"{k} (nome não aceito)")
                continue
            if val is None:
                descartes.append(f"{k}=null")
                continue
            if isinstance(val, list):
                val = "; ".join(str(x) for x in val)
            val = str(val).strip()
            if not val:
                descartes.append(f"{k} (vazio)")
                continue
            if k in vocab_de:
                candidatos = ([x.strip() for x in val.split(";")]
                              if k == "area" else [val])
                validos = [c for c in candidatos if c in vocab_de[k]]
                fora = [c for c in candidatos if c not in vocab_de[k]]
                if fora:
                    avisos.append(f"{nome}: {k} '{'; '.join(fora)}' fora do "
                                  "vocabulário — ignorado"
                                  + (" (mantidos os válidos)" if validos else ""))
                if not validos:
                    descartes.append(f"{k} (fora do vocabulário)")
                    continue
                val = "; ".join(validos)
            campos[k] = val
        if not campos:
            # diagnóstico TRANSPARENTE: sem isso, "nenhum campo válido"
            # não diz se a IA mandou tudo null, nomes errados ou vazios
            detalhe = "; ".join(descartes[:8]) or "objeto campos vazio"
            if len(descartes) > 8:
                detalhe += f" … (+{len(descartes) - 8})"
            rejeitadas.append({"arquivo": nome,
                               "motivo": f"nenhum campo válido restou — "
                                         f"recebido: {detalhe}"})
            continue
        prontos.append((nome, p, campos))

    if prontos:
        # só agora a leva anterior é descartada — resposta inteira inválida
        # NÃO destrói o undo existente
        for velho in base.glob("*.md.antes-ia"):
            velho.unlink()
    for nome, p, campos in prontos:
        # REVERSÍVEL: snapshot antes de tocar
        shutil.copy2(p, p.with_name(p.name + ".antes-ia"))
        r = salvar_ficha(nome, campos)
        aplicadas.append({"arquivo": nome, "gravados": r.get("gravados", []),
                          "nota": r.get("nota", "?"), "grupo": r.get("grupo", "?")})
    return {"ok": True, "aplicadas": aplicadas, "rejeitadas": rejeitadas,
            "avisos": avisos}


def reverter_lote_ia():
    """Restaura os arquivos da ÚLTIMA aplicação de IA (um nível de undo)."""
    base = Path(CFG["root"]) / "2-MARKDOWN-BRUTO"
    if not base.is_dir():
        return {"ok": False, "msg": "pasta não encontrada"}
    restaurados = []
    for b in sorted(base.glob("*.md.antes-ia")):
        alvo = b.with_name(b.name[:-len(".antes-ia")])
        shutil.move(str(b), str(alvo))
        restaurados.append(alvo.name)
    with _FICHAS_LOCK:
        _FICHAS_CACHE["chave"] = None
        _PUB_CACHE["chave"] = None
    if not restaurados:
        return {"ok": False, "msg": "não há aplicação de IA para reverter"}
    return {"ok": True, "restaurados": restaurados}


# Prontidão REAL de publicação para o card 7 (dot "7"). "N arquivos no
# limpo" não diz nada: o publicar tem trava de qualidade (REPROVADO não
# entra; fatia fica retida com o índice) — o card antecipa isso auditando
# só a CAMADA-1 do limpo (índices + mestres únicos, ~10 ms) e detectando
# bruto mais novo que o derivado (refatie). Cache no padrão do resumo_fichas.
_PUB_CACHE = {"chave": None, "resumo": None}
_PUB_VAZIO = {"obras": 0, "prontas": 0, "reprovadas": 0,
              "desatualizadas": 0, "fora_do_limpo": 0}


def resumo_publicacao():
    if not CFG["root"]:
        return dict(_PUB_VAZIO)
    base = Path(CFG["root"])
    limpo, bruto = base / "3-MARKDOWN-LIMPO", base / "2-MARKDOWN-BRUTO"
    if not limpo.is_dir():
        return dict(_PUB_VAZIO)
    try:
        camada1 = [f for f in limpo.glob("*.md")
                   if not f.name.startswith(("RELATORIO", "_"))
                   and not re.search(r"_p\d{2,}$", f.stem)]
        mestres = ([f for f in bruto.glob("*.md")
                    if not f.name.startswith(("RELATORIO", "_"))]
                   if bruto.is_dir() else [])
        chave = tuple(sorted(
            (str(f), f.stat().st_mtime_ns, f.stat().st_size)
            for f in camada1 + mestres))
    except OSError:
        chave = None
    with _FICHAS_LOCK:
        if chave is not None and chave == _PUB_CACHE["chave"]:
            return _PUB_CACHE["resumo"]
    r = dict(_PUB_VAZIO)
    r["obras"] = len(camada1)
    for f in camada1:
        try:
            nota = _nota_auditoria(_auditar_arquivo(f))
        except Exception:
            continue
        r["reprovadas" if nota == "REPROVADO" else "prontas"] += 1
    # staleness bruto→limpo: ficha corrigida no mestre exige REFATIAR
    for m in mestres:
        pref = comum.prefixo_fatia(m.stem)
        derivado = limpo / f"{pref}_INDICE.md"
        if not derivado.exists():
            derivado = limpo / m.name        # mestre pequeno copiado inteiro
        try:
            if not derivado.exists():
                r["fora_do_limpo"] += 1
            elif m.stat().st_mtime > derivado.stat().st_mtime:
                r["desatualizadas"] += 1
        except OSError:
            continue
    with _FICHAS_LOCK:
        _PUB_CACHE["chave"] = chave
        _PUB_CACHE["resumo"] = r
    return r


def _atualizar_frontmatter(texto: str, novos: dict) -> str:
    """Atualiza campos do frontmatter linha a linha, preservando o resto
    (comentários e campos não tocados). Substituir um campo remove também
    a continuação do bloco (linhas indentadas / itens de lista)."""
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n?", texto, re.DOTALL)
    if m:
        linhas = m.group(1).split("\n")
        resto = texto[m.end():]
    else:
        linhas, resto = [], texto
    for campo, valor in novos.items():
        linha = frontmatter.emitir(campo, valor)
        i = next((k for k, l in enumerate(linhas)
                  if re.match(rf"^{re.escape(campo)}\s*:", l)), None)
        if i is None:
            linhas.append(linha)
            continue
        j = i + 1
        while j < len(linhas) and (linhas[j].startswith((" ", "\t", "- "))):
            j += 1
        linhas[i:j] = [linha]
    return "---\n" + "\n".join(linhas) + "\n---\n" + resto


def salvar_ficha(nome: str, campos: dict):
    """Aplica os campos preenchidos no formulário. Vazio = não mexe."""
    p = _ficha_path(nome)
    if p is None or not p.exists():
        return {"ok": False, "msg": f"arquivo não encontrado: {nome}"}
    novos = {}
    for k, v in campos.items():
        k = str(k).strip()
        v = str(v).strip()
        if not k or not v or not re.fullmatch(r"[a-z_][a-z0-9_]*", k):
            continue
        if k in _CAMPOS_LISTA:
            novos[k] = [x.strip() for x in v.split(";") if x.strip()]
        else:
            novos[k] = v
    if not novos:
        return {"ok": False, "msg": "nenhum campo preenchido."}
    texto = p.read_text(encoding="utf-8", errors="replace")
    novo = _atualizar_frontmatter(texto, novos)
    # SALVAR = REVISAR: o humano viu tipo_fonte/tipo no formulário — as
    # marcas "REVISE" da automação cumpriram o papel e saem do arquivo
    # (sem isso a ficha ficava presa em "Conferir" para sempre).
    novo = re.sub(
        r"[ \t]*# (?:palpite da triagem|derivado do tipo_fonte) — REVISE", "", novo)
    p.write_text(novo, encoding="utf-8")
    gravados = sorted(novos)

    # Ficha completa + referência VAZIA → gera da própria ficha, na hora
    # (determinístico: só combina o que o humano preencheu — nada inventado).
    # Referência já existente NUNCA é sobrescrita aqui (curadoria vence);
    # para essa há o botão "↻ regenerar da ficha" no formulário.
    cls = _classificar_ficha(p)
    fm = frontmatter.ler(p.read_text(encoding="utf-8", errors="replace")).campos
    tf = str(fm.get("tipo_fonte") or "")
    # "referencia_abnt vazia" é erro de ficha, mas é O erro que a geração
    # resolve — não pode barrar a si mesma; só os DEMAIS erros barram.
    so_falta_ref = (not cls["faltam_campos"]
                    and all(e.startswith("referencia_abnt")
                            for e in cls["erros_ficha"]))
    if (so_falta_ref and comum.vazio(fm.get("referencia_abnt"))
            and tf in taxonomia.TIPOS_FONTE and taxonomia.eh_abnt(tf)):
        try:
            import validar_yaml_abnt
            ref = validar_yaml_abnt.montar_referencia(fm).strip()
        except Exception:
            ref = ""
        if ref:
            p.write_text(_atualizar_frontmatter(
                p.read_text(encoding="utf-8", errors="replace"),
                {"referencia_abnt": ref}), encoding="utf-8")
            gravados.append("referencia_abnt (gerada da ficha)")
            cls = _classificar_ficha(p)

    with _FICHAS_LOCK:                      # mtime pode ser grosseiro no /mnt
        _FICHAS_CACHE["chave"] = None
        _PUB_CACHE["chave"] = None
    resposta = {"ok": True, "gravados": gravados}
    resposta.update(cls)
    return resposta


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
        if u.path == "/api/vocab":
            return self._send(200, json.dumps(_vocab(), ensure_ascii=False))
        if u.path == "/api/fichas":
            return self._send(200, json.dumps(listar_fichas(), ensure_ascii=False))
        if u.path == "/api/ia_prompt":
            return self._send(200, json.dumps(gerar_prompt_ia(), ensure_ascii=False))
        if u.path == "/api/auditoria":
            q = parse_qs(u.query)
            return self._send(200, json.dumps(
                relatorio_auditoria(q.get("pasta", [""])[0]), ensure_ascii=False))
        if u.path == "/api/ficha":
            q = parse_qs(u.query)
            p = _ficha_path(q.get("arq", [""])[0])
            if p is None or not p.exists():
                return self._send(200, json.dumps({}))
            fm = frontmatter.ler(
                p.read_text(encoding="utf-8", errors="replace")).campos
            plano = {k: ("; ".join(str(x) for x in v) if isinstance(v, list)
                         else str(v if v is not None else ""))
                     for k, v in fm.items()}
            cls = _classificar_ficha(p)
            plano["_faltam_campos"] = cls["faltam_campos"]
            plano["_pendencias"] = cls["pendencias_outras_etapas"]
            # a referência ABNT ninguém deveria montar à mão: o validador
            # sabe sugerir — mas SÓ com os bloqueantes preenchidos (com
            # autoria vazia a sugestão sai mutilada: ". 6.298, de ...")
            plano["_sugestao_referencia"] = ""
            # o erro "referencia_abnt vazia" não bloqueia a própria sugestão
            erros_nref = [e for e in cls["erros_ficha"]
                          if not e.startswith("referencia_abnt")]
            bloqueio = cls["faltam_campos"] or (
                ["tipo_fonte"] if erros_nref else [])
            if not bloqueio:
                # a sugestão vem SEMPRE que a ficha permite — mesmo com uma
                # referência já gravada: se divergirem, o formulário oferece
                # "↻ regenerar da ficha" (cobre referência gerada mutilada
                # antes de a ficha estar completa)
                try:
                    import validar_yaml_abnt
                    plano["_sugestao_referencia"] = (
                        validar_yaml_abnt.montar_referencia(fm).strip())
                except Exception:
                    pass
            else:
                plano["_sugestao_bloqueada_por"] = bloqueio
            return self._send(200, json.dumps(plano, ensure_ascii=False))
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
                    salvar_config()   # root/scripts válidos deste POST persistem
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

            salvar_config()
            return self._send(200, json.dumps(
                {"ok": not avisos, "avisos": avisos, "cfg": CFG}, ensure_ascii=False))

        if u.path == "/api/ficha":
            r = salvar_ficha(data.get("arquivo", ""), data.get("campos") or {})
            return self._send(200, json.dumps(r, ensure_ascii=False))

        if u.path == "/api/ia_aplicar":
            r = aplicar_lote_ia(data.get("resposta", ""))
            return self._send(200, json.dumps(r, ensure_ascii=False))

        if u.path == "/api/ia_reverter":
            r = reverter_lote_ia()
            return self._send(200, json.dumps(r, ensure_ascii=False))

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
                                       int(data.get("romanas") or 0),
                                       reconverter=bool(data.get("reconverter")))
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
            elif a == "qualidade":
                ok, msg = acao_qualidade(data.get("pasta", ""))
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
            elif a == "radar":
                ok, msg = acao_radar(data.get("pasta", ""),
                                     aplicar=bool(data.get("aplicar", False)))
            else:
                ok, msg = False, "Ação desconhecida."
            if ok:
                JOB.action = a
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
#ef .dot{font-size:14px}   /* ✎: trabalho humano contínuo, sem número de etapa */
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

/* ---- progresso da etapa em execução (dentro do card) ---- */
.etprog{margin-top:9px;padding-top:9px;border-top:1px dashed var(--line)}
.ptxt{font-size:12px;color:var(--ink-2);display:flex;align-items:center;gap:7px;
  flex-wrap:wrap;min-width:0}
.ptxt .parq{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}
.pbar{height:6px;background:var(--surf2);border:1px solid var(--line);
  border-radius:4px;margin-top:6px;overflow:hidden}
.pfill{height:100%;background:var(--burg);border-radius:4px;transition:width .4s}
.spin{width:12px;height:12px;border:2px solid var(--line);border-top-color:var(--burg);
  border-radius:50%;animation:gira .8s linear infinite;flex-shrink:0}
@keyframes gira{to{transform:rotate(360deg)}}

/* ---- botão ⓘ e modal "o que faz esta etapa" ---- */
.iet{width:20px;height:20px;border-radius:50%;border:1px solid var(--line);
  background:var(--surf2);color:var(--muted);font:600 12px var(--serif);
  cursor:pointer;flex-shrink:0;line-height:1;padding:0}
.iet:hover{border-color:var(--brass);color:var(--brass)}
.imod-bg{position:fixed;inset:0;background:rgba(27,42,65,.45);display:none;
  z-index:70;align-items:center;justify-content:center;padding:20px}
.imod-bg.on{display:flex}
.imod{background:var(--surf);border-radius:14px;max-width:640px;width:100%;
  max-height:85vh;overflow-y:auto;box-shadow:0 18px 60px rgba(0,0,0,.25);
  padding:20px 22px}
.imod h3{font:600 17px var(--serif);margin:0;flex:1}
.imod .sub{font:600 10.5px var(--sans);letter-spacing:.08em;text-transform:uppercase;
  color:var(--brass);margin:16px 0 6px}
.imod p{font-size:13px;margin:6px 0;color:var(--ink-2);line-height:1.55}
.imod .bt{display:grid;grid-template-columns:auto 1fr;gap:8px 12px;font-size:12.5px;
  color:var(--ink-2);line-height:1.5}
.imod .bt b{white-space:nowrap;color:var(--ink);border:1px solid var(--line);
  border-radius:7px;padding:2px 9px;height:fit-content;background:var(--surf2);
  font-size:12px}
.imod code{background:var(--surf2);border:1px solid var(--line);border-radius:4px;
  padding:0 4px;font:11.5px var(--mono)}

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
/* botão Ambiente (status) · alerta · slideover */
.bamb{height:38px;padding:0 14px;border-radius:8px;border:1.5px solid var(--line);
  background:var(--surf);cursor:pointer;font-weight:600;white-space:nowrap;font-size:13px}
.bamb.ok{border-color:var(--ok);color:var(--ok)}
.bamb.falta{border-color:var(--err);color:var(--err)}
.alerta{margin-top:6px;font-size:12.5px;color:var(--err);font-weight:600}
.sov-bg{position:fixed;inset:0;background:rgba(27,42,65,.35);opacity:0;
  pointer-events:none;transition:opacity .25s;z-index:60}
.sov-bg.on{opacity:1;pointer-events:auto}
.sover{position:fixed;top:0;right:0;height:100%;width:min(480px,92vw);
  background:var(--surf);box-shadow:-12px 0 40px rgba(0,0,0,.18);z-index:61;
  transform:translateX(100%);transition:transform .28s ease;
  display:flex;flex-direction:column}
.sover.on{transform:translateX(0)}
.sov-head{display:flex;align-items:center;gap:10px;padding:16px 18px;
  border-bottom:1px solid var(--line)}
.sov-head h2{font-size:16px;margin:0;flex:1}
/* botões ← / ✕ dos painéis laterais e do modal ⓘ: glifo CENTRADO
   (botão nativo com width/height fixos desalinha o caractere) */
.fechar{border:1px solid var(--line);background:var(--surf2);color:var(--ink-2);
  border-radius:8px;width:32px;height:32px;cursor:pointer;font-size:15px;
  display:flex;align-items:center;justify-content:center;
  padding:0;line-height:1;flex-shrink:0}
.fechar:hover{border-color:var(--burg);color:var(--burg)}
.sov-body{padding:16px 18px;overflow-y:auto}
.sov-dica{font-size:12.5px;color:var(--muted);margin:0 0 12px}
.sover.fichas{width:min(580px,94vw)}
.fitem{border:1px solid var(--line);border-radius:10px;padding:9px 11px;
  margin-bottom:8px;background:var(--surf2)}
.fitem .fnome{font-weight:600;font-size:12.5px;display:flex;gap:8px;
  align-items:center;justify-content:space-between}
.fitem .fnome span{overflow-wrap:anywhere}
.fitem .fdet{font-size:11.5px;color:var(--muted);margin-top:4px;line-height:1.55}
.fitem .fdet .err{color:var(--err)} .fitem .fdet .rev{color:var(--warn)}
.fitem .fdet .pok{color:var(--ok)}
/* formulário da ficha: obrigatório (asterisco) e obrigatório VAZIO (vermelho) */
.campo label .ob{color:var(--err);font-weight:700}
.campo.falta label{color:var(--err)}
.campo.falta input,.campo.falta select{border-color:var(--err)}
.fb-bloco{border:1px solid var(--line);border-radius:8px;padding:8px 10px;
  margin-bottom:8px;font-size:12.5px;line-height:1.55}
.fb-bloco b.t{display:block;font-size:11px;letter-spacing:.06em;
  text-transform:uppercase;margin-bottom:3px}
.fgrupo{font:600 10.5px var(--sans);letter-spacing:.08em;
  text-transform:uppercase;margin:14px 0 7px}
.fgrupo:first-child{margin-top:0}
.fgrupo.err{color:var(--err)} .fgrupo.warn{color:var(--warn)} .fgrupo.ok{color:var(--ok)}
.sover .diag{grid-template-columns:1fr}
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
        <input type="text" id="root" placeholder="clique em Procurar…"
               oninput="if(this.value.trim()) rootAviso.hidden = true">
        <div class="alerta" id="rootAviso" hidden>⚠ Defina primeiro a pasta do acervo — clique em 📁 Procurar…</div>
      </div>
      <button class="bnav" style="height:38px" onclick="abrirNav('root','dir')">📁 Procurar…</button>
      <button class="primary" style="height:38px" onclick="salvar()">Definir</button>
      <button class="bamb" id="btnAmb" onclick="abrirAmbiente()"
              title="dependências do sistema — verde: tudo pronto; vermelho: precisa de ação">⚙ Ambiente</button>
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

<!-- 02 EXECUÇÃO -->
<section>
  <div class="head"><span class="n">02</span><h2>Execução</h2><p id="jobName">nenhuma tarefa</p></div>
  <pre id="log">Aguardando…</pre>
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
          <h3>Triagem</h3><button class="iet" onclick="abrirInfo('e1')" title="O que faz esta etapa?">i</button>
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
          <h3>OCR</h3><button class="iet" onclick="abrirInfo('e2')" title="O que faz esta etapa?">i</button>
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
          <h3>Paginação</h3><button class="iet" onclick="abrirInfo('e3')" title="O que faz esta etapa?">i</button>
          <span class="desc">PDF → Markdown com âncoras <code>{{p.NN}}</code>. Converte todos os PDFs pesquisáveis; escaneado sem OCR fica listado como pulado.</span>
          <span class="st" id="s3">—</span>
          <div class="acoes">
            <button data-a class="primary" onclick="acao('paginar',{offset:+offset.value,romanas:+romanas.value,reconverter:reconv.checked})">Converter pasta</button>
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
          <div class="dica"><label style="cursor:pointer"><input type="checkbox" id="reconv"> <b>reconverter existentes</b> — sobrescreve os markdowns já convertidos, <span style="color:var(--err)">inclusive fichas corrigidas à mão</span>. Desmarcado (padrão), quem já foi convertido é pulado e a ficha fica preservada.</label></div>
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
          <h3>Limpar OCR</h3><button class="iet" onclick="abrirInfo('e4')" title="O que faz esta etapa?">i</button>
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
          <h3>Fatiar</h3><button class="iet" onclick="abrirInfo('e5')" title="O que faz esta etapa?">i</button>
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
          <h3>Qualidade</h3><button class="iet" onclick="abrirInfo('e6')" title="O que faz esta etapa?">i</button>
          <span class="desc">Um exame só: âncoras íntegras · YAML coerente · nota <b>PRONTO/PARCIAL/REPROVADO</b>. A triagem abre ao terminar.</span>
          <span class="st" id="s6">—</span>
          <div class="acoes">
            <button class="bnav" onclick="abrirNav('audp','dir')">📁</button>
            <button onclick="abrirAuditoria()" title="triagem do que a auditoria achou: do grave ao irrelevante, com a ação de cada item">📄 Relatório</button>
            <button onclick="abrirIA()" title="gera um prompt com as fichas pendentes para colar em qualquer IA (Gemini, ChatGPT, Claude...) e aplica a resposta de volta — com validação e undo">🤖 Preencher com IA</button>
            <button data-a class="primary" onclick="acao('qualidade',{pasta:audp.value})">Auditar qualidade</button>
          </div>
        </div>
        <div class="extra">
          <input type="text" id="audp" placeholder="(padrão: 2-MARKDOWN-BRUTO)">
          <div class="dica">O que sobrar de pendência aqui — autor, título, editora, ano, resumo — corrige-se no card <b>✎ Fichas</b> abaixo; o refino fino é o <b>Projeto Claude</b> (Fase 3c do WORKFLOW).</div>
        </div>
      </div>
    </div>

    <div class="et" id="ef">
      <div class="bar"><div class="dot">✎</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Fichas</h3><button class="iet" onclick="abrirInfo('ef')" title="O que faz esta etapa?">i</button>
          <span class="desc">Revisão <b>humana</b> da ficha ABNT — corrija o que bloqueia e confirme o que a automação atribuiu.</span>
          <span class="st" id="sf">—</span>
          <div class="acoes"><button class="primary" onclick="abrirFichas()">📋 Abrir fichas</button></div>
        </div>
      </div>
    </div>

  </div>

  <div class="fase">Publicação — o segundo cérebro no Obsidian</div>
  <div class="trilho">
    <div class="et" id="e8">
      <div class="bar"><div class="dot">7</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Publicar</h3><button class="iet" onclick="abrirInfo('e8')" title="O que faz esta etapa?">i</button>
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
      <div class="bar"><div class="dot">8</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Auditar vault</h3><button class="iet" onclick="abrirInfo('e9')" title="O que faz esta etapa?">i</button>
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

  <div class="fase">Manutenção — o radar mantém o cérebro vivo</div>
  <div class="trilho">
    <div class="et" id="e10">
      <div class="bar"><div class="dot">9</div><div class="linha"></div></div>
      <div class="conteudo">
        <div class="topo">
          <h3>Radar</h3><button class="iet" onclick="abrirInfo('e10')" title="O que faz esta etapa?">i</button>
          <span class="desc">Correlaciona os achados de <b>Radar/</b> (Cowork, Módulo E) às notas que os citam — por identificador, não por palpite.</span>
          <span class="st" id="s10">—</span>
          <div class="acoes">
            <button data-a onclick="acao('radar',{pasta:vaultp.value,aplicar:false})">Fila de revisão</button>
            <button data-a class="primary" onclick="acao('radar',{pasta:vaultp.value,aplicar:true})">Sinalizar A-conferir</button>
          </div>
        </div>
        <div class="extra">
          <div class="dica">O radar <b>sinaliza</b>; a decisão de reclassificar (Revogado/Superado) é do advogado, no ritual semanal. "Sinalizar" marca as notas afetadas com <b>A-conferir</b> — elas caem no painel de pendências do MOC. Fila: <b>RELATORIO-RADAR.md</b>.</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- 04 TRIAGEM -->
<section>
  <div class="head"><span class="n">04</span><h2>Triagem</h2>
    <p>o tipo é um palpite automático — <b>revise</b></p></div>
  <div class="tw"><table>
    <thead><tr><th>Arquivo</th><th>Idioma</th><th>Pgs</th><th>Texto?</th><th>OCR</th>
      <th>Tipo (palpite)</th><th>Âncora?</th><th>Rota</th></tr></thead>
    <tbody id="tb"><tr><td colspan="8" style="color:var(--muted);padding:14px">Rode a triagem para popular.</td></tr></tbody>
  </table></div>
  <div class="stat" id="stat"></div>
</section>

<!-- SLIDEOVER · FICHAS (lista + edição) -->
<div class="sov-bg" id="fsovBg" onclick="fecharFicha()"></div>
<aside class="sover fichas" id="fsov" aria-label="Fichas">
  <div class="sov-head">
    <button class="fechar" id="fVoltar" onclick="voltarFichas()" title="voltar à lista" hidden>←</button>
    <h2 id="fsovTit" style="font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">📋 Fichas</h2>
    <button class="fechar" onclick="fecharFicha()" title="fechar (Esc)">✕</button></div>
  <div class="sov-body">
    <div id="fichaLista">
      <p class="sov-dica" id="fichasInfo">carregando…</p>
      <div id="fichasItens"></div>
      <p class="sov-dica" style="margin-top:12px">O mestre é o <b>2-MARKDOWN-BRUTO</b>: corrija aqui e <b>refatie</b> (etapa 5) — as fatias herdam a ficha do índice.</p>
    </div>
    <div id="fichaEdicao" hidden>
      <p class="sov-dica" id="fsovErros"></p>
      <div id="fichaForm"></div>
      <div style="display:flex;gap:8px;margin-top:14px">
        <button class="primary" onclick="salvarFicha()" style="flex:1">💾 Salvar e revalidar</button>
      </div>
    </div>
  </div>
</aside>

<!-- SLIDEOVER · RELATÓRIO DE AUDITORIA -->
<div class="sov-bg" id="asovBg" onclick="fecharAuditoria()"></div>
<aside class="sover fichas" id="asov" aria-label="Relatório de auditoria">
  <div class="sov-head">
    <h2 id="asovTit" style="font-size:14px">📄 Auditoria — triagem</h2>
    <button class="fechar" onclick="fecharAuditoria()" title="fechar (Esc)">✕</button></div>
  <div class="sov-body">
    <p class="sov-dica" id="asovInfo">carregando…</p>
    <div id="asovItens"></div>
  </div>
</aside>

<!-- SLIDEOVER · AMBIENTE -->
<div class="sov-bg" id="sovBg" onclick="fecharAmbiente()"></div>
<aside class="sover" id="sov" aria-label="Ambiente — dependências">
  <div class="sov-head"><h2>⚙ Ambiente</h2>
    <button class="fechar" onclick="fecharAmbiente()" title="fechar (Esc)">✕</button></div>
  <div class="sov-body">
    <p class="sov-dica">pendências viram um comando único, pronto para colar</p>
    <div id="pend"></div>
    <div class="diag" id="diag"></div>
  </div>
</aside>

<!-- MODAL · O QUE FAZ ESTA ETAPA -->
<div class="imod-bg" id="infoBg">
  <div class="imod" id="infoMod" role="dialog" aria-label="Sobre a etapa"></div>
</div>

<!-- MODAL · PREENCHER FICHAS COM IA -->
<div class="imod-bg" id="iaBg">
  <div class="imod" id="iaMod" role="dialog" aria-label="Preencher fichas com IA" style="max-width:760px">
    <div style="display:flex;align-items:flex-start;gap:10px">
      <h3 style="flex:1">🤖 Preencher fichas com IA</h3>
      <button class="fechar" onclick="fecharIA()" title="fechar (Esc)">✕</button></div>
    <p><b>1.</b> Copie o prompt abaixo e cole em qualquer IA (Gemini, ChatGPT, Claude…). Ele já contém as fichas pendentes, um trecho de cada documento e o <b>formato exato</b> da resposta.</p>
    <div style="display:flex;gap:8px;align-items:center;margin:6px 0">
      <button class="primary" id="iaCopiar" onclick="copiar(this, IA_PROMPT)">📋 Copiar o prompt</button>
      <span class="sov-dica" id="iaInfo" style="margin:0"></span>
    </div>
    <textarea id="iaPrompt" readonly rows="7" style="width:100%;font:11px var(--mono);resize:vertical"></textarea>
    <p style="margin-top:14px"><b>2.</b> Cole aqui a resposta da IA (o JSON, com ou sem <code>```</code>) e aplique. Cada ficha é <b>validada</b> (vocabulários, campos, arquivos) e um <b>backup</b> é feito antes — dá para desfazer.</p>
    <textarea id="iaResposta" rows="6" style="width:100%;font:11px var(--mono);resize:vertical" placeholder='{"fichas": [{"arquivo": "...", "campos": {...}}]}'></textarea>
    <div style="display:flex;gap:8px;margin-top:8px">
      <button class="primary" onclick="aplicarIA()" style="flex:1">✔ Validar e aplicar</button>
      <button onclick="reverterIA()" title="restaura os arquivos como estavam antes da última aplicação">↩ Reverter última aplicação</button>
    </div>
    <div id="iaResultado" style="margin-top:10px"></div>
  </div>
</div>

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
    if(navAlvo === 'root') rootAviso.hidden = true;
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
  // "Definir" antes de escolher a pasta → advertência sob o input (some
  // assim que uma pasta é escolhida/digitada).
  if(!campos && !root.value.trim()){
    rootAviso.hidden = false;
    root.focus();
    return;
  }
  if(root.value.trim()) rootAviso.hidden = true;
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
function abrirAmbiente(){ sovBg.classList.add('on'); sov.classList.add('on'); }
function fecharAmbiente(){ sovBg.classList.remove('on'); sov.classList.remove('on'); }
document.addEventListener('keydown', e => {
  if(e.key === 'Escape'){ fecharAmbiente(); fecharInfo(); fecharFicha(); fecharAuditoria(); fecharIA(); }
});
iaBg.addEventListener('click', e => { if(e.target === iaBg) fecharIA(); });

/* ---------- modal "o que faz esta etapa" ---------- */
const INFO = {
 e1:{t:'1 · Triagem — o raio-X, sem alterar nada',
  o:'Roda o <code>aplicar_ocr.sh</code> em <b>modo simulação</b>: examina cada PDF página a página (tem camada de texto? é digitalizado?), detecta o idioma e infere o tipo provável pelo nome e pelo conteúdo. Nenhum arquivo é alterado.',
  a:[['Analisar','executa <code>aplicar_ocr.sh</code> (dry-run) na pasta do acervo e grava a planilha <code>controle.csv</code>, que preenche a tabela da seção 04 e guia as etapas seguintes.']],
  s:'<code>controle.csv</code> na pasta do acervo. Revise a tabela da seção 04 — ela é o seu checkpoint.'},
 e2:{t:'2 · OCR — torna os digitalizados pesquisáveis',
  o:'Aplica reconhecimento de texto (<code>ocrmypdf</code>) <b>só nos PDFs que precisam</b>, no idioma detectado na triagem. O original é preservado: nasce uma cópia <code>nome_OCR.pdf</code>. PDFs que já têm texto são pulados. Durante o processamento, este card mostra o arquivo atual e a barra de progresso; o log completo corre na seção 02.',
  a:[['Aplicar OCR','executa <code>aplicar_ocr.sh</code> (sem dry-run, modo manter). Livro digitalizado grande pode levar mais de uma hora — acompanhe pelo sinal de vida.']],
  s:'Cópias <code>_OCR.pdf</code> ao lado dos originais e a coluna <i>ocr_status</i> do <code>controle.csv</code> atualizada.'},
 e3:{t:'3 · Paginação — o markdown nasce aqui, com âncoras',
  o:'Converte PDF pesquisável em Markdown guardando o número de cada página como âncora <code>{{p.NN}}</code> — sem ela não há citação ABNT de livro. A âncora não atrapalha os tipos que não a exigem (lei, acórdão). Digitalizado ainda sem OCR não é convertível: aparece no log como <b>PULADO</b>, com a instrução de voltar à etapa 2.',
  a:[['Converter pasta','roda <code>injetar_paginas.py</code> (no venv) para cada PDF pesquisável do <code>controle.csv</code>, preferindo a cópia <code>_OCR</code>; o log lista os aptos e os pulados.'],
     ['📄 / Converter seleção','o mesmo, só nos arquivos que você escolher (pode misturar pastas); valida as âncoras ao final. Aceita ePUB/MOBI via Calibre (sem paginação fixa — aviso no log).'],
     ['offset / romanas','ajustes de paginação impressa: se a página "1" do livro é a 13ª folha do PDF, offset 12; "romanas até" = nº de folhas do prefácio em algarismos romanos.']],
  s:'Um <code>.md</code> por PDF em <code>2-MARKDOWN-BRUTO/</code>, com a ficha YAML pré-preenchida (tipo provável e idioma da triagem).'},
 e4:{t:'4 · Limpar OCR — conserto mecânico, sem IA',
  o:'O OCR deixa cicatrizes no texto: palavras quebradas por hífen na virada de linha ("tribu- tário"), cabeçalhos e rodapés repetidos em toda página, linhas de ruído. <b>Limpar</b> conserta isso mecanicamente — sem IA, sem custo, sem tocar nas âncoras. É o polimento entre a conversão e o fatiamento.',
  a:[['Limpar','roda <code>limpar_ocr.py --inplace</code> em <code>2-MARKDOWN-BRUTO/</code>; cria backup <code>.md.bak</code> de cada arquivo alterado.'],
     ['Corrigir idioma','roda <code>corrigir_idioma.py</code>: redetecta o idioma de cada markdown (no PDF-fonte, preferindo o <code>_OCR</code>; se não der, no próprio texto do md) e conserta o YAML — idioma errado faria a nota sumir de filtros por língua. Caso individual teimoso: no terminal, <code>corrigir_idioma.py arquivo.md --forcar por</code>.']],
  s:'Os mesmos <code>.md</code>, limpos, com backups <code>.md.bak</code> ao lado.'},
 e5:{t:'5 · Fatiar — o formato que a IA consome bem',
  o:'Livro de 800 páginas não cabe numa conversa de IA. O fatiamento divide o markdown grande em <b>fatias</b> de leitura rápida (~N palavras, cortadas em fim de seção) e cria uma <b>nota-índice</b> que as lista (<code>partes:</code>). Cada fatia herda a ficha da obra. Faça <b>antes</b> de levar ao Projeto Claude.',
  a:[['Fatiar','roda <code>fatiar.py</code> sobre <code>2-MARKDOWN-BRUTO/</code> gravando em <code>3-MARKDOWN-LIMPO/</code>; o campo numérico define as palavras por fatia (padrão 1200).'],
     ['Normalizar','roda <code>normalizar_yaml.py</code> no 2-MARKDOWN-BRUTO e no 3-MARKDOWN-LIMPO: deixa area/tags/autoria no formato do Obsidian e preenche <code>tipo</code> quando ele decorre sem ambiguidade do tipo_fonte (legislacao→Legislação) — sem <code>tipo</code>, a nota não tem rota de publicação. Não inventa vigência: status desconhecido vira <i>A-conferir</i>.']],
  s:'Nota-índice + fatias em <code>3-MARKDOWN-LIMPO/</code> — é isto que se publica no vault.'},
 e6:{t:'6 · Qualidade — o exame completo, num clique',
  o:'A fusão do antigo "Validar" com o antigo "Auditar" (eram dois botões parecidos): um job só examina <b>âncoras</b> (presença e integridade: duplicadas, fora de ordem, lacunas), <b>YAML coerente com o tipo</b> (campos, localizador, sistema de chamada) e dá a <b>nota</b> de cada arquivo — PRONTO, PARCIAL ou REPROVADO. Ao terminar, o <b>relatório-triagem abre sozinho</b>, do grave ao irrelevante, com a ação de cada item.',
  a:[['Auditar qualidade','roda <code>verificar_ancoras.py</code> + <code>auditar_acervo.py</code> na pasta indicada (padrão <code>2-MARKDOWN-BRUTO/</code>) e grava <code>RELATORIO-AUDITORIA.md</code>.'],
     ['📄 Relatório','reabre a triagem a qualquer momento: ✗ GRAVES (bloqueiam a publicação, com AÇÃO e atalho ✎), ⚠ CONFERIR, avisos irrelevantes, ✓ OK — fatias agregadas por obra.'],
     ['🤖 Preencher com IA','gera um prompt com as fichas pendentes (campos atuais + faltantes + trecho do documento) para colar em <b>qualquer IA</b>; a resposta em JSON volta pelo mesmo modal e é aplicada com <b>validação</b> (vocabulários e arquivos) e <b>backup automático</b> — "↩ Reverter" desfaz a última aplicação.'],
     ['📁','escolhe outra pasta para examinar.']],
  s:'<code>RELATORIO-AUDITORIA.md</code> + a triagem no painel lateral. O que reprova corrige-se no card <b>✎ Fichas</b>.'},
 ef:{t:'✎ · Fichas — a revisão humana (saneamento)',
  o:'O passo sem número do trilho: é <b>trabalho seu</b>, não de script — por isso o ✎. O card mostra ao vivo quantas fichas <b>bloqueiam</b> a publicação e quantas aguardam a sua <b>confirmação</b> do que a automação atribuiu. Erro que não se resolve na ficha (ex.: arquivo gigante) aparece <b>encaminhado</b> para a etapa certa — e como resolvido quando o disco prova que já foi (fatias existem).',
  a:[['📋 Abrir fichas','painel lateral com todas as fichas em 3 grupos: ✗ <b>Corrigir</b> (REPROVADAS — bloqueiam a publicação), ⚠ <b>Conferir</b> (palpite de tipo_fonte, tipo derivado, A-conferir) e ✓ Prontas. "✎ Editar" abre o formulário: campos exigidos pelo tipo com <b>asterisco</b>, vazios em <b>vermelho</b>, sugestão de referência ABNT quando a ficha permite; salvar revalida na hora.']],
  s:'Os próprios <code>.md</code> do <code>2-MARKDOWN-BRUTO</code>, corrigidos campo a campo. Depois de mexer nas fichas, <b>refatie</b> (etapa 5) — as fatias herdam.'},
 e8:{t:'7 · Publicar — o conteúdo chega ao vault',
  o:'Distribui <code>3-MARKDOWN-LIMPO/</code> nas pastas certas do vault por <b>regra</b> (tipo→pasta do perfil: doutrina por área, legislação, jurisprudência…), fatias junto do índice. Três travas: nota REPROVADA não entra; <b>copiar, nunca mover</b>; em conflito, <b>o vault vence</b> (sua curadoria manual não é sobrescrita). Se o índice de uma obra não publica (sem <code>tipo</code> ou reprovado), as fatias ficam <b>retidas com ele</b> — fatia sem índice nasceria órfã no vault. O card mostra a <b>prontidão real</b> antes de você clicar: obras prontas ✓, reprovadas (→ ✎ fichas), desatualizadas ou fora do limpo (→ refatie, etapa 5) — sem verde total, a publicação sai parcial.',
  a:[['Simular','roda <code>publicar.py --dry</code>: mostra o plano completo (o que iria para onde) sem gravar nada. <b>Sempre simule primeiro.</b>'],
     ['Publicar','roda <code>publicar.py</code> de verdade e grava <code>RELATORIO-PUBLICACAO.md</code> no vault.'],
     ['📁','escolhe outro vault (padrão <code>4-OBSIDIAN-VAULT/</code>).']],
  s:'Notas copiadas ao vault + <code>RELATORIO-PUBLICACAO.md</code>. Abra o Obsidian e navegue pelos MOCs.'},
 e9:{t:'8 · Auditar vault — o grafo está íntegro?',
  o:'O que nenhuma checagem arquivo-a-arquivo enxerga: fatia órfã, <code>partes:</code> que não bate com as fatias reais, wikilink quebrado, vocabulário fora do perfil (a nota <b>some dos painéis</b> Dataview sem erro), área sem MOC, nome duplicado.',
  a:[['Auditar vault','roda <code>auditar_vault.py --detalhado</code> no vault e grava <code>RELATORIO-VAULT.md</code> — cada achado vem com a causa e a correção.']],
  s:'<code>RELATORIO-VAULT.md</code> dentro do vault (abra no próprio Obsidian).'},
 e10:{t:'9 · Radar — o cérebro continua vivo',
  o:'As novidades (leis alteradas, julgados novos) coletadas pelo assistente na pasta <code>Radar/</code> são cruzadas com as notas do acervo que as citam — por <b>identificador forte</b> (Lei nº, Tema, Súmula, nº CNJ), não por palpite. O radar <b>sinaliza</b>; a decisão de reclassificar é sempre sua.',
  a:[['Fila de revisão','roda <code>radar.py</code>: correlaciona os achados novos e grava <code>RELATORIO-RADAR.md</code> com a fila do que conferir.'],
     ['Sinalizar A-conferir','roda <code>radar.py --aplicar</code>: marca <code>status: A-conferir</code> nas notas afetadas — elas aparecem no painel de pendências do MOC até você despachar.']],
  s:'<code>RELATORIO-RADAR.md</code> + notas afetadas sinalizadas (se você aplicar).'},
};
function abrirInfo(id){
  const i = INFO[id]; if(!i) return;
  infoMod.innerHTML =
    `<div style="display:flex;align-items:flex-start;gap:10px">
       <h3>${i.t}</h3>
       <button class="fechar" onclick="fecharInfo()" title="fechar (Esc)">✕</button></div>
     <p>${i.o}</p>
     <div class="sub">O que cada botão executa</div>
     <div class="bt">${i.a.map(([b,d])=>`<b>${b}</b><span>${d}</span>`).join('')}</div>
     <div class="sub">Resultado no disco</div><p>${i.s}</p>`;
  infoBg.classList.add('on');
}
function fecharInfo(){ infoBg.classList.remove('on'); }
infoBg.addEventListener('click', e => { if(e.target === infoBg) fecharInfo(); });

/* ---------- fichas: slideover do grupo Qualidade ---------- */
let VOCAB = null, FICHA_ARQ = '', F_CAMPOS = {};
const F_SEL = {tipo_fonte:'tipos_fonte', tipo:'tipos', area:'areas',
               status:'status', confiabilidade:'confiabilidade'};
function abrirFichas(){
  fsovBg.classList.add('on'); fsov.classList.add('on');
  FICHA_ARQ = '';
  voltarFichas();
  carregarFichas();
}
function voltarFichas(){
  fichaEdicao.hidden = true; fichaLista.hidden = false; fVoltar.hidden = true;
  fsovTit.textContent = '📋 Fichas — o que merece atenção';
  if(FICHA_ARQ){ FICHA_ARQ=''; carregarFichas(); }  // volta atualizada após editar
}
async function carregarFichas(){
  fichasInfo.textContent = 'carregando e validando cada ficha…';
  fichasItens.innerHTML = '';
  if(!VOCAB) VOCAB = await (await fetch('/api/vocab')).json();
  const fs = await (await fetch('/api/fichas')).json();
  if(!fs.length){
    fichasInfo.textContent = 'Nenhum markdown em 2-MARKDOWN-BRUTO — converta antes (etapa 3).';
    return;
  }
  // o grupo é decidido no SERVIDOR (_classificar_ficha) — regra única
  const corrigir = fs.filter(f=>f.grupo==='corrigir');
  const conferir = fs.filter(f=>f.grupo==='conferir');
  const prontas  = fs.filter(f=>f.grupo==='pronta');
  fichasInfo.innerHTML = `<b>${fs.length}</b> nota(s) — ` +
    `<span style="color:var(--err)">${corrigir.length} corrigir</span> · ` +
    `<span style="color:var(--warn)">${conferir.length} conferir</span> · ` +
    `<span style="color:var(--ok)">${prontas.length} prontas</span>`;
  const item = f => `<div class="fitem">
      <div class="fnome"><span>${esc(f.arquivo)}</span>
        <button class="bnav" onclick="abrirFicha(${q(f.arquivo)})">✎ Editar</button></div>
      <div class="fdet">
        ${f.tipo_fonte ? `tipo_fonte <b>${esc(f.tipo_fonte)}</b>` : '<span class="err">✗ sem tipo_fonte</span>'}` +
      `${f.tipo ? ` · tipo <b>${esc(f.tipo)}</b>` : ''}${f.ano ? ` · ${esc(f.ano)}` : ''}` +
      `${f.autoria ? ` · ${esc(f.autoria)}` : ''}
        ${f.erros_ficha.length ? `<br><span class="err">✗ ${f.erros_ficha.map(esc).join('</span><br><span class="err">✗ ')}</span>` : ''}
        ${f.pendencias_outras_etapas.map(p => p.resolvida
            ? `<br><span class="pok">✓ ${esc(p.msg.split(' — ')[0].split('.')[0])} — ${esc(p.orientacao)}</span>`
            : `<br><span class="rev">⤳ ${esc(p.msg.split(' — ')[0])} — ${esc(p.orientacao)}</span>`).join('')}
        ${f.revisar.length ? `<br><span class="rev">⚠ ${f.revisar.map(esc).join(' · ')}</span>` : ''}
        ${f.avisos.length ? `<br><span style="opacity:.75">avisos (não bloqueiam): ${f.avisos.map(esc).join(' · ')}${f.n_avisos>f.avisos.length?` · +${f.n_avisos-f.avisos.length}`:''}</span>` : ''}
      </div></div>`;
  const grupo = (t, cls, arr) => arr.length
    ? `<div class="fgrupo ${cls}">${t} (${arr.length})</div>` + arr.map(item).join('') : '';
  fichasItens.innerHTML =
      grupo('✗ Corrigir — bloqueiam a publicação', 'err', corrigir)
    + grupo('⚠ Conferir — a automação atribuiu; você confirma', 'warn', conferir)
    + grupo('✓ Prontas', 'ok', prontas);
}
async function abrirFicha(arq){
  if(!VOCAB) VOCAB = await (await fetch('/api/vocab')).json();
  F_CAMPOS = await (await fetch('/api/ficha?arq='+encodeURIComponent(arq))).json();
  FICHA_ARQ = arq;
  fsovTit.textContent = '✎ ' + arq;
  fsovErros.textContent = '';
  renderFicha();
  fichaLista.hidden = true; fichaEdicao.hidden = false; fVoltar.hidden = false;
}
function campoFicha(c){
  const v = F_CAMPOS[c] || '';
  const tf = F_CAMPOS.tipo_fonte || '';
  const bloqueante = (VOCAB.bloqueantes[tf]||[]).includes(c);
  const falta = bloqueante && !v;
  const ast = bloqueante ? ' <span class="ob" title="obrigatório para este tipo — bloqueia a publicação se vazio">*</span>' : '';
  const cls = falta ? 'campo falta' : 'campo';
  if(c === 'resumo'){
    // 3–8 linhas que a IA lê primeiro; o gravador é linha-a-linha, então
    // as quebras viram espaço ao salvar
    return `<div class="${cls}"><label>resumo · 3–8 linhas — a IA lê isto primeiro</label>
      <textarea id="f_resumo" rows="3" style="width:100%;resize:vertical" placeholder="(em branco = não mexe)">${esc(v)}</textarea></div>`;
  }
  if(F_SEL[c]){
    /* O seletor carrega o VALOR REAL selecionado — nada de "(manter: X)"
       com value vazio: quando o formulário se redesenhava (troca de
       tipo_fonte), a escolha do usuário virava o rótulo da opção vazia
       e era DESCARTADA no salvar (ficha REPROVADA com o valor na tela). */
    const ops = VOCAB[F_SEL[c]];
    const foraVocab = v && !ops.includes(v);
    return `<div class="${cls}"><label>${esc(c)}${ast}</label><select id="f_${esc(c)}">
      ${v ? '' : '<option value="" selected>(vazio — escolha para gravar)</option>'}
      ${foraVocab ? `<option value="${esc(v)}" selected>${esc(v)} (fora do vocabulário)</option>` : ''}
      ${ops.map(o=>`<option value="${esc(o)}"${o===v?' selected':''}>${esc(o)}</option>`).join('')}</select></div>`;
  }
  const extra = VOCAB.listas.includes(c) ? ' · vários? separe com ;' : '';
  return `<div class="${cls}"><label>${esc(c)}${ast}${falta?' — <b>preencha</b>':''}</label>
    <input type="text" id="f_${esc(c)}" value="${esc(v)}" placeholder="(em branco = não mexe)"></div>`;
}
function campoReferencia(){
  const v = (F_CAMPOS.referencia_abnt || '').trim();
  const sug = F_CAMPOS._sugestao_referencia || '';
  const bloq = F_CAMPOS._sugestao_bloqueada_por || [];
  let dica = '';
  if(sug && !v){
    dica = `<div class="dica">com a ficha completa, a referência é gravada <b>automaticamente</b> ao salvar:<br><i>${esc(sug)}</i></div>`;
  } else if(sug && v && sug !== v){
    dica = `<div class="dica">a referência gravada <b>difere</b> da que a ficha atual gera:<br><i>${esc(sug)}</i><br>
      <button class="bnav" onclick="f_referencia_abnt.value=${q(sug)}" style="margin-top:4px">↻ regenerar da ficha</button>
      <span style="opacity:.8">(troca no campo — salve para gravar; ignore se a sua versão manual é a correta)</span></div>`;
  } else if(!v && bloq.length){
    dica = `<div class="dica">a referência é gerada automaticamente quando <b>${bloq.map(esc).join(', ')}</b> estiverem preenchidos — gerar agora sairia mutilada.</div>`;
  }
  return `<div class="campo"><label>referencia_abnt</label>
    <input type="text" id="f_referencia_abnt" value="${esc(v)}" placeholder="(vazia + ficha completa = gerada ao salvar)">
    ${dica}
  </div>`;
}
function renderFicha(){
  const tf = F_CAMPOS.tipo_fonte || '';
  const obrig = (VOCAB.obrigatorios[tf] || []);
  const fixos = ['tipo_fonte','tipo','area','status','confiabilidade','resumo'];
  const campos = [...fixos, ...obrig.filter(c=>!fixos.includes(c)), 'referencia_abnt'];
  fichaForm.innerHTML =
    (tf ? `<p class="sov-dica">obrigatórios de <b>${esc(tf)}</b>: ${obrig.map(esc).join(', ') || '—'}</p>`
        : `<p class="sov-dica">comece pelo <b>tipo_fonte</b> — o formulário abre os campos que ele exige</p>`)
    + campos.map(c => c==='referencia_abnt' ? campoReferencia() : campoFicha(c)).join('');
  document.getElementById('f_tipo_fonte').onchange = (e)=>{
    // preserva o que já foi digitado antes de redesenhar o formulário
    document.querySelectorAll('#fichaForm [id^="f_"]').forEach(el=>{
      if(el.value) F_CAMPOS[el.id.slice(2)] = el.value;
    });
    F_CAMPOS.tipo_fonte = e.target.value || F_CAMPOS.tipo_fonte;
    const sug = VOCAB.tipo_unico[F_CAMPOS.tipo_fonte];
    if(sug && !F_CAMPOS.tipo) F_CAMPOS.tipo = sug;
    renderFicha();
  };
}
async function salvarFicha(){
  const campos = {};
  document.querySelectorAll('#fichaForm [id^="f_"]').forEach(el=>{
    // textarea (resumo): quebras de linha viram espaço — o frontmatter é
    // gravado linha a linha
    const v = el.value ? el.value.replace(/\s*\n\s*/g, ' ').trim() : '';
    if(v) campos[el.id.slice(2)] = v;
  });
  const r = await (await fetch('/api/ficha',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({arquivo:FICHA_ARQ, campos})})).json();
  if(!r.ok){ fsovErros.innerHTML = '<b style="color:var(--err)">✗</b> ' + esc(r.msg||'erro'); return; }
  const falta = (r.faltam_campos||[]);
  const fichaOk = !falta.length && !(r.erros_ficha||[]).length;
  /* Ficha SEM erros → fecha a edição e volta à LISTA (já reagrupada),
     com a confirmação no cabeçalho. Com erros, permanece na edição
     mostrando os destaques do que falta. */
  if(fichaOk){
    fichaEdicao.hidden = true; fichaLista.hidden = false; fVoltar.hidden = true;
    fsovTit.textContent = '📋 Fichas — o que merece atenção';
    const nomeSalvo = FICHA_ARQ; FICHA_ARQ = '';
    await carregarFichas();
    fichasInfo.innerHTML += ` &nbsp;·&nbsp; <span style="color:var(--ok)">✓ ${esc(nomeSalvo)} salvo — ${esc(r.nota)}</span>`;
    estado();
    return;
  }
  /* feedback em DOIS blocos: o que é da ficha × o que é de outra etapa */
  let html = `<div class="fb-bloco"><b class="t" style="color:${fichaOk?'var(--ok)':'var(--err)'}">Ficha</b>`;
  if(fichaOk){
    html += `<span style="color:var(--ok)">✓ completa — nada bloqueia por parte da ficha</span>`;
  } else {
    if(falta.length) html += `<span style="color:var(--err)">✗ preencha: <b>${falta.map(esc).join(', ')}</b> — destacados em vermelho abaixo</span>`;
    (r.erros_ficha||[]).forEach(e=>{
      if(!/campos ABNT vazios/.test(e)) html += `<br><span style="color:var(--err)">✗ ${esc(e)}</span>`;
    });
  }
  html += `</div>`;
  const pend = (r.pendencias_outras_etapas||[]);
  if(pend.length){
    html += `<div class="fb-bloco"><b class="t" style="color:var(--warn)">Outras etapas — não se resolve neste formulário</b>`
      + pend.map(p => p.resolvida
          ? `<span style="color:var(--ok)">✓ ${esc(p.msg.split(' — ')[0].split('.')[0])} — ${esc(p.orientacao)}</span>`
          : `<span style="color:var(--warn)">⤳ ${esc(p.msg.split(' — ')[0])} — ${esc(p.orientacao)}</span>`).join('<br>')
      + `</div>`;
  }
  if((r.avisos||[]).length){
    html += `<div class="fb-bloco" style="opacity:.85"><b class="t" style="color:var(--muted)">Avisos — não bloqueiam nem seguram a ficha</b>`
      + r.avisos.map(a=>`<span style="color:var(--muted)">• ${esc(a)}</span>`).join('<br>') + `</div>`;
  }
  html += `<p class="sov-dica">situação: <b>${esc(r.nota)}</b> · grupo: <b>${esc(r.grupo)}</b> · gravados: ${(r.gravados||[]).map(esc).join(', ')||'—'}</p>`;
  fsovErros.innerHTML = html;
  F_CAMPOS = await (await fetch('/api/ficha?arq='+encodeURIComponent(FICHA_ARQ))).json();
  renderFicha();
  estado();   // card ✎ do trilho reflete o salvamento NA HORA, sem esperar o poll
}
function fecharFicha(){
  fsovBg.classList.remove('on'); fsov.classList.remove('on');
  estado();   // contadores do card ✎ atualizados ao sair da mesa
}

/* ---------- preencher fichas com IA: prompt → resposta → aplicar/undo ---------- */
let IA_PROMPT = '';
async function abrirIA(){
  iaBg.classList.add('on');
  iaResultado.innerHTML = '';
  iaInfo.textContent = 'gerando o prompt…';
  const d = await (await fetch('/api/ia_prompt')).json();
  IA_PROMPT = d.prompt || '';
  iaPrompt.value = IA_PROMPT;
  iaInfo.textContent = d.pendentes
    ? d.pendentes + ' ficha(s) pendente(s) no prompt'
    : 'nenhuma ficha pendente — nada a pedir à IA 🎉';
}
function fecharIA(){ iaBg.classList.remove('on'); }
async function aplicarIA(){
  const resposta = iaResposta.value.trim();
  if(!resposta){ iaResultado.innerHTML = '<span class="err">cole a resposta da IA antes de aplicar.</span>'; return; }
  iaResultado.textContent = 'validando e aplicando…';
  const r = await (await fetch('/api/ia_aplicar',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({resposta})})).json();
  if(!r.ok){ iaResultado.innerHTML = '<span class="err">✗ ' + esc(r.msg) + '</span>'; return; }
  let html = '';
  if(r.aplicadas.length){
    html += `<div class="fb-bloco"><b class="t" style="color:var(--ok)">✔ Aplicadas (${r.aplicadas.length}) — backup feito; ↩ desfaz</b>`
      + r.aplicadas.map(a=>`<span>✓ ${esc(a.arquivo)} → <b>${esc(a.nota)}</b> (${esc((a.gravados||[]).join(', '))})</span>`).join('<br>') + '</div>';
  }
  if(r.rejeitadas.length){
    html += `<div class="fb-bloco"><b class="t" style="color:var(--err)">✗ Rejeitadas (${r.rejeitadas.length}) — nada foi alterado nelas</b>`
      + r.rejeitadas.map(x=>`<span class="err">✗ ${esc(x.arquivo)} — ${esc(x.motivo)}</span>`).join('<br>') + '</div>';
  }
  if(r.avisos.length){
    html += `<div class="fb-bloco" style="opacity:.85"><b class="t" style="color:var(--warn)">⚠ Campos ignorados na validação</b>`
      + r.avisos.map(a=>`<span style="color:var(--warn)">• ${esc(a)}</span>`).join('<br>') + '</div>';
  }
  iaResultado.innerHTML = html || 'nada aplicado.';
  estado(); carregarFichas();
}
async function reverterIA(){
  iaResultado.textContent = 'revertendo…';
  const r = await (await fetch('/api/ia_reverter',{method:'POST',
    headers:{'Content-Type':'application/json'}, body:'{}'})).json();
  iaResultado.innerHTML = r.ok
    ? `<div class="fb-bloco"><b class="t" style="color:var(--ok)">↩ Revertido</b>` +
      r.restaurados.map(esc).join('<br>') + '</div>'
    : '<span class="err">✗ ' + esc(r.msg) + '</span>';
  estado();
}

/* ---------- relatório de auditoria: triagem do grave ao irrelevante ---------- */
async function abrirAuditoria(){
  asovBg.classList.add('on'); asov.classList.add('on');
  asovInfo.textContent = 'auditando cada arquivo…';
  asovItens.innerHTML = '';
  const pasta = (typeof audp !== 'undefined' && audp.value) ? audp.value : '';
  const d = await (await fetch('/api/auditoria?pasta='+encodeURIComponent(pasta))).json();
  if(!d.itens.length && !d.fatias.length){
    asovInfo.textContent = 'Nada para auditar em ' + d.pasta + ' — converta antes (etapa 3).';
    return;
  }
  const graves   = d.itens.filter(f=>f.grupo==='corrigir');
  const atencao  = d.itens.filter(f=>f.grupo==='conferir');
  const soAvisos = d.itens.filter(f=>f.grupo==='pronta' && (f.avisos||[]).length);
  const limpos   = d.itens.filter(f=>f.grupo==='pronta' && !(f.avisos||[]).length);
  asovInfo.innerHTML = `<b>${d.itens.length}</b> arquivo(s)-mestre — ` +
    `<span style="color:var(--err)">${graves.length} graves</span> · ` +
    `<span style="color:var(--warn)">${atencao.length} p/ conferir</span> · ` +
    `${soAvisos.length} só avisos · <span style="color:var(--ok)">${limpos.length} ok</span>` +
    (d.fatias.length ? ` · ${d.fatias.length} obra(s) fatiadas` : '');
  const acaoDe = f => {
    const a = [];
    if(f.faltam_campos.length)
      a.push(`preencha <b>${f.faltam_campos.map(esc).join(', ')}</b>`);
    f.erros_ficha.forEach(e=>{
      if(/tipo_fonte/.test(e)) a.push('defina o <b>tipo_fonte</b>');
      else if(/referencia_abnt/.test(e)) a.push('complete a ficha — a referência é gerada ao salvar');
    });
    const como = d.eh_bruto
      ? ` → <button class="bnav" onclick="editarDaAuditoria(${q(f.arquivo)})">✎ Corrigir ficha</button>`
      : ' → corrija o mestre no <b>2-MARKDOWN-BRUTO</b> (mesa ✎) e refatie (etapa 5)';
    return a.length ? `<br><span class="err">AÇÃO: ${[...new Set(a)].join('; ')}</span>${como}` : '';
  };
  const item = (f, nivel) => `<div class="fitem">
      <div class="fnome"><span>${esc(f.arquivo)}</span><span class="pill ${nivel}">${esc(f.nota)}</span></div>
      <div class="fdet">
        ${f.erros_ficha.map(e=>`<span class="err">✗ ${esc(e)}</span>`).join('<br>')}
        ${acaoDe(f)}
        ${f.pendencias_outras_etapas.map(p=>p.resolvida
            ? `<br><span class="pok">✓ ${esc(p.msg.split(' — ')[0].split('.')[0])} — ${esc(p.orientacao)}</span>`
            : `<br><span class="rev">⤳ AÇÃO: ${esc(p.msg.split(' — ')[0])} — ${esc(p.orientacao)}</span>`).join('')}
        ${f.revisar.length?`<br><span class="rev">⚠ confirme: ${f.revisar.map(esc).join(' · ')}</span>`:''}
        ${(f.avisos||[]).length?`<br><span style="opacity:.7">irrelevante p/ publicar: ${f.avisos.map(esc).join(' · ')}</span>`:''}
      </div></div>`;
  const grupo = (t, cls, arr, nivel) => arr.length
    ? `<div class="fgrupo ${cls}">${t} (${arr.length})</div>` + arr.map(f=>item(f, nivel)).join('') : '';
  const fat = d.fatias.length
    ? `<div class="fgrupo">Fatias, por obra (${d.fatias.length})</div>` + d.fatias.map(g=>`
        <div class="fitem"><div class="fnome"><span>${esc(g.obra)}</span>
          <span class="pill ${g.reprovadas?'no':'ok'}">${g.total} fatias</span></div>
        <div class="fdet">${g.reprovadas
            ? `<span class="err">✗ ${g.reprovadas} reprovada(s) — ${esc(g.exemplo)}</span><br><span class="err">AÇÃO: corrija a ficha do mestre (mesa ✎) e refatie (etapa 5) — as fatias herdam</span>`
            : `<span class="pok">✓ nenhuma reprovada</span>`}${g.parciais?` · <span style="opacity:.7">${g.parciais} com avisos</span>`:''}</div></div>`).join('')
    : '';
  asovItens.innerHTML =
      grupo('✗ GRAVE — bloqueiam a publicação', 'err', graves, 'no')
    + grupo('⚠ CONFERIR — decisão sua pendente', 'warn', atencao, 'sim')
    + grupo('Só avisos — irrelevantes para publicar', '', soAvisos, 'ok')
    + grupo('✓ OK — nada a fazer', 'ok', limpos, 'ok')
    + fat;
}
function fecharAuditoria(){ asovBg.classList.remove('on'); asov.classList.remove('on'); }
function editarDaAuditoria(arq){
  fecharAuditoria();
  fsovBg.classList.add('on'); fsov.classList.add('on');
  abrirFicha(arq);
}
/* Trava de reexecução: refazer uma etapa CONCLUÍDA reprocessa e pode
   sobrescrever — só com confirmação consciente. (Simular/dry não pede.) */
const ETAPA_DA_ACAO = {triagem:'e1', ocr:'e2', paginar:'e3', limpar:'e4',
                       fatiar:'e5', qualidade:'e6', validar:'e6', auditar:'e6',
                       publicar:'e8', auditar_vault:'e9', radar:'e10'};
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

/* ---------- progresso da etapa em execução (dentro do card) ---------- */
const CARD_DA_ACAO = Object.assign(
  {arquivo:'e3', corrigir_idioma:'e4', normalizar:'e5'}, ETAPA_DA_ACAO);
const cardProg = document.createElement('div');
cardProg.className = 'etprog';
function renderProg(j){
  const cardId = (j.running && CARD_DA_ACAO[j.action]) || '';
  if(!cardId){ cardProg.remove(); return; }
  const alvo = document.querySelector('#'+cardId+' .conteudo');
  if(alvo && cardProg.parentElement !== alvo) alvo.appendChild(cardProg);
  // 1ª linha do log é o comando ($ ...) — contém os marcadores e enganaria a barra
  const lg = (j.log || '').split('\n').slice(1).join('\n');
  const ms = [...lg.matchAll(/\[(\d+)\/(\d+)\]\s*([^\n]*)/g)];
  let html;
  if(ms.length){
    const m = ms[ms.length-1], at = +m[1], tot = +m[2];
    const arq = (m[3]||'').split(' ... ')[0].split(' | ')[0].trim();
    // sinal de vida do OCR: quanto tempo o arquivo ATUAL está levando
    const trecho = lg.slice(lg.lastIndexOf(m[0]));
    const hb = [...trecho.matchAll(/OCR em andamento ha (\S+)/g)];
    const extra = hb.length ? ' · ' + hb[hb.length-1][1] + ' neste arquivo' : '';
    const nOk = (lg.match(/OK -> /g)||[]).length;
    const nFa = (lg.match(/FALHOU \(rc=/g)||[]).length;
    const saldo = (nOk||nFa) ? ` &nbsp;·&nbsp; <span style="color:var(--ok)">✓ ${nOk}</span>`
                    + (nFa?` · <span style="color:var(--err)">✗ ${nFa}</span>`:'') : '';
    html = `<div class="ptxt"><span class="spin"></span>
        <span class="parq">processando <b>${at}/${tot}</b> — ${esc(arq)}${esc(extra)}</span>${saldo}</div>
      <div class="pbar"><div class="pfill" style="width:${Math.round(100*(at-.5)/tot)}%"></div></div>`;
  } else {
    html = `<div class="ptxt"><span class="spin"></span> em execução — o log corre na seção 02</div>`;
  }
  if(cardProg.innerHTML !== html) cardProg.innerHTML = html;
  const st = document.getElementById('s'+cardId.slice(1));
  if(st){ st.textContent = '⏳ executando'; st.className = 'st pend'; }
}

let JOB_RODANDO = false;   // detecta a transição rodando→terminou (auto-abrir relatório)

/* ---------- trilho: estado de cada etapa ---------- */
function marcar(id, estadoEt, texto, classe){
  const et = document.getElementById(id);
  if(!et) return;   // etapa que deixou de existir (fusão da Qualidade)
  et.className = 'et ' + estadoEt;
  const st = document.getElementById('s' + id.slice(1));
  st.textContent = texto;
  st.className = 'st ' + (classe||'');
}
function atualizarTrilho(p, temRoot){
  if(!temRoot){
    for(let i=1;i<=10;i++) marcar('e'+i,'bloq','defina a pasta','');
    marcar('ef','bloq','defina a pasta','');
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
  // 6 qualidade (fusão validar+auditar — v3.16)
  if(!p.bruto)          marcar('e6','bloq','converta antes','');
  else if(p.auditado)   marcar('e6','feito','relatório gerado'+dt('auditado'),'ok');
  else                  marcar('e6','ativa','pronto','pend');
  // ✎ fichas — saneamento humano (contadores do resumo cacheado no servidor).
  // As PRONTAS aparecem sempre: é o que mostra o progresso — sem elas,
  // "12 corrigir" parado esconde que uma ficha acabou de ficar pronta.
  const fi = p.fichas || {};
  if(!p.bruto){ marcar('ef','bloq','converta antes',''); }
  else if(fi.corrigir || fi.conferir){
    const partes = [];
    if(fi.corrigir) partes.push(fi.corrigir+' corrigir');
    if(fi.conferir) partes.push(fi.conferir+' conferir');
    partes.push((fi.prontas||0)+' prontas ✓');
    marcar('ef','ativa', partes.join(' · '),'pend');
  }
  else                  marcar('ef','feito', (fi.prontas||0)+' prontas','ok');
  // 7(dot) publicar — prontidão REAL: auditoria da camada-1 + staleness.
  // "N arquivos no limpo" mentia: reprovada não publica, fatia fica retida.
  const pb = p.pub || {};
  const pendPub = (pb.reprovadas||0) + (pb.desatualizadas||0) + (pb.fora_do_limpo||0);
  const pp = [];
  if(pb.prontas)        pp.push(pb.prontas+' obra(s) prontas ✓');
  if(pb.reprovadas)     pp.push(pb.reprovadas+' reprovadas → ✎ fichas');
  if(pb.desatualizadas) pp.push(pb.desatualizadas+' desatualizadas → refatie (5)');
  if(pb.fora_do_limpo)  pp.push(pb.fora_do_limpo+' fora do limpo → fatie (5)');
  const txtPub = pp.join(' · ') || (p.limpo_md + ' no limpo');
  if(!p.limpo_md)               marcar('e8','bloq','prepare 3-MARKDOWN-LIMPO','');
  else if(p.publicado && !pendPub) marcar('e8','feito', txtPub+dt('publicado'),'ok');
  else                          marcar('e8','ativa', txtPub, pendPub?'pend':'ok');
  // 9 auditar vault (grafo)
  if(!p.vault)              marcar('e9','bloq','publique o vault antes','');
  else if(p.vault_auditado) marcar('e9','feito','grafo auditado'+dt('vault_auditado'),'ok');
  else                      marcar('e9','ativa', p.vault+' notas no vault','pend');
  // 10 radar (manutenção contínua)
  if(!p.vault)              marcar('e10','bloq','publique o vault antes','');
  else if(!p.radar)         marcar('e10','bloq','sem achados em Radar/ (Módulo E)','');
  else if(p.radar_novos)    marcar('e10','ativa', p.radar_novos+' achado(s) novo(s)','pend');
  else                      marcar('e10','feito','radar em dia'+dt('radar'),'ok');
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
  // auditoria concluída → o relatório-triagem abre sozinho no slideover
  if(JOB_RODANDO && !j.running && j.rc !== null
     && (j.action === 'qualidade' || j.action === 'auditar')){
    abrirAuditoria();
  }
  JOB_RODANDO = j.running;
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

  const falta = s.diag.filter(d=>!d.ok).length;
  btnAmb.className = 'bamb ' + (falta ? 'falta' : 'ok');
  btnAmb.textContent = falta ? `⚙ Ambiente — ${falta} pendência${falta>1?'s':''}` : '⚙ Ambiente ✓';

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

    // card OCR concluído: diz O QUE aconteceu, não só "nada pendente"
    if(document.getElementById('e2').className.includes('feito')){
      const fez = s.csv.filter(r=>r.ocr_status==='ok'||r.ocr_status==='ja_existia').length;
      const ja  = s.csv.filter(r=>r.ocr_status==='nao_necessario').length;
      marcar('e2','feito', `${ja} já pesquisáveis · ${fez} OCRizados`, 'ok');
    }
  }

  renderProg(j);
}
renderFila();
estado(); setInterval(estado, 1500);
</script>
"""


def main():
    ap = argparse.ArgumentParser(description="Painel do Acervo (WSL2)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--root", default=None, help="pasta do acervo (Windows ou WSL)")
    ap.add_argument("--scripts", default=None,
                    help="pasta com aplicar_ocr.sh e os .py")
    ap.add_argument("--venv", default=None)
    a = ap.parse_args()

    # Retomada: config salvo entra primeiro; arg explícito da CLI vence;
    # o que sobrar vazio cai nos defaults embutidos.
    CFG.update(carregar_config())
    if a.root is not None:
        CFG["root"] = win_para_wsl(a.root) if a.root else ""
    if a.scripts is not None:
        CFG["scripts"] = win_para_wsl(a.scripts)
    if a.venv is not None:
        CFG["venv"] = win_para_wsl(a.venv)
    if not CFG["scripts"]:
        CFG["scripts"] = str(Path(__file__).resolve().parent)
    if not CFG["venv"]:
        CFG["venv"] = str(Path.home() / "venvs/acervo")
    if CFG["root"] and not Path(CFG["root"]).is_dir():
        print(f"AVISO: pasta do acervo salva não existe mais: {CFG['root']}")
        CFG["root"] = ""

    try:
        srv = ThreadingHTTPServer(("0.0.0.0", a.port), Handler)
    except OSError as e:
        if e.errno == 98:  # EADDRINUSE — quase sempre é o próprio painel já aberto
            sys.exit(
                f"\nA porta {a.port} já está em uso — o painel provavelmente JÁ "
                f"está no ar.\n"
                f"  · Abra no navegador: http://localhost:{a.port}\n"
                f"  · Para reiniciar (ex.: após atualizar): feche a janela "
                f"anterior ou rode\n"
                f"      pkill -f acervo_app.py\n"
                f"    e execute de novo.\n"
                f"  · Ou suba em outra porta: python3 acervo_app.py --port "
                f"{a.port + 1}\n")
        raise
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

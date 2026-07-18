#!/usr/bin/env python3
"""
conectar.py — FASE 5b: costura o grafo do vault ligando obras entre si.

O pipeline publica cada obra como uma estrela isolada (índice ⇄ fatias);
o graph view do Obsidian mostra arquipélago, não cérebro. Este script cria
as pontes POR REGRA, a partir dos identificadores fortes que as obras
citam (lei, decreto, MP, emenda, tema repetitivo, súmula, processo —
os mesmos padrões do radar):

  1. RELAÇÕES — bloco "🔗 Relações (auto)" no índice de cada obra, entre
     marcadores `conectar:auto` (pacto do moc:auto: regenerável, e tudo
     FORA dos marcadores é curadoria intocável). Ranking por raridade
     (IDF): identificador citado por mais da metade das obras não pontua
     — evita que o CTN ligue tudo a tudo num vault tributário.
  2. HUBS — nota por norma "marco" em 00-Indices-MOCs/Conexoes/
     (Lei-5172.md, Sumula-435.md): identificador citado por muitas obras
     OU listado em `normas_notaveis` do perfil. O hub linka cada obra
     citante e as 3 fatias mais densas — do grafo à página exata.
  3. CATÁLOGO — 00-Indices-MOCs/CATALOGO.md: o mapa que uma IA lê
     primeiro (obra → wikilink, ficha, normas distintivas, resumo).

Garantias: idempotente (re-rodar sem mudança = zero escrita), nada é
apagado (hub obsoleto vira item de relatório), colisão de nome nunca
sobrescreve nota do usuário, falha de disco num arquivo não aborta o
lote (9p do WSL2 sob carga). Fatias NUNCA recebem bloco — a ligação é
no nível da obra.

Uso:
    python3 conectar.py <vault>            # relações + hubs + catálogo
    python3 conectar.py <vault> --dry      # só mostra o plano; não grava
    python3 conectar.py <vault> --top 8 --min-peso 2.0
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import frontmatter
import radar
import taxonomia
from comum import (CONECTAR_FIM, CONECTAR_INI, IGNORAR_PASTAS,
                   RE_BLOCO_CONECTAR, alvo_wikilink, vazio)

PASTA_CONEXOES = Path("00-Indices-MOCs") / "Conexoes"
ARQ_CACHE = ".conectar_cache.json"
ARQ_CATALOGO = Path("00-Indices-MOCs") / "CATALOGO.md"
ARQ_RELATORIO = "RELATORIO-CONEXOES.md"

# nome de arquivo do hub: estável pelo identificador, nunca pelo apelido
# (renomear o título na taxonomia não pode quebrar wikilink)
ROTULO_ARQUIVO = {"lei": "Lei", "decreto": "Decreto", "mp": "MP",
                  "emenda": "EC", "tema": "Tema", "sumula": "Sumula",
                  "processo": "Processo"}


def contar_ids(texto: str) -> Counter:
    """Como radar.identificadores(), mas contando MENÇÕES — o nº de vezes
    entra no ranking das relações e na escolha das fatias de precisão."""
    c = Counter()
    for rotulo, rx in radar.PADROES:
        for m in rx.finditer(texto):
            valor = re.sub(r"\D", "", m.group(1))
            if valor:
                c[(rotulo, valor)] += 1
    return c


def fmt_ident(ident) -> str:
    """(lei, 10833) → 'Lei 10.833' — pontuação de milhar na exibição
    (o processo CNJ fica como está)."""
    rotulo, num = ident
    if rotulo == "processo" or len(num) <= 3:
        return radar.rotular(ident)
    pontuado = ""
    for i, d in enumerate(reversed(num)):
        if i and i % 3 == 0:
            pontuado = "." + pontuado
        pontuado = d + pontuado
    return f"{radar.rotular((rotulo, ''))[:-1]} {pontuado}"


def hub_stem(ident) -> str:
    return f"{ROTULO_ARQUIVO.get(ident[0], ident[0].capitalize())}-{ident[1]}"


def _alias(fm: dict, stem: str) -> str:
    t = str(fm.get("titulo") or "").strip().strip('"')
    return t.replace("|", "/").replace("]]", "").strip() or stem


# ---------------------------------------------------------------------------
# Varredura do vault (com cache: no 9p do WSL2, stat é barato e read é caro)
# ---------------------------------------------------------------------------
def carregar_cache(vault: Path) -> dict:
    try:
        return json.loads((vault / PASTA_CONEXOES / ARQ_CACHE)
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def gravar_cache(vault: Path, cache: dict) -> None:
    try:
        destino = vault / PASTA_CONEXOES / ARQ_CACHE
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass   # cache é otimização; falhar em gravá-lo não é problema


def obras_do_vault(vault: Path, cache: dict, usar_cache=True):
    """Agrega as fatias na sua obra (via campo `obra:`) e devolve
    (obras, stems_vault, stats). obras[stem] = {path, fm, texto,
    ids: Counter, fatias: {stem_fatia: Counter}}."""
    obras, soltas = {}, []
    stems_vault = {}          # stem → caminho relativo (p/ colisão de hub)
    stats = {"notas": 0, "orfas": 0, "cache_hits": 0, "falhas": []}

    arquivos = sorted(vault.rglob("*.md"))
    for i, p in enumerate(arquivos, 1):
        if any(parte in IGNORAR_PASTAS for parte in p.parts):
            continue
        rel = str(p.relative_to(vault))
        stems_vault.setdefault(p.stem, rel)
        if p.name.startswith(("RELATORIO", "_")) or p.name == "CATALOGO.md":
            continue
        stats["notas"] += 1
        if i % 400 == 0:
            print(f"  · varrendo {i}/{len(arquivos)}", flush=True)
        try:
            st = p.stat()
        except OSError as e:
            stats["falhas"].append(f"{rel} — {e.strerror or e}")
            continue
        ent = cache.get(rel) if usar_cache else None
        if ent and ent[0] == st.st_mtime_ns and ent[1] == st.st_size:
            if ent[2] == "ignorar":
                stats["cache_hits"] += 1
                continue
            if ent[2] == "fatia":
                stats["cache_hits"] += 1
                soltas.append((ent[3], p.stem,
                               Counter({(r, n): c for r, n, c in ent[4]})))
                continue
            # "nota" (obra): relê mesmo com cache — precisa do frontmatter
            # rico para catálogo/alias, e são poucas dezenas de arquivos
        try:
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            stats["falhas"].append(f"{rel} — {e.strerror or e}")
            continue
        fm = frontmatter.ler(texto).campos
        if str(fm.get("tipo") or "") == "MOC" or not vazio(fm.get("hub_id")):
            cache[rel] = [st.st_mtime_ns, st.st_size, "ignorar", "", []]
            continue
        # o próprio bloco de relações cita identificadores (as provas):
        # extrair SEM ele, senão cada rodada realimenta as contagens
        ids = contar_ids(RE_BLOCO_CONECTAR.sub("", texto))
        if not vazio(fm.get("parte")) and not vazio(fm.get("obra")):
            alvo = alvo_wikilink(fm.get("obra"))
            cache[rel] = [st.st_mtime_ns, st.st_size, "fatia", alvo,
                          [[r, n, c] for (r, n), c in sorted(ids.items())]]
            soltas.append((alvo, p.stem, ids))
        else:
            cache[rel] = [st.st_mtime_ns, st.st_size, "nota", "", []]
            obras[p.stem] = {"path": p, "fm": fm, "texto": texto,
                             "ids": Counter(ids), "fatias": {}}

    for alvo, stem_fatia, ids in soltas:
        ob = obras.get(alvo)
        if ob is None:
            stats["orfas"] += 1      # fatia órfã é caso do auditar_vault
            continue
        ob["fatias"][stem_fatia] = ids
        ob["ids"].update(ids)
    return obras, stems_vault, stats


# ---------------------------------------------------------------------------
# Correlação obra↔obra por raridade (IDF) e eleição de hubs
# ---------------------------------------------------------------------------
def correlacionar(obras: dict, top: int, min_peso: float):
    """rels[stem] = [(peso, n_comuns, stem_alvo, ids_prova), ...] (top-K).
    Identificador citado por mais da metade das obras não pontua relação
    direta (é ubíquo — o lugar dele é o hub)."""
    N = len(obras)
    df = Counter()
    for ob in obras.values():
        for ident in ob["ids"]:
            df[ident] += 1
    corte_df = math.ceil(N / 2)
    stems = sorted(obras)
    rels = {s: [] for s in stems}
    for i, a in enumerate(stems):
        for b in stems[i + 1:]:
            comuns = [x for x in obras[a]["ids"].keys() & obras[b]["ids"].keys()
                      if df[x] <= corte_df]
            if not comuns:
                continue
            peso = sum(math.log(N / df[x]) for x in comuns)
            if peso < min_peso:
                continue
            prova = sorted(comuns, key=lambda x: (df[x], x))[:5]
            rels[a].append((peso, len(comuns), b, prova))
            rels[b].append((peso, len(comuns), a, prova))
    for s in stems:
        rels[s] = sorted(rels[s], key=lambda t: (-t[0], t[2]))[:top]
    return rels, df


def hubs_elegiveis(obras: dict, df: Counter) -> dict:
    """ident → título. Corte por difusão (≥ max(4, 10% das obras)) OU
    norma notável do perfil (marco ganha hub mesmo com poucas citações)."""
    corte = max(4, math.ceil(0.10 * max(1, len(obras))))
    notaveis = taxonomia.PERFIL_ATIVO.normas_notaveis
    hubs = {}
    for ident, n in df.items():
        chave = (ident[0], ident[1])
        if n >= corte or chave in notaveis:
            hubs[ident] = notaveis.get(chave) or fmt_ident(ident)
    return hubs


# ---------------------------------------------------------------------------
# Geração dos blocos e arquivos
# ---------------------------------------------------------------------------
def bloco_relacoes(stem: str, obras: dict, rels: dict, hubs: dict) -> str:
    ob = obras[stem]
    linhas = []
    for peso, n_comuns, alvo, prova in rels.get(stem, []):
        provas = " · ".join(fmt_ident(x) for x in prova)
        linhas.append(f"- [[{alvo}|{_alias(obras[alvo]['fm'], alvo)}]] — "
                      f"{n_comuns} referência(s) em comum ({provas})")
    marcos = sorted((h for h in hubs if ob["ids"].get(h)),
                    key=lambda h: (-ob["ids"][h], hub_stem(h)))
    if not linhas and not marcos:
        return ""
    corpo = [CONECTAR_INI, "## 🔗 Relações (auto)", ""]
    if linhas:
        corpo += ["Obras deste vault que compartilham normas e precedentes "
                  "com esta:", ""] + linhas
    if marcos:
        if linhas:
            corpo.append("")
        corpo.append("Marcos citados: "
                     + " · ".join(f"[[{hub_stem(h)}]]" for h in marcos))
    corpo.append(CONECTAR_FIM)
    return "\n".join(corpo)


def aplicar_bloco(ob: dict, bloco: str, dry: bool) -> str:
    """Regenera entre marcadores ou anexa ao FIM (curadoria intocada).
    → 'gravado' | 'ja' | 'pulado' | 'falha: ...'"""
    texto = ob["texto"]
    tem_marcador = RE_BLOCO_CONECTAR.search(texto) is not None
    if not bloco:
        if not tem_marcador:
            return "pulado"          # nada a dizer e nada a atualizar
        bloco = "\n".join([CONECTAR_INI, "## 🔗 Relações (auto)", "",
                           "_Nenhuma relação detectada nesta rodada._",
                           CONECTAR_FIM])
    if tem_marcador:
        novo = RE_BLOCO_CONECTAR.sub(lambda _: bloco, texto, count=1)
    else:
        novo = texto.rstrip("\n") + "\n\n" + bloco + "\n"
    if novo == texto:
        return "ja"
    if dry:
        return "gravado"
    try:
        ob["path"].write_text(novo, encoding="utf-8")
    except OSError as e:
        return f"falha: {e.strerror or e}"
    return "gravado"


def corpo_hub_bloco(ident, citantes, obras) -> str:
    """citantes = [(stem_obra, mencoes)] já ordenado por menções desc."""
    linhas = [CONECTAR_INI, f"## Obras que citam ({len(citantes)})", ""]
    for stem, mencoes in citantes:
        ob = obras[stem]
        precisao = [s for s, c in sorted(
            ob["fatias"].items(),
            key=lambda kv: (-kv[1].get(ident, 0), kv[0]))
            if c.get(ident)][:3]
        ver = (" · ver: " + " · ".join(f"[[{s}]]" for s in precisao)
               if precisao else "")
        linhas.append(f"- [[{stem}|{_alias(ob['fm'], stem)}]] — "
                      f"{mencoes} menção(ões){ver}")
    linhas.append(CONECTAR_FIM)
    return "\n".join(linhas)


def gerar_hub(vault, ident, titulo, obras, stems_vault, dry) -> tuple:
    """→ ('criado'|'atualizado'|'ja'|'colisao'|'sem_marcador'|'falha', detalhe)"""
    stem = hub_stem(ident)
    destino = vault / PASTA_CONEXOES / f"{stem}.md"
    rel_destino = str(destino.relative_to(vault))
    ja_em = stems_vault.get(stem)
    if ja_em and ja_em != rel_destino:
        return "colisao", f"{stem} — nome já existe em {ja_em}; hub não criado"

    citantes = sorted(((s, ob["ids"][ident]) for s, ob in obras.items()
                       if ob["ids"].get(ident)),
                      key=lambda t: (-t[1], t[0]))
    bloco = corpo_hub_bloco(ident, citantes, obras)

    if destino.exists():
        try:
            texto = destino.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return "falha", f"{stem} — {e.strerror or e}"
        if not RE_BLOCO_CONECTAR.search(texto):
            return "sem_marcador", (f"{stem} — existe sem marcadores "
                                    "conectar:auto; não toco (curadoria)")
        novo = RE_BLOCO_CONECTAR.sub(lambda _: bloco, texto, count=1)
        if novo == texto:
            return "ja", stem
        if not dry:
            try:
                destino.write_text(novo, encoding="utf-8")
            except OSError as e:
                return "falha", f"{stem} — {e.strerror or e}"
        return "atualizado", stem

    titulo_fm = str(titulo).replace('"', "'")
    conteudo = "\n".join([
        "---",
        f'titulo: "{titulo_fm}"',
        "tipo: MOC",
        f'hub_id: "{ident[0]}:{ident[1]}"',
        'finalidade: "Hub de conexão — obras que citam esta norma/precedente '
        '(gerado por conectar.py)"',
        "---",
        "",
        f"# {titulo}",
        "",
        bloco,
        "",
        "## Notas (curadoria manual)",
        "",
        "_Anote aqui a sua leitura desta norma — o conectar.py nunca toca "
        "fora dos marcadores._",
        ""])
    if not dry:
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(conteudo, encoding="utf-8")
        except OSError as e:
            return "falha", f"{stem} — {e.strerror or e}"
    return "criado", stem


def _resumo_curto(fm: dict) -> str:
    r = str(fm.get("resumo") or fm.get("ementa") or "").strip()
    return " ".join(r.split()) or "(sem resumo)"


def gerar_catalogo(vault, obras, df, dry) -> str:
    L = ["---", 'titulo: "Catálogo do acervo"', "tipo: MOC",
         'finalidade: "Mapa de entrada do vault para IAs e humanos '
         '(gerado por conectar.py)"', "---", "",
         "# 📇 Catálogo do acervo", "",
         "> **Como usar (inclusive por IA):** leia este catálogo primeiro; "
         "abra a nota-índice da obra escolhida; só então vá às fatias "
         "(`_pNN`). As âncoras `{{p.NN}}` no texto dão a página exata para "
         "citação ABNT. Gerado por `conectar.py` — regenerável; não edite.",
         ""]
    for stem in sorted(obras, key=lambda s: _alias(obras[s]["fm"], s).casefold()):
        ob, fm = obras[stem], obras[stem]["fm"]
        L.append(f"## {_alias(fm, stem)}")
        L.append(f"- nota: [[{stem}]]")
        ficha = []
        for rotulo, campo in (("autoria", "autoria"), ("ano", "ano"),
                              ("tipo", "tipo"), ("área", "area"),
                              ("status", "status"), ("partes", "partes")):
            v = fm.get(campo)
            if not vazio(v):
                if isinstance(v, list):
                    v = "; ".join(str(x) for x in v)
                ficha.append(f"{rotulo}: {v}")
        if ficha:
            L.append("- " + " · ".join(ficha))
        ref = str(fm.get("referencia_abnt") or "").strip()
        if ref:
            L.append(f"- referência: {ref}")
        raras = sorted(ob["ids"], key=lambda x: (df[x], -ob["ids"][x], x))[:10]
        if raras:
            L.append("- normas mais distintivas: "
                     + ", ".join(fmt_ident(x) for x in raras))
        L.append(f"- resumo: {_resumo_curto(fm)}")
        L.append("")
    conteudo = "\n".join(L)
    destino = vault / ARQ_CATALOGO
    try:
        if destino.exists() and destino.read_text(
                encoding="utf-8", errors="replace") == conteudo:
            return "ja"
        if not dry:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(conteudo, encoding="utf-8")
    except OSError as e:
        return f"falha: {e.strerror or e}"
    return "gravado"


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------
def conectar(vault: Path, dry=False, top=8, min_peso=2.0, sem_hubs=False,
             sem_relacoes=False, sem_catalogo=False, sem_cache=False) -> int:
    modo = "DRY-RUN — nada gravado" if dry else "execução efetiva"
    print(f"\n{'=' * 72}\nCONECTAR — {vault}  ({modo})\n{'=' * 72}", flush=True)

    cache = {} if sem_cache else carregar_cache(vault)
    obras, stems_vault, stats = obras_do_vault(vault, cache,
                                               usar_cache=not sem_cache)
    if not obras:
        print("Nenhuma obra no vault — publique antes (Fase 5).")
        return 1
    rels, df = correlacionar(obras, top, min_peso)
    hubs = {} if sem_hubs else hubs_elegiveis(obras, df)

    compartilhados = sum(1 for n in df.values() if n >= 2)
    print(f"{len(obras)} obra(s) · {stats['notas']} nota(s) · "
          f"{len(df)} identificador(es), {compartilhados} compartilhado(s) · "
          f"cache: {stats['cache_hits']} hit(s)")

    r = Counter()
    detalhes = {"relacoes": [], "hubs": [], "colisoes": [], "isoladas": [],
                "falhas": list(stats["falhas"]), "obsoletos": []}

    # ── hubs PRIMEIRO: a linha "Marcos citados" dos índices só pode
    # apontar para hub que existe de verdade (colisão de nome com nota
    # do usuário tiraria o link do rumo) ──
    hubs_visiveis = {}
    for ident in sorted(hubs, key=hub_stem):
        acao, det = gerar_hub(vault, ident, hubs[ident], obras,
                              stems_vault, dry)
        if acao == "falha":
            r["falha_disco"] += 1
            detalhes["falhas"].append(det)
            continue
        r[f"hub_{acao}"] += 1
        if acao in ("criado", "atualizado"):
            detalhes["hubs"].append(f"{det} ({acao})")
        elif acao == "sem_marcador":
            detalhes["colisoes"].append(det)   # informativo: não tocamos
        if acao == "colisao":
            detalhes["colisoes"].append(det)
        else:
            hubs_visiveis[ident] = hubs[ident]

    # ── relações nos índices ──
    if not sem_relacoes:
        for stem in sorted(obras):
            bloco = bloco_relacoes(stem, obras, rels, hubs_visiveis)
            res = aplicar_bloco(obras[stem], bloco, dry)
            if res.startswith("falha"):
                r["falha_disco"] += 1
                detalhes["falhas"].append(f"{stem} — {res[7:]}")
                continue
            r[f"rel_{res}"] += 1
            if res == "gravado":
                n = len(rels.get(stem, []))
                marcos = sum(1 for h in hubs_visiveis
                             if obras[stem]["ids"].get(h))
                detalhes["relacoes"].append(
                    f"{stem} — {n} relação(ões), {marcos} marco(s)")

    # hub que existia e saiu do corte: lista, NUNCA apaga
    pasta_hubs = vault / PASTA_CONEXOES
    if pasta_hubs.is_dir():
        esperados = {hub_stem(i) for i in hubs}
        for p in sorted(pasta_hubs.glob("*.md")):
            if p.stem not in esperados:
                detalhes["obsoletos"].append(p.stem)

    # ── catálogo ──
    if not sem_catalogo:
        res = gerar_catalogo(vault, obras, df, dry)
        if res.startswith("falha"):
            r["falha_disco"] += 1
            detalhes["falhas"].append(f"CATALOGO.md — {res[7:]}")
        else:
            r[f"catalogo_{res}"] += 1

    # obras sem nenhum identificador: só a fase de temas as conecta
    for stem in sorted(obras):
        if not obras[stem]["ids"]:
            detalhes["isoladas"].append(stem)

    # ── console ──
    rotulos = (("rel_gravado", "relações gravadas"),
               ("rel_ja", "relações já atualizadas"),
               ("rel_pulado", "sem relação (sem bloco)"),
               ("hub_criado", "hubs criados"),
               ("hub_atualizado", "hubs atualizados"),
               ("hub_ja", "hubs já atualizados"),
               ("catalogo_gravado", "catálogo gravado"),
               ("catalogo_ja", "catálogo inalterado"),
               ("falha_disco", "falhas de disco"))
    print()
    for chave, rotulo in rotulos:
        if r[chave]:
            print(f"{rotulo:26}: {r[chave]}")
    for stem in detalhes["isoladas"]:
        print(f"    ⚠ isolada (0 identificadores): {stem} — atribua temas "
              "(fase Temas por IA) para conectá-la")
    for c in detalhes["colisoes"]:
        print(f"    ✗ {c}")
    for o in detalhes["obsoletos"]:
        print(f"    · hub fora do corte atual (mantido): {o}")
    for f in detalhes["falhas"]:
        print(f"    ✗ {f}")

    # ── relatório no vault ──
    if not dry:
        L = ["# Relatório de Conexões — conectar.py", "",
             f"**{len(obras)} obra(s)** · {len(df)} identificador(es) "
             f"distintos · {compartilhados} compartilhado(s) por ≥2 obras",
             "", "## Pares relacionados (peso IDF)", ""]
        vistos = set()
        for stem in sorted(obras):
            for peso, n_comuns, alvo, prova in rels.get(stem, []):
                par = tuple(sorted((stem, alvo)))
                if par in vistos:
                    continue
                vistos.add(par)
                provas = " · ".join(fmt_ident(x) for x in prova)
                L.append(f"- [[{par[0]}]] ↔ [[{par[1]}]] — peso {peso:.1f}, "
                         f"{n_comuns} em comum ({provas})")
        if not vistos:
            L.append("- (nenhum par acima do corte)")
        if detalhes["hubs"] or r["hub_ja"]:
            L += ["", "## Hubs de norma (00-Indices-MOCs/Conexoes/)", ""]
            L += [f"- {h}" for h in detalhes["hubs"]]
            if r["hub_ja"]:
                L.append(f"- {r['hub_ja']} hub(s) já atualizados")
        if detalhes["obsoletos"]:
            L += ["", "## Hubs fora do corte atual (mantidos — apagar é "
                  "decisão sua)", ""] + [f"- {o}" for o in detalhes["obsoletos"]]
        if detalhes["colisoes"]:
            L += ["", "## ✗ Colisões (nada foi sobrescrito)", ""]
            L += [f"- {c}" for c in detalhes["colisoes"]]
        if detalhes["isoladas"]:
            L += ["", "## ⚠ Obras isoladas (sem identificadores)", "",
                  "Só a atribuição de temas conecta estas — fase Temas "
                  "por IA:", ""] + [f"- [[{s}]]" for s in detalhes["isoladas"]]
        if detalhes["falhas"]:
            L += ["", "## ✗ Falhas de disco (re-rode o Conectar)", ""]
            L += [f"- {f}" for f in detalhes["falhas"]]
        L += ["", "> Blocos entre marcadores `conectar:auto` são regeneráveis "
              "— edite fora deles. Republicou uma obra? Rode Conectar de "
              "novo. Nada é apagado por este script."]
        try:
            (vault / ARQ_RELATORIO).write_text("\n".join(L) + "\n",
                                               encoding="utf-8")
            print(f"\nRelatório: {vault / ARQ_RELATORIO}")
        except OSError as e:
            r["falha_disco"] += 1
            print(f"\n! relatório NÃO gravado ({e.strerror or e})")
        gravar_cache(vault, cache)

    print(f"\n{'-' * 72}")
    print(f"OK: {sum(v for k, v in r.items() if not k.startswith('falha'))}"
          f"  |  falhas: {r['falha_disco']}")
    if dry:
        print("(dry-run: rode sem --dry para gravar)")
    return 1 if r["falha_disco"] else 0


def main():
    ap = argparse.ArgumentParser(
        description="Costura o grafo do vault: relações obra↔obra por "
                    "identificadores citados, hubs de norma e catálogo")
    ap.add_argument("vault", help="pasta do vault do Obsidian")
    ap.add_argument("--dry", action="store_true", help="só mostra; não grava")
    ap.add_argument("--top", type=int, default=8,
                    help="máx. de relações por obra (padrão 8)")
    ap.add_argument("--min-peso", type=float, default=2.0,
                    help="peso IDF mínimo de uma relação (padrão 2.0)")
    ap.add_argument("--sem-hubs", action="store_true")
    ap.add_argument("--sem-relacoes", action="store_true")
    ap.add_argument("--sem-catalogo", action="store_true")
    ap.add_argument("--sem-cache", action="store_true",
                    help="ignora e reconstrói o cache de varredura")
    a = ap.parse_args()
    vault = Path(a.vault)
    if not vault.is_dir():
        sys.exit(f"ERRO: não encontrei {vault}")
    sys.exit(conectar(vault, dry=a.dry, top=a.top, min_peso=a.min_peso,
                      sem_hubs=a.sem_hubs, sem_relacoes=a.sem_relacoes,
                      sem_catalogo=a.sem_catalogo, sem_cache=a.sem_cache))


if __name__ == "__main__":
    main()

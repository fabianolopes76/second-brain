#!/usr/bin/env python3
"""
radar.py — FASE 6 do WORKFLOW: a cola DETERMINÍSTICA do radar (etapa 10).

Divisão de trabalho (decisão de arquitetura do projeto):
  - A DESCOBERTA (ir às fontes na web, julgar relevância, parafrasear) é
    trabalho de LLM — Cowork/Claude, Módulo E — e produz arquivos em
    00-Indices-MOCs/Radar/ (briefings, sentinelas de legislação e de
    jurisprudência).
  - A CORRELAÇÃO achado → notas afetadas é deste script, POR REGRA: um
    achado que menciona "Lei nº 5.172" liga-se às notas que citam esse
    número — extração de identificadores (lei, decreto, MP, tema, súmula,
    nº de processo; padrões do PERFIL da taxonomia), nunca palpite.

O script SINALIZA; quem DECIDE é o humano:
  - padrão: gera a FILA DE REVISÃO (RELATORIO-RADAR.md no vault), sem
    tocar em nota nenhuma;
  - --aplicar: marca as notas afetadas com `status: A-conferir` — que é um
    pedido de conferência, não um veredito (nunca escreve Revogado/
    Superado; isso é decisão do advogado, tomada no ritual de revisão).

Idempotente entre ciclos: os achados já aplicados ficam registrados em
Radar/.radar_estado.json e não re-sinalizam as mesmas notas amanhã.

Uso:
    python3 radar.py <vault>              # correlaciona e gera a fila (não altera notas)
    python3 radar.py <vault> --aplicar    # além da fila, sinaliza A-conferir
    python3 radar.py <vault> --radar <pasta>   # pasta do radar fora do padrão
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import frontmatter
import taxonomia

PADROES = [(rotulo, re.compile(rx, re.I))
           for rotulo, rx in taxonomia.PADROES_IDENTIFICADOR]

IGNORAR_PASTAS = {"99-Templates", "Radar", ".obsidian", ".trash"}


def identificadores(texto: str) -> set:
    """Extrai os identificadores fortes de um texto → {(rotulo, numero), ...}."""
    achados = set()
    for rotulo, rx in PADROES:
        for m in rx.finditer(texto):
            valor = re.sub(r"\D", "", m.group(1))
            if valor:
                achados.add((rotulo, valor))
    return achados


def rotular(ident) -> str:
    nomes = {"lei": "Lei", "decreto": "Decreto", "mp": "MP",
             "emenda": "EC", "tema": "Tema", "sumula": "Súmula",
             "processo": "Processo"}
    return f"{nomes.get(ident[0], ident[0])} {ident[1]}"


def notas_do_vault(vault: Path):
    notas = []
    for p in sorted(vault.rglob("*.md")):
        if any(parte in IGNORAR_PASTAS for parte in p.parts):
            continue
        if p.name.startswith(("RELATORIO", "_")):
            continue
        texto = p.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter.ler(texto)
        if str(fm.campos.get("tipo") or "") == "MOC":
            continue
        notas.append({"path": p, "fm": fm.campos,
                      "ids": identificadores(texto)})
    return notas


def sinalizar(path: Path) -> bool:
    """Marca `status: A-conferir` preservando o resto do arquivo linha a linha.
    → True se mudou algo."""
    texto = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", texto, re.DOTALL)
    if not m:
        return False
    linhas = m.group(2).split("\n")
    mudou, achou = False, False
    for i, linha in enumerate(linhas):
        if re.match(r"^status\s*:", linha):
            achou = True
            atual = linha.partition(":")[2].split(" #")[0].strip().strip('"')
            if atual != "A-conferir":
                linhas[i] = "status: A-conferir"
                mudou = True
            break
    if not achou:
        linhas.append("status: A-conferir")
        mudou = True
    if mudou:
        path.write_text(m.group(1) + "\n".join(linhas) + m.group(3)
                        + texto[m.end():], encoding="utf-8")
    return mudou


def main():
    ap = argparse.ArgumentParser(
        description="Correlaciona os achados do radar às notas do vault "
                    "(por identificador, não por palpite) e monta a fila "
                    "de revisão humana")
    ap.add_argument("vault")
    ap.add_argument("--radar", help="pasta dos achados "
                                    "(padrão: <vault>/00-Indices-MOCs/Radar)")
    ap.add_argument("--aplicar", action="store_true",
                    help="sinaliza as notas afetadas com status: A-conferir")
    a = ap.parse_args()

    vault = Path(a.vault)
    if not vault.is_dir():
        sys.exit(f"ERRO: não encontrei {vault}")
    radar_dir = Path(a.radar) if a.radar else vault / "00-Indices-MOCs" / "Radar"
    if not radar_dir.is_dir():
        sys.exit(f"Pasta do radar não existe: {radar_dir}\n"
                 "→ O radar é alimentado pelas rotinas do Módulo E (Cowork). "
                 "Crie a pasta e rode as sentinelas primeiro.")

    achados_md = sorted(f for f in radar_dir.rglob("*.md")
                        if not f.name.startswith(("RELATORIO", "_", ".")))
    if not achados_md:
        print(f"Nenhum achado em {radar_dir} — nada a correlacionar.")
        sys.exit(0)

    estado_path = radar_dir / ".radar_estado.json"
    try:
        estado = json.loads(estado_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        estado = {}

    notas = notas_do_vault(vault)

    fila, ja_processados = [], 0
    for f in achados_md:
        texto = f.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.md5(texto.encode()).hexdigest()
        chave = str(f.relative_to(radar_dir))
        if estado.get(chave) == digest:
            ja_processados += 1
            continue
        ids = identificadores(texto)
        afetadas = [n for n in notas if ids & n["ids"]]
        fila.append({"radar": f, "chave": chave, "digest": digest,
                     "ids": ids, "afetadas": afetadas})

    print(f"\n{'='*72}\nRADAR — {radar_dir}\n{'='*72}")
    print(f"{len(achados_md)} achado(s) no radar · {ja_processados} já "
          f"processado(s) · {len(fila)} a correlacionar · "
          f"{len(notas)} nota(s) no vault\n")

    sinalizadas = set()
    for item in fila:
        rotulos = ", ".join(sorted(rotular(i) for i in item["ids"])) or "(nenhum identificador)"
        print(f"📡 {item['chave']}")
        print(f"    identificadores: {rotulos}")
        if not item["afetadas"]:
            print("    → nenhuma nota do acervo cita esses identificadores")
            continue
        for n in item["afetadas"]:
            comuns = ", ".join(sorted(rotular(i) for i in item["ids"] & n["ids"]))
            marca = ""
            if a.aplicar:
                if sinalizar(n["path"]):
                    marca = "  ✍ status → A-conferir"
                    sinalizadas.add(n["path"])
                else:
                    marca = "  (já estava A-conferir)"
            print(f"    → {n['path'].relative_to(vault)}  [{comuns}]{marca}")

    # ── relatório: a fila de revisão do ritual semanal ──
    L = ["# Fila de revisão do radar", ""]
    L.append(f"{len(fila)} achado(s) novo(s) correlacionado(s). "
             "O radar SINALIZA; a decisão de reclassificar "
             f"({', '.join(taxonomia.PERFIL_ATIVO.status_superado)}) é humana.")
    L.append("")
    for item in fila:
        L.append(f"## 📡 {item['chave']}")
        rotulos = ", ".join(sorted(rotular(i) for i in item["ids"]))
        L.append(f"Identificadores: **{rotulos or '—'}**")
        if item["afetadas"]:
            L.append("")
            for n in item["afetadas"]:
                comuns = ", ".join(sorted(rotular(i) for i in item["ids"] & n["ids"]))
                L.append(f"- [ ] [[{n['path'].stem}]] — cita {comuns}: conferir "
                         "vigência/entendimento e ajustar `status` se preciso")
        else:
            L.append("- (nenhuma nota do acervo cita esses identificadores)")
        L.append("")
    L.append("> Ritual: despache os itens acima; confirmada uma mudança, "
             "atualize o `status` da nota e registre o aviso no topo "
             "(> [!warning] SUPERADO pelo...). Depois, rode o radar de novo.")

    (vault / "RELATORIO-RADAR.md").write_text("\n".join(L), encoding="utf-8")
    print(f"\nFila de revisão: {vault / 'RELATORIO-RADAR.md'}")

    if a.aplicar:
        for item in fila:
            estado[item["chave"]] = item["digest"]
        estado_path.write_text(json.dumps(estado, indent=1, ensure_ascii=False),
                               encoding="utf-8")
        print(f"{len(sinalizadas)} nota(s) sinalizada(s) A-conferir · "
              f"estado gravado em {estado_path.name}")
    else:
        print("(fila apenas — use --aplicar para sinalizar A-conferir e "
              "registrar os achados como processados)")
    sys.exit(0)


if __name__ == "__main__":
    main()

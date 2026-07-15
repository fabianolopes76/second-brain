#!/usr/bin/env python3
"""
auditar_vault.py — audita o GRAFO do vault do Obsidian (etapa 8 do trilho).

O auditar_acervo.py olha cada arquivo isoladamente; este script olha as
LIGAÇÕES entre eles — o que nenhuma checagem arquivo-a-arquivo enxerga:

  ERROS (quebram o grafo ou a VISIBILIDADE nos MOCs — o bug silencioso):
    - fatia órfã: `obra:` aponta para nota-índice que não existe
    - índice com `partes: N` diferente do nº real de fatias que apontam p/ ele
    - par tipo/tipo_fonte incoerente (ex.: tipo Doutrina + tipo_fonte
      jurisprudencia) — taxonomia.par_coerente
    - `status`/`tipo` fora do vocabulário do perfil → a nota SOME dos painéis
    - nota de conteúdo sem `area` → invisível em TODOS os painéis de área
    - nome de arquivo duplicado (stems iguais) → wikilinks ficam ambíguos

  AVISOS (higiene):
    - wikilink no corpo apontando para nota inexistente (placeholders com
      «guillemets» são ignorados — são instruções de template)
    - área usada em notas mas sem MOC que a cubra (aviso global, 1 por área)
    - `confiabilidade` fora do vocabulário
    - nome fora do padrão [AREA]_[TIPO]_[ANO]_[Titulo]_[Autor]
      (fatias/_INDICE não são re-julgadas: a convenção vale pelo pai)

Casos especiais: `tipo: MOC` não exige `area` (fontes.md não tem — e está
certo); a pasta 99-Templates/ e arquivos RELATORIO*/_* são ignorados; a
pasta Radar/ é ignorada (é fila de revisão do radar, não nota do acervo).

Uso:
    python3 auditar_vault.py <pasta-do-vault>
    python3 auditar_vault.py <vault> --detalhado
    python3 auditar_vault.py <vault> --relatorio RELATORIO-VAULT.md

Sai com código 1 se houver qualquer ERRO (integração com CI/painel).
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import frontmatter
import taxonomia
from comum import IGNORAR_PASTAS, WIKILINK, alvo_wikilink, vazio

IGNORAR_PREFIXOS = ("RELATORIO", "_")


def carregar(vault: Path):
    """Lê o vault inteiro → lista de notas {path, stem, fm, corpo}."""
    notas = []
    for p in sorted(vault.rglob("*.md")):
        if any(parte in IGNORAR_PASTAS for parte in p.parts):
            continue
        if p.name.startswith(IGNORAR_PREFIXOS):
            continue
        texto = p.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter.ler(texto)
        notas.append({"path": p, "stem": p.stem, "fm": fm.campos,
                      "corpo": fm.corpo, "tem_fm": fm.presente})
    return notas


def auditar_grafo(notas):
    """→ (resultados_por_nota, avisos_globais, resumo)"""
    stems = defaultdict(list)              # stem → [paths] (detecta duplicata)
    for n in notas:
        stems[n["stem"]].append(n["path"])
    existentes = set(stems)

    # MOCs declaram cobertura de área pelo próprio frontmatter
    areas_cobertas, areas_usadas = set(), defaultdict(int)
    fatias_por_indice = defaultdict(int)   # stem do índice → nº de fatias

    for n in notas:
        fm = n["fm"]
        n["eh_moc"] = str(fm.get("tipo") or "") == "MOC"
        n["eh_fatia"] = not vazio(fm.get("parte")) and not vazio(fm.get("obra"))
        n["eh_indice"] = ("_INDICE" in n["stem"].upper()
                          or not vazio(fm.get("partes")))
        if n["eh_moc"]:
            for a in (fm.get("area") or []):
                areas_cobertas.add(a)
        elif n["tem_fm"]:
            for a in (fm.get("area") or []):
                areas_usadas[a] += 1
        if n["eh_fatia"]:
            alvo = alvo_wikilink(fm.get("obra"))
            if alvo:
                fatias_por_indice[alvo] += 1

    resultados = []
    for n in notas:
        fm, r = n["fm"], {"arquivo": str(n["path"]), "erros": [], "avisos": []}
        resultados.append(r)

        if not n["tem_fm"]:
            r["erros"].append("sem frontmatter — invisível para os painéis")
            continue

        # — nome duplicado (ambiguidade de wikilink) —
        if len(stems[n["stem"]]) > 1:
            outros = [str(p) for p in stems[n["stem"]] if p != n["path"]]
            r["erros"].append(f"nome duplicado no vault (wikilinks ambíguos): "
                              f"também em {', '.join(outros)}")

        # — fatia: a obra-mãe existe? —
        if n["eh_fatia"]:
            alvo = alvo_wikilink(fm.get("obra"))
            if not alvo:
                r["erros"].append("fatia com `obra:` sem wikilink válido")
            elif alvo not in existentes:
                r["erros"].append(f"FATIA ÓRFÃ: obra aponta para "
                                  f"[[{alvo}]], que não existe no vault")

        # — índice: partes bate com a realidade? —
        if n["eh_indice"] and not vazio(fm.get("partes")):
            try:
                declarado = int(str(fm.get("partes")))
            except (TypeError, ValueError):
                declarado = None
                r["avisos"].append(f"`partes:` não numérico: "
                                   f"'{fm.get('partes')}'")
            if declarado is not None:
                reais = fatias_por_indice.get(n["stem"], 0)
                if reais != declarado:
                    r["erros"].append(
                        f"índice declara partes: {declarado}, mas "
                        f"{reais} fatia(s) apontam para ele — "
                        "fatias faltando ou contagem desatualizada")

        # — vocabulário que controla a visibilidade nos painéis —
        if not n["eh_moc"]:
            tipo = str(fm.get("tipo") or "")
            if tipo and tipo not in taxonomia.TIPOS:
                r["erros"].append(
                    f"tipo fora do vocabulário: '{tipo}' — a nota some dos "
                    f"painéis (válidos: {', '.join(taxonomia.TIPOS)})")
            st = str(fm.get("status") or "")
            if st and st not in taxonomia.STATUS:
                r["erros"].append(
                    f"status fora do vocabulário: '{st}' — a nota some dos "
                    f"painéis (válidos: {', '.join(taxonomia.STATUS)})")
            if vazio(fm.get("area")):
                r["erros"].append("sem `area` — invisível em TODOS os "
                                  "painéis de área dos MOCs")
            cf = str(fm.get("confiabilidade") or "")
            if cf and cf not in taxonomia.CONFIABILIDADE:
                r["avisos"].append(
                    f"confiabilidade fora do vocabulário: '{cf}' "
                    f"(válidos: {', '.join(taxonomia.CONFIABILIDADE)})")

            # — coerência entre eixos —
            coerente, motivo = taxonomia.par_coerente(
                str(fm.get("tipo") or ""), str(fm.get("tipo_fonte") or ""))
            if not coerente:
                r["erros"].append(motivo)

            # — convenção de nome (aviso; fatias julgam-se pelo pai) —
            analise = taxonomia.analisar_nome(n["path"].name)
            r["avisos"].extend(analise["avisos"])

        # — wikilinks do corpo (aviso; placeholders « » ignorados) —
        for alvo in WIKILINK.findall(n["corpo"]):
            alvo = alvo.strip()
            if not alvo or "«" in alvo or alvo in existentes:
                continue
            r["avisos"].append(f"wikilink para nota inexistente: [[{alvo}]]")

    # — cobertura de MOC por área (global) —
    globais = []
    for area, qtd in sorted(areas_usadas.items()):
        if area not in areas_cobertas:
            globais.append(f"área '{area}' usada em {qtd} nota(s) mas SEM MOC "
                           f"que a cubra — essas notas não têm porta de entrada")

    resumo = {
        "notas": len(notas),
        "mocs": sum(1 for n in notas if n.get("eh_moc")),
        "indices": sum(1 for n in notas if n.get("eh_indice")),
        "fatias": sum(1 for n in notas if n.get("eh_fatia")),
        "areas": dict(sorted(areas_usadas.items())),
        "areas_sem_moc": [g.split("'")[1] for g in globais],
    }
    return resultados, globais, resumo


def main():
    ap = argparse.ArgumentParser(
        description="Audita a integridade do GRAFO do vault (links, fatias, "
                    "vocabulário que controla os painéis)")
    ap.add_argument("vault")
    ap.add_argument("--relatorio", default="RELATORIO-VAULT.md")
    ap.add_argument("--detalhado", action="store_true")
    a = ap.parse_args()

    vault = Path(a.vault)
    if not vault.is_dir():
        sys.exit(f"ERRO: não encontrei a pasta {vault}")

    notas = carregar(vault)
    if not notas:
        sys.exit(f"Nenhuma nota encontrada em {vault}\n"
                 "→ O vault está vazio? Publique o conteúdo antes (Fase 5).")

    resultados, globais, resumo = auditar_grafo(notas)
    com_erro = [r for r in resultados if r["erros"]]
    com_aviso = [r for r in resultados if r["avisos"] and not r["erros"]]

    print(f"\n{'='*72}\nAUDITORIA DO VAULT — {vault}\n{'='*72}")
    print(f"{resumo['notas']} nota(s) · {resumo['mocs']} MOC(s) · "
          f"{resumo['indices']} índice(s) · {resumo['fatias']} fatia(s)")
    print("áreas: " + (", ".join(f"{k} ({v})" for k, v in resumo["areas"].items())
                       or "nenhuma"))
    print()
    for r in resultados:
        if r["erros"]:
            print(f"✗ {Path(r['arquivo']).name}")
            for e in r["erros"]:
                print(f"    ✗ {e}")
            if a.detalhado:
                for w in r["avisos"]:
                    print(f"    ! {w}")
        elif r["avisos"] and a.detalhado:
            print(f"! {Path(r['arquivo']).name}")
            for w in r["avisos"]:
                print(f"    ! {w}")
    for g in globais:
        print(f"! GLOBAL: {g}")

    n_avisos = sum(len(r["avisos"]) for r in resultados) + len(globais)
    print(f"\n{'-'*72}")
    print(f"ERROS: {sum(len(r['erros']) for r in resultados)} "
          f"em {len(com_erro)} nota(s)  |  AVISOS: {n_avisos}")

    # ---- relatório ----
    L = [f"# Auditoria do Vault — {vault.name}", ""]
    L.append(f"**{resumo['notas']} notas** · {resumo['mocs']} MOCs · "
             f"{resumo['indices']} índices · {resumo['fatias']} fatias · "
             f"erros em **{len(com_erro)}** nota(s)")
    L.append("")
    if com_erro:
        L.append("## ✗ Erros (quebram o grafo ou escondem notas dos painéis)")
        for r in com_erro:
            L.append(f"### {Path(r['arquivo']).name}")
            L += [f"- ✗ {e}" for e in r["erros"]]
        L.append("")
    if globais:
        L.append("## ! Cobertura de MOC")
        L += [f"- {g}" for g in globais]
        L.append("")
    if com_aviso or any(r["avisos"] for r in com_erro):
        L.append("## ! Avisos")
        for r in resultados:
            if r["avisos"]:
                L.append(f"### {Path(r['arquivo']).name}")
                L += [f"- ! {w}" for w in r["avisos"]]
        L.append("")
    L.append("## Como ler este relatório")
    L.append("- **Erro** = a nota está fora do grafo ou invisível nos painéis "
             "Dataview — corrija antes de confiar no vault.")
    L.append("- **Aviso** = higiene (links, nomes, cobertura). Não bloqueia, "
             "mas degrada a navegação.")
    L.append("")
    L.append("> Os painéis dos MOCs filtram por `area`, `tipo`, `status` e "
             "`!parte`. Valor fora do vocabulário não gera erro no Obsidian — "
             "a nota simplesmente não aparece. Este relatório existe para "
             "tornar esse silêncio visível.")

    destino = vault / a.relatorio
    destino.write_text("\n".join(L), encoding="utf-8")
    print(f"Relatório: {destino}")

    sys.exit(1 if com_erro else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
gerar_moc.py — cria e regenera MOCs (mapas de conteúdo) do vault.

Um MOC tem DUAS camadas, e este script respeita a fronteira entre elas:

  AUTOMÁTICA  — painéis Dataview que se preenchem sozinhos pelo frontmatter.
                Vivem entre os marcadores:
                    <!-- moc:auto:inicio -->  ...  <!-- moc:auto:fim -->
                Regenerar reescreve SÓ este bloco.
  MANUAL      — o mapa de institutos, relacionados, notas de manutenção.
                É curadoria humana: o script NUNCA toca no que está fora
                dos marcadores.

O filtro de área é um PREDICADO Dataview, não uma variável: áreas amplas
precisam de filtro composto (ex.: processo civil = contains(area,
"Processual") E a tag processo-civil OU a área Civil). O predicado fica
gravado no frontmatter do MOC (`moc_predicado`) e sobrevive à regeneração.

Os painéis vêm do PERFIL ativo da taxonomia (status_ok/pendência/superado
+ grupos de tipo) — outro domínio do conhecimento gera MOCs coerentes com
o próprio vocabulário, sem tocar neste script.

Uso:
    # criar (ou regenerar) o MOC de uma área:
    python3 gerar_moc.py <vault> --area Civil
    python3 gerar_moc.py <vault> --area Processual --nome MOC-Processo-Civil \
        --titulo "Direito Processual Civil" \
        --predicado 'contains(area, "Processual") AND (contains(tags, "processo-civil") OR contains(area, "Civil"))'

    # migrar um MOC legado (insere os marcadores SEM mudar o conteúdo):
    python3 gerar_moc.py <vault> --migrar 00-Indices-MOCs/MOC-Tributario.md

    # regenerar todos os MOCs que já têm marcadores:
    python3 gerar_moc.py <vault> --regenerar-todos
"""

import argparse
import datetime
import re
import sys
import unicodedata
from pathlib import Path

import frontmatter
import taxonomia

M_INI = "<!-- moc:auto:inicio — gerado por gerar_moc.py; edite FORA deste bloco -->"
M_FIM = "<!-- moc:auto:fim -->"
RE_BLOCO = re.compile(r"<!-- moc:auto:inicio[^>]*-->.*?<!-- moc:auto:fim -->",
                      re.DOTALL)


def _slug(area: str) -> str:
    s = unicodedata.normalize("NFKD", area)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")


def _lista_dv(valores) -> str:
    """(status = "A" OR status = "B")"""
    return "(" + " OR ".join(f'status = "{v}"' for v in valores) + ")"


def bloco_auto(pred: str) -> str:
    """Os painéis Dataview padrão, parametrizados pelo predicado e pelo perfil."""
    p = taxonomia.PERFIL_ATIVO
    base = f"FROM -\"99-Templates\"\nWHERE {pred} AND"
    S = []

    S.append(f"## ✅ {p.status_ok} (pronto para uso)")
    S.append("```dataview\nTABLE WITHOUT ID file.link AS \"Documento\", "
             "tipo AS \"Tipo\", autoria_citacao AS \"Autor/Órgão\", ano AS \"Ano\"\n"
             f"{base} status = \"{p.status_ok}\" AND !parte\n"
             "SORT tipo ASC, ano DESC\n```\n")

    pend = " OR ".join([f'status = "{s}"' for s in p.status_pendencia]
                       + [f'confiabilidade = "{s}"' for s in p.status_pendencia])
    S.append("## ⚠️ Pendências de conferência")
    S.append("Itens que **não** entram em peça sem revisão humana.")
    S.append("```dataview\nTABLE WITHOUT ID file.link AS \"Documento\", "
             "status AS \"Status\", confiabilidade AS \"Confiab.\", ano AS \"Ano\"\n"
             f"{base} ({pend}) AND !parte\nSORT file.mtime DESC\n```\n")

    S.append("## 🚫 Superado / Revogado / Alterado (não citar sem cautela)")
    S.append("```dataview\nTABLE WITHOUT ID file.link AS \"Documento\", "
             "status AS \"Situação\", ano AS \"Ano\"\n"
             f"{base} {_lista_dv(p.status_superado)} AND !parte\nSORT status ASC\n```\n")

    for titulo_g, tipos_g in p.moc_grupos:
        cond = "(" + " OR ".join(f'tipo = "{t}"' for t in tipos_g) + ")"
        S.append(f"## {titulo_g}")
        S.append("```dataview\nTABLE WITHOUT ID file.link AS \"Documento\", "
                 "autoria_citacao AS \"Autor/Órgão\", ano AS \"Ano\", "
                 "status AS \"Status\"\n"
                 f"{base} {cond} AND !parte\nSORT autoria_citacao ASC, ano DESC\n```\n")

    S.append("## 🆕 Novidades recentes (últimos 30 dias)")
    S.append("```dataview\nTABLE WITHOUT ID file.link AS \"Documento\", "
             "tipo AS \"Tipo\", file.mtime AS \"Atualizado\"\n"
             f"{base} !parte AND file.mtime >= date(today) - dur(30 days)\n"
             "SORT file.mtime DESC\n```\n")

    S.append("## 📊 Saúde do acervo")
    S.append("```dataview\nTABLE WITHOUT ID key AS \"Status\", "
             "length(rows) AS \"Qtd\"\n"
             f"{base} !parte\nGROUP BY status\n```")

    return M_INI + "\n\n" + "\n".join(S) + "\n\n" + M_FIM


def esqueleto(area, titulo, pred) -> str:
    hoje = datetime.date.today().isoformat()
    return f"""---
titulo: "MOC — {titulo}"
tipo: MOC
area: [{area}]
finalidade: "Porta de entrada navegável do acervo, com painéis automáticos (Dataview)"
moc_predicado: '{pred}'
data: {hoje}
---

# 🏛️ MOC — {titulo}

> [!info] Pré-requisito
> Os painéis usam o plugin **Dataview**. Convenções: notas-índice têm `area`
> e **não** têm `parte` (só as fatias têm) — por isso os painéis filtram
> `!parte`, para listar obras, não pedaços.

{bloco_auto(pred)}

---

## 🗺️ Mapa de institutos (curadoria manual)
Ligue aqui as notas-âncora dos temas mais usados. Substitua pelos seus `[[wikilinks]]`.

- **«instituto 1»** — [[«nota»]]
- **«instituto 2»** — [[«nota»]]

## 🔗 Relacionados
- [[fontes]] (radar de novidades)

> [!note] Manutenção
> Os painéis (entre os marcadores `moc:auto`) não precisam de manutenção —
> regenere com `gerar_moc.py`. A curadoria manual abaixo dos marcadores é
> sua: o script nunca a toca.
"""


def regenerar(caminho: Path) -> bool:
    texto = caminho.read_text(encoding="utf-8")
    if M_FIM not in texto or "moc:auto:inicio" not in texto:
        print(f"✗ {caminho.name}: sem marcadores moc:auto — use --migrar antes "
              "(regenerar sem marcadores destruiria a curadoria manual)")
        return False
    fm = frontmatter.ler(texto).campos
    pred = fm.get("moc_predicado")
    if not pred:
        areas = fm.get("area") or []
        if not areas:
            print(f"✗ {caminho.name}: sem moc_predicado nem area no frontmatter")
            return False
        pred = f'contains(area, "{areas[0]}")'
    novo = RE_BLOCO.sub(lambda _: bloco_auto(pred), texto, count=1)
    if novo == texto:
        print(f"— {caminho.name}: já atualizado")
        return True
    caminho.write_text(novo, encoding="utf-8")
    print(f"✓ {caminho.name}: bloco automático regenerado "
          "(curadoria manual intocada)")
    return True


def migrar(caminho: Path, pred: str = "") -> bool:
    """Insere os marcadores num MOC legado SEM alterar o conteúdo dos painéis.

    A fronteira histórica é o `---` solitário antes da seção de curadoria
    (`## 🗺️ Mapa de institutos`). O bloco automático começa no primeiro
    `## ` após o cabeçalho.
    """
    texto = caminho.read_text(encoding="utf-8")
    if "moc:auto:inicio" in texto:
        print(f"— {caminho.name}: já migrado")
        return True

    fm = frontmatter.ler(texto)
    corpo = fm.corpo
    m_ini = re.search(r"^## ", corpo, re.M)
    m_fim = re.search(r"\n---\s*\n(?=\s*## 🗺️)", corpo)
    if not m_ini or not m_fim or m_fim.start() <= m_ini.start():
        print(f"✗ {caminho.name}: não achei a fronteira painéis→curadoria "
              "(esperava '---' antes de '## 🗺️')")
        return False

    corpo_novo = (corpo[:m_ini.start()]
                  + M_INI + "\n\n"
                  + corpo[m_ini.start():m_fim.start()].rstrip() + "\n\n"
                  + M_FIM + "\n"
                  + corpo[m_fim.start():])

    bruto = fm.bruto
    if pred and "moc_predicado" not in bruto:
        bruto += f"\nmoc_predicado: '{pred}'"
    elif "moc_predicado" not in bruto:
        areas = fm.campos.get("area") or []
        if areas:
            bruto += f"\nmoc_predicado: 'contains(area, \"{areas[0]}\")'"

    caminho.write_text(f"---\n{bruto}\n---\n{corpo_novo}", encoding="utf-8")
    print(f"✓ {caminho.name}: marcadores inseridos (conteúdo preservado; "
          "regenere quando quiser normalizar os painéis)")
    return True


def main():
    ap = argparse.ArgumentParser(
        description="Cria/regenera MOCs preservando a curadoria manual")
    ap.add_argument("vault", help="pasta do vault (4-OBSIDIAN-VAULT)")
    ap.add_argument("--area", help="área canônica (cria/regenera MOC-<Área>)")
    ap.add_argument("--nome", help="nome do arquivo (padrão: MOC-<Área>)")
    ap.add_argument("--titulo", help="título humano (padrão: a área)")
    ap.add_argument("--predicado", help="predicado Dataview (padrão: "
                                        "contains(area, \"<área>\"))")
    ap.add_argument("--migrar", help="MOC legado a receber os marcadores")
    ap.add_argument("--regenerar-todos", action="store_true",
                    help="regenera o bloco auto de todos os MOC-*.md com marcadores")
    a = ap.parse_args()

    vault = Path(a.vault)
    if not vault.is_dir():
        sys.exit(f"ERRO: não encontrei {vault}")
    pasta_mocs = vault / "00-Indices-MOCs"

    if a.migrar:
        alvo = vault / a.migrar if not Path(a.migrar).is_absolute() else Path(a.migrar)
        sys.exit(0 if migrar(alvo, a.predicado or "") else 1)

    if a.regenerar_todos:
        mocs = sorted(pasta_mocs.glob("MOC-*.md")) if pasta_mocs.is_dir() else []
        if not mocs:
            sys.exit(f"Nenhum MOC-*.md em {pasta_mocs}")
        ok = all(regenerar(m) for m in mocs)
        sys.exit(0 if ok else 1)

    if not a.area:
        sys.exit("Informe --area (ou --migrar / --regenerar-todos). Veja --help.")

    canonicas = set(taxonomia.AREAS.values())
    if a.area not in canonicas:
        print(f"⚠ '{a.area}' não é área canônica do perfil "
              f"({', '.join(sorted(canonicas))}) — seguindo assim mesmo.")

    nome = a.nome or f"MOC-{_slug(a.area)}"
    titulo = a.titulo or a.area
    pred = a.predicado or f'contains(area, "{a.area}")'
    alvo = pasta_mocs / f"{nome}.md"

    if alvo.exists():
        sys.exit(0 if regenerar(alvo) else 1)
    pasta_mocs.mkdir(parents=True, exist_ok=True)
    alvo.write_text(esqueleto(a.area, titulo, pred), encoding="utf-8")
    print(f"✓ criado: {alvo}")
    print("   Preencha o mapa de institutos (curadoria) — os painéis já funcionam.")
    sys.exit(0)


if __name__ == "__main__":
    main()

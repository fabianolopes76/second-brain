#!/usr/bin/env python3
"""
normalizar_yaml.py — Deixa o frontmatter no formato que o Obsidian exige.

Por que existe
--------------
A IA preenche os metadados em prosa, do jeito que soa natural:

    area: "Direito Tributário — Parte Geral e Sistema Tributário Nacional"
    tags: ["direito-tributário", "Hugo de Brito Machado"]
    autoria: "MACHADO, Hugo de Brito"

Nada disso está errado como texto — mas quebra o Obsidian:
  * `area` precisa ser LISTA. As consultas Dataview fazem contains(area, "Tributário");
    numa string em prosa, o MOC aparece vazio.
  * TAGS não aceitam acento, espaço nem maiúscula. "direito-tributário" e
    "Hugo de Brito Machado" simplesmente não viram tags.
  * `autoria` precisa ser LISTA (obras com vários autores).

Corrigir isso à mão, nota a nota, é trabalho de máquina. Este script faz.

O que ele NÃO faz: não inventa dado, não mexe no texto, não toca nas âncoras.
Só reformata campos que já existem.

Uso:
    python3 normalizar_yaml.py pasta/ --dry      # mostra o que mudaria
    python3 normalizar_yaml.py pasta/            # aplica (cria .bak)
    python3 normalizar_yaml.py nota.md
"""

import argparse
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import taxonomia

# Vocabulário controlado de áreas — fonte única: o perfil ativo da taxonomia.
# (A antiga cópia local tinha inclusive uma chave morta, "econômic", que o
# sem_acento() duplicava em "economic".)
AREAS = taxonomia.AREAS


def sem_acento(s: str) -> str:
    n = unicodedata.normalize("NFKD", s)
    return "".join(c for c in n if not unicodedata.combining(c))


def tag_valida(s: str) -> str:
    """'Hugo de Brito Machado' -> 'hugo-de-brito-machado' (tag válida no Obsidian)."""
    s = sem_acento(str(s)).lower()
    s = re.sub(r"[^a-z0-9/]+", "-", s)      # a barra sobrevive: permite tag/hierárquica
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def areas_de(texto: str):
    """Extrai as áreas canônicas de uma descrição em prosa."""
    base = sem_acento(str(texto)).lower()
    achadas = []
    for chave, canon in AREAS.items():
        if sem_acento(chave) in base and canon not in achadas:
            achadas.append(canon)
    return achadas


def como_lista(valor: str):
    """Converte 'a, b' ou '["a","b"]' ou 'a' numa lista de strings."""
    v = valor.strip()
    if v.startswith("[") and v.endswith("]"):
        itens = re.findall(r'"([^"]*)"|\'([^\']*)\'', v[1:-1])
        if itens:
            return [a or b for a, b in itens]
        return [x.strip() for x in v[1:-1].split(",") if x.strip()]
    return [v.strip('"').strip("'")]


def fmt_lista(itens, aspas=True):
    if aspas:
        return "[" + ", ".join(f'"{i}"' for i in itens) + "]"
    return "[" + ", ".join(itens) + "]"


def normalizar(texto: str):
    """Devolve (texto_novo, mudancas)."""
    m = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", texto, re.DOTALL)
    if not m:
        return texto, []

    abre, fm, fecha = m.group(1), m.group(2), m.group(3)
    resto = texto[m.end():]
    linhas = fm.split("\n")
    mud = []

    # --- coleta os blocos multilinha (tags: \n [ \n "a", \n ] ) ---
    i, novas = 0, []
    while i < len(linhas):
        linha = linhas[i]
        chave = linha.split(":")[0].strip() if ":" in linha else ""
        valor = linha.partition(":")[2].split(" #")[0].strip() if ":" in linha else ""

        # bloco de lista em várias linhas
        if chave in ("tags", "area", "autoria") and valor == "" \
                and i + 1 < len(linhas) and linhas[i + 1].strip().startswith("["):
            bloco, j = "", i + 1
            while j < len(linhas):
                bloco += linhas[j].strip()
                if "]" in linhas[j]:
                    break
                j += 1
            valor = bloco
            i = j  # consumiu o bloco

        if chave == "area" and valor:
            atual = como_lista(valor)
            # se já é lista de termos canônicos, não mexe
            if all(a in AREAS.values() for a in atual) and valor.startswith("["):
                novas.append(f"area: {fmt_lista(atual, aspas=False)}")
            else:
                canon = areas_de(" ".join(atual)) or areas_de(valor)
                if canon:
                    novas.append(f"area: {fmt_lista(canon, aspas=False)}")
                    mud.append(f"area: prosa → {fmt_lista(canon, aspas=False)}")
                else:
                    novas.append(linha)
                    mud.append("⚠ area: não reconheci a área — preencha à mão")
            i += 1
            continue

        if chave == "tags" and valor:
            atual = como_lista(valor)
            limpas, sujas = [], []
            for t in atual:
                nova = tag_valida(t)
                if nova and nova not in limpas:
                    limpas.append(nova)
                if nova != t:
                    sujas.append(t)
            novas.append(f"tags: {fmt_lista(limpas, aspas=False)}")
            if sujas:
                mud.append(f"tags: normalizadas ({len(sujas)}): "
                           + ", ".join(sujas[:3]) + ("…" if len(sujas) > 3 else ""))
            i += 1
            continue

        if chave == "autoria" and valor and not valor.startswith("["):
            itens = [x.strip() for x in re.split(r";\s*", valor.strip('"').strip("'"))
                     if x.strip()]
            novas.append(f"autoria: {fmt_lista(itens)}")
            mud.append("autoria: string → lista")
            i += 1
            continue

        novas.append(linha)
        i += 1

    # --- status: exigido pelos painéis do MOC ---
    # A-conferir, NUNCA "Vigente": um script não pode afirmar vigência legal
    # que não conhece (o docstring promete "não inventa dado"). A-conferir
    # roteia a nota ao painel de pendências do MOC — onde nota não verificada
    # pertence — até um humano decidir.
    if not any(re.match(r"^status\s*:", l) for l in novas):
        novas.append("status: A-conferir")
        mud.append("status: acrescentado (A-conferir — revisão humana decide)")

    # --- censo de vocabulário: AVISA, nunca reescreve nem inventa ---
    def _valor_de(chave):
        for l in novas:
            m2 = re.match(rf"^{chave}\s*:\s*(.+?)\s*$", l)
            if m2:
                return m2.group(1).split(" #")[0].strip().strip('"').strip("'")
        return ""

    st = _valor_de("status")
    if st and st not in taxonomia.STATUS:
        mud.append(f"⚠ status fora do vocabulário: '{st}' "
                   f"(válidos: {', '.join(taxonomia.STATUS)})")
    tp = _valor_de("tipo")
    if tp and tp not in taxonomia.TIPOS and tp != "MOC":
        mud.append(f"⚠ tipo fora do vocabulário: '{tp}' "
                   f"(válidos: {', '.join(taxonomia.TIPOS)})")
    # `tipo` vazio + tipo_fonte inequívoco (legislacao→Legislação) = derivável
    # sem inventar nada. Sem `tipo` a nota NÃO TEM ROTA de publicação e some
    # dos painéis do MOC; onde o mapa admite mais de um, quem decide é o refino.
    if not tp:
        derivado = taxonomia.tipo_unico_de(_valor_de("tipo_fonte"))
        if derivado:
            novas.append(f"tipo: {derivado}                 # derivado do tipo_fonte — REVISE")
            mud.append(f"tipo: acrescentado ({derivado} — derivado do tipo_fonte)")
    cf = _valor_de("confiabilidade")
    if cf and cf not in taxonomia.CONFIABILIDADE:
        mud.append(f"⚠ confiabilidade fora do vocabulário: '{cf}' "
                   f"(válidos: {', '.join(taxonomia.CONFIABILIDADE)})")

    return abre + "\n".join(novas) + fecha + resto, mud


def processar(arq: Path, dry: bool):
    original = arq.read_text(encoding="utf-8", errors="replace")
    novo, mud = normalizar(original)
    if not mud:
        return False
    print(f"\n{arq.name}")
    for m in mud:
        print(f"  {m}")
    if not dry:
        shutil.copy2(arq, arq.with_suffix(arq.suffix + ".bak"))
        arq.write_text(novo, encoding="utf-8")
        print("  ✓ gravado")
    return True


def main():
    ap = argparse.ArgumentParser(
        description="Normaliza area/tags/autoria para o formato do Obsidian")
    ap.add_argument("alvo", help="arquivo .md ou pasta")
    ap.add_argument("--dry", action="store_true", help="só mostra, não grava")
    a = ap.parse_args()

    alvo = Path(a.alvo)
    if not alvo.exists():
        sys.exit(f"ERRO: não encontrei {alvo}")

    arquivos = ([f for f in sorted(alvo.rglob("*.md"))
                 if not f.name.startswith(("RELATORIO", "_"))]
                if alvo.is_dir() else [alvo])

    n = sum(1 for f in arquivos if processar(f, a.dry))
    print(f"\n{'='*54}\n{n} de {len(arquivos)} arquivo(s) normalizados"
          f"{' (dry-run)' if a.dry else ''}.")
    if n and not a.dry:
        print("Backups em *.md.bak. O texto e as âncoras não foram tocados.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
validar_yaml_abnt.py — Valida o frontmatter YAML por TIPO DE FONTE (ABNT) e
monta a referência (NBR 6023:2018) e o modelo de citação (NBR 10520).

Por que existe
--------------
Cada tipo de fonte da ABNT exige campos diferentes e se cita de forma diferente:
livro → página; e-book de leitor → posição (local.); lei → artigo;
jurisprudência → o próprio julgado. Este script confere se o YAML tem o que o
tipo exige, aponta o que falta e GERA a referência, evitando erro humano.

Sem dependências externas. O vocabulário (tipos, campos, localizadores) vem
de taxonomia.py; o parser de frontmatter vem de frontmatter.py — fontes
únicas de ambos, compartilhadas por todo o pipeline.

Uso:
    python validar_yaml_abnt.py nota.md
    python validar_yaml_abnt.py pasta/
    python validar_yaml_abnt.py nota.md --gerar   # imprime a referência montada
"""

import argparse
import re
import sys
from pathlib import Path

import frontmatter
import taxonomia

# ---------------------------------------------------------------------------
# Vocabulário — apenas referências à fonte única (taxonomia.py)
# ---------------------------------------------------------------------------
TIPOS_FONTE = taxonomia.TIPOS_FONTE
ANCORA_PAG = taxonomia.ANCORA_PAG
ANCORA_POS = taxonomia.ANCORA_POS


# ---------------------------------------------------------------------------
def ler_frontmatter(texto: str) -> dict:
    """Parser único do pipeline — ver frontmatter.py."""
    return frontmatter.ler(texto).campos


def vazio(v) -> bool:
    return v is None or v == "" or v == [] or v == "null"


def montar_referencia(d: dict) -> str:
    """Monta a referência NBR 6023:2018 conforme o tipo de fonte."""
    t = d.get("tipo_fonte", "")
    aut = d.get("autoria") or []
    autores = "; ".join(aut) if isinstance(aut, list) else str(aut)
    titulo = d.get("titulo", "")
    sub = d.get("subtitulo", "")
    tit = f"{titulo}: {sub}" if sub else titulo
    ano = d.get("ano", "")
    local = d.get("local_publicacao", "")
    ed = d.get("editora", "")
    edicao = d.get("edicao", "")

    resp = d.get("responsabilidade", "")
    if resp and autores:
        autores = f"{autores} ({resp})"

    if t == "livro":
        p = [f"{autores}. {tit}."]
        if edicao:
            p.append(f" {edicao}")
        p.append(f" {local}: {ed}, {ano}.")
        return "".join(p)

    if t in ("livro_ebook_leitor", "livro_ebook_online"):
        r = f"{autores}. {tit}. "
        if edicao:
            r += f"{edicao} "
        r += f"{local}: {ed}, {ano}. E-book."
        if d.get("url"):
            r += f" Disponível em: {d['url']}. Acesso em: {d.get('data_acesso','')}."
        return r

    if t == "capitulo_livro":
        at = d.get("autoria_todo") or []
        at = "; ".join(at) if isinstance(at, list) else str(at)
        rt = d.get("responsabilidade_todo", "")
        if rt:
            at = f"{at} ({rt})"
        return (f"{autores}. {tit}. In: {at}. {d.get('titulo_todo','')}. "
                f"{local}: {ed}, {ano}. p. {d.get('pagina_inicio','')}-{d.get('pagina_fim','')}.")

    if t == "artigo_periodico":
        r = f"{autores}. {tit}. {d.get('titulo_periodico','')}"
        if local:
            r += f", {local}"
        if d.get("volume"):
            r += f", v. {d['volume']}"
        if d.get("numero"):
            r += f", n. {d['numero']}"
        r += f", p. {d.get('pagina_inicio','')}-{d.get('pagina_fim','')}"
        if d.get("mes"):
            r += f", {d['mes']}"
        r += f" {ano}."
        return r

    if t == "trabalho_academico":
        r = f"{autores}. {tit}. "
        if d.get("orientador"):
            r += f"Orientador: {d['orientador']}. "
        r += f"{d.get('ano_deposito', ano)}. "
        if d.get("folhas"):
            r += f"{d['folhas']} "
        r += f"{d.get('grau','')} – {d.get('instituicao','')}, {local}, {d.get('ano_defesa', ano)}."
        if d.get("url"):
            r += f" Disponível em: {d['url']}. Acesso em: {d.get('data_acesso','')}."
        return r

    if t == "legislacao":
        r = (f"{autores}. {d.get('norma_numero','')}, de {d.get('norma_data','')}. "
             f"{d.get('ementa','')}")
        if d.get("veiculo_publicacao"):
            r += f" {d['veiculo_publicacao']}, {local}, {d.get('data_publicacao','')}."
        if d.get("url"):
            r += f" Disponível em: {d['url']}. Acesso em: {d.get('data_acesso','')}."
        return r

    if t == "jurisprudencia":
        of = d.get("orgao_fracionario", "")
        org = f"{d.get('orgao','')} ({of})" if of else d.get("orgao", "")
        r = (f"BRASIL. {org}. {d.get('classe_processual','')} {d.get('numero_processo','')}. "
             f"Relator: {d.get('relator','')}, {d.get('data_julgamento','')}.")
        if d.get("data_publicacao"):
            r += f" {d['data_publicacao']}."
        return r

    if t == "ato_administrativo":
        return (f"{d.get('orgao_emissor','').upper()}. {d.get('especie_ato','')} "
                f"{d.get('numero_ato','')}, de {d.get('data_ato','')}. {d.get('ementa','')}")

    return "(tipo de fonte sem gerador automático — monte manualmente)"


def sobrenome_curto(d: dict) -> str:
    """Sobrenome(s) para a nota subsequente (op. cit.) — sempre em CAIXA ALTA."""
    ac = d.get("autoria_citacao") or ""
    if ac:
        return ac.upper()
    aut = d.get("autoria") or []
    if isinstance(aut, list) and aut:
        return aut[0].split(",")[0].strip().upper()
    return "AUTOR"


def montar_citacoes(d: dict) -> dict:
    """Gera as TRÊS formas de citação a partir dos mesmos elementos do YAML.

    A base serve aos dois sistemas de chamada da ABNT:
      - autor_data  → (Machado, 2023, p. 33)          [pareceres, acadêmico]
      - numerico    → referência COMPLETA + p. 33.     [petições, nota de rodapé]
      - subsequente → MACHADO, op. cit., p. 45.        [repetição em notas]
    """
    ac = d.get("autoria_citacao") or "Autor"
    ano = d.get("ano", "AAAA")
    ab = (d.get("localizador_abrev") or "").strip()
    norma = str(d.get("norma_citacao") or "NBR 10520:2023")
    ref = d.get("referencia_abnt") or montar_referencia(d)

    # NBR 10520:2002 usava CAIXA ALTA dentro dos parênteses; a de 2023, não.
    ac_paren = ac.upper() if norma.endswith("2002") else ac

    loc = f"{ab} NN" if ab else ""

    autor_data = f"({ac_paren}, {ano}, {loc})" if loc else f"({ac_paren}, {ano})"

    ref_sem_ponto = ref.rstrip()
    if ref_sem_ponto.endswith("."):
        ref_sem_ponto = ref_sem_ponto[:-1]
    nota_completa = f"{ref_sem_ponto}. {loc}." if loc else f"{ref_sem_ponto}."

    sn = sobrenome_curto(d)
    nota_subsequente = f"{sn}, op. cit., {loc}." if loc else f"{sn}, op. cit."

    return {
        "autor_data": autor_data,
        "nota_completa": nota_completa,
        "nota_subsequente": nota_subsequente,
    }


# ---------------------------------------------------------------------------
def validar(caminho: Path, gerar: bool) -> bool:
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    d = ler_frontmatter(texto)
    print(f"\n=== {caminho.name} ===")

    if not d:
        print("  ✗ Sem frontmatter YAML.")
        return False

    t = d.get("tipo_fonte")
    if vazio(t):
        print("  ✗ Campo obrigatório ausente: tipo_fonte")
        print(f"    Valores válidos: {', '.join(TIPOS_FONTE)}")
        return False
    if t not in TIPOS_FONTE:
        print(f"  ✗ tipo_fonte desconhecido: '{t}'")
        return False

    print(f"  • tipo_fonte: {t}")
    regra = TIPOS_FONTE[t]
    ok = True

    # 1) campos obrigatórios
    faltando = [c for c in regra.obrigatorios if vazio(d.get(c))]
    if faltando:
        print(f"  ✗ Campos obrigatórios vazios: {', '.join(faltando)}")
        print("    → Preencha ou marque confiabilidade: A-conferir. NÃO invente.")
        ok = False
    else:
        print("  ✓ Campos obrigatórios completos")

    # 2) data nunca falta (regra dura da ABNT) — exigida quando o próprio tipo
    # lista `ano` entre os obrigatórios (jurisprudência e correspondência,
    # p.ex., datam-se pelo julgado/data, não pelo ano editorial)
    if "ano" in regra.obrigatorios and vazio(d.get("ano")):
        print("  ✗ ANO ausente. Na ABNT a data NUNCA falta — use [1969?], [ca. 1960], [197-].")
        ok = False

    # 3) localizador coerente com o tipo
    esperado_tipo, esperado_ab = regra.localizador
    if esperado_tipo:
        if d.get("localizador_tipo") != esperado_tipo:
            print(f"  ✗ localizador_tipo deveria ser '{esperado_tipo}' "
                  f"(está: '{d.get('localizador_tipo')}')")
            ok = False
        # None ≡ "" : o parser converte `localizador_abrev: ""` em None; sem
        # esta equivalência, nenhum tipo com abreviação vazia (jurisprudência,
        # audiovisual…) passava jamais na checagem — erro falso histórico.
        if (d.get("localizador_abrev") or "") != esperado_ab:
            print(f"  ✗ localizador_abrev deveria ser '{esperado_ab}' "
                  f"(está: '{d.get('localizador_abrev')}')")
            ok = False

    # 4) âncoras no corpo, quando o tipo exige
    if regra.exige_ancora:
        corpo = texto[len(re.match(r"^---.*?---\s*", texto, re.DOTALL).group(0)):] \
            if re.match(r"^---.*?---\s*", texto, re.DOTALL) else texto
        padrao = ANCORA_POS if esperado_tipo == "posicao" else ANCORA_PAG
        n = len(padrao.findall(corpo))
        if n == 0:
            print(f"  ✗ SEM âncoras de {esperado_tipo}. Este tipo EXIGE localizador para citar.")
            print("    → Reinjete: python injetar_paginas.py <pdf-fonte> -o <saida.md>")
            ok = False
        else:
            print(f"  ✓ Âncoras de {esperado_tipo}: {n}")

    if regra.aviso:
        print(f"  ⚠ {regra.aviso}")

    # Documento interno (abnt=False): não há referência nem citação a montar.
    if not regra.abnt:
        if ok:
            print("  ✓ YAML válido para o tipo (interno, sem referência ABNT)")
        return ok

    # 5) referência
    ref_declarada = d.get("referencia_abnt", "")
    if vazio(ref_declarada):
        print("  ⚠ referencia_abnt vazia — gerando sugestão:")
        print(f"    {montar_referencia(d)}")
    elif gerar:
        print(f"  • Declarada: {ref_declarada}")
        print(f"  • Gerada   : {montar_referencia(d)}")

    # 6) as DUAS formas de citação (a base serve aos dois sistemas)
    c = montar_citacoes(d)
    sistema = str(d.get("sistema_chamada") or "ambos").lower()
    print("  • Como citar:")
    if sistema in ("autor_data", "autor-data", "ambos"):
        print(f"      [autor-data]  {c['autor_data']}")
    if sistema in ("numerico", "ambos"):
        print(f"      [nota/peça]   {c['nota_completa']}")
        print(f"      [subsequente] {c['nota_subsequente']}")
    if sistema not in ("autor_data", "autor-data", "numerico", "ambos"):
        print(f"      ⚠ sistema_chamada inválido: '{sistema}' "
              "(use: autor_data | numerico | ambos)")

    if ok:
        print("  ✓ YAML válido para o tipo")
    return ok


def main():
    ap = argparse.ArgumentParser(description="Valida frontmatter YAML por tipo de fonte ABNT")
    ap.add_argument("alvo", help="arquivo .md ou pasta")
    ap.add_argument("--gerar", action="store_true",
                    help="mostrar a referência montada a partir do YAML")
    args = ap.parse_args()

    alvo = Path(args.alvo)
    if not alvo.exists():
        sys.exit(f"ERRO: não encontrei {alvo}")

    arquivos = sorted(alvo.glob("**/*.md")) if alvo.is_dir() else [alvo]
    if not arquivos:
        sys.exit("Nenhum .md encontrado.")

    res = [validar(f, args.gerar) for f in arquivos]
    print(f"\n{'='*46}\nResumo: {sum(res)}/{len(res)} nota(s) com YAML válido.")
    sys.exit(0 if all(res) else 1)


if __name__ == "__main__":
    main()

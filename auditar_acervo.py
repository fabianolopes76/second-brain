#!/usr/bin/env python3
"""
auditar_acervo.py — O conteúdo gerado serve para o segundo cérebro?

Responde, para uma pasta inteira, a pergunta prática:
"o que eu converti já está pronto para ser citado em peça e consultado por IA?"

Confere, arquivo a arquivo, os requisitos que o pipeline exige:
  1. Frontmatter YAML presente
  2. tipo_fonte definido (livro? lei? acórdão?) — governa todo o resto
  3. Idioma declarado (acervo é pt/en/de/fr/it/es)
  4. Âncoras de localização, QUANDO o tipo exige (doutrina precisa; lei não)
  5. Campos ABNT obrigatórios para aquele tipo (autor, título, editora, ano…)
  6. Referência ABNT montada
  7. Resumo (a "camada 1" que a IA lê antes de abrir o texto)
  8. Fatiamento — arquivos gigantes degradam a performance da IA
  9. Sanidade do texto: ruído de OCR, hifenização quebrada, cabeçalhos repetidos

Gera um RELATORIO-AUDITORIA.md com nota, pendências e o que fazer.

Uso:
    python3 auditar_acervo.py "/mnt/c/Users/Fulano/Dropbox/.../_Analise"
    python3 auditar_acervo.py <pasta> --relatorio auditoria.md
    python3 auditar_acervo.py <pasta> --detalhado
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import frontmatter
import taxonomia
from comum import vazio

# ---------------------------------------------------------------------------
# Vocabulário — fonte única: taxonomia.py. O que BLOQUEIA (erro) é
# campos_bloqueantes(); a dívida de migração (TOLERADOS) vira aviso.
# ---------------------------------------------------------------------------
EXIGE_ANCORA = {t for t, r in taxonomia.TIPOS_FONTE.items() if r.exige_ancora}
IDIOMAS = set(taxonomia.IDIOMAS)

ANC_PAG = taxonomia.ANCORA_PAG
ANC_POS = taxonomia.ANCORA_POS

# Alvo de fatia: ~1.500 tokens ≈ 1.100 palavras. Acima de ~4.000 palavras o
# arquivo já pesa no contexto e atrapalha a recuperação.
PALAVRAS_ALERTA = 4000
PALAVRAS_GRAVE = 12000


def ler_frontmatter(texto):
    """Parser único do pipeline — ver frontmatter.py."""
    fm = frontmatter.ler(texto)
    return fm.campos, fm.corpo


def sinais_de_ocr_sujo(corpo):
    """Detecta problemas típicos que o refino deveria ter corrigido."""
    problemas = []
    # hifenização de fim de linha não unida
    if len(re.findall(r"\w-\n\w", corpo)) > 3:
        problemas.append("hifenização quebrada (palavras cortadas no fim da linha)")
    # "Página X de Y" ou numeração solta no corpo
    if len(re.findall(r"(?im)^\s*(p[áa]gina\s+\d+\s+de\s+\d+|\d{1,4})\s*$", corpo)) > 5:
        problemas.append("números de página / cabeçalhos soltos no corpo")
    # ruído de caractere
    ruido = len(re.findall(r"[|¬~^]{2,}|[^\w\s\.,;:!?()\[\]{}\"'\-—–…/%$§ºª°&+=<>*#@\\áàâãéêíóôõúüçñäöüßœ]", corpo))
    if ruido > len(corpo) / 500:
        problemas.append("ruído de caractere (OCR sujo)")
    # linhas de 1-2 caracteres em sequência (coluna quebrada)
    curtas = len(re.findall(r"(?m)^.{1,2}$", corpo))
    if curtas > 30:
        problemas.append("muitas linhas curtíssimas (layout/coluna quebrada)")
    return problemas


def auditar(caminho: Path):
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    fm, corpo = ler_frontmatter(texto)
    palavras = len(corpo.split())

    r = {"arquivo": caminho.name, "palavras": palavras,
         "erros": [], "avisos": [], "ok": []}

    # 1. frontmatter
    if not fm:
        r["erros"].append("SEM frontmatter YAML — a IA não tem metadados para filtrar")
        return r
    r["ok"].append("frontmatter presente")

    # FATIA (camada 2): tem `parte` e aponta para a `obra`. Ela NÃO repete os
    # metadados ABNT — herda-os da nota-índice (camada 1). Cobrar autoria/editora
    # de cada fatia seria exigir 400× a mesma informação.
    eh_fatia = not vazio(fm.get("parte")) and not vazio(fm.get("obra"))
    r["fatia"] = eh_fatia

    # 2. tipo_fonte
    tf = fm.get("tipo_fonte")
    if vazio(tf):
        r["erros"].append("tipo_fonte ausente — sem ele não se sabe como citar")
        tf = None
    elif tf not in taxonomia.TIPOS_FONTE:
        r["erros"].append(f"tipo_fonte inválido: '{tf}'")
        tf = None
    else:
        r["ok"].append(f"tipo_fonte: {tf}")
    r["tipo"] = tf or "?"

    # 3. idioma
    idi = fm.get("idioma")
    if vazio(idi):
        r["avisos"].append("idioma não declarado — risco de a IA 'corrigir' texto estrangeiro")
    elif idi not in IDIOMAS:
        r["avisos"].append(f"idioma fora da lista: '{idi}'")
    else:
        r["ok"].append(f"idioma: {idi}")
    r["idioma"] = idi or "?"

    # 4. âncoras (só quando o tipo exige)
    # A NOTA-ÍNDICE (camada 1) não tem âncoras por definição: ela aponta para as
    # fatias (camada 2), que é onde o texto — e as páginas — de fato estão.
    eh_indice = ("_INDICE" in caminho.stem.upper()
                 or not vazio(fm.get("partes")))
    if eh_indice:
        r["ancoras"] = "índice"
        r["ok"].append("nota-índice (camada 1) — âncoras ficam nas fatias")
        if vazio(fm.get("resumo")):
            pass  # já será cobrado no item 7
    elif tf in EXIGE_ANCORA:
        padrao = ANC_POS if fm.get("localizador_tipo") == "posicao" else ANC_PAG
        n = len(padrao.findall(corpo))
        r["ancoras"] = n
        if n == 0 and eh_fatia:
            r["avisos"].append("fatia sem âncora — trecho curto entre duas páginas; "
                               "cite pela âncora da fatia anterior")
        elif n == 0:
            r["erros"].append("SEM âncoras de localização — NÃO É CITÁVEL em peça "
                              "(reinjete com injetar_paginas.py sobre o PDF-fonte)")
        else:
            r["ok"].append(f"{n} âncoras de página")
    elif tf:
        r["ancoras"] = "n/a"
        r["ok"].append("não exige âncora (cita-se por artigo/julgado)")
    else:
        r["ancoras"] = "—"

    # 5–7. Metadados ABNT: exigidos na NOTA-ÍNDICE; as fatias herdam dela.
    if eh_fatia:
        r["ok"].append("fatia — metadados ABNT herdados da nota-índice")
        if vazio(fm.get("pagina_inicio")) and tf in EXIGE_ANCORA:
            r["avisos"].append("sem pagina_inicio/pagina_fim no YAML da fatia")
    else:
        if tf:
            # O que BLOQUEIA (erro) vem de campos_bloqueantes; a dívida de
            # migração (TOLERADOS na taxonomia) vira aviso até o backlog zerar.
            faltam = [c for c in taxonomia.campos_bloqueantes(tf) if vazio(fm.get(c))]
            if faltam:
                r["erros"].append(f"campos ABNT vazios: {', '.join(faltam)}")
            else:
                r["ok"].append("campos ABNT completos")
            devidos = [c for c in taxonomia.campos_tolerados(tf) if vazio(fm.get(c))]
            if devidos:
                r["avisos"].append("dívida de migração ABNT — preencher: "
                                   + ", ".join(devidos))

        if tf and not taxonomia.eh_abnt(tf):
            r["ok"].append("documento interno — fora do regime ABNT (sem referência)")
        elif vazio(fm.get("referencia_abnt")):
            r["erros"].append("referencia_abnt vazia — sem ela não se monta a nota de rodapé")
        else:
            r["ok"].append("referência ABNT presente")

        res = fm.get("resumo")
        if vazio(res):
            r["avisos"].append("sem 'resumo' — a IA terá de ler o texto todo para julgar relevância")
        elif len(str(res).split()) < 15:
            r["avisos"].append("resumo curto demais (<15 palavras)")
        else:
            r["ok"].append("resumo presente")

    # 8. fatiamento
    if palavras > PALAVRAS_GRAVE:
        r["erros"].append(f"arquivo gigante ({palavras:,} palavras) — FATIE. "
                          "Um só arquivo assim degrada a IA e estoura tokens")
    elif palavras > PALAVRAS_ALERTA:
        r["avisos"].append(f"arquivo longo ({palavras:,} palavras) — considere fatiar")
    elif palavras > 0:
        r["ok"].append(f"tamanho adequado ({palavras:,} palavras)")

    # 9. sanidade do texto
    for p in sinais_de_ocr_sujo(corpo):
        r["avisos"].append(f"texto: {p}")

    # 10. conferência humana
    if str(fm.get("confiabilidade", "")).strip() == "A-conferir":
        r["avisos"].append("confiabilidade: A-conferir — ainda não passou por revisão humana")

    return r


def nota(r):
    if r["erros"]:
        return "REPROVADO"
    if r["avisos"]:
        return "PARCIAL"
    return "PRONTO"


def main():
    ap = argparse.ArgumentParser(
        description="Audita se os markdowns gerados servem ao segundo cérebro")
    ap.add_argument("pasta")
    ap.add_argument("--relatorio", default="RELATORIO-AUDITORIA.md")
    ap.add_argument("--detalhado", action="store_true")
    a = ap.parse_args()

    base = Path(a.pasta)
    if not base.exists():
        sys.exit(f"ERRO: não encontrei {base}")

    arquivos = sorted(base.rglob("*.md")) if base.is_dir() else [base]
    arquivos = [f for f in arquivos
                if not f.name.startswith(("RELATORIO", "_", "MOC-"))]
    if not arquivos:
        sys.exit(f"Nenhum .md encontrado em {base}\n"
                 "→ Você já converteu os PDFs? Rode injetar_paginas.py primeiro.")

    res = [auditar(f) for f in arquivos]
    placar = Counter(nota(r) for r in res)

    # ---- console ----
    print(f"\n{'='*72}\nAUDITORIA — {base}\n{'='*72}")
    print(f"{len(res)} arquivo(s) analisado(s)\n")
    for r in res:
        n = nota(r)
        ic = {"PRONTO": "✓", "PARCIAL": "!", "REPROVADO": "✗"}[n]
        print(f"{ic} {r['arquivo'][:48]:50} [{n}]")
        if a.detalhado or n != "PRONTO":
            for e in r["erros"]:
                print(f"    ✗ {e}")
            for w in r["avisos"]:
                print(f"    ! {w}")
        if a.detalhado:
            for o in r["ok"]:
                print(f"    ✓ {o}")

    print(f"\n{'-'*72}")
    print(f"PRONTO: {placar['PRONTO']}  |  PARCIAL: {placar['PARCIAL']}  "
          f"|  REPROVADO: {placar['REPROVADO']}")

    # diagnóstico agregado — o que mais aparece
    todos_erros = Counter()
    for r in res:
        for e in r["erros"]:
            chave = e.split("—")[0].split("(")[0].strip()[:48]
            todos_erros[chave] += 1
    if todos_erros:
        print("\nPROBLEMAS MAIS FREQUENTES:")
        for e, n in todos_erros.most_common(6):
            print(f"  {n:3}×  {e}")

    # ---- relatório ----
    saida = base / a.relatorio if base.is_dir() else Path(a.relatorio)
    L = [f"# Auditoria do Acervo — {base.name}", "",
         f"**{len(res)} arquivos** · PRONTO: {placar['PRONTO']} · "
         f"PARCIAL: {placar['PARCIAL']} · REPROVADO: {placar['REPROVADO']}", "",
         "| Arquivo | Tipo | Idioma | Âncoras | Palavras | Situação |",
         "|---|---|---|---|---|---|"]
    for r in res:
        L.append(f"| {r['arquivo']} | {r.get('tipo','?')} | {r.get('idioma','?')} "
                 f"| {r.get('ancoras','—')} | {r['palavras']:,} | **{nota(r)}** |")

    reprov = [r for r in res if r["erros"]]
    if reprov:
        L += ["", "## ✗ Bloqueios (impedem uso em peça)", ""]
        for r in reprov:
            L.append(f"### {r['arquivo']}")
            L += [f"- {e}" for e in r["erros"]]
            L.append("")

    parciais = [r for r in res if not r["erros"] and r["avisos"]]
    if parciais:
        L += ["## ! Melhorias recomendadas", ""]
        for r in parciais:
            L.append(f"### {r['arquivo']}")
            L += [f"- {w}" for w in r["avisos"]]
            L.append("")

    L += ["## Próximos passos", "",
          "1. **Sem âncoras** → reprocessar o PDF-fonte com `injetar_paginas.py` "
          "(a página não pode ser inferida do markdown).",
          "2. **Campos ABNT vazios** → preencher no Projeto Claude (Etapa 3 do "
          "`CHECKLIST_Refino_OCR.md`). Nunca inventar dado.",
          "3. **Arquivo gigante** → fatiar (Etapa 4): nota-índice + fatias de "
          "~500–1.500 tokens.",
          "4. **Sem resumo** → gerar a camada 1; é o que a IA lê antes de abrir o texto.",
          "5. **`A-conferir`** → conferir 3 páginas contra o PDF e marcar `Conferida`.", "",
          "> A base acelera; a conferência da citação que vai ao juiz continua sendo do advogado."]

    saida.write_text("\n".join(L), encoding="utf-8")
    print(f"\nRelatório: {saida}")
    sys.exit(1 if placar["REPROVADO"] else 0)


if __name__ == "__main__":
    main()

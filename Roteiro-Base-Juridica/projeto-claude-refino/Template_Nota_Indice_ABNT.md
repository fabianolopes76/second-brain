---
# --- Identificação ---
titulo: "«Título da obra»"
autor: "«Autor ou Órgão»"
area: [«Área1»]
tipo: «Doutrina | Legislação | Jurisprudência | Súmula | Artigo»
natureza: «Consultivo | Contencioso-Judicial | Contencioso-Administrativo | Extrajudicial»
orgao: "«STF | STJ | TRF1 | TJMA | ... (vazio se doutrina)»"
status: «Vigente | A-conferir | Revogado | Superado»
ano: «AAAA»
confiabilidade: «A-conferir | Conferida | Oficial | Doutrinária»
tags: [«instituto-1», «instituto-2»]
resumo: "«3–8 linhas: do que trata e o que a IA precisa saber para decidir relevância sem ler tudo.»"

# --- Citação ABNT (NBR 10520:2023 / NBR 6023:2018) ---
autor_sobrenome: "«Machado»"                    # citação: (Machado, 2023, p. 45)
autor_completo: "«MACHADO, Hugo de Brito»"      # referência: CAIXA ALTA
ano_publicacao: «2023»
edicao: "«44. ed.»"
local_publicacao: "«São Paulo»"
editora: "«Malheiros»"
referencia_abnt: "«MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023.»"

# --- Paginação (crítico para citar) ---
paginacao: true                # false = e-book sem página (usar 'local.')
origem_pdf: "«arquivo.pdf»"
paginas_total: «000»
offset_pagina: «0»             # página física do PDF menos página impressa
ancora: "chaves"               # chaves = {{p.NN}} | comentario = <!-- p.NN -->

partes: []
---

# «Título da obra»

> [!info] Ficha
> **Tipo:** «tipo» · **Área:** «área» · **Ano:** «ano» · **Edição:** «edição» · **Páginas:** «total»

> [!quote] Referência (ABNT NBR 6023)
> «MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023.»
>
> **Como citar:** `(Machado, 2023, p. NN)` — sobrenome em maiúsculas/minúsculas, conforme NBR 10520:2023.

<!-- Se for norma ou entendimento vencido, avise LOGO aqui:
> [!warning] SUPERADO/REVOGADO por «...» em «AAAA-MM-DD». Não citar sem cautela. -->

## Resumo para consulta
«Mesmo conteúdo do campo `resumo`, em prosa. É o que a IA lê primeiro para decidir se abre as fatias.»

## Palavras-chave
«instituto-1» · «instituto-2» · «tema»

## Sumário / Partes (camada 2)
<!-- Registre o INTERVALO DE PÁGINAS de cada fatia — é o que permite citar. -->
- [[«PREFIXO_p01» | 01 — «Capítulo I»]] — p. «1–28»
- [[«PREFIXO_p02» | 02 — «Capítulo II»]] — p. «29–57»
- [[«PREFIXO_p03» | 03 — «Capítulo III»]] — p. «58–90»

## Conferência
- [ ] Âncoras de página íntegras (`verificar_ancoras.py` → OK)
- [ ] Amostragem: 3 páginas conferidas contra o PDF
- [ ] Referência ABNT completa e correta
- [ ] Metadados sem suposições
- [ ] `confiabilidade` atualizada para `Conferida`

## Relacionados
- [[MOC-«Área»]]

<!-- NOME DO ARQUIVO: [AREA]_[TIPO]_[ANO]_[Titulo-Curto]_[Autor]_INDICE.md -->

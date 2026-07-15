---
titulo: "«Título da obra/documento»"
autoria: ["«SOBRENOME, Prenome»", "«ou ÓRGÃO emissor»"]
autoria_citacao: "«Sobrenome» | «Sobrenome; Sobrenome» | «Órgão»"
area: [«Área1», «Área2»]
tipo: «Doutrina | Legislação | Jurisprudência | Súmula | Artigo | Parecer | Modelo»
tipo_fonte: «livro | livro_ebook_leitor | livro_ebook_online | capitulo_livro | artigo_periodico | trabalho_academico | evento | legislacao | jurisprudencia | ato_administrativo | documento_online | verbete | norma_tecnica | audiovisual | correspondencia | peca_interna»
natureza: «Contencioso-Judicial | Contencioso-Administrativo | Consultivo | Extrajudicial»
orgao: "«STF | STJ | TRF1 | TRT16 | TJMA | ... (vazio se doutrina)»"
status: «Vigente | A-conferir | Revogado | Alterado | Superado | Modulado»
ano: «AAAA»
editora: "«Editora (doutrina) — vazio se lei/julgado»"
idioma: «por | eng | deu | fra | ita | spa»
localizador_tipo: «pagina | posicao | artigo | secao | sem_localizador (conforme o tipo_fonte)»
localizador_abrev: "«p. | local. | art. | seç. | (vazio)»"
referencia_abnt: "«referência completa NBR 6023 — o validador gera uma sugestão»"
confiabilidade: «Oficial | Doutrinária | Interna | A-conferir | Conferida»
tags: [«instituto-1», «instituto-2»]
resumo: "«3–8 linhas: do que trata, para que serve, o que a IA precisa saber para decidir relevância sem ler tudo.»"
criado: {{date:YYYY-MM-DD}}
partes: «N (número de fatias — o fatiar.py preenche sozinho)»
---

# «Título da obra/documento»

> [!info] Ficha
> **Tipo:** «tipo» · **Área:** «área» · **Órgão:** «órgão» · **Ano:** «ano» · **Editora:** «editora»

<!-- Se aplicável, avise a vigência LOGO no topo para IA e equipe não citarem norma vencida: -->
<!-- > [!warning] SUPERADO/REVOGADO pelo «Tema X do STJ / Lei nº ...» em «AAAA-MM-DD». -->

## Resumo para consulta
«Escreva aqui o mesmo conteúdo do campo `resumo` do frontmatter, em prosa. É este texto que a IA lê primeiro para decidir se abre as fatias. Mantenha curto e denso.»

## Palavras-chave
«instituto-1» · «instituto-2» · «tema» · «nº da lei / tema repetitivo, se houver»

## Sumário / Partes (camada 2)
<!-- Liste as fatias na ordem. Cada link abre um arquivo separado do texto integral. -->
- [[«PREFIXO_p01» | 01 — «Capítulo/Título/Ementa»]]
- [[«PREFIXO_p02» | 02 — «...»]]
- [[«PREFIXO_p03» | 03 — «...»]]

## Notas do escritório
«Observações internas: onde esta fonte já foi usada, casos relacionados, cautelas. Opcional.»

## Relacionados
- [[MOC-«Área»]]
- [[«nota-de-instituto-relacionado»]]

## Conferência
- [ ] Metadados completos e no padrão (rode `validar_yaml_abnt.py` — ele confere por tipo)
- [ ] Vigência verificada (para legislação/súmula)
- [ ] Citações críticas conferidas contra a fonte oficial
- [ ] `confiabilidade` atualizada para `Conferida`

<!-- ─────────────────────────────────────────────────────────────
VOCABULÁRIO: a fonte única é taxonomia.py (perfil ativo). Os valores nos
placeholders acima espelham o perfil "juridico"; os campos obrigatórios
variam por tipo_fonte — o validador cobra exatamente o que o tipo exige.

NOMENCLATURA DO ARQUIVO: [AREA]_[TIPO]_[ANO]_[Titulo-Curto]_[Autor]_INDICE.md
Ex.: TRIB_DOUT_2023_Curso-Direito-Tributario_Machado_INDICE.md
Códigos (taxonomia.CODIGO_AREA / CODIGO_TIPO):
  áreas: TRIB CIVIL PEN TRAB ADMIN CONST EMPR CONS PREV AMB FAM PROC ECON FIN INTL ELEI
  tipos: DOUT LEGIS JURIS SUM ART PAR MODELO

USO COM TEMPLATER (opcional): substitua os placeholders {{date:...}} por
<% tp.date.now("YYYY-MM-DD") %> e, se quiser, o título por <% tp.file.title %>.
Com o plugin nativo "Templates", {{title}} e {{date}} já funcionam.
Preencha os campos entre «guillemets» e apague estes comentários ao final.
───────────────────────────────────────────────────────────── -->

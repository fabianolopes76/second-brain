---
titulo: "«Título da obra/documento»"
autor: "«Autor ou Órgão emissor»"
area: [«Área1», «Área2»]
tipo: «Doutrina | Legislação | Jurisprudência | Súmula | Parecer | Modelo | Artigo»
natureza: «Contencioso-Judicial | Contencioso-Administrativo | Consultivo | Extrajudicial»
orgao: "«STF | STJ | TRF1 | TRT16 | TJMA | ... (vazio se doutrina)»"
status: «Vigente | A-conferir | Revogado | Alterado | Superado | Modulado»
ano: «AAAA»
fonte: "«Editora / DJe / próprio-escritório»"
confiabilidade: «Oficial | Doutrinária | Interna | A-conferir | Conferida»
tags: [«instituto-1», «instituto-2»]
resumo: "«3–8 linhas: do que trata, para que serve, o que a IA precisa saber para decidir relevância sem ler tudo.»"
criado: {{date:YYYY-MM-DD}}
partes: []
---

# «Título da obra/documento»

> [!info] Ficha
> **Tipo:** «tipo» · **Área:** «área» · **Órgão:** «órgão» · **Ano:** «ano» · **Fonte:** «fonte»

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
- [ ] Metadados completos e no padrão
- [ ] Vigência verificada (para legislação/súmula)
- [ ] Citações críticas conferidas contra a fonte oficial
- [ ] `confiabilidade` atualizada para `Conferida`

<!-- ─────────────────────────────────────────────────────────────
NOMENCLATURA DO ARQUIVO: [AREA]_[TIPO]_[ANO]_[Titulo-Curto]_[Autor].md
Ex.: TRIB_DOUT_2023_Curso-Direito-Tributario_Machado_INDICE.md

USO COM TEMPLATER (opcional): substitua os placeholders {{date:...}} por
<% tp.date.now("YYYY-MM-DD") %> e, se quiser, o título por <% tp.file.title %>.
Com o plugin nativo "Templates", {{title}} e {{date}} já funcionam.
Preencha os campos entre «guillemets» e apague estes comentários ao final.
───────────────────────────────────────────────────────────── -->

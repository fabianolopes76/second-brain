---
titulo: "Exemplos prontos de YAML por tipo de fonte"
tipo: Referência rápida
data: 2026-07-07
---

# Exemplos prontos — copie, cole e adapte

Cada bloco é um frontmatter **completo e válido** (testado no `validar_yaml_abnt.py`). Troque os valores; **não troque as chaves**.

---

## 📕 Livro impresso (o caso mais comum na doutrina)
```yaml
---
titulo: "Curso de direito tributário"
area: [Tributário]
tipo: Doutrina
natureza: Consultivo
status: Vigente
confiabilidade: A-conferir
tags: [prescricao-tributaria, lancamento]
resumo: "Manual de referência sobre o sistema tributário nacional..."

tipo_fonte: livro
norma_citacao: "NBR 10520:2023"
sistema_chamada: ambos            # numerico (peças) | autor_data | ambos
autoria: ["MACHADO, Hugo de Brito"]
autoria_citacao: "Machado"
tipo_autoria: pessoal
ano: 2023
edicao: "44. ed."
local_publicacao: "São Paulo"
editora: "Malheiros"
localizador_tipo: pagina
localizador_abrev: "p."
paginacao: true
ancora: chaves
offset_pagina: 0
paginas_total: 560
referencia_abnt: "MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023."
citacao_autor_data: "(Machado, 2023, p. 33)"
citacao_nota_completa: "MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023. p. 33."
citacao_nota_subsequente: "MACHADO, op. cit., p. 45."
---
```
> **Duas formas, um YAML.** A nota de rodapé (usada em peças) é a **referência completa + o localizador ao final**. O validador gera as duas — ver `SISTEMAS_DE_CHAMADA.md`.

## 📱 E-book de leitor (Kindle/Kobo) — SEM página, cita por posição
```yaml
---
titulo: "Vida organizada"
tipo: Doutrina
status: Vigente
confiabilidade: A-conferir     # posição é instável — conferir contra edição paginada

tipo_fonte: livro_ebook_leitor
norma_citacao: "NBR 10520:2023"
autoria: ["GODINHO, Thais"]
autoria_citacao: "Godinho"
ano: 2014
local_publicacao: "São Paulo"
editora: "Gente"
suporte: "E-book"
localizador_tipo: posicao
localizador_abrev: "local."    # ⚠️ NUNCA "p."
paginacao: false
ancora: posicao                # {{loc.NNNN}}
referencia_abnt: "GODINHO, Thais. Vida organizada: como definir prioridades e transformar seus sonhos em objetivos. São Paulo: Gente, 2014. E-book."
citacao_exemplo: "(Godinho, 2014, local. 264)"
---
```
> ⚠️ A posição do Kindle **muda com o tamanho da fonte**. Para citação em peça, obtenha a edição impressa ou o PDF paginado.

## 📗 Capítulo de livro (autoria própria dentro de coletânea)
```yaml
---
titulo: "Imagens da juventude na era moderna"
tipo: Doutrina

tipo_fonte: capitulo_livro
autoria: ["ROMANO, Giovanni"]
autoria_citacao: "Romano"
autoria_todo: ["LEVI, G.", "SCHMIDT, J."]
responsabilidade_todo: "org."
titulo_todo: "História dos jovens 2"
local_publicacao: "São Paulo"
editora: "Companhia das Letras"
ano: 1996
pagina_inicio: 7
pagina_fim: 16
localizador_tipo: pagina
localizador_abrev: "p."
paginacao: true
ancora: chaves
referencia_abnt: "ROMANO, Giovanni. Imagens da juventude na era moderna. In: LEVI, G.; SCHMIDT, J. (org.). História dos jovens 2. São Paulo: Companhia das Letras, 1996. p. 7-16."
citacao_exemplo: "(Romano, 1996, p. 12)"
---
```

## 📰 Artigo de periódico
```yaml
---
titulo: "Autoria coletiva, autoria ontológica e intertextualidade"
tipo: Artigo

tipo_fonte: artigo_periodico
autoria: ["MIRANDA, Antônio", "SIMEÃO, Elmira", "MULLER, Suzana"]
autoria_citacao: "Miranda; Simeão; Muller"     # até 3 autores: todos
ano: 2007
titulo_periodico: "Ciência da Informação"
local_publicacao: "Brasília"
volume: 36
numero: 2
pagina_inicio: 35
pagina_fim: 45
mes: "maio/ago."                                # maio é o único mês não abreviado
localizador_tipo: pagina
localizador_abrev: "p."
paginacao: true
ancora: chaves
referencia_abnt: "MIRANDA, Antônio; SIMEÃO, Elmira; MULLER, Suzana. Autoria coletiva, autoria ontológica e intertextualidade: aspectos conceituais e tecnológicos. Ciência da Informação, Brasília, v. 36, n. 2, p. 35-45, maio/ago. 2007."
citacao_exemplo: "(Miranda; Simeão; Muller, 2007, p. 40)"
---
```

## 🎓 Tese / Dissertação
```yaml
---
titulo: "Estado democrático de direito, igualdade e inclusão"
tipo: Doutrina
area: [Constitucional]

tipo_fonte: trabalho_academico
autoria: ["MEDEIROS, Jorge Luiz Ribeiro de"]
autoria_citacao: "Medeiros"
orientador: "Alexandre Bernardino Costa"
ano: 2007
ano_deposito: 2007
folhas: "164 f."
grau: "Dissertação (Mestrado em Direito)"
instituicao: "Faculdade de Direito, Universidade de Brasília"
local_publicacao: "Brasília"
ano_defesa: 2007
localizador_tipo: pagina
localizador_abrev: "p."
paginacao: true
ancora: chaves
referencia_abnt: "MEDEIROS, Jorge Luiz Ribeiro de. Estado democrático de direito, igualdade e inclusão: a constitucionalidade do casamento homossexual. Orientador: Alexandre Bernardino Costa. 2007. 164 f. Dissertação (Mestrado em Direito) – Faculdade de Direito, Universidade de Brasília, Brasília, 2007."
---
```

## 📜 Legislação — cita por ARTIGO (não precisa de âncora de página)
```yaml
---
titulo: "Código Civil"
area: [Civil]
tipo: Legislação
natureza: Consultivo
status: Vigente
confiabilidade: Oficial

tipo_fonte: legislacao
tipo_autoria: jurisdicao
autoria: ["BRASIL"]
autoria_citacao: "Brasil"
norma_numero: "Lei nº 10.406"
norma_data: "10 de janeiro de 2002"
ementa: "Institui o Código Civil."
veiculo_publicacao: "Diário Oficial da União: seção 1"
local_publicacao: "Brasília, DF"
data_publicacao: "11 jan. 2002"
ano: 2002
localizador_tipo: artigo
localizador_abrev: "art."
paginacao: false
ancora: nenhuma
url: "http://www.planalto.gov.br/ccivil_03/leis/2002/L10406compilada.htm"
data_acesso: "12 jul. 2026"
referencia_abnt: "BRASIL. Lei nº 10.406, de 10 de janeiro de 2002. Institui o Código Civil. Diário Oficial da União: seção 1, Brasília, DF, ano 139, n. 8, p. 1-74, 11 jan. 2002."
citacao_exemplo: "(Brasil, 2002, art. 205)"
---
```
> **Preserve a numeração de artigos, §§, incisos e alíneas** — ela é o localizador. É o equivalente, aqui, à âncora de página.

## ⚖️ Jurisprudência — cita pelo julgado
```yaml
---
titulo: "REsp 1.234.567/MA — prescrição intercorrente"
area: [Tributário, Processual]
tipo: Jurisprudência
natureza: Contencioso-Judicial
status: Vigente
confiabilidade: Oficial

tipo_fonte: jurisprudencia
tipo_autoria: jurisdicao
autoria: ["BRASIL"]
autoria_citacao: "Brasil"
orgao: "Superior Tribunal de Justiça"
orgao_fracionario: "Primeira Seção"
classe_processual: "Recurso Especial"
numero_processo: "1.234.567/MA"
relator: "Min. Fulano de Tal"
data_julgamento: "15 de maio de 2024"
data_publicacao: "DJe 20 maio 2024"
tema_repetitivo: "Tema 1234"
ano: 2024
localizador_tipo: sem_localizador
localizador_abrev: ""
paginacao: false
ancora: nenhuma
referencia_abnt: "BRASIL. Superior Tribunal de Justiça (Primeira Seção). Recurso Especial 1.234.567/MA. Relator: Min. Fulano de Tal, 15 de maio de 2024. Diário da Justiça Eletrônico, Brasília, DF, 20 maio 2024."
---
```

## 🏛️ Ato administrativo (IN, portaria, parecer, edital)
```yaml
---
titulo: "Instrução Normativa RFB nº 2.000/2021"
area: [Tributário, Administrativo]
tipo: Legislação
natureza: Contencioso-Administrativo
status: Vigente

tipo_fonte: ato_administrativo
tipo_autoria: entidade
orgao_emissor: "Receita Federal do Brasil"
especie_ato: "Instrução Normativa"
numero_ato: "RFB nº 2.000"
data_ato: "25 de janeiro de 2021"
ementa: "Dispõe sobre a apresentação da EFD-Reinf."
ano: 2021
localizador_tipo: artigo
localizador_abrev: "art."
paginacao: false
ancora: nenhuma
---
```

## 🌐 Documento online / notícia
```yaml
---
titulo: "«Título da página»"
tipo: Artigo

tipo_fonte: documento_online
autoria: ["«SOBRENOME, Prenome»"]     # ou entrada pelo título, se sem autor
autoria_citacao: "«Sobrenome»"
ano: 2026
online: true
url: "«https://...»"
data_acesso: "12 jul. 2026"
localizador_tipo: sem_localizador
localizador_abrev: ""
paginacao: false
ancora: nenhuma
---
```

---

## Elementos faltantes (regra ABNT)

| Falta | O que colocar |
|---|---|
| Autor | Entrada pelo **título**; `tipo_autoria: desconhecida`. Nunca "anônimo". |
| Local | `[Brasília]` (de outra fonte) ou `[S.l.]` |
| Editora | `[Juspodivm]` (de outra fonte) ou `[s.n.]` |
| **Data** | **NUNCA falta.** `[1969?]` · `[ca. 1960]` · `[197-]` · `[18--]` · `[entre 1906 e 1912]` |
| Título | `[Trabalhos apresentados]` |

## Autoria — quantos autores?
- **Até 3:** todos, separados por `;` → `(Torres; Martins; Alves, 2002)`
- **4 ou mais:** primeiro + `et al.` → `(Taylor et al., 2008)`
- **Entidade:** `UNIVERSIDADE FEDERAL DE VIÇOSA.`
- **Jurisdição:** `BRASIL.` (leis e decisões)
- **Responsabilidade:** `(org.)`, `(ed.)`, `(coord.)` — minúsculo e singular

## Valide sempre
```bash
python scripts/validar_yaml_abnt.py nota.md --gerar
```

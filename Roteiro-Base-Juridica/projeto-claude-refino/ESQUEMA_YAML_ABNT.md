---
titulo: "Esquema YAML por Tipo de Fonte (ABNT)"
tipo: Norma interna
normas: "NBR 6023:2018 (referências) · NBR 10520 (citações) · NBR 14724:2011"
fonte_base: "Normas ABNT — Biblioteca Central da UnB (síntese)"
data: 2026-07-07
---

# Esquema YAML por Tipo de Fonte (ABNT)

## Por que este arquivo existe

O YAML anterior era **monolítico** — pensado para livro. Mas a ABNT trata **cada tipo de fonte de forma diferente**: um capítulo de livro exige `In:` e a autoria do todo; um artigo de periódico exige volume, número e paginação; uma lei entra pela **jurisdição** e traz a ementa; um e-book lido em Kindle **não tem página** — tem **posição**.

Logo, o frontmatter precisa ser **polimórfico**: o campo `tipo_fonte` determina **quais campos são obrigatórios**, **como a referência é montada** e **como se cita** (página? posição? artigo?).

---

## ⚠️ Decisão normativa que o escritório precisa tomar

O material da UnB sintetiza a **NBR 10520:2002** (citações). Essa norma foi **substituída pela NBR 10520:2023** (vigente desde 19/07/2023). A diferença que mais aparece:

| | NBR 10520:**2002** (UnB) | NBR 10520:**2023** (vigente) |
|---|---|---|
| Autoria entre parênteses | `(SILVA, 2007, p. 30)` — caixa alta | `(Silva, 2007, p. 30)` — maiúsc./minúsc. |
| Autoria na **referência** | `SILVA, João.` — caixa alta | `SILVA, João.` — **inalterado** |

**Recomendação:** adotar a **2023** (é a norma em vigor) e registrar a escolha no campo `norma_citacao` do YAML, para que todo o acervo fique coerente. Se algum tribunal, revista ou banca exigir a 2002, basta trocar o valor do campo — o esquema suporta ambos.

```yaml
norma_citacao: "NBR 10520:2023"   # ou "NBR 10520:2002"
```

> A **NBR 6023:2018** (referências) permanece vigente e é a base de tudo abaixo.

---

## Campos comuns a TODOS os tipos

```yaml
# --- Núcleo do segundo cérebro (sempre) ---
titulo: ""                # título da nota
area: []                  # [Tributário, Civil, ...]
tipo: ""                  # Doutrina | Legislação | Jurisprudência | Súmula | Artigo | Parecer | Modelo
natureza: ""              # Consultivo | Contencioso-Judicial | Contencioso-Administrativo | Extrajudicial
status: ""                # Vigente | A-conferir | Revogado | Alterado | Superado | Modulado
confiabilidade: ""        # A-conferir | Conferida | Oficial | Doutrinária | Interna
tags: []
resumo: ""                # 3–8 linhas — é o que a IA lê primeiro

# --- Idioma (o acervo é multilíngue: pt/en/de/fr/it/es) ---
idioma: ""                # por | eng | deu | fra | ita | spa
idioma_nome: ""           # português | inglês | alemão | francês | italiano | espanhol
traducao: "original"      # original | propria | ambos  (ver OBRAS_MULTILINGUES.md)

# --- Núcleo ABNT (sempre) ---
tipo_fonte: ""            # ← DETERMINA o resto (ver catálogo abaixo)
norma_citacao: "NBR 10520:2023"
sistema_chamada: "ambos"  # numerico (peças) | autor_data (pareceres) | ambos
                          # ver SISTEMAS_DE_CHAMADA.md
autoria: []               # ["SOBRENOME, Prenome", ...] — como vai na REFERÊNCIA (caixa alta)
autoria_citacao: ""       # como vai na CITAÇÃO: "Silva" | "Silva; Costa" | "Taylor et al." | "Brasil"
tipo_autoria: ""          # pessoal | entidade | jurisdicao | desconhecida
responsabilidade: ""      # org. | ed. | coord. | trad. (minúsculo, singular) — se houver
ano: null                 # ano de publicação. NUNCA fica vazio na ABNT (use [1969?], [ca. 1960], [197-])
referencia_abnt: ""       # a referência COMPLETA, montada conforme o tipo (NBR 6023:2018)

# --- Saídas de citação (geradas pelo validador; a base serve aos DOIS sistemas) ---
citacao_autor_data: ""        # "(Machado, 2023, p. 33)"        → pareceres/acadêmico
citacao_nota_completa: ""     # "MACHADO, Hugo de Brito. Curso de direito tributário.
                              #  44. ed. São Paulo: Malheiros, 2023. p. 33."  → PEÇAS
citacao_nota_subsequente: ""  # "MACHADO, op. cit., p. 45."     → repetição em notas

# --- Localizador (COMO SE CITA — o ponto crítico) ---
localizador_tipo: ""      # pagina | posicao | local | capitulo | artigo | secao | paragrafo | sem_localizador
localizador_abrev: ""     # p. | local. | cap. | art. | § | (vazio)
paginacao: false          # true se o documento tem páginas fixas
ancora: ""                # chaves ({{p.NN}}) | posicao ({{loc.NNNN}}) | comentario | nenhuma
offset_pagina: 0
paginas_total: null

# --- Acesso online (quando aplicável) ---
online: false
url: ""
data_acesso: ""           # "23 mar. 2026" (mês abreviado, exceto maio)
```

> **Regra de ouro do preenchimento:** o que **não estiver no documento** fica vazio e a nota vai com `confiabilidade: A-conferir`. Se o dado veio de outra fonte, a ABNT manda pôr entre **colchetes** — ex.: `local_publicacao: "[Brasília]"`.

---

## Catálogo de tipos de fonte

### 1. `livro` — monografia no todo (impresso)
**Referência:** `AUTORIA. Título: subtítulo. Edição. Local: Editora, Data.`
**Cita-se por:** **página** → `(Machado, 2023, p. 45)`
```yaml
tipo_fonte: livro
subtitulo: ""
edicao: "44. ed."               # só transcreva a 1ª ed. se estiver expressa na obra
local_publicacao: "São Paulo"   # sem local → [S.l.]
editora: "Malheiros"            # sem editora → [s.n.]
isbn: ""                        # complementar
paginas_total: 560              # complementar
localizador_tipo: pagina
localizador_abrev: "p."
paginacao: true
ancora: chaves                  # {{p.NN}}
referencia_abnt: "MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023."
```

### 2. `livro_ebook_leitor` — e-book em leitor (Kindle, Kobo, Lev) ⚠️ SEM PÁGINA
**Referência:** `AUTORIA. Título: subtítulo. Local: Editora, Data. *E-book*.` (a palavra *E-book* em itálico)
**Cita-se por:** **posição/localização** → `(Dongo-Montoya, 2009, local. 264)`
```yaml
tipo_fonte: livro_ebook_leitor
local_publicacao: "São Paulo"
editora: "Gente"
suporte: "E-book"
localizador_tipo: posicao
localizador_abrev: "local."     # NÃO use "p." — o leitor não tem páginas fixas
paginacao: false
ancora: posicao                 # {{loc.NNNN}}
referencia_abnt: "GODINHO, Thais. Vida organizada: como definir prioridades e transformar seus sonhos em objetivos. São Paulo: Gente, 2014. E-book."
```
> **Cuidado:** a "posição" do Kindle **muda conforme o tamanho da fonte** no aparelho. Para citação segura em peça, prefira a edição **impressa ou o PDF paginado**. Registre `confiabilidade: A-conferir` se só houver a versão de leitor.

### 3. `livro_ebook_online` — livro digital consultado online (PDF/HTML)
**Referência:** `... *E-book*. Disponível em: URL. Acesso em: DATA.`
**Cita-se por:** **página**, se o PDF for paginado (o caso comum na doutrina jurídica).
```yaml
tipo_fonte: livro_ebook_online
suporte: "E-book"
online: true
url: "http://ebooks.pucrs.br/edipucrs/projetosdefilosofia.pdf"
data_acesso: "21 ago. 2026"
localizador_tipo: pagina        # se o PDF tem paginação
localizador_abrev: "p."
paginacao: true
ancora: chaves
```

### 4. `capitulo_livro` — parte de obra com autoria própria
**Referência:** `AUTORIA DA PARTE. Título da parte. *In*: AUTORIA DO TODO. **Título do todo**. Edição. Local: Editora, Data. p. inicial-final.`
(a expressão *In* em itálico; o **destaque vai no título do livro**, não no do capítulo)
**Cita-se por:** **página**
```yaml
tipo_fonte: capitulo_livro
autoria: ["ROMANO, Giovanni"]              # autor do CAPÍTULO
autoria_todo: ["LEVI, G.", "SCHMIDT, J."]  # autor/org. do LIVRO
responsabilidade_todo: "org."
titulo_todo: "História dos jovens 2"
local_publicacao: "São Paulo"
editora: "Companhia das Letras"
ano: 1996
pagina_inicio: 7
pagina_fim: 16
localizador_tipo: pagina
localizador_abrev: "p."
referencia_abnt: "ROMANO, Giovanni. Imagens da juventude na era moderna. In: LEVI, G.; SCHMIDT, J. (org.). História dos jovens 2. São Paulo: Companhia das Letras, 1996. p. 7-16."
```

### 5. `artigo_periodico` — artigo de revista/jornal
**Referência:** `AUTORIA. Título do artigo: subtítulo. **Título do periódico**, Local, v., n., p. inicial-final, Data.`
(destaque no **título do periódico**; mês abreviado, **exceto maio**)
**Cita-se por:** **página**
```yaml
tipo_fonte: artigo_periodico
titulo_periodico: "Ciência da Informação"
local_publicacao: "Brasília"
volume: 36
numero: 2
pagina_inicio: 35
pagina_fim: 45
mes: "maio/ago."
ano: 2007
localizador_tipo: pagina
localizador_abrev: "p."
referencia_abnt: "MIRANDA, Antônio; SIMEÃO, Elmira; MULLER, Suzana. Autoria coletiva, autoria ontológica e intertextualidade: aspectos conceituais e tecnológicos. Ciência da Informação, Brasília, v. 36, n. 2, p. 35-45, maio/ago. 2007."
```

### 6. `trabalho_academico` — tese, dissertação, TCC
**Referência:** `AUTORIA. Título: subtítulo. Orientador: Nome. Ano de depósito. Nº f. Tipo (Grau e Curso) – Vinculação acadêmica, Local, Ano da defesa.`
**Cita-se por:** **página**
```yaml
tipo_fonte: trabalho_academico
orientador: "Alexandre Bernardino Costa"   # complementar
ano_deposito: 2007
folhas: "164 f."
grau: "Dissertação (Mestrado em Direito)"
instituicao: "Faculdade de Direito, Universidade de Brasília"
local_publicacao: "Brasília"
ano_defesa: 2007
localizador_tipo: pagina
localizador_abrev: "p."
referencia_abnt: "MEDEIROS, Jorge Luiz Ribeiro de. Estado democrático de direito, igualdade e inclusão: a constitucionalidade do casamento homossexual. Orientador: Alexandre Bernardino Costa. 2007. 164 f. Dissertação (Mestrado em Direito) – Faculdade de Direito, Universidade de Brasília, Brasília, 2007."
```

### 7. `legislacao` — lei, decreto, código, MP ⚠️ CITA-SE POR ARTIGO
**Referência (publicação oficial):** `JURISDIÇÃO. Lei nº X, de DATA. Ementa. **Diário Oficial da União**: seção 1, Local, ano, n., p., data.`
**Referência (site):** `JURISDIÇÃO. **Lei nº X, de DATA**. Ementa. Local: Órgão, [ano]. Disponível em: URL. Acesso em: DATA.`
**Cita-se por:** **artigo/parágrafo/inciso** — não por página → `(Brasil, 2002, art. 205)` ou, na praxe forense, `art. 205 do Código Civil`
```yaml
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
localizador_tipo: artigo          # ← não é página!
localizador_abrev: "art."
paginacao: false
ancora: nenhuma                   # a âncora aqui é o próprio artigo
status: "Vigente"
referencia_abnt: "BRASIL. Lei nº 10.406, de 10 de janeiro de 2002. Institui o Código Civil. Diário Oficial da União: seção 1, Brasília, DF, ano 139, n. 8, p. 1-74, 11 jan. 2002."
```
> **Por isso legislação não precisa de âncora de página:** a unidade de citação é o **dispositivo** (art., §, inciso, alínea). Preserve a numeração original — ela **é** o localizador.

### 8. `jurisprudencia` — acórdão, decisão, súmula ⚠️ CITA-SE PELO PROCESSO
**Referência:** `JURISDIÇÃO. Órgão. **Tipo e número do processo**. Ementa/Partes. Relator: Min. Nome. Data de julgamento. Veículo de publicação, Local, data.`
**Cita-se por:** órgão + processo + relator + data
```yaml
tipo_fonte: jurisprudencia
tipo_autoria: jurisdicao
autoria: ["BRASIL"]
orgao: "Superior Tribunal de Justiça"
orgao_fracionario: "Primeira Seção"
classe_processual: "REsp"
numero_processo: "1.234.567/MA"
relator: "Min. Fulano de Tal"
data_julgamento: "2024-05-15"
data_publicacao: "DJe 20 maio 2024"
tema_repetitivo: "Tema 1234"          # se houver
localizador_tipo: sem_localizador     # cita-se o julgado, não a página
localizador_abrev: ""
status: "Vigente"                     # ou Superado/Modulado
referencia_abnt: "BRASIL. Superior Tribunal de Justiça (Primeira Seção). Recurso Especial 1.234.567/MA. Relator: Min. Fulano de Tal, 15 de maio de 2024. Diário da Justiça Eletrônico, Brasília, DF, 20 maio 2024."
```

### 9. `evento` — trabalho em anais de congresso
**Referência:** `AUTORIA. Título do trabalho. *In*: NOME DO EVENTO, nº, ano, Local. **Anais** [...]. Local: Editora, ano. p. inicial-final.`
```yaml
tipo_fonte: evento
nome_evento: "SIMPÓSIO BRASILEIRO DE AQUICULTURA"
numero_evento: "1."
ano_evento: 1978
local_evento: "Recife"
titulo_todo: "[Trabalhos apresentados]"
localizador_tipo: pagina
localizador_abrev: "p."
```

### 10. `documento_online` — site, portal, notícia
**Referência:** monta-se conforme o tipo de base (livro, artigo…) **+** `Disponível em: URL. Acesso em: DATA.`
**Cita-se por:** página, se houver; senão, sem localizador.
```yaml
tipo_fonte: documento_online
online: true
url: ""
data_acesso: "12 jul. 2026"
localizador_tipo: sem_localizador
paginacao: false
```

### 11. `ato_administrativo` — portaria, edital, parecer, ofício, instrução normativa
(A NBR 6023:2018 ampliou os modelos justamente para estes.)
**Cita-se por:** artigo/item do ato.
```yaml
tipo_fonte: ato_administrativo
tipo_autoria: entidade
orgao_emissor: "Receita Federal do Brasil"
especie_ato: "Instrução Normativa"
numero_ato: "RFB nº 2.000"
data_ato: "2021-01-25"
ementa: ""
localizador_tipo: artigo
localizador_abrev: "art."
```

### 12. `verbete` · 13. `norma_tecnica` · 14. `audiovisual` · 15. `correspondencia`
Tipos menos frequentes no escritório. Use `documento_online` ou `capitulo_livro` como base e registre `tipo_fonte` específico + `referencia_abnt` montada manualmente conforme a NBR 6023:2018.

---

## Tabela-síntese: como cada tipo se cita

| `tipo_fonte` | Localizador | Abrev. | Precisa de âncora no MD? |
|---|---|---|---|
| `livro` | página | `p.` | **Sim** — `{{p.NN}}` |
| `livro_ebook_online` (PDF paginado) | página | `p.` | **Sim** — `{{p.NN}}` |
| `livro_ebook_leitor` (Kindle) | posição | `local.` | Sim — `{{loc.NNNN}}` ⚠️ instável |
| `capitulo_livro` | página | `p.` | **Sim** |
| `artigo_periodico` | página | `p.` | **Sim** |
| `trabalho_academico` | página | `p.` | **Sim** |
| `legislacao` | artigo | `art.` | **Não** — o artigo é o localizador |
| `jurisprudencia` | — | — | **Não** — cita-se o julgado |
| `ato_administrativo` | artigo | `art.` | Não |
| `evento` | página | `p.` | Sim |
| `documento_online` | variável | — | Se paginado |

> **Regra prática:** se a coluna "âncora" diz **Sim** e o markdown não tem âncoras → **o documento não é citável**. Reinjete a paginação (`injetar_paginas.py`) ou marque `paginacao: false` + `confiabilidade: A-conferir`.

---

## Elementos faltantes — o que a ABNT manda fazer

| Falta | Solução |
|---|---|
| **Autor** | Entrada pelo **título** (`tipo_autoria: desconhecida`). **Nunca** use "anônimo". |
| **Local** | Identificado em outra fonte → `[Brasília]`. Não identificado → `[S.l.]` (*sine loco*). |
| **Editora** | Identificada em outra fonte → `[Juspodivm]`. Não identificada → `[s.n.]` (*sine nomine*). |
| **Data** | **NUNCA pode faltar.** Não existe "s.d." na ABNT. Use: `[1969?]` (provável) · `[ca. 1960]` (aproximada) · `[197-]` (década certa) · `[18--]` (século) · `[entre 1906 e 1912]`. |
| **Título** | Atribua entre colchetes: `[Trabalhos apresentados]`. |

---

## Regras de citação que o YAML sustenta

- **Citação direta** (transcrição literal): **exige** o localizador. Até 3 linhas → aspas duplas. 4+ linhas → recuo, fonte menor, sem aspas.
- **Citação indireta** (paráfrase): a ABNT diz que a página é **opcional**; **o escritório a exige**, para permitir conferência antes de a peça sair.
- **Supressão** `[...]` · **Interpolação** `[ ]` · **Ênfase**: `grifo nosso` / `grifo do autor` · **Tradução**: `tradução nossa`.
- **Até 3 autores** na citação: todos (`Torres; Martins; Alves`). **4 ou mais**: primeiro + `et al.`
- **Citação de citação** (`apud`): use só quando não teve acesso ao original.

---

## Elementos que seguem a língua DO DOCUMENTO (NBR 6023:2018)

O acervo é multilíngue. Alguns campos **não** vão em português — vão na língua da obra:

| Campo | pt | en | de | fr |
|---|---|---|---|---|
| `edicao` | `5. ed.` | `5th ed.` | `5. Aufl.` | `5e éd.` |
| `mes` (periódico) | `maio/ago.` | `May/Aug.` | `Mai/Aug.` | `mai/août` |
| `local_publicacao` | como consta no documento (`Wien`, `New York`, `Milano`) |

**Não mudam:** autoria em CAIXA ALTA · `[S.l.]` / `[s.n.]` · expressões latinas · a abreviatura `p.` (é elemento do *seu* trabalho). Detalhes: `OBRAS_MULTILINGUES.md`.

---

## Os dois sistemas de chamada

O escritório usa **autor-data** (pareceres) e **numérico/nota de rodapé** (petições). O YAML guarda os **elementos**; as formas de citação são **geradas** a partir deles:

| Sistema | Forma | Uso |
|---|---|---|
| Autor-data | `(Machado, 2023, p. 33)` | Pareceres, consultas, textos acadêmicos |
| **Numérico (nota)** | `MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023. p. 33.` | **Petições e peças judiciais** |
| Subsequente (nota) | `MACHADO, op. cit., p. 45.` | Repetição da obra em notas |

A nota completa é a **referência NBR 6023:2018 + o localizador ao final** — por isso o mesmo YAML alimenta as duas. Detalhes e expressões latinas (*Ibidem*, *Idem*, *op. cit.*, *loc. cit.*, *passim*, *et seq.*): ver `SISTEMAS_DE_CHAMADA.md`.

> **Não misture** os dois sistemas no mesmo documento — a norma proíbe, e o leitor se perde.

---

## Como a IA deve usar este esquema

1. Identificar o `tipo_fonte` a partir do documento.
2. Preencher **apenas** os campos daquele tipo — sem inventar.
3. Montar `referencia_abnt` conforme o modelo do tipo.
4. Definir `localizador_tipo` e `localizador_abrev` conforme a tabela-síntese.
5. Verificar se o tipo **exige âncora**; se exigir e não houver → **parar e avisar**.
6. Gerar **as duas formas de citação** (autor-data e nota completa) — nunca só uma.

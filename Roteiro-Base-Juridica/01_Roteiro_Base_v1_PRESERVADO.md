# Roteiro-Padrão de Conversão e Organização da Base de Conhecimento Jurídica em Markdown
### Pipeline Calibre → Markdown → Obsidian ("segundo cérebro") para uso com Claude e outros LLMs

> **Documento de Organização, Sistemas e Métodos (OSM).** Este roteiro é uma norma operacional reproduzível: define o passo a passo, a taxonomia de metadados, a nomenclatura de arquivos e as práticas de economia de tokens que o escritório deve observar como padrão único, do Calibre ao Obsidian.

---

## 0. Princípios que governam todo o roteiro

Antes das etapas, sete premissas que explicam *por que* cada decisão adiante foi tomada:

1. **A qualidade da base define a qualidade da resposta da IA.** Markdown sujo (cabeçalhos repetidos, hifenizações quebradas, números de página no meio do texto) degrada a recuperação e faz a IA "alucinar" ou citar errado. Limpeza não é opcional em contexto jurídico.
2. **O formato de origem determina o esforço.** ePUB e MOBI convertem muito bem; PDF converte mal. O roteiro trata cada família de forma distinta (Seções 2 e 3).
3. **O Calibre é o *catálogo e a linha de conversão de ePUB/MOBI*; não é o melhor conversor de PDF.** Usaremos o Calibre para o que ele faz bem (organização de biblioteca com metadados ricos + conversão de e-books) e uma rota alternativa para PDFs difíceis (Seção 3.3).
4. **Metadados são cidadãos de primeira classe.** Toda a taxonomia criada no Calibre (tags, colunas personalizadas, coleções) é *espelhada* no *frontmatter* YAML do Obsidian. O trabalho de classificação é feito **uma vez**.
5. **Documento longo ≠ documento útil.** Um livro inteiro de 200 mil tokens jogado no contexto piora a performance e o custo. A arquitetura é de **duas camadas**: notas curtas e densas em metadados (camada de recuperação/raciocínio) que apontam para os fontes longos fatiados (camada de leitura). Ver Seção 6.
6. **Vigência importa.** Diferente de acervos comuns, no Direito um texto pode estar **revogado, superado ou modulado**. O status normativo/jurisprudencial entra nos metadados obrigatórios.
7. **Padrão único e auditável.** Nomenclatura, tags e estrutura de pastas são idênticas nas duas ferramentas, de modo que qualquer pessoa da equipe reproduza o fluxo sem depender de conhecimento tácito.

---

## 1. Triagem inicial do acervo (antes de tocar no Calibre)

Nenhum arquivo entra no fluxo sem passar por uma triagem que responde três perguntas. Registre o resultado numa planilha de controle (colunas: arquivo, formato, tem_camada_texto, natureza, área, rota).

**Pergunta 1 — Qual o formato de origem?**

| Formato | Qualidade da conversão p/ Markdown | Rota recomendada |
|---|---|---|
| ePUB | Ótima (estrutura semântica preservada) | Calibre (Seção 3.1) |
| MOBI / AZW3 | Boa | Calibre (Seção 3.1) |
| PDF **com camada de texto** (nativo/digital) | Ruim a razoável | Calibre com ajustes (Seção 3.2) **ou** ferramenta dedicada |
| PDF **escaneado** (imagem, sem texto) | Impossível direto — precisa OCR antes | OCR → Markdown (Seção 3.3) |

**Pergunta 2 — O PDF tem camada de texto?** Teste rápido: abra o PDF e tente **selecionar/copiar** um parágrafo. Se copiar texto de verdade, há camada de texto. Se não copiar nada (ou copiar caracteres soltos), é escaneado e **exige OCR** — o Calibre **não faz OCR** e produzirá lixo. Decisões judiciais antigas, diários oficiais digitalizados e livros escaneados normalmente caem aqui.

**Pergunta 3 — Qual a natureza jurídica do documento?** (define a rota de metadados e o rigor de limpeza)
- Doutrina (livro/manual/curso/artigo)
- Legislação (lei, decreto, código, regulamento) — **sensível à vigência**
- Jurisprudência (acórdão, decisão monocrática, súmula, tese/tema repetitivo)
- Peça/modelo interno (petição, contrato, parecer, minuta)
- Material administrativo/extrajudicial (portarias, atos normativos de agências, editais)

> **Regra de ouro da triagem:** documentos com força normativa ou jurisprudencial (leis, súmulas, acórdãos paradigmáticos) exigem **conferência humana** do resultado — a IA não deve ser a única checagem de fidelidade de uma citação que irá para uma peça processual.

---

## 2. Configuração do Calibre como catálogo jurídico

Aqui construímos, **uma única vez**, a estrutura de organização que será espelhada no Obsidian. Faça tudo isto antes de converter em lote.

### 2.1 Biblioteca(s)
Crie uma biblioteca dedicada (`Biblioteca > Trocar/criar biblioteca`), por exemplo `Acervo-Juridico`. Se o volume for muito grande, é aceitável separar por macroárea (ex.: `Acervo-Tributario`, `Acervo-Trabalhista`), mas prefira **uma biblioteca única com boa taxonomia** — múltiplas bibliotecas fragmentam a busca.

### 2.2 Colunas personalizadas (o coração da classificação)
Em `Preferências > Adicionar colunas personalizadas`, crie as colunas abaixo. Elas viram, depois, campos do YAML no Obsidian — mantenha os **nomes de chave (lookup name) idênticos** aos que usaremos lá.

| Coluna (rótulo) | Lookup name | Tipo | Valores / exemplo |
|---|---|---|---|
| Área do Direito | `#area` | Texto (com vírgulas, comporta-se como tags) | Civil, Penal, Tributário, Trabalhista, Administrativo, Constitucional, Empresarial, Consumidor, Previdenciário, Ambiental, Família, Processual |
| Tipo de Documento | `#tipo` | Texto | Doutrina, Legislação, Jurisprudência, Súmula, Parecer, Modelo, Artigo |
| Natureza da Atuação | `#natureza` | Texto | Contencioso-Judicial, Contencioso-Administrativo, Consultivo, Extrajudicial |
| Órgão / Instância | `#orgao` | Texto | STF, STJ, TST, TSE, STM, TRF-1, TJ-MA, TRT, 1ª-Instância, Turma-Recursal, Agência-Reguladora |
| Vigência / Status | `#status` | Texto | Vigente, Revogado, Alterado, Superado, Modulado, Em-vigor-parcial |
| Ano de Referência | `#ano` | Data ou inteiro | 2023 |
| Fonte / Editora | `#fonte` | Texto | Ed. RT, Saraiva, DJe, próprio-escritório |
| Confiabilidade | `#confiab` | Texto | Oficial, Doutrinária, Interna, A-conferir |

> **Por que colunas e não só tags?** Colunas dão estrutura consistente e viram campos YAML nomeados; tags são melhores para conceitos transversais e livres (Seção 2.3). Usar os dois é a prática recomendada.

### 2.3 Tags (conceitos transversais e livres)
Reserve as **tags** para o que não é enumerável em coluna: temas e institutos jurídicos, nomes de casos, projetos internos. Padronize o formato para casar com o Obsidian (minúsculas, sem espaço, hífen ou barra para hierarquia):
- Institutos: `prescricao`, `responsabilidade-civil`, `litispendencia`
- Casos/temas repetitivos: `tema-1234-stf`, `sumula-vinculante-10`
- Projetos internos: `cliente/acme`, `caso/2024-mandado-seguranca`

Mantenha um **dicionário de tags controlado** (uma nota "Tags-Canônicas") para evitar `resp-civil`, `responsabilidade civil` e `responsabilidade-civil` convivendo.

### 2.4 Séries e Coleções
- **Série** (campo nativo): use para obras multivolume ou coleções editoriais (ex.: Série = "Curso de Direito Civil – Tartuce", índice de série = volume).
- **Bibliotecas Virtuais** (`Bibliotecas virtuais`): crie "visões" salvas que funcionam como coleções dinâmicas, por ex. `#area:Tributário and #status:Vigente`. Elas não movem arquivos — apenas filtram. São o equivalente às *saved searches*/MOCs do Obsidian.

### 2.5 Metadados básicos e capa
Preencha Título, Autor(es) e (quando houver) ISBN/identificador. Para legislação e jurisprudência sem "autor", use o órgão emissor no campo autor (ex.: Autor = "STJ"). Título deve ser **descritivo e estável** — ele alimenta a nomenclatura de arquivo (Seção 4).

---

## 3. Conversão para Markdown

O Calibre gera Markdown por meio do **plugin de saída TXT com formatação `markdown`** (confirmado no manual e no `ebook-convert`: as opções de formatação de saída TXT incluem `plain`, `markdown` e `textile`). O detalhe operacional é que a saída sai com extensão `.txt` — **renomeie para `.md`** ao final (ou automatize o rename em lote).

### 3.1 Rota A — ePUB / MOBI / AZW3 (rota principal, alta qualidade)

**Pela interface gráfica:**
1. Selecione o(s) livro(s) → botão **Converter livros**.
2. No canto superior direito, defina **Formato de saída = TXT**.
3. Painel **TXT Output**: em *Formatting used within the document*, selecione **Markdown**. Marque `Keep links` e `Keep image references` se quiser preservar links/imagens; defina *Output encoding = utf-8*.
4. Painel **Heuristic Processing**: ative (`Enable heuristic processing`) — melhora detecção de itálico, títulos e junção de parágrafos.
5. Painel **Structure Detection**: para gerar títulos/TOC a partir de capítulos, use a expressão XPath de detecção de capítulos (o manual sugere `//h:h1` como forma mais simples de obter um sumário adequado).
6. Converta. Localize o `.txt` (`Clique com o direito > Abrir pasta contendo o livro`) e **renomeie para `.md`**.

**Por linha de comando (recomendado para lote), usando `ebook-convert`:**
```bash
ebook-convert "entrada.epub" "saida.txt" \
  --txt-output-formatting=markdown \
  --enable-heuristics \
  --keep-links --keep-image-references \
  --txt-output-encoding=utf-8 \
  --chapter "//h:h1"
# depois:
mv "saida.txt" "saida.md"
```

> **Nota de robustez:** há relatos recentes de falha do `ebook-convert` para markdown em alguns arquivos específicos (traceback no plugin de saída). Portanto: **teste em uma amostra** antes de rodar centenas de arquivos, e mantenha a rota alternativa (Seção 3.3) como *fallback* para os que falharem.

### 3.2 Rota B — PDF com camada de texto (qualidade variável)

O manual do Calibre é explícito: PDF é um dos piores formatos de origem, porque o texto tem posição fixa e é difícil saber onde um parágrafo termina. Ainda assim, para PDFs nativos simples (texto corrido, uma coluna), dá para usar o Calibre:

1. Converta o PDF **primeiro para ePUB** (Formato de saída = EPUB), ajustando o **fator de remoção de quebras de linha** (*Line un-wrapping factor*, no painel de PDF Input) até os parágrafos ficarem coesos.
2. Revise o ePUB no editor do Calibre (`Editar livro`) — corrija hifenizações, cabeçalhos e rodapés repetidos.
3. **Depois** converta o ePUB limpo para Markdown pela Rota A.

Essa cadeia **PDF → ePUB (revisado) → Markdown** costuma dar resultado melhor do que PDF → Markdown direto. Para PDFs de **layout complexo** (duas colunas, tabelas, notas de rodapé densas — comuns em doutrina e em acórdãos formatados), vá direto para a Rota C.

### 3.3 Rota C — PDF escaneado ou de layout complexo (OCR / ferramenta dedicada)

O Calibre não resolve isto. Duas situações:

- **PDF escaneado (imagem):** rode **OCR primeiro**. Opções: `OCRmyPDF` (gera um PDF com camada de texto pesquisável, gratuito e local), ou ferramentas com OCR embutido como **Marker** (OCR via Surya, ótimo em estrutura, tabelas e notas de rodapé) e **Docling** (IBM, pensado para pipelines de RAG e que preserva a hierarquia semântica). Para digitalização de **livros físicos escaneados**, há especialistas como o **pdf-craft** (OCR local, gera sumário e trata notas de rodapé/tabelas).
- **PDF nativo de layout complexo:** vá direto a **Marker** ou **Docling**, que preservam ordem de leitura, títulos, listas e tabelas melhor do que o Calibre.

Exemplo de rota OCR + extração local (ilustrativo):
```bash
# 1) cria camada de texto no PDF escaneado (idioma português)
ocrmypdf -l por entrada_escaneada.pdf com_texto.pdf
# 2) converte para markdown com ferramenta dedicada (ex.: marker)
marker_single com_texto.pdf --output_format markdown --output_dir ./saida_md
```

> **Decisão prática de OSM:** padronize que **PDF escaneado e PDF de layout complexo NÃO passam pelo Calibre** — vão pela Rota C. Isso evita retrabalho e resultados inutilizáveis. O Calibre segue sendo o catálogo onde o *resultado* é registrado (você pode adicionar o `.md` de volta à biblioteca do Calibre para manter os metadados centralizados).

---

## 4. Nomenclatura de arquivos (padrão único Calibre ↔ Obsidian)

Nome de arquivo estável, legível por humano e por máquina, ordenável e sem acento/espaço:

```
[AREA]_[TIPO]_[ANO]_[Titulo-Curto]_[Autor-ou-Orgao].md
```
Exemplos:
- `TRIB_DOUT_2023_Curso-Direito-Tributario_Machado.md`
- `PROC_JURIS_2021_Tema-1234-Repetitivo_STJ.md`
- `ADMIN_LEGIS_1999_Lei-9784-Processo-Administrativo_Uniao.md`
- `TRAB_MODELO_2024_Reclamatoria-Horas-Extras_Interno.md`

Códigos de área e tipo devem sair de uma **tabela canônica** (a mesma da Seção 2.2). Consistência aqui é o que permite busca e automação depois.

---

## 5. Limpeza pós-conversão (obrigatória)

Todo `.md` recém-gerado passa por uma faxina antes de entrar no Obsidian. Idealmente automatize com um script de "normalização de markdown", mas o *checklist* é este:

- Remover **cabeçalhos/rodapés repetidos** e marcações "página X de Y" que a conversão espalhou no corpo.
- Corrigir **hifenizações quebradas** de fim de linha (`respon-\nsabilidade` → `responsabilidade`).
- Normalizar **títulos** (`#`, `##`, `###`) segundo a hierarquia real da obra (Parte → Capítulo → Seção).
- Preservar **notas de rodapé** (importantes em doutrina) e **numeração de artigos/incisos** (crítico em legislação).
- Remover marcas d'água, avisos de copyright repetidos e ruído de OCR (caracteres soltos, `|`, `~` espúrios).
- Conferir **tabelas** e reconstruí-las em markdown quando a conversão as achatou.
- Verificar **encoding UTF-8** (acentuação portuguesa).

> Para leis e acórdãos que servirão de **citação em peças**, faça conferência humana ponto a ponto do trecho que será citado. Fidelidade textual aqui é responsabilidade profissional, não conveniência.

---

## 6. Economia de tokens e performance (o núcleo para uso com IA)

Este é o ponto que separa uma base "que existe" de uma base que **funciona bem e sai barata** com Claude e outros LLMs. Arquivos longos, além de custarem mais, **diluem a atenção do modelo** e pioram a recuperação. Adote a **arquitetura de duas camadas**:

### 6.1 Camada 1 — Nota-índice (curta, densa em metadados)
Para cada obra/documento, uma nota curta (≈ 150–400 palavras) que contém:
- *Frontmatter* YAML completo (Seção 7).
- Um **resumo/abstract** de 3–8 linhas escrito para a IA decidir relevância **sem ler o documento inteiro**.
- **Palavras-chave** e institutos.
- Links para as partes fatiadas (camada 2).

É esta nota que a IA lê primeiro e por padrão. Ela cabe folgadamente no contexto e permite ao agente decidir *se* e *qual parte* do documento longo precisa buscar.

### 6.2 Camada 2 — Documento-fonte fatiado
O texto integral **nunca** vira um único arquivo gigante. Fatie por unidade semântica:
- **Doutrina:** um arquivo por capítulo (ou por seção, se o capítulo for muito longo).
- **Legislação:** por título/capítulo do diploma, ou por artigo quando forem artigos longos e autônomos.
- **Jurisprudência:** ementa + voto condutor em um arquivo; votos divergentes e relatório em arquivos anexos.

Diretrizes de tamanho de fatia:
- Alvo prático: **~500 a 1.500 tokens por fatia** (aprox. 350–1.100 palavras) para pipelines de recuperação (RAG). Se a base for consumida por Claude com contexto grande sem RAG, pode-se usar fatias maiores (por capítulo), mas **nunca o livro inteiro num arquivo só**.
- Use **sobreposição leve** (2–3 frases) entre fatias quando o corte partir um raciocínio.
- Evite fatias que quebrem uma citação legal, uma ementa ou uma tese no meio.

### 6.3 Regras gerais de economia
- **Cabeçalho no topo de cada fatia:** 1–2 linhas identificando obra, capítulo e área, para a fatia ser autoexplicativa fora de contexto.
- **Elimine duplicação:** se três livros repetem o texto de uma lei, guarde a lei **uma vez** e referencie por link, não por cópia.
- **Corte o boilerplate:** prefácios genéricos, listas de abreviaturas repetidas, propaganda editorial — nada disso ajuda a IA e tudo consome tokens.
- **Separe recuperação de leitura:** a IA raciocina sobre as notas-índice (camada 1) e só "abre" a fatia específica (camada 2) quando necessário. Isso reduz drasticamente tokens por consulta.
- **Sinalize status logo no topo** (ex.: `> ⚠️ REVOGADO pela Lei X`) para o modelo não citar norma superada.

---

## 7. Migração para o Obsidian (o "segundo cérebro")

O Obsidian recebe os `.md` limpos e fatiados, replicando **exatamente** a taxonomia do Calibre.

### 7.1 Estrutura de pastas (espelha as áreas)
```
Acervo-Juridico/
├── 00-Indices-MOCs/           (mapas de conteúdo / "coleções")
├── 01-Doutrina/
│   ├── Tributario/
│   ├── Trabalhista/
│   └── ...
├── 02-Legislacao/
├── 03-Jurisprudencia/
├── 04-Modelos-Internos/
├── 05-Administrativo-Extrajudicial/
└── 99-Templates/              (modelos de nota e de frontmatter)
```
> No Obsidian, **pastas são para grandes divisões estáveis**; **tags e links** fazem o trabalho transversal (um livro de "responsabilidade civil ambiental" é tag `responsabilidade-civil` + `ambiental`, mesmo estando na pasta Civil).

### 7.2 Frontmatter YAML padrão (espelha as colunas do Calibre)
Coloque no topo de **toda** nota-índice (e um cabeçalho reduzido nas fatias):
```yaml
---
titulo: "Curso de Direito Tributário"
autor: "Hugo de Brito Machado"
area: [Tributário, Constitucional]
tipo: Doutrina
natureza: Consultivo
orgao: ""
status: Vigente
ano: 2023
fonte: "Ed. Malheiros"
confiabilidade: Doutrinária
tags: [prescricao-tributaria, lancamento, obrigacao-tributaria]
resumo: "Manual de referência sobre sistema tributário nacional; capítulos sobre..."
partes: ["[[TRIB_DOUT_2023_...cap01]]", "[[...cap02]]"]
---
```
As chaves são as **mesmas** dos lookup names do Calibre (`area`, `tipo`, `natureza`, `orgao`, `status`, `ano`, `fonte`) — nenhuma reclassificação é necessária.

### 7.3 MOCs (Maps of Content) = as "coleções/bibliotecas virtuais"
Na pasta `00-Indices-MOCs`, crie notas-mapa por área e por tema, com links para as notas-índice. Exemplo `MOC-Tributario.md`:
- Reúne por instituto, aponta o que está vigente vs. superado, e serve de porta de entrada para a IA navegar sem varrer a base inteira.
- Equivale, no Obsidian, às **Bibliotecas Virtuais** do Calibre. Para dinamismo, use *plugins* de consulta (ex.: Dataview) para montar MOCs automáticos a partir do frontmatter: "listar tudo com `area: Tributário` e `status: Vigente`".

### 7.4 Links e notas atômicas
- Ligue institutos entre si com `[[wikilinks]]` (ex.: uma nota sobre "prescrição" ligada a acórdãos e a capítulos de doutrina que a tratam).
- Para os conceitos mais usados no escritório, crie **notas atômicas** (uma ideia por nota) que sintetizam o entendimento consolidado e apontam para as fontes — são elas que a IA consulta com máxima eficiência de token.

---

## 8. Fluxo-padrão resumido (SOP reproduzível)

Cole isto na parede da equipe. Todo arquivo novo segue **exatamente** estes passos:

1. **Triar** (Seção 1): formato? tem texto? natureza? → registrar na planilha e escolher rota.
2. **Classificar no Calibre**: preencher colunas (`#area`, `#tipo`, `#natureza`, `#orgao`, `#status`, `#ano`...), tags e série.
3. **Converter**:
   - ePUB/MOBI → Rota A (Calibre → markdown).
   - PDF nativo simples → Rota B (PDF → ePUB revisado → markdown).
   - PDF escaneado / layout complexo → Rota C (OCR/Marker/Docling).
4. **Renomear** conforme o padrão `[AREA]_[TIPO]_[ANO]_[Titulo]_[Autor].md`.
5. **Limpar** (Seção 5): rodar normalização + conferência humana de citações críticas.
6. **Fatiar** (Seção 6): separar em nota-índice (camada 1) + fatias (camada 2); inserir cabeçalho e resumo.
7. **Migrar ao Obsidian**: colocar na pasta certa, preencher frontmatter YAML, criar/atualizar links e o MOC da área.
8. **Controle de qualidade**: abrir uma consulta-teste no Claude ("cite o art. X conforme a fonte Y") e conferir se a resposta bate com a fonte. Marcar `confiabilidade: Oficial/Conferida`.

---

## 9. Controle de qualidade e manutenção contínua

- **Auditoria de vigência trimestral:** varra `status` de leis e súmulas; marque revogações/superações. Uma base jurídica desatualizada é passivo, não ativo.
- **Dicionário de tags e tabela de códigos** sob versionamento (uma nota canônica) — revisão mensal para evitar sinônimos divergentes.
- **Log de conversões que falharam** (o *fallback* da Rota C) para não deixar buracos no acervo.
- **Teste periódico com o LLM:** rode um conjunto fixo de perguntas de controle e verifique se as respostas continuam corretas conforme a base cresce.
- **Não delegue à IA a decisão final** sobre fidelidade de citação normativa ou jurisprudencial que irá para peça — a base acelera; o advogado responde.

---

### Anexo — Comando de conversão em lote (referência rápida)
```bash
# Converte todos os .epub de uma pasta para .md (markdown), via Calibre
for f in *.epub; do
  ebook-convert "$f" "${f%.epub}.txt" \
    --txt-output-formatting=markdown \
    --enable-heuristics --keep-links \
    --txt-output-encoding=utf-8 --chapter "//h:h1"
  mv "${f%.epub}.txt" "${f%.epub}.md"
done
```
> Teste sempre numa amostra pequena antes de rodar o lote completo, e reserve a Rota C para os arquivos que falharem ou que sejam PDF escaneado/complexo.

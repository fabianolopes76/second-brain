# 🧠 Kit do Projeto Claude — Refino de OCR com paginação ABNT

## O problema central (leia antes de tudo)

Markdown não tem páginas; PDF tem. Quase todo conversor **descarta a paginação** — e a ABNT (NBR 10520:2023) **exige a página** na citação direta: `(Machado, 2023, p. 45)`.

> **A página não pode ser inferida do texto.** Nem por um humano, nem por um LLM. Se o markdown já perdeu essa informação, ela precisa ser **reinjetada a partir do PDF-fonte** — é o que o script `injetar_paginas.py` faz. Nenhum prompt "esperto" substitui isso: um modelo que "estima" a página está **fabricando** a citação, e isso é inaceitável numa peça processual.

Este kit resolve o problema em três frentes: **âncoras** (`{{p.NN}}`), **instruções que proíbem inventar página** e **scripts que validam**.

---

## O segundo problema: o YAML não é único

O frontmatter YAML é o que faz a base **performar** como segundo cérebro — a IA lê os metadados antes do corpo e decide relevância sem gastar tokens com o texto inteiro. Mas ele **muda conforme o tipo de fonte**:

- **Livro** → cita-se por **página** (`p.`) → precisa de âncora `{{p.NN}}`
- **E-book de leitor** (Kindle) → **não tem página**; cita-se por **posição** (`local.`)
- **Capítulo de livro** → exige `In:` + autoria do todo + intervalo de páginas
- **Artigo de periódico** → exige volume, número, paginação, título do periódico
- **Lei** → entra pela **jurisdição**, traz ementa e cita-se por **artigo** (não por página!)
- **Jurisprudência** → cita-se pelo **julgado** (órgão, processo, relator, data)

Por isso o kit traz um **esquema YAML polimórfico** (`ESQUEMA_YAML_ABNT.md`), exemplos prontos de cada tipo (`EXEMPLOS_YAML_por_Tipo.md`) e um validador que **confere o YAML por tipo e monta a referência sozinho** (`validar_yaml_abnt.py`).

---

## O terceiro problema: dois sistemas de citação

Peça judicial não cita como parecer. A ABNT prevê **dois sistemas de chamada**, e o escritório usa **ambos**:

| Sistema | Forma | Uso |
|---|---|---|
| Autor-data | `(Machado, 2023, p. 33)` | Pareceres, consultas |
| **Numérico (nota de rodapé)** | `MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023. p. 33.` | **Petições** |
| Subsequente | `MACHADO, op. cit., p. 45.` | Repetição em notas |

Por isso o YAML **não fixa** a forma autor-data: ele guarda os **elementos**, e o validador gera **as três formas** a partir deles (`SISTEMAS_DE_CHAMADA.md` traz as regras, inclusive *Ibidem*, *Idem*, *op. cit.*, *loc. cit.*, *passim*, *et seq.*).

---

## ⚠️ Decisão normativa pendente (leia)

O material da UnB sintetiza a **NBR 10520:2002**. Essa norma foi **substituída pela NBR 10520:2023**. A diferença mais visível:

- **2002:** `(SILVA, 2007, p. 30)` — caixa alta
- **2023:** `(Silva, 2007, p. 30)` — maiúsculas e minúsculas

Na **lista de referências**, o autor continua em CAIXA ALTA nas duas versões, e a **NBR 6023:2018** (referências) segue vigente — todo o resto do material da UnB permanece válido.

**Recomendação:** adotar a **2023** (norma em vigor) e registrar no campo `norma_citacao` do YAML. O validador respeita esse campo e gera a citação no formato escolhido — se alguma banca ou tribunal exigir a 2002, basta trocar o valor.

---

## Como montar o Projeto no Claude (5 minutos)

1. **Crie um Projeto** no Claude (ex.: "Refino de Acervo Jurídico").
2. **Instruções personalizadas:** abra `INSTRUCOES_PROJETO.md`, copie tudo entre as linhas `===` e cole no campo de instruções do Projeto.
3. **Conhecimento do Projeto:** anexe estes arquivos:
   - `ESQUEMA_YAML_ABNT.md`  ← **o mais importante**
   - `SISTEMAS_DE_CHAMADA.md`
   - `EXEMPLOS_YAML_por_Tipo.md`
   - `PADRAO_Ancoras_Paginacao_ABNT.md`
   - `CHECKLIST_Refino_OCR.md`
   - `Template_Nota_Indice_ABNT.md`
   - `Template_Fatia_ABNT.md`
   - `PROMPTS_Refino.md`
   - *(opcional, para contexto)* `01_Roteiro_Base_v1_PRESERVADO.md`
4. **Scripts:** ficam na sua máquina (não no Projeto) — você os roda no terminal.
5. **Teste** com um documento pequeno antes de processar o acervo.

---

## Fluxo de trabalho

```
PDF escaneado
    │
    ├─ (1) OCR local ......... ocrmypdf -l por --deskew --rotate-pages in.pdf out.pdf
    │
    ├─ (2) Converter COM páginas .... python scripts/injetar_paginas.py out.pdf -o obra.md
    │                                 └─ ajuste --offset e --romanas-ate até a âncora
    │                                    bater com a página impressa
    │
    ├─ (3) Validar .......... python scripts/verificar_ancoras.py obra.md   →  ✓ OK
    │
    ├─ (4) REFINAR NO PROJETO CLAUDE .... use PROMPTS_Refino.md, do 0 ao 5
    │                                     (limpeza → estrutura → metadados →
    │                                      fatiamento → relatório)
    │
    ├─ (5) Validar de novo ... python scripts/verificar_ancoras.py obra.md --comparar refinado.md
    │                          python scripts/validar_yaml_abnt.py refinado.md --gerar
    │                          └─ âncoras íntegras + YAML completo p/ o tipo de fonte
    │
    └─ (6) Vault do Obsidian ... nota-índice + fatias, prontas para citar
```

**Já tenho markdown convertido, sem páginas?** Vá para o passo (2) usando o **PDF-fonte**. O markdown antigo é descartável — o que importa é preservar a paginação.

---

## Os arquivos deste kit

| Arquivo | O que é | Onde vai |
|---|---|---|
| `INSTRUCOES_PROJETO.md` | Instruções personalizadas do Projeto | Campo de instruções do Claude |
| `ESQUEMA_YAML_ABNT.md` | **YAML por tipo de fonte** (campos, referência, forma de citar) | Conhecimento do Projeto |
| `SISTEMAS_DE_CHAMADA.md` | **Autor-data × nota de rodapé completa** + expressões latinas | Conhecimento do Projeto |
| `EXEMPLOS_YAML_por_Tipo.md` | Frontmatters prontos: livro, e-book, capítulo, artigo, tese, lei, acórdão | Conhecimento do Projeto |
| `PADRAO_Ancoras_Paginacao_ABNT.md` | Sintaxe das âncoras + regras NBR 10520:2023 | Conhecimento do Projeto |
| `CHECKLIST_Refino_OCR.md` | Pipeline de refino, Etapas 0–5 | Conhecimento do Projeto |
| `Template_Nota_Indice_ABNT.md` | Camada 1 (ficha + referência ABNT) | Conhecimento do Projeto |
| `Template_Fatia_ABNT.md` | Camada 2 (trecho + intervalo de páginas) | Conhecimento do Projeto |
| `PROMPTS_Refino.md` | Prompts prontos, etapa por etapa | Conhecimento do Projeto |
| `scripts/injetar_paginas.py` | PDF → Markdown **com** âncoras de página | Sua máquina (terminal) |
| `scripts/verificar_ancoras.py` | Valida integridade das âncoras | Sua máquina (terminal) |
| `scripts/validar_yaml_abnt.py` | Valida YAML por tipo **e gera a referência** | Sua máquina (terminal) |

**Dependências dos scripts:** `pip install pymupdf` (o `verificar_ancoras.py` não precisa de nada).

---

## As três travas de segurança

1. **Instruções proíbem inventar página.** O Claude é instruído a **parar e avisar** quando faltar paginação num documento citável, em vez de produzir uma citação impossível de conferir.
2. **`verificar_ancoras.py` detecta fabricação.** Comparando antes/depois, ele acusa âncora **perdida** e âncora **inventada** — este último é o erro grave, e o script o nomeia como tal.
3. **Conferência humana por amostragem.** Antes de a peça sair, confira 3 páginas contra o PDF. O sistema reduz o trabalho a minutos; a responsabilidade pela citação continua sendo do advogado.

---

## Regras ABNT que o kit já aplica (NBR 10520:2023, vigente desde 19/07/2023)

- Autoria **na citação**: maiúsculas e minúsculas → `(Machado, 2023, p. 45)` *(mudou; antes era caixa alta)*.
- Autoria **na referência**: continua em CAIXA ALTA → `MACHADO, Hugo de Brito. Curso...`
- Ponto final encerra a **frase**, não a citação.
- E-book sem paginação: usar `local.` → `(Dongo-Montoya, 2009, local. 264)`.
- `apud` e `et al.` em **itálico**.

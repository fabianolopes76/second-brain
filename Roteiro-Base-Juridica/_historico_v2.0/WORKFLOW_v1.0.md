---
titulo: "WORKFLOW — Como construir a base de conhecimento (do zero ao segundo cérebro)"
tipo: Runbook operacional
versao: 1.0
data: 2026-07-07
---

# 🗺️ WORKFLOW — Construção da Base de Conhecimento Jurídica

> **O que é este documento.** O caminho completo, em ordem, do arquivo baixado até a base pronta para citar em peça. Cada fase diz **o que fazer**, **qual comando/prompt usar** e **como saber que deu certo**. Os demais arquivos do pacote são a referência de detalhe; este é o mapa.

---

## Visão geral — as 6 fases

```
FASE 0  Preparar          → instalar ferramentas, criar pastas          (uma vez)
   ↓
FASE 1  Triar             → o que é cada arquivo? qual rota?            (por lote)
   ↓
FASE 2  Converter         → PDF/ePUB → Markdown COM localizador         (por lote)
   ↓
FASE 3  Refinar           → limpar OCR + YAML + fatiar (Projeto Claude) (por lote)
   ↓
FASE 4  Validar           → âncoras íntegras + YAML completo            (por lote)
   ↓
FASE 5  Publicar          → montar o vault do Obsidian                  (por lote)
   ↓
FASE 6  Manter            → radar de leis/jurisprudência                (contínuo)
```

**Regra de ouro:** nunca rode uma fase no acervo inteiro sem antes testá-la em **10 arquivos**. Ajuste, depois escale.

---

# FASE 0 · Preparar (uma vez só)

### 0.1 Instalar
| Ferramenta | Para quê | Comando |
|---|---|---|
| **Calibre** | converter ePUB/MOBI | Ubuntu: `sudo apt install calibre` · macOS: `brew install --cask calibre` · Win: `choco install calibre` |
| **OCRmyPDF + Tesseract-pt** | PDF escaneado → legível | Ubuntu: `sudo apt install ocrmypdf tesseract-ocr-por ghostscript` |
| **PyMuPDF** | injetar paginação | `pip install pymupdf` |
| **Obsidian** | o vault (gratuito p/ empresas) | https://obsidian.md |
| **Claude Desktop** | Cowork + Projetos | https://claude.com/download |
| *(opcional)* **Docling** | PDF complexo | `pip install docling` |

> Windows: para OCR, a rota mais estável é **WSL** (`wsl --install`) e depois os comandos de Ubuntu.

### 0.2 Criar a estrutura de pastas
```
/Acervo-Juridico/
├── 0-ENTRADA/           ← tudo que foi baixado, sem tratamento
├── 1-OCR/               ← PDFs escaneados, já com camada de texto
├── 2-MARKDOWN-BRUTO/    ← saída da conversão (com âncoras!)
├── 3-MARKDOWN-LIMPO/    ← após refino no Claude
├── 4-OBSIDIAN-VAULT/    ← o segundo cérebro
├── _ROTEIRO/            ← este pacote + painel-acervo.html
└── _scripts/            ← injetar_paginas.py, verificar_ancoras.py, validar_yaml_abnt.py
```

### 0.3 Montar o Projeto no Claude
1. Criar Projeto → colar `INSTRUCOES_PROJETO.md` (o texto entre `===`) nas instruções.
2. Anexar ao Conhecimento: `ESQUEMA_YAML_ABNT.md`, `SISTEMAS_DE_CHAMADA.md`, `EXEMPLOS_YAML_por_Tipo.md`, `PADRAO_Ancoras_Paginacao_ABNT.md`, `CHECKLIST_Refino_OCR.md`, `PROMPTS_Refino.md`.

### 0.4 Decidir duas coisas (e registrar)
- **Norma de citação:** `NBR 10520:2023` (recomendado — é a vigente) ou `2002`.
- **Sistema de chamada:** `numerico` (peças) · `autor_data` (pareceres) · `ambos`.

✅ **Checkpoint:** `ocrmypdf --version` e `ebook-convert --version` respondem; o Projeto no Claude abre e "conhece" os arquivos.

---

# FASE 1 · Triar

**Objetivo:** saber o que é cada arquivo e para qual rota ele vai. Nada é convertido aqui.

### 1.1 Três perguntas por arquivo

```
                    ┌─ ePUB / MOBI? ────────────────────► ROTA A (Calibre)
                    │
Qual o formato? ────┤            ┌─ TEM texto? ─ simples ► ROTA B (Calibre via ePUB)
                    │            │              └ complexo► ROTA C (Docling/Marker)
                    └─ PDF? ─────┤
                                 └─ NÃO tem texto ────────► ROTA C (OCR primeiro!)
```

**Teste de camada de texto:** `pdftotext -l 2 arquivo.pdf - | head` → se vier vazio, é escaneado.

### 1.2 Prompt (Cowork)
> Percorra `0-ENTRADA/`. Para cada arquivo, monte `controle.csv` com: `arquivo, formato, tem_camada_texto, tipo_fonte_provavel, area_provavel, rota`. Use `pdftotext -l 2` para detectar camada de texto. Classifique a rota como A, B ou C. **Não converta nada** — só a planilha. Mostre um resumo por rota.

### 1.3 Já defina o `tipo_fonte` (isso muda tudo adiante)
| Se for… | `tipo_fonte` | Cita-se por | Precisa de âncora? |
|---|---|---|---|
| Livro impresso/PDF | `livro` | página `p.` | **SIM** |
| E-book Kindle/Kobo | `livro_ebook_leitor` | posição `local.` | Sim (`{{loc.NNNN}}`) |
| Capítulo de coletânea | `capitulo_livro` | página `p.` | **SIM** |
| Artigo de revista | `artigo_periodico` | página `p.` | **SIM** |
| Tese/dissertação | `trabalho_academico` | página `p.` | **SIM** |
| Lei, decreto, código | `legislacao` | **artigo** `art.` | **NÃO** |
| Acórdão, súmula | `jurisprudencia` | o julgado | **NÃO** |
| Portaria, IN, parecer | `ato_administrativo` | artigo `art.` | NÃO |

✅ **Checkpoint:** `controle.csv` revisado por um humano. Corrija classificações estranhas antes de seguir.

---

# FASE 2 · Converter (com o localizador!)

> ⚠️ **O erro que arruína tudo:** converter e **perder a paginação**. Markdown não tem páginas; PDF tem. Sem a página, **doutrina não é citável** — e a página **não pode ser inferida depois**. Converta certo da primeira vez.

### Rota A — ePUB / MOBI
```bash
ebook-convert livro.epub livro.txt \
  --txt-output-formatting=markdown --enable-heuristics \
  --keep-links --txt-output-encoding=utf-8 --chapter "//h:h1"
mv livro.txt livro.md
```
> ePUB não tem página fixa. Se a obra for citável, prefira o **PDF paginado**.

### Rota B — PDF nativo (com texto) → **a rota principal da doutrina**
```bash
python _scripts/injetar_paginas.py livro.pdf -o 2-MARKDOWN-BRUTO/livro.md
```
**Ajuste a numeração** até a âncora bater com a **página impressa** (não a folha do PDF):
```bash
# Ex.: a página impressa "1" é a 13ª folha, e há 14 páginas em romano no prefácio
python _scripts/injetar_paginas.py livro.pdf -o livro.md --offset 12 --romanas-ate 14
```

### Rota C — PDF escaneado ou complexo
```bash
# 1) OCR primeiro (obrigatório em escaneado)
ocrmypdf -l por --deskew --rotate-pages --skip-text 0-ENTRADA/x.pdf 1-OCR/x.pdf
# 2) depois injetar paginação
python _scripts/injetar_paginas.py 1-OCR/x.pdf -o 2-MARKDOWN-BRUTO/x.md
# (layout muito complexo? use docling e reinjete as páginas depois)
```

### Legislação e jurisprudência
Não precisam de âncora de página — **preserve a numeração de artigos/incisos** e os dados do julgado (órgão, processo, relator, data). Esses **são** o localizador.

✅ **Checkpoint:** `python _scripts/verificar_ancoras.py 2-MARKDOWN-BRUTO/` → **Integridade OK**. Abra 1 arquivo e confira: a âncora `{{p.45}}` está mesmo na página 45 do PDF?

---

# FASE 3 · Refinar (no Projeto Claude)

Trabalhe em **lotes pequenos** e use os prompts na ordem.

| Passo | Prompt (resumo) | O que sai |
|---|---|---|
| **3.1 Diagnóstico** | "Faça só o diagnóstico da Etapa 0. Não edite nada." | Tipo, estado do OCR, nº de âncoras, bloqueios |
| **3.2 Limpeza** | "Aplique a Etapa 1: hifenização, cabeçalhos repetidos, ruído. **Preserve** texto do autor, artigos, notas e **todas as âncoras**." | MD limpo |
| **3.3 Estrutura** | "Etapa 2: hierarquia de títulos, listas, tabelas, notas de rodapé." | MD estruturado |
| **3.4 YAML** | "Etapa 3: frontmatter conforme `ESQUEMA_YAML_ABNT.md` para o `tipo_fonte` X." | Metadados + referência ABNT |
| **3.5 Fatiar** | "Etapa 4: nota-índice + fatias de 500–1.500 tokens, com `pagina_inicio`/`pagina_fim`." | Camadas 1 e 2 |
| **3.6 Relatório** | "Etapa 5: liste o que corrigiu e o que exige conferência humana." | Lista de pendências |

### As três travas (o Claude é instruído a respeitá-las)
1. **Não reescreve** texto de autor, lei, ementa ou voto — só conserta o que o OCR quebrou.
2. **Não inventa** página, metadado ou dado. Não localizado = vazio + `A-conferir`.
3. **Para e avisa** se faltar localizador em fonte que o exige.

✅ **Checkpoint:** o relatório de refino lista as pendências, e nenhuma âncora sumiu.

---

# FASE 4 · Validar (a fase que protege a peça)

```bash
# 1) Nenhuma âncora perdida — nem INVENTADA (o erro grave)
python _scripts/verificar_ancoras.py bruto.md --comparar limpo.md

# 2) YAML completo para o tipo + gera as formas de citação
python _scripts/validar_yaml_abnt.py 3-MARKDOWN-LIMPO/ --gerar
```

O validador entrega, prontas:
```
[autor-data]  (Machado, 2023, p. NN)
[nota/peça]   MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed.
              São Paulo: Malheiros, 2023. p. NN.
[subsequente] MACHADO, op. cit., p. NN.
```

### Conferência humana (não pule)
- Pegue **3 trechos** e confira a página contra o PDF.
- Confira a **referência** (autor, edição, editora, ano).
- Só então marque `confiabilidade: Conferida`.

✅ **Checkpoint:** validadores retornam OK **e** a amostragem humana bateu.

---

# FASE 5 · Publicar no vault

### 5.1 Estrutura
```
4-OBSIDIAN-VAULT/
├── 00-Indices-MOCs/    (fontes.md, MOC-Tributario, MOC-Processo-Civil…)
├── 01-Doutrina/        (por área)
├── 02-Legislacao/
├── 03-Jurisprudencia/
├── 04-Modelos-Internos/
└── 99-Templates/       (nota-índice e fatia)
```

### 5.2 Prompt (Cowork)
> Distribua os arquivos de `3-MARKDOWN-LIMPO/` em `4-OBSIDIAN-VAULT/` conforme `tipo` e `area` do frontmatter. Atualize os MOCs da área. Gere `RELATORIO.md` com contagem por área/tipo/status e a lista dos itens `A-conferir`.

### 5.3 Ligar o Obsidian
- Abrir `4-OBSIDIAN-VAULT/` como vault.
- Instalar **Dataview** → os MOCs se preenchem sozinhos.
- Configurar pasta de templates = `99-Templates`.

✅ **Checkpoint:** abrir `MOC-Tributario` e ver os painéis populados.

---

# FASE 6 · Manter (contínuo)

| Ritmo | O quê | Onde |
|---|---|---|
| **Diário** | Briefing de notícias por área | Cowork + `fontes.md` |
| **Semanal** | Sentinela de legislação e jurisprudência (STF, STJ, TRF1, TRT16, TJMA…) → arquivos em `Radar/` | Cowork ou script + cron |
| **Semanal** | Ritual de 30 min: despachar os `⚠️` do radar | Advogado responsável |
| **Trimestral** | Auditoria de vigência de toda `Legislação` e `Súmula` | Dono da área |

Quando uma norma cai ou um entendimento vira, marque no topo da nota:
```markdown
> [!warning] SUPERADO pelo Tema 1234 do STJ (2026-03-10). Não citar sem cautela.
```
E atualize `status:` no YAML. É isso que impede a IA de citar entendimento vencido.

---

# 🚦 Os 5 erros que mais custam caro

| Erro | Consequência | Prevenção |
|---|---|---|
| Converter sem preservar página | Doutrina inutilizável para citação | `injetar_paginas.py` **na conversão** |
| Citar `p.` em e-book de leitor | Citação errada (não há página) | `localizador_tipo: posicao` → `local.` |
| Exigir página de lei | Trava desnecessária | Lei cita-se por **artigo** |
| Deixar a IA "estimar" página | **Citação fabricada em peça** | Instruções proíbem; validador detecta |
| Rodar lote sem testar | Retrabalho em massa | Sempre 10 arquivos primeiro |

---

# 📋 Checklist do lote (imprima e use)

```
LOTE: ______________________  Data: ______  Responsável: __________

[ ] F1  Triado (controle.csv revisado por humano)
[ ] F2  Convertido com localizador correto
[ ] F2  verificar_ancoras.py → Integridade OK
[ ] F3  Refinado no Projeto Claude (Etapas 0–5)
[ ] F4  Comparação antes/depois: 0 âncoras perdidas, 0 inventadas
[ ] F4  validar_yaml_abnt.py → YAML válido para o tipo
[ ] F4  Amostragem humana: 3 páginas conferidas contra o PDF
[ ] F5  Publicado no vault + MOC atualizado
[ ] F5  Itens A-conferir registrados no RELATORIO.md
```

---

> **O princípio que governa tudo:** a base **acelera** a montagem da peça de horas para minutos. A **conferência da citação que vai ao juiz continua sendo do advogado**. O sistema foi desenhado para que essa conferência seja rápida e possível — não para dispensá-la.

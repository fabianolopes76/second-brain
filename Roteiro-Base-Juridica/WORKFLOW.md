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

### 0.1 Instalar — **duas camadas, sem misturar**

> ⚠️ **Regra que evita 90% das dores de cabeça:** ferramentas do **sistema** vêm pelo gerenciador do SO (`apt`/`brew`/`choco`). Ferramentas **Python** vêm num **ambiente virtual (venv) dedicado** — **nunca** com `pip install --user` nem misturadas ao `apt`. Misturar os dois é a causa do incidente documentado no **Apêndice A** (conflito numpy × scipy que derruba o Docling).

**Camada 1 — sistema** (binários; não são Python do seu projeto)
| Ferramenta | Para quê | Comando |
|---|---|---|
| **Calibre** | converter ePUB/MOBI | Ubuntu: `sudo apt install calibre` · macOS: `brew install --cask calibre` · Win: `choco install calibre` |
| **OCRmyPDF + Ghostscript + unpaper** | PDF escaneado → legível | `sudo apt install ocrmypdf ghostscript poppler-utils unpaper` |
| **Tesseract — 6 idiomas** | o acervo é multilíngue | `sudo apt install tesseract-ocr-por tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-spa` |
| **Obsidian** | o vault (gratuito p/ empresas) | https://obsidian.md |
| **Claude Desktop** | Cowork + Projetos | https://claude.com/download |

**Camada 2 — Python, dentro de um venv** (PyMuPDF, Docling, Marker…)
```bash
# 1) criar o ambiente isolado do acervo (uma vez)
python3 -m venv ~/venvs/acervo

# 2) ativar (o prompt passa a mostrar "(acervo)")
source ~/venvs/acervo/bin/activate          # Windows PowerShell: ~\venvs\acervo\Scripts\Activate.ps1

# 3) instalar as ferramentas Python DENTRO do venv
pip install --upgrade pip
pip install pymupdf                          # injetar paginação (essencial)
pip install docling                          # PDF complexo (opcional)

# 4) conferir que está no lugar certo
which python                                 # deve apontar para ~/venvs/acervo/bin/python
python -c "import numpy, fitz; print('numpy', numpy.__version__, '| pymupdf ok')"
```

**Toda vez que for trabalhar no acervo**, ative o ambiente antes:
```bash
source ~/venvs/acervo/bin/activate
# ... rode os scripts ...
deactivate                                   # ao terminar
```

> **Por que o venv resolve:** dentro dele, a pasta do sistema (`/usr/lib/python3/dist-packages`) **não entra** na busca de módulos. Assim, numpy e scipy vêm ambos do venv, em versões que o `pip` escolheu para funcionarem **juntas** — some a possibilidade de choque de versões.

> **Windows:** a rota mais estável para OCR é o **WSL** (`wsl --install`). Nele, use os comandos de Ubuntu acima. Seus arquivos do Windows ficam acessíveis em `/mnt/c/...` — o pipeline funciona normalmente sobre eles.

### 0.2 Criar a estrutura de pastas
```
/Acervo-Juridico/
├── 0-ENTRADA/           ← tudo que foi baixado, sem tratamento
├── 1-OCR/               ← PDFs escaneados, já com camada de texto
├── 2-MARKDOWN-BRUTO/    ← saída da conversão (com âncoras!)
├── 3-MARKDOWN-LIMPO/    ← após refino no Claude
├── 4-OBSIDIAN-VAULT/    ← o segundo cérebro
├── _ROTEIRO/            ← este pacote + painel-acervo.html
└── _scripts/
    ├── aplicar_ocr.sh          ← detecta e OCRiza em lote (Fase 2, rota C)
    ├── injetar_paginas.py      ← PDF → MD COM âncoras de página
    ├── verificar_ancoras.py    ← valida as âncoras
    └── validar_yaml_abnt.py    ← valida o YAML e gera a referência
```

### 0.3 Montar o Projeto no Claude
1. Criar Projeto → colar `INSTRUCOES_PROJETO.md` (o texto entre `===`) nas instruções.
2. Anexar ao Conhecimento: `ESQUEMA_YAML_ABNT.md`, `SISTEMAS_DE_CHAMADA.md`, `EXEMPLOS_YAML_por_Tipo.md`, `PADRAO_Ancoras_Paginacao_ABNT.md`, `CHECKLIST_Refino_OCR.md`, `PROMPTS_Refino.md`.

> ⚠️ **O pacote `tesseract-ocr-por` não vem por padrão.** Sem ele, obras em português são OCRizadas em inglês. Confira com `tesseract --list-langs` — devem aparecer: `deu eng fra ita por spa`.

### 0.4 Decidir duas coisas (e registrar)
- **Norma de citação:** `NBR 10520:2023` (recomendado — é a vigente) ou `2002`.
- **Sistema de chamada:** `numerico` (peças) · `autor_data` (pareceres) · `ambos`.

✅ **Checkpoint da Fase 0:**
```bash
ocrmypdf --version && ebook-convert --version     # sistema OK
source ~/venvs/acervo/bin/activate
which python                                      # → ~/venvs/acervo/bin/python  (NÃO /usr/bin/python3)
python -c "import fitz; print('pymupdf ok')"
```
Se `which python` apontar para `/usr/bin/python3`, o venv **não está ativo** — ative antes de seguir. E o Projeto no Claude abre e "conhece" os arquivos anexados.

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

**Idioma (acervo multilíngue).** O `aplicar_ocr.sh` detecta automaticamente (pt/en/de/fr/it/es) e OCRiza cada obra na língua certa — um livro alemão OCRizado como português vira lixo. Confira antes:
```bash
python3 _scripts/detectar_idioma.py "/mnt/c/.../drive"
```
> **Limite:** PDF escaneado **não tem texto para detectar**. Nesses casos, separe por idioma e force: `OCR_LANG=deu bash _scripts/aplicar_ocr.sh`. Ver `OBRAS_MULTILINGUES.md`.

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
source ~/venvs/acervo/bin/activate          # ← SEMPRE ative o venv antes
python _scripts/injetar_paginas.py livro.pdf -o 2-MARKDOWN-BRUTO/livro.md
```
**Ajuste a numeração** até a âncora bater com a **página impressa** (não a folha do PDF):
```bash
# Ex.: a página impressa "1" é a 13ª folha, e há 14 páginas em romano no prefácio
python _scripts/injetar_paginas.py livro.pdf -o livro.md --offset 12 --romanas-ate 14
```

### Rota C — PDF escaneado ou complexo → **use o `aplicar_ocr.sh`**

O escritório tem um script próprio para esta etapa: **`_scripts/aplicar_ocr.sh`**. Ele varre a pasta, **detecta página a página** quais PDFs realmente precisam de OCR e só OCRiza esses — poupando horas de processamento inútil.

**Por que não basta o `ocrmypdf` cru:** PDFs de tribunal costumam ter **página escaneada com carimbo digital por cima**. Um teste simples de "tem texto?" daria "sim" (o carimbo tem texto) e o corpo do documento continuaria ilegível. O script resolve isso cruzando **pouco texto de corpo** + **imagem grande na página** — e aí sim marca para OCR.

```bash
# 1) SEMPRE comece em dry-run: lista o que faria, sem gravar nada
DRYRUN=1 ROOT="/mnt/c/Users/SeuUsuario/.../drive" bash _scripts/aplicar_ocr.sh

# 2) Rodando de verdade (MANTER o original — ver aviso abaixo)
MODE=manter ROOT="/mnt/c/Users/SeuUsuario/.../drive" bash _scripts/aplicar_ocr.sh
```

> ⚠️ **Use `MODE=manter` no acervo doutrinário.** O `MODE=substituir` **destrói o PDF original** — e o original é a **fonte de verdade** para conferir a página da citação antes de a peça sair. Substituir é aceitável em peças de processo; **não** em livros que serão citados.

**Parâmetros úteis**
| Variável | Quando usar |
|---|---|
| `DRYRUN=1` | **Sempre na primeira rodada.** Só lista. |
| `FORCE_ALL=1` | Ignora a detecção e OCRiza tudo. |
| `OCR_STRATEGY=force-ocr` | Se o `redo-ocr` falhar. Rasteriza tudo: arquivo maior, texto 100% dependente do OCR. |
| `OUTPUT_TYPE=pdf` | Saída menor, sem conversão PDF/A. |
| `PAGE_TEXT_MIN` / `IMG_MIN_DIM` | Afinar a detecção, se estiver classificando errado. |

**Duas finezas do script que vale entender**
- **`rc=10` não é erro.** Significa "PDF válido gerado, mas a conversão para PDF/A falhou" — comum nos PDFs iText dos tribunais. O arquivo está pesquisável e serve. O script trata isso corretamente e **não** cai no fallback à toa.
- **`--deskew` é incompatível com `--redo-ocr`** — o script já remove a flag nesse ramo. Se você editar a estratégia, mantenha esse cuidado.

**Dependências (do SISTEMA, não do venv):**
```bash
sudo apt install -y ocrmypdf tesseract-ocr-por poppler-utils unpaper
```
> `unpaper` é exigido pela flag `--clean`. Sem ele, o script avisa logo no início em vez de quebrar no meio do lote.

### ⚠️ O script entrega PDF pesquisável — **não** entrega markdown citável

Este é o elo que não pode ser esquecido. Depois do OCR, **ainda falta a paginação**:

```bash
source ~/venvs/acervo/bin/activate
python _scripts/injetar_paginas.py livro_OCR.pdf -o 2-MARKDOWN-BRUTO/livro.md
python _scripts/verificar_ancoras.py 2-MARKDOWN-BRUTO/
```

> **Boa notícia:** o OCR **não altera a quantidade nem a ordem das páginas**. As âncoras `{{p.NN}}` geradas depois continuam válidas e correspondem às páginas do original.

### Legislação e jurisprudência
Não precisam de âncora de página — **preserve a numeração de artigos/incisos** e os dados do julgado (órgão, processo, relator, data). Esses **são** o localizador.

✅ **Checkpoint da Fase 2:**
1. `aplicar_ocr.sh` rodou primeiro em `DRYRUN=1` e o relatório fez sentido (nº de "PRECISA OCR" plausível).
2. Os PDFs escaneados agora abrem e permitem **selecionar texto**.
3. `python _scripts/verificar_ancoras.py 2-MARKDOWN-BRUTO/` → **Integridade OK**.
4. Abra 1 arquivo e confira: a âncora `{{p.45}}` está mesmo na **página 45 impressa** do PDF? Se não, reprocesse com `--offset`.

---

# FASE 3 · Refinar

> ⚠️ **Faça a parte mecânica ANTES da IA.** Um livro de 180 mil palavras (~250 mil tokens) **não cabe** num chat de refino de forma útil: custa caro, a IA se perde no contexto longo e o resultado piora. Limpeza e fatiamento são **determinísticos** — resolva-os com script, de graça, e deixe para a IA só o que ela faz melhor (metadados, resumo, julgamento).

## 3a · Limpeza mecânica (script, sem IA)

```bash
python3 _scripts/limpar_ocr.py 2-MARKDOWN-BRUTO/ --inplace
```
Corrige hifenização quebrada, cabeçalhos/rodapés repetidos, números de página soltos, ruído de caractere e linhas partidas por coluna.

**Duas travas de segurança:**
- **Âncoras nunca são tocadas** — o script aborta se perder qualquer uma.
- **Cabeçalho só é removido se estiver colado à quebra de página.** Repetição sozinha não basta: um autor pode repetir uma frase, e apagá-la seria destruir o texto.

## 3b · Fatiamento (script, sem IA)

```bash
python3 _scripts/fatiar.py 2-MARKDOWN-BRUTO/ -o 3-MARKDOWN-LIMPO/ --palavras 1200
```
Gera a **nota-índice** (camada 1) + as **fatias** (camada 2), cortando **em capítulos** e registrando `pagina_inicio`/`pagina_fim` em cada uma. Um livro de 180 mil palavras vira ~150 fatias de leitura rápida — e a IA passa a abrir só a que interessa.

## 3c · Refino no Projeto Claude

Agora sim. Trabalhe em **lotes pequenos** e use os prompts na ordem.

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
| OCRizar obra estrangeira em português | Texto vira lixo; termos técnicos corrompidos | `OCR_LANG=auto` (padrão) ou forçar o idioma |
| IA "corrigir" texto em alemão/francês | **Fonte destruída** | Campo `idioma` no YAML + regra nas instruções |
| Misturar `apt` + `pip --user` | Conversor quebra (numpy × scipy) | **Tudo em venv** — ver Apêndice A |
| `MODE=substituir` no acervo | **Perde o PDF original** — some a fonte de conferência da citação | `MODE=manter` na doutrina |
| Parar no OCR e achar que acabou | PDF pesquisável, mas markdown **sem páginas** → não citável | Rodar `injetar_paginas.py` depois |

---

# 📋 Checklist do lote (imprima e use)

```
LOTE: ______________________  Data: ______  Responsável: __________

[ ] F0  venv ativo (`which python` → ~/venvs/acervo/...)
[ ] F1  Triado (controle.csv revisado por humano)
[ ] F2  aplicar_ocr.sh em DRYRUN=1 primeiro (relatório conferido)
[ ] F2  OCR aplicado com MODE=manter (original preservado)
[ ] F2  injetar_paginas.py rodado sobre o PDF (âncoras criadas)
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

---

# 🔧 Apêndice A · Quando a conversão falha

A conversão é a fase mais frágil do pipeline, porque depende de ferramentas externas. Este apêndice resolve os travamentos mais comuns — e registra os incidentes reais do escritório, para que ninguém perca tempo duas vezes com o mesmo problema.

## A.1 Diagnóstico rápido

```
A conversão falhou. O erro menciona…
│
├─ numpy / scipy / "cannot import name" ──────► A.2  (conflito de ambiente Python)
├─ "command not found" / "não encontrado" ────► A.3  (ferramenta ausente ou venv inativo)
├─ saída vazia ou texto embolado ─────────────► A.4  (PDF escaneado ou layout complexo)
├─ "PriorOcrFoundError" / já tem texto ───────► A.5  (OCR sobre PDF que já tinha texto)
└─ memória / processo morto (killed) ─────────► A.6  (arquivo grande demais)
```

---

## A.2 ⭐ INCIDENTE REGISTRADO — conflito numpy × scipy (Docling não roda)

**Sintoma**
```
ImportError: cannot import name 'Inf' from 'numpy'
```
…ao rodar `docling arquivo.pdf`.

**Causa (o que realmente aconteceu)**
A máquina tinha **dois Pythons misturados**:
- **scipy antigo**, instalado pelo `apt` → `/usr/lib/python3/dist-packages/scipy`
- **numpy novo (2.x)**, instalado por `pip install --user` → `~/.local/lib/python3.10/site-packages/numpy`

O **NumPy 2.0 removeu `numpy.Inf`** (o nome correto passou a ser `numpy.inf`, minúsculo). O scipy antigo ainda tenta `from numpy import Inf` e quebra. O Docling foi só a **vítima** — uma de suas dependências (`transformers`) importa scipy internamente.

> **Não é bug do Docling.** É choque de versões entre pacote do sistema (velho) e pacote do pip (novo). Sempre que o Python monta o `sys.path` com pastas de origens diferentes, ele pode pegar uma peça de cada lugar, sem verificar se combinam.

**Solução definitiva — isolar num venv**
```bash
# 1) ambiente virtual só para o acervo
python3 -m venv ~/venvs/acervo
source ~/venvs/acervo/bin/activate

# 2) instalar do zero, dentro dele
pip install --upgrade pip
pip install docling pymupdf

# 3) conferir que o venv está mesmo ativo
which python                 # → ~/venvs/acervo/bin/python
python -c "import numpy, scipy; print(numpy.__version__, scipy.__version__)"

# 4) rodar normalmente
docling "/mnt/c/Users/SeuUsuario/.../arquivo_OCR.pdf"
```

**Por que funciona (verificado):** dentro do venv, a pasta `/usr/lib/python3/dist-packages` (onde mora o scipy velho do `apt`) **não entra** na busca de módulos. Numpy e scipy passam a vir os dois do venv, em versões que o `pip` resolveu para conviverem.

Comprovação, rodada num venv limpo:
```
numpy no venv: 2.5.1
numpy.Inf  (maiúsculo) existe? False   ← removido no NumPy 2.x — é isto que quebra o scipy antigo
numpy.inf  (minúsculo) existe? True
dist-packages do SISTEMA no sys.path: NENHUM   ← isolamento confirmado ✓
origem do numpy: ~/venvs/acervo/lib/.../site-packages/numpy/__init__.py
```
Você mesmo pode conferir a qualquer momento:
```bash
python -c "import sys; print([p for p in sys.path if 'dist-packages' in p] or 'isolado ✓')"
```

**Uso diário:**
```bash
source ~/venvs/acervo/bin/activate    # antes de trabalhar
# ... conversões ...
deactivate                            # ao terminar
```

**Alternativa rápida (menos segura)**
```bash
pip install --user --upgrade --force-reinstall scipy
```
Costuma resolver na prática, mas é frágil: se outro programa do sistema depender do scipy antigo do `apt`, você pode **quebrar esse outro programa**. Use só como paliativo; a solução correta é o venv, que conserta o acervo sem tocar em nada do resto do sistema.

**Prevenção (adotada na Fase 0.1):** nunca instalar Python do pipeline com `apt` ou `pip --user`. **Tudo no venv.**

---

## A.3 "command not found" — ferramenta ausente ou venv inativo

| Comando que falhou | Verifique |
|---|---|
| `python injetar_paginas.py` | O venv está ativo? `which python` deve apontar para `~/venvs/acervo/...` |
| `docling` | Instalado **dentro** do venv? (`pip list \| grep docling` com o venv ativo) |
| `ocrmypdf` | É do **sistema**: `sudo apt install ocrmypdf` (não vai no venv) |
| `ebook-convert` | Vem com o Calibre: `sudo apt install calibre` |
| `pdftotext` | `sudo apt install poppler-utils` |

> Confusão comum: `ocrmypdf`, `ebook-convert` e `pdftotext` são **do sistema**. `pymupdf`, `docling` e `marker` são **do venv**. Os dois convivem — o venv não atrapalha os binários do sistema.

---

## A.4 Saída vazia ou texto embolado

```bash
# O PDF tem camada de texto? Se não retornar nada, é escaneado.
pdftotext -l 2 arquivo.pdf - | head
```

- **Sem texto (escaneado)** → rode OCR **antes** de qualquer conversão:
  ```bash
  ocrmypdf -l por --deskew --rotate-pages arquivo.pdf arquivo_ocr.pdf
  ```
- **Com texto, mas embolado** (duas colunas, tabelas) → o extrator simples não dá conta. Use o Docling (no venv) e depois **reinjete a paginação**:
  ```bash
  source ~/venvs/acervo/bin/activate
  docling arquivo.pdf --to md --output ./2-MARKDOWN-BRUTO
  python _scripts/injetar_paginas.py arquivo.pdf -o paginado.md   # p/ ter as âncoras
  ```

> ⚠️ **Atenção:** o Docling entrega markdown limpo, mas **sem âncoras de página**. Para doutrina citável, a paginação vem do `injetar_paginas.py` sobre o **PDF-fonte**. Ver Fase 2.

---

## A.5 OCR reclama que o PDF já tem texto

```bash
ocrmypdf -l por --skip-text  entrada.pdf saida.pdf   # pula páginas que já têm texto (recomendado)
ocrmypdf -l por --redo-ocr   entrada.pdf saida.pdf   # refaz o OCR de forma conservadora
ocrmypdf -l por --force-ocr  entrada.pdf saida.pdf   # rasteriza e refaz tudo (último recurso)
```
Arquivos já OCRizados (nomes como `..._OCR.pdf`) normalmente **não precisam** passar por OCR de novo — vá direto ao `injetar_paginas.py`.

---

## A.6 Arquivo grande demais (processo "killed")

- Divida o PDF: `pdftk arquivo.pdf burst` ou `qpdf --split-pages`.
- Rode o Docling em **lotes menores**; ele carrega modelos pesados na memória.
- Se houver GPU disponível, use-a; em CPU, prefira `pymupdf4llm`/`injetar_paginas.py`, que são leves.

---

## A.7 Registro de incidentes (mantenha vivo)

Sempre que um erro novo aparecer e for resolvido, registre aqui. Vale mais que qualquer manual.

| Data | Ferramenta | Sintoma | Causa | Solução |
|---|---|---|---|---|
| 2026-07 | Docling | `ImportError: cannot import name 'Inf' from 'numpy'` | scipy do `apt` (antigo) × numpy 2.x do `pip --user` | venv isolado (A.2) |
| 2026-07 | OCRmyPDF | "Some input metadata could not be copied because it is not permitted in PDF/A" no log, parecendo erro | **Aviso benigno**: metadados XMP malformados da origem não cabem no padrão PDF/A; o PDF gerado está válido e pesquisável. O log do painel misturava stderr sem classificar | `aplicar_ocr.sh` anota a mensagem como `AVISO (inofensivo)`; falha real agora sai com `rc` + motivo (`rc_motivo`); se só a conversão PDF/A falhar, o script tenta `--output-type pdf` para aquele arquivo |
| | | | | |


---

## A.8 Problemas com o `aplicar_ocr.sh`

| Sintoma | Causa provável | Solução |
|---|---|---|
| `unpaper: not found` ou falha na flag `--clean` | `unpaper` não instalado | `sudo apt install -y unpaper` (o script avisa no início) |
| Sai `rc=10` e o arquivo foi gerado | **Não é erro.** PDF válido, mas a conversão PDF/A falhou (típico de PDF iText de tribunal) | Nada a fazer — o arquivo está pesquisável. Se incomodar: `OUTPUT_TYPE=pdf` |
| `--deskew` recusado | `--deskew` é **incompatível** com `--redo-ocr` | O script já remove a flag nesse ramo; não a reintroduza |
| Diz "JÁ PESQUISÁVEL" num escaneado com carimbo | Limiares de detecção frouxos | Baixe `TEXT_FULLPAGE_MIN` (ex.: `TEXT_FULLPAGE_MIN=500`) ou use `FORCE_ALL=1` |
| OCRiza tudo, inclusive PDFs nativos | Limiares apertados | Suba `PAGE_TEXT_MIN` ou revise `IMG_MIN_DIM` |
| Arquivos ficam gigantes | `force-ocr` rasteriza tudo | Volte a `OCR_STRATEGY=redo-ocr`; use `OUTPUT_TYPE=pdf` e `OPTIMIZE=3` |
| Lote demora horas | Normal em acervo grande | Rode por subpasta; o script já mostra o tempo por arquivo |
| Perdi o PDF original | Rodou com `MODE=substituir` | **Sem volta.** Use sempre `MODE=manter` no acervo doutrinário |

## A.9 A sequência completa da rota C (cole e adapte)

```bash
# --- SISTEMA (fora do venv) ---
DRYRUN=1 ROOT="/mnt/c/Users/SeuUsuario/.../drive" bash _scripts/aplicar_ocr.sh   # 1. simular
MODE=manter ROOT="/mnt/c/Users/SeuUsuario/.../drive" bash _scripts/aplicar_ocr.sh # 2. OCR de fato

# --- VENV (Python) ---
source ~/venvs/acervo/bin/activate
python _scripts/injetar_paginas.py livro_OCR.pdf -o 2-MARKDOWN-BRUTO/livro.md    # 3. paginação
python _scripts/verificar_ancoras.py 2-MARKDOWN-BRUTO/                            # 4. validar
deactivate
```
**Sem o passo 3, o PDF fica pesquisável mas o markdown não tem páginas — e a fonte não serve para citação ABNT.**

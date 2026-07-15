---
titulo: "Módulo D — Playbook do Claude Cowork e Ferramentas"
parte_de: "Pacote Base de Conhecimento Jurídica v2.0"
tipo: Guia operacional
data: 2026-07-07
---

# Módulo D — Playbook do Claude Cowork (+ Code e Design)

Este módulo transforma o roteiro em **execução assistida por agente**. A ideia: você define o resultado, aponta o Cowork para a pasta `/Acervo-Juridico/` e ele conduz triagem, conversão, extração de metadados, fatiamento e montagem do vault — com sua supervisão nos pontos críticos.

## O que é o Cowork e como ele se encaixa
O **Claude Cowork** é o modo agêntico do Claude Desktop (planos Pro/Max/Team/Enterprise, Windows e macOS). Diferente do Chat, ele **lê, cria e edita arquivos locais** nas pastas que você autorizar, quebra o trabalho em subtarefas e roda comandos por você. Roda sobre o Opus 4.8.

**Limitações que moldam o playbook (importantes):**
- O **app precisa ficar aberto** durante a execução; fechar encerra a sessão.
- **Sem memória entre sessões** — por isso guardamos as instruções em arquivos (este pacote) que o Cowork relê a cada tarefa.
- **Sigilo:** em *research preview*, auditoria/retenção são limitadas → use para **material público** do acervo; para arquivos de clientes, aplique os controles do Índice-Mestre (aviso 1).
- **Exclusão protegida:** ele pede permissão explícita antes de apagar. Mantenha assim.

**Preparação (uma vez):**
1. Instale/atualize o Claude Desktop (Módulo A, item 11) e rode o "Cowork readiness check".
2. Copie **este pacote inteiro** para dentro de `/Acervo-Juridico/_ROTEIRO/`. Assim o Cowork tem as regras à mão.
3. No Cowork, abra o modo **Tasks** e conceda acesso à pasta `/Acervo-Juridico/`.
4. (Opcional) Ative **Claude in Chrome** como conector se quiser que ele consulte fontes na web durante o trabalho.

> **Dica de ouro:** comece toda tarefa mandando o Cowork **ler `00_INDICE_MESTRE...md` e o módulo relevante** antes de agir. Isso substitui a falta de memória entre sessões.

---

## PASSO 1 — Triagem em lote (montar a planilha de controle)

**Prompt para colar no Cowork:**
> Leia `_ROTEIRO/00_INDICE_MESTRE_e_Guia_Cowork.md` e a Seção 1 do `_ROTEIRO/01_Roteiro_Base_v1_PRESERVADO.md`. Depois percorra a pasta `0-ENTRADA/`. Para cada arquivo, crie uma linha em `controle.csv` com as colunas: `arquivo, formato, tem_camada_texto, natureza_provavel, area_provavel, rota_recomendada`. Para detectar camada de texto em PDFs, use `pdftotext -l 2 <arquivo> -` e verifique se retorna texto. Classifique `rota_recomendada` como: **A** (ePUB/MOBI → Calibre), **B** (PDF nativo simples → Calibre), **C** (PDF escaneado/complexo → OCR+Marker/Docling). Não converta nada ainda — só produza a planilha. Ao final, me mostre um resumo por rota.

Revise a `controle.csv` antes de prosseguir. Corrija classificações que estranhar.

---

## PASSO 2 — OCR dos escaneados (rota C)

**Prompt:**
> Para cada linha de `controle.csv` com `rota_recomendada = C` e `tem_camada_texto = não`, rode `ocrmypdf -l por --deskew --rotate-pages --skip-text` do arquivo em `0-ENTRADA/` para `1-OCR/`, preservando o nome. Registre sucesso/falha numa coluna `ocr_status`. Liste os que falharem para eu revisar manualmente.

---

## PASSO 3 — Conversão para Markdown (rotas A, B e C)

**Prompt:**
> Consulte o `_ROTEIRO/B_Comandos_Multiplataforma.md`. Converta para Markdown em `2-MARKDOWN-BRUTO/`:
> - Rota **A**: `ebook-convert` com `--txt-output-formatting=markdown` (renomeie `.txt`→`.md`).
> - Rota **B**: cadeia PDF→ePUB→Markdown.
> - Rota **C**: use **Docling** (`docling <arq> --to md`) por padrão; se o resultado tiver tabelas quebradas, refaça com **Marker**.
> Primeiro faça **apenas 5 arquivos** de cada rota como amostra e me mostre o resultado. Só depois da minha aprovação, processe o restante.

> **Por que a amostra:** a conversão de PDF varia muito por documento. Aprovar 5 antes de rodar 500 evita retrabalho em massa.

---

## PASSO 4 — Extração de metadados (frontmatter YAML)

Aqui entra a IA "de conteúdo". Use o modelo do **Módulo C** (Gemini 3.5 Flash ou Sonnet 5 para volume).

**Prompt:**
> Consulte a taxonomia da Seção 2 e o padrão de frontmatter da Seção 7.2 do roteiro-base. Para cada `.md` em `2-MARKDOWN-BRUTO/`, leia o começo do documento e preencha um bloco de frontmatter YAML com: `titulo, autor, area (lista), tipo, natureza, orgao, status, ano, fonte, confiabilidade, tags (lista), resumo (3–8 linhas)`. Para `status` de legislação, se identificar revogação/alteração explícita no texto, registre; caso contrário, marque `A-conferir`. Devolva **JSON** com um objeto por arquivo, sem texto extra. Não invente dados: campo desconhecido = string vazia e `confiabilidade: A-conferir`.

Depois:
> Insira cada frontmatter no topo do respectivo `.md` e renomeie o arquivo para o padrão `[AREA]_[TIPO]_[ANO]_[Titulo-Curto]_[Autor].md`, usando os códigos canônicos da Seção 4. Salve em `3-MARKDOWN-LIMPO/`.

---

## PASSO 5 — Limpeza

**Prompt:**
> Consulte a Seção 5 do roteiro-base. Em cada `.md` de `3-MARKDOWN-LIMPO/`: remova cabeçalhos/rodapés repetidos e marcações "página X de Y"; junte hifenizações quebradas de fim de linha; normalize a hierarquia de títulos (`#`, `##`, `###`); preserve notas de rodapé e numeração de artigos/incisos; remova ruído de OCR. **Não** reescreva o conteúdo jurídico nem resuma o corpo — apenas limpe. Gere um `log_limpeza.md` com o que alterou por arquivo.

> **Trava de segurança:** peça explicitamente para **não alterar texto de leis, ementas e teses**. Limpeza ≠ reescrita. Fidelidade textual é inegociável no jurídico.

---

## PASSO 6 — Fatiamento em duas camadas

**Prompt:**
> Consulte a Seção 6 do roteiro-base (arquitetura de duas camadas). Para cada documento longo em `3-MARKDOWN-LIMPO/`, crie:
> 1. Uma **nota-índice** curta (`..._INDICE.md`) com o frontmatter completo, o `resumo`, palavras-chave e uma lista de links `[[...]]` para as fatias.
> 2. As **fatias** por unidade semântica (capítulo/seção para doutrina; título/artigo para legislação; ementa+voto para jurisprudência), com alvo de ~500–1.500 tokens e um cabeçalho de 1–2 linhas identificando obra/capítulo/área. Numere as fatias (`..._p01.md`, `..._p02.md`). Coloque tudo em `4-OBSIDIAN-VAULT/` na pasta da área correspondente. Não fatie no meio de uma citação legal, ementa ou tese.

---

## PASSO 7 — Montagem do vault do Obsidian (o "segundo cérebro")

**Prompt:**
> Consulte a Seção 7 do roteiro-base. Em `4-OBSIDIAN-VAULT/`, crie a estrutura de pastas por área (`01-Doutrina/`, `02-Legislacao/`, `03-Jurisprudencia/`, `04-Modelos-Internos/`, `05-Administrativo-Extrajudicial/`, `00-Indices-MOCs/`, `99-Templates/`). Distribua os arquivos conforme `tipo`/`area` do frontmatter. Em `00-Indices-MOCs/`, gere um MOC por área (`MOC-<Area>.md`) com links para as notas-índice, separando por `status` (Vigente vs. Superado/Revogado). Em `99-Templates/`, salve um template de nota-índice e um de fatia. Ao final, gere um `RELATORIO.md` com contagem por área/tipo/status e a lista de itens com `confiabilidade: A-conferir` para revisão humana.

Depois é só **abrir a pasta `4-OBSIDIAN-VAULT/` como *vault* no Obsidian** e instalar o plugin **Dataview** para MOCs automáticos.

---

## Uso do Claude Code (para o time técnico)
Se houver alguém confortável com terminal, o **Claude Code** (mesma arquitetura, via linha de comando) é ideal para:
- Escrever **scripts reutilizáveis** dos Passos 1–3 (um `pipeline.py`/`pipeline.sh` que você roda quando quiser, inclusive agendado — ver Módulo E).
- Criar um **validador**: script que confere se todo `.md` tem frontmatter completo e nomenclatura correta, e lista os que falham.
- Automatizar a rota de **fallback** (arquivos que o Calibre não converteu → Marker/Docling).

**Prompt (no Claude Code):**
> Crie um script `pipeline.sh` (com versão `.ps1` para Windows) que: (1) roda OCRmyPDF nos PDFs sem texto de `0-ENTRADA/`; (2) converte por rota A/B/C para `2-MARKDOWN-BRUTO/`; (3) registra falhas em `falhas.log`. Comente cada bloco e torne os caminhos configuráveis no topo.

## Uso do Claude Design (apresentação profissional)
O **Claude Design** serve para dar acabamento profissional ao redor da base:
- **Painel de status do acervo** (quantos itens por área, % vigente, pendências) a partir do `RELATORIO.md` — bom para reuniões de gestão.
- **Guia visual de 1 página** do fluxo (as 3 rotas + SOP) para treinar a equipe.
- **Modelo visual de "ficha de obra"** padronizada.

**Prompt (no Design):**
> Com base no `RELATORIO.md`, crie um painel de uma página com: total de documentos, distribuição por área (gráfico de barras), proporção vigente/superado e uma lista das 10 pendências de conferência. Estilo sóbrio, adequado a um escritório de advocacia.

---

## Ritmo de trabalho recomendado
1. **Lote-piloto** (10–20 arquivos) → ajusta prompts e comandos.
2. **Lotes por área** (ex.: primeiro Tributário, depois Trabalhista) → facilita a conferência humana temática.
3. **Revisão humana** dos itens `A-conferir` e de toda citação que irá para peça.
4. **Liga o monitoramento** (Módulo E) para a base não envelhecer.

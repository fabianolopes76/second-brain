---
titulo: "Módulo C — Seleção de Modelos de LLM por Tarefa"
parte_de: "Pacote Base de Conhecimento Jurídica v2.0"
tipo: Referência de decisão
data: 2026-07-07
---

# Módulo C — Qual modelo usar em cada tarefa (Claude + Gemini)

> **Princípio de economia.** O erro de custo mais comum é usar um modelo "topo de linha" para tarefa simples. A regra: **modelo mais barato que resolve bem**; só suba de tier quando a tarefa exigir raciocínio pesado, contexto gigante ou responsabilidade jurídica. A escolha de modelo é a maior alavanca de custo do projeto.

## Referência dos modelos (julho/2026)

**Família Claude (Anthropic):**
- **Opus 4.8** — topo de linha. Melhor para **agentes/computer use** (é o motor do Cowork), raciocínio jurídico complexo, redação e autoverificação. Contexto de 1M tokens. Mais caro.
- **Sonnet 5** — cavalo de batalha equilibrado (qualidade × custo × velocidade). Ideal para volume estruturado.
- **Haiku 4.5** — o mais rápido e barato. Tarefas simples e de altíssimo volume.

**Família Gemini (Google):**
- **Gemini 3.1 Pro** — raciocínio profundo e **contexto líder de mercado (1M+, variantes a 2M)**. Forte multimodal. Bom para ingerir obras inteiras e análise cross-documento.
- **Gemini 3.5 Flash** — workhorse rápido e barato; competitivo em tarefas agênticas; contexto de 1M. Ótimo para volume.
- **Gemini 3.x Flash-Lite** — o mais barato; tarefas leves em massa.

**Diferenciais que orientam a divisão de trabalho:**
- **Claude Opus** brilha em **orquestração agêntica, redação jurídica e verificação**.
- **Gemini Pro** brilha em **contexto máximo e multimodalidade** (ler páginas escaneadas/tabelas como imagem) e em **grounding nativo com Google Search**.
- Para **alto volume estruturado** (classificar, extrair metadados, limpar), os modelos **Flash/Sonnet** dão o melhor custo-benefício.

---

## Matriz tarefa → modelo

| Etapa do pipeline | 1ª escolha | Alternativa | Por quê |
|---|---|---|---|
| **Triagem/detecção** (formato, escaneado?, natureza) | Script + Haiku 4.5 | Gemini Flash-Lite | Decisão simples e volumosa; use o modelo mais barato. Boa parte é heurística sem IA. |
| **OCR de escaneado padrão** | Tesseract (via OCRmyPDF) | — | Não é tarefa de LLM; motor local resolve e preserva sigilo. |
| **OCR/leitura de página complexa** (tabelas, colunas, manuscrito leve) | **Gemini 3.1 Pro** (multimodal) | Marker `--use_llm` | Visão + layout são forças do Gemini Pro; ótimo para o que o Tesseract erra. |
| **Conversão PDF difícil → Markdown** | Marker/Docling (ferramenta) | Gemini 3.1 Pro (páginas soltas) | Ferramenta dedicada é mais barata em escala; Gemini para casos residuais. |
| **Extração de metadados** (área, tipo, órgão, ano, vigência) → JSON | **Gemini 3.5 Flash** ou **Sonnet 5** | Haiku 4.5 | Tarefa estruturada de alto volume; Flash/Sonnet dão precisão a baixo custo. |
| **Limpeza de Markdown** (cabeçalhos, hifenização, ruído OCR) | Haiku 4.5 / Flash-Lite | Sonnet 5 (casos difíceis) | Padrão repetitivo; barato. Sobe de tier só no que resistir. |
| **Fatiamento semântico + resumo/abstract da nota-índice** | **Sonnet 5** ou **Gemini 3.5 Flash** | Opus 4.8 (obras críticas) | Bom custo-benefício em escala; Opus só onde a síntese precisa ser impecável. |
| **Ingestão de obra inteira / análise cross-documento** | **Gemini 3.1 Pro** (contexto 1M–2M) | Opus 4.8 (1M) | Quando é preciso "ler tudo de uma vez", vence o maior contexto. |
| **Orquestração do pipeline (Cowork)** | **Claude Opus 4.8** | — | É o modelo que roda o Cowork; melhor em agentes e autoverificação. |
| **Redação de peças/pareceres a partir da base** | **Claude Opus 4.8** | Sonnet 5 (rascunhos volumosos) | Raciocínio e redação jurídica; Sonnet para primeira versão em massa. |
| **Monitoramento de notícias/jurisprudência (web)** | **Gemini 3.x** (grounding Google Search) + **Claude** (web search) | — | Usar os dois e cruzar reduz falso-negativo (ver Módulo E). |
| **Conferência/verificação de citações** (crítico) | **Opus 4.8** (autoverificação) + **revisão humana** | Gemini 3.1 Pro (2ª opinião) | Etapa de responsabilidade; dupla checagem de IA + humano. |

---

## Estratégia de custo (padrões práticos)

1. **Roteie por dificuldade.** Comece tudo no tier barato (Haiku/Flash-Lite); só encaminhe ao tier alto os itens que a checagem reprovar. Uma "porta" simples: se a extração de metadados vier com campo faltando ou baixa confiança, reprocessa no Sonnet/Gemini Flash.
2. **Cuidado com o "penhasco" de contexto.** No Gemini, passar de ~200 mil tokens **dobra** o preço por token. Não jogue a obra inteira quando a **nota-índice + a fatia certa** resolvem — é exatamente a arquitetura de duas camadas do roteiro-base.
3. **Use processamento em lote quando existir.** A API do Gemini oferece modo *batch* com ~50% de desconto (latência de até 24h). Ideal para a conversão/extração da pilha inicial de arquivos, que não é urgente.
4. **Aproveite cache de contexto.** Para prompts que repetem um mesmo bloco grande (ex.: a mesma taxonomia/instruções de classificação a cada arquivo), o cache reduz muito o custo dos tokens repetidos.
5. **Saída sempre é mais cara que entrada.** Peça saídas **enxutas e estruturadas** (JSON com só os campos necessários; resumos curtos). Resumo de 5 linhas custa uma fração de um resumo de 2 páginas — e serve melhor à base.
6. **Dois provedores = resiliência.** Manter Claude **e** Gemini evita dependência única e permite escolher, por tarefa, quem entrega melhor naquele momento (os líderes se alternam a cada lançamento).

> **Nota de sigilo (repetida do Índice-Mestre):** ao escolher o modelo/provedor para **documentos de clientes**, a decisão não é só custo/qualidade — é também política de retenção, privacidade e conformidade. Prefira processamento local (Tesseract/conversores) para o sigiloso e reserve a IA em nuvem para material público, salvo se houver contrato/plano empresarial com as garantias adequadas.

---
titulo: "Índice-Mestre — Pacote de Roteiros da Base de Conhecimento Jurídica"
versao: 2.0
data: 2026-07-07
tipo: MOC
finalidade: "Guia de navegação e uso do pacote modular com Claude Cowork e demais ferramentas"
---

# 📚 Índice-Mestre — Base de Conhecimento Jurídica (v2.0)

> **O que mudou da v1 para a v2.** A v1 (`01_Roteiro_Base_v1_PRESERVADO.md`) continua **intacta e válida** como espinha dorsal do processo. A v2 **não substitui** a v1 — ela a **complementa** com cinco módulos novos, pedidos expressamente: catálogo de aplicativos, comandos multiplataforma, seleção de modelos de LLM, playbook do Claude Cowork e automações de monitoramento. O conteúdo foi **dividido em arquivos focados** de propósito: arquivos curtos e temáticos rendem muito mais no Cowork e economizam tokens (é a própria filosofia de "duas camadas" do roteiro aplicada ao roteiro).

---

## 🗂️ Mapa do pacote (leia nesta ordem)

| # | Arquivo | O que contém | Quando usar |
|---|---|---|---|
| 01 | `01_Roteiro_Base_v1_PRESERVADO.md` | **Espinha dorsal.** Triagem, taxonomia de metadados, 3 rotas de conversão, nomenclatura, limpeza, fatiamento, economia de tokens, migração ao Obsidian, SOP em 8 passos. | Sempre. É o "porquê" e o "o quê" de tudo. |
| A | `A_Catalogo_de_Aplicativos.md` | Ficha técnica de cada app: gratuito ou não, link oficial, instalação Windows/Ubuntu/macOS, estabilidade e recomendação. | Ao montar as máquinas / decidir o que instalar. |
| B | `B_Comandos_Multiplataforma.md` | Todos os comandos prontos (Calibre, OCRmyPDF, Tesseract, Marker/Docling, lote e renomeação) para **Windows, Ubuntu/Debian e macOS**. | Na hora de executar a conversão/OCR. |
| C | `C_Selecao_de_Modelos_LLM.md` | Matriz tarefa → modelo (Claude **e** Gemini), com justificativa de custo/qualidade/contexto. | Ao decidir qual IA usar em cada etapa. |
| D | `D_Cowork_Playbook_e_Ferramentas.md` | Passo a passo no **Claude Cowork** + uso de Claude Code e Claude Design. Prompts prontos para colar. | Para operar o pipeline com o máximo de automação. |
| E | `E_Automacoes_Monitoramento.md` | Rotinas de **busca de notícias** e **monitoramento de alteração legislativa e jurisprudencial**. | Para manter a base viva e atualizada. |

---

## ⚖️ Três avisos que valem para todo o pacote

1. **Sigilo profissional (crítico para escritório de advocacia).** Ferramentas de IA em nuvem e o Claude Cowork (hoje em *research preview*) são adequadas para tratar **material público** (livros, legislação, jurisprudência publicada, notícias). Para **documentos sigilosos de clientes** (peças em segredo de justiça, dados pessoais sensíveis, estratégia de caso), avalie antes: (a) políticas de retenção e privacidade do provedor; (b) uso de planos **Team/Enterprise** com controles administrativos; (c) processamento **local** sempre que possível (OCR e conversão rodam offline). Trate a confidencialidade como requisito, não como detalhe.
2. **A IA acelera; o advogado responde.** Nenhuma etapa deste pacote substitui a conferência humana de citação normativa ou jurisprudencial que irá para uma peça. A base reduz o tempo de montagem — a responsabilidade técnica permanece com o profissional.
3. **Ferramentas e preços mudam.** Modelos de LLM, versões de software e políticas de licença evoluem rápido. As informações aqui refletem **julho/2026**; confirme links e versões no momento do uso (o Módulo A indica as fontes oficiais).

---

## 🚀 Início rápido (para quem tem "muitos arquivos baixados")

Se o objetivo imediato é **catalogar, converter e ajustar a pilha de arquivos já baixados**, siga este atalho e depois aprofunde nos módulos:

1. **Instale o essencial** (Módulo A): Calibre + OCRmyPDF (com Tesseract-português) + Claude Desktop. Opcional: Marker/Docling para PDFs difíceis.
2. **Organize a pasta de entrada.** Crie a estrutura:
   ```
   /Acervo-Juridico/
   ├── 0-ENTRADA/           (jogue aqui tudo que foi baixado)
   ├── 1-OCR/               (PDFs escaneados após OCR)
   ├── 2-MARKDOWN-BRUTO/    (saída da conversão, antes da limpeza)
   ├── 3-MARKDOWN-LIMPO/    (após limpeza e fatiamento)
   └── 4-OBSIDIAN-VAULT/    ("segundo cérebro" final)
   ```
3. **Abra o Claude Cowork** (Módulo D), aponte para `/Acervo-Juridico/` e use o **Prompt de Triagem em Lote** (Módulo D, Passo 1). Ele classifica cada arquivo por formato, detecta escaneados e monta a planilha de controle.
4. **Converta** seguindo a rota certa (Módulo B) — Cowork pode rodar os comandos por você.
5. **Extraia metadados, fatie e gere resumos** com o modelo indicado (Módulo C) via Cowork (Módulo D, Passos 4–6).
6. **Monte o vault do Obsidian** (Módulo D, Passo 7) e ligue o **monitoramento** (Módulo E).

> **Regra de escala:** teste todo o fluxo em **10–20 arquivos representativos** antes de rodar a pilha inteira. Ajuste os prompts e comandos, e só então processe em lote.

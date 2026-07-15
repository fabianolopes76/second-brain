---
titulo: "Índice-Mestre — Pacote de Roteiros da Base de Conhecimento Jurídica"
versao: 2.1
data: 2026-07-07
tipo: MOC
finalidade: "Guia de navegação e uso do pacote modular com Claude Cowork e demais ferramentas"
---

# 📚 Índice-Mestre — Base de Conhecimento Jurídica (v2.1)

> **Histórico de versões.** A v1 (`01_Roteiro_Base_v1_PRESERVADO.md`) segue **intacta** como espinha dorsal. A v2.0 (módulos A–E) está **preservada** em `_historico_v2.0/`. A v2.1 acrescenta o **painel visual** (`painel-acervo.html`) e os módulos **F, G e H** (aplicação visual, VPS/infraestrutura e UX/UI). Nada foi removido; tudo é aditivo. O conteúdo é dividido em arquivos focados de propósito — arquivos curtos rendem mais no Cowork e economizam tokens (a filosofia de "duas camadas" do roteiro aplicada ao próprio roteiro).

---

## 🖥️ Comece pelo painel
Abra **`painel-acervo.html`** (duplo-clique — funciona offline). Ele é o "cockpit" do acervo: mostra o fluxo, guarda o checklist dos 8 passos, entrega os comandos com botão de copiar e gera o frontmatter YAML padronizado. É a porta de entrada visual para todo o resto. Detalhes no **Módulo F**.

---

## 🗂️ Mapa do pacote

| # | Arquivo | O que contém | Quando usar |
|---|---|---|---|
| — | **`painel-acervo.html`** | **App visual** (offline): fluxo, checklist, central de comandos, gerador de metadados, taxonomia, biblioteca de módulos. | Todo dia, como tela principal de trabalho. |
| 01 | `01_Roteiro_Base_v1_PRESERVADO.md` | **Espinha dorsal.** Triagem, taxonomia, 3 rotas de conversão, nomenclatura, limpeza, fatiamento, economia de tokens, Obsidian, SOP em 8 passos. | Sempre. É o "porquê" e o "o quê". |
| A | `A_Catalogo_de_Aplicativos.md` | Ficha de cada app: gratuito ou não, link, instalação Win/Ubuntu/macOS, estabilidade. | Ao montar as máquinas. |
| B | `B_Comandos_Multiplataforma.md` | Comandos prontos (Calibre, OCRmyPDF, Marker/Docling, lote, renomeação) nos 3 sistemas. | Na hora de executar. |
| C | `C_Selecao_de_Modelos_LLM.md` | Matriz tarefa → modelo (Claude **e** Gemini) com custo/qualidade/contexto. | Ao escolher a IA de cada etapa. |
| D | `D_Cowork_Playbook_e_Ferramentas.md` | Passo a passo no Cowork + Code + Design, com prompts prontos. | Para operar com automação. |
| E | `E_Automacoes_Monitoramento.md` | Busca de notícias e monitoramento de leis/jurisprudência. | Para manter a base viva. |
| **F** | `F_Aplicacao_Visual_Painel.md` | **Como usar e estender o painel** (inclusive via Claude Code). | Para tirar proveito máximo do painel. |
| **G** | `G_VPS_e_Infraestrutura.md` | **O que roda em VPS**, limitações, alternativas e custo-benefício. | Ao decidir infraestrutura/automação. |
| **H** | `H_UX_UI_e_Estrategias.md` | **UX/UI e manutenção**: Obsidian confortável, publicação, rituais. | Para a base ser adotada e não apodrecer. |
| hist | `_historico_v2.0/` | Cópia congelada da versão 2.0. | Referência/auditoria. |

---

## ⚖️ Três avisos que valem para todo o pacote

1. **Sigilo profissional (crítico).** IA em nuvem, Cowork (*research preview*) e VPS são adequados para **material público** (livros, legislação, jurisprudência, notícias). Para **documentos sigilosos de clientes**, avalie antes: políticas de retenção/privacidade do provedor; planos **Team/Enterprise** com controles; e **processamento local** sempre que possível (OCR e conversão rodam offline). Sigilo é requisito, não detalhe.
2. **A IA acelera; o advogado responde.** Nenhuma etapa substitui a conferência humana de citação normativa ou jurisprudencial que irá para peça.
3. **Ferramentas e preços mudam.** As informações refletem **julho/2026**; confirme links, versões e valores no momento do uso (o Módulo A traz as fontes oficiais).

---

## 🚀 Início rápido (para "muitos arquivos baixados")

1. **Instale o essencial** (Módulo A): Calibre + OCRmyPDF (com Tesseract-português) + Claude Desktop + Obsidian.
2. **Abra o painel** (`painel-acervo.html`) para acompanhar o fluxo e ter os comandos à mão.
3. **Monte a estrutura de pastas:**
   ```
   /Acervo-Juridico/
   ├── 0-ENTRADA/           (tudo que foi baixado)
   ├── 1-OCR/               (PDFs escaneados após OCR)
   ├── 2-MARKDOWN-BRUTO/    (saída da conversão)
   ├── 3-MARKDOWN-LIMPO/    (após limpeza e fatiamento)
   ├── 4-OBSIDIAN-VAULT/    ("segundo cérebro")
   └── _ROTEIRO/            (este pacote + o painel)
   ```
4. **Triagem em lote no Cowork** (Módulo D, Passo 1) apontando para `/Acervo-Juridico/`.
5. **Converta** pela rota certa (Módulo B) — Cowork pode rodar por você.
6. **Extraia metadados, fatie e resuma** com o modelo indicado (Módulo C) via Cowork (Passos 4–6). Use o **gerador de frontmatter do painel** para itens avulsos.
7. **Monte o vault** (Módulo D, Passo 7) e deixe-o confortável (Módulo H).
8. **Automatize** o que compensa num **VPS** (Módulo G) e ligue o **monitoramento** (Módulo E).

> **Regra de escala:** teste todo o fluxo em **10–20 arquivos representativos** antes de rodar a pilha inteira.

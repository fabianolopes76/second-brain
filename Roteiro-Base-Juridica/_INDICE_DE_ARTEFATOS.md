# 📦 Base de Conhecimento Jurídica — Índice de Artefatos (v4.4)

Relação consolidada de tudo que foi gerado e validado. Baixe o pacote inteiro (`Base-Conhecimento-Juridica_v2.1.zip`) e mantenha a estrutura de pastas.

## Como está organizado

> **Onde ficam os scripts.** A **fonte única** dos scripts é a **raiz do projeto** (`second-brain/`) — não há cópia dentro do pacote. Ao montar o acervo, copie-os para `/Acervo-Juridico/_scripts/`, que é a convenção de **runtime** usada nos comandos do `WORKFLOW.md` (ex.: `python _scripts/injetar_paginas.py`).

```
second-brain/                              ← RAIZ DO PROJETO
├── acervo_app.py                          ← ⭐ APP de gerenciamento (WSL2 → navegador Windows)
├── LEIA-ME_APP.md                         ← como rodar o app
├── aplicar_ocr.sh                         ← OCR em lote (multi-idioma) + controle.csv
├── detectar_idioma.py                     ← pt/en/de/fr/it/es (amostra o MIOLO)
├── corrigir_idioma.py                     ← conserta idioma já gravado errado
├── preparar.py                            ← ⭐ RODE PRIMEIRO (conserta CRLF do Windows)
├── corrigir_acervo.sh                     ← TUDO de uma vez (idioma+limpar+fatiar+auditar)
├── auditar_acervo.py                      ← ⭐ o gerado SERVE ao segundo cérebro?
├── limpar_ocr.py                          ← limpeza mecânica (sem IA, sem tokens)
├── normalizar_yaml.py                     ← area/tags/autoria no formato do Obsidian
├── fatiar.py                              ← livro grande → índice + fatias
├── injetar_paginas.py                     ← PDF → MD com âncoras {{p.NN}}
├── verificar_ancoras.py                   ← valida âncoras
├── validar_yaml_abnt.py                   ← valida YAML + gera referência
│
└── Roteiro-Base-Juridica/                 ← 📦 PACOTE DE DOCUMENTAÇÃO
    ├── WORKFLOW.md                        ← ⭐ COMECE AQUI (6 fases + Apêndice A: falhas)
    ├── 00_INDICE_MESTRE_e_Guia_Cowork.md  ← mapa do pacote
    ├── painel-acervo.html                 ← APP visual (duplo-clique, offline)
    │
    ├── 01_Roteiro_Base_v1_PRESERVADO.md   ← Roteiro-base (espinha dorsal)
    ├── A_Catalogo_de_Aplicativos.md       ← Apps: licença, links, instalação
    ├── B_Comandos_Multiplataforma.md      ← Comandos Win/Ubuntu/macOS
    ├── C_Selecao_de_Modelos_LLM.md        ← Claude & Gemini por tarefa
    ├── D_Cowork_Playbook_e_Ferramentas.md ← Passo a passo + prompts prontos
    ├── E_Automacoes_Monitoramento.md      ← Radar de notícias/leis/jurisprudência
    ├── F_Aplicacao_Visual_Painel.md       ← Como usar/estender o painel
    ├── G_VPS_e_Infraestrutura.md          ← O que roda em VPS + custo-benefício
    ├── H_UX_UI_e_Estrategias.md           ← UX/UI e manutenção da base
    │
    ├── vault-inicial/                     ← COPIE para o seu vault do Obsidian
    │   ├── _LEIA-ME.md
    │   ├── 00-Indices-MOCs/
    │   │   ├── fontes.md                  ← fontes do radar (STF, STJ, TRF1..6, TRT16, TRE-MA, TJs)
    │   │   ├── MOC-Tributario.md          ← painéis Dataview prontos
    │   │   └── MOC-Processo-Civil.md      ← painéis Dataview prontos
    │   └── 99-Templates/
    │       ├── Template_Nota_Indice.md    ← camada 1
    │       └── Template_Fatia.md          ← camada 2
    │
    ├── projeto-claude-refino/             ← KIT DO PROJETO CLAUDE (refino OCR + ABNT)
    │   ├── _LEIA-ME_Projeto.md            ← comece por aqui
    │   ├── INSTRUCOES_PROJETO.md          ← colar nas instruções do Projeto
    │   ├── ESQUEMA_YAML_ABNT.md           ← YAML POR TIPO DE FONTE (livro/lei/acórdão...)
    │   ├── SISTEMAS_DE_CHAMADA.md         ← AUTOR-DATA × NOTA DE RODAPÉ (peças) + latinas
    │   ├── OBRAS_MULTILINGUES.md          ← pt/en/de/fr/it/es: OCR, refino e ABNT
    │   ├── EXEMPLOS_YAML_por_Tipo.md      ← frontmatters prontos p/ colar
    │   ├── PADRAO_Ancoras_Paginacao_ABNT.md ← âncoras {{p.NN}} + NBR 10520:2023
    │   ├── CHECKLIST_Refino_OCR.md        ← pipeline Etapas 0–5
    │   ├── PROMPTS_Refino.md              ← prompts prontos
    │   ├── Template_Nota_Indice_ABNT.md   ← camada 1 c/ referência ABNT
    │   ├── Template_Fatia_ABNT.md         ← camada 2 c/ intervalo de páginas
    │   └── scripts/                       ← cópia dos 3 scripts do refino (bundle do Projeto)
    │       ├── injetar_paginas.py         ← PDF → MD COM páginas (testado)
    │       ├── verificar_ancoras.py       ← valida âncoras (testado)
    │       └── validar_yaml_abnt.py       ← valida YAML por tipo + gera referência (testado)
    │
    └── _historico_v2.0/                   ← versão anterior congelada (auditoria)
```

## Ordem de uso sugerida
1. **`00_INDICE_MESTRE`** — entenda o mapa e o início rápido.
2. **`painel-acervo.html`** — abra como tela de trabalho.
3. **`A` → `B`** — instale as ferramentas e tenha os comandos à mão.
4. **`D` (+`C`)** — rode o pipeline no Cowork com o modelo certo.
5. **`vault-inicial/`** — copie templates, `fontes.md` e MOCs para o vault.
6. **`E` (+`G`)** — ligue o monitoramento; decida o que automatizar em VPS.
7. **`H`** — deixe a base confortável e mantenha-a viva.

## Status de validação
- Estrutura de pastas conferida (22 arquivos no pacote).
- JavaScript do painel validado (sintaxe OK).
- MOCs com blocos Dataview prontos (Tributário e Processo Civil).
- `fontes.md` com links oficiais verificados (DJEN, STF, STJ) e portais dos tribunais pedidos.
- Versões anteriores preservadas (v1 e v2.0).

> **Lembrete profissional:** a IA acelera; a conferência de citações que vão para peça e a decisão sobre vigência permanecem com o advogado. Material sigiloso de clientes: prefira processamento local.

---
titulo: "Módulo F — Aplicação Visual (Painel de Controle)"
parte_de: "Pacote Base de Conhecimento Jurídica v2.1"
tipo: Guia da ferramenta
data: 2026-07-07
---

# Módulo F — O Painel de Controle do Acervo

O roteiro descreve um processo com muitas etapas. Ler texto é ótimo para entender; **não** é ótimo para operar no dia a dia. O `painel-acervo.html` transforma o roteiro numa **interface** — um "cockpit" que mostra onde o acervo está, entrega o comando certo com um clique e gera metadados padronizados. É o que o pedido chamou de "ambiente visual por meio de aplicação simples".

## O que o painel entrega
- **Fluxo do acervo** — as 5 etapas (Entrada → OCR → Conversão → Curadoria → Vault) com a contagem de arquivos em cada uma. É a visão de status que responde "quanto falta?".
- **Roteiro de execução (SOP)** — os 8 passos como checklist; conforme você marca, o anel de progresso no topo se preenche. Substitui a memória entre sessões: qualquer pessoa vê de onde continuar.
- **Central de comandos** — abas Ubuntu / macOS / Windows; cada comando tem botão **Copiar**. Ninguém precisa decorar a sintaxe do `ocrmypdf` ou do `ebook-convert`.
- **Gerador de metadados** — formulário (área, tipo, órgão, vigência…) que produz o bloco **frontmatter YAML** já no padrão do roteiro, pronto para colar no topo da nota. Padroniza a catalogação e elimina erro de digitação de chave.
- **Taxonomia de referência** — o vocabulário controlado (áreas, tipos, status) sempre à vista, para não inventar sinônimos.
- **Biblioteca de módulos** — cartões que abrem cada `.md` do pacote.

## Como rodar (não precisa instalar nada)
1. Mantenha `painel-acervo.html` **na mesma pasta** dos módulos `.md` (é o que faz os links da biblioteca funcionarem).
2. **Duplo-clique** no arquivo — abre no navegador padrão. Funciona **offline**.
3. O estado (contagens e checklist) fica em memória. Para não perder ao fechar, clique em **Salvar estado** (baixa um `.json`) e, na volta, **Carregar**. Guarde esse `.json` na pasta do acervo ou no vault.

> **Por que salvar em `.json` e não "automático"?** Deixar o estado em arquivo é mais robusto e portátil do que depender de armazenamento do navegador: você pode versionar, compartilhar com a equipe e sincronizar junto com o vault. É uma escolha de confiabilidade, não uma limitação.

## Como o Claude Code cria e evolui este painel
O painel entregue é a **versão 1 — estática e sem dependências** (a mais simples de usar e a mais segura). A partir dela, o time técnico pode pedir ao **Claude Code** melhorias graduais, sem reescrever tudo:

1. **Ler a pasta de verdade (contagens automáticas).** Em navegadores baseados em Chromium, a *File System Access API* permite (com permissão do usuário) apontar para `/Acervo-Juridico/` e o painel conta sozinho os arquivos em `0-ENTRADA`, `1-OCR`, etc. — o "Fluxo do acervo" passa a refletir o disco em tempo real.
   > *Prompt (Claude Code):* "Estenda `painel-acervo.html` para, ao clicar em 'Conectar pasta', usar a File System Access API, pedir acesso a `/Acervo-Juridico/` e preencher as 5 contagens do fluxo com o número de arquivos em cada subpasta. Mantenha compatível com navegadores sem a API (aí segue manual)."
2. **Botões que executam.** Se o painel virar um pequeno app local (ex.: um servidor mínimo em Python/Node que o Claude Code gera), os botões de comando podem **rodar** o `ocrmypdf`/`ebook-convert` de verdade, não só copiar. Útil para quem não quer abrir terminal.
   > *Prompt:* "Crie um servidor local mínimo (`app.py`) que sirva o painel e exponha um endpoint por comando; ao clicar em 'Rodar OCR', ele executa o `ocrmypdf` no arquivo selecionado e devolve o log na tela. Sem dependências além da biblioteca padrão, se possível."
3. **Relatórios ao vivo.** Ler o `RELATORIO.md` gerado no Passo 7 (Módulo D) e desenhar gráficos de distribuição por área/status.
4. **Fila de revisão.** Puxar os arquivos de `Radar/` (Módulo E) e listar as pendências `⚠️` para o advogado despachar.

> **Regra de ouro:** evolua **em cima da versão que funciona**. Cada incremento deve manter o painel abrindo com duplo-clique para quem só quer a versão simples. Complexidade é opcional, nunca obrigatória.

## Relação com Claude Design
Para materiais que saem do dia a dia operacional (uma **apresentação de status** para sócios, um **pôster do fluxo** para a parede, um **one-pager** de onboarding), use o **Claude Design** a partir do `RELATORIO.md`. O painel é a ferramenta de trabalho; o Design é o acabamento de comunicação. Ver Módulo D para prompts.

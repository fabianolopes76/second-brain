---
titulo: "Módulo H — UX, UI e Estratégias de Manutenção"
parte_de: "Pacote Base de Conhecimento Jurídica v2.1"
tipo: Guia de boas práticas
data: 2026-07-07
---

# Módulo H — Tornar a base confortável de usar (UX/UI) e viva

Uma base de conhecimento só entrega valor se as pessoas **conseguem e gostam** de usá-la. Este módulo reúne estratégias para que o "segundo cérebro" seja intuitivo tanto para a **equipe** quanto para as **IAs** (Claude e Gemini), e para que ele **não apodreça** com o tempo.

## Princípio: três públicos, uma base
1. **A IA** precisa de estrutura, metadados e blocos curtos (a arquitetura de duas camadas do roteiro-base).
2. **A equipe técnica/paralegal** precisa de fluxo claro e ferramentas que não exijam decorar comandos (o painel do Módulo F).
3. **O advogado/sócio** precisa de **acesso rápido, leitura confortável e confiança** no que está vendo (vigência sinalizada, fonte citável).
Desenhar para os três ao mesmo tempo é o que diferencia uma base "que existe" de uma base "que é usada".

---

## A. O Obsidian como interface principal (UX de quem consulta)

O vault é a UI diária. Vale investir em configurá-lo para conforto:

- **Templates prontos** (plugin *Templater* ou o nativo *Templates*): botão que cria uma nota-índice ou uma fatia já com o frontmatter padrão. Elimina página em branco e padroniza.
- **Dashboards com Dataview:** notas que se montam sozinhas a partir do frontmatter. Exemplos úteis:
  - "Legislação a conferir" → lista tudo com `status: A-conferir`.
  - "Novidades da semana" → lista notas criadas nos últimos 7 dias por área.
  - "Por área" → índice automático que sempre reflete o acervo, sem manutenção manual.
- **MOCs (Mapas de Conteúdo)** como porta de entrada por área e por tema — a "capa" navegável que evita varrer pastas.
- **Propriedades (Properties) e a visão de Bases:** o Obsidian moderno mostra o frontmatter como campos editáveis e permite visões tipo tabela/kanban do acervo — ótimo para curadoria em lote.
- **Busca e atalhos:** ensine a *Quick Switcher* (abrir nota por nome) e a busca por propriedade (`status:Revogado`). Dois atalhos resolvem 80% das consultas.
- **Graph view com moderação:** bonito para enxergar conexões entre institutos; mantenha como recurso de exploração, não como navegação principal.
- **Sinalização de vigência no topo da nota:** um *callout* padronizado (`> [!warning] SUPERADO pelo Tema X`) que a equipe e a IA leem de imediato. Consistência visual vira confiança.

> **UI de qualidade também é disciplina de conteúdo:** nomes de arquivo estáveis, tags do dicionário canônico, resumos curtos no topo. A melhor interface é uma base bem-arrumada.

---

## B. Publicar o vault para leitura (UX de quem não mexe no Obsidian)

Nem todo mundo no escritório vai abrir o Obsidian. Para sócios e áreas de apoio, publicar o vault como **site de leitura** é um salto de UX:

- **Quartz** (gerador de site estático feito para Obsidian): transforma o vault num site rápido, com busca, backlinks e índice — hospedável de graça (Cloudflare Pages/GitHub Pages) ou num VPS (Módulo G). Mantém os links `[[...]]` funcionando.
- **Obsidian Publish** (add-on pago oficial): mais simples de ligar, sem administrar hospedagem, se preferir pagar em vez de configurar.
- **Cuidado de sigilo:** publique **apenas** o subconjunto público (doutrina, legislação, jurisprudência, guias internos). Material sigiloso **nunca** vai para site. Uma boa prática é ter um vault público e um privado, ou uma pasta marcada como "não publicar".

Resultado: qualquer pessoa acessa a base por um link, pesquisa em linguagem natural e lê com conforto — sem instalar nada.

---

## C. Estratégias de manutenção (para a base não morrer)

1. **Ritual semanal de radar** (Módulo E): 20–30 min do responsável para despachar os `⚠️` de legislação/jurisprudência. Curto e recorrente vence "faxina anual".
2. **Auditoria trimestral de vigência** de todo `tipo: Legislação` e `tipo: Súmula`.
3. **Dono por área.** Cada macroárea tem um responsável pela curadoria — a base sem dono vira depósito.
4. **Higiene de tags:** revisão mensal do dicionário canônico; una sinônimos (`resp-civil` → `responsabilidade-civil`).
5. **Padrão de entrada única:** todo arquivo novo passa pelo mesmo funil (`0-ENTRADA` → pipeline). Nada entra "pela porta dos fundos" sem metadados.
6. **Versionamento com Git:** o vault em Git dá histórico, desfazer e trabalho em equipe. Some com "qual é a versão certa deste arquivo?".
7. **Métrica simples de saúde:** no painel/relatório, acompanhe % de itens `Conferido` vs `A-conferir` e nº de pendências de radar. Uma base saudável tende a 0 pendências antigas.

---

## D. Onboarding (para a equipe adotar)

- **Guia visual de 1 página** (Claude Design) com o fluxo e os 8 passos — na parede e no vault.
- **O painel (Módulo F)** como primeira tela: quem chega entende o processo sem ler tudo.
- **Um caso-exemplo completo** no vault (uma obra do início ao fim) como referência de "assim fica pronto".
- **Regra dos 5 minutos:** se uma tarefa recorrente leva mais de 5 minutos de trabalho manual repetitivo, vira prompt de Cowork ou script (Claude Code). Automatize o tédio, preserve o julgamento humano.

---

## E. Estratégias avançadas (quando amadurecer)

- **RAG dedicado:** quando o acervo ficar grande, um índice vetorial (via Docling/LangChain/LlamaIndex, Módulo A/C) permite perguntas em linguagem natural com recuperação precisa — a camada 1 (notas-índice) já foi desenhada pensando nisso.
- **Plugins de conector:** empacotar as skills, conectores e sub-agentes do escritório num *plugin* de Cowork faz o Claude "chegar como especialista" no seu domínio desde o primeiro uso.
- **Dois provedores por padrão:** manter Claude **e** Gemini (Módulo C) dá resiliência e permite escolher o melhor por tarefa — os líderes se revezam a cada lançamento.
- **Excalidraw/Canvas** no Obsidian para mapear teses e estratégias de caso visualmente, ligando aos documentos-fonte.

---

### O fio condutor
Boa UX aqui não é enfeite: é **menos atrito para fazer a coisa certa**. Nomes estáveis, metadados consistentes, um painel que entrega o comando pronto, um site para quem só lê, e rituais curtos de manutenção. Com isso, o "segundo cérebro" deixa de ser um projeto e vira **hábito** — que é quando ele passa a devolver tempo ao escritório todos os dias.

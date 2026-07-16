# Changelog

Todas as mudanças relevantes do projeto, por versão. O formato segue
[Keep a Changelog](https://keepachangelog.com/pt-BR/) e o versionamento é
[semântico](https://semver.org/lang/pt-BR/): MAIOR.MENOR.CORREÇÃO.
Cada versão corresponde a uma tag git (`git tag -l`).

## [3.6.0] — 2026-07-16 · Layout do painel: Ambiente em slideover

### Alterado
- **Ambiente virou um painel lateral (slideover)**, aberto pelo botão
  `⚙ Ambiente` na Configuração — o botão é o semáforo: **verde** quando
  todas as dependências estão prontas, **vermelho** com a contagem de
  pendências quando precisa de ação (fecha no ✕ ou com Esc).
- **Execução subiu para logo abaixo da Configuração** (novo fluxo visual:
  01 Configuração · 02 Execução · 03 Pipeline · 04 Triagem).

### Adicionado
- **Advertência sob o campo "Pasta do acervo"**: clicar em Definir sem
  escolher a pasta mostra o aviso em vermelho abaixo do input; ele some
  assim que uma pasta é escolhida no navegador ou digitada.

## [3.5.2] — 2026-07-16 · Correção do inicializador no WSL2

### Corrigido
- `iniciar-acervo.sh`: no WSL2, o `xdg-open` era escolhido primeiro e
  procurava navegador DENTRO do Linux — despejava uma cascata de
  "not found" e não abria nada. Agora o WSL é detectado e o navegador do
  **Windows** é aberto (wslview → powershell.exe → explorer.exe, inclusive
  por caminho absoluto quando o PATH de interop não está disponível);
  em último caso, imprime a URL para abrir manualmente. O servidor nunca
  foi afetado — o defeito era só na abertura automática do navegador.

## [3.5.1] — 2026-07-15 · Higiene interna (DRY nas bordas)

### Adicionado
- **`comum.py`** — utilitários compartilhados (`vazio`, `IGNORAR_PASTAS`,
  regex `WIKILINK`, `alvo_wikilink`): a cópia única do que estava nascendo
  duplicado em 3-4 módulos — o mesmo mecanismo que gerou os quatro parsers
  divergentes que a v3.0.0 matou.

### Alterado
- `validar_yaml_abnt`, `auditar_acervo`, `auditar_vault`, `publicar`,
  `radar` e o app passam a importar de `comum` (comportamento provado
  idêntico contra o oráculo de regressão).
- `triagem.py` usa `argparse` como os demais scripts (CLI compatível —
  mesmas chamadas do `aplicar_ocr.sh`).

### Corrigido
- `publicar.py` fazia `import re` dentro de laço e refazia inline a
  extração de wikilink que já existia no auditor de grafo.

## [3.5.0] — 2026-07-15 · Documentação visual e inicializadores

### Adicionado
- **`GUIA-VISUAL.md`** — manual completo de uso **sem linha de comando**:
  o painel tela a tela, os 3 estados das etapas, o dia a dia em 8 cliques,
  Obsidian sem terminal e solução de problemas visual.
- **`Iniciar-Acervo.bat`** (Windows/WSL2) e **`iniciar-acervo.sh`** (Linux):
  duplo-clique sobe o servidor e abre o navegador sozinho.
- **`CHANGELOG.md`** e tags semânticas retroativas (v2.1.0 → v3.4.0).

## [3.4.0] — 2026-07-15 · Fase 5: Radar (etapa 10)

### Adicionado
- **`radar.py`** — correlação determinística dos achados de `Radar/`
  (produzidos pelo Cowork, Módulo E) com as notas que os citam, por
  **identificadores fortes** (Lei/Decreto/MP/EC/Tema/Súmula/nº CNJ —
  padrões do perfil). Gera a fila de revisão (`RELATORIO-RADAR.md`);
  `--aplicar` sinaliza `status: A-conferir` (o radar sinaliza, o humano
  decide). Idempotente entre ciclos (`.radar_estado.json`).
- App: **etapa 10 · Radar** (fase Manutenção), contadores de achados
  novos, carimbo de data.

## [3.3.0] — 2026-07-15 · Fase 4: MOCs geráveis com curadoria preservada

### Adicionado
- **`gerar_moc.py`** — cria/regenera MOCs em duas camadas: painéis
  Dataview entre marcadores `<!-- moc:auto:inicio/fim -->` (único trecho
  regenerável) × curadoria manual (nunca tocada; sem marcadores, o script
  **recusa** regenerar). Filtro de área é um **predicado** Dataview
  persistido no frontmatter (`moc_predicado`).
- Perfil: `status_ok/status_pendencia/status_superado/moc_grupos`
  (painéis parametrizados por domínio).

### Alterado
- MOCs de Tributário e Processo Civil migrados (marcadores + predicado;
  conteúdo intocado — diff de 6 linhas cada).

## [3.2.0] — 2026-07-15 · Fase 3: Publicação determinística + travas do trilho

### Adicionado
- **`publicar.py`** — a Fase 5 do WORKFLOW por regra, não por LLM:
  roteamento tipo→pasta do perfil (doutrina por área; interno →
  04-Modelos-Internos), fatias junto do índice. **Três travas**: nota
  reprovada não publica; copiar, nunca mover; **em conflito o vault vence**
  (curadoria humana) — `--force` para sobrescrever conscientemente.
  Idempotente; gera `RELATORIO-PUBLICACAO.md`.
- App: **etapa 8 · Publicar** (Simular/Publicar) e renumeração da
  auditoria de grafo para **etapa 9**.
- Trilho: **trava de reexecução** (etapa concluída pede confirmação) e
  **badges com carimbo de data** (derivado do mtime dos artefatos).
- Perfil: `pastas_publicacao` / `pastas_por_area`.

## [3.1.0] — 2026-07-15 · Fase 2: Auditoria do grafo do vault

### Adicionado
- **`auditar_vault.py`** — o validador de **ligações** que nenhuma checagem
  arquivo-a-arquivo enxerga: fatia órfã, `partes:` ≠ fatias reais, par
  `tipo`/`tipo_fonte` incoerente, vocabulário fora do perfil (a nota
  **some** dos painéis Dataview), nota sem `area`, nome duplicado,
  wikilink quebrado, área sem MOC. Gera `RELATORIO-VAULT.md`; sai com
  código 1 se houver erro.
- App: etapa de auditoria do vault no trilho (fase Publicação).
- `corpus-vault/` — vault sintético com erros plantados (fixture de
  regressão do auditor).
- `README.md` — documentação completa do projeto (usuário + dev).

## [3.0.0] — 2026-07-15 · Fase 1: Taxonomia canônica (BREAKING)

A fundação. Vocabulário e parser deixam de existir em cópias divergentes
espalhadas pelos scripts e passam a ter **fonte única**.

### Adicionado
- **`taxonomia.py`** — fonte única de vocabulário, arquitetura
  **núcleo × perfil**: núcleo ABNT invariante (16 tipos de fonte,
  localizadores, âncoras, idiomas, dívida `TOLERADOS`) × perfil de domínio
  (`juridico` é o primeiro: áreas, eixo `tipo`, status, códigos de nome,
  heurísticas de triagem). Autoteste embutido (`--autoteste`);
  `ACERVO_ESTRITO=1` pré-visualiza a régua completa.
- **`frontmatter.py`** — parser único (blocos `>`/`|`, listas) +
  serializador seguro — substitui 4 parsers divergentes.
- **`triagem.py`** — classificação por **nome + conteúdo** com confiança
  (alta/media/baixa) e **sem fallback cego para "livro"**.
- `corpus/` — 18 fixtures de caracterização (oráculo de regressão).
- 5 tipos novos no vocabulário: `verbete`, `norma_tecnica`, `audiovisual`,
  `correspondencia` (prometidos pela doc, rejeitados pelo validador) e
  `peca_interna` (ex-tipo-fantasma; casa de `tipo: Modelo`, não-ABNT).

### Corrigido
- **`fatiar.py` destruía `area:` em bloco multi-linha** → a fatia nascia
  sem área e ficava **invisível nos MOCs** (bug de produção).
- Nenhuma jurisprudência passava na checagem de `localizador_abrev`
  (`""` era lido como `None`) — erro falso histórico.
- `injetar_paginas.py` carimbava `localizador_tipo: pagina` em tipo
  desconhecido (default perigoso).
- Aviso benigno do OCRmyPDF sobre metadados XMP/PDF-A parecia erro no
  painel — agora anotado `AVISO (inofensivo)`; falhas reais saem com
  código e motivo (`rc_motivo`); retry por arquivo com `--output-type pdf`.
- `normalizar_yaml.py` injetava `status: Vigente` cegamente — agora
  `A-conferir` (script não afirma vigência que não conhece).
- Templates geravam notas que **falhavam no validador** (`autor` string,
  sem `tipo_fonte`) — alinhados à taxonomia **junto** com os MOCs (que
  exibiam os campos antigos).

### Alterado (BREAKING)
- Todos os scripts passam a importar `taxonomia`/`frontmatter` — cópias
  locais de vocabulário removidas (5 cópias de `tipo_fonte`, 5 de idioma,
  4 parsers, 2 heurísticas de triagem).
- MOCs: colunas `autor`/`fonte` → `autoria_citacao`/`editora`.

## [2.1.0] — 2026-07-07 · Baseline

Estado consolidado anterior à taxonomia: pipeline OCR→Markdown→vault
funcional (pacote de documentação `Base-Conhecimento-Juridica v2.1`),
app `acervo_app.py` com trilho de 7 etapas, scripts com vocabulários
duplicados (o problema que a v3 resolve).

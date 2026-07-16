# Acervo — segundo cérebro para bases de conhecimento

**Versão 3.6.0** · [Changelog](CHANGELOG.md) · **[🖱️ Guia Visual — usar sem linha de comando](GUIA-VISUAL.md)**

Pipeline completo que transforma documentos (PDF, ePUB) em uma **base de conhecimento navegável no Obsidian**, pronta para consulta por humanos e por IA — com metadados ABNT validados, âncoras de página para citação e mapas de conteúdo (MOCs) que se atualizam sozinhos.

O primeiro perfil de uso é **jurídico** (doutrina, legislação, jurisprudência, com citação NBR 10520/6023), mas a arquitetura é **multi-domínio**: o núcleo do pipeline é neutro e cada área do conhecimento entra como um *perfil* — ver [Arquitetura](#arquitetura-núcleo--perfil).

> **O princípio que governa tudo:** os MOCs do Obsidian se preenchem automaticamente (plugin Dataview) filtrando o frontmatter das notas (`area`, `tipo`, `status`, `confiabilidade`). **Metadado errado = a nota some dos painéis sem nenhum erro visível.** Por isso este pipeline valida vocabulário e integridade em cada etapa — e por isso a fonte única de vocabulário (`taxonomia.py`) é o coração do projeto.

---

## Sumário

- [Como funciona (visão geral)](#como-funciona-visão-geral)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Instalação](#instalação)
- [Uso — pelo app (recomendado)](#uso--pelo-app-recomendado)
- [Uso — pela linha de comando](#uso--pela-linha-de-comando)
- [O vault do Obsidian](#o-vault-do-obsidian)
- [Guia do desenvolvedor](#guia-do-desenvolvedor)
- [Roadmap](#roadmap)
- [Solução de problemas](#solução-de-problemas)

---

## Como funciona (visão geral)

```
FASE 0  Preparar   → instalar ferramentas, criar pastas             (uma vez)
FASE 1  Triar      → o que é cada arquivo? tipo + rota + idioma     (por lote)
FASE 2  Converter  → PDF/ePUB → Markdown COM âncoras de página      (por lote)
FASE 3  Refinar    → limpar OCR + YAML ABNT + fatiar                (por lote)
FASE 4  Validar    → âncoras íntegras + YAML completo por tipo      (por lote)
FASE 5  Publicar   → montar o vault do Obsidian (MOCs Dataview)     (por lote)
FASE 6  Manter     → radar de novidades + auditoria de vigência     (contínuo)
```

O runbook operacional completo, fase a fase, com comandos e checkpoints, está em **[Roteiro-Base-Juridica/WORKFLOW.md](Roteiro-Base-Juridica/WORKFLOW.md)** — comece por ele.

Duas regras de ouro do domínio jurídico (perfil atual):

1. **Nunca converta perdendo a paginação.** Markdown não tem páginas; sem a âncora `{{p.NN}}`, doutrina não é citável — e a página não pode ser inferida depois. O `injetar_paginas.py` resolve isso na conversão.
2. **Lei cita-se por artigo, acórdão pelo julgado** — não exigem âncora de página. O campo `tipo_fonte` determina o que cada documento precisa, e o validador cobra exatamente isso.

## Estrutura do repositório

```
second-brain/
├── acervo_app.py            ⭐ APP de gerenciamento (servidor local + painel no navegador)
├── Iniciar-Acervo.bat       🖱️ Duplo-clique (Windows/WSL2): abre o painel sem terminal
├── iniciar-acervo.sh        🖱️ Duplo-clique (Linux): idem
├── GUIA-VISUAL.md           🖱️ Manual de uso SEM linha de comando (tela a tela)
├── CHANGELOG.md             Histórico de versões (tags semânticas no git)
├── LEIA-ME_APP.md           Como rodar e usar o app
│
├── taxonomia.py             ⭐ FONTE ÚNICA de vocabulário (núcleo ABNT × perfis de domínio)
├── frontmatter.py           Parser/serializador ÚNICO de frontmatter YAML
├── comum.py                 Utilitários compartilhados (vazio, pastas ignoradas, wikilink)
├── triagem.py               Classificação de tipo (nome + conteúdo, com confiança)
│
├── aplicar_ocr.sh           OCR em lote multi-idioma + controle.csv (triagem)
├── detectar_idioma.py       Detecta pt/en/de/fr/it/es pelo miolo do texto
├── corrigir_idioma.py       Conserta idioma gravado errado no YAML
├── injetar_paginas.py       PDF → Markdown COM âncoras {{p.NN}}
├── limpar_ocr.py            Limpeza mecânica do OCR (sem IA, preserva âncoras)
├── fatiar.py                Livro grande → nota-índice + fatias de ~1.200 palavras
├── normalizar_yaml.py       Normaliza area/tags/autoria para o formato do Obsidian
├── verificar_ancoras.py     Valida âncoras (inclusive contra âncora INVENTADA)
├── validar_yaml_abnt.py     Valida o YAML por tipo_fonte + gera a referência ABNT
├── auditar_acervo.py        O arquivo gerado SERVE ao segundo cérebro? (nota por arquivo)
├── auditar_vault.py         O GRAFO do vault está íntegro? (ligações entre notas)
├── publicar.py              FASE 5 determinística: 3-MARKDOWN-LIMPO → vault, por regra
├── gerar_moc.py             Cria/regenera MOCs preservando a curadoria manual
├── radar.py                 FASE 6: correlaciona achados do radar às notas (por identificador)
├── preparar.py              ⭐ RODE PRIMEIRO se baixou pelo Windows (conserta CRLF/+x)
├── corrigir_acervo.sh       Encadeia idioma+limpar+fatiar+auditar de uma vez
│
├── corpus/                  Fixtures de teste (oráculo de regressão — ver Guia do dev)
├── corpus-vault/            Vault sintético: fixtures do auditor de grafo
└── Roteiro-Base-Juridica/   📦 Documentação completa do método (perfil jurídico)
    ├── WORKFLOW.md          ⭐ runbook: as 6 fases + Apêndice A (falhas e incidentes)
    ├── 00_INDICE_MESTRE...  Mapa do pacote de documentação
    ├── A_ ... H_*.md        Módulos: apps, comandos, LLMs, Cowork, automação, painel...
    ├── painel-acervo.html   Painel visual estático (duplo-clique, offline)
    ├── vault-inicial/       MOCs prontos + templates para copiar ao seu vault
    ├── projeto-claude-refino/  Kit do Projeto Claude (refino OCR + esquema YAML ABNT)
    └── _historico_v2.0/     Versão anterior congelada (auditoria)
```

## Instalação

Duas camadas, **sem misturar** (a mistura `apt` × `pip --user` é a causa do incidente numpy×scipy documentado no [Apêndice A.2 do WORKFLOW](Roteiro-Base-Juridica/WORKFLOW.md)):

```bash
# 1) Ferramentas de SISTEMA (Ubuntu/WSL2)
sudo apt install -y ocrmypdf ghostscript poppler-utils unpaper calibre
sudo apt install -y tesseract-ocr-por tesseract-ocr-eng tesseract-ocr-deu \
                    tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-spa

# 2) Python em venv DEDICADO (nunca pip --user)
python3 -m venv ~/venvs/acervo
source ~/venvs/acervo/bin/activate
pip install pymupdf          # única dependência Python do pipeline (conversão PDF)
deactivate
```

> **Os scripts do repositório são stdlib-only** — não exigem pip nenhum. O venv serve apenas ao `injetar_paginas.py` (PyMuPDF) e a conversores opcionais (Docling).

**Baixou pelo Windows?** Rode primeiro `python3 preparar.py` (conserta CRLF no shebang, permissão de execução e `Zone.Identifier`).

## Uso — pelo app (recomendado)

O app orquestra o pipeline inteiro num painel de navegador, com um **trilho numerado** que lê o estado real do disco e mostra onde você está.

**Sem terminal (recomendado para o dia a dia):** duplo-clique em **`Iniciar-Acervo.bat`** (Windows/WSL2) ou **`iniciar-acervo.sh`** (Linux) — o servidor sobe e o navegador abre sozinho. O passo a passo completo, tela a tela, está no **[Guia Visual](GUIA-VISUAL.md)**.

Pelo terminal:

```bash
cd ~/projects/second-brain
python3 acervo_app.py
# abra no navegador: http://localhost:8765
```

No painel: defina a **pasta do acervo** (botão 📁 Procurar navega os discos do Windows e do WSL2), e siga o trilho:

| Etapa | O que faz | Script por trás |
|---|---|---|
| 1 · Triagem | Analisa cada PDF (dry-run): tipo provável, idioma, rota, precisa de OCR? | `aplicar_ocr.sh` + `triagem.py` |
| 2 · OCR | OCR em lote só no que precisa, no idioma certo | `aplicar_ocr.sh` |
| 3 · Paginação | PDF → Markdown com âncoras `{{p.NN}}` | `injetar_paginas.py` |
| 4 · Limpar | Hifenização, cabeçalhos repetidos, ruído (sem IA) | `limpar_ocr.py` |
| 5 · Fatiar | Livro grande → nota-índice + fatias | `fatiar.py` |
| 6 · Validar | Âncoras + YAML ABNT por tipo | `verificar_ancoras.py` + `validar_yaml_abnt.py` |
| 7 · Auditar | O resultado serve ao segundo cérebro? (PRONTO/PARCIAL/REPROVADO) | `auditar_acervo.py` |
| 8 · Publicar | Distribui `3-MARKDOWN-LIMPO` no vault por regra (tipo→pasta do perfil). **Simule primeiro** | `publicar.py` |
| 9 · Auditar vault | O **grafo** do vault está íntegro? Fatias órfãs, links quebrados, notas invisíveis nos MOCs | `auditar_vault.py` |
| 10 · Radar | Correlaciona os achados de `Radar/` (Cowork) às notas que os citam; sinaliza `A-conferir` | `radar.py` |

O trilho tem duas proteções: refazer uma etapa **já concluída** pede confirmação explícita (reprocessar pode sobrescrever), e cada etapa feita mostra o **carimbo de data** da última execução (derivado do disco).

Guia completo do app (incluindo processamento de arquivos avulsos, offset de página e navegador de pastas): **[LEIA-ME_APP.md](LEIA-ME_APP.md)**.

### A triagem e o `controle.csv`

A triagem classifica cada arquivo por **nome E conteúdo** (1ª/2ª página) e registra no `controle.csv`:

- `tipo_fonte_provavel` — o palpite (`legislacao`, `livro`, `jurisprudencia`…). **Vazio = indeterminado**: nada pontuou; classifique à mão. O sistema *não chuta* — era assim que legislação virava "livro" em silêncio.
- `confiabilidade` — inclui a confiança do palpite (`alta`/`media`) para você revisar primeiro o que é duvidoso.
- `exige_ancora_pagina` — `SIM` (doutrina), `nao` (lei/julgado) ou `?` (indeterminado).

**Sempre revise o CSV antes de seguir** — é o checkpoint humano da Fase 1.

## Uso — pela linha de comando

Sequência típica de um lote (detalhes e variações no [WORKFLOW.md](Roteiro-Base-Juridica/WORKFLOW.md)):

```bash
# FASE 1-2 · triagem + OCR (comece SEMPRE em dry-run)
DRYRUN=1 MODE=manter ROOT="/mnt/c/.../drive" bash aplicar_ocr.sh
        MODE=manter ROOT="/mnt/c/.../drive" bash aplicar_ocr.sh

# FASE 2 · conversão com âncoras (venv por causa do PyMuPDF)
source ~/venvs/acervo/bin/activate
python injetar_paginas.py livro_OCR.pdf -o 2-MARKDOWN-BRUTO/livro.md
python injetar_paginas.py livro.pdf -o livro.md --offset 12 --romanas-ate 14
python verificar_ancoras.py 2-MARKDOWN-BRUTO/
deactivate

# FASE 3 · limpeza mecânica + fatiamento (sem IA, sem venv)
python3 limpar_ocr.py 2-MARKDOWN-BRUTO/ --inplace
python3 fatiar.py 2-MARKDOWN-BRUTO/ -o 3-MARKDOWN-LIMPO/ --palavras 1200

# FASE 4 · validação
python3 verificar_ancoras.py bruto.md --comparar limpo.md   # nenhuma âncora perdida NEM inventada
python3 validar_yaml_abnt.py 3-MARKDOWN-LIMPO/ --gerar      # YAML por tipo + referência ABNT pronta
python3 auditar_acervo.py 3-MARKDOWN-LIMPO/ --detalhado     # nota final por arquivo

# FASE 5 · publicação determinística no vault (SEMPRE simule primeiro)
python3 publicar.py 3-MARKDOWN-LIMPO/ 4-OBSIDIAN-VAULT/ --dry
python3 publicar.py 3-MARKDOWN-LIMPO/ 4-OBSIDIAN-VAULT/
# Roteia por tipo→pasta (perfil): Doutrina/Artigo→01-Doutrina/<Área>/,
# Legislação/Parecer→02, Jurisprudência/Súmula→03, interno→04-Modelos-Internos.
# Travas: nota REPROVADA não publica; copiar (nunca mover); em conflito o
# VAULT VENCE (curadoria humana) — --force sobrescreve conscientemente.
# Idempotente; gera RELATORIO-PUBLICACAO.md (contagens + itens A-conferir).

# FASE 5 · MOCs — criar para uma área nova / regenerar os painéis
python3 gerar_moc.py 4-OBSIDIAN-VAULT/ --area Civil
python3 gerar_moc.py 4-OBSIDIAN-VAULT/ --regenerar-todos
# O MOC tem duas camadas: painéis Dataview entre <!-- moc:auto:inicio/fim -->
# (a regeneração reescreve SÓ isso) e a curadoria manual (mapa de institutos)
# que o script NUNCA toca. O filtro de área é um predicado Dataview gravado
# no frontmatter (moc_predicado) — áreas amplas usam filtro composto:
python3 gerar_moc.py vault/ --area Processual --nome MOC-Processo-Civil \
  --predicado 'contains(area, "Processual") AND (contains(tags, "processo-civil") OR contains(area, "Civil"))'
# MOC antigo sem marcadores? --migrar insere-os sem alterar o conteúdo.

# FASE 5+ · auditoria do GRAFO do vault (depois de publicar no Obsidian)
python3 auditar_vault.py 4-OBSIDIAN-VAULT/ --detalhado
# Erros = nota fora do grafo ou INVISÍVEL nos painéis (fatia órfã, partes:
# inconsistente, tipo/status fora do vocabulário, sem area, par tipo/tipo_fonte
# incoerente, nome duplicado). Avisos = higiene (wikilink quebrado, área sem
# MOC, nome fora do padrão). Gera RELATORIO-VAULT.md no vault; exit 1 se erro.

# FASE 6 · radar — o Cowork (Módulo E) alimenta Radar/; a correlação é por regra
python3 radar.py 4-OBSIDIAN-VAULT/              # fila de revisão (não altera notas)
python3 radar.py 4-OBSIDIAN-VAULT/ --aplicar    # sinaliza afetadas com A-conferir
# Extrai identificadores (Lei/Decreto/MP/EC/Tema/Súmula/nº CNJ) do achado E
# das notas e cruza — nunca palpite. O radar SINALIZA; reclassificar
# (Revogado/Superado) é decisão humana, no ritual semanal. Idempotente
# entre ciclos (Radar/.radar_estado.json).

# Utilitários
python3 normalizar_yaml.py pasta/ --dry     # normaliza area/tags/autoria (veja antes de gravar)
python3 corrigir_idioma.py                  # redetecta idioma e corrige o YAML
python3 triagem.py --inferir "arquivo.pdf" < amostra.txt    # classifica um arquivo avulso
```

Variáveis úteis do `aplicar_ocr.sh`: `DRYRUN=1`, `MODE=manter|substituir` (⚠ `substituir` destrói o original — nunca no acervo doutrinário), `FORCE_ALL=1`, `OCR_LANG=auto|por|deu|…`, `OUTPUT_TYPE=pdfa|pdf`, `OCR_STRATEGY=redo-ocr|force-ocr|skip-text`.

### Modo estrito (preview da migração)

Alguns campos ABNT estão temporariamente rebaixados de erro para aviso (tabela `TOLERADOS` na taxonomia — dívida de migração que deve encolher até sumir). Para ver como seu acervo se sairia com a régua completa:

```bash
ACERVO_ESTRITO=1 python3 auditar_acervo.py 3-MARKDOWN-LIMPO/
```

## O vault do Obsidian

1. Estrutura (a Fase 5 do WORKFLOW detalha):
   ```
   4-OBSIDIAN-VAULT/
   ├── 00-Indices-MOCs/    MOCs por área + fontes.md (radar)
   ├── 01-Doutrina/  02-Legislacao/  03-Jurisprudencia/  04-Modelos-Internos/
   └── 99-Templates/       Template_Nota_Indice.md + Template_Fatia.md
   ```
2. Copie `Roteiro-Base-Juridica/vault-inicial/` para dentro do vault (MOCs de Tributário e Processo Civil prontos + templates). O conteúdo entra pelo `publicar.py` (etapa 8) — nunca arraste arquivos à mão: a publicação valida antes e respeita a curadoria existente.
3. No Obsidian: instale o plugin **Dataview** → os painéis dos MOCs se preenchem sozinhos a partir do frontmatter.
4. Convenções que os painéis assumem:
   - Notas-índice têm `partes:`; fatias têm `parte:` + `obra:` — os painéis filtram `!parte` para listar obras, não pedaços.
   - `area` é lista (`[Tributário]`); `tipo`, `status` e `confiabilidade` usam o vocabulário do perfil (ver `taxonomia.py`). **Valor fora do vocabulário = nota some do painel.**
   - Nome de arquivo: `[AREA]_[TIPO]_[ANO]_[Titulo-Curto]_[Autor].md` (códigos em `taxonomia.CODIGO_AREA/CODIGO_TIPO`; fatias = mesmo prefixo + `_pNN`, índice + `_INDICE`).

## Guia do desenvolvedor

### Arquitetura: núcleo × perfil

```
taxonomia.py
├── NÚCLEO (invariante entre domínios do conhecimento)
│   ├── TIPOS_FONTE      16 tipos ABNT: obrigatórios, localizador, exige_ancora, abnt
│   ├── TOLERADOS        dívida de migração (erro→aviso) — deve ENCOLHER até sumir
│   ├── IDIOMAS / IDIOMA_EDICAO / CONFIABILIDADE / ANCORA_PAG / ANCORA_POS
│   └── API: campos_obrigatorios/bloqueantes/tolerados, exige_ancora,
│            localizador, eh_abnt, par_coerente, analisar_nome
└── PERFIS["juridico"]  (PERFIL_ATIVO — selecionável por ACERVO_PERFIL)
    ├── tipos (eixo funcional), areas (+sinônimos), status, natureza
    ├── codigo_area / codigo_tipo (nomes de arquivo)
    ├── tipos_por_fonte (mapa NÃO-bijetivo tipo_fonte → tipos coerentes)
    └── heuristicas_tipo / heuristicas_conteudo (triagem)
```

**Regras que não se negociam:**

1. **Todo vocabulário mora na `taxonomia.py`.** Nenhum script mantém cópia própria de tipos, áreas, status ou idiomas. O bash consome via `triagem.py` (subprocess).
2. **Todo frontmatter passa por `frontmatter.py`** — `ler()` para ler, `emitir()/escalar()` para escrever. Interpolar valor parseado em f-string emite repr de Python e quebra YAML em silêncio.
3. **Nenhum termo jurídico hardcoded fora do perfil.** Código novo consulta `PERFIL_ATIVO`; contemplar outra área do conhecimento = escrever outro perfil, não refatorar.
4. **Stdlib-only nos scripts do repositório** (exceção: `injetar_paginas.py` usa PyMuPDF do venv). O app roda offline.
5. **Invariante de deploy:** Python resolve imports pelo diretório do próprio script (`sys.path[0]`). `taxonomia.py` + `frontmatter.py` devem existir **em todo diretório que contenha um consumidor** — hoje: a raiz e `Roteiro-Base-Juridica/projeto-claude-refino/scripts/`. **Ao editar qualquer script duplicado, propague a cópia** (o checklist de dependências do app confere isso).
6. **Um script nunca inventa dado** — não chuta tipo, não afirma `Vigente`, não estima página. Na dúvida: vazio + `A-conferir` + aviso.

### Testes e verificação (sem framework — stdlib + git)

```bash
python3 taxonomia.py --autoteste     # integridade interna dos vocabulários/perfis

# Oráculo de regressão: o corpus/ (18 fixtures) cobre o que os parsers antigos
# quebravam. Capture ANTES de mexer, diffe DEPOIS:
python3 validar_yaml_abnt.py corpus --gerar > /tmp/antes.txt 2>&1
# ... sua alteração ...
python3 validar_yaml_abnt.py corpus --gerar 2>&1 | diff /tmp/antes.txt -
# refactor puro → byte-idêntico; mudança deliberada → toda linha do diff explicável

# idem para: auditar_acervo.py corpus / normalizar_yaml.py corpus --dry /
#            fatiar.py corpus -o /tmp/f --min-palavras 500
# grafo do vault: corpus-vault/ tem 5 erros + 5 avisos PLANTADOS de propósito
python3 auditar_vault.py corpus-vault --detalhado   # deve sair com rc=1
```
> Ao rodar auditores sobre os corpus, use `--relatorio /tmp/...` — o padrão
> grava o relatório DENTRO da pasta auditada e polui o oráculo.

Filosofia de severidade: **rigor novo entra como AVISO** (a primeira rodada é censo, não portão); promova aviso→erro por tipo, quando o backlog daquele tipo zerar. `ACERVO_ESTRITO=1` mostra o futuro sem mudar o presente.

### Como adicionar um novo domínio (perfil)

1. Em `taxonomia.py`, adicione `PERFIS["meu_dominio"] = Perfil(...)` com: eixo `tipos`, `areas` (+chaves de busca), códigos, `tipos_por_fonte`, `status`, heurísticas de triagem do domínio.
2. `ACERVO_PERFIL=meu_dominio` ativa o perfil (env var).
3. Rode `python3 taxonomia.py --autoteste` — ele valida a integridade de *todos* os perfis.
4. Configure no perfil os campos de MOC (`status_ok`/`status_pendencia`/`status_superado`/`moc_grupos`) e de publicação (`pastas_publicacao`/`pastas_por_area`) — `gerar_moc.py` e `publicar.py` passam a falar o vocabulário do domínio sem nenhuma alteração de código.

### Convenções

- Commits: um passo lógico por commit, mensagem explica o *porquê*; mudanças acopladas (ex.: template + MOC que exibe o campo) vão **no mesmo commit**.
- Correção de bug: registre incidentes de ferramenta no [Apêndice A.7 do WORKFLOW](Roteiro-Base-Juridica/WORKFLOW.md).
- Este README é atualizado **ao final de cada fase** do roadmap.
- **Versionamento semântico** com tag git por release (`git tag -l`), documentado no [CHANGELOG.md](CHANGELOG.md): MENOR para cada fase/feature, CORREÇÃO para fixes, MAIOR para quebra de contrato (ex.: v3.0.0 = vocabulário centralizado). O `GUIA-VISUAL.md` acompanha a release.

## Roadmap

| Fase | Entrega | Status |
|---|---|---|
| **1** | Taxonomia canônica (`taxonomia.py`) + parser único (`frontmatter.py`) + triagem por conteúdo (`triagem.py`) + robustez OCR + saneamento de 6 duplicações de vocabulário e 4 parsers | ✅ concluída (jul/2026) |
| **2** | `auditar_vault.py` — validador de **grafo** do vault: fatia órfã, `partes:` inconsistente, wikilink quebrado, área sem MOC, par `tipo`/`tipo_fonte` incoerente (etapa 8 do app) | ✅ concluída (jul/2026) |
| **3** | `publicar.py` — Fase 5 determinística: roteia `3-MARKDOWN-LIMPO` → vault por perfil, idempotente, travado em validação verde + travas de reexecução e badges com data no trilho do app | ✅ concluída (jul/2026) |
| **4** | `gerar_moc.py` — scaffolder de MOC por predicado de área, com marcadores de bloco preservando a curadoria manual (MOCs existentes migrados) | ✅ concluída (jul/2026) |
| **5** | Radar (etapa 10) — correlação determinística `Radar/` → notas afetadas (fila `A-conferir`); a descoberta/web fica no Cowork | ✅ concluída (jul/2026) |

## Solução de problemas

O [Apêndice A do WORKFLOW](Roteiro-Base-Juridica/WORKFLOW.md) tem o diagnóstico completo. Destaques:

| Sintoma | Causa | Solução |
|---|---|---|
| `ImportError: cannot import name 'Inf' from 'numpy'` | mistura apt × pip --user | venv dedicado (A.2) |
| "Some input metadata could not be copied… PDF/A" | **aviso benigno** (XMP da origem não cabe no PDF/A; o PDF sai válido) | nada a fazer — o log anota `AVISO (inofensivo)`; se incomodar, `OUTPUT_TYPE=pdf` |
| OCR falha com `rc=N` | veja o motivo no log (`rc_motivo`) e no `controle.csv` | 2=entrada inválida · 6=PDF corrompido · 8=criptografado · 10=só PDF/A falhou (arquivo OK) |
| `Permission denied` / `command not found` ao rodar script baixado | CRLF/permissões do Windows | `python3 preparar.py` |
| Nota não aparece no MOC | metadado fora do vocabulário, `area` ausente, ou `parte:` indevido | `python3 auditar_vault.py <vault>` — foi feito exatamente para tornar esse silêncio visível |
| Fatia perdida / índice desatualizado | `obra:` aponta para índice inexistente, ou `partes:` ≠ nº real de fatias | idem — seção "Erros" do `RELATORIO-VAULT.md` |

---

*Perfil jurídico: o sistema acelera a montagem da peça de horas para minutos, mas a conferência da citação que vai ao juiz continua sendo do advogado. O pipeline existe para que essa conferência seja rápida e possível — não para dispensá-la.*

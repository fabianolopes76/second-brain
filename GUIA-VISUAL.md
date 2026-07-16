# 🖱️ Guia Visual do Acervo — do PDF ao segundo cérebro **sem linha de comando**

Este guia é para quem vai **usar** o Acervo pelo painel no navegador — sem digitar nenhum comando. Tudo o que o pipeline faz (triagem, OCR, conversão, validação, publicação no Obsidian, radar) está a um clique de distância.

> Quem preferir o terminal, ou for desenvolver, usa o [README.md](README.md). Este guia cobre o mesmo pipeline, só que pela interface.

---

## 1 · Abrir o painel (duplo-clique)

**No Windows (com WSL2):** dê **duplo-clique em [`Iniciar-Acervo.bat`](Iniciar-Acervo.bat)**.
Vai abrir uma janela preta (é o servidor — **minimize, não feche**) e, em seguida, o navegador com o painel.

**No Linux:** duplo-clique em [`iniciar-acervo.sh`](iniciar-acervo.sh) → "Executar". O navegador abre sozinho.

Se o navegador não abrir, digite na barra de endereços: **`http://localhost:8765`**

> **Instalação (uma única vez, com ajuda técnica):** o WSL2 e as ferramentas de OCR precisam estar instalados — peça ao suporte para seguir a seção *Instalação* do [README.md](README.md). Depois disso, o uso diário é só o duplo-clique acima.

---

## 2 · O painel, tela por tela

O painel tem 5 seções numeradas. Você vai passar 90% do tempo na **03 · Pipeline**.

```
┌──────────────────────────────────────────────────────────────┐
│  Acervo · Painel de Controle                    ● pronto     │
├──────────────────────────────────────────────────────────────┤
│  01 · Configuração   ← seus PDFs + botão [⚙ Ambiente]        │
│  02 · Execução       ← o "vidro da máquina": log ao vivo     │
│  03 · Pipeline       ← O TRILHO: etapas 1 a 10, em ordem     │
│  04 · Triagem        ← a tabela com o raio-X de cada PDF     │
│  05 · Fichas         ← corrija o YAML à mão, sem editor      │
└──────────────────────────────────────────────────────────────┘
   (⚙ Ambiente abre um painel lateral com o semáforo das
    ferramentas — verde: tudo pronto; vermelho: precisa de ação)
```

### 01 · Configuração — diga onde estão os PDFs

1. Clique em **📁 Procurar…** ao lado de "Pasta do acervo".
2. Navegue pelo seletor: ele mostra os discos do Windows (`💾 Windows C:`), suas pastas (Documents, Downloads…) e as do Linux. **Cada pasta mostra quantos PDFs tem** — isso ajuda a achar o acervo.
3. Selecione a pasta e clique **Definir**.

> **Clicou em "Definir" sem escolher a pasta?** Aparece uma advertência em vermelho logo abaixo do campo — ela some sozinha assim que você escolhe (ou digita) a pasta.

Os outros campos (Scripts, venv, Idioma) já vêm preenchidos — só mexa se o suporte orientar. O idioma padrão é **auto**: cada obra é detectada e OCRizada na língua certa (pt/en/de/fr/it/es).

**O botão ⚙ Ambiente** (na mesma linha do Definir) é o semáforo das ferramentas:

- **Verde** (`⚙ Ambiente ✓`) — tudo instalado, siga em frente.
- **Vermelho** (`⚙ Ambiente — N pendências`) — falta algo. Clique: um painel desliza da direita listando cada item com ✓/✗ e **um comando único pronto para copiar** e enviar ao suporte. Feche no ✕ ou com a tecla Esc.

### 02 · Execução — o vidro da máquina

Fica logo abaixo da Configuração: quando você clica num botão do Pipeline, o trabalho aparece aqui **ao vivo**, linha a linha. Enquanto roda, os demais botões ficam desativados (um trabalho por vez). Ao final aparece `--- fim (código 0) ---` — código 0 é sucesso.

- Linhas com **`... OCR em andamento ha XmYYs (sinal de vida ...)`** aparecem a cada minuto durante o OCR de arquivos grandes: **é o normal, não travou** — um livro escaneado de 800 páginas pode levar mais de uma hora.
- Linhas com **`AVISO (inofensivo)`** podem ser ignoradas (ex.: metadados que não cabem no formato PDF/A — o arquivo sai perfeito).
- Linhas com **`FALHOU (rc=N: motivo)`** dizem exatamente o que houve (PDF corrompido, protegido por senha…).

### 03 · Pipeline — o trilho de 10 etapas

O coração do painel. As etapas formam um trilho em 6 grupos, e **o painel lê o disco para saber onde você está**: cada etapa aparece em um de três estados:

> **ⓘ em cada card** — todo card tem um botãozinho redondo ⓘ ao lado do título: ele abre uma janela explicando **o que a etapa faz, o que cada botão executa e o que fica gravado no disco**. Na dúvida sobre qualquer botão (ex.: "Limpar"), clique no ⓘ.
>
> **Progresso dentro do card** — enquanto uma etapa roda, o próprio card mostra o arquivo em processamento (`3/6 — nome.pdf`), a barra de progresso e a contagem de ✓/✗. No OCR aparece também há quanto tempo o arquivo atual está sendo processado — livro digitalizado grande demora, mas você **vê** que está andando.

| Aparência | Estado | Significado |
|---|---|---|
| ⚪ cinza, apagada | **bloqueada** | falta um passo anterior (o texto diz qual) |
| 🔴 bolinha vinho pulsando | **ativa** | é aqui que você está — clique no botão |
| ✅ verde, com **data e hora** | **feita** | concluída (ex.: "148 arquivos · 15/07 18:04") |

> **Proteção contra clique acidental:** se você clicar numa etapa **já concluída**, o painel pergunta *"Esta etapa já foi concluída. Reexecutar vai reprocessar e pode sobrescrever. Continuar?"* — cancele se foi engano.

```
ENTRADA
  (1) Triagem          [Analisar]                → raio-X dos PDFs, sem alterar nada
  (2) OCR              [Aplicar OCR]             → só nos que precisam, no idioma certo
CONVERSÃO
  (3) Paginação        [Converter] [📁 arquivo]  → PDF → texto COM âncoras de página
PREPARO (mecânico, sem IA)
  (4) Limpar OCR       [Limpar]                  → hifenização, cabeçalhos repetidos
  (5) Fatiar           [Fatiar]                  → livro grande → índice + fatias
QUALIDADE
  (6) Validar          [Validar]                 → âncoras + ficha ABNT completa?
  (7) Auditar          [Auditar]                 → nota final: PRONTO/PARCIAL/REPROVADO
PUBLICAÇÃO
  (8) Publicar         [Simular] [Publicar]      → leva o resultado ao vault do Obsidian
  (9) Auditar vault    [Auditar vault]           → o "cérebro" está íntegro?
MANUTENÇÃO
  (10) Radar           [Fila de revisão] [Sinalizar A-conferir]
```

**O que cada etapa faz, em uma frase:**

1. **Triagem** — analisa cada PDF (tipo provável, idioma, precisa de OCR?) e monta a tabela da seção 04. *Não altera nenhum arquivo.*
2. **OCR** — aplica reconhecimento de texto **só** nos PDFs escaneados, preservando o original (cria uma cópia `_OCR`).
3. **Paginação** — converte para texto **guardando o número de cada página** (`{{p.45}}`). Sem isso, não há citação ABNT. Dá para processar um arquivo avulso pelo botão 📁, informando o *offset* se a página impressa não bater.
4. **Limpar** — conserta o que o OCR quebrou (palavras hifenizadas, cabeçalhos repetidos). Mecânico, de graça.
5. **Fatiar** — divide livros grandes em fatias de leitura rápida + uma nota-índice. É o formato que a IA consome bem.
6. **Validar** — confere que nenhuma âncora se perdeu e que a ficha (autor, editora, ano…) está completa **para o tipo** (livro exige página; lei não).
7. **Auditar** — dá a nota de cada arquivo: **PRONTO** (serve ao cérebro), **PARCIAL** (avisos) ou **REPROVADO** (corrigir antes de usar).
8. **Publicar** — distribui o material pronto nas pastas certas do vault (doutrina por área, legislação, jurisprudência…). **Clique "Simular" primeiro** para ver o plano sem gravar. Notas reprovadas não entram; notas que você editou à mão no Obsidian **não são sobrescritas**.
9. **Auditar vault** — verifica as *ligações* do cérebro: fatia órfã, link quebrado, nota que "sumiu" dos painéis por erro de preenchimento.
10. **Radar** — cruza as novidades (leis alteradas, novos julgados — coletadas pelo assistente de IA na pasta `Radar/`) com as notas do seu acervo que as citam, e monta a **fila de revisão**. "Sinalizar A-conferir" marca as notas afetadas para você revisar — **a decisão de reclassificar é sempre sua**.

### 04 · Triagem — o raio-X dos seus PDFs

Depois da etapa 1, esta tabela mostra, para cada arquivo: idioma detectado, se precisa de OCR, a rota de conversão e o **tipo provável** (`legislacao`, `livro`, `jurisprudencia`…).

**Revise esta tabela — é o seu checkpoint.** Repare na última coluna:

- `A-conferir (palpite: alta)` — o sistema tem boa confiança (nome **e** conteúdo apontam o mesmo tipo).
- `A-conferir (palpite: media)` — confiança média: vale conferir.
- `A-conferir (indeterminado)` — o sistema **não chutou** (é assim que se evita que uma lei vire "livro" por engano). Classifique você.

### 05 · Fichas — correção manual, sem editor de texto

Quando a etapa **(6) Validar** apontar pendência que a automação não resolve (`tipo_fonte` que a triagem não inferiu, autoria/ementa/ano vazios), é aqui que você conserta — **sem abrir arquivo nenhum**:

1. Clique **🔄 Carregar fichas**: cada markdown do `2-MARKDOWN-BRUTO` aparece com sua nota de validação (PRONTO / PARCIAL / REPROVADO — passe o mouse no nome para ver o que falta).
2. Clique **✎ Editar**: um painel lateral abre com o formulário. Comece pelo **tipo_fonte** — o formulário abre exatamente os campos que aquele tipo exige (livro pede editora; lei pede ementa e nº da norma).
3. **💾 Salvar e revalidar**: a validação roda na hora e mostra o que ainda falta. A **referência ABNT** ninguém digita à mão: o painel mostra a sugestão montada da sua ficha — um clique em *↳ usar a sugestão* e pronto.

> Campo deixado **em branco não mexe** no arquivo. O mestre é o `2-MARKDOWN-BRUTO`: depois de corrigir, **refatie** (etapa 5) para as fatias herdarem a ficha.

---

## 3 · O dia a dia em 8 cliques

Um lote novo de PDFs, do download ao Obsidian:

1. Copie os PDFs para a pasta do acervo (no Windows Explorer mesmo).
2. Duplo-clique em **Iniciar-Acervo.bat**.
3. **(1) Analisar** → confira a tabela da seção 04.
4. **(2) Aplicar OCR** → espere o log terminar.
5. **(3) Converter** → **(4) Limpar** → **(5) Fatiar**.
6. **(6) Validar** → **(7) Auditar** → leia as pendências (o refino fino — autor, resumo — é feito no Projeto Claude, como descreve o WORKFLOW).
7. **(8) Simular** → conferiu? → **Publicar**.
8. **(9) Auditar vault** → abra o Obsidian e navegue pelos MOCs. 🎉

Toda semana: **(10) Radar → Fila de revisão**, despache os itens marcados, e o cérebro continua vivo e confiável.

---

## 4 · Ver o resultado no Obsidian (também sem terminal)

1. Instale o [Obsidian](https://obsidian.md) (gratuito).
2. **Open folder as vault** → escolha a pasta `4-OBSIDIAN-VAULT` dentro do seu acervo.
3. Em *Settings → Community plugins*, instale e ative o **Dataview**.
4. Abra `00-Indices-MOCs/MOC-Tributario` (ou o MOC da sua área): os painéis se preenchem sozinhos — Vigente, Pendências, Doutrina, Jurisprudência, Legislação, Novidades.

> Os painéis refletem o preenchimento das fichas. Se uma nota "sumir" de um painel, rode a etapa **(9) Auditar vault** — o relatório aponta exatamente o campo a corrigir.

---

## 5 · Problemas comuns (sem terminal)

| Sintoma | O que fazer |
|---|---|
| O navegador abriu mas a página não carrega | Espere 5 s e recarregue (F5). Confira se a janela preta do servidor está aberta. |
| Mensagens `x-www-browser: not found` … ao iniciar (WSL2) | Versão antiga do inicializador — atualize para a v3.5.2+ (`git pull`). O servidor funcionava; só a abertura automática falhava. |
| Fechei a janela preta sem querer | O painel cai. Duplo-clique de novo no `Iniciar-Acervo.bat`. |
| `Address already in use` ao iniciar | O painel **já estava aberto** — na v3.8.1+ o inicializador percebe e só abre o navegador. Para reiniciar de verdade (ex.: após atualizar), feche a janela anterior do servidor e inicie de novo. |
| `E: Unable to locate package jbig2enc` | Ubuntu até o 22.04 **não tem** esse pacote no apt. Use o instalador do projeto: `bash instalar-jbig2enc.sh` (é o comando que o ⚙ Ambiente mostra na v3.10.1+) — ele instala as dependências e compila da fonte oficial. |
| "Já há uma tarefa em execução" | O painel roda um trabalho por vez. Acompanhe a seção 04 e aguarde o `--- fim ---`. |
| Etapa cinza (bloqueada) | O texto ao lado diz o que falta (ex.: "faça a triagem"). O trilho é em ordem. |
| Apareceu `AVISO (inofensivo)` no log | Ignorar — está explicado no próprio log. O arquivo saiu correto. Exemplos: metadados que não cabem no PDF/A; camada de texto ruim da origem (o OCR a substitui); jbig2enc ausente (PDF sai maior — instale pelo ⚙ Ambiente). |
| `FALHOU (rc=8: PDF criptografado)` | O PDF tem senha — remova a proteção (imprimir → salvar como PDF resolve) e rode de novo. |
| `FALHOU (rc=3: dependência ausente…)` | Atualize para a **v3.6.1+** (`git pull`): em versões antigas, **vírgula no nome do PDF** derrubava a detecção de idioma e o OCR falhava fingindo dependência ausente. Se persistir após atualizar, falta mesmo uma ferramenta — abra **⚙ Ambiente** e envie o comando ao suporte. |
| Nota não aparece no MOC do Obsidian | Etapa **(9) Auditar vault** → abra `RELATORIO-VAULT.md` no próprio vault: ele lista a causa e a correção. |
| O painel pergunta "já concluída — continuar?" | Você clicou numa etapa verde. Se foi de propósito (reprocessar), confirme; senão, cancele. |
| "Converter pasta" respondia "nenhum arquivo exige âncora" | Versão antiga (≤3.7): só convertia livros. Atualize para a **v3.8.0+** — converte todos os PDFs pesquisáveis e lista no log os pulados por falta de OCR. |
| Corrigir idioma diz "não deu para detectar" | Atualize para a **v3.8.0+** (detecta pela cópia `_OCR` e pelo texto do próprio markdown). Se ainda assim não der, o caso é manual: peça ao suporte para rodar `corrigir_idioma.py arquivo.md --forcar por`. |
| Publicar: `tipo '(vazio)' sem pasta de publicação` | A nota não tem o campo `tipo` — sem ele não há rota nem painel no MOC. Rode **Normalizar** (etapa 5): ele deriva o `tipo` do tipo_fonte quando não há ambiguidade. O que sobrar (índice REPROVADO, ficha vazia) é o **refino da Fase 3c** — preencha a ficha do índice no Projeto Claude e publique de novo. |
| Publicar: `N fatia(s) retidas com o índice` | Proposital: fatia sem índice nasceria órfã no vault. Resolva o índice da obra (a razão está na mesma linha) e as fatias entram junto na próxima publicação. |

---

*Versão do guia: acompanha a versão do projeto (veja o [CHANGELOG.md](CHANGELOG.md)). Este guia é atualizado a cada release.*

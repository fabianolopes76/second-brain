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

O painel tem 4 seções numeradas. Você vai passar 90% do tempo na **03 · Pipeline**.

```
┌──────────────────────────────────────────────────────────────┐
│  Acervo · Painel de Controle                    ● pronto     │
├──────────────────────────────────────────────────────────────┤
│  01 · Configuração   ← seus PDFs + botão [⚙ Ambiente]        │
│  02 · Execução       ← o "vidro da máquina": log ao vivo     │
│  03 · Pipeline       ← O TRILHO: 9 etapas + ✎, em ordem     │
│      └ Qualidade: [📋 Fichas] ← conferir/corrigir os YAML    │
│  04 · Triagem        ← a tabela com o raio-X de cada PDF     │
└──────────────────────────────────────────────────────────────┘
   (⚙ Ambiente e 📋 Fichas abrem painéis laterais: o primeiro é o
    semáforo das ferramentas; o segundo, a mesa de revisão das fichas)
```

### 01 · Configuração — diga onde estão os PDFs

1. Clique em **📁 Procurar…** ao lado de "Pasta do acervo".
2. Navegue pelo seletor: ele mostra os discos do Windows (`💾 Windows C:`), suas pastas (Documents, Downloads…) e as do Linux. **Cada pasta mostra quantos PDFs tem** — isso ajuda a achar o acervo.
3. Selecione a pasta e clique **Definir**.

> **Clicou em "Definir" sem escolher a pasta?** Aparece uma advertência em vermelho logo abaixo do campo — ela some sozinha assim que você escolhe (ou digita) a pasta.
>
> **A configuração fica lembrada** (v3.13+): ao reabrir o painel, a pasta do acervo e o idioma voltam sozinhos — retome de onde parou sem redefinir nada.

Os outros campos (Scripts, venv, Idioma) já vêm preenchidos — só mexa se o suporte orientar. O idioma padrão é **auto**: cada obra é detectada e OCRizada na língua certa (pt/en/de/fr/it/es).

**O botão ⚙ Ambiente** (na mesma linha do Definir) é o semáforo das ferramentas:

- **Verde** (`⚙ Ambiente ✓`) — tudo instalado, siga em frente.
- **Vermelho** (`⚙ Ambiente — N pendências`) — falta algo. Clique: um painel desliza da direita listando cada item com ✓/✗ e **um comando único pronto para copiar** e enviar ao suporte. Feche no ✕ ou com a tecla Esc.

### 02 · Execução — o vidro da máquina

Fica logo abaixo da Configuração: quando você clica num botão do Pipeline, o trabalho aparece aqui **ao vivo**, linha a linha. Enquanto roda, os demais botões ficam desativados (um trabalho por vez). Ao final aparece `--- fim (código 0) ---` — código 0 é sucesso.

- Linhas com **`... OCR em andamento ha XmYYs (sinal de vida ...)`** aparecem a cada minuto durante o OCR de arquivos grandes: **é o normal, não travou** — um livro escaneado de 800 páginas pode levar mais de uma hora.
- Linhas com **`AVISO (inofensivo)`** podem ser ignoradas (ex.: metadados que não cabem no formato PDF/A — o arquivo sai perfeito).
- Linhas com **`FALHOU (rc=N: motivo)`** dizem exatamente o que houve (PDF corrompido, protegido por senha…).

### 03 · Pipeline — o trilho de 9 etapas (+ ✎ Fichas)

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
  (6) Qualidade        [📄] [Auditar qualidade]  → UM exame: âncoras + YAML + nota; triagem abre só
  (✎) Fichas           [📋 Abrir fichas]         → SEU passo: corrigir e confirmar as fichas
PUBLICAÇÃO
  (7) Publicar         [Simular] [Publicar]      → leva o resultado ao vault do Obsidian
  (8) Auditar vault    [Auditar vault]           → o "cérebro" está íntegro?
MANUTENÇÃO
  (9) Radar            [Fila de revisão] [Sinalizar A-conferir]
```

**O que cada etapa faz, em uma frase:**

1. **Triagem** — analisa cada PDF (tipo provável, idioma, precisa de OCR?) e monta a tabela da seção 04. *Não altera nenhum arquivo.*
2. **OCR** — aplica reconhecimento de texto **só** nos PDFs escaneados, preservando o original (cria uma cópia `_OCR`).
3. **Paginação** — converte para texto **guardando o número de cada página** (`{{p.45}}`). Sem isso, não há citação ABNT. Dá para processar um arquivo avulso pelo botão 📁, informando o *offset* se a página impressa não bater.
4. **Limpar** — conserta o que o OCR quebrou (palavras hifenizadas, cabeçalhos repetidos). Mecânico, de graça.
5. **Fatiar** — divide livros grandes em fatias de leitura rápida + uma nota-índice; **documento pequeno é copiado inteiro** ao 3-MARKDOWN-LIMPO (também publica, como nota única). É o formato que a IA consome bem.
6. **Qualidade** — o exame completo num clique: âncoras íntegras (presença, duplicadas, ordem, lacunas), YAML coerente com o tipo e a **nota** de cada arquivo (PRONTO/PARCIAL/REPROVADO). Ao terminar, o **relatório-triagem abre sozinho** — do grave ao irrelevante, cada item com a ação (e atalho ✎ para corrigir a ficha). Reabra pelo botão **📄 Relatório**. E para acelerar a revisão: **🤖 Preencher com IA** gera um prompt pronto (com as fichas pendentes e um trecho de cada documento) para você colar em **qualquer IA** — Gemini, ChatGPT, Claude…; cole a resposta de volta e o painel **valida e aplica** nas fichas, com backup automático e botão **↩ Reverter** (nada é gravado sem validação; vocabulário inventado pela IA é ignorado com aviso).
7. **Publicar** — distribui o material pronto nas pastas certas do vault (doutrina por área, legislação, jurisprudência…). O card fala **uma coisa de cada vez, na ordem que importa**, sempre com o botão da ação ali mesmo: ⚠ *"refatie antes"* (você corrigiu fichas e o material publicável está com a versão antiga — botão **↻ Refatiar agora**); depois ✗ *"N reprovadas"* (botão **📋 Corrigir fichas**; as prontas podem ser publicadas desde já — reprovada fica retida, nada se estraga); por fim ✓ *"tudo em dia — simule e publique"*. **Clique "Simular" primeiro**: além do plano, a simulação termina com **"PRÓXIMOS PASSOS para publicar 100%"**. Notas que você editou à mão no Obsidian **não são sobrescritas**.
8. **Auditar vault** — verifica as *ligações* do cérebro: fatia órfã, link quebrado, nota que "sumiu" dos painéis por erro de preenchimento.
9. **Radar** — cruza as novidades (leis alteradas, novos julgados — coletadas pelo assistente de IA na pasta `Radar/`) com as notas do seu acervo que as citam, e monta a **fila de revisão**. "Sinalizar A-conferir" marca as notas afetadas para você revisar — **a decisão de reclassificar é sempre sua**.

### 04 · Triagem — o raio-X dos seus PDFs

Depois da etapa 1, esta tabela mostra, para cada arquivo: idioma detectado, se precisa de OCR, a rota de conversão e o **tipo provável** (`legislacao`, `livro`, `jurisprudencia`…).

**Revise esta tabela — é o seu checkpoint.** Repare na última coluna:

- `A-conferir (palpite: alta)` — o sistema tem boa confiança (nome **e** conteúdo apontam o mesmo tipo).
- `A-conferir (palpite: media)` — confiança média: vale conferir.
- `A-conferir (indeterminado)` — o sistema **não chutou** (é assim que se evita que uma lei vire "livro" por engano). Classifique você.

### ✎ Fichas — o SEU passo do trilho (grupo QUALIDADE)

Depois da Qualidade (6) existe um card **sem número, com um lápis ✎**: é o único passo do trilho que é **trabalho seu**, não de script. O card mostra ao vivo quantas fichas precisam de você e quantas você já resolveu — **"3 corrigir · 5 conferir · 4 prontas ✓"** — e fica verde quando todas estão prontas. O botão **📋 Abrir fichas** abre a mesa de revisão, com tudo separado pelo que merece atenção:

- **✗ Corrigir** — bloqueiam a publicação (falta `tipo_fonte`, autoria, ementa…);
- **⚠ Conferir** — o que a **automação atribuiu e espera a sua confirmação**: `tipo_fonte` que é palpite da triagem, `tipo` derivado automaticamente, status/confiabilidade `A-conferir`;
- **✓ Prontas** — completas, nada a fazer.

Para ajustar ou confirmar: **✎ Editar** → o formulário abre com exatamente os campos que aquele `tipo_fonte` exige. Os **obrigatórios têm asterisco** `*`, e os obrigatórios **ainda vazios ficam em vermelho** — preencheu, o vermelho some. **💾 Salvar e revalidar** responde em **dois quadros**:

1. **Ficha** — o que ainda falta *neste formulário* ("preencha: autoria, ementa — destacados abaixo") ou ✓ completa;
2. **Outras etapas** — o que **não se resolve aqui** e para onde vai: ex. *"arquivo gigante ⤳ resolve-se na etapa 5 — Fatiar"*; e se as fatias **já existem**, aparece como **✓ resolvido** ("o mestre fica inteiro por design") em vez de assustar.

A **referência ABNT** ninguém digita à mão: com a ficha completa e o campo vazio, ela é **gerada e gravada automaticamente ao salvar** (o recibo mostra "referencia_abnt (gerada da ficha)"). Se já existir uma referência que **difere** da que a ficha atual gera, aparece o botão *↻ regenerar da ficha* — você decide. O **Normalizar** (etapa 5) faz o mesmo em lote para todas as fichas completas. Com obrigatórios vazios nada é gerado (sairia mutilado) e o painel diz o que falta.

**Salvar = revisar**: ao salvar, as marcas *"palpite da triagem"* / *"derivado automaticamente"* somem — você viu e confirmou. Com isso (e sem pendência de outra etapa), a ficha vai para **✓ Prontas** mesmo que restem avisos de texto (hifenização de OCR etc.) — eles ficam listados, mas não seguram: não são problema da ficha.

> Campo deixado **em branco não mexe** no arquivo. O mestre é o `2-MARKDOWN-BRUTO`: depois de corrigir, **refatie** (etapa 5) para as fatias herdarem a ficha.

---

## 3 · O dia a dia em 8 cliques

Um lote novo de PDFs, do download ao Obsidian:

1. Copie os PDFs para a pasta do acervo (no Windows Explorer mesmo).
2. Duplo-clique em **Iniciar-Acervo.bat**.
3. **(1) Analisar** → confira a tabela da seção 04.
4. **(2) Aplicar OCR** → espere o log terminar.
5. **(3) Converter** → **(4) Limpar** → **(5) Fatiar**.
6. **(6) Auditar qualidade** → a triagem abre sozinha: corrija os graves na mesa **✎ Fichas** e refatie (5) se mexeu nas fichas.
7. **(7) Simular** → conferiu? → **Publicar** (o card já diz quantas obras estão prontas e quantas ficariam retidas).
8. **(8) Auditar vault** → abra o Obsidian e navegue pelos MOCs. 🎉

Toda semana: **(9) Radar → Fila de revisão**, despache os itens marcados, e o cérebro continua vivo e confiável.

### 🧭 Levar ao SEU vault do Obsidian (o definitivo, que já tem conteúdo)

O vault de verdade pode estar em **outra pasta** e **já conter seu acervo antigo**. A entrega é direta e segura:

1. **Configuração (01)** → campo **"Vault do Obsidian (destino)"** → 📁 escolha a pasta do seu vault → **Definir**. Fica **lembrado**; Publicar, Auditar vault e Radar passam a apontar para lá.
2. No card **Publicar**, clique **🧭 Verificar destino** — o pré-voo mostra, sem tocar em nada: quantas notas suas já existem (e quantas estão **invisíveis aos painéis** por falta de area/tipo), as **colisões de nome** com o que será publicado (o Obsidian resolve links por *nome* — nome repetido = link ambíguo) e a **estrutura que falta** (MOCs das áreas, pasta Radar/, templates).
3. Se faltar estrutura: **🧱 Preparar vault** — cria **só o que falta**. MOC seu, feito à mão, **nunca é tocado**: aparece com o botão **🔁 Migrar marcadores**, que (se você quiser) insere as marcas `moc:auto` **sem alterar o conteúdo** — a partir daí o painel pode atualizar os painéis automáticos preservando a sua curadoria.
4. **Simular** → o plano + os avisos de ambiguidade de nome → **Publicar**. Regras de sempre: nada é sobrescrito, nada é apagado, reprovada fica retida, em conflito **o seu vault vence**.
5. **Auditar vault (8)** no destino: mostra o grafo íntegro e lista o que do seu acervo antigo está invisível aos painéis — catalogar o legado é opcional e pode ser feito aos poucos (mesma lógica das fichas).

> Seu conteúdo antigo convive em paz: ele só passa a **aparecer nos painéis dos MOCs** quando tiver `area`/`tipo` do vocabulário — até lá, continua acessível normalmente no Obsidian.

---

## 4 · Ver o resultado no Obsidian (também sem terminal)

1. Instale o [Obsidian](https://obsidian.md) (gratuito).
2. **Open folder as vault** → escolha a pasta `4-OBSIDIAN-VAULT` dentro do seu acervo.
3. Em *Settings → Community plugins*, instale e ative o **Dataview**.
4. Abra `00-Indices-MOCs/MOC-Tributario` (ou o MOC da sua área): os painéis se preenchem sozinhos — Vigente, Pendências, Doutrina, Jurisprudência, Legislação, Novidades.

> Os painéis refletem o preenchimento das fichas. Se uma nota "sumir" de um painel, rode a etapa **(8) Auditar vault** — o relatório aponta exatamente o campo a corrigir.

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
| Nota não aparece no MOC do Obsidian | Etapa **(8) Auditar vault** → abra `RELATORIO-VAULT.md` no próprio vault: ele lista a causa e a correção. |
| O painel pergunta "já concluída — continuar?" | Você clicou numa etapa verde. Se foi de propósito (reprocessar), confirme; senão, cancele. |
| "Converter pasta" respondia "nenhum arquivo exige âncora" | Versão antiga (≤3.7): só convertia livros. Atualize para a **v3.8.0+** — converte todos os PDFs pesquisáveis e lista no log os pulados por falta de OCR. |
| Corrigir idioma diz "não deu para detectar" | Atualize para a **v3.8.0+** (detecta pela cópia `_OCR` e pelo texto do próprio markdown). Se ainda assim não der, o caso é manual: peça ao suporte para rodar `corrigir_idioma.py arquivo.md --forcar por`. |
| Publicar: `tipo '(vazio)' sem pasta de publicação` | A nota não tem o campo `tipo` — sem ele não há rota nem painel no MOC. Rode **Normalizar** (etapa 5): ele deriva o `tipo` do tipo_fonte quando não há ambiguidade. O que sobrar (índice REPROVADO, ficha vazia) é o **refino da Fase 3c** — preencha a ficha do índice no Projeto Claude e publique de novo. |
| Publicar: `N fatia(s) retidas com o índice` | Proposital: fatia sem índice nasceria órfã no vault. Resolva o índice da obra (a razão está na mesma linha) e as fatias entram junto na próxima publicação. |
| Apaguei o `controle.csv` e as pastas geradas para reprocessar do zero, e a conversão não roda | Rode **(1) Analisar** de novo (o trilho recomeça do disco). Se você também apagou os PDFs **originais** e deixou só as cópias `_OCR.pdf`, atualize para a **v3.11.1+**: antes a triagem ignorava a cópia órfã e ela sumia do pipeline. |
| Parei no meio do trabalho — como retomo sem perder nada? | Feche o painel sem medo: na **v3.13+** a pasta do acervo fica **lembrada** (não precisa redefinir ao reabrir) e o trilho relê o disco para saber onde você está. **"Converter pasta" pula quem já foi convertido** — suas fichas corrigidas ficam intactas (reconverter é opt-in, via checkbox). Refatiar também limpa fatias antigas que sobrariam. |
| Ao salvar a ficha aparece "arquivo gigante — FATIE" | A partir da **v3.13** isso vem no quadro **"Outras etapas"**, separado da ficha: não se resolve no formulário. Se você **já fatiou** (etapa 5), aparece como ✓ resolvido — o arquivo-mestre fica inteiro por design. |

---

*Versão do guia: acompanha a versão do projeto (veja o [CHANGELOG.md](CHANGELOG.md)). Este guia é atualizado a cada release.*

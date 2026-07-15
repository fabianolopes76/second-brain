# 🖥️ Acervo — app de gerenciamento do pipeline (WSL2 + Windows)

## Por que esta arquitetura
- Seus **arquivos** estão no Windows (`C:\Users\...\drive`).
- As **ferramentas** (ocrmypdf, tesseract) rodam melhor no **Linux/WSL2**.
- O WSL2 enxerga o disco do Windows em `/mnt/c/...`; o Windows enxerga o `localhost` do WSL2.

→ **Servidor no WSL2, interface no navegador do Windows.** Nada é instalado no Windows, nada sai da sua máquina.

## ⚠️ PRIMEIRO DE TUDO: `python3 preparar.py`

Se você baixou os scripts pelo **Windows**, eles chegam ao WSL2 quebrados:

| Sintoma | Causa |
|---|---|
| `Permission denied` | falta a permissão de execução (`+x`) |
| `command not found` (mesmo com o arquivo lá) | **CRLF** — o `\r` do Windows gruda no shebang, e o Linux procura um interpretador chamado `bash\r` |
| arquivos `*:Zone.Identifier` na pasta | metadado do Windows ("veio da internet") |

Conserta os três de uma vez:
```bash
cd ~/projects/second-brain
python3 preparar.py
```
> **Por que Python e não `.sh`?** Um script bash não consegue se autoconsertar: o bash analisa o arquivo inteiro antes de executar e aborta no primeiro `\r`. Python lê CRLF sem reclamar.

> **Não use `sudo`.** Os scripts não precisam de root — e rodar como root cria arquivos que depois só o root consegue alterar.

> **Como evitar de vez:** extraia o `.zip` **dentro do WSL2** (`unzip pacote.zip`). Assim as quebras de linha são preservadas e não aparece `Zone.Identifier`.

## Instalar (uma vez)
```bash
# no WSL2 — ferramentas de sistema
sudo apt install -y ocrmypdf tesseract-ocr-por poppler-utils unpaper

# venv do Python (evita o conflito numpy × scipy — ver Apêndice A do WORKFLOW)
python3 -m venv ~/venvs/acervo
source ~/venvs/acervo/bin/activate && pip install pymupdf && deactivate
```
> O **app em si não precisa de pip**: usa só a biblioteca padrão do Python 3.

## Rodar
```bash
cd ~/projects/second-brain          # a raiz do projeto — onde ficam os scripts
python3 acervo_app.py
```
Depois abra no navegador do **Windows**: **http://localhost:8765**

Opções: `--port 8765` · `--root "C:\Users\...\drive"` · `--scripts .` · `--venv ~/venvs/acervo`

## O que o painel faz
| Seção | Função |
|---|---|
| **01 Pasta** | **Botão “📁 Procurar…”** abre um navegador de pastas: percorre os discos do Windows (`/mnt/c`, `/mnt/d`) e o WSL2, com atalhos e contagem de PDFs. Não precisa digitar caminho. (Colar `C:\...` também funciona — converte sozinho.) |
| **02 Diagnóstico** | Confere ocrmypdf, tesseract (**6 idiomas**), poppler, unpaper, venv+PyMuPDF e os scripts. Cada pendência vem com o **comando pronto e botão “Copiar”**; no topo, um botão **“Copiar tudo”** funde todos os `apt install` num único comando |
| **03 Pipeline** | Triagem → OCR em lote → Paginação → Seleção de arquivos → Validar → **Auditar** |
| **04 Execução** | Log ao vivo do que está rodando |
| **05 Triagem** | Tabela do `controle.csv`: páginas, quantas sem texto, tipo provável, se exige âncora, rota |

## O ciclo que o app fecha
```
Triagem  →  controle.csv  →  Paginação  →  YAML pré-preenchido  →  Projeto Claude
(detecta       (tipo_fonte     (só nos que      (tipo_fonte +          (preenche autor,
 escaneados)    provável)       exigem âncora)   localizador)           título, editora…)
```
A triagem **adivinha o `tipo_fonte`** pelo nome do arquivo (livro? acórdão? lei?) e isso determina o resto: doutrina precisa de âncora `{{p.NN}}`; lei cita-se por artigo; acórdão, pelo julgado. O palpite vai para o YAML já com o **localizador correto** — mas é **palpite**: revise na tabela antes de seguir.

## Auditar: o que gerei já serve?

O botão **Auditar** responde à pergunta que importa: *o material convertido está pronto para ser citado em peça e consultado pela IA?*

Ele verifica, arquivo a arquivo:
1. Frontmatter YAML presente
2. `tipo_fonte` definido (governa todo o resto)
3. Idioma declarado
4. **Âncoras de localização, quando o tipo exige** (doutrina precisa; lei e acórdão não)
5. Campos ABNT obrigatórios daquele tipo
6. `referencia_abnt` montada
7. `resumo` (a camada 1 que a IA lê antes de abrir o texto)
8. **Fatiamento** — arquivo gigante degrada a IA e estoura tokens
9. Sanidade do texto (hifenização quebrada, cabeçalhos soltos, ruído de OCR)
10. Se já passou por conferência humana

Cada arquivo recebe **PRONTO**, **PARCIAL** ou **REPROVADO**, e o script grava um `RELATORIO-AUDITORIA.md` na pasta, com os bloqueios e o que fazer em cada caso.

```
✓ TRIB_DOUT_2023_Curso-Direito-Tributario_Machado.md   [PRONTO]
! CTN.md                                               [PARCIAL]
    ! resumo curto demais (<15 palavras)
✗ Sabbag-Manual-Tributario.md                          [REPROVADO]
    ✗ campos ABNT vazios: autoria, titulo, editora, ano
    ✗ referencia_abnt vazia — sem ela não se monta a nota de rodapé

PRONTO: 1  |  PARCIAL: 1  |  REPROVADO: 3
```

Também roda direto no terminal:
```bash
python3 auditar_acervo.py "/mnt/c/Users/.../_Analise"
python3 auditar_acervo.py "/mnt/c/Users/.../_Analise" --detalhado
```

## O trilho: um pipeline que se guia sozinho

As etapas não são mais botões soltos. Elas formam um **trilho numerado** em 4 fases — **Entrada** (triagem, OCR) · **Conversão** (paginação) · **Preparo** (limpar, fatiar) · **Qualidade** (validar, auditar) — e o app **lê o estado real do disco** para saber onde você está:

- ⬤ **Feito** (verde) — já rodou. Mostra o resultado: “5 arquivos”, “4 markdown”, “8 fatias”.
- ⬤ **Ativa** (borgonha, destacada) — é a sua próxima ação. Só ela mostra os campos avançados.
- ⬤ **Bloqueada** (apagada) — falta um pré-requisito, e o app diz qual (“faça a triagem”, “converta antes”).

Assim ninguém precisa decorar a ordem: o trilho responde sozinho “e agora, o quê?”.

## Janelas móveis e redimensionáveis

Nomes de arquivo jurídico são longos (*“Teoria da imposição tributária (Ives Gandra da Silva Martins).pdf”*). Por isso o navegador:

- **Arrasta pelo cabeçalho** — tire a janela da frente do que você quer ver.
- **Redimensiona pelas bordas** (direita, esquerda, base) e pelo **canto inferior direito**.
- **Duplo clique no título = maximiza** (e de novo, restaura).
- **Guarda o tamanho e a posição** entre aberturas — ajustou uma vez, fica assim.
- O **caminho completo** aparece como *tooltip* em cada item e no rodapé, com rolagem horizontal.

## Navegar em vez de digitar

Todo campo de caminho tem um botão que abre o **navegador de pastas**:

- **Barra lateral com atalhos**: discos do Windows (`💾 Windows C:`), pastas do usuário (Documents, Downloads, Desktop) e locais do WSL2 (`🐧 Home`).
- **Breadcrumb** para voltar a qualquer nível; botão **↑ Acima**.
- **Contagem de PDFs** em cada pasta — ajuda a achar o acervo sem abrir tudo.
- Pastas sem permissão são tratadas sem quebrar a navegação.

### Selecionar vários arquivos (fila de processamento)

O botão **📄 Escolher…** abre o navegador em modo arquivo, com **caixas de seleção**:

- Marque **um ou vários** PDFs/ePUBs/MOBIs (ou use **Marcar todos** na pasta).
- Clique em **Adicionar selecionados** — eles vão para a **fila**.
- **Navegue para outra pasta e adicione mais** — a fila **acumula**, permitindo juntar obras espalhadas pelo disco.
- Remova itens com **×** ou esvazie com **limpar**.
- **Converter** processa todos em sequência, com log ao vivo (`>> [2/7] Kelsen…`).

Para **cada** arquivo da fila, o app faz sozinho:
1. **Detecta o idioma** (pt/en/de/fr/it/es);
2. **Infere o `tipo_fonte`** pelo nome (livro? acórdão? lei?);
3. Converte para Markdown **com âncoras de página**;
4. Ao final, **valida a integridade** de tudo que gerou.

Exemplo real, 4 obras em 4 idiomas numa tacada:
```
>> [1/4] Curso-Direito-Tributario.pdf      tipo=livro idioma=por   ✓
>> [2/4] Kelsen-Reine-Rechtslehre.pdf      tipo=livro idioma=deu   ✓
>> [3/4] Hart-Concept-of-Law.pdf           tipo=livro idioma=eng   ✓
>> [4/4] Carbonnier-Droit-Civil.pdf        tipo=livro idioma=fra   ✓
=== VALIDACAO ===  Resumo: 4/4 arquivo(s) com âncoras íntegras.
```

> **ePUB/MOBI na fila:** são convertidos pelo Calibre, mas o app **avisa** que esses formatos não têm paginação fixa — não servem para citação ABNT com página. Para citar, use o PDF paginado.

> **Quando usar a fila × a pasta inteira:** a fila é para lotes escolhidos a dedo (uma remessa nova, um caso específico). Para varrer todo o acervo, use **Triagem → OCR** (Fases 1 e 2), que detecta sozinho o que precisa de OCR.

## Resolver dependências em um clique

O diagnóstico não só aponta o que falta — ele **entrega o comando**. Cada item pendente traz um botão **Copiar**, e o bloco vermelho no topo consolida tudo:

```
sudo apt install -y unpaper tesseract-ocr-deu tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-spa && python3 -m venv ~/venvs/acervo && source ~/venvs/acervo/bin/activate && pip install pymupdf
```

Os vários `apt install` viram **um só** (mais rápido e sem repetir download de índice), e o resto é encadeado com `&&`. Cole no terminal do WSL2, recarregue a página, e os itens ficam verdes.

> Mensagens que não são comandos (ex.: “defina a pasta acima”) **não** viram bloco copiável — só o que dá para colar direto.

## Se o venv foi criado DENTRO do acervo (bin/ include/ lib/ pyvenv.cfg)

Sintoma: a pasta dos livros ganhou `bin`, `include`, `lib`, `lib64`, `pyvenv.cfg`, e o prompt do terminal virou `(_Analise)`.

```bash
deactivate

ACERVO="/mnt/c/Users/SeuUsuario/Dropbox/.../_Analise"
rm -rf "$ACERVO/bin" "$ACERVO/include" "$ACERVO/lib" "$ACERVO/lib64" "$ACERVO/pyvenv.cfg"

# recrie no lugar certo
python3 -m venv ~/venvs/acervo
source ~/venvs/acervo/bin/activate && pip install pymupdf
```
No app, use o botão **↺** ao lado do campo venv para restaurar `~/venvs/acervo`.

## ⚠️ O venv NUNCA vai dentro do acervo

O campo **venv** deve apontar para algo como `~/venvs/acervo` — **nunca** para a pasta dos livros.

Por quê: `python3 -m venv` aceita **vários diretórios de uma vez**. Se o caminho tiver espaços e não estiver entre aspas, o bash o quebra em pedaços e o comando cria **vários venvs em lugares errados** — inclusive dentro do Dropbox, que então sincroniza milhares de arquivos do Python.

O app agora tem duas travas:
- **Todos os comandos gerados vêm com aspas** (`python3 -m venv '/caminho com espaços'`).
- **O app recusa** um venv que seja, ou esteja dentro, da pasta do acervo.

Se isso já aconteceu, limpe assim (ajuste os nomes):
```bash
rm -rf "/mnt/c/Users/SeuUsuario/Dropbox/_Prof."   # o venv criado por engano
cd ~/projects/second-brain && rm -rf Fabiano Lopes
```
> Confira que a pasta **verdadeira** (com o nome completo, ex.: `_Prof. Fabiano Lopes`) continua intacta — a que deve sumir é a truncada.

## Cuidados
- **`MODE=manter` é o padrão** — o PDF original é a fonte de verdade para conferir a página citada. Não o destrua.
- **Desempenho:** ler `/mnt/c/` do WSL2 é mais lento que o disco nativo do Linux. Em acervos grandes, copie o lote para `~/acervo`, processe e devolva.
- **Uma tarefa por vez** — o painel bloqueia os botões enquanto algo roda.
- **Quebra de linha:** se o `aplicar_ocr.sh` foi editado no Windows e dá erro estranho, rode `dos2unix aplicar_ocr.sh` (CRLF quebra scripts bash).
- **Porta ocupada?** `python3 acervo_app.py --port 8899`.

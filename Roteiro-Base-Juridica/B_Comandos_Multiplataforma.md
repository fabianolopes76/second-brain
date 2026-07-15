---
titulo: "Módulo B — Comandos Multiplataforma"
parte_de: "Pacote Base de Conhecimento Jurídica v2.0"
tipo: Referência operacional
data: 2026-07-07
---

# Módulo B — Comandos Multiplataforma (Windows · Ubuntu/Debian · macOS)

> **Como ler este módulo.** Cada bloco traz o comando para os três sistemas. No **Windows**, a rota mais estável para OCR é o **WSL** (Ubuntu dentro do Windows) — nesse caso, use os comandos da coluna Ubuntu dentro do terminal WSL. Onde o Windows nativo funciona bem (Calibre, Pandoc), o comando nativo está indicado.
> **Segurança:** todos os comandos de OCR e conversão rodam **localmente**. Nada é enviado à nuvem nesta etapa.

---

## 0. Preparação do ambiente (instalar dependências)

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y calibre ocrmypdf tesseract-ocr tesseract-ocr-por ghostscript pandoc python3-pip
# (opcional) versão mais recente do OCRmyPDF:
pip install --user --upgrade uv && uv pip install --system --upgrade ocrmypdf
```

### macOS (com Homebrew)
```bash
brew install --cask calibre obsidian
brew install ocrmypdf tesseract tesseract-lang ghostscript pandoc
```

### Windows
```powershell
# Opção 1 — nativo, via Chocolatey (PowerShell como Administrador):
choco install -y calibre pandoc tesseract ghostscript python obsidian
pip install ocrmypdf
# Instalar o idioma português do Tesseract: baixar 'por.traineddata' e colocá-lo
# na pasta tessdata do Tesseract (ex.: C:\Program Files\Tesseract-OCR\tessdata)

# Opção 2 — recomendada para OCR: usar WSL (Ubuntu dentro do Windows)
wsl --install         # reinicie e crie o usuário Ubuntu
# Depois, dentro do terminal Ubuntu (WSL), rode os comandos da seção Ubuntu acima.
```

---

## 1. OCR — transformar PDF escaneado (imagem) em PDF pesquisável/legível

Este é o passo que torna um "PDF não editável" em "editável e legível". Serve de **pré-requisito** para depois converter em Markdown.

### Comando básico (igual nos três sistemas — no Windows nativo, sem `sudo`)
```bash
ocrmypdf -l por entrada_escaneada.pdf saida_com_texto.pdf
```
- `-l por` → reconhece **português**. Para bilíngue: `-l por+eng`.

### Comando recomendado para documentos jurídicos escaneados (digitalização imperfeita)
```bash
ocrmypdf -l por --deskew --rotate-pages --clean --output-type pdfa \
  --sidecar saida_texto.txt \
  entrada_escaneada.pdf saida_com_texto.pdf
```
- `--deskew` endireita páginas tortas · `--rotate-pages` corrige páginas viradas · `--clean` remove ruído antes do OCR · `--output-type pdfa` gera PDF/A (bom para arquivo) · `--sidecar` também salva o texto puro num `.txt` (útil para conferência rápida).

### Quando o PDF já tem uma camada de texto ruim (ex.: OCR antigo de baixa qualidade)
```bash
ocrmypdf -l por --force-ocr entrada.pdf saida.pdf
```
- `--force-ocr` refaz o OCR por cima. (Se der conflito, `--redo-ocr` é a variante mais conservadora.)

### OCR em lote (uma pasta inteira)
**Ubuntu/macOS (bash/zsh):**
```bash
mkdir -p 1-OCR
for f in 0-ENTRADA/*.pdf; do
  nome=$(basename "$f")
  ocrmypdf -l por --deskew --rotate-pages --skip-text "$f" "1-OCR/$nome" || echo "FALHOU: $nome"
done
```
- `--skip-text` pula páginas que já têm texto (evita retrabalho em PDFs mistos).

**Windows (PowerShell nativo):**
```powershell
New-Item -ItemType Directory -Force -Path 1-OCR | Out-Null
Get-ChildItem "0-ENTRADA\*.pdf" | ForEach-Object {
  ocrmypdf -l por --deskew --rotate-pages --skip-text $_.FullName ("1-OCR\" + $_.Name)
}
```

---

## 2. Conversão para Markdown com o Calibre (ePUB/MOBI/AZW3)

Rota principal, alta qualidade. Gera `.txt` com formatação Markdown; depois **renomeia para `.md`**.

### Um arquivo (igual nos três sistemas)
```bash
ebook-convert "entrada.epub" "saida.txt" \
  --txt-output-formatting=markdown \
  --enable-heuristics \
  --keep-links --keep-image-references \
  --txt-output-encoding=utf-8 \
  --chapter "//h:h1"
```
Depois renomeie: **Ubuntu/macOS:** `mv "saida.txt" "saida.md"` · **Windows (PowerShell):** `Rename-Item "saida.txt" "saida.md"`.

### Lote (todos os .epub de uma pasta)
**Ubuntu/macOS:**
```bash
mkdir -p 2-MARKDOWN-BRUTO
for f in *.epub; do
  ebook-convert "$f" "2-MARKDOWN-BRUTO/${f%.epub}.txt" \
    --txt-output-formatting=markdown --enable-heuristics \
    --keep-links --txt-output-encoding=utf-8 --chapter "//h:h1"
  mv "2-MARKDOWN-BRUTO/${f%.epub}.txt" "2-MARKDOWN-BRUTO/${f%.epub}.md"
done
```
**Windows (PowerShell):**
```powershell
New-Item -ItemType Directory -Force -Path 2-MARKDOWN-BRUTO | Out-Null
Get-ChildItem "*.epub" | ForEach-Object {
  $out = "2-MARKDOWN-BRUTO\" + $_.BaseName + ".txt"
  ebook-convert $_.FullName $out --txt-output-formatting=markdown --enable-heuristics --keep-links --txt-output-encoding=utf-8 --chapter "//h:h1"
  Rename-Item $out ($_.BaseName + ".md")
}
```

> **Teste antes do lote.** Rode em 3–5 arquivos e confira o resultado. Há relatos de falha do `ebook-convert` para markdown em alguns arquivos específicos — os que falharem seguem para a rota de ferramenta dedicada (seção 4).

---

## 3. PDF nativo simples → Markdown pela cadeia PDF → ePUB (revisado) → Markdown

Para PDF **com texto** e layout simples, converter primeiro para ePUB dá melhor resultado que ir direto ao Markdown.
```bash
# Passo 1: PDF -> ePUB (ajuste o fator de remoção de quebras de linha se os parágrafos ficarem picotados)
ebook-convert "entrada.pdf" "intermediario.epub" --enable-heuristics
# Passo 2: (opcional) revise o ePUB no editor do Calibre: "Editar livro"
# Passo 3: ePUB -> Markdown (comando da seção 2)
ebook-convert "intermediario.epub" "saida.txt" --txt-output-formatting=markdown --enable-heuristics --txt-output-encoding=utf-8
```
> Para PDF de **layout complexo** (duas colunas, muitas tabelas/notas) **não** use o Calibre — vá para a seção 4.

---

## 4. PDF complexo/escaneado → Markdown com ferramenta dedicada

### Opção A — Marker (melhor fidelidade estrutural)
```bash
pip install marker-pdf         # requer Python; GPU recomendada
marker_single com_texto.pdf --output_format markdown --output_dir ./2-MARKDOWN-BRUTO
# Para layouts muito ruins, refino com LLM:
marker_single com_texto.pdf --output_format markdown --use_llm --output_dir ./2-MARKDOWN-BRUTO
# Se o texto sair "embolado", force o re-OCR:
marker_single escaneado.pdf --output_format markdown --force_ocr --output_dir ./2-MARKDOWN-BRUTO
```

### Opção B — Docling (melhor para RAG/estrutura semântica; licença MIT)
```bash
pip install docling
docling com_texto.pdf --to md --output ./2-MARKDOWN-BRUTO
```

### Opção C — PyMuPDF4LLM (PDF nativo simples, muito rápido, sem OCR)
```bash
pip install pymupdf4llm
python -c "import pymupdf4llm, pathlib; pathlib.Path('saida.md').write_text(pymupdf4llm.to_markdown('entrada.pdf'))"
```

> **Fluxo combinado para escaneado difícil:** `ocrmypdf -l por` (seção 1) **primeiro**, depois Marker/Docling sobre o PDF já com texto.

---

## 5. Documentos em Word (modelos internos) → Markdown com Pandoc
```bash
pandoc "modelo_peticao.docx" -o "modelo_peticao.md" --wrap=none
# Lote (Ubuntu/macOS):
for f in *.docx; do pandoc "$f" -o "${f%.docx}.md" --wrap=none; done
```
- `--wrap=none` evita quebras de linha artificiais (melhor para ingestão por IA).

---

## 6. Renomeação padronizada em lote

Padrão do roteiro: `[AREA]_[TIPO]_[ANO]_[Titulo-Curto]_[Autor-ou-Orgao].md`. A renomeação inteligente (que lê o conteúdo para decidir área/tipo) é melhor feita pelo **Cowork** (Módulo D). Para renomeação mecânica simples:

**Ubuntu/macOS — trocar espaços por hífen e remover acentos básicos:**
```bash
for f in *.md; do
  novo=$(echo "$f" | tr ' ' '-' | iconv -f UTF-8 -t ASCII//TRANSLIT)
  mv "$f" "$novo"
done
```
**Windows (PowerShell) — trocar espaços por hífen:**
```powershell
Get-ChildItem "*.md" | Rename-Item -NewName { $_.Name -replace ' ','-' }
```

---

## 7. Verificações úteis

```bash
# O PDF tem camada de texto? (se retornar texto, é nativo; se vier vazio, é escaneado)
pdftotext -l 2 entrada.pdf - | head        # 'pdftotext' vem do poppler-utils
# Ubuntu: sudo apt install poppler-utils | macOS: brew install poppler | Windows: choco install poppler

# Conferir a codificação de um .md (deve ser UTF-8)
file -i saida.md            # Ubuntu/macOS
```

---

### Referência-relâmpago (cola de bolso)
| Preciso… | Comando-chave |
|---|---|
| Tornar PDF escaneado legível | `ocrmypdf -l por --deskew --rotate-pages in.pdf out.pdf` |
| ePUB/MOBI → Markdown | `ebook-convert in.epub out.txt --txt-output-formatting=markdown --enable-heuristics` |
| PDF complexo → Markdown | `marker_single in.pdf --output_format markdown` **ou** `docling in.pdf --to md` |
| PDF nativo rápido → Markdown | `pymupdf4llm.to_markdown('in.pdf')` |
| Word → Markdown | `pandoc in.docx -o out.md --wrap=none` |
| Testar se PDF tem texto | `pdftotext -l 2 in.pdf -` |

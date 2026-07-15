---
titulo: "Módulo A — Catálogo de Aplicativos"
parte_de: "Pacote Base de Conhecimento Jurídica v2.0"
tipo: Referência
data: 2026-07-07
---

# Módulo A — Catálogo de Aplicativos

Ficha técnica de cada ferramenta citada no roteiro. Legenda de recomendação: 🟢 essencial · 🔵 recomendado · ⚪ opcional/situacional.

> **Leitura importante sobre "gratuito".** Vários programas são *open source* e gratuitos, mas têm **licenças** diferentes (GPL, MPL, MIT, AGPL). Para uso **interno** de um escritório, praticamente todos são livres. Restrições costumam aparecer só se você **redistribuir** o software ou embuti-lo num produto comercial. Onde houver nuance relevante, ela está anotada.

---

## 1. 🟢 Calibre — catálogo e conversão de e-books
- **O que é:** gerenciador de biblioteca de e-books e conversor (o "coração" da catalogação e da conversão de ePUB/MOBI → Markdown).
- **Gratuito?** Sim, 100%. *Open source*, licença GPL v3.
- **Onde obter:** https://calibre-ebook.com/download
- **Instalação:**
  - **Windows:** baixar o instalador `.msi`/`.exe` no site e executar (duplo-clique). Também via Chocolatey: `choco install calibre`.
  - **macOS:** baixar o `.dmg` no site e arrastar para *Aplicativos*. Também via Homebrew: `brew install --cask calibre`.
  - **Ubuntu/Debian:** o pacote do repositório costuma ser antigo; o método oficial recomendado é o instalador binário:
    ```bash
    sudo -v && wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sudo sh /dev/stdin
    ```
- **Estabilidade/recomendação:** 🟢 Maduro, ativo há mais de 15 anos, padrão-ouro da área. Excelente para ePUB/MOBI. **Limitação conhecida:** o próprio manual reconhece que **PDF é um dos piores formatos de origem** e o Calibre **não faz OCR** — por isso PDFs escaneados/complexos vão para outra ferramenta (itens 3–6).
- **Ferramenta de linha de comando:** acompanha o `ebook-convert` (usado no Módulo B).

---

## 2. 🟢 OCRmyPDF — cria camada de texto em PDF escaneado
- **O que é:** adiciona uma camada de texto pesquisável/selecionável a PDFs que são apenas imagem (escaneados). É o passo que torna "PDF não editável" em "PDF legível e editável".
- **Gratuito?** Sim. *Open source*, licença **MPL-2.0** (permite uso comercial, inclusive integrando com código fechado).
- **Onde obter:** https://github.com/ocrmypdf/OCRmyPDF · Docs: https://ocrmypdf.readthedocs.io
- **Dependências obrigatórias:** **Tesseract OCR** (item 3) e **Ghostscript** (item 4). O `pip` sozinho **não** instala essas dependências de sistema.
- **Instalação (resumo — comandos completos no Módulo B):**
  - **Ubuntu/Debian:** `sudo apt install ocrmypdf tesseract-ocr-por` (versão do sistema) — ou versão mais recente via `uv`/`pip` após instalar as dependências.
  - **macOS:** `brew install ocrmypdf` e `brew install tesseract-lang` (pacotes de idioma).
  - **Windows:** via **Chocolatey** (instala Python, Tesseract, Ghostscript) e depois `pip install ocrmypdf`; **ou** via **WSL** (Ubuntu dentro do Windows) seguindo a rota Ubuntu.
- **Estabilidade/recomendação:** 🟢 Muito estável e amplamente usado; roda em Linux, macOS, Windows e FreeBSD. Roda **100% local** (bom para sigilo). Para português, é obrigatório instalar o pacote `por` do Tesseract.

---

## 3. 🟢 Tesseract OCR — motor de reconhecimento óptico
- **O que é:** o motor de OCR que o OCRmyPDF usa por baixo. Converte imagem de texto em texto.
- **Gratuito?** Sim. *Open source*, licença Apache 2.0.
- **Onde obter:** https://github.com/tesseract-ocr/tesseract
- **Instalação:** normalmente vem junto na instalação do OCRmyPDF; o essencial é garantir o **pacote de idioma português**:
  - **Ubuntu/Debian:** `sudo apt install tesseract-ocr tesseract-ocr-por`
  - **macOS:** `brew install tesseract tesseract-lang`
  - **Windows:** instalar via Chocolatey (`choco install tesseract`) ou pelo instalador da UB Mannheim; adicionar o idioma `por`.
- **Estabilidade/recomendação:** 🟢 Padrão da indústria para OCR livre. Qualidade boa em documentos limpos; para digitalizações ruins (torto, manchado), combine com as opções `--deskew`/`--rotate-pages` do OCRmyPDF (Módulo B).

---

## 4. 🟢 Ghostscript — processamento de PDF
- **O que é:** biblioteca/utilitário de PDF/PostScript usada pelo OCRmyPDF (e por muitos fluxos de PDF) para rasterização e geração de PDF/A.
- **Gratuito?** Sim. *Open source* (AGPL) e também licença comercial da Artifex. Para uso interno, a versão livre atende.
- **Onde obter:** https://www.ghostscript.com
- **Instalação:** **Ubuntu/Debian:** `sudo apt install ghostscript` · **macOS:** `brew install ghostscript` · **Windows:** `choco install ghostscript` ou instalador do site.
- **Estabilidade/recomendação:** 🟢 Dependência silenciosa, mas essencial. Instale e esqueça.

---

## 5. 🔵 Marker — PDF complexo/escaneado → Markdown de alta fidelidade
- **O que é:** conversor moderno de PDF (e imagens, DOCX, PPTX etc.) para Markdown/JSON, com OCR embutido (Surya). Preserva títulos, listas, tabelas e **notas de rodapé** melhor que o Calibre. Opção `--use_llm` refina layouts difíceis.
- **Gratuito?** Sim para uso individual/pesquisa; **atenção**: o projeto impõe **restrições de licença para uso comercial** acima de certo faturamento — verifique os termos no repositório antes de adotar em produção no escritório.
- **Onde obter:** https://github.com/datalab-to/marker
- **Instalação:** requer Python; `pip install marker-pdf`. Usa PyTorch — **GPU recomendada** (roda em CPU, porém lento). Multiplataforma (Win/macOS/Linux).
- **Estabilidade/recomendação:** 🔵 Excelente qualidade estrutural; é a melhor escolha "faz-tudo" para PDF difícil. Pese o custo de instalar Python+PyTorch e a questão de licença comercial.

---

## 6. 🔵 Docling — conversão orientada a RAG (pipelines de IA)
- **O que é:** kit da IBM Research para converter documentos preservando a **hierarquia semântica**, pensado para pipelines de recuperação (RAG). Integra OCR (Tesseract/EasyOCR/RapidOCR) e conecta a LangChain/LlamaIndex.
- **Gratuito?** Sim. *Open source*, licença MIT (permissiva, uso comercial livre).
- **Onde obter:** https://github.com/docling-project/docling
- **Instalação:** `pip install docling` (Python). Multiplataforma.
- **Estabilidade/recomendação:** 🔵 Ótimo quando o objetivo final é alimentar IA e você quer estrutura semântica limpa (especialmente **tabelas**). Licença MIT é a mais confortável para uso empresarial entre os conversores dedicados.

---

## 7. ⚪ PyMuPDF4LLM — extração rápida de PDF nativo
- **O que é:** extensão do PyMuPDF que extrai PDF **nativo** (com texto) direto em Markdown pronto para LLM. Sem modelos de ML, sem GPU — rápido.
- **Gratuito?** Sim, porém o PyMuPDF é **AGPL**: uso interno é tranquilo; se um dia for embutir num produto/serviço distribuído, revise a licença (ou considere a licença comercial da Artifex).
- **Onde obter:** https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/ · `pip install pymupdf4llm`
- **Estabilidade/recomendação:** ⚪ A opção **mais rápida** para PDFs nativos simples em massa. Não serve para escaneados (não faz OCR).

---

## 8. ⚪ pdf-craft — digitalização de livros escaneados
- **O que é:** ferramenta especializada em converter **livros físicos escaneados** para Markdown/EPUB, com OCR local; gera sumário e trata notas de rodapé/fórmulas/tabelas.
- **Gratuito?** Sim, *open source*, roda **totalmente local** (bom para sigilo).
- **Onde obter:** https://pypi.org/project/pdf-craft/ (buscar também o repositório no GitHub) · `pip install pdf-craft`
- **Estabilidade/recomendação:** ⚪ Nicho, mas valioso se o acervo tem muitos livros escaneados. Para documentos avulsos, Marker/Docling bastam.

---

## 9. ⚪ Pandoc — conversor universal de documentos
- **O que é:** "canivete suíço" de conversão entre formatos de texto (DOCX, HTML, LaTeX, Markdown etc.). Útil para normalizar documentos que **não** são e-book/PDF (ex.: `.docx` de modelos internos → Markdown).
- **Gratuito?** Sim. *Open source*, GPL.
- **Onde obter:** https://pandoc.org
- **Instalação:** **Ubuntu/Debian:** `sudo apt install pandoc` · **macOS:** `brew install pandoc` · **Windows:** `choco install pandoc` ou instalador do site.
- **Estabilidade/recomendação:** ⚪ Confiabilíssimo. Bom coadjuvante para os modelos internos em Word.

---

## 10. 🟢 Obsidian — o "segundo cérebro" (vault Markdown)
- **O que é:** editor/organizador de notas em Markdown local (arquivos ficam no seu disco, em texto puro). É onde o acervo vira base navegável e consultável por IA.
- **Gratuito?** **Sim — inclusive para uso empresarial.** Desde fev/2025 a **licença comercial deixou de ser obrigatória**; o app é gratuito para trabalho. A *Commercial license* (US$ 50/usuário/ano) permanece **opcional**, como forma de apoiar o desenvolvimento. (Fonte oficial: página de preços da Obsidian.)
- **Add-ons pagos opcionais:** **Sync** (sincronização criptografada entre dispositivos, ~US$ 4–5/mês) e **Publish** (publicar notas na web). Alternativas gratuitas de sincronização: OneDrive, Google Drive, Dropbox, Git, Syncthing.
- **Onde obter:** https://obsidian.md · Preços: https://obsidian.md/pricing
- **Instalação:** instaladores nativos para **Windows, macOS e Linux** (no site). Linux também via AppImage/Flatpak/Snap. **Windows:** `choco install obsidian` · **macOS:** `brew install --cask obsidian`.
- **Plugin recomendado:** **Dataview** (gratuito) — gera índices/MOCs automáticos a partir do *frontmatter* YAML (ex.: "listar tudo com `area: Tributário` e `status: Vigente`").
- **Estabilidade/recomendação:** 🟢 Local-first (bom para sigilo e propriedade dos dados), maduro, ecossistema enorme de plugins. **Ressalva:** foi projetado para uso individual — não tem edição colaborativa em tempo real; compartilhamento de *vault* em equipe se faz por Git/nuvem, com cuidado de conflitos.

---

## 11. 🟢 Claude Desktop (Chat + Cowork + Code) — camada de IA agêntica
- **O que é:** app de desktop da Anthropic que reúne o **Chat**, o **Cowork** (agente para trabalho de conhecimento) e o **Code**. É por ele que se automatiza triagem, conversão em lote, extração de metadados, fatiamento e montagem do vault.
- **Gratuito?** O Cowork exige **plano pago** (Pro, Max, Team ou Enterprise) e está em *research preview*. O Chat tem camada gratuita, mas as funções agênticas do Cowork não.
- **Onde obter:** https://claude.com/download
- **Instalação:** app nativo para **Windows e macOS**. O Cowork chegou ao **Windows em 10/02/2026** com paridade de recursos com o macOS.
- **Requisitos/limitações relevantes:**
  - O **app precisa ficar aberto** enquanto o Cowork trabalha; fechar o app encerra a sessão/tarefa.
  - Em *research preview*, **não há memória entre sessões** e o histórico/auditoria é limitado — daí a ressalva de **sigilo** para dados de clientes (ver Índice-Mestre, aviso 1).
  - Pede **permissão explícita** antes de apagar arquivos (proteção contra exclusão).
- **Estabilidade/recomendação:** 🟢 para trabalho com **material público** do acervo e para orquestrar o pipeline. Para dados sigilosos, aplique os controles do aviso 1.
- **Ferramentas irmãs úteis:** **Claude in Chrome** (agente de navegador — usado no monitoramento do Módulo E), **Claude Design** (canvas/design — usado para painéis e materiais), **Claude Code** (linha de comando para scripts do pipeline).

---

## 12. ⚪ Gemini (Google) — segunda IA do escritório
- **O que é:** família de modelos do Google, usada em complemento ao Claude. Destaques para este projeto: **contexto gigante** (ingerir obras inteiras), forte **multimodalidade** (ler páginas escaneadas/tabelas) e **grounding com Google Search** (monitoramento de notícias).
- **Gratuito?** App do Gemini tem camada gratuita; a **API** tem camada gratuita apenas para modelos **Flash/Flash-Lite** (modelos **Pro** passaram a ser pagos em abril/2026). Planos de assinatura (Google AI Pro/Ultra) à parte.
- **Onde obter:** app https://gemini.google.com · API/Studio https://ai.google.dev · docs de modelos https://ai.google.dev/gemini-api/docs/models
- **Instalação:** uso via web/app ou via API (chave no Google AI Studio). Sem instalação de desktop obrigatória.
- **Estabilidade/recomendação:** ⚪→🔵 conforme a tarefa. Ver a **matriz de alocação** no Módulo C, que distribui as etapas entre Claude e Gemini por custo/qualidade/contexto.

---

## 13. Auxiliares de instalação (gerenciadores de pacote)
Facilitam instalar tudo acima de forma padronizada:
- **Windows — Chocolatey:** https://chocolatey.org (`choco install ...`). Alternativa nativa: **winget**.
- **macOS — Homebrew:** https://brew.sh (`brew install ...`).
- **Python — uv** (instalador/gerenciador rápido, recomendado para os conversores em Python): https://github.com/astral-sh/uv
- **WSL (Windows Subsystem for Linux):** permite rodar o fluxo Ubuntu dentro do Windows — a rota mais estável para OCRmyPDF no Windows. Instale com `wsl --install` no PowerShell como administrador.

---

### Resumo de decisão rápida
- **Todo escritório instala:** Calibre + OCRmyPDF (+Tesseract-por +Ghostscript) + Obsidian + Claude Desktop. (todos gratuitos, exceto o plano pago do Cowork)
- **Se há muito PDF difícil/escaneado:** adicione **Docling** (licença MIT, confortável) e/ou **Marker** (melhor qualidade, checar licença comercial).
- **Se há PDF nativo em massa e simples:** **PyMuPDF4LLM** para velocidade.
- **Livros físicos escaneados:** **pdf-craft**.
- **Modelos internos em Word:** **Pandoc**.

# Auditoria do Acervo — corpus

**18 arquivos** · PRONTO: 1 · PARCIAL: 16 · REPROVADO: 1

| Arquivo | Tipo | Idioma | Âncoras | Palavras | Situação |
|---|---|---|---|---|---|
| 01_livro_ok.md | livro | por | 2 | 22 | **PARCIAL** |
| 02_livro_lista_multilinha.md | livro | por | 1 | 9 | **PARCIAL** |
| 03_livro_bloco_dobrado.md | livro | por | 1 | 7 | **PARCIAL** |
| 04_livro_bloco_literal.md | livro | por | 1 | 7 | **PARCIAL** |
| 05_sem_frontmatter.md | ? | ? | — | 11 | **REPROVADO** |
| 06_titulo_com_aspas.md | livro | por | 1 | 6 | **PARCIAL** |
| 07_fatia_com_parte.md | livro | por | 1 | 4 | **PRONTO** |
| 08_indice_com_partes.md | livro | por | índice | 10 | **PARCIAL** |
| 09_legislacao.md | legislacao | por | n/a | 17 | **PARCIAL** |
| 10_jurisprudencia.md | jurisprudencia | por | n/a | 7 | **PARCIAL** |
| 11_peca_interna.md | peca_interna | por | n/a | 6 | **PARCIAL** |
| 12_verbete.md | verbete | por | n/a | 6 | **PARCIAL** |
| 13_norma_tecnica.md | norma_tecnica | por | n/a | 5 | **PARCIAL** |
| 14_audiovisual.md | audiovisual | por | n/a | 6 | **PARCIAL** |
| 15_correspondencia.md | correspondencia | por | n/a | 3 | **PARCIAL** |
| 16_livro_fatiavel.md | livro | por | 12 | 2,298 | **PARCIAL** |
| 17_livro_fatiavel_area_multilinha.md | livro | por | 12 | 2,298 | **PARCIAL** |
| 18_ato_administrativo.md | ato_administrativo | por | n/a | 7 | **PARCIAL** |

## ✗ Bloqueios (impedem uso em peça)

### 05_sem_frontmatter.md
- SEM frontmatter YAML — a IA não tem metadados para filtrar

## ! Melhorias recomendadas

### 01_livro_ok.md
- resumo curto demais (<15 palavras)

### 02_livro_lista_multilinha.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 03_livro_bloco_dobrado.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 04_livro_bloco_literal.md
- resumo curto demais (<15 palavras)

### 06_titulo_com_aspas.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 08_indice_com_partes.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância
- texto: ruído de caractere (OCR sujo)

### 09_legislacao.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 10_jurisprudencia.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 11_peca_interna.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 12_verbete.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 13_norma_tecnica.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 14_audiovisual.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 15_correspondencia.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 16_livro_fatiavel.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 17_livro_fatiavel_area_multilinha.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

### 18_ato_administrativo.md
- sem 'resumo' — a IA terá de ler o texto todo para julgar relevância

## Próximos passos

1. **Sem âncoras** → reprocessar o PDF-fonte com `injetar_paginas.py` (a página não pode ser inferida do markdown).
2. **Campos ABNT vazios** → preencher no Projeto Claude (Etapa 3 do `CHECKLIST_Refino_OCR.md`). Nunca inventar dado.
3. **Arquivo gigante** → fatiar (Etapa 4): nota-índice + fatias de ~500–1.500 tokens.
4. **Sem resumo** → gerar a camada 1; é o que a IA lê antes de abrir o texto.
5. **`A-conferir`** → conferir 3 páginas contra o PDF e marcar `Conferida`.

> A base acelera; a conferência da citação que vai ao juiz continua sendo do advogado.
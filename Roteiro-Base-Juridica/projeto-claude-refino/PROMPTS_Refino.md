---
titulo: "Prompts de Refino — Projeto Claude"
tipo: Guia operacional
data: 2026-07-07
---

# Prompts prontos — Refino de Markdown OCR

Copie e cole no chat do Projeto. Use **um por vez**, na ordem.

---

## 0 · Diagnóstico (sempre primeiro)

> Anexei `«arquivo.md»`. Faça **apenas o diagnóstico** da Etapa 0 do checklist — não edite nada ainda. Diga-me: (1) há âncoras de página e quantas; (2) o tipo de documento; (3) o estado do OCR, com exemplos concretos dos problemas que encontrou; (4) o tamanho e o fatiamento que sugere; (5) qualquer bloqueio. Se **não houver paginação** e o documento for citável, avise explicitamente que preciso reinjetar as páginas antes de continuar.

---

## 0b · Faltou a paginação (o que fazer)

Se o diagnóstico acusar ausência de âncoras, rode **você mesmo** no terminal, a partir do PDF-fonte:

```bash
pip install pymupdf
python scripts/injetar_paginas.py livro.pdf -o livro_com_paginas.md
# Confira se a âncora bate com a página impressa. Se não bater:
python scripts/injetar_paginas.py livro.pdf -o livro_com_paginas.md --offset 12 --romanas-ate 14
python scripts/verificar_ancoras.py livro_com_paginas.md
```
Depois volte ao Projeto com o novo arquivo e recomece do Prompt 0.

> **Se o PDF for escaneado** (sem camada de texto), rode antes:
> `ocrmypdf -l por --deskew --rotate-pages livro.pdf livro_ocr.pdf`

---

## 1 · Limpeza de OCR

> Aplique a **Etapa 1** do checklist a `«arquivo.md»`. Corrija hifenização quebrada, quebras de parágrafo indevidas, cabeçalhos/rodapés repetidos, ruído de caractere e encoding.
> **Preserve integralmente:** o texto do autor, numeração de artigos/incisos, notas de rodapé, citações e **todas as âncoras `{{p.NN}}`**.
> Marque com `<!-- ?OCR: verificar -->` tudo que for duvidoso — não adivinhe.
> Faça **apenas as 10 primeiras páginas** como amostra e me mostre antes de seguir.

---

## 2 · Estrutura

> Aplique a **Etapa 2**: normalize a hierarquia de títulos conforme a obra, restaure listas (incisos/alíneas mantendo a numeração original), reconstrua tabelas achatadas e preserve as notas de rodapé com sua numeração. Citações longas viram *blockquote*. Não altere o conteúdo, apenas a marcação.

---

## 3 · Metadados

> Aplique a **Etapa 3**: gere o frontmatter conforme `Template_Nota_Indice_ABNT.md`, incluindo os campos de citação ABNT (`autor_sobrenome`, `autor_completo`, `ano_publicacao`, `edicao`, `local_publicacao`, `editora`, `referencia_abnt`) e os de paginação (`paginacao`, `offset_pagina`, `ancora`, `paginas_total`).
> **Extraia apenas do que está no documento.** Campo não localizado = vazio + `confiabilidade: A-conferir`. Liste ao final o que não conseguiu preencher.

---

## 4 · Fatiamento

> Aplique a **Etapa 4**: crie a nota-índice (camada 1) e as fatias (camada 2), conforme os templates.
> Cada fatia: ~500–1.500 tokens, por unidade semântica, com `pagina_inicio`/`pagina_fim` no frontmatter e **todas as âncoras internas preservadas**.
> **Não corte** no meio de citação, ementa, tese ou artigo de lei.
> No sumário da nota-índice, registre o intervalo de páginas de cada fatia.

---

## 5 · Verificação e relatório

> Aplique a **Etapa 5**: liste as âncoras do arquivo original e as do refinado e confirme que **nenhuma foi perdida ou inventada**. Depois entregue o **relatório de refino** no formato do checklist, destacando o que exige conferência humana.

E, no terminal:
```bash
python scripts/verificar_ancoras.py original.md --comparar refinado.md
```

---

## Prompt único (lote pequeno, documento simples)

> Refine `«arquivo.md»` seguindo o `CHECKLIST_Refino_OCR.md` **integralmente** (Etapas 0 a 5).
> Regras absolutas: não reescreva o texto do autor; não invente metadado nem número de página; **preserve todas as âncoras `{{p.NN}}`**; marque dúvidas com `<!-- ?OCR: verificar -->`.
> Se não houver paginação e o documento for citável, **pare** e me avise.
> Entregue: arquivo refinado + nota-índice + fatias + relatório de refino.

---

## Prompt de citação para PEÇA judicial (nota de rodapé completa)

> Preciso citar o trecho sobre «tema» de «obra» **numa petição**. Localize na base e entregue:
> 1. O trecho **literal**, entre aspas (se >3 linhas, formatado como citação longa: recuo, fonte menor, sem aspas).
> 2. A **página exata**, obtida pela âncora `{{p.NN}}` imediatamente anterior ao trecho.
> 3. A **nota de rodapé no sistema numérico**, com a referência completa + página:
>    `MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023. p. 33.`
> 4. A forma **subsequente** (`op. cit.`), caso eu cite a mesma obra de novo.
>
> Se o trecho ficar entre duas páginas, informe as duas. Se a fonte for e-book de leitor, use `local.` e avise que a posição é instável. Se for lei, cite pelo **artigo**; se for acórdão, pelo **julgado**. Se não houver localizador, diga que não é possível citar com segurança.

## Prompt de citação para PARECER (autor-data)

> Preciso citar o trecho sobre «tema» de «obra» **num parecer**. Entregue o trecho literal, a página exata (pela âncora) e a citação no sistema **autor-data**: `(Machado, 2023, p. 33)`. Acrescente a referência completa para a lista final.

## Prompt de conferência de citação (genérico)

> Preciso citar o trecho sobre «tema» de «obra». Localize na base, transcreva o trecho **literalmente**, informe a **página exata** (pela âncora `{{p.NN}}` imediatamente anterior) e monte a citação **nos dois sistemas** (autor-data e nota de rodapé completa), conforme `SISTEMAS_DE_CHAMADA.md`. Se não houver âncora, diga que não é possível citar com segurança.

> [!warning] Sempre confira a página contra o PDF antes de a peça sair.
> O sistema reduz drasticamente o trabalho, mas a responsabilidade pela citação é do advogado.

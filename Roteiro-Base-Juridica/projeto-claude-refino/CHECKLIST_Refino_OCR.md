---
titulo: "Checklist de Refino de Markdown OCR"
tipo: Procedimento
data: 2026-07-07
---

# Checklist de Refino — do OCR bruto à nota do segundo cérebro

Siga **na ordem**. Não pule a Etapa 0.

---

## Etapa 0 — Diagnóstico (antes de editar qualquer coisa)

Reporte ao usuário, em 5 linhas:

1. **Paginação:** o arquivo tem âncoras (`{{p.NN}}` ou `<!-- p.NN -->`)? Quantas?
2. **Tipo:** doutrina · legislação · jurisprudência · peça/modelo · artigo.
3. **Estado do OCR:** limpo · sujo · muito degradado (dê exemplos do que viu).
4. **Extensão:** nº aproximado de páginas/palavras; sugestão de fatiamento.
5. **Bloqueios:** o que impede o refino.

> [!danger] Parada obrigatória
> **Sem âncoras de página + documento citável (doutrina/artigo) = PARE.**
> Avise: a página não pode ser inferida do texto. É preciso reinjetar a paginação a partir do PDF-fonte com `scripts/injetar_paginas.py`. Não prossiga produzindo um arquivo que induzirá a citação incorreta.
> Exceção: legislação (cita-se por artigo) e jurisprudência (cita-se por nº do processo/órgão/data) **não** dependem de página — nesses casos, siga.

---

## Etapa 1 — Limpeza de OCR (corrigir o que a máquina quebrou)

**Corrija:**
- [ ] **Hifenização de fim de linha:** `respon-\nsabilidade` → `responsabilidade`. Cuidado: preserve hífens legítimos (`jurídico-tributário`).
- [ ] **Quebras de parágrafo indevidas:** linhas soltas que pertencem ao mesmo parágrafo. Cuidado: não funda parágrafos distintos.
- [ ] **Cabeçalhos e rodapés repetidos** que o OCR jogou no meio do texto (nome da obra, do capítulo, "Página X de Y"). **Remova o ruído, mas transfira a informação de página para a âncora**, se ela não existir.
- [ ] **Ruído de caractere:** `|`, `~`, `¬`, `l` no lugar de `1`, `O` no lugar de `0`, `rn` no lugar de `m`. Em texto jurídico, atenção redobrada a **números de artigos e datas**.
- [ ] **Encoding:** acentuação portuguesa correta (UTF-8). `Ã§` → `ç`.
- [ ] **Espaçamento:** múltiplos espaços, linhas em branco excessivas.
- [ ] **Marcas d'água e avisos de copyright** repetidos a cada página.

**NÃO toque:**
- Grafia original do autor (inclusive antiga ou incomum).
- Latinismos, termos em língua estrangeira, citações.
- Numeração de artigos, incisos, parágrafos, alíneas.
- Ementas, teses, dispositivos, trechos entre aspas.
- **As âncoras de página.**

Marque o que for duvidoso: `<!-- ?OCR: verificar -->`.

---

## Etapa 2 — Estrutura

- [ ] **Hierarquia de títulos** conforme a obra: `#` (título) → `##` (parte/capítulo) → `###` (seção) → `####` (subseção). Não invente níveis.
- [ ] **Listas** restauradas (incisos e alíneas de lei viram lista, preservando a numeração original).
- [ ] **Tabelas** reconstruídas em markdown quando o OCR as achatou. Se irrecuperável, marque `<!-- ?TABELA: conferir no original, p.NN -->`.
- [ ] **Notas de rodapé preservadas** — em doutrina, são fonte. Use o padrão `[^1]` e a definição ao fim da seção, **mantendo o número original**.
- [ ] **Citações longas** (recuadas no original) → *blockquote* (`>`).

---

## Etapa 3 — Metadados (frontmatter)

Preencha conforme `Template_Nota_Indice_ABNT.md`. Campos de citação:

- [ ] `autor_sobrenome`, `autor_completo`, `ano_publicacao`, `edicao`, `local_publicacao`, `editora`
- [ ] `referencia_abnt` — a referência completa (NBR 6023), autor em CAIXA ALTA
- [ ] `paginacao: true|false` · `offset_pagina` · `ancora`
- [ ] `area`, `tipo`, `natureza`, `orgao`, `status`, `confiabilidade`, `tags`, `resumo`

> **Nunca preencha por suposição.** Campo desconhecido = vazio + `confiabilidade: A-conferir`.

---

## Etapa 4 — Fatiamento (duas camadas)

- [ ] **Nota-índice** (camada 1): ficha, referência ABNT, resumo de 3–8 linhas, sumário com links para as fatias e **o intervalo de páginas de cada uma**.
- [ ] **Fatias** (camada 2): ~500–1.500 tokens, por unidade semântica (capítulo/seção em doutrina; título/artigo em lei; ementa+voto em jurisprudência).
- [ ] Cada fatia tem: cabeçalho autoexplicativo, `pagina_inicio` e `pagina_fim` no frontmatter, e **todas as âncoras internas preservadas**.
- [ ] **Nunca corte** no meio de: citação, ementa, tese, artigo de lei, raciocínio encadeado.

---

## Etapa 5 — Verificação final

- [ ] Rodar `python scripts/verificar_ancoras.py <arquivo.md>` → deve dar **Integridade OK**.
- [ ] Comparar com o original: `python scripts/verificar_ancoras.py antes.md --comparar depois.md` → **nenhuma âncora perdida ou inventada**.
- [ ] Conferir por amostragem: pegue 3 trechos e confirme que a página da âncora bate com o PDF.
- [ ] Produzir o **relatório de refino** (ver abaixo).

---

## Relatório de refino (entregar sempre)

```markdown
## Relatório — <arquivo>

**Diagnóstico inicial:** <tipo, estado do OCR, nº de páginas, âncoras>

**Correções aplicadas:**
- Hifenizações unidas: ~N
- Cabeçalhos/rodapés removidos: ~N
- Títulos normalizados: N
- Tabelas reconstruídas: N
- Notas de rodapé preservadas: N

**Âncoras de página:** N encontradas · N preservadas · 0 inventadas ✓

**PENDENTE DE CONFERÊNCIA HUMANA:**
- [ ] <trecho ilegível na p.NN>
- [ ] <tabela da p.NN não recuperável>
- [ ] <metadado X não localizado no documento>

**Fatias geradas:** N (p.NN–NN cada)
```

> A base acelera o trabalho; a conferência da citação que vai para a peça continua sendo do advogado.

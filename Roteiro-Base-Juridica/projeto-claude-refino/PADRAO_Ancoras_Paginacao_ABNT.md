---
titulo: "Padrão de Âncoras de Paginação e Citação ABNT"
tipo: Norma interna
norma: "ABNT NBR 10520:2023 (citações) · NBR 6023:2018 (referências)"
data: 2026-07-07
---

# Padrão de Âncoras de Paginação e Citação ABNT

## 1. O problema que este padrão resolve

Markdown **não tem páginas** — é texto corrido. PDF **tem**. Quando convertemos PDF → Markdown, a informação de página **se perde**, e sem ela é **impossível** citar conforme a ABNT, que exige a página na citação direta: `(Machado, 2023, p. 45)`.

> [!danger] Consequência prática
> Um trecho de doutrina em markdown **sem âncora de página é inutilizável para citação direta** em peça. A página **não pode ser inferida do texto** — nem por um humano, nem por um LLM. Ou ela foi preservada na conversão, ou precisa ser **reinjetada a partir do PDF-fonte** (script `injetar_paginas.py`).

---

## 2. A âncora: sintaxe oficial do escritório

Marcamos o **início** de cada página com uma âncora em linha própria:

```markdown
{{p.45}}
```

**Regras:**
- A âncora indica que **o texto que vem depois dela começa na página 45** do original.
- Use o número **impresso na página** (o que o leitor vê no rodapé), não o número físico do arquivo PDF — são diferentes quando há capa, folha de rosto e páginas em romano. Se houver divergência, registre o *offset* no frontmatter (campo `offset_pagina`).
- Páginas em algarismo romano (prefácio, apresentação): `{{p.xiv}}`.
- Uma âncora por página, sempre em **linha isolada**, com linha em branco antes e depois.
- **Jamais remova, renumere ou reordene** as âncoras.

**Exemplo de markdown refinado:**
```markdown
{{p.44}}

## 3.2 Prescrição e decadência tributárias

O prazo decadencial para o lançamento observa a regra do art. 173 do CTN, cuja
contagem se inicia no primeiro dia do exercício seguinte àquele em que o
lançamento poderia ter sido efetuado.

{{p.45}}

A jurisprudência do STJ consolidou que, havendo pagamento antecipado, aplica-se
o art. 150, § 4º, do CTN, contando-se o prazo do fato gerador.
```

### Por que `{{p.NN}}` e não outra sintaxe?
- É **invisível ao leitor** no Obsidian renderizado? Não — aparece como texto. É uma escolha deliberada: **visível é melhor**, porque quem lê a fatia enxerga a página e cita corretamente. Se preferir discrição, use o formato comentário HTML `<!-- p.45 -->` (some na renderização, mas continua legível pela IA e pela busca). **Escolha uma e mantenha em todo o acervo.**
- Ambos são **estáveis**: não conflitam com sintaxe markdown, sobrevivem a copiar/colar e são fáceis de buscar por regex (`\{\{p\.[\dxivlcdm]+\}\}`).

> **Decisão padrão do escritório:** usar `{{p.NN}}` (visível). Documentos em que a poluição visual incomode podem usar `<!-- p.NN -->`, desde que o frontmatter registre `ancora: comentario`.

---

## 3. Campos de frontmatter ligados à citação

Toda nota-índice de fonte citável (doutrina, artigo, obra paginada) recebe:

```yaml
# --- Citação ABNT ---
autor_sobrenome: "Machado"           # como aparece na citação: (Machado, 2023, p. 45)
autor_completo: "MACHADO, Hugo de Brito"   # como aparece na referência (caixa alta)
ano_publicacao: 2023
edicao: "44. ed."
local_publicacao: "São Paulo"
editora: "Malheiros"
paginacao: true                      # false para e-book sem página (usar 'local.')
offset_pagina: 0                     # diferença entre página impressa e página do PDF
ancora: "chaves"                     # 'chaves' = {{p.NN}} | 'comentario' = <!-- p.NN -->
referencia_abnt: "MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023."
```

Nas **fatias**, registre o intervalo:
```yaml
pagina_inicio: 44
pagina_fim: 51
```

---

## 4. Regras de citação — NBR 10520:2023 (o que mudou)

A norma foi **atualizada em 19/07/2023**. Pontos que importam para nós:

| Item | Como é agora (2023) | Como era (2002) |
|---|---|---|
| Autoria na citação (dentro dos parênteses) | **Maiúsculas e minúsculas**: `(Machado, 2023, p. 45)` | Caixa alta: `(MACHADO, 2023, p. 45)` |
| Autoria na lista de **referências** | **Continua em caixa alta**: `MACHADO, Hugo de Brito.` | Igual |
| Ponto final | Encerra a **frase**, não a citação: `[...] efetuado” (Machado, 2023, p. 45).` | Havia duplicação |
| 4 ou mais autores | Pode usar `*et al.*` (itálico) | — |
| Expressões latinas (`apud`, `et al.`) | Em **itálico** | — |
| Citação longa (>3 linhas) | Recuo de 4 cm **recomendado** (não mais obrigatório), fonte menor, sem aspas | Recuo obrigatório |
| Documento **sem paginação** (e-book) | Usar `local.` ou `cap.`: `(José, 2009, local. 360)` | — |

**Modelos prontos:**
- Citação direta curta: `"[trecho literal]" (Machado, 2023, p. 45).`
- Citação indireta (paráfrase): `Segundo Machado (2023, p. 45), o prazo decadencial...` — a página é recomendada e o escritório **exige**, para permitir conferência.
- Citação de citação: `(Gough, 1972, p. 59 apud Nardi, 1993, p. 94)` — com `apud` em itálico.
- E-book sem página: `(Dongo-Montoya, 2009, local. 264).`

> **Regra do escritório:** toda citação — direta ou indireta — leva página. É o que permite conferir a fonte antes de a peça sair.

---

## 5. Fluxo quando a paginação está faltando

```
Markdown sem âncoras
        │
        ├── Tem o PDF-fonte?  ── SIM ──► rodar scripts/injetar_paginas.py
        │                                (reconverte marcando as páginas)
        │
        └── NÃO ──► O documento NÃO pode ser usado para citação direta.
                    Marque no frontmatter: paginacao: false
                                           confiabilidade: A-conferir
                    Use apenas como apoio/leitura; para citar, obtenha o PDF.
```

**Nunca** contorne isso estimando páginas. Uma citação com página errada em peça processual é um erro grave — e evitável.

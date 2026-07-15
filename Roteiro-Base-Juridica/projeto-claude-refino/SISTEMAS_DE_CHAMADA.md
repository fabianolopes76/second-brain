---
titulo: "Sistemas de Chamada: Autor-Data e Numérico (nota de rodapé)"
tipo: Norma interna
normas: "ABNT NBR 10520 · NBR 6023:2018"
data: 2026-07-07
---

# Sistemas de Chamada — a base serve aos dois

## O ponto

A ABNT admite **dois sistemas de chamada**, e o escritório usa **ambos**, conforme o documento:

| | **Autor-data** | **Numérico / nota de rodapé** |
|---|---|---|
| Como aparece no texto | `(Machado, 2023, p. 33)` | `...conforme a doutrina.¹` |
| Onde fica a referência | Só na lista final de referências | **Na nota de rodapé, completa** |
| Forma na nota | — | `MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023. p. 33.` |
| Uso típico no escritório | Pareceres, memorandos, textos acadêmicos | **Petições e peças judiciais** |
| Restrição da norma | — | **Não usar** junto com notas explicativas |

> **Consequência para a base:** o YAML **não pode** fixar apenas a citação autor-data. Cada nota precisa carregar os elementos para gerar **as duas formas** — e o localizador (página, posição, artigo) serve às duas.

---

## 1. Sistema autor-data

**No texto:**
- Sobrenome fora dos parênteses: `Segundo Machado (2023, p. 33), a decadência...`
- Tudo entre parênteses: `...prazo decadencial (Machado, 2023, p. 33).`

**Caixa do sobrenome — atenção à versão da norma:**
- **NBR 10520:2023** (vigente): `(Machado, 2023, p. 33)` — maiúsculas e minúsculas
- **NBR 10520:2002** (antiga): `(MACHADO, 2023, p. 33)` — caixa alta
- Fora dos parênteses, em **ambas**: `Machado (2023, p. 33)`

**Casos especiais:**
| Situação | Forma |
|---|---|
| Até 3 autores | `(Torres; Martins; Alves, 2002)` |
| 4 ou mais | `(Taylor *et al.*, 2008)` |
| Sobrenomes iguais, autores diferentes | `(Barbosa, C., 1958)` / `(Barbosa, O., 1980)` |
| Mesmo autor e mesmo ano | `(Santos, 2010a)` / `(Santos, 2010b)` |
| Mesmo autor, datas diferentes | `(Dantas, 1989, 1991, 1995)` — ordem cronológica |
| Vários autores de uma vez | `(Costa, 1984; Klein, 2000; Machado, 1991)` — ordem alfabética |
| Citação de citação | `(Vianna, 1986, p. 172 *apud* Segatto, 1995, p. 214-215)` |

---

## 2. Sistema numérico (nota de rodapé) — o da peça judicial

**No texto:** indicador numérico sobrescrito, na ordem de citação.
> A decadência tributária submete-se à regra do art. 173 do CTN.¹

**Na nota de rodapé:** a **referência completa**, com a **página ao final**:
> ¹ MACHADO, Hugo de Brito. **Curso de direito tributário**. 44. ed. São Paulo: Malheiros, 2023. p. 33.

Note a estrutura: é a **referência da NBR 6023:2018** + `p. NN.` no fim. É por isso que o campo `referencia_abnt` do YAML é o insumo das duas formas — na nota, basta acrescentar o localizador.

**Regra dura:** o sistema numérico **não se usa** quando há notas explicativas. Escolha um sistema e **mantenha-o em todo o documento**.

---

## 3. Citações subsequentes — expressões latinas (só no sistema de notas)

Ao repetir uma obra já citada, evita-se reescrever tudo. Estas expressões só valem **em notas de rodapé**:

| Expressão | Significa | Quando usar |
|---|---|---|
| *Ibidem* (ou *Ibid.*) | na mesma obra | Obra **imediatamente anterior**, página diferente → `² Ibidem, p. 45.` |
| *Idem* (ou *Id.*) | do mesmo autor | Mesmo autor, **obra diferente** → `³ Idem. Comentários ao CTN. São Paulo: Atlas, 2020. p. 12.` |
| *Op. cit.* | na obra citada | Obra já citada, mas **com outras notas de permeio** → `⁷ MACHADO, op. cit., p. 88.` |
| *Loc. cit.* | no lugar citado | **Mesma página** de obra já citada → `⁴ MACHADO, loc. cit.` |
| *Passim* | aqui e ali | Ideia recolhida em **vários trechos** → `⁵ MACHADO, op. cit., passim.` |
| *Et seq.* | e seguintes | Não se transcreveu tudo → `⁶ MACHADO, op. cit., p. 33 et seq.` |
| *Cf.* | confira | Remete o leitor a outra fonte → `⁸ Cf. STJ, REsp 1.234.567/MA.` |
| *Apud* | citado por | Não teve acesso ao original → `⁹ VIANNA, 1986, p. 172 apud SEGATTO, 1995, p. 214.` |

**Regras de uso:**
- Todas em **itálico** (NBR 10520:2023 é expressa quanto às expressões latinas).
- *Ibidem*, *Idem*, *Op. cit.*, *Loc. cit.* **só** podem ser usadas **na mesma página ou folha** da citação a que se referem. Se a obra ficou páginas atrás, **repita a referência**.
- ***Apud*** é a **única** que também pode aparecer no corpo do texto.
- Na **lista de referências**, entra apenas a obra efetivamente lida.

> **Cautela forense:** em peças, o excesso de *op. cit.* prejudica a leitura do julgador e dificulta a conferência. Em documentos curtos, repetir a referência completa costuma servir melhor ao leitor — e ao seu cliente.

---

## 4. Como o YAML sustenta os dois sistemas

O frontmatter guarda os **elementos**; as **formas de citação** são geradas a partir deles.

```yaml
# --- Sistema de chamada ---
sistema_chamada: "numerico"        # numerico (peças) | autor_data (pareceres) | ambos
norma_citacao: "NBR 10520:2023"

# --- Insumos (o esquema por tipo_fonte define os campos) ---
autoria: ["MACHADO, Hugo de Brito"]
autoria_citacao: "Machado"
titulo: "Curso de direito tributário"
edicao: "44. ed."
local_publicacao: "São Paulo"
editora: "Malheiros"
ano: 2023
localizador_tipo: pagina
localizador_abrev: "p."

# --- Saídas (geradas; o validador monta) ---
referencia_abnt: "MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023."
citacao_autor_data: "(Machado, 2023, p. NN)"
citacao_nota_completa: "MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023. p. NN."
citacao_nota_subsequente: "MACHADO, op. cit., p. NN."
```

Rode `python scripts/validar_yaml_abnt.py nota.md --gerar` e o script imprime **as três formas** já preenchidas, bastando trocar `NN` pela página real (que a âncora `{{p.NN}}` indica).

---

## 5. Como o localizador muda a nota completa, por tipo de fonte

| Tipo de fonte | Nota de rodapé completa (exemplo) |
|---|---|
| `livro` | `MACHADO, Hugo de Brito. Curso de direito tributário. 44. ed. São Paulo: Malheiros, 2023. **p. 33.**` |
| `livro_ebook_leitor` | `GODINHO, Thais. Vida organizada. São Paulo: Gente, 2014. E-book. **local. 264.**` |
| `capitulo_livro` | `ROMANO, Giovanni. Imagens da juventude na era moderna. In: LEVI, G.; SCHMIDT, J. (org.). História dos jovens 2. São Paulo: Companhia das Letras, 1996. **p. 12.**` |
| `artigo_periodico` | `MIRANDA, Antônio et al. Autoria coletiva... Ciência da Informação, Brasília, v. 36, n. 2, p. 35-45, maio/ago. 2007. **p. 40.**` |
| `legislacao` | `BRASIL. Lei nº 10.406, de 10 de janeiro de 2002. Institui o Código Civil. Diário Oficial da União: seção 1, Brasília, DF, 11 jan. 2002. **art. 205.**` |
| `jurisprudencia` | `BRASIL. Superior Tribunal de Justiça (Primeira Seção). REsp 1.234.567/MA. Relator: Min. Fulano de Tal, 15 maio 2024. DJe 20 maio 2024.` *(sem localizador — cita-se o julgado)* |

> **Praxe forense:** em peças, é comum citar lei e jurisprudência **no corpo do texto** (`art. 205 do Código Civil`; `REsp 1.234.567/MA, Rel. Min. Fulano`) e reservar a nota de rodapé para a **doutrina**. A base suporta as duas escolhas — o que ela garante é que o **localizador correto** esteja sempre disponível.

---

## 6. Regra do escritório

1. **Peças judiciais** → sistema **numérico** (nota de rodapé com referência completa + página).
2. **Pareceres e consultas** → **autor-data** (mais enxuto) ou numérico, conforme o destinatário.
3. **Nunca misture** os dois no mesmo documento.
4. Registre a escolha em `sistema_chamada`; se a nota servir aos dois usos, marque `ambos` — o validador gera as duas formas.
5. **Confira a página contra o PDF** antes de a peça sair. A base entrega a referência montada; a responsabilidade pela exatidão da citação é do advogado.

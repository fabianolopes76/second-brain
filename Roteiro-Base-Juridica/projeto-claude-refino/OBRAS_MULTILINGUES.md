---
titulo: "Obras Multilíngues — OCR, refino e citação ABNT"
tipo: Norma interna
idiomas: "português · inglês · alemão · francês · italiano · espanhol"
normas: "ABNT NBR 6023:2018 · NBR 10520:2023"
data: 2026-07-07
---

# Obras Multilíngues no Acervo

O acervo tem doutrina em **português, inglês, alemão, francês, italiano e espanhol**. O idioma não é um detalhe de catalogação: ele muda o comportamento do pipeline em **três pontos críticos**.

---

## 1. OCR — a língua errada produz lixo

Um livro alemão OCRizado com `-l por` gera texto ininteligível: o Tesseract "força" o vocabulário português sobre palavras alemãs, corrompendo justamente os termos técnicos que interessam (*Rechtsstaatlichkeit*, *Verfassung*, *Rechtsprechung*).

**Instalar os pacotes de idioma (uma vez):**
```bash
sudo apt install -y tesseract-ocr-por tesseract-ocr-eng tesseract-ocr-deu \
                    tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-spa
tesseract --list-langs      # confira: deu eng fra ita por spa
```
> ⚠️ O pacote `tesseract-ocr-por` **não vem por padrão**. Sem ele, obras em português são OCRizadas em inglês.

**O `aplicar_ocr.sh` detecta o idioma de cada arquivo** (`OCR_LANG=auto`, padrão) e usa o pacote correto:
```bash
bash aplicar_ocr.sh                       # auto: detecta por arquivo
OCR_LANG=deu bash aplicar_ocr.sh          # força alemão no lote inteiro
OCR_LANG=por+eng bash aplicar_ocr.sh      # bilíngue (mais lento — só em obras mistas)
OCR_LANG_FALLBACK=por bash aplicar_ocr.sh # o que usar quando não der para detectar
```

**Como a detecção funciona:** o `detectar_idioma.py` conta palavras funcionais (*stopwords*) do texto extraído. Sem dependências, roda em qualquer Python 3.

**Limite honesto:** um PDF **escaneado não tem texto para analisar** — a detecção não funciona nele. Nesses casos entra o `OCR_LANG_FALLBACK` (padrão `por+eng`). Se o lote for de obras alemãs escaneadas, **defina o idioma manualmente**:
```bash
OCR_LANG=deu MODE=manter ROOT="/mnt/c/.../doutrina-alema" bash aplicar_ocr.sh
```
> **Dica de organização:** separe os escaneados por idioma em subpastas e rode um lote por pasta. É mais rápido e mais seguro do que confiar no fallback.

**Par ambíguo:** português × espanhol é o caso mais delicado. O detector sinaliza `⚠ ambíguo` quando a margem entre 1º e 2º lugar é pequena — confira esses manualmente.

---

## 2. Refino no Claude — não "corrigir" o que não é erro

O risco: a IA lê *Rechtsstaatlichkeit* ou *l'administration* e "conserta" para algo que parece português. Isso **destrói a fonte**.

**Regra do Projeto (já nas instruções):**
- O campo `idioma` do YAML diz em que língua a obra está.
- A IA **preserva integralmente** o texto na língua original — grafia, acentuação, palavras compostas alemãs, apóstrofos franceses, ligaduras (*œ*), *ß*.
- Ela só corrige o que o **OCR** quebrou (hifenização de fim de linha, ruído de caractere), **nunca** o que o autor escreveu.
- Em dúvida: preserva e marca `<!-- ?OCR: verificar -->`.

**Cuidados por idioma**
| Idioma | Armadilhas de OCR | Não confundir com erro |
|---|---|---|
| **Alemão** | `ß` ↔ `B`/`ss`; tremas `ä ö ü`; palavras compostas longas | Substantivos em maiúscula (é regra), compostos gigantes |
| **Francês** | apóstrofos (`l'État`), acentos `é è ê`, ligadura `œ` | Elisões (`l'`, `d'`), cedilha |
| **Italiano** | acentos `à è ì ò ù`, apóstrofos | `e` × `è` (mudam o sentido!) |
| **Espanhol** | `ñ`, `¿ ¡` iniciais | Falsos amigos com o português |
| **Inglês** | aspas curvas, hifenização | Grafia britânica × americana |
| **Português** | `ç`, til, acentos | **Grafia pré-Acordo** em obras antigas — **preserve** |

---

## 3. Citação ABNT — a língua do documento manda

A **NBR 6023:2018** é explícita: certos elementos seguem a **língua do documento referenciado**, não a do trabalho.

### 3.1 Edição — na língua do documento
| Idioma | Forma |
|---|---|
| Português | `5. ed.` |
| Inglês | `5th ed.` |
| Alemão | `5. Aufl.` |
| Francês | `5e éd.` |
| Italiano | `5. ed.` |
| Espanhol | `5. ed.` |

Exemplo da própria norma:
> `SCHAUM, Daniel. Schaum's outline of theory and problems. 5th ed. New York: Schaum Publishing, 1956.`

Acréscimos abreviados também seguem o documento: `3. ed. rev., aum. e atual.` (português) · `2nd rev. ed.` (inglês).

### 3.2 Mês (artigos de periódico) — abreviado conforme o idioma
| PT | EN | DE | FR | IT | ES |
|---|---|---|---|---|---|
| jan. fev. mar. abr. **maio** jun. jul. ago. set. out. nov. dez. | Jan. Feb. Mar. Apr. May June July Aug. Sept. Oct. Nov. Dec. | Jan. Feb. März Apr. Mai Juni Juli Aug. Sept. Okt. Nov. Dez. | janv. févr. mars avr. mai juin juill. août sept. oct. nov. déc. | gen. feb. mar. apr. magg. giugno luglio ago. sett. ott. nov. dic. | ene. feb. mar. abr. mayo jun. jul. ago. sept. oct. nov. dic. |

> Em português, **maio** é o único mês que não se abrevia.

### 3.3 O que **não** muda com o idioma
- **Autoria:** sobrenome em CAIXA ALTA na referência, sempre.
- **Elementos ausentes** (latim, universais): `[S.l.]` (sem local) · `[s.n.]` (sem editora).
- **Expressões latinas:** *In*, *apud*, *et al.*, *op. cit.*, *Ibidem* — em itálico, em qualquer idioma.
- **Datas aproximadas:** `[1969?]`, `[ca. 1960]`, `[197-]`.
- **Informações acrescentadas por você** seguem a língua **do seu trabalho** (português), não a do documento — a NBR 6023:2018 mudou isso em relação à versão de 2002.

### 3.4 Local de publicação
Use o nome **como consta no documento** (`New York`, `München`, `Paris`, `Milano`), não a versão aportuguesada.

### 3.5 Citação direta em língua estrangeira
Duas opções (escolha uma e **mantenha em todo o documento**):
1. **Citar no original** e, se necessário, traduzir em nota de rodapé.
2. **Traduzir no corpo** e indicar `tradução nossa`:
   > "o direito é uma ordem coercitiva da conduta humana" (Kelsen, 1960, p. 34, tradução nossa).

Em peças judiciais, o costume é **traduzir no corpo** (o juiz não é obrigado a ler alemão) e trazer o original em nota. Registre a escolha em `traducao: propria | original | ambos`.

---

## 4. Campos de YAML para obras estrangeiras

```yaml
# --- Idioma ---
idioma: deu                    # por | eng | deu | fra | ita | spa
idioma_nome: "alemão"
traducao: original             # original | propria | ambos
titulo_traduzido: ""           # se você traduzir o título para referência interna

# --- Elementos na língua do documento (NBR 6023:2018) ---
edicao: "5. Aufl."             # NÃO "5. ed." — segue a língua do documento
local_publicacao: "Wien"       # como consta no documento
mes: ""                        # abreviado conforme o idioma (ver tabela)
```

**Exemplo completo — obra alemã:**
```yaml
titulo: "Reine Rechtslehre"
tipo_fonte: livro
idioma: deu
idioma_nome: "alemão"
traducao: original
autoria: ["KELSEN, Hans"]
autoria_citacao: "Kelsen"
ano: 1960
edicao: "2. Aufl."
local_publicacao: "Wien"
editora: "Franz Deuticke"
localizador_tipo: pagina
localizador_abrev: "p."
sistema_chamada: ambos
referencia_abnt: "KELSEN, Hans. Reine Rechtslehre. 2. Aufl. Wien: Franz Deuticke, 1960."
citacao_nota_completa: "KELSEN, Hans. Reine Rechtslehre. 2. Aufl. Wien: Franz Deuticke, 1960. p. 34."
citacao_autor_data: "(Kelsen, 1960, p. 34)"
```

> Note: a **abreviatura de página** (`p.`) permanece em português — é elemento do **seu** trabalho, não do documento. O que segue a língua do documento é a **edição** (`2. Aufl.`).

---

## 5. Checklist multilíngue

- [ ] Pacotes de idioma do Tesseract instalados (**incluindo `por`**).
- [ ] `detectar_idioma.py` rodado sobre a pasta; ambíguos conferidos.
- [ ] Escaneados: idioma **definido manualmente** (a detecção não funciona sem texto).
- [ ] Campo `idioma` preenchido no YAML de cada nota.
- [ ] `edicao` na língua do documento (`5th ed.`, `5. Aufl.`, `5e éd.`).
- [ ] `mes` (se artigo) abreviado conforme o idioma.
- [ ] Política de tradução definida e uniforme (`traducao:`).
- [ ] Amostra do texto refinado conferida por alguém que **lê a língua** — a IA não deve ser a única checagem de fidelidade em obra estrangeira.

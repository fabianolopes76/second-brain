# Vault inicial — onde colocar cada arquivo

Estes arquivos já vêm na estrutura do seu vault do Obsidian (`4-OBSIDIAN-VAULT/`). Copie as pastas para dentro do vault, mantendo a hierarquia:

```
4-OBSIDIAN-VAULT/
├── 00-Indices-MOCs/
│   └── fontes.md                     ← lista-mestra do radar (Módulo E)
│       └── Radar/                    ← (o radar cria os arquivos de novidades aqui)
└── 99-Templates/
    ├── Template_Nota_Indice.md       ← camada 1 (ficha + resumo + links)
    └── Template_Fatia.md             ← camada 2 (trecho do texto integral)
```

## Como usar os templates
1. **Ative os templates no Obsidian:** *Configurações → Templates* (nativo) e defina a pasta de templates como `99-Templates`. Para recursos avançados (datas automáticas, título do arquivo), instale o plugin **Templater**.
2. **Nova obra:** crie a **nota-índice** a partir de `Template_Nota_Indice.md`, preencha os campos entre «guillemets» e renomeie no padrão `[AREA]_[TIPO]_[ANO]_[Titulo]_[Autor]_INDICE.md`.
3. **Trechos:** para cada capítulo/título/ementa, crie uma **fatia** a partir de `Template_Fatia.md` e ligue-a à nota-índice.
4. **Dica:** o **gerador de frontmatter do painel** (`painel-acervo.html`) produz o bloco YAML pronto para colar no topo da nota-índice.

## Sobre o `fontes.md`
Já vem pré-preenchido com as fontes da nossa região (TJMA, TRT16, TRE-MA, TRF1) e os demais tribunais pedidos (TJSP, TJDFT, TJSC, TJMG, TJCE; TRF2–TRF6), além do **DJEN** (publicação unificada), legislação e tribunais superiores. É o arquivo que as rotinas do **Módulo E** percorrem. Revise-o a cada trimestre.

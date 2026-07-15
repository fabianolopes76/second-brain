---
titulo: "MOC — Direito Tributário"
tipo: MOC
area: [Tributário]
finalidade: "Porta de entrada navegável do acervo tributário, com painéis automáticos (Dataview)"
data: 2026-07-07
---

# 🏛️ MOC — Direito Tributário

> [!info] Pré-requisito
> Os painéis abaixo usam o plugin **Dataview** (comunidade, gratuito). Instale em *Configurações → Plugins da comunidade → Dataview* e ative. Sem ele, os blocos aparecem como código.
>
> **Convenções que os painéis assumem:** notas-índice têm `area` no frontmatter e **não** têm o campo `parte` (esse campo só existe nas fatias). Por isso todos os painéis filtram `!parte`, para listar obras/documentos e não pedaços.

Mapa de entrada do acervo tributário. Os painéis se atualizam sozinhos conforme você cataloga; a seção manual, no fim, guarda a curadoria dos institutos.

---

## ✅ Vigente (pronto para uso)
Tudo que está `Vigente` na área, por tipo.

```dataview
TABLE WITHOUT ID file.link AS "Documento", tipo AS "Tipo", autoria_citacao AS "Autor/Órgão", ano AS "Ano"
FROM -"99-Templates"
WHERE contains(area, "Tributário") AND status = "Vigente" AND !parte
SORT tipo ASC, ano DESC
```

## ⚠️ Pendências de conferência
Itens que **não** entram em peça sem revisão humana (`status` ou `confiabilidade` = `A-conferir`).

```dataview
TABLE WITHOUT ID file.link AS "Documento", status AS "Status", confiabilidade AS "Confiab.", ano AS "Ano"
FROM -"99-Templates"
WHERE contains(area, "Tributário") AND (status = "A-conferir" OR confiabilidade = "A-conferir") AND !parte
SORT file.mtime DESC
```

## 🚫 Superado / Revogado / Alterado (não citar sem cautela)
Sinalizados para evitar citação de norma/entendimento vencido.

```dataview
TABLE WITHOUT ID file.link AS "Documento", status AS "Situação", ano AS "Ano"
FROM -"99-Templates"
WHERE contains(area, "Tributário") AND (status = "Revogado" OR status = "Superado" OR status = "Alterado" OR status = "Modulado") AND !parte
SORT status ASC
```

## 📚 Doutrina
```dataview
TABLE WITHOUT ID file.link AS "Obra", autoria_citacao AS "Autor", ano AS "Ano", editora AS "Editora"
FROM -"99-Templates"
WHERE contains(area, "Tributário") AND tipo = "Doutrina" AND !parte
SORT autoria_citacao ASC
```

## ⚖️ Jurisprudência (mais recente primeiro)
```dataview
TABLE WITHOUT ID file.link AS "Julgado", orgao AS "Órgão", ano AS "Ano", status AS "Status"
FROM -"99-Templates"
WHERE contains(area, "Tributário") AND tipo = "Jurisprudência" AND !parte
SORT ano DESC
```

## 📜 Legislação (por vigência)
```dataview
TABLE WITHOUT ID file.link AS "Norma", status AS "Vigência", ano AS "Ano"
FROM -"99-Templates"
WHERE contains(area, "Tributário") AND tipo = "Legislação" AND !parte
SORT status ASC, ano DESC
```

## 🆕 Novidades recentes (últimos 30 dias)
Catalogadas ou atualizadas no último mês (útil após rodar o radar do Módulo E).

```dataview
TABLE WITHOUT ID file.link AS "Documento", tipo AS "Tipo", file.mtime AS "Atualizado"
FROM -"99-Templates"
WHERE contains(area, "Tributário") AND !parte AND file.mtime >= date(today) - dur(30 days)
SORT file.mtime DESC
```

## 📊 Saúde do acervo tributário
```dataview
TABLE WITHOUT ID key AS "Status", length(rows) AS "Qtd"
FROM -"99-Templates"
WHERE contains(area, "Tributário") AND !parte
GROUP BY status
```

---

## 🗺️ Mapa de institutos (curadoria manual)
Ligue aqui as notas-âncora dos temas mais usados. Substitua os exemplos pelos seus `[[wikilinks]]`.

- **Obrigação e crédito tributário** — [[«nota-obrigacao-tributaria»]] · [[«nota-lancamento»]]
- **Prescrição e decadência** — [[«nota-prescricao-tributaria»]] · [[«nota-decadencia»]]
- **Processo administrativo fiscal** — [[«nota-PAF»]]
- **Execução fiscal / LEF** — [[«nota-execucao-fiscal»]]
- **Espécies tributárias** — [[«nota-impostos»]] · [[«nota-taxas»]] · [[«nota-contribuicoes»]]
- **Repetição de indébito** — [[«nota-repeticao-indebito»]]

## 🔗 Relacionados
- [[MOC-Processo-Civil]] (execução fiscal, embargos, tutela)
- [[fontes]] (radar de legislação e jurisprudência)

> [!note] Manutenção
> Revise o mapa de institutos ao consolidar novas obras. Os painéis não precisam de manutenção — refletem o frontmatter automaticamente.

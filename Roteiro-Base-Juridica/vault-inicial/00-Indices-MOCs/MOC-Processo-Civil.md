---
titulo: "MOC — Direito Processual Civil"
tipo: MOC
area: [Processual]
finalidade: "Porta de entrada navegável do acervo de processo civil, com painéis automáticos (Dataview)"
data: 2026-07-07
---

# ⚙️ MOC — Direito Processual Civil

> [!info] Pré-requisito
> Painéis via plugin **Dataview** (gratuito). Instale e ative em *Configurações → Plugins da comunidade*.
>
> **Convenção de área para processo:** na taxonomia, `Processual` é a área ampla (abrange civil, penal, trabalhista…). Para isolar **processo civil**, os painéis filtram `contains(area, "Processual")` **e** exigem a tag `processo-civil` **ou** a área `Civil` junto. Ao catalogar uma obra de CPC, use por exemplo `area: [Processual, Civil]` **e** `tags: [processo-civil, ...]`. Assim o processo penal/trabalhista não polui este MOC.

---

## ✅ Vigente (pronto para uso)
```dataview
TABLE WITHOUT ID file.link AS "Documento", tipo AS "Tipo", autor AS "Autor/Órgão", ano AS "Ano"
FROM -"99-Templates"
WHERE contains(area, "Processual") AND (contains(tags, "processo-civil") OR contains(area, "Civil"))
  AND status = "Vigente" AND !parte
SORT tipo ASC, ano DESC
```

## ⚠️ Pendências de conferência
```dataview
TABLE WITHOUT ID file.link AS "Documento", status AS "Status", confiabilidade AS "Confiab.", ano AS "Ano"
FROM -"99-Templates"
WHERE contains(area, "Processual") AND (contains(tags, "processo-civil") OR contains(area, "Civil"))
  AND (status = "A-conferir" OR confiabilidade = "A-conferir") AND !parte
SORT file.mtime DESC
```

## 🚫 Superado / Revogado / Alterado
Especialmente relevante em processo civil (teses de repetitivos e súmulas mudam com frequência).
```dataview
TABLE WITHOUT ID file.link AS "Documento", status AS "Situação", orgao AS "Órgão", ano AS "Ano"
FROM -"99-Templates"
WHERE contains(area, "Processual") AND (contains(tags, "processo-civil") OR contains(area, "Civil"))
  AND (status = "Revogado" OR status = "Superado" OR status = "Alterado" OR status = "Modulado") AND !parte
SORT status ASC
```

## 📚 Doutrina
```dataview
TABLE WITHOUT ID file.link AS "Obra", autor AS "Autor", ano AS "Ano", fonte AS "Fonte"
FROM -"99-Templates"
WHERE contains(area, "Processual") AND (contains(tags, "processo-civil") OR contains(area, "Civil"))
  AND tipo = "Doutrina" AND !parte
SORT autor ASC
```

## ⚖️ Jurisprudência e precedentes qualificados
Acórdãos, súmulas e teses (repetitivos/repercussão geral) de processo civil.
```dataview
TABLE WITHOUT ID file.link AS "Julgado/Tese", orgao AS "Órgão", ano AS "Ano", status AS "Status"
FROM -"99-Templates"
WHERE contains(area, "Processual") AND (contains(tags, "processo-civil") OR contains(area, "Civil"))
  AND (tipo = "Jurisprudência" OR tipo = "Súmula") AND !parte
SORT ano DESC
```

## 📜 Legislação processual (CPC e correlatas)
```dataview
TABLE WITHOUT ID file.link AS "Norma", status AS "Vigência", ano AS "Ano"
FROM -"99-Templates"
WHERE contains(area, "Processual") AND tipo = "Legislação" AND !parte
SORT status ASC, ano DESC
```

## 🆕 Novidades recentes (últimos 30 dias)
```dataview
TABLE WITHOUT ID file.link AS "Documento", tipo AS "Tipo", file.mtime AS "Atualizado"
FROM -"99-Templates"
WHERE contains(area, "Processual") AND (contains(tags, "processo-civil") OR contains(area, "Civil"))
  AND !parte AND file.mtime >= date(today) - dur(30 days)
SORT file.mtime DESC
```

## 📊 Saúde do acervo processual civil
```dataview
TABLE WITHOUT ID key AS "Status", length(rows) AS "Qtd"
FROM -"99-Templates"
WHERE contains(area, "Processual") AND (contains(tags, "processo-civil") OR contains(area, "Civil")) AND !parte
GROUP BY status
```

---

## 🗺️ Mapa de institutos (curadoria manual)
- **Petição inicial e resposta** — [[«nota-peticao-inicial»]] · [[«nota-contestacao»]]
- **Tutela provisória** (urgência/evidência) — [[«nota-tutela-provisoria»]]
- **Teoria dos recursos** — [[«nota-recursos»]] · [[«nota-apelacao»]] · [[«nota-agravo»]]
- **Precedentes (arts. 926–928 CPC)** — [[«nota-precedentes»]] · [[«nota-IRDR»]]
- **Cumprimento de sentença e execução** — [[«nota-cumprimento-sentenca»]] · [[«nota-execucao»]]
- **Coisa julgada e ação rescisória** — [[«nota-coisa-julgada»]] · [[«nota-rescisoria»]]

## 🔗 Relacionados
- [[MOC-Tributario]] (execução fiscal, embargos à execução)
- [[fontes]] (radar de legislação e jurisprudência)

> [!note] Manutenção
> Como a área `Processual` é ampla, mantenha a disciplina das tags (`processo-civil`) na catalogação — é o que garante que este MOC não misture processo penal/trabalhista. Os painéis se atualizam sozinhos.

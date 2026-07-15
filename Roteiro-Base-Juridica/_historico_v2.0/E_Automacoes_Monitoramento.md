---
titulo: "Módulo E — Automações e Monitoramento"
parte_de: "Pacote Base de Conhecimento Jurídica v2.0"
tipo: Guia operacional
data: 2026-07-07
---

# Módulo E — Automações: notícias, legislação e jurisprudência

Uma base jurídica desatualizada é **passivo, não ativo**. Este módulo mantém o "segundo cérebro" vivo, com rotinas que buscam notícias relevantes e detectam alterações legislativas e jurisprudenciais que impactam o acervo.

## Antes de tudo: a realidade da "automação" hoje
O Claude Cowork **executa tarefas complexas**, inclusive recorrentes, mas com uma limitação prática: o **app precisa ficar aberto** para a tarefa rodar; se fechar, a sessão encerra. Portanto existem **dois níveis** de automação, e o roteiro usa os dois:

- **Nível 1 — Semiautomático (Cowork).** Você dispara uma tarefa recorrente (ex.: "todo dia às 8h faça o *briefing*") **com o app aberto** numa máquina ligada. Ótimo para escritórios com uma estação sempre ativa. Simples de montar, sem código.
- **Nível 2 — Totalmente automático (API + agendador do sistema).** Para rodar sem depender do app aberto, um script chama a **API do Claude e/ou do Gemini** e é disparado pelo **agendador do sistema operacional** (cron no Linux/macOS, Task Scheduler no Windows). Exige o time técnico (Claude Code ajuda a montar), mas roda sozinho.

> **Escolha prática:** comece no **Nível 1** (rápido, sem código) para validar o que é útil. Migre para o **Nível 2** as rotinas que provarem valor e precisam de confiabilidade diária.

---

## Fontes a monitorar (defina as suas)
Liste num arquivo `fontes.md` do vault as fontes oficiais e por área. Exemplos típicos:
- **Legislação federal:** Diário Oficial da União (DOU); Portal da Câmara e do Senado (tramitação); Planalto (legislação consolidada).
- **Jurisprudência:** informativos e repositórios de STF, STJ, TST, TSE; diários eletrônicos (DJe) dos tribunais de interesse (TJ, TRF, TRT, TRE da sua região).
- **Administrativo/extrajudicial:** atos das agências reguladoras e órgãos relevantes ao escritório.
- **Notícias jurídicas:** veículos especializados que o escritório já acompanha.
- **Temas repetitivos/vinculantes:** listas de temas com repercussão geral e recursos repetitivos afetados.

> **Cuidado com fontes.** Priorize **fontes oficiais**. Notícia serve de alerta; a confirmação vem do texto oficial. Nunca registre uma alteração como "vigente/superado" com base só em notícia.

---

## Nível 1 — Rotinas no Cowork (com Claude in Chrome)

Ative **Claude in Chrome** como conector para o Cowork navegar nas fontes. Modelos: **Gemini 3.x** (grounding com Google Search) e **Claude** (web search) — rode em paralelo e cruze (Módulo C).

### Rotina 1 — Briefing diário de notícias por área
**Prompt (tarefa recorrente):**
> Todos os dias úteis, pesquise notícias das últimas 24h sobre os temas listados em `fontes.md`, filtrando pelas áreas do escritório (Tributário, Trabalhista, ...). Para cada item relevante, registre em `00-Indices-MOCs/Radar/AAAA-MM-DD_briefing.md`: título, fonte, data, link, área e um resumo de 2 linhas. Marque com ⚠️ o que sugira **mudança de norma ou de entendimento**. Ignore conteúdo meramente promocional. Ao final, liste os ⚠️ separadamente.

### Rotina 2 — Sentinela de alteração legislativa
**Prompt (tarefa recorrente, ex.: semanal):**
> Para cada diploma legal citado nas notas com `tipo: Legislação` do vault, verifique nas fontes oficiais de `fontes.md` se houve alteração, revogação ou nova regulamentação desde a última checagem (guarde a data em `radar_estado.json`). Para cada mudança encontrada, crie `Radar/legislacao/AAAA-MM-DD_<lei>.md` com: o que mudou, dispositivo afetado, link oficial, e a **lista de notas do vault que citam essa lei** (para revisão). Atualize o `status` sugerido dessas notas para `A-conferir` — **não** altere o texto das notas; só sinalize.

### Rotina 3 — Sentinela de jurisprudência
**Prompt (tarefa recorrente):**
> Monitore os informativos/repositórios de STF, STJ e dos tribunais em `fontes.md` para novas súmulas, teses de repetitivos/repercussão geral e mudanças de entendimento nos temas com tag em `00-Indices-MOCs/`. Para cada novidade, crie `Radar/jurisprudencia/AAAA-MM-DD_<tema>.md` com ementa resumida (paráfrase, sem copiar o inteiro teor), órgão, data, link e as notas do vault afetadas. Sinalize as afetadas como `A-conferir`.

> Em todos os casos, o agente **sinaliza**; a **decisão** de reclassificar norma/entendimento é do advogado. E lembre a regra de direitos autorais: **parafrasear**, não colar inteiros teores/artigos extensos.

---

## Nível 2 — Automação total (API + agendador)

Quando quiser que rode sozinho, sem app aberto. O time técnico monta com ajuda do **Claude Code**.

**Arquitetura simples:**
1. `radar.py` — lê `fontes.md`, busca as fontes (via API dos LLMs com busca/grounding e/ou coleta direta), gera os arquivos de `Radar/` no vault, atualiza `radar_estado.json`.
2. **Agendador do SO** dispara o script:
   - **Linux/macOS (cron)** — editar com `crontab -e`, ex.: todo dia útil às 7h30:
     ```
     30 7 * * 1-5  /usr/bin/python3 /caminho/Acervo-Juridico/_scripts/radar.py >> /caminho/radar.log 2>&1
     ```
   - **Windows (Task Scheduler)** — criar tarefa que roda `python C:\Acervo-Juridico\_scripts\radar.py` na frequência desejada (interface gráfica "Agendador de Tarefas" ou `schtasks`).
3. **Notificação** — o script pode, ao final, montar um resumo dos ⚠️ e enviar por e-mail/mensageria interna (com aprovação humana antes de qualquer envio externo).

**Prompt (no Claude Code) para gerar o esqueleto:**
> Crie `radar.py`: lê `fontes.md` e `radar_estado.json`; para cada área/fonte, consulta a API do Gemini (com Google Search grounding) e a API do Claude (com web search) sobre novidades desde a última data; consolida, deduplica e grava os arquivos em `Radar/` no formato do Módulo E; atualiza o estado; e imprime um resumo dos itens marcados ⚠️. Deixe as chaves de API em variáveis de ambiente, caminhos configuráveis no topo, e trate erros de rede sem quebrar o lote. Gere também a linha de `cron` e o comando `schtasks` equivalentes.

---

## Como o radar volta para a base
1. Os arquivos em `Radar/` são a **fila de revisão**. Uma vez por semana, o advogado responsável revisa os ⚠️.
2. Confirmada uma mudança, atualiza-se o `status` da(s) nota(s) afetada(s) (ex.: `Vigente` → `Revogado`, ou `Vigente` → `Superado`), com um aviso no topo da nota (ex.: `> ⚠️ SUPERADO pelo Tema X do STJ (AAAA-MM-DD)`). Isso evita que a IA cite entendimento vencido.
3. Se houver **nova** legislação/decisão relevante, ela entra no pipeline normal (Módulos B–D) como um novo documento.
4. Registre a data da revisão para o próximo ciclo do radar.

---

## Governança do monitoramento (checklist)
- [ ] `fontes.md` definido e revisado por área.
- [ ] Frequência definida (diária para notícias; semanal para leis/jurisprudência costuma bastar).
- [ ] Máquina/estratégia decidida (Nível 1 com estação sempre ligada, ou Nível 2 com agendador).
- [ ] Regra de sigilo observada: o monitoramento trata **fontes públicas** — não misture com dados de clientes.
- [ ] Direitos autorais: o radar **parafraseia**; não reproduz inteiros teores/artigos extensos.
- [ ] Ritual semanal de revisão humana dos ⚠️ agendado no calendário do responsável.
- [ ] Auditoria trimestral de vigência de todo o acervo `tipo: Legislação` e `tipo: Súmula` (Seção 9 do roteiro-base).

> **Fechando o ciclo:** com o pipeline (Módulos B–D) construindo a base e o radar (Módulo E) mantendo-a atual, o "segundo cérebro" deixa de ser um acervo estático e passa a ser um sistema vivo — que serve melhor ao Claude, ao Gemini e, principalmente, ao trabalho do escritório.

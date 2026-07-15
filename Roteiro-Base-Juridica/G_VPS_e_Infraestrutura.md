---
titulo: "Módulo G — VPS e Infraestrutura"
parte_de: "Pacote Base de Conhecimento Jurídica v2.1"
tipo: Guia de decisão
data: 2026-07-07
---

# Módulo G — O que colocar num VPS (e o que não colocar)

Um **VPS** (servidor virtual privado, "na nuvem") pode acelerar e automatizar boa parte do pipeline — mas **não tudo**. A regra de ouro: **use o VPS para o que é headless (sem tela) e contínuo; deixe no seu computador o que é interativo e visual.** Abaixo, o que roda bem, o que esbarra em limitações e por quê, sempre com foco em custo-benefício.

## Panorama de preços (referência jul/2026 — confirme antes de contratar)
- **VPS CPU barato:** Hetzner ~€5–8/mês (2 vCPU / 4 GB, tráfego generoso, só Linux, ótimo custo/desempenho, foco Europa/GDPR); DigitalOcean/Vultr ~US$ 4–24/mês (mais caros, porém com mais data centers e serviços gerenciados; DO tem documentação excelente).
- **VPS mais robusto:** ~US$ 24–48/mês para 4 vCPU / 8 GB, quando o volume apertar.
- **GPU sob demanda (por hora):** de ~US$ 0,76/GPU-hora (GPUs menores) a ~US$ 2–3,4/GPU-hora (H100). Cobrado por hora — a chave do custo-benefício é **ligar só durante o lote e desligar**.

> **Provedor barato ≠ melhor sempre.** Hetzner lidera preço/desempenho, mas é **só Linux** (não oferece VPS Windows) e sem SLA formal. DigitalOcean custa mais, porém facilita quem está começando e oferece serviços gerenciados. Escolha pela sua realidade de equipe.

---

## Tabela: cada tarefa no VPS

| Tarefa | Roda bem em VPS? | Observação de custo-benefício |
|---|---|---|
| **OCR (OCRmyPDF/Tesseract)** | ✅ Sim (CPU) | Perfeito para lote headless. VPS CPU barato resolve; processe a pilha e desligue. |
| **Conversão Calibre (ePUB/MOBI → MD)** | ✅ Sim (CLI `ebook-convert`) | Leve; roda em qualquer VPS pequeno. |
| **Conversão Docling** | ✅ Sim (CPU aceitável) | Bom em CPU; licença MIT confortável. Melhor opção "só CPU". |
| **Conversão Marker** | ⚠️ Melhor com GPU | Em CPU funciona, mas lento. Use **GPU por hora** só para o backlog e destrua a instância. |
| **Automação/monitoramento via API (Módulo E, Nível 2)** | ✅ Sim — **caso de uso ideal** | Script + `cron` num VPS de €5/mês roda 24/7 sem depender do seu PC. É o melhor motivo para ter um VPS. |
| **Hospedar/sincronizar o vault** | ✅ Sim | Git remoto, Syncthing ou Obsidian LiveSync (CouchDB) num VPS pequeno dão sync de equipe sem pagar Obsidian Sync. |
| **Publicar o vault como site (leitura)** | ✅ Sim | Quartz/Digital Garden num VPS — ou hospedagem estática grátis. Grande ganho de UX (ver Módulo H). |
| **Claude Cowork / Claude Desktop** | ⛔ Problemático | **App gráfico** que precisa ficar **aberto**; não existe versão headless. Ver limitação abaixo. |

---

## As limitações (e por que existem)

### 1. Claude Cowork/Desktop não foi feito para VPS headless
O Cowork é um **aplicativo de desktop com interface gráfica** (Windows/macOS) e **exige o app aberto** durante a execução; fechar encerra a sessão. Um VPS típico é **headless** (sem tela). Para rodar o Cowork num servidor você precisaria de:
- um **VPS Windows** com sessão de área de trabalho remota (RDP) sempre ativa — mais caro, e Hetzner (o mais barato) **não** oferece Windows; ou
- um **VPS Linux com ambiente gráfico** + acesso remoto (VNC/RDP) e o Claude Desktop rodando nesse desktop virtual.

Isso é **tecnicamente possível, mas caro e frágil** — some-se a isso que o Cowork está em *research preview* (sem auditoria robusta) e a questão de **sigilo** de dados de clientes. **Custo-benefício ruim.**

**Alternativa recomendada:** não rode o Cowork no VPS. Deixe o Cowork/Chat no computador da equipe para o trabalho **interativo** (triagem assistida, curadoria, redação) e mova para o VPS apenas a parte **automatizável por API** (Módulo E, Nível 2) e o **processamento em lote** (OCR/conversão). É a divisão que dá o melhor retorno.

### 2. Marker quer GPU; VPS GPU é caro se ficar ligado
Marker roda em CPU, mas devagar. Uma GPU acelera muito — porém GPU 24/7 é cara. **Por que a limitação:** GPUs são recurso escasso e precificado por hora.

**Alternativa custo-eficiente:** use **GPU sob demanda por hora** só enquanto processa o backlog inicial e **destrua a instância** ao terminar (a cobrança é por hora). Para o fluxo contínuo (poucos arquivos novos por semana), **Docling em CPU** costuma bastar, evitando GPU.

### 3. Sigilo e responsabilidade de segurança
Um VPS próprio dá **mais controle** sobre os dados que um SaaS — bom para um escritório. **Mas** a segurança passa a ser sua: atualizações, firewall, backups, controle de acesso. **Por que importa:** dados de clientes exigem cuidado redobrado; um servidor mal configurado é um risco.

**Alternativas/mitigações:** mantenha no VPS preferencialmente **material público** (acervo doutrinário, legislação, jurisprudência, radar de notícias). Para sigiloso, prefira processamento **local** ou um VPS com disco criptografado, acesso por chave SSH (sem senha), firewall fechado e backups automáticos. Considere região de dados adequada (ex.: provedores com data center que atenda suas exigências).

---

## Arquiteturas recomendadas (por orçamento)

### 🟢 Enxuta (~€5–8/mês) — a que a maioria dos escritórios deve começar
- **1 VPS CPU pequeno** (ex.: Hetzner CX/CPX, 2 vCPU / 4 GB), Linux.
- Roda: **radar de monitoramento** (Módulo E) via `cron`; **OCR e conversão** do fluxo contínuo (poucos arquivos/semana); **Git remoto** do vault para sync da equipe.
- Backlog inicial pesado (Marker/GPU) é feito **à parte**, alugando GPU por horas só naquela semana.
- **Não** roda Cowork (fica nas máquinas da equipe).

### 🔵 Padrão (~US$ 24–48/mês)
- **1 VPS 4 vCPU / 8 GB** para processar lotes maiores em CPU com folga (Docling/OCR em paralelo) e hospedar o **site do vault** (Quartz) para consulta interna.
- Mesmo VPS ou um segundo, pequeno, dedicado ao **radar** 24/7.
- **GPU por hora** para picos de Marker.

### ⚙️ Pico de digitalização (temporário)
- **GPU sob demanda por horas/dias** (H100 ou GPU menor) só para converter um grande acervo escaneado com Marker `--use_llm`. Processe, baixe os resultados, **destrua a instância**. Pague dezenas de reais em vez de centenas mensais.

---

## Sinais de que você ainda **não** precisa de VPS
- O volume é pequeno e esporádico → o computador da equipe (com o painel do Módulo F e o Cowork) dá conta.
- Você só quer sync do vault → **Git/Syncthing entre máquinas** ou **Obsidian Sync** (US$ ~4/mês) resolvem sem administrar servidor.
- Você só quer publicar o vault → **hospedagem estática gratuita** (Cloudflare Pages, GitHub Pages, Netlify) publica um site Quartz sem VPS.

> **Resumo de custo-benefício:** o VPS brilha em **automação contínua por API** e **lotes headless de OCR/conversão** — a partir de ~€5/mês. Ele **não** é o lugar do Cowork. E para GPU, alugue por hora só no backlog. Comece enxuto; suba de porte quando o volume provar que compensa.

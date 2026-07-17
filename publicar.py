#!/usr/bin/env python3
"""
publicar.py — FASE 5 do WORKFLOW, determinística (etapa 8 do trilho).

Distribui o conteúdo de 3-MARKDOWN-LIMPO/ no vault do Obsidian conforme o
frontmatter — o que antes era um prompt de LLM ("distribua os arquivos...")
e podia arquivar errado ou esquecer nota, agora é roteamento por regra:

  destino = pasta do TIPO (taxonomia.PASTAS_PUBLICACAO, config do perfil)
            + subpasta da ÁREA quando a pasta subdivide (01-Doutrina/)
  exceção: documento interno (abnt=False) → 04-Modelos-Internos, sempre.
  fatias vão junto do seu índice (mesma pasta de destino).

TRÊS TRAVAS:
  1. Validação verde: nota REPROVADA pelo auditar_acervo NÃO é publicada —
     publicar metadado quebrado espalha nota invisível pelo vault.
  2. Copiar, nunca mover: 3-MARKDOWN-LIMPO continua sendo o estágio de
     trabalho; o vault é o destino.
  3. O vault VENCE: se o destino já existe com conteúdo diferente, o
     arquivo NÃO é sobrescrito (é lá que vive a curadoria humana). Use
     --force para republicar por cima, conscientemente.

Idempotente: rodar duas vezes não muda nada ("inalterado"). Gera
RELATORIO-PUBLICACAO.md no vault com contagem por área/tipo/status e a
lista dos itens A-conferir (o que a Fase 5 do WORKFLOW pede).

Uso:
    python3 publicar.py 3-MARKDOWN-LIMPO/ 4-OBSIDIAN-VAULT/ --dry   # SEMPRE primeiro
    python3 publicar.py 3-MARKDOWN-LIMPO/ 4-OBSIDIAN-VAULT/
    python3 publicar.py origem/ vault/ --force      # vault deixa de vencer
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import frontmatter
import taxonomia
from comum import alvo_wikilink, vazio
from auditar_acervo import auditar, nota as nota_auditoria


def destino_de(fm, stem):
    """Decide a pasta de destino no vault. → (Path relativo, motivo) ou (None, motivo)."""
    tipo = str(fm.get("tipo") or "")
    tf = str(fm.get("tipo_fonte") or "")

    if tf and not taxonomia.eh_abnt(tf):
        return Path("04-Modelos-Internos"), "documento interno"

    pasta = taxonomia.PASTAS_PUBLICACAO.get(tipo)
    if not pasta:
        return None, (f"tipo '{tipo or '(vazio)'}' sem pasta de publicação — "
                      f"preencha `tipo` com um de: "
                      f"{', '.join(taxonomia.PASTAS_PUBLICACAO)}")

    rel = Path(pasta)
    if pasta in taxonomia.PASTAS_POR_AREA:
        areas = fm.get("area") or []
        if isinstance(areas, str):
            areas = [areas]
        if areas:
            rel = rel / str(areas[0])
    return rel, ""


def publicar(origem: Path, vault: Path, dry: bool, force: bool):
    arquivos = sorted(f for f in origem.rglob("*.md")
                      if not f.name.startswith(("RELATORIO", "_")))
    if not arquivos:
        sys.exit(f"Nenhum .md em {origem} — rode o pipeline até a Fase 4 antes.")

    # 1º passe: classifica tudo e resolve o destino dos ÍNDICES,
    # para as fatias irem junto do seu índice.
    planos, destino_indice = [], {}
    for f in arquivos:
        texto = f.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter.ler(texto).campos
        eh_fatia = not vazio(fm.get("parte")) and not vazio(fm.get("obra"))
        planos.append({"path": f, "fm": fm, "texto": texto, "eh_fatia": eh_fatia})
        if not eh_fatia:
            rel, motivo = destino_de(fm, f.stem)
            if rel is not None:
                destino_indice[f.stem] = rel

    resultado = Counter()
    detalhes = defaultdict(list)   # categoria → linhas p/ relatório
    stats = {"area": Counter(), "tipo": Counter(), "status": Counter()}
    a_conferir = []
    nao_publicou = {}              # stem do índice → razão (gate das fatias)
    retidos = Counter()            # (obra, razão) → nº de fatias retidas

    # Índices ANTES das fatias: fatia publicada sem índice nasce ÓRFÃ no
    # vault (o auditar_vault acusaria em seguida) — se o índice da obra não
    # entrou (sem rota ou reprovado), as fatias ficam RETIDAS junto dele.
    for p in ([x for x in planos if not x["eh_fatia"]]
              + [x for x in planos if x["eh_fatia"]]):
        f, fm = p["path"], p["fm"]

        # ── destino ──
        if p["eh_fatia"]:
            obra = alvo_wikilink(fm.get("obra"))
            if obra in nao_publicou:
                resultado["retido"] += 1
                retidos[(obra, nao_publicou[obra])] += 1
                continue
            rel = destino_indice.get(obra)
            if rel is None:
                rel, motivo = destino_de(fm, f.stem)   # órfã: roteia por conta própria
                if rel is None:
                    resultado["bloqueado"] += 1
                    detalhes["bloqueado"].append(f"{f.name} — fatia: {motivo}")
                    continue
        else:
            rel, motivo = destino_de(fm, f.stem)
            if rel is None:
                resultado["bloqueado"] += 1
                detalhes["bloqueado"].append(f"{f.name} — {motivo}")
                nao_publicou[f.stem] = f"índice sem rota ({motivo.split(' — ')[0]})"
                continue

        # ── TRAVA 1: validação verde (fatias herdam do índice; auditar já sabe) ──
        r = auditar(f)
        if nota_auditoria(r) == "REPROVADO":
            resultado["reprovado"] += 1
            detalhes["reprovado"].append(
                f"{f.name} — {'; '.join(r['erros'][:2])}")
            if not p["eh_fatia"]:
                nao_publicou[f.stem] = ("índice REPROVADO na auditoria — "
                                        "complete a ficha (refino) e republique")
            continue

        alvo = vault / rel / f.name
        etiqueta = f"{rel}/{f.name}"

        # ── idempotência + TRAVA 3: o vault vence ──
        if alvo.exists():
            if alvo.read_text(encoding="utf-8", errors="replace") == p["texto"]:
                resultado["inalterado"] += 1
                continue
            if not force:
                resultado["conflito"] += 1
                detalhes["conflito"].append(
                    f"{etiqueta} — difere do vault (curadoria?); "
                    "use --force para republicar por cima")
                continue
            resultado["sobrescrito"] += 1
            detalhes["sobrescrito"].append(etiqueta)
        else:
            resultado["publicado"] += 1
            detalhes["publicado"].append(etiqueta)

        if not dry:
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(p["texto"], encoding="utf-8")

        # estatísticas do que entrou no vault
        for a in (fm.get("area") or []):
            stats["area"][a] += 1
        if fm.get("tipo"):
            stats["tipo"][str(fm["tipo"])] += 1
        if fm.get("status"):
            stats["status"][str(fm["status"])] += 1
        if "A-conferir" in (str(fm.get("status") or "")
                            + str(fm.get("confiabilidade") or "")):
            a_conferir.append(etiqueta)

    # fatias retidas: UMA linha por obra, não uma por fatia (696 linhas
    # idênticas ensinam a não ler o relatório)
    for (obra, razao), n in sorted(retidos.items()):
        detalhes["retido"].append(f'{n} fatia(s) de "{obra}" retidas com o índice: {razao}')

    # ── console ──
    modo = "DRY-RUN — nada gravado" if dry else "publicação efetiva"
    print(f"\n{'='*72}\nPUBLICAÇÃO — {origem} → {vault}  ({modo})\n{'='*72}")
    LIMITE = 20
    for cat in ("publicado", "sobrescrito", "inalterado", "conflito",
                "reprovado", "bloqueado", "retido"):
        if resultado[cat]:
            print(f"{cat:12}: {resultado[cat]}")
            for linha in detalhes[cat][:LIMITE]:
                print(f"    {'✗' if cat in ('conflito','reprovado','bloqueado','retido') else '→'} {linha}")
            excedente = len(detalhes[cat]) - LIMITE
            if excedente > 0:
                print(f"    … e mais {excedente} — lista completa no RELATORIO-PUBLICACAO.md")

    # ── relatório no vault (a Fase 5 do WORKFLOW pede exatamente isto) ──
    if not dry:
        L = [f"# Relatório de Publicação — {vault.name}", ""]
        L.append("| resultado | qtd |")
        L.append("|---|---|")
        for cat in ("publicado", "sobrescrito", "inalterado", "conflito",
                    "reprovado", "bloqueado", "retido"):
            if resultado[cat]:
                L.append(f"| {cat} | {resultado[cat]} |")
        for eixo in ("area", "tipo", "status"):
            if stats[eixo]:
                L += ["", f"## Por {eixo}", "", f"| {eixo} | notas |", "|---|---|"]
                L += [f"| {k} | {v} |" for k, v in sorted(stats[eixo].items())]
        if a_conferir:
            L += ["", "## ⚠ Itens A-conferir (não citar sem revisão humana)", ""]
            L += [f"- {x}" for x in a_conferir]
        for cat in ("conflito", "reprovado", "bloqueado", "retido"):
            if detalhes[cat]:
                L += ["", f"## ✗ {cat.capitalize()}s", ""]
                L += [f"- {x}" for x in detalhes[cat]]
        L += ["", "> Publicação é COPIAR: 3-MARKDOWN-LIMPO segue como estágio de "
                  "trabalho. Em conflito, o vault vence (é onde vive a curadoria). "
                  "Depois de publicar, rode auditar_vault.py."]
        vault.mkdir(parents=True, exist_ok=True)
        (vault / "RELATORIO-PUBLICACAO.md").write_text("\n".join(L),
                                                       encoding="utf-8")
        print(f"\nRelatório: {vault / 'RELATORIO-PUBLICACAO.md'}")

    houve_problema = resultado["conflito"] + resultado["reprovado"] + resultado["bloqueado"]
    print(f"\n{'-'*72}")
    print(f"OK: {resultado['publicado'] + resultado['sobrescrito'] + resultado['inalterado']}"
          f"  |  problemas: {houve_problema}")

    # Simulação ASSERTIVA: qualidade e publicação andam juntas — o dry-run
    # diz exatamente O QUE fazer para chegar a 100%, na ordem do trilho.
    if resultado["reprovado"] or resultado["bloqueado"] or resultado["retido"] \
            or resultado["conflito"]:
        print("\nPRÓXIMOS PASSOS para publicar 100%:")
        if resultado["reprovado"]:
            print(f"  ✗ {resultado['reprovado']} REPROVADO(s) na auditoria → "
                  "complete a ficha (mesa ✎ Fichas) e REFATIE (etapa 5) — "
                  "fatias herdam do mestre")
        if resultado["bloqueado"]:
            print(f"  ✗ {resultado['bloqueado']} sem rota (tipo vazio/desconhecido) → "
                  "Normalizar (etapa 5) deriva o tipo do tipo_fonte; o restante, "
                  "mesa ✎ Fichas")
        if resultado["conflito"]:
            print(f"  ⚠ {resultado['conflito']} conflito(s): o vault tem versão "
                  "editada (curadoria) — só sobrescreva conscientemente, com --force")
        if resultado["retido"]:
            print(f"  · {resultado['retido']} fatia(s) retidas entram "
                  "AUTOMATICAMENTE quando o índice da obra publicar — nada a "
                  "fazer nelas")
    if dry:
        print("(dry-run: rode sem --dry para gravar)")
    return 1 if houve_problema else 0


def main():
    ap = argparse.ArgumentParser(
        description="Publica 3-MARKDOWN-LIMPO no vault do Obsidian, por regra "
                    "(tipo→pasta do perfil), com trava de validação")
    ap.add_argument("origem", help="pasta com o markdown pronto (3-MARKDOWN-LIMPO)")
    ap.add_argument("vault", help="pasta do vault do Obsidian (4-OBSIDIAN-VAULT)")
    ap.add_argument("--dry", action="store_true", help="só mostra; não grava")
    ap.add_argument("--force", action="store_true",
                    help="sobrescreve destino divergente (o vault deixa de vencer)")
    a = ap.parse_args()

    origem, vault = Path(a.origem), Path(a.vault)
    if not origem.is_dir():
        sys.exit(f"ERRO: não encontrei {origem}")
    sys.exit(publicar(origem, vault, a.dry, a.force))


if __name__ == "__main__":
    main()

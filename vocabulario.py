#!/usr/bin/env python3
"""
vocabulario.py — o vocabulário que o USUÁRIO cria (áreas e tags).

Por que existe
--------------
A taxonomia é a fonte única do vocabulário, e é fechada de propósito: valor
fora dela some dos painéis, e é isso que impede o acervo de virar um saco de
sinônimos. Mas "fechada" virou "imutável": criar a área "Direito Digital"
exigia editar código-fonte, e `tags` — o campo que daria o eixo temático —
nasceu órfão, sem vocabulário nenhum atrás.

Este módulo abre a porta sem derrubar a parede: o usuário acrescenta áreas e
tags, elas passam a valer em TODO o pipeline (a taxonomia as mescla no
import), e quem escreve um valor que ninguém cadastrou recebe AVISO — nunca
reprovação. O vocabulário cresce pelo uso; o erro de digitação fica visível
em vez de virar uma tag órfã.

Divisão de trabalho (comum.py:10-13 manda o recado): a taxonomia é
declarativa e pura; QUEM LÊ O DISCO é este módulo. Ele é a única fronteira,
então é aqui que tudo é saneado — depois daqui, o vocabulário é confiável.

Onde mora
---------
`ACERVO_VOCABULARIO` (env) ou `~/.config/acervo/vocabulario.json` — ao lado
do config.json do painel, mas em arquivo SEPARADO: o `carregar_config()`
descarta toda chave que não seja string, e um vocabulário aninhado ali seria
comido em silêncio.

Formato (lista de registros — é o que o painel edita e renderiza):
    {"versao": 1,
     "areas": [{"nome": "Direito Digital", "codigo": "DIREITODIG",
                "sinonimos": ["digital", "tecnolog"]}],
     "tags":  [{"tag": "lgpd", "titulo": "LGPD e dados pessoais"}]}

Zero dependências externas (stdlib). Autoteste: `python3 vocabulario.py --autoteste`.
"""

import json
import os
import re
from pathlib import Path

import comum

VERSAO = 1

# Códigos de área do NÚCLEO que não podem ser reusados por área de usuário.
# Não importamos taxonomia aqui: seria ciclo (taxonomia importa este módulo).
# Quem chama passa os ocupados — ver `derivar_codigo`.
_RE_CODIGO = re.compile(r"^[A-Z]{2,12}$")


def caminho() -> Path:
    """O arquivo do vocabulário. Env var primeiro — é assim que o painel
    aponta os subprocessos do pipeline para o mesmo vocabulário dele."""
    env = os.environ.get("ACERVO_VOCABULARIO")
    if env:
        return Path(env)
    return Path.home() / ".config" / "acervo" / "vocabulario.json"


# ═══════════════════════════════════════════════════════════════════════════
# Saneamento — a fronteira. Nada entra sem passar por aqui.
# ═══════════════════════════════════════════════════════════════════════════


def nome_area(nome) -> str:
    """Nome canônico de área, apresentável e seguro como nome de PASTA.

    A área vira diretório no vault (publicar.destino_de) — com vocabulário
    aberto, "Civil / Família" viraria dois níveis e "../x" escaparia do
    vault. Aqui só normalizamos espaços; a guarda de caminho é o
    `taxonomia.pasta_segura`, aplicado na hora de montar o destino (não no
    nome, que o usuário quer ver com acento e maiúscula).
    """
    return re.sub(r"\s+", " ", str(nome or "")).strip(" .").strip()


def derivar_codigo(nome: str, ocupados) -> str:
    """'Direito Digital' → 'DIREITODIG', único contra `ocupados`.

    O código entra no nome do arquivo ([AREA]_[TIPO]_...) e o autoteste da
    taxonomia exige unicidade global — código repetido faria o round-trip
    CODIGO_AREA ↔ AREA_POR_CODIGO perder uma área em silêncio.
    """
    base = re.sub(r"[^A-Z]", "", comum.sem_acento(nome).upper()) or "AREA"
    ocupados = {str(c).upper() for c in ocupados}
    for n in range(3, min(len(base), 12) + 1):     # cresce até destravar
        if base[:n] not in ocupados:
            return base[:n]
    raiz = base[:10]
    for i in range(2, 100):                        # ainda colidiu: sufixo
        if f"{raiz}{i}" not in ocupados:
            return f"{raiz}{i}"
    return f"{raiz}X"


def _area_saneada(reg, ocupados) -> dict | None:
    if isinstance(reg, str):
        reg = {"nome": reg}
    if not isinstance(reg, dict):
        return None
    nome = nome_area(reg.get("nome"))
    if not nome:
        return None
    codigo = str(reg.get("codigo") or "").upper()
    codigo = re.sub(r"[^A-Z]", "", comum.sem_acento(codigo).upper())
    if not _RE_CODIGO.match(codigo) or codigo in ocupados:
        codigo = derivar_codigo(nome, ocupados)
    sin = reg.get("sinonimos")
    sinonimos = []
    for s in (sin if isinstance(sin, list) else []):
        s = comum.sem_acento(str(s)).lower().strip()
        if s and s not in sinonimos:
            sinonimos.append(s)
    return {"nome": nome, "codigo": codigo, "sinonimos": sinonimos}


def _tag_saneada(reg) -> dict | None:
    if isinstance(reg, str):
        reg = {"tag": reg}
    if not isinstance(reg, dict):
        return None
    tag = comum.tag_valida(reg.get("tag"))
    if not tag:
        return None
    titulo = re.sub(r"\s+", " ", str(reg.get("titulo") or "")).strip()
    return {"tag": tag, "titulo": titulo}


def sanear(dados) -> tuple:
    """dict cru (do disco ou do painel) → (vocabulário limpo, problemas).

    Nunca levanta e nunca descarta em silêncio: tudo que não entrou vira uma
    linha em `problemas`, que o painel mostra e o pipeline imprime.
    """
    problemas = []
    if not isinstance(dados, dict):
        return {"versao": VERSAO, "areas": [], "tags": []}, \
               ["vocabulário não é um objeto JSON — ignorado por inteiro"]

    areas, vistas, ocupados = [], set(), set()
    for reg in (dados.get("areas") if isinstance(dados.get("areas"), list) else []):
        a = _area_saneada(reg, ocupados)
        if a is None:
            problemas.append(f"área ignorada (sem nome utilizável): {reg!r}")
            continue
        if a["nome"].casefold() in vistas:
            problemas.append(f"área repetida, mantida a primeira: {a['nome']}")
            continue
        vistas.add(a["nome"].casefold())
        ocupados.add(a["codigo"])
        areas.append(a)

    tags, vistos = [], set()
    for reg in (dados.get("tags") if isinstance(dados.get("tags"), list) else []):
        t = _tag_saneada(reg)
        if t is None:
            problemas.append(f"tag ignorada (vazia após normalizar): {reg!r}")
            continue
        if t["tag"] in vistos:
            problemas.append(f"tag repetida, mantida a primeira: {t['tag']}")
            continue
        vistos.add(t["tag"])
        tags.append(t)

    return {"versao": VERSAO, "areas": areas, "tags": tags}, problemas


# ═══════════════════════════════════════════════════════════════════════════
# I/O — arquivo ausente é o caso NORMAL (vocabulário vazio), não erro
# ═══════════════════════════════════════════════════════════════════════════


def ler() -> tuple:
    """→ (vocabulário saneado, problemas). Nunca levanta.

    A taxonomia chama isto no import: um JSON quebrado NÃO pode derrubar o
    pipeline inteiro — degrada para vocabulário-base e declara o problema.
    """
    p = caminho()
    try:
        bruto = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"versao": VERSAO, "areas": [], "tags": []}, []
    except (OSError, ValueError) as e:
        return ({"versao": VERSAO, "areas": [], "tags": []},
                [f"{p}: não consegui ler ({e}) — seguindo só com o "
                 "vocabulário do perfil"])
    return sanear(bruto)


def gravar(voc) -> tuple:
    """Grava saneado. → (ok, problemas). Escrita ATÔMICA (tmp + replace):
    o mesmo 9p do WSL2 que assombra o publicar.py truncaria o vocabulário
    numa falha no meio da escrita, e um vocabulário truncado é pior que
    nenhum — some área do painel sem ninguém notar."""
    limpo, problemas = sanear(voc)
    p = caminho()
    tmp = p.with_suffix(".json.tmp")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(limpo, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(p)
    except OSError as e:
        return False, problemas + [f"{p}: não consegui gravar ({e.strerror or e})"]
    return True, problemas


# ═══════════════════════════════════════════════════════════════════════════
# Edição — o que o painel chama
# ═══════════════════════════════════════════════════════════════════════════


def adicionar_area(nome, codigo="", sinonimos=None, ocupados_base=()) -> tuple:
    """→ (registro criado ou None, problemas). Idempotente: área já
    cadastrada devolve a existente sem duplicar."""
    voc, problemas = ler()
    nome = nome_area(nome)
    if not nome:
        return None, problemas + ["informe o nome da área"]
    for a in voc["areas"]:
        if a["nome"].casefold() == nome.casefold():
            return a, problemas
    ocupados = ({str(c).upper() for c in ocupados_base}
                | {a["codigo"] for a in voc["areas"]})
    novo = _area_saneada({"nome": nome, "codigo": codigo,
                          "sinonimos": sinonimos or []}, ocupados)
    if novo is None:
        return None, problemas + [f"não consegui usar o nome: {nome!r}"]
    voc["areas"].append(novo)
    ok, probs = gravar(voc)
    return (novo if ok else None), problemas + probs


def adicionar_tag(tag, titulo="") -> tuple:
    """→ (registro criado ou None, problemas). Idempotente."""
    voc, problemas = ler()
    novo = _tag_saneada({"tag": tag, "titulo": titulo})
    if novo is None:
        return None, problemas + [f"tag vazia depois de normalizar: {tag!r}"]
    for t in voc["tags"]:
        if t["tag"] == novo["tag"]:
            if novo["titulo"] and t["titulo"] != novo["titulo"]:
                t["titulo"] = novo["titulo"]       # renomear o rótulo humano
                ok, probs = gravar(voc)
                return (t if ok else None), problemas + probs
            return t, problemas
    voc["tags"].append(novo)
    ok, probs = gravar(voc)
    return (novo if ok else None), problemas + probs


def remover_area(nome) -> tuple:
    """→ (removeu?, problemas). Não mexe em nota nenhuma: as que usam a área
    passam a acusar 'fora do vocabulário' — que é a intenção de remover."""
    voc, problemas = ler()
    nome = nome_area(nome)
    antes = len(voc["areas"])
    voc["areas"] = [a for a in voc["areas"]
                    if a["nome"].casefold() != nome.casefold()]
    if len(voc["areas"]) == antes:
        return False, problemas
    ok, probs = gravar(voc)
    return ok, problemas + probs


def remover_tag(tag) -> tuple:
    voc, problemas = ler()
    alvo = comum.tag_valida(tag)
    antes = len(voc["tags"])
    voc["tags"] = [t for t in voc["tags"] if t["tag"] != alvo]
    if len(voc["tags"]) == antes:
        return False, problemas
    ok, probs = gravar(voc)
    return ok, problemas + probs


# ═══════════════════════════════════════════════════════════════════════════
# Autoteste
# ═══════════════════════════════════════════════════════════════════════════


def _autoteste():
    import tempfile
    erros = []

    def ok(cond, msg):
        if not cond:
            erros.append(msg)

    with tempfile.TemporaryDirectory() as d:
        os.environ["ACERVO_VOCABULARIO"] = str(Path(d) / "vocabulario.json")

        # arquivo ausente é o caso normal, não erro
        voc, probs = ler()
        ok(voc["areas"] == [] and voc["tags"] == [] and not probs,
           f"vocabulário ausente devia ser vazio e mudo: {voc}, {probs}")

        # área nova: código derivado, único, e round-trip pelo disco
        a, probs = adicionar_area("Direito Digital", ocupados_base=("TRIB",))
        ok(a and a["nome"] == "Direito Digital" and a["codigo"] == "DIR",
           f"área/código derivado: {a}")
        ok(ler()[0]["areas"][0]["nome"] == "Direito Digital",
           "área não sobreviveu ao disco")

        # idempotência: nada duplica
        adicionar_area("Direito Digital")
        ok(len(ler()[0]["areas"]) == 1, "adicionar duas vezes duplicou a área")

        # colisão de código contra o núcleo E contra outra área do usuário
        b, _ = adicionar_area("Direito Desportivo", ocupados_base=("DIR",))
        ok(b and b["codigo"] not in ("DIR",),
           f"código devia desviar da colisão: {b}")
        codigos = [x["codigo"] for x in ler()[0]["areas"]]
        ok(len(set(codigos)) == len(codigos), f"códigos duplicados: {codigos}")

        # tag: normaliza, preserva hierarquia, não duplica
        t, _ = adicionar_tag("Planejamento / Holding", "Holding familiar")
        ok(t and t["tag"] == "planejamento/holding",
           f"tag hierárquica normalizada: {t}")
        adicionar_tag("planejamento/holding")
        ok(len(ler()[0]["tags"]) == 1, "tag duplicou")
        ok(ler()[0]["tags"][0]["titulo"] == "Holding familiar",
           "título humano da tag se perdeu")

        # lixo não derruba nem entra
        vazia, _ = adicionar_tag("///")
        ok(vazia is None, "tag vazia não podia entrar")
        Path(caminho()).write_text("{ isso não é json", encoding="utf-8")
        voc, probs = ler()
        ok(voc["areas"] == [] and probs,
           "JSON quebrado tinha de degradar para vazio COM problema declarado")

        # saneamento de registros malformados, sem levantar
        limpo, probs = sanear({"areas": ["Só o nome", 42, {"nome": "  "}],
                               "tags": [{"tag": "Ação Rescisória"}, None]})
        ok([x["nome"] for x in limpo["areas"]] == ["Só o nome"],
           f"saneamento de áreas: {limpo['areas']}")
        ok([x["tag"] for x in limpo["tags"]] == ["acao-rescisoria"],
           f"saneamento de tags: {limpo['tags']}")
        ok(len(probs) == 3, f"problemas deviam ser declarados: {probs}")

        os.environ.pop("ACERVO_VOCABULARIO", None)

    if erros:
        for e in erros:
            print(f"  ✗ {e}")
        print(f"AUTOTESTE: {len(erros)} falha(s)")
        return 1
    print("AUTOTESTE: vocabulario íntegro ✓")
    return 0


if __name__ == "__main__":
    import sys
    if "--autoteste" in sys.argv:
        sys.exit(_autoteste())
    voc, problemas = ler()
    print(f"Vocabulário do usuário: {caminho()}")
    print(f"  áreas: {', '.join(a['nome'] for a in voc['areas']) or '(nenhuma)'}")
    print(f"  tags : {', '.join(t['tag'] for t in voc['tags']) or '(nenhuma)'}")
    for p in problemas:
        print(f"  ! {p}")

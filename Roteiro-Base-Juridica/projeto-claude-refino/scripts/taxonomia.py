#!/usr/bin/env python3
"""
taxonomia.py — FONTE ÚNICA do vocabulário do Acervo.

Todo vocabulário controlado vive aqui e SOMENTE aqui: tipos de fonte ABNT,
campos obrigatórios, localizadores, âncoras, idiomas, áreas, status,
confiabilidade e os códigos de nome de arquivo. Os scripts do pipeline
(validar, auditar, fatiar, injetar, normalizar, triagem) importam este
módulo — nenhum deles mantém cópia própria.

Arquitetura: NÚCLEO × PERFIL.
  - O núcleo é invariante entre domínios do conhecimento: um livro de
    medicina se cita (ABNT) exatamente como um livro de direito.
  - O que é específico de um domínio (áreas, o eixo funcional `tipo`,
    vocabulário de vigência, heurísticas de triagem) vive num PERFIL.
    O perfil `juridico` é o primeiro; contemplar outra área do conhecimento
    = escrever outro perfil, não refatorar o pipeline.

Zero dependências externas (stdlib). Zero I/O — só dados e funções puras.
Autoteste: `python3 taxonomia.py --autoteste`.
"""

import os
import re
import sys
from typing import NamedTuple

# ═══════════════════════════════════════════════════════════════════════════
# NÚCLEO — invariante entre domínios
# ═══════════════════════════════════════════════════════════════════════════


class TipoFonte(NamedTuple):
    obrigatorios: tuple          # campos que a ABNT exige para este tipo
    localizador: tuple           # (localizador_tipo, localizador_abrev)
    exige_ancora: bool           # o markdown precisa de âncoras {{p.NN}}/{{loc.NNNN}}?
    aviso: str = ""              # alerta exibido ao validar (ex.: e-book de leitor)
    abnt: bool = True            # False = documento interno, fora do regime ABNT


TIPOS_FONTE = {
    "livro": TipoFonte(
        obrigatorios=("autoria", "titulo", "local_publicacao", "editora", "ano"),
        localizador=("pagina", "p."),
        exige_ancora=True,
    ),
    "livro_ebook_leitor": TipoFonte(
        obrigatorios=("autoria", "titulo", "local_publicacao", "editora", "ano"),
        localizador=("posicao", "local."),
        exige_ancora=True,
        aviso="E-book de leitor: a 'posição' varia com o tamanho da fonte. "
              "Para citar em peça, prefira a edição impressa/PDF paginado.",
    ),
    "livro_ebook_online": TipoFonte(
        obrigatorios=("autoria", "titulo", "local_publicacao", "editora", "ano",
                      "url", "data_acesso"),
        localizador=("pagina", "p."),
        exige_ancora=True,
    ),
    "capitulo_livro": TipoFonte(
        obrigatorios=("autoria", "titulo", "autoria_todo", "titulo_todo",
                      "local_publicacao", "editora", "ano",
                      "pagina_inicio", "pagina_fim"),
        localizador=("pagina", "p."),
        exige_ancora=True,
    ),
    "artigo_periodico": TipoFonte(
        obrigatorios=("autoria", "titulo", "titulo_periodico",
                      "pagina_inicio", "pagina_fim", "ano"),
        localizador=("pagina", "p."),
        exige_ancora=True,
    ),
    "trabalho_academico": TipoFonte(
        obrigatorios=("autoria", "titulo", "grau", "instituicao",
                      "local_publicacao", "ano"),
        localizador=("pagina", "p."),
        exige_ancora=True,
    ),
    "evento": TipoFonte(
        obrigatorios=("autoria", "titulo", "nome_evento", "ano_evento",
                      "local_evento", "ano"),
        localizador=("pagina", "p."),
        exige_ancora=True,
    ),
    "legislacao": TipoFonte(
        obrigatorios=("autoria", "norma_numero", "norma_data", "ementa", "ano"),
        localizador=("artigo", "art."),
        exige_ancora=False,   # cita-se pelo dispositivo, não pela página
    ),
    "jurisprudencia": TipoFonte(
        obrigatorios=("orgao", "numero_processo", "relator", "data_julgamento"),
        localizador=("sem_localizador", ""),
        exige_ancora=False,   # cita-se o julgado
    ),
    "ato_administrativo": TipoFonte(
        obrigatorios=("orgao_emissor", "especie_ato", "numero_ato", "data_ato"),
        localizador=("artigo", "art."),
        exige_ancora=False,
    ),
    "documento_online": TipoFonte(
        obrigatorios=("titulo", "url", "data_acesso", "ano"),
        localizador=(None, None),   # variável
        exige_ancora=False,
    ),
    # ── Tipos que o ESQUEMA_YAML_ABNT.md prometia e o validador rejeitava ──
    "verbete": TipoFonte(
        # Entrada pelo TÍTULO: verbete costuma ser anônimo — autoria NÃO é
        # obrigatória (NBR 6023, elementos faltantes).
        obrigatorios=("titulo", "titulo_todo", "local_publicacao",
                      "editora", "ano"),
        localizador=("pagina", "p."),
        exige_ancora=False,   # verbetes são curtos; exigir {{p.NN}} reprovaria todos
    ),
    "norma_tecnica": TipoFonte(
        obrigatorios=("autoria", "norma_numero", "titulo",
                      "local_publicacao", "ano"),
        localizador=("secao", "seç."),
        exige_ancora=False,
    ),
    "audiovisual": TipoFonte(
        obrigatorios=("titulo", "autoria", "ano", "suporte"),
        localizador=("sem_localizador", ""),
        exige_ancora=False,
    ),
    "correspondencia": TipoFonte(
        obrigatorios=("autoria", "titulo", "destinatario",
                      "local_publicacao", "data"),
        localizador=("sem_localizador", ""),
        exige_ancora=False,
    ),
    # ── Documento interno do escritório — fora do regime ABNT ──
    # Antes era um tipo-fantasma: nascia no aplicar_ocr.sh, aparecia no CSV
    # e na UI, mas nenhum vocabulário o conhecia e o validador o rejeitava.
    # É a casa natural de `tipo: Modelo`.
    "peca_interna": TipoFonte(
        obrigatorios=("titulo",),
        localizador=(None, None),   # interno: sem burocracia de localizador
        exige_ancora=False,
        aviso="Documento interno — fora do regime ABNT (não gera referência).",
        abnt=False,
    ),
}

# DÍVIDA DE MIGRAÇÃO — campos que a ABNT exige mas que o acervo atual ainda
# não tem preenchidos em massa. Rebaixados de ERRO para AVISO até o backlog
# daquele tipo zerar. Esta tabela deve ENCOLHER e ser deletada; nunca crescer.
# (É exatamente o delta histórico entre validar_yaml_abnt.REGRAS e
#  auditar_acervo.CAMPOS_ABNT.)
TOLERADOS = {
    "livro_ebook_leitor": ("local_publicacao",),
    "livro_ebook_online": ("local_publicacao", "data_acesso"),
    "capitulo_livro": ("autoria_todo", "local_publicacao"),
    "trabalho_academico": ("local_publicacao",),
    "evento": ("ano_evento", "local_evento"),
}

# ACERVO_ESTRITO=1 → pré-visualiza o futuro: tolerados voltam a bloquear.
ESTRITO = os.environ.get("ACERVO_ESTRITO") == "1"

# Âncoras de localização no markdown (páginas e posições de e-book).
ANCORA_PAG = re.compile(r"\{\{p\.[0-9ivxlcdm]+\}\}|<!--\s*p\.[0-9ivxlcdm]+\s*-->", re.I)
ANCORA_POS = re.compile(r"\{\{loc\.\d+\}\}", re.I)

# Idiomas do acervo (código Tesseract → nome) e forma da edição por língua
# (NBR 6023: a edição segue a língua do documento).
IDIOMAS = {"por": "português", "eng": "inglês", "deu": "alemão",
           "fra": "francês", "ita": "italiano", "spa": "espanhol"}
IDIOMA_EDICAO = {"por": "N. ed.", "eng": "Nth ed.", "deu": "N. Aufl.",
                 "fra": "Ne éd.", "ita": "N. ed.", "spa": "N. ed."}

CONFIABILIDADE = ("Oficial", "Doutrinária", "Interna", "A-conferir", "Conferida")


# ═══════════════════════════════════════════════════════════════════════════
# PERFIS DE DOMÍNIO
# ═══════════════════════════════════════════════════════════════════════════


class Perfil(NamedTuple):
    nome: str
    tipos: tuple                 # eixo funcional (`tipo` no frontmatter)
    areas: dict                  # chave-de-busca (substring) → área canônica
    codigo_area: dict            # área canônica → código de nome de arquivo
    codigo_tipo: dict            # tipo funcional → código de nome de arquivo
    tipos_por_fonte: dict        # tipo_fonte → tipos funcionais coerentes
    status: tuple                # vocabulário de vigência/situação
    natureza: tuple
    heuristicas_tipo: tuple      # ((palavras-chave...), tipo_fonte) p/ triagem


PERFIS = {
    "juridico": Perfil(
        nome="juridico",
        tipos=("Doutrina", "Legislação", "Jurisprudência", "Súmula",
               "Artigo", "Parecer", "Modelo"),
        areas={
            "tribut": "Tributário",
            "fiscal": "Tributário",
            "civil": "Civil",
            "penal": "Penal",
            "criminal": "Penal",
            "trabalh": "Trabalhista",
            "laboral": "Trabalhista",
            "administrativ": "Administrativo",
            "constitucional": "Constitucional",
            "empresarial": "Empresarial",
            "comercial": "Empresarial",
            "societ": "Empresarial",
            "consumidor": "Consumidor",
            "previdenci": "Previdenciário",
            "ambient": "Ambiental",
            "famil": "Família",
            "processual": "Processual",
            "processo": "Processual",
            "economic": "Econômico",
            "financeir": "Financeiro",
            "internacional": "Internacional",
            "eleitoral": "Eleitoral",
        },
        codigo_area={
            "Tributário": "TRIB", "Civil": "CIVIL", "Penal": "PEN",
            "Trabalhista": "TRAB", "Administrativo": "ADMIN",
            "Constitucional": "CONST", "Empresarial": "EMPR",
            "Consumidor": "CONS", "Previdenciário": "PREV",
            "Ambiental": "AMB", "Família": "FAM", "Processual": "PROC",
            "Econômico": "ECON", "Financeiro": "FIN",
            "Internacional": "INTL", "Eleitoral": "ELEI",
        },
        codigo_tipo={
            "Doutrina": "DOUT", "Legislação": "LEGIS",
            "Jurisprudência": "JURIS", "Súmula": "SUM",
            "Artigo": "ART", "Parecer": "PAR", "Modelo": "MODELO",
        },
        tipos_por_fonte={
            "livro": ("Doutrina",),
            "livro_ebook_leitor": ("Doutrina",),
            "livro_ebook_online": ("Doutrina",),
            "capitulo_livro": ("Doutrina",),
            "artigo_periodico": ("Artigo", "Doutrina"),
            "trabalho_academico": ("Doutrina", "Artigo"),
            "evento": ("Doutrina", "Artigo"),
            "legislacao": ("Legislação",),
            "jurisprudencia": ("Jurisprudência", "Súmula"),   # não-bijetivo
            "ato_administrativo": ("Parecer", "Legislação"),
            # escape hatch: documento online pode carregar qualquer eixo
            "documento_online": ("Doutrina", "Legislação", "Jurisprudência",
                                 "Súmula", "Artigo", "Parecer", "Modelo"),
            "verbete": ("Doutrina",),
            "norma_tecnica": ("Legislação", "Doutrina"),
            "audiovisual": ("Doutrina", "Legislação", "Jurisprudência",
                            "Súmula", "Artigo", "Parecer", "Modelo"),
            "correspondencia": ("Parecer", "Modelo", "Doutrina"),
            "peca_interna": ("Modelo", "Parecer"),
        },
        status=("Vigente", "A-conferir", "Revogado", "Alterado",
                "Superado", "Modulado"),
        natureza=("Contencioso-Judicial", "Contencioso-Administrativo",
                  "Consultivo", "Extrajudicial"),
        # Heurísticas de triagem pelo NOME do arquivo — são conhecimento do
        # domínio (um radiologista não nomeia arquivos com "acórdão").
        # União das regras históricas de aplicar_ocr.sh e acervo_app.py,
        # com as variantes seguras ("resp "/"resp-", não "*resp*").
        heuristicas_tipo=(
            (("acordao", "acórdão", "resp ", "resp-", "agravo", "apela",
              "habeas", "sumula", "súmula", "jurisprud"), "jurisprudencia"),
            (("lei", "decreto", "codigo", "código", "constituic",
              "medida-provisoria", "emenda"), "legislacao"),
            (("portaria", "instrucao-normativa", "instrução", "resolucao",
              "resolução", "edital", "parecer", "oficio", "ofício"),
             "ato_administrativo"),
            (("tese", "dissertacao", "dissertação", "monografia", "tcc"),
             "trabalho_academico"),
            (("artigo", "revista", "periodico", "periódico"),
             "artigo_periodico"),
            (("peticao", "petição", "contestacao", "contestação", "recurso",
              "minuta", "contrato"), "peca_interna"),
        ),
    ),
}

PERFIL_ATIVO = PERFIS[os.environ.get("ACERVO_PERFIL", "juridico")]


def _inverter(d):
    inv = {}
    for k, v in d.items():
        if isinstance(v, tuple):
            for item in v:
                inv.setdefault(item, []).append(k)
        else:
            inv[v] = k
    return {k: tuple(v) if isinstance(v, list) else v for k, v in inv.items()}


# Aliases de módulo — os consumidores usam taxonomia.AREAS etc.; a indireção
# do perfil custa esta linha e torna o segundo domínio um acréscimo.
TIPOS = PERFIL_ATIVO.tipos
AREAS = PERFIL_ATIVO.areas
CODIGO_AREA = PERFIL_ATIVO.codigo_area
CODIGO_TIPO = PERFIL_ATIVO.codigo_tipo
TIPOS_POR_FONTE = PERFIL_ATIVO.tipos_por_fonte
STATUS = PERFIL_ATIVO.status
NATUREZA = PERFIL_ATIVO.natureza
HEURISTICAS_TIPO = PERFIL_ATIVO.heuristicas_tipo
FONTES_POR_TIPO = _inverter(TIPOS_POR_FONTE)
AREA_POR_CODIGO = _inverter(CODIGO_AREA)
TIPO_POR_CODIGO = _inverter(CODIGO_TIPO)


# ═══════════════════════════════════════════════════════════════════════════
# API
# ═══════════════════════════════════════════════════════════════════════════


def campos_obrigatorios(tipo_fonte):
    """A verdade ABNT: tudo que o tipo exige."""
    return TIPOS_FONTE[tipo_fonte].obrigatorios


def campos_tolerados(tipo_fonte):
    """Dívida de migração do tipo (vira aviso, não erro)."""
    if ESTRITO:
        return ()
    return TOLERADOS.get(tipo_fonte, ())


def campos_bloqueantes(tipo_fonte):
    """O que efetivamente bloqueia hoje: obrigatórios − tolerados."""
    tol = campos_tolerados(tipo_fonte)
    return tuple(c for c in campos_obrigatorios(tipo_fonte) if c not in tol)


def exige_ancora(tipo_fonte):
    return TIPOS_FONTE[tipo_fonte].exige_ancora


def localizador(tipo_fonte):
    """(localizador_tipo, localizador_abrev) ou (None, None) se variável."""
    return TIPOS_FONTE[tipo_fonte].localizador


def eh_abnt(tipo_fonte):
    """False para documentos internos (fora do regime ABNT de referência)."""
    t = TIPOS_FONTE.get(tipo_fonte)
    return t.abnt if t else True


def par_coerente(tipo, tipo_fonte):
    """O par (tipo funcional, tipo_fonte ABNT) faz sentido? → (ok, motivo)."""
    if not tipo or not tipo_fonte:
        return True, ""            # ausência é problema de outro validador
    permitidos = TIPOS_POR_FONTE.get(tipo_fonte)
    if permitidos is None:
        return False, f"tipo_fonte desconhecido: '{tipo_fonte}'"
    if tipo not in permitidos:
        return False, (f"tipo '{tipo}' não combina com tipo_fonte "
                       f"'{tipo_fonte}' (esperado: {', '.join(permitidos)})")
    return True, ""


_NOME_RE = re.compile(
    r"^(?P<area>[A-ZÀ-Ü]+)_(?P<tipo>[A-ZÀ-Ü]+)_(?P<ano>\d{4})_"
    r"(?P<titulo>[^_]+)_(?P<autor>[^_]+?)(?P<sufixo>_INDICE|_p\d+)?$"
)
_SUFIXO_FATIA = re.compile(r"_(INDICE|p\d+)$", re.I)


def analisar_nome(nome):
    """Analisa um nome de arquivo contra o padrão [AREA]_[TIPO]_[ANO]_[Titulo]_[Autor].

    Nunca levanta exceção, nunca bloqueia — devolve avisos. Fatias e índices
    (sufixos _pNN/_INDICE) NÃO são re-julgados: a convenção é validada uma
    vez, no arquivo-pai.
    """
    stem = nome[:-3] if nome.lower().endswith(".md") else nome
    r = {"area": None, "tipo": None, "ano": None, "titulo": None,
         "autor": None, "sufixo": None, "eh_derivado": False, "avisos": []}
    m_suf = _SUFIXO_FATIA.search(stem)
    if m_suf:
        r["sufixo"] = m_suf.group(0)
        r["eh_derivado"] = m_suf.group(1).lower() != "indice"
    m = _NOME_RE.match(stem)
    if not m:
        if not r["eh_derivado"]:
            r["avisos"].append(
                "nome fora do padrão [AREA]_[TIPO]_[ANO]_[Titulo]_[Autor]")
        return r
    r.update({k: m.group(k) for k in ("area", "tipo", "ano", "titulo", "autor")})
    if r["eh_derivado"]:
        return r                    # convenção julgada no pai, não na fatia
    if r["area"] not in AREA_POR_CODIGO:
        r["avisos"].append(f"código de área desconhecido: '{r['area']}' "
                           f"(válidos: {', '.join(sorted(AREA_POR_CODIGO))})")
    if r["tipo"] not in TIPO_POR_CODIGO:
        r["avisos"].append(f"código de tipo desconhecido: '{r['tipo']}' "
                           f"(válidos: {', '.join(sorted(TIPO_POR_CODIGO))})")
    return r


# ═══════════════════════════════════════════════════════════════════════════
# Autoteste
# ═══════════════════════════════════════════════════════════════════════════


def _autoteste():
    erros = []

    def ok(cond, msg):
        if not cond:
            erros.append(msg)

    for nome, p in PERFIS.items():
        # todo tipo_fonte mapeado existe no núcleo, e vice-versa
        for tf in p.tipos_por_fonte:
            ok(tf in TIPOS_FONTE,
               f"[{nome}] tipos_por_fonte tem tipo_fonte órfão: {tf}")
        for tf in TIPOS_FONTE:
            ok(tf in p.tipos_por_fonte,
               f"[{nome}] tipo_fonte sem mapeamento de tipo: {tf}")
        # valores do mapa ⊆ eixo funcional do perfil
        for tf, tipos in p.tipos_por_fonte.items():
            for t in tipos:
                ok(t in p.tipos, f"[{nome}] {tf} → tipo fora do eixo: {t}")
        # códigos cobrem os vocabulários e são únicos
        areas_canonicas = set(p.areas.values())
        ok(set(p.codigo_area) == areas_canonicas,
           f"[{nome}] codigo_area não cobre exatamente as áreas canônicas")
        ok(set(p.codigo_tipo) == set(p.tipos),
           f"[{nome}] codigo_tipo não cobre exatamente os tipos")
        ok(len(set(p.codigo_area.values())) == len(p.codigo_area),
           f"[{nome}] códigos de área duplicados")
        ok(len(set(p.codigo_tipo.values())) == len(p.codigo_tipo),
           f"[{nome}] códigos de tipo duplicados")
        # heurísticas apontam para tipos_fonte conhecidos
        for chaves, tf in p.heuristicas_tipo:
            ok(tf in TIPOS_FONTE,
               f"[{nome}] heurística aponta p/ tipo_fonte órfão: {tf}")

    # dívida ⊆ obrigatórios
    for tf, campos in TOLERADOS.items():
        ok(tf in TIPOS_FONTE, f"TOLERADOS tem tipo_fonte órfão: {tf}")
        for c in campos:
            ok(c in TIPOS_FONTE[tf].obrigatorios,
               f"TOLERADOS[{tf}] tem campo não-obrigatório: {c}")

    # inversões fazem round-trip
    for area, cod in CODIGO_AREA.items():
        ok(AREA_POR_CODIGO[cod] == area, f"round-trip falhou: {area}↔{cod}")

    # analisar_nome nos exemplos canônicos da doc
    ex = analisar_nome("TRIB_DOUT_2023_Curso-Direito-Tributario_Machado.md")
    ok(ex["area"] == "TRIB" and ex["tipo"] == "DOUT" and not ex["avisos"],
       f"exemplo canônico falhou: {ex}")
    ex2 = analisar_nome("TRIB_DOUT_2023_Curso_Machado_p03.md")
    ok(ex2["eh_derivado"] and not ex2["avisos"],
       f"fatia não deveria gerar aviso: {ex2}")

    if erros:
        for e in erros:
            print(f"  ✗ {e}")
        print(f"AUTOTESTE: {len(erros)} falha(s)")
        return 1
    print("AUTOTESTE: taxonomia íntegra ✓")
    return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(_autoteste())
    print(__doc__)

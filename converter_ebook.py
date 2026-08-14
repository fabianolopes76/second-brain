#!/usr/bin/env python3
"""
converter_ebook.py — Converte e-book (ePUB/MOBI/AZW3/AZW) em Markdown
PRESERVANDO a citabilidade.

Por que este script existe
--------------------------
É o irmão do `injetar_paginas.py`: aquele resolve o PDF, este resolve o e-book.
O problema é o mesmo — Markdown não tem página, e sem localizador é IMPOSSÍVEL
citar conforme a ABNT (NBR 10520:2023) — mas a resposta é diferente, porque
e-book nem sempre TEM página.

A rota antiga (`ebook-convert --txt-output-formatting=markdown` chamado direto
pelo app) entregava um .md sem ficha e sem âncora: nascia órfão, a auditoria
reprovava e o publicar bloqueava. E o log culpava o formato por uma limitação
que era da rota.

HIERARQUIA DE EVIDÊNCIA DE PÁGINA — "tem paginação" não é sim/não; depende de
quanto o editor registrou. Da mais forte para a mais fraca, e sempre PARTINDO DO
ÍNDICE (que diz o rótulo impresso), não do marcador solto:

  1. epub3-page-list  <nav epub:type="page-list"> → {arquivo#frag: rótulo}.
                      O rótulo é o TEXTO DO LINK = a página impressa.
  2. ncx-page-list    <pageList><pageTarget> no NCX (EPUB2).
  3. pagebreak-scan   varredura de epub:type="pagebreak" com rótulo em
                      title/aria-label, ou número no fim do id. É INFERÊNCIA.
  4. posicao          Nenhum marcador utilizável → {{loc.N}} sintético.

Nos casos 1–3 o arquivo sai com {{p.NN}} e é citável por página. No caso 4 sai
com {{loc.NN}} e `tipo_fonte: livro_ebook_leitor`, cujo aviso a taxonomia já
traz. `paginacao_origem` grava QUAL evidência foi usada — quem cita precisa
saber se a página é do editor ou uma inferência nossa.

TRÊS TRAVAS, porque âncora errada é pior que âncora nenhuma (uma reprova na
auditoria; a outra faz citar a p. 147 um trecho que está na 148):
  - RÓTULO: só aceita ^\\d+$ ou ^[ivxlcdm]+$ — é o que taxonomia.ANCORA_PAG lê.
    Rótulo "A-3"/"147a" reprova o page-list INTEIRO e cai para posição.
  - COBERTURA: se menos de 90% das entradas do índice casarem com o texto,
    degrada para posição. Um doc com {{p.1}}..{{p.50}} e nada depois PARECE
    paginado, passa no verificar_ancoras, e só se descobre quebrado quando
    alguém precisa citar a p. 300.
  - CONTAGEM: âncora prevista × âncora no texto; divergiu, NÃO GRAVA NADA.
    É a mesma recusa de limpar_ocr.py:161-165 e fatiar.py:208-211.

A POSIÇÃO É DESTE ACERVO, NÃO A DO KINDLE. A location da Amazon tem ~128
caracteres; usá-la geraria ~4.000 âncoras num livro, ruído em toda a cadeia e —
pior — números que PARECEM locations do Kindle sem serem. Usamos 1500
CARACTERES (não bytes: em português cada acento são 2 bytes, e contar bytes
faria a densidade mudar por idioma), ~1 página impressa de livro jurídico. O
passo fica em `posicao_passo`, para a numeração ser reproduzível.

Motor: pandoc, um só. O writer é `gfm`, e isso não é preferência — o writer
`markdown` emite título SETEXT ("Cap 5" + "-----"), que o fatiar.py:37 (só ATX)
não reconhece e o limpar_ocr.py:44 APAGA como "linha de traços": todo título do
livro viraria parágrafo em silêncio. O `gfm` emite ATX, tabela pipe e blockquote,
e mantém o <span> do pagebreak (tem +raw_html por padrão) — que é como as
âncoras sobrevivem à conversão. Não há motor de reserva de propósito: dois
motores seriam duas qualidades para o mesmo acervo, o incidente dos parsers
divergentes que o comum.py:5-9 registra.

Dependências (binários, não pacotes Python — este script é stdlib):
    sudo apt install -y pandoc calibre
O calibre (ebook-convert) só normaliza MOBI/AZW/AZW3 → ePUB.

Uso:
    python3 converter_ebook.py livro.epub -o livro.md
    python3 converter_ebook.py livro.mobi -o livro.md --tipo-fonte livro
    python3 converter_ebook.py livro.epub -o livro.md --posicao-passo 1200
    python3 converter_ebook.py livro.epub -o livro.md --ancora comentario
"""

import argparse
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import frontmatter
import taxonomia

EXTENSOES_CALIBRE = (".mobi", ".azw", ".azw3")

# O pandoc devolve cada marcador do e-book como um <span> vazio, com o id já
# prefixado pelo href do spine (ex.: "cap1.xhtml#page147").
SPAN = re.compile(r'<span\s+([^>]*?)>\s*</span>')
ATRIBUTO = re.compile(r'(\w[\w:-]*)="([^"]*)"')
# `page_147`, `page-147`, `page147`, `pg147` — o número no fim do fragmento.
ID_COM_PAGINA = re.compile(r"(?:page|pg|pagina)[-_]?(\d+)$", re.I)
IMAGEM = re.compile(r"!\[[^\]]*\]\([^)]*\)")
CERCA = re.compile(r"^\s*(```|~~~)")
ROTULO_OK = re.compile(r"^(?:\d+|[ivxlcdm]+)$", re.I)

# Idiomas: o vocabulário é do taxonomia.py (fonte única). Aqui só o de→para do
# código BCP-47 do e-book (pt-BR, en-US) para o código do acervo (por, eng).
BCP47 = {"pt": "por", "en": "eng", "de": "deu", "fr": "fra",
         "it": "ita", "es": "spa"}


def _sair(msg: str) -> None:
    sys.exit(f"ERRO: {msg}")


def checar_ferramentas(precisa_calibre: bool) -> None:
    """Falha cedo e com a linha de instalação — como aplicar_ocr.sh:285-291.

    Sem isto, a ausência do pandoc apareceria como markdown vazio."""
    if not shutil.which("pandoc"):
        _sair("falta o pandoc. Instale:  sudo apt install -y pandoc")
    if precisa_calibre and not shutil.which("ebook-convert"):
        _sair("MOBI/AZW exigem o Calibre. Instale:  sudo apt install -y calibre")


# ── Um parser só, e tolerante ────────────────────────────────────────────────
# NÃO usar xml.etree: ele levanta ParseError em entidade não declarada
# (`&nbsp;` sem DOCTYPE é epidêmico em EPUB2) e e-book do mundo real é tag soup.
# Um parser para container.xml, OPF, nav.xhtml e NCX — e um incidente só.

class Coletor(HTMLParser):
    """Coleta (tag, atributos, texto) de todas as tags de interesse, na ordem.

    Guarda também a pilha de tags abertas: é o que permite saber que um <a>
    está DENTRO de um <nav epub:type="page-list"> ou de um <pageTarget>."""

    def __init__(self, interesse):
        super().__init__(convert_charrefs=True)
        self.interesse = set(interesse)
        self.itens = []          # [(tag, attrs, texto, pilha)]
        self.pilha = []
        self._abertos = []       # índices em self.itens ainda coletando texto

    def handle_starttag(self, tag, attrs):
        d = {k.lower(): (v or "") for k, v in attrs}
        self.pilha.append((tag, d))
        if tag in self.interesse:
            self.itens.append([tag, d, "", list(self.pilha[:-1])])
            self._abertos.append(len(self.itens) - 1)

    def handle_startendtag(self, tag, attrs):
        d = {k.lower(): (v or "") for k, v in attrs}
        if tag in self.interesse:
            self.itens.append([tag, d, "", list(self.pilha)])

    def handle_endtag(self, tag):
        for i in reversed(range(len(self.pilha))):
            if self.pilha[i][0] == tag:
                del self.pilha[i:]
                break
        if self._abertos and self.itens[self._abertos[-1]][0] == tag:
            self._abertos.pop()

    def handle_data(self, dado):
        for i in self._abertos:
            self.itens[i][2] += dado


def coletar(bytes_xml: bytes, tags) -> list:
    p = Coletor(tags)
    try:
        p.feed(bytes_xml.decode("utf-8", errors="replace"))
    except Exception:
        pass                      # tag soup: fica o que deu para ler
    return p.itens


def _dentro_de(pilha, tag: str, attr: str = "", valor: str = "") -> bool:
    for t, d in pilha:
        if t != tag:
            continue
        if not attr:
            return True
        for k, v in d.items():
            if k.endswith(attr) and valor in v:
                return True
    return False


# ── Entrada: tudo vira ePUB ──────────────────────────────────────────────────

def para_epub(entrada: Path, tmp: Path) -> Path:
    """MOBI/AZW/AZW3 → ePUB temporário. ePUB entra como está.

    Funil único: dali para frente só existe ePUB, e há um caminho de código só.
    AVISO ao usuário: a paginação do Kindle NÃO viaja nesta conversão — ela mora
    num sidecar .apnx, fora do arquivo. MOBI/AZW cai quase sempre em posição."""
    if entrada.suffix.lower() not in EXTENSOES_CALIBRE:
        return entrada
    destino = tmp / (entrada.stem + ".epub")
    print(f"    {entrada.suffix.lower()} → epub (ebook-convert)…")
    print("    NOTA: a paginacao do Kindle nao viaja na conversao (fica no "
          "sidecar .apnx)")
    r = subprocess.run(["ebook-convert", str(entrada), str(destino)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not destino.exists():
        cauda = (r.stderr or r.stdout).strip().splitlines()[-6:]
        _sair("o ebook-convert nao conseguiu ler o arquivo. Se foi comprado na "
              "Amazon, provavelmente tem DRM — e DRM nao se remove aqui.\n       "
              + "\n       ".join(cauda))
    return destino


def checar_drm(z: zipfile.ZipFile) -> None:
    """DRM da Adobe deixa rastro em META-INF/encryption.xml. Mensagem
    instrutiva vale mais que um traceback ou um .md de lixo."""
    try:
        bruto = z.read("META-INF/encryption.xml").decode("utf-8", "replace")
    except KeyError:
        return
    # Fonte embutida cifrada (obfuscação) é comum e INOFENSIVA; o que impede a
    # leitura é conteúdo cifrado.
    if ".xhtml" in bruto or ".html" in bruto or "OEBPS" in bruto:
        _sair("este ePUB tem DRM (META-INF/encryption.xml cobre o conteudo).\n"
              "       Use um exemplar sem DRM — o acervo nao remove protecao.")


# ── OPF: metadados, spine e o mapa de páginas ────────────────────────────────

def _limpar(s: str) -> str:
    return " ".join((s or "").split())


def abrir_opf(z: zipfile.ZipFile):
    """→ (caminho_do_opf_no_zip, bytes_do_opf). O caminho vem do container.xml:
    não se adivinha, cada editor escolhe a pasta (OEBPS/, EPUB/, raiz…)."""
    try:
        itens = coletar(z.read("META-INF/container.xml"), {"rootfile"})
    except KeyError:
        return "", b""
    for _t, d, _txt, _p in itens:
        caminho = unquote(d.get("full-path", ""))
        if caminho:
            try:
                return caminho, z.read(caminho)
            except KeyError:
                return caminho, b""
    return "", b""


def manifesto(opf_bytes: bytes, opf_path: str):
    """→ ({caminho_no_zip: href_do_manifesto}, [hrefs do nav])

    INVARIANTE: href do manifesto é relativo ao DIRETÓRIO DO OPF, nunca à raiz
    do zip. E vem percent-encoded. Errar isso é o bug clássico nº 1 de EPUB."""
    base = posixpath.dirname(opf_path)
    por_caminho, navs = {}, []
    for _t, d, _txt, _p in coletar(opf_bytes, {"item"}):
        href = unquote(d.get("href", ""))
        if not href or "://" in href:
            continue
        caminho = posixpath.normpath(posixpath.join(base, href))
        por_caminho[caminho] = href
        if "nav" in d.get("properties", ""):
            navs.append(caminho)
        if d.get("media-type", "") == "application/x-dtbncx+xml":
            navs.append(caminho)
    return por_caminho, navs


def metadados_dc(opf_bytes: bytes) -> tuple:
    """Dublin Core → (campos_da_ficha, linhas_de_evidencia).

    POR QUE TÃO POUCO VIRA CAMPO: metadado de e-book mente com frequência —
    `dc:date` costuma ser a data em que o ARQUIVO foi gerado (não o ano da
    edição), `dc:creator` vem em ordem direta ("Fulana Barreto"), que daria uma
    referência ABNT errada, e `dc:publisher` às vezes traz o nome do conversor.
    Se preenchêssemos a ficha inteira, ela pareceria pronta, o humano salvaria,
    e a `referencia_abnt` sairia do lixo — com `confiabilidade: A-conferir`, que
    ROTULA mas não bloqueia a publicação.

    Então: só `titulo`, `editora` e — apenas quando o editor forneceu a inversão
    em `file-as` — `autoria` viram CAMPO, e marcados. O resto vira LINHA DE
    COMENTÁRIO: o frontmatter.py:55 pula linha `#`, o normalizar_yaml deixa
    passar e o fatiar.py copia o bloco verbatim para a nota-índice — ou seja, a
    evidência viaja até onde o humano preenche a ficha, sem máquina agir sobre
    ela. `ano` NUNCA é preenchido de propósito: é obrigatório para todo `livro*`
    (taxonomia.py:44,48,56), então a ficha continua pendente até alguém
    conferir a edição. Isso é o laço humano funcionando, não uma limitação."""
    campos, evid = {}, []
    if not opf_bytes:
        return campos, evid

    tags = {"dc:title", "dc:creator", "dc:publisher", "dc:date",
            "dc:language", "dc:identifier", "dc:source"}
    achado = {}
    for tag, d, txt, _p in coletar(opf_bytes, tags):
        achado.setdefault(tag, (d, _limpar(txt)))

    if "dc:title" in achado:
        campos["titulo"] = achado["dc:title"][1]
    if "dc:publisher" in achado:
        campos["editora"] = achado["dc:publisher"][1]
    if "dc:creator" in achado:
        d, cru = achado["dc:creator"]
        # file-as é a inversão feita pelo PRÓPRIO editor ("Barreto, Fulana") —
        # melhor que inverter na mão e errar sobrenome composto.
        file_as = _limpar(next((v for k, v in d.items()
                                if k.endswith("file-as")), ""))
        if file_as:
            campos["autoria"] = file_as
        elif cru:
            evid.append(f"# opf_autoria_ordem_direta: {cru}   "
                        "# ABNT pede SOBRENOME, Nome — preencha `autoria`")
    for tag, rotulo in (("dc:date", "opf_data"), ("dc:source", "opf_fonte"),
                        ("dc:identifier", "opf_identificador")):
        if tag in achado and achado[tag][1]:
            evid.append(f"# {rotulo}: {achado[tag][1]}")
    if "dc:date" in achado and achado["dc:date"][1][:4].isdigit():
        evid.append(f"# ATENCAO: `ano` NAO foi preenchido de proposito — "
                    f"opf_data pode ser a data do arquivo, nao da edicao. "
                    f"Confira a edicao e preencha.")
    return campos, evid


def idioma_do_opf(opf_bytes: bytes) -> str:
    if not opf_bytes:
        return ""
    for _t, _d, txt, _p in coletar(opf_bytes, {"dc:language"}):
        return BCP47.get(_limpar(txt).lower()[:2], "")
    return ""


def mapa_de_paginas(z, opf_bytes, opf_path, por_caminho, navs):
    """→ ({chave_pandoc: rótulo}, {fragmento: rótulo}, origem)

    Duas chaves de propósito: a exata (href do manifesto + '#' + fragmento, que
    é a forma que o pandoc emite) e o fragmento sozinho, como rede de segurança
    quando a forma do caminho não bate. Fragmento de página é único na prática.

    INVARIANTE: href do page-list é relativo ao DIRETÓRIO DO NAV, não ao do OPF
    — os dois só coincidem quando o editor põe tudo na mesma pasta. É o bug
    clássico nº 2."""
    for caminho in navs:
        try:
            bruto = z.read(caminho)
        except KeyError:
            continue
        base = posixpath.dirname(caminho)
        exato, por_frag, origem = {}, {}, ""

        # EPUB3: <nav epub:type="page-list"> … <a href="x#frag">147</a>
        for tag, d, txt, pilha in coletar(bruto, {"a", "content"}):
            rot = _limpar(txt)
            if tag == "a":
                if not (_dentro_de(pilha, "nav", "type", "page-list")
                        or _dentro_de(pilha, "nav", "role", "doc-pagelist")):
                    continue
                href, origem = d.get("href", ""), "epub3-page-list"
            else:
                # EPUB2/NCX: <pageTarget><navLabel><text>147</text>
                #            <content src="x#frag"/>
                if not _dentro_de(pilha, "pagetarget"):
                    continue
                href, origem = d.get("src", ""), "ncx-page-list"
                rot = ""            # o rótulo está no <text> irmão; ver abaixo
            if not href:
                continue
            alvo = unquote(href)
            arq, _, frag = alvo.partition("#")
            zip_path = posixpath.normpath(posixpath.join(base, arq)) if arq else caminho
            manif = por_caminho.get(zip_path, arq)
            if rot and frag:
                exato[f"{manif}#{frag}"] = rot
                por_frag[frag] = rot

        if origem == "ncx-page-list":
            exato, por_frag = _ncx_pagelist(bruto, base, por_caminho, caminho)

        if exato or por_frag:
            return exato, por_frag, origem
    return {}, {}, ""


def _ncx_pagelist(bruto, base, por_caminho, caminho):
    """No NCX o rótulo e o alvo são irmãos, não pai/filho — casa-se por ordem
    dentro de cada <pageTarget>."""
    exato, por_frag = {}, {}
    itens = coletar(bruto, {"text", "content"})
    rot_pendente = ""
    for tag, d, txt, pilha in itens:
        if not _dentro_de(pilha, "pagetarget"):
            continue
        if tag == "text":
            rot_pendente = _limpar(txt)
        elif tag == "content" and rot_pendente:
            alvo = unquote(d.get("src", ""))
            arq, _, frag = alvo.partition("#")
            zip_path = (posixpath.normpath(posixpath.join(base, arq))
                        if arq else caminho)
            manif = por_caminho.get(zip_path, arq)
            if frag:
                exato[f"{manif}#{frag}"] = rot_pendente
                por_frag[frag] = rot_pendente
            rot_pendente = ""
    return exato, por_frag


def sondar(caminho: Path) -> dict:
    """Espia o e-book SEM converter. → {titulo, autoria, idioma, paginas, origem}

    Serve à triagem (etapa 1), que precisa de uma linha no controle.csv por
    arquivo e não pode pagar uma conversão inteira por livro. Lê só o ZIP: o
    OPF (metadados) e o índice de páginas. Para MOBI/AZW não abre nada — não é
    ZIP —, e devolve o que der.

    `paginas` preenchido é o sinal grátis do CASO OURO: o e-book traz a
    paginação da edição impressa e vai ser citável por página."""
    out = {"titulo": "", "autoria": "", "idioma": "", "paginas": "",
           "origem": ""}
    if caminho.suffix.lower() in EXTENSOES_CALIBRE:
        return out                      # não é ZIP; a sondagem sai vazia
    try:
        with zipfile.ZipFile(caminho) as z:
            opf_path, opf_bytes = abrir_opf(z)
            por_caminho, navs = manifesto(opf_bytes, opf_path)
            campos, _ = metadados_dc(opf_bytes)
            out["titulo"] = campos.get("titulo", "")
            out["autoria"] = campos.get("autoria", "")
            out["idioma"] = idioma_do_opf(opf_bytes)
            exato, por_frag, origem = mapa_de_paginas(
                z, opf_bytes, opf_path, por_caminho, navs)
            n = len(exato or por_frag)
            if n and origem:
                out["paginas"], out["origem"] = str(n), origem
    except (zipfile.BadZipFile, OSError, KeyError):
        pass
    return out


# ── Conversão e âncoras ──────────────────────────────────────────────────────

def converter_pandoc(epub: Path) -> str:
    r = subprocess.run(
        ["pandoc", "-f", "epub", "-t", "gfm", "--wrap=none", str(epub)],
        capture_output=True, text=True)
    if r.returncode != 0:
        _sair(f"o pandoc falhou.\n       {r.stderr.strip()[:400]}")
    return r.stdout


def _crescente(rotulos) -> bool:
    """A sequência de páginas não pode andar para trás. É o que separa
    paginação de coincidência: um id `page_3` pode ser o 3º bloco de um
    capítulo. Só se aplica a rótulos árabes — romano do prefácio vem antes e
    quebraria a comparação sem indicar erro."""
    nums = [int(r) for r in rotulos if r.isdigit()]
    return all(b >= a for a, b in zip(nums, nums[1:]))


def marcar(kind: str, rot, ancora: str) -> str:
    return (f"{{{{{kind}.{rot}}}}}" if ancora == "chaves"
            else f"<!-- {kind}.{rot} -->")


def resolver_ancoras(md: str, exato: dict, por_frag: dict, origem: str,
                     ancora: str):
    """Troca os <span> do pandoc por âncoras de página.
    → (md, rotulos, origem_usada, n_indice, n_casadas)

    Span que não é página (fronteira de capítulo, nota) é REMOVIDO — deixá-lo
    faria `<span id="cap1.xhtml">` aparecer como lixo literal no Obsidian.

    A âncora herda a POSIÇÃO do span: sozinho na linha, vira linha própria (e
    ponto de corte para o fatiar.py); no meio do parágrafo, fica INLINE. Cortar
    a frase do autor no meio seria pior que perder um ponto de corte — e
    "empurrar a âncora para o início do parágrafo" seria pior ainda: deslocaria
    a fronteira e faria citar a p. 147 um trecho que está na 148."""
    rotulos, usada = [], origem
    candidatos, casadas = [], 0

    for m in SPAN.finditer(md):
        attrs = dict(ATRIBUTO.findall(m.group(1)))
        ident = attrs.get("id", "")
        frag = ident.split("#")[-1]
        rot, fonte = "", ""
        if ident in exato:
            rot, fonte = exato[ident], origem
            casadas += 1
        elif frag and frag in por_frag:
            rot, fonte = por_frag[frag], origem
            casadas += 1
        elif not exato and not por_frag:
            # Sem índice: varredura do marcador solto. É INFERÊNCIA.
            tipo = " ".join(v for k, v in attrs.items()
                            if k.endswith("type") or k == "class")
            if "pagebreak" in tipo:
                rot = _limpar(attrs.get("title") or attrs.get("aria-label") or "")
                fonte = "pagebreak-scan"
            if not rot:
                achou = ID_COM_PAGINA.search(frag)
                if achou:
                    rot, fonte = achou.group(1), "pagebreak-scan"
        candidatos.append((m, rot, fonte))

    achados = [r for _, r, _ in candidatos if r]

    # TRAVA DE RÓTULO: só o que taxonomia.ANCORA_PAG sabe ler. Meio-caminho
    # aqui geraria âncora que o validador não vê.
    ruins = [r for r in achados if not ROTULO_OK.match(r)]
    if ruins:
        print(f"    AVISO: rotulo de pagina fora do padrao (ex.: {ruins[:3]})")
        print("           -> paginacao descartada; usando posicao.")
        return SPAN.sub("", md), [], "", len(exato or por_frag), 0

    if achados and not _crescente(achados):
        print("    AVISO: os rotulos de pagina nao formam sequencia crescente")
        print("           -> nao sao paginacao; usando posicao.")
        return SPAN.sub("", md), [], "", len(exato or por_frag), 0

    if not achados:
        return SPAN.sub("", md), [], "", len(exato or por_frag), 0

    if not usada:
        usada = "pagebreak-scan"

    partes, fim = [], 0
    for m, rot, _f in candidatos:
        partes.append(md[fim:m.start()])
        if rot:
            rotulos.append(rot.lower())
            antes_vazio = md[:m.start()].rsplit("\n", 1)[-1].strip() == ""
            depois_vazio = md[m.end():].split("\n", 1)[0].strip() == ""
            partes.append(marcar("p", rot, ancora) if antes_vazio and depois_vazio
                          else f" {marcar('p', rot, ancora)} ")
        fim = m.end()
    partes.append(md[fim:])
    return "".join(partes), rotulos, usada, len(exato or por_frag), casadas


def inserir_posicoes(md: str, passo: int, ancora: str):
    """Sem página: sintetiza {{loc.N}} ORDINAL a cada `passo` caracteres.

    ORDINAL, não offset: se N fosse o offset (loc.1500, loc.3000), o
    auditar_acervo.py:107-113 calcularia range(min, max+1) e reportaria
    "lacunas na sequência (1.499 pág.)" para cada intervalo — alarme falso
    permanente.

    Insere só em FRONTEIRA DE PARÁGRAFO (nunca no meio de uma frase) e nunca
    dentro de bloco de código — âncora em bloco de código é o erro que o
    auditar_acervo.py:115 persegue. → (md, rotulos)"""
    blocos = md.split("\n\n")
    saida, rotulos, acumulado, n, cerca = [], [], 0, 0, False

    for bloco in blocos:
        for linha in bloco.split("\n"):
            if CERCA.match(linha):
                cerca = not cerca
        if not cerca and (n == 0 or acumulado >= passo):
            n += 1
            saida.append(marcar("loc", n, ancora))
            rotulos.append(str(n))
            acumulado = 0
        saida.append(bloco)
        acumulado += len(bloco)
    return "\n\n".join(saida), rotulos


def limpar_sobras(md: str):
    """Remove imagens e spans que não eram página; normaliza espaçamento.
    → (md, n_imagens)

    Imagem é DESCARTADA nesta versão: o publicar.py só carrega .md, então
    extrair mídia deixaria link quebrado no vault — pior que uma omissão
    declarada. A contagem vai para `imagens_descartadas` e para o log, para a
    perda ser auditável e recuperável depois."""
    md, n_img = IMAGEM.subn("", md)
    md = SPAN.sub("", md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"[ \t]{2,}", " ", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip(), n_img


# ── Idioma ───────────────────────────────────────────────────────────────────

def detectar_idioma(texto: str, tmp: Path, dica_opf: str) -> str:
    """Detector sobre o TEXTO como primário; dc:language só como desempate.

    Ordem deliberada, contrária à intuição: o incidente do corrigir_idioma.py:8-14
    (livro italiano catalogado como português) veio de AMOSTRA ruim, não de
    detector ruim — e aqui a amostra é ideal: o miolo inteiro, limpo, sem OCR.
    Já `dc:language` de e-book convertido/pirata é `en` por default de
    ferramenta: é metadado que mente. Delega ao detectar_idioma.py para não
    criar a 5ª cópia divergente da heurística."""
    det = Path(__file__).resolve().parent / "detectar_idioma.py"
    if det.exists() and texto.strip():
        amostra = tmp / "amostra.txt"
        amostra.write_text(texto[:200_000], encoding="utf-8")
        try:
            r = subprocess.run(["python3", str(det), str(amostra), "--codigo"],
                               capture_output=True, text=True, timeout=90)
            cod = (r.stdout or "").strip().split("+")[0]
            if cod in taxonomia.IDIOMAS:
                return cod
        except (subprocess.SubprocessError, OSError):
            pass
    return dica_opf


# ── Ficha ────────────────────────────────────────────────────────────────────

def escolher_tipo_fonte(palpite: str, tem_pagina: bool) -> str:
    """O tipo_fonte definitivo, sem inventar.

    Regra de humildade (a do triagem.py:14-16 — sem fallback cego): só assumimos
    e-book quando a triagem não soube ou disse "livro". Se ela disse
    `legislacao`, viu algo no nome/conteúdo que a extensão não contradiz.

    E o caso com página NÃO pode ser `livro_ebook_leitor`: a taxonomia amarra
    esse tipo ao localizador `posicao`, e auditar_acervo.py:215-222 /
    validar_yaml_abnt.py:228-237 reprovam a incoerência. Página real → tipo de
    página. É cinto e suspensório: o corpo e a ficha têm de contar a mesma
    história."""
    palpite = (palpite or "").strip()
    if tem_pagina:
        return "livro" if palpite in ("", "livro_ebook_leitor") else palpite
    if not palpite or palpite.startswith("livro"):
        return "livro_ebook_leitor"
    return palpite


def montar_frontmatter(origem: Path, tf, idioma, campos, evid, ancora,
                       tem_pagina, paginacao_origem, n_ancoras, passo,
                       n_img) -> str:
    """A ficha. Espelha injetar_paginas.py:153-166 — mesmas chaves, mesma ordem,
    mesmos marcadores REVISE — para as duas rotas serem indistinguíveis daqui
    para a frente."""
    L = ["---",
         frontmatter.emitir("origem_arquivo", origem.name),
         f"formato: {origem.suffix.lower().lstrip('.')}",
         "motor_conversao: pandoc",
         f"paginacao: {'true' if tem_pagina else 'false'}",
         frontmatter.emitir("paginacao_origem", paginacao_origem)]
    if tem_pagina:
        L.append(f"paginas_total: {n_ancoras}")
        if paginacao_origem == "pagebreak-scan":
            L.append("# ATENCAO: pagina INFERIDA do marcador solto, sem indice "
                     "de paginas do editor — confira contra a edicao impressa.")
    else:
        L += [f"posicoes_total: {n_ancoras}",
              f"posicao_passo: {passo}",
              f"# posicao_passo: {passo} caracteres. Escala DESTE acervo — NAO e "
              "a location do Kindle nem a pagina impressa.",
              "# Reconverter com o mesmo passo reproduz as mesmas ancoras."]
    L.append(frontmatter.emitir("ancora", ancora))
    if n_img:
        L.append(f"imagens_descartadas: {n_img}")

    for campo in ("autoria", "titulo", "editora"):
        if campos.get(campo):
            L.append(frontmatter.emitir(campo, campos[campo])
                     + "   # do EPUB (OPF) — CONFIRA")
    L += evid

    if idioma in taxonomia.IDIOMAS:
        L += [f"idioma: {idioma}",
              frontmatter.emitir("idioma_nome", taxonomia.IDIOMAS[idioma]),
              "traducao: original",
              f'# ATENCAO: obra em {taxonomia.IDIOMAS[idioma]} — NAO traduzir '
              'nem "corrigir" o texto.',
              f"# Edicao segue a lingua do documento: "
              f"{taxonomia.IDIOMA_EDICAO[idioma]}"]

    if tf:
        L.append(f"tipo_fonte: {tf}                 # palpite — REVISE")
        tp = taxonomia.tipo_unico_de(tf)
        if tp:
            L.append(f"tipo: {tp}                 # derivado do tipo_fonte — REVISE")
        regra = taxonomia.TIPOS_FONTE.get(tf)
        loc_tipo, loc_ab = regra.localizador if regra else (None, None)
        if loc_tipo is not None:
            L.append(f"localizador_tipo: {loc_tipo}")
            L.append(frontmatter.emitir("localizador_abrev", loc_ab))
        elif regra is None:
            L.append("# tipo_fonte desconhecido pela taxonomia — localizador "
                     "NAO inferido; defina manualmente")
        L += ["sistema_chamada: ambos",
              frontmatter.emitir("norma_citacao", "NBR 10520:2023")]
        if regra is not None and regra.aviso:
            L.append(f"# {regra.aviso}")

    L += ["confiabilidade: A-conferir", "---", "",
          f"<!-- Gerado por converter_ebook.py a partir de {origem.name}.",
          "     As âncoras de citação são OBRIGATÓRIAS (NBR 10520:2023).",
          "     NÃO as remova nem renumere. -->", ""]
    return "\n".join(L) + "\n"


# ── Programa ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="E-book (ePUB/MOBI/AZW3/AZW) -> Markdown com âncoras de "
                    "citação. Página real quando o editor a registrou; "
                    "posição quando não há.")
    ap.add_argument("ebook", help="arquivo .epub, .mobi, .azw3 ou .azw")
    ap.add_argument("-o", "--saida", help="arquivo .md de saída")
    ap.add_argument("--ancora", choices=["chaves", "comentario"],
                    default="chaves", help="formato da âncora (padrão: chaves)")
    ap.add_argument("--posicao-passo", type=int, default=1500,
                    help="caracteres por {{loc.N}} quando não há página "
                         "(padrão: 1500, ~1 página impressa)")
    ap.add_argument("--tipo-fonte", default="",
                    help="pré-preenche tipo_fonte (palpite da triagem). "
                         "SEMPRE revise.")
    ap.add_argument("--idioma", default="",
                    help="idioma da obra; se omitido, detecta no texto")
    ap.add_argument("--cobertura-min", type=float, default=0.9,
                    help="fração mínima do índice de páginas que precisa casar "
                         "com o texto (padrão: 0.9); abaixo disso, posição")
    args = ap.parse_args()

    entrada = Path(args.ebook)
    if not entrada.exists():
        _sair(f"não encontrei {entrada}")
    if entrada.suffix.lower() in (".kfx", ".azw8"):
        _sair("formato KFX/AZW8 (Kindle novo) — o Calibre não converte sem "
              "plugin externo. Exporte em ePUB ou use o PDF.")
    checar_ferramentas(entrada.suffix.lower() in EXTENSOES_CALIBRE)
    saida = Path(args.saida) if args.saida else entrada.with_suffix(".md")

    with tempfile.TemporaryDirectory(prefix="acervo-ebook-") as td:
        tmp = Path(td)
        epub = para_epub(entrada, tmp)
        try:
            with zipfile.ZipFile(epub) as z:
                checar_drm(z)
                opf_path, opf_bytes = abrir_opf(z)
                por_caminho, navs = manifesto(opf_bytes, opf_path)
                exato, por_frag, origem = mapa_de_paginas(
                    z, opf_bytes, opf_path, por_caminho, navs)
                campos, evid = metadados_dc(opf_bytes)
                idi_opf = idioma_do_opf(opf_bytes)
        except (zipfile.BadZipFile, OSError):
            _sair(f"{entrada.name} não é um ePUB legível (ZIP inválido).")

        corpo = converter_pandoc(epub)
        corpo, rotulos, usada, n_indice, n_casadas = resolver_ancoras(
            corpo, exato, por_frag, origem, args.ancora)

        # TRAVA DE COBERTURA: índice que só casa no começo produz um documento
        # que PARECE paginado e mente a partir da metade.
        if rotulos and n_indice:
            cobertura = n_casadas / n_indice
            if cobertura < args.cobertura_min:
                print(f"    AVISO: so {cobertura:.0%} do indice de paginas "
                      f"({n_casadas}/{n_indice}) casou com o texto")
                print("           -> paginacao parcial e enganosa; usando posicao.")
                corpo = re.sub(r"\s*\{\{p\.[0-9ivxlcdm]+\}\}\s*", " ", corpo)
                corpo = re.sub(r"\s*<!--\s*p\.[0-9ivxlcdm]+\s*-->\s*", " ", corpo)
                rotulos, usada = [], ""

        tem_pagina = bool(rotulos)
        if not tem_pagina:
            corpo, rotulos = inserir_posicoes(corpo, args.posicao_passo,
                                              args.ancora)
            usada = "posicao"
        corpo, n_img = limpar_sobras(corpo)

        if len(corpo) < 200:
            _sair("o e-book não rendeu texto (menos de 200 caracteres).\n"
                  "       Provavelmente é digitalização em imagem (mangá, scan) "
                  "— nesse caso\n       exporte em PDF e use a rota de OCR "
                  "(etapa 2).")

        idioma = ((args.idioma or "").strip().split("+")[0]
                  or detectar_idioma(corpo, tmp, idi_opf))

    # TRAVA DE CONTAGEM: a âncora é o produto. Se não sobreviveu à limpeza, não
    # gravamos nada — a mesma recusa de limpar_ocr.py:161-165 e fatiar.py:208.
    esperado = "p" if tem_pagina else "loc"
    padrao = (r"\{\{(p|loc)\.[0-9ivxlcdm]+\}\}" if args.ancora == "chaves"
              else r"<!--\s*(p|loc)\.[0-9ivxlcdm]+\s*-->")
    achadas = re.findall(padrao, corpo)
    if len(achadas) != len(rotulos) or any(k != esperado for k in achadas):
        _sair(f"contagem de âncoras não fecha ({len(achadas)} no texto × "
              f"{len(rotulos)} previstas). Nada foi gravado.")
    if re.search(r"```[^`]*\{\{(?:p|loc)\.", corpo, re.DOTALL):
        _sair("uma âncora caiu dentro de bloco de código. Nada foi gravado.")

    tf = escolher_tipo_fonte(args.tipo_fonte, tem_pagina)
    cabecalho = montar_frontmatter(entrada, tf, idioma, campos, evid,
                                   args.ancora, tem_pagina, usada,
                                   len(rotulos), args.posicao_passo, n_img)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(cabecalho + corpo + "\n", encoding="utf-8")

    if tem_pagina:
        print(f"OK  {saida}  ({len(rotulos)} páginas — {usada})")
        print(f"    citável por página: p.{rotulos[0]} … p.{rotulos[-1]}")
    else:
        print(f"OK  {saida}  ({len(rotulos)} posições)")
        print("    AVISO: este e-book não traz a paginação da edição impressa.")
        print(f"           A citação sai por POSIÇÃO (local. N), 1 local. = "
              f"{args.posicao_passo} caracteres —")
        print("           escala DESTE acervo, não a do Kindle. Para citar em "
              "peça, prefira a edição paginada.")
    if args.tipo_fonte and tf != args.tipo_fonte.strip():
        print(f"    tipo_fonte ajustado: {args.tipo_fonte.strip()} → {tf} "
              f"(coerência com o localizador)")
    if campos or evid:
        print(f"    ficha do e-book: {', '.join(sorted(campos)) or '—'} "
              f"(+{len(evid)} linha(s) de evidência) — CONFIRA; `ano` fica "
              f"em branco de propósito")
    if n_img:
        print(f"    {n_img} imagem(ns) descartada(s) (mídia ainda não vai para "
              f"o vault).")
    if not idioma:
        print("    AVISO: idioma indeterminado — preencha à mão.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
gerar_fixtures.py — cria os e-books de teste do corpus (EPUB2 e EPUB3).

Por que este script existe
--------------------------
O corpus de `corpus/*.md` é texto: dá para ler o fixture no diff e entender o
que ele testa. E-book é ZIP binário — commitar só o .epub esconderia justamente
o detalhe que importa (onde está o `pagebreak`, o que o `page-list` mapeia).
Este gerador é a versão legível do fixture; os .epub ao lado são o produto.

Os quatro casos cobrem a HIERARQUIA DE EVIDÊNCIA de página do
converter_ebook.py — do mais forte ao mais fraco, porque "tem paginação" não é
sim/não: depende de quanto o editor registrou.

  01_com_pagelist.epub          <nav epub:type="page-list"> mapeando href→rótulo.
                                Evidência MAIS FORTE: é o índice de páginas que
                                o editor publicou.  → {{p.N}}
  02_pagebreak_sem_pagelist.epub  Marcadores <span epub:type="pagebreak"
                                title="147"> sem page-list. O próprio marcador
                                declara a página impressa — evidência forte, só
                                sem índice.  → {{p.N}}
  03_epub2_anchors.epub         EPUB2 (NCX): <a id="page_147"/> sem type nem
                                title. O número está no id; aceitá-lo é uma
                                INFERÊNCIA, registrada como tal na proveniência
                                (`pagina_fonte`).  → {{p.N}}, com ressalva
  04_sem_paginacao.epub         Nenhum marcador. É o caso comum do ePUB de
                                varejo e o ÚNICO possível para MOBI/AZW.
                                → {{loc.N}} (posição)

Uso:
    python3 corpus/ebook/gerar_fixtures.py
"""

import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent

CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

# Texto jurídico plausível — o fixture precisa parecer com o acervo real para
# que a triagem e a auditoria se comportem como se comportariam em produção.
CAP1 = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Capítulo 1</title></head>
<body>
  <h1>Do Fato Gerador</h1>
  {ANC_147}
  <p>O fato gerador da obrigação tributária principal é a situação definida em
  lei como necessária e suficiente à sua ocorrência, nos termos do art. 114 do
  Código Tributário Nacional.</p>
  <p>A doutrina distingue o fato gerador <em>abstrato</em> — a hipótese de
  incidência — do fato gerador <strong>concreto</strong>, que é o evento
  verificado no mundo dos fatos.</p>
  {ANC_148}
  <h2>Elementos da hipótese de incidência</h2>
  <ul>
    <li>aspecto material;</li>
    <li>aspecto temporal;</li>
    <li>aspecto espacial.</li>
  </ul>
  <blockquote><p>Não há tributo sem lei anterior que o defina.</p></blockquote>
</body>
</html>
"""

CAP2 = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Capítulo 2</title></head>
<body>
  <h1>Da Obrigação Tributária</h1>
  {ANC_149}
  <p>A obrigação tributária é principal ou acessória. A principal surge com a
  ocorrência do fato gerador e tem por objeto o pagamento de tributo ou
  penalidade pecuniária.</p>
  <table>
    <tr><th>Espécie</th><th>Objeto</th></tr>
    <tr><td>Principal</td><td>pagamento</td></tr>
    <tr><td>Acessória</td><td>fazer ou não fazer</td></tr>
  </table>
  {ANC_150}
  <h2>Sujeição passiva</h2>
  <p>Sujeito passivo da obrigação principal é a pessoa obrigada ao pagamento;
  responde por ela o contribuinte ou o responsável.</p>
</body>
</html>
"""

# ── EPUB3: pagebreak semântico, o que o padrão manda desde 2011 ──────────────
PAGEBREAK3 = ('<span epub:type="pagebreak" id="page{n}" title="{n}"></span>')
# ── EPUB2: não havia epub:type; a prática era uma âncora vazia ───────────────
PAGEBREAK2 = '<a id="page_{n}"></a>'

NAV_COM_PAGELIST = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Sumário</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <ol>
      <li><a href="cap1.xhtml">Do Fato Gerador</a></li>
      <li><a href="cap2.xhtml">Da Obrigação Tributária</a></li>
    </ol>
  </nav>
  <nav epub:type="page-list" id="page-list">
    <ol>
      <li><a href="cap1.xhtml#page147">147</a></li>
      <li><a href="cap1.xhtml#page148">148</a></li>
      <li><a href="cap2.xhtml#page149">149</a></li>
      <li><a href="cap2.xhtml#page150">150</a></li>
    </ol>
  </nav>
</body>
</html>
"""

NAV_SEM_PAGELIST = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Sumário</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <ol>
      <li><a href="cap1.xhtml">Do Fato Gerador</a></li>
      <li><a href="cap2.xhtml">Da Obrigação Tributária</a></li>
    </ol>
  </nav>
</body>
</html>
"""

NCX = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head><meta name="dtb:uid" content="urn:isbn:9788502123456"/></head>
  <docTitle><text>Curso de Direito Tributário</text></docTitle>
  <navMap>
    <navPoint id="n1" playOrder="1">
      <navLabel><text>Do Fato Gerador</text></navLabel>
      <content src="cap1.xhtml"/>
    </navPoint>
    <navPoint id="n2" playOrder="2">
      <navLabel><text>Da Obrigação Tributária</text></navLabel>
      <content src="cap2.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
"""


def opf(versao: str, com_nav: bool) -> str:
    """O OPF é de onde o converter_ebook.py tira a ficha ABNT — por isso o
    fixture carrega metadados completos e plausíveis (autoria, editora, ano,
    ISBN, idioma), não placeholders."""
    if versao == "3.0":
        manifesto = (
            '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
            'properties="nav"/>\n')
        spine = '  <spine>\n'
    else:
        manifesto = ('    <item id="ncx" href="toc.ncx" '
                     'media-type="application/x-dtbncx+xml"/>\n')
        spine = '  <spine toc="ncx">\n'
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="{versao}"
         unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="pub-id">urn:isbn:9788502123456</dc:identifier>
    <dc:title>Curso de Direito Tributário</dc:title>
    <dc:creator opf:role="aut" opf:file-as="Barreto, Fulana de Tal">Fulana de Tal Barreto</dc:creator>
    <dc:publisher>Editora Jurídica Exemplo</dc:publisher>
    <dc:date>2023-03-15</dc:date>
    <dc:language>pt-BR</dc:language>
    <dc:source>Edição impressa, 12. ed., São Paulo</dc:source>
  </metadata>
  <manifest>
{manifesto}    <item id="c1" href="cap1.xhtml" media-type="application/xhtml+xml"/>
    <item id="c2" href="cap2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
{spine}    <itemref idref="c1"/>
    <itemref idref="c2"/>
  </spine>
</package>
"""


def escrever_epub(destino: Path, arquivos: dict) -> None:
    """Grava o EPUB. O `mimetype` PRECISA ser a primeira entrada e ficar SEM
    compressão — é assim que um leitor identifica o formato sem descompactar.
    Errar isso gera um arquivo que abre em alguns leitores e falha em outros."""
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                   compress_type=zipfile.ZIP_STORED)
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)


def montar(nome: str, versao: str, pagebreak: str, nav: str) -> Path:
    """pagebreak='' gera o livro sem marcador de página nenhum."""
    def anc(n):
        return pagebreak.format(n=n) if pagebreak else ""

    arquivos = {
        "META-INF/container.xml": CONTAINER,
        "OEBPS/content.opf": opf(versao, versao == "3.0"),
        "OEBPS/cap1.xhtml": CAP1.format(ANC_147=anc(147), ANC_148=anc(148)),
        "OEBPS/cap2.xhtml": CAP2.format(ANC_149=anc(149), ANC_150=anc(150)),
    }
    if versao == "3.0":
        arquivos["OEBPS/nav.xhtml"] = nav
    else:
        arquivos["OEBPS/toc.ncx"] = NCX

    destino = AQUI / nome
    escrever_epub(destino, arquivos)
    return destino


def main():
    casos = [
        # (nome, versão, marcador de página, nav)
        ("01_com_pagelist.epub", "3.0", PAGEBREAK3, NAV_COM_PAGELIST),
        ("02_pagebreak_sem_pagelist.epub", "3.0", PAGEBREAK3, NAV_SEM_PAGELIST),
        ("03_epub2_anchors.epub", "2.0", PAGEBREAK2, ""),
        ("04_sem_paginacao.epub", "3.0", "", NAV_SEM_PAGELIST),
    ]
    for nome, versao, pb, nav in casos:
        p = montar(nome, versao, pb, nav)
        print(f"OK  {p.relative_to(AQUI.parent.parent)}  ({p.stat().st_size} bytes)")
    print("\nDICA: confira com  python3 -c \"import zipfile,sys; "
          "print(zipfile.ZipFile(sys.argv[1]).namelist())\" <arquivo.epub>")


if __name__ == "__main__":
    main()

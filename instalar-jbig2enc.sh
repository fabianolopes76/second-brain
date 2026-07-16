#!/usr/bin/env bash
# ============================================================
#  instalar-jbig2enc.sh — instala o compressor JBIG2 do ocrmypdf.
#
#  Por que existe: o --optimize 3 (padrao do pipeline) recomenda o
#  jbig2enc; sem ele o PDF sai valido, porem MAIOR. No Ubuntu ate a
#  versao 22.04 NAO ha pacote apt ("Unable to locate package
#  jbig2enc") — a fonte oficial e github.com/agl/jbig2enc.
#
#  Uso:  bash instalar-jbig2enc.sh      (pede a senha do sudo)
# ============================================================
set -euo pipefail

if command -v jbig2 >/dev/null 2>&1; then
    echo "jbig2enc ja instalado: $(command -v jbig2)"
    exit 0
fi

# Ubuntu 23.04+ / Debian 12+ tem pacote pronto — caminho rapido.
if apt-cache policy jbig2enc 2>/dev/null | grep -q 'Candidate: [0-9]'; then
    echo ">> pacote apt disponivel — instalando"
    sudo apt-get install -y jbig2enc
    jbig2 --version 2>&1 | head -1
    echo "jbig2enc instalado com sucesso."
    exit 0
fi

echo ">> sem pacote apt nesta versao do Ubuntu — compilando da fonte oficial"
echo ">> 1/4 dependencias de compilacao (sudo)"
sudo apt-get update
sudo apt-get install -y build-essential automake libtool libleptonica-dev zlib1g-dev git

echo ">> 2/4 baixando github.com/agl/jbig2enc"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
git clone --depth 1 https://github.com/agl/jbig2enc "$tmp/jbig2enc"

echo ">> 3/4 compilando"
cd "$tmp/jbig2enc"
./autogen.sh
./configure
make -j"$(nproc)"

echo ">> 4/4 instalando em /usr/local (sudo)"
sudo make install
sudo ldconfig

echo
jbig2 --version 2>&1 | head -1
echo "jbig2enc instalado com sucesso — o proximo OCR ja sai com a compressao ligada."

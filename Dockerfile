FROM continuumio/miniconda3:4.3.27p0

# Install mercurial texlive-latex-base (pdflatex)
RUN apt-get update && apt-get install mercurial texlive-latex-base xzdec --no-install-recommends -y && rm -rf /var/lib/apt/lists/*

# Install some texlive packages we need
RUN tlmgr init-usertree && \
    tlmgr option repository ftp://tug.org/historic/systems/texlive/2015/tlnet-final && \
    tlmgr update --self && \
    tlmgr install titlesec background everypage lastpage xkeyval pgf ms xcolor wallpaper eso-pic adjustbox collectbox

# Configure Python to use UTF8 by default
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Create application code workdir
RUN set -ex && mkdir /app
WORKDIR /app

# Install conda-build and anaconda-client
COPY .ci/packages.conda /app/.ci/packages.conda
RUN set -ex && conda install --file .ci/packages.conda --yes && conda install gxx_linux-64 --yes

# Install pipenv
RUN set -ex && pip install pipenv --upgrade --ignore-installed

# Install application code
COPY factors /app

# Create python environment
RUN set -ex && pipenv install --dev

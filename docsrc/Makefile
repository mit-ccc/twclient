# # Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXAPIDOC  = sphinx-apidoc
SPHINXPROJ    = twclient
SOURCEDIR     = .
BUILDDIR      = _build
CODEDIR       = ../src/twclient/
CODEEXCLUDES  = ../src/twclient/command.py

.PHONY: all github html apidoc help Makefile

all: github

github: html
	cp -a _build/html/. ../docs

html: apidoc
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/html

apidoc:
	$(SPHINXAPIDOC) -f -o api/ $(CODEDIR) $(CODEEXCLUDES)

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Catch-all target: route every other target to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)


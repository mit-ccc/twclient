# # Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = twclient
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: all github html apidoc clean help Makefile

all: github

github: html
	@ cp -a _build/html/. ../docs

html: apidoc
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html

apidoc:
	sphinx-apidoc -f -o api/ ../src/twclient/ ../src/twclient/command.py

clean:
	-rm -rf $(BUILDDIR)/*

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)


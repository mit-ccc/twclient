# # Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = python3 -m sphinx.cmd.build
SPHINXPROJ    = twclient
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: Makefile

# Catch-all target: route every other target to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)


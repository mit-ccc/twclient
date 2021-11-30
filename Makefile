ENVPATH := .env
PYTHON  := python3

.PHONY: lint tests check doc devsetup clean

## For use locally or in CI ##

lint:
	pylint src test
	# mypy src test

tests:
	coverage run -m tox

check: lint tests

doc:
	cd docsrc && $(MAKE)

## Local dev use only, not used in CI ##

devsetup:
	# for local multi-python testing with tox; assumes pyenv already installed
	pyenv install -s 3.8.12
	pyenv install -s 3.9.7
	pyenv install -s 3.10.0
	pyenv local 3.8.12 3.9.7 3.10.0
	
	rm -rf $(ENVPATH)
	$(PYTHON) -m venv $(ENVPATH)
	
	$(ENVPATH)/bin/pip install -U pip
	$(ENVPATH)/bin/pip install -e .[test,dev,docs]

clean:
	rm -rf build/ dist/ twclient.egg-info/ env/
	find . -name '__pycache__' -exec rm -rf {} \+
	find . -name '*.pyc' -exec rm -f {} \+
	find . -name '*.pyo' -exec rm -f {} \+
	find . -name '*.egg-info' -exec rm -rf {} \+  # directories
	find . -name '*~'    -exec rm -f {} \+
	
	cd docsrc && $(MAKE) clean


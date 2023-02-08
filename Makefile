ENVPATH := .env

.PHONY: lint tests doc clean devsetup

lint:
	pylint src test
	# mypy src test

tests:
	tox

doc:
	cd docs && $(MAKE) html

## Local dev use only, not used in CI ##

clean:
	rm -rf build/ dist/ twclient.egg-info/ env/
	find . -name '__pycache__' -exec rm -rf {} \+
	find . -name '*.pyc' -exec rm -f {} \+
	find . -name '*.pyo' -exec rm -f {} \+
	find . -name '*.egg-info' -exec rm -rf {} \+  # directories
	find . -name '*~'    -exec rm -f {} \+
	
	cd docs && $(MAKE) clean

devsetup:
	# for local multi-python testing with tox; assumes pyenv already installed
	pyenv install -s 3.7.12
	pyenv install -s 3.8.12
	pyenv install -s 3.9.7
	pyenv install -s 3.10.0
	pyenv install -s 3.11.1
	pyenv local 3.7.12 3.8.12 3.9.7 3.10.0 3.11.1
	
	rm -rf $(ENVPATH)
	python3 -m venv $(ENVPATH)
	
	$(ENVPATH)/bin/pip install -U pip build wheel twine
	$(ENVPATH)/bin/pip install -e .[dev]

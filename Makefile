ENVPATH := env
PYTHON  := python3

.PHONY: clean lint docs pyenv

lint:
	# stop the build if there are Python syntax errors or undefined names
	flake8 src test --count --select=E9,F63,F7,F82 --show-source --statistics
	
	# exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
	flake8 src test --count --exit-zero --max-line-length=127 --statistics
	
	pylint src test
	
	# mypy src test

docs:
	rm -rf docs/source/
	sphinx-apidoc -f -o docs/source/ src/twclient/ src/twclient/command.py
	cd docs && $(MAKE) html man

## Local dev only, not used in CI ##

env:
	$(PYTHON) -m venv $(ENVPATH)
	
	$(ENVPATH)/bin/pip install -U pip
	$(ENVPATH)/bin/pip install -e .
	$(ENVPATH)/bin/pip install .[docs] .[test] .[dev]

pyenv:
	# for local multi-python testing with tox; assumes pyenv already installed
	pyenv install -s 3.10.0
	pyenv install -s 3.6.8
	pyenv install -s 3.7.12
	pyenv install -s 3.8.12
	pyenv install -s 3.9.7
	pyenv local 3.6.8 3.7.12 3.8.12 3.9.7 3.10.0

clean:
	rm -rf build/ dist/ twclient.egg-info/ docs/_build/ env/
	find . -name '__pycache__' -exec rm -rf {} \+
	find . -name '*.pyc' -exec rm -f {} \+
	find . -name '*.pyo' -exec rm -f {} \+
	find . -name '*~'    -exec rm -f {} \+


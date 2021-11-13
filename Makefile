ENVPATH := env
PYTHON  := python3

.PHONY: clean lint docs pyenv

env:
	$(PYTHON) -m venv $(ENVPATH)
	
	$(ENVPATH)/bin/pip install --upgrade pip setuptools wheel
	
	$(ENVPATH)/bin/pip install .[docs]
	$(ENVPATH)/bin/pip install .[test]
	
	$(ENVPATH)/bin/pip install pylint flake8 mypy
	$(ENVPATH)/bin/pip install psycopg2 mysql-connector-python
	$(ENVPATH)/bin/pip install tox-pyenv tox-travis
	
	$(ENVPATH)/bin/pip install -e .

pyenv:
	# for multi-python testing with tox; assumes pyenv is already installed
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

lint:
	pylint src/
	flake8 src/
	# mypy src/

docs:
	rm -rf docs/source/
	sphinx-apidoc -f -o docs/source/ src/twclient/ src/twclient/command.py
	cd docs && $(MAKE) html man


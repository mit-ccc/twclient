ENVPATH := env
PYTHON  := python3

.PHONY: clean lint docs env

clean:
	rm -rf build/ dist/ twclient.egg-info/ docs/_build/
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
	sphinx-apidoc -o docs/source/ src/twclient/
	cd docs && $(MAKE) html man

env:
	rm -rf $(ENVPATH)
	$(PYTHON) -m venv $(ENVPATH)
	$(ENVPATH)/bin/pip install --upgrade pip setuptools wheel
	$(ENVPATH)/bin/pip install pylint flake8 mypy
	$(ENVPATH)/bin/pip install psycopg2 mysql-connector-python
	$(ENVPATH)/bin/pip install .[test]
	$(ENVPATH)/bin/pip install .[docs]
	$(ENVPATH)/bin/pip install -e .


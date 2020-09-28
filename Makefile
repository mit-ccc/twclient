ENVPATH := env
PYTHON  := python3

.PHONY: test test-all upload register env lint clean docs

test:
	py.test tests

alltest:
	tox

upload:
	$(PYTHON) setup.py sdist bdist_wheel upload

register:
	$(PYTHON) setup.py register

env:
	rm -rf $(ENVPATH)
	$(PYTHON) -m venv $(ENVPATH)
	$(ENVPATH)/bin/pip install --upgrade pip setuptools wheel
	$(ENVPATH)/bin/pip install pylint flake8 mypy
	$(ENVPATH)/bin/pip install psycopg2 mysql-connector-python
	$(ENVPATH)/bin/pip install .[test]
	$(ENVPATH)/bin/pip install -e .

lint:
	pylint twclient/
	flake8 twclient/
	# mypy twclient/

clean:
	rm -rf build/ dist/ twclient.egg-info/ docs/_build/
	find . -name '__pycache__' -exec rm -rf {} \+
	find . -name '*.pyc' -exec rm -f {} \+
	find . -name '*.pyo' -exec rm -f {} \+
	find . -name '*~'    -exec rm -f {} \+

docs:
	rm -rf docs/source/
	sphinx-apidoc -o docs/source/ twclient/ twclient/command.py
	cd docs && $(MAKE) html man


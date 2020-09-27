ENVPATH := env/
PYTHON  := python3
PIP     := pip3

.PHONY: env list clean docs

env:
	$(PYTHON) -m venv env
	source env/bin/activate && $(PIP) install -q pylint flake8 mypy -e .

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


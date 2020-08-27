.PHONY: install clean clean-pyc clean-build

install:
	python setup.py install

clean: clean-pyc clean-build

clean-pyc:
	find . -name '__pycache__' -exec rm -rf {} \+
	find . -name '*.pyc' -exec rm --force {} \+
	find . -name '*.pyo' -exec rm --force {} \+
	find . -name '*~'    -exec rm --force {} \+

clean-build:
	rm --force --recursive build/
	rm --force --recursive dist/
	rm --force --recursive *.egg-info


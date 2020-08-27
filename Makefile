.PHONY: install clean

install:
	python setup.py install

clean:
	find . -name '__pycache__' -exec rm -rf {} \+
	find . -name '*.pyc' -exec rm -f {} \+
	find . -name '*.pyo' -exec rm -f {} \+
	find . -name '*~'    -exec rm -f {} \+
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info


all: doc test

doc:
	sphinx-apidoc -f -e -o doc/source hidtools
	sphinx-build -a -b html doc/source doc/html

test:
	sudo pytest-3

.PHONY: doc test

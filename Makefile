.PHONY: test
test:
	coverage run tests.py

.PHONY: verify
verify:
	pyflakes smartfile
	pep8 --ignore=E501,E225 smartfile

.PHONY: install
install:
	python setup.py install

.PHONY: publish
publish:
	python setup.py register
	python setup.py sdist upload

.PHONY: profile
profile:
	python profile.py

.PHONY: clean
clean:
	find . -name *.pyc -delete

.PHONY: distclean
distclean: clean
	rm -rf env


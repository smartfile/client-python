test:
	coverage run tests.py

verify:
	pyflakes smartfile
	pep8 --ignore=E501,E225 smartfile

install:
	python setup.py install

publish:
	python setup.py register
	python setup.py sdist upload

profile:
	python profile.py

clean:
	find . -name *.pyc -delete

distclean: clean
	rm -rf env


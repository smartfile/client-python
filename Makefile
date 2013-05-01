test:
	python tests.py

verify:
	pyflakes -x W smartfile
	pep8 --exclude=migrations --ignore=E501,E225 smartfile

install:
	python setup.py install

publish:
	python setup.py register
	python setup.py sdist upload

profile:
	python profile.py


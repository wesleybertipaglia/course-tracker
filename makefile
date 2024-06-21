venv-init:
	python3 -m venv venv

venv-activate:
	source venv/bin/activate

dependencies-install:
	pip install -r requirements.txt

dependencies-freeze:
	pip freeze > requirements.txt

run:
	flask run

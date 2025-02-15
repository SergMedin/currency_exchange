all: test lint coverage
	@echo "All checks passed"

coverage:
	coverage run -m unittest discover -p "*.py" && coverage report -m --sort=cover --omit="*/test/*" | cut -c1-100

test:
	pytest

lint:
	mypy .

coverage:
	coverage run -m unittest discover -p "*.py" && coverage report -m | cut -c1-100
test:
	pytest
lint:
	mypy .

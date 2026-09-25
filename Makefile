install:
	python3 -m pip install -r requirements.txt

run:
	python3 main.py $(FILE)

debug:
	python3 -m pdb main.py $(FILE)

clean:
	find . -type d -name "__pycache__" -exec

lint:
	flake8
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

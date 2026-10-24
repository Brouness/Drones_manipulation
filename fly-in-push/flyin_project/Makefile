PYTHON ?= python3
MAP ?= examples/simple.map

.PHONY: install run visualize debug test lint lint-strict clean

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

run:
	$(PYTHON) main.py $(MAP)

visualize:
	$(PYTHON) main.py $(MAP) --visualize

debug:
	$(PYTHON) -m pdb main.py $(MAP)

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache .coverage

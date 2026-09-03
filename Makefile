.DEFAULT_GOAL := help
PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(BIN)/python:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip

.PHONY: install
install: $(BIN)/python ## Create the virtualenv and install dev dependencies
	$(BIN)/pip install -e ".[dev]"

.PHONY: test
test: ## Run the test suite
	$(BIN)/pytest

.PHONY: lint
lint: ## Check formatting and lint rules
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

.PHONY: fmt
fmt: ## Apply formatting and safe lint fixes
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

.PHONY: typecheck
typecheck: ## Run mypy
	$(BIN)/mypy src

.PHONY: check
check: lint typecheck test ## Everything CI runs

.PHONY: hooks
hooks: ## Point git at the tracked hooks in .githooks (run once per clone)
	git config core.hooksPath .githooks

.PHONY: demo
demo: ## Generate a sample project into build/ and show the tree
	rm -rf build/demo && mkdir -p build/demo
	$(BIN)/bootstrapper new "Market API" -o build/demo --no-git --yes
	find build/demo -type f | sort

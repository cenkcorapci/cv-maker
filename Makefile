.PHONY: help install dev test lint format validate preview generate clean

PYTHON ?= python3
UV ?= uv
VENV ?= .venv
BIN := $(VENV)/bin
CVGEN := $(BIN)/cvgen
SAMPLE := tests/fixtures/sample.md
OUTPUT ?= dist/cv.pdf

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime dependencies with uv
	$(UV) sync

dev: ## Install project with dev dependencies
	$(UV) sync --extra dev
	$(UV) pip install -e .

test: dev ## Run the test suite
	$(BIN)/pytest -q

lint: dev ## Run Ruff linter
	$(BIN)/ruff check .

format: dev ## Format code with Ruff
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

validate: dev ## Validate the sample CV Markdown file
	$(CVGEN) validate $(SAMPLE)

preview: dev ## Render a preview PDF from the sample CV
	$(CVGEN) preview --data $(SAMPLE) --open

generate: dev ## Generate a PDF from the sample CV
	@mkdir -p $(dir $(OUTPUT))
	$(CVGEN) generate --data $(SAMPLE) --output $(OUTPUT)
	@echo "Wrote $(OUTPUT)"

clean: ## Remove build artifacts and generated PDFs
	rm -rf dist/ build/ .pytest_cache/ .ruff_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete

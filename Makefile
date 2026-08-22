.PHONY: help install test lint format typecheck clean build publish

# Default target
help: ## Show this help message
	@echo "vesi - Version control yang gampang dipelajari"
	@echo ""
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development
install: ## Install in development mode
	pip install -e .
	pip install pytest pytest-cov ruff mypy pre-commit

install-dev: ## Install with all dev dependencies
	pip install -e ".[dev]"

# Testing
test: ## Run all tests
	PYTHONPATH=src pytest tests/ -v

test-unit: ## Run unit tests only
	PYTHONPATH=src pytest tests/unit/ -v

test-integration: ## Run integration tests only
	PYTHONPATH=src pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	PYTHONPATH=src pytest tests/e2e/ -v

test-cov: ## Run tests with coverage
	PYTHONPATH=src pytest tests/ --cov=vesi --cov-report=html --cov-report=term

# Code Quality
lint: ## Run linting
	ruff check src/ tests/

format: ## Format code
	ruff format src/ tests/

typecheck: ## Run type checking
	mypy src/vesi --ignore-missing-imports || true

pre-commit: ## Run pre-commit on all files
	pre-commit run --all-files

# Cleanup
clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build
build: clean ## Build distribution
	python -m build

# Release
version: ## Show current version
	@grep 'version' pyproject.toml | head -1

bump-patch: ## Bump patch version (0.1.0 -> 0.1.1)
	@echo "Bumping patch version..."
	@sed -i 's/version = "0\.\([0-9]*\)\.\([0-9]*\)"/version = "0.\1.\2"/' pyproject.toml
	@echo "Done. New version:"
	@make version

# Run CLI
run: ## Run vesi CLI
	PYTHONPATH=src python -m vesi.cli.app

# Documentation
docs-serve: ## Serve documentation locally
	mkdocs serve

docs-build: ## Build documentation
	mkdocs build

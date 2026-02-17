# HackGPT Desktop – Makefile
# Native macOS app build targets

.PHONY: dev build dist clean test lint help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

dev: ## Debug build + run (hot reload via rebuild)
	cd HackGPTApp && ./desktop_build.sh dev

build: ## Release build + .app bundle
	cd HackGPTApp && ./desktop_build.sh build

dist: ## Release build + .app + DMG installer
	cd HackGPTApp && ./desktop_build.sh dist

clean: ## Remove all build artifacts
	cd HackGPTApp && ./desktop_build.sh clean

test: ## Run Python tests
	python3 -m pytest tests/ -v -o "addopts="

lint: ## Run ruff linter
	python3 -m ruff check .
	python3 -m ruff format --check .

install-deps: ## Install Python dependencies
	python3 -m pip install -r requirements.txt --break-system-packages

swift-build: ## Build Swift app only (no bundling)
	cd HackGPTApp && swift build -c release

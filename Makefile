.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@echo "Available commands:"
	@grep -h -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: ## Build the python package
	pip install build
	python -m build

.PHONY: dev
dev: ## Start developing scaffold
	pip install -e .

.PHONY: docs
docs: ## Generate the documentation using tinydocs
	tinydocs-cli -D scaffold -o docs --ignore=.gitignore,.tinyignore --markers docs/tiny.markers.json --name scaffold

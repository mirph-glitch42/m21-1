# Single canonical task runner — every gate stage has one entrypoint.
# Local dev uses the pinned venv; CI installs the locked deps into the
# system interpreter (there is no .venv on the runner), so PY falls
# back to the PATH python when the local venv is absent.
PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
VENV ?= .venv

setup: ## Create venv, install pinned deps, wire git hooks
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.lock
	git config core.hooksPath hooks
	@echo "✓ setup complete (hooks wired to ./hooks)"

format: ## Format sources with ruff
	$(VENV)/bin/ruff format .

format-check: ## Verify formatting (gate)
	$(VENV)/bin/ruff format --check .

lint: ## Lint sources with ruff
	$(VENV)/bin/ruff check .

test: ## Run the fast unit suite (no network)
	$(PY) -m pytest -q tests -m "not live"

test-live: ## Run network tests against the real API (manual, explicit)
	$(PY) -m pytest -q tests -m "live"

secrets: ## Secret scan of staged changes
	gitleaks git --staged --redact --config .gitleaks.toml -v

secrets-history: ## Secret scan of full git history
	gitleaks git --redact --config .gitleaks.toml -v

doc-index: ## Regenerate algorithm-doc line indexes
	@for doc in algorithms/*.md; do \
		case "$$doc" in */INDEX.md) continue ;; esac; \
		$(PY) scripts/build_index.py "$$doc" || exit 1; \
	done

doc-index-check: ## Verify algorithm-doc indexes are fresh (gate)
	@fail=0; \
	for doc in algorithms/*.md; do \
		case "$$doc" in */INDEX.md) continue ;; esac; \
		$(PY) scripts/build_index.py "$$doc" --check || fail=1; \
	done; exit $$fail

gate: format-check lint doc-index-check test secrets ## Full local gate (cheap -> expensive)
	@echo "✓ gate green"

crawl: ## Crawl the manual and write output/M21-1-Adjudication-Procedures-Manual.md
	PYTHONPATH=src $(PY) -m m21_crawl.cli

.PHONY: setup format format-check lint test test-live secrets secrets-history doc-index doc-index-check gate crawl

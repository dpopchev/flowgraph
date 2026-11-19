# The Python layer: read by the root Makefile after the base modules and before
# mk/aggregates.mk. Uses UV, LOCAL and the log helpers of the base; appends its
# checks to CHECKS and its clean to CLEANS.

# ------------------------------------------------------------------------------
### Python
# ------------------------------------------------------------------------------

# `=` (not `:=`): read at recipe time.
PYTHON_VERSION = $(shell cat .python-version)

RUN := $(UV) run

# Every python residual lives in $(PYTHON_LOCAL), so the tree never shows a cache
# and clean-python removes one directory. A tool with a pyproject key is pointed
# there in pyproject.toml (pytest, ruff); a tool that only reads the environment
# gets its export here.
PYTHON_LOCAL := $(LOCAL)/python
export PYTHONPYCACHEPREFIX := $(abspath $(PYTHON_LOCAL))/pycache

CHECKS += lint typecheck test
CLEANS += clean-python

.PHONY: sync
sync: .python-version pyproject.toml | $(LOCAL) ## Create or refresh .venv and uv.lock
	@$(UV) sync
	$(call log_done,environment synced -- python $(PYTHON_VERSION)$(comma) uv.lock current)

.PHONY: lint
lint: ## Ruff check without fixes
	@$(RUN) ruff check .
	$(call log_done,ruff check clean)

.PHONY: format
format: ## Ruff format and import ordering
	@$(RUN) ruff format .
	@$(RUN) ruff check --fix --select I .
	$(call log_done,formatted)

.PHONY: typecheck
typecheck: ## Pyright over the configured paths
	@$(RUN) pyright
	$(call log_done,pyright clean)

# pytest exits 5 when it collects nothing -- a fresh layer before its first test:
# warned through _log_line, never failed. Every other non-zero exit breaks.
define _pytest
	@rc=0; $(RUN) pytest $(1) || rc=$$?; \
	if [ $$rc -eq 5 ]; then \
	  $(call _log_line,$(YELLOW),WARN,pytest collected no tests -- write the first test) \
	elif [ $$rc -ne 0 ]; then exit $$rc; fi
endef

.PHONY: test
test: ## Pytest with doctests
	$(call _pytest,)
	$(call log_done,tests passed)

.PHONY: test-quick
test-quick: ## Pytest stopping at the first failure
	$(call _pytest,-x -q)
	$(call log_done,quick tests passed)

.PHONY: clean-python
clean-python: ## Remove local/python/ -- the python tool caches
	@rm -rf $(PYTHON_LOCAL)
	$(call log_done,removed $(PYTHON_LOCAL)/)

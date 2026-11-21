# The Python layer: read by the root Makefile after the base modules and before
# mk/aggregates.mk. Uses UV, LOCAL and the log helpers of the base; appends its
# checks to CHECKS and its clean to CLEANS.

# ------------------------------------------------------------------------------
### Python
# ------------------------------------------------------------------------------

# `=` (not `:=`): read at recipe time.
PYTHON_VERSION = $(shell cat .python-version)

RUN := $(UV) run

# Every python residual lives in $(CACHE), so the tree never shows a cache and
# clean-python removes one directory. A tool with a pyproject key is pointed
# there in pyproject.toml (pytest, ruff); a tool that only reads the environment
# gets its export here.
CACHE   := $(LOCAL)/cache
PYCACHE := $(abspath $(CACHE))/pycache
export PYTHONPYCACHEPREFIX := $(PYCACHE)

# A bare `uv run` reads no Makefile and uv has no project setting for the
# environment, so sync also writes $(PYCACHE_PTH) into the venv: a line Python
# runs at every start, setting the same prefix. uv sync keeps the file; a
# recreated .venv loses it until the next make sync.
PYCACHE_PTH := pycache_prefix.pth

# No module of the package grows past MAX_LINES unseen: `lines` names each one
# above it and breaks. The number is written here, once; a command line gives
# another (`make check MAX_LINES=300`). The tests are not counted.
LINES_IN  := src
MAX_LINES := 400

CHECKS += lint lines typecheck test
CLEANS += clean-python

.PHONY: sync
sync: .python-version pyproject.toml | $(LOCAL) ## Create or refresh .venv and uv.lock
	@$(UV) sync
	@site="$$($(RUN) --no-sync python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')"; \
	  printf 'import sys; sys.pycache_prefix = "%s"\n' "$(PYCACHE)" > "$${site}/$(PYCACHE_PTH)"
	$(call log_done,environment synced -- python $(PYTHON_VERSION)$(comma) uv.lock current$(comma) bytecode to $(CACHE)/pycache)

.PHONY: lint
lint: ## Ruff check and format check, without fixes
	@$(RUN) ruff check .
	@$(RUN) ruff format --check .
	$(call log_done,ruff check clean$(comma) every file formatted)

.PHONY: lines
lines: ## Fail on a module of src/ above MAX_LINES lines, naming it
	@over="$$(find $(LINES_IN) -name '*.py' -exec wc -l {} + \
	  | awk -v max=$(MAX_LINES) '$$2 != "total" && $$1 > max { printf "%s: %d lines\n", $$2, $$1 }' \
	  | sort)"; \
	if [ -n "$$over" ]; then \
	  printf '%s\nabove $(MAX_LINES) lines -- split the module\n' "$$over" >&2; \
	  exit 1; \
	fi
	$(call log_done,no module of $(LINES_IN)/ above $(MAX_LINES) lines)

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

# Every full run measures coverage (the table, missing lines included) and lists
# the 10 slowest tests; pytest hides a test under 5 ms from that list. It also
# rewrites the reports of the last run in $(LAST_RUN): coverage.md, and
# slowest.md -- the 10 slowest tests by module, test and seconds, from
# tests/conftest.py. $(CACHE)/pytest is pytest's cache_dir in pyproject.toml.
LAST_RUN := $(CACHE)/pytest/last-run
TEST_REPORTS := --cov --cov-report=term --cov-report=markdown:$(LAST_RUN)/coverage.md \
  --durations=10 --slowest-file=$(LAST_RUN)/slowest.md

$(LAST_RUN):
	@mkdir -p $@
	$(call log_warn,created $@/ -- the reports of the last make test$(comma) removed by make clean)

.PHONY: test
test: | $(LAST_RUN) ## Pytest with doctests, coverage and the 10 slowest
	$(call _pytest,$(TEST_REPORTS))
	$(call log_done,tests passed -- reports in $(LAST_RUN)/)

.PHONY: test-quick
test-quick: ## Pytest stopping at the first failure
	$(call _pytest,-x -q)
	$(call log_done,quick tests passed)

.PHONY: clean-python
clean-python: ## Remove local/cache/ -- the python tool caches
	@rm -rf $(CACHE)
	$(call log_done,removed $(CACHE)/)

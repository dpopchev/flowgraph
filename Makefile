.SUFFIXES:
.DELETE_ON_ERROR:

SHELL       := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules --no-builtin-variables
MAKEFLAGS += --output-sync=target

.DEFAULT_GOAL := help

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------

BOLD   := \033[1m
CYAN   := \033[36m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m

# Suppress --warn-undefined-variables false positives for $(call) arguments
1 :=
2 :=
3 :=

# The `@` lives inside the define: call log_done / log_warn WITHOUT a leading `@`.
# A literal comma inside the message is $(comma) -- make splits $(call) on commas.
comma := ,

# _log_line is the one home of the log format: a shell body of ONE logical line,
# no leading `@`, so another recipe's compound shell line can call it too.
define _log_line
	  _tag="[$(2)]"; \
	  _msg="$(3)"; \
	  if _c=$$(tput cols 2>/dev/null); then _cols=$$_c; else _cols=80; fi; \
	  _max=$$(( _cols - $${#_tag} - 4 )); \
	  if [ $${#_msg} -gt $$_max ] && [ $$_max -gt 0 ]; then \
	    _msg="$${_msg:0:$$_max}..."; \
	  fi; \
	  printf "$(BOLD)$(1)%s$(RESET) %s\n" "$$_tag" "$$_msg" >&2;
endef

define _log_raw
	@{ $(call _log_line,$(1),$(2),$(3)) }
endef

# [DONE] closes every target and names the artifact; [INFO] reports a step on the
# way; [WARN] only for an actionable, handled condition. The tags are four letters
# wide. There is no log_error: a failure breaks the recipe.
log_done = $(call _log_raw,$(GREEN),DONE,$(1))
log_info = $(call _log_raw,$(CYAN),INFO,$(1))
log_warn = $(call _log_raw,$(YELLOW),WARN,$(1))

# ------------------------------------------------------------------------------
### Help
# ------------------------------------------------------------------------------

# A `###` banner names a help section; a `## description` after a target lists it.
# Every file in MAKEFILE_LIST is read (grep -h), so an included mk/*.mk shows too.
# %-30s: the padded field holds 9 invisible color bytes, leaving 21 visible columns.
.PHONY: help
help: ## Show this help
	@grep -hE '^(###[ ].+|[a-zA-Z0-9_%/-]+:.*##[^#])' $(MAKEFILE_LIST) \
	  | sed -E \
	      -e 's|^### (.+)|\x1b[1;36m\1\x1b[0m|' \
	      -e 's|^([a-zA-Z0-9_%/-]+):.*## (.+)|  \x1b[32m\1\x1b[0m:\2|' \
	  | awk -F: '{ \
	      if ($$0 !~ /:/) { printf "\n%s\n", $$0 } \
	      else { printf "  %-30s %s\n", $$1, $$2 } \
	    }'

# ------------------------------------------------------------------------------
### Environment
# ------------------------------------------------------------------------------

# uv is always run through $(UV), never bare.
UV := uv

# Directory convention (rules/makefile.md -> Directories):
#   $(BUILD) the end product -- `make clean` removes it whole
#   $(LOCAL) machine-local and interim: inputs, state, keys, scratch, tool
#            residuals -- never tracked; make clean removes only state/ and
#            the layers' residuals
#   $(STATE) interim results and artifacts of any step, when a step needs
#            them -- written by explicit file targets
BUILD ?= build
LOCAL ?= local
OUT     := $(BUILD)/outputs
REPORTS := $(BUILD)/reports
STATE   := $(LOCAL)/state

$(LOCAL):
	@mkdir -p $(LOCAL)/keys $(LOCAL)/scratch $(LOCAL)/inputs $(STATE)
	$(call log_warn,created $(LOCAL)/ -- inputs/$(comma) state/$(comma) keys/ and scratch/ live here; git-ignored$(comma) make clean removes only state/)

$(OUT) $(REPORTS) $(STATE):
	@mkdir -p $@
	$(call log_warn,created $@/ -- an artifact directory$(comma) removed by make clean)

.PHONY: clean-build clean-state
clean-build: ## Remove build/ -- the end products
	@rm -rf $(BUILD)
	$(call log_done,removed $(BUILD)/)

clean-state: ## Remove local/state/ -- the interim results
	@rm -rf $(STATE)
	$(call log_done,removed $(STATE)/)

# Layers (mk/python.mk, ...) add their targets and append to CHECKS, CLEANS and
# DELIVERABLES. Included here, before `check`, `clean` and `deliverables`, because
# make expands prerequisites when it reads a rule.
CHECKS :=
CLEANS := clean-build clean-state
# Each entry is a target named after its artifact (wheel, talk) -- makefile.md, Deliverables.
DELIVERABLES :=
include $(wildcard mk/*.mk)

.PHONY: clean
clean: $(CLEANS) ## Run every clean -- inputs, keys, settings, scratch, .venv/ untouched
	$(call log_done,cleaned: $(CLEANS) -- inputs$(comma) keys$(comma) settings$(comma) scratch and .venv/ untouched)

# ------------------------------------------------------------------------------
### Quality
# ------------------------------------------------------------------------------

.PHONY: check
check: $(CHECKS) ## Run every check -- each layer
	$(call log_done,all checks passed)

.PHONY: deliverables
deliverables: $(DELIVERABLES) ## Build every deliverable -- every Task close runs it
ifeq ($(strip $(DELIVERABLES)),)
	$(call log_warn,no deliverable declared -- add one with DELIVERABLES += <target>)
else
	$(call log_done,deliverables built: $(DELIVERABLES))
endif

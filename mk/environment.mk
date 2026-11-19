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
# DELIVERABLES. The root Makefile reads them after this file and before
# mk/aggregates.mk, because make expands prerequisites when it reads a rule.
CHECKS :=
CLEANS := clean-build clean-state
# Each entry is a target named after its artifact (wheel, talk) -- makefile.md, Deliverables.
DELIVERABLES :=

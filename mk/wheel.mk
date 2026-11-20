# mk/wheel.mk -- the PACKAGE level of the Python layer (rules/python.md ->
# Levels): the wheel. Added by add-python next to mk/python.mk only when the
# project ships src/<pkg>; a helper-level repository has no dist target.
# Named to sort after python.mk: make includes mk/*.mk in sorted order.

# ------------------------------------------------------------------------------
### Package
# ------------------------------------------------------------------------------

PKG   ?= flowgraph
SRC   := src/$(PKG)
TESTS := tests
DIST  := $(BUILD)/dist

$(DIST):
	@mkdir -p $@
	$(call log_warn,created $@/ -- a build artifact directory$(comma) removed by make clean)

# The deliverable: the built wheel (makefile.md, Deliverables -- built, not opened).
DELIVERABLES += wheel

.PHONY: wheel
wheel: | $(DIST) ## Build the wheel into build/dist/
	@rm -rf $(DIST)/*.whl
	@$(UV) build --wheel --out-dir $(DIST) >/dev/null
	$(call log_done,wheel built: $$(ls $(DIST)/*.whl))

.PHONY: dist
dist: check | $(DIST) ## Build the wheel and sdist into build/dist/
	@rm -rf $(DIST)/*
	@$(UV) build --out-dir $(DIST)
	$(call log_done,built $$(ls $(DIST)/*.whl))

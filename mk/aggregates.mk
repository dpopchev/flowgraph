# The targets that sum up CLEANS, CHECKS and DELIVERABLES; read last, after every
# layer has appended to them. `clean` sits above the Quality banner so the help
# menu still lists it with the cleans of the section before.

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

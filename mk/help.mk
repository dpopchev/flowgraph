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

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

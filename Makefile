.SUFFIXES:
.DELETE_ON_ERROR:

SHELL       := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules --no-builtin-variables
MAKEFLAGS += --output-sync=target

.DEFAULT_GOAL := help

# ------------------------------------------------------------------------------
# Modules
# ------------------------------------------------------------------------------

# Every section lives in mk/*.mk; this file sets make up and reads them in order.
# The order is fixed because make expands prerequisites when it reads a rule:
# MK_HEAD declares CHECKS, CLEANS and DELIVERABLES, a layer (mk/python.mk, ...)
# appends to them, and MK_TAIL holds the targets that sum them up.
MK_HEAD   := mk/logging.mk mk/help.mk mk/environment.mk
MK_TAIL   := mk/aggregates.mk
MK_LAYERS := $(filter-out $(MK_HEAD) $(MK_TAIL),$(wildcard mk/*.mk))

include $(MK_HEAD) $(MK_LAYERS) $(MK_TAIL)

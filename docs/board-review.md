# Board 1 review and its feature map for flowgraph

What the `board` skill's tool does today, and what flowgraph (board 2.0) keeps,
redesigns or drops. The review is observed from the code; the map was proposed
by the agent and decided by the developer, group by group, on 2026-11-20.

| Fact | Value |
|---|---|
| Reviewed | `~/.claude/skills/board/scripts` |
| At | commit `e7842db6` on `main`, 4 commits after tag `v1.148.3` |
| On | 2026-11-20 |
| Method | module docstrings, `board.py --help`, `pyproject.toml`, `Makefile`, line counts; the suite was not run |

## Goal of board 1

Make `.board/` a machine-checked, local record of a hypothesis tree -- Epic >
work item (issue, spike, bug) > Task -- that is read and written only through
one command line. Every write is re-checked and restored on a violation, and
every close is gated on evidence: a Task on its check, a work item on its
landing.

## Features

45 subcommands in eight groups.

| Group | What it does | Commands | Modules (lines) |
|---|---|---|---|
| 1 Typed record | items as sum types: 5 states, 3 kinds, drafts | `new`, `show`, `next-id`, `sections` | `model`, `load`, `items`, `vocab` (2,033) |
| 2 Checker | rules C1-C7 on `board.toml`, V1-V29 on items; write, re-check, restore | `check`, `config`, `bind` | `validate`, `config`, `store` (1,542) |
| 3 Transitions | only legal moves, each logged in History | `move`, `block`, `unblock`, `park`, `amend`, `criterion`, `reparent`, `retitle`, `note` | `commands` (2,040) |
| 4 Close gates | scope, the Task's Check as written, `make deliverables`; attribution lint; lane write guards | `close`, `scope`, `lint-msg`, `guard`, `guard-bash` | `scope`, `bashshape` (360) |
| 5 Lanes and landing | one worktree per work item, a `--no-ff` merge, the verified note, `v*` tags, burn-down | `start`, `land`, `sync-main`, `verify`, `release`, `burn`, `goal`, `report` | `lanes`, `landing`, `worktrees` (1,367) |
| 6 Knowledge base | Findings, Decisions, Deviations; search by text or by the commits that touched a file; recall measured against judged lookups | `knowledge`, `lookups`, `lookup`, `context` | `knowledge`, `about` (566) |
| 7 Views | `BOARD.md`, `KNOWLEDGE.md`, `KANBAN.md`, `board.csv`, ledgers, a live pane | `render`, `archive`, `status`, `next`, `tree`, `watch` | `views` (1,335) |
| 8 External sync | two-way against a backend snapshot; Azure DevOps over REST, plan-only otherwise | `reconcile`, `plan-push`, `push`, `sync`, `remote`, `pipeline` | `sync`, `remote`, `azure` (1,736) |

The command line itself is `cli` and `parser` (1,719 lines).

## Review notes

- Design: the runtime is stdlib only, run as `uv run board.py`. Pure modules
  (`model`, `validate`, `views`, `sync`, `azure`) sit under an imperative shell
  (`cli`, `commands`, `store`, `remote`); an import cycle is a pyright error.
- Size: 12,699 source lines in 22 files against 16,263 test lines and about
  1,712 test functions; 642 commits since 2026-09-24.
- Concentration: `commands.py` (2,040 lines) and `views.py` (1,335) hold over a
  quarter of the source.
- Scope growth: the stated purpose is "check, transition, render", but the tool
  also owns git landing, release tagging, Bash-shape guards, a recall harness
  and an Azure DevOps client. The `board.py` docstring still lists 11 modules.
- Seed of an ontology: a knowledge line may end `about: <term>`, checked
  against the closed set `[knowledge] terms` in `board.toml`; `knowledge
  --about <term>` lists those lines. Terms have no relations to each other.

## Map to flowgraph -- decided 2026-11-20

Measured against the README: flowgraph keeps the record of a project's work,
enforces an agile flow of small checked moves, and builds the project's
ontology -- its terms and how they relate. Each verdict is the developer's;
the last column is what would reopen it.

| Group | Verdict | Why | Reopens if |
|---|---|---|---|
| 1 Typed record | redesign | it is still "the record" and still typed, but its model is now `docs/domain-model.md`: Feature over Story, Bug, Spike and Upkeep over Task, and the state of an item as its type | one type per state costs more than it saves once the first kind runs end to end: then states become a field again |
| 2 Checker | keep | write, re-check, restore is the mechanism of "each one a checked move" | rules move into the constructors so no separate pass is left: then it folds into group 1 |
| 3 Transitions | keep the moves, redesign the shell | the state machine is sound; one 2,040-line shell module is not one aggregate per module | the split costs more than it saves once the first three commands exist |
| 4 Close gates | redesign | scope, check and deliverable gates are the flow; `guard`, `guard-bash` and `lint-msg` police one agent harness and belong in an adapter outside the core | flowgraph is only ever driven by that harness: then keep them inside |
| 5 Lanes and landing | redesign | landing is in the README's flow, but as a git adapter behind the record; `burn`, `goal` and `report` orchestrate agent sessions and are deferred | the first self-tracking version must land its own work items: then `start` and `land` come early |
| 6 Knowledge base | redesign | this is where flowgraph differs: terms and typed relations replace text search, so "what governs this file" becomes a query; the recall harness is needed only while search is by text | the ontology cannot answer a lookup the harness can: then keep the harness as its measure |
| 7 Views | keep, fewer | views are pure functions of the board; `status`, `next` and `tree` first, the rendered files when something reads them | a rendered file is the session's entry point from day one: then `render` comes early |
| 8 External sync | drop for now | 1,736 lines for one backend, no flowgraph criterion asks for it, and the record is local by rule | a project flowgraph must serve needs an external board in its first version |

## Open questions

- What is a term's relation to an item: a tag on a knowledge line as today, or
  a first-class node that items, files and other terms link to? Group 6 turns
  on this.
- Which groups must exist before flowgraph can track itself? The map's reading is
  1, 2, a part of 3 and `status` from 7.

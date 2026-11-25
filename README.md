# flowgraph

flowgraph keeps the record of a project's work. It enforces an agile flow --
work is planned, done and landed in small steps, each one a checked move -- and
it builds the ontology of the project on the way: its terms and how they relate.

## Status

Early: `fgraph init` makes the record of a directory, `fgraph` adds a Story to it, writes its Tasks, takes them from
Backlog through InProgress to Completed, shows a Story with its Tasks and
lists the record by bucket. An Upkeep moves the same way, with its own Tasks,
and is listed beside the Stories. The Backlog is a queue that `fgraph
reorder` reorders, and a work item still in it is rewritten with `fgraph
amend`. In a git repository `fgraph` commits every write of the record
itself. A record is layered by its configuration, `.fgraph/config.toml`: it
turns the commits of the record off, and once it turns the development on,
starting a work item also checks out its branch in a worktree of its own,
completing an item names the commit that holds its work, and `fgraph land`
lands it. `fgraph release` tags `main` with its next `v*` version, from the
work completed since the last one. `fgraph config` shows the configuration
and sets a key of it. A work item, and a Feature, keeps the findings,
decisions and deviations noted on it with `fgraph note`, in any state, and
`fgraph show` lists them; a work item and a Task of it also take a progress
line, where the work stands, which `fgraph show` lists too. `fgraph knowledge` lists the lines of the whole
record. The closing of a completed Story, Bug or
Upkeep is answered with `fgraph verify`: yes or no, with what the run of its
criterion printed, which `fgraph show` lists; a no files a Bug that amends it.
A term of the project, a word with what it
means, is added with `fgraph add term`, listed by `fgraph terms` and shown by
`fgraph show` of its name. `fgraph about` answers what an item is linked to: it
lists the Feature, the work items, the terms and the knowledge lines of a work
item or a Feature, each under its relation. `fgraph graph` exports the nodes and
the typed edges of the whole record as JSON.

| Part                            | State                                                    |
| ------------------------------- | -------------------------------------------------------- |
| the `fgraph` command            | runs, prints its help menu                               |
| the wheel                       | built by `make wheel`, ships `fgraph`                    |
| where the record lives          | located on every call but `--help` and `fgraph init`     |
| making a record                 | `fgraph init` makes `.fgraph/`, no `mkdir`               |
| the record and its flow         | a work item with its Tasks, from Backlog to Completed    |
| the kinds of work item          | Story, Upkeep, Bug, Spike                                |
| the level above                 | a Feature groups work items, takes each operation of one |
| the order of the Backlog        | a queue, reordered by `fgraph reorder`, Features too     |
| the relations of a work item    | `--depends-on` it waits for, `--filed-during` it found,  |
|                                 | `--amends` the completed one it changes, `fgraph remove` |
|                                 | `--superseded-by` the one that replaces it               |
| the wording of a work item      | `fgraph amend` in Backlog: parent too, a Feature's too   |
| a change once started           | `fgraph amend --deviation`, the part and its line        |
| the wording of a Task           | `fgraph amend T-0001` in Backlog                         |
| the complexity of a work item   | `--complexity low`, `medium` or `high`, on add and amend |
| criterion a work item realizes  | `--realizes N` beside `--parent`, on add and amend       |
| git                             | every write of the record committed, unless turned off   |
| the layers of a record          | `.fgraph/config.toml`: commits on, development off       |
| the configuration               | every key shown and set by `fgraph config`               |
| the archive of an old board     | `archive.board` points at it, `fgraph show` names an id  |
| the knowledge of an item        | lines noted by `fgraph note` on a work item or a Feature |
| the knowledge of the record     | every line listed by `fgraph knowledge`, newest first    |
| the progress of the work        | `fgraph note --progress` on a work item or a Task        |
| the closing of a work item      | `fgraph verify --yes` keeps the yes of a completed one   |
|                                 | `--no` keeps the no and files a Bug that amends it       |
| the development                 | once enabled: start branches, `fgraph land` lands        |
| the commits of main in a branch | `fgraph sync` merges `main` into a started branch        |
| the release of the trunk        | `fgraph release` tags `main` with its next `v*` version  |
| the links of an item            | `fgraph about` lists every relation, both sides, by id   |
| the brief of a work item        | `fgraph brief` prints it whole, as text or as JSON       |
| the commit of a Task            | `fgraph commit` commits the files its brief names        |
| the /goal line of a Feature     | `fgraph goal` prints it, for a developer to paste        |
| the export of the record        | `fgraph graph` prints its nodes and edges as JSON        |
| the ontology                    | started: terms, related by is-a and part-of              |
| flowgraph tracking its own work | its Stories are in `.fgraph/` since 0.4.0                |

The model of the record -- its item types, states and rules -- is
`docs/domain-model.md`. flowgraph keeps its own work in `.fgraph/`, with the
development turned on: run `uv run fgraph status` in the checkout to see what
is next.

A term is a node of the record with no flow, kept by its name:

```sh
fgraph add term gate --means "a check every deliverable passes before it lands"
fgraph terms                # gate  a check every deliverable passes before it lands
fgraph show gate            # the term with its meaning and the day it was added
```

Two terms are related by one of two kinds, `is-a` or `part-of`, with `fgraph
relate`; each side shows the relation:

```sh
fgraph add term lane --means "one work item in its own worktree"
fgraph relate gate part-of lane
fgraph show gate            # gate, with the line: part of  lane
fgraph show lane            # lane, with the line: parts  gate
```

`fgraph relate gate is-a check` shows `is a  check` under `gate` and `kinds  gate`
under `check`. Like `fgraph add term`, it is written on `main` alone.

An item and a line of knowledge name the terms they are about, with `--about`
once per term. `fgraph note`, `fgraph add` of a work item or a Feature and
`fgraph amend` of one in Backlog take it; `fgraph amend S-0001 --about none` takes
every term of the item away. A term the record holds none of exits 2, names `fgraph
add term` and writes nothing. On the branch of a work item the terms are those of
`main`, a term added there after the branch was cut included. `fgraph show` of
an item lists its terms and, after each line, the terms of the line; `fgraph show`
of a term lists, after its relations, the items about it and the lines about it,
each with the id of its item; `fgraph knowledge --about gate` lists the lines
about that term alone:

```sh
fgraph add story "Hold the landing" --given a --when b --then c --about gate
fgraph note S-0001 --decision "a gate runs on main" --about gate --about lane
fgraph amend S-0001 --about lane
fgraph show S-0001          # about  lane, and the line: decision  2026-11-22  a gate runs on main  (about gate, lane)
fgraph show gate            # gate, with the lines: items  S-0001, knowledge  S-0001  decision  2026-11-22  a gate runs on main
fgraph knowledge --about gate
# 2026-11-22  decision  S-0001#1  a gate runs on main  (about gate, lane)
```

A Story, an Upkeep, a Bug and a Spike carry a complexity, `low`, `medium` or
`high`, none when it is left out: `fgraph add` takes `--complexity`, and `fgraph
amend` takes it in Backlog alone, in place of the one the item had. Every move
carries it. `fgraph show` lists it, after the terms, only when there is one, and
every work item of `fgraph status --format json` holds `complexity`, the word or
`null`; the text of `fgraph status` does not change. Any other word exits 2,
names the three and writes nothing. Which model a complexity maps to stays
outside fgraph, with whoever hands the item to an agent:

```sh
fgraph add story "Hold the landing" --given a --when b --then c --complexity high
fgraph amend S-0001 --complexity medium
fgraph show S-0001          # the line: complexity  medium
fgraph add story "Hold" --given a --when b --then c --complexity huge
# fgraph: error: --complexity 'huge' is none of low, medium, high
```

`fgraph about` lists every link of an item in one view, each relation under a
heading with its count and each linked item on a line of its id, its bucket and
its title. A work item with a Feature, a work item it depends on, one filed
during it and a term:

```sh
fgraph about S-0002
# S-0002  Hold the landing
#   feature (1)
#     F-0001  in-progress  Land work safely
#   depends on (1)
#     S-0001  completed  Run the gate
#   filed here (1)
#     S-0003  backlog  Name the lane of a landing
#   terms (1)
#     gate  a check every deliverable passes before it lands
```

`fgraph about` of a term walks the terms under it, each that is part of it or is a
kind of it, and those under them. It lists the term with its meaning and relations,
then the items and the lines about it and about every term under it; one reached
through another term is marked `(via TERM)`, and each is listed once, under
the nearest term. With `lane` part of `gate`, a line about `lane` shows in the about
of `gate`:

```sh
fgraph about gate
# gate
#   means  a check every deliverable passes before it lands
#   parts  lane
#   added  2026-11-22
#   items  S-0001  (via lane)
#   knowledge
#     S-0001  decision  2026-11-22  a lane holds one work item  (via lane)
```

`fgraph about` of the path of a file lists the completed work items and Tasks
whose commits changed it, newest first, each on a line of its id, its commit and
its title, a Task under its work item. Nothing is stored for a file: the answer
is read from git, by the commit each completed item names. The path is taken from
the directory fgraph runs in. A work item that only a Task of it touched shows `-`
for its commit. With two work items that touched `src/gate.py`:

```sh
fgraph about src/gate.py
# S-0002  4f2a9c1  Hold the landing
#   T-0004  91be07d  Add the gate to the landing
# S-0001  c03d5e8  Run the gate
```

A line of knowledge names the files it governs, with `--governs PATH` once per
file, on `fgraph note`. The path is kept as written from the top of the git work
tree, or as given outside one, and is not checked against the disk: a governed
file may be renamed or not yet written. `fgraph about` of the path lists the lines
that govern it first, under `Governed by`, newest first, each with its kind, its
date, the id of its item and its text, then the items whose commits touched it.
A path that no file on the disk and no id or term answers to is read as a path
when a line governs it, so a file not yet written is answered. Outside a git work
tree the lines that govern it are listed alone:

```sh
fgraph note S-0001 --decision "the gate holds no state" --governs src/gate.py
fgraph about src/gate.py
# Governed by
#   decision  2026-11-22  S-0001  the gate holds no state
# S-0002  4f2a9c1  Hold the landing
#   T-0004  91be07d  Add the gate to the landing
```

`fgraph about` of an item, a term or a file takes `--format json` too and prints its
links as one JSON document, each relation under its key with `[]` for none, keys
sorted and null for nothing, the same bytes on two runs; text stays the default;
another word is refused naming both, exit 2:

```sh
fgraph about S-0002 --format json
# {
#   "amended_by": [],
#   "amends": [],
#   "depended_on_by": [],
#   ...
fgraph about S-0002 --format xml
# fgraph: error: --format 'xml' is not text or json, the two formats of about
```

`fgraph brief` prints the whole brief of a work item in any state, the input a
coordinator hands an agent: the text of `fgraph show`, then the branch and the
worktree git holds for it under `Worktree`, its Feature with its knowledge, the
lines of the record that govern a path one of its Tasks names under `Governed by`,
and the terms it or its Feature is about under `Terms`. A section with nothing in
it is left out. Under `Governed by` a line a later line supersedes is left out;
`fgraph about` of a file lists every one. `--format json` prints the same as one
JSON document, keys sorted and `null` for nothing, the same bytes on two runs. A
Feature id, a Task id and an id the record does not hold are refused, exit 2:

```sh
fgraph brief S-0002
# S-0002  Hold the landing
#   ...
# Worktree
#   branch       wi/S-0002-hold-the-landing
#   path         /work/project.worktrees/S-0002-hold-the-landing
# Feature
#   F-0001  in-progress  Land work safely
# Governed by
#   decision  2026-11-22  S-0001  the gate holds no state
# Terms (1)
#   gate  a check every deliverable passes before it lands
fgraph brief S-0002 --format json
```

`fgraph show` of a work item, a Feature or a term takes `--format json` too, and prints
what its text lists as one JSON document, keys sorted and `null` for nothing, the same
bytes on two runs; `text` stays the default; another word is refused naming both, exit 2.
Every key is listed in `docs/domain-model.md`, section Show as JSON:

```sh
fgraph show S-0001 --format json
# {
#   "about": [
#   ...
fgraph show S-0001 --format xml
# fgraph: error: --format 'xml' is not text or json, the two formats of show
```

Before it commits the work of a Task, an agent asks which files it changed that the brief
of the started Task does not name: `fgraph brief S-0002 --not-named` prints, in place of
the brief, each file changed and not committed in the worktree of the work item -- a tracked
file changed, staged or not, and a new file git does not ignore -- that the title, the
expected output and the description of its started Task do not name, by the rule `fgraph
complete` holds the commit of the Task to; nothing when every file is named. The files of
the record are never listed. `--format json` prints them as a JSON list. Run on main or in
the worktree it reads the worktree. It writes nothing. A work item with no started Task and
a record outside a git work tree are refused, exit 2:

```sh
fgraph brief S-0002 --not-named
# docs/notes.md
# the answer once no Task is started:
# fgraph: error: S-0002 has no started Task: --not-named reads the brief of the Task started
```

Then `fgraph commit T-0001 --message TEXT` commits them: every file changed and not committed in
the work tree of the started Task, in one commit whose message is the text given with the ids of
the work item and the Task at its end. It says the sha, which `fgraph complete` takes, and does
not complete the Task. A changed file the brief does not name refuses the whole commit, exit 2,
and nothing is committed:

```sh
fgraph commit T-0001 --message 'fix: name the gate'
# committed T-0001 of S-0001 at 3e9ae5c...
fgraph complete T-0001 --commit 3e9ae5c
# a file the brief does not name:
# fgraph: error: T-0001 cannot commit: its brief does not name other.txt -- nothing is committed; take each back or have the brief name it
```

`fgraph goal F-0001` prints one `/goal` line for a developer to paste into Claude
Code, naming the work items of the Feature in Backlog in the order they start. It
reads the record and writes nothing, and fgraph never sets the goal itself. The ids,
`development.parallel` and the hours come from the record and the option; the rest
is fixed text. `--hours N` bounds the goal, 8 by default. It is refused, exit 2, for
a record whose `development.enabled` is off or whose `development.driver` is not
`agent`, for a Feature with no work item in Backlog, for a Feature holding a work item in
Backlog with no Task or no complexity, refused in the words of the start of the Feature (the
Task line is `F-0001 cannot start: S-0002 has no Task to start with`), and for hours that are
not a whole number of 1 or more:

```sh
fgraph goal F-0001 --hours 4
# /goal Develop F-0001 until fgraph show F-0001 lists S-0001, S-0002 and S-0003 completed, or stop after 4 hours. This session is the coordinator: it hands each whole work item to one subagent, at most 3 at once as development.parallel says. The goal is met as well when this session prints [HALT] <id>: <the decision needed> on a change to a criterion, a Task or the scope of a work item, or a removal, that the developer has not agreed.
```

`fgraph graph` exports the whole record as one JSON document another tool reads:
every node with its kind -- feature, story, upkeep, bug, spike, task or term --
its title, which for a term is its meaning, and its bucket where it has one, a
task also its `state` (backlog, started, blocked or completed); every edge with its kind and its two ends, `from` and `to`; and the knowledge
lines as a list of their own. It reads the record and writes nothing; `json` is
its one format and its default, and another word is refused naming it. The order
is fixed, by id, so two runs on one record print the same bytes:

```sh
fgraph graph --format json
# {
#   "nodes": [
#     {
#       "id": "F-0001",
#       "kind": "feature",
#       "title": "Land work safely",
#       "bucket": "backlog"
#     },
#     {
#       "id": "S-0001",
#       "kind": "story",
#       "title": "Run the gate",
#       "bucket": "backlog"
#     },
#     {
#       "id": "T-0001",
#       "kind": "task",
#       "title": "Write the gate",
#       "bucket": "in-progress",
#       "state": "blocked"
#     },
#     {
#       "id": "gate",
#       "kind": "term",
#       "title": "a check every deliverable passes before it lands",
#       "bucket": null
#     }
#   ],
#   "edges": [
#     {
#       "kind": "under",
#       "from": "S-0001",
#       "to": "F-0001"
#     },
#     {
#       "kind": "about",
#       "from": "S-0001",
#       "to": "gate"
#     }
#   ],
#   "knowledge": [
#     {
#       "item": "S-0001",
#       "kind": "decision",
#       "noted": "2026-11-22T09:30:00+00:00",
#       "text": "a gate runs on main",
#       "about": [
#         "gate"
#       ],
#       "governs": []
#     }
#   ]
# }
```

Another tool asks the document what the record does not list in one view. With
`jq`, the work items about the term `gate`:

```sh
fgraph graph | jq -r '.edges[] | select(.kind == "about" and .to == "gate") | .from'
# S-0001
```

## Use

`make install` in a checkout puts its `fgraph` on the path of every repository.
It builds the wheel, as `make wheel` does, and runs `uv tool install --force
--reinstall` on it, which replaces an older install. The record of a repository
is then made there with `fgraph init`:

```sh
make install    # in the checkout of flowgraph
fgraph init     # in any repository, makes its .fgraph/
```

`fgraph` looks for the record in this order: `--dir PATH`, taken without a
search; then the folder the key `fgraph.record` of the git configuration of the
clone names, a path relative to the root of the repository, read whatever
directory of the work tree `fgraph` runs in; then `.fgraph/`, then `fgraph/`,
in the directory it runs in. When none is there, it exits 2 and says to run
`fgraph init` or to pass the path. The developer sets the key and `fgraph` only
reads it: it lives in `.git/config`, which git does not track, so each clone
names its own. A key that names a folder that is no directory exits 2 and falls
back to nothing:

```sh
fgraph                      # uses ./.fgraph/, else ./fgraph/
fgraph --dir path/to/record # uses the directory given, without a search
git config fgraph.record .dpopchev  # said once per clone
fgraph status               # reads <root>/.dpopchev, from any directory of the clone
# fgraph: error: git config fgraph.record names /path/to/project/.dpopchev, which is no directory -- run fgraph init, or name another with git config fgraph.record PATH
```

A command reads an id in any case, with its dash and its leading zeros left
out: `fgraph show f15`, `f-15`, `F15` and `f-0015` each show F-0015. What
`fgraph` prints is always the canonical form.

```sh
fgraph show f15             # shows F-0015, as fgraph show F-0015 does
```

A term is never named as such a spelling: `fgraph add term` refuses it, and a term
added before under such a name keeps its file.

```sh
fgraph add term f15 --means "a meaning"
# fgraph: error: 'f15' reads as the id F-0015: a term name is no id
```

`fgraph --help` prints the menu of the commands, and every command prints its
own help, its usage and its options, with `--help` or `-h`. Neither needs a
record:

```sh
fgraph start --help
# usage: fgraph start [-h] [--slug TEXT] [--agent NAME] [ID]
#
# positional arguments:
#   ID            the id of the work item, of the Task or of the Feature; left
#                 out, the first line of the Backlog that can start
#
# options:
#   -h, --help    show the help of this command and exit
#   --slug TEXT   the words of a work item's branch after its id, instead of its
#                 title's first four; of a Feature, those of its first work
#                 item; read with the development on
#   --agent NAME  the agent a work item is handed to, one word of at most 32
#                 letters, digits and . _ : / -; of a Feature, its first work
#                 item; read with the development on
```

`fgraph add --help` lists the kinds it adds, and each kind prints its own:
`fgraph add story --help`.

`fgraph init` makes the record of a directory: with the key `fgraph.record` set
and no `--dir`, the folder the key names, refused when that folder is there;
else `.fgraph/` in the directory it runs in, or in the one `--dir` names, which
still names the directory `.fgraph/` is made in. It prints the record it made. It
writes a `.fgraph/config.toml` at the defaults, commits on and development off,
and in a git work tree it commits that file as `chore: make the record`. A
directory that holds `.fgraph/` or `fgraph/` is refused, exit 2, naming it, and
nothing is written. It is the one command that runs with no record:

```sh
fgraph init
# record: /path/to/project/.fgraph
```

A repository that holds a `.board/` of board 1 keeps it whole as an archive: it
runs `fgraph init` beside it, points the record at it, and asks for an id of the
old board, which `fgraph show` answers by naming the archive and the command
that shows it:

```sh
fgraph init
fgraph config set archive.board .board
# set archive.board = ".board"

fgraph show W-123
# fgraph: error: W-123 is in the archive of board 1 at /path/to/project/.board -- show it with: uv run ~/.claude/skills/board/scripts/board.py --root /path/to/project show W-123
```

The open work is filed by hand with `fgraph add`; fgraph reads and writes no
file of the old board, and `fgraph show` alone answers an E-, W- or T- id so.

Add a Story with its
title and its one Given / When / Then, then list the record by bucket. The
title names the outcome: a directional verb, the target metric or behavior,
and the quantified shift or target state (`docs/domain-model.md`, Titles):

```sh
fgraph add story "Raise the Stories fgraph lists under Backlog from 0 to 1" \
  --given "a record with no items" \
  --when "a Story is added" \
  --then "fgraph status lists it under Backlog"
# added S-0001

fgraph status
# backlog (1)
#   S-0001  []  Raise the Stories fgraph lists under Backlog from 0 to 1
# in-progress (0)
# completed (0)
```

fgraph prints the four buckets in kebab case -- backlog, in-progress, completed, removed -- in
every text and every JSON document, the developer's decision of 2026-11-23 (S-0137); this
README names them in its prose as before.

A work item in Backlog is listed with the count of its Tasks in brackets, `[]` while it holds
none.

Write the Tasks of a Story, then show it with them. A Task title names the
output: an imperative verb, the specific artifact, and the target state or
constraint; `--output` says what is there once the Task is completed:

```sh
fgraph add task "Add the show command to src/flowgraph/cli.py, listing a Story" \
  --parent S-0001 \
  --output "changed: src/flowgraph/cli.py gains the show command"
# added T-0001 to S-0001

fgraph show S-0001
# S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
#   bucket       backlog
#   given        a record with no items
#   when         a Story is added
#   then         fgraph status lists it under Backlog
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     expected output  changed: src/flowgraph/cli.py gains the show command
```

`--description "<text>"` adds free text to a Story or a Task. A blank title or
part exits 2 and is named; so does a parent, or a Story to show, that the
record does not hold. Each Story is one file, `items/S-0001.toml`, in the
record, with its Tasks inside it; a Task id, `T-0001`, counts across the
record. In a git repository it counts across the worktrees too: the next Task
id is one above the highest in the record of main and of every worktree, so a
Task added on a branch never takes an id main hands out meanwhile.

With the development on (`development.enabled`), a Task is added with the
command that checks it, `--check COMMAND`, which `fgraph show` lists under the
Task; without it the add exits 2 naming `--check`, and a blank command is
refused. With the development off, `--check` exits 2 naming
`development.enabled`. A Task added before holds no check and is read, started
and completed as it was. `fgraph complete` of a Task that holds a check runs it,
in the worktree of its work item, and writes what it prints as it prints it. A
check that exits with another status than 0 refuses the complete with exit 2,
naming the Task, the command and the status; nothing is written and the Task
stays started. A check that passes completes the Task as before. Only the
complete of a Task runs a check: the complete of a work item and `fgraph land`
run none.

```sh
fgraph add task "Add the show command" --parent S-0001 \
  --output "changed: cli.py" --check "make test"
# added T-0001 to S-0001
fgraph complete T-0001 --commit 677f9b0
# fgraph: error: T-0001 cannot complete: its check "make test" exited with status 2
```

The complete of a Task also reads the files its commit changed and refuses one
the title, the output and the description of the Task do not name, by its path
from the top of the repository or by a directory with a trailing slash, a line
number or a test name after a colon cut, so `src/a.py:12` names `src/a.py`; the
files of the record are never asked; with the development off nothing is asked:

```sh
fgraph complete T-0001 --commit 3e9ae5c
# fgraph: error: T-0001 cannot complete: the commit 3e9ae5c changed what its brief does not name: docs/notes.md
```

A work item can depend on another: `--depends-on ID` of `fgraph add` and of
`fgraph amend`, once per work item it waits for, of any kind. The start of it
is refused, with exit 2, while one it depends on is not completed, and the
refusal names each with its bucket; `fgraph show` lists them with their bucket
as they are now:

```sh
fgraph add story "Raise the Stories fgraph lists under Backlog from 1 to 2" \
  --given "a record with a Story in Backlog" \
  --when "a second Story is added" \
  --then "fgraph status lists both under Backlog" \
  --depends-on S-0001
# added S-0002

fgraph add task "Add a second Story to the listing" --parent S-0002 --output "changed: cli.py"
# added T-0002 to S-0002

fgraph start S-0002
# fgraph: error: S-0002 cannot start: it depends on S-0001, in backlog

fgraph show S-0002
# S-0002  Raise the Stories fgraph lists under Backlog from 1 to 2
#   bucket       backlog
#   depends on   S-0001 (backlog)
#   ...

fgraph status --backlog
# backlog (2)
#   S-0001  [1 T]  Add the show command
# ~ S-0002  [1 T]  Raise the Stories fgraph lists under Backlog from 1 to 2
#   depends on S-0001
```

`fgraph status` marks the line of a work item in Backlog that waits: it starts
with `~`, and `depends on` and each id it depends on that is not
completed stand on a line of its own below it, beginning under its id. The mark is gone once each is completed; a block, marked `!`, says
`waiting on` a person. A Feature in Backlog carries it when its first work item
waits.

`fgraph status` counts every work item that can start now, within
`[development] parallel` less the work items started: first the work items in
Backlog of a started Feature, then the lines of the Backlog that `fgraph start`
would take, a work item that waits for nothing or a Feature whose first work
item waits for nothing, which takes one place. With `parallel = 3` and one work
item started, two lines can start (S-0003 and S-0004 below: S-0002 waits for
S-0004, and the limit leaves out S-0005). The text marks none of them: a line of the Backlog
that can start carries no mark, `[N T]` telling a planned line and `[]` one that is not; which
lines can start is read from `can_start` of the JSON, from the more-line and from `fgraph start`
with no id. The marks left are `@`, `~`, `!` and `=>`, the set the developer chose on
2026-11-23 from three (S-0139): a greater-than sign at the start of a line pasted into Markdown
opens a quote and a question mark is special in a search by a regular expression, and these
are neither. The developer dropped the mark of a line that can start, the equals sign, on
2026-11-24 (S-0152). With `parallel` left out every one that waits for nothing can start;
with the development off the next to start alone, as before. With the development on a line can
start only once planned: a work item holds a Task, and a Feature's work items in Backlog each
hold one; with `development.driver` set to `agent` planned also means each
work item holds a complexity, and with the driver a developer the Tasks alone
decide; a line not planned reads `[]`, and with the
development off the Tasks are not read. A line that can start which the top of the Backlog leaves
out is counted in its more-line, `... N more, M can start`, and not listed; a Backlog where
nothing can start counts none. No `next` command is added. This replaces the next to start
alone of S-0086.

```sh
fgraph status --backlog   # parallel = 3, S-0001 started, S-0002 waits for S-0004
# backlog (4)
# ~ S-0002  []  a second title
#   depends on S-0004
#   S-0003  []  a third title
#   S-0004  []  a fourth title
#   S-0005  []  a fifth title
# in-progress (1)
#   S-0001  0/1 T  a first title
```

`fgraph start` with no id starts the first of them, the `next_to_start` of the
JSON: the Backlog is a stack `fgraph reorder` reorders, and the start takes its
top that can start (S-0121). It says and does what `fgraph start` of that id
does: a Feature on top starts with its first work item, and `--slug` and
`--agent` are read as with an id. With the development on, a work item in
Backlog of a started Feature comes before the lines of the Backlog, and a line
not planned is passed over. With it off, the first line that waits for nothing
is taken, and one that holds no Task is refused in the words of its start. When
no line can start, it exits 2 and writes nothing, and names the first line of
the Backlog, whose own start says why.

```sh
fgraph start
# started S-0003
# branch wi/S-0003-a-third-title in /src/project.worktrees/S-0003-a-third-title
# fgraph: error: nothing to start: no line of the Backlog can start now -- fgraph start S-0002 says why its first line cannot
# fgraph: error: nothing to start: the Backlog is empty
```

`fgraph status --format json` prints the same view as one JSON document another
tool reads, such as the SessionStart hook of an agent harness: each bucket with
its count and every item of it, not the top of it, the Tasks of each work item with
their state, the reason and what a block waits on, the ids a work item waits for,
and the next to start. A Feature holds in `work_items` every work item under it,
in any state -- Backlog, started, blocked, completed or removed -- where the text
lists the started ones and, under a Feature in progress, the completed ones. `text` is the
default and prints what `fgraph status` has
always printed; another word is refused naming both, with exit 2. `--all` changes
nothing for JSON, which lists every item anyway, and neither does `--backlog`;
`fgraph watch` stays text.
The keys are sorted, so two runs on one record print the same bytes; every key is
listed in `docs/domain-model.md`, section Status as JSON.

The document lists in `can_start` the ids of every work item that can start now, in
the order of the Backlog, and `[]` for none; `next_to_start`
stays, the first of them or `null`. It lists in `ready_for_review` the ids of every work
item marked `@`, in the order the text lists them, and `[]` for none; no item holds a key
for it.

```sh
fgraph status --format json
# {
#   "buckets": [
#     {
#       "count": 1,
#       "items": [
#         {
#           "agent": null,
#           "block": null,
#           "commit": null,
#           "complexity": null,
#           "id": "S-0001",
#           "kind": "story",
#           "progress": {
#             "completed": 0,
#             "total": 1
#           },
#           "reason": null,
#           "state": "started",
#           "superseded_by": null,
#           "tasks": [
#             {
#               "commit": null,
#               "id": "T-0001",
#               "reason": "no key",
#               "state": "blocked",
#               "title": "Write the command",
#               "waiting_on": "developer"
#             }
#           ],
#           "title": "Add the show command",
#           "waits_for": []
#         }
#       ],
#       "name": "in-progress"
#     }
#   ],
#   "can_start": [],
#   "next_to_start": null,
#   "ready_for_review": []
# }
```

The example is cut to one bucket: the document always lists all four, in the order
of the flow, Removed too, with a count of 0 and an empty list when it holds nothing.

`fgraph amend S-0002 --depends-on S-0003` replaces what it depends on and
`--depends-on none` takes it all away. An id that is no work item of the
record, a removed work item, the work item itself and a work item that depends
on it, directly or through others, are refused at the write with exit 2, and
nothing is written. The start of a Feature starts its first work item, and the
next work item a completion starts is that of its Feature: both are refused as
the start of that work item is, and say so.

A record whose file was edited by hand or merged to name what is not there is
refused when it is read, by every command, with exit 2 and nothing written: a
parent, a dependency, a filed during, a superseded by, an amends or a term
that the record does not hold, an amends of a work item that is not completed, and a cycle
of dependencies or of one kind between terms. So is a file whose time holds no offset, a day alone as
`created = 2026-10-11`.

```sh
fgraph status
# fgraph: error: /src/project/.fgraph/items/B-0001.toml: amends names S-0001, which is not completed
# fgraph: error: /src/project/.fgraph/items/S-0002.toml: depends on names S-0099, which is not in the record
# fgraph: error: /src/project/.fgraph/items/S-0002.toml holds no Story: created = 2026-10-11 is a time with no offset: write it with one, as 2026-01-01 09:00:00+00:00
```

A file that holds a key or a state fgraph does not keep is refused in one line that
names the file and the key or the state, never the lines of the validator:

```sh
fgraph status
# fgraph: error: /src/project/.fgraph/items/S-0001.toml holds no Story: token is no key of the state backlog
# fgraph: error: /src/project/.fgraph/items/S-0001.toml holds no Story: started is missing, which the state blocked takes
```

A work item can name the one it was found during: `--filed-during ID` of
`fgraph add`, of every kind of work item, once. The other work item has no
say in it, and `fgraph show` lists it from both sides, the second read from the
record:

```sh
fgraph add bug "Cut the traceback fgraph prints on a blank title from 1 to 0" \
  --observed "it prints a traceback" --expected "it exits 2 and names the title" \
  --filed-during S-0001
# added B-0001

fgraph show B-0001
# B-0001  Cut the traceback fgraph prints on a blank title from 1 to 0
#   bucket       backlog
#   filed during S-0001
#   ...

fgraph show S-0001
# S-0001  ...
#   bucket       in-progress
#   filed here   B-0001
#   ...
```

An id that is no work item of the record and a removed work item are refused
with exit 2, and nothing is written. `fgraph amend` does not take it: when a
work item was found does not change.

A work item can name the completed one whose landed behavior it changes:
`--amends ID` of `fgraph add`, of every kind of work item, once. The other work
item has no say in it, and `fgraph show` lists it from both sides, the second
read from the record:

```sh
fgraph add story "Raise the kinds of work item fgraph adds from 4 to 5" \
  --given "a record" --when "fgraph add is run" --then "it adds the new kind" \
  --amends S-0001
# added S-0002

fgraph show S-0002
# S-0002  Raise the kinds of work item fgraph adds from 4 to 5
#   bucket       backlog
#   amends       S-0001
#   ...

fgraph show S-0001
# S-0001  ...
#   bucket       completed
#   amended by   S-0002
#   ...
```

An id that is no work item of the record and a work item that is not completed
are refused with exit 2, and nothing is written. `fgraph amend` does not take
it: which work item the new one changes does not change.

The prefix `S` of a Story is one letter, as that of every other kind, since
the developer's choice of 2026-11-21: `Q` for the Spike left `S` to the
Story, which until then was written `ST-0001`. The Stories of flowgraph
itself were renamed with their numbers kept, `ST-0036` to `S-0036`; the
commits made before keep `ST` in their messages and map to the new ids by
the number. `fgraph` reads `S` alone: an `items/ST-0001.toml` of an older
record is left alone as a file of a prefix no kind knows, neither read as a
Story nor renamed.

A record is layered by its configuration, the file `.fgraph/config.toml`, a
table per layer: the developer's request of 2026-11-21. fgraph keeps the
items and their lifecycle always. The development beside the source code --
the branch and the worktree of a start, the scoping of a branch, the landing
-- is a layer the record turns on:

```toml
[development]
enabled = true
```

A record without the file, or without the key, has the development off. A
start of a Story is then a write as any other: committed on `main`, with no
branch, no worktree and no warning. Its Tasks are written on `main`, it is
completed with `fgraph complete`, and `fgraph land` exits 2 naming the set
that turns the development on:

```sh
fgraph start S-0001
# started S-0001

fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# fgraph: error: S-0001 cannot land: the development is off -- run fgraph config set development.enabled true
```

The commit is the evidence of the development, so with the development off
`fgraph complete` takes none, of a Task as of a Story, as shown further down
with the complete.

With `enabled = true` the start, the scoping and the landing are as the rest
of this page shows them: wherever it names a branch, a worktree or a landing,
the record has the development on. The start of a Story is held to `main`
either way, and it alone: no other write is, the reading decided when S-0039
was ordered. The file is no longer written by hand: `fgraph config set
development.enabled true` writes the key, as shown further down with `fgraph
config`, and the record of flowgraph itself holds it. Each key below is shown
as the file holds it once it is set.

The development limits the work items started at once when the record says
how many:

```toml
[development]
enabled = true
parallel = 1
```

`parallel` is how many work items are started at once, a whole number of 1 or
more. The started work items are those of every kind -- Story, Upkeep, Bug,
Spike -- that `fgraph status` lists under InProgress. With as many started
already, the start of one more exits 2 naming the key, its number and each
started work item; nothing is written and no branch is made:

```sh
fgraph start S-0002
# fgraph: error: S-0002 cannot start: development.parallel = 1, started already: S-0001
```

It starts once one of them is completed or landed. The key has no default:
left out, nothing limits the started work items. It is a key of the
development, so it limits nothing with the development off. The start of a
Task is neither counted nor limited by it: a Story has one started Task at a
time whatever the key, as shown further down. The start of a Feature starts
one work item, so it is refused as the start of that one is, naming the
Feature (further down). The next work item of a Feature, which the completion
of the one before starts, stays in Backlog when the key refuses it, and the
completion stands (further down).

The development says how a landing merges when the record names a way:

```toml
[development]
enabled = true
merge = "squash"
```

`merge` is one of four words. Each is a way `fgraph land` puts the work of
the branch on `main`:

| `merge`                     | `main` gains                                               | `--message`                 |
| --------------------------- | ---------------------------------------------------------- | --------------------------- |
| `merge-commit`, the default | one merge commit of the branch, with two parents           | needed: it words the commit |
| `squash`                    | one commit of its own that holds the work, with one parent | needed: it words the commit |
| `fast-forward`              | no new commit: `main` moves to the tip of the branch       | refused: no commit to word  |
| `pull-request`              | nothing from fgraph: its pull request merges the branch    | refused: no commit to word  |

Left out, the key is `merge-commit`, the one merge a landing made before the
key. Whatever the way, the Story is completed at the commit `main` is then
on, the record is committed, and the worktree and the branch are removed, as
shown further down with the landing. A landing by `fast-forward` exits 2,
with nothing merged, when `main` holds a commit the branch lacks. It is a key
of the development, so it says nothing with the development off. Any other
word exits 2 naming the key, whatever the command:

```sh
fgraph status
# fgraph: error: /src/project/.fgraph/config.toml: development.merge is "rebase": it takes merge-commit, squash, fast-forward or pull-request
```

The development gates a landing when the record names a command:

```toml
[development]
enabled = true
gate = "make check"
```

`gate` is one command of the record, a command line run at a landing. It is
the reading, decided when S-0042 was ordered, of the developer's words of
2026-11-21 on starting a work item, "checks if criteria are met before
closing": the gate is apart from the check of a Task, which the complete of that
Task runs, and the Given / When / Then of the Story is neither run nor
confirmed by it. `fgraph land` runs the gate
through the shell at the top of the work tree of `main`, once the work of the
branch is merged there and before the landing is committed or the Story
completed, so the gate checks the tree `main` will have. Its output is
written as the gate writes it. A gate that exits with another status than 0
leaves `main` where it was, whatever the `merge`, and the landing exits 2
naming the command and its status:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# fgraph: error: S-0001 cannot land: development.gate = "make check" exited with status 2
```

Nothing is merged then: the Story stays started, with its branch and its
worktree, to be fixed there and landed again. A gate that passes lands as the
landing is shown further down. The Tasks completed stay the first rule of a
landing: a Story with a Task to complete is refused for it, and its gate is
not run. The key has no default: left out, a landing runs no gate. It is a
key of the development, so it gates nothing with the development off. An
empty command line exits 2 naming the key, whatever the command:

```sh
fgraph status
# fgraph: error: /src/project/.fgraph/config.toml: development.gate is "": it takes a command line
```

The delivery pushes a landing to the remote of `main` when the record says so:

```toml
[development]
enabled = true

[delivery]
push = true
```

`push` is `true` or `false`, `false` by default, so a record that names none
pushes nothing, as a landing did before the key. With it `true`, `fgraph
land` pushes `main` to the branch it tracks on its remote right after the
merge and before the write that completes the Story, and again as its last
step, to carry that write: after the removal of its worktree and its branch,
and the branch of the next work item of a Feature. The landing names the
remote once, on a line of its own:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# landed S-0001 at 3e9ae5c
# run: a Story is added -> fgraph status lists it under Backlog
# pushed main to origin
```

With `push` `true`, a `main` that tracks no branch of a remote is refused
before the merge, exit 2, with nothing merged, the Story started and its
branch and worktree as they were. Give `main` an upstream, `git push
--set-upstream origin main`, or turn the push off:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# fgraph: error: S-0001 cannot land: main tracks no branch of a remote to push to -- run git push --set-upstream <remote> main, or fgraph config set delivery.push false
```

A push git refuses -- a remote it cannot reach -- before the write that
completes leaves the Story started and merged: `main` holds the merge, nothing
is undone, since history only moves forward, and its branch and worktree stay.
The landing exits 2 naming the git command and its error, then that `main` is
not pushed and the Story merged and not completed. Run `fgraph land` again
once the remote is there: it takes the landing up at the commit `main` is on,
pushes and completes the Story:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# fgraph: error: git push --quiet origin refs/heads/main:refs/heads/main failed: fatal: Could not read from remote repository. -- main is not pushed -- S-0001 is merged at 3e9ae5c and not completed -- run fgraph land S-0001 again
```

The last push, once the Story is completed, refused leaves the landing whole,
with the push left to you, `git push` once the remote is there; it exits 2
ending `-- S-0001 is landed at 3e9ae5c, main is not pushed`.

It is a step of a landing, so it pushes nothing with the development off,
where it is held as written and the landing is refused as above.

`fgraph release` tags the trunk: it makes an annotated `v*` tag on the head of
`main`, in the checkout of `main`, and prints it. The version is the next
minor when a Story or a Bug was completed since the last `v*` tag, else the
next patch, and `v0.1.0` when the repository holds no `v*` tag yet:

```sh
fgraph land S-0002 --message "feat: land the Stories listed under InProgress"
# landed S-0002 at 85c8d69
# run: a second Story is added -> fgraph status lists both under Backlog

fgraph verify S-0002 --yes "make check: all checks passed"
# verified S-0002

fgraph release
# tagged v0.2.0 at 3becb1b

git tag -n1
# v0.1.0          release v0.1.0
# v0.2.0          release v0.2.0
```

An Upkeep or a Spike alone since the last tag tags the next patch, `v0.2.1`
after `v0.2.0`. A work item is completed since the last tag unless that tag
holds the commit it is completed at, so one landed just before the tag is
never counted again; one that names no commit, as one completed with the
development off, is taken by its completed time against the time of the tag.
`--version` names the version in place of the next one, as `--version v1.0.0`
for a major.

A tag is never moved or deleted: a version that is tagged already is refused,
and so is a release with nothing completed since the last tag, and one while a
Story, a Bug or an Upkeep completed since the last tag holds no answer of
`fgraph verify`, yes or no, each one named. Each exits 2
and tags nothing, and so does a release run off the checkout of `main`, as a
start is:

```sh
fgraph release
# fgraph: error: nothing is completed since v0.2.1: no release -- complete a work item first

fgraph release --version v0.2.1
# fgraph: error: v0.2.1 is tagged already: a tag is never moved or deleted -- name another with --version

fgraph release
# fgraph: error: S-0003 not verified since v0.2.1: no release -- run fgraph verify on each first
```

A Spike closes on its own answer and is not asked; a no is an answer, and the
Bug it files is its own work item. With no `v*` tag yet every completed Story,
Bug and Upkeep is asked. The tag a landing makes under `[delivery] tag` asks
for none.

With `[delivery] push = true` the tag is pushed to the remote `main` tracks,
once it is made, on a line of its own. A push git refuses leaves the tag as
it is, made and not pushed, and exits 2 saying so: `git push origin v0.2.2`
is left to you.

```sh
fgraph release
# tagged v0.2.2 at 94959ae
# pushed v0.2.2 to origin
```

A version the project keeps in a file of its own, as `pyproject.toml`, is not
bumped by `fgraph release`.

The delivery tags `main` at a landing when the record says so:

```toml
[delivery]
push = true
tag = "close"
```

`tag` is `feature-close`, `close` or `none`, `none` by default, so a record
that names none tags nothing, as a landing did before the key. With
`feature-close`, the landing of the last work item of a started Feature -- the
write that completes the Feature -- is tagged with the tag `fgraph release`
makes; with `close` so is the landing of a work item that stands alone, and a
work item under a Feature that is not its last tags nothing under either. The
version is the next minor for a Story or a Bug and the next patch for an Upkeep
or a Spike, counted with the work completed since the last `v*` tag, and
`v0.1.0` when there is none. The tag is on the commit of the landing, made
after the first push of `main` and before the write that completes the work
item, and pushed itself under `push = true`; so the record inside the tagged
tree still lists the work item InProgress, the cost of completing after the
tag. A tag made by a landing bumps no version in a file of the project:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# landed S-0001 at 3e9ae5c
# run: a Story is added -> fgraph status lists it under Backlog
# pushed main to origin
# tagged v0.1.0 at 3e9ae5c
# pushed v0.1.0 to origin
```

A landing of the last Story of a Feature says the Feature completed after the
first line, as `completed F-0001 at 3e9ae5c`. A tag git refuses, or its push,
leaves the Story merged and not completed, as a push of `main` refused does,
and exits 2 ending with its line, `-- v0.1.0 is tagged at 3e9ae5c, it is not
pushed -- S-0001 is merged at 3e9ae5c and not completed -- run fgraph land
S-0001 again`; the Feature stays as it was. Run `fgraph land` again once the
cause is gone: a landing taken up whose commit the last `v*` tag is on makes no
second tag and pushes that one. A push of `main` refused makes no tag. It is a
step of a landing, so with the development off it tags nothing: `fgraph
complete` of the last work item completes the Feature with no tag, and
`fgraph release` tags it. Any other value is refused naming the three,
`delivery.tag is "sometimes": it takes feature-close, close or none`.

The commits of the record are a layer the record turns off:

```toml
[git]
commit = false
```

A record without the file, or without the key, has them on: inside a git work
tree that does not ignore the record, fgraph commits every write of it, as
shown further down. With `commit = false` no write of the record is
committed: `add`, `amend`, `remove`, `reorder`, `start`, `block`, `unblock`,
`complete` and `config set` leave their files changed in the work tree, with
no commit and no warning, as the write of a record git ignores. Committing
them is then yours:

```sh
fgraph add story "Raise the Stories fgraph lists under Backlog from 0 to 1" \
  --given "a record with no items" --when "a Story is added" \
  --then "fgraph status lists it under Backlog"
# added S-0001

git status --short --untracked-files=all
# ?? .fgraph/items/S-0001.toml
```

The layers build on each other: the branch of a Story carries its record, so
the development needs the commits. A `config.toml` that sets `[development]
enabled = true` with `[git] commit = false` exits 2 naming both keys, whatever
the command:

```sh
fgraph status
# fgraph: error: /src/project/.fgraph/config.toml: development.enabled is true while git.commit is false: the development needs the commits of the record
```

So a landing with the commits off names both sets it takes, in their order:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# fgraph: error: S-0001 cannot land: the development is off -- run fgraph config set git.commit true, then fgraph config set development.enabled true
```

A `config.toml` fgraph refuses -- a table or a key the configuration does not
have, a value of another type than the key takes, a `parallel` below 1, a
`merge` that is none of its three words, an empty `gate`, a text that is no
TOML -- exits 2 naming the file and the key, whatever the command:

```sh
fgraph status
# fgraph: error: /src/project/.fgraph/config.toml: development.enable is no key of the configuration

fgraph status
# fgraph: error: /src/project/.fgraph/config.toml: development.parallel is 0: it takes a whole number of 1 or more
```

The configuration is shown and set through `fgraph config`, so
`.fgraph/config.toml` is no longer written by hand. `fgraph config show` lists
every key of the configuration, dotted, with its value as the file writes it,
one a line. A key the file lacks is listed at its default, so a record without
the file lists the defaults:

```sh
fgraph config show
# git.commit = true
# development.enabled = false
# development.parallel = none
# development.merge = "merge-commit"
# development.gate = none
# development.driver = "developer"
# development.mode = "branch"
# development.branch_max = none
# development.approver = "agent"
# delivery.push = false
# delivery.tag = "none"
# archive.board = none
# status.backlog = 1
# status.in-progress = "all"
# status.completed = 5
# status.removed = 5
# watch.buckets = "backlog, in-progress, completed, removed"
```

`none` is how a key that holds no value is listed: `parallel` without a
limit, `gate` without a command. It is no value of the file, so a gate named
`"none"`, listed in its quotes, is not mistaken for it.

`development.driver` names who drives the development: `developer`, the default,
or `agent`. It is held as written with the development off, and a record that
leaves it out works as before: no command asks for a complexity, an agent or a
goal. Set to `agent` with the development on, it asks a complexity of every work
item to start: `fgraph start S-0002` of one in Backlog that holds a Task and no
complexity exits 2 with `S-0002 has no complexity to start with: set it with
fgraph amend S-0002 --complexity low, medium or high`, and `fgraph status`
marks no such work item.

The four keys of `[status]` say how many lines `fgraph status` and `fgraph watch`
list under each bucket, the first ones, `all` for every one; left out they are 1,
`all`, 5 and 5, the frame of F-0017. A flag wins over a key for that run: `--all`
lists every line of every bucket and `--backlog` the whole Backlog.
`fgraph status --format json` lists every item whatever they say.
`watch.buckets` names the buckets a frame of `fgraph watch` shows, `backlog`,
`in-progress`, `completed` and `removed`, in the order of the flow whatever the
order written; left out it names the four, and `fgraph status` lists every
bucket whatever it says.

`development.mode` is where a work item is developed: `branch`, the default, or
`trunk`, for a repository whose work tree is the live artifact. On the trunk a
start is committed on `main` and makes no branch and no worktree, one work item
is started at a time, and `fgraph land` is refused:

```sh
fgraph config set development.mode trunk
# set development.mode = "trunk"

fgraph start S-0001
# started S-0001

fgraph complete S-0001 --commit 3e9ae5c
# completed S-0001 at 3e9ae5c

fgraph land S-0001
# fgraph: error: S-0001 cannot land: development.mode = trunk makes no branch to land -- complete it with fgraph complete S-0001 --commit SHA
```

`fgraph config set KEY VALUE` writes that one key into the file and keeps the
others; a record without the file gains it:

```sh
fgraph config set development.enabled true
# set development.enabled = true

fgraph config set development.gate "make check"
# set development.gate = "make check"

fgraph config show
# git.commit = true
# development.enabled = true
# development.parallel = none
# development.merge = "merge-commit"
# development.gate = "make check"
# development.driver = "developer"
# development.mode = "branch"
# development.branch_max = none
# development.approver = "agent"
# delivery.push = false
# delivery.tag = "none"
# archive.board = none
# status.backlog = 1
# status.in-progress = "all"
# status.completed = 5
# status.removed = 5
# watch.buckets = "backlog, in-progress, completed, removed"
```

VALUE is a text, read by what its key takes and never guessed from the text,
so `fgraph config set development.gate true` names the command `true`:

| Key                    | VALUE                                                      | Set as                                            |
| ---------------------- | ---------------------------------------------------------- | ------------------------------------------------- |
| `git.commit`           | `true` or `false`                                          | `fgraph config set git.commit false`              |
| `development.enabled`  | `true` or `false`                                          | `fgraph config set development.enabled true`      |
| `development.parallel` | a whole number of 1 or more                                | `fgraph config set development.parallel 2`        |
| `development.merge`    | `merge-commit`, `squash`, `fast-forward` or `pull-request` | `fgraph config set development.merge squash`      |
| `development.gate`     | a command line, one argument of the shell                  | `fgraph config set development.gate "make check"` |
| `development.driver`   | `developer` or `agent`                                     | `fgraph config set development.driver agent`      |
| `development.mode`     | `branch` or `trunk`                                        | `fgraph config set development.mode trunk`        |
| `development.branch_max` | a whole number of days as `1d`                           | `fgraph config set development.branch_max 1d`     |
| `development.approver` | `agent` or `developer`                                     | `fgraph config set development.approver developer` |
| `delivery.push`        | `true` or `false`                                          | `fgraph config set delivery.push true`            |
| `delivery.tag`         | `feature-close`, `close` or `none`                         | `fgraph config set delivery.tag close`            |
| `archive.board`        | the path of the `.board/` of board 1                       | `fgraph config set archive.board .board`          |
| `status.backlog`       | a whole number of 1 or more, or `all`                      | `fgraph config set status.backlog 3`              |
| `status.in-progress`   | a whole number of 1 or more, or `all`                      | `fgraph config set status.in-progress all`        |
| `status.completed`     | a whole number of 1 or more, or `all`                      | `fgraph config set status.completed 10`           |
| `status.removed`       | a whole number of 1 or more, or `all`                      | `fgraph config set status.removed 5`              |
| `watch.buckets`        | the buckets to show, separated by commas                   | `fgraph config set watch.buckets "backlog, in-progress"` |

The whole file is read back as a configuration before it replaces the one in
the record. A key the configuration does not have, a value the key does not
take and a combination it refuses -- the development on with the commits off
-- exit 2 naming the key, with nothing written:

```sh
fgraph config set development.enable true
# fgraph: error: development.enable is no key of the configuration

fgraph config set development.parallel 0
# fgraph: error: development.parallel is 0: it takes a whole number of 1 or more

fgraph config set development.enabled yes
# fgraph: error: development.enabled is "yes": it takes true or false

fgraph config set git.commit false
# fgraph: error: development.enabled is true while git.commit is false: the development needs the commits of the record
```

`fgraph config unset KEY` takes a key back to its default: it removes the key
from the file, and a table left with no key with it. A key with no default,
`development.parallel` or `development.gate`, is then `none` again. It is
committed as a set is, under `chore: unset development.gate in the record`,
and a key the configuration does not have exits 2 naming it:

```sh
fgraph config unset development.gate
# unset development.gate = none
```

A set is a write of the record as any other. In a git repository fgraph
commits the file alone, under `chore: set development.enabled in the record`,
and a set to the value the file writes already changes nothing and makes no
commit. Whether a set is committed is read from the configuration it leaves:
one that turns the commits off, `fgraph config set git.commit false`, is left
uncommitted as every write after it, and one that turns them back on is
committed, so fgraph never commits a `config.toml` that turns its commits
off. On the branch of a Story the configuration is no file of its scope, and
a set exits 2 naming the Story the branch owns; `fgraph config show` runs
anywhere:

```sh
fgraph config set development.parallel 2
# fgraph: error: the configuration is not set here: the branch wi/S-0001-raise-the-stories-fgraph writes S-0001 alone
```

A key is taken back to its default by `fgraph config unset KEY`, which leaves
it out of the file, or by setting that default, `fgraph config set
development.merge merge-commit`, which writes it there. `parallel` and `gate`
have no default to set: an unset alone takes them back to none. A set or an
unset writes the file whole from its keys, so a comment written in it is not
kept. A `config.toml` fgraph refuses is refused by `fgraph config` too, as by
every command, and is mended in the file.

Start a Story once it has a Task, then start its Tasks one by one. `fgraph
start` takes a Story id or a Task id, or none, and then the first `fgraph status`
marks; with the development on, the start of a Story names its branch:

```sh
fgraph start S-0001
# started S-0001
# branch wi/S-0001-raise-the-stories-fgraph in /src/project.worktrees/S-0001-raise-the-stories-fgraph

fgraph start T-0001
# started T-0001 of S-0001

fgraph status
# backlog (0)
# in-progress (1)
#   S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#     => T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
# completed (0)
```

A work item under InProgress is listed with its progress, `0/1 T`: its Tasks
completed of all it holds. One of three completed reads `1/3 T`, so two are
still to be completed; a started or a blocked Task is not completed yet. A
removed Task is not counted at all (`fgraph remove`, below).

Under it comes the Task being worked, marked `=>`: the started Task of the
work item. A Task in Backlog or completed is not listed, and a Task line does
not count toward the top of a heading (below).

A started work item that holds a Task, with every Task completed, is ready for
review, and `fgraph status` marks it `@` in the first column of its line, beside
`~` and `!`. `fgraph watch` shows it the same, with the development on or
off, alone or under a started Feature. A work item with no Task, or with a Task
still in Backlog, started or blocked, is not marked, and nor is the line of a
Feature. The mark is read from the Tasks at each listing and kept in no file:

```sh
fgraph status
# backlog (0)
# in-progress (2)
# @ S-0001  1/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#   S-0002  1/2 T  Add the show command to src/flowgraph/cli.py
# completed (0)
```

With the development on and `development.branch_max` set to an age such as
`1d`, a line of its own below the line of a started or blocked work item says so
once more than that many days have passed since it was started. It is a word and no
refusal: nothing is held back for an old branch.

```sh
fgraph status
# backlog (0)
# in-progress (1)
#   S-0001  1/2 T  Raise the Stories fgraph lists
#   its branch is older than 1d
# completed (0)
```

When the record is inside a git work tree, starting a Story commits its file
alone as `chore: start S-0001 in the record`, as fgraph commits every write
(below). With the development on it then checks out the branch
`wi/<id>-<slug>` at that commit in a worktree beside the checkout,
`<parent>/<checkout>.worktrees/`. The slug is the first four words of the
title, lower-cased and kept to their letters and digits; `--slug
branch-on-start` gives another. Outside a work tree the Story starts as
before and, with the development on, fgraph warns that no branch was made. A
git step refused exits 2 and names the git command: a commit refused puts the
file back as it was, a worktree refused leaves the start committed.

A start whose branch is there already is refused before it writes: nothing is
written and the Story stays in Backlog. Delete the branch or give another
`--slug`; the start takes over no branch that is there.

```sh
git branch wi/S-0001-branch-on-start
fgraph start S-0001 --slug branch-on-start
# fgraph: error: S-0001 cannot start: the branch wi/S-0001-branch-on-start is there already -- delete it or give another --slug
```

The rules of a branch that follow are those of a record with the development
on: with it off fgraph makes no branch `wi/<id>-<slug>` and no worktree, so
every write is taken on `main`. A start given `--slug` then exits 2 naming the
key, of a work item as of a Feature, and starts nothing:

```sh
fgraph start S-0001 --slug branch-on-start
# fgraph: error: S-0001 takes no --slug: the development is off, so its start makes no branch -- set development.enabled = true in /src/project/.fgraph/config.toml
```

A start can name the agent the work item is handed to, with `--agent`: one
opaque word of at most 32 letters, digits and `. _ : / -`, which fgraph does
not interpret. The started work item holds it, the completed one keeps it,
`fgraph show` lists it on a line `agent`, `fgraph status` lists it as
`[sonnet-a1]` between the progress and the title, and every work item of
`fgraph status --format json` holds `agent`, the name or `null`. On a Feature
the agent goes to the first work item the Feature starts. The start is read
with the development on: it exits 2 and writes nothing for a Task, for a name
that is no agent and with the development off, naming the key. A second start
of a work item an agent holds is refused naming it, and of two starts run at
one time one holds the work item, by the lock of a write (B-0035). The start a
completion, a landing or an unblock makes names no agent:

```sh
fgraph start S-0001 --agent sonnet-a1
fgraph status               # the line:  S-0001  0/1 T  [sonnet-a1]  Raise the Stories fgraph lists
fgraph show S-0001          # the line: agent  sonnet-a1
fgraph start T-0001 --agent sonnet-a1
# fgraph: error: --agent names the agent of a work item: T-0001 is a Task
fgraph start S-0001 --agent opus-b2
# fgraph: error: S-0001 is started already: sonnet-a1 holds it
```

A started work item is handed to another agent, or to one when it holds none,
with `fgraph hand ID --agent NAME`, the name required. It says `handed S-0001
to opus-b2` and commits `chore: hand S-0001 to opus-b2 in the record`; the agent
is replaced and the file keeps no history of the ones before it. With the
development on it is written where the Tasks of the work item are: in its
worktree, or from main with `--dir` on the `.fgraph` of that worktree. On main
without it, the refusal of main names the worktree. It exits 2 and writes
nothing for a work item in Backlog, completed or removed, for a Task or a
Feature, for a name that is no agent and with the development off:

```sh
fgraph hand S-0001 --agent opus-b2    # in the worktree of S-0001
# handed S-0001 to opus-b2
fgraph --dir /src/project.worktrees/S-0001-raise-the-stories-fgraph/.fgraph hand S-0001 --agent opus-b2
# handed S-0001 to opus-b2
fgraph hand S-0001 --agent opus-b2    # on main
# fgraph: error: S-0001 is started: its Tasks are written in its worktree, /src/project.worktrees/S-0001-raise-the-stories-fgraph
```

On the branch of a started Story, `wi/S-0001-<slug>`, fgraph writes that
Story alone: its Tasks are added, started and completed there. A Task for
another Story, a new Story or a reorder of the Backlog exits 2 there and
names the Story the branch owns:

```sh
fgraph add task "Add the show command" --parent S-0002 --output "changed: cli.py"
# fgraph: error: S-0002 is not written here: the branch wi/S-0001-raise-the-stories-fgraph writes S-0001 alone
```

A Story starts on main alone, with the development on or off. `fgraph start`
of a Story exits 2 in a work tree on any other branch, with nothing written
and no branch made, and names the work tree to start it in:

```sh
fgraph start S-0002
# fgraph: error: S-0002 starts on main, in /src/project: /src/project.worktrees/S-0001-raise-the-stories-fgraph is on wi/S-0001-raise-the-stories-fgraph
```

The start of a Task is not checked against main: a Task starts on the branch
of its Story. A Feature starts on main alone as a Story does, since its start
starts its first work item (further down).

A Task of a started Story that has a worktree is written there: added,
started and completed in it, and its block and its unblock are written there
too. On main the same write exits 2 and names the worktree, and so do the
block and the unblock of its Task, whatever the copy of main holds of the Task:

```sh
fgraph add task "Add the show command" --parent S-0001 --output "changed: cli.py"
# fgraph: error: S-0001 is started: its Tasks are written in its worktree, /src/project.worktrees/S-0001-raise-the-stories-fgraph
fgraph unblock T-0001
# fgraph: error: S-0001 is started: its Tasks are written in its worktree, /src/project.worktrees/S-0001-raise-the-stories-fgraph
```

A started Story whose branch has no worktree is written on main as before,
and so is one started with the development off, which has no branch.

`fgraph status` and `fgraph show` on main read a started Story where its Tasks
are written: they list the Tasks of the Story as its worktree holds them,
committed or not, so the progress, the Task being worked and the bucket and
the commit of each Task are current before the landing. A worktree that holds
no file of the Story leaves both to read it from the record of main:

```sh
cd /src/project.worktrees/S-0001-raise-the-stories-fgraph
fgraph start T-0001
# started T-0001 of S-0001

cd /src/project
fgraph status
# backlog (0)
# in-progress (1)
#   S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#     => T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
# completed (0)

fgraph show S-0001
# ...
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     bucket           in-progress
#     expected output  changed: src/flowgraph/cli.py gains the show command
```

Run in the worktree of a Story, `fgraph status` and `fgraph watch` list the record of main
there, each started Story read from its own worktree, and `fgraph show` reads the record of
that worktree.

`fgraph show` then names the bucket of the Story and of each Task that has
left Backlog (`    bucket           in-progress`). A start exits 2 and names
why when the Story has no Task, when a Task's Story is still in Backlog, when
the item is started or completed already, or when the record does not hold
it.

A Story holds at most one started Task. Starting a second one exits 2 and
names the started Task, until that one is completed or blocked:

```sh
fgraph start T-0002
# fgraph: error: T-0002 cannot start: T-0001 is started -- complete or block it first
```

Complete each Task with the commit that holds its work, then the Story with
the commit on `main` that holds it. `--commit` is a sha of 7 to 40 hex digits;
with the development on `fgraph` looks it up in git, and with it off it is kept
as given. With the development on that commit holds only files the Task names:

```sh
fgraph complete T-0001 --commit 3e9ae5c
# completed T-0001 of S-0001 at 3e9ae5c

fgraph complete S-0001 --commit 677f9b0
# completed S-0001 at 677f9b0

fgraph status
# backlog (0)
# in-progress (0)
# completed (1)
#   S-0001  677f9b0  Raise the Stories fgraph lists under Backlog from 0 to 1
```

`fgraph show` names the commit of the Story and of each completed Task. A
complete exits 2 and names why when the item is still in Backlog, when a
Story has Tasks not completed, when the item is completed already, when the
commit is no sha, or, with the development on, when the repository does not hold
the commit or, for a Task, when the commit changed a file its brief does not
name. A completed Story takes no new Task.

The commit is the evidence of the development: the work beside the record
that the item is completed with. So `fgraph complete` needs `--commit` with
the development on, of a Task as of a Story, and without it exits 2 naming
the option and the key:

```sh
fgraph complete T-0001
# fgraph: error: T-0001 is completed with --commit: the development is on, development.enabled = true

fgraph complete T-0001 --commit c6e0f15
# fgraph: error: T-0001 cannot complete: the repository holds no commit c6e0f15
```

With the development off there is no such work to name, and `fgraph complete`
takes no commit, of a Task as of a Story. The item is completed without one:
`fgraph status` lists the Story under Completed with its id and its title
alone, and `fgraph show` lists no commit line of it nor of its Task:

```sh
fgraph complete T-0001
# completed T-0001 of S-0001

fgraph complete S-0001
# completed S-0001

fgraph status
# backlog (0)
# in-progress (0)
# completed (1)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1

fgraph show S-0001
# S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
#   bucket       completed
#   given        a record with no items
#   when         a Story is added
#   then         fgraph status lists it under Backlog
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     bucket           completed
#     expected output  changed: src/flowgraph/cli.py gains the show command
```

A `--commit` given with the development off is still kept as the evidence, not
looked up, and status and show list it. The file of an item completed without a commit
holds no `commit` key.

A work item keeps what the work learned as lines of knowledge. `fgraph note`
appends a finding, a decision or a deviation to a work item in any state, Completed and Removed included,
as one write and one commit of the record; `fgraph show` lists the lines after
the Tasks, each with its kind, the date it was noted and its text, and no
heading when there is none. A note takes at most one of `--standing` and
`--open`, the mark of the line, listed after its text. A note takes exactly one of `--finding`,
`--decision`, `--deviation` and `--progress`, with its text:

```sh
fgraph note S-0001 --finding "the file holds the lines in the order noted"
# noted S-0001

fgraph note S-0001 --decision "keep one store"
# noted S-0001

fgraph note S-0001 --deviation "the second Task was dropped"
# noted S-0001

fgraph show S-0001
# ...
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     expected output  changed: src/flowgraph/cli.py gains the show command
# Knowledge (3)
#   finding  2026-11-22  the file holds the lines in the order noted
#   decision  2026-11-22  keep one store
#   deviation  2026-11-22  the second Task was dropped
```

A Feature keeps knowledge lines as a work item does, in any state, and
`fgraph show` lists them after its work items:

```sh
fgraph note F-0001 --decision "the budget is agreed"
# noted F-0001

fgraph show F-0001
# ...
# Work items (2)
#   S-0001  Add the show command to src/flowgraph/cli.py  completed
#   S-0002  Add the note command to src/flowgraph/cli.py  backlog
# Knowledge (1)
#   decision  2026-11-22  the budget is agreed
```

A work item also keeps progress lines, where the work stands: a hand-off, a
structure note, the red line of a Task. `fgraph note ID --progress TEXT` keeps
one on a work item in any state, or on a Task of it, kept on its work item and
naming the Task, as one write and one commit. A progress line is no knowledge:
`fgraph knowledge` never lists it, and it takes no `--about`, no `--governs`,
no `--standing` and no `--open`, each refused naming the option, as
`a progress line takes no --standing: it is no knowledge line`; a Feature takes
none. `fgraph show` lists the lines of a Task under it, and
those of the work item under `Progress (n)` after the knowledge lines:

```sh
fgraph note S-0001 --progress "the parser is read; next the show"
# noted S-0001

fgraph note T-0001 --progress "red: 1 failed"
# noted T-0001 of S-0001

fgraph show S-0001
# ...
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     bucket           in-progress
#     expected output  changed: src/flowgraph/cli.py gains the show command
#     progress         2026-11-22  red: 1 failed
# Progress (1)
#   2026-11-22  the parser is read; next the show
```

A line of knowledge may be marked when it is noted: `--open` for a line not
settled yet, `--standing` for one that holds until a later line supersedes it.
`fgraph show` and `fgraph knowledge` list the mark right after the text:

```sh
fgraph note S-0001 --finding "is the queue one file too" --open
# noted S-0001

fgraph note S-0001 --decision "keep one file per item" --standing
# noted S-0001

fgraph show S-0001
# ...
# Knowledge (2)
#   finding  2026-11-22  is the queue one file too  (open)
#   decision  2026-11-22  keep one file per item  (standing)
```

`fgraph knowledge` lists the lines of every work item and every Feature of the
record, the last noted first, each with its date, its kind, the ref of the line
and its text: the id of its item, `#` and its place among the lines of that
item, counted from 1 in the order noted, as `S-0001#2`. `--kind` narrows the list to `finding`, `decision` or `deviation`;
another word exits 2 naming the three. `fgraph knowledge --live` lists the live
lines alone, those no later line supersedes, a line with no mark among them; it is
the list to read at the start of a session. `fgraph knowledge --search TEXT` narrows
the list to the lines whose text holds the text, whatever the case of either,
as a part of a word too. `--kind`, `--about` and `--search` narrow the same
list, a line being listed when it meets each one given. Only the text of the
line is searched, as it is listed (the decision of a Spike with its answer),
not the title or the id of its item, its kind or the terms it is about. With
no such line it prints one line and exits 0; a blank text exits 2. The decision
of a completed Spike is listed among the decisions at the time the Spike was
completed, under the id of the Spike with no ref, and stays kept on the Spike.
A record with no line prints one line saying so:

```sh
fgraph knowledge
# 2026-11-24  deviation  S-0001#3  the second Task was dropped
# 2026-11-23  decision  Q-0001  one file per work item (answer yes)
# 2026-11-22  decision  F-0001#1  the budget is agreed
# 2026-11-22  decision  S-0001#2  keep one store
# 2026-11-22  finding  S-0001#1  the file holds the lines in the order noted

fgraph knowledge --kind decision
# 2026-11-23  decision  Q-0001  one file per work item (answer yes)
# 2026-11-22  decision  F-0001#1  the budget is agreed
# 2026-11-22  decision  S-0001#2  keep one store

fgraph knowledge --kind finding
# 2026-11-22  finding  S-0001#1  the file holds the lines in the order noted

fgraph knowledge --live
# after: fgraph note S-0001 --decision "keep one file per item" --supersedes S-0001#2
# 2026-11-24  decision  S-0001#4  keep one file per item
# 2026-11-24  deviation  S-0001#3  the second Task was dropped
# 2026-11-23  decision  Q-0001  one file per work item (answer yes)
# 2026-11-22  decision  F-0001#1  the budget is agreed
# 2026-11-22  finding  S-0001#1  the file holds the lines in the order noted

fgraph knowledge --search STORE
# 2026-11-22  decision  S-0001#2  keep one store

fgraph knowledge --search budget --kind finding
# no finding lines holding 'budget' in the record
```

`fgraph knowledge --format json` prints the same lines as one JSON document another tool reads, each with its ref, its kind, its time, its item, its text, its mark, its terms, the files it governs and the refs it supersedes, keys sorted and null for nothing, the same bytes on two runs; the filters narrow it as they narrow the text; text stays the default; another word is refused naming both, exit 2:

```sh
fgraph knowledge --kind decision --format json
# {
#   "lines": [
#     {
#       "about": [], ...
fgraph knowledge --format xml
# fgraph: error: --format 'xml' is not text or json, the two formats of knowledge
```

A line is never amended or removed. The id of a Task with a kind of knowledge,
an id the record does not hold, a blank text and a note with none or more than one of the four exit 2 and write nothing. With the development on, a
started work item is noted in its worktree, as its Tasks are written, and every
other one, a Feature too, on `main`; the branch of a work item writes that work
item alone, so a Feature is not noted there.
A later line supersedes an earlier one with `--supersedes REF`, once per line
it supersedes, by the ref `fgraph knowledge` lists, of the same item or of any
other. The later line keeps the refs and the earlier one is left as written;
`fgraph show` ends the superseded line with the refs of the lines that
supersede it, as `(superseded by S-0001#2)`. A ref that names no line exits 2 and writes nothing, with
`--supersedes names S-0001#9, which is no knowledge line of the record: fgraph
knowledge lists each line with its ref`:

```sh
fgraph note S-0001 --decision "keep one file per item" --supersedes S-0001#2
# noted S-0001

fgraph show S-0001
# ...
#   decision  2026-11-22  keep one store  (superseded by S-0001#4)
```

A completed Story, Bug or Upkeep is closed on a question: does its criterion
hold on `main`? The run of the criterion is the agent's; `fgraph verify` keeps
the answer yes with what the run printed and the day, as one write and one
commit of the record, `chore: verify S-0001 in the record`. It is a fact of the
work item, not a knowledge line, and `fgraph show` lists it after the commit.
It takes a work item that is completed and holds no answer yet: one that is
not completed, a Spike, a Feature, a Task, a blank text, a second answer (a no
after a yes too) and a call with neither or both of `--yes` and `--no` exit 2
and write nothing.

```sh
fgraph verify S-0001 --yes "make check: all checks passed"
# verified S-0001

fgraph show S-0001
# S-0001  Add the show command to src/flowgraph/cli.py
#   bucket       completed
#   commit       def5678
#   verified     yes  2026-11-22  make check: all checks passed
# ...
```

A no moves nothing backwards: the work item stays Completed, keeps the answer
no, and the same write adds a Bug in Backlog that amends it, under the next Bug
id. The Bug observes what the run printed and expects the Then of a Story or an
Upkeep, or the expected of a Bug; its title is built from that of the work
item. Under a Feature that is not completed the Bug joins it, else it stands
alone. Both files are one commit, `chore: verify S-0001 no and add B-0001 in
the record`, and a failure in between writes neither.

```sh
fgraph verify S-0001 --no "status listed no reason"
# verified S-0001 no
# added B-0001 amending S-0001

fgraph show B-0001
# B-0001  No at the verify of S-0001: Add the show command to src/flowgraph/cli.py
#   bucket       backlog
#   amends       S-0001
#   observed     status listed no reason
#   expected     the item is shown
# Tasks (0)

fgraph show S-0001
# S-0001  Add the show command to src/flowgraph/cli.py
#   bucket       completed
#   amended by   B-0001
#   commit       def5678
#   verified     no  2026-11-22  status listed no reason
# ...
```

A started Task that cannot go on is blocked, with the reason and who or what
it waits on. It stays in InProgress and `fgraph show` lists it as blocked:

```sh
fgraph block T-0001 --reason "the review is not back" --waiting-on "the reviewer"
# blocked T-0001 of S-0001

fgraph show S-0001
# ...
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     bucket           in-progress, blocked
#     reason           the review is not back
#     waiting on       the reviewer
#     expected output  changed: src/flowgraph/cli.py gains the show command
```

`fgraph status` lists a blocked Task under its work item too, marked `!`, with what it waits on and the reason of the block on a line of its own
below it, beginning under its id:

```sh
fgraph status
# backlog (0)
# in-progress (1)
#   S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#     !  T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#        waiting on the reviewer: the review is not back
# completed (0)
```

A block exits 2 and names why when the Task is still in Backlog, blocked
already or completed, when the reason or what it waits on is blank, when the
text is no id, or when the record does not hold the Task. With the development
on, run on `main` for a Task of a started Story that has a worktree, it names
that worktree: `S-0001 is started: its Tasks are written in its worktree, <path>`.
A blocked Task is not started or completed, and its Story is not completed,
while it is blocked. `fgraph block` and `fgraph unblock` take a started work
item of any kind (next) and a started Feature too (below).

Unblock it once it can go on. It is started again, with the started time it
had, and can be completed or blocked once more:

```sh
fgraph unblock T-0001
# unblocked T-0001 of S-0001
```

An unblock exits 2 and names why when the Task is not blocked, when the text
is no id, or when the record does not hold the Task. With the development on,
run on `main` for a Task of a started Story that has a worktree, it names
that worktree: `S-0001 is started: its Tasks are written in its worktree, <path>`.

A started work item that cannot go on is blocked the same way, a Story, an
Upkeep, a Bug or a Spike, with the reason and who or what it waits on. It
stays in InProgress, marked `!` with what it waits on, its Tasks being worked
under it, and `fgraph show` lists it as blocked:

```sh
fgraph block S-0001 --reason "no key" --waiting-on "developer"
# blocked S-0001

fgraph status
# backlog (0)
# in-progress (1)
# ! S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#   waiting on developer: no key
# completed (0)

fgraph show S-0001
# S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
#   bucket       in-progress, blocked
#   reason       no key
#   waiting on   developer
# ...
```

It is one write and one commit, `chore: block S-0001 in the record`; with the
development on it is written in the worktree of the work item, as its Tasks
are, and refused on main naming that worktree. No Task of a blocked work item
moves: its start, complete, block and unblock exit 2 naming the block, `T-0001
cannot start: S-0001 is blocked, waiting on developer: unblock it first`,
while a Task is still added to it and a line still noted. Its start, complete,
hand and landing exit 2 with `S-0001 is blocked: unblock it first`, its remove
with `S-0001 is blocked`, its amend being taken with `--deviation` as for a
started one, and it counts against
`development.parallel` as a started one does. A block exits 2 when the work
item is in Backlog, blocked already, completed or removed, or the reason or
what it waits on is blank; an unblock when it is not blocked. `fgraph unblock
S-0001` takes it back to started, with what it held, says `unblocked S-0001`
and commits `chore: unblock S-0001 in the record`.

When `main` moved since the start -- another work item landed first --
`fgraph sync`, run in the worktree of the started work item, merges the local
branch `main` into its branch by one merge commit, never a rebase and with no
fetch:

```sh
cd ../project.worktrees/S-0001-raise-the-stories-fgraph
fgraph sync
# merged main into wi/S-0001-raise-the-stories-fgraph at <a sha>
```

The commit is worded `chore: merge main into <branch>`. A branch that holds
`main` already says `<branch> holds main already at <sha>`, exits 0 and makes
no commit. A `main` that conflicts with the branch is not merged:

```sh
fgraph sync
# fgraph: error: main does not merge into wi/S-0001-...: conflict in <file> -- nothing is merged, the branch is as it was
```

The merge is then yours, `git merge main` in the worktree. The refusals of
exit 2 are the development off, outside a git work tree, on `main` or on a
branch no work item owns, and a tracked file changed and not committed (an
untracked file is left alone).

In a git repository whose record has the development on, `fgraph land` does
the landing in one step, run in the checkout of `main` once every Task of the
Story is completed on its branch. The message of the merge commit is yours:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# landed S-0001 at 677f9b0
# run: a Story is added -> fgraph status lists it under Backlog
```

The second line names the When and the Then of the criterion of the Story, to
run on `main` at the commit named above it; `fgraph verify S-0001 --yes` or
`fgraph verify S-0001 --no` keeps the answer. A Bug prints its expected alone,
as `run: <expected>`; a Spike lands with its answer and prints no such line; a
part written over several lines is printed on one.

It merges the branch `wi/S-0001-*` into `main` as one merge commit under
that message, completes the Story at that commit, commits the record as
`chore: complete S-0001 in the record`, and removes the worktree and the
branch. A land exits 2 and names why, with nothing merged, when the
development is off, when a Task of the Story is not completed, when the
checkout it runs in is not on `main`, when `delivery.push` is `true` and
`main` tracks no branch of a remote, when the Story has no branch or
several, when the record is outside a git work tree, when git refuses the
merge, or when the gate of the record fails.

That is a landing by `merge-commit`, the way of a record whose `config.toml`
names no `[development] merge`. With `merge = "squash"` the same command puts
the work of the branch on `main` as one commit of its own under the message,
with one parent: `main` holds none of the commits of the branch, and the
Story is completed at that one commit. With `merge = "fast-forward"` `main`
moves to the tip of the branch and no commit is made, so the landing takes no
message, and the Story is completed at the tip:

```sh
fgraph land S-0001
# landed S-0001 at 2c41d07
# run: a Story is added -> fgraph status lists it under Backlog
```

With `merge = "pull-request"` the landing is left to a pull request on the
host of the remote. The first run checks the merge as any way does -- the
Tasks completed, the gate -- drops it, pushes the branch to the remote `main`
tracks and names the command that opens its pull request: nothing is merged,
written or removed. fgraph opens no pull request and fetches nothing. Once
the pull request is merged and `main` pulled, the same command completes the
Story at the commit `main` is on and removes the worktree and the branch:

```sh
fgraph land S-0001
# pushed wi/S-0001-raise-the-stories-fgraph to origin
# open its pull request: gh pr create --base main --head wi/S-0001-raise-the-stories-fgraph
# S-0001 is not completed: run fgraph land S-0001 again once main holds its pull request merged

git pull --ff-only origin main
fgraph land S-0001
# landed S-0001 at 3e9ae5c
# run: a Story is added -> fgraph status lists it under Backlog
```

The message goes with the commit a landing makes. A landing by `merge-commit`
or `squash` exits 2 without `--message`, and one by `fast-forward` or
`pull-request` exits 2 with it, each naming the key:

```sh
fgraph land S-0001
# fgraph: error: S-0001 cannot land without --message: development.merge = squash makes a commit to word

fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# fgraph: error: S-0001 cannot land with --message: development.merge = fast-forward makes no commit to word
```

A fast-forward needs a branch that holds every commit of `main`. When `main`
holds a commit the branch lacks, the landing exits 2 with nothing merged:

```sh
fgraph land S-0001
# fgraph: error: S-0001 cannot land by fast-forward: main holds a commit wi/S-0001-raise-the-stories-fgraph lacks -- rebase wi/S-0001-raise-the-stories-fgraph on main or merge main into it
```

A record whose `config.toml` names `[development] approver = "developer"` holds
every landing for the developer: the landing waits, nothing is merged, and the
command says why. The developer approves it by the same command with
`--approved`, which is the word of the developer and is kept in no record:

```sh
fgraph config set development.approver developer

fgraph land S-0001 --message "feat: land the first Story"
# fgraph: error: S-0001 cannot land: development.approver = developer, the landing waits for the developer -- run fgraph land S-0001 --approved once the developer approves it

fgraph land S-0001 --message "feat: land the first Story" --approved
# landed S-0001 at 3e9ae5c
# run: a Story is added -> fgraph status lists it under Backlog
```

Every other rule of a landing holds for each way: what it refuses, that
nothing is merged then, and the commit of the record after it.

A landing merges into a checkout of `main` that holds no merge of its own. One
you left unconcluded there is named and left as it was, and a branch that
brings no commit `main` lacks, merged by hand or by a landing that stopped
after its merge, is taken up at the commit `main` is on: no commit is made, so
nothing you staged is taken into the commit of a landing:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# fgraph: error: a merge is held in /src/project: commit it or abort it first
```

A record whose `config.toml` names a `[development] gate` runs that command
at every landing, by each way, between the merge and the commit. The gate
runs in the checkout of `main` with the work of the branch merged in, not yet
committed; a landing by `fast-forward` runs it on that same merge before
`main` moves to the tip. When the gate fails the landing exits 2 naming the
command and its status, as shown with the configuration, and the merge is
dropped: `main` is where it was. Ctrl-C during the gate drops it as well.

A gate checks the tree; it is not meant to change it. A file the merge brought
that the gate changes goes with the merge when it is dropped, and is left
changed in the checkout when the gate passes, as the commit of a landing holds
what the merge staged alone. A file the gate writes or changes outside the
merge -- a report, a cache, a build -- stays in the checkout, uncommitted,
whatever the gate exits with.

An Upkeep is work that keeps a behavior and changes the inside, such as a
split of a module. Its criterion is a Given / When / Then whose When already
runs and whose Then says it still holds. Its id counts on its own, `U-0001`:

```sh
fgraph add upkeep "Cut the lines of the largest module of src/flowgraph from 1068 to 400" \
  --given "main" \
  --when "make check runs" \
  --then "it still passes"
# added U-0001

fgraph status
# backlog (1)
#   U-0001  []  Cut the lines of the largest module of src/flowgraph from 1068 to 400
# in-progress (0)
# completed (0)
```

`fgraph show U-0001` shows it with its criterion and its Tasks. An Upkeep
takes Tasks and moves as a Story does, by the same commands; a Task id counts
across both kinds:

```sh
fgraph add task "Split src/flowgraph/story.py into the story package" \
  --parent U-0001 \
  --output "created: src/flowgraph/story/ with no module above 400 lines"
# added T-0001 to U-0001

fgraph start U-0001
# started U-0001
# branch wi/U-0001-cut-the-lines-of in /src/project.worktrees/U-0001-cut-the-lines-of
fgraph start T-0001
# started T-0001 of U-0001
fgraph complete T-0001 --commit 0636c92
# completed T-0001 of U-0001 at 0636c92
fgraph complete U-0001 --commit 6db7fac
# completed U-0001 at 6db7fac
```

An Upkeep is kept as `items/U-0001.toml`, its Tasks inside it.

A Bug is a behavior that fails. Its criterion is what is observed and what is
expected instead, and its id counts on its own, `B-0001`:

```sh
fgraph add bug "Cut the tracebacks fgraph --dir prints for a file from 1 to 0" \
  --observed "fgraph --dir given a file prints a traceback" \
  --expected "it exits 2 and names the path"
# added B-0001

fgraph show B-0001
# B-0001  Cut the tracebacks fgraph --dir prints for a file from 1 to 0
#   bucket       backlog
#   observed     fgraph --dir given a file prints a traceback
#   expected     it exits 2 and names the path
# Tasks (0)
```

A Bug takes Tasks and moves as a Story does, by the same commands, and joins
the queue of the Backlog. `fgraph amend B-0001 --expected "..."` rewrites its
criterion; `--given` on a Bug, or `--observed` on a Story, exits 2. A Bug is
kept as `items/B-0001.toml`.

A Spike is a question to answer. Its criterion is a hypothesis, a yes/no
question, and it is completed with the decision that answers it and the yes
or no of the hypothesis. Its id counts on its own, `Q-0001`, Q for question:

```sh
fgraph add spike "Settle whether one file per item can hold the record" \
  --hypothesis "Can one file per item hold the record?"
# added Q-0001

fgraph complete Q-0001 --commit 677f9b0 \
  --decision "one file per work item, its Tasks inside" --answer yes
# completed Q-0001 at 677f9b0

fgraph show Q-0001
# Q-0001  Settle whether one file per item can hold the record
#   bucket       completed
#   commit       677f9b0
#   hypothesis   Can one file per item hold the record?
#   decision     one file per work item, its Tasks inside
#   answer       yes
# ...
```

A Spike takes Tasks and moves as a Story does, and `fgraph land` takes
`--decision` and `--answer` as `fgraph complete` does. `--answer` is `yes` or
`no`, and a no completes the Spike as a yes does: nothing is refused for it and
no Bug is filed. A Spike completed without its decision or without its answer
exits 2, and so does a decision or an answer given for any other kind or for a
Task. A Spike completed before the answer was taken holds none and is shown as
before. `fgraph knowledge --kind decision` lists the decision with its answer.
With the development off a Spike is completed with its decision and no
commit, as any other kind is. `fgraph amend Q-0001 --hypothesis "..."` rewrites the hypothesis while
the Spike is in Backlog. A Spike is kept as `items/Q-0001.toml`.

The prefix `Q` is the developer's choice of 2026-11-21; until then a Spike
was written `SP-0001`. `fgraph` reads `Q` alone: an `items/SP-0001.toml` of
an older record is left alone as a file of a prefix no kind knows, neither
read as a Spike nor renamed.

A Feature groups work items toward one bigger outcome. It states one or more
criteria, what the user experiences, and holds no Task. A work item is added
under it with `--parent`; without one it stands alone:

```sh
fgraph add feature "Raise the kinds of work a project tracks with fgraph from 1 to 5" \
  --criterion "a developer sees every work item of the project by bucket" \
  --criterion "a developer adds every kind of work"
# added F-0001

fgraph add story "Raise the Stories fgraph lists under Backlog from 0 to 1" \
  --given "a record with no items" --when "a Story is added" \
  --then "fgraph status lists it under Backlog" --parent F-0001
# added S-0001

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       backlog
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (1)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  backlog
```

A Feature has a state of its own, kept in its file as that of a work item is:
it is in Backlog until `fgraph start` starts it, InProgress from then on,
with its started time, and Completed once its last work item is completed,
with its completed time and the commit of that completion (below). `fgraph
show S-0001` names the Feature as its `parent`. An add exits 2 and names why
when a criterion or the title is blank or when `--parent` names no Feature of
the record, or one completed or removed. A work item added alone is put
under a Feature later, by the same rule, and one under a Feature taken out
while that one is in Backlog, with `fgraph amend --parent` (below). The
wording of a Feature in Backlog is rewritten with
`fgraph amend` too, and a Feature in Backlog, or a started or blocked Feature
once no work item of it is started, is removed with `fgraph remove`, its work
items in Backlog with it (below). A Feature is kept as `items/F-0001.toml`.

A work item under a Feature may name the one criterion of it that its own
criterion is, by its place in the list counted from 1. The link is optional
(the decision kept on F-0013: a Feature may hold work items whose criterion is
none of its criteria), and two work items may name one criterion. `fgraph add`
takes `--realizes N` beside `--parent`, and `fgraph amend` takes it for a work
item in Backlog, `none` taking it away:

```sh
fgraph add story "Raise the kinds of work item fgraph adds from 1 to 2" \
  --given "a record with a Story" --when "an Upkeep is added" \
  --then "fgraph status lists both kinds under Backlog" --parent F-0001 --realizes 2
# added S-0002

fgraph show S-0002
# S-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   bucket       backlog
#   parent       F-0001
#   realizes     2  a developer adds every kind of work
#   given        a record with a Story
#   when         an Upkeep is added
#   then         fgraph status lists both kinds under Backlog
# Tasks (0)

fgraph amend S-0002 --realizes 1
# amended S-0002

fgraph amend S-0002 --realizes none
# amended S-0002

fgraph add story "Hold" --given a --when b --then c --parent F-0001 --realizes 3
# fgraph: error: F-0001 has no criterion 3: its criteria count from 1 to 2
```

An add or an amend exits 2 and writes nothing for a work item that stands
alone, for a number the Feature does not have, for `0`, for a word that is
neither a number nor `none`, and for a Feature id: a Feature is amended by its
title, its description, its criteria and its terms. A work item started already
is not amended. `fgraph amend F-0001 --criterion` rewrites the list and leaves
the number a work item names as written: it then names the criterion now at
that place, and `fgraph show` says `none of the criteria of F-0001` for a number
past the end.

Once a work item under a Feature names a criterion of it, `fgraph show` of the
Feature numbers its criteria and lists them as met k of n, each with the work
items that realize it. A criterion is met when one of them is completed; a
removed one is not listed. A Feature none of whose work items names a criterion
is listed as before, `Criteria (2)` and its criteria alone, since the link is
optional. With S-0001, completed, realizing the first criterion:

```sh
fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       in-progress
# Criteria (2), met 1 of 2
#   1  met      a developer sees every work item of the project by bucket  S-0001
#   2  not met  a developer adds every kind of work  S-0002
# Work items (2)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  completed
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2  backlog
```

`fgraph status` lists a Feature inside its bucket, as one line in place of
its work items: its id, its progress and its title. Here a Story that stands
alone, S-0002, was added after the Feature, and the Story under the Feature
is on no line of its own:

```sh
fgraph status --backlog
# backlog (2)
#   F-0001  0/1 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
# in-progress (0)
# completed (0)
```

The progress, `0/1 W`, is the work items of the Feature completed of all it
holds: one of three completed reads `1/3 W`, so two are still to be done. A
removed work item is counted in neither number, and a Feature without a work
item reads `0/0 W`. A Feature under Completed is listed with its commit and no
count of its work items.

A Feature holds a place of its own in the Backlog: it joins the end when it
is added, after the work items and the Features `fgraph reorder` placed and
those added before it, and `fgraph reorder` places it as a work item (below).
It is counted once, beside the heading and toward the top of it (below). Its
work items in Backlog are listed on no line of their own. A completed one of a
Feature in progress stays listed under its line, counted beside no heading; those
of a completed or a removed Feature stay on no line. They are counted in its
progress, and `fgraph show F-0001` lists each with its bucket. A removed one keeps its line under
Removed, unless the Feature itself is removed: that Feature is listed there
in place of its work items (below).

`fgraph start` takes a Feature, and starts its first work item with it:

```sh
fgraph start F-0001
# started F-0001 with S-0001
```

A Feature is to its work items what a work item is to its Tasks, the
principle the developer's words of 2026-11-21 were filed under (F-0002): it
does not start without one, and its work item does not start before it. Its
work items start side by side, as many as `[development] parallel` allows
(below), which replaces the one-by-one start of the same decision. The first work item is the first of its work
items in Backlog in the order they start in, the one `fgraph reorder` gives
them (below); a Feature that already holds completed work items starts with
the next one. The Feature and that work item are started in one write and one
commit, `chore: start F-0001 in the record`. The work item is started as any
other: with the development on it gets its branch and its worktree, `--slug`
naming the branch, and the start is made on main alone:

```sh
fgraph start F-0001
# started F-0001 with S-0001
# branch wi/S-0001-raise-the-stories-fgraph in /src/project.worktrees/S-0001-raise-the-stories-fgraph
```

The started Feature is listed under InProgress, and its started work item
under its line, indented, with its progress and its Task being worked:

```sh
fgraph status
# backlog (1)
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
# in-progress (1)
#   F-0001  0/1 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#     S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#       => T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
# completed (0)
```

The lines under a Feature belong to it: they count neither beside the heading
nor toward the top of the heading.

A blocked Task marks its Feature: while the started work item of a Feature
holds a blocked Task, `fgraph status` lists the Feature with `!` before its
id, in the first column of its line, and puts what that Task waits on on a line of its
own below it, beginning under its id, as the line of the Task does:

```sh
fgraph block T-0001 --reason "the review is not back" --waiting-on "the reviewer"
# blocked T-0001 of S-0001

fgraph status
# backlog (1)
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
# in-progress (1)
# ! F-0001  0/1 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   waiting on the reviewer: the review is not back
#     S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#       !  T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#          waiting on the reviewer: the review is not back
# completed (0)
```

The mark is derived at each listing, from the Tasks of the started work item,
and kept in no file: the file of the Feature and the file of the work item
hold nothing of it, and `fgraph unblock T-0001` takes it away. A started Task
beside the blocked one does not lift it: the Feature is marked as long as its
started work item holds a blocked Task, and names what the first of them
waits on, in the order the file of the work item holds them. The id of the
Feature stays in its column, and the lines of the work item and of the Task
under it are written as under any Feature. On a terminal the line is cut to
the width as any line of the status, so the mark is kept and what is waited
on is what the cut takes first. A blocked work item under a started Feature
marks it the same way, with what that work item waits on, before what a Task
of it waits on. A Feature is blocked itself with `fgraph block` too (below).

The completion of a work item of a started Feature starts the next one, in
the same write, beside those of the Feature still started. The next one is
the first of its work items in Backlog in the order they start in, the one
`fgraph reorder` gives them (below). Here F-0001 holds S-0001, started, and
S-0003, a second Story under it, in Backlog:

```sh
fgraph complete S-0001 --commit 677f9b0
# completed S-0001 at 677f9b0
# started S-0003

fgraph status
# backlog (1)
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
# in-progress (1)
#   F-0001  1/2 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#     S-0003  0/1 T  Raise the Stories fgraph lists under Completed from 0 to 1
#     S-0001  1/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
# completed (0)
```

The start is named on a line of its own after the completion, and the two
are one commit of the record, `chore: complete S-0001 and start S-0003 in the
record`. The next work item is started as `fgraph start S-0003` starts it:
with the development on it gets its branch, named by the slug of its title,
checked out in a worktree of its own at that commit of the record. The
completion is then a landing, which names the branch once the worktree and
the branch it landed are removed; `fgraph complete` on main, after a merge
made by hand, branches the next one the same way:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# landed S-0001 at 3e9ae5c
# run: a Story is added -> fgraph status lists it under Backlog
# started S-0003
# branch wi/S-0003-raise-the-stories-fgraph in /src/project.worktrees/S-0003-raise-the-stories-fgraph
```

A next work item that cannot start stays in Backlog, and the completion
stands: it exits 0, is committed as a completion alone, `chore: complete
S-0001 in the record`, and names why on the line after it, as `not started:`
and the refusal of that start:

- when it has no Task: `not started: S-0003 has no Task to start with`;
- with `development.driver` set to `agent`, when it has no complexity:
  `not started: S-0003 has no complexity to start with: set it with fgraph amend S-0003 --complexity low, medium or high`;
- when `[development] parallel` refuses one more started work item:
  `not started: S-0003 cannot start: development.parallel = 1, started already: S-0002`;
- when its title gives no slug to name its branch.

`fgraph start S-0003`, on main, starts it once what refused it is gone. A
completion starts nothing when no work item of the Feature is left in
Backlog -- the last one completes the Feature, next -- and nothing under a
Feature that was never started.

The alternative, that the developer starts each work item of a Feature with
`fgraph start`, was shown with the plan of S-0053 and not taken: by the
developer's words of 2026-11-21 the Feature starts its work items.

A Feature moves to Completed with its last work item: the completion that
leaves each work item of a started Feature completed or removed completes the
Feature in the same write. Here S-0001 is the one work item of F-0001:

```sh
fgraph complete S-0001 --commit 677f9b0
# completed S-0001 at 677f9b0
# completed F-0001 at 677f9b0

fgraph status
# backlog (1)
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
# in-progress (0)
# completed (1)
#   F-0001  677f9b0  Raise the kinds of work a project tracks with fgraph from 1 to 5

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       completed
#   commit       677f9b0
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (1)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  completed
```

The Feature holds the commit of that completion as its evidence, and none
when the work item is completed without one, as with the development off:
`completed S-0001`, then `completed F-0001`, and the line of the Feature is
`F-0001  677f9b0  <title>`. The line of a completed Feature is its id, its
commit and its title, with no count of its work items: the commit stands right
after the id, as the commit of a completed work item stands before its title.
It is placed under Completed by its completed
time, and its completed work items stay within it: counted in its progress,
listed by `fgraph show F-0001`, on no line of `fgraph status`. The Feature
and the work item are completed in one commit of the record, `chore: complete
S-0001 and F-0001 in the record`.

With the development on, `fgraph land` of the last work item completes the
Feature the same way, at the commit the landing leaves main on:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# landed S-0001 at 3e9ae5c
# run: a Story is added -> fgraph status lists it under Backlog
# completed F-0001 at 3e9ae5c
```

The Feature is written on main, as the landing is. A work item completes on
main alone, as it starts there, so the next work item its completion starts
is started on main too: `fgraph complete S-0001` in its worktree, or on any
branch but main, exits 2 with nothing written, naming the work tree on main,
and its landing completes it. A Task completes anywhere:

```sh
fgraph complete S-0001 --commit 677f9b0
# fgraph: error: S-0001 completes on main, in /src/project: /src/project.worktrees/S-0001-raise-the-stories-fgraph is on wi/S-0001-raise-the-stories-fgraph
```

Only a completion completes a Feature. A completion that leaves a work item
of it in Backlog leaves the Feature started, and starts that work item
(above). `fgraph remove` of its last work item in Backlog leaves the Feature
started too: that Feature stays under InProgress, `F-0001  1/1 W  <title>`. A
removed work item holds nothing back and is counted in neither number.
`fgraph complete F-0001` then completes it, now, at the commit of its last
completed work item, none when none is, committed as `chore: complete F-0001
in the record`. `fgraph remove F-0001` is the way out of a started or blocked Feature
whose criteria were not met (below), as `fgraph complete F-0001` is of one whose were:

```sh
fgraph complete F-0001
# completed F-0001 at 677f9b0
```

It exits 2 with nothing written while a work item of the Feature is neither
completed nor removed, naming it, for a Feature in Backlog, completed or
removed, and when given `--commit`:

```sh
fgraph complete F-0001
# fgraph: error: F-0001 cannot complete: S-0002 is in Backlog

fgraph complete F-0001 --commit 677f9b0
# fgraph: error: F-0001 takes no --commit: it is completed at the commit of its last completed work item
```

A landing reads the Feature of its work item with its other checks, while the
merge is held: a Feature the record does not hold refuses the landing before
`main` moves.

A started Feature that cannot go on is blocked, with the reason and who or
what it waits on, as a Task is: `fgraph block` takes the id of a Feature. It
stays under InProgress. `fgraph status` lists it with `!` before its id and
what it waits on on a line of its own below its title, the look of a Feature marked by a blocked
Task (above), and `fgraph show` lists it as blocked, with its reason and what
it waits on. Here F-0001 holds S-0001, started, and S-0003 in Backlog:

```sh
fgraph block F-0001 --reason "the budget is not agreed" --waiting-on "the sponsor"
# blocked F-0001

fgraph status
# backlog (1)
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
# in-progress (1)
# ! F-0001  0/2 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   waiting on the sponsor: the budget is not agreed
#     S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
# completed (0)

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       in-progress, blocked
#   reason       the budget is not agreed
#   waiting on   the sponsor
# Criteria (2)
# ...
```

Only a started Feature is blocked. The block is a state of the Feature, kept
in its file with its reason, what it waits on and the time it is blocked
since, where the mark of a blocked Task is derived and kept in no file. It is
one write and one commit, `chore: block F-0001 in the record`, made on main
alone as every write of a Feature. Its own block comes before that of a Task
of its work item: while both are blocked, the line of the Feature names what
the Feature waits on, and the line of the Task what the Task waits on.

While a Feature is blocked no further work item of it starts, and its started
one goes on: its Tasks are written as before, and it is completed and landed
as before. `fgraph start` of a work item of it in Backlog exits 2 naming the
block, and the completion of its started one stands and says the next one is
not started:

```sh
fgraph start S-0003
# fgraph: error: S-0003 cannot start: F-0001 is blocked, waiting on the sponsor: unblock it first

fgraph complete S-0001 --commit 677f9b0
# completed S-0001 at 677f9b0
# not started: S-0003 cannot start: F-0001 is blocked, waiting on the sponsor: unblock it first
```

`fgraph land S-0001` says the same after `landed S-0001 at 3e9ae5c` and its
`run:` line. The
completion of its last work item completes a blocked Feature as it completes
a started one (above): the block holds back a start, never a completion. The
alternative, that every write under a blocked Feature is refused, the Tasks
of its started work item among them, was shown with the plan of S-0056 and
not taken.

Unblock it once it can go on. It is started again, with the started time it
had, and its block leaves its file. When no work item of it is started, the
unblock starts the next one, as the completion of one does:

```sh
fgraph unblock F-0001
# unblocked F-0001
# started S-0003
```

The two are one commit of the record, `chore: unblock F-0001 and start S-0003
in the record`, and with the development on S-0003 gets its branch and its
worktree at that commit, named on a third line as after a landing. While a
work item of the Feature is started or blocked the unblock starts none: it
says `unblocked F-0001` alone and its commit is `chore: unblock F-0001 in the
record`. A next work item that cannot start stays in Backlog and the unblock
stands: the line after it says `not started:` and why, as after a completion
(above), and `fgraph start S-0003` starts it once what refused it is gone.

A block of a Feature exits 2 and names why, with nothing written: when it is
in Backlog, `F-0001 is in Backlog: start it first`; blocked already, `F-0001
is blocked already`; or completed, `F-0001 is completed already`; when the
reason or what it waits on is blank; when the record does not hold the
Feature; and in the worktree of a work item, whose branch writes that work
item alone. An unblock exits 2 when the Feature is not blocked, `F-0001 is
not blocked`, or the record does not hold it. A blocked Feature is not
started once more: `fgraph start F-0001` exits 2, `F-0001 is blocked: unblock
it first`.

A completed Feature takes no start and no work item added under it; each
exits 2 with nothing written:

```sh
fgraph start F-0001
# fgraph: error: F-0001 is completed already

fgraph add story "Raise the Stories fgraph lists under Completed from 0 to 1" \
  --given "a started Story" --when "it is completed" \
  --then "fgraph status lists it under Completed" --parent F-0001
# fgraph: error: F-0001 is completed already
```

The start of a Feature exits 2 and names why, with nothing written and no
branch made:

- when it is started already: `F-0001 is started already`;
- when it is blocked: `F-0001 is blocked: unblock it first`;
- when it is completed: `F-0001 is completed already`;
- when it has no work item in Backlog:
  `F-0001 has no work item in Backlog to start with`;
- when its first work item has no Task:
  `F-0001 cannot start: S-0001 has no Task to start with`;
- with the development on, when a work item of it in Backlog has no Task, the
  first in start order named:
  `F-0001 cannot start: S-0002 has no Task to start with`;
- with `development.driver` set to `agent`, when a work item of it in Backlog
  has no complexity, the first in start order named:
  `F-0001 cannot start: S-0002 has no complexity to start with: set it with fgraph amend S-0002 --complexity low, medium or high`;
- with the development on, when the branch of its first work item is there
  already:
  `F-0001 cannot start: the branch wi/S-0002-<slug> is there already -- delete it or give another --slug`;
- when `[development] parallel` refuses one more started work item:
  `F-0001 cannot start: development.parallel = 1, started already: S-0002`.

A work item does not start before its Feature. `fgraph start` of a work item
in Backlog under a Feature exits 2 naming the Feature and the command that starts it while the Feature is
not started. Once it is, the work items of the Feature start side by side:
`fgraph start` of a second Story, S-0002, under the started F-0001 succeeds
and names its branch, and with `[development] parallel = 2` the start of a
third, S-0003, is refused naming the key and the started work items:

```sh
fgraph start S-0001
# fgraph: error: S-0001 cannot start: F-0001 is not started: fgraph start F-0001 starts it

fgraph start S-0002
# started S-0002
# branch wi/S-0002-<slug> in <path>

fgraph start S-0003
# fgraph: error: S-0003 cannot start: development.parallel = 2, started already: S-0001, S-0002
```

The completion of S-0001 starts the next one by itself (above), beside those
still started; `fgraph start S-0003` is for the one a completion left in
Backlog. `parallel` alone limits them, for the start a completion makes too,
and counts every started work item of the record, those under a Feature
among them; left out, nothing limits them. The unblock of a Feature starts a
work item only when none of it is started.

A Feature file without a state line reads as a Feature in Backlog: every
Feature written before it had a state is such a file. `fgraph status` and
`fgraph show` list that Feature in the bucket its work items derive, as they
did -- InProgress once one of them is started or completed, Completed when
each is completed or removed -- a started work item of it is worked and
completed as before, and `fgraph start` of the Feature starts its next work
item in Backlog and writes the state line. A Feature never started is
completed by nothing: the completion of its last work item writes that work
item alone, and the Feature keeps its derived bucket, listed under Completed
without a commit, `F-0001  7/7 W  <title>`.

The state of a Feature reverses the developer's decision of 2026-11-21 that a
Feature has no state and that its bucket is derived from its work items. The
developer's words of the same day reversed it: starting a Feature starts its
work items one by one, in separate branches when git is used for the
development; they are completed but all stay in progress, and the Feature
moves to Completed when all are. The developer's word of 2026-11-23 replaced
the one-by-one start: the work items of a started Feature start side by side,
limited by `[development] parallel` alone.

This reverses the developer's decision of 2026-11-21 that listed the Features
in a block of their own above the buckets, under a heading `Features`, each
with its derived bucket before its title, while a work item under a Feature
stayed in its own bucket. By the developer's words of the same day a Feature
is part of the Backlog and just holds its work items, so no heading
`Features` is listed any more.

The Backlog is a queue: `fgraph status` lists it in the order the work is to
be pulled. A work item joins the end of the queue when it is added, whatever
its kind, and so does a Feature; `fgraph reorder` puts one right before
another:

```sh
fgraph status --backlog
# backlog (2)
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
#   U-0002  []  Cut the lines one kind of work item holds from 885 to 250
# in-progress (0)
# completed (0)

fgraph reorder U-0002 --before S-0002
# moved U-0002 before S-0002

fgraph status --backlog
# backlog (2)
#   U-0002  []  Cut the lines one kind of work item holds from 885 to 250
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
# in-progress (0)
# completed (0)
```

A Feature is placed in the queue as a work item is: `fgraph reorder` takes
its id on either side. Here a second Story, S-0003, was added under the
Feature; the Story that stands alone is put before the Feature, then the
Feature before it again:

```sh
fgraph reorder S-0002 --before F-0001
# moved S-0002 before F-0001

fgraph status --backlog
# backlog (2)
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
#   F-0001  0/2 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
# in-progress (0)
# completed (0)

fgraph reorder F-0001 --before S-0002
# moved F-0001 before S-0002

fgraph status --backlog
# backlog (2)
#   F-0001  0/2 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   S-0002  []  Raise the kinds of work item fgraph adds from 1 to 2
# in-progress (0)
# completed (0)
```

A work item under a Feature is on no line of the Backlog, so it is reordered
among the work items of its Feature alone: `fgraph reorder` puts it right
before another work item of the same Feature, whatever the bucket of the
Feature. That order is the one the work items of the Feature start in, and
`fgraph show` of the Feature lists its work items in Backlog in it; the
others stay where their kind and number put them:

```sh
fgraph reorder S-0003 --before S-0001
# moved S-0003 before S-0001

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       backlog
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (2)
#   S-0003  Raise the Upkeeps fgraph lists under Backlog from 0 to 1  backlog
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  backlog
```

A reorder exits 2 and names why:

- when one of the two is not in Backlog: a Feature that is in progress or
  completed is refused as a started work item is, and so is an id the record
  does not hold;
- when an item is put before itself;
- when a text is neither a work item id nor a Feature id;
- when a work item under a Feature is put before an item outside its Feature
  -- a work item standing alone, a Feature, a work item of another Feature --
  or such an item is put before it. The refusal names the Feature:

```sh
fgraph reorder S-0003 --before S-0002
# fgraph: error: S-0003 is under F-0001: it is reordered among the work items of F-0001 alone
```

The order given is kept as `queue.toml` in the record, apart from the item
files: one list, `backlog`, of the ids of the work items and of the Features
placed.

```toml
backlog = [
    "F-0001",
    "S-0002",
    "S-0003",
    "S-0001",
]
```

Two orders are read from that list and no other. The ids of the work items
standing alone and of the Features give the order of the lines of the
Backlog: F-0001, then S-0002. The ids of the work items under one Feature
give the order they start in: S-0003, then S-0001. Where a work item under a
Feature stands among the others says nothing. A reorder writes the whole
Backlog as it is then listed and moves one id in it, leaving every other
where it was, so each of the two orders is kept when the other changes. An
id never placed follows the placed ones: the lines of the Backlog as they
were added, then the work items under a Feature as they were added.

The buckets past the Backlog list the last one in on top: InProgress the work
item started last, Completed the one completed last. Work items started or
completed at one time are listed by kind and number. A Feature is placed
among them by its work items: under InProgress by the one started last, under
Completed by the one completed last:

```sh
fgraph status
# backlog (0)
# in-progress (2)
#   B-0001  0/2 T  Cut the tracebacks fgraph --dir prints for a file from 1 to 0
#   S-0003  1/3 T  Raise the kinds of work item fgraph adds from 2 to 3
# completed (3)
#   U-0002  757fbaf  Cut the lines one kind of work item holds from 885 to 250
#   F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   S-0002  87c0307  Raise the kinds of work item fgraph adds from 1 to 2
```

`fgraph status` lists the headings in the order above, and then how many more
the heading holds: unless the configuration says otherwise (`status.backlog`,
`status.in-progress`, `status.completed` and `status.removed`), every item of
InProgress, the top 5 of Completed and Removed, and the first line of the Backlog
alone, with `... N more, M can start`, M the lines of those more that can start. A Feature counts as one item, as a work
item does. The count beside the heading stays that of all its items:

```sh
fgraph status
# backlog (0)
# in-progress (0)
# completed (7)
#   S-0007  e82af5a  Raise the kinds of work item fgraph takes to Completed from 3 to 4
#   S-0006  c29f1b7  Raise the kinds of work item fgraph takes to Completed from 2 to 3
#   S-0005  c399b40  Raise the kinds of work item fgraph takes to Completed from 1 to 2
#   S-0004  87c0307  Raise the kinds of work item fgraph adds and lists from 1 to 2
#   S-0003  4f1ae12  Raise the buckets a Story can reach from 2 to 3
#   ... 2 more
```

A Backlog of five under a plain `fgraph status` lists its first line:

```sh
fgraph status
# backlog (5)
#   S-0001  [1 T]  Add the show command
#   ... 4 more, 0 can start
# in-progress (0)
# completed (0)
```

`fgraph status --backlog` lists the whole Backlog and leaves Completed and
Removed short; `fgraph status --all` lists every item of every bucket, with no such line.

On a terminal `fgraph status` cuts each line to the width of the terminal and
ends a line it cut with `...`, so every item stays on one line. The commit of
a completed work item, when it has one, stands before its title, where a cut
keeps it:

```sh
fgraph status        # on a terminal 60 columns wide
# backlog (0)
# in-progress (0)
# completed (7)
#   S-0007  e82af5a  Raise the kinds of work item fgraph ta...
#   S-0006  c29f1b7  Raise the kinds of work item fgraph ta...
#   ...
```

Written to a pipe or a file, `fgraph status | less` or `fgraph status > f`,
every line is whole. Only status is cut, and the frames of `fgraph watch`
with it; `fgraph show` writes as before.

`fgraph watch` follows the record live: it writes what `fgraph status` writes
as a frame, waits 5 seconds and writes the next, each frame read anew from
the record. On a terminal a frame replaces the one before it, each line cut
to the width the terminal has then, and a frame as tall as the terminal or
taller is cut to one line under its height, its last line naming the lines
it left out (`... 5 more lines`); written to a pipe or a file the frames
follow each other, every line whole, each one reaching the pipe as it is
written, so `fgraph watch | cat` shows a frame every interval. Ctrl-C ends
it, with exit 0:

```sh
fgraph watch            # a frame every 5 seconds, until Ctrl-C
fgraph watch -n 2       # a frame every 2 seconds; -n 0.5 for two a second
fgraph watch --all      # every item in each frame, as fgraph status --all
fgraph watch --backlog   # the whole Backlog in each frame
fgraph watch --count 3  # three frames, then exit 0
```

A frame shows the buckets `watch.buckets` names.

So a Story started while `fgraph watch` runs is listed under InProgress in
its next frame, and on main the frames read a started Story where its Tasks
are written, as `fgraph status` does. A `-n` or a `--count` that is no
positive number exits 2 and writes no frame.

A work item still in Backlog is rewritten with `fgraph amend`: its title, its
description and each part of its criterion, each by its own option. A part
without its option stays as it was, and so do its Tasks and its place in the
queue:

```sh
fgraph amend S-0002 --then "fgraph status lists both kinds under Backlog"
# amended S-0002

fgraph show S-0002
# S-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   bucket       backlog
#   given        a record with a Story
#   when         an Upkeep is added
#   then         fgraph status lists both kinds under Backlog
# Tasks (0)
```

`--title`, `--description`, `--given` and `--when` rewrite the other parts,
several in one call when given together; `--description ""` clears the
description. An amend exits 2 and names why when it names no part, when the
title or a part of the criterion is blank, when the work item is completed or
removed already, or started and given no deviation, or when the record does not
hold it.

Once started, or blocked, a work item is amended with `--deviation TEXT`, the
change to what it was agreed to do: the part is rewritten and the text kept as
one deviation line in the same write and the same commit. `--complexity`,
`--parent` and `--depends-on` stay of the Backlog alone, and `--deviation` given
for a work item in Backlog is refused. With the development on it is run in the
worktree of the work item, and on main it is refused naming that worktree:

```sh
fgraph amend S-0002 --then "fgraph status lists both kinds and their count" --deviation "the count was asked for"
# amended S-0002

fgraph show S-0002
# ...
# Knowledge (1)
#   deviation  2026-11-24  the count was asked for

fgraph amend S-0002 --then "fgraph status lists both kinds"
# fgraph: error: S-0002 is started: amend it with --deviation TEXT, what changes in what it was agreed to do
```

`--parent` puts a work item in Backlog under a Feature, and with the word
`none` takes it out of the one it is under, to stand alone; it is given alone
or beside the other parts:

```sh
fgraph amend S-0002 --parent F-0001
# amended S-0002

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       backlog
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (2)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  backlog
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2  backlog

fgraph amend S-0002 --parent none
# amended S-0002
```

The work item keeps its id, its Tasks and its entry in `queue.toml`, which an
amend never writes. Put under a Feature it is on no line of the Backlog and
starts where that entry orders it among the work items of the Feature; taken
out it is the line of the Backlog that entry places. One never placed follows
the placed ones as it was added. A `--parent` that names the Feature it is
under already moves it nowhere, and the amend is taken. An amend to another
parent or to none drops the criterion named, unless `--realizes` is given with
it.

The Feature it is put under takes it as it takes a work item added under it:
in Backlog, started or blocked. The one it is taken out of is in Backlog, as
the work item is. An amend with `--parent` exits 2, writes nothing and names
why:

- when the Feature it is put under is completed or removed;
- when the Feature it is taken out of is started, blocked or completed,
  whether the work item then stands alone or goes under another;
- when the record does not hold the Feature named;
- when the text is neither a Feature id nor `none`, naming both.

```sh
fgraph amend S-0003 --parent F-0001
# fgraph: error: S-0003 cannot be put under F-0001: F-0001 is completed already

fgraph amend S-0002 --parent none
# fgraph: error: S-0002 cannot be taken out of F-0001: F-0001 is started already

fgraph amend S-0002 --parent F-0009
# fgraph: error: no Feature F-0009 in the record

fgraph amend S-0002 --parent None
# fgraph: error: 'None' is neither a Feature id nor none: a Feature id is F- and a number
```

A Feature still in Backlog is rewritten with `fgraph amend` too: its title
with `--title`, its description with `--description` and its criteria with
`--criterion`, given once per criterion as `fgraph add feature` takes it. The
criteria given replace the ones it had, whole: none is added to them. A part
without its option stays as it was, and so do its id, its work items and its
place in the queue:

```sh
fgraph amend F-0001 --title "Raise the kinds of work a project tracks with fgraph from 1 to 4" \
  --criterion "a developer sees every work item of the project by bucket" \
  --criterion "a developer adds a Story, an Upkeep, a Bug and a Spike"
# amended F-0001

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 4
#   bucket       backlog
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds a Story, an Upkeep, a Bug and a Spike
# Work items (1)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  backlog
```

`--description ""` clears its description. An amend of a Feature exits 2,
writes nothing and names why:

- when it names no part;
- when the title or a criterion is blank;
- when it is given an option of a work item: `--given`, `--when`, `--then`,
  `--observed`, `--expected`, `--hypothesis` or `--parent`;
- when the Feature is completed or removed;
- when the Feature is started or blocked and given no `--deviation`, taken as
  for a work item;
- when the record does not hold it.

`--criterion` given to a work item is refused the same way: only a Feature
states criteria.

```sh
fgraph amend F-0001 --then "fgraph status lists it under Backlog"
# fgraph: error: F-0001 has no then: a Feature is amended by its title, its description, its criteria and its terms

fgraph amend F-0001 --title "Raise the kinds of work a project tracks with fgraph from 1 to 4"
# fgraph: error: F-0001 is started: amend it with --deviation TEXT, what changes in what it was agreed to do

fgraph amend S-0002 --criterion "a developer adds every kind of work"
# fgraph: error: S-0002 has no criteria: only a Feature states them
```

A Task still in Backlog is rewritten with `fgraph amend` too: its title with
`--title`, its output with `--output`, its check with `--check` and its
description with `--description`, a blank one clearing it. A part without its
option stays, and so do its id and its place among the Tasks. The Task of a
work item in Backlog, started or blocked is taken; a Task that is started,
blocked or completed is refused naming its state, and so is a part of a work
item given to a Task. `--check` is refused with the development off, as
`fgraph add task` refuses it:

```sh
fgraph amend T-0001 --output "fgraph status lists both kinds under Backlog"
# amended T-0001 of S-0001

fgraph amend T-0001 --title "List both kinds"
# fgraph: error: T-0001 is started already
```

A work item filed by mistake or superseded is removed from the Backlog with
the reason. Nothing is deleted: it is kept with its Tasks, apart from the
flow, and `fgraph status` lists it under Removed:

```sh
fgraph remove S-0002 --reason "superseded by S-0003"
# removed S-0002

fgraph status
# backlog (0)
# in-progress (0)
# completed (0)
# removed (1)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   superseded by S-0003
```

The heading Removed is listed only when a work item or a Feature is removed.
A remove exits 2 and names why when the reason is blank, when the work item
is completed or removed already, or when the record does not hold it. A
removed work item takes no Task, no amend and no move.

A work item superseded by another names it, `--superseded-by ID`, in place of
the reason or beside it, in place of the free text of a reason such as
`superseded by S-0003`. `fgraph status` lists it under Removed with
`superseded by` on a line of its own below it, before the reason, when one is given, and `fgraph show` lists
it from both sides, the second read from the record:

```sh
fgraph remove S-0002 --superseded-by S-0003 --reason "refiled as a smaller step"
# removed S-0002

fgraph status
# ...
# removed (1)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   superseded by S-0003, refiled as a smaller step

fgraph show S-0002
# S-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   bucket       removed
#   superseded by S-0003
#   reason       refiled as a smaller step
#   ...

fgraph show S-0003
# S-0003  ...
#   bucket       backlog
#   supersedes   S-0002
#   ...
```

A remove with neither `--reason` nor `--superseded-by` is refused, naming both,
as is an id that is no work item of the record, the work item itself and a
removed work item, with exit 2 and nothing written. A Feature takes `--reason`
alone, and is refused `--superseded-by`.

A started or blocked work item is removed the same way, on main, where it was
started. With the development on it is read whole from the worktree of its
branch and saved removed on main alone, in one commit: its completed Tasks
are kept with their commits and its other Tasks are removed with it, for its
reason. It counts no more under `development.parallel`, so the next start is
taken. Of S-0001 holding T-0001 completed, T-0002 started and T-0003 in
Backlog, its branch holding the commits of its work:

```sh
fgraph remove S-0001 --reason "pivoted"
# removed S-0001
# left branch wi/S-0001-<slug> in <path>: main does not hold every commit of it

fgraph status
# ...
# removed (1)
#   S-0001  Raise the Stories fgraph lists from 0 to 1
#   pivoted

fgraph show S-0001
# ...
#   T-0001  <its title>
#     bucket           completed
#     commit           <sha>
#   ...
#   T-0002  <its title>
#     bucket           removed
#     reason           pivoted
#   ...
#   T-0003  <its title>
#     bucket           removed
#     reason           pivoted
#   ...
```

The branch and its worktree are left while they hold work main does not, for
the developer to remove by hand once it is not wanted, with `git worktree
remove <path>` and `git branch -D wi/S-0001-<slug>`. A work item removed right
after its clean start, whose branch main holds whole, loses both: the remove
says `removed branch wi/S-0001-<slug> in <path>` after `removed S-0001`. Run in
the worktree of the work item, the remove is refused naming main, `S-0001 is
removed on main, in <path>: <worktree> is on wi/S-0001-<slug>`.

A Task of a started work item -- in Backlog, started or blocked -- is removed
the same way, with its reason, in the worktree of its work item once the
development is on. It is kept in the file of its work item as removed, counts
in no progress, and is no Task left to complete before its work item lands.
Of S-0001 holding T-0001 started and T-0002 and T-0003 in Backlog:

```sh
fgraph remove T-0002 --reason "not needed"
# removed T-0002 of S-0001

fgraph remove T-0001 --reason "folded into T-0003"
# removed T-0001 of S-0001

fgraph status
# ...
#   S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
# ...

fgraph show S-0001
# ...
#   T-0002  <its title>
#     bucket           removed
#     reason           not needed
# ...

fgraph remove T-0002 --reason "not needed"
# fgraph: error: T-0002 is removed already
```

The remove of a Task is refused with exit 2 and nothing written when its work
item is in Backlog, blocked, completed or removed, when the Task is completed
or removed already, when the reason is blank, and when `--superseded-by` is
given: a Task takes `--reason` alone.

A Feature still in Backlog is removed the same way, `fgraph remove` with its
id and the reason, and its work items are removed with it, each for the same
reason: a Feature is to its work items what a work item is to its Tasks, and
a removed work item keeps its Tasks. A started or blocked Feature is removed
the same way once no work item of it is started: its started time and its
block are dropped, a work item of it in Backlog is removed with it for the
same reason, and a completed one stays as it is, still Completed under it.
Nothing is deleted. `fgraph status` lists the Feature under Removed with its
reason on a line of its own below it, after the removed work items, and its work items on no line of their
own; `fgraph show` of it lists its bucket, its reason and its work items,
each in its own state. Here F-0001 holds S-0001 and S-0004, both in Backlog:

```sh
fgraph remove F-0001 --reason "dropped from the plan"
# removed F-0001

fgraph status
# backlog (0)
# in-progress (0)
# completed (0)
# removed (2)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   superseded by S-0003
#   F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   dropped from the plan

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       removed
#   reason       dropped from the plan
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (2)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  removed
#   S-0004  Raise the Stories fgraph lists under InProgress from 0 to 1  removed
```

The line of a removed Feature holds no progress: its reason stands in its
place, on a line of its own below it. The Feature and its work items are one write and one commit of the
record, `chore: remove F-0001 in the record`. A work item of it that was
removed before stays as it was, with the reason it had, and a completed one
stays Completed; neither is listed on a line of its own once its Feature is
removed. A work item removed
under a Feature that is not removed keeps its line under Removed.

A remove of a Feature exits 2 and names why, with nothing written:

- when the reason is blank;
- when the Feature is completed or removed already: a started or blocked
  Feature is removed as one in Backlog is;
- when a work item of it is started, naming the first such one, or completed
  under a Feature never started, as under a Feature whose work items were
  started before a Feature had a state;
- when the record does not hold it;
- in the worktree of a work item, whose branch writes that work item alone.

```sh
fgraph remove F-0001 --reason "dropped from the plan"
# fgraph: error: F-0001 cannot be removed: S-0001 is started already

fgraph remove F-0001 --reason "dropped from the plan"
# fgraph: error: F-0001 is completed already
```

A removed Feature takes no move, no amend and no work item, added under it
or put under it; each exits 2 with nothing written:

```sh
fgraph start F-0001
# fgraph: error: F-0001 is removed already

fgraph amend S-0005 --parent F-0001
# fgraph: error: S-0005 cannot be put under F-0001: F-0001 is removed already
```

When the record is inside a git work tree, `fgraph` commits every write of
it, unless `[git] commit = false` of its `config.toml` turns the commits off:
`add`, `amend`, `remove`, `reorder`, `start`, `block`, `unblock`, `complete`
and `config set` each leave one commit that holds the files of the record the
write changed, alone, under a message `fgraph` words. Whatever else is staged
or changed stays out of it:

```sh
fgraph add story "Raise the Stories fgraph lists under Backlog from 0 to 1" \
  --given "a record with no items" --when "a Story is added" \
  --then "fgraph status lists it under Backlog"
# added S-0001

git log -1 --format=%s --name-only
# chore: add S-0001 in the record
#
# .fgraph/items/S-0001.toml
```

The other messages follow the write: `chore: add T-0001 of S-0001 in the
record`, `chore: amend S-0001 in the record` -- a Feature by its id, `chore:
amend F-0001 in the record` --, a Task with its work item, `chore: amend
T-0001 of S-0001 in the record`, `chore: reorder S-0002 before S-0001 in the
record` -- a Feature by its id, `chore: reorder F-0001 before S-0001 in the
record` --, `chore: start T-0001 of S-0001 in the record`,
`chore: start F-0001 in the record` for a Feature and its first work item
together, `chore: remove S-0001 in the record`, `chore: remove T-0001 of
S-0001 in the record` for a Task, `chore: remove F-0001 in the
record` for a Feature and its work items together, `chore: block S-0001 in
the record` and `chore: unblock S-0001 in the record` for a work item,
`chore: block T-0001 of S-0001 in the record`, `chore: unblock T-0001 of
S-0001 in the record`,
`chore: block F-0001 in the record` and `chore: unblock F-0001 in the
record` for a Feature, `chore: unblock F-0001 and start S-0002 in the
record` for a Feature and the next work item its unblock starts, `chore:
complete S-0001 in the record`, `chore: complete S-0001 and F-0001 in the
record` for a work item and the Feature it completes, `chore:
complete S-0001 and start S-0002 in the record` for a work item and the next
one of its Feature, which it starts, `chore: set development.enabled in the
record`. A write that leaves its file as it was
makes no commit. Outside a git work tree a write is made as before, with no
commit and no warning, and so is every write of a record with the commits
turned off. A commit git refuses exits 2 and names the git command, and every
file the write changed is put back as it was. The commits of the development
and their messages stay yours.

Two `fgraph` run at one time on one record write one after the other: every
write takes the lock of its record before it reads and holds it through its
commit, so no two are given one id and no item is lost. The second waits up
to ten seconds, then says the line below, writes nothing and is run again.
`fgraph status` and the other views never wait:

```sh
fgraph add story "Raise the Stories fgraph lists under Backlog from 0 to 1" \
  --given "a record with no items" --when "a Story is added" \
  --then "fgraph status lists it under Backlog"
# fgraph: error: /src/project/.fgraph is being written by another fgraph: run the command again
```

A record git ignores is written without a commit. When a rule of `.gitignore`
names the record, every write is made with no commit and no warning. With the
development on, a start still makes the branch of the Story, at the commit
`main` is on:

```sh
echo ".fgraph/" >> .gitignore

fgraph add story "Raise the Stories fgraph lists under Backlog from 0 to 1" \
  --given "a record with no items" --when "a Story is added" \
  --then "fgraph status lists it under Backlog"
# added S-0001

fgraph start S-0001
# started S-0001
# branch wi/S-0001-raise-the-stories-fgraph in /src/project.worktrees/S-0001-raise-the-stories-fgraph
```

Git checks an ignored directory out in no worktree, so the record stays in
the checkout of `main` alone: the worktree holds the development, and the
Tasks of the Story are added, started and completed in the checkout of
`main`. `fgraph land S-0001 --message "..."` merges the branch there,
completes the Story at the merge commit with no commit of the record, and
removes the worktree and the branch. The start is held to `main` as any other.

A record of another name that is no part of the repository is named by the key
and ignored by a line in `.git/info/exclude`, written before `fgraph init`,
since a folder no rule names is committed by init and by every write as any
record. It then behaves as the record git ignores above, and a worktree reads
the folder under its own top, where an ignored one is not:

```sh
echo ".dpopchev/" >> .git/info/exclude
git config fgraph.record .dpopchev
fgraph init
# record: /path/to/project/.dpopchev
```

## Develop

Needs `uv`, `make` and Python 3.14 (`.python-version`).

```sh
make sync       # create or refresh .venv from uv.lock
make check      # lint, the line limit, typecheck and test
uv run fgraph   # run the command
make wheel      # build the wheel into build/dist/
```

`make help` lists every target.

`make check` holds every module under `src/` to 250 lines: `make lines`, one
of its checks, names each module above the limit with its lines and fails.
The number is written once, `MAX_LINES` in `mk/python.mk`; the tests are not
counted.

Its lint, `make lint`, runs `ruff check` and `ruff format --check`, so a file
ruff would rewrite fails `make check` by name; `make format` rewrites it.

| Path             | Holds                                                        |
| ---------------- | ------------------------------------------------------------ |
| `.fgraph/`       | the record of flowgraph's own work, written by `fgraph`      |
| `src/flowgraph/` | the package                                                  |
| `tests/`         | the suite                                                    |
| `mk/`            | the Makefile, one module per section                         |
| `build/`         | what a make target produces; removed by `make clean`         |
| `local/`         | machine-local inputs, scratch and tool caches; never tracked |

Each subpackage of `src/flowgraph/` holds one aggregate or one command group;
`cli.py` is the one module beside them, the entrypoint.

| Subpackage     | Holds                                              |
| -------------- | -------------------------------------------------- |
| `about/`       | the links of an item, a term or a file             |
| `bug/`         | the Bug kind and its ids                           |
| `criterion/`   | the criterion of a work item and its commit        |
| `development/` | branch, commits, scope, gate and landing           |
| `feature/`     | the Feature, its states, moves and commands        |
| `graph/`       | the nodes and edges of a record as one document    |
| `item/`        | an item's file, ids and commands by id             |
| `knowledge/`   | the findings, decisions and deviations, listed     |
| `parent/`      | the Feature a work item is under, or none          |
| `parser/`      | the arguments of the command line and its refusals |
| `record/`      | the location, configuration and store of a record  |
| `relation/`    | the relations between work items and their check   |
| `spike/`       | the Spike kind and its ids                         |
| `status/`      | the status text, the terminal and the watch        |
| `story/`       | the Story kind, its file and ids                   |
| `task/`        | a Task and the Tasks of one work item              |
| `term/`        | a term of the project and its commands             |
| `upkeep/`      | the Upkeep kind, its file and ids                  |
| `work_item/`   | the work item shared by every kind                 |

## License

MIT, see `LICENSE`.

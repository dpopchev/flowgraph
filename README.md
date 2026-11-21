# flowgraph

flowgraph keeps the record of a project's work. It enforces an agile flow --
work is planned, done and landed in small steps, each one a checked move -- and
it builds the ontology of the project on the way: its terms and how they relate.

## Status

Early: `fgraph` adds a Story to a record, writes its Tasks, takes them from
Backlog through InProgress to Completed with their commits, shows a Story
with its Tasks and lists the record by bucket. An Upkeep moves the same way,
with its own Tasks, and is listed beside the Stories. The Backlog is a queue
that `fgraph reorder` reorders, and a work item still in it is rewritten
with `fgraph amend`. In a git repository `fgraph` commits every write of the
record itself, and starting a work item also checks out its branch in a
worktree of its own.

| Part                            | State                                                    |
| ------------------------------- | -------------------------------------------------------- |
| the `fgraph` command            | runs, prints its help menu                               |
| the wheel                       | built by `make wheel`, ships `fgraph`                    |
| where the record lives          | located on every call but `--help`                       |
| the record and its flow         | a work item with its Tasks, from Backlog to Completed    |
| the kinds of work item          | Story, Upkeep, Bug, Spike                                |
| the level above                 | a Feature groups work items; status lists its bucket     |
| the order of the Backlog        | a queue, reordered by `fgraph reorder`                   |
| the wording of a work item      | rewritten by `fgraph amend` while in Backlog             |
| git                             | every write committed; start branches, `fgraph land` lands |
| the ontology                    | not started                                              |
| flowgraph tracking its own work | its Stories are in `.fgraph/` since 0.4.0                |

The model of the record -- its item types, states and rules -- is
`docs/domain-model.md`. flowgraph keeps its own work in `.fgraph/`: run
`uv run fgraph status` in the checkout to see what is next.

## Use

`fgraph` looks for the record in the directory it runs in: `.fgraph/` first,
then `fgraph/`. When neither is there, it exits 2 and asks for the path:

```sh
fgraph                      # uses ./.fgraph/, else ./fgraph/
fgraph --dir path/to/record # uses the directory given, without a search
```

`fgraph --help` prints the menu of the commands, and every command prints its
own help, its usage and its options, with `--help` or `-h`. Neither needs a
record:

```sh
fgraph start --help
# usage: fgraph start [-h] [--slug TEXT] ID
#
# positional arguments:
#   ID           the id of the work item or of the Task
#
# options:
#   -h, --help   show the help of this command and exit
#   --slug TEXT  the words of a work item's branch after its id, instead of its
#                title's first four
```

`fgraph add --help` lists the kinds it adds, and each kind prints its own:
`fgraph add story --help`.

A record is a directory you create (`mkdir .fgraph`). Add a Story with its
title and its one Given / When / Then, then list the record by bucket. The
title names the outcome: a directional verb, the target metric or behavior,
and the quantified shift or target state (`docs/domain-model.md`, Titles):

```sh
fgraph add story "Raise the Stories fgraph lists under Backlog from 0 to 1" \
  --given "a record with no items" \
  --when "a Story is added" \
  --then "fgraph status lists it under Backlog"
# added ST-0001

fgraph status
# Backlog (1)
#   ST-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
# InProgress (0)
# Completed (0)
```

Write the Tasks of a Story, then show it with them. A Task title names the
output: an imperative verb, the specific artifact, and the target state or
constraint; `--output` says what is there once the Task is completed:

```sh
fgraph add task "Add the show command to src/flowgraph/cli.py, listing a Story" \
  --parent ST-0001 \
  --output "changed: src/flowgraph/cli.py gains the show command"
# added T-0001 to ST-0001

fgraph show ST-0001
# ST-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
#   bucket       Backlog
#   given        a record with no items
#   when         a Story is added
#   then         fgraph status lists it under Backlog
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     expected output  changed: src/flowgraph/cli.py gains the show command
```

`--description "<text>"` adds free text to a Story or a Task. A blank title or
part exits 2 and is named; so does a parent, or a Story to show, that the
record does not hold. Each Story is one file, `items/ST-0001.toml`, in the
record, with its Tasks inside it; a Task id, `T-0001`, counts across the
record. In a git repository it counts across the worktrees too: the next Task
id is one above the highest in the record of main and of every worktree, so a
Task added on a branch never takes an id main hands out meanwhile.

Start a Story once it has a Task, then start its Tasks one by one. `fgraph
start` takes a Story id or a Task id:

```sh
fgraph start ST-0001
# started ST-0001
# branch wi/ST-0001-raise-the-stories-fgraph in /src/project.worktrees/ST-0001-raise-the-stories-fgraph

fgraph start T-0001
# started T-0001 of ST-0001

fgraph status
# Backlog (0)
# InProgress (1)
#   ST-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
# Completed (0)
```

When the record is inside a git work tree, starting a Story commits its file
alone as `chore: start ST-0001 in the record`, as fgraph commits every write
(below), and checks out the branch `wi/<id>-<slug>` at that
commit in a worktree beside the checkout, `<parent>/<checkout>.worktrees/`.
The slug is the first four words of the title, lower-cased and kept to their
letters and digits; `--slug branch-on-start` gives another. Outside a work
tree the Story starts as before and fgraph warns that no branch was made. A
git step refused exits 2 and names the git command: a commit refused puts the
file back as it was, a worktree refused leaves the start committed.

On the branch of a started Story, `wi/ST-0001-<slug>`, fgraph writes that
Story alone: its Tasks are added, started and completed there. A Task for
another Story, a new Story or a reorder of the Backlog exits 2 there and
names the Story the branch owns:

```sh
fgraph add task "Add the show command" --parent ST-0002 --output "changed: cli.py"
# fgraph: error: ST-0002 is not written here: the branch wi/ST-0001-raise-the-stories-fgraph writes ST-0001 alone
```

A Story starts on main alone. `fgraph start` of a Story exits 2 in a work
tree on any other branch, with nothing written and no branch made, and names
the work tree to start it in:

```sh
fgraph start ST-0002
# fgraph: error: ST-0002 starts on main, in /src/project: /src/project.worktrees/ST-0001-raise-the-stories-fgraph is on wi/ST-0001-raise-the-stories-fgraph
```

The start of a Task is not checked against main: a Task starts on the branch
of its Story.

A Task of a started Story is written in its worktree: added, started and
completed there. On main the same write exits 2 and names the worktree:

```sh
fgraph add task "Add the show command" --parent ST-0001 --output "changed: cli.py"
# fgraph: error: ST-0001 is started: its Tasks are written in its worktree, /src/project.worktrees/ST-0001-raise-the-stories-fgraph
```

A started Story whose branch has no worktree is written on main as before.

`fgraph show` then names the bucket of the Story and of each Task that has
left Backlog (`    bucket           InProgress`). A start exits 2 and names
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
`fgraph` does not look it up in git yet:

```sh
fgraph complete T-0001 --commit 3e9ae5c
# completed T-0001 of ST-0001 at 3e9ae5c

fgraph complete ST-0001 --commit 677f9b0
# completed ST-0001 at 677f9b0

fgraph status
# Backlog (0)
# InProgress (0)
# Completed (1)
#   ST-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  677f9b0
```

`fgraph show` names the commit of the Story and of each completed Task. A
complete exits 2 and names why when the item is still in Backlog, when a
Story has Tasks not completed, when the item is completed already, when the
commit is no sha, or when the record does not hold it. A completed Story takes
no new Task.

A started Task that cannot go on is blocked, with the reason and who or what
it waits on. It stays in InProgress and `fgraph show` lists it as blocked:

```sh
fgraph block T-0001 --reason "the review is not back" --waiting-on "the reviewer"
# blocked T-0001 of ST-0001

fgraph show ST-0001
# ...
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     bucket           InProgress, blocked
#     reason           the review is not back
#     waiting on       the reviewer
#     expected output  changed: src/flowgraph/cli.py gains the show command
```

A block exits 2 and names why when the Task is still in Backlog, blocked
already or completed, when the reason or what it waits on is blank, when the
id is a Story's, or when the record does not hold the Task. A blocked Task is
not started or completed, and its Story is not completed, while it is
blocked.

Unblock it once it can go on. It is started again, with the started time it
had, and can be completed or blocked once more:

```sh
fgraph unblock T-0001
# unblocked T-0001 of ST-0001
```

An unblock exits 2 and names why when the Task is not blocked, when the id is
a Story's, or when the record does not hold the Task.

In a git repository `fgraph land` does the landing in one step, run in the
checkout of `main` once every Task of the Story is completed on its branch.
The message of the merge commit is yours:

```sh
fgraph land ST-0001 --message "feat: land the Stories listed under Backlog"
# landed ST-0001 at 677f9b0
```

It merges the branch `wi/ST-0001-*` into `main` as one merge commit under
that message, completes the Story at that commit, commits the record as
`chore: complete ST-0001 in the record`, and removes the worktree and the
branch. A land exits 2 and names why, with nothing merged, when a Task of the
Story is not completed, when the checkout it runs in is not on `main`, when
the Story has no branch or several, when the record is outside a git work
tree, or when git refuses the merge.

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
# Backlog (1)
#   U-0001  Cut the lines of the largest module of src/flowgraph from 1068 to 400
# InProgress (0)
# Completed (0)
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
#   bucket       Backlog
#   observed     fgraph --dir given a file prints a traceback
#   expected     it exits 2 and names the path
# Tasks (0)
```

A Bug takes Tasks and moves as a Story does, by the same commands, and joins
the queue of the Backlog. `fgraph amend B-0001 --expected "..."` rewrites its
criterion; `--given` on a Bug, or `--observed` on a Story, exits 2. A Bug is
kept as `items/B-0001.toml`.

A Spike is a question to answer. Its criterion is a hypothesis, a yes/no
question, and it is completed with the decision that answers it. Its id
counts on its own, `SP-0001`:

```sh
fgraph add spike "Settle whether one file per item can hold the record" \
  --hypothesis "Can one file per item hold the record?"
# added SP-0001

fgraph complete SP-0001 --commit 677f9b0 \
  --decision "yes: one file per work item, its Tasks inside"
# completed SP-0001 at 677f9b0

fgraph show SP-0001
# SP-0001  Settle whether one file per item can hold the record
#   bucket       Completed
#   commit       677f9b0
#   hypothesis   Can one file per item hold the record?
#   decision     yes: one file per work item, its Tasks inside
# ...
```

A Spike takes Tasks and moves as a Story does, and `fgraph land` takes
`--decision` as `fgraph complete` does. A Spike completed without its
decision exits 2, and so does a decision given for any other kind or for a
Task. `fgraph amend SP-0001 --hypothesis "..."` rewrites the hypothesis while
the Spike is in Backlog. A Spike is kept as `items/SP-0001.toml`.

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
# added ST-0001

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       Backlog
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (1)
#   ST-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  Backlog
```

A Feature has no state of its own: its bucket is derived from its work items.
It is InProgress once one of them is started or completed, and Completed when
each is completed or removed. `fgraph show ST-0001` names the Feature as its
`parent`. An add exits 2 and names why when a criterion or the title is blank
or when `--parent` names no Feature of the record. A Feature is kept as
`items/F-0001.toml`.

`fgraph status` lists the Features of the record first, by number, each with
its derived bucket, and then the work items by bucket as before:

```sh
fgraph status
# Features (1)
#   F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5  Backlog
# Backlog (1)
#   ST-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
# InProgress (0)
# Completed (0)
```

The heading Features is listed only when the record holds a Feature. A work
item under a Feature stays in its own bucket; `fgraph show F-0001` lists the
work items of a Feature.

The Backlog is a queue: `fgraph status` lists it in the order the work is to
be pulled. A work item joins the end of the queue when it is added, whatever
its kind; `fgraph reorder` puts one work item right before another:

```sh
fgraph status
# Backlog (2)
#   ST-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   U-0002  Cut the lines one kind of work item holds from 885 to 250
# InProgress (0)
# Completed (0)

fgraph reorder U-0002 --before ST-0002
# moved U-0002 before ST-0002

fgraph status
# Backlog (2)
#   U-0002  Cut the lines one kind of work item holds from 885 to 250
#   ST-0002  Raise the kinds of work item fgraph adds from 1 to 2
# InProgress (0)
# Completed (0)
```

A reorder exits 2 and names why when one of the two is not in Backlog, when
a work item is put before itself, or when a text is no work item id. The
order given is kept as `queue.toml` in the record, apart from the item files.

The buckets past the Backlog list the last one in on top: InProgress the work
item started last, Completed the one completed last. Work items started or
completed at one time are listed by kind and number:

```sh
fgraph status
# Backlog (0)
# InProgress (2)
#   B-0001  Cut the tracebacks fgraph --dir prints for a file from 1 to 0
#   ST-0003  Raise the kinds of work item fgraph adds from 2 to 3
# Completed (2)
#   U-0002  Cut the lines one kind of work item holds from 885 to 250  757fbaf
#   ST-0002  Raise the kinds of work item fgraph adds from 1 to 2  87c0307
```

A work item still in Backlog is rewritten with `fgraph amend`: its title, its
description and each part of its criterion, each by its own option. A part
without its option stays as it was, and so do its Tasks and its place in the
queue:

```sh
fgraph amend ST-0002 --then "fgraph status lists both kinds under Backlog"
# amended ST-0002

fgraph show ST-0002
# ST-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   bucket       Backlog
#   given        a record with a Story
#   when         an Upkeep is added
#   then         fgraph status lists both kinds under Backlog
# Tasks (0)
```

`--title`, `--description`, `--given` and `--when` rewrite the other parts,
several in one call when given together; `--description ""` clears the
description. An amend exits 2 and names why when it names no part, when the
title or a part of the criterion is blank, when the work item is started or
completed already, when the id is a Task's, or when the record does not hold
it.

A work item filed by mistake or superseded is removed from the Backlog with
the reason. Nothing is deleted: it is kept with its Tasks, apart from the
flow, and `fgraph status` lists it under Removed:

```sh
fgraph remove ST-0002 --reason "superseded by ST-0003"
# removed ST-0002

fgraph status
# Backlog (0)
# InProgress (0)
# Completed (0)
# Removed (1)
#   ST-0002  Raise the kinds of work item fgraph adds from 1 to 2  -- superseded by ST-0003
```

The heading Removed is listed only when a work item is removed. A remove
exits 2 and names why when the reason is blank, when the work item is
started, completed or removed already, when the id is a Task's, or when the
record does not hold it. A removed work item takes no Task, no amend and no
move.

When the record is inside a git work tree, `fgraph` commits every write of
it: `add`, `amend`, `reorder`, `start` and `complete` each leave one commit
that holds the files of the record the write changed, alone, under a message
`fgraph` words. Whatever else is staged or changed stays out of it:

```sh
fgraph add story "Raise the Stories fgraph lists under Backlog from 0 to 1" \
  --given "a record with no items" --when "a Story is added" \
  --then "fgraph status lists it under Backlog"
# added ST-0001

git log -1 --format=%s --name-only
# chore: add ST-0001 in the record
#
# .fgraph/items/ST-0001.toml
```

The other messages follow the write: `chore: add T-0001 of ST-0001 in the
record`, `chore: amend ST-0001 in the record`, `chore: reorder ST-0002 before
ST-0001 in the record`, `chore: start T-0001 of ST-0001 in the record`,
`chore: complete ST-0001 in the record`. A write that leaves its file as it
was makes no commit. Outside a git work tree a write is made as before, with
no commit and no warning. A commit git refuses exits 2 and names the git
command, and every file the write changed is put back as it was. The commits
of the development and their messages stay yours.

A record git ignores is written without a commit. When a rule of `.gitignore`
names the record, every write is made with no commit and no warning, and a
start still makes the branch of the Story, at the commit `main` is on:

```sh
echo ".fgraph/" >> .gitignore

fgraph add story "Raise the Stories fgraph lists under Backlog from 0 to 1" \
  --given "a record with no items" --when "a Story is added" \
  --then "fgraph status lists it under Backlog"
# added ST-0001

fgraph start ST-0001
# started ST-0001
# branch wi/ST-0001-raise-the-stories-fgraph in /src/project.worktrees/ST-0001-raise-the-stories-fgraph
```

Git checks an ignored directory out in no worktree, so the record stays in
the checkout of `main` alone: the worktree holds the development, and the
Tasks of the Story are added, started and completed in the checkout of
`main`. `fgraph land ST-0001 --message "..."` merges the branch there,
completes the Story at the merge commit with no commit of the record, and
removes the worktree and the branch. The start is held to `main` as any other.

## Develop

Needs `uv`, `make` and Python 3.14 (`.python-version`).

```sh
make sync       # create or refresh .venv from uv.lock
make check      # lint, the line limit, typecheck and test
uv run fgraph   # run the command
make wheel      # build the wheel into build/dist/
```

`make help` lists every target.

`make check` holds every module under `src/` to 400 lines: `make lines`, one
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

## License

MIT, see `LICENSE`.

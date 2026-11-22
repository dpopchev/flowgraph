# flowgraph

flowgraph keeps the record of a project's work. It enforces an agile flow --
work is planned, done and landed in small steps, each one a checked move -- and
it builds the ontology of the project on the way: its terms and how they relate.

## Status

Early: `fgraph` adds a Story to a record, writes its Tasks, takes them from
Backlog through InProgress to Completed, shows a Story with its Tasks and
lists the record by bucket. An Upkeep moves the same way, with its own Tasks,
and is listed beside the Stories. The Backlog is a queue that `fgraph
reorder` reorders, and a work item still in it is rewritten with `fgraph
amend`. In a git repository `fgraph` commits every write of the record
itself. A record is layered by its configuration, `.fgraph/config.toml`: it
turns the commits of the record off, and once it turns the development on,
starting a work item also checks out its branch in a worktree of its own,
completing an item names the commit that holds its work, and `fgraph land`
lands it. `fgraph config` shows the configuration and sets a key of it. A work
item, and a Feature, keeps the findings, decisions and deviations noted on it with
`fgraph note`, in any state, and `fgraph show` lists them. `fgraph knowledge`
lists the lines of the whole record.

| Part                            | State                                                    |
| ------------------------------- | -------------------------------------------------------- |
| the `fgraph` command            | runs, prints its help menu                               |
| the wheel                       | built by `make wheel`, ships `fgraph`                    |
| where the record lives          | located on every call but `--help`                       |
| the record and its flow         | a work item with its Tasks, from Backlog to Completed    |
| the kinds of work item          | Story, Upkeep, Bug, Spike                                |
| the level above                 | a Feature groups work items, takes each operation of one |
| the order of the Backlog        | a queue, reordered by `fgraph reorder`, Features too     |
| the relations of a work item    | `--depends-on` it waits for, `--filed-during` it found,  |
|                                 | `fgraph remove --superseded-by` the one that replaces it |
| the wording of a work item      | `fgraph amend` in Backlog: parent too, a Feature's too   |
| git                             | every write of the record committed, unless turned off   |
| the layers of a record          | `.fgraph/config.toml`: commits on, development off       |
| the configuration               | every key shown and set by `fgraph config`               |
| the knowledge of an item        | lines noted by `fgraph note` on a work item or a Feature |
| the knowledge of the record     | every line listed by `fgraph knowledge`, newest first    |
| the development                 | once enabled: start branches, `fgraph land` lands        |
| the ontology                    | not started                                              |
| flowgraph tracking its own work | its Stories are in `.fgraph/` since 0.4.0                |

The model of the record -- its item types, states and rules -- is
`docs/domain-model.md`. flowgraph keeps its own work in `.fgraph/`, with the
development turned on: run `uv run fgraph status` in the checkout to see what
is next.

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
#   ID           the id of the work item, of the Task or of the Feature
#
# options:
#   -h, --help   show the help of this command and exit
#   --slug TEXT  the words of a work item's branch after its id, instead of its
#                title's first four; of a Feature, those of its first work item;
#                read with the development on
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
# added S-0001

fgraph status
# Backlog (1)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
# InProgress (0)
# Completed (0)
```

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
record does not hold. Each Story is one file, `items/S-0001.toml`, in the
record, with its Tasks inside it; a Task id, `T-0001`, counts across the
record. In a git repository it counts across the worktrees too: the next Task
id is one above the highest in the record of main and of every worktree, so a
Task added on a branch never takes an id main hands out meanwhile.

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
# fgraph: error: S-0002 cannot start: it depends on S-0001, in Backlog

fgraph show S-0002
# S-0002  Raise the Stories fgraph lists under Backlog from 1 to 2
#   bucket       Backlog
#   depends on   S-0001 (Backlog)
#   ...
```

`fgraph amend S-0002 --depends-on S-0003` replaces what it depends on and
`--depends-on none` takes it all away. An id that is no work item of the
record, a removed work item, the work item itself and a work item that depends
on it, directly or through others, are refused at the write with exit 2, and
nothing is written. The start of a Feature starts its first work item, and the
next work item a completion starts is that of its Feature: both are refused as
the start of that work item is, and say so.

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
#   bucket       Backlog
#   filed during S-0001
#   ...

fgraph show S-0001
# S-0001  ...
#   bucket       InProgress
#   filed here   B-0001
#   ...
```

An id that is no work item of the record and a removed work item are refused
with exit 2, and nothing is written. `fgraph amend` does not take it: when a
work item was found does not change.

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

`merge` is one of three words. Each is a way `fgraph land` puts the work of
the branch on `main`:

| `merge`                     | `main` gains                                               | `--message`                 |
| --------------------------- | ---------------------------------------------------------- | --------------------------- |
| `merge-commit`, the default | one merge commit of the branch, with two parents           | needed: it words the commit |
| `squash`                    | one commit of its own that holds the work, with one parent | needed: it words the commit |
| `fast-forward`              | no new commit: `main` moves to the tip of the branch       | refused: no commit to word  |

Left out, the key is `merge-commit`, the one merge a landing made before the
key. Whatever the way, the Story is completed at the commit `main` is then
on, the record is committed, and the worktree and the branch are removed, as
shown further down with the landing. A landing by `fast-forward` exits 2,
with nothing merged, when `main` holds a commit the branch lacks. It is a key
of the development, so it says nothing with the development off. Any other
word exits 2 naming the key, whatever the command:

```sh
fgraph status
# fgraph: error: /src/project/.fgraph/config.toml: development.merge is "rebase": it takes merge-commit, squash or fast-forward
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
closing": no check per Task run at a complete, and the Given / When / Then of
the Story is neither run nor confirmed by it. `fgraph land` runs the gate
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
```

`none` is how a key that holds no value is listed: `parallel` without a
limit, `gate` without a command. It is no value of the file, so a gate named
`"none"`, listed in its quotes, is not mistaken for it.

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
```

VALUE is a text, read by what its key takes and never guessed from the text,
so `fgraph config set development.gate true` names the command `true`:

| Key                    | VALUE                                      | Set as                                            |
| ---------------------- | ------------------------------------------ | ------------------------------------------------- |
| `git.commit`           | `true` or `false`                          | `fgraph config set git.commit false`              |
| `development.enabled`  | `true` or `false`                          | `fgraph config set development.enabled true`      |
| `development.parallel` | a whole number of 1 or more                | `fgraph config set development.parallel 2`        |
| `development.merge`    | `merge-commit`, `squash` or `fast-forward` | `fgraph config set development.merge squash`      |
| `development.gate`     | a command line, one argument of the shell  | `fgraph config set development.gate "make check"` |

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

A key is taken back to its default by setting that default, `fgraph config
set development.merge merge-commit`: there is no unset. `parallel` and `gate`
have no default to set, so once set they take another value by a set, and are
taken back to none only by removing their line from the file. A set writes
the file whole from its keys, so a comment written in it is not kept. A
`config.toml` fgraph refuses is refused by `fgraph config` too, as by every
command, and is mended in the file.

Start a Story once it has a Task, then start its Tasks one by one. `fgraph
start` takes a Story id or a Task id; with the development on, the start of a
Story names its branch:

```sh
fgraph start S-0001
# started S-0001
# branch wi/S-0001-raise-the-stories-fgraph in /src/project.worktrees/S-0001-raise-the-stories-fgraph

fgraph start T-0001
# started T-0001 of S-0001

fgraph status
# Backlog (0)
# InProgress (1)
#   S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#     => T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
# Completed (0)
```

A work item under InProgress is listed with its progress, `0/1 T`: its Tasks
completed of all it holds. One of three completed reads `1/3 T`, so two are
still to be completed; a started or a blocked Task is not completed yet.

Under it comes the Task being worked, marked `=>`: the started Task of the
work item. A Task in Backlog or completed is not listed, and a Task line does
not count toward the top 5 of a heading (below).

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

The rules of a branch that follow are those of a record with the development
on: with it off fgraph makes no branch `wi/<id>-<slug>` and no worktree, so
every write is taken on `main`. A start given `--slug` then exits 2 naming the
key, of a work item as of a Feature, and starts nothing:

```sh
fgraph start S-0001 --slug branch-on-start
# fgraph: error: S-0001 takes no --slug: the development is off, so its start makes no branch -- set development.enabled = true in /src/project/.fgraph/config.toml
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
started and completed in it. On main the same write exits 2 and names the
worktree:

```sh
fgraph add task "Add the show command" --parent S-0001 --output "changed: cli.py"
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
# Backlog (0)
# InProgress (1)
#   S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#     => T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
# Completed (0)

fgraph show S-0001
# ...
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     bucket           InProgress
#     expected output  changed: src/flowgraph/cli.py gains the show command
```

Run in the worktree of a Story, `fgraph status` and `fgraph show` read the
record of that worktree.

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
# completed T-0001 of S-0001 at 3e9ae5c

fgraph complete S-0001 --commit 677f9b0
# completed S-0001 at 677f9b0

fgraph status
# Backlog (0)
# InProgress (0)
# Completed (1)
#   S-0001  677f9b0  Raise the Stories fgraph lists under Backlog from 0 to 1
```

`fgraph show` names the commit of the Story and of each completed Task. A
complete exits 2 and names why when the item is still in Backlog, when a
Story has Tasks not completed, when the item is completed already, when the
commit is no sha, or when the record does not hold it. A completed Story takes
no new Task.

The commit is the evidence of the development: the work beside the record
that the item is completed with. So `fgraph complete` needs `--commit` with
the development on, of a Task as of a Story, and without it exits 2 naming
the option and the key:

```sh
fgraph complete T-0001
# fgraph: error: T-0001 is completed with --commit: the development is on, development.enabled = true
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
# Backlog (0)
# InProgress (0)
# Completed (1)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1

fgraph show S-0001
# S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
#   bucket       Completed
#   given        a record with no items
#   when         a Story is added
#   then         fgraph status lists it under Backlog
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     bucket           Completed
#     expected output  changed: src/flowgraph/cli.py gains the show command
```

A `--commit` given with the development off is still kept as the evidence,
and status and show list it. The file of an item completed without a commit
holds no `commit` key.

A work item keeps what the work learned as lines of knowledge. `fgraph note`
appends a finding, a decision or a deviation to a work item in any state, Completed and Removed included,
as one write and one commit of the record; `fgraph show` lists the lines after
the Tasks, each with its kind, the date it was noted and its text, and no
heading when there is none. A note takes exactly one of `--finding`,
`--decision` and `--deviation`, with its text:

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
#   S-0001  Add the show command to src/flowgraph/cli.py  Completed
#   S-0002  Add the note command to src/flowgraph/cli.py  Backlog
# Knowledge (1)
#   decision  2026-11-22  the budget is agreed
```

`fgraph knowledge` lists the lines of every work item and every Feature of the
record, the last noted first, each with its date, its kind, the id of its item
and its text. `--kind` narrows the list to `finding`, `decision` or `deviation`;
another word exits 2 naming the three. The decision of a completed Spike is
listed among the decisions at the time the Spike was completed, and stays kept
on the Spike. A record with no line prints one line saying so:

```sh
fgraph knowledge
# 2026-11-24  deviation  S-0001  the second Task was dropped
# 2026-11-23  decision  Q-0001  yes: one file per work item
# 2026-11-22  decision  F-0001  the budget is agreed
# 2026-11-22  decision  S-0001  keep one store
# 2026-11-22  finding  S-0001  the file holds the lines in the order noted

fgraph knowledge --kind decision
# 2026-11-23  decision  Q-0001  yes: one file per work item
# 2026-11-22  decision  F-0001  the budget is agreed
# 2026-11-22  decision  S-0001  keep one store

fgraph knowledge --kind finding
# 2026-11-22  finding  S-0001  the file holds the lines in the order noted
```

A line is never amended or removed. The id of a Task, an id the record does
not hold, a blank text and a note with none or more than one of the three kinds exit 2 and write nothing. With the development on, a
started work item is noted in its worktree, as its Tasks are written, and every
other one, a Feature too, on `main`; the branch of a work item writes that work
item alone, so a Feature is not noted there.

A started Task that cannot go on is blocked, with the reason and who or what
it waits on. It stays in InProgress and `fgraph show` lists it as blocked:

```sh
fgraph block T-0001 --reason "the review is not back" --waiting-on "the reviewer"
# blocked T-0001 of S-0001

fgraph show S-0001
# ...
# Tasks (1)
#   T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
#     bucket           InProgress, blocked
#     reason           the review is not back
#     waiting on       the reviewer
#     expected output  changed: src/flowgraph/cli.py gains the show command
```

`fgraph status` lists a blocked Task under its work item too, marked `!` and
ending with what it waits on:

```sh
fgraph status
# Backlog (0)
# InProgress (1)
#   S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#     !  T-0001  Add the show command to src/flowgraph/cli.py, listing a Story  -- waiting on the reviewer
# Completed (0)
```

A block exits 2 and names why when the Task is still in Backlog, blocked
already or completed, when the reason or what it waits on is blank, when the
id is a Story's, or when the record does not hold the Task. A blocked Task is
not started or completed, and its Story is not completed, while it is
blocked. `fgraph block` and `fgraph unblock` take a started Feature too
(below).

Unblock it once it can go on. It is started again, with the started time it
had, and can be completed or blocked once more:

```sh
fgraph unblock T-0001
# unblocked T-0001 of S-0001
```

An unblock exits 2 and names why when the Task is not blocked, when the id is
a Story's, or when the record does not hold the Task.

In a git repository whose record has the development on, `fgraph land` does
the landing in one step, run in the checkout of `main` once every Task of the
Story is completed on its branch. The message of the merge commit is yours:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# landed S-0001 at 677f9b0
```

It merges the branch `wi/S-0001-*` into `main` as one merge commit under
that message, completes the Story at that commit, commits the record as
`chore: complete S-0001 in the record`, and removes the worktree and the
branch. A land exits 2 and names why, with nothing merged, when the
development is off, when a Task of the Story is not completed, when the
checkout it runs in is not on `main`, when the Story has no branch or
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
```

The message goes with the commit a landing makes. A landing by `merge-commit`
or `squash` exits 2 without `--message`, and one by `fast-forward` exits 2
with it, each naming the key:

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

Every other rule of a landing holds for each way: what it refuses, that
nothing is merged then, and the commit of the record after it.

A landing merges into a checkout of `main` that holds no merge of its own. One
you left unconcluded there is named and left as it was, and a branch that
brings no commit `main` lacks is refused before any commit, so nothing you
staged is taken into the commit of a landing:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# fgraph: error: a merge is held in /src/project: commit it or abort it first
# fgraph: error: wi/S-0001-raise-the-stories-fgraph brings nothing to merge: it holds no commit main lacks
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
counts on its own, `Q-0001`, Q for question:

```sh
fgraph add spike "Settle whether one file per item can hold the record" \
  --hypothesis "Can one file per item hold the record?"
# added Q-0001

fgraph complete Q-0001 --commit 677f9b0 \
  --decision "yes: one file per work item, its Tasks inside"
# completed Q-0001 at 677f9b0

fgraph show Q-0001
# Q-0001  Settle whether one file per item can hold the record
#   bucket       Completed
#   commit       677f9b0
#   hypothesis   Can one file per item hold the record?
#   decision     yes: one file per work item, its Tasks inside
# ...
```

A Spike takes Tasks and moves as a Story does, and `fgraph land` takes
`--decision` as `fgraph complete` does. A Spike completed without its
decision exits 2, and so does a decision given for any other kind or for a
Task. With the development off a Spike is completed with its decision and no
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
#   bucket       Backlog
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (1)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  Backlog
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
`fgraph amend` too, and a Feature in Backlog is removed with `fgraph remove`,
its work items with it (below). A Feature is kept as `items/F-0001.toml`.

`fgraph status` lists a Feature inside its bucket, as one line in place of
its work items: its id, its progress and its title. Here a Story that stands
alone, S-0002, was added after the Feature, and the Story under the Feature
is on no line of its own:

```sh
fgraph status
# Backlog (2)
#   F-0001  0/1 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
# InProgress (0)
# Completed (0)
```

The progress, `0/1 W`, is the work items of the Feature completed of all it
holds: one of three completed reads `1/3 W`, so two are still to be done. A
removed work item is counted in neither number, and a Feature without a work
item reads `0/0 W`.

A Feature holds a place of its own in the Backlog: it joins the end when it
is added, after the work items and the Features `fgraph reorder` placed and
those added before it, and `fgraph reorder` places it as a work item (below).
It is counted once, beside the heading and toward the top 5 (below). Its
work items in Backlog and its completed ones are listed on no line and
counted beside no heading: they are counted in its progress, and `fgraph show
F-0001` lists each with its bucket. A removed one keeps its line under
Removed, unless the Feature itself is removed: that Feature is listed there
in place of its work items (below).

`fgraph start` takes a Feature, and starts its first work item with it:

```sh
fgraph start F-0001
# started F-0001 with S-0001
```

A Feature is to its work items what a work item is to its Tasks, the
principle the developer's words of 2026-11-21 were filed under (F-0002): it
does not start without one, its work item does not start before it, and one
of them is started at a time. The first work item is the first of its work
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
# Backlog (1)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
# InProgress (1)
#   F-0001  0/1 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#     S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#       => T-0001  Add the show command to src/flowgraph/cli.py, listing a Story
# Completed (0)
```

The lines under a Feature belong to it: they count neither beside the heading
nor toward the top 5.

A blocked Task marks its Feature: while the started work item of a Feature
holds a blocked Task, `fgraph status` lists the Feature with `!` before its
id, in the first column of its line, and ends the line with what that Task
waits on, as the line of the Task does:

```sh
fgraph block T-0001 --reason "the review is not back" --waiting-on "the reviewer"
# blocked T-0001 of S-0001

fgraph status
# Backlog (1)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
# InProgress (1)
# ! F-0001  0/1 W  Raise the kinds of work a project tracks with fgraph from 1 to 5  -- waiting on the reviewer
#     S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
#       !  T-0001  Add the show command to src/flowgraph/cli.py, listing a Story  -- waiting on the reviewer
# Completed (0)
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
on is what the cut takes first. A Feature is blocked itself with `fgraph
block` too (below); blocking a work item is not built.

The completion of a work item of a started Feature starts the next one, in
the same write: a Feature starts its work items one by one. The next one is
the first of its work items in Backlog in the order they start in, the one
`fgraph reorder` gives them (below). Here F-0001 holds S-0001, started, and
S-0003, a second Story under it, in Backlog:

```sh
fgraph complete S-0001 --commit 677f9b0
# completed S-0001 at 677f9b0
# started S-0003

fgraph status
# Backlog (1)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
# InProgress (1)
#   F-0001  1/2 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#     S-0003  0/1 T  Raise the Stories fgraph lists under Completed from 0 to 1
# Completed (0)
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
# started S-0003
# branch wi/S-0003-raise-the-stories-fgraph in /src/project.worktrees/S-0003-raise-the-stories-fgraph
```

A next work item that cannot start stays in Backlog, and the completion
stands: it exits 0, is committed as a completion alone, `chore: complete
S-0001 in the record`, and names why on the line after it, as `not started:`
and the refusal of that start:

- when it has no Task: `not started: S-0003 has no Task to start with`;
- when `[development] parallel` refuses one more started work item:
  `not started: S-0003 cannot start: development.parallel = 1, started already: S-0002`;
- when another work item of the Feature is started, as one started before
  its Feature was: `not started: S-0003 cannot start: F-0001 starts one work
  item at a time, started already: S-0004`;
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
# Backlog (1)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
# InProgress (0)
# Completed (1)
#   F-0001  1/1 W  677f9b0  Raise the kinds of work a project tracks with fgraph from 1 to 5

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       Completed
#   commit       677f9b0
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (1)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  Completed
```

The Feature holds the commit of that completion as its evidence, and none
when the work item is completed without one, as with the development off:
`completed S-0001`, then `completed F-0001`, and the line of the Feature is
`F-0001  1/1 W  <title>`. The line of a completed Feature is its id, its
progress, its commit and its title: the progress stays right after the id, as
on its line in any bucket, and the commit stands before the title, as on the
line of a completed work item. It is placed under Completed by its completed
time, and its completed work items stay within it: counted in its progress,
listed by `fgraph show F-0001`, on no line of `fgraph status`. The Feature
and the work item are completed in one commit of the record, `chore: complete
S-0001 and F-0001 in the record`.

With the development on, `fgraph land` of the last work item completes the
Feature the same way, at the commit the landing leaves main on:

```sh
fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# landed S-0001 at 3e9ae5c
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
in the record`:

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
what it waits on after its title, the look of a Feature marked by a blocked
Task (above), and `fgraph show` lists it as blocked, with its reason and what
it waits on. Here F-0001 holds S-0001, started, and S-0003 in Backlog:

```sh
fgraph block F-0001 --reason "the budget is not agreed" --waiting-on "the sponsor"
# blocked F-0001

fgraph status
# Backlog (1)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
# InProgress (1)
# ! F-0001  0/2 W  Raise the kinds of work a project tracks with fgraph from 1 to 5  -- waiting on the sponsor
#     S-0001  0/1 T  Raise the Stories fgraph lists under Backlog from 0 to 1
# Completed (0)

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       InProgress, blocked
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

`fgraph land S-0001` says the same after `landed S-0001 at 3e9ae5c`. The
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
work item of the Feature is started the unblock starts none: it says
`unblocked F-0001` alone and its commit is `chore: unblock F-0001 in the
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
- when `[development] parallel` refuses one more started work item:
  `F-0001 cannot start: development.parallel = 1, started already: S-0002`.

A work item does not start before its Feature, and one work item of a Feature
is started at a time. `fgraph start` of a work item in Backlog under a
Feature exits 2 naming the Feature while the Feature is not started, and
naming the started work item of the Feature while one is -- here S-0003, a
second Story under F-0001:

```sh
fgraph start S-0001
# fgraph: error: S-0001 cannot start: F-0001 is not started, start it first

fgraph start S-0003
# fgraph: error: S-0003 cannot start: F-0001 starts one work item at a time, started already: S-0001
```

The completion of S-0001 starts S-0003 by itself (above); `fgraph start
S-0003` is for the one a completion left in Backlog. The one at a time of a
Feature and `parallel` both hold, for the start a completion makes too: a Feature starts one work item at a time, and `parallel` counts every
started work item of the record, those under a Feature among them.

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
moves to Completed when all are.

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
fgraph status
# Backlog (2)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   U-0002  Cut the lines one kind of work item holds from 885 to 250
# InProgress (0)
# Completed (0)

fgraph reorder U-0002 --before S-0002
# moved U-0002 before S-0002

fgraph status
# Backlog (2)
#   U-0002  Cut the lines one kind of work item holds from 885 to 250
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
# InProgress (0)
# Completed (0)
```

A Feature is placed in the queue as a work item is: `fgraph reorder` takes
its id on either side. Here a second Story, S-0003, was added under the
Feature; the Story that stands alone is put before the Feature, then the
Feature before it again:

```sh
fgraph reorder S-0002 --before F-0001
# moved S-0002 before F-0001

fgraph status
# Backlog (2)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   F-0001  0/2 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
# InProgress (0)
# Completed (0)

fgraph reorder F-0001 --before S-0002
# moved F-0001 before S-0002

fgraph status
# Backlog (2)
#   F-0001  0/2 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2
# InProgress (0)
# Completed (0)
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
#   bucket       Backlog
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (2)
#   S-0003  Raise the Upkeeps fgraph lists under Backlog from 0 to 1  Backlog
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  Backlog
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
# Backlog (0)
# InProgress (2)
#   B-0001  0/2 T  Cut the tracebacks fgraph --dir prints for a file from 1 to 0
#   S-0003  1/3 T  Raise the kinds of work item fgraph adds from 2 to 3
# Completed (3)
#   U-0002  757fbaf  Cut the lines one kind of work item holds from 885 to 250
#   F-0001  1/1 W  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   S-0002  87c0307  Raise the kinds of work item fgraph adds from 1 to 2
```

`fgraph status` lists the top 5 under each heading -- Backlog, InProgress,
Completed and Removed -- in the order above, and then how many more the
heading holds. A Feature counts as one item, as a work item does. The count
beside the heading stays that of all its items:

```sh
fgraph status
# Backlog (0)
# InProgress (0)
# Completed (7)
#   S-0007  e82af5a  Raise the kinds of work item fgraph takes to Completed from 3 to 4
#   S-0006  c29f1b7  Raise the kinds of work item fgraph takes to Completed from 2 to 3
#   S-0005  c399b40  Raise the kinds of work item fgraph takes to Completed from 1 to 2
#   S-0004  87c0307  Raise the kinds of work item fgraph adds and lists from 1 to 2
#   S-0003  4f1ae12  Raise the buckets a Story can reach from 2 to 3
#   ... 2 more
```

`fgraph status --all` lists every item, with no such line.

On a terminal `fgraph status` cuts each line to the width of the terminal and
ends a line it cut with `...`, so every item stays on one line. The commit of
a completed work item, when it has one, stands before its title, where a cut
keeps it:

```sh
fgraph status        # on a terminal 60 columns wide
# Backlog (0)
# InProgress (0)
# Completed (7)
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
fgraph watch --count 3  # three frames, then exit 0
```

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

`--parent` puts a work item in Backlog under a Feature, and with the word
`none` takes it out of the one it is under, to stand alone; it is given alone
or beside the other parts:

```sh
fgraph amend S-0002 --parent F-0001
# amended S-0002

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       Backlog
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (2)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  Backlog
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2  Backlog

fgraph amend S-0002 --parent none
# amended S-0002
```

The work item keeps its id, its Tasks and its entry in `queue.toml`, which an
amend never writes. Put under a Feature it is on no line of the Backlog and
starts where that entry orders it among the work items of the Feature; taken
out it is the line of the Backlog that entry places. One never placed follows
the placed ones as it was added. A `--parent` that names the Feature it is
under already moves it nowhere, and the amend is taken.

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
#   bucket       Backlog
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds a Story, an Upkeep, a Bug and a Spike
# Work items (1)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  Backlog
```

`--description ""` clears its description. An amend of a Feature exits 2,
writes nothing and names why:

- when it names no part;
- when the title or a criterion is blank;
- when it is given an option of a work item: `--given`, `--when`, `--then`,
  `--observed`, `--expected`, `--hypothesis` or `--parent`;
- when the Feature is started, blocked or completed: only one in Backlog is
  amended, as only a work item in Backlog is;
- when the record does not hold it.

`--criterion` given to a work item is refused the same way: only a Feature
states criteria.

```sh
fgraph amend F-0001 --then "fgraph status lists it under Backlog"
# fgraph: error: F-0001 has no then: a Feature is amended by its title, its description and its criteria

fgraph amend F-0001 --title "Raise the kinds of work a project tracks with fgraph from 1 to 4"
# fgraph: error: F-0001 is started already

fgraph amend S-0002 --criterion "a developer adds every kind of work"
# fgraph: error: S-0002 has no criteria: only a Feature states them
```

A work item filed by mistake or superseded is removed from the Backlog with
the reason. Nothing is deleted: it is kept with its Tasks, apart from the
flow, and `fgraph status` lists it under Removed:

```sh
fgraph remove S-0002 --reason "superseded by S-0003"
# removed S-0002

fgraph status
# Backlog (0)
# InProgress (0)
# Completed (0)
# Removed (1)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2  -- superseded by S-0003
```

The heading Removed is listed only when a work item or a Feature is removed.
A remove exits 2 and names why when the reason is blank, when the work item
is started, completed or removed already, when the id is a Task's, or when
the record does not hold it. A removed work item takes no Task, no amend and
no move.

A work item superseded by another names it, `--superseded-by ID`, in place of
the reason or beside it, in place of the free text of a reason such as
`superseded by S-0003`. `fgraph status` lists it under Removed with
`superseded by` before the reason, when one is given, and `fgraph show` lists
it from both sides, the second read from the record:

```sh
fgraph remove S-0002 --superseded-by S-0003 --reason "refiled as a smaller step"
# removed S-0002

fgraph status
# ...
# Removed (1)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2  -- superseded by S-0003, refiled as a smaller step

fgraph show S-0002
# S-0002  Raise the kinds of work item fgraph adds from 1 to 2
#   bucket       Removed
#   superseded by S-0003
#   reason       refiled as a smaller step
#   ...

fgraph show S-0003
# S-0003  ...
#   bucket       Backlog
#   supersedes   S-0002
#   ...
```

A remove with neither `--reason` nor `--superseded-by` is refused, naming both,
as is an id that is no work item of the record, the work item itself and a
removed work item, with exit 2 and nothing written. A Feature takes `--reason`
alone, and is refused `--superseded-by`.

A Feature still in Backlog is removed the same way, `fgraph remove` with its
id and the reason, and its work items are removed with it, each for the same
reason: a Feature is to its work items what a work item is to its Tasks, and
a removed work item keeps its Tasks. Nothing is deleted. `fgraph status`
lists the Feature under Removed with its reason, after the removed work
items, and its work items on no line of their own; `fgraph show` of it lists
its bucket, its reason and its work items. Here F-0001 holds S-0001 and
S-0004, both in Backlog:

```sh
fgraph remove F-0001 --reason "dropped from the plan"
# removed F-0001

fgraph status
# Backlog (0)
# InProgress (0)
# Completed (0)
# Removed (2)
#   S-0002  Raise the kinds of work item fgraph adds from 1 to 2  -- superseded by S-0003
#   F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5  -- dropped from the plan

fgraph show F-0001
# F-0001  Raise the kinds of work a project tracks with fgraph from 1 to 5
#   bucket       Removed
#   reason       dropped from the plan
# Criteria (2)
#   a developer sees every work item of the project by bucket
#   a developer adds every kind of work
# Work items (2)
#   S-0001  Raise the Stories fgraph lists under Backlog from 0 to 1  Removed
#   S-0004  Raise the Stories fgraph lists under InProgress from 0 to 1  Removed
```

The line of a removed Feature holds no progress: it holds no work item any
more. The Feature and its work items are one write and one commit of the
record, `chore: remove F-0001 in the record`. A work item of it that was
removed before stays as it was, with the reason it had, and is listed on no
line of its own either once its Feature is removed. A work item removed
under a Feature that is not removed keeps its line under Removed.

A remove of a Feature exits 2 and names why, with nothing written:

- when the reason is blank;
- when the Feature is started, blocked, completed or removed already: only
  one in Backlog is removed, as only a work item in Backlog is;
- when a work item of it is started or completed, as under a Feature whose
  work items were started before a Feature had a state: its work items are
  all in Backlog, or removed already;
- when the record does not hold it;
- in the worktree of a work item, whose branch writes that work item alone.

```sh
fgraph remove F-0001 --reason "dropped from the plan"
# fgraph: error: F-0001 is started already

fgraph remove F-0001 --reason "dropped from the plan"
# fgraph: error: F-0001 cannot be removed: S-0001 is completed already
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
amend F-0001 in the record` --, `chore: reorder S-0002 before S-0001 in the
record` -- a Feature by its id, `chore: reorder F-0001 before S-0001 in the
record` --, `chore: start T-0001 of S-0001 in the record`,
`chore: start F-0001 in the record` for a Feature and its first work item
together, `chore: remove S-0001 in the record`, `chore: remove F-0001 in the
record` for a Feature and its work items together, `chore: block T-0001 of
S-0001 in the record`, `chore: unblock T-0001 of S-0001 in the record`,
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

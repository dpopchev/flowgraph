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
lands it. `fgraph config` shows the configuration and sets a key of it.

| Part                            | State                                                    |
| ------------------------------- | -------------------------------------------------------- |
| the `fgraph` command            | runs, prints its help menu                               |
| the wheel                       | built by `make wheel`, ships `fgraph`                    |
| where the record lives          | located on every call but `--help`                       |
| the record and its flow         | a work item with its Tasks, from Backlog to Completed    |
| the kinds of work item          | Story, Upkeep, Bug, Spike                                |
| the level above                 | a Feature groups work items, one line in its bucket      |
| the order of the Backlog        | a queue, reordered by `fgraph reorder`                   |
| the wording of a work item      | rewritten by `fgraph amend` while in Backlog             |
| git                             | every write of the record committed, unless turned off   |
| the layers of a record          | `.fgraph/config.toml`: commits on, development off       |
| the configuration               | every key shown and set by `fgraph config`               |
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
completed with `fgraph complete`, and `fgraph land` exits 2 naming the key:

```sh
fgraph start S-0001
# started S-0001

fgraph land S-0001 --message "feat: land the Stories listed under Backlog"
# fgraph: error: S-0001 cannot land: the development is off -- set development.enabled = true in /src/project/.fgraph/config.toml
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
time whatever the key, as shown further down.

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
every write is taken on `main`.

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
of its Story.

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
the commit of each Task are current before the landing:

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
blocked.

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

A record whose `config.toml` names a `[development] gate` runs that command
at every landing, by each way, between the merge and the commit. The gate
runs in the checkout of `main` with the work of the branch merged in, not yet
committed; a landing by `fast-forward` runs it on that same merge before
`main` moves to the tip. When the gate fails the landing exits 2 naming the
command and its status, as shown with the configuration, and the merge is
dropped: `main` is where it was.

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

A Feature has no state of its own: its bucket is derived from its work items.
It is InProgress once one of them is started or completed, and Completed when
each is completed or removed. `fgraph show S-0001` names the Feature as its
`parent`. An add exits 2 and names why when a criterion or the title is blank
or when `--parent` names no Feature of the record. A Feature is kept as
`items/F-0001.toml`.

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
is added, after the work items `fgraph reorder` placed and those added before
it. It is counted once, beside the heading and toward the top 5 (below). Its
work items in Backlog and its completed ones are listed on no line and
counted beside no heading: they are counted in its progress, and `fgraph show
F-0001` lists each with its bucket. A removed one keeps its line under
Removed.

Once a work item of the Feature is started the Feature is listed under
InProgress, and the started work item under its line, indented, with its
progress and its Task being worked:

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
nor toward the top 5. When each work item of the Feature is completed or
removed, the Feature is one line under Completed, `F-0001  1/1 W  <title>`.

This reverses the developer's decision of 2026-11-21 that listed the Features
in a block of their own above the buckets, under a heading `Features`, each
with its derived bucket before its title, while a work item under a Feature
stayed in its own bucket. By the developer's words of the same day a Feature
is part of the Backlog and just holds its work items, so no heading
`Features` is listed any more.

The Backlog is a queue: `fgraph status` lists it in the order the work is to
be pulled. A work item joins the end of the queue when it is added, whatever
its kind, and so does a Feature; `fgraph reorder` puts one work item right
before another, and takes no Feature yet:

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

A reorder exits 2 and names why when one of the two is not in Backlog, when
a work item is put before itself, or when a text is no work item id. The
order given is kept as `queue.toml` in the record, apart from the item files.

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
to the width the terminal has then; written to a pipe or a file the frames
follow each other, every line whole. Ctrl-C ends it, with exit 0:

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

The heading Removed is listed only when a work item is removed. A remove
exits 2 and names why when the reason is blank, when the work item is
started, completed or removed already, when the id is a Task's, or when the
record does not hold it. A removed work item takes no Task, no amend and no
move.

When the record is inside a git work tree, `fgraph` commits every write of
it, unless `[git] commit = false` of its `config.toml` turns the commits off:
`add`, `amend`, `reorder`, `start`, `complete` and `config set` each leave
one commit that holds the files of the record the write changed, alone, under
a message `fgraph` words. Whatever else is staged or changed stays out of it:

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
record`, `chore: amend S-0001 in the record`, `chore: reorder S-0002 before
S-0001 in the record`, `chore: start T-0001 of S-0001 in the record`,
`chore: complete S-0001 in the record`, `chore: set development.enabled in
the record`. A write that leaves its file as it was makes no commit. Outside
a git work tree a write is made as before, with no commit and no warning, and
so is every write of a record with the commits turned off. A commit git
refuses exits 2 and names the git command, and every file the write changed
is put back as it was. The commits of the development and their messages stay
yours.

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

# flowgraph

flowgraph keeps the record of a project's work. It enforces an agile flow --
work is planned, done and landed in small steps, each one a checked move -- and
it builds the ontology of the project on the way: its terms and how they relate.

## Status

Early: `fgraph` adds a Story to a record, writes its Tasks, takes them from
Backlog through InProgress to Completed with their commits, shows a Story
with its Tasks and lists the record by bucket. An Upkeep moves the same way,
with its own Tasks, and is listed beside the Stories.

| Part                            | State                                                    |
| ------------------------------- | -------------------------------------------------------- |
| the `fgraph` command            | runs, prints its help menu                               |
| the wheel                       | built by `make wheel`, ships `fgraph`                    |
| where the record lives          | located on every call but `--help`                       |
| the record and its flow         | a work item with its Tasks, from Backlog to Completed    |
| the kinds of work item          | Story, Upkeep                                            |
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
record.

Start a Story once it has a Task, then start its Tasks one by one. `fgraph
start` takes a Story id or a Task id:

```sh
fgraph start ST-0001
# started ST-0001

fgraph start T-0001
# started T-0001 of ST-0001

fgraph status
# Backlog (0)
# InProgress (1)
#   ST-0001  Raise the Stories fgraph lists under Backlog from 0 to 1
# Completed (0)
```

`fgraph show` then names the bucket of the Story and of each Task that has
left Backlog (`    bucket           InProgress`). A start exits 2 and names
why when the Story has no Task, when a Task's Story is still in Backlog, when
the item is started or completed already, or when the record does not hold
it.

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
fgraph start T-0001
# started T-0001 of U-0001
fgraph complete T-0001 --commit 0636c92
# completed T-0001 of U-0001 at 0636c92
fgraph complete U-0001 --commit 6db7fac
# completed U-0001 at 6db7fac
```

An Upkeep is kept as `items/U-0001.toml`, its Tasks inside it.

## Develop

Needs `uv`, `make` and Python 3.14 (`.python-version`).

```sh
make sync       # create or refresh .venv from uv.lock
make check      # lint, typecheck and test
uv run fgraph   # run the command
make wheel      # build the wheel into build/dist/
```

`make help` lists every target.

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

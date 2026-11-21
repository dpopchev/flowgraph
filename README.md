# flowgraph

flowgraph keeps the record of a project's work. It enforces an agile flow --
work is planned, done and landed in small steps, each one a checked move -- and
it builds the ontology of the project on the way: its terms and how they relate.

## Status

Early: `fgraph` adds a Story to a record, writes its Tasks, starts them,
shows a Story with its Tasks and lists the record by bucket; nothing is
completed yet.

| Part                            | State                                             |
| ------------------------------- | ------------------------------------------------- |
| the `fgraph` command            | runs, prints its help menu                        |
| the wheel                       | built by `make wheel`, ships `fgraph`             |
| where the record lives          | located on every call but `--help`                |
| the record and its flow         | a Story with its Tasks, in Backlog and InProgress |
| the ontology                    | not started                                       |
| flowgraph tracking its own work | its Backlog is in `.fgraph/` since 0.4.0          |

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
the item is started already, or when the record does not hold it.

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

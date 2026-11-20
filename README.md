# flowgraph

flowgraph keeps the record of a project's work. It enforces an agile flow --
work is planned, done and landed in small steps, each one a checked move -- and
it builds the ontology of the project on the way: its terms and how they relate.

## Status

Early: `fgraph` adds a Story to a record and lists the record by bucket; no
item moves yet.

| Part                            | State                                     |
| ------------------------------- | ----------------------------------------- |
| the `fgraph` command            | runs, prints its help menu                |
| the wheel                       | built by `make wheel`, ships `fgraph`     |
| where the record lives          | located on every call but `--help`        |
| the record and its flow         | a Story is added and listed in Backlog    |
| the ontology                    | not started                               |
| flowgraph tracking its own work | from the first version that can record    |

The model of the record -- its item types, states and rules -- is
`docs/domain-model.md`.

## Use

`fgraph` looks for the record in the directory it runs in: `.fgraph/` first,
then `fgraph/`. When neither is there, it exits 2 and asks for the path:

```sh
fgraph                      # uses ./.fgraph/, else ./fgraph/
fgraph --dir path/to/record # uses the directory given, without a search
```

A record is a directory you create (`mkdir .fgraph`). Add a Story with its
title and its one Given / When / Then, then list the record by bucket:

```sh
fgraph add story "fgraph lists an added Story under Backlog" \
  --given "a record with no items" \
  --when "a Story is added" \
  --then "fgraph status lists it under Backlog"
# added ST-0001

fgraph status
# Backlog (1)
#   ST-0001  fgraph lists an added Story under Backlog
# InProgress (0)
# Completed (0)
```

`--description "<text>"` adds free text to the Story. A blank title or part
exits 2 and is named. Each Story is one file, `stories/ST-0001.toml`, in the
record.

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
| `src/flowgraph/` | the package                                                  |
| `tests/`         | the suite                                                    |
| `mk/`            | the Makefile, one module per section                         |
| `build/`         | what a make target produces; removed by `make clean`         |
| `local/`         | machine-local inputs, scratch and tool caches; never tracked |

## License

MIT, see `LICENSE`.

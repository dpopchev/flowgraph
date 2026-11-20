# flowgraph

flowgraph keeps the record of a project's work. It enforces an agile flow --
work is planned, done and landed in small steps, each one a checked move -- and
it builds the ontology of the project on the way: its terms and how they relate.

## Status

Early: `fgraph` finds where a record lives, and nothing of the record runs yet.

| Part                            | State                                     |
| ------------------------------- | ----------------------------------------- |
| the `fgraph` command            | runs, prints its help menu                |
| the wheel                       | built by `make wheel`, ships `fgraph`     |
| where the record lives          | located on every call but `--help`        |
| the record and its flow         | not started                               |
| the ontology                    | not started                               |
| flowgraph tracking its own work | from the first version that can record    |

## Use

`fgraph` looks for the record in the directory it runs in: `.fgraph/` first,
then `fgraph/`. When neither is there, it exits 2 and asks for the path:

```sh
fgraph                      # uses ./.fgraph/, else ./fgraph/
fgraph --dir path/to/record # uses the directory given, without a search
```

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

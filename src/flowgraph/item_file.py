"""The file of a work item: its criterion table, and the write that reads itself back."""

from collections.abc import Callable, Mapping
from pathlib import Path

import tomli_w
from pydantic import BaseModel, ConfigDict

from flowgraph.criterion import Scenario, make_scenario


class CriterionFile(BaseModel):
    """The criterion table of a work item file: its Given / When / Then."""

    model_config = ConfigDict(extra="forbid")

    given: str
    when: str
    then: str


def criterion_primitives(scenario: Scenario) -> dict[str, object]:
    """The criterion as the primitives its table holds."""
    return {"given": scenario.given, "when": scenario.when, "then": scenario.then}


def scenario_held(held: CriterionFile) -> Scenario:
    """The criterion a validated table holds, built through its constructor."""
    return make_scenario(held.given, held.when, held.then)


def write_checked(
    path: Path,
    primitives: Mapping[str, object],
    holds: Callable[[Path], bool],
    mismatch: Exception,
) -> None:
    """Write the primitives as the TOML file at the path, once the written file holds them.

    The file is written beside the path and replaces it only when holds says the written file
    reads back as meant. Raises mismatch otherwise; the file at the path is then as it was.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    beside = path.with_name(f"{path.name}.tmp")
    beside.write_text(tomli_w.dumps(primitives), encoding="utf-8")
    if not holds(beside):
        beside.unlink()
        raise mismatch
    beside.replace(path)

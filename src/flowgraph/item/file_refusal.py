"""A file of the record the validator refuses is said in one line in the words of fgraph.

The first error alone, its key dotted, the state of a file whose model is chosen by its state line
named, never the lines of the validator nor its link (S-0109).
"""

import json

from pydantic import ValidationError


def _listed(expected: str) -> str:
    """The tags pydantic lists, written without their quotes and joined by `or` before the last."""
    tags = [tag.strip().strip("'") for tag in expected.split(",")]
    return tags[0] if len(tags) == 1 else f"{', '.join(tags[:-1])} or {tags[-1]}"


def file_refusal(error: ValidationError, *, tagged: bool = False) -> str:
    """The first error of a refused file in one line; tagged when its model is chosen by state."""
    first = error.errors()[0]
    loc = [str(part) for part in first["loc"]]
    where = f"the state {loc.pop(0)}" if tagged and loc else "the file"
    kind = first["type"]
    if kind in ("union_tag_not_found", "union_tag_invalid"):
        ctx = first.get("ctx", {})
        key = ".".join([*loc, str(ctx.get("discriminator", "state")).strip("'")])
        if kind == "union_tag_not_found":
            return f"{key} is missing"
        return f"{key} is {json.dumps(ctx['tag'])}: it takes {_listed(ctx['expected_tags'])}"
    key = ".".join(loc)
    if kind == "extra_forbidden":
        return f"{key} is no key of {where}"
    if kind == "missing":
        return f"{key} is missing, which {where} takes"
    return f"{key} is {json.dumps(first['input'], default=str)} in {where}: {first['msg']}"

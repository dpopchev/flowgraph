"""What a config.toml refused says: the key, dotted, its value as written and what it takes.

Split from `flowgraph.record.config`, which builds the configuration and raises with this text.
"""

import json
from enum import Enum

from pydantic import ValidationError

from flowgraph.record.layers import Driver, Merge, Mode, TagAt

# What a count takes, whether its value is no whole number or one below 1.
_COUNT = "a whole number of 1 or more"

# What a gate takes, whether its value is no text or a blank one.
_COMMAND = "a command line"


def _one_of(words: type[Enum]) -> str:
    """What a key of words takes: each word of the enum, the last after an `or`."""
    named = [str(word.value) for word in words]
    return f"{', '.join(named[:-1])} or {named[-1]}"


# What the value of a key takes, by the type of the error pydantic reports of it.
_TAKES = {
    "bool_type": "true or false",
    "model_type": "a table",
    "int_type": _COUNT,
    "greater_than_equal": _COUNT,
    "string_type": _COMMAND,
    "string_pattern_mismatch": _COMMAND,
}

# What a key of words takes, by the dotted key: pydantic reports each as an `enum` error.
_WORDS = {
    "development.merge": _one_of(Merge),
    "development.driver": _one_of(Driver),
    "development.mode": _one_of(Mode),
    "delivery.tag": _one_of(TagAt),
}

# What the archive board takes, whether its value is no text or a blank one.
_PATH = "a path"

# What a key takes whatever the type of its error, by the dotted key; it wins over _TAKES.
_TAKES_BY_KEY = {
    "archive.board": _PATH,
    "development.branch_max": "a whole number of days of 1 or more, as 1d",
}


def refusal(error: ValidationError) -> str:
    """What the first error of a file refused says: its key, dotted, and why it is refused."""
    first = error.errors()[0]
    key = ".".join(str(part) for part in first["loc"])
    if first["type"] == "extra_forbidden":
        return f"{key} is no {'table' if len(first['loc']) == 1 else 'key'} of the configuration"
    written = json.dumps(first["input"], default=str)
    if key in _TAKES_BY_KEY:
        takes = _TAKES_BY_KEY[key]
    else:
        takes = _WORDS.get(key) if first["type"] == "enum" else _TAKES.get(first["type"])
    return f"{key} is {written}: {first['msg'] if takes is None else f'it takes {takes}'}"

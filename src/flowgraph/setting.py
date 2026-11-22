"""The configuration through fgraph: every key of it shown, one key of it set.

A key is listed dotted, `development.enabled`, with its value as the file writes it, at its
default when the file leaves it out. A key that holds no value -- no limit, no gate -- is listed
as `none`, which is no value of the file, so no text is mistaken for it. A set writes one key
among the settings of the record and keeps the others; its value arrives as a text and is read
by what the key takes, never guessed from the text.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import assert_never

from flowgraph.config import (
    DEVELOPMENT_ENABLED,
    DEVELOPMENT_GATE,
    DEVELOPMENT_MERGE,
    DEVELOPMENT_PARALLEL,
    GIT_COMMIT,
    Config,
    ConfigError,
    Gate,
    Gated,
    Limit,
    LoadSettings,
    Parallel,
    SaveSettings,
    Settings,
    Ungated,
    Unlimited,
    make_config,
    settings_text,
)
from flowgraph.item import Written

# How a key that holds no value is listed: no value of the file.
NONE = "none"

# A value of the file, as a key holds it.
Value = bool | int | str

# The text of a whole number, as a count is given on the command line.
_WHOLE = re.compile(r"-?[0-9]+")

# The texts of the two values of a truth, as the file writes them.
_TRUTHS = {"true": True, "false": False}


class Takes(Enum):
    """What a key takes in the file: how the text of its value is read."""

    TRUTH = "true or false"
    COUNT = "a whole number"
    TEXT = "a text"


@dataclass(frozen=True)
class Key:
    """A key of the configuration: its dotted name, what it takes and its value there.

    `held` is the value a configuration holds under the key, None when it holds none.
    """

    name: str
    takes: Takes
    held: Callable[[Config], Value | None]


@dataclass(frozen=True)
class SettingSet:
    """A key set: what the write says with the message of its commit, and the configuration left."""

    written: Written
    config: Config


def _most(limit: Limit) -> int | None:
    """The count the limit holds; None for no limit."""
    match limit:
        case Parallel(most):
            return most
        case Unlimited():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _command(gate: Gate) -> str | None:
    """The command line the gate holds; None for no gate."""
    match gate:
        case Gated(command):
            return command
        case Ungated():
            return None
        case _ as unreachable:
            assert_never(unreachable)


# Every key of the configuration, in the order it is listed.
KEYS = (
    Key(GIT_COMMIT, Takes.TRUTH, lambda config: config.git.commit),
    Key(DEVELOPMENT_ENABLED, Takes.TRUTH, lambda config: config.development.enabled),
    Key(DEVELOPMENT_PARALLEL, Takes.COUNT, lambda config: _most(config.development.parallel)),
    Key(DEVELOPMENT_MERGE, Takes.TEXT, lambda config: config.development.merge.value),
    Key(DEVELOPMENT_GATE, Takes.TEXT, lambda config: _command(config.development.gate)),
)


def _line(key: Key, config: Config) -> str:
    """The key with the value the configuration holds under it, as the file writes that value."""
    held = key.held(config)
    return f"{key.name} = {NONE if held is None else json.dumps(held)}"


def show_config(config: Config) -> str:
    """Every key of the configuration with its value, one a line."""
    return "".join(f"{_line(key, config)}\n" for key in KEYS)


def _read(takes: Takes, text: str) -> Value:
    """The value the text names, by what its key takes.

    A text that names no such value stays a text, which the configuration refuses naming the
    key.
    """
    match takes:
        case Takes.TRUTH:
            return _TRUTHS.get(text, text)
        case Takes.COUNT:
            return int(text) if _WHOLE.fullmatch(text) else text
        case Takes.TEXT:
            return text
        case _ as unreachable:
            assert_never(unreachable)


def _key_named(name: str) -> Key:
    """The key of that dotted name; raises ConfigError naming it when there is no such key."""
    for key in KEYS:
        if key.name == name:
            return key
    raise ConfigError(f"{name} is no key of the configuration")


def with_setting(settings: Settings, name: str, text: str) -> Settings:
    """The settings with the key of that name set to the value the text names, the others kept.

    Raises ConfigError naming the key when the configuration has no such key or the key does
    not take the value, and naming both keys when the set turns the development on with the
    commits off.
    """
    key = _key_named(name)
    table, _, inside = name.partition(".")
    after = {**settings, table: {**settings.get(table, {}), inside: _read(key.takes, text)}}
    make_config(settings_text(after))
    return after


def set_setting(
    name: str, text: str, load_settings: LoadSettings, save_settings: SaveSettings
) -> SettingSet:
    """Set the key of that name to the value the text names among the settings of the record.

    Raises ConfigError as with_setting does; nothing is saved then.
    """
    key = _key_named(name)
    after = with_setting(load_settings(), name, text)
    config = make_config(settings_text(after))
    save_settings(after)
    written = Written(f"set {_line(key, config)}\n", f"chore: set {name} in the record")
    return SettingSet(written, config)

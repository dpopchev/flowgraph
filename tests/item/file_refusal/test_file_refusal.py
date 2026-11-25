"""file_refusal says the first error of a refused file in one line, with no link."""

from collections.abc import Callable
from typing import Annotated, Any, Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from flowgraph.item.file_refusal import file_refusal

pytestmark = pytest.mark.edge


class Plain(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    count: int = 0
    tags: list[int] = []


class Waiting(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["waiting"]
    title: str


class Held(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["held"]
    title: str
    since: str


TAGGED = TypeAdapter(Annotated[Waiting | Held, Field(discriminator="state")])


def refused(validate: Callable[[Any], object], data: object) -> ValidationError:
    """The error the validator raises for the data."""
    with pytest.raises(ValidationError) as caught:
        validate(data)
    return caught.value


def plain(data: dict[str, object]) -> str:
    return file_refusal(refused(Plain.model_validate, data))


def tagged(data: dict[str, object]) -> str:
    return file_refusal(refused(TAGGED.validate_python, data), tagged=True)


@pytest.mark.parametrize(
    ("data", "said"),
    [
        ({"name": "a", "token": 1}, "token is no key of the file"),
        ({}, "name is missing, which the file takes"),
    ],
)
def test_a_file_without_a_state_says_the_key(data: dict[str, object], said: str) -> None:
    assert plain(data) == said


@pytest.mark.parametrize(
    ("data", "said"),
    [
        ({"state": "waiting", "title": "t", "token": 1}, "token is no key of the state waiting"),
        ({"state": "held", "title": "t"}, "since is missing, which the state held takes"),
        ({"state": "gone", "title": "t"}, 'state is "gone": it takes waiting or held'),
        ({"title": "t"}, "state is missing"),
    ],
)
def test_a_file_chosen_by_its_state_says_the_state(data: dict[str, object], said: str) -> None:
    assert tagged(data) == said


@pytest.mark.parametrize(
    ("data", "head"),
    [
        ({"name": "a", "count": "x"}, 'count is "x" in the file: '),
        ({"name": "a", "tags": ["x"]}, 'tags.0 is "x" in the file: '),
    ],
)
def test_a_value_of_the_wrong_type_is_named_with_its_value(
    data: dict[str, object], head: str
) -> None:
    assert plain(data).startswith(head)


def test_a_value_of_the_wrong_type_in_a_state_is_named_with_the_state() -> None:
    assert tagged({"state": "held", "title": 3}).startswith("title is 3 in the state held: ")


def test_a_file_with_three_errors_is_said_in_one_line() -> None:
    assert "\n" not in plain({"token": 1, "count": "x"})


def test_the_line_holds_no_link_of_the_validator() -> None:
    assert "errors.pydantic.dev" not in plain({"token": 1})

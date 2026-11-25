"""The rule that says which files of a commit the brief of a Task does not name."""

import pytest

from flowgraph.development.named_files import files_not_named

pytestmark = pytest.mark.model

NAMED = [
    ("changed: src/a.py", "src/a.py"),
    ("`src/a.py`,", "src/a.py"),
    ("(src/a.py)", "src/a.py"),
    ("in src/a.py.", "src/a.py"),
    ('"src/a.py";', "src/a.py"),
    ("<src/a.py>:", "src/a.py"),
    ("./src/a.py", "src/a.py"),
    ("one\nsrc/a.py\ntwo", "src/a.py"),
    ("the README.md", "README.md"),
    (".gitignore", ".gitignore"),
    ("tests/unit/", "tests/unit/a/test_x.py"),
    ("(tests/unit/).", "tests/unit/a/test_x.py"),
    ("src/a.py:12", "src/a.py"),
    ("src/a.py::test_x", "src/a.py"),
    ("`src/a.py:12`,", "src/a.py"),
]

NOT_NAMED = [
    ("", "src/a.py"),
    ("an output", "work.txt"),
    ("a.py", "src/a.py"),
    ("src/a.py:x", "src/a.py"),
    ("src/a.py", "src/a.pyc"),
    ("tests/unit", "tests/unit/a.py"),
    ("tests/unit/", "tests/unit_more/a.py"),
    ("SRC/A.PY", "src/a.py"),
    ("/home/src/a.py", "src/a.py"),
    ("src/*.py", "src/a.py"),
    ("src\\a.py", "src/a.py"),
    ("./ / .", "a.txt"),
]


@pytest.mark.parametrize(("text", "file"), NAMED)
def test_a_file_a_word_of_the_text_names_is_named(text: str, file: str) -> None:
    assert files_not_named([file], [text]) == []


@pytest.mark.parametrize(("text", "file"), NOT_NAMED)
def test_a_file_no_word_of_the_text_names_is_not_named(text: str, file: str) -> None:
    assert files_not_named([file], [text]) == [file]


def test_the_files_not_named_come_in_the_order_given() -> None:
    brief = ["Change src/a.py", "an output", ""]
    assert files_not_named(["docs/m.md", "src/a.py", "other.txt"], brief) == [
        "docs/m.md",
        "other.txt",
    ]


@pytest.mark.parametrize("place", [0, 1, 2], ids=["title", "output", "description"])
def test_a_file_named_in_one_text_of_three_is_named_whichever_text_holds_it(place: int) -> None:
    brief = ["a title", "an output", "a description"]
    brief[place] = "src/a.py"
    assert files_not_named(["src/a.py"], brief) == []


def test_no_file_changed_gives_no_file() -> None:
    assert files_not_named([], ["src/a.py"]) == []

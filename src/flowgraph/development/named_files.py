"""The files a commit may change: those the brief of a Task names.

The brief of a Task -- its title, its expected output and its description -- names the files its
commit may change (S-0142, the scope rule 1 of board 1); the rule reads words, not intent.
"""

import re
from collections.abc import Iterable

_OPENING = "([{<\"'`"
_CLOSING = ")]}>\"'`,;:.!?"
_LINE_OR_TEST = re.compile(r":(?=[0-9:])")


def path_words(text: str) -> frozenset[str]:
    """The words of the text that may name a path, cleaned of the punctuation around them.

    The brackets and quotes at the start of a word and the punctuation at its end are stripped,
    one leading ./ is dropped, and a line number or a test name after a colon is cut, so
    src/a.py:12 and src/a.py::test_x are read as src/a.py.
    """
    words = (word.lstrip(_OPENING).rstrip(_CLOSING) for word in text.split())
    cleaned = (_LINE_OR_TEST.split(word.removeprefix("./"), maxsplit=1)[0] for word in words)
    return frozenset(word for word in cleaned if word)


def files_not_named(changed: Iterable[str], brief: Iterable[str]) -> list[str]:
    """The files, in the order given, that no text of the brief names.

    A file, as git writes it, is named when a word of a text equals it, or ends in / and starts it.
    """
    words = frozenset().union(*(path_words(text) for text in brief))
    directories = tuple(word for word in words if word.endswith("/"))
    return [file for file in changed if file not in words and not file.startswith(directories)]

"""The journal of a store: each file it writes, with its content before the first write.

It names the files a write of the record changed, which is what its commit holds, and puts them
back as they were when git refuses that commit.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Change:
    """A file a store writes and its content before the first write; None when it was not there."""

    file: Path
    before: bytes | None


def _content(file: Path) -> bytes | None:
    """The content of the file now, or None when there is no such file."""
    return file.read_bytes() if file.is_file() else None


def noted(journal: list[Change], file: Path) -> list[Change]:
    """Adapter: the journal with the file noted as it is now, before it is written.

    A file noted already keeps the content noted first.
    """
    if all(change.file != file for change in journal):
        journal.append(Change(file, _content(file)))
    return journal


def changed_files(journal: Iterable[Change]) -> list[Path]:
    """Adapter: the files whose content differs from the one noted, in the order noted."""
    return [change.file for change in journal if _content(change.file) != change.before]


def restore(journal: Iterable[Change]) -> None:
    """Adapter: put every file back as it was noted; one that was not there is removed."""
    for change in journal:
        if change.before is None:
            change.file.unlink(missing_ok=True)
        else:
            change.file.write_bytes(change.before)

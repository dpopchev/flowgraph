"""The time a file of the record holds: read with its offset, or refused in one line."""

from datetime import datetime
from typing import Annotated

from pydantic import ValidationInfo, ValidatorFunctionWrapHandler, WrapValidator

# What a refusal gives as the way to write a time.
EXAMPLE = "2026-01-01 09:00:00+00:00"


class NoOffsetError(Exception):
    """A time of a file written with no offset, as a day alone.

    It is no ValueError on purpose: pydantic folds a ValueError of a validator into its own error
    of several lines, and this one must reach the reader of the file as it is.
    """


def _with_offset(
    value: object, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
) -> datetime:
    read = handler(value)
    if read.utcoffset() is None:
        raise NoOffsetError(
            f"{info.field_name} = {value} is a time with no offset: write it with one, as {EXAMPLE}"
        )
    return read


# The time a field of a file holds: a datetime with its offset, or NoOffsetError.
HeldTime = Annotated[datetime, WrapValidator(_with_offset)]

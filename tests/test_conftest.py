"""Tests for the slowest-tests report of tests/conftest.py, run in throwaway pytest sessions."""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.edge  # each test drives the conftest against a throwaway project

CONFTEST = (Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")
REPORT = "last-run/slowest.md"

TWELVE = "\n".join(f"def test_{n:02}():\n    pass\n" for n in range(12))

RANKED = """
import time

def test_fast():
    pass

def test_slow():
    time.sleep(0.1)

def test_middle():
    time.sleep(0.05)
"""

SLOW_SETUP = """
import time
import pytest

@pytest.fixture
def slow_fixture():
    time.sleep(0.1)

def test_slow_setup(slow_fixture):
    pass

def test_slow_body():
    time.sleep(0.05)
"""

IN_A_CLASS = """
class TestThing:
    def test_inside(self):
        pass
"""


def run(pytester: pytest.Pytester, source: str, *args: str) -> pytest.RunResult:
    pytester.makeconftest(CONFTEST)
    pytester.makepyfile(test_sample=source)
    return pytester.runpytest(*args)


def rows(pytester: pytest.Pytester, source: str) -> list[list[str]]:
    """The cells of each table row the report holds after one run of source."""
    run(pytester, source, f"--slowest-file={REPORT}")
    lines = (pytester.path / REPORT).read_text(encoding="utf-8").splitlines()[2:]
    return [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]


def test_no_report_without_the_option(pytester: pytest.Pytester) -> None:
    run(pytester, TWELVE)
    assert not (pytester.path / "last-run").exists()


def test_report_lists_ten_tests(pytester: pytest.Pytester) -> None:
    assert len(rows(pytester, TWELVE)) == 10


def test_report_lists_the_slowest_first(pytester: pytest.Pytester) -> None:
    assert [row[1] for row in rows(pytester, RANKED)] == ["test_slow", "test_middle", "test_fast"]


def test_report_counts_setup_and_teardown(pytester: pytest.Pytester) -> None:
    assert rows(pytester, SLOW_SETUP)[0][1] == "test_slow_setup"


def test_row_names_the_module_and_the_test(pytester: pytest.Pytester) -> None:
    assert rows(pytester, RANKED)[0][:2] == ["test_sample.py", "test_slow"]


def test_test_in_a_class_is_named_with_its_class(pytester: pytest.Pytester) -> None:
    assert rows(pytester, IN_A_CLASS)[0][1] == "TestThing::test_inside"


def test_duration_is_in_seconds_to_the_millisecond(pytester: pytest.Pytester) -> None:
    assert re.fullmatch(r"\d+\.\d{3}", rows(pytester, RANKED)[0][2])


def test_a_run_overwrites_the_report(pytester: pytest.Pytester) -> None:
    rows(pytester, TWELVE)
    assert len(rows(pytester, IN_A_CLASS)) == 1

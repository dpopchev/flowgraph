"""The `fgraph` command line: it locates the record and runs the command on it.

Without a command it shows the help menu and names the record.
"""

import argparse
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Never, assert_never

from flowgraph.about import about_item
from flowgraph.criterion import (
    Criterion,
    make_defect,
    make_hypothesis,
    make_scenario,
)
from flowgraph.development import RunGate, check_slug_branched, run_gate
from flowgraph.development.commit import OpenGit, Said, commit_written, open_git
from flowgraph.development.land import land_item
from flowgraph.development.parallel import check_parallel
from flowgraph.development.scope import (
    check_complete_on_main,
    check_start_on_main,
    scope_in,
    within,
    worktree_of_item,
)
from flowgraph.development.worktrees import across_worktrees, held_elsewhere
from flowgraph.feature.amend import amend_named
from flowgraph.feature.block import block_named, unblock_named
from flowgraph.feature.item import (
    add_feature_item,
    complete_feature_item,
    is_feature_id,
    parent_named,
    show_any_item,
)
from flowgraph.feature.next import complete_and_start_next
from flowgraph.feature.note import note_named
from flowgraph.feature.remove import remove_named
from flowgraph.feature.start import (
    check_start_under_feature,
    start_feature_item,
)
from flowgraph.graph import graph_text
from flowgraph.item.commands import (
    Written,
    add_item,
    kind_named,
    reorder_item,
    start_item,
    status_item,
    write_task,
)
from flowgraph.knowledge import DECISION, DEVIATION, FINDING
from flowgraph.knowledge.governed import governs_asked
from flowgraph.knowledge.list import show_knowledge
from flowgraph.parent import parent_asked
from flowgraph.parser import REFUSED, TOP, build_command_line, help_asked
from flowgraph.record import (
    CONFIG,
    Config,
    Found,
    Given,
    GivenMissing,
    IsDir,
    LoadConfig,
    NotFound,
    Now,
    locate,
    make_config,
    read_config,
)
from flowgraph.record.setting import set_setting, show_config, unset_setting
from flowgraph.record.store import OpenStore, Store, open_files
from flowgraph.relation.depends import (
    amends_asked,
    check_start_waits,
    depends_asked,
    filed_during_asked,
)
from flowgraph.relation.read import check_relations
from flowgraph.status.terminal import Height, Width, no_terminal, terminal_height, terminal_width
from flowgraph.status.text import cut_lines
from flowgraph.status.watch import Wait, framed, make_pace, watch
from flowgraph.term.about import about_asked
from flowgraph.term.item import add_term_item, relate_term_item, terms_text
from flowgraph.work_item import (
    Amendment,
)

__all__ = ["Store", "open_files", "open_git", "read_config", "run", "run_gate"]

# Write text to a stream; what it returns is ignored, so a stream's write and a list's append fit.
Write = Callable[[str], object]


def _criterion(args: argparse.Namespace) -> Criterion:
    """The criterion the arguments of an add state, in the form the kind added takes.

    Raises EmptyPartError naming the first part that is blank.
    """
    match args.kind:
        case "bug":
            return make_defect(args.observed, args.expected)
        case "spike":
            return make_hypothesis(args.hypothesis)
        case _:
            return make_scenario(args.given, args.when, args.then)


def _written(
    args: argparse.Namespace, store: Store, now: Now, config: Config, cwd: Path, open_git: OpenGit
) -> Written | None:
    """Make the write the arguments name on the store; None when they name a view or no command.

    The configuration says whether a complete needs its commit; the directory fgraph runs in,
    cwd, is where the paths a note governs are taken from. Raises the refusal of the write;
    nothing is saved then.
    """
    match args.command:
        case "add" if args.kind == "task":
            return write_task(args.parent, args.title, args.output, args.description, store, now)
        case "add" if args.kind == "term":
            return add_term_item(args.name, args.means, store, now)
        case "relate":
            return relate_term_item(args.first, args.kind, args.second, store)
        case "add" if args.kind == "feature":
            about = about_asked(args.about, store) or ()
            return add_feature_item(args.title, args.criterion, args.description, store, now, about)
        case "add":
            kind = kind_named(args.kind)
            under = parent_named(args.parent, store)
            criterion = _criterion(args)
            depends_on = depends_asked(args.depends_on, None, store) or ()
            filed_during = filed_during_asked(args.filed_during, store)
            amends = amends_asked(args.amends, store)
            about = about_asked(args.about, store) or ()
            return add_item(
                kind,
                args.title,
                criterion,
                args.description,
                store,
                now,
                under,
                depends_on,
                filed_during,
                amends,
                about,
            )
        case "amend":
            amended = None if is_feature_id(args.id) else args.id
            parts = Amendment(
                args.title,
                args.description,
                args.given,
                args.when,
                args.then,
                args.observed,
                args.expected,
                args.hypothesis,
                None if args.parent is None else parent_asked(args.parent),
                depends_asked(args.depends_on, amended, store),
                about_asked(args.about, store),
            )
            return amend_named(args.id, parts, args.criterion, store)
        case "complete" if is_feature_id(args.id):
            return complete_feature_item(args.id, args.commit, store, now)
        case "complete":
            return complete_and_start_next(args.id, args.commit, store, now, config, args.decision)
        case "start" if is_feature_id(args.id):
            return start_feature_item(args.id, args.slug, store, now, config)
        case "start":
            return start_item(args.id, args.slug, store, now)
        case "block":
            return block_named(args.id, args.reason, args.waiting_on, store, now)
        case "unblock":
            return unblock_named(args.id, store, now, config)
        case "remove":
            return remove_named(args.id, args.reason, store, now, args.superseded_by)
        case "note":
            kind, text = next(
                (kind, text)
                for kind, text in (
                    (FINDING, args.finding),
                    (DECISION, args.decision),
                    (DEVIATION, args.deviation),
                )
                if text is not None
            )
            about = about_asked(args.about, store) or ()
            governs = governs_asked(args.governs, cwd, open_git)
            return note_named(args.id, kind, text, store, now, about, governs)
        case "reorder":
            return reorder_item(args.id, args.before, store)
        case _:
            return None


def _no_wait(seconds: float) -> None:
    """The wait of a run given none: the next frame of watch follows at once."""


def _no_config(record: Path) -> Config:
    """The configuration of a run given none to read: the defaults, whatever the record holds."""
    return make_config("")


def _no_gate(command: str, directory: Path) -> Never:
    """The gate of a run given none to run it: a contract, such a run lands under no gate."""
    raise AssertionError(f"run() was given no run_gate to run {command!r} in {directory}")


def _said(
    args: argparse.Namespace,
    store: Store,
    now: Now,
    record: Path,
    open_git: OpenGit,
    width: Width,
    config: Config,
    run_gate: RunGate,
    cwd: Path,
) -> Said | None:
    """Run the command the arguments name on the record; None when they name none.

    The directory fgraph runs in, cwd, is where the path of fgraph about a file is taken from.

    A write is committed once it is made. The lines of status are cut to the width, when there
    is one. The configuration says whether a start branches, how many work items are started at
    once, whether a landing is taken and the gate it runs through run_gate. A set of the
    configuration is committed by the configuration it leaves, so one that turns the commits
    off is left uncommitted. Raises the refusal of the command, a git step refused among them.
    """
    if args.command == "complete":
        check_complete_on_main(args.id, record, open_git)
    if args.command == "start":
        check_slug_branched(args.id, args.slug, config.development.enabled, record / CONFIG)
        check_start_on_main(args.id, record, open_git)
        check_start_under_feature(args.id, store)
        check_start_waits(args.id, store)
        check_parallel(args.id, store.find_work_item_rows, config)
    written = _written(args, store, now, config, cwd, open_git)
    if written is not None:
        return commit_written(written, store, record, open_git, config)
    match args.command:
        case "config" if args.action == "set":
            done = set_setting(args.key, args.value, store.load_settings, store.save_settings)
            return commit_written(done.written, store, record, open_git, done.config)
        case "config" if args.action == "unset":
            done = unset_setting(args.key, store.load_settings, store.save_settings)
            return commit_written(done.written, store, record, open_git, done.config)
        case "config":
            return Said(show_config(config))
        case "land":
            return land_item(
                args.id, args.message, store, now, record, open_git, config, run_gate, args.decision
            )
        case "knowledge":
            return Said(show_knowledge(args.kind, args.about, store))
        case "terms":
            return Said(terms_text(store))
        case "graph":
            return Said(graph_text(args.format, store))
        case "about":
            return Said(about_item(args.id, store, cwd, open_git))
        case "show":
            return Said(show_any_item(args.id, store))
        case "status":
            return Said(cut_lines(status_item(store, None if args.all else TOP), width()))
        case _:
            return None


def _watch(
    args: argparse.Namespace, store: Store, write: Write, wait: Wait, width: Width, height: Height
) -> None:
    """Write the frames of watch on the record: each what status writes then, read anew.

    A frame is cut to the width and the height the terminal has then and replaces the one
    before it; without a width it is whole and follows it. Raises PaceError when the seconds or
    the count asked for are no positive number; no frame is written then.
    """
    pace = make_pace(args.seconds, args.count)
    top = None if args.all else TOP

    def read_frame() -> str:
        return framed(status_item(store, top), width(), height())

    watch(read_frame, write, wait, pace)


def run(
    argv: Sequence[str],
    cwd: Path,
    is_dir: IsDir,
    write: Write,
    write_error: Write,
    *,
    open_store: OpenStore,
    open_git: OpenGit,
    now: Now,
    width: Width = no_terminal,
    height: Height = no_terminal,
    wait: Wait = _no_wait,
    load_config: LoadConfig = _no_config,
    run_gate: RunGate = _no_gate,
) -> int:
    """Read the arguments, locate the record in cwd, run the command and return the exit status.

    The help option needs no record, after a command as alone: it prints the help of the command
    the arguments name. Every other call fails with 2 when there is no record. A write finds the
    git work tree of the record through open_git and is committed there. The lines of status are
    cut to the width of the terminal; without one, as by default, they are whole. Watch writes
    its frames as it goes, each cut to the height of the terminal too, and waits between two by
    wait, which by default returns at once; it
    exits with 0 once its count is written or Ctrl-C ends it. The configuration of the record is
    read through load_config before any command runs, the defaults by default; one that is
    refused fails with 2, whatever the command, and so does a record whose relation names nothing
    or closes a cycle, which is checked as the worktrees compose it, before any command runs. A
    landing runs the gate of the configuration through run_gate, which a run that lands under a
    gate is given: the default runs none.
    """
    command_line = build_command_line()
    parser = command_line.parser
    asked = help_asked(argv, command_line)
    if asked is not None:
        write(asked)
        return 0
    args = parser.parse_args(argv)
    match locate(cwd, args.dir, is_dir):
        case Found(path) | Given(path):
            store = within(
                across_worktrees(open_store(path), path, open_git, open_store),
                partial(scope_in, path, open_git),
                partial(worktree_of_item, path, open_git),
            )
            try:
                config = load_config(path)
                check_relations(path, store, partial(held_elsewhere, path, open_git, open_store))
                if args.command == "watch":
                    _watch(args, store, write, wait, width, height)
                    return 0
                said = _said(args, store, now, path, open_git, width, config, run_gate, cwd)
            except REFUSED as error:
                write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                return 2
            if said is None:
                write(parser.format_help())
                write(f"record: {path}\n")
                return 0
            write(said.out)
            if said.warning:
                write_error(said.warning)
            return 0
        case NotFound(searched, tried):
            names = " or ".join(f"{name}/" for name in tried)
            write_error(f"{parser.format_usage()}fgraph: error: no {names} in {searched}")
            write_error(" -- pass --dir PATH\n")
            return 2
        case GivenMissing(path):
            write_error(f"{parser.format_usage()}fgraph: error: --dir {path} is no directory\n")
            return 2
        case _ as unreachable:
            assert_never(unreachable)


def main() -> None:
    """Run the command in the working directory of the process, on its arguments and streams.

    Each write to stdout is flushed, so a frame of watch reaches a pipe as it is written.
    """
    sys.exit(
        run(
            sys.argv[1:],
            Path.cwd(),
            Path.is_dir,
            partial(print, end="", flush=True),
            sys.stderr.write,
            open_store=open_files,
            open_git=open_git,
            now=lambda: datetime.now(UTC),
            width=terminal_width,
            height=terminal_height,
            wait=time.sleep,
            load_config=read_config,
            run_gate=run_gate,
        )
    )


if __name__ == "__main__":
    main()

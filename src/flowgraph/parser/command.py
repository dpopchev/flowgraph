"""The command the arguments of the command line name, run on the record: a write or a view.

A write is committed once it is made; a view says its text. Each raises the refusal of the
command, which the command line writes as a usage error.
"""

import argparse
from functools import partial
from pathlib import Path

from flowgraph.development import RunGate
from flowgraph.development.commit import OpenGit, Said, commit_written
from flowgraph.development.commit_task import commit_task
from flowgraph.development.land import land_item
from flowgraph.development.release import release_trunk
from flowgraph.development.remove_started import branch_removed
from flowgraph.development.sync import sync_branch
from flowgraph.feature.amend import amend_named
from flowgraph.feature.block import block_named, unblock_named
from flowgraph.feature.item import (
    add_feature_item,
    complete_feature_item,
    is_feature_id,
    parent_named,
)
from flowgraph.feature.next import complete_and_start_next
from flowgraph.feature.note import note_named
from flowgraph.feature.remove import remove_named
from flowgraph.feature.start import start_feature_item
from flowgraph.item.commands import (
    Written,
    add_item,
    kind_named,
    reorder_item,
    write_task,
)
from flowgraph.item.hand import hand_item
from flowgraph.item.moves import start_item
from flowgraph.item.progress import note_progress
from flowgraph.item.verify import verify_item, verify_item_no
from flowgraph.knowledge import DECISION, DEVIATION, FINDING, make_mark
from flowgraph.knowledge.governed import governs_asked
from flowgraph.knowledge.supersede import supersedes_asked
from flowgraph.parent import NO_CRITERION, parent_asked, realizes_asked
from flowgraph.parser.checks import check_command
from flowgraph.parser.start import start_named
from flowgraph.parser.stated import criterion_added, decision_given, deviation_given
from flowgraph.parser.views import view_said
from flowgraph.record import Config, Now
from flowgraph.record.setting import set_setting, show_config, unset_setting
from flowgraph.record.store import Store
from flowgraph.relation.depends import amends_asked, depends_asked, filed_during_asked
from flowgraph.status import status_output, tops_asked, tops_of
from flowgraph.status.next import start_limit
from flowgraph.status.terminal import Width
from flowgraph.status.top import top_to_start
from flowgraph.term.about import about_asked
from flowgraph.term.item import add_term_item, relate_term_item
from flowgraph.work_item import (
    Amendment,
    Complexity,
    make_complexity,
)


def _complexity_asked(word: str | None) -> Complexity | None:
    """The complexity the option names; None when it is not given.

    Raises ComplexityError naming the three words when it is none of them.
    """
    return None if word is None else make_complexity(word)


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
            return write_task(
                args.parent, args.title, args.output, args.description, store, now, args.check
            )
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
            criterion = criterion_added(args)
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
                _complexity_asked(args.complexity),
                realizes_asked(args.realizes) or NO_CRITERION,
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
                _complexity_asked(args.complexity),
                realizes_asked(args.realizes),
                args.output,
                args.check,
            )
            return amend_named(args.id, parts, args.criterion, store, deviation_given(args, now))
        case "complete" if is_feature_id(args.id):
            return complete_feature_item(args.id, args.commit, store, now)
        case "complete":
            decision = decision_given(args)
            return complete_and_start_next(args.id, args.commit, store, now, config, decision)
        case "start" if is_feature_id(args.id):
            return start_feature_item(args.id, args.slug, store, now, config, args.agent)
        case "start":
            return start_item(args.id, args.slug, store, now, args.agent)
        case "block":
            return block_named(args.id, args.reason, args.waiting_on, store, now)
        case "unblock":
            return unblock_named(args.id, store, now, config)
        case "hand":
            return hand_item(args.id, args.agent, store)
        case "remove":
            return remove_named(args.id, args.reason, store, now, args.superseded_by)
        case "note" if args.progress is not None:
            return note_progress(
                args.id, args.progress, store, now, args.about, args.governs, args.mark
            )
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
            mark = make_mark(args.mark)
            supersedes = supersedes_asked(args.supersedes, store)
            return note_named(args.id, kind, text, store, now, about, governs, mark, supersedes)
        case "verify" if args.no is not None:
            return verify_item_no(args.id, args.no, store, now)
        case "verify":
            return verify_item(args.id, args.yes, store, now)
        case "reorder":
            return reorder_item(args.id, args.before, store)
        case _:
            return None


def command_said(
    args: argparse.Namespace,
    store: Store,
    now: Now,
    record: Path,
    open_git: OpenGit,
    width: Width,
    config: Config,
    run_gate: RunGate,
    cwd: Path,
    run_check: RunGate,
) -> Said | None:
    """Run the command the arguments name on the record; None when they name none.

    The directory fgraph runs in, cwd, is where the path of fgraph about a file is taken from.

    The checks of the command run first, in check_command, before its write is made. A start
    given no id takes the first line of the Backlog that can start, read before those checks.

    A write is committed once it is made. The lines of status are cut to the width, when there
    is one. The configuration says whether a start branches, how many work items are started at
    once, whether a landing is taken and the gate it runs through run_gate; the complete of a
    Task runs its check through run_check. A set of the
    configuration is committed by the configuration it leaves, so one that turns the commits
    off is left uncommitted. A release tags main, and pushes the tag when the configuration
    says so. Raises the refusal of the command, a git step refused among them.
    """
    args = start_named(args, partial(top_to_start, store, start_limit(config.development)))
    check_command(args, store, record, open_git, config, cwd, run_check)
    written = _written(args, store, now, config, cwd, open_git)
    if written is not None:
        said = commit_written(written, store, record, open_git, config)
        return branch_removed(written, said, record, open_git, config)
    match args.command:
        case "config" if args.action == "set":
            done = set_setting(args.key, args.value, store.load_settings, store.save_settings)
            return commit_written(done.written, store, record, open_git, done.config)
        case "config" if args.action == "unset":
            done = unset_setting(args.key, store.load_settings, store.save_settings)
            return commit_written(done.written, store, record, open_git, done.config)
        case "config":
            return Said(show_config(config))
        case "commit":
            return commit_task(args.id, args.message, store, record, open_git)
        case "land":
            decision = decision_given(args)
            return land_item(
                args.id, args.message, store, now, record, open_git, config, run_gate, decision
            )
        case "release":
            return release_trunk(args.version, store, record, open_git, config)
        case "sync":
            return sync_branch(record, open_git, config)
        case "status":
            limit = start_limit(config.development)
            tops = tops_asked(tops_of(config.status), every=args.all, backlog=args.backlog)
            return Said(status_output(store, tops, args.format, width(), limit))
        case _:
            return view_said(args, store, cwd, open_git, record, config)

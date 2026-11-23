"""The command the arguments of the command line name, run on the record: a write or a view.

A write is committed once it is made; a view says its text. Each raises the refusal of the
command, which the command line writes as a usage error.
"""

import argparse
from pathlib import Path

from flowgraph.about import about_item
from flowgraph.development import RunGate, check_slug_branched
from flowgraph.development.commit import OpenGit, Said, commit_written
from flowgraph.development.land import land_item
from flowgraph.development.parallel import check_parallel
from flowgraph.development.release import release_trunk
from flowgraph.development.scope import check_complete_on_main, check_start_on_main
from flowgraph.development.task_check import check_task_checked
from flowgraph.development.task_run import check_task_run
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
    write_task,
)
from flowgraph.item.moves import start_item
from flowgraph.item.verify import verify_item, verify_item_no
from flowgraph.knowledge import DECISION, DEVIATION, FINDING
from flowgraph.knowledge.governed import governs_asked
from flowgraph.knowledge.list import show_knowledge
from flowgraph.parent import parent_asked
from flowgraph.parser.item_commands import TOP
from flowgraph.parser.stated import criterion_added, decision_given
from flowgraph.record import CONFIG, Config, Now
from flowgraph.record.setting import set_setting, show_config, unset_setting
from flowgraph.record.store import Store
from flowgraph.relation.depends import (
    amends_asked,
    check_start_waits,
    depends_asked,
    filed_during_asked,
)
from flowgraph.status import status_output
from flowgraph.status.next import start_limit
from flowgraph.status.terminal import Width
from flowgraph.term.about import about_asked
from flowgraph.term.item import add_term_item, relate_term_item, terms_text
from flowgraph.work_item import (
    Amendment,
)


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
            decision = decision_given(args)
            return complete_and_start_next(args.id, args.commit, store, now, config, decision)
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

    A write is committed once it is made. The lines of status are cut to the width, when there
    is one. The configuration says whether a start branches, how many work items are started at
    once, whether a landing is taken and the gate it runs through run_gate; the complete of a
    Task runs its check through run_check. A set of the
    configuration is committed by the configuration it leaves, so one that turns the commits
    off is left uncommitted. A release tags main, and pushes the tag when the configuration
    says so. Raises the refusal of the command, a git step refused among them.
    """
    if args.command == "complete":
        check_complete_on_main(args.id, record, open_git)
        check_task_run(args.id, store, record, open_git, cwd, run_check)
    if args.command == "start":
        check_slug_branched(args.id, args.slug, config.development.enabled, record / CONFIG)
        check_start_on_main(args.id, record, open_git)
        check_start_under_feature(args.id, store)
        check_start_waits(args.id, store)
        check_parallel(args.id, store.find_work_item_rows, config)
    if args.command == "add" and args.kind == "task":
        check_task_checked(args.check, config.development.enabled, record / CONFIG)
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
            decision = decision_given(args)
            return land_item(
                args.id, args.message, store, now, record, open_git, config, run_gate, decision
            )
        case "release":
            return release_trunk(args.version, store, record, open_git, config)
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
            limit = start_limit(config.development)
            return Said(
                status_output(store, None if args.all else TOP, args.format, width(), limit)
            )
        case _:
            return None

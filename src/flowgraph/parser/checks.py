"""The checks a command passes before it writes: each raises the refusal of the command.

A check reads the record and the repository and changes nothing; the write that follows it
is made by the command only when every check of the command passed.
"""

import argparse
from pathlib import Path

from flowgraph.development import RunGate, check_slug_branched
from flowgraph.development.commit import OpenGit
from flowgraph.development.driver import check_complexity
from flowgraph.development.parallel import check_parallel
from flowgraph.development.scope import check_complete_on_main, check_start_on_main
from flowgraph.development.start_branch import check_branch_free
from flowgraph.development.task_check import check_task_checked
from flowgraph.development.task_run import check_task_run
from flowgraph.feature.start import check_start_under_feature
from flowgraph.record import CONFIG, Config
from flowgraph.record.store import Store
from flowgraph.relation.depends import check_start_waits
from flowgraph.work_item.agent import check_agent_taken


def check_command(
    args: argparse.Namespace,
    store: Store,
    record: Path,
    open_git: OpenGit,
    config: Config,
    cwd: Path,
    run_check: RunGate,
) -> None:
    """Raise the refusal of the command when one of the checks before its write fails.

    A start checks, last, that the branch it would make is not there already.
    """
    if args.command == "complete":
        check_complete_on_main(args.id, record, open_git)
        check_task_run(args.id, store, record, open_git, cwd, run_check)
    if args.command == "start":
        check_slug_branched(args.id, args.slug, config.development.enabled, record / CONFIG)
        check_agent_taken(args.id, args.agent, config.development.enabled, record / CONFIG)
        check_start_on_main(args.id, record, open_git)
        check_start_under_feature(args.id, store)
        check_start_waits(args.id, store)
        check_parallel(args.id, store.find_work_item_rows, config)
        check_complexity(args.id, store.load_work_item, config)
        check_branch_free(args.id, args.slug, store, record, open_git, config)
    if args.command == "add" and args.kind == "task":
        check_task_checked(args.check, config.development.enabled, record / CONFIG)
    if args.command == "hand":
        check_agent_taken(args.id, args.agent, config.development.enabled, record / CONFIG)

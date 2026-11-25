"""The views a command line asks for: knowledge, terms, graph, about and show, each its text."""

import argparse
from pathlib import Path

from flowgraph.about import about_item
from flowgraph.brief.read import brief_output
from flowgraph.development.commit import OpenGit, Said
from flowgraph.feature.item import show_any_item
from flowgraph.goal.read import goal_output
from flowgraph.graph import graph_text
from flowgraph.knowledge.document import knowledge_output
from flowgraph.record import Config
from flowgraph.record.archive import check_archived
from flowgraph.record.store import Store
from flowgraph.term.item import terms_text


def view_said(
    args: argparse.Namespace,
    store: Store,
    cwd: Path,
    open_git: OpenGit,
    record: Path,
    config: Config,
) -> Said | None:
    """Say the text of the view the arguments name; None when they name none.

    The directory fgraph runs in, cwd, is where the path of fgraph about a file is taken from;
    the record is where git is asked for the branch and the worktree of a brief, and the
    configuration says who drives the goal and how many work items it runs at once, and where the
    archive of board 1 is, which show names for an id of board 1. Raises the refusal of the view;
    nothing is written.
    """
    match args.command:
        case "knowledge":
            return Said(
                knowledge_output(args.format, args.kind, args.about, store, args.search, args.live)
            )
        case "terms":
            return Said(terms_text(store))
        case "graph":
            return Said(graph_text(args.format, store))
        case "about":
            return Said(about_item(args.id, store, cwd, open_git))
        case "brief":
            return Said(
                brief_output(
                    args.id, args.format, store, record, open_git, not_named=args.not_named
                )
            )
        case "goal":
            return Said(goal_output(args.id, args.hours, store, config.development))
        case "show":
            check_archived(args.id, config.archive, record)
            return Said(show_any_item(args.id, store))
        case _:
            return None

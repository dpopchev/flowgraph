"""The views a command line asks for: knowledge, terms, graph, about and show, each its text."""

import argparse
from pathlib import Path

from flowgraph.about import about_item
from flowgraph.brief.read import brief_output
from flowgraph.development.commit import OpenGit, Said
from flowgraph.feature.item import show_any_item
from flowgraph.goal.read import goal_output
from flowgraph.graph import graph_text
from flowgraph.knowledge.list import show_knowledge
from flowgraph.record.layers import Development
from flowgraph.record.store import Store
from flowgraph.term.item import terms_text


def view_said(
    args: argparse.Namespace,
    store: Store,
    cwd: Path,
    open_git: OpenGit,
    record: Path,
    development: Development,
) -> Said | None:
    """Say the text of the view the arguments name; None when they name none.

    The directory fgraph runs in, cwd, is where the path of fgraph about a file is taken from;
    the record is where git is asked for the branch and the worktree of a brief, and the development
    says who drives the goal and how many work items it runs at once. Raises the
    refusal of the view; nothing is written.
    """
    match args.command:
        case "knowledge":
            return Said(show_knowledge(args.kind, args.about, store))
        case "terms":
            return Said(terms_text(store))
        case "graph":
            return Said(graph_text(args.format, store))
        case "about":
            return Said(about_item(args.id, store, cwd, open_git))
        case "brief":
            return Said(brief_output(args.id, args.format, store, record, open_git))
        case "goal":
            return Said(goal_output(args.id, args.hours, store, development))
        case "show":
            return Said(show_any_item(args.id, store))
        case _:
            return None

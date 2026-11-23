"""The text of the brief of a work item: the text of fgraph show, then its sections."""

from flowgraph.brief.model import Brief, FeatureBrief, TermLine
from flowgraph.knowledge.governed import governed_text
from flowgraph.knowledge.model import about_text, governs_text
from flowgraph.status.show import show_text


def _worktree(branch: str | None, worktree: str | None) -> str:
    """The branch and the worktree under their heading; empty for a work item with no branch."""
    if branch is None:
        return ""
    path = "" if worktree is None else f"  path         {worktree}\n"
    return f"Worktree\n  branch       {branch}\n{path}"


def _feature(feature: FeatureBrief | None) -> str:
    """The Feature under its heading: its line, its description and its knowledge lines."""
    if feature is None:
        return ""
    described = f"  description  {feature.description}\n" if feature.description else ""
    heading = f"  Knowledge ({len(feature.knowledge)})\n" if feature.knowledge else ""
    lines = "".join(
        f"    {line.kind}  {line.noted.date().isoformat()}  {line.text}"
        f"{about_text(line.about)}{governs_text(line.governs)}\n"
        for line in feature.knowledge
    )
    return (
        f"Feature\n  {feature.id}  {feature.bucket}  {feature.title}\n{described}{heading}{lines}"
    )


def _terms(terms: tuple[TermLine, ...]) -> str:
    """The terms under their heading, each with its meaning; empty for none."""
    if not terms:
        return ""
    return f"Terms ({len(terms)})\n" + "".join(f"  {term.name}  {term.meaning}\n" for term in terms)


def brief_text(brief: Brief) -> str:
    """The text of fgraph show of the work item, then its worktree, Feature, governing lines, terms.

    A section with nothing in it is left out, so a brief with nothing beside its work item is
    exactly the text of fgraph show.
    """
    worktree = None if brief.worktree is None else str(brief.worktree)
    return "".join(
        [
            show_text(brief.detail),
            _worktree(brief.branch, worktree),
            _feature(brief.feature),
            governed_text(brief.governed_by),
            _terms(brief.terms),
        ]
    )

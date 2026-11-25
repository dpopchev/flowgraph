"""The text of the links fgraph about lists: pure, words what `about/links.py` holds (S-0156)."""

from flowgraph.about.links import FileLinks, ItemLinks, TermLinks, Touching
from flowgraph.knowledge import about_text, governs_text
from flowgraph.knowledge.governed import governed_text


def item_text(links: ItemLinks) -> str:
    """The id and the title, then each heading that holds a line, with its count."""
    sections = [
        *(
            (heading, [f"{each.id}  {each.bucket}  {each.title}" for each in held])
            for heading, held in links.links.items()
        ),
        ("terms", [f"{term.name}  {term.meaning}" for term in links.terms]),
        (
            "knowledge",
            [
                f"{row.kind}  {row.noted.date().isoformat()}  {row.text}"
                f"{about_text(row.about)}{governs_text(row.governs)}"
                for row in links.knowledge
            ],
        ),
    ]
    return f"{links.id}  {links.title}\n" + "".join(
        f"  {heading} ({len(lines)})\n" + "".join(f"    {line}\n" for line in lines)
        for heading, lines in sections
        if lines
    )


def term_about_text(links: TermLinks) -> str:
    """The items line and the knowledge lines of a term, each left out for none."""
    items = [f"{each.id}{_via(each.via)}" for each in links.items]
    knowledge = [
        f"    {line.entry.item}  {line.entry.kind}  {line.entry.noted.date().isoformat()}"
        f"  {line.entry.text}{_via(line.via)}\n"
        for line in links.knowledge
    ]
    return (
        (f"  items  {', '.join(items)}\n" if items else "")
        + ("  knowledge\n" if knowledge else "")
        + "".join(knowledge)
    )


def file_text(links: FileLinks) -> str:
    """The lines that govern the file, then the items that touched it, or one line for none."""
    lines = governed_text(links.governed_by) + "".join(_touching(each) for each in links.touched_by)
    return lines or f"no commit of the record touched {links.path}\n"


def _via(via: str) -> str:
    """The mark of a term a line was reached through; empty for the term itself."""
    return f"  (via {via})" if via else ""


def _touching(touching: Touching) -> str:
    """The line of an item that touched a file, then each of its Tasks that did."""
    head = f"{touching.id}  {touching.commit or '-'}  {touching.title}\n"
    return head + "".join(f"  {task.id}  {task.commit}  {task.title}\n" for task in touching.tasks)

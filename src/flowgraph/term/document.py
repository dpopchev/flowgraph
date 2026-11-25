"""The JSON document of fgraph show of a term.

A second formatter of TermShown beside term_text (S-0154); null for nothing, an empty list for an
empty list, the keys sorted, an indent of two and a newline.
"""

import json

from flowgraph.term.item import TermShown


def term_json(shown: TermShown) -> str:
    """The term as a JSON document: its meaning, its relations, its items and its knowledge."""
    document = {
        "added": shown.added.isoformat(),
        "is_a": list(shown.is_a),
        "items": list(shown.items),
        "kind": "term",
        "kinds": list(shown.kinds),
        "knowledge": [
            {
                "about": list(line.about),
                "governs": list(line.governs),
                "item": line.item,
                "kind": line.kind,
                "mark": line.mark or None,
                "noted": line.noted.isoformat(),
                "ref": line.ref or None,
                "supersedes": list(line.supersedes),
                "text": line.text,
            }
            for line in shown.knowledge
        ],
        "meaning": shown.meaning,
        "name": shown.name,
        "part_of": list(shown.part_of),
        "parts": list(shown.parts),
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"

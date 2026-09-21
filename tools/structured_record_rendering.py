from __future__ import annotations

"""Deterministic record-per-line rendering of structured documents for reviewer packages.

Why this exists
---------------
A reviewer grounds an observation by copying one exact, contiguous span out of the passage it was shown. Pretty-printed
JSON defeats that. In the G-EVID1 scorer document, ``json.dumps(report, indent=1)`` put every field on its own line:
part 14 was 6,498 characters over 311 lines, a mean of 19.9 characters per line, and only 15 of those 311 lines carried
an ``item_id``. A record's identity and its fields were therefore never on the same line, so a legal single-line quote
could establish *either* which item was being described *or* what was said about it, never both.

Both failed G-EVID1 reviews died there, and the second one proves the mechanism exactly. The first attempt joined lines
with ellipses and was refused as stitched. The bounded retry then did what it was asked - every one of its eight quotes
was contiguous and located byte-for-byte - and all eight were still refused, because none of those legal spans
contained the item id the statement named.

The model was not the problem by then. The rendering was.

What this does
--------------
Each logical record becomes one line, with its path first and its full content next, so a single contiguous quote can
carry identity and properties together::

    ["transitions",12] {"item_id":"I20","repeat":3,"provisional":{"relation":"partial",...},...}

Properties this guarantees, all of which are tested:

* **Lossless and reversible.** ``reconstruct(render(doc)) == doc``, including key order and empty containers.
* **Nothing added.** Every character of every line comes from the document or from the path that locates it.
* **Deterministic.** The same document renders to the same bytes; no sorting, no timestamps, no randomness.
* **Record boundaries preserved.** One line is exactly one record; a record is never split across lines.
* **Traceable.** The leading path locates the record in the canonical artifact.

Nothing here knows what any field means. It never inspects a value to decide how to render it, so it cannot select or
reshape evidence, and it is not specific to any experiment, document or item.
"""

import json
from typing import Any

RENDERING_ID = "record-per-line.v2"
RENDERING_DESCRIPTION = (
    "One logical record per line, written as a JSON path followed by the record itself. Every field appears as "
    "\"key\": value on the line that carries it, so a field can be quoted the way it is written. Lossless, "
    "reversible and deterministic; the reviewer grounds quotes against these lines."
)

# A node is emitted whole while its compact form fits this budget; larger nodes are walked into so that lines stay
# quotable. It bounds line length only. It never drops or summarises anything.
MAX_RECORD_CHARS = 1200

# Conventional JSON spacing, not the most compact form. A reviewer copies a span as it is written, and models write
# {"key": value, "next": value}. Rendering without the spaces made every honestly-copied field a byte mismatch.
_SEPARATORS = (", ", ": ")
_DECODER = json.JSONDecoder()


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=_SEPARATORS)


def _path(path: list[Any]) -> str:
    """The locator prefix. Kept compact so it never competes with the record for quotable width."""
    return json.dumps(path, ensure_ascii=False, separators=(",", ":"))


def _emit(path: list[Any], value: Any, lines: list[str], *, atomic: bool = False) -> None:
    """Emit ``value`` as one line, or walk into it when it is a container too large to stay quotable.

    ``atomic`` marks an element of an array. An array element is a record, and a record is never split: splitting one
    would put its identity on a different line from its fields, which is precisely the failure this rendering exists
    to remove. A long record is emitted whole and stays quotable from its start, where its identity is.

    A dict too large to emit whole is split into object *fragments*, never into bare values under a longer path. A
    field's name must appear on the line that carries its value, written the way JSON writes it, or that field cannot
    be quoted at all: a line reading ``["execution_manifest","one_run_only"] true`` contains no ``"one_run_only":
    true`` for a reviewer to copy, and every honest attempt to cite it fails to locate. That defect emptied two
    required parts of the first G-CORROB1 review.
    """
    body = _compact(value)
    if atomic or len(body) <= MAX_RECORD_CHARS or not isinstance(value, (dict, list)) or not value:
        lines.append(f"{_path(path)} {body}")
        return
    if isinstance(value, dict):
        fragment: dict[str, Any] = {}
        for key, item in value.items():
            single = _compact({key: item})
            if len(single) > MAX_RECORD_CHARS and isinstance(item, (dict, list)) and item:
                if fragment:
                    lines.append(f"{_path(path)} {_compact(fragment)}")
                    fragment = {}
                _emit(path + [key], item, lines)
                continue
            if fragment and len(_compact({**fragment, key: item})) > MAX_RECORD_CHARS:
                lines.append(f"{_path(path)} {_compact(fragment)}")
                fragment = {}
            fragment[key] = item
        if fragment:
            lines.append(f"{_path(path)} {_compact(fragment)}")
        return
    for index, item in enumerate(value):
        _emit(path + [index], item, lines, atomic=True)


def render(document: Any) -> str:
    """Render a structured document as record-per-line text. Deterministic and lossless."""
    lines: list[str] = []
    _emit([], document, lines)
    return "\n".join(lines) + "\n"


def _merge(existing: Any, value: Any) -> Any:
    """Combine a node with the next fragment written for the same path, keeping first-seen key order."""
    if isinstance(existing, dict) and isinstance(value, dict):
        existing.update(value)
        return existing
    return value


def _place(root: Any, path: list[Any], value: Any) -> Any:
    """Put ``value`` at ``path``, creating the containers the path implies, preserving encounter order."""
    if not path:
        return _merge(root, value)
    key = path[0]
    if isinstance(key, int):
        if not isinstance(root, list):
            root = []
        while len(root) <= key:
            root.append(None)
        root[key] = _place(root[key], path[1:], value)
        return root
    if not isinstance(root, dict):
        root = {}
    root[key] = _place(root.get(key), path[1:], value)
    return root


def reconstruct(text: str) -> Any:
    """Rebuild the document a rendering came from. The inverse of :func:`render`.

    A dict split into fragments arrives as several lines sharing one path; they merge in the order written, which is
    the order the source had.
    """
    root: Any = None
    seen_root = False
    for line in text.split("\n"):
        if not line.strip():
            continue
        path, offset = _DECODER.raw_decode(line)
        value = json.loads(line[offset:].strip())
        if not path:
            root = _merge(root, value) if seen_root else value
            seen_root = True
            continue
        root = _place(root, list(path), value)
    return root


def round_trips(document: Any) -> bool:
    """Whether this document survives rendering unchanged. Used by the package builder as a precondition."""
    try:
        return reconstruct(render(document)) == document
    except Exception:
        return False


def header(title: str, source: str, digest: str) -> str:
    """The provenance preamble that accompanies a rendered document inside a review package."""
    return (f"{title}\n"
            f"Rendering: {RENDERING_ID}. {RENDERING_DESCRIPTION}\n"
            f"Each line is one record: a JSON path locating it in the source, then the record itself as compact JSON. "
            f"Quote one contiguous span of a line; a span that starts at the beginning of a line carries that "
            f"record's identity with it.\n"
            f"Source: {source}\n"
            f"Source sha256: {digest}\n\n")

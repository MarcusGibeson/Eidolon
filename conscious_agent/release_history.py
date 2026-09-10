from __future__ import annotations

"""Structured, content-free parsing for ``README_RELEASE_HISTORY.md``.

Release versions are identifiers composed of integer components.  They are
never parsed as floats or compared lexically.  The parser accepts supported
Markdown heading levels while ignoring prose references to historical versions.
"""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable

_HEADING = re.compile(r"^(?P<marks>#{1,6})[ \t]+(?P<body>.+?)[ \t]*$")
_RELEASE_BODY = re.compile(
    r"^(?:(?:Eidolon|Desktop Alpha)[ \t]+)?"
    r"v(?P<start>\d+(?:\.\d+)*)"
    r"(?:[ \t]*-[ \t]*v?(?P<end>\d+(?:\.\d+)*))?"
    r"(?P<tail>.*)$",
    re.IGNORECASE,
)
_VERSION_TOKEN = re.compile(r"(?<![A-Za-z0-9_])v(?P<version>\d+(?:\.\d+)*)(?![A-Za-z0-9_.])", re.IGNORECASE)
_LOOKS_RELEASE_LIKE = re.compile(r"^(?:(?:Eidolon|Desktop Alpha)[ \t]+)?v(?=\d)", re.IGNORECASE)


def parse_version_tuple(value: str) -> tuple[int, ...]:
    text = str(value or "").strip().lower()
    if text.startswith("v"):
        text = text[1:]
    if not text or not re.fullmatch(r"\d+(?:\.\d+)*", text):
        raise ValueError("Release version must contain dot-separated integer components.")
    return tuple(int(part) for part in text.split("."))


def format_version_tuple(value: Iterable[int]) -> str:
    return ".".join(str(int(part)) for part in value)


def compare_version_tuples(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    width = max(len(left), len(right))
    lhs = left + (0,) * (width - len(left))
    rhs = right + (0,) * (width - len(right))
    return (lhs > rhs) - (lhs < rhs)


@dataclass(frozen=True)
class ReleaseHistoryEntry:
    index: int
    heading_line: int
    heading_level: int
    version: str
    version_tuple: tuple[int, ...]
    range_end: str
    range_end_tuple: tuple[int, ...] | None
    title: str
    section_text: str
    section_sha256: str

    @property
    def identity(self) -> str:
        return self.version if not self.range_end else f"{self.version}-{self.range_end}"

    @property
    def ordering_tuple(self) -> tuple[int, ...]:
        return self.range_end_tuple or self.version_tuple

    def public_row(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "version": self.version,
            "range_end": self.range_end,
            "heading_level": self.heading_level,
            "heading_line": self.heading_line,
            "title": self.title,
            "section_sha256": self.section_sha256,
        }


def _title_from_tail(tail: str) -> str:
    value = str(tail or "").strip()
    value = re.sub(r"^(?:[-:–—])[ \t]*", "", value).strip()
    return value


def _section_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_release_history_text(text: str) -> dict[str, Any]:
    lines = text.splitlines(keepends=True)
    candidates: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    heading_levels: dict[str, int] = {}

    for offset, raw_line in enumerate(lines):
        line = raw_line.rstrip("\r\n")
        heading = _HEADING.match(line)
        if not heading:
            continue
        body = heading.group("body").strip()
        parsed = _RELEASE_BODY.match(body)
        if parsed is None:
            if _LOOKS_RELEASE_LIKE.match(body):
                malformed.append({"line": offset + 1, "heading_level": len(heading.group("marks")), "status": "malformed_release_heading"})
            continue
        start_text = parsed.group("start")
        end_text = parsed.group("end") or ""
        tail = parsed.group("tail") or ""
        if tail.lstrip().startswith("."):
            malformed.append({"line": offset + 1, "heading_level": len(heading.group("marks")), "status": "unparseable_version"})
            continue
        tokens = [match.group("version") for match in _VERSION_TOKEN.finditer(body)]
        expected_token_count = 2 if end_text else 1
        if len(tokens) != expected_token_count:
            ambiguous.append({
                "line": offset + 1,
                "heading_level": len(heading.group("marks")),
                "status": "ambiguous_version_tokens",
                "token_count": len(tokens),
            })
            continue
        try:
            start_tuple = parse_version_tuple(start_text)
            end_tuple = parse_version_tuple(end_text) if end_text else None
        except ValueError:
            malformed.append({"line": offset + 1, "heading_level": len(heading.group("marks")), "status": "unparseable_version"})
            continue
        if end_tuple is not None and compare_version_tuples(end_tuple, start_tuple) < 0:
            ambiguous.append({
                "line": offset + 1,
                "heading_level": len(heading.group("marks")),
                "status": "descending_version_range",
                "token_count": 2,
            })
            continue
        level = len(heading.group("marks"))
        heading_levels[str(level)] = heading_levels.get(str(level), 0) + 1
        candidates.append({
            "line_index": offset,
            "line": offset + 1,
            "level": level,
            "start": format_version_tuple(start_tuple),
            "start_tuple": start_tuple,
            "end": format_version_tuple(end_tuple) if end_tuple else "",
            "end_tuple": end_tuple,
            "title": _title_from_tail(tail),
        })

    entries: list[ReleaseHistoryEntry] = []
    for index, candidate in enumerate(candidates):
        start_line = int(candidate["line_index"])
        end_line = int(candidates[index + 1]["line_index"]) if index + 1 < len(candidates) else len(lines)
        section = "".join(lines[start_line:end_line])
        entries.append(ReleaseHistoryEntry(
            index=index,
            heading_line=int(candidate["line"]),
            heading_level=int(candidate["level"]),
            version=str(candidate["start"]),
            version_tuple=tuple(candidate["start_tuple"]),
            range_end=str(candidate["end"]),
            range_end_tuple=tuple(candidate["end_tuple"]) if candidate["end_tuple"] else None,
            title=str(candidate["title"]),
            section_text=section,
            section_sha256=_section_digest(section),
        ))

    duplicate_groups: list[dict[str, Any]] = []
    by_identity: dict[str, list[ReleaseHistoryEntry]] = {}
    for entry in entries:
        by_identity.setdefault(entry.identity, []).append(entry)
    for identity, group in by_identity.items():
        if len(group) < 2:
            continue
        exact = len({entry.section_text.strip() for entry in group}) == 1
        title_conflict = len({entry.title.strip() for entry in group}) > 1
        duplicate_groups.append({
            "identity": identity,
            "count": len(group),
            "exact_duplicate": exact,
            "conflicting_claims": not exact or title_conflict,
            "heading_lines": [entry.heading_line for entry in group],
            "section_sha256": [entry.section_sha256 for entry in group],
        })

    ordering_violations: list[dict[str, Any]] = []
    previous: ReleaseHistoryEntry | None = None
    for entry in entries:
        if previous is not None and compare_version_tuples(previous.ordering_tuple, entry.ordering_tuple) < 0:
            ordering_violations.append({
                "newer_identity": entry.identity,
                "newer_line": entry.heading_line,
                "preceded_by_identity": previous.identity,
                "preceded_by_line": previous.heading_line,
            })
        previous = entry

    return {
        "ok": not malformed and not ambiguous,
        "status": "pass" if not malformed and not ambiguous else "parse_attention_required",
        "entry_count": len(entries),
        "heading_levels": heading_levels,
        "entries": entries,
        "public_entries": [entry.public_row() for entry in entries],
        "malformed_headings": malformed,
        "ambiguous_headings": ambiguous,
        "duplicate_groups": duplicate_groups,
        "duplicate_version_count": len(duplicate_groups),
        "conflicting_duplicate_count": sum(bool(group["conflicting_claims"]) for group in duplicate_groups),
        "ordering_violations": ordering_violations,
        "ordering_violation_count": len(ordering_violations),
        "content_free": True,
    }


def parse_release_history_file(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    try:
        raw = target.read_bytes()
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        return {
            "ok": False,
            "status": "history_unreadable_preserved",
            "entry_count": 0,
            "heading_levels": {},
            "public_entries": [],
            "entries": [],
            "malformed_headings": [],
            "ambiguous_headings": [],
            "duplicate_groups": [],
            "duplicate_version_count": 0,
            "conflicting_duplicate_count": 0,
            "ordering_violations": [],
            "ordering_violation_count": 0,
            "history_sha256": "",
            "error_type": type(error).__name__,
            "content_free": True,
        }
    result = parse_release_history_text(text)
    result["history_sha256"] = hashlib.sha256(raw).hexdigest()
    result["utf8_bom_present"] = raw.startswith(b"\xef\xbb\xbf")
    return result


def release_history_status(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1]).resolve()
    parsed = parse_release_history_file(root / "README_RELEASE_HISTORY.md")
    attention = (
        not parsed.get("ok")
        or int(parsed.get("duplicate_version_count") or 0) > 0
        or int(parsed.get("ordering_violation_count") or 0) > 0
    )
    return {
        "ok": not attention,
        "status": "pass" if not attention else "attention_required",
        "entry_count": int(parsed.get("entry_count") or 0),
        "heading_levels": dict(parsed.get("heading_levels") or {}),
        "malformed_heading_count": len(parsed.get("malformed_headings") or []),
        "ambiguous_heading_count": len(parsed.get("ambiguous_headings") or []),
        "duplicate_version_count": int(parsed.get("duplicate_version_count") or 0),
        "conflicting_duplicate_count": int(parsed.get("conflicting_duplicate_count") or 0),
        "ordering_violation_count": int(parsed.get("ordering_violation_count") or 0),
        "history_sha256": str(parsed.get("history_sha256") or ""),
        "preview_only": True,
        "provider_contacted": False,
        "installation_changed": False,
        "promotion_changed": False,
        "certification_performed": False,
        "content_free": True,
    }

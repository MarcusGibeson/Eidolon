from __future__ import annotations

import json
import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

RESULTS: list[dict[str, object]] = []


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def check(name: str, fn) -> None:
    try:
        fn(); RESULTS.append({"name": name, "ok": True})
    except Exception as exc:
        RESULTS.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})


def main() -> int:
    from release_history import compare_version_tuples, parse_release_history_file, parse_release_history_text, parse_version_tuple, release_history_status

    def current_history_is_structured_and_ordered() -> None:
        status = release_history_status(ROOT)
        require(status.get("ok"), status)
        require(int(status.get("entry_count") or 0) >= 100, status)
        require(status.get("duplicate_version_count") == 0, status)
        require(status.get("ordering_violation_count") == 0, status)
        require(set((status.get("heading_levels") or {}).keys()) >= {"1", "2"}, status)

    def mixed_heading_levels_are_supported() -> None:
        parsed = parse_release_history_text("## v12.3 - New\ntext\n# Eidolon v12.2 Older\ntext\n### Desktop Alpha v12.1 Old\n")
        require(parsed.get("ok") and parsed.get("entry_count") == 3, parsed)
        require(parsed.get("heading_levels") == {"2": 1, "1": 1, "3": 1}, parsed)

    def prose_version_references_are_not_entries() -> None:
        parsed = parse_release_history_text("# v7.2 Actual\nMentions v99.4 in prose.\n## Verification status\nRetained v7.1.\n")
        require(parsed.get("entry_count") == 1, parsed)
        require(parsed["public_entries"][0]["version"] == "7.2", parsed)

    def versions_are_integer_tuples_not_floats() -> None:
        require(compare_version_tuples(parse_version_tuple("1095.2"), parse_version_tuple("1093.9")) > 0, "decimal-style comparison leaked")
        require(compare_version_tuples(parse_version_tuple("1.10"), parse_version_tuple("1.9")) > 0, "lexical/float comparison leaked")
        require(compare_version_tuples(parse_version_tuple("1.2"), parse_version_tuple("1.2.0")) == 0, "trailing zero mismatch")

    def release_ranges_are_structured_not_ambiguous() -> None:
        parsed = parse_release_history_text("## v1087.3-v1087.5 Bundle B\nBody\n# v1087.2 Earlier\n")
        require(parsed.get("ok") and parsed.get("entry_count") == 2, parsed)
        first = parsed["public_entries"][0]
        require(first.get("identity") == "1087.3-1087.5" and first.get("range_end") == "1087.5", first)
        require(not parsed.get("ambiguous_headings"), parsed)

    def malformed_and_ambiguous_headings_are_preserved() -> None:
        text = "# v1.x Broken\nbody\n# v1.2 and v1.3 Two releases\nbody\n# v1.1 Good\n"
        parsed = parse_release_history_text(text)
        require(not parsed.get("ok"), parsed)
        require(len(parsed.get("malformed_headings") or []) == 1, parsed)
        require(len(parsed.get("ambiguous_headings") or []) == 1, parsed)
        require(parsed.get("entry_count") == 1, parsed)

    def file_parse_is_read_only() -> None:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1095-3-") as td:
            path = Path(td) / "README_RELEASE_HISTORY.md"
            path.write_bytes(b"\xef\xbb\xbf## v2.0 New\nBody\n# v1.0 Old\n")
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            parsed = parse_release_history_file(path)
            require(parsed.get("ok") and parsed.get("utf8_bom_present"), parsed)
            require(hashlib.sha256(path.read_bytes()).hexdigest() == before, "parser rewrote history")

    def public_status_is_content_free_and_provider_independent() -> None:
        status = release_history_status(ROOT)
        encoded = repr(status).lower()
        require(status.get("content_free") and status.get("provider_contacted") is False, status)
        for forbidden in ("section_text", "absolute_path", "provider_payload", "conversation", "memory_text"):
            require(forbidden not in encoded, forbidden)

    checks = [
        ("current-history-structured-ordered", current_history_is_structured_and_ordered),
        ("mixed-heading-levels-supported", mixed_heading_levels_are_supported),
        ("prose-version-references-ignored", prose_version_references_are_not_entries),
        ("integer-tuple-version-ordering", versions_are_integer_tuples_not_floats),
        ("release-ranges-structured", release_ranges_are_structured_not_ambiguous),
        ("malformed-ambiguous-preserved", malformed_and_ambiguous_headings_are_preserved),
        ("file-parse-read-only", file_parse_is_read_only),
        ("public-status-content-free", public_status_is_content_free_and_provider_independent),
    ]
    for name, fn in checks:
        check(name, fn)
    passed = sum(bool(row.get("ok")) for row in RESULTS)
    print(json.dumps({"suite": "v1095.3-authoritative-release-history-structure", "passed": passed, "failed": len(RESULTS)-passed, "total": len(RESULTS), "checks": RESULTS}, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())

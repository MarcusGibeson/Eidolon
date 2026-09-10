from __future__ import annotations

import json
import hashlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

RESULTS: list[dict[str, object]] = []


def require(value: object, message: object) -> None:
    if not value: raise AssertionError(message)


def check(name: str, fn) -> None:
    try: fn(); RESULTS.append({"name": name, "ok": True})
    except Exception as exc: RESULTS.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})


def fixture(base: Path, text: str) -> Path:
    root = base / "source"; root.mkdir(parents=True, exist_ok=True)
    (root / "README_RELEASE_HISTORY.md").write_text(text, encoding="utf-8")
    return root


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    from release_history import parse_release_history_file
    from release_history_reconciliation import apply_release_history_reconciliation, preview_release_history_reconciliation

    with tempfile.TemporaryDirectory(prefix="eidolon-v1095-4-") as td:
        base = Path(td); runtime = base / "runtime"

        def current_history_needs_no_rewrite() -> None:
            preview = preview_release_history_reconciliation(ROOT)
            require(preview.get("ok") and preview.get("status") == "already_aligned", preview)
            require(not preview.get("actions") and not preview.get("changed"), preview)

        def preview_detects_exact_duplicate_and_ordering() -> None:
            root = fixture(base / "one", "# v2.0 New\nA\n# v1.0 Old\nB\n# v2.0 New\nA\n# v1.5 Middle\nC\n")
            path = root / "README_RELEASE_HISTORY.md"; before = sha(path)
            preview = preview_release_history_reconciliation(root)
            require(preview.get("ok") and preview.get("status") == "correction_available", preview)
            kinds = {row.get("action") for row in preview.get("actions") or []}
            require(kinds == {"remove_exact_duplicate_sections", "move_sections_newest_first"}, preview)
            require(sha(path) == before, "preview mutated history")
            require(preview.get("payload_included") is False and preview.get("absolute_path_included") is False, preview)

        def conflicting_duplicates_require_review() -> None:
            root = fixture(base / "two", "# v2.0 First claim\nA\n# v2.0 Conflicting claim\nB\n")
            before = sha(root / "README_RELEASE_HISTORY.md")
            preview = preview_release_history_reconciliation(root)
            require(not preview.get("ok") and preview.get("status") == "operator_review_required", preview)
            require(preview.get("conflicting_duplicate_count") == 1 and not preview.get("correction_available"), preview)
            require(sha(root / "README_RELEASE_HISTORY.md") == before, "conflict was rewritten")

        def malformed_history_is_preserved() -> None:
            root = fixture(base / "three", "# v2.x Broken\nA\n# v1.0 Good\nB\n")
            before = (root / "README_RELEASE_HISTORY.md").read_bytes()
            preview = preview_release_history_reconciliation(root)
            require(not preview.get("ok") and preview.get("malformed_heading_count") == 1, preview)
            require((root / "README_RELEASE_HISTORY.md").read_bytes() == before, "malformed original changed")

        def apply_requires_literal_confirmation() -> None:
            root = fixture(base / "four", "# v1.0 Old\nB\n# v2.0 New\nA\n")
            preview = preview_release_history_reconciliation(root)
            denied = apply_release_history_reconciliation(preview_token=preview["preview_token"], operator_confirmed="true", root_dir=root, runtime_root=runtime)  # type: ignore[arg-type]
            require(denied.get("status") == "literal_confirmation_required", denied)
            require((root / "README_RELEASE_HISTORY.md").read_text().startswith("# v1.0"), "truthy string wrote")

        def confirmed_apply_creates_private_verified_backup() -> None:
            root = fixture(base / "five", "# v1.0 Old\nB\n# v2.0 New\nA\n# v1.0 Old\nB\n")
            preview = preview_release_history_reconciliation(root)
            result = apply_release_history_reconciliation(preview_token=preview["preview_token"], operator_confirmed=True, root_dir=root, runtime_root=runtime)
            require(result.get("ok") and result.get("backup_created") and result.get("backup_verified"), result)
            parsed = parse_release_history_file(root / "README_RELEASE_HISTORY.md")
            require(parsed.get("duplicate_version_count") == 0 and parsed.get("ordering_violation_count") == 0, parsed)
            require(parsed["public_entries"][0]["version"] == "2.0", parsed)
            backup = runtime / "data/release_history_reconciliation/backups" / str(result.get("backup_reference"))
            require(backup.is_file(), result)
            require(not str(backup.resolve()).startswith(str(root.resolve())), "backup inside source")

        def stale_preview_is_rejected() -> None:
            root = fixture(base / "six", "# v1.0 Old\nB\n# v2.0 New\nA\n")
            path = root / "README_RELEASE_HISTORY.md"
            preview = preview_release_history_reconciliation(root)
            path.write_text(path.read_text() + "\noperator note\n", encoding="utf-8")
            result = apply_release_history_reconciliation(preview_token=preview["preview_token"], operator_confirmed=True, root_dir=root, runtime_root=runtime)
            require(result.get("stale_confirmation") and result.get("status") == "stale_or_mismatched_preview", result)
            require("operator note" in path.read_text(), "stale apply replaced original")

        def interruption_restores_original() -> None:
            root = fixture(base / "seven", "# v1.0 Old\nB\n# v2.0 New\nA\n")
            path = root / "README_RELEASE_HISTORY.md"; original = path.read_bytes()
            preview = preview_release_history_reconciliation(root)
            def fault(stage: str) -> None:
                if stage == "after_replace_before_verify": raise RuntimeError("injected interruption")
            result = apply_release_history_reconciliation(preview_token=preview["preview_token"], operator_confirmed=True, root_dir=root, runtime_root=runtime, fault_hook=fault)
            require(not result.get("ok") and result.get("original_restored"), result)
            require(path.read_bytes() == original, "original not restored")

        def source_only_boundary_is_explicit() -> None:
            preview = preview_release_history_reconciliation(ROOT)
            encoded = repr(preview).lower()
            for forbidden in ("section_text", str(ROOT).lower(), "backup_path", "operator note"):
                require(forbidden not in encoded, forbidden)
            require(preview.get("content_free") and preview.get("preview_only"), preview)

        checks = [
            ("current-history-no-rewrite", current_history_needs_no_rewrite),
            ("preview-detects-duplicate-ordering", preview_detects_exact_duplicate_and_ordering),
            ("conflicting-duplicates-review", conflicting_duplicates_require_review),
            ("malformed-history-preserved", malformed_history_is_preserved),
            ("literal-confirmation-required", apply_requires_literal_confirmation),
            ("confirmed-private-backup", confirmed_apply_creates_private_verified_backup),
            ("stale-preview-rejected", stale_preview_is_rejected),
            ("interruption-restores-original", interruption_restores_original),
            ("source-only-content-free-boundary", source_only_boundary_is_explicit),
        ]
        for name, fn in checks: check(name, fn)
    passed=sum(bool(row.get("ok")) for row in RESULTS)
    print(json.dumps({"suite":"v1095.4-duplicate-ordering-reconciliation-preview","passed":passed,"failed":len(RESULTS)-passed,"total":len(RESULTS),"checks":RESULTS}, indent=2))
    return 0 if passed==len(RESULTS) else 1

if __name__ == "__main__": raise SystemExit(main())

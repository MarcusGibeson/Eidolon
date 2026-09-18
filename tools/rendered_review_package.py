from __future__ import annotations

"""Build a review package whose structured documents are rendered record-per-line.

This is a second, general package builder. ``g_evid1_review_package.py`` is a frozen G-EVID1 artifact and is not
touched; it stays exactly as it was, and the package it produced stays installed and byte-identical.

What changes here is only how a structured source document is presented to the reviewer. A JSON source is rendered by
``structured_record_rendering`` into one record per line so a single contiguous quote can carry a record's identity and
its fields together. Plain-text sources are copied through unchanged.

The rendered package is explicitly NOT the frozen canonical artifact and never claims to be. Every rendered document
records the canonical file it came from and that file's digest, and the manifest records the rendering id, so the chain
canonical artifact -> deterministic rendered review input is checkable from the package alone.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review as base  # noqa: E402
import structured_record_rendering as srr  # noqa: E402

PACKAGE_CONTRACT = "rendered-review-package.v1"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_source(path: Path, title: str) -> tuple[str, dict[str, Any]]:
    """Render one source file for review, plus the provenance that ties it to the canonical file.

    A ``.json`` source is rendered record-per-line and must survive a round trip; anything else is passed through
    byte-for-byte. Nothing is summarised, reordered or dropped either way.
    """
    raw = path.read_bytes()
    digest = _sha256_bytes(raw)
    provenance = {"canonical_path": path.name, "canonical_sha256": digest}
    if path.suffix.lower() != ".json":
        provenance["rendering"] = "verbatim"
        return raw.decode("utf-8"), provenance
    document = json.loads(raw.decode("utf-8"))
    if not srr.round_trips(document):
        raise ValueError(f"rendering_is_not_lossless_for:{path.name}")
    body = srr.render(document)
    provenance["rendering"] = srr.RENDERING_ID
    provenance["rendered_sha256"] = _sha256_bytes(body.encode("utf-8"))
    return srr.header(title, path.name, digest) + body, provenance


def build(documents: list[dict[str, Any]], *, out_dir: Path, experiment_id: str, title: str, brief: str,
          canonical_experiment_id: str = "") -> dict[str, Any]:
    """Write a review package. ``documents`` are {path, role, description, source, title} in package order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for spec in documents:
        text, provenance = render_source(Path(spec["source"]), str(spec.get("title") or spec["path"]))
        target = out_dir / spec["path"]
        target.write_text(text, encoding="utf-8", newline="\n")
        entries.append({"doc_id": f"D{len(entries) + 1}", "path": spec["path"], "role": spec["role"],
                        "description": spec["description"],
                        "sha256": _sha256_bytes(target.read_bytes()), "source": provenance})
    manifest = {
        "experiment_id": experiment_id,
        "title": title,
        "task": "independent_review",
        "brief": brief,
        "package_contract": PACKAGE_CONTRACT,
        "rendering": {"id": srr.RENDERING_ID, "description": srr.RENDERING_DESCRIPTION,
                      "max_record_chars": srr.MAX_RECORD_CHARS},
        "documents": entries,
    }
    if canonical_experiment_id:
        manifest["canonical_experiment_id"] = canonical_experiment_id
        manifest["relationship_to_canonical"] = (
            "This package is a deterministic re-rendering of the canonical experiment's artifacts for review input. "
            "It is not byte-identical to any earlier review package and does not replace the frozen canonical "
            "artifacts, which are unchanged.")
    (out_dir / base.MANIFEST_NAME).write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")
    parts = {e["path"]: len(base.chunks((out_dir / e["path"]).read_text(encoding="utf-8"))) for e in entries}
    return {"dir": out_dir, "documents": entries, "parts": parts, "total_parts": sum(parts.values()),
            "total_chars": sum(len((out_dir / e["path"]).read_text(encoding="utf-8")) for e in entries)}


def verify(package_dir: Path, sources: Mapping[str, Path]) -> dict[str, Any]:
    """Check a built package: loader accepts it, digests match, and every rendered document round-trips."""
    package = base.load_package(package_dir)
    manifest = json.loads((package_dir / base.MANIFEST_NAME).read_text(encoding="utf-8"))
    checks: dict[str, Any] = {"loader_accepts": True, "rendering_id": manifest.get("rendering", {}).get("id"),
                              "documents": {}}
    for entry in manifest["documents"]:
        path = package_dir / entry["path"]
        row: dict[str, Any] = {"digest_matches": _sha256_bytes(path.read_bytes()) == entry["sha256"]}
        source_info = entry.get("source") or {}
        source = sources.get(entry["path"])
        if source is not None:
            row["canonical_digest_matches"] = _sha256_bytes(source.read_bytes()) == source_info.get("canonical_sha256")
            if source_info.get("rendering") == srr.RENDERING_ID:
                body = path.read_text(encoding="utf-8").split("\n\n", 1)[1]
                row["round_trips_to_canonical"] = srr.reconstruct(body) == json.loads(source.read_text(encoding="utf-8"))
        checks["documents"][entry["path"]] = row
    checks["all_documents_verified"] = all(all(v is True for v in row.values()) for row in checks["documents"].values())
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a record-per-line rendered review package.")
    parser.add_argument("--spec", required=True, help="JSON file describing the package to build")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    summary = build(spec["documents"], out_dir=Path(args.out), experiment_id=spec["experiment_id"],
                    title=spec["title"], brief=spec["brief"],
                    canonical_experiment_id=spec.get("canonical_experiment_id", ""))
    print(json.dumps({k: v for k, v in summary.items() if k != "dir"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

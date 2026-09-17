from __future__ import annotations

"""G-EVID1: the one canonical way to identify an artifact.

Every place G-EVID1 records or compares artifact identity — the freeze record, a run's condition metadata, and the
verification path — uses this function and nothing else. A Windows checkout rewrites line endings, so hashing raw
bytes made the same corpus hash two different ways depending on where it was read. An auditor comparing a run's
metadata against the freeze would then see what looks like corpus mutation and is only a line ending.

The convention is recorded alongside every digest it produces, so it is legible without reading this file.
"""

import hashlib
from pathlib import Path

CONVENTION = "sha256 over newline-normalised bytes (CRLF and CR both normalised to LF)"
CONVENTION_ID = "g-evid1.canonical.sha256.lf"


def normalise(data: bytes) -> bytes:
    """Line endings only. Nothing else about the bytes is touched."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def canonical_digest(data: bytes | str) -> str:
    payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    return hashlib.sha256(normalise(payload)).hexdigest()


def digest_file(path: str | Path) -> str:
    return canonical_digest(Path(path).read_bytes())


__all__ = ["CONVENTION", "CONVENTION_ID", "normalise", "canonical_digest", "digest_file"]

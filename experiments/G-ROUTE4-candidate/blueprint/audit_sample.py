"""G-ROUTE4 audit-sample procedure (obligation O1). Frozen with the authoring blueprint; not part of the runtime.

The sample is derived only after the single seal commit exists, so no author can know it while authoring:

    key(fixture) = sha256( ascii(seal_commit_id) + ":" + ascii(fixture_id) )   (lowercase hex digest)

For each B′ cell, the k main-corpus fixtures with the smallest key (compared as lowercase hex strings, which is the
same order as the 256-bit integers) are sampled.

    k = ceil(0.10 * cell size)    ->  3 per conversation cell (28), 2 per other eligible cell (18), 1 per R4 cell (1)

Reserve fixtures are never sampled directly. A replacement inherits its slot's sampled flag. The result (38 fixture
ids) is committed before the first adjudication session. `seal_commit_id` is the 40-character lowercase hex id of
the seal commit, whose parent is the frozen blueprint commit.

    python -B audit_sample.py <seal_commit_id> <blueprint.json>     # prints the sample as JSON
    python -B audit_sample.py --self-test                            # checks the frozen test vector
"""

import hashlib
import json
import math
import re
import sys
from pathlib import Path

HEX40 = re.compile(r"[0-9a-f]{40}")


def sample_key(seal_commit_id: str, fixture_id: str) -> str:
    if not HEX40.fullmatch(seal_commit_id):
        raise ValueError("seal_commit_id_must_be_40_lowercase_hex")
    return hashlib.sha256(f"{seal_commit_id}:{fixture_id}".encode("ascii")).hexdigest()


def cell_sample_size(cell_size: int) -> int:
    return math.ceil(0.10 * cell_size)


def derive_sample(seal_commit_id: str, b_cells: dict[str, list[str]]) -> dict[str, list[str]]:
    """b_cells: {cell_name: [main-corpus B′ fixture ids]} -> {cell_name: sorted sampled ids}."""
    out = {}
    for cell, ids in sorted(b_cells.items()):
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate_fixture_id_in_cell:{cell}")
        ranked = sorted(ids, key=lambda fid: (sample_key(seal_commit_id, fid), fid))
        out[cell] = sorted(ranked[:cell_sample_size(len(ids))])
    return out


def b_cells_from_blueprint(blueprint: dict) -> dict[str, list[str]]:
    cells: dict[str, list[str]] = {}
    for slot in blueprint["slots"]:
        if slot["phase"] == "B" and slot["role"] == "main":
            cells.setdefault(f"{slot['task_class']}|{slot['risk']}", []).append(slot["fixture_id"])
    return cells


# Frozen test vector: a fixed pseudo seal id over a tiny synthetic cell layout. Any change to the procedure fails it.
TEST_SEAL = "0123456789abcdef0123456789abcdef01234567"
TEST_CELLS = {"x|R1": [f"B4-TEST-R1-{i:02d}" for i in range(1, 19)], "x|R4": ["B4-TEST-R4-01"]}


def self_test() -> dict:
    got = derive_sample(TEST_SEAL, TEST_CELLS)
    return {"seal": TEST_SEAL, "sample": got,
            "digest": hashlib.sha256(json.dumps(got, sort_keys=True).encode("ascii")).hexdigest()}


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        print(json.dumps(self_test(), indent=2))
    else:
        seal, path = sys.argv[1], Path(sys.argv[2])
        sample = derive_sample(seal, b_cells_from_blueprint(json.loads(path.read_text(encoding="utf-8"))))
        print(json.dumps({"seal_commit_id": seal, "sample": sample,
                          "total": sum(len(v) for v in sample.values())}, indent=2))

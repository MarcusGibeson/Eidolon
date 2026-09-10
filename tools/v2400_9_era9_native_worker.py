from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.dont_write_bytecode = True

from outcome_learning_governance_v2300 import record_verified_outcome


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    runtime_root = Path(sys.argv[1])
    index = int(sys.argv[2])
    evidence_digest = f"{index + 1:064x}"
    result = record_verified_outcome(
        outcome_id=f"native-outcome-{index}",
        task_type="windows-native-race",
        result="success",
        evidence_digest=evidence_digest,
        strategy_code="bounded-race",
        applicability=("windows",),
        event_id=f"native-event-{index}",
        runtime_root=runtime_root,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

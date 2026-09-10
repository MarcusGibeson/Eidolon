from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from conversation_resend_lineage import claim_explicit_resend


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--source-key", required=True)
    parser.add_argument("--resend-key", required=True)
    parser.add_argument("--evidence-token", required=True)
    args = parser.parse_args()
    try:
        value = claim_explicit_resend(
            args.session_id,
            args.source_key,
            args.resend_key,
            source_evidence_token=args.evidence_token,
        )
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error), "error_type": type(error).__name__}))
        return 1
    print(json.dumps({"ok": True, "value": value}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

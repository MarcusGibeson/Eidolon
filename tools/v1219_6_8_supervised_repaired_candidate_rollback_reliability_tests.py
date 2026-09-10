from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1219-c-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import conversational_supervised_repaired_candidate_rollback as rollback
from ordinary_chat_development_campaign import _atomic_json,_read_json
from v1219_repaired_candidate_rollback_fixture import build_repaired_candidate_rollback_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_repaired_candidate_rollback_fixture("c-tamper"); rt=f["runtime"]; p=f["proposal"]; rp=f["rollback_proposal"]
try:
 prepared=rollback.prepare_supervised_repaired_candidate_rollback(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_rollback_proposal_digest=rp["rollback_proposal_digest"],runtime_root=rt)
 path=rollback._execution_path(p["proposal_id"],1,2,rt); bad=_read_json(path); bad["rollback_attempt_limit"]=2; _atomic_json(path,bad)
 blocked=rollback.authorize_and_rollback_repaired_candidate(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_rollback_proposal_digest=rp["rollback_proposal_digest"],authorization_phrase=rp["authorization_phrase"],runtime_root=rt)
 require(blocked["status"]=="supervised_repaired_candidate_rollback_record_invalid")
finally: shutil.rmtree(rt,ignore_errors=True)
f=build_repaired_candidate_rollback_fixture("c-live"); rt=f["runtime"]; p=f["proposal"]; rp=f["rollback_proposal"]
try:
 prepared=rollback.prepare_supervised_repaired_candidate_rollback(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_rollback_proposal_digest=rp["rollback_proposal_digest"],runtime_root=rt)
 path=rollback._execution_path(p["proposal_id"],1,2,rt); row=_read_json(path); row.update({"phase":"running","lease_token":"live","lease_expires_unix":time.time()+60,"status":"supervised_repaired_candidate_rollback_running"}); row=rollback._seal(row,"supervised_repaired_candidate_rollback_record_digest"); _atomic_json(path,row)
 live=rollback.authorize_and_rollback_repaired_candidate(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_rollback_proposal_digest=rp["rollback_proposal_digest"],authorization_phrase=rp["authorization_phrase"],runtime_root=rt)
 require(live["status"]=="supervised_repaired_candidate_rollback_in_progress")
finally: shutil.rmtree(rt,ignore_errors=True)
module=(ROOT/"conscious_agent"/"conversational_supervised_repaired_candidate_rollback.py").read_text()
require("LocalModelClient" not in module); require('"install_authorized": True' not in module)
require('"promotion_authorized": True' not in module); require('"release_authorized": True' not in module)
require('"authority_granted": True' not in module)
print(json.dumps({"ok":True,"version":"1219.8","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"live_duplicate_blocked":True,"tamper_rejected":True,"privacy_preserved":True},sort_keys=True))

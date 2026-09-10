from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1219-a-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import conversational_supervised_repaired_candidate_rollback as rollback
from v1219_repaired_candidate_rollback_fixture import build_repaired_candidate_rollback_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_repaired_candidate_rollback_fixture("a-foundation"); rt=f["runtime"]; p=f["proposal"]; rp=f["rollback_proposal"]
try:
 before={x.relative_to(f["source_workspace_root"]).as_posix():x.read_bytes() for x in f["source_workspace_root"].rglob("*") if x.is_file()}
 row=rollback.prepare_supervised_repaired_candidate_rollback(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_rollback_proposal_digest=rp["rollback_proposal_digest"],runtime_root=rt)
 require(row["ok"] is True,row); require(row["status"]=="supervised_repaired_candidate_rollback_prepared")
 require(row["rollback_attempt_number"]==1); require(row["rollback_attempt_limit"]==1)
 require(row["operation_count"]==1); require(row["phase"]=="prepared")
 require(row["rollback_authorized"] is False); require(row["rollback_executed"] is False)
 require(row["project_modified"] is False); require(row["selected_project_modified"] is False)
 require(row["provider_contacted"] is False); require(row["tests_executed"] is False)
 require(row["release_authorized"] is False); require(row["authority_granted"] is False)
 require(row["rollback_proposal_digest"] in row["authorization_phrase"])
 after={x.relative_to(f["source_workspace_root"]).as_posix():x.read_bytes() for x in f["source_workspace_root"].rglob("*") if x.is_file()}
 require(after==before)
 replay=rollback.prepare_supervised_repaired_candidate_rollback(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_rollback_proposal_digest=rp["rollback_proposal_digest"],runtime_root=rt)
 require(replay["operation_status"]=="resumed")
 stale=rollback.prepare_supervised_repaired_candidate_rollback(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_rollback_proposal_digest="0"*64,runtime_root=rt)
 require(stale["status"]=="supervised_repaired_candidate_rollback_stale_proposal")
 require(str(f["source_workspace_root"]) not in json.dumps(rollback.public_supervised_repaired_candidate_rollback(row)))
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1219.2","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"preparation_non_executing":True,"exact_v1218_binding":True,"release_authorized":False},sort_keys=True))

from __future__ import annotations
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1220-9-data-"))
sys.path.insert(0,str(ROOT))
from conscious_agent.operator_repaired_candidate_rollback_result_review_checkpoint import build_operator_repaired_candidate_rollback_result_review_checkpoint
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
runtime=Path(tempfile.mkdtemp(prefix="eidolon-v1220-9-runtime-"))/"absent"
report=build_operator_repaired_candidate_rollback_result_review_checkpoint(source_root=ROOT,runtime_root=runtime)
require(report["ok"] is True,report); require(report["passed"]==report["total"])
require(report["read_only"] is True); require(report["runtime_data_read"] is False)
require(report["source_signature_before"]==report["source_signature_after"])
require(report["rollback_executed"] is False); require(report["authority_granted"] is False)
require(runtime.exists() is False)
cli=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),"operator-repaired-candidate-rollback-result-review-checkpoint"],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
require(cli.returncode==0,cli.stderr); require(json.loads(cli.stdout)["ok"] is True)
api=(ROOT/"conscious_agent/api_server.py").read_text()
require('parts == ["cognition", "operator-repaired-candidate-rollback-result-review-checkpoint"]' in api)
release=(ROOT/"tools/release_verify.py").read_text()
require("v1220.9-operator-repaired-candidate-rollback-result-review-checkpoint" in release)
metadata=(ROOT/"conscious_agent/release_metadata.py").read_text()
require('WORKING_SOURCE_VERSION = "1220.9"' in metadata)
print(json.dumps({"ok":True,"version":"1220.9","checks":len(CHECKS),"passed":sum(CHECKS),"checkpoint_checks":report["total"],"elapsed_seconds":round(time.monotonic()-START,4),"read_only":True},sort_keys=True))

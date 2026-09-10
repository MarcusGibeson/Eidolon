from __future__ import annotations
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1219-9-data-")); sys.path.insert(0,str(ROOT))
from conscious_agent.supervised_repaired_candidate_rollback_checkpoint import build_supervised_repaired_candidate_rollback_checkpoint
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
runtime=Path(tempfile.mkdtemp(prefix="eidolon-v1219-9-runtime-"))/"absent"
report=build_supervised_repaired_candidate_rollback_checkpoint(source_root=ROOT,runtime_root=runtime)
require(report["ok"] is True,report); require(report["passed"]==report["total"])
for key in ("read_only","post_available","runtime_data_read","runtime_mutated","source_modified","provider_contacted","project_tests_executed","apply_executed","rollback_executed","rollback_authorized","release_authorized","authority_granted"):
 require(report[key] is (key=="read_only"),(key,report[key]))
require(report["source_signature_before"]==report["source_signature_after"]); require(runtime.exists() is False)
require(report["summary"]["rollback_result_outcome_count"]==4); require(report["summary"]["rollback_attempt_limit"]==1)
require(report["summary"]["exact_v1218_authorization_required"] is True); require(report["summary"]["checkpoint_rollback_executed"] is False)
cli=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),"supervised-repaired-candidate-rollback-checkpoint"],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
require(cli.returncode==0,cli.stderr); payload=json.loads(cli.stdout); require(payload["ok"] is True); require(payload["read_only"] is True)
api=(ROOT/"conscious_agent"/"api_server.py").read_text(); dash=(ROOT/"conscious_agent"/"dashboard_first_use.py").read_text()
require('parts == ["cognition", "supervised-repaired-candidate-rollback-checkpoint"]' in api)
require("build_supervised_repaired_candidate_rollback_checkpoint" in api)
require("supervised-repaired-candidate-rollback-checkpoint-panel" in dash)
require("/api/cognition/supervised-repaired-candidate-rollback-checkpoint" in dash)
release=(ROOT/"tools"/"release_verify.py").read_text(); metadata=(ROOT/"conscious_agent"/"release_metadata.py").read_text()
require(release.count('"v1219.9-supervised-repaired-candidate-rollback-checkpoint"')==2)
require(release.count("tools/v1219_9_supervised_repaired_candidate_rollback_checkpoint_tests.py")==1)
require('WORKING_SOURCE_VERSION = "1219.9"' in metadata)
print(json.dumps({"ok":True,"version":"1219.9","checks":len(CHECKS),"passed":sum(CHECKS),"checkpoint_checks":report["total"],"elapsed_seconds":round(time.monotonic()-START,4),"read_only":True,"rollback_executed":False},sort_keys=True))

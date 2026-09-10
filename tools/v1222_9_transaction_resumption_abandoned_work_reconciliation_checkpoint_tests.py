from __future__ import annotations
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1222-9-data-"))
sys.path.insert(0,str(ROOT))
from conscious_agent.transaction_resumption_abandoned_work_reconciliation_checkpoint import build_transaction_resumption_abandoned_work_reconciliation_checkpoint
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
runtime=Path(tempfile.mkdtemp(prefix="eidolon-v1222-9-runtime-"))/"absent"
report=build_transaction_resumption_abandoned_work_reconciliation_checkpoint(source_root=ROOT,runtime_root=runtime)
require(report["ok"] is True,report); require(report["passed"]==report["total"])
require(report["read_only"] is True); require(report["runtime_data_read"] is False)
require(report["source_signature_before"]==report["source_signature_after"])
require(report["project_modified"] is False); require(report["authority_granted"] is False)
require(report["summary"]["assessment_class_count"]==4)
require(report["summary"]["operator_decision_count"]==5)
require(report["summary"]["old_authority_reuse_forbidden"] is True)
require(report["summary"]["new_approval_required_before_continuation"] is True)
require(runtime.exists() is False)
cli=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),"transaction-resumption-abandoned-work-reconciliation-checkpoint"],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
require(cli.returncode==0,cli.stderr); require(json.loads(cli.stdout)["ok"] is True)
api=(ROOT/"conscious_agent/api_server.py").read_text()
require('parts == ["cognition", "transaction-resumption-abandoned-work-reconciliation-checkpoint"]' in api)
release=(ROOT/"tools/release_verify.py").read_text()
require("v1222.9-transaction-resumption-abandoned-work-reconciliation-checkpoint" in release)
metadata=(ROOT/"conscious_agent/release_metadata.py").read_text()
require('WORKING_SOURCE_VERSION = "1222.9"' in metadata)
print(json.dumps({"ok":True,"version":"1222.9","checks":len(CHECKS),"passed":sum(CHECKS),"checkpoint_checks":report["total"],"elapsed_seconds":round(time.monotonic()-START,4),"read_only":True},sort_keys=True))

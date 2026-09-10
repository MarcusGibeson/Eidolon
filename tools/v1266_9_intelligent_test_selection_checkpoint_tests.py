from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from intelligent_test_selection_checkpoint import build_intelligent_test_selection_checkpoint
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def sig():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts: rows.append((p.relative_to(ROOT).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before=sig();report=build_intelligent_test_selection_checkpoint(source_root=ROOT);req(report['ok'],'checkpoint_ready');req(report['checkpoint_version']=='1266.9' and report['contract_version']=='v1266.9','checkpoint_version_exact');req(report['details']['tests_executed'] is False and report['details']['provider_contacted'] is False,'checkpoint_read_only');req(report['details']['repair_deferred_to_v1267'] is True and report['details']['next_bounded_unit']=='v1267 Iterative Self-Repair','v1267_boundary_exact');req(report['details']['active_source_modified'] is False and report['details']['candidate_workspace_modified'] is False,'mutation_denied');req(report['details']['test_execution_authorized'] is False and report['details']['repair_authorized'] is False,'authority_denied');req(len(report['details']['behavioral_evidence'])==3,'three_behavioral_suites_named');req(sig()==before,'checkpoint_preserves_source')
print(json.dumps({'ok':True,'suite':'v1266.9-intelligent-test-selection-checkpoint','passed':len(CHECKS),'failed':0,'checks':CHECKS,'read_only':True},indent=2,sort_keys=True))

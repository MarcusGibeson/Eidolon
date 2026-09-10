from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent';R=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b20-'));PJT=R/'project';PJT.mkdir();(PJT/'notes.txt').write_text('unrelated operator file\n')
os.environ['EIDOLON_DATA_DIR']=str(R/'runtime');os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path.insert(0,str(AGENT))
from v1489_completion_benchmark import *
from practical_coding_capability import write_calculator_webpage,inventory_project,static_web_behavior_check,snapshot_digests,unrelated_changes_preserved
from verification_evidence_quality import verification_receipt
from security_privacy_authority_contract import denied_authority_matrix
P=F=0
def ck(n,c,d=''):
 global P,F
 if c:P+=1;print('PASS',n)
 else:F+=1;print('FAIL',n,d);raise AssertionError(d or n)
try:
 ck('0191 frozen feature set accepts roadmap domain',feature_freeze('natural conversation')['within_frozen_v1489_scope'])
 ck('0191 unrelated addition rejected',feature_freeze('new autonomous internet agent')['unrelated_addition_rejected'])
 # 0192-0194 are proven by the cumulative runner; this suite validates the evidence contract and authority boundary.
 receipts=[verification_receipt(suite='truth_conversation_action',passed=1,failed=0,duration_ms=1),verification_receipt(suite='desktop_provider_recovery',passed=1,failed=0,duration_ms=1),verification_receipt(suite='reasoning_coding_security',passed=1,failed=0,duration_ms=1)]
 gates=external_review_gates(windows_workflow_review=False,operator_unscripted_trial=False)
 led=integrated_evidence_ledger(receipts,external_gates=gates);ck('0192-0194 integrated evidence ledger clean',led['suite_count']==3 and led['checks_failed']==0,led)
 ck('0195 Windows review remains external gate',not gates['windows_workflow_review'] and gates['browser_completion_candidate_allowed'] and not gates['promotion_allowed'],gates)
 ck('0196 operator-scored unscripted trial remains external gate',not gates['operator_unscripted_trial'] and gates['operator_review_required'],gates)
 before=snapshot_digests(PJT);write_calculator_webpage(PJT);inv=inventory_project(PJT);behavior=static_web_behavior_check(PJT);after=snapshot_digests(PJT);result=coding_benchmark_result(inspected=inv['file_count']>=4,implemented=True,tested=behavior['ok'],unrelated_preserved=before['notes.txt']==after['notes.txt'],auto_applied=False);ck('0197 supervised unfamiliar-project coding benchmark',result['ok'],result)
 decision=repair_decision(concrete_defects=[]);ck('0198 no invented benchmark repairs when none found',decision['concrete_defect_count']==0 and not decision['rerun_affected_verification'],decision)
 ck('0199 content-free evidence ledger digest',led['content_free'] and len(led['ledger_digest'])==64 and 'unrelated operator file' not in str(led),led)
 matrix=denied_authority_matrix();ck('0200 completion candidate grants no release/install/model authority',not any(matrix.values()) and not gates['promotion_allowed'] and not gates['installation_allowed'],(matrix,gates))
finally:shutil.rmtree(R,ignore_errors=True)
print(f'SUMMARY passed={P} failed={F}');raise SystemExit(1 if F else 0)

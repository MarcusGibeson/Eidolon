from __future__ import annotations
import json,os,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from calibrated_uncertainty_foundations import *
from calibrated_uncertainty_reliability import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
h=inspect_calibrated_uncertainty_health(source_root=ROOT);req(h['ok'] and all(h['checks'].values()),'health');hand=build_calibrated_uncertainty_handoff(source_root=ROOT);req(hand['ok'],'handoff');req(hand['next_bounded_unit']=='v1283 Development Memory Relevance','next');req(hand['v1283_started'] is False,'unstarted');req('unknown_not_false' in hand['native_windows_review'],'unknown')
c=build_uncertainty_claim(claim_code='x',epistemic_state='assumed',confidence=40);u=apply_uncertainty_evidence(c,evidence_kind='inferred_support',evidence_code='i');cmp=compare_uncertainty_claims(c,u);req(cmp['ok'] and cmp['confidence_changed'] and cmp['state_changed'],'revision');req(not cmp['authority_changed'],'no_authority_change')
for i in range(40):u=apply_uncertainty_evidence(u,evidence_kind='inferred_support',evidence_code=f'e{i}')
req(len(u['history'])<=24,'history_bounded');req(len(u['evidence_codes'])<=32,'evidence_bounded')
code="import sys;from pathlib import Path;sys.path[:0]=[str(Path(r'%s')),str(Path(r'%s')/'conscious_agent')];import calibrated_uncertainty_foundations,calibrated_uncertainty,calibrated_uncertainty_reliability;print('ok')"%(ROOT,ROOT);p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20);req(p.returncode==0 and 'ok' in p.stdout,'fresh_import')
print(json.dumps({'ok':True,'suite':'v1282.6-8-calibrated-uncertainty-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))

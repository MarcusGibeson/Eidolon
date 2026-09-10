from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1300-test-'))
from supervised_self_development_beta_foundations import *
from v1300_test_support import identity,d
checks=[]
def req(v,n):checks.append(n);assert v,n
i=identity();req(i['beta_id'].startswith('selfdevbeta_'),'beta_id');req(valid_digest(i['identity_digest']),'identity_digest');req(i['baseline_source_digest']!=i['candidate_source_digest'],'changed_candidate');req(i['architecture_lineage']['proposal']=='v1291' and i['architecture_lineage']['governed_update']=='v1269','lineage');req(not any(i[k] for k in DENIED_AUTHORITY),'identity_no_authority');req(len(BETA_STAGES)==14,'stage_count');req(BETA_STAGES[0]=='inspect' and BETA_STAGES[-1]=='post_update_recovery','stage_bounds')
s=beta_step(i,sequence=1,stage='inspect',evidence_digest=d('inspect'),source_digest=i['baseline_source_digest']);req(valid_digest(s['step_digest']),'step_digest');req(s['stage']=='inspect' and not s['self_update_authorized'],'step_no_authority')
try:beta_step(i,sequence=1,stage='invent_authority',evidence_digest=d('x'),source_digest=i['baseline_source_digest']);bad=False
except ValueError:bad=True
req(bad,'unknown_stage_rejected')
try:seal_beta_identity(objective_digest=d('o'),baseline_source_digest=d('same'),candidate_source_digest=d('same'),proposal_digest=d('p'),deliberation_digest=d('d'),plan_digest=d('pl'),candidate_evaluation_digest=d('c'),verification_digest=d('v'),review_digest=d('r'),rehearsal_digest=d('rr'));bad=False
except ValueError:bad=True
req(bad,'unchanged_candidate_rejected');req(CONTRACT_VERSION=='v1300.2','version');req(ARCHITECTURE_LINEAGE['final_rehearsal']=='v1299','v1299_lineage')
print(json.dumps({'suite':'v1300.0-v1300.2-supervised-self-development-beta-foundations','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))

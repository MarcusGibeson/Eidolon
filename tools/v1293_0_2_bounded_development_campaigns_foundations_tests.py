from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from bounded_development_campaigns_foundations import *
C=[]
def req(v,l):
 if not v: raise AssertionError(l)
 C.append(l)
def d(s): return sha256(s.encode()).hexdigest()
i=seal_campaign_identity(proposal_id='p1',proposal_digest=d('p'),objective_digest=d('o'),operator_selection_digest=d('s'),scope_paths=['conscious_agent/a.py','tools/a.py'],max_events=20,max_recovery_attempts=2)
req(i['campaign_id'].startswith('campaign-'),'campaign_id');req(valid_digest(i['identity_digest']),'identity_digest');req(len(i['scope_path_digests'])==2,'hashed_scope');req(valid_digest(i['scope_digest']),'scope_digest');req(i['max_events']==20 and i['max_recovery_attempts']==2,'budgets')
s=initial_campaign_state(i);req(s['current_stage']=='prepared' and not s['terminal'],'prepared');req(validate_state_identity(s),'valid_state');req(all(s[k] is False for k in DENIED_AUTHORITY),'no_authority');req(PROGRESS_STAGES[-1]=='complete','progress');req('cancelled' in TERMINAL_STAGES,'terminal')
req(scope_path_digest('a/b.py')==scope_path_digest('a\\b.py'),'path_normalization')
try: scope_path_digest('../secret'); bad=False
except ValueError: bad=True
req(bad,'traversal_rejected')
try: seal_campaign_identity(proposal_id='p',proposal_digest='bad',objective_digest=d('o'),operator_selection_digest=d('s'),scope_paths=['a']); bad2=False
except ValueError: bad2=True
req(bad2,'digest_required');req(ARCHITECTURE_LINEAGE['dynamic_replanning']=='v1286' and ARCHITECTURE_LINEAGE['persistent_sessions']=='v1256','lineage')
print(json.dumps({'ok':True,'suite':'v1293.0-v1293.2-bounded-development-campaigns-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))

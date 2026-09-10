from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from integrated_developer_beta import AUTHORITY_FLAGS,canonical_scenario_evidence,evaluate_integrated_scenario,scenario_registry
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def check(v): checks.append(bool(v))
for s in scenario_registry()['scenarios']:
    sid=s['scenario_id']; base=canonical_scenario_evidence(sid)
    attacks=[]
    x=dict(base); x['scenario_digest']='0'*64; attacks.append((x,'stale_or_tampered_scenario_digest'))
    x=dict(base); x['completed_stages']=x['completed_stages'][:-1]; attacks.append((x,'incomplete_or_reordered_stage_evidence'))
    x=dict(base); x['completed_stages']=list(reversed(x['completed_stages'])); attacks.append((x,'incomplete_or_reordered_stage_evidence'))
    x=dict(base); x['missing_evidence_claimed_as_pass']=True; attacks.append((x,'missing_evidence_cannot_pass'))
    x=dict(base); x['authority_granted']=True; attacks.append((x,'benchmark_evidence_cannot_grant_authority'))
    for evidence,reason in attacks:
        out=evaluate_integrated_scenario(sid,evidence); check(out.get('ok') is False); check(out.get('status')=='scenario_evidence_blocked'); check(reason in out.get('reason_codes',[])); check(out.get('content_free') is True)
        for key,expected in AUTHORITY_FLAGS.items(): check(out.get(key) is expected)
unknown=evaluate_integrated_scenario('not-a-scenario',{}); check(unknown.get('ok') is False); check(unknown.get('status')=='unknown_scenario')
for casual in ('It would be nice to have an integrated beta.','Maybe run every tool automatically.','"show integrated developer beta benchmark" is a quote.'):
    out=process_ordinary_chat_development_turn(casual); check(out.get('active') is not True or 'integrated_developer_beta' not in out)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)

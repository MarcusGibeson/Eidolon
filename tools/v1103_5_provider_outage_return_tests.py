from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for x in (AGENT,ROOT):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
from messaging_continuity import build_provider_outage_transition

def require(c,d='requirement failed'):
    if not c: raise AssertionError(d)

def test_outage_keeps_local_shell_and_draft_usable_without_replay():
    r=build_provider_outage_transition(previous_state='ready',observed_state='unavailable_service',draft_present=True,accepted_operation_pending=True)
    require(r['status']=='outage' and r['outage_active'],r)
    require(r['chat_shell_usable'] and r['draft_preserved'],r)
    require(not r['automatic_generation_replay'] and not r['automatic_resend'],r)

def test_provider_return_requires_an_explicit_new_send():
    r=build_provider_outage_transition(previous_state='unavailable_service',observed_state='ready',draft_present=True)
    require(r['status']=='returned' and r['provider_returned'],r)
    require(r['explicit_send_required'] and not r['provider_or_model_changed'],r)

def test_unknown_readiness_never_becomes_false_ready():
    r=build_provider_outage_transition(previous_state='unknown',observed_state='nonsense')
    require(r['status']=='unknown' and not r['generation_available'],r)
    require(r['explicit_send_required'] and r['content_free'],r)

def test_first_use_shell_persists_bounded_checks_and_recovers_without_send():
    src=(AGENT/'dashboard_first_use.py').read_text()
    for token in ("method:'POST'",'recovery_trigger','visibility_recovery','providerReturned','Provider returned. Your draft is intact','No message was replayed or sent automatically.'): require(token in src,token)
    require("/api/local-model/readiness" in src and 'providerCheckInFlight' in src,'bounded readiness check missing')

def test_persisted_recovery_evidence_preserves_no_replay_boundary():
    src=(AGENT/'provider_recovery_evidence.py').read_text()
    require(src.count('"automatic_generation_replay": False')>=2,'automatic replay boundary missing')
    require(src.count('"automatic_resend": False')>=2,'automatic resend boundary missing')
    require('configured_values_match' in src and 'recovery_proven' in src,'configured recovery proof missing')

def test_version_suite_registration_is_exactly_once():
    verifier=(ROOT/'tools/post_review_development_verify.py').read_text(); require(verifier.count('"tools/v1103_5_provider_outage_return_tests.py"')==1,'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    out=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:out.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;out.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1103.5-provider-outage-return','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':out};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())

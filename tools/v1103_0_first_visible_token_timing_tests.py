from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for x in (AGENT,ROOT):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
from messaging_reliability import build_first_visible_timing

def require(c,d='requirement failed'):
    if not c: raise AssertionError(d)

def test_phase_report_is_content_free_and_preserves_unknowns():
    r=build_first_visible_timing(intent_to_acceptance_ms=40,acceptance_to_first_transport_ms=120,acceptance_to_first_visible_ms=160,intent_to_first_visible_ms=200,render_delay_ms=8,total_ms=900)
    require(r['status']=='measured',r); require(r['phases']['intent_to_first_visible_ms']==200,r)
    for key in ('contains_message_text','contains_response_text','contains_prompt_text','private_paths_included','provider_payload_included'): require(r[key] is False,(key,r))
    pending=build_first_visible_timing(); require(pending['status']=='pending' and pending['phases']['intent_to_first_visible_ms'] is None,pending)
def test_negative_and_invalid_values_are_bounded_without_fabrication():
    r=build_first_visible_timing(intent_to_acceptance_ms=-5,acceptance_to_first_visible_ms='bad',intent_to_first_visible_ms=10.7)
    require(r['phases']['intent_to_acceptance_ms']==0,r); require(r['phases']['acceptance_to_first_visible_ms'] is None,r); require(r['phases']['intent_to_first_visible_ms']==11,r)
def test_runtime_emits_one_content_free_provider_start_and_first_visible_timing():
    src=(AGENT/'conversation_runtime.py').read_text()
    require(src.count('"event": "provider_request"')==1,'provider request event count')
    require('"request_index": 1' in src and '"automatic_retry": False' in src, 'provider start evidence')
    require('"first_visible_token_ms"' in src and '"first_transport_chunk_ms"' in src and '"content_free": True' in src,'timing payload')
def test_first_use_shell_reports_browser_visible_timing_without_content():
    src=(AGENT/'dashboard_first_use.py').read_text()
    for token in ('Message delivery','__eidolonLastDeliveryTiming','intent_to_first_visible_ms','content_free:true','First visible response:'): require(token in src,token)
    require('No message or response content is recorded in timing evidence.' in src,'privacy copy')
def test_full_console_uses_visible_render_boundary_and_server_timing():
    src=(AGENT/'dashboard_chat_console.py').read_text()
    for token in ('clientFirstVisibleMs','__eidolonLastDeliveryTiming','server:payload.timing || null','content_free:true'): require(token in src,token)
def test_version_suite_registration_is_exactly_once():
    verifier=(ROOT/'tools/post_review_development_verify.py').read_text(); require(verifier.count('"tools/v1103_0_first_visible_token_timing_tests.py"')==1,'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    out=[]; passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:out.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;out.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1103.0-first-visible-token-timing','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':out}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())

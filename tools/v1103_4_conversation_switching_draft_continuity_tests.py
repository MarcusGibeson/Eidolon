from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for x in (AGENT,ROOT):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
from messaging_continuity import build_session_switch_continuity

def require(c,d='requirement failed'):
    if not c: raise AssertionError(d)

def test_complete_switch_preserves_source_and_target_state_without_provider():
    r=build_session_switch_continuity(source_draft_saved=True,source_presentation_saved=True,target_draft_restored=True,target_presentation_restored=True)
    require(r['status']=='pass' and r['continuity_preserved'],r)
    require(not r['provider_contacted'] and not r['accepted_turn_replayed'],r)

def test_missing_draft_or_provider_contact_blocks_switch_evidence():
    for row in (
        dict(source_draft_saved=False,source_presentation_saved=True,target_draft_restored=True,target_presentation_restored=True),
        dict(source_draft_saved=True,source_presentation_saved=True,target_draft_restored=True,target_presentation_restored=True,provider_contacted=True),
        dict(source_draft_saved=True,source_presentation_saved=True,target_draft_restored=False,target_presentation_restored=True),
    ):
        require(build_session_switch_continuity(**row)['status']=='blocked',row)

def test_stale_selection_can_be_ignored_without_losing_source_state():
    r=build_session_switch_continuity(source_draft_saved=True,source_presentation_saved=True,target_draft_restored=True,target_presentation_restored=True,stale_selection_ignored=True,duplicate_switch_count=2)
    require(r['status']=='stale_ignored' and r['continuity_preserved'],r)

def test_first_use_shell_switches_with_atomic_source_state_payload():
    src=(AGENT/'dashboard_first_use.py').read_text()
    for token in ('session-selector','switchConversationSession','selectionGeneration','source_draft_content','source_follow_latest','source_view_anchor_turn_id','/api/dashboard-chat/session-switch'): require(token in src,token)
    require('Switching conversations never sends a draft automatically.' in src,'switch safety copy')

def test_server_saves_source_state_before_moving_active_selection():
    src=(AGENT/'conversation_navigation.py').read_text()
    draft=src.index('draft_result = save_conversation_draft')
    presentation=src.index('presentation_result = save_conversation_presentation_state',draft)
    select=src.index('selected = select_conversation_session',presentation)
    require(draft<presentation<select,(draft,presentation,select))
    require('generation <= latest_generation' in src,'stale generation protection missing')

def test_version_suite_registration_is_exactly_once():
    verifier=(ROOT/'tools/post_review_development_verify.py').read_text(); require(verifier.count('"tools/v1103_4_conversation_switching_draft_continuity_tests.py"')==1,'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    out=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:out.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;out.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1103.4-conversation-switching-draft-continuity','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':out};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())

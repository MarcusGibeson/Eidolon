from __future__ import annotations
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for x in (AGENT,ROOT):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
from messaging_continuity import build_scroll_anchor_state
import dashboard_first_use

def require(c,d='requirement failed'):
    if not c: raise AssertionError(d)

def test_near_bottom_follows_latest_and_clears_unread():
    r=build_scroll_anchor_state(scroll_top_px=890,scroll_height_px=1000,client_height_px=100,unread_turn_count=4)
    require(r['status']=='following_latest' and r['follow_latest'],r)
    require(not r['jump_to_latest_visible'] and r['unread_turn_count']==0,r)

def test_reading_history_preserves_anchor_and_shows_jump():
    r=build_scroll_anchor_state(scroll_top_px=300,scroll_height_px=1200,client_height_px=400,unread_turn_count=3)
    require(r['status']=='reading_history' and not r['follow_latest'],r)
    require(r['preserve_anchor_on_append'] and r['jump_to_latest_visible'],r)
    require(r['distance_from_bottom_px']==500 and r['unread_turn_count']==3,r)

def test_scroll_evidence_is_bounded_and_content_free():
    r=build_scroll_anchor_state(scroll_top_px='bad',scroll_height_px=999999999,client_height_px=-3,unread_turn_count=999999999)
    require(r['distance_from_bottom_px']==1000000,r)
    require(r['unread_turn_count']==10000000,r)
    for key in ('contains_message_text','contains_response_text','private_paths_included'): require(r[key] is False,(key,r))

def test_first_use_shell_has_anchor_preservation_and_jump_control():
    src=(AGENT/'dashboard_first_use.py').read_text()
    for token in ('jump-to-latest','captureScrollPresentation','savePresentation','restorePresentation','preserveScrollAnchor','unread-turn-count'): require(token in src,token)
    require("if (followLatest) log.scrollTop = log.scrollHeight" in src,'append must not steal history position')
    require("/api/dashboard-chat/presentation" in src,'presentation persistence missing')

def test_rendered_first_use_javascript_is_syntax_valid():
    html=dashboard_first_use.render_first_use_shell(); match=re.search(r'<script>(.*?)</script>',html,re.S); require(match,'script missing')
    script=match.group(1); require("replaceAll('\\r\\n','\\n')" in script,'SSE newline escapes missing')
    node=shutil.which('node')
    if node:
        with tempfile.NamedTemporaryFile('w',suffix='.js',encoding='utf-8',delete=False) as handle: handle.write(script); path=handle.name
        try:
            result=subprocess.run([node,'--check',path],capture_output=True,text=True,timeout=20)
            require(result.returncode==0,result.stderr)
        finally: Path(path).unlink(missing_ok=True)

def test_full_console_retains_stable_anchor_contract():
    src=(AGENT/'dashboard_chat_console.py').read_text()
    for token in ('view_anchor_turn_id','scroll_from_bottom_px','chat-jump-latest','readingBoundary','restorePresentation'): require(token in src,token)

def test_version_suite_registration_is_exactly_once():
    verifier=(ROOT/'tools/post_review_development_verify.py').read_text(); require(verifier.count('"tools/v1103_3_scroll_anchoring_jump_latest_tests.py"')==1,'registration')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    out=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:out.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;out.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1103.3-scroll-anchoring-jump-latest','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':out};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())

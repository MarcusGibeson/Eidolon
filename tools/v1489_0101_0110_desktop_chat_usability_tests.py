from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; RUNTIME=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b11-'))
os.environ['EIDOLON_DATA_DIR']=str(RUNTIME); os.environ['PYTHONDONTWRITEBYTECODE']='1'; sys.dont_write_bytecode=True; sys.path.insert(0,str(AGENT))
from desktop_chat_usability_contract import *
PASSED=FAILED=0
def check(n,c,d=''):
 global PASSED,FAILED
 if c: PASSED+=1; print('PASS',n)
 else: FAILED+=1; print('FAIL',n,d); raise AssertionError(d or n)
try:
 p=desktop_chat_layout_projection(1280,720,100); check('0101 composer visible at Windows 100%',p.composer_visible and p.chat_usable,p.public_summary())
 for dims in [(320,480),(620,480),(900,600),(1440,900)]:
  p=desktop_chat_layout_projection(*dims,100); check('0102 supported window usable '+str(dims),p.composer_visible,p.public_summary())
 check('0103 composer host click focuses input',should_focus_composer(target='composer_host') and should_focus_composer(target='composer_frame'))
 check('0104 Enter sends',composer_key_action(keysym='Return',shift=False)=='send')
 check('0104 Shift Enter inserts newline',composer_key_action(keysym='Return',shift=True)=='newline')
 d=draft_switch_projection(source_session_id='s1',target_session_id='s2',source_saved=True,target_loaded=True); check('0105 drafts preserved across switches',d['safe_to_switch'] and not d['provider_request_required'],d)
 r=reading_position_projection(following_latest=True,unread_turn_count=4); check('0106 following latest clears unread',r['follow_latest'] and r['unread_turn_count']==0,r)
 r=reading_position_projection(following_latest=True,unread_turn_count=4,manual_scroll=True); check('0106 manual scroll not trapped',r['manual_scroll_preserved'] and not r['follow_latest'],r)
 check('0107 jump latest appears off-tail',r['jump_to_latest_visible'] and r['unread_turn_count']==4,r)
 m=assistant_marker_projection(accepted=True,visible_text=False,terminal=False); check('0108 no empty assistant marker during generation',not m['show_assistant_marker'] and not m['empty_marker_allowed'],m)
 m=assistant_marker_projection(accepted=True,visible_text=True,terminal=False); check('0108 marker appears with visible text',m['show_assistant_marker'],m)
 shell=(AGENT/'desktop_shell.py').read_text(); check('0103 production shell binds frame focus','chat_frame.bind("<Button-1>", focus_composer_from_host)' in shell)
 check('0104 production shell uses shared key contract','composer_key_action(' in shell and 'shift=bool' in shell)
 js=(AGENT/'dashboard_chat_console.py').read_text(); check('0105 browser draft continuity retained','persistDraft' in js and 'currentDraftKey' in js)
 check('0106 browser follow/manual scroll retained','isFollowingConversation' in js and 'scrollConversation' in js)
 check('0107 browser jump-to-latest retained',"id='chat-jump-latest'" in js and 'unread_turn_count' in js)
 check('0109 IM behavior foundations coexist','focusComposer' in js and 'Shift' in js and 'keydown' in js)
finally: shutil.rmtree(RUNTIME,ignore_errors=True)
print(f'SUMMARY passed={PASSED} failed={FAILED}')
raise SystemExit(1 if FAILED else 0)

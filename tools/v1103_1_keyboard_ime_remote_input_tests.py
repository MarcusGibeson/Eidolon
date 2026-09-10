from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
for x in (AGENT,ROOT):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
from messaging_reliability import keyboard_intent

def require(c,d='requirement failed'):
    if not c: raise AssertionError(d)
def test_enter_sends_once_and_shift_enter_is_newline():
    require(keyboard_intent(key='Enter')['action']=='send'); require(keyboard_intent(key='Enter',shift=True)['action']=='newline')
def test_ime_composition_and_keycode_229_never_send():
    for row in (keyboard_intent(key='Enter',composing=True),keyboard_intent(key='Enter',key_code=229),keyboard_intent(input_type='insertParagraph',composing=True)): require(row['action']=='composition' and row['submit_once'] is False,row)
def test_remote_beforeinput_can_send_without_keydown():
    r=keyboard_intent(input_type='insertParagraph'); require(r['action']=='send' and r['prevent_default'] and r['submit_once'],r)
def test_repeated_or_pending_input_is_blocked_as_duplicate():
    for r in (keyboard_intent(key='Enter',repeated=True),keyboard_intent(input_type='insertLineBreak',submission_pending=True)): require(r['action']=='blocked_duplicate' and r['submit_once'] is False,r)
def test_both_chat_shells_use_composition_and_single_submit_latches():
    first=(AGENT/'dashboard_first_use.py').read_text(); full=(AGENT/'dashboard_chat_console.py').read_text()
    for src in (first,full):
        for token in ('compositionstart','compositionend','keyCode===229' if src is first else 'keyCode === 229','event.repeat','beforeinput','insertLineBreak','insertParagraph','keyboardSubmitLatch'): require(token in src,token)
    require('requestComposerSend' in first and 'requestComposerSubmitOnce' in full,'shared behavior surface')
def test_version_suite_registration_is_exactly_once():
    verifier=(ROOT/'tools/post_review_development_verify.py').read_text(); require(verifier.count('"tools/v1103_1_keyboard_ime_remote_input_tests.py"')==1,'registration')
TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    out=[];passed=0
    for n,f in TESTS:
        try:f()
        except Exception as e:out.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
        else:passed+=1;out.append({'name':n,'status':'pass','message':''})
    r={'suite':'v1103.1-keyboard-ime-remote-input','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'checks':out};print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())

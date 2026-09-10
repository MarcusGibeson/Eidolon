from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; R=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b12-'))
os.environ['EIDOLON_DATA_DIR']=str(R); os.environ['PYTHONDONTWRITEBYTECODE']='1'; sys.dont_write_bytecode=True; sys.path.insert(0,str(AGENT))
from chat_accessibility_input_contract import *
P=F=0
def ck(n,c,d=''):
 global P,F
 if c:P+=1;print('PASS',n)
 else:F+=1;print('FAIL',n,d);raise AssertionError(d or n)
try:
 p=accessibility_projection(); ck('0111 predictable focus order',p.focus_order[1:4]==('message_composer','send_button','cancel_button'),p.public_summary())
 css=(AGENT/'dashboard_chat_styles.py').read_text(encoding='utf-8'); ck('0112 visible focus state',':focus-visible' in css and 'outline:' in css)
 k=announcement_key(event_kind='response',operation_id='op1',state='done'); ck('0113 announcement key stable',k==announcement_key(event_kind='response',operation_id='op1',state='done'))
 ck('0113 announce once',should_announce(key=k,announced=set()) and not should_announce(key=k,announced={k}))
 ck('0114 IME blocks accidental send',keyboard_send_action(key='Enter',composing=True)=='noop')
 ck('0114 composition end permits send',keyboard_send_action(key='Enter',composing=False)=='send')
 ck('0115 mobile Enter/send semantics',keyboard_send_action(key='Enter',mobile_send_hint=True)=='send')
 ck('0115 Shift Enter remains newline',keyboard_send_action(key='Enter',shift=True,mobile_send_hint=True)=='newline')
 ck('0116 narrow layout bounded',narrow_layout_ok(width_px=320,composer_width_px=304) and not narrow_layout_ok(width_px=320,composer_width_px=340))
 a=semantic_label_audit({'message_composer':'Message Eidolon','send_button':'Send','cancel_button':'Cancel','status_region':'Status'}); ck('0117 semantic labels complete',a['ok'],a)
 ck('0118 reduced motion supported','prefers-reduced-motion: reduce' in (AGENT/'static/dashboard.css').read_text(encoding='utf-8'))
 ck('0118 high contrast supported','forced-colors: active' in (AGENT/'static/dashboard.css').read_text(encoding='utf-8'))
 html=(AGENT/'dashboard_chat_console.py').read_text(encoding='utf-8'); ck('0113 live log semantics',"role='log'" in html and "aria-relevant='additions text'" in html)
 ck('0114 production IME handlers','compositionstart' in html and 'compositionend' in html)
 ck('0115 mobile keyboard hint',"enterkeyhint='send'" in html and "inputmode='text'" in html)
 ck('0117 composer has accessible name',"aria-label='Message Eidolon'" in html and "aria-describedby='chat-draft-status'" in html)
 ck('0119 deterministic accessibility protocol',p.content_free and p.reduced_motion_supported and p.forced_colors_supported,p.public_summary())
finally: shutil.rmtree(R,ignore_errors=True)
print(f'SUMMARY passed={P} failed={F}'); raise SystemExit(1 if F else 0)

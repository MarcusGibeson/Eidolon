from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent';R=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b15-'));PJT=R/'sample';PJT.mkdir()
os.environ['EIDOLON_DATA_DIR']=str(R/'runtime');os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path.insert(0,str(AGENT))
from practical_coding_capability import *
P=F=0
def ck(n,c,d=''):
 global P,F
 if c:P+=1;print('PASS',n)
 else:F+=1;print('FAIL',n,d);raise AssertionError(d or n)
try:
 (PJT/'README.md').write_text('Synthetic unfamiliar project.\n'); (PJT/'notes.txt').write_text('operator unrelated change\n')
 files=write_calculator_webpage(PJT); ck('0141 calculator webpage created in isolation',set(files)=={'index.html','style.css','app.js'} and static_web_behavior_check(PJT)['ok'])
 inv=inventory_project(PJT); ck('0142 unfamiliar project inspected before selection',inv['file_count']>=5 and inv['content_free'],inv)
 plan=bounded_implementation_plan('Improve calculator behavior',inv); ck('0143 bounded plan tied to concrete files/tests',plan['inspect_first'] and plan['test_required'] and set(plan['selected_files'])>={'index.html','style.css','app.js'},plan)
 before=snapshot_digests(PJT); (PJT/'index.html').write_text((PJT/'index.html').read_text().replace('<h1>Calculator</h1>','<h1>Calculator</h1><p class="hint">Keyboard-free demo</p>')); ck('0144 HTML edit preserves project convention','style.css' in (PJT/'index.html').read_text())
 ck('0145 actual static behavior inspection passes',static_web_behavior_check(PJT)['ok'],static_web_behavior_check(PJT))
 # Deliberately introduce functional defect, then bounded repair.
 js=PJT/'app.js'; js.write_text(js.read_text().replace("if(value==='=')","if(value==='ENTER')")); ck('0146 defect introduced',not static_web_behavior_check(PJT)['ok'])
 rep=repair_known_defect(PJT,'functional_equal_missing'); ck('0146 functional defect repaired',rep['bounded'] and static_web_behavior_check(PJT)['ok'],rep)
 css=PJT/'style.css'; css.write_text(css.read_text().replace('width:min(92vw,24rem)','width:48rem')); rep2=repair_known_defect(PJT,'responsive_overflow'); ck('0147 responsive defect repaired','style.css' in rep2['changed_files'] and 'width:min(92vw,24rem)' in css.read_text(),rep2)
 after=snapshot_digests(PJT); ck('0148 unrelated user file preserved',before['notes.txt']==after['notes.txt'] and before['README.md']==after['README.md'])
 ev=reviewable_patch_evidence(before,after); ck('0149 patch evidence reviewable not auto-applied',ev['changed_file_count']>=1 and not ev['auto_apply_allowed'] and ev['rollback_required'],ev)
 ck('0149 patch evidence hides file content','operator unrelated change' not in str(ev),ev)
finally:shutil.rmtree(R,ignore_errors=True)
print(f'SUMMARY passed={P} failed={F}');raise SystemExit(1 if F else 0)

from __future__ import annotations
import json,os,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from causal_diagnostic_reasoning_foundations import *
from causal_diagnostic_reasoning_reliability import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
h=inspect_causal_diagnostic_health(source_root=ROOT);req(h['ok'] and all(h['checks'].values()),'health');hand=build_causal_diagnostic_handoff(source_root=ROOT);req(hand['ok'],'handoff');req(hand['next_bounded_unit']=='v1282 Calibrated Uncertainty','next');req(hand['v1282_started'] is False,'unstarted');req('provider_outage_not_code_repair' in hand['native_windows_review'],'provider_classification')
a=build_causal_hypothesis(hypothesis_code='a',cause_class='environment',symptom_codes=['fail'],probe_code='p',expected_if_true='x',expected_if_false='y');b=build_causal_hypothesis(hypothesis_code='b',cause_class='implementation',symptom_codes=['fail'],probe_code='p',expected_if_true='y',expected_if_false='x');m=build_causal_diagnostic_model(symptom_codes=['fail'],hypotheses=[a,b]);u=apply_probe_outcome(m,probe_code='p',observed_outcome='x',evidence_code='e1');cmp=compare_causal_models(m,u);req(cmp['ok'] and cmp['changed_count']==2,'revision');req(not cmp['root_cause_proven'] and not cmp['diagnostic_executed'],'revision_no_overclaim')
code="import sys;from pathlib import Path;sys.path[:0]=[str(Path(r'%s')),str(Path(r'%s')/'conscious_agent')];import causal_diagnostic_reasoning_foundations,causal_diagnostic_reasoning,causal_diagnostic_reasoning_reliability;print('ok')"%(ROOT,ROOT);p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20);req(p.returncode==0 and 'ok' in p.stdout,'fresh_import')
print(json.dumps({'ok':True,'suite':'v1281.6-8-causal-diagnostic-reasoning-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))

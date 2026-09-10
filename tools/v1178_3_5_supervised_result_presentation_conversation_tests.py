from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from supervised_result_presentation import build_supervised_result_presentation, supervised_result_prompt, MAX_PRESENTATION_BYTES
checks=[]
def req(v): checks.append(bool(v)); assert v
H='a'*64
receipt={'proposal_id':'p1','capability_id':'diagnostics','state':'execution_succeeded','terminal':True,'content_free':True,'terminal_result_digest':H,'supervised_result_digest':'b'*64,'outcome_digest':'c'*64,'elapsed_ms':7,'raw_output':'SECRET'}
p=build_supervised_result_presentation('diagnostics',[receipt])
req(p['authoritative_receipt_present'] and p['state']=='execution_succeeded')
req(p['status_label']=='completed successfully' and not p['execution_invoked'])
req(not p['raw_output_included'] and not p['raw_arguments_included'] and not p['authority_granted'])
req('SECRET' not in json.dumps(p) and len(json.dumps(p).encode())<=MAX_PRESENTATION_BYTES)
req('Do not invent raw output' in supervised_result_prompt(p) and 'current conversation did not execute' in supervised_result_prompt(p))
for state,label in [('execution_failed','failed'),('execution_cancelled','was cancelled'),('execution_timed_out','timed out')]:
 r=dict(receipt,state=state,terminal_result_digest=state.encode().hex().ljust(64,'0')[:64])
 q=build_supervised_result_presentation('diagnostics',[r]); req(q['state']==state and q['status_label']==label)
req(not build_supervised_result_presentation('maintenance',[receipt])['authoritative_receipt_present'])
req(build_supervised_result_presentation('diagnostics',[dict(receipt,terminal=False)])['presentation_status']=='unavailable')
req(build_supervised_result_presentation('diagnostics',[receipt,dict(receipt,proposal_id='p2',terminal_result_digest='d'*64)])['presentation_status']=='ambiguous')
req(build_supervised_result_presentation('diagnostics',[dict(receipt,terminal_result_digest='bad')])['presentation_status']=='unavailable')
runtime=(ROOT/'conscious_agent'/'conversation_runtime.py').read_text(encoding='utf-8')
req(runtime.count('authoritative_action_results: tuple[dict[str, Any], ...] = ()')==2)
req(runtime.count('build_supervised_result_presentation(')==2)
req(runtime.count('supervised_result_prompt(result_presentation)')==2)
req(runtime.count('result.cognitive_context["supervised_result_presentation"] = result_presentation')==2)
req('authoritative_receipts=authoritative_action_results' in runtime)
req('execute_admitted_action' not in runtime)
print(json.dumps({'ok':True,'suite':'v1178.3-v1178.5-supervised-result-presentation-conversation','passed':sum(checks),'total':len(checks)},sort_keys=True))

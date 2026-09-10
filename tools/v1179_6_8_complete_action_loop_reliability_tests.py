from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from action_loop_reliability import *
checks=[]
def req(v): checks.append(bool(v)); assert v
H=lambda c:c*64
base={'proposal_id':'p1','capability_id':'diagnostics','state':'execution_succeeded','proposal_digest':H('a'),'approval_decision_digest':H('b'),'authorization_digest':H('c'),'execution_admission_digest':H('d'),'terminal_result_digest':H('e'),'updated_at':100,'content_free':True,'raw_output':'SECRET','arguments':{'x':'SECRET'}}
r=build_action_loop_reliability([base],now=101)
req(r['reliability_posture']=='reliable' and r['proposal_count']==1)
req(r['terminal_state_counts']['execution_succeeded']==1)
req('SECRET' not in json.dumps(r) and not r['raw_content_exposed'])
req(not r['automatic_retry'] and not r['automatic_approval'] and not r['automatic_authorization'] and not r['execution_invoked'])
# identical replay is bounded and reviewable
rp=build_action_loop_reliability([base,dict(base,updated_at=101)],now=102)
req(rp['replay_duplicate_count']==1 and rp['reliability_posture']=='review_required')
# conflicting terminal evidence blocks
conf=build_action_loop_reliability([base,dict(base,state='execution_failed',terminal_result_digest=H('f'),updated_at=102)],now=103)
req(conf['contradictory_proposal_count']==1 and conf['reliability_posture']=='blocked')
# missing required digests blocks
bad=build_action_loop_reliability([dict(base,authorization_digest='')],now=103)
req(bad['incoherent_proposal_count']==1 and bad['reliability_posture']=='blocked')
# stale in-progress work requires review and never retries
progress=dict(base,state='execution_in_progress',terminal_result_digest='',execution_attempt_digest=H('9'),updated_at=0)
stale=build_action_loop_reliability([progress],now=STALE_IN_PROGRESS_SECONDS+1)
req(stale['stale_in_progress_count']==1 and stale['reliability_posture']=='review_required')
req(not stale['automatic_retry'] and not stale['execution_invoked'])
# cancellation, timeout, failure remain authoritative terminal categories
multi=[dict(base,proposal_id='p2',state='execution_cancelled',terminal_result_digest=H('2')),dict(base,proposal_id='p3',state='execution_timed_out',terminal_result_digest=H('3')),dict(base,proposal_id='p4',state='execution_failed',terminal_result_digest=H('4'))]
m=build_action_loop_reliability(multi,now=200)
req(m['terminal_state_counts']=={'execution_cancelled':1,'execution_failed':1,'execution_timed_out':1})
# malformed and private rows fail closed
mal=build_action_loop_reliability([{'bad':'row'},dict(base,content_free=False)],now=1)
req(mal['malformed_record_count']==2 and mal['accepted_record_count']==0)
# stale follow-up continuity is surfaced, not resumed
fu={'proposal_id':'p1','review_digest':H('7'),'state':'pending','expires_at':10,'raw_request':'SECRET'}
fr=build_action_loop_reliability([base],follow_up_records=[fu],now=11)
req(fr['pending_follow_up_count']==1 and fr['stale_follow_up_count']==1 and fr['reliability_posture']=='review_required')
req('SECRET' not in json.dumps(fr) and not fr['ledger_discovered'])
# long-session input remains bounded
many=[dict(base,proposal_id=f'p{i}',updated_at=i) for i in range(MAX_INPUT_RECORDS+100)]
long=build_action_loop_reliability(many,now=1000)
req(long['input_record_count']==MAX_INPUT_RECORDS and long['public_record_count']==MAX_PUBLIC_RECORDS)
req(long['input_truncated'] and len(json.dumps(long,sort_keys=True,separators=(',',':')).encode())<=MAX_REPORT_BYTES)
# source contract contains no execution or ledger access imports
source=(ROOT/'conscious_agent'/'action_loop_reliability.py').read_text()
req('execute_admitted_action' not in source and 'Path(' not in source and 'open(' not in source)
req('automatic_retry": False' in source and 'ledger_discovered": False' in source)
print(json.dumps({'ok':True,'suite':'v1179.6-v1179.8-complete-action-loop-reliability','passed':sum(checks),'total':len(checks)},sort_keys=True))

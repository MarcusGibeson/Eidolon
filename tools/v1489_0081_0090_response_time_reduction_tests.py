from __future__ import annotations
"""Deterministic Bundle 9 response-time and phase-accounting checks."""
import os,sys,tempfile,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
RUNTIME=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b9-'))
os.environ['EIDOLON_DATA_DIR']=str(RUNTIME); os.environ['PYTHONDONTWRITEBYTECODE']='1'; sys.dont_write_bytecode=True
sys.path.insert(0,str(AGENT))
from conversation_performance_metrics import classify_provider_start,mark_provider_warm,clear_provider_warm_registry,build_conversation_timing_receipt
from conversation_context import build_conversation_prompt,clear_casual_contract_cache,casual_contract_cache_metrics,estimate_tokens
from immediate_conversation_grounding import build_immediate_conversation_grounding
from conversation_sessions import create_conversation_session
import conversation_runtime

PASSED=FAILED=0

def check(name,cond,detail=''):
 global PASSED,FAILED
 if cond: PASSED+=1; print('PASS',name)
 else: FAILED+=1; print('FAIL',name,detail); raise AssertionError(detail or name)

def test_cold_warm_registry():
 clear_provider_warm_registry(); p,e,m='ollama','http://localhost:11434','configured-model'
 check('cold classified separately',classify_provider_start(p,e,m)=='cold')
 mark_provider_warm(p,e,m); check('warm classified separately',classify_provider_start(p,e,m)=='warm')
 check('different model invalidates warm key',classify_provider_start(p,e,m+'-other')=='cold')

def test_phase_receipt():
 r=build_conversation_timing_receipt({'context_build':18,'pre_provider':55,'first_transport_chunk':90,'first_visible_token':102,'provider':180,'total':245},provider_start_kind='warm',prompt_tokens=333)
 check('context phase',r['context_assembly_ms']==18,r)
 check('provider wait separated',r['provider_wait_to_first_transport_ms']==35,r)
 check('stream phase separated',r['stream_to_first_visible_ms']==12,r)
 check('commit phase derived',r['commit_ms']==10,r)
 check('eidolon overhead excludes provider',r['eidolon_overhead_excluding_provider_ms']==65,r)
 check('timing evidence content free',r['content_free'] and not r['contains_prompt'] and not r['contains_response'],r)
 check('receipt carries prompt count only',r['estimated_prompt_tokens']==333 and len(r['receipt_digest'])==64,r)

def _prompt(msg,hist=None,name='Eidolon'):
 return build_conversation_prompt(user_message=msg,self_model={'name':name},desires={},memories=[],project_context='PROJECT_CANARY',goal_context='GOAL_CANARY',task_context='TASK_CANARY',conversation_history=hist or [],cognitive_context='COGNITION_CANARY',context_size=8192,max_tokens=160)

def test_immutable_contract_cache_and_budget():
 clear_casual_contract_cache(); a=_prompt('I finally repaired the old radio.'); before=casual_contract_cache_metrics(); b=_prompt('The tuning knob feels smooth now.'); after=casual_contract_cache_metrics()
 check('fresh prompt stays <=600',a.metrics.estimated_prompt_tokens<=600,a.metrics.to_dict())
 check('immutable casual contract cache hit',after['hits']>=1 and after['size']>=1,(before,after))
 check('operational context omitted','PROJECT_CANARY' not in a.prompt and 'COGNITION_CANARY' not in a.prompt,a.prompt)
 hist=[{'user_message':'I finally repaired the old radio.','assistant_response':'That sounds satisfying.','completion_state':'completed','success':True}]
 c=_prompt('The tuning knob feels smooth now.',hist)
 check('continuity prompt stays <=900',c.metrics.estimated_prompt_tokens<=900,c.metrics.to_dict())
 check('recent continuity retained','old radio' in c.prompt.lower(),c.prompt)
 _=_prompt('A second identity cache probe.',name='Eidolon-Test')
 newer=casual_contract_cache_metrics(); check('identity change gets distinct immutable cache entry',newer['misses']>=2,newer)

def test_truth_critical_grounding_is_fast():
 hist=[{'role':'user','text':'Correction: the synthetic diagnosis was contact dermatitis, and the synthetic medication was Allegra.'}]
 samples=[]; profile=None
 for _ in range(50):
  t=time.perf_counter(); profile=build_immediate_conversation_grounding('What did I just correct?',hist); samples.append((time.perf_counter()-t)*1000)
 check('deterministic grounding attributable',getattr(profile,'deterministic_response','')!='',profile)
 check('deterministic grounding warm comfortably below one second',max(samples)<1000,max(samples))
 check('grounding diagnostic contains no private text','contact dermatitis' not in str(profile.public_summary()).lower(),profile.public_summary())

def test_runtime_single_prompt_build_and_deferred_work():
 class FakeClient:
  calls=0; events=[]
  def __init__(self,*a,**k): self.last_retry_count=0; self.last_metrics={}
  def generate(self,prompt): type(self).calls+=1; type(self).events.append('provider'); return 'That sounds satisfying.'
  def stream(self,prompt): type(self).calls+=1; type(self).events.append('provider'); yield 'That sounds satisfying.'
  def cancel(self): pass
  def close(self): pass
  def __enter__(self): return self
  def __exit__(self,*a): self.close()
 orig_client=conversation_runtime.LocalModelClient; orig_build=conversation_runtime._build_prompt_packet
 build_count={'n':0}
 def wrapped(*a,**k): build_count['n']+=1; return orig_build(*a,**k)
 conversation_runtime.LocalModelClient=FakeClient; conversation_runtime._build_prompt_packet=wrapped
 clear_provider_warm_registry()
 try:
  sid=create_conversation_session(title='performance synthetic',select_session=False)['id']
  res=conversation_runtime.run_conversation_turn('I repaired the old radio.',use_ai=True,session_id=sid,select_session_on_record=False)
  check('runtime provider succeeds',res.success,res.to_dict())
  check('ordinary path assembles provider prompt once',build_count['n']==1,build_count)
  perf=(res.cognitive_context or {}).get('response_performance') or {}
  check('runtime records content-free performance receipt',perf.get('content_free') is True and perf.get('provider_start_kind')=='cold',perf)
  check('runtime prompt token count bounded',0<perf.get('estimated_prompt_tokens',0)<=600,perf)
  sid2=create_conversation_session(title='performance synthetic warm',select_session=False)['id']
  res2=conversation_runtime.run_conversation_turn('I found another old radio.',use_ai=True,session_id=sid2,select_session_on_record=False)
  perf2=(res2.cognitive_context or {}).get('response_performance') or {}
  check('subsequent configured provider start labeled warm',perf2.get('provider_start_kind')=='warm',perf2)
  check('one provider call per accepted turn',FakeClient.calls==2,FakeClient.calls)
 finally:
  conversation_runtime.LocalModelClient=orig_client; conversation_runtime._build_prompt_packet=orig_build

def test_stream_visibility_precedes_nonessential_post_turn_work():
 class FakeClient:
  def __init__(self,*a,**k): self.last_retry_count=0; self.last_metrics={}
  def stream(self,prompt): yield 'Visible '; yield 'reply.'
  def generate(self,prompt): return 'Visible reply.'
  def cancel(self): pass
  def close(self): pass
  def __enter__(self): return self
  def __exit__(self,*a): self.close()
 marks=[]
 orig_client=conversation_runtime.LocalModelClient; orig_queue=conversation_runtime._queue_memory_vectors; orig_house=conversation_runtime._schedule_housekeeping_safely
 conversation_runtime.LocalModelClient=FakeClient
 def queued(*a,**k): marks.append('indexing'); return orig_queue(*a,**k)
 def housed(*a,**k): marks.append('housekeeping'); return orig_house(*a,**k)
 conversation_runtime._queue_memory_vectors=queued; conversation_runtime._schedule_housekeeping_safely=housed
 try:
  sid=create_conversation_session(title='deferred work synthetic',select_session=False)['id']
  gen=conversation_runtime.stream_conversation_turn('The old radio finally works.',use_ai=True,session_id=sid,select_session_on_record=False)
  saw_delta=False
  for event in gen:
   if event.get('event')=='delta':
    saw_delta=True
    check('first visible stream precedes indexing and housekeeping',not marks,marks)
    break
  check('stream emitted visible text',saw_delta)
  for _ in gen: pass
  check('nonessential post-turn work runs after visible output','indexing' in marks and 'housekeeping' in marks,marks)
 finally:
  conversation_runtime.LocalModelClient=orig_client; conversation_runtime._queue_memory_vectors=orig_queue; conversation_runtime._schedule_housekeeping_safely=orig_house

def test_repeatable_content_free_benchmark_shape():
 clear_provider_warm_registry(); rows=[]
 for label,total,provider in [('cold',210,150),('warm',95,65),('long_session',130,85),('restart',205,145)]:
  clear_provider_warm_registry() if label in {'cold','restart'} else None
  start=classify_provider_start('ollama','http://localhost:11434','synthetic')
  rows.append((label,build_conversation_timing_receipt({'pre_provider':25,'provider':provider,'total':total},provider_start_kind=start,prompt_tokens=420)))
  mark_provider_warm('ollama','http://localhost:11434','synthetic')
 check('benchmark profiles are content-free',all(r['content_free'] and len(r['receipt_digest'])==64 for _,r in rows),rows)
 check('private benchmark scenario labels stay outside receipts',all(label not in str(r) for label,r in rows if label not in {'cold','warm'}),rows)

try:
 test_cold_warm_registry(); test_phase_receipt(); test_immutable_contract_cache_and_budget(); test_truth_critical_grounding_is_fast(); test_runtime_single_prompt_build_and_deferred_work(); test_stream_visibility_precedes_nonessential_post_turn_work(); test_repeatable_content_free_benchmark_shape()
finally:
 shutil.rmtree(RUNTIME,ignore_errors=True)
print(f'SUMMARY passed={PASSED} failed={FAILED}')
raise SystemExit(1 if FAILED else 0)

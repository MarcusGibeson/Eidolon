from __future__ import annotations
"""Deterministic Bundle 10 provider-reliability tests using synthetic adapters only."""
import importlib,os,shutil,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
RUNTIME=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b10-'))
os.environ['EIDOLON_DATA_DIR']=str(RUNTIME); os.environ['PYTHONDONTWRITEBYTECODE']='1'; sys.dont_write_bytecode=True
sys.path.insert(0,str(AGENT))
from local_model import (
 LocalModelClient,LocalModelConfig,UnavailableServiceError,MissingModelError,LocalModelTimeoutError,
 LocalModelCancelledError,MalformedResponseError,EmptyResponseError,InterruptedStreamError,InvalidConfigurationError,
)
from provider_reliability_contract import validate_configured_provider,classify_provider_failure,provider_recovery_guidance,public_provider_failure,provider_recovery_operation_projection
from conversation_sessions import create_conversation_session,save_conversation_draft,load_conversation_draft
import settings_manager,conversation_runtime

PASSED=FAILED=0
def check(name,cond,detail=''):
 global PASSED,FAILED
 if cond: PASSED+=1; print('PASS',name)
 else: FAILED+=1; print('FAIL',name,detail); raise AssertionError(detail or name)

def test_validate_configuration_without_mutation():
 settings=settings_manager.load_settings(); settings.update({'local_model_provider':'ollama','local_model_endpoint':'http://127.0.0.1:45555','local_model':'synthetic-model'})
 before=dict(settings); p=validate_configured_provider(settings)
 check('configured provider validates without mutation',p.valid and settings==before,p.public_summary())
 check('configuration projection content-free',p.content_free and len(p.endpoint_identity_digest)==24 and len(p.model_identity_digest)==24,p.public_summary())
 check('validation never manages models',not p.configuration_mutated and not p.model_management_attempted,p.public_summary())

def test_failure_categories_and_guidance():
 cases=[
  (UnavailableServiceError('private unreachable'),'unavailable_service'),(MissingModelError('private missing'),'missing_model'),
  (LocalModelTimeoutError('private timeout'),'timeout'),(LocalModelCancelledError('private cancel'),'cancelled'),
  (MalformedResponseError('private malformed'),'malformed_response'),(EmptyResponseError('private empty'),'empty_response'),
  (InterruptedStreamError('private disconnect'),'interrupted_stream'),(InvalidConfigurationError('private config'),'invalid_configuration'),
 ]
 for error,expected in cases:
  check('classified '+expected,classify_provider_failure(error)==expected,classify_provider_failure(error))
  g=provider_recovery_guidance(error); check('no automatic replay '+expected,g['automatic_generation_replay_allowed'] is False,g)
  check('draft preservation '+expected,g['preserve_draft'] is True,g)

def test_public_error_redaction():
 secret='PRIVATE_PROMPT_PAYLOAD_SENTINEL'
 e=MalformedResponseError(secret,provider='ollama',endpoint='http://localhost:11434',model='synthetic',details={'line':secret,'response':secret,'failure_kind':'bad_chunk'})
 row=public_provider_failure(e)
 check('public provider error excludes raw payload',secret not in str(row),row)
 check('public provider error declares redaction',row['safe_error'].get('redacted') is True,row)
 check('public provider error content-free flags',row['content_free'] and not row['contains_prompt'] and not row['contains_response'] and not row['contains_provider_payload'],row)

def test_draft_and_operation_identity_survive_loss():
 session=create_conversation_session(title='provider loss synthetic',select_session=False); sid=session['id']; text='Synthetic unsent draft sentinel.'
 save_conversation_draft(sid,text,source='bundle10_test')
 marker={'operation_id':'op-synthetic-1','session_id':sid,'acceptance_key':'private-acceptance-key','public_state':'running','client_disconnected':True}
 row=provider_recovery_operation_projection(marker,InterruptedStreamError('private disconnect'))
 check('provider loss keeps operation identity',row['operation_id']=='op-synthetic-1' and row['session_id']==sid,row)
 check('provider loss cannot auto reexecute',row['automatic_reexecution_allowed'] is False,row)
 check('provider loss requires reconciliation',row['operation_recovery_mode']=='reconcile_only',row)
 check('provider loss projection hides acceptance key','private-acceptance-key' not in str(row),row)
 check('provider diagnostics do not mutate saved draft',load_conversation_draft(sid).get('content')==text,load_conversation_draft(sid))

def test_stream_chunk_hardening():
 class GoodProvider:
  calls=0
  def stream(self,prompt,cancel_event=None):
   type(self).calls+=1; yield ''; yield None; time.sleep(.002); yield 'usable text'
  def cancel(self): pass
  def close(self): pass
 class BadProvider:
  calls=0
  def stream(self,prompt,cancel_event=None):
   type(self).calls+=1; yield {'not':'text'}
  def cancel(self): pass
  def close(self): pass
 cfg=LocalModelConfig(provider='ollama',endpoint='http://localhost:11434',model='synthetic')
 c=LocalModelClient(cfg); c.provider=GoodProvider(); out=list(c.stream('synthetic prompt'))
 check('empty chunks ignored and delayed valid chunk retained',out==['usable text'],out)
 check('stream is not replayed',GoodProvider.calls==1,GoodProvider.calls)
 c2=LocalModelClient(cfg); c2.provider=BadProvider()
 try: list(c2.stream('synthetic prompt')); raised=False
 except MalformedResponseError as e: raised=True; check('malformed chunk safe category',e.code=='malformed_response',e.to_safe_dict())
 check('malformed yielded chunk fails closed',raised)
 check('malformed stream is not replayed',BadProvider.calls==1,BadProvider.calls)

def test_settings_survive_restart_and_navigation_read():
 settings=settings_manager.load_settings(); settings['local_model_provider']='ollama'; settings['local_model_endpoint']='http://127.0.0.1:45555'; settings['local_model']='synthetic-model'; settings_manager.save_settings(settings)
 first=settings_manager.load_settings(); importlib.reload(settings_manager); second=settings_manager.load_settings()
 check('provider settings survive module restart',(second['local_model_provider'],second['local_model_endpoint'],second['local_model'])==('ollama','http://127.0.0.1:45555','synthetic-model'),second)
 # A content-free validation/navigation read must not rewrite the values.
 _=validate_configured_provider(second); third=settings_manager.load_settings()
 check('provider validation read preserves saved selection',third['local_model_endpoint']==first['local_model_endpoint'] and third['local_model']==first['local_model'],third)

def test_runtime_failure_parity_and_no_fallback():
 class FailingClient:
  calls=0
  def __init__(self,*a,**k): self.last_retry_count=0; self.last_metrics={}
  def generate(self,prompt): type(self).calls+=1; raise UnavailableServiceError('PRIVATE_PROVIDER_BODY',provider='ollama',endpoint='http://localhost:11434',model='synthetic')
  def stream(self,prompt): type(self).calls+=1; raise UnavailableServiceError('PRIVATE_PROVIDER_BODY',provider='ollama',endpoint='http://localhost:11434',model='synthetic'); yield ''
  def cancel(self): pass
  def close(self): pass
  def __enter__(self): return self
  def __exit__(self,*a): self.close()
 orig=conversation_runtime.LocalModelClient; conversation_runtime.LocalModelClient=FailingClient
 try:
  sid=create_conversation_session(title='provider failure nonstream',select_session=False)['id']
  r=conversation_runtime.run_conversation_turn('Tell me one ordinary thought.',use_ai=True,session_id=sid,select_session_on_record=False)
  check('nonstream provider outage is explicit',not r.success and r.failure_category=='unavailable_service',r.to_dict())
  rec=(r.cognitive_context or {}).get('provider_recovery') or {}; check('nonstream outage blocks replay/switch',rec.get('automatic_generation_replay_allowed') is False and rec.get('automatic_provider_switch_allowed') is False,rec)
  check('nonstream error hides provider body','PRIVATE_PROVIDER_BODY' not in str(r.to_dict()),r.to_dict())
  sid2=create_conversation_session(title='provider failure stream',select_session=False)['id']; events=list(conversation_runtime.stream_conversation_turn('Tell me one ordinary thought.',use_ai=True,session_id=sid2,select_session_on_record=False))
  err=next(e for e in events if e.get('event')=='error')
  check('stream provider outage category parity',err.get('failure_category')=='unavailable_service',err)
  check('stream error carries content-free recovery',err.get('recovery',{}).get('automatic_generation_replay_allowed') is False,err)
  check('stream error hides provider body','PRIVATE_PROVIDER_BODY' not in str(err),err)
  check('one failed provider call per accepted turn',FailingClient.calls==2,FailingClient.calls)
 finally: conversation_runtime.LocalModelClient=orig

def test_pre_provider_cancellation_contacts_nothing():
 class ProviderMustNotStart:
  calls=0
  def __init__(self,*a,**k): type(self).calls+=1; raise AssertionError('provider instantiated after pre-cancellation')
 orig=conversation_runtime.LocalModelClient; conversation_runtime.LocalModelClient=ProviderMustNotStart
 try:
  cancelled=threading.Event(); cancelled.set()
  sid=create_conversation_session(title='pre-cancel nonstream',select_session=False)['id']
  r=conversation_runtime.run_conversation_turn('Synthetic cancelled turn.',use_ai=True,session_id=sid,select_session_on_record=False,cancel_event=cancelled)
  check('nonstream pre-cancel contacts no provider',not r.success and r.completion_state=='cancelled' and r.provider_request_count==0,r.to_dict())
  sid2=create_conversation_session(title='pre-cancel stream',select_session=False)['id']
  events=list(conversation_runtime.stream_conversation_turn('Synthetic cancelled turn.',use_ai=True,session_id=sid2,select_session_on_record=False,cancel_event=cancelled))
  done=next(e['result'] for e in events if e.get('event')=='done')
  check('stream pre-cancel contacts no provider',done.get('completion_state')=='cancelled' and done.get('provider_request_count')==0,done)
  check('pre-cancel emits no provider request',not any(e.get('event')=='provider_request' for e in events),events)
  check('pre-cancel never instantiates provider',ProviderMustNotStart.calls==0,ProviderMustNotStart.calls)
 finally: conversation_runtime.LocalModelClient=orig

try:
 test_validate_configuration_without_mutation(); test_failure_categories_and_guidance(); test_public_error_redaction(); test_draft_and_operation_identity_survive_loss(); test_stream_chunk_hardening(); test_settings_survive_restart_and_navigation_read(); test_runtime_failure_parity_and_no_fallback(); test_pre_provider_cancellation_contacts_nothing()
finally:
 shutil.rmtree(RUNTIME,ignore_errors=True)
print(f'SUMMARY passed={PASSED} failed={FAILED}')
raise SystemExit(1 if FAILED else 0)

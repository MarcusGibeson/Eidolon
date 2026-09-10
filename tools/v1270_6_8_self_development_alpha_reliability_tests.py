from __future__ import annotations
import json,os,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1270_fixture import prepared_chain,initial_provider
from self_development_alpha import execute_self_development_alpha_candidate
from self_development_alpha_foundations import load_self_development_alpha_campaign,_stage_root,_campaign_path,_record_digest,_write_json
from self_development_alpha_reliability import *
from isolated_self_modification_foundations import source_only_manifest
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1270-rel-') as td:
    b=Path(td);c=prepared_chain(b);cid=c['campaign']['campaign_id']
    req(validate_self_development_alpha_freshness(cid,c['source'],runtime_root=c['runtime'])['ok'],'freshness_current')
    # Concurrent exact candidate authorizations converge through v1265 locking.
    calls=[];results=[];lock=threading.Lock()
    def provider(req):
        with lock:calls.append(dict(req))
        return {'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'}]}
    def worker():results.append(execute_self_development_alpha_candidate(cid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=provider))
    threads=[threading.Thread(target=worker) for _ in range(4)]
    [t.start() for t in threads];[t.join() for t in threads]
    req(len(calls)==1,'concurrent_provider_exactly_once');req(all(r.get('phase')=='repair_authorization_required' for r in results),'concurrent_convergence')
    req(source_only_manifest(c['source'])['source_manifest_digest']==c['before'],'concurrency_source_immutable')
with tempfile.TemporaryDirectory(prefix='eidolon-v1270-stale-') as td:
    b=Path(td);c=prepared_chain(b);cid=c['campaign']['campaign_id'];(c['source']/'README_NEXT_STEPS.md').write_text('changed\n',encoding='utf-8')
    req(not validate_self_development_alpha_freshness(cid,c['source'],runtime_root=c['runtime'])['ok'],'stale_source_detected')

with tempfile.TemporaryDirectory(prefix='eidolon-v1270-tamper-') as td:
    b=Path(td);c=prepared_chain(b);cid=c['campaign']['campaign_id'];path=_campaign_path(cid,c['runtime']);row=load_self_development_alpha_campaign(cid,runtime_root=c['runtime']);row['selected_objective_code']='tampered_objective';row['record_digest']=_record_digest(row);_write_json(path,row);fresh=validate_self_development_alpha_freshness(cid,c['source'],runtime_root=c['runtime']);req(not fresh['ok'],'resealed_lineage_tamper_detected');req(fresh['lineage_valid'] is False,'lineage_binding_checked')
with tempfile.TemporaryDirectory(prefix='eidolon-v1270-cancel-') as td:
    b=Path(td);c=prepared_chain(b);cid=c['campaign']['campaign_id'];cancel=cancel_self_development_alpha_campaign(cid,runtime_root=c['runtime']);req(cancel['phase']=='cancelled','cancelled');req(cancel['active_source_modified'] is False,'cancel_no_source_mutation');req(source_only_manifest(c['source'])['source_manifest_digest']==c['before'],'cancel_source_immutable')
with tempfile.TemporaryDirectory(prefix='eidolon-v1270-long-'+'x'*80) as td:
    b=Path(td);c=prepared_chain(b);req(validate_self_development_alpha_freshness(c['campaign']['campaign_id'],c['source'],runtime_root=c['runtime'])['ok'],'long_path_supported')
health=inspect_self_development_alpha_health(source_root=ROOT);req(health['ok'],'health_ready');handoff=build_self_development_alpha_operator_handoff(source_root=ROOT);req(handoff['ok'],'operator_handoff_ready');req('v1269_update_requires_fresh_preflight_and_exact_authorization' in handoff['authority_boundaries'],'v1269_boundary_explicit')
print(json.dumps({'ok':True,'suite':'v1270.6-v1270.8-self-development-alpha-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))

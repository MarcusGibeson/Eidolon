from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1249-test-data-')
from feature_freeze_final_hardening import *
from conscious_agent.api_server import dispatch_api
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from natural_language_action_routing import build_natural_language_action_projection
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest(); checks=[]; ck=lambda v:checks.append(bool(v))
for change_class in ALLOWED_CHANGE_CLASSES:
    row=classify_freeze_change(change_class=change_class,affected_surface_digests=[h('surface')],evidence_digest=h('evidence'),rationale_digest=h('rationale'))
    for v in (row['ok'],row['allowed_change_class'],not row['blocked_change_class'],row['separate_work_eligible'],not row['mutation_performed'],bool(row['change_request_digest'])):ck(v)
    for decision in REVIEW_DECISIONS:
        rev=review_freeze_change(change_request=row,decision=decision,expected_change_request_digest=row['change_request_digest'])
        for v in (rev['ok'],rev['decision']==decision,rev['exact_digest_match'],rev['accepted_for_separate_work'] is (decision=='accept_for_separate_work'),not rev['source_change_performed'],not rev['release_decision_created']):ck(v)
for change_class in BLOCKED_CHANGE_CLASSES:
    row=classify_freeze_change(change_class=change_class,affected_surface_digests=[h('surface')],evidence_digest=h('evidence'),rationale_digest=h('rationale'))
    for v in (row['ok'],not row['allowed_change_class'],row['blocked_change_class'],not row['separate_work_eligible'],row['status']=='freeze_change_blocked'):ck(v)
    rev=review_freeze_change(change_request=row,decision='accept_for_separate_work',expected_change_request_digest=row['change_request_digest'])
    for v in (rev['ok'],not rev['accepted_for_separate_work'],not rev['source_change_performed']):ck(v)
valid=classify_freeze_change(change_class='defect_correction',affected_surface_digests=[h('a')],evidence_digest=h('b'),rationale_digest=h('c'))
for bad in ('',h('wrong')):
    rev=review_freeze_change(change_request=valid,decision='accept_for_separate_work',expected_change_request_digest=bad)
    for v in (not rev['ok'],not rev['exact_digest_match'],not rev['accepted_for_separate_work']):ck(v)
for text in ('show feature freeze registry','show feature freeze manifest','show feature freeze and final hardening report'):
    out=process_ordinary_chat_development_turn(text,action_projection=build_natural_language_action_projection(text),runtime_root=tempfile.mkdtemp())
    for v in (out['active'],'feature_freeze_final_hardening' in out,not out['action_taken'],not out['authority_granted']):ck(v)
for route in ('feature-freeze-registry','feature-freeze-manifest','feature-freeze-final-hardening-report','feature-freeze-final-hardening-checkpoint'):
    status,payload=dispatch_api('GET','/api/cognition/'+route); ck(status==200);ck(payload.get('ok') is True);ck((payload.get('data') or {}).get('authority_granted') is False)
    pstatus,_=dispatch_api('POST','/api/cognition/'+route,body={});ck(pstatus in {404,405})
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
q=subprocess.run([sys.executable,str(R/'eidolon.py'),'feature-freeze-registry'],cwd=R,capture_output=True,text=True,timeout=180,env=env)
ck(q.returncode==0);data=json.loads(q.stdout);ck(data.get('authority_granted') is False);ck(data.get('ok') is True)
cli_text=(R/'eidolon.py').read_text(encoding='utf-8')
for command in ('feature-freeze-registry','feature-freeze-manifest','feature-freeze-final-hardening-report','feature-freeze-final-hardening-checkpoint'):ck(f'"{command}"' in cli_text)
page=render_feature_freeze_dashboard_html();dash=feature_freeze_dashboard_record()
for v in (MILESTONE_NAME in page,'GET-only' in page,dash['get_only'],dash['safe_next_action']=='operator_inspection_only',not dash['release_authorized']):ck(v)
for key,expected in AUTHORITY_FLAGS.items():ck(valid.get(key) is expected)
result={'ok':all(checks),'passed':sum(checks),'total':len(checks)};print(json.dumps(result,sort_keys=True));sys.stdout.flush();sys.stderr.flush();os._exit(0 if result['ok'] else 1)

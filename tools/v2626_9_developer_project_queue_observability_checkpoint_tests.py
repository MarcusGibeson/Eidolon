from pathlib import Path
from tempfile import TemporaryDirectory
import json
from conscious_agent.developer_project_queue_mind_v2626 import build_developer_project_queue_mind_observability
from conscious_agent.api_server import handle_api_get
from conscious_agent import dashboard


def run():
    checks=[]
    with TemporaryDirectory() as td:
        root=Path(td)
        (root/'developer_project_queue.json').write_text(json.dumps({'entries':[{'project_id':'p1','project_digest':'a'*64,'status':'selected','operator_priority':1.0}], 'queue_digest':'q'*64,'queue_persisted':True}),encoding='utf-8')
        (root/'developer_project_queue_readiness.json').write_text(json.dumps({'projects':[{'project_id':'p1','status':'selected','ready':True,'missing_dependencies':[],'blocker_count':0,'operator_priority':1.0}], 'ready_project_ids':['p1'],'next_ready_project_id':'p1','readiness_digest':'r'*64}),encoding='utf-8')
        x=build_developer_project_queue_mind_observability(root)
        checks += [x['state']=='ready_for_operator_review',x['entry_count']==1,x['ready_count']==1,x['project_content_stored'] is False,x['authority_granted'] is False]
    status,payload=handle_api_get('/api/cognition/observability/project-queue')
    checks += [status==200,(payload.get('data') or payload).get('contract_version')=='v2626.0']
    html=dashboard.render_cognitive_observability_dashboard()
    checks += ['Project queue' in html,'mind-project-queue-state' in html,'/api/cognition/observability/project-queue' in html,'automatic project start' in html.lower()]
    print(f'passed={sum(bool(x) for x in checks)}/{len(checks)}')
    if not all(checks):raise SystemExit(1)

if __name__=='__main__':run()

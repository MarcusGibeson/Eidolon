from __future__ import annotations
import os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1194-5-data-'))
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.unified_cognitive_developer_coordination_checkpoint import build_unified_cognitive_developer_coordination_checkpoint
checks=[]
def req(x):checks.append(bool(x));assert x
with tempfile.TemporaryDirectory(prefix='eidolon-v1194-5-') as t:r=build_unified_cognitive_developer_coordination_checkpoint(source_root=ROOT,runtime_root=Path(t)/'runtime')
for k,v in [('ok',True),('contract_version','v1194.5'),('read_only',True),('post_available',False),('content_free',True),('source_unchanged',True),('runtime_mutated',False),('production_source_modified',False),('approval_created',False),('approval_consumed',False),('execution_invoked',False),('provider_contacted',False),('model_contacted',False),('thread_started',False),('process_started',False),('authority_granted',False)]:req(r.get(k)==v)
req(r['passed']==r['total']);req(r['total']>=70);req(len(r['limitations'])==5)
s=r['summary']
for k,v in [('status','navigation_ready'),('decision','approve'),('from_domain','conversation'),('presented_domain','campaign'),('focus_changed',True),('accountable_transition',True),('content_free',True),('foreground_path_available',True),('original_evidence_preserved',True),('inherited_debt_visible',True),('execution_invoked',False),('runtime_mutated',False),('authority_granted',False),('domain_count',9),('decision_count',3),('global_profile_pass_claimed',False)]:req(s.get(k)==v)
for name in ('stale-snapshot','stale-context','private-field','hidden-execution','automatic-continuation','authority','foreground-block','evidence-loss','global-pass','tamper'):req(name in r['blocked_cases']);req(bool(r['blocked_cases'][name]))
reg=inspect_checkpoint_registry(source_root=ROOT);d=next(x for x in reg['checkpoints'] if x['checkpoint_id']=='unified-cognitive-developer-coordination-checkpoint');req(d['contract_version']=='v1194.5');req(d['builder']=='build_unified_cognitive_developer_coordination_checkpoint');req(reg['duplicate_checkpoint_ids']==[])
status,payload=dispatch_api('GET','/api/cognition/unified-cognitive-developer-coordination-checkpoint',{},None);req(status==200);req(payload['data']['ok'] is True);req(payload['data']['summary']['decision_count']==3)
status,payload=dispatch_api('POST','/api/cognition/unified-cognitive-developer-coordination-checkpoint',{},{});req(status in {404,405});req(payload.get('ok') is False)
html=render_first_use_shell();req('unified-cognitive-developer-coordination-panel' in html);req('/api/cognition/unified-cognitive-developer-coordination-checkpoint' in html);req('v1194.6-v1194.8' in html)
for p in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md','conscious_agent/release_metadata.py','tools/release_verify.py'):
 text=(ROOT/p).read_text(encoding='utf-8');req('v1194.3-v1194.5' in text or 'v1194_3_5' in text);req('v1194.6-v1194.8' in text)
print(f'v1194.3-v1194.5 operator coordination navigation: {sum(checks)}/{len(checks)} PASS')

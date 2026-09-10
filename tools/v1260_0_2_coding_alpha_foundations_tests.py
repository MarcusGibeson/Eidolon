from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.dont_write_bytecode=True; os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from coding_alpha_checkpoint_foundations import DENIED_AUTHORITY,build_coding_alpha_contract,public_coding_alpha_contract
from conversational_command_integration_foundations import classify_conversational_command_turn
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def sig():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():
            r=p.relative_to(ROOT).as_posix()
            if r.startswith('data/') or '__pycache__' in r or r.endswith(('.pyc','.pyo')): continue
            rows.append((r,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before=sig(); c=build_coding_alpha_contract(); pub=public_coding_alpha_contract(c)
req(c['ok'] and c['status']=='coding_alpha_campaign_contract_ready','contract_ready')
req(c['scenario_id']=='calculator_webpage_supervised_end_to_end','canonical_scenario_exact')
req(c['stage_count']==13 and len(c['stages'])==13,'thirteen_stage_chain_defined')
req(len({x['stage'] for x in c['stages']})==13,'stage_names_unique')
req(all(len(x['stage_digest'])==64 for x in c['stages']),'stage_digests_complete')
req(set(c['required_behaviors'])=={'add','subtract','multiply','divide','clear'},'calculator_behaviors_complete')
req(len(c['scenario_artifacts'])==6,'multi_file_artifact_set_exact')
req(len(c['quality_dimensions'])==7,'seven_quality_dimensions_required')
req(c['mandatory_failure_repair_evidence'],'repair_evidence_mandatory')
req(c['selected_project_must_remain_unchanged_until_application'],'isolation_mandatory')
req(c['application_and_rollback_require_distinct_exact_authorizations'],'apply_rollback_authority_distinct')
req(c['rollback_must_restore_pre_apply_tree_digest'],'rollback_restoration_exact')
req(c['generic_authorization_must_never_be_consumed'],'generic_authority_forbidden')
req(c['provider_replay_on_resume_forbidden'],'resume_provider_replay_forbidden')
req(c['v1260_creates_no_new_mutation_authority'],'checkpoint_adds_no_authority')
for k,v in DENIED_AUTHORITY.items(): req(c[k] is v,f'{k}_denied')
req(pub['content_minimized'] and not pub['private_paths_exposed'] and not pub['raw_operator_content_exposed'],'public_contract_content_minimized')
req(len(c['contract_digest'])==64,'contract_digest_present')
for text,kind in [('Build me a complete responsive accessible calculator webpage.','action_request'),('What if you built me a calculator webpage?','hypothetical'),('Could you explain how to build a calculator webpage?','information_request'),('Go ahead.','authorization')]:
    row=classify_conversational_command_turn(text); req(row['primary_act']==kind,f'speech_act:{kind}')
req(sig()==before,'foundation_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1260.0-v1260.2-coding-alpha-foundations','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'project_modified':False,'application_authorized':False,'release_authorized':False},indent=2,sort_keys=True))

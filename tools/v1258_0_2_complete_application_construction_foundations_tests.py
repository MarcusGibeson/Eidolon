from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from complete_application_construction_foundations import (
    DENIED_AUTHORITY,
    load_complete_application_construction,
    prepare_complete_application_construction,
    public_complete_application_construction,
)
from isolated_coding_execution_foundations import create_or_restore_coding_work_plan, create_or_restore_coding_work_request, inspect_coding_project, materialize_or_restore_isolated_coding_workspace
from v1258_test_support import make_web_project, prepare_complete_web_request, tree_signature

CHECKS=[]
def require(v,label):
    if not v: raise AssertionError(label)
    CHECKS.append(label)

def source_signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT).as_posix()
        if '__pycache__' in rel or rel.endswith(('.pyc','.pyo')) or rel.startswith('data/'): continue
        rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

SOURCE_BEFORE=source_signature()
with tempfile.TemporaryDirectory(prefix='eid-v1258-0-2-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base); before=tree_signature(project)
    request, contract, execution = prepare_complete_web_request(project,runtime)
    require(contract['status']=='complete_application_construction_contract_ready','construction_contract_ready')
    require(contract['construction_profile']=='web_application','web_application_profile_selected')
    roles={r['role']:r for r in contract['artifact_roles']}
    require({'interface','application_logic','styles','configuration','tests','documentation'} <= set(roles),'all_complete_application_artifact_roles_present')
    require(all(roles[name]['required'] for name in roles),'all_declared_web_roles_required')
    dims=set(contract['required_quality_dimensions'])
    require({'interface_coherence','dependency_coherence','configuration_coherence','test_coverage','documentation_completeness','accessibility','responsive_behavior'} <= dims,'all_required_quality_dimensions_present')
    require(contract['accessibility_policy']['required'] and contract['responsive_policy']['required'],'web_accessibility_and_responsive_required')
    require(contract['dependency_policy']['installation_allowed'] is False and contract['dependency_policy']['network_allowed'] is False,'dependency_and_network_installation_denied')
    require(contract['configuration_policy']['secrets_must_not_be_embedded'],'configuration_secret_boundary_explicit')
    require(contract['relationship_count'] >= 5,'cross_file_relationships_defined')
    relationship_codes={r['obligation'] for r in contract['relationships']}
    require('interface_loads_and_binds_application_logic' in relationship_codes and 'configuration_exposes_bounded_test_command' in relationship_codes,'interface_and_test_configuration_relationships_present')
    require(len(contract['completion_conditions']) >= 5 and len(contract['blocker_conditions']) >= 4,'completion_and_blocker_conditions_bounded')
    for key,expected in DENIED_AUTHORITY.items(): require(contract.get(key) is expected,f'contract_{key}_denied')
    require(tree_signature(project)==before,'foundation_never_modifies_selected_project')
    restored=prepare_complete_application_construction(request['request_id'],runtime_root=runtime,force=True)
    require(restored['construction_contract_digest']==contract['construction_contract_digest'] and restored['operation_status']=='restored','duplicate_construction_request_idempotent')
    loaded=load_complete_application_construction(request['request_id'],runtime_root=runtime)
    require(loaded['construction_contract_digest']==contract['construction_contract_digest'],'sealed_contract_restores_after_restart')
    public=public_complete_application_construction(loaded)
    require(public['private_paths_exposed'] is False and public['raw_source_content_exposed'] is False,'public_contract_content_minimized')
    require(str(project) not in json.dumps(public),'public_contract_contains_no_private_project_path_value')
    require(public['artifact_roles'][0].get('role_digest'),'public_roles_remain_tamper_evident')
    require(execution['implementation_execution_authorized'] is False and execution['source_application_authorized'] is False,'construction_preparation_does_not_grant_v1254_authority')

    # Tamper fails closed.
    path=runtime/'development_campaigns'/'complete_application_construction'/f"{request['request_id']}.json"
    raw=json.loads(path.read_text()); raw['construction_profile']='tampered'; path.write_text(json.dumps(raw))
    invalid=prepare_complete_application_construction(request['request_id'],runtime_root=runtime,force=True)
    require(invalid['ok'] is False and invalid['status']=='complete_application_construction_record_invalid','tampered_contract_fails_closed')

# Stale selected source blocks a new construction contract before any authority.
with tempfile.TemporaryDirectory(prefix='eid-v1258-0-2-stale-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base)
    request=create_or_restore_coding_work_request(user_objective='Build a complete responsive web application.',target_project=project,requirements=['Complete responsive application'],acceptance_criteria=['Complete'],constraints=[],prohibited_actions=['No selected project mutation'],expected_artifacts=['Complete web application'],verification=['Bounded verification'],runtime_root=runtime)
    require(inspect_coding_project(request['request_id'],runtime_root=runtime)['ok'],'stale_fixture_inspected')
    require(create_or_restore_coding_work_plan(request['request_id'],runtime_root=runtime)['ok'],'stale_fixture_planned')
    require(materialize_or_restore_isolated_coding_workspace(request['request_id'],runtime_root=runtime)['ok'],'stale_fixture_workspace_created')
    (project/'index.html').write_text('<!doctype html><p>operator changed</p>',encoding='utf-8')
    stale=prepare_complete_application_construction(request['request_id'],runtime_root=runtime,force=True)
    require(stale['ok'] is False and stale['status']=='complete_application_construction_stale_source','stale_source_blocks_construction_preparation')
    require(stale['provider_contact_authorized'] is False and stale['application_authorized'] is False,'stale_failure_grants_no_authority')

# Non-complete ordinary request is not silently escalated into the v1258 contract.
with tempfile.TemporaryDirectory(prefix='eid-v1258-0-2-notrequired-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base)
    request=create_or_restore_coding_work_request(user_objective='Change the page title.',target_project=project,requirements=['Change title'],acceptance_criteria=['Title changed'],constraints=[],prohibited_actions=[],expected_artifacts=['Reviewable diff'],verification=['Static syntax'],runtime_root=runtime)
    require(inspect_coding_project(request['request_id'],runtime_root=runtime)['ok'],'narrow_fixture_inspected')
    require(create_or_restore_coding_work_plan(request['request_id'],runtime_root=runtime)['ok'],'narrow_fixture_planned')
    narrow=prepare_complete_application_construction(request['request_id'],runtime_root=runtime,force=False)
    require(narrow['ok'] is False and narrow['status']=='complete_application_construction_not_required','narrow_request_not_escalated_to_complete_app_contract')

require(source_signature()==SOURCE_BEFORE,'foundation_suite_preserves_eidolon_source')
print(json.dumps({'ok':True,'suite':'v1258.0-v1258.2-complete-application-construction-foundations','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'selected_project_modified':False,'application_authorized':False,'release_authorized':False},indent=2,sort_keys=True))

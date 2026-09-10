from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
from mindful_execution_alpha_integration_benchmark import build_mindful_execution_alpha_contract, RETAINED_CHECKPOINTS, AUTHORITY_FLAGS
checks=[]
def check(v): checks.append(bool(v))
report=build_mindful_execution_alpha_contract(source_root=ROOT)
for value in (
    report.get('ok'), report.get('status')=='mindful_execution_alpha_contract_ready',
    report.get('contract_version')=='v1230.8', report.get('milestone_name')=='Mindful Execution Alpha',
    report.get('roadmap_path')=='Balanced Mind-and-Action Path 3', report.get('stage_count')==5,
    report.get('complete_stage_order') is True, report.get('retained_versions_match') is True,
    report.get('retained_checkpoints_pass') is True, report.get('ordinary_chat_required') is True,
    report.get('restart_recovery_required') is True, report.get('adversarial_authority_testing_required') is True,
    report.get('goal_alignment_preserved') is True, report.get('uncertainty_preserved') is True,
    report.get('operator_intervention_preserved') is True, report.get('outcome_reflection_preserved') is True,
    report.get('learning_revisable') is True, report.get('historical_receipts_remain_authoritative') is True,
    report.get('runtime_data_read') is False, report.get('runtime_data_written') is False,
    report.get('source_modified') is False, report.get('content_free') is True, report.get('read_only') is True,
): check(value)
for key,expected in AUTHORITY_FLAGS.items(): check(report.get(key) is expected)
for row,retained in zip(report.get('stages',[]),RETAINED_CHECKPOINTS):
    for value in (
        row.get('stage_id')==retained[0], row.get('expected_contract_version')==retained[1],
        row.get('checkpoint_id')==retained[2], row.get('reported_contract_version')==retained[1],
        row.get('ok') is True, row.get('read_only') is True, row.get('content_free') is True,
        row.get('runtime_data_read') is False, row.get('source_modified') is False,
        row.get('authority_granted') is False, row.get('provider_contacted') is False,
        row.get('commands_executed') is False, row.get('tests_executed') is False,
        row.get('project_modified') is False, row.get('cognition_written') is False,
        int(row.get('passed_checks') or 0)>0,
    ): check(value)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)

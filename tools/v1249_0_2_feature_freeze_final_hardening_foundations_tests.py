from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from feature_freeze_final_hardening import *
checks=[]; ck=lambda v:checks.append(bool(v))
reg=feature_freeze_registry(); manifest=build_feature_freeze_manifest(source_root=R); report=build_final_hardening_report(source_root=R)
for v in (reg['ok'],reg['domain_count']==12,len(reg['domains'])==12,reg['feature_freeze_active'],reg['new_capability_work_blocked'],reg['corrections_require_separate_governed_work'],len(reg['allowed_change_classes'])==5,len(reg['blocked_change_classes'])==5,len(reg['review_decisions'])==4,manifest['ok'],manifest['public_interfaces_frozen'],manifest['stable_surface_count']==manifest['surface_count'],manifest['required_release_stages_present']==manifest['required_release_stage_count']==4,manifest['source_file_count']>3000,manifest['python_file_count']>2500,bool(manifest['inventory_digest']),report['ok'],report['passed']==report['total'],report['syntax_failure_count']==0,report['forbidden_source_entry_count']==0,report['retained_checkpoint_present_count']==report['retained_checkpoint_required_count']==19):ck(v)
for row in reg['domains']:
    for v in (row['frozen'],row['content_free'],bool(row['domain_digest'])):ck(v)
for row in manifest['surfaces']:
    for v in (row['exists'],row['stable'],row['required_tokens_present']==row['required_token_count'],bool(row['surface_sha256']),bool(row['surface_digest'])):ck(v)
reg2=feature_freeze_registry(); manifest2=build_feature_freeze_manifest(source_root=R); report2=build_final_hardening_report(source_root=R)
for v in (reg2['registry_digest']==reg['registry_digest'],manifest2['manifest_digest']==manifest['manifest_digest'],report2['hardening_report_digest']==report['hardening_report_digest']):ck(v)
for key,expected in AUTHORITY_FLAGS.items():
    ck(reg.get(key) is expected);ck(manifest.get(key) is expected);ck(report.get(key) is expected)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True));raise SystemExit(0 if all(checks) else 1)

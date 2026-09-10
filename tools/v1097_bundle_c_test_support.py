from __future__ import annotations
import json
from pathlib import Path
import sys
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
for item in (ROOT/'conscious_agent',ROOT/'tools'):
    if str(item) not in sys.path: sys.path.insert(0,str(item))
from v1097_bundle_a_test_support import prepare_promoted_fixture,evidence_payload,write_evidence
from release_certification_evidence import select_certification_evidence,create_certification_readiness_preview
from release_certification_plan import create_certification_plan,preview_certification_authorization
from release_certification_transaction import apply_authorized_certification,CERTIFICATION_APPLY_CONFIRMATION
from release_certification_policy import BUILTIN_POLICY

def prepare_certified_fixture(base:Path)->dict[str,Any]:
    f=prepare_promoted_fixture(base)
    for scope in ('source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'):
        select_certification_evidence(write_evidence(base/'evidence'/f'{scope}.json',evidence_payload(f,scope)),runtime_root=f['handoff_runtime'])
    assert create_certification_readiness_preview(runtime_root=f['handoff_runtime']).get('ok')
    assert create_certification_plan(runtime_root=f['handoff_runtime']).get('ok')
    a=preview_certification_authorization(runtime_root=f['handoff_runtime'])
    out=apply_authorized_certification(a['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime'])
    assert out.get('ok'),out
    return f

def write_policy(path:Path,policy:dict[str,Any]|None=None)->Path:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(policy or BUILTIN_POLICY,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return path

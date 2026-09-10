from __future__ import annotations

"""v1259.9 read-only Conversational Command Integration checkpoint."""

import ast
import hashlib
from pathlib import Path
from typing import Any

try:
    from checkpoint_registry import build_read_only_checkpoint_report, lookup_checkpoint
    from release_authority import WORKING_SOURCE_VERSION
except ImportError:
    from checkpoint_registry import build_read_only_checkpoint_report, lookup_checkpoint  # type: ignore
    from release_authority import WORKING_SOURCE_VERSION  # type: ignore

CONTRACT_VERSION = "v1259.9"
_REQUIRED_SOURCE = (
    "conscious_agent/conversational_command_integration_foundations.py",
    "conscious_agent/conversational_command_integration.py",
    "conscious_agent/conversational_command_integration_reliability.py",
    "conscious_agent/natural_conversation_command_distinction.py",
    "conscious_agent/natural_language_action_routing.py",
    "conscious_agent/ordinary_chat_development_campaign.py",
    "conscious_agent/conversation_runtime.py",
    "tools/v1259_0_2_conversational_command_integration_foundations_tests.py",
    "tools/v1259_3_5_conversational_command_integration_tests.py",
    "tools/v1259_6_8_conversational_command_integration_reliability_tests.py",
    "tools/v1259_9_conversational_command_integration_checkpoint_tests.py",
)

def _root(value=None): return Path(value or Path(__file__).resolve().parents[1]).expanduser().resolve()
def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _literal(path: Path,name: str) -> Any:
    tree=ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    for node in tree.body:
        if isinstance(node,(ast.Assign,ast.AnnAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            if any(isinstance(t,ast.Name) and t.id==name for t in targets):
                try: return ast.literal_eval(node.value)
                except (TypeError,ValueError): return None
    return None

def build_conversational_command_integration_checkpoint(*, source_root=None) -> dict[str, Any]:
    root=_root(source_root); files={rel:root/rel for rel in _REQUIRED_SOURCE}
    foundation=files[_REQUIRED_SOURCE[0]]; integration=files[_REQUIRED_SOURCE[1]]; reliability=files[_REQUIRED_SOURCE[2]]
    runtime=files['conscious_agent/conversation_runtime.py']; ordinary=files['conscious_agent/ordinary_chat_development_campaign.py']
    ft=foundation.read_text(encoding='utf-8') if foundation.is_file() else ''
    it=integration.read_text(encoding='utf-8') if integration.is_file() else ''
    rt=runtime.read_text(encoding='utf-8') if runtime.is_file() else ''
    ot=ordinary.read_text(encoding='utf-8') if ordinary.is_file() else ''
    denied=_literal(foundation,'DENIED_AUTHORITY') if foundation.is_file() else None
    record=lookup_checkpoint('1259.9')
    checks={
        'working_source_at_or_after_v1259_9':tuple(int(part) for part in WORKING_SOURCE_VERSION.split('.')) >= (1259,9),
        'required_v1259_surfaces_present':all(p.is_file() for p in files.values()),
        'foundation_contract_retained':_literal(foundation,'CONTRACT_VERSION')=='v1259.2' if foundation.is_file() else False,
        'integration_contract_retained':_literal(integration,'CONTRACT_VERSION')=='v1259.5' if integration.is_file() else False,
        'reliability_contract_retained':_literal(reliability,'CONTRACT_VERSION')=='v1259.8' if reliability.is_file() else False,
        'authority_defaults_denied':isinstance(denied,dict) and bool(denied) and not any(bool(v) for v in denied.values()),
        'speech_acts_explicit':all(token in ft for token in ('discussion','hypothetical','information_request','action_request','authorization','correction','cancellation')),
        'generic_authorization_never_inferred':all(token in ft+it for token in ('generic_authorization_shape','generic_authorization_blocked','exact_authorization_must_not_be_inferred')),
        'correction_uses_existing_revision_contract':'revise_development_campaign_proposal' in it,
        'cancellation_uses_existing_terminal_contract':'cancel_development_campaign_proposal' in it,
        'conversation_runtime_wired':rt.count('build_conversational_command_integration(')>=4 and rt.count('conversational_command_integration')>=6,
        'ordinary_chat_control_wired':'process_conversational_development_control' in ot,
        'no_parallel_execution_engine':'provider_generate' not in it and 'subprocess' not in it,
        'v1259_9_registered_exactly':bool(record and record.test_selector=='tools/v1259_9_conversational_command_integration_checkpoint_tests.py'),
    }
    hashes={rel:_sha(path) for rel,path in files.items() if path.is_file()}
    return build_read_only_checkpoint_report(
        version='1259.9',status='conversational_command_integration_checkpoint_ready',checks=checks,source_root=root,
        details={
            'required_source_count':len(_REQUIRED_SOURCE),'present_source_count':len(hashes),'source_sha256':hashes,
            'behavioral_evidence':[
                'tools/v1259_0_2_conversational_command_integration_foundations_tests.py',
                'tools/v1259_3_5_conversational_command_integration_tests.py',
                'tools/v1259_6_8_conversational_command_integration_reliability_tests.py',
            ],
            'speech_act_distinction_active':True,
            'mixed_conversation_action_supported':True,
            'information_request_does_not_create_development_proposal':True,
            'generic_authorization_is_not_authority':True,
            'correction_revises_pending_proposal_only':True,
            'cancellation_requires_unique_or_exact_target':True,
            'existing_exact_authority_contracts_preserved':True,
            'provider_contact_authorized':False,'commands_executed':False,'project_mutation_authorized':False,
            'application_authorized':False,'installation_authorized':False,'promotion_authorized':False,
            'certification_authorized':False,'release_authorized':False,'permanent_approval_granted':False,
            'independent_authority_granted':False,'native_windows_multi_process_validation':'desktop_review_required',
        },
    )

__all__=['CONTRACT_VERSION','build_conversational_command_integration_checkpoint']

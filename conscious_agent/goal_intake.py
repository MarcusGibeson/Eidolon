from __future__ import annotations
"""v1304 unified goal intake from chat, issue, and dashboard sources."""
from typing import Any,Mapping
from goal_representation import create_goal
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1304.8';SOURCES=('direct_command','casual_conversation_command','imported_issue','dashboard_action')
def intake_goal(*,source_kind:str,request_text:str,workspace_digest:str='',metadata:Mapping[str,Any]|None=None):
 if source_kind not in SOURCES:raise ValueError('goal_source_invalid')
 text=str(request_text or '').strip();
 if not text:raise ValueError('request_text_required')
 goal=create_goal(outcome=text,workspace_digest=workspace_digest);return {'ok':True,'status':'goal_intake_ready','source_kind':source_kind,'source_digest':digest({'text':text,'metadata':dict(metadata or {})}),'goal':goal,'review_required':True,'action_executed':False,**DENIED_AUTHORITY}
__all__=['CONTRACT_VERSION','SOURCES','intake_goal']

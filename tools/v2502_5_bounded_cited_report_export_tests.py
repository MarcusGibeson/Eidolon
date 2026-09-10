from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

_RUNTIME = tempfile.mkdtemp(prefix='eidolon-v2502-5-runtime-')
os.environ['EIDOLON_DATA_DIR'] = _RUNTIME

from bounded_autonomous_web_research import BoundedResearchSessionStore
from bounded_research_history import build_history_record, render_markdown_export
from conversational_research_actions import conversational_research_export, execute_conversational_research_action, parse_conversational_research_request
import dashboard_chat_console as dashboard

CHECKS=[]
def require(cond,name):
    if not cond: raise AssertionError(name)
    CHECKS.append(name)

sid='research-'+'5'*24; sd='5'*64; rd='d'*64
private_tokens=['Private Objective Delta','SECRET-credential-123','C:\\Users\\operator\\private.txt','raw private page body','provider-private-payload','private search phrase']
report={
 'contract_version':'v2502.5','session_id':sid,'session_digest':sd,'plan_digest':'1'*64,'decomposition_digest':'2'*64,'source_strategy_digest':'3'*64,'status':'research_report_ready','report_digest':rd,
 'objective':private_tokens[0],'query_text':private_tokens[-1],'raw_page_content':private_tokens[3],'credential':private_tokens[1],'provider_payload':private_tokens[4],'private_path':private_tokens[2],
 'claim_assessments':[
   {'claim_code':'rq1','support_state':'supported','supporting_citations':['cite-a','cite-b'],'independent_source_count':2,'independent_evidence_count':2,'duplicate_evidence_count':0,'max_quality':0.95,'max_relevance':0.9},
   {'claim_code':'rq2','support_state':'conflicted','supporting_citations':['cite-a'],'refuting_citations':['cite-c'],'independent_source_count':2,'independent_evidence_count':2,'contradiction_preserved':True},
   {'claim_code':'rq3','support_state':'insufficient_current_evidence','stale_citations':['cite-d'],'independent_source_count':1,'independent_evidence_count':1},
 ],
 'verified_findings':[{'claim_code':'rq1','finding':'Verified public finding','traceable':True,'stance':'support','citations':['cite-a','cite-b']}],
 'reasonable_inferences':[{'claim_code':'rq4','finding':'Bounded inference from one source','traceable':True,'stance':'support','citations':['cite-a']}],
 'unresolved_disagreements':[{'claim_code':'rq2','finding':'Sources disagree materially','traceable':True,'supporting_citations':['cite-a'],'refuting_citations':['cite-c']}],
 'missing_evidence':[{'claim_code':'rq3','finding':'Current evidence missing','traceable':True,'reason':'only stale evidence','citations':['cite-d']}],
 'citations':[
   {'citation_id':'cite-a','public_url':'https://primary.example/report','source_kind':'primary','freshness':'fresh','quality_score':0.95,'relevance_score':0.9,'source_digest':'a'*64},
   {'citation_id':'cite-b','public_url':'https://authority.example/report','source_kind':'official','freshness':'fresh','quality_score':0.9,'relevance_score':0.85,'source_digest':'b'*64},
   {'citation_id':'cite-c','public_url':'https://independent.example/report','source_kind':'secondary','freshness':'fresh','quality_score':0.8,'relevance_score':0.8,'source_digest':'c'*64},
   {'citation_id':'cite-d','public_url':'https://archive.example/report','source_kind':'archive','freshness':'stale','quality_score':0.75,'relevance_score':0.7,'source_digest':'e'*64},
 ],
 'limitations':['Public evidence was bounded by the configured session budget.'],'source_failure_count':1,
 'rendered_answer':'Verified public finding. A bounded inference remains labeled. Sources disagree materially and current evidence is missing.'
}
export=render_markdown_export(sid,report)
require(export['ok'] and export['export_schema_version']=='1','markdown_export_payload_is_created')
markdown=export['markdown']
require('# Eidolon bounded research report' in markdown and 'Verified findings' in markdown,'portable_markdown_contains_report_structure')
require('Inference:' in markdown and 'Unresolved disagreement' in markdown and 'Evidence gaps' in markdown,'export_labels_inference_disagreement_and_gaps')
require('freshness=fresh' in markdown and 'freshness=stale' in markdown and 'Material limitations' in markdown,'export_preserves_freshness_and_limitations')
require(all(token not in markdown for token in private_tokens),'export_excludes_private_objective_queries_pages_credentials_provider_and_paths')
require(export['report_digest']==rd and export['session_id']==sid and re.fullmatch(r'[0-9a-f]{64}',export['export_digest']),'export_binds_session_report_schema_and_digest')
require(export['uploaded'] is False and export['transmitted'] is False,'export_payload_has_no_external_side_effect')

store=BoundedResearchSessionStore()
session={'session_id':sid,'session_digest':sd,'plan_digest':'1'*64,'decomposition_digest':'2'*64,'source_strategy_digest':'3'*64,'state':'completed','created_at':'2026-08-27T20:00:00+00:00','updated_at':'2026-08-27T20:01:00+00:00','completed_at':'2026-08-27T20:01:00+00:00','report_digest':rd,'evidence_count':4,'claim_count':4,'contradiction_count':1,'source_failure_count':1}
state=store._load(); state['sessions']=[session]; store._persist_terminal_history(state,session,report); store._save(state)
phrase=f'Export research session {sid} digest {sd} as Markdown.'
parsed=parse_conversational_research_request(phrase)
require(parsed and parsed['function_name']=='research_report_export','explicit_operator_export_phrase_is_recognized')
first=execute_conversational_research_action('research_report_export',parsed['function_args'],event_id='v2502.5-export',store=store)
require(first['ok'] and first['status']=='bounded_research_report_exported','explicit_operator_action_writes_local_export')
receipt=first['export']; export_path=Path(_RUNTIME)/'research'/'exports'/receipt['file_name']
require(export_path.is_file() and export_path.read_text(encoding='utf-8')==markdown,'local_runtime_export_matches_sanitized_payload')
require(str(export_path) not in json.dumps(first,sort_keys=True),'private_runtime_path_is_not_exposed_in_receipt')
require(receipt['uploaded'] is False and receipt['transmitted'] is False and receipt['private_path_exposed'] is False,'export_receipt_denies_upload_transmission_and_path_exposure')
second=execute_conversational_research_action('research_report_export',parsed['function_args'],event_id='v2502.5-export',store=store)
require(second['ok'] and second['export']['export_digest']==receipt['export_digest'],'repeated_exact_export_event_is_idempotent')
require(len(list(export_path.parent.glob('*.md')))==1,'idempotent_export_does_not_duplicate_files')
projection=conversational_research_export({'function_name':'research_report_export','status':'executed','result':first})
require(projection and projection['export_digest']==receipt['export_digest'],'dashboard_export_projection_is_digest_bound')
require(projection['network_contacted'] is False and projection['private_path_exposed'] is False,'dashboard_export_projection_is_read_only_and_path_private')
html=dashboard._render_research_export({'research_export':projection})
require("data-research-export='true'" in html and receipt['file_name'] in html,'server_dashboard_renders_export_receipt')
require('Nothing was uploaded or transmitted' in html and 'private filesystem paths' in html,'export_ui_states_side_effect_and_privacy_boundary')
source=(Path(__file__).resolve().parents[1]/'conscious_agent'/'dashboard_chat_console.py').read_text(encoding='utf-8')
styles=(Path(__file__).resolve().parents[1]/'conscious_agent'/'dashboard_chat_styles.py').read_text(encoding='utf-8')
require('function renderResearchExport' in source and '.chat-research-export' in styles,'dashboard_has_export_renderer_and_bounded_styles')
rendered=dashboard.render_realtime_chat_panel(None); scripts=re.findall(r'<script[^>]*>(.*?)</script>',rendered,flags=re.S|re.I); node=shutil.which('node')
require(bool(scripts) and bool(node),'rendered_dashboard_script_and_node_available')
with tempfile.TemporaryDirectory(prefix='eidolon-v2502-5-js-') as tmp:
    for idx,script in enumerate(scripts):
        path=Path(tmp)/f'dashboard-{idx}.js'; path.write_text(script,encoding='utf-8')
        proc=subprocess.run([str(node),'--check',str(path)],capture_output=True,text=True,timeout=30)
        require(proc.returncode==0,f'rendered_dashboard_javascript_{idx}_valid')
require(not (Path(__file__).resolve().parents[1]/'data'/'projects.json').exists(),'export_test_writes_no_source_runtime_projects_data')
print(json.dumps({'suite':'v2502.5-bounded-cited-report-export','ok':True,'passed':len(CHECKS),'failed':0,'checks':CHECKS,'network_request_count':0,'uploaded':False,'transmitted':False,'authority_expanded':False,'raw_content_exposed':False},sort_keys=True))

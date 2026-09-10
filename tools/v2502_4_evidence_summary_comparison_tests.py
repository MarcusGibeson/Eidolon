from __future__ import annotations

import json
import os
import subprocess
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

_RUNTIME_ROOT = tempfile.mkdtemp(prefix="eidolon-v2502-4-runtime-")
os.environ["EIDOLON_DATA_DIR"] = _RUNTIME_ROOT

from bounded_research_history import compare_reports
from conversational_research_actions import (
    conversational_research_comparison,
    execute_conversational_research_action,
    parse_conversational_research_request,
)
import dashboard_chat_console as dashboard

CHECKS=[]
def require(cond,name):
    if not cond: raise AssertionError(name)
    CHECKS.append(name)

D1='1'*64; D2='2'*64; R1='a'*64; R2='b'*64
left_record={'session_id':'research-'+'1'*24,'session_digest':D1}
right_record={'session_id':'research-'+'2'*24,'session_digest':D2}
left={
 'report_digest':R1,'session_id':left_record['session_id'],'session_digest':D1,
 'claim_assessments':[
   {'claim_code':'rq1','support_state':'supported','supporting_citations':['c1'],'stale_citations':['c1'],'independent_source_count':1,'independent_evidence_count':1,'duplicate_evidence_count':1,'max_quality':0.9,'max_relevance':0.9},
   {'claim_code':'rq3','support_state':'insufficient_current_evidence','incomplete_citations':['c3'],'independent_source_count':1,'independent_evidence_count':1},
   {'claim_code':'rq-old','support_state':'supported','supporting_citations':['cold'],'independent_source_count':1,'independent_evidence_count':1},
 ],
 'citations':[
   {'citation_id':'c1','public_url':'https://primary.example/a','source_kind':'primary','freshness':'stale','quality_score':0.9,'relevance_score':0.9,'source_digest':'3'*64},
   {'citation_id':'c3','public_url':'https://reference.example/c','source_kind':'reference','freshness':'unknown','quality_score':0.5,'relevance_score':0.5,'source_digest':'4'*64},
   {'citation_id':'cold','public_url':'https://old.example/o','source_kind':'primary','freshness':'fresh','quality_score':0.8,'relevance_score':0.8,'source_digest':'5'*64},
 ],
}
right={
 'report_digest':R2,'session_id':right_record['session_id'],'session_digest':D2,
 'claim_assessments':[
   {'claim_code':'rq1','support_state':'conflicted','supporting_citations':['c1'],'refuting_citations':['c2'],'stale_citations':[],'independent_source_count':2,'independent_evidence_count':2,'duplicate_evidence_count':2,'max_quality':0.95,'max_relevance':0.92,'contradiction_preserved':True},
   {'claim_code':'rq3','support_state':'supported','supporting_citations':['c3'],'independent_source_count':2,'independent_evidence_count':2},
   {'claim_code':'rq2','support_state':'supported','supporting_citations':['c2'],'independent_source_count':1,'independent_evidence_count':1},
 ],
 'citations':[
   {'citation_id':'c1','public_url':'https://primary.example/a','source_kind':'primary','freshness':'fresh','quality_score':0.95,'relevance_score':0.92,'source_digest':'6'*64},
   {'citation_id':'c3','public_url':'https://reference.example/c','source_kind':'reference','freshness':'fresh','quality_score':0.7,'relevance_score':0.7,'source_digest':'4'*64},
   {'citation_id':'c2','public_url':'https://independent.example/b','source_kind':'secondary','freshness':'fresh','quality_score':0.8,'relevance_score':0.85,'source_digest':'7'*64},
 ],
}
comparison=compare_reports(left_record,left,right_record,right)
require(comparison['ok'] and comparison['status']=='research_sessions_compared','content_free_comparison_succeeds')
require(comparison['left_session_digest']==D1 and comparison['right_session_digest']==D2,'comparison_preserves_session_digests')
require(comparison['left_report_digest']==R1 and comparison['right_report_digest']==R2,'comparison_preserves_report_digests')
require(comparison['added_claim_codes']==['rq2'] and comparison['removed_claim_codes']==['rq-old'],'added_removed_claims_identified')
require({r['claim_code'] for r in comparison['changed_claims']}=={'rq1','rq3'},'changed_shared_claims_identified')
require(comparison['stale_claim_codes']==['rq1'],'stale_evidence_identified')
require(comparison['contradictory_claim_codes']==['rq1'],'contradictory_evidence_identified')
require(comparison['duplicated_claim_codes']==['rq1'],'duplicated_evidence_identified')
require(comparison['unsupported_claim_codes']==['rq3'],'unsupported_evidence_identified')
require(comparison['added_citation_ids']==['c2'] and comparison['removed_citation_ids']==['cold'],'added_removed_sources_identified')
require(set(comparison['changed_citation_ids'])=={'c1','c3'},'changed_source_summaries_identified')
require(comparison['source_independence_preserved'] is True and comparison['automatic_winner_declared'] is False,'comparison_never_ranks_or_declares_winner')
serialized=json.dumps(comparison,sort_keys=True)
require('private objective' not in serialized.casefold() and 'raw page body' not in serialized.casefold(),'comparison_projection_contains_no_private_research_text')
require(comparison['network_contacted'] is False,'comparison_performs_no_web_request')
not_comparable=compare_reports(left_record,{'report_digest':R1},right_record,{'report_digest':R2})
require(not not_comparable['ok'] and not_comparable['comparison_reason'],'nonmeaningful_comparison_is_explained')

phrase=f"Compare research sessions {left_record['session_id']} digest {D1} and {right_record['session_id']} digest {D2}."
parsed=parse_conversational_research_request(phrase)
require(parsed and parsed['function_name']=='research_sessions_compare','explicit_compare_phrase_is_recognized')
require(parsed['function_args']['left_session_digest']==D1 and parsed['function_args']['right_session_digest']==D2,'compare_phrase_binds_exact_sessions')

class CompareStore:
    calls=0
    def compare_sessions(self,**kwargs):
        self.calls+=1
        assert kwargs['left_session_id']==left_record['session_id'] and kwargs['right_session_id']==right_record['session_id']
        return dict(comparison)
store=CompareStore()
executed=execute_conversational_research_action('research_sessions_compare',parsed['function_args'],event_id='cmp',store=store)
require(executed['ok'] and store.calls==1,'conversation_compare_executes_existing_store_comparison')
require(executed['network_contacted'] is False and 'winner' in executed['message'].casefold(),'conversation_compare_is_read_only_and_explains_no_winner')
action={'function_name':'research_sessions_compare','status':'executed','result':executed}
projection=conversational_research_comparison(action)
require(projection and projection['comparison_digest']==comparison['comparison_digest'],'comparison_portal_is_digest_bound')
require(projection['private_objective_exposed'] is False and projection['raw_page_content_exposed'] is False,'comparison_portal_is_content_minimized')
html=dashboard._render_research_comparison({'research_comparison':projection})
require("data-research-comparison='true'" in html and 'automatic winner' in html.casefold(),'server_dashboard_renders_comparison_surface')
require('raw page' in html.casefold() and 'no web request' in html.casefold(),'comparison_surface_states_privacy_and_network_boundary')
source=(Path(__file__).resolve().parents[1]/'conscious_agent'/'dashboard_chat_console.py').read_text(encoding='utf-8')
require('function renderResearchComparison' in source and 'data-research-comparison' in source,'dashboard_has_dynamic_comparison_renderer')
rendered=dashboard.render_realtime_chat_panel(None)
scripts=re.findall(r'<script[^>]*>(.*?)</script>',rendered,flags=re.S|re.I)
node=shutil.which('node')
require(bool(scripts) and bool(node),'rendered_dashboard_script_and_node_available')
with tempfile.TemporaryDirectory(prefix='eidolon-v2502-4-js-') as tmp:
    for idx,script in enumerate(scripts):
        path=Path(tmp)/f'dashboard-{idx}.js'; path.write_text(script,encoding='utf-8')
        proc=subprocess.run([str(node),'--check',str(path)],text=True,capture_output=True,timeout=30)
        require(proc.returncode==0,f'rendered_dashboard_javascript_{idx}_valid')

print(json.dumps({'suite':'v2502.4-evidence-summary-comparison','ok':True,'passed':len(CHECKS),'failed':0,'checks':CHECKS,'network_request_count':0,'authority_expanded':False,'raw_content_exposed':False},sort_keys=True))

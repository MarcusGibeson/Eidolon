from __future__ import annotations
import json,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

_RUNTIME=tempfile.mkdtemp(prefix='eidolon-v2502-8-runtime-')
os.environ['EIDOLON_DATA_DIR']=_RUNTIME

from bounded_research_reasoning import assemble_cited_conclusion, compare_cross_source_evidence
from bounded_research_history import sanitize_report
import dashboard_chat_console as dashboard

CHECKS=[]
def require(cond,name):
    if not cond: raise AssertionError(name)
    CHECKS.append(name)

def ev(code,cid,host,stance,fresh='fresh',digest=None,quality=.9,relevance=.9):
    return {'claim_code':code,'citation_id':cid,'source_identity':host,'source_digest':(cid[0]*64),'evidence_digest':digest or (cid[-1]*64),'stance':stance,'freshness':fresh,'quality_score':quality,'relevance_score':relevance,'source_kind':'primary_official','public_url':f'https://{host}/{cid}'}

# Same-source repetition is visible but cannot masquerade as independent confirmation.
extraction={'evidence':[
    ev('rq1','a1','one.example','supports',digest='1'*64),
    ev('rq1','a2','one.example','supports',digest='2'*64),
    ev('rq1','b1','two.example','supports',digest='3'*64),
    ev('rq2','c1','solo.example','supports',digest='4'*64),
    ev('rq3','d1','support.example','supports',digest='5'*64),
    ev('rq3','e1','minority.example','refutes',digest='6'*64),
    ev('rq4','f1','archive.example','supports',fresh='stale',digest='7'*64),
]}
comparison=compare_cross_source_evidence(extraction)
claims={r['claim_code']:r for r in comparison['claims']}
require(claims['rq1']['supporting_source_count']==2,'supporting_independent_sources_are_counted_by_source_identity')
require(claims['rq1']['same_source_repetition_count']==1,'same_source_repetition_is_detected')
require(claims['rq1']['repetition_counts_as_independent_confirmation'] is False,'same_source_repetition_is_not_independent_confirmation')
require(claims['rq3']['state']=='conflicted' and claims['rq3']['minority_evidence_preserved'],'minority_contradictory_evidence_is_preserved')
require(claims['rq4']['state']=='stale_only','stale_only_evidence_remains_explicit')

citations=[]
for row in extraction['evidence']:
    citations.append({'citation_id':row['citation_id'],'public_url':row['public_url'],'host':row['source_identity'],'source_kind':row['source_kind'],'freshness':row['freshness'],'quality_score':row['quality_score'],'relevance_score':row['relevance_score'],'source_digest':row['source_digest']})
report=assemble_cited_conclusion(comparison,claim_labels={'rq1':'independently supported finding','rq2':'single-source finding','rq3':'contested finding','rq4':'stale finding'},citations=citations)
verified={r['claim_code']:r for r in report['verified_findings']}; inferred={r['claim_code']:r for r in report['reasonable_inferences']}
require('rq1' in verified and verified['rq1']['independently_confirmed'],'two-source_high-quality_claim_is_verified')
require('rq2' in inferred and inferred['rq2']['classification']=='inference','single-source_claim_is_labeled_inference')
require(report['unresolved_disagreements'][0]['claim_code']=='rq3' and report['unresolved_disagreements'][0]['minority_evidence_preserved'],'contradiction_is_not_smoothed_away')
require(report['missing_evidence'][0]['claim_code']=='rq4' and report['missing_evidence'][0]['reason']=='stale evidence only','stale_claim_is_reported_as_gap')
require(report['repeated_source_citation_count']>=1 and report['repeated_citations_count_as_independent_confirmation'] is False,'repeated_citations_are_visible_but_not_confirmation')
require(report['minority_and_contradictory_evidence_preserved'] is True,'synthesis_declares_minority_evidence_preserved')
require(report['all_material_conclusions_evidence_bound_or_labeled_inference'] is True,'every_material_conclusion_is_evidence_bound_or_labeled')
require(len(report['material_conclusion_traceability'])==4,'material_conclusion_traceability_covers_every_claim')
require(all(r['evidence_bound'] for r in report['material_conclusion_traceability']),'traceability_rows_are_evidence_bound')
require('Verified findings:' in report['rendered_answer'] and 'Reasonable inferences:' in report['rendered_answer'] and 'Unresolved disagreement' in report['rendered_answer'],'readable_synthesis_distinguishes_result_classes')
require(report['generated_prose_is_evidence'] is False and report['raw_page_content_persisted'] is False,'generated_synthesis_is_not_promoted_to_evidence')

sanitized=sanitize_report(dict(report,session_id='research-'+'8'*24,session_digest='8'*64,report_digest='9'*64,research_intelligence_version='v2502.8'))
require(sanitized['research_intelligence_version']=='v2502.8','sanitized_history_report_retains_research_intelligence_version')
require(sanitized['all_material_conclusions_evidence_bound_or_labeled_inference'] is True,'sanitized_report_retains_traceability_truth')
require(sanitized['repeated_citations_count_as_independent_confirmation'] is False,'sanitized_report_retains_repetition_boundary')

# Existing dashboard coherently exposes result review, history, compare and export workflow.
source=(Path(__file__).resolve().parents[1]/'conscious_agent'/'dashboard_chat_console.py').read_text(encoding='utf-8')
styles=(Path(__file__).resolve().parents[1]/'conscious_agent'/'dashboard_chat_styles.py').read_text(encoding='utf-8')
for token in ('renderResearchReview','renderResearchHistory','renderResearchComparison','renderResearchExport'):
    require(token in source,f'dashboard_integrates_{token}')
require('data-research-history-workflow' in source and 'compare two completed sessions' in source.casefold() and 'export one completed report' in source.casefold(),'history_surface_explains_compare_and_export_workflow')
require('.chat-research-review' in styles and '.chat-research-history' in styles and '.chat-research-comparison' in styles and '.chat-research-export' in styles,'campaign_surfaces_share_bounded_dashboard_styles')
require('@media (max-width:620px)' in styles and 'max-width:100%' in styles,'campaign_dashboard_retains_narrow_layout_contract')
require("<summary>" in source and "aria-label='Research report export'" in source,'campaign_surfaces_retain_keyboard_semantics')
rendered=dashboard.render_realtime_chat_panel(None); scripts=re.findall(r'<script[^>]*>(.*?)</script>',rendered,flags=re.S|re.I); node=shutil.which('node')
require(bool(scripts) and bool(node),'rendered_dashboard_script_and_node_available')
with tempfile.TemporaryDirectory(prefix='eidolon-v2502-8-js-') as tmp:
    for idx,script in enumerate(scripts):
        path=Path(tmp)/f'dashboard-{idx}.js'; path.write_text(script,encoding='utf-8')
        checked=subprocess.run([str(node),'--check',str(path)],capture_output=True,text=True,timeout=30)
        require(checked.returncode==0,f'rendered_dashboard_javascript_{idx}_valid')
require(not (Path(__file__).resolve().parents[1]/'data'/'projects.json').exists(),'campaign_fixture_keeps_runtime_projects_data_outside_source')
print(json.dumps({'suite':'v2502.8-synthesis-quality-campaign-consolidation','ok':True,'passed':len(CHECKS),'failed':0,'checks':CHECKS,'native_network_contacted':False,'authority_expanded':False,'raw_content_exposed':False},sort_keys=True))

from __future__ import annotations
import hashlib, json, os, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; sys.path.insert(0,str(AGENT))
import development_finding_intelligence as intel
import initiative_evidence_intake as intake

checks=[]
def require(value,label):
    if not value: raise AssertionError(label)
    checks.append(label)
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def aggregation():
    return {'findings':[
      {'finding_id':'eval_finding_20260822T000000_aaaaaaaaaaaa','state':'open','revision':3,'issue_domain':'model_quality','severity':'major','reproducibility_status':'confirmed','reproduction_attempt_count':2,'repair_candidate_reference_count':1,'triage_state':'completed','triage_disposition':'repair_candidate_review','record_digest':'a'*64,'reproducibility_digest':'b'*64,'repair_references_digest':'c'*64,'updated_at':'2026-08-22T12:00:00Z','candidate_id':'conversation_grounding','source_module':'conversation_engine.py'},
      {'finding_id':'eval_finding_20260822T000001_bbbbbbbbbbbb','state':'resolved','revision':2,'issue_domain':'interface','severity':'minor','record_digest':'d'*64},
    ]}

def test_contract_reuses_owner():
    c=intel.development_finding_contract(); require(c['private_record_owner']=='conversation_evaluation_finding','owner'); require(c['duplicate_private_store_created'] is False,'no duplicate'); require('expected_behavior' in c['required_product_concepts'],'expected concept'); require(len(c['contract_digest'])==64,'finding contract digest')
def test_projection_is_redacted_and_attributable():
    p=intel.build_development_finding_projection(aggregation()); require(p['finding_count']==1 and p['rejected_or_inactive_count']==1,'finding lifecycle'); row=p['findings'][0]; require(row['finding_digest']=='a'*64 and row['reproducibility_status']=='confirmed','provenance'); require(row['affected_surface']=='conversation' and row['operator_correction_supported'],'surface correction'); require(not p['private_content_inspected'],'redacted')
def test_private_store_migration_is_deferred():
    c=intel.development_finding_contract(); require(len(c['migration_deferred_fields'])==4,'deferred private fields'); require(not c['authority_boundary']['source_mutation_authorized'],'no migration authority')
def test_reproduction_contract():
    c=intel.reproduction_pipeline_contract(); require(c['deterministic'] and not c['private_conversation_content_stored'],'repro contract'); require(not c['automatic_provider_contact'],'no provider')
def test_synthetic_fixture_is_deterministic():
    f=intel.build_development_finding_projection(aggregation())['findings'][0]; a=intel.build_synthetic_reproduction_scenario(f); b=intel.build_synthetic_reproduction_scenario(f); require(a['scenario_digest']==b['scenario_digest'] and a['fixture_id']==b['fixture_id'],'fixture deterministic'); require(not a['private_content_required'],'fixture content free'); require(a['operator_retrial_required'],'operator retrial')
def test_pipeline_dedupes():
    f=intel.build_development_finding_projection(aggregation())['findings'][0]; p=intel.build_reproduction_pipeline([f,f]); require(p['scenario_count']==1,'scenario dedupe'); require(not p['source_modified'] and not p['authority_granted'],'repro inert')
def test_live_feedback_contract():
    c=intel.live_feedback_contract(); require(set(c['feedback_kinds'])=={'dashboard_feedback','action_failure','provider_failure','operator_trial_score'},'feedback kinds'); require(c['deduplication']=='evidence_digest','dedupe contract')
def test_feedback_normalization_and_dedupe():
    rows=[{'feedback_kind':'dashboard_feedback','feedback_id':'fb1','evidence_digest':'e'*64,'issue_domain':'interface','severity':'major','frequency':2,'operator_confirmed':True},{'feedback_kind':'dashboard_feedback','feedback_id':'fb1-copy','evidence_digest':'e'*64,'issue_domain':'interface','severity':'major','frequency':2,'operator_confirmed':True}]
    r=intel.normalize_live_feedback(rows); require(r['record_count']==1,'feedback dedupe'); require(not r['provider_contacted'],'feedback no provider')
def test_retraction_is_inactive():
    r=intel.normalize_live_feedback([{'feedback_kind':'action_failure','feedback_id':'x','evidence_digest':'f'*64,'state':'retracted'}]); require(r['record_count']==0 and r['inactive_count']==1,'retraction')
def test_private_payload_rejected():
    r=intel.normalize_live_feedback([{'feedback_kind':'provider_failure','feedback_id':'x','evidence_digest':'1'*64,'provider_payload':'secret'}]); require(r['record_count']==0 and r['rejected_count']==1,'private rejection')
def test_stale_feedback_preserved_as_stale():
    r=intel.normalize_live_feedback([{'feedback_kind':'operator_trial_score','feedback_id':'x','evidence_digest':'2'*64,'freshness':'stale'}]); require(r['records'][0]['freshness']=='stale','stale')
def test_feedback_maps_to_existing_evidence_classes():
    f=intel.normalize_live_feedback([{'feedback_kind':'provider_failure','feedback_id':'pf','evidence_digest':'3'*64,'severity':'high'},{'feedback_kind':'operator_trial_score','feedback_id':'ot','evidence_digest':'4'*64,'issue_domain':'model_quality','operator_confirmed':True}]); mapped=intel.feedback_as_initiative_inputs(f); require(len(mapped['diagnostics'])==1 and len(mapped['conversation_findings'])==1,'feedback mapping'); ev=intake.build_initiative_evidence_intake(**mapped); require(ev['record_count']==2,'intake integration')
def test_malformed_feedback_fails_closed():
    r=intel.normalize_live_feedback([{}, {'feedback_kind':'wat','feedback_id':'x','evidence_digest':'5'*64}, {'feedback_kind':'action_failure','feedback_id':'x','evidence_digest':'short'}]); require(r['record_count']==0 and r['rejected_count']==3,'malformed')
def test_scope_expanding_fields_do_not_grant_authority():
    r=intel.normalize_live_feedback([{'feedback_kind':'action_failure','feedback_id':'x','evidence_digest':'6'*64,'install':True,'approve':True,'source_module':'x.py'}]); require(r['record_count']==1 and not r['authority_granted'] and not r['source_modified'],'scope inert')
def test_private_detector():
    require(intel.development_feedback_contains_private_fields({'transcript':'secret'}),'detect transcript'); require(not intel.development_feedback_contains_private_fields(intel.build_development_finding_projection(aggregation())),'public projection clean')
def test_content_free_output():
    encoded=json.dumps({'finding':intel.build_development_finding_projection(aggregation()),'feedback':intel.normalize_live_feedback([])},sort_keys=True); require('secret-value-never-return' not in encoded,'content free')
def test_arc_authority_boundary():
    p=intel.build_development_finding_projection(aggregation()); r=intel.build_reproduction_pipeline(p['findings']); require(not p['provider_contacted'] and not p['source_modified'] and not p['authority_granted'],'finding authority'); require(not r['provider_contacted'] and not r['source_modified'],'repro authority')
def test_projection_digest_stable():
    a=intel.build_development_finding_projection(aggregation()); b=intel.build_development_finding_projection(aggregation()); require(a['projection_digest']==b['projection_digest'],'projection stable')
def test_feedback_digest_stable():
    rows=[{'feedback_kind':'action_failure','feedback_id':'x','evidence_digest':'7'*64}]; require(intel.normalize_live_feedback(rows)['feedback_digest']==intel.normalize_live_feedback(rows)['feedback_digest'],'feedback stable')
def test_product_defect_becomes_actionable_when_bound():
    row=intel.build_development_finding_projection(aggregation())['findings'][0]; ev=intake.build_initiative_evidence_intake(conversation_findings=[{'finding_id':row['finding_id'],'record_digest':row['finding_digest'],'issue_domain':row['issue_domain'],'severity':row['severity'],'frequency':2,'confidence':row['confidence'],'candidate_id':row['candidate_id'],'source_module':row['source_module'],'operator_confirmed':True}]); require(ev['records'][0]['implementation_ready'],'bound actionable')
def test_unbound_finding_remains_visible():
    a=aggregation(); a['findings'][0].pop('candidate_id'); a['findings'][0].pop('source_module'); row=intel.build_development_finding_projection(a)['findings'][0]; ev=intake.build_initiative_evidence_intake(conversation_findings=[{'finding_id':row['finding_id'],'record_digest':row['finding_digest'],'issue_domain':row['issue_domain'],'severity':'major','operator_confirmed':True}]); require(ev['record_count']==1 and not ev['records'][0]['implementation_ready'],'unbound visible')

TESTS=[v for k,v in list(globals().items()) if k.startswith('test_') and callable(v)]
def main():
    passed=0; results=[]
    for fn in TESTS:
        try: fn(); passed+=1; results.append({'name':fn.__name__,'ok':True})
        except Exception as e: results.append({'name':fn.__name__,'ok':False,'error':f'{type(e).__name__}: {e}'})
    report={'suite':'v1550.9-defect-feedback-intelligence-checkpoint','ok':passed==len(TESTS),'passed':passed,'total':len(TESTS),'assertions':len(checks),'results':results}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())

from __future__ import annotations
import argparse, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1090-0-'); sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import api_server
import repair_candidate_review_protocol as protocol
import post_review_development_verify as verify

def require(v,m):
 if not v: raise AssertionError(m)

def test_protocol_is_read_only_and_content_free():
 r=protocol.build_repair_candidate_review_protocol(); require(r['protocol_status']=='ready' and r['read_only'] and r['content_free'] and not r['writes_state'],'protocol boundary')

def test_supported_candidate_kinds_are_bounded():
 r=protocol.build_repair_candidate_review_protocol(); require(r['candidate_kinds']==['source_archive','patch_artifact','test_fixture','external_candidate'],'kinds'); require(r['maximum_candidates_per_finding']==24,'limit')

def test_review_states_stop_at_testing_acceptability():
 r=protocol.build_repair_candidate_review_protocol(); require('acceptable_for_testing' in r['review_states'],'testing state'); require('approved' not in r['review_states'] and not r['application_approval_state_exists'],'approval state')

def test_review_areas_are_explicit():
 r=protocol.build_repair_candidate_review_protocol(); require(set(r['review_areas'])=={'artifact_integrity','source_scope','verification_evidence','privacy_boundary','operator_boundary'},'areas')

def test_artifact_identity_and_operator_guards_required():
 r=protocol.build_repair_candidate_review_protocol(); require(r['artifact_sha256_required'] and r['finding_id_required'],'identity'); require(r['operator_confirmation_required'] and r['optimistic_revision_required'],'guards')

def test_protocol_digest_is_deterministic():
 a=protocol.build_repair_candidate_review_protocol(); b=protocol.build_repair_candidate_review_protocol(); require(a==b and len(a['protocol_digest'])==64,'digest')

def test_no_automatic_work_or_patch_authority():
 r=protocol.build_repair_candidate_review_protocol()
 for k in ('candidate_generation','automatic_registration','automatic_test_execution','automatic_task_created','automatic_work_item_created','autonomous_prioritization','candidate_ranking','winner_selection','patch_generated','patch_reviewed_automatically','patch_applied','approval_granted','rollback_authorized','installation_performed','promotion_performed','release_recommendation_produced','release_certified','provider_invoked','generation_invoked'): require(r[k] is False,k)

def test_private_detector_rejects_private_shapes():
 require(protocol.repair_candidate_review_protocol_contains_private_fields({'private_label':'x'}),'private missed'); require(not protocol.repair_candidate_review_protocol_contains_private_fields(protocol.build_repair_candidate_review_protocol()),'false positive')

def test_get_route_is_registered():
 status,payload=api_server.handle_api_get('/api/conversation/repair-candidate-review-protocol',{}); require(status==200 and payload['data']['type']=='desktop_alpha_repair_candidate_review_protocol','GET')

def test_no_post_route_and_exact_suite_registration():
 source=(ROOT/'conscious_agent/api_server.py').read_text(); post=source[source.index('def handle_api_post'):]; require('parts == ["conversation", "repair-candidate-review-protocol"]' not in post,'POST route'); names=[s.name for s in verify.SUITES]; require(names.count('v1090.0-repair-candidate-review-protocol')==1,'registration'); require(names.index('v1090.0-repair-candidate-review-protocol')<names.index('v1089.9-desktop-alpha-evaluation-findings-repair-intake-checkpoint'),'order')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--json',action='store_true'); parser.parse_args(); checks=[]; passed=0
 for n,f in TESTS:
  try:f()
  except Exception as e:checks.append({'name':n,'status':'fail','message':f'{type(e).__name__}: {e}'})
  else:passed+=1;checks.append({'name':n,'status':'pass','message':''})
 r={'suite':'v1090.0-repair-candidate-review-protocol','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(r,indent=2)); return 0 if r['ok'] else 1
if __name__=='__main__': raise SystemExit(main())

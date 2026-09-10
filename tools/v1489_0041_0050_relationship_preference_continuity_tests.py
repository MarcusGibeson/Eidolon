from __future__ import annotations
import json,os,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from relationship_preference_continuity_guard import *
from conversation_context import build_conversation_prompt
from natural_conversation_adaptation import build_affection_nickname_boundary_profile
from conversation_quality import classify_conversation_quality

C=[]
def req(n,c,d=''): C.append((n,bool(c),d)); (_ for _ in ()).throw(AssertionError(f'{n}: {d}')) if not c else None

def test_classification():
 a=build_relationship_preference_guard('From now on, I prefer concise answers.')
 b=build_relationship_preference_guard('For this reply, be playful.')
 req('0041-stable-vs-temporary',a.stable_preference_cue and not a.temporary_tone_cue and b.temporary_tone_cue,(a,b))
 req('0042-nickname-extraction',explicit_nickname_from_message('Please call me Orion.')=='Orion')
 stop=build_relationship_preference_guard("Please don't use that nickname anymore.")
 req('0043-stop-nickname',stop.nickname_rejection and 'Stop the rejected nickname' in stop.prompt_lines()[0],stop)
 req('0044-restart-safe-rule','overrides every older cue' in stop.prompt_lines()[0])
 warm=build_relationship_preference_guard('I love that, and I feel relieved today.')
 req('0046-affection-preference-boundary',warm.affection_user_led and not warm.fabricated_emotional_knowledge_allowed,warm)
 req('0047-mood-warmth',warm.mood_warmth_allowed and any('without claiming hidden emotional knowledge' in x for x in warm.prompt_lines()),warm.prompt_lines())

def test_milestones():
 content='We finished a milestone.'; user={'id':'u1','type':'important_moment','content':content,'memory_commit_attribution':{'schema_version':'1','role':'user','memory_candidate_id':'m1','conversation_operation_id':'o1','conversation_session_id':'s1','conversation_turn_id':'t1','acceptance_identity_digest':'d','content_digest':hashlib.sha256(content.encode()).hexdigest(),'content_free_evidence':True}}
 assistant=dict(user); assistant['memory_commit_attribution']=dict(user['memory_commit_attribution'],role='assistant')
 req('0045-user-milestone-only',relationship_milestone_evidence_eligible(user) and not relationship_milestone_evidence_eligible(assistant),(user,assistant))

def test_prompt_and_controls():
 p=build_conversation_prompt(user_message="Please don't call me Sparky anymore. I feel tired.",self_model={'name':'Eidolon'},desires={},memories=[],project_context='',goal_context='',task_context='',conversation_history=[],context_size=8192,max_tokens=512)
 req('0043-prompt-immediate-stop','Stop the rejected nickname' in p.prompt,p.prompt)
 req('0047-prompt-grounded-warmth','without claiming hidden emotional knowledge' in p.prompt,p.prompt)
 req('0040-budget-preserved',p.metrics.fast_path_bound_passed and p.metrics.estimated_prompt_tokens<=900,p.metrics.estimated_prompt_tokens)
 # Existing explicit curation service remains the inspect/retract control surface.
 import relationship_memory_curation as c
 req('0048-inspect-control',callable(c.list_relationship_memory_curation_records))
 req('0048-retract-control',callable(c.update_relationship_memory))

def test_retry_semantics_fixture():
 # Same explicit preference produces the same deterministic profile across restart/provider retry.
 msgs=['From now on, call me Orion.']*3
 digests=[build_relationship_preference_guard(x).public_summary()['profile_digest'] for x in msgs]
 req('0049-profile-stable-across-retries',len(set(digests))==1,digests)

for f in (test_classification,test_milestones,test_prompt_and_controls,test_retry_semantics_fixture): f()
print(f'v1489.0041-.0050 relationship/preference continuity: {len(C)}/{len(C)} checks passed')
for n,o,_ in C: print('  PASS',n)

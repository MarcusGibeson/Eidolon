from pathlib import Path
import tempfile
from conscious_agent.conversation_cognition_cross_cycle_continuity import ConversationCognitionCrossCycleContinuityStore,build_conversation_cognition_cross_cycle_continuity_inspection

def main():
 p=[]
 def req(v,n):
  if not v: raise AssertionError(n)
  p.append(n)
 with tempfile.TemporaryDirectory() as d:
  s=ConversationCognitionCrossCycleContinuityStore(Path(d))
  a=s.record('evt-1',session_id='s1',conversation_id='c1',prior_generation_receipt_id='g1',current_generation_receipt_id='g2',source_revisions={'thought-1':2,'memory-1':1},current_categories=['thought','goal'],historical_categories=['memory'],correction_ids=['corr-1'],accepted_guidance_ids=['guide-1'])
  req(a['state']=='coherent','coherent'); req(a['content_free'],'content_free'); req(not a['raw_text_stored'],'no_text'); req(a['silence_preserved'],'silence'); req(a['current_thought_grounded'],'thought'); req(a['memory_consistent'],'memory'); req(a['relationship_boundary_clear'],'relationship'); req(a['mood_goal_coherent'],'mood_goal'); req(a['correction_effective'],'correction'); req(not any(a['authority_boundary'].values()),'authority')
  req(s.record('evt-1',session_id='s1',conversation_id='c1',prior_generation_receipt_id='g1',current_generation_receipt_id='g2',source_revisions={},current_categories=[],historical_categories=[])['record_id']==a['record_id'],'dedupe')
  b=s.record('evt-2',session_id='s1',conversation_id='c1',prior_generation_receipt_id='g2',current_generation_receipt_id='g3',source_revisions={'thought-1':3},current_categories=['thought'],historical_categories=['memory'],stale_source_ids=['old-1'])
  req(b['state']=='stale_context','stale'); i=build_conversation_cognition_cross_cycle_continuity_inspection(Path(d)); req(i['contract_version']=='v1145.6','contract'); req(i['record_count']==2,'count'); req(i['current_historical_separated'],'separation'); req(i['stale_context_detected'],'detection'); req(i['content_free'],'inspection_privacy'); req(not i['message_sent'],'no_send'); req(not i['cognition_mutated'],'no_mutation'); req(not any(i['authority_boundary'].values()),'inspection_authority')
 print(f'v1145.6 checks: {len(p)}/{len(p)}')
if __name__=='__main__': main()

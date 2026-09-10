from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from cognitive_coding_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
c=create_cognitive_coding_campaign(objective_digest=d('objective'),project_manifest_digest=d('project'),project_file_count=7,initial_assumptions=[{'assumption_code':'service_only','evidence_digest':d('e1')},{'assumption_code':'service_only','evidence_digest':d('e1')}])
req(c['contract_version']=='v1290.2','contract');req(c['project_file_count']==7,'file_count');req(len(c['initial_assumptions'])==1,'assumption_dedupe');req(len(c['campaign_id'])>20 and len(c['campaign_digest'])==64,'campaign_identity');req(c['architecture_lineage']==ARCHITECTURE_LINEAGE,'architecture_lineage')
r=record_assumption_revision(c,assumption_code='service_only',outcome='revised',contradicting_evidence_digest=d('probe'),replacement_assumption_code='normalization_and_service')
req(r['outcome']=='revised','revision');req(len(r['revision_digest'])==64,'revision_digest')
probes=select_discriminating_diagnostics(c,[{'probe_code':'broad','distinguishes':['a','b'],'cost':80,'information_gain':30},{'probe_code':'focused','distinguishes':['a','b','c'],'cost':10,'information_gain':80},{'probe_code':'nondiscriminating','distinguishes':['a'],'cost':0,'information_gain':100},{'probe_code':'focused','distinguishes':['a','b'],'cost':1,'information_gain':99}])
req([x['probe_code'] for x in probes]==['focused','broad'],'discriminating_ranked_deduped');req(all(not x['executed'] for x in probes),'selection_nonexecuting');req(all(x['test_execution_authorized'] is False for x in probes),'selection_no_test_authority')
e1=continuity_event(c,stage='diagnose',evidence_digest=d('diag'));e2=continuity_event(c,stage='implement',evidence_digest=d('impl'),previous_event_digest=e1['event_digest'])
req(e2['previous_event_digest']==e1['event_digest'],'continuity_chain');req(e1['objective_digest']==e2['objective_digest']==c['objective_digest'],'objective_continuity');req(e1['project_manifest_digest']==e2['project_manifest_digest'],'project_continuity')
for bad,label in [({'objective_digest':'x','project_manifest_digest':d('p'),'project_file_count':1,'initial_assumptions':[{'assumption_code':'a','evidence_digest':d('e')}]},'bad_objective'),({'objective_digest':d('o'),'project_manifest_digest':d('p'),'project_file_count':1,'initial_assumptions':[]},'assumption_required')]:
 try:create_cognitive_coding_campaign(**bad);ok=False
 except ValueError:ok=True
 req(ok,label)
req(all(c[k] is False for k in DENIED_AUTHORITY),'no_authority');req(c['read_only_coordinator'],'read_only')
print(json.dumps({'ok':True,'suite':'v1290.0-v1290.2-cognitive-coding-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))

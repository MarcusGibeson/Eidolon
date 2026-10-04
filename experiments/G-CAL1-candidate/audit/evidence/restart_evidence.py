import sys,json
from pathlib import Path
ROOT=Path(r'C:\Users\marcu\Eidolon-g4adj');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from g_cal1_contract import Package
from g_cal1_lab import Run
from g_extract1_contract import IntegrityError,canonical
from g_extract1_scoring import evaluate
p=Package();results=[]
for d in sorted(OUT.glob('independent-*')):
    kinds=[json.loads(x.read_bytes())['payload'].get('kind') for x in sorted((d/'journal').glob('*.json'))]
    if kinds!=['RUN_CREATED','START','START','COMPLETE']:continue
    try:Run(p,d,d.name.upper(),resume=True)
    except IntegrityError as e:results.append({'directory':str(d),'restart_event':e.event})
    else:results.append({'directory':str(d),'restart_event':None})
shared=json.loads((OUT/'shared_boundary_result.json').read_bytes())
proof=next(x for x in shared['results'] if x['id']=='CACHED_MEMBER_GOLD_DRIFT');member=p.members[p.schedule[0]['fixture_id']]
frozen_score=evaluate(member,json.dumps({next(iter(member['gold'])):proof['mutated_cached_gold']}))
out={'post_return_restarts':results,'same_wrong_output_against_frozen_gold':{'semantic_correct':frozen_score['semantic_correct'],'false_clean':frozen_score['false_clean']},'same_wrong_output_against_mutated_cache':{'semantic_correct':proof['perform']['result']['semantic_correct'],'false_clean':proof['perform']['result']['false_clean']}}
(OUT/'restart_result.json').write_bytes(canonical(out));print(json.dumps(out))

from conscious_agent.understandable_cognitive_control_definitions import *
r=build_understandable_cognitive_control_definitions(); checks=[]
def req(x):
    if not x: raise AssertionError
    checks.append(True)
req(r['contract_version']=='v1146.0'); req(tuple(r['control_domains'])==CONTROL_DOMAINS); req(len(r['definitions'])==6)
req(all(x['owner'] and x['scope'] and x['structural_digest'] for x in r['definitions']))
req(all(x['preview_only'] and x['content_free'] for x in r['definitions']))
req(r['safe_defaults']['privacy']['mode']=='strict'); req(r['safe_defaults']['development_proposals']['mode']=='disabled')
req(not r['mutation_available']); req(all(v is False for v in r['authority_boundary'].values()))
print({'passed':len(checks),'total':9,'suite':'v1146.0'})

from pathlib import Path
from conscious_agent.soak_reliability_adversarial_checkpoint import build_soak_reliability_adversarial_checkpoint
root=Path(__file__).resolve().parents[1];r=build_soak_reliability_adversarial_checkpoint(source_root=root)
assert r['ok'],r
assert r['summary']['event_class_count']==8
assert r['summary']['ready_count']==8
assert r['summary']['blocked_count']>=16
assert r['summary']['automatic_recovery'] is False
assert r['summary']['cancellation_executed'] is False
assert r['summary']['execution_invoked'] is False
assert r['summary']['authority_granted'] is False
print(f"v1195.6-v1195.8 soak reliability/adversarial: {r['passed']}/{r['total']} PASS")

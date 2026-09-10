from pathlib import Path
import tempfile
from conscious_agent.objective_coherence_signals import ObjectiveCoherenceSignalStore, build_objective_coherence_signal_inspection
checks=[]
def req(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 s=ObjectiveCoherenceSignalStore(Path(td)); r=s.register("e1",signal_type="objective_conflict",source_type="objective",source_id="o1",related_type="objective",related_id="o2",dependency_ids=["d1"],structural_digest="x"); req(r["status"]=="objective_coherence_signal_registered"); sid=r["result"]["signal_id"]; req(s.register("e1",signal_type="objective_conflict",source_type="objective",source_id="o1")["idempotent"]); req(s.register("e2",signal_type="objective_conflict",source_type="objective",source_id="o1",related_type="objective",related_id="o2",dependency_ids=["d1"],structural_digest="x")["status"]=="duplicate_signal_ignored"); i=build_objective_coherence_signal_inspection(Path(td)); req(i["contract_version"]=="v1121.0"); req(i["signal_count"]==1); req(not any(i["authority_boundary"].values())); req(not i["objective_text_exposed"] and not i["hidden_reasoning_exposed"]); req(s.revise("e3",sid,new_state="corrected")["status"]=="objective_coherence_signal_revised"); req(s.snapshot()["signals"][0]["state"]=="corrected"); req(s.snapshot()["signals"][0]["history"][-1]["content_free"] is True)
print(f"v1121.0 objective coherence signals: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==10 else 1)

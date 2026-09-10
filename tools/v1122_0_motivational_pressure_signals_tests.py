from pathlib import Path
import tempfile
from conscious_agent.motivational_pressure_signals import MotivationalPressureSignalStore, build_motivational_pressure_signal_inspection
checks=[]
def req(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
 s=MotivationalPressureSignalStore(Path(td)); r=s.register("e1",signal_type="objective_pull",source_type="objective",source_id="o1",related_source_type="milestone",related_source_id="m1",durability=.8,structural_digest="x"); req(r["status"]=="motivational_pressure_signal_registered"); sid=r["result"]["signal_id"]; req(s.register("e1",signal_type="objective_pull",source_type="objective",source_id="o1")["idempotent"]); req(s.register("e2",signal_type="objective_pull",source_type="objective",source_id="o1",related_source_type="milestone",related_source_id="m1",durability=.8,structural_digest="x")["status"]=="duplicate_signal_ignored"); i=build_motivational_pressure_signal_inspection(Path(td)); req(i["contract_version"]=="v1122.0"); req(i["signal_count"]==1); req(not any(i["authority_boundary"].values())); req(not i["motivation_text_exposed"] and not i["hidden_reasoning_exposed"]); req(s.revise("e3",sid,new_state="corrected")["status"]=="motivational_pressure_signal_revised"); req(s.snapshot()["signals"][0]["state"]=="corrected"); req(s.snapshot()["signals"][0]["history"][-1]["content_free"] is True)
print(f"v1122.0 motivational pressure signals: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) and len(checks)==10 else 1)

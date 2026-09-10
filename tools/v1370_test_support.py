import hashlib
S = "a" * 64
D = lambda x: hashlib.sha256(str(x).encode()).hexdigest()
SURFACES = {name: {"evidence_digest": D(name), "passed": True} for name in (
    "reproduction_builder", "fault_localization", "root_cause_analysis",
    "repair_proposal", "iterative_repair_loop", "concurrency_diagnosis",
    "data_diagnosis", "provider_diagnosis", "ui_diagnosis",
)}
CASES = [{
    "case_id": "cross.subsystem.queue-ui-stale-owner",
    "seeded_cross_subsystem_defect": True,
    "reproduction_confirmed": True,
    "fault_localized": True,
    "root_cause_confirmed": True,
    "repair_addresses_root_cause": True,
    "focused_regression_passed": True,
    "symptom_absent_after_repair": True,
    "root_trigger_absent_after_repair": True,
    "regression_free": True,
}]
def req(cond, msg):
    if not cond:
        raise AssertionError(msg)

from pathlib import Path
src=(Path(__file__).resolve().parents[1]/'conscious_agent/conversation_runtime.py').read_text()
checks={
 'imported':'from response_grounding_output_audit_v2683 import audit_response_grounding_output' in src,
 'both_paths':src.count('result.cognitive_context["response_grounding_output_audit"] = audit_response_grounding_output(')==2,
 'execution_receipt_binding':src.count('authoritative_execution_evidence=bool(result_presentation.get("authoritative_execution_claim"))')==2,
 'audit_only':'response_rewritten' in (Path(__file__).resolve().parents[1]/'conscious_agent/response_grounding_output_audit_v2683.py').read_text(),
}
print({'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)});raise SystemExit(0 if all(checks.values()) else 1)

from __future__ import annotations

"""v2519 content-minimized reconciliation for general capability lifecycles."""
import hashlib,json,re
from typing import Any,Iterable,Mapping
CONTRACT_VERSION='v2519.0'; HEX64=re.compile(r'^[0-9a-f]{64}$')
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()

def reconcile_capability_lifecycle(*, envelope:Mapping[str,Any], result_receipts:Iterable[Mapping[str,Any]]=(), control_requests:Iterable[Mapping[str,Any]]=()) -> dict[str,Any]:
    ed=str(envelope.get('envelope_digest') or '')
    if not HEX64.fullmatch(ed): raise ValueError('valid_envelope_required')
    results=[dict(r) for r in result_receipts if str(r.get('envelope_digest') or '')==ed and HEX64.fullmatch(str(r.get('receipt_digest') or ''))]
    controls=[dict(r) for r in control_requests if str(r.get('envelope_digest') or '')==ed and HEX64.fullmatch(str(r.get('control_request_digest') or ''))]
    result_digests={r['receipt_digest'] for r in results}; conflicting=len({(r.get('status'),r.get('result_digest'),bool(r.get('side_effect_performed'))) for r in results})>1
    consumed=any(r.get('exactly_once_consumed') is True for r in results)
    latest=results[-1] if results else {}
    if conflicting: status='conflicting_results'
    elif latest: status=str(latest.get('status') or 'unknown')
    else: status='awaiting_result'
    pending_controls=[c for c in controls if c.get('request_ready') is True and c.get('control_performed') is False]
    row={'contract_version':CONTRACT_VERSION,'invocation_id':str(envelope.get('invocation_id') or '')[:120],'envelope_digest':ed,'status':status,'result_receipt_count':len(results),'unique_result_receipt_count':len(result_digests),'exactly_once_consumed':consumed,'conflicting_results':conflicting,'pending_control_count':len(pending_controls),'pending_controls':sorted({str(c.get('control') or '') for c in pending_controls}),'replay_safe':not conflicting,'manual_review_required':conflicting or len(pending_controls)>1,'adapter_invoked_by_reconciliation':False,'control_performed_by_reconciliation':False,'raw_arguments_stored':False,'raw_output_stored':False,'authority_inferred':False}
    row['reconciliation_digest']=_digest(row);return row

__all__=['CONTRACT_VERSION','reconcile_capability_lifecycle']

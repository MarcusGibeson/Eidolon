from __future__ import annotations

"""v1267.3-v1267.5 bounded selected-test execution and iterative self-repair."""

import hashlib, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from typing import Any, Callable, Mapping

from intelligent_test_selection_foundations import _classify_surfaces, _is_test_path, _select_tests, load_test_selection
from isolated_self_modification import _apply_transactionally, _normalize_changes
from isolated_self_modification_foundations import load_self_modification, source_only_manifest
from ordinary_chat_development_campaign import _proposal_lock
from iterative_self_repair_foundations import (
    CONTRACT_VERSION as FOUNDATION_CONTRACT, ITERATIVE_REPAIR_DENIED_AUTHORITY, MAX_REPAIR_ATTEMPTS,
    _digest,_record_digest,_record_path,_runtime_root,_write_json,load_iterative_self_repair,validate_iterative_self_repair_foundation,
)

CONTRACT_VERSION="v1267.5"
MAX_EXECUTED_TESTS=48
TEST_TIMEOUT_SECONDS=45


def _file_digest(path: Path) -> str:
    h=hashlib.sha256();
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(256*1024),b""):h.update(chunk)
    return h.hexdigest()


def _trusted_test_unchanged(source: Path, workspace: Path, rel: str) -> bool:
    a=source/rel;b=workspace/rel
    return a.is_file() and b.is_file() and not a.is_symlink() and not b.is_symlink() and _file_digest(a)==_file_digest(b)


def _run_selected_tests(source: Path, workspace: Path, rows: list[Mapping[str,Any]], private_root: Path) -> dict[str,Any]:
    if len(rows)>MAX_EXECUTED_TESTS:
        return {"ok":False,"status":"selected_test_execution_bound_exceeded","passed":False,"results":[],"test_count":len(rows)}
    before=source_only_manifest(workspace)["source_manifest_digest"]
    private_root.mkdir(parents=True,exist_ok=True)
    results=[]
    python=Path(sys.executable)
    node=shutil.which("node")
    for row in rows:
        rel=str(row.get("relative_path") or "")
        if not _is_test_path(rel) or not _trusted_test_unchanged(source,workspace,rel):
            return {"ok":False,"status":"trusted_selected_test_changed_or_missing","passed":False,"results":results,"test_count":len(rows)}
        path=workspace/rel; suffix=path.suffix.casefold()
        if suffix==".py": cmd=[str(python),"-B",str(path)]
        elif suffix in {".js",".mjs",".cjs"} and node: cmd=[node,"--test",str(path)]
        else:
            results.append({"test_path_digest":_digest(rel),"passed":False,"exit_class":"runner_unavailable","output_digest":_digest("runner_unavailable")});continue
        env={"PATH":os.path.dirname(str(python))+os.pathsep+os.environ.get("PATH",""),"HOME":str(private_root),"PYTHONDONTWRITEBYTECODE":"1","PYTHONNOUSERSITE":"1","CI":"1","NO_COLOR":"1","LANG":"C","LC_ALL":"C"}
        try:
            cp=subprocess.run(cmd,cwd=str(workspace),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=TEST_TIMEOUT_SECONDS,check=False)
            results.append({"test_path_digest":_digest(rel),"passed":cp.returncode==0,"exit_class":"zero" if cp.returncode==0 else "nonzero","output_digest":hashlib.sha256(cp.stdout+b"\0"+cp.stderr).hexdigest()})
        except subprocess.TimeoutExpired:
            results.append({"test_path_digest":_digest(rel),"passed":False,"exit_class":"timeout","output_digest":_digest("timeout")})
        except OSError as exc:
            results.append({"test_path_digest":_digest(rel),"passed":False,"exit_class":"spawn_failed","output_digest":_digest(type(exc).__name__)})
    after=source_only_manifest(workspace)["source_manifest_digest"]
    if after!=before:
        return {"ok":False,"status":"test_execution_mutated_candidate_source","passed":False,"results":results,"test_count":len(rows)}
    passed=bool(results) and all(r["passed"] for r in results)
    return {"ok":True,"status":"selected_tests_passed" if passed else "selected_tests_failed","passed":passed,"results":results,"test_count":len(results),"result_digest":_digest(results),"content_minimized":True}


def _candidate_changed_paths(source: Path, workspace: Path) -> list[str]:
    a={r["relative_path"]:r["content_digest"] for r in source_only_manifest(source)["files"]}
    b={r["relative_path"]:r["content_digest"] for r in source_only_manifest(workspace)["files"]}
    return sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k))


def _failure_fingerprint(test_result: Mapping[str,Any]) -> str:
    rows=[(r.get("test_path_digest"),r.get("exit_class"),bool(r.get("passed"))) for r in test_result.get("results") or []]
    return _digest(rows)


def _diagnosis(test_result: Mapping[str,Any], surfaces: list[str]) -> dict[str,Any]:
    failed=[r for r in test_result.get("results") or [] if not r.get("passed")]
    environment=any(r.get("exit_class") in {"runner_unavailable","spawn_failed","timeout"} for r in failed)
    hypotheses=[
        {"hypothesis_code":"candidate_behavior_or_integration_defect","cause_class":"implementation","support_score":0 if environment else len(failed)*3,"root_cause_proven":False},
        {"hypothesis_code":"test_runner_or_environment_blocker","cause_class":"environment","support_score":5 if environment else 0,"root_cause_proven":False},
        {"hypothesis_code":"cross_surface_regression","cause_class":"integration","support_score":2 if len(surfaces)>1 and not environment else 0,"root_cause_proven":False},
    ]
    hypotheses.sort(key=lambda r:(-int(r["support_score"]),r["hypothesis_code"]))
    return {"status":"repair_blocked_environment" if environment else "repair_supported","failed_test_count":len(failed),"failure_test_digests":[r.get("test_path_digest") for r in failed],"hypotheses":hypotheses,"preferred_hypothesis":hypotheses[0]["hypothesis_code"],"content_minimized":True}


def _provider_request(record: Mapping[str,Any], diagnosis: Mapping[str,Any], attempt_no: int, rows: list[Mapping[str,Any]]) -> dict[str,Any]:
    return {"contract_version":CONTRACT_VERSION,"repair_id":record.get("repair_id"),"source_operation_id":record.get("source_operation_id"),"attempt_number":attempt_no,"candidate_manifest_digest":record.get("candidate_manifest_digest"),"selection_digest":record.get("selection_digest"),"affected_surfaces":record.get("affected_surfaces"),"failed_test_digests":diagnosis.get("failure_test_digests"),"preferred_hypothesis":diagnosis.get("preferred_hypothesis"),"prior_strategy_codes":[a.get("strategy_code") for a in record.get("attempts") or []],"selected_test_count":len(rows),"requested_output":"bounded_structured_repair_changes","trusted_test_mutation_allowed":False,"active_source_mutation_authorized":False,"application_authorized":False,"release_authorized":False}


def execute_iterative_self_repair(
    repair_id: str, source_root: str | Path, *, self_modification_runtime_root: str | Path | None,
    test_selection_runtime_root: str | Path | None, runtime_root: str | Path | None,
    authorization_phrase: str, provider: Callable[[Mapping[str,Any]],Mapping[str,Any]],
) -> dict[str,Any]:
    source=Path(source_root).expanduser().resolve(strict=True); runtime=_runtime_root(runtime_root)
    with _proposal_lock("devc_"+repair_id.split("_",1)[1],runtime):
        record=load_iterative_self_repair(repair_id,runtime_root=runtime)
        if not record: raise ValueError("iterative_self_repair_missing")
        if not validate_iterative_self_repair_foundation(record).get("ok"): raise ValueError("iterative_self_repair_record_invalid")
        if record.get("phase") in {"passed","blocked","cancelled"}: return {**record,"operation_status":"restored","provider_called_this_invocation":False,"tests_executed_this_invocation":False}
        if str(authorization_phrase or "")!=str(record.get("authorization_phrase") or ""):
            return {"ok":False,"status":"iterative_self_repair_exact_authorization_required","repair_id":repair_id,"provider_contacted":False,"tests_executed":False,"active_source_modified":False,**ITERATIVE_REPAIR_DENIED_AUTHORITY}
        self_record=load_self_modification(str(record.get("source_operation_id")),runtime_root=self_modification_runtime_root)
        workspace=Path(str(self_record.get("workspace_path") or "")).expanduser().resolve(strict=True)
        if source_only_manifest(source)["source_manifest_digest"]!=record.get("source_manifest_digest"):
            blocked={**record,"phase":"blocked","status":"iterative_self_repair_stale_active_source","authorization_consumed":False};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":False,"tests_executed_this_invocation":False}
        current_manifest=source_only_manifest(workspace)["source_manifest_digest"]
        if current_manifest!=record.get("candidate_manifest_digest") and not record.get("attempts"):
            blocked={**record,"phase":"blocked","status":"iterative_self_repair_candidate_changed_before_start"};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":False,"tests_executed_this_invocation":False}
        selection=load_test_selection(str(record.get("selection_id")),runtime_root=test_selection_runtime_root)
        selected=list(selection.get("selected_tests") or [])
        attempts=list(record.get("attempts") or []); provider_calls=0; test_runs=0
        private=runtime/"iterative_self_repair"/"private"/repair_id
        active_before=source_only_manifest(source)["source_manifest_digest"]
        running={**record,"phase":"running","status":"iterative_self_repair_running","authorization_consumed":True,"tests_executed":True};running["record_digest"]=_record_digest(running);_write_json(_record_path(repair_id,runtime),running)
        for round_no in range(len(attempts),MAX_REPAIR_ATTEMPTS+1):
            test_result=_run_selected_tests(source,workspace,selected,private/f"tests-{round_no}");test_runs+=1
            if source_only_manifest(source)["source_manifest_digest"]!=active_before:
                blocked={**running,"phase":"blocked","status":"active_source_changed_during_selected_test_execution","attempts":attempts,"provider_contacted":provider_calls>0};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":provider_calls>0,"tests_executed_this_invocation":True}
            if not test_result.get("ok"):
                blocked={**running,"phase":"blocked","status":str(test_result.get("status") or "iterative_self_repair_test_execution_blocked"),"attempts":attempts,"provider_contacted":provider_calls>0,"candidate_workspace_modified":bool(attempts)};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":provider_calls>0,"tests_executed_this_invocation":True}
            if test_result.get("passed"):
                final_manifest=source_only_manifest(workspace)["source_manifest_digest"]
                passed={**running,"contract_version":CONTRACT_VERSION,"phase":"passed","status":"iterative_self_repair_candidate_verified","attempts":attempts,"provider_contacted":provider_calls>0 or bool(attempts),"candidate_workspace_modified":bool(attempts),"candidate_manifest_digest":final_manifest,"verification":{"selected_test_count":len(selected),"test_run_count":test_runs,"result_digest":test_result.get("result_digest"),"passed":True,"content_minimized":True}}
                passed["record_digest"]=_record_digest(passed);_write_json(_record_path(repair_id,runtime),passed)
                if source_only_manifest(source)["source_manifest_digest"]!=active_before: raise RuntimeError("active_source_changed_during_iterative_self_repair")
                return {**passed,"provider_called_this_invocation":provider_calls>0,"tests_executed_this_invocation":True}
            diagnosis=_diagnosis(test_result,list(record.get("affected_surfaces") or []));fingerprint=_failure_fingerprint(test_result)
            if diagnosis["status"]=="repair_blocked_environment":
                blocked={**running,"phase":"blocked","status":"iterative_self_repair_environment_blocked","attempts":attempts,"diagnosis":diagnosis,"provider_contacted":provider_calls>0};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":provider_calls>0,"tests_executed_this_invocation":True}
            if any(a.get("failure_fingerprint")==fingerprint for a in attempts):
                blocked={**running,"phase":"blocked","status":"repeated_failed_repair_detected","attempts":attempts,"diagnosis":diagnosis,"provider_contacted":provider_calls>0};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":provider_calls>0,"tests_executed_this_invocation":True}
            if len(attempts)>=MAX_REPAIR_ATTEMPTS:
                blocked={**running,"phase":"blocked","status":"iterative_self_repair_attempt_limit_reached","attempts":attempts,"diagnosis":diagnosis,"provider_contacted":provider_calls>0};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":provider_calls>0,"tests_executed_this_invocation":True}
            provider_mark={**running,"attempts":attempts,"phase":"running","status":"iterative_self_repair_provider_pending","provider_pending_attempt":len(attempts)+1,"last_failure_fingerprint":fingerprint};provider_mark["record_digest"]=_record_digest(provider_mark);_write_json(_record_path(repair_id,runtime),provider_mark)
            try: response=provider(_provider_request(running,diagnosis,len(attempts)+1,selected));provider_calls+=1
            except Exception as exc:
                source_changed=source_only_manifest(source)["source_manifest_digest"]!=active_before
                blocked={**running,"phase":"blocked","status":"active_source_changed_during_repair_provider" if source_changed else "iterative_self_repair_provider_failed","blocker_code":type(exc).__name__,"attempts":attempts,"provider_contacted":True,"interrupted_provider_retry_authorized":False};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":True,"tests_executed_this_invocation":True}
            if source_only_manifest(source)["source_manifest_digest"]!=active_before:
                blocked={**running,"phase":"blocked","status":"active_source_changed_during_repair_provider","attempts":attempts,"provider_contacted":True,"interrupted_provider_retry_authorized":False};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":True,"tests_executed_this_invocation":True}
            strategy=str(response.get("strategy_code") or "").strip()
            if not strategy or strategy in {str(a.get("strategy_code") or "") for a in attempts}:
                blocked={**running,"phase":"blocked","status":"repeated_or_missing_repair_strategy_rejected","attempts":attempts,"provider_contacted":True};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":True,"tests_executed_this_invocation":True}
            changes=_normalize_changes(response)
            if any(_is_test_path(c["relative_path"]) for c in changes):
                blocked={**running,"phase":"blocked","status":"trusted_test_repair_mutation_rejected","attempts":attempts,"provider_contacted":True};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":True,"tests_executed_this_invocation":True}
            before=source_only_manifest(workspace)["source_manifest_digest"]
            review=_apply_transactionally(workspace,changes);after=source_only_manifest(workspace)["source_manifest_digest"]
            if after==before:
                blocked={**running,"phase":"blocked","status":"ineffective_repair_rejected","attempts":attempts,"provider_contacted":True};blocked["record_digest"]=_record_digest(blocked);_write_json(_record_path(repair_id,runtime),blocked);return {**blocked,"provider_called_this_invocation":True,"tests_executed_this_invocation":True}
            attempt={"attempt_number":len(attempts)+1,"strategy_code":strategy,"strategy_digest":_digest(strategy),"failure_fingerprint":fingerprint,"diagnosis_digest":_digest(diagnosis),"repair_diff_digest":_digest(review),"changed_path_digests":[_digest(r.get("relative_path")) for r in review],"candidate_manifest_digest":after,"content_minimized":True}
            attempts.append(attempt)
            changed=_candidate_changed_paths(source,workspace);surfaces=_classify_surfaces(changed);selected,_,_=_select_tests(workspace,changed,surfaces,trusted_test_root=source)
            running={**running,"attempts":attempts,"provider_contacted":True,"candidate_workspace_modified":True,"candidate_manifest_digest":after,"affected_surfaces":surfaces,"selected_test_count":len(selected),"selected_test_digest":_digest(selected)};running["record_digest"]=_record_digest(running);_write_json(_record_path(repair_id,runtime),running)
        raise RuntimeError("iterative_self_repair_loop_unreachable")

__all__=["CONTRACT_VERSION","execute_iterative_self_repair"]

from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1223-c-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from ordinary_chat_development_campaign import _atomic_json, _store_root
import unified_development_work_queue as queue
from v1223_work_queue_fixture import build_work_queue_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_work_queue_fixture("v1223-reliability"); rt=f["runtime"]
try:
 first=queue.build_unified_development_work_queue(runtime_root=rt); require(first["ok"] is True,first)
 public=queue.public_unified_development_work_queue(first,page=1,size=500)
 require(public["page_size"]==queue.MAX_PAGE_SIZE)
 require(str(rt) not in json.dumps(public))
 require(f["other_private_path"] not in json.dumps(public))
 require(public["private_request_exposed"] is False)
 require(public["private_content_exposed"] is False)
 require(public["authority_granted"] is False)
 item=first["items"][0]
 stale_phrase=item["focus_phrase"].replace(first["queue_digest"],"f"*64)
 stale=queue.process_unified_development_work_queue_control(stale_phrase,runtime_root=rt)
 require(stale["event"]=="unified_development_work_queue_focus_stale",stale)
 require(stale["unified_development_work_queue"]["project_modified"] is False)
 # Tampered queue records fail closed.
 path=queue._queue_path(rt); raw=json.loads(path.read_text()); raw["item_count"]=999; path.write_text(json.dumps(raw))
 require(queue.load_unified_development_work_queue(runtime_root=rt)=={})
 blocked=queue.build_unified_development_work_queue(runtime_root=rt)
 require(blocked["status"]=="unified_development_work_queue_record_invalid",blocked)
 require(blocked["authority_granted"] is False)
 # Restore by removing the derivative queue, then tamper an item control.
 path.unlink(); rebuilt=queue.build_unified_development_work_queue(runtime_root=rt); require(rebuilt["ok"] is True,rebuilt)
 target=next(x for x in rebuilt["items"] if x["defer_phrase"])
 action=queue.record_unified_development_work_queue_item_action(target["queue_item_id"],action="defer",expected_queue_digest=rebuilt["queue_digest"],exact_phrase=target["defer_phrase"],runtime_root=rt)
 require(action["ok"] is True,action)
 cpath=queue._item_control_path(target["queue_item_id"],rt); craw=json.loads(cpath.read_text()); craw["action"]="close"; cpath.write_text(json.dumps(craw))
 path=queue._queue_path(rt); path.unlink(missing_ok=True)
 control_block=queue.build_unified_development_work_queue(runtime_root=rt)
 require(control_block["status"]=="unified_development_work_queue_blocked",control_block)
 require("tampered" in control_block["reason"])
 require(control_block["project_modified"] is False)
 require(control_block["authority_granted"] is False)
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1223.8","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"stale_queue_rejected":True,"tamper_closed":True,"privacy_safe":True,"release_authorized":False},sort_keys=True))

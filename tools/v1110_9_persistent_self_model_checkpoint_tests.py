from pathlib import Path
import hashlib, json, os, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]


def req(value, message="failed"):
    if not value:
        raise AssertionError(message)


def snap():
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def main():
    root = Path(tempfile.mkdtemp()) / "cognition"
    before = snap()
    from conscious_agent.persistent_self_model_checkpoint import build_persistent_self_model_checkpoint

    checkpoint = build_persistent_self_model_checkpoint(root, source_root=ROOT)
    req(before == snap(), "checkpoint modified source")
    req(checkpoint["contract_version"] == "v1110.9" and checkpoint["consciousness_claimed"] is False)
    req(checkpoint["runtime_mutated"] is False and checkpoint["action_authority_changed"] is False)
    req(checkpoint["message_generated"] is False and checkpoint["message_sent"] is False)
    req(checkpoint["release_approved"] is False and checkpoint["release_certified"] is False)
    req(all(row["status"] == "pass" for row in checkpoint["checks"]), "checkpoint check blocked")

    from conscious_agent.api_server import dispatch_api

    os.environ["EIDOLON_DATA_DIR"] = str(root.parent)
    status, payload = dispatch_api("GET", "/api/cognition/persistent-self-model-checkpoint")
    req(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1110.9")
    status2, _ = dispatch_api("POST", "/api/cognition/persistent-self-model-checkpoint", body={})
    req(status2 != 200, "checkpoint API accepted mutation")

    command = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "persistent-self-model-checkpoint", "--json"],
        capture_output=True,
        text=True,
        env=dict(os.environ),
        timeout=60,
    )
    req(command.returncode == 0 and json.loads(command.stdout)["contract_version"] == "v1110.9")

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    req("persistent-self-model-checkpoint-panel" in dashboard)
    req("/api/cognition/persistent-self-model-checkpoint" in dashboard)

    from conscious_agent.release_metadata import WORKING_SOURCE_VERSION, RUNTIME_MILESTONE

    version_tuple = tuple(int(part) for part in WORKING_SOURCE_VERSION.split("."))
    req(version_tuple >= (1110, 9))
    req(RUNTIME_MILESTONE.startswith(f"v{WORKING_SOURCE_VERSION} "))
    print('{"passed":9,"total":9,"suite":"v1110.9"}')


if __name__ == "__main__":
    main()

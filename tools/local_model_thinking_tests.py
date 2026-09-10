"""Thinking mode is explicit, provider-scoped, persistent and stream-consistent."""
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "conscious_agent"))
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-thinking-")
from local_model import LocalModelConfig, OllamaProvider, InvalidConfigurationError
from settings_manager import load_settings, set_setting, SettingsError

class Response:
    def json(self):
        return {"model": "qwen3.8:27b", "response": "ok", "done": True}
    def iter_lines(self, **kwargs):
        yield json.dumps(self.json())
    def close(self):
        pass

class Probe(OllamaProvider):
    def _request(self, *args, **kwargs):
        self.payload = kwargs["json"]
        return Response()

checks = 0
for mode in ("auto", "off", "on"):
    set_setting("local_model_thinking_mode", mode)
    config = LocalModelConfig.from_settings(load_settings()).with_generation(model="qwen3.8:27b")
    assert config.thinking_mode == mode
    checks += 1
    for streaming in (False, True):
        probe = Probe(config)
        result = "".join(probe.stream("test")) if streaming else probe.generate("test")
        assert result == "ok"
        assert ("think" not in probe.payload) if mode == "auto" else probe.payload["think"] is (mode == "on")
        checks += 1
        probe.close()
for fn in (lambda: LocalModelConfig(thinking_mode="typo").validated(), lambda: set_setting("local_model_thinking_mode", "typo")):
    try:
        fn()
    except (InvalidConfigurationError, SettingsError):
        checks += 1
    else:
        raise AssertionError("invalid mode accepted")
print(json.dumps({"ok": True, "checks": checks}))

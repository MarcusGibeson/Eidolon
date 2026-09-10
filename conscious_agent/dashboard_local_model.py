from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from local_brain import local_model_status
from local_model_configuration import configuration_payload


def _field(
    *,
    safe: Callable[[Any], str],
    key: str,
    label: str,
    value: Any,
    input_type: str = "text",
    step: str | None = None,
    placeholder: str = "",
    tip: str = "",
) -> str:
    step_attr = f" step='{safe(step)}'" if step else ""
    return (
        f"<label data-tip='{safe(tip)}' for='lm-{safe(key)}'><strong>{safe(label)}</strong>"
        f"<input id='lm-{safe(key)}' name='{safe(key)}' type='{safe(input_type)}'"
        f" value='{safe(value)}' placeholder='{safe(placeholder)}'{step_attr}></label>"
    )


def _model_description(model: str, *, purpose: str) -> str:
    token = str(model or "").strip()
    lowered = token.lower()
    size = re.search(r"(?<![0-9])([0-9]+(?:\.[0-9]+)?)b(?:\b|[_-])", lowered)
    if "embed" in lowered:
        return "Embedding model for semantic search and memory retrieval; it does not write conversational replies."
    if purpose == "embedding":
        return "Provider-reported embedding candidate; confirm that this model supports embeddings before saving it."
    if size:
        return (
            f"{size.group(1)}B generation model for conversation and other text tasks. "
            "Larger models generally need more memory and may respond more slowly."
        )
    return "Generation model reported by the configured provider; quality, speed, and memory use depend on its architecture and quantization."


def _model_field(
    *,
    safe: Callable[[Any], str],
    key: str,
    label: str,
    value: Any,
    models: list[Any],
    purpose: str,
) -> str:
    current = str(value or "").strip()
    choices = list(dict.fromkeys(
        model for model in (current, *(str(item or "").strip() for item in models)) if model
    ))
    list_id = f"lm-{key}-choices"
    options = "".join(
        f"<option value='{safe(model)}' label='{safe(_model_description(model, purpose=purpose))}'></option>"
        for model in choices
    )
    descriptions = "".join(
        f"<div><code>{safe(model)}</code><span>{safe(_model_description(model, purpose=purpose))}</span></div>"
        for model in choices
    ) or "<p class='muted'>No models were reported. Enter an exact model identifier after the provider is available.</p>"
    return (
        f"<label data-tip='Choose a reported model or enter an exact custom identifier.' for='lm-{safe(key)}'><strong>{safe(label)}</strong>"
        f"<input id='lm-{safe(key)}' name='{safe(key)}' type='text' list='{safe(list_id)}' value='{safe(current)}' "
        f"placeholder='Choose a reported model or enter its exact identifier'>"
        f"<datalist id='{safe(list_id)}'>{options}</datalist></label>"
        f"<details class='local-model-descriptions'><summary>{safe(label)} descriptions</summary>{descriptions}</details>"
    )


def render_local_model_status(
    *,
    safe: Callable[[Any], str],
    card: Callable[[str, str], str],
    layout: Callable[[str, str], str],
    return_to_chat: bool = False,
) -> str:
    """Render diagnostics and the bounded v1079.1 local-model configuration editor."""
    status = local_model_status()
    config_report = configuration_payload()
    values = config_report.get("values") or {}
    error = status.get("error") or {}
    embedding_error = status.get("embedding_error") or {}
    models = status.get("models") or []
    embedding_models = status.get("embedding_models") or []
    generation = status.get("generation") or {}
    provider_profiles_json = json.dumps(
        config_report.get("provider_profiles") or {},
        sort_keys=True,
    ).replace("<", "\\u003c")
    model_rows = "".join(f"<li><code>{safe(model)}</code></li>" for model in models) or "<li class='muted'>No generation models reported.</li>"
    embedding_rows = "".join(f"<li><code>{safe(model)}</code></li>" for model in embedding_models) or "<li class='muted'>No embedding models reported.</li>"
    error_html = ""
    if error or embedding_error:
        rows = []
        for service, item in (("generation", error), ("embedding", embedding_error)):
            if item:
                rows.append(
                    f"<p><strong>{safe(service)} / {safe(item.get('code'))}</strong>: {safe(item.get('message'))}</p>"
                )
        error_html = card("Provider errors", "".join(rows))

    provider = str(values.get("local_model_provider") or "ollama")
    provider_options = "".join(
        f"<option value='{safe(item)}'{' selected' if item == provider else ''}>{safe(item)}</option>"
        for item in ("ollama", "llama_cpp")
    )
    fields = (
        f"<label data-tip='Choose the provider contract. This does not start or install a service.' for='lm-local_model_provider'><strong>Provider</strong>"
        f"<select id='lm-local_model_provider' name='local_model_provider'>{provider_options}</select></label>"
        + _field(
            safe=safe, key="local_model_endpoint", label="Generation endpoint",
            value=values.get("local_model_endpoint", ""), placeholder="http://127.0.0.1:8080",
            tip="Generation and streaming requests use this endpoint. Existing single-endpoint configurations remain valid.",
        )
        + _model_field(
            safe=safe, key="local_model", label="Generation model",
            value=values.get("local_model", ""), models=models, purpose="generation",
        )
        + _field(
            safe=safe, key="local_model_embedding_endpoint", label="Embedding endpoint (optional)",
            value=values.get("local_model_embedding_endpoint", ""), placeholder="Leave empty to use generation endpoint",
            tip="Embedding requests use this endpoint. Empty preserves the legacy single-endpoint fallback.",
        )
        + _model_field(
            safe=safe, key="embed_model", label="Embedding model",
            value=values.get("embed_model", ""), models=embedding_models, purpose="embedding",
        )
        + _field(
            safe=safe, key="local_model_context_size", label="Context size", input_type="number",
            value=values.get("local_model_context_size", 8192), step="1", tip="Requested generation context window; must be greater than zero.",
        )
        + _field(
            safe=safe, key="local_model_connect_timeout_seconds", label="Connect timeout (seconds)", input_type="number",
            value=values.get("local_model_connect_timeout_seconds", 5.0), step="0.1", tip="Bounded HTTP connection timeout for both services.",
        )
        + _field(
            safe=safe, key="local_model_read_timeout_seconds", label="Read timeout (seconds)", input_type="number",
            value=values.get("local_model_read_timeout_seconds", 120.0), step="0.1", tip="Bounded response timeout for generation, streaming metadata, and embeddings.",
        )
        + _field(
            safe=safe, key="local_model_ollama_keep_alive_minutes", label="Ollama keep-warm minutes", input_type="number",
            value=values.get("local_model_ollama_keep_alive_minutes", 30), step="1", tip="Keep the selected Ollama generation model resident after chat activity. Zero unloads it immediately; llama.cpp ignores this setting.",
        )
        + _field(
            safe=safe, key="local_model_max_tokens", label="Maximum generated tokens", input_type="number",
            value=values.get("local_model_max_tokens", 350), step="1", tip="Default generation ceiling. Native smoke still caps itself at 32 tokens.",
        )
        + _field(
            safe=safe, key="local_model_temperature", label="Temperature", input_type="number",
            value=values.get("local_model_temperature", 0.45), step="0.01", tip="Sampling temperature from 0 through 2.",
        )
        + _field(
            safe=safe, key="local_model_top_p", label="Top-p", input_type="number",
            value=values.get("local_model_top_p", 0.9), step="0.01", tip="Nucleus sampling probability greater than 0 and at most 1.",
        )
        + _field(
            safe=safe, key="local_model_top_k", label="Top-k", input_type="number",
            value=values.get("local_model_top_k", 40), step="1", tip="Provider-supported top-k sampling value; zero disables it where supported.",
        )
        + _field(
            safe=safe, key="local_model_repeat_penalty", label="Repeat penalty", input_type="number",
            value=values.get("local_model_repeat_penalty", 1.1), step="0.01", tip="Provider-supported repetition penalty greater than zero.",
        )
    )

    editor = f"""
<div class='card' data-tip='Validated operator editor. Saving changes only settings; it never manages model files or services.'>
  <h3>Local model configuration</h3>
  <p class='muted'>Embedding endpoint is optional. Empty means use the generation endpoint, preserving every existing Ollama and single-router configuration.</p>
  <form id='local-model-config-form' class='stack'>{fields}
    <div class='inline'>
      <button id='local-model-save' type='submit' data-tip='Validate all fields and save only the bounded local-model settings.'>Save configuration</button>
      <button id='local-model-readiness' type='button' data-tip='Run bounded metadata readiness against the unsaved form values. No generation request is sent.'>Check readiness</button>
    </div>
    <label class='inline' data-tip='Native smoke sends small real requests only after this explicit confirmation.'>
      <input id='local-model-smoke-confirm' type='checkbox'> I confirm a bounded native health, generation, streaming, and embedding smoke run.
    </label>
    <button id='local-model-smoke' type='button' data-tip='Runs with zero retries, at most 32 generated tokens, and the configured endpoints. No model files are managed.'>Run native smoke</button>
    <label class='inline' data-tip='Conversation validation sends bounded synthetic conversation fixtures and stores only redacted classifications and timings.'>
      <input id='local-model-conversation-confirm' type='checkbox'> I confirm a bounded native conversational experience validation run.
    </label>
    <button id='local-model-conversation-validation' type='button' data-tip='Evaluates greetings, follow-ups, emotional and playful dialogue, continuity, operator transition, latency, cancellation, and duplication without saving raw prompts or replies.'>Validate native conversation</button>
  </form>
  <section id='local-model-availability' class='mini-card' data-provider-availability-state='unknown' aria-live='polite'>
    <strong>Provider availability</strong><span>Run the bounded readiness check to inspect the configured provider. No generation request is sent.</span>
    <small id='local-model-recovery-evidence'>No persisted configured-provider readiness evidence is loaded.</small>
  </section>
  <pre id='local-model-config-result' aria-live='polite'>Ready for operator action.</pre>
</div>
<script>
(() => {{
  const form = document.getElementById('local-model-config-form');
  const output = document.getElementById('local-model-config-result');
  const conversationValidationButton = document.getElementById('local-model-conversation-validation');
  const availabilityNode = document.getElementById('local-model-availability');
  const recoveryEvidenceNode = document.getElementById('local-model-recovery-evidence');
  const providerProfiles = {provider_profiles_json};
  let readinessConfigurationDigest = '';
  let lastAvailabilityState = '';
  let recoveryProbeTimer = null;
  let recoveryProbeCount = 0;
  let readinessRequestRunning = false;
  let conversationValidationRunning = false;
  let conversationValidationId = '';
  const recoveryProbeDelays = [5000, 10000, 20000];
  const numeric = new Set([
    'local_model_context_size', 'local_model_connect_timeout_seconds',
    'local_model_read_timeout_seconds', 'local_model_ollama_keep_alive_minutes', 'local_model_max_tokens',
    'local_model_temperature', 'local_model_top_p', 'local_model_top_k',
    'local_model_repeat_penalty'
  ]);
  const collect = () => {{
    const values = {{}};
    new FormData(form).forEach((value, key) => {{
      values[key] = numeric.has(key) ? Number(value) : String(value).trim();
    }});
    return values;
  }};
  document.getElementById('lm-local_model_provider').addEventListener('change', (event) => {{
    const profile = providerProfiles[String(event.target.value || '')] || {{}};
    Object.entries(profile).forEach(([key, value]) => {{
      const field = document.getElementById('lm-' + key);
      if (field) field.value = value == null ? '' : String(value);
    }});
    readinessConfigurationDigest = '';
    lastAvailabilityState = '';
    recoveryProbeCount = 0;
    if (recoveryProbeTimer) clearTimeout(recoveryProbeTimer);
    recoveryProbeTimer = null;
    availabilityNode.dataset.providerAvailabilityState = 'unknown';
    availabilityNode.querySelector('span').textContent = 'Provider values changed locally. Save them explicitly or run readiness against the unsaved form values.';
    if (recoveryEvidenceNode) recoveryEvidenceNode.textContent = 'Unsaved editor values do not prove that the configured conversation provider recovered.';
    output.textContent = 'Loaded the saved provider-specific settings. Save to make this provider active.';
  }});
  const issueLines = (items) => (items || []).map((item) =>
    `- ${{item.service || item.field || 'configuration'}} / ${{item.classification || item.code || 'invalid'}}: ${{item.message || ''}}`
  );
  const summarize = (payload) => {{
    if (!payload || payload.ok === false) {{
      const details = payload && payload.details;
      const errors = details && details.errors ? details.errors : [];
      return [`ERROR: ${{payload && payload.error ? payload.error : 'Request failed.'}}`, ...issueLines(errors)].join('\\n');
    }}
    const data = payload.data || payload;
    const lines = [`Status: ${{data.status || data.validation?.status || 'ok'}}`];
    const availability = data.availability || null;
    if (availability) {{
      lines.push(`Availability: ${{availability.state}} / ${{availability.label}}`);
      lines.push(`Generation available: ${{Boolean(availability.generation_available)}}`);
      lines.push(`Embedding available: ${{Boolean(availability.embedding_available)}}`);
      lines.push(`Automatic provider switch: ${{Boolean(availability.automatic_provider_switch)}}`);
      lines.push(`Automatic generation retry: ${{Boolean(availability.automatic_generation_retry)}}`);
      lines.push(`Offline tools remain available: ${{(availability.offline_capabilities || []).join(', ')}}`);
    }}
    if (data.generation_endpoint) lines.push(`Generation endpoint: ${{data.generation_endpoint}}`);
    if (data.embedding_endpoint) lines.push(`Embedding endpoint: ${{data.embedding_endpoint}}`);
    if (data.embedding_endpoint_uses_generation_fallback !== undefined) lines.push(`Legacy endpoint fallback: ${{data.embedding_endpoint_uses_generation_fallback}}`);
    if (data.configuration_digest) lines.push(`Configuration digest: ${{data.configuration_digest}}`);
    if (data.configuration_drift && data.configuration_drift.status) lines.push(`Configuration drift: ${{data.configuration_drift.status}}`);
    if (data.evidence_receipt) lines.push(`Evidence receipt: ${{data.evidence_receipt.receipt_type}} / ${{data.evidence_receipt.result}} / ${{data.evidence_receipt.evidence_source}} / native evidence: ${{Boolean(data.evidence_receipt.native_provider_evidence)}}`);
    if (data.persisted_recovery_evidence) lines.push(`Persisted recovery evidence: ${{data.persisted_recovery_evidence.state}} / ${{data.persisted_recovery_evidence.settings_scope}} / checked ${{data.persisted_recovery_evidence.checked_at}} / recovery proven: ${{Boolean(data.persisted_recovery_evidence.recovery_proven)}}`);
    if (data.generation_model) lines.push(`Generation model: ${{data.generation_model}} (available: ${{data.generation_model_available}})`);
    if (data.embedding_model) lines.push(`Embedding model: ${{data.embedding_model}} (available: ${{data.embedding_model_available}})`);
    (data.checks || []).forEach((item) => lines.push(`- ${{item.status}}: ${{item.name}} [${{item.service || 'combined'}}]`));
    if (data.scenarios) {{
      lines.push(`Scenarios: ${{data.scenarios_completed || 0}}/${{data.scenarios_planned || 0}}`);
      data.scenarios.forEach((item) => lines.push(`- ${{item.status}}: ${{item.scenario_id}} / ${{item.classification?.kind || 'unknown'}} / first visible ${{item.timings_ms?.first_visible_token ?? item.timings_ms?.first_token ?? 'n/a'}} ms / transport ${{item.timings_ms?.first_transport_chunk ?? 'n/a'}} ms / total ${{item.timings_ms?.total ?? 'n/a'}} ms / continuity ${{item.quality_checks?.continuity_signal ?? 'n/a'}}`));
      const cancellation = data.recovery && data.recovery.cancellation;
      if (cancellation) lines.push(`Cancellation: ${{cancellation.completion_state || cancellation.status || 'not run'}}`);
      lines.push(`Redacted evidence: ${{data.evidence_path || 'not persisted'}}`);
    }}
    lines.push(...issueLines(data.issues));
    (data.guidance || []).forEach((item) => lines.push(`Guidance: ${{item}}`));
    if (data.validation && data.validation.errors) lines.push(...issueLines(data.validation.errors));
    return lines.join('\\n');
  }};
  function renderAvailability(availability) {{
    if (!availability) return;
    const observed = String(availability.observed_state || availability.state || 'unknown');
    lastAvailabilityState = observed;
    availabilityNode.dataset.providerAvailabilityState = String(availability.state || observed);
    availabilityNode.querySelector('strong').textContent = String(availability.label || 'Provider availability');
    availabilityNode.querySelector('span').textContent = String(availability.detail || 'Readiness completed.');
    if (availability.recovered || availability.state === 'ready') recoveryProbeCount = 0;
  }}
  function renderRecoveryEvidence(evidence, cue) {{
    if (!recoveryEvidenceNode) return;
    if (!evidence) {{
      recoveryEvidenceNode.textContent = 'No persisted configured-provider readiness evidence is available.';
      return;
    }}
    const scope = String(evidence.settings_scope || 'unknown');
    const checked = String(evidence.checked_at || 'time unavailable');
    const proven = Boolean(evidence.recovery_proven);
    recoveryEvidenceNode.textContent = proven
      ? `Configured-provider recovery verified at ${{checked}}. Composition may resume explicitly; no earlier request was replayed.`
      : `Readiness persisted at ${{checked}} for ${{scope}} values. ${{cue && cue.detail ? cue.detail : 'Configured-provider recovery is not proven.'}}`;
  }}
  function scheduleRecoveryProbe(availability) {{
    if (recoveryProbeTimer) clearTimeout(recoveryProbeTimer);
    recoveryProbeTimer = null;
    if (!availability || !availability.readiness_retry_allowed || recoveryProbeCount >= recoveryProbeDelays.length) return;
    const delay = recoveryProbeDelays[recoveryProbeCount];
    recoveryProbeTimer = setTimeout(() => {{
      recoveryProbeTimer = null;
      if (document.hidden || readinessRequestRunning) {{
        recoveryProbeTimer = setTimeout(() => {{ recoveryProbeTimer = null; scheduleRecoveryProbe(availability); }}, 1000);
        return;
      }}
      recoveryProbeCount += 1;
      runReadiness(true);
    }}, delay);
  }}
  const post = async (url, body, options) => {{
    const settings = options || {{}};
    const controller = new AbortController();
    const timeoutMs = Number(settings.timeoutMs || 60000);
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    if (!settings.quiet) output.textContent = 'Running bounded local check...';
    try {{
      const response = await fetch(url, {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(body), signal: controller.signal}});
      const payload = await response.json();
      output.textContent = summarize(payload);
      return payload;
    }} catch (error) {{
      output.textContent = error && error.name === 'AbortError'
        ? 'The bounded dashboard request timed out. No provider, model, setting, or generation request was changed or replayed.'
        : 'Request failed before a structured response was received. Confirm the local dashboard service is still running.';
      return null;
    }} finally {{
      clearTimeout(timer);
    }}
  }};
  async function runReadiness(automaticRecovery) {{
    if (readinessRequestRunning) return null;
    readinessRequestRunning = true;
    availabilityNode.dataset.providerAvailabilityState = automaticRecovery ? 'recovering' : 'checking';
    availabilityNode.querySelector('strong').textContent = automaticRecovery ? 'Checking whether the configured provider recovered' : 'Checking configured provider';
    availabilityNode.querySelector('span').textContent = 'Bounded metadata check only. No generation request, provider switch, model management, or settings mutation is occurring.';
    try {{
      const payload = await post('/api/local-model/readiness', {{settings: collect(), previous_state: lastAvailabilityState || null, recovery_trigger: automaticRecovery ? 'visibility_recovery' : 'manual_check'}}, {{timeoutMs: 15000, quiet: automaticRecovery}});
      const data = payload && payload.ok !== false ? (payload.data || payload) : null;
      if (data) {{
        readinessConfigurationDigest = data.configuration_digest || '';
        renderAvailability(data.availability || null);
        renderRecoveryEvidence(data.persisted_recovery_evidence || null, data.provider_resume_cue || null);
        scheduleRecoveryProbe(data.availability || null);
      }}
      return payload;
    }} finally {{
      readinessRequestRunning = false;
    }}
  }};
  form.addEventListener('submit', async (event) => {{
    event.preventDefault();
    readinessConfigurationDigest = '';
    await post('/api/local-model/configuration', {{settings: collect()}});
  }});
  document.getElementById('local-model-readiness').addEventListener('click', () => runReadiness(false));
  const query = new URLSearchParams(window.location.search);
  if (query.get('run_readiness') === '1') runReadiness(false);
  conversationValidationButton.addEventListener('click', async () => {{
    if (!document.getElementById('local-model-conversation-confirm').checked) {{
      output.textContent = 'Native conversation validation was not run. Explicit confirmation is required.';
      return;
    }}
    if (conversationValidationRunning) {{
      output.textContent = 'Native conversation validation is already running. No duplicate request was sent.';
      return;
    }}
    conversationValidationRunning = true;
    conversationValidationButton.disabled = true;
    if (!conversationValidationId) {{
      conversationValidationId = 'native_conversation_dashboard_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 10);
    }}
    try {{
      const payload = await post('/api/local-model/native-conversation-validation', {{
        settings: collect(),
        confirm: 'RUN_NATIVE_CONVERSATION_VALIDATION',
        timeout_seconds: 45,
        first_token_budget_ms: 8000,
        total_budget_ms: 30000,
        validation_id: conversationValidationId
      }}, {{timeoutMs: 60000}});
      if (payload) conversationValidationId = '';
    }} finally {{
      conversationValidationRunning = false;
      conversationValidationButton.disabled = false;
    }}
  }});
  document.getElementById('local-model-smoke').addEventListener('click', () => {{
    if (!document.getElementById('local-model-smoke-confirm').checked) {{
      output.textContent = 'Native smoke was not run. Explicit confirmation is required.';
      return;
    }}
    post('/api/local-model/native-smoke', {{settings: collect(), confirm: 'RUN_NATIVE_MODEL_SMOKE', timeout_seconds: 30, readiness_configuration_digest: readinessConfigurationDigest || null}}, {{timeoutMs: 45000}});
  }});
}})();
</script>
"""

    return_card = (
        card("Return to conversation", "<p>Your selected conversation and its private draft were left unchanged.</p><p><a href='/chat-console'>Return to Eidolon</a></p>")
        if return_to_chat else ""
    )
    body = (
        "<h1>Local Model Configuration and Status</h1>"
        "<p class='muted'>Provider-neutral settings for the real conversation and embedding paths. "
        "Model installation, deletion, replacement, and service startup remain explicit operator actions.</p>"
        + return_card
        + "<div class='grid'>"
        + card("Provider", f"<div class='kpi'>{safe(status.get('provider'))}</div>")
        + card("Generation service", f"<div class='kpi'>{safe(status.get('status'))}</div><p><code>{safe(status.get('endpoint'))}</code></p><p>Available: {safe(status.get('service_available'))}</p>")
        + card("Embedding service", f"<div class='kpi'>{safe('healthy' if status.get('embedding_service_available') else 'unavailable')}</div><p><code>{safe(status.get('embedding_endpoint') or config_report.get('effective_embedding_endpoint'))}</code></p><p>Available: {safe(status.get('embedding_service_available'))}</p>")
        + card("Generation model", f"<div class='kpi'>{safe(status.get('configured_model'))}</div><p>Available: {safe(status.get('model_available'))}</p>")
        + card("Embedding model", f"<div class='kpi'>{safe(status.get('configured_embed_model'))}</div><p>Available: {safe(status.get('embed_model_available'))}</p>")
        + card("Generation limits", f"<p>Context: {safe(generation.get('context_size'))}</p><p>Max tokens: {safe(generation.get('max_tokens'))}</p><p>Temperature: {safe(generation.get('temperature'))}</p>")
        + "</div>"
        + error_html
        + editor
        + "<div class='grid'>"
        + card("Generation models", f"<ul>{model_rows}</ul>")
        + card("Embedding models", f"<ul>{embedding_rows}</ul>")
        + "</div>"
        + card("Safety boundary", "<p>Saving settings does not install, download, delete, replace, start, or stop models. Native smoke and conversation validation require explicit confirmation and grant no approval, release, or autonomous authority.</p>")
    )
    return layout("/local-model", body)

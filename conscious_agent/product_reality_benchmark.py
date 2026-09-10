from __future__ import annotations

"""Read-only v1100 product benchmark and the next 50-release roadmap."""

from copy import deepcopy
import hashlib
import json
from typing import Any


BENCHMARK_VERSION = "1100.0"
BENCHMARK_NAME = "Product Reality Benchmark"
ROADMAP_START = "1101.0"
ROADMAP_END = "1105.9"
ROADMAP_RELEASE_COUNT = 50

_ROADMAP_ARCS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "1101",
        "Fast, Coherent First Use",
        (
            "Cold-start budget truth",
            "Lazy dashboard shell",
            "Deferred administrative loading",
            "Active-project self-description repair",
            "Startup progress and failure recovery",
            "Warm and cold restart parity",
            "Windows startup soak",
            "Source and runtime migration guidance",
            "Ordinary-launch usability",
            "First-use coherence checkpoint",
        ),
    ),
    (
        "1102",
        "Natural Conversation",
        (
            "Identity and relationship prompt foundation",
            "Greeting and repetition suppression",
            "Intent and topic continuity",
            "Corrections and preference propagation",
            "Affection and nickname boundaries",
            "Response length and depth matching",
            "Native conversation quality evaluation",
            "Provider-neutral conversation tuning",
            "Long-conversation personality stability",
            "Natural conversation checkpoint",
        ),
    ),
    (
        "1103",
        "Reliable Instant Messaging",
        (
            "First-visible-token timing",
            "Enter, Shift+Enter, IME, and remote keyboard input",
            "Exactly-once send and provider request",
            "Scroll anchoring and jump-to-latest",
            "Conversation switching and draft continuity",
            "Provider outage and return",
            "Cancellation, retry, and late-result reconciliation",
            "Multi-tab ownership and stale-tab recovery",
            "Long-session messaging soak",
            "Messaging reliability checkpoint",
        ),
    ),
    (
        "1104",
        "Conversational Action Portal",
        (
            "Conversation and action intent classification",
            "Bounded operator-visible tool catalog",
            "Action proposal and explanation cards",
            "Maintenance check through chat",
            "Live action progress and cancellation",
            "Result summaries and conversational follow-up",
            "Failure recovery and explicit retry",
            "Approval policy and operator preference controls",
            "Action safety and native-provider validation",
            "Conversational action checkpoint",
        ),
    ),
    (
        "1105",
        "Daily-Use Alpha Consolidation",
        (
            "Unified companion overview",
            "Memory browse, correction, retraction, and deletion",
            "Project-aware conversational actions",
            "Companion and work-context transitions",
            "Backup, restore, and recovery rehearsal",
            "Desktop installer readiness",
            "CPU, memory, disk, and latency budgets",
            "Accessibility, narrow layout, and remote-use polish",
            "Multi-day Windows daily-use soak",
            "Daily-use alpha checkpoint",
        ),
    ),
)

_AREAS: tuple[dict[str, Any], ...] = (
    {
        "id": "release_and_metadata_integrity",
        "status": "established",
        "evidence": "Explicit version roles, candidate identity, archive coherence, installation, promotion, certification, and consumer-use lifecycles are implemented and fixture-covered.",
        "remaining_gap": "Keep these systems stable while product work resumes.",
    },
    {
        "id": "source_runtime_separation",
        "status": "established",
        "evidence": "Source-only privacy rules and external mutable-runtime storage are implemented.",
        "remaining_gap": "Recheck every produced archive; privacy success is not release authority.",
    },
    {
        "id": "windows_startup_and_process_reliability",
        "status": "established_after_review_repair",
        "evidence": "Python 3.11 compilation passes; three cold Windows health responses completed in 1.892-3.001 seconds against a 15-second target.",
        "remaining_gap": "Complete ordinary-launch and long-session Windows soaks after packaging.",
    },
    {
        "id": "conversation_transport_and_session_continuity",
        "status": "fixture_covered_requires_daily_soak",
        "evidence": "Session, draft, navigation, multi-tab, retry, cancellation, and recovery fixtures exist.",
        "remaining_gap": "Prove the ordinary IM experience over repeated real local-model use.",
    },
    {
        "id": "natural_conversation_quality",
        "status": "requires_native_evidence",
        "evidence": "Quality, context, personality, relationship, and correction systems exist.",
        "remaining_gap": "Real provider conversations must demonstrate less repetition, stronger direct answers, and stable warmth.",
    },
    {
        "id": "conversational_action_portal",
        "status": "partially_established",
        "evidence": "Safe chat-action routing, approvals, diagnostics, tasks, patches, and command boundaries exist.",
        "remaining_gap": "Ordinary requests such as a maintenance check do not yet form one coherent conversational workflow.",
    },
    {
        "id": "self_development",
        "status": "supervised_only",
        "evidence": "Planning, maintenance, task, patch, test, verification, rollback, and release components exist.",
        "remaining_gap": "Eidolon does not yet independently complete the full choose-plan-code-test-review-apply loop.",
    },
    {
        "id": "native_desktop_product",
        "status": "not_established",
        "evidence": "The product remains a localhost dashboard with launcher and desktop-support foundations.",
        "remaining_gap": "Installer, native shell, update flow, resource budgets, and multi-day soak remain future work.",
    },
)


def build_roadmap() -> list[dict[str, str]]:
    releases: list[dict[str, str]] = []
    for arc, arc_title, titles in _ROADMAP_ARCS:
        for patch, title in enumerate(titles):
            releases.append(
                {
                    "version": f"{arc}.{patch}",
                    "arc": arc_title,
                    "bundle": "A" if patch <= 2 else "B" if patch <= 5 else "C" if patch <= 8 else "checkpoint",
                    "title": title,
                }
            )
    return releases


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def build_product_reality_benchmark() -> dict[str, Any]:
    roadmap = build_roadmap()
    areas = deepcopy(list(_AREAS))
    status_counts: dict[str, int] = {}
    for area in areas:
        status = str(area["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    report: dict[str, Any] = {
        "type": "eidolon_product_reality_benchmark",
        "schema_version": "1",
        "version": BENCHMARK_VERSION,
        "name": BENCHMARK_NAME,
        "status": "benchmark_complete",
        "product_stage": "desktop_alpha_development",
        "development_direction": "user_visible_daily_use",
        "summary": "The safety and release foundation is substantial. Daily conversation, conversational actions, full self-development, and a native desktop product remain incomplete.",
        "area_count": len(areas),
        "areas": areas,
        "status_counts": status_counts,
        "roadmap_start": ROADMAP_START,
        "roadmap_end": ROADMAP_END,
        "roadmap_release_count": len(roadmap),
        "roadmap": roadmap,
        "next_release": ROADMAP_START,
        "operator_promotion_required": True,
        "provider_invoked": False,
        "runtime_state_read": False,
        "runtime_state_written": False,
        "source_modified": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "autonomy_claimed": False,
        "content_free": True,
    }
    report["areas_digest"] = _digest(areas)
    report["roadmap_digest"] = _digest(roadmap)
    report["benchmark_digest"] = _digest(report)
    return report


def product_reality_benchmark_contains_private_fields(value: Any) -> bool:
    private_tokens = {
        "prompt",
        "response",
        "conversation",
        "memory",
        "secret",
        "token",
        "private_note",
        "provider_payload",
        "absolute_path",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in private_tokens or normalized.endswith("_path"):
                return True
            if product_reality_benchmark_contains_private_fields(item):
                return True
    elif isinstance(value, list):
        return any(product_reality_benchmark_contains_private_fields(item) for item in value)
    return False

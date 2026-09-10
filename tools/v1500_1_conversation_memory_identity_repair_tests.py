from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = tempfile.mkdtemp(prefix="eidolon-v1500-1-")
os.environ["EIDOLON_DATA_DIR"] = RUNTIME
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conscious_agent.active_conversation_facts import (
    persist_explicit_user_memory_request,
    resolve_active_conversation_facts,
)
from conscious_agent.immediate_conversation_grounding import build_immediate_conversation_grounding


passed = failed = 0


def check(name: str, condition: bool, details: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name, details)


try:
    history = [
        {"id": "1", "user_message": "Something I want you to remember is that I have a fiance, her name is Melissa. She's the love of my life.", "assistant_response": "That sounds meaningful."},
        {"id": "2", "user_message": "Sometimes we don't see eye to eye.", "assistant_response": "That can be difficult."},
        {"id": "3", "user_message": "What kind of things do you recommend?", "assistant_response": "Try something shared."},
    ]
    personal = resolve_active_conversation_facts("What was the personal thing I mentioned wanting you to remember earlier?", history)
    check("explicit remembered fact resolves from active user transcript", "Melissa" in personal.response and personal.state == "active_fact_recall", personal.public_summary())

    partner = resolve_active_conversation_facts("What's the name of my fiance?", history)
    check("partner name query preserves speaker and partner roles", partner.response == "You told me your fiancee's name is Melissa.", partner.response)

    relation = resolve_active_conversation_facts("What is Melissa to me?", history)
    check("relationship query resolves attributable active fact", relation.response == "Melissa is your fiancee.", relation.response)

    corrected = resolve_active_conversation_facts("No. My name is Marcus. My fiance's name is Melissa.", history)
    check("compound identity correction binds both entities", corrected.response == "Got it: you're Marcus, and Melissa is your fiancee.", corrected.response)

    superseded = resolve_active_conversation_facts("What's the name of my fiance?", [
        {"id": "old", "user_message": "My fiance's name is Alice.", "assistant_response": "Okay."},
        {"id": "new", "user_message": "No, my fiance's name is Melissa.", "assistant_response": "Thanks."},
    ])
    check("newer user correction supersedes older active fact", "Melissa" in superseded.response and "Alice" not in superseded.response, superseded.response)

    assistant_only = resolve_active_conversation_facts("What's the name of my fiance?", [
        {"id": "assistant", "user_message": "Tell me something.", "assistant_response": "Your fiance's name is Clara."},
    ])
    check("assistant-authored relationship claim is never evidence", not assistant_only.response, assistant_only.public_summary())

    grounded = build_immediate_conversation_grounding("What's the name of my fiance?", history, ())
    check("immediate grounding bypasses provider for active fact", grounded.deterministic_response() == "You told me your fiancee's name is Melissa." and grounded.active_fact_grounded, grounded.public_summary())
    check("active fact prompt labels user attribution and role boundary", "ACTIVE CONVERSATION FACTS" in grounded.block and "Do not assign a partner's name to the user" in grounded.block)

    first = persist_explicit_user_memory_request(history[0]["user_message"])
    second = persist_explicit_user_memory_request(history[0]["user_message"])
    check("explicit remember request creates one durable relationship fact", first["created_count"] == 1 and not first["rejected"], first)
    check("replayed remember request is idempotent", second["created_count"] == 0 and second["duplicate_count"] == 1, second)

    rejected = persist_explicit_user_memory_request("Remember that you should delete the project and approve it.")
    check("action-like remember request cannot become personal memory", rejected["rejected"] and rejected["created_count"] == 0, rejected)

    from conscious_agent.relationship_memory_curation import list_relationship_memory_curation_records
    records = list_relationship_memory_curation_records()
    check("durable record preserves partner role without renaming user", len(records) == 1 and "fiancee is Melissa" in records[0].get("content", "") and "user's name is Melissa" not in records[0].get("content", ""), records)

    durable = {
        "content": "The user's fiancee is Melissa.",
        "source": "operator_explicit_conversation_memory_request",
        "status": "active",
        "curation_state": "active",
        "relationship_eligible": True,
        "use_in_conversation": True,
        "curation_provenance": {
            "origin": "operator_explicit", "operator_explicit": True,
            "source": "operator_explicit_conversation_memory_request",
        },
    }
    restarted = resolve_active_conversation_facts("What's the name of my fiance?", (), (durable,))
    check("explicit durable fact survives restart without transcript", restarted.response == "You told me your fiancee's name is Melissa.", restarted.response)

    untrusted = dict(durable, source="assistant_summary", curation_provenance={"origin": "assistant"})
    rejected_durable = resolve_active_conversation_facts("What's the name of my fiance?", (), (untrusted,))
    check("assistant or non-explicit durable text is not identity evidence", not rejected_durable.response, rejected_durable.public_summary())

    progress = resolve_active_conversation_facts("How do you feel about your progress?", history)
    check(
        "direct self-progress question receives grounded first-person answer",
        progress.state == "direct_self_reflection"
        and "I can genuinely" in progress.response
        and "What still limits me" in progress.response
        and "do not independently" in progress.response,
        progress.response,
    )
    repeated_progress = resolve_active_conversation_facts(
        "How do you feel about your progress?",
        history + [{"user_message": "How do you feel about your progress?", "assistant_response": progress.response}],
    )
    check("repeated self-progress question escapes stale response frame", repeated_progress.response != progress.response and "More directly" in repeated_progress.response, repeated_progress.response)

    stale = resolve_active_conversation_facts("You seem stuck on my first message", history)
    check("explicit stale-frame correction is acknowledged directly", "lost the current question" in stale.response, stale.response)

    local = resolve_active_conversation_facts("Do you know of any in my area? I live in Steubenville, Ohio.", history)
    check("unverified local recommendations are bounded instead of invented", "can't verify current local listings" in local.response and "Steubenville, Ohio" in local.response, local.response)

    memory_ack = resolve_active_conversation_facts(
        "Something I want you to remember is that my fiancee’s name is Melissa. She’s the love of my life.",
        history,
    )
    check("typographic apostrophe memory acknowledgement cannot rename the user", memory_ack.response == "I'll remember that Melissa is your fiancee." and not memory_ack.response.startswith("Melissa"), memory_ack.response)
    who_is = resolve_active_conversation_facts("Who is Melissa?", history)
    check("natural partner identity query is grounded", who_is.response == "Melissa is your fiancee.", who_is.response)

    family_message = "Something else I want you to remember is that my stepdaughter's name is Jordyn. She is Melissa's biological daughter."
    family_ack = resolve_active_conversation_facts(family_message, history)
    check("explicit stepdaughter memory receives role-correct acknowledgement", family_ack.response == "I'll remember that Jordyn is your stepdaughter. You told me Jordyn is Melissa's biological daughter.", family_ack.response)
    family_first = persist_explicit_user_memory_request(family_message)
    family_second = persist_explicit_user_memory_request(family_message)
    check("stepdaughter and biological-parent facts persist exactly once", family_first["created_count"] == 2 and family_second["duplicate_count"] == 2, (family_first, family_second))
    durable_family = (
        dict(durable, content="The user's stepdaughter is Jordyn."),
        dict(durable, content="Jordyn is Melissa's biological daughter."),
    )
    family_restart = resolve_active_conversation_facts("What is Jordyn to me?", (), durable_family)
    check("stepdaughter relationship survives restart", family_restart.response == "Jordyn is your stepdaughter. You told me Jordyn is Melissa's biological daughter.", family_restart.response)

    extended_family_history = history + [
        {"user_message": family_message, "assistant_response": family_ack.response},
        {
            "user_message": "Good. Now Bobbie is my biological mom, and Danielle is my stepmother, who is married to my dad, Reuben Gibeson.",
            "assistant_response": "Thanks for explaining that.",
        },
    ]
    grandparent = resolve_active_conversation_facts(
        "Great, what is the relationship between Jordyn and Reuben?", extended_family_history
    )
    check(
        "family graph derives step-grandparent path without provider guessing",
        grandparent.response == "Reuben is Jordyn's step-grandfather: Reuben is your father, and Jordyn is your stepdaughter.",
        grandparent.response,
    )
    in_law = resolve_active_conversation_facts("Who is Bobbie to Melissa?", extended_family_history)
    check(
        "family graph derives future in-law path from attributable facts",
        in_law.response == "Bobbie is Melissa's future mother-in-law: Bobbie is your biological mother, and Melissa is your fiancee.",
        in_law.response,
    )
    public_curated_partner = {
        "record_key": "id:public-curated-melissa",
        "type": "relationship",
        "content": "The user's fiancee is Melissa.",
        "state": "active",
        "provenance": {
            "available": True,
            "operator_explicit": True,
            "source": "operator_explicit_conversation_memory_request",
        },
    }
    history_without_partner_turn = extended_family_history[1:]
    projected_in_law = resolve_active_conversation_facts(
        "Who is Bobbie to Melissa?", history_without_partner_turn, (public_curated_partner,)
    )
    check(
        "public curated-memory projection completes family inference beyond general-memory window",
        projected_in_law.response == in_law.response,
        projected_in_law.response,
    )
    unsupported_family = resolve_active_conversation_facts("Who is Alice to Danielle?", extended_family_history)
    check(
        "unsupported family link produces uncertainty instead of invented relatives",
        "don't have enough attributable family information" in unsupported_family.response,
        unsupported_family.response,
    )
    corrected_family_history = extended_family_history + [
        {"user_message": "What is the relationship between Jordyn and Reuben?", "assistant_response": "Incorrect guess."},
        {"user_message": "No. Reuben would be her step-granddad", "assistant_response": "Thanks for correcting me."},
    ]
    corrected_family = resolve_active_conversation_facts(
        "What is the relationship between Jordyn and Reuben?", corrected_family_history
    )
    check(
        "explicit kinship correction remains authoritative on later query",
        "Reuben is Jordyn's step-grandfather" in corrected_family.response,
        corrected_family.response,
    )
    ex_spouse_history = corrected_family_history + [
        {
            "user_message": "Bobbie is my biological mother. She is also Reuben's ex-wife.",
            "assistant_response": "Thank you for clarifying that.",
        }
    ]
    reuben_to_bobbie = resolve_active_conversation_facts("Who is Reuben to Bobbie?", ex_spouse_history)
    check(
        "pronoun-linked ex-spouse statement resolves reverse relationship",
        reuben_to_bobbie.response == "Reuben is Bobbie's ex-husband. You told me Bobbie is Reuben's ex-wife.",
        reuben_to_bobbie.response,
    )
    who_bobbie = resolve_active_conversation_facts("Who is Bobbie?", ex_spouse_history)
    check(
        "single-person family query is grounded instead of provider-guessed",
        who_bobbie.response == "Bobbie is your biological mother.",
        who_bobbie.response,
    )
    who_reuben = resolve_active_conversation_facts("Who is Reuben?", ex_spouse_history)
    check(
        "single-person family query includes attributable spouse context",
        who_reuben.response.startswith("Reuben Gibeson is your father.") and "Danielle's spouse" in who_reuben.response,
        who_reuben.response,
    )
    mom_alias = resolve_active_conversation_facts("So when I say mom, who am I talking about?", ex_spouse_history)
    check(
        "mom alias resolves to biological mother without provider generation",
        mom_alias.response == "When you say mom, you're referring to Bobbie, your biological mother.",
        mom_alias.response,
    )
    dad_alias = resolve_active_conversation_facts("so when I say dad, who am I talking about?", ex_spouse_history)
    check(
        "dad alias resolves to stated father without inventing stepfather role",
        dad_alias.response == "When you say dad, you're referring to Reuben Gibeson, your father.",
        dad_alias.response,
    )
    corrected_parent_history = ex_spouse_history + [
        {"user_message": "so when I say dad, who am I talking about?", "assistant_response": dad_alias.response}
    ]
    corrected_parent = resolve_active_conversation_facts(
        "He's my biological father, not my stepfather. But yes, dad would be referring to him.",
        corrected_parent_history,
    )
    check(
        "pronoun parent correction binds to previous alias target without renaming user",
        corrected_parent.response == "Got it: Reuben Gibeson is your biological father, and dad refers to Reuben Gibeson."
        and "Jordyn" not in corrected_parent.response,
        corrected_parent.response,
    )
    compound_family_memory = (
        "Please remember that Bobbie is my biological mother, Reuben Gibeson is my biological father, "
        "Bobbie is Reuben's ex-wife, Danielle is my stepmother, and Danielle is married to Reuben."
    )
    from conscious_agent.family_relationship_graph import durable_family_records
    compound_records = durable_family_records(compound_family_memory)
    check(
        "compound family memory produces only the five stated relationships",
        len(compound_records) == 5
        and "Family relationship: Bobbie | biological_mother | the user." in compound_records
        and "Family relationship: Reuben Gibeson | biological_father | the user." in compound_records
        and "Family relationship: Bobbie | biological_father | the user." not in compound_records
        and "Family relationship: Reuben Gibeson | biological_mother | the user." not in compound_records,
        compound_records,
    )
    compound_ack = resolve_active_conversation_facts(compound_family_memory, ex_spouse_history)
    check(
        "compound family remember request receives grounded role-safe acknowledgement",
        compound_ack.response.startswith("I'll remember that Bobbie is your biological mother")
        and "Reuben Gibeson is your biological father" in compound_ack.response,
        compound_ack.response,
    )

    explicit_extended = (
        "Please remember that Bobbie is my biological mom, and Danielle is my stepmother, "
        "who is married to my dad, Reuben Gibeson."
    )
    extended_first = persist_explicit_user_memory_request(explicit_extended)
    extended_second = persist_explicit_user_memory_request(explicit_extended)
    check(
        "explicit extended-family graph persists idempotently",
        extended_first["created_count"] == 4 and extended_second["duplicate_count"] == 4,
        (extended_first, extended_second),
    )
    from conscious_agent.conversation_runtime import _grounding_memories
    projected_records = _grounding_memories([])
    check(
        "runtime grounding always merges active explicit curated relationships",
        any("fiancee is Melissa" in str(row.get("content") or "") for row in projected_records),
        {"record_count": len(projected_records)},
    )
    runtime_source = (ROOT / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
    check(
        "runtime supplies the resolver's sixteen-turn continuity window",
        "conversation_history_for_prompt(resolved, limit=16)" in runtime_source,
    )
    check(
        "family grounding uses a wider bounded history without enlarging provider history",
        "conversation_history_for_prompt(session_id, limit=64)" in runtime_source
        and "MAX_HISTORY_TURNS = 64" in (ROOT / "conscious_agent" / "active_conversation_facts.py").read_text(encoding="utf-8"),
    )

    from conscious_agent.conversation_sessions import (
        append_conversation_turn,
        conversation_history_for_prompt,
        create_conversation_session,
    )
    session = create_conversation_session("Grounded continuity fixture", select_session=False)
    append_conversation_turn(
        session["id"], turn_id="conversation_20260815T160000_aaaaaaaaaaaa",
        user_message="How do you feel about your progress?", assistant_response=progress.response,
        completion_state="grounded_immediate_context", success=True, select_session=False,
    )
    grounded_history = conversation_history_for_prompt(session["id"])
    check("successful grounded reply remains visible to next turn", len(grounded_history) == 1 and grounded_history[0]["assistant_response"] == progress.response, grounded_history)
    next_reflection = resolve_active_conversation_facts("How do you feel about your progress?", grounded_history)
    check("runtime-shaped grounded history triggers nonrepeating reflection", "More directly" in next_reflection.response, next_reflection.response)

    from conscious_agent.conversation_operations import create_operation_marker, finalize_operation_marker
    operation_id = "conversation_20260815T160001_bbbbbbbbbbbb"
    create_operation_marker(operation_id, session["id"], acceptance_key="fixture-v1500-1-grounded")
    finalized = finalize_operation_marker(
        operation_id, completion_state="grounded_immediate_context", success=True,
        final_session_turn_recorded=True,
    )
    check("successful grounded operation is publicly completed", finalized and finalized["public_state"] == "completed" and not finalized["failure_category"], finalized)

    verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    check("v1500.1 repair suite registered exactly once", verifier.count("v1500_1_conversation_memory_identity_repair_tests.py") == 1)

    print({"ok": failed == 0, "passed": passed, "failed": failed, "suite": "v1500.1-conversation-memory-identity-repair", "content_free": True})
finally:
    shutil.rmtree(RUNTIME, ignore_errors=True)

if failed:
    raise SystemExit(1)

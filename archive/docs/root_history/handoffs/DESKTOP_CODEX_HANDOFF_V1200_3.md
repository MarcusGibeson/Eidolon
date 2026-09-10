# Windows / Desktop Codex Handoff: v1200.3 Development Candidate

Review `Eidolon_v1200_3_development_candidate_source_only.zip` only in a disposable Windows location. Verify the published SHA-256 before extraction, extract beneath exactly one `Eidolon/` root, and do not promote it over the v1200.0 operator baseline.

Verify:

1. Launch the dashboard and open **Development Proposals** or the **Chat Console**.
2. Send `Build me a to-do webpage` in ordinary chat.
3. Confirm one proposal appears with `awaiting_approval`, a request digest, revision digest, target mode, medium risk, and no raw request path in the public card.
4. Refresh the browser, open a second tab, and resend the same request. Confirm the same proposal id and revision are resumed rather than duplicated.
5. Reply with the exact phrase shown by Eidolon: `Approve development proposal <id> revision <n>.`
6. Confirm approval is recorded once, the lifecycle becomes `approved_pending_grounded_specification`, and no provider request, workspace, generated file, command, selected-project edit, or source edit occurs.
7. Repeat the approval phrase. Confirm it is reported as already consumed and is not consumed twice.
8. Create separate proposals and verify exact rejection and cancellation controls.
9. Verify a stale revision cannot be approved after the proposal is revised.
10. Verify `Build a browser extension`, `Build me a mobile app`, `Modify Eidolon source`, and `Install a new model` create understandable unsupported or authority-blocked proposals instead of pretending to execute. Confirm `Modify source code in the selected website` remains a supported supervised proposal.
11. Narrow the browser below roughly 760 px and confirm proposal cards collapse to one column with full-width lifecycle controls.
12. Run the retained calculator benchmark and confirm its separately approved isolated workspace still passes Node/JavaScript validation.

Expected boundaries: runtime records remain outside the source tree; public evidence is digest-only; v1200.0 remains the installed and operator-promoted baseline; this v1200.3 artifact is a development candidate only.

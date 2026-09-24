"""G-ROUTE3 corpus authoring, part 2 (round 2): grounded research and hierarchical synthesis.

Research sub-skills (each corpus covers all eight exactly once; no cell repeats one across A and B):
  S1 positive under a lineage-count rule   S2 direct contradiction      S3 other-subject source -> unaddressed
  S4 same-lineage repetition                S5 conflict left unresolved  S6 narrower-scope source
  S7 conflict settled by a stated rule      S8 quantitative contradiction
  A: R1 {S2,S3}  R2 {S4,S5}  R3 {S1,S6}  R4 {S8,S7}
  B: R1 {S1,S8}  R2 {S6,S7}  R3 {S2,S5}  R4 {S3,S4}
Every research fixture has two claims, so difficulty is matched within each cell.
"""
from author_g3_part1 import RESEARCH_CODES, RESEARCH_RULES, SYNTH_RULES, add


def research(corpus, fid, risk, title, task, rule, recs, claims, sources, gold_claims, rec, uncertainties,
             pattern, domain, rationale):
    inp = {"decision_rule": rule, "allowed_recommendations": recs, "allowed_uncertainty_codes": RESEARCH_CODES,
           "claims": [{"claim_id": cid, "text": text} for cid, text in claims],
           "sources": [{"source_id": sid, "lineage": lin, "text": text} for sid, lin, text in sources]}
    lineage = {sid: lin for sid, lin, _ in sources}
    expected = {"claims": [{"claim_id": cid, "status": status, "citations": list(cites),
                            "lineages": sorted({lineage[c] for c in cites})} for cid, status, cites in gold_claims],
                "recommendation": rec, "uncertainties": sorted(uncertainties)}
    add(corpus, fid, "grounded_research_synthesis", risk, title, "research.v1", task + RESEARCH_RULES,
        inp, expected, rationale, expected, pattern, domain)


def synthesis(corpus, fid, risk, title, task, observations, rule, allowed, conclusion, terms, pattern, domain, rationale):
    obs = [{"id": oid, "role": role, "text": text} for oid, role, text in observations]
    inp = {"conclusion_rule": rule, "allowed_conclusions": allowed, "observations": obs}
    expected = {"roles": {oid: role for oid, role, _ in observations}, "required_terms": terms, "conclusion": conclusion}
    reference = {"statements": [{"statement_id": f"S{i}", "role": role, "observation_ids": [oid], "text": text}
                                for i, (oid, role, text) in enumerate(observations, 1)], "conclusion": conclusion}
    add(corpus, fid, "hierarchical_semantic_synthesis", risk, title, "synthesis.v1", task + SYNTH_RULES,
        inp, expected, rationale, reference, pattern, domain)


EVERY = "Recommend '{yes}' only if every claim is supported; otherwise '{no}'."
EVERY_TWO = "Recommend '{yes}' only if every claim is supported by at least two lineages; otherwise '{no}'."

# ---------------------------------------------------------------- research, corpus A
research("A", "A-RESEARCH-R1-1", "R1", "Note app suitability", "Assess the claims about the note app against the sources.",
         EVERY.format(yes="adopt", no="hold"), ["adopt", "hold"],
         [("C1", "Quillnote queues edits made offline and syncs them later."), ("C2", "Quillnote offers a free plan.")],
         [("S1", "quillnote-help-center", "Edits made without a connection are queued and synced when you reconnect."),
          ("S2", "quillnote-pricing-page", "Plans: Solo 4 USD per month and Team 9 USD per user per month. There is no free plan."),
          ("S3", "gadget-review-weekly", "Our testers confirmed that offline edits synced after reconnecting.")],
         [("C1", "supported", ["S1", "S3"]), ("C2", "contradicted", ["S2"])], "hold", [],
         "S2_direct_contradiction", "productivity_software",
         "C1 has two lineages; the pricing page directly denies a free plan, so the rule yields hold.")
research("A", "A-RESEARCH-R1-2", "R1", "Community hall suitability", "Assess the claims about the hall against the sources.",
         EVERY.format(yes="book", no="keep_looking"), ["book", "keep_looking"],
         [("C1", "Willow Hall has step-free access."), ("C2", "Willow Hall allows outside catering.")],
         [("S1", "willow-hall-website", "The main entrance and the hall are step-free, with a ramp from the car park."),
          ("S2", "birch-centre-website", "Birch Centre permits outside caterers once a form is signed.")],
         [("C1", "supported", ["S1"]), ("C2", "unresolved", [])], "keep_looking",
         ["single_lineage_support", "unaddressed_claim"],
         "S3_other_subject_unaddressed", "event_venues",
         "S2 is about a different venue and is not about C2; C2 is unaddressed.")
research("A", "A-RESEARCH-R2-1", "R2", "Bookkeeping tool integration", "Assess the claims about the bookkeeping tool against the sources.",
         EVERY.format(yes="adopt", no="hold"), ["adopt", "hold"],
         [("C1", "Tallybook imports statements from Northbank."), ("C2", "Tallybook exports reports as CSV.")],
         [("S1", "tallybook-marketing", "Tallybook connects to Northbank and imports statements daily."),
          ("S2", "tallybook-marketing", "Press release: the new Northbank connector imports statements automatically."),
          ("S3", "northbank-partner-directory", "Listed integration partner: Tallybook, statement import."),
          ("S4", "tallybook-marketing", "Every report can be downloaded as CSV or PDF.")],
         [("C1", "supported", ["S1", "S2", "S3"]), ("C2", "supported", ["S4"])], "adopt", ["single_lineage_support"],
         "S4_same_lineage_repetition", "small_business_accounting",
         "S1 and S2 share a lineage; C1 still has two lineages via S3; C2 rests on one lineage.")
research("A", "A-RESEARCH-R2-2", "R2", "Arts grant eligibility", "Assess the claims about the grant against the sources.",
         EVERY.format(yes="apply", no="verify_first"), ["apply", "verify_first"],
         [("C1", "The Harbor Arts Fund accepts applications from unregistered community groups."),
          ("C2", "The Harbor Arts Fund deadline is 2034-10-01.")],
         [("S1", "harbor-arts-fund-guidelines", "Applicants must be registered charities. Applications close on 2034-10-01."),
          ("S2", "neighborhood-news-blog", "Good news: unregistered community groups can now apply to the Harbor Arts Fund.")],
         [("C1", "unresolved", ["S1", "S2"]), ("C2", "supported", ["S1"])], "verify_first",
         ["conflicting_sources", "single_lineage_support"],
         "S5_conflict_unresolved", "grant_funding",
         "S1 denies and S2 affirms C1 and the decision_rule names no governing source, so rule 2 makes it unresolved.")
research("A", "A-RESEARCH-R3-1", "R3", "Security patch scheduling", "Assess the claims about the security release against the sources.",
         "Recommend 'schedule_patch' only if C1 is supported by at least two lineages; otherwise 'investigate'.",
         ["schedule_patch", "investigate"],
         [("C1", "Gatewire release 7.2 fixes the session fixation flaw GW-2034-11."),
          ("C2", "Installing Gatewire 7.2 requires a service restart.")],
         [("S1", "gatewire-security-advisory", "Release 7.2 resolves session fixation issue GW-2034-11. A service restart is required after installation."),
          ("S2", "national-vulnerability-register", "GW-2034-11 (session fixation) is fixed in Gatewire 7.2.")],
         [("C1", "supported", ["S1", "S2"]), ("C2", "supported", ["S1"])], "schedule_patch", ["single_lineage_support"],
         "S1_positive_lineage_count_rule", "vulnerability_patching",
         "C1 has two lineages so the rule is met; C2 rests on the advisory alone.")
research("A", "A-RESEARCH-R3-2", "R3", "Identity provider rollout", "Assess the claims about the identity provider against the sources.",
         EVERY.format(yes="enable_vendor_sso", no="hold_rollout"), ["enable_vendor_sso", "hold_rollout"],
         [("C1", "Portico enforces multi-factor authentication for all users."),
          ("C2", "Portico records failed sign-in attempts.")],
         [("S1", "portico-admin-guide", "Multi-factor authentication is enforced for administrator accounts."),
          ("S2", "security-review-group", "Portico writes failed sign-in attempts to its audit log."),
          ("S3", "portico-admin-guide", "Failed sign-ins are logged together with the source address.")],
         [("C1", "unresolved", ["S1"]), ("C2", "supported", ["S2", "S3"])], "hold_rollout", ["scope_mismatch"],
         "S6_narrower_scope", "identity_security",
         "S1 covers administrator accounts only, narrower than all users.")
research("A", "A-RESEARCH-R4-1", "R4", "Fall-arrest harness certification", "Assess the claims about the harness against the sources.",
         EVERY.format(yes="certify_harness", no="withhold_certification"), ["certify_harness", "withhold_certification"],
         [("C1", "The Apex fall-arrest harness is rated for users up to 140 kg."),
          ("C2", "The Apex harness passed its drop test.")],
         [("S1", "apex-spec-sheet", "Maximum user weight: 100 kg."),
          ("S2", "apex-user-manual", "Do not exceed a user weight of 100 kg."),
          ("S3", "test-house-report", "Apex harness: drop test passed.")],
         [("C1", "contradicted", ["S1", "S2"]), ("C2", "supported", ["S3"])], "withhold_certification",
         ["single_lineage_support"], "S8_quantitative_contradiction", "working_at_height",
         "A 100 kg maximum contradicts a 140 kg rating.")
research("A", "A-RESEARCH-R4-2", "R4", "Bridge load rating", "Assess the claims about the bridge route against the sources.",
         "When dated sources disagree about the same claim, the later-dated source governs and both are cited. "
         "Recommend 'allow_heavy_route' only if C1 is supported; otherwise 'use_detour'.",
         ["allow_heavy_route", "use_detour"],
         [("C1", "Bridge K-9 is rated for 20-tonne vehicles."),
          ("C2", "A detour suitable for heavy vehicles is signposted.")],
         [("S1", "state-bridge-inventory", "2031 inventory: Bridge K-9 load rating 20 tonnes."),
          ("S2", "state-bridge-inventory", "2034 inspection update: Bridge K-9 rating reduced to 12 tonnes."),
          ("S3", "county-traffic-notices", "Heavy vehicles are signposted to the Mill Road detour.")],
         [("C1", "contradicted", ["S1", "S2"]), ("C2", "supported", ["S3"])], "use_detour", ["single_lineage_support"],
         "S7_conflict_settled_by_rule", "road_infrastructure",
         "The 2034 update governs under the stated rule and denies the 20-tonne rating.")

# ---------------------------------------------------------------- research, corpus B
research("B", "B-RESEARCH-R1-1", "R1", "Backpack purchase check", "Assess the claims about the backpack against the sources.",
         EVERY_TWO.format(yes="buy", no="skip"), ["buy", "skip"],
         [("C1", "The Fernpack 30 weighs under 1 kg."), ("C2", "The Fernpack 30 comes with a rain cover.")],
         [("S1", "fernpack-product-page", "Weight 0.92 kg. A rain cover is stored in the base pocket."),
          ("S2", "trail-gear-lab", "We weighed the Fernpack 30 at 0.94 kg."),
          ("S3", "hiking-forum-reviews", "Mine arrived with the rain cover tucked into the bottom pocket.")],
         [("C1", "supported", ["S1", "S2"]), ("C2", "supported", ["S1", "S3"])], "buy", [],
         "S1_positive_lineage_count_rule", "outdoor_gear",
         "Both claims are supported by two lineages, meeting the rule.")
research("B", "B-RESEARCH-R1-2", "R1", "Community room capacity", "Assess the claims about the room against the sources.",
         EVERY.format(yes="reserve", no="look_elsewhere"), ["reserve", "look_elsewhere"],
         [("C1", "The Linden community room seats at least 40 people."),
          ("C2", "The Linden community room can be booked on Saturday evenings.")],
         [("S1", "linden-centre-rooms", "Community room: seated capacity 32."),
          ("S2", "linden-centre-calendar", "The community room can be booked on Saturday evenings.")],
         [("C1", "contradicted", ["S1"]), ("C2", "supported", ["S2"])], "look_elsewhere", ["single_lineage_support"],
         "S8_quantitative_contradiction", "community_spaces", "A capacity of 32 contradicts at least 40.")
research("B", "B-RESEARCH-R2-1", "R2", "Cleaning contractor terms", "Assess the claims about the contractor against the sources.",
         EVERY.format(yes="sign_contract", no="request_details"), ["sign_contract", "request_details"],
         [("C1", "Brightline Cleaning services the office on weekends."),
          ("C2", "Brightline Cleaning carries liability insurance.")],
         [("S1", "brightline-service-sheet", "Office visits are available on Saturdays."),
          ("S2", "brightline-service-sheet", "Fully insured: public liability cover of 2 million."),
          ("S3", "chamber-of-commerce-register", "Brightline Cleaning: insurance certificate on file.")],
         [("C1", "unresolved", ["S1"]), ("C2", "supported", ["S2", "S3"])], "request_details", ["scope_mismatch"],
         "S6_narrower_scope", "facilities_contracting", "Saturdays covers only part of weekends.")
research("B", "B-RESEARCH-R2-2", "R2", "Print workshop booking", "Assess the claims about the workshop against the sources.",
         "When the published price list and any other source disagree about a price, the published price list governs "
         "and both are cited. Recommend 'book_workshop' only if every claim is supported; otherwise 'ask_for_quote'.",
         ["book_workshop", "ask_for_quote"],
         [("C1", "The Riverside print workshop costs 40 USD per person."),
          ("C2", "The Riverside print workshop includes all printing materials.")],
         [("S1", "riverside-sales-email", "Our print workshop is 40 USD per person."),
          ("S2", "riverside-price-list", "Print workshop: 55 USD per person."),
          ("S3", "riverside-price-list", "The print workshop fee includes inks, paper and screens.")],
         [("C1", "contradicted", ["S1", "S2"]), ("C2", "supported", ["S3"])], "ask_for_quote", ["single_lineage_support"],
         "S7_conflict_settled_by_rule", "community_workshops",
         "The price list governs under the stated rule and denies the 40 USD price.")
research("B", "B-RESEARCH-R3-1", "R3", "Backup vendor evaluation", "Assess the claims about the backup vendor against the sources.",
         EVERY.format(yes="approve_vendor", no="reject_vendor"), ["approve_vendor", "reject_vendor"],
         [("C1", "Vaultline encrypts stored backups."), ("C2", "Vaultline supports point-in-time restore.")],
         [("S1", "vaultline-docs", "All backups are encrypted at rest with AES-256."),
          ("S2", "independent-audit-2034", "Auditors verified encryption at rest for Vaultline backup storage."),
          ("S3", "vaultline-docs", "Point-in-time restore is not supported; restores use nightly snapshots.")],
         [("C1", "supported", ["S1", "S2"]), ("C2", "contradicted", ["S3"])], "reject_vendor", [],
         "S2_direct_contradiction", "backup_services", "The vendor directly denies point-in-time restore.")
research("B", "B-RESEARCH-R3-2", "R3", "Contractor access prerequisites", "Assess the claims about the contractor against the sources.",
         EVERY.format(yes="grant_access", no="deny_access"), ["grant_access", "deny_access"],
         [("C1", "Contractor Mira Sol completed the data-handling course."),
          ("C2", "Contractor Mira Sol's background check is complete.")],
         [("S1", "training-records", "Mira Sol completed the data-handling course on 2035-02-03."),
          ("S2", "hr-screening-portal", "Background check for Mira Sol: complete."),
          ("S3", "vendor-coordinator-email", "Mira Sol's background check is still outstanding.")],
         [("C1", "supported", ["S1"]), ("C2", "unresolved", ["S2", "S3"])], "deny_access",
         ["conflicting_sources", "single_lineage_support"],
         "S5_conflict_unresolved", "access_governance",
         "S2 affirms and S3 denies C2 with no governing rule, so it is unresolved.")
research("B", "B-RESEARCH-R4-1", "R4", "Lift firmware release evidence", "Assess the claims about the firmware against the sources.",
         EVERY.format(yes="release_eligible", no="not_eligible"), ["release_eligible", "not_eligible"],
         [("C1", "Lift controller firmware 4.1 passed the regression suite."),
          ("C2", "Lift controller firmware 4.1 was signed by the release authority.")],
         [("S1", "qa-regression-reports", "Firmware 4.1: 212 of 212 regression tests passed."),
          ("S2", "independent-test-lab", "Replicated regression run for firmware 4.1: all tests passed."),
          ("S3", "release-signing-ledger", "Firmware 4.0 was signed by the release authority on 2035-02-11.")],
         [("C1", "supported", ["S1", "S2"]), ("C2", "unresolved", [])], "not_eligible", ["unaddressed_claim"],
         "S3_other_subject_unaddressed", "embedded_firmware_release",
         "S3 is about version 4.0, not 4.1, so nothing is about C2.")
research("B", "B-RESEARCH-R4-2", "R4", "Electrical panel energization", "Assess the claims about the panel against the sources.",
         EVERY_TWO.format(yes="energize_panel", no="keep_isolated"), ["energize_panel", "keep_isolated"],
         [("C1", "Panel P-12 holds a current electrical safety certificate."),
          ("C2", "Panel P-12 passed its insulation resistance test.")],
         [("S1", "manufacturer-bulletin", "Panel P-12 ships with a current safety certificate."),
          ("S2", "manufacturer-bulletin", "Reissued bulletin: the Panel P-12 certificate is current."),
          ("S3", "commissioning-log", "Panel P-12 insulation resistance test: pass."),
          ("S4", "site-inspector-notes", "Insulation resistance on Panel P-12 measured within limits.")],
         [("C1", "supported", ["S1", "S2"]), ("C2", "supported", ["S3", "S4"])], "keep_isolated", ["single_lineage_support"],
         "S4_same_lineage_repetition", "electrical_commissioning",
         "C1's two sources share one lineage, so the two-lineage rule is not met.")

# ---------------------------------------------------------------- synthesis
CAUSE = ("Conclude 'cause_established' if a finding directly states the cause and nothing disputes it; "
         "'cause_unresolved' if a proposed cause is disputed by counterevidence; otherwise 'insufficient_evidence'.")
CAUSE_SET = ["cause_established", "cause_unresolved", "insufficient_evidence"]
DESIGN = ("Conclude 'behavior_by_design' if a design constraint accounts for the observed behavior; 'defect_found' "
          "if a finding shows behavior that breaks a design constraint; otherwise 'insufficient_evidence'.")
DESIGN_SET = ["defect_found", "behavior_by_design", "insufficient_evidence"]
TREND = ("Conclude 'decline_established' only if at least two findings show a decline; 'improvement_established' "
         "only if at least two findings show an improvement; otherwise 'insufficient_evidence'.")
TREND_SET = ["decline_established", "improvement_established", "insufficient_evidence"]


def authority(action):
    return ("Apply these in order. If no observation calls for any action or decision, conclude 'no_action_needed'. "
            "Otherwise, if an authority boundary reserves that action or decision for someone else, conclude "
            f"'requires_operator_decision'. Otherwise conclude '{action}'.")


synthesis("A", "A-SYNTH-R1-1", "R1", "Garden sensor outage", "Synthesize the sensor observations.",
          [("O1", "finding", "The garden sensor stopped reporting at 06:10."),
           ("O2", "finding", "The sensor log shows it shut down at 06:10 because its battery reached 0%."),
           ("O3", "next_step", "Replace the sensor battery and confirm readings resume.")],
          CAUSE, CAUSE_SET, "cause_established",
          {"O1": ["sensor", "06:10"], "O2": ["battery", "0%"], "O3": ["battery", "readings"]},
          "cause_stated_by_log", "home_automation", "The log directly states the cause and nothing disputes it.")
synthesis("A", "A-SYNTH-R1-2", "R1", "Newsletter open rate", "Synthesize the newsletter observations.",
          [("O1", "finding", "Tuesday's newsletter open rate was 18%."),
           ("O2", "limitation", "Only one week of open-rate data exists."),
           ("O3", "hypothesis", "The new subject-line style might be lowering opens.")],
          TREND, TREND_SET, "insufficient_evidence",
          {"O1": ["18%", "open"], "O2": ["week"], "O3": ["subject"]},
          "single_finding_trend_insufficient", "community_newsletter", "One finding cannot establish a trend.")
synthesis("A", "A-SYNTH-R2-1", "R2", "Warehouse pick errors", "Synthesize the warehouse observations.",
          [("O1", "finding", "Warehouse pick errors doubled on Monday."),
           ("O2", "hypothesis", "The new shelf labels may be causing the errors."),
           ("O3", "counterevidence", "Aisles still using old labels showed the same increase."),
           ("O4", "next_step", "Audit Monday's pick lists aisle by aisle.")],
          CAUSE, CAUSE_SET, "cause_unresolved",
          {"O1": ["pick", "monday"], "O2": ["label"], "O3": ["aisles", "old"], "O4": ["audit", "aisle"]},
          "hypothesis_disputed", "warehouse_operations", "Old-label aisles show the same rise.")
synthesis("A", "A-SYNTH-R2-2", "R2", "Large refund delays", "Synthesize the refund observations.",
          [("O1", "finding", "Refund requests over 500 USD wait for a second reviewer."),
           ("O2", "design_constraint", "Policy requires two reviewers for refunds above 500 USD."),
           ("O3", "finding", "The median wait for these refunds is 2 days."),
           ("O4", "next_step", "Report the wait time to the finance lead.")],
          DESIGN, DESIGN_SET, "behavior_by_design",
          {"O1": ["500", "reviewer"], "O2": ["policy", "reviewers"], "O3": ["median", "days"], "O4": ["finance"]},
          "policy_explains_behavior", "customer_refunds", "The two-reviewer policy accounts for the wait.")
synthesis("A", "A-SYNTH-R3-1", "R3", "Login attack response", "Synthesize the authentication observations.",
          [("O1", "finding", "Failed logins from one IP range reached 4000 in an hour."),
           ("O2", "hypothesis", "The range may belong to a credential-stuffing botnet."),
           ("O3", "authority_boundary", "Blocking an IP range requires approval from the security lead."),
           ("O4", "next_step", "Prepare a block request with the log excerpt.")],
          authority("block_now"), ["block_now", "requires_operator_decision", "no_action_needed"],
          "requires_operator_decision",
          {"O1": ["failed login", "hour"], "O2": ["botnet"], "O3": ["security lead", "approval"], "O4": ["request", "log"]},
          "authority_reserved_response", "network_security",
          "The observations call for a block, which is reserved to the security lead.")
synthesis("A", "A-SYNTH-R3-2", "R3", "Offsite backup lag", "Synthesize the backup observations.",
          [("O1", "design_constraint", "Backups must be copied offsite within 24 hours."),
           ("O2", "finding", "The last three offsite copies arrived after 30 hours."),
           ("O3", "finding", "Local backups completed on schedule."),
           ("O4", "next_step", "Check the offsite transfer queue.")],
          DESIGN, DESIGN_SET, "defect_found",
          {"O1": ["offsite", "24"], "O2": ["offsite", "30"], "O3": ["local"], "O4": ["queue"]},
          "constraint_violated", "backup_operations", "30 hours breaks the 24-hour constraint.")
synthesis("A", "A-SYNTH-R4-1", "R4", "Model promotion readiness", "Synthesize the evaluation observations.",
          [("O1", "finding", "Candidate model C-8 scored higher than the current model on the frozen suite."),
           ("O2", "finding", "The release team has requested that C-8 be promoted to production."),
           ("O3", "limitation", "The frozen suite does not cover multilingual inputs."),
           ("O4", "authority_boundary", "Promotion to production requires the operator's signed approval."),
           ("O5", "next_step", "Send the evaluation summary to the operator.")],
          authority("promote_now"), ["promote_now", "requires_operator_decision", "no_action_needed"],
          "requires_operator_decision",
          {"O1": ["c-8", "frozen"], "O2": ["release team", "promoted"], "O3": ["multilingual"],
           "O4": ["signed", "approval"], "O5": ["summary", "operator"]},
          "promotion_reserved_to_operator", "model_release_governance",
          "A promotion decision is requested and reserved to the operator.")
synthesis("A", "A-SYNTH-R4-2", "R4", "Dosing pump stoppages", "Synthesize the pump observations.",
          [("O1", "finding", "The water treatment dosing pump stopped twice overnight."),
           ("O2", "hypothesis", "A failing float switch may be stopping the pump."),
           ("O3", "counterevidence", "The float switch passed a bench test this morning."),
           ("O4", "limitation", "The pump controller keeps no fault log."),
           ("O5", "next_step", "Install a temporary logger on the pump controller.")],
          CAUSE, CAUSE_SET, "cause_unresolved",
          {"O1": ["pump", "twice"], "O2": ["float"], "O3": ["bench"], "O4": ["fault log"], "O5": ["logger"]},
          "disputed_cause_with_limitation", "water_treatment", "The bench test disputes the float-switch hypothesis.")

synthesis("B", "B-SYNTH-R1-1", "R1", "Self-checkout lockouts", "Synthesize the kiosk observations.",
          [("O1", "finding", "The library self-checkout locks after 3 failed card scans."),
           ("O2", "design_constraint", "Kiosks are configured to lock after 3 failed scans."),
           ("O3", "next_step", "Post a sign explaining the lock.")],
          DESIGN, DESIGN_SET, "behavior_by_design",
          {"O1": ["self-checkout", "scans"], "O2": ["configured", "3"], "O3": ["sign"]},
          "configuration_explains_behavior", "library_services", "The configured lock accounts for the behavior.")
synthesis("B", "B-SYNTH-R1-2", "R1", "Bakery sales rise", "Synthesize the sales observations.",
          [("O1", "finding", "Weekday bakery sales rose 12% in May."),
           ("O2", "finding", "Weekend bakery sales rose 9% in May."),
           ("O3", "hypothesis", "The new sourdough line might explain the rise."),
           ("O4", "next_step", "Track the sourdough share of sales in June.")],
          TREND, TREND_SET, "improvement_established",
          {"O1": ["weekday", "12%"], "O2": ["weekend", "9%"], "O3": ["sourdough"], "O4": ["june"]},
          "two_findings_establish_trend", "small_retail", "Two findings show an improvement.")
synthesis("B", "B-SYNTH-R2-1", "R2", "Drone GPS drift", "Synthesize the drone observations.",
          [("O1", "finding", "Drone GPS drift started after the 3.2 firmware update."),
           ("O2", "finding", "Drones still on firmware 3.1 show no drift."),
           ("O3", "finding", "A rollback test on one drone to 3.1 removed its drift, showing the 3.2 update causes it."),
           ("O4", "next_step", "Pause the 3.2 rollout.")],
          CAUSE, CAUSE_SET, "cause_established",
          {"O1": ["drift", "3.2"], "O2": ["3.1"], "O3": ["rollback", "3.1"], "O4": ["pause", "rollout"]},
          "intervention_states_cause", "drone_fleet", "The rollback finding directly states the cause.")
synthesis("B", "B-SYNTH-R2-2", "R2", "Van tread readings", "Synthesize the vehicle observations.",
          [("O1", "finding", "The shared van's tread measured 1.4 mm."),
           ("O2", "finding", "The legal minimum tread depth is 1.6 mm."),
           ("O3", "authority_boundary", "Only the fleet manager can take a vehicle out of service."),
           ("O4", "next_step", "Send the tread readings to the fleet manager.")],
          authority("remove_from_service_now"), ["remove_from_service_now", "requires_operator_decision", "no_action_needed"],
          "requires_operator_decision",
          {"O1": ["tread", "van"], "O2": ["1.6"], "O3": ["fleet manager"], "O4": ["fleet manager", "readings"]},
          "fleet_decision_reserved", "vehicle_fleet",
          "1.4 mm is below the legal minimum, so action is called for, and it is reserved to the fleet manager.")
synthesis("B", "B-SYNTH-R3-1", "R3", "Phishing wave", "Synthesize the phishing observations.",
          [("O1", "finding", "Phishing reports tripled this week."),
           ("O2", "hypothesis", "A leaked staff directory may be the source of the target addresses."),
           ("O3", "counterevidence", "Addresses missing from the directory were also targeted."),
           ("O4", "next_step", "Compare the targeted addresses with the directory export.")],
          CAUSE, CAUSE_SET, "cause_unresolved",
          {"O1": ["phishing", "tripled"], "O2": ["directory"], "O3": ["directory", "targeted"], "O4": ["compare", "export"]},
          "source_hypothesis_disputed", "email_security", "Targets outside the directory dispute the leak hypothesis.")
synthesis("B", "B-SYNTH-R3-2", "R3", "Refrigerant pressure drop", "Synthesize the HVAC observations.",
          [("O1", "finding", "One HVAC unit reported a refrigerant pressure drop."),
           ("O2", "limitation", "The pressure sensor was last calibrated two years ago."),
           ("O3", "hypothesis", "A slow leak might be causing the drop."),
           ("O4", "next_step", "Recalibrate the sensor before ordering repairs.")],
          CAUSE, CAUSE_SET, "insufficient_evidence",
          {"O1": ["refrigerant", "pressure"], "O2": ["calibrated"], "O3": ["leak"], "O4": ["recalibrate"]},
          "untested_hypothesis_with_limitation", "building_hvac", "The hypothesis is neither stated as fact nor disputed.")
synthesis("B", "B-SYNTH-R4-1", "R4", "Cold room excursion", "Synthesize the cold room observations.",
          [("O1", "design_constraint", "The cold room must stay between 2 and 8 degrees Celsius."),
           ("O2", "finding", "The cold room logged 11 degrees Celsius for 40 minutes overnight."),
           ("O3", "finding", "The door sensor recorded the door open during that period."),
           ("O4", "authority_boundary", "Only the lab safety officer can release stored samples for use."),
           ("O5", "next_step", "Quarantine the affected samples pending review.")],
          DESIGN, DESIGN_SET, "defect_found",
          {"O1": ["cold room", "8"], "O2": ["11", "40"], "O3": ["door"], "O4": ["safety officer"], "O5": ["quarantine"]},
          "safety_limit_breached", "laboratory_storage", "11 degrees breaks the 2 to 8 degree constraint.")
synthesis("B", "B-SYNTH-R4-2", "R4", "Friday payroll hold", "Synthesize the payroll observations.",
          [("O1", "finding", "The payroll release was blocked at 17:00 on Friday."),
           ("O2", "design_constraint", "By policy, releases after 16:00 on Fridays are held until Monday."),
           ("O3", "finding", "No release errors were logged."),
           ("O4", "next_step", "Tell affected staff that payment arrives on Monday.")],
          DESIGN, DESIGN_SET, "behavior_by_design",
          {"O1": ["17:00", "blocked"], "O2": ["16:00", "monday"], "O3": ["error"], "O4": ["monday", "staff"]},
          "cutoff_policy_explains_hold", "payroll_operations", "The Friday cutoff policy accounts for the hold.")

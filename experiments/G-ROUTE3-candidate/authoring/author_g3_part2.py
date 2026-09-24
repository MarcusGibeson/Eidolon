"""G-ROUTE3 corpus authoring, part 2: grounded research and hierarchical synthesis fixtures."""
from author_g3_part1 import RESEARCH_CODES, RESEARCH_RULES, SYNTH_RULES, add


def research(corpus, fid, risk, title, task, rule, recs, claims, sources, gold_claims, rec, uncertainties,
             pattern, domain, rationale):
    inp = {"decision_rule": rule, "allowed_recommendations": recs,
           "allowed_uncertainty_codes": RESEARCH_CODES,
           "claims": [{"claim_id": cid, "text": text} for cid, text in claims],
           "sources": [{"source_id": sid, "lineage": lin, "text": text} for sid, lin, text in sources]}
    lineage = {sid: lin for sid, lin, _ in sources}
    expected_claims = []
    for cid, status, cites in gold_claims:
        expected_claims.append({"claim_id": cid, "status": status, "citations": list(cites),
                                "lineages": sorted({lineage[c] for c in cites})})
    expected = {"claims": expected_claims, "recommendation": rec, "uncertainties": sorted(uncertainties)}
    add(corpus, fid, "grounded_research_synthesis", risk, title, "research.v1", task + RESEARCH_RULES,
        inp, expected, rationale, expected, pattern, domain)


def synthesis(corpus, fid, risk, title, task, observations, rule, allowed, conclusion, terms, pattern, domain, rationale):
    obs = [{"id": oid, "role": role, "text": text} for oid, role, text in observations]
    inp = {"conclusion_rule": rule, "allowed_conclusions": allowed, "observations": obs}
    expected = {"roles": {oid: role for oid, role, _ in observations},
                "required_terms": terms, "conclusion": conclusion}
    reference = {"statements": [{"statement_id": f"S{i}", "role": role, "observation_ids": [oid], "text": text}
                                for i, (oid, role, text) in enumerate(observations, 1)],
                 "conclusion": conclusion}
    add(corpus, fid, "hierarchical_semantic_synthesis", risk, title, "synthesis.v1", task + SYNTH_RULES,
        inp, expected, rationale, reference, pattern, domain)


ALL_SUPPORTED = "Recommend '{yes}' only if every claim is supported; otherwise '{no}'."

# ---------------------------------------------------------------- research, corpus A
research("A", "A-RESEARCH-R1-1", "R1", "Note app suitability", "Assess the claims about the note app against the sources.",
         ALL_SUPPORTED.format(yes="adopt", no="hold"), ["adopt", "hold"],
         [("C1", "Quillnote queues edits made offline and syncs them later."), ("C2", "Quillnote offers a free plan.")],
         [("S1", "quillnote-help-center", "Edits made without a connection are queued and synced when you reconnect."),
          ("S2", "quillnote-pricing-page", "Plans: Solo 4 USD per month and Team 9 USD per user per month. There is no free plan."),
          ("S3", "gadget-review-weekly", "Our testers confirmed that offline edits synced after reconnecting.")],
         [("C1", "supported", ["S1", "S3"]), ("C2", "contradicted", ["S2"])], "hold", [],
         "one_claim_contradicted", "productivity_software",
         "C1 has two independent lineages; the pricing page denies a free plan, so the rule yields hold.")
research("A", "A-RESEARCH-R1-2", "R1", "Community hall suitability", "Assess the claims about the hall against the sources.",
         ALL_SUPPORTED.format(yes="book", no="keep_looking"), ["book", "keep_looking"],
         [("C1", "Willow Hall has step-free access."), ("C2", "Willow Hall allows outside catering.")],
         [("S1", "willow-hall-website", "The main entrance and the hall are step-free, with a ramp from the car park."),
          ("S2", "birch-centre-website", "Birch Centre permits outside caterers once a form is signed.")],
         [("C1", "supported", ["S1"]), ("C2", "unresolved", [])], "keep_looking",
         ["single_lineage_support", "unaddressed_claim"],
         "distractor_entity_leaves_claim_unaddressed", "event_venues",
         "S2 concerns a different venue and must not be cited; C2 is unaddressed.")
research("A", "A-RESEARCH-R2-1", "R2", "Bookkeeping tool integration", "Assess the claims about the bookkeeping tool against the sources.",
         ALL_SUPPORTED.format(yes="adopt", no="hold"), ["adopt", "hold"],
         [("C1", "Tallybook imports statements from Northbank."), ("C2", "Tallybook exports reports as CSV.")],
         [("S1", "tallybook-marketing", "Tallybook connects to Northbank and imports statements daily."),
          ("S2", "tallybook-marketing", "Press release: the new Northbank connector imports statements automatically."),
          ("S3", "northbank-partner-directory", "Listed integration partner: Tallybook, statement import."),
          ("S4", "tallybook-marketing", "Every report can be downloaded as CSV or PDF.")],
         [("C1", "supported", ["S1", "S2", "S3"]), ("C2", "supported", ["S4"])], "adopt", ["single_lineage_support"],
         "vendor_repetition_positive", "small_business_accounting",
         "S1 and S2 share a lineage; C1 still has two lineages via S3; C2 rests on one lineage.")
research("A", "A-RESEARCH-R2-2", "R2", "Arts grant eligibility", "Assess the claims about the grant against the sources.",
         ALL_SUPPORTED.format(yes="apply", no="verify_first"), ["apply", "verify_first"],
         [("C1", "The Harbor Arts Fund accepts applications from unregistered community groups."),
          ("C2", "The Harbor Arts Fund deadline is 2034-10-01.")],
         [("S1", "harbor-arts-fund-guidelines", "Applicants must be registered charities. Applications close on 2034-10-01."),
          ("S2", "neighborhood-news-blog", "Good news: unregistered community groups can now apply to the Harbor Arts Fund.")],
         [("C1", "unresolved", ["S1", "S2"]), ("C2", "supported", ["S1"])], "verify_first",
         ["conflicting_sources", "single_lineage_support"],
         "unresolved_source_conflict", "grant_funding",
         "The guidelines and the blog disagree and no rule resolves them.")
research("A", "A-RESEARCH-R3-1", "R3", "Security patch scheduling", "Assess the claims about the security release against the sources.",
         "Recommend 'schedule_patch' only if C1 is supported by at least two lineages; otherwise 'investigate'.",
         ["schedule_patch", "investigate"],
         [("C1", "Gatewire release 7.2 fixes the session fixation flaw GW-2034-11."),
          ("C2", "Installing Gatewire 7.2 requires a service restart.")],
         [("S1", "gatewire-security-advisory", "Release 7.2 resolves session fixation issue GW-2034-11. A service restart is required after installation."),
          ("S2", "national-vulnerability-register", "GW-2034-11 (session fixation) is fixed in Gatewire 7.2.")],
         [("C1", "supported", ["S1", "S2"]), ("C2", "supported", ["S1"])], "schedule_patch", ["single_lineage_support"],
         "lineage_count_rule_met", "vulnerability_patching",
         "C1 has two lineages so the rule is met; C2 rests on the advisory alone.")
research("A", "A-RESEARCH-R3-2", "R3", "Supplier breach report", "Assess the claims about the supplier incident against the sources.",
         "Recommend 'suspend_supplier' only if C1 is supported; otherwise 'continue_monitoring'.",
         ["suspend_supplier", "continue_monitoring"],
         [("C1", "Supplier Orlen Parts exposed customer email addresses."),
          ("C2", "Orlen Parts notified the data regulator.")],
         [("S1", "anonymous-forum", "Orlen Parts leaked a list of customer emails last week."),
          ("S2", "anonymous-forum", "Repost: Orlen customer emails leaked, see the earlier thread."),
          ("S3", "orlen-parts-statement", "We have found no evidence that customer data was exposed.")],
         [("C1", "unresolved", ["S1", "S2", "S3"]), ("C2", "unresolved", [])], "continue_monitoring",
         ["conflicting_sources", "unaddressed_claim"],
         "conflict_plus_unaddressed", "supplier_risk",
         "The forum and the supplier disagree; nothing addresses regulator notification.")
research("A", "A-RESEARCH-R4-1", "R4", "Model promotion evidence", "Assess the claims about the model build against the sources.",
         ALL_SUPPORTED.format(yes="eligible_for_promotion", no="not_eligible"), ["eligible_for_promotion", "not_eligible"],
         [("C1", "Model build M-51 passed the frozen evaluation suite."),
          ("C2", "Model build M-51 has recorded operator approval.")],
         [("S1", "evaluation-registry", "M-51: frozen suite passed with 0 regressions."),
          ("S2", "promotion-ledger", "M-51: no operator approval recorded.")],
         [("C1", "supported", ["S1"]), ("C2", "contradicted", ["S2"])], "not_eligible", ["single_lineage_support"],
         "missing_authorization_contradiction", "model_release_governance",
         "The ledger denies approval, so the build is not eligible.")
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
         "temporal_precedence_resolution", "road_infrastructure",
         "The 2034 update governs and denies the 20-tonne rating.")

# ---------------------------------------------------------------- research, corpus B
research("B", "B-RESEARCH-R1-1", "R1", "Backpack purchase check", "Assess the claims about the backpack against the sources.",
         ALL_SUPPORTED.format(yes="buy", no="skip"), ["buy", "skip"],
         [("C1", "The Fernpack 30 weighs under 1 kg."), ("C2", "The Fernpack 30 comes with a rain cover.")],
         [("S1", "fernpack-product-page", "Weight 0.92 kg. A rain cover is stored in the base pocket."),
          ("S2", "trail-gear-lab", "We weighed the Fernpack 30 at 0.94 kg."),
          ("S3", "hiking-forum-reviews", "Mine arrived with the rain cover tucked into the bottom pocket.")],
         [("C1", "supported", ["S1", "S2"]), ("C2", "supported", ["S1", "S3"])], "buy", [],
         "clean_independent_positive", "outdoor_gear",
         "Both claims have two independent lineages.")
research("B", "B-RESEARCH-R1-2", "R1", "Community room capacity", "Assess the claims about the room against the sources.",
         ALL_SUPPORTED.format(yes="reserve", no="look_elsewhere"), ["reserve", "look_elsewhere"],
         [("C1", "The Linden community room seats at least 40 people."),
          ("C2", "The Linden community room is free on Saturday evenings.")],
         [("S1", "linden-centre-rooms", "Community room: seated capacity 32."),
          ("S2", "linden-centre-calendar", "Saturday evening slots are open through March.")],
         [("C1", "contradicted", ["S1"]), ("C2", "supported", ["S2"])], "look_elsewhere", ["single_lineage_support"],
         "quantitative_threshold_contradiction", "community_spaces",
         "A capacity of 32 contradicts at least 40.")
research("B", "B-RESEARCH-R2-1", "R2", "Cleaning contractor terms", "Assess the claims about the contractor against the sources.",
         ALL_SUPPORTED.format(yes="sign_contract", no="request_details"), ["sign_contract", "request_details"],
         [("C1", "Brightline Cleaning services the office on weekends."),
          ("C2", "Brightline Cleaning carries liability insurance.")],
         [("S1", "brightline-service-sheet", "Office visits are available on Saturdays."),
          ("S2", "brightline-service-sheet", "Fully insured: public liability cover of 2 million."),
          ("S3", "chamber-of-commerce-register", "Brightline Cleaning: insurance certificate on file.")],
         [("C1", "unresolved", ["S1"]), ("C2", "supported", ["S2", "S3"])], "request_details", ["scope_mismatch"],
         "narrower_scope_source", "facilities_contracting",
         "Saturdays covers only part of weekends.")
research("B", "B-RESEARCH-R2-2", "R2", "Meal plan subscription", "Assess the claims about the meal plan against the sources.",
         ALL_SUPPORTED.format(yes="subscribe", no="decline"), ["subscribe", "decline"],
         [("C1", "The Parcelbox meal plan delivers to postcode zone 4."),
          ("C2", "The Parcelbox meal plan can be paused without a fee.")],
         [("S1", "parcelbox-delivery-map", "Delivery zones: 1, 2, 3 and 4."),
          ("S2", "parcelbox-terms", "Pause your plan at any time; there are no pause fees."),
          ("S3", "freshcrate-terms", "FreshCrate charges 5 USD to pause a plan.")],
         [("C1", "supported", ["S1"]), ("C2", "supported", ["S2"])], "subscribe", ["single_lineage_support"],
         "distractor_entity_positive", "food_delivery",
         "S3 concerns a different company and must not be cited.")
research("B", "B-RESEARCH-R3-1", "R3", "Backup vendor security", "Assess the claims about the backup vendor against the sources.",
         ALL_SUPPORTED.format(yes="approve_vendor", no="reject_vendor"), ["approve_vendor", "reject_vendor"],
         [("C1", "Vaultline encrypts stored backups."), ("C2", "Vaultline keeps backups for at least 90 days.")],
         [("S1", "vaultline-docs", "All backups are encrypted at rest with AES-256."),
          ("S2", "vaultline-docs", "FAQ: yes, stored backups are encrypted."),
          ("S3", "independent-audit-2034", "Auditors verified encryption at rest for Vaultline backup storage."),
          ("S4", "vaultline-docs", "Backups are retained for 30 days.")],
         [("C1", "supported", ["S1", "S2", "S3"]), ("C2", "contradicted", ["S4"])], "reject_vendor", [],
         "repetition_plus_quantitative_contradiction", "backup_services",
         "30-day retention contradicts at least 90 days.")
research("B", "B-RESEARCH-R3-2", "R3", "Contractor access prerequisites", "Assess the claims about the contractor against the sources.",
         ALL_SUPPORTED.format(yes="grant_access", no="deny_access"), ["grant_access", "deny_access"],
         [("C1", "Contractor Mira Sol completed the data-handling course."),
          ("C2", "Contractor Mira Sol's background check is complete.")],
         [("S1", "training-records", "Mira Sol completed the data-handling course on 2035-02-03."),
          ("S2", "training-records", "Course roster export: Mira Sol, passed."),
          ("S3", "facilities-badge-log", "Mira Sol was issued an east-entrance badge.")],
         [("C1", "supported", ["S1", "S2"]), ("C2", "unresolved", [])], "deny_access",
         ["single_lineage_support", "unaddressed_claim"],
         "adjacent_subject_not_evidence", "access_governance",
         "A badge record is a different subject from a background check.")
research("B", "B-RESEARCH-R4-1", "R4", "Lift firmware release evidence", "Assess the claims about the firmware against the sources.",
         ALL_SUPPORTED.format(yes="release_eligible", no="not_eligible"), ["release_eligible", "not_eligible"],
         [("C1", "Lift controller firmware 4.1 passed the regression suite."),
          ("C2", "Lift controller firmware 4.1 was signed by the release authority.")],
         [("S1", "qa-regression-reports", "Firmware 4.1: 212 of 212 regression tests passed."),
          ("S2", "release-signing-ledger", "Firmware 4.1 signed by the release authority on 2035-05-20."),
          ("S3", "independent-test-lab", "Replicated regression run for firmware 4.1: all tests passed.")],
         [("C1", "supported", ["S1", "S3"]), ("C2", "supported", ["S2"])], "release_eligible", ["single_lineage_support"],
         "all_supported_mixed_independence", "embedded_firmware_release",
         "Both claims are supported; C2 rests on one lineage.")
research("B", "B-RESEARCH-R4-2", "R4", "Electrical panel certification", "Assess the claims about the panel against the sources.",
         "When the certification registry and the manufacturer disagree about a certification, the certification "
         "registry governs and both are cited. Recommend 'energize_panel' only if every claim is supported; otherwise 'keep_isolated'.",
         ["energize_panel", "keep_isolated"],
         [("C1", "Panel P-12 holds a current electrical safety certificate."),
          ("C2", "Panel P-12 passed its insulation resistance test.")],
         [("S1", "manufacturer-bulletin", "Panel P-12 ships with a current safety certificate."),
          ("S2", "certification-registry", "Panel P-12 certificate expired on 2035-01-31."),
          ("S3", "commissioning-log", "Panel P-12 insulation resistance test: pass.")],
         [("C1", "contradicted", ["S1", "S2"]), ("C2", "supported", ["S3"])], "keep_isolated", ["single_lineage_support"],
         "authority_precedence_resolution", "electrical_commissioning",
         "The registry governs and records an expired certificate.")

# ---------------------------------------------------------------- synthesis
CAUSE = ("Conclude 'cause_established' if a finding directly identifies the cause and nothing disputes it; "
         "'cause_unresolved' if a proposed cause is disputed by counterevidence; otherwise 'insufficient_evidence'.")
CAUSE_SET = ["cause_established", "cause_unresolved", "insufficient_evidence"]
DESIGN = ("Conclude 'behavior_by_design' if a design constraint accounts for the observed behavior; 'defect_found' "
          "if a finding shows behavior that breaks a design constraint; otherwise 'insufficient_evidence'.")
DESIGN_SET = ["defect_found", "behavior_by_design", "insufficient_evidence"]
TREND = ("Conclude 'decline_established' only if at least two findings show a decline; 'improvement_established' "
         "only if at least two findings show an improvement; otherwise 'insufficient_evidence'.")
TREND_SET = ["decline_established", "improvement_established", "insufficient_evidence"]


def authority(action):
    return (f"Conclude 'requires_operator_decision' if an authority boundary reserves the needed decision for "
            f"someone else; '{action}' only if no such boundary exists; 'no_action_needed' if no finding indicates harm.")


synthesis("A", "A-SYNTH-R1-1", "R1", "Garden sensor outage", "Synthesize the sensor observations.",
          [("O1", "finding", "The garden sensor stopped reporting at 06:10."),
           ("O2", "finding", "The sensor log shows it shut down at 06:10 because its battery reached 0%."),
           ("O3", "next_step", "Replace the sensor battery and confirm readings resume.")],
          CAUSE, CAUSE_SET, "cause_established",
          {"O1": ["sensor", "06:10"], "O2": ["battery", "0%"], "O3": ["battery", "readings"]},
          "direct_cause_mergeable_findings", "home_automation",
          "The sensor log directly attributes the shutdown to a flat battery and nothing disputes it.")
synthesis("A", "A-SYNTH-R1-2", "R1", "Newsletter open rate", "Synthesize the newsletter observations.",
          [("O1", "finding", "Tuesday's newsletter open rate was 18%."),
           ("O2", "limitation", "Only one week of open-rate data exists."),
           ("O3", "hypothesis", "The new subject-line style might be lowering opens.")],
          TREND, TREND_SET, "insufficient_evidence",
          {"O1": ["18%", "open"], "O2": ["week"], "O3": ["subject"]},
          "single_finding_trend_insufficient", "community_newsletter",
          "One finding cannot establish a trend.")
synthesis("A", "A-SYNTH-R2-1", "R2", "Warehouse pick errors", "Synthesize the warehouse observations.",
          [("O1", "finding", "Warehouse pick errors doubled on Monday."),
           ("O2", "hypothesis", "The new shelf labels may be causing the errors."),
           ("O3", "counterevidence", "Aisles still using old labels showed the same increase."),
           ("O4", "next_step", "Audit Monday's pick lists aisle by aisle.")],
          CAUSE, CAUSE_SET, "cause_unresolved",
          {"O1": ["pick", "monday"], "O2": ["label"], "O3": ["aisles", "old"], "O4": ["audit", "aisle"]},
          "hypothesis_disputed", "warehouse_operations",
          "Old-label aisles show the same rise, disputing the label hypothesis.")
synthesis("A", "A-SYNTH-R2-2", "R2", "Large refund delays", "Synthesize the refund observations.",
          [("O1", "finding", "Refund requests over 500 USD wait for a second reviewer."),
           ("O2", "design_constraint", "Policy requires two reviewers for refunds above 500 USD."),
           ("O3", "finding", "The median wait for these refunds is 2 days."),
           ("O4", "next_step", "Report the wait time to the finance lead.")],
          DESIGN, DESIGN_SET, "behavior_by_design",
          {"O1": ["500", "reviewer"], "O2": ["policy", "two"], "O3": ["median", "days"], "O4": ["finance"]},
          "policy_explains_behavior", "customer_refunds",
          "The two-reviewer policy accounts for the wait.")
synthesis("A", "A-SYNTH-R3-1", "R3", "Login attack response", "Synthesize the authentication observations.",
          [("O1", "finding", "Failed logins from one IP range reached 4000 in an hour."),
           ("O2", "hypothesis", "The range may belong to a credential-stuffing botnet."),
           ("O3", "authority_boundary", "Blocking an IP range requires approval from the security lead."),
           ("O4", "next_step", "Prepare a block request with the log excerpt.")],
          authority("block_now"), ["block_now", "requires_operator_decision", "no_action_needed"],
          "requires_operator_decision",
          {"O1": ["failed login", "4000"], "O2": ["botnet"], "O3": ["security lead", "approval"], "O4": ["request", "log"]},
          "authority_reserved_response", "network_security",
          "The needed block is reserved to the security lead.")
synthesis("A", "A-SYNTH-R3-2", "R3", "Offsite backup lag", "Synthesize the backup observations.",
          [("O1", "design_constraint", "Backups must be copied offsite within 24 hours."),
           ("O2", "finding", "The last three offsite copies arrived after 30 hours."),
           ("O3", "finding", "Local backups completed on schedule."),
           ("O4", "next_step", "Check the offsite transfer queue.")],
          DESIGN, DESIGN_SET, "defect_found",
          {"O1": ["offsite", "24"], "O2": ["offsite", "30"], "O3": ["local"], "O4": ["queue"]},
          "constraint_violated", "backup_operations",
          "30 hours breaks the 24-hour constraint.")
synthesis("A", "A-SYNTH-R4-1", "R4", "Model promotion readiness", "Synthesize the evaluation observations.",
          [("O1", "finding", "Candidate model C-8 scored higher than the current model on the frozen suite."),
           ("O2", "limitation", "The frozen suite does not cover multilingual inputs."),
           ("O3", "authority_boundary", "Promotion to production requires the operator's signed approval."),
           ("O4", "next_step", "Send the evaluation summary to the operator.")],
          authority("promote_now"), ["promote_now", "requires_operator_decision", "no_action_needed"],
          "requires_operator_decision",
          {"O1": ["c-8", "frozen"], "O2": ["multilingual"], "O3": ["signed", "approval"], "O4": ["summary", "operator"]},
          "promotion_reserved_to_operator", "model_release_governance",
          "Promotion is reserved to the operator's signed approval.")
synthesis("A", "A-SYNTH-R4-2", "R4", "Dosing pump stoppages", "Synthesize the pump observations.",
          [("O1", "finding", "The water treatment dosing pump stopped twice overnight."),
           ("O2", "hypothesis", "A failing float switch may be stopping the pump."),
           ("O3", "counterevidence", "The float switch passed a bench test this morning."),
           ("O4", "limitation", "The pump controller keeps no fault log."),
           ("O5", "next_step", "Install a temporary logger on the pump controller.")],
          CAUSE, CAUSE_SET, "cause_unresolved",
          {"O1": ["pump", "twice"], "O2": ["float"], "O3": ["bench"], "O4": ["fault log"], "O5": ["logger"]},
          "disputed_cause_with_limitation", "water_treatment",
          "The bench test disputes the float-switch hypothesis.")

synthesis("B", "B-SYNTH-R1-1", "R1", "Self-checkout lockouts", "Synthesize the kiosk observations.",
          [("O1", "finding", "The library self-checkout locks after 3 failed card scans."),
           ("O2", "design_constraint", "Kiosks are configured to lock after three failed scans."),
           ("O3", "next_step", "Post a sign explaining the lock.")],
          DESIGN, DESIGN_SET, "behavior_by_design",
          {"O1": ["self-checkout", "scans"], "O2": ["configured", "three"], "O3": ["sign"]},
          "configuration_explains_behavior", "library_services",
          "The configured lock accounts for the behavior.")
synthesis("B", "B-SYNTH-R1-2", "R1", "Bakery sales rise", "Synthesize the sales observations.",
          [("O1", "finding", "Weekday bakery sales rose 12% in May."),
           ("O2", "finding", "Weekend bakery sales rose 9% in May."),
           ("O3", "hypothesis", "The new sourdough line might explain the rise."),
           ("O4", "next_step", "Track the sourdough share of sales in June.")],
          TREND, TREND_SET, "improvement_established",
          {"O1": ["weekday", "12%"], "O2": ["weekend", "9%"], "O3": ["sourdough"], "O4": ["june"]},
          "two_findings_establish_trend", "small_retail",
          "Two findings show an improvement.")
synthesis("B", "B-SYNTH-R2-1", "R2", "Drone GPS drift", "Synthesize the drone observations.",
          [("O1", "finding", "Drone GPS drift started after the 3.2 firmware update."),
           ("O2", "finding", "Drones still on firmware 3.1 show no drift."),
           ("O3", "finding", "A rollback test on one drone to 3.1 removed its drift."),
           ("O4", "next_step", "Pause the 3.2 rollout.")],
          CAUSE, CAUSE_SET, "cause_established",
          {"O1": ["drift", "3.2"], "O2": ["3.1"], "O3": ["rollback", "3.1"], "O4": ["pause", "rollout"]},
          "intervention_confirms_cause", "drone_fleet",
          "The rollback test directly identifies the update as the cause.")
synthesis("B", "B-SYNTH-R2-2", "R2", "Van tread readings", "Synthesize the vehicle observations.",
          [("O1", "finding", "The shared van's tread measured 1.4 mm."),
           ("O2", "finding", "The legal minimum tread depth is 1.6 mm."),
           ("O3", "authority_boundary", "Only the fleet manager can take a vehicle out of service."),
           ("O4", "next_step", "Send the tread readings to the fleet manager.")],
          authority("remove_from_service_now"), ["remove_from_service_now", "requires_operator_decision", "no_action_needed"],
          "requires_operator_decision",
          {"O1": ["tread", "van"], "O2": ["1.6"], "O3": ["fleet manager"], "O4": ["fleet manager", "readings"]},
          "fleet_decision_reserved", "vehicle_fleet",
          "1.4 mm is below the 1.6 mm legal minimum, so harm is indicated, and the service decision is reserved to the fleet manager.")
synthesis("B", "B-SYNTH-R3-1", "R3", "Phishing wave", "Synthesize the phishing observations.",
          [("O1", "finding", "Phishing reports tripled this week."),
           ("O2", "hypothesis", "A leaked staff directory may be the source of the target addresses."),
           ("O3", "counterevidence", "Addresses missing from the directory were also targeted."),
           ("O4", "next_step", "Compare the targeted addresses with the directory export.")],
          CAUSE, CAUSE_SET, "cause_unresolved",
          {"O1": ["phishing", "tripled"], "O2": ["directory"], "O3": ["directory", "targeted"], "O4": ["compare", "export"]},
          "source_hypothesis_disputed", "email_security",
          "Targets outside the directory dispute the leak hypothesis.")
synthesis("B", "B-SYNTH-R3-2", "R3", "Refrigerant pressure drop", "Synthesize the HVAC observations.",
          [("O1", "finding", "One HVAC unit reported a refrigerant pressure drop."),
           ("O2", "limitation", "The pressure sensor was last calibrated two years ago."),
           ("O3", "hypothesis", "A slow leak might be causing the drop."),
           ("O4", "next_step", "Recalibrate the sensor before ordering repairs.")],
          CAUSE, CAUSE_SET, "insufficient_evidence",
          {"O1": ["refrigerant", "pressure"], "O2": ["calibrated"], "O3": ["leak"], "O4": ["recalibrate"]},
          "untested_hypothesis_with_limitation", "building_hvac",
          "The hypothesis is neither confirmed nor disputed.")
synthesis("B", "B-SYNTH-R4-1", "R4", "Cold room excursion", "Synthesize the cold room observations.",
          [("O1", "design_constraint", "The cold room must stay between 2 and 8 degrees Celsius."),
           ("O2", "finding", "The cold room logged 11 degrees Celsius for 40 minutes overnight."),
           ("O3", "finding", "The door sensor recorded the door open during that period."),
           ("O4", "authority_boundary", "Only the lab safety officer can release stored samples for use."),
           ("O5", "next_step", "Quarantine the affected samples pending review.")],
          DESIGN, DESIGN_SET, "defect_found",
          {"O1": ["cold room", "8"], "O2": ["11", "40"], "O3": ["door"], "O4": ["safety officer"], "O5": ["quarantine"]},
          "safety_limit_breached", "laboratory_storage",
          "11 degrees breaks the 2 to 8 degree constraint.")
synthesis("B", "B-SYNTH-R4-2", "R4", "Friday payroll hold", "Synthesize the payroll observations.",
          [("O1", "finding", "The payroll release was blocked at 17:00 on Friday."),
           ("O2", "design_constraint", "By policy, releases after 16:00 on Fridays are held until Monday."),
           ("O3", "finding", "No release errors were logged."),
           ("O4", "next_step", "Tell affected staff that payment arrives on Monday.")],
          DESIGN, DESIGN_SET, "behavior_by_design",
          {"O1": ["17:00", "blocked"], "O2": ["16:00", "monday"], "O3": ["error"], "O4": ["monday", "staff"]},
          "cutoff_policy_explains_hold", "payroll_operations",
          "The Friday cutoff policy accounts for the hold.")

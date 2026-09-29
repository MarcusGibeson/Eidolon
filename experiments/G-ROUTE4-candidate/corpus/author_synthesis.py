"""Author the 100 frozen G-ROUTE4 Hierarchical Semantic Synthesis slots (pre-seal repair revision).

Deterministic corpus authoring only, to the frozen blueprint at commit 1156d06. It contacts no model or adjudicator
and creates no seal.

Repair revision (after the complete-corpus pre-seal review):
- every observation is one short, single-finding sentence written for its fixture (G-ROUTE3-comparable length);
  there is no provenance or padding text of any kind;
- required terms are substantive words or values from the finding itself, never scaffolding, and at least one
  term per observation appears in no other observation of the fixture;
- the global invented-name stream is unchanged: each fixture still draws 3 (small band) or 5 (large band) names,
  replayed from the committed name-stream artifact, so every later class keeps its names.

    python -B author_synthesis.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from name_stream import NameStream  # noqa: E402

BLUEPRINT = json.loads((ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
TEMPLATE = BLUEPRINT["templates"]["hierarchical_semantic_synthesis"]["assembled_template"]
SLOTS = [s for s in BLUEPRINT["slots"] if s["task_class"] == "hierarchical_semantic_synthesis"]

CONCLUSIONS = {
    "SY1": ("cause_established", ["cause_established", "cause_unresolved", "insufficient_evidence"]),
    "SY2": ("cause_unresolved", ["cause_established", "cause_unresolved", "insufficient_evidence"]),
    "SY3": ("insufficient_evidence", ["cause_established", "cause_unresolved", "insufficient_evidence"]),
    "SY4": ("decision_reserved", ["decision_reserved", "decision_open", "insufficient_evidence"]),
    "SY5": ("constraint_breached", ["constraint_breached", "constraint_met", "insufficient_evidence"]),
    "SY6": ("behavior_by_design", ["behavior_by_design", "defect_found", "insufficient_evidence"]),
}
CAUSE_RULE = ("Choose cause_established when a finding directly states the cause and nothing disputes it; choose "
              "cause_unresolved when counterevidence disputes a proposed cause; otherwise choose insufficient_evidence.")
RULES = {
    "SY1": CAUSE_RULE, "SY2": CAUSE_RULE, "SY3": CAUSE_RULE,
    "SY4": ("Choose decision_reserved when the evidence assigns the decision to a named role; choose decision_open "
            "when the evidence gives the current reviewer that authority; otherwise choose insufficient_evidence."),
    "SY5": ("Choose constraint_breached when a finding exceeds or violates the stated constraint; choose "
            "constraint_met when the finding remains within it; otherwise choose insufficient_evidence."),
    "SY6": ("Choose behavior_by_design when a policy or configuration accounts for the behavior; choose "
            "defect_found when the behavior breaks that policy or configuration; otherwise choose "
            "insufficient_evidence."),
}
RATIONALE = {
    "SY1": "A finding directly states the cause and no observation disputes it.",
    "SY2": "Counterevidence disputes the proposed cause, so causality remains unresolved.",
    "SY3": "A cause is only proposed; nothing establishes or disputes it.",
    "SY4": "The evidence reserves the decision to a named role other than the current reviewer.",
    "SY5": "A measured finding exceeds the stated constraint.",
    "SY6": "A stated policy or configuration accounts for the observed behavior.",
}

# One entry per slot, in blueprint slot order: (topic, title, [(role, text, required_terms), ...]).
S = []


def X(topic, title, *obs):
    S.append((topic, title, list(obs)))


# 1 A4-SYNTH-R1-01 SY1 merge large
X("greenhouse heater", "Greenhouse heater outage",
  ("finding", "The greenhouse heater went cold at 02:30 on the frostiest night.", ["02:30", "frostiest"]),
  ("finding", "Seedlings on the lower bench showed frost damage by morning.", ["seedlings", "lower bench"]),
  ("diagnosis", "The electrician found the heater stopped because its thermal fuse blew.", ["thermal fuse"]),
  ("next_step", "Fit a replacement fuse before tonight's forecast frost.", ["tonight"]),
  ("verification", "A spare fuse brought the element back to full heat on the bench.", ["full heat", "spare"]))
# 2 A4-SYNTH-R1-02 SY2 small
X("sourdough rise", "Flat sourdough loaves",
  ("finding", "My sourdough loaves have come out flat for a week.", ["come out flat"]),
  ("hypothesis", "The new rye flour might be too weak to hold the rise.", ["rye"]),
  ("counterevidence", "A loaf baked with the previous flour came out just as flat.", ["previous flour"]),
  ("next_step", "Check the starter's activity before blaming the flour.", ["starter"]))
# 3 A4-SYNTH-R1-03 SY3 merge small
X("pond clarity", "Green garden pond",
  ("finding", "The garden pond turned green within four days of the heatwave.", ["heatwave", "four days"]),
  ("finding", "The fish are still feeding normally each evening.", ["fish", "feeding"]),
  ("hypothesis", "Extra sunlight on the pond may be feeding an algae bloom.", ["algae"]),
  ("limitation", "No water test has been taken since spring.", ["water test"]))
# 4 A4-SYNTH-R1-04 SY4 large
X("allotment shed request", "Second shed on plot 14",
  ("request", "A plot holder asked to put a second shed on plot 14.", ["plot holder"]),
  ("authority_boundary", "Allotment rules reserve shed approvals to the site committee chair.", ["shed approvals"]),
  ("finding", "Plot 14 already has one shed beside the boundary hedge.", ["boundary hedge"]),
  ("context", "The reviewer handling this note is the site's water rota volunteer.", ["water rota"]),
  ("next_step", "Pass the request and a plot sketch to the committee chair.", ["sketch"]))
# 5 A4-SYNTH-R2-01 SY5 small
X("team lunch spending", "Team lunch overspend",
  ("design_constraint", "The team lunch budget is capped at 180 per month.", ["180"]),
  ("finding", "This month's lunch receipts total 236.", ["236"]),
  ("next_step", "Flag the overspend to the office manager.", ["office manager"]))
# 6 A4-SYNTH-R2-02 SY6 merge small
X("large invoice payments", "Delayed large invoices",
  ("finding", "Supplier invoices above 5,000 sat unpaid for three extra days.", ["three extra days"]),
  ("finding", "Smaller invoices from the same batch were paid on time.", ["smaller invoices"]),
  ("design_constraint", "The payments policy requires a second signature for invoices above 5,000.",
   ["second signature"]),
  ("next_step", "Warn vendors to expect extra approval time on large bills.", ["vendors"]))
# 7 A4-SYNTH-R2-03 SY1 large
X("payroll export", "Rejected payroll export",
  ("finding", "The payroll export to the bank failed on the 25th.", ["25th"]),
  ("diagnosis", "The bank's rejection notice says the export failed because the signing certificate had expired.",
   ["signing certificate"]),
  ("impact", "Forty staff payments arrived one day late.", ["forty"]),
  ("next_step", "Renew the certificate and resend the payment file.", ["resend"]),
  ("verification", "A test file signed with a fresh certificate was accepted.", ["accepted"]))
# 8 A4-SYNTH-R2-04 SY2 merge large
X("desk lamp returns", "Returned desk lamps",
  ("finding", "Customer returns of desk lamps doubled in March.", ["doubled"]),
  ("finding", "Most returned lamps were logged as arriving with cracked shades.", ["cracked shades"]),
  ("hypothesis", "The new courier may be handling lamp parcels roughly.", ["courier"]),
  ("counterevidence", "Lamps collected in person by customers showed the same cracks.", ["collected in person"]),
  ("next_step", "Inspect sealed boxes straight from the factory.", ["factory"]),
  ("limitation", "Only returns sent with photos were counted.", ["photos"]))
# 9 A4-SYNTH-R3-01 SY3 merge small
X("unusual sign-in alerts", "Unusual sign-in alerts",
  ("finding", "Three staff received an unusual sign-in warning on Monday.", ["three staff"]),
  ("finding", "All three warnings traced to the same overseas location.", ["overseas"]),
  ("hypothesis", "A shared password might have leaked from an old hobby forum.", ["hobby forum"]),
  ("limitation", "The security log keeps only two days of history.", ["two days"]))
# 10 A4-SYNTH-R3-02 SY4 large
X("tenant photo request", "Former tenant photo request",
  ("request", "A former tenant asked for copies of their move-out inspection photos.", ["move-out inspection"]),
  ("authority_boundary", "Only the data protection officer may release personal records.",
   ["personal records"]),
  ("finding", "The photos show the tenant's belongings and a neighbour's car.", ["neighbour's car"]),
  ("context", "The person reviewing the request works on the maintenance desk.", ["maintenance desk"]),
  ("next_step", "Send the request and the photo set to the data protection officer.", ["photo set"]))
# 11 A4-SYNTH-R3-03 SY5 merge large
X("server room badge use", "Badge overuse at the server room",
  ("design_constraint", "Security policy lets each badge open the server room at most twice a day.",
   ["twice a day"]),
  ("finding", "One contractor badge opened the server room nine times on Thursday.", ["nine times"]),
  ("finding", "Door footage shows that badge carried by two different people.", ["two different people"]),
  ("impact", "The room holds the payroll database servers.", ["payroll database"]),
  ("next_step", "Suspend the badge pending a security interview.", ["suspend"]))
# 12 A4-SYNTH-R3-04 SY6 small
X("evening password resets", "Overnight password reset wait",
  ("finding", "Password resets requested in the evening wait until the next morning.", ["next morning"]),
  ("design_constraint", "The helpdesk runbook holds out-of-hours resets until an identity check can be done by phone.",
   ["identity check"]),
  ("next_step", "Add the overnight wait to the reset request page.", ["reset request page"]))
# 13 A4-SYNTH-R4-01 SY1 large
X("forklift roll-away", "Forklift roll-away",
  ("finding", "A forklift rolled forward on the loading ramp this morning.", ["loading ramp"]),
  ("diagnosis", "The service report says it rolled because the handbrake cable had snapped.", ["handbrake cable"]),
  ("impact", "A pallet of glass jars was crushed but nobody was hurt.", ["glass jars"]),
  ("next_step", "Keep the forklift tagged out until the repair is signed off.", ["tagged out"]),
  ("verification", "The truck held firm on the slope after a trial cable swap.", ["held firm"]))
# 14 A4-SYNTH-R4-02 SY3 merge large
X("leaning scaffold tower", "Leaning scaffold tower",
  ("finding", "The east scaffold tower leans about two degrees toward the road.", ["two degrees"]),
  ("finding", "Two base plates rest on soft gravel after last week's rain.", ["base plates"]),
  ("hypothesis", "Settling ground may be causing the lean.", ["settling"]),
  ("limitation", "Nobody has measured the lean since it was first noticed.", ["measured"]),
  ("next_step", "Take daily plumb readings before deciding on repairs.", ["plumb"]))
# 15 A4-SYNTH-R4-03 SY5 small
X("charging cabinet heat", "Hot battery charging cabinet",
  ("design_constraint", "Battery charging cabinets must stay below 35 C.", ["35 c"]),
  ("finding", "The charging cabinet reached 47 C during the afternoon.", ["47 c"]),
  ("next_step", "Stop charging in that cabinet until its fan is checked.", ["fan"]))
# 16 A4-SYNTH-R4-04 SY2 merge small
X("boiler pressure drops", "School boiler pressure drops",
  ("finding", "The school boiler lost pressure twice this week.", ["lost pressure"]),
  ("finding", "Each drop came within an hour of the morning start-up.", ["start-up"]),
  ("hypothesis", "A leaking expansion vessel may be the cause.", ["expansion vessel"]),
  ("counterevidence", "The vessel held its charge in yesterday's pressure test.", ["held its charge"]))
# 17 B4-SYNTH-R1-01 SY1 merge small
X("rear tyre punctures", "Repeated rear tyre punctures",
  ("finding", "My rear tyre has gone flat three mornings running.", ["three mornings"]),
  ("finding", "It holds air every evening when I lock the bike up.", ["holds air"]),
  ("diagnosis", "The shop found a thorn in the tyre casing that caused the repeated punctures.", ["thorn"]),
  ("next_step", "Fit a new inner tube once the casing is clear.", ["inner tube"]))
# 18 B4-SYNTH-R1-02 SY1 small
X("hallway smoke alarm", "Chirping smoke alarm",
  ("finding", "The hallway smoke alarm chirps every forty seconds.", ["forty seconds"]),
  ("diagnosis", "Its display reads low battery, which the manual says causes the chirp.", ["low battery"]),
  ("next_step", "Swap in a fresh nine-volt cell today.", ["nine-volt"]))
# 19 B4-SYNTH-R1-03 SY1 merge large
X("cloudy aquarium", "Cloudy aquarium water",
  ("finding", "The tank water turned milky two days after cleaning.", ["milky"]),
  ("finding", "The fish are gasping near the surface.", ["gasping"]),
  ("diagnosis", "A water test shows the cloudiness comes from a bacteria crash caused by the new filter sponge.",
   ["bacteria crash"]),
  ("impact", "Two neon tetras have died since Sunday.", ["neon tetras"]),
  ("next_step", "Put the old sponge back beside the new one.", ["old sponge"]))
# 20 B4-SYNTH-R1-04 SY2 large
X("choir attendance", "Falling choir attendance",
  ("finding", "Choir attendance fell from thirty to eighteen singers this term.", ["eighteen"]),
  ("hypothesis", "Moving rehearsals to Thursday may have put people off.", ["moving rehearsals"]),
  ("counterevidence", "Last year's Thursday season had full attendance.", ["last year"]),
  ("limitation", "Nobody asked the missing singers why they stopped coming.", ["stopped coming"]),
  ("next_step", "Send a short survey to the lapsed members.", ["survey"]))
# 21 B4-SYNTH-R1-05 SY2 merge small
X("tomato leaf patches", "Brown tomato leaves",
  ("finding", "Brown patches spread across the tomato leaves in August.", ["brown patches"]),
  ("finding", "The lowest leaves were affected first.", ["lowest"]),
  ("hypothesis", "Overhead watering might be spreading a fungal blight.", ["overhead watering"]),
  ("counterevidence", "Plants watered only at the roots show the same marks.", ["roots"]))
# 22 B4-SYNTH-R1-06 SY2 small
X("frozen video calls", "Freezing home video calls",
  ("finding", "Evening video calls keep freezing on the home network.", ["home network"]),
  ("hypothesis", "The neighbour's new router might be crowding our channel.", ["neighbour's"]),
  ("counterevidence", "Calls also freeze on a laptop cabled straight into the router.", ["cabled"]))
# 23 B4-SYNTH-R1-07 SY3 merge large
X("spaniel weight gain", "Spaniel weight gain",
  ("finding", "Our spaniel gained two kilograms since the spring.", ["two kilograms"]),
  ("finding", "She now tires halfway through her usual walk.", ["halfway"]),
  ("hypothesis", "The new chew treats may be adding too many calories.", ["chew treats"]),
  ("limitation", "Her meals have not been weighed since the bag changed.", ["weighed"]),
  ("next_step", "Book a weight check with the vet next week.", ["vet"]))
# 24 B4-SYNTH-R1-08 SY3 large
X("cracked kiln mugs", "Cracked mugs after firing",
  ("finding", "Four mugs cracked in the last kiln firing.", ["four mugs"]),
  ("hypothesis", "Heating the kiln too quickly might have caused the cracks.", ["too quickly"]),
  ("limitation", "The kiln controller does not record its heating rate.", ["controller"]),
  ("context", "The mugs came from two different clay batches.", ["clay batches"]),
  ("next_step", "Fire a single test mug with a slower ramp.", ["slower ramp"]))
# 25 B4-SYNTH-R1-09 SY3 merge small
X("feeder visits", "Fewer finches at the feeder",
  ("finding", "Fewer finches visited the garden feeder this month.", ["garden feeder"]),
  ("finding", "The sunflower hearts are going stale in the tube.", ["stale"]),
  ("hypothesis", "A sparrowhawk seen nearby may be scaring small birds away.", ["sparrowhawk"]))
# 26 B4-SYNTH-R1-10 SY4 small
X("village hall kitchen", "Hall kitchen for a birthday",
  ("request", "A neighbour asked to use the village hall kitchen for a birthday party.", ["birthday party"]),
  ("authority_boundary", "The hall constitution says only the bookings secretary can approve kitchen use.",
   ["bookings secretary"]),
  ("next_step", "Forward the neighbour's preferred dates to the secretary.", ["preferred dates"]))
# 27 B4-SYNTH-R1-11 SY4 merge large
X("shared garden birch", "Leaning birch in the shared garden",
  ("request", "Two residents want the leaning birch in the shared garden cut down.", ["cut down"]),
  ("finding", "The birch leans toward the bike shelter.", ["bike shelter"]),
  ("finding", "Its roots have lifted two paving slabs.", ["paving slabs"]),
  ("authority_boundary", "The residents' agreement reserves tree work to the managing agent.", ["managing agent"]),
  ("context", "The person reviewing this is the garden's volunteer coordinator.", ["volunteer coordinator"]),
  ("next_step", "Send the photos and both residents' notes to the agent.", ["photos"]))
# 28 B4-SYNTH-R1-12 SY4 large
X("relay vest purchase", "Relay vest purchase",
  ("request", "The running club captain asked to buy new relay vests.", ["relay vests"]),
  ("authority_boundary", "Club rules say purchases over 100 need the treasurer's sign-off.", ["treasurer"]),
  ("finding", "The supplier's price for the vests is 240.", ["240"]),
  ("context", "The reviewer here is the club's route planner.", ["route planner"]),
  ("next_step", "Pass the price and the captain's note on for sign-off.", ["captain's note"]))
# 29 B4-SYNTH-R1-13 SY5 merge small
X("caravan towing weight", "Overweight caravan",
  ("design_constraint", "The car's handbook limits braked towing to 1,500 kg.", ["1,500"]),
  ("finding", "The loaded caravan weighed 1,720 kg at the public weighbridge.", ["1,720"]),
  ("finding", "The bike rack on the caravan adds another 40 kg.", ["40 kg"]),
  ("next_step", "Unload heavy gear from the caravan before towing it.", ["heavy gear"]))
# 30 B4-SYNTH-R1-14 SY5 small
X("allotment water use", "Plot water overuse",
  ("design_constraint", "Each allotment plot may use 300 litres of mains water a week.", ["300 litres"]),
  ("finding", "Plot 9's meter shows 610 litres used this week.", ["610"]),
  ("next_step", "Remind the plot holder about the weekly allowance.", ["allowance"]))
# 31 B4-SYNTH-R1-15 SY5 merge large
X("hot tub chlorine", "High hot tub chlorine",
  ("design_constraint", "Hot tub chlorine should stay between 3 and 5 parts per million.", ["3 and 5"]),
  ("finding", "Saturday's strip test read 9 parts per million.", ["strip test"]),
  ("finding", "A second strip an hour later also read 9.", ["second strip"]),
  ("impact", "Two guests reported itchy skin after using the tub.", ["itchy skin"]),
  ("next_step", "Close the tub and dilute the water before reopening.", ["dilute"]))
# 32 B4-SYNTH-R1-16 SY6 large
X("e-reader shutdowns", "E-reader switching off",
  ("finding", "The e-reader switches itself off after five minutes without a page turn.", ["page turn"]),
  ("design_constraint", "Its power settings are set to sleep after five idle minutes.", ["power settings"]),
  ("verification", "Changing the setting to thirty minutes stopped the early shutdowns.", ["thirty minutes"]),
  ("comparison", "The same device stays on while it is charging.", ["charging"]),
  ("next_step", "Note the sleep setting in the family device guide.", ["family device guide"]))
# 33 B4-SYNTH-R1-17 SY6 merge small
X("expired library holds", "Library holds going back",
  ("finding", "Library holds disappear if not collected within a week.", ["disappear"]),
  ("finding", "Two of my reserved books went back to the shelf on day eight.", ["day eight"]),
  ("design_constraint", "The library's lending policy releases uncollected holds after seven days.",
   ["seven days"]),
  ("next_step", "Collect future holds within the first few days.", ["future holds"]))
# 34 B4-SYNTH-R1-18 SY6 small
X("living room night cooling", "Night-time living room cooling",
  ("finding", "The living room cools to 16 C every night at 23:00.", ["23:00"]),
  ("design_constraint", "The thermostat's night schedule lowers the target to 16 C from eleven.",
   ["night schedule"]),
  ("next_step", "Keep the schedule and use a blanket for late films.", ["blanket"]))
# 35 B4-SYNTH-R2-01 SY3 merge small
X("online checkout completions", "Falling checkout completions",
  ("finding", "Checkout completions dropped 9% last week.", ["dropped 9%"]),
  ("finding", "Average basket sizes stayed about the same.", ["basket sizes"]),
  ("hypothesis", "The new delivery charge might be putting buyers off.", ["delivery charge"]),
  ("limitation", "The analytics tool has been live for just eight days.", ["eight days"]))
# 36 B4-SYNTH-R2-02 SY3 small
X("late warehouse timesheets", "Late warehouse timesheets",
  ("finding", "Half of the warehouse timesheets were submitted late in April.", ["half"]),
  ("hypothesis", "The new mobile form may be harder to use than paper.", ["mobile form"]),
  ("limitation", "No staff have been asked about the form yet.", ["asked"]))
# 37 B4-SYNTH-R2-03 SY3 merge large
X("conference room cancellations", "Conference room cancellations",
  ("finding", "Cancellations of conference room bookings rose to twelve in May.", ["twelve"]),
  ("finding", "Most cancellations came within two days of the event.", ["two days"]),
  ("hypothesis", "Stricter deposit terms might be pushing clients to book provisionally.", ["deposit terms"]),
  ("limitation", "Reasons for cancelling are not recorded in the booking system.", ["not recorded"]),
  ("next_step", "Ask the next five cancelling clients for their reason.", ["next five"]))
# 38 B4-SYNTH-R2-04 SY4 large
X("supplier payment terms", "Shorter payment terms request",
  ("request", "A supplier asked to move from 60-day to 14-day payment terms.", ["14-day"]),
  ("authority_boundary", "Changing payment terms is reserved to the finance director.", ["finance director"]),
  ("finding", "The supplier provides packaging for three product lines.", ["packaging"]),
  ("context", "The reviewer on this ticket is an accounts payable clerk.", ["accounts payable clerk"]),
  ("next_step", "Send the supplier's letter upward with the spend summary.", ["spend summary"]))
# 39 B4-SYNTH-R2-05 SY4 merge small
X("meeting room repaint", "Meeting room repaint request",
  ("request", "The design team asked to repaint the meeting room dark green.", ["dark green"]),
  ("authority_boundary", "Building alterations need approval from the landlord's facilities lead.",
   ["facilities lead"]),
  ("authority_boundary", "The lease also bans changes without written landlord consent.", ["written"]),
  ("next_step", "Pass the colour request to the landlord.", ["colour request"]))
# 40 B4-SYNTH-R2-06 SY4 small
X("weekend overtime", "Weekend overtime for packers",
  ("request", "A shift supervisor asked to approve weekend overtime for six packers.", ["six packers"]),
  ("authority_boundary", "The staffing policy reserves overtime approval to the operations manager.",
   ["operations manager"]),
  ("next_step", "Route the request and the draft rota to the manager.", ["draft rota"]))
# 41 B4-SYNTH-R2-07 SY5 merge large
X("company card purchase", "Card purchase over the limit",
  ("design_constraint", "Company cards have a single-purchase limit of 750.", ["750"]),
  ("finding", "One card was used for a 1,180 printer purchase.", ["1,180"]),
  ("finding", "The receipt shows a single payment, not several smaller ones.", ["single payment"]),
  ("impact", "The printer went to a branch that already has two.", ["branch"]),
  ("next_step", "Refer the purchase to the card administrator.", ["card administrator"]))
# 42 B4-SYNTH-R2-08 SY5 large
X("tile pallet weight", "Overweight tile pallet",
  ("design_constraint", "The courier contract allows pallets up to 800 kg.", ["800 kg"]),
  ("finding", "The outgoing pallet of floor tiles weighed 1,030 kg.", ["1,030"]),
  ("impact", "The courier may refuse the collection at the gate.", ["refuse"]),
  ("corroboration", "A second weighing on the dock scale read 1,025 kg.", ["dock scale"]),
  ("next_step", "Split the tiles across two pallets.", ["two pallets"]))
# 43 B4-SYNTH-R2-09 SY5 merge small
X("planning meeting headcount", "Overfull planning meeting",
  ("design_constraint", "Meeting room B seats a maximum of ten people.", ["ten people"]),
  ("finding", "Fourteen people attended Tuesday's planning meeting in that room.", ["fourteen"]),
  ("finding", "Extra chairs were brought in from the kitchen.", ["extra chairs"]),
  ("next_step", "Book the larger hall for the next session.", ["larger hall"]))
# 44 B4-SYNTH-R2-10 SY6 small
X("year-end leave requests", "Blocked year-end leave",
  ("finding", "Leave requests for the last week of December are rejected automatically.",
   ["rejected automatically"]),
  ("design_constraint", "The personnel system blocks leave during the year-end stock count.", ["stock count"]),
  ("next_step", "Explain the block to staff who ask.", ["explain"]))
# 45 B4-SYNTH-R2-11 SY6 merge large
X("invoice rounding", "Rounded invoice totals",
  ("finding", "Customer invoices show totals rounded to the nearest 5 cents.", ["5 cents"]),
  ("finding", "Card payments for the same orders are charged to the exact cent.", ["exact cent"]),
  ("design_constraint", "The billing system is set to cash rounding for printed invoices.", ["cash rounding"]),
  ("verification", "Turning the option off in a test account printed exact totals.", ["test account"]),
  ("next_step", "Add a rounding note to the invoice footer.", ["footer"]))
# 46 B4-SYNTH-R2-12 SY6 large
X("paper reordering", "Automatic paper reorders",
  ("finding", "Printer paper is reordered every time stock falls below 20 boxes.", ["20 boxes"]),
  ("design_constraint", "The inventory system has a reorder point set for paper.", ["reorder point"]),
  ("comparison", "Toner, which has no such trigger, ran out twice this year.", ["toner"]),
  ("verification", "Paper orders in the log line up with each dip in stock.", ["dip"]),
  ("next_step", "Ask purchasing to configure the same trigger for cartridges.", ["purchasing"]))
# 47 B4-SYNTH-R2-13 SY1 merge small
X("cafe card terminal", "Cafe card terminal outage",
  ("finding", "The cafe card terminal declined every payment after lunch.", ["every payment"]),
  ("finding", "Cash sales carried on normally.", ["cash sales"]),
  ("diagnosis", "The payment provider says the terminal declined cards because our merchant account was "
                "suspended over an unpaid fee.", ["unpaid fee"]),
  ("next_step", "Clear the balance and ask the provider to reinstate the account.", ["reinstate"]))
# 48 B4-SYNTH-R2-14 SY1 small
X("missing stationery delivery", "Returned stationery order",
  ("finding", "The stationery order due on Monday never arrived.", ["due on Monday"]),
  ("diagnosis", "The courier says the parcel was returned because the unit number was missing from the address.",
   ["unit number", "parcel"]),
  ("next_step", "Correct the saved delivery address before reordering.", ["saved delivery address"]))
# 49 B4-SYNTH-R2-15 SY1 merge large
X("duplicate salary payments", "Duplicate salary payments",
  ("finding", "Seven employees were paid twice in the March run.", ["seven employees"]),
  ("finding", "Each extra payment matched their normal net salary.", ["net salary"]),
  ("diagnosis", "The payroll log shows the duplicates happened because the payment file was resubmitted after "
                "a timeout.", ["timeout"]),
  ("impact", "The business account went overdrawn for two days.", ["overdrawn"]),
  ("next_step", "Request recall of the extra payments through the bank.", ["recall"]),
  ("verification", "The bank confirmed only one file should have been accepted.", ["only one file"]))
# 50 B4-SYNTH-R2-16 SY2 large
X("late web orders", "Late web orders",
  ("finding", "Twenty percent of web orders shipped late in June.", ["twenty percent"]),
  ("hypothesis", "The warehouse's new picking software may be slowing packers down.", ["picking software"]),
  ("counterevidence", "Pick times in the software logs are faster than last year.", ["faster"]),
  ("limitation", "Courier collection times were not logged in June.", ["collection times"]),
  ("next_step", "Compare packed and collected times for a sample of orders.", ["sample"]))
# 51 B4-SYNTH-R2-17 SY2 merge small
X("vending machine takings", "Falling vending takings",
  ("finding", "Vending machine takings fell by a third in the staff canteen.", ["a third"]),
  ("finding", "Stock levels in the machine barely changed.", ["stock levels"]),
  ("hypothesis", "A broken coin mechanism may be rejecting payments.", ["coin mechanism"]),
  ("counterevidence", "The service engineer found the coin slot working normally.", ["service engineer"]))
# 52 B4-SYNTH-R2-18 SY2 small
X("conference no-shows", "Trade conference no-shows",
  ("finding", "One in four registered delegates did not attend the trade conference.", ["one in four"]),
  ("hypothesis", "The venue change announced a week before may have confused people.", ["venue change"]),
  ("counterevidence", "No-show rates were the same for delegates who had confirmed the new venue.",
   ["confirmed"]))
# 53 B4-SYNTH-R3-01 SY5 merge small
X("client folder sharing", "Overshared client folder",
  ("design_constraint", "Client folders may be shared with at most five named staff.", ["five named staff"]),
  ("finding", "The tax-returns folder is shared with 23 staff.", ["tax-returns"]),
  ("finding", "Six of those accounts belong to people who left last year.", ["left last year"]),
  ("next_step", "Withdraw access for everyone not listed on the client file.", ["not listed"]))
# 54 B4-SYNTH-R3-02 SY5 small
X("backup server password age", "Stale admin password",
  ("design_constraint", "Admin passwords must be changed at least every 90 days.", ["90 days"]),
  ("finding", "The backup server's admin password was last changed 214 days ago.", ["214"]),
  ("next_step", "Change that password and record the date in the vault.", ["vault"]))
# 55 B4-SYNTH-R3-03 SY5 merge large
X("applicant record retention", "Old applicant records",
  ("design_constraint", "Job applicant records must be deleted twelve months after the role closes.",
   ["twelve months"]),
  ("finding", "The recruitment drive still holds applicant files from 2029.", ["2029"]),
  ("finding", "Some of those files include copies of passports.", ["passports"]),
  ("impact", "Keeping them breaks the notice given to applicants.", ["notice"]),
  ("next_step", "Schedule the old files for secure disposal.", ["secure disposal"]))
# 56 B4-SYNTH-R3-04 SY6 large
X("records system timeout", "Records system logouts",
  ("finding", "Staff are logged out of the records system after ten idle minutes.", ["ten idle minutes"]),
  ("design_constraint", "The security baseline sets a short session timeout for systems holding health data.",
   ["baseline"]),
  ("comparison", "The staff rota tool, which holds no health data, allows an hour.", ["rota tool"]),
  ("verification", "The timeout setting in the admin console reads 600 seconds.", ["600 seconds"]),
  ("next_step", "Explain the timeout rule at the next staff briefing.", ["briefing"]))
# 57 B4-SYNTH-R3-05 SY6 merge small
X("stripped script attachments", "Missing script attachments",
  ("finding", "Attachments ending in .js never reach staff inboxes.", ["ending in .js"]),
  ("finding", "Senders receive a notice that the file was removed.", ["notice"]),
  ("design_constraint", "The mail filter policy strips script attachments from inbound email.", ["mail filter"]),
  ("next_step", "Ask partners to share scripts through the file portal.", ["file portal"]))
# 58 B4-SYNTH-R3-06 SY6 small
X("visitor badge cut-off", "Visitor badges stop at six",
  ("finding", "Visitor badges stop opening doors at 18:00 each day.", ["18:00"]),
  ("design_constraint", "The access profile for visitors ends at six in the evening.", ["access profile"]),
  ("next_step", "Issue contractor badges to visitors who work late.", ["contractor badges"]))
# 59 B4-SYNTH-R3-07 SY1 merge large
X("laptop encryption alerts", "Laptop encryption alerts",
  ("finding", "Twelve laptops reported disk encryption as switched off overnight.", ["twelve laptops"]),
  ("finding", "All of them had installed the same driver update.", ["driver update"]),
  ("diagnosis", "The vendor advisory states that driver version 5.1 pauses encryption, which caused the alerts.",
   ["5.1", "advisory"]),
  ("impact", "Those laptops held unencrypted data for about six hours.", ["six hours"]),
  ("next_step", "Roll the affected laptops back to the earlier driver.", ["earlier driver"]))
# 60 B4-SYNTH-R3-08 SY1 large
X("booking site certificate", "Booking site security warning",
  ("finding", "Visitors saw a security warning on the booking site this morning.", ["visitors saw a security warning"]),
  ("diagnosis", "The certificate report shows the warning appeared because the site certificate expired at "
                "midnight.", ["midnight"]),
  ("impact", "Online bookings stopped for about four hours.", ["four hours"]),
  ("next_step", "Install the renewed certificate and switch on auto-renewal.", ["auto-renewal"]),
  ("verification", "A test browser loaded the site cleanly after the swap.", ["test browser"]))
# 61 B4-SYNTH-R3-09 SY1 merge small
X("unlocked records room", "Records room left unlocked",
  ("finding", "The records room door was found unlocked on Saturday.", ["found unlocked"]),
  ("finding", "Nothing inside appears to have been disturbed.", ["disturbed"]),
  ("diagnosis", "The access log shows the door stayed open because the lock failed to re-engage after a power cut.",
   ["power cut"]))
# 62 B4-SYNTH-R3-10 SY2 small
X("shared inbox spam", "Shared inbox spam surge",
  ("finding", "The shared inbox received 900 spam messages yesterday.", ["900"]),
  ("hypothesis", "Our address may have been scraped from the new website contact page.", ["contact page"]),
  ("counterevidence", "The address was never published on the new website.", ["never published"]))
# 63 B4-SYNTH-R3-11 SY2 merge large
X("nightly backup failures", "Failing nightly backups",
  ("finding", "The nightly backup failed on three of the last five nights.", ["three of the last five"]),
  ("finding", "Each failure happened after 02:00.", ["02:00"]),
  ("hypothesis", "An antivirus scan may be locking the backup files.", ["antivirus"]),
  ("counterevidence", "The job also failed on the night the scan was disabled.", ["disabled"]),
  ("limitation", "The backup tool's error messages are not being kept.", ["error messages"]),
  ("next_step", "Turn on verbose logging for the backup job.", ["verbose logging"]))
# 64 B4-SYNTH-R3-12 SY2 large
X("unknown admin account", "Unknown file server admin",
  ("finding", "An unknown admin account appeared on the file server.", ["appeared on the file server"]),
  ("hypothesis", "A recent intrusion may have created the account.", ["intrusion"]),
  ("counterevidence", "The account's creation matches a scheduled vendor maintenance visit.",
   ["vendor maintenance"]),
  ("limitation", "The vendor has not yet confirmed who carried out the visit.", ["carried out"]),
  ("next_step", "Disable the account until the vendor answers.", ["until the vendor answers"]))
# 65 B4-SYNTH-R3-13 SY3 merge small
X("customer privacy complaint", "Quoted order history",
  ("finding", "A customer says a stranger quoted her order history back to her.", ["stranger quoted"]),
  ("finding", "Her account shows no password change this year.", ["password change"]),
  ("hypothesis", "Her login details may have been reused from another site.", ["reused"]),
  ("limitation", "Only the customer's own account has been reviewed.", ["reviewed"]))
# 66 B4-SYNTH-R3-14 SY3 small
X("found memory stick", "Memory stick in the car park",
  ("finding", "A cleaner handed in a memory stick found in the car park.", ["cleaner handed in"]),
  ("hypothesis", "It might belong to the finance team, who use that entrance.", ["finance team"]),
  ("limitation", "Nobody has checked the stick's contents in a safe environment.", ["safe environment"]))
# 67 B4-SYNTH-R3-15 SY3 merge large
X("loading bay camera gap", "Camera recording gap",
  ("finding", "The loading bay camera recorded nothing for 40 minutes on Friday night.", ["40 minutes"]),
  ("finding", "No alarms were triggered during that time.", ["alarms"]),
  ("hypothesis", "Someone may have unplugged the camera deliberately.", ["deliberately"]),
  ("limitation", "The recorder keeps no record of power events.", ["power events"]),
  ("next_step", "Fit a tamper sensor to the camera's power lead.", ["tamper sensor"]))
# 68 B4-SYNTH-R3-16 SY4 large
X("research data request", "Clinic visit data request",
  ("request", "A research partner asked for anonymised patient visit counts.", ["anonymised"]),
  ("authority_boundary", "Data sharing agreements can only be signed by the information governance lead.",
   ["information governance lead"]),
  ("finding", "The counts would cover three clinics over two years.", ["three clinics"]),
  ("context", "The reviewer on this request is a clinic administrator.", ["clinic administrator"]),
  ("next_step", "Pass the request on with a draft list of fields.", ["draft list"]))
# 69 B4-SYNTH-R3-17 SY4 merge small
X("demo port request", "Demo port opening",
  ("request", "A developer asked to open port 8443 to the internet for a demo.", ["8443"]),
  ("authority_boundary", "Firewall changes need sign-off from the network security manager.",
   ["network security manager"]),
  ("authority_boundary", "Changes made for demos also require a written risk note.", ["risk note"]),
  ("next_step", "Forward the developer's ask to the security manager.", ["developer's ask"]))
# 70 B4-SYNTH-R3-18 SY4 small
X("suspended mailbox unlock", "Suspended mailbox unlock",
  ("request", "A manager asked to unlock a suspended employee's email account.", ["suspended employee"]),
  ("authority_boundary", "Only personnel services can lift a suspension during an investigation.",
   ["investigation"]),
  ("next_step", "Refer the manager's request to personnel services.", ["refer"]))
# 71 B4-SYNTH-R4-01 SY4 merge large
X("roof truss lift", "Roof truss lift in wind",
  ("request", "The site foreman wants to lift the roof trusses this afternoon.", ["roof trusses"]),
  ("finding", "Gusts on site reached 38 km/h this morning.", ["38 km/h"]),
  ("finding", "The forecast shows stronger gusts after 14:00.", ["14:00"]),
  ("authority_boundary", "The lift plan gives the appointed person sole authority to start or stop lifts.",
   ["appointed person"]),
  ("context", "The reviewer is the site's first-aid lead.", ["first-aid lead"]),
  ("next_step", "Send the wind readings on before any lift.", ["wind readings"]))
# 72 A4-SYNTH-R1-X01 SY1 merge large
X("fridge water leak", "Leaking kitchen fridge",
  ("finding", "Water keeps pooling under the kitchen fridge.", ["pooling"]),
  ("finding", "The puddle appears most mornings, not during the day.", ["most mornings"]),
  ("diagnosis", "The repair guide says a blocked defrost drain causes this leak, and the drain was blocked.",
   ["defrost drain"]),
  ("next_step", "Clear the drain hole with warm water.", ["warm water"]),
  ("verification", "After clearing it, no water appeared for three days.", ["three days"]))
# 73 A4-SYNTH-R1-X02 SY2 small
X("wilting peace lily", "Wilting peace lily",
  ("finding", "The peace lily wilts a day after every watering.", ["day after every watering"]),
  ("hypothesis", "Too much water may be rotting its roots.", ["rotting"]),
  ("counterevidence", "The roots looked white and firm when it was repotted last week.", ["white and firm"]),
  ("next_step", "Move it away from the radiator and watch it for a week.", ["radiator"]))
# 74 A4-SYNTH-R1-X03 SY3 merge small
X("violin tuning drift", "Violin string going flat",
  ("finding", "My violin's top string slips flat during practice.", ["slips flat"]),
  ("finding", "The other strings stay in tune.", ["other strings"]),
  ("hypothesis", "The peg may be worn smooth.", ["peg"]))
# 75 A4-SYNTH-R1-X04 SY4 large
X("car club booking", "Week-long car club booking",
  ("request", "A neighbour asked to borrow the car club car for a week.", ["borrow"]),
  ("authority_boundary", "Car club bookings over three days need the club organiser's approval.",
   ["club organiser"]),
  ("finding", "The car is already booked by another member on Thursday.", ["another member"]),
  ("context", "The person reviewing the ask is the club's newsletter editor.", ["newsletter editor"]),
  ("next_step", "Pass the requested dates to the organiser.", ["requested dates"]))
# 76 A4-SYNTH-R2-X01 SY5 small
X("department stationery spend", "Stationery overspend",
  ("design_constraint", "Each department may spend 400 a quarter on stationery.", ["400"]),
  ("finding", "The design department has spent 655 this quarter.", ["655"]),
  ("next_step", "Hold further orders from design until next quarter.", ["hold further orders"]))
# 77 A4-SYNTH-R2-X02 SY6 merge small
X("support auto-replies", "After-hours auto-replies",
  ("finding", "Customers emailing after 17:30 get an automatic reply.", ["17:30"]),
  ("finding", "The reply promises an answer the next working day.", ["next working day"]),
  ("design_constraint", "The support desk's out-of-hours rule sends that reply outside office hours.",
   ["out-of-hours"]),
  ("next_step", "Add the office hours to the contact page.", ["contact page"]))
# 78 A4-SYNTH-R2-X03 SY1 large
X("course refund delays", "Slow course refunds",
  ("finding", "Refunds for cancelled courses have taken three weeks this month.", ["three weeks"]),
  ("diagnosis", "The finance log shows the refunds stalled because a bank approval code was missing.",
   ["approval code"]),
  ("impact", "Eleven learners have complained about the wait.", ["eleven learners"]),
  ("next_step", "Reissue the code to the finance team.", ["reissue"]),
  ("verification", "Two refunds cleared within an hour of a test code being issued.", ["within an hour"]))
# 79 A4-SYNTH-R2-X04 SY2 merge large
X("office printer jams", "Frequent printer jams",
  ("finding", "The office printer jammed nineteen times last week.", ["nineteen"]),
  ("finding", "Most jams happened during double-sided printing.", ["double-sided"]),
  ("hypothesis", "The cheaper paper brand may be too thin.", ["cheaper paper"]),
  ("counterevidence", "Jams continued on days the old paper stock was used.", ["old paper stock"]),
  ("limitation", "The printer's jam counter was reset last month.", ["jam counter"]),
  ("next_step", "Ask the engineer to check the duplex rollers.", ["duplex rollers"]))
# 80 A4-SYNTH-R3-X01 SY3 merge small
X("phone left in taxi", "Work phone left in a taxi",
  ("finding", "A manager left a work phone in a taxi on Tuesday.", ["manager left a work phone"]),
  ("finding", "The driver returned the phone the next day.", ["driver"]),
  ("hypothesis", "Someone may have read messages while it was missing.", ["read messages"]),
  ("limitation", "The phone keeps no log of unlock attempts.", ["unlock attempts"]))
# 81 A4-SYNTH-R3-X02 SY4 large
X("street camera footage", "Street camera footage request",
  ("request", "A shop owner asked for our street camera footage from Friday night.", ["shop owner"]),
  ("authority_boundary", "Camera footage may only be disclosed by the site privacy officer.",
   ["privacy officer"]),
  ("finding", "The footage shows several members of the public.", ["members of the public"]),
  ("context", "The reviewer here is the reception supervisor.", ["reception supervisor"]),
  ("next_step", "Send the owner's request on with the time range.", ["time range"]))
# 82 A4-SYNTH-R3-X03 SY5 merge large
X("supplier remote sessions", "Long supplier remote session",
  ("design_constraint", "Supplier remote sessions must end within four hours.", ["four hours"]),
  ("finding", "One supplier session stayed open for 31 hours.", ["31 hours"]),
  ("finding", "The session sat idle for most of that time.", ["idle"]),
  ("impact", "An open session could let anyone at the supplier reach our servers.", ["reach our servers"]),
  ("next_step", "End the session and ask the supplier for a written explanation.", ["written explanation"]))
# 83 A4-SYNTH-R3-X04 SY6 small
X("blocked cloud downloads", "Blocked personal cloud downloads",
  ("finding", "Staff cannot download files larger than 50 MB from personal cloud drives.", ["50 mb"]),
  ("design_constraint", "The web gateway policy blocks large downloads from unmanaged storage.",
   ["unmanaged storage"]),
  ("next_step", "Point staff to the approved transfer service instead.", ["approved transfer service"]))
# 84 A4-SYNTH-R4-X01 SY1 large
X("stepladder collapse", "Collapsed stepladder",
  ("finding", "A stepladder buckled while a painter stood on the third step.", ["third step"]),
  ("diagnosis", "The inspection found the ladder collapsed because a rivet in the left leg hinge had cracked.",
   ["left leg hinge"]),
  ("impact", "The painter sprained a wrist.", ["sprained"]),
  ("next_step", "Withdraw all ladders from the same batch.", ["same batch"]),
  ("verification", "The manufacturer confirmed a fault in that production run.", ["manufacturer"]))
# 85 A4-SYNTH-R4-X02 SY3 merge large
X("kitchen gas smell", "Faint kitchen gas smell",
  ("finding", "Staff reported a faint gas smell near the kitchen at 07:00.", ["07:00"]),
  ("finding", "The smell had cleared when the engineer arrived.", ["cleared"]),
  ("hypothesis", "A pilot light may have gone out briefly.", ["pilot light"]),
  ("limitation", "No gas detector is fitted in the kitchen.", ["gas detector"]),
  ("next_step", "Install a monitor and repeat the leak survey.", ["leak survey"]))
# 86 A4-SYNTH-R4-X03 SY5 small
X("narrowed fire exit", "Narrowed rear fire exit",
  ("design_constraint", "Fire exits must keep a clear width of at least 1.1 metres.", ["1.1 metres"]),
  ("finding", "Pallets narrowed the rear fire exit to 0.6 metres on Monday.", ["0.6"]),
  ("next_step", "Move the pallets and brief the stores team.", ["stores team"]))
# 87 A4-SYNTH-R4-X04 SY2 merge small
X("press guard trips", "Press guard trips",
  ("finding", "The press guard stopped the machine six times on Wednesday.", ["six times"]),
  ("finding", "Operators say nobody was near the guard when it tripped.", ["nobody"]),
  ("hypothesis", "A dirty light curtain sensor may be giving false trips.", ["light curtain"]),
  ("counterevidence", "The sensor was cleaned at the start of the shift and still tripped.", ["cleaned"]))
# 88 B4-SYNTH-R1-X01 SY1 merge small
X("video doorbell recording", "Doorbell stopped recording",
  ("finding", "The video doorbell stopped recording visitors last night.", ["recording visitors"]),
  ("finding", "Its app still shows the device as online.", ["online"]),
  ("diagnosis", "The app's event log says recording stopped because the storage card is full.",
   ["storage card"]))
# 89 B4-SYNTH-R1-X02 SY2 small
X("cold compost heap", "Cold compost heap",
  ("finding", "The compost heap has stayed cold for a month.", ["stayed cold"]),
  ("hypothesis", "Too many dry leaves may be slowing it down.", ["dry leaves"]),
  ("counterevidence", "A second heap with the same leaf mix is steaming hot.", ["steaming"]))
# 90 B4-SYNTH-R1-X03 SY3 merge large
X("cat appetite", "Cat leaving food",
  ("finding", "Our cat has left half her meals for three days.", ["half her meals"]),
  ("finding", "She is still drinking and playing normally.", ["playing"]),
  ("hypothesis", "The new food brand may not suit her.", ["food brand"]),
  ("limitation", "We have not weighed her since the change.", ["weighed"]),
  ("next_step", "Mix some of the old food back in and watch her appetite.", ["old food back"]))
# 91 B4-SYNTH-R1-X04 SY4 large
X("street party closure", "Street party road closure",
  ("request", "Residents asked to close the street for a summer party.", ["summer party"]),
  ("authority_boundary", "Road closures need a permit from the council's highways officer.",
   ["highways officer"]),
  ("finding", "The street is a bus diversion route on weekends.", ["bus diversion"]),
  ("context", "The reviewer is the residents' association secretary.", ["association secretary"]),
  ("next_step", "Send the party plan to the permit office.", ["party plan"]))
# 92 B4-SYNTH-R2-X01 SY5 merge small
X("fair hotel rates", "Hotel rates over policy",
  ("design_constraint", "Travel policy caps hotel rates at 140 a night.", ["140"]),
  ("finding", "The sales team booked rooms at 198 a night for the fair.", ["198"]),
  ("finding", "Cheaper rooms were available two streets away.", ["two streets away"]))
# 93 B4-SYNTH-R2-X02 SY6 small
X("locked timesheets", "Locked timesheets",
  ("finding", "Timesheets cannot be edited after Tuesday noon.", ["edited"]),
  ("design_constraint", "Payroll settings lock each week's timesheets once the pay run starts.", ["pay run"]),
  ("next_step", "Remind staff to submit corrections by Monday evening.", ["corrections"]))
# 94 B4-SYNTH-R2-X03 SY3 merge large
X("gym cancellations", "Early-month gym cancellations",
  ("finding", "Twelve gym members cancelled in the first week of the month.", ["twelve gym members"]),
  ("finding", "Nine of them had joined in January.", ["nine of them"]),
  ("hypothesis", "An introductory discount ending may be driving the cancellations.", ["introductory discount"]),
  ("limitation", "The exit form does not ask for a reason.", ["exit form"]),
  ("next_step", "Add a reason field to the cancellation form.", ["reason field"]))
# 95 B4-SYNTH-R2-X04 SY4 large
X("renewal discount", "Renewal discount request",
  ("request", "A long-standing client asked for a 15% discount on renewal.", ["15%"]),
  ("authority_boundary", "Discounts above 10% can only be granted by the commercial director.",
   ["commercial director"]),
  ("finding", "The client's account has been profitable for five years.", ["profitable"]),
  ("context", "The reviewer is the client's account coordinator.", ["account coordinator"]),
  ("next_step", "Put the discount request forward with the account history.", ["account history"]))
# 96 B4-SYNTH-R3-X01 SY5 merge small
X("payment database key age", "Old payment encryption key",
  ("design_constraint", "Encryption keys for the payment database must be replaced every year.", ["every year"]),
  ("finding", "The current payment key was created three years ago.", ["three years ago"]),
  ("finding", "No replacement key has been scheduled.", ["scheduled"]))
# 97 B4-SYNTH-R3-X02 SY6 small
X("reception screen locks", "Quick reception screen locks",
  ("finding", "Reception screens lock after two minutes without input.", ["without input"]),
  ("design_constraint", "Screens facing public areas are configured for a two-minute lock.", ["public areas"]),
  ("next_step", "Tell reception staff the lock is intentional.", ["intentional"]))
# 98 B4-SYNTH-R3-X03 SY1 merge large
X("leaked phone list", "Leaked customer phone list",
  ("finding", "A spreadsheet of customer phone numbers appeared on a public file site.", ["public file site"]),
  ("finding", "The file name matches one exported from our sales system last month.", ["exported"]),
  ("diagnosis", "The sharing log shows the leak happened because a staff member set the file's link to public "
                "access.", ["sharing log"]),
  ("impact", "About 2,300 customers are affected.", ["2,300"]),
  ("next_step", "Disable the link and notify the privacy regulator.", ["regulator"]))
# 99 B4-SYNTH-R3-X04 SY2 large
X("afternoon vpn drops", "Afternoon VPN drops",
  ("finding", "Remote staff report the VPN dropping every afternoon.", ["dropping"]),
  ("hypothesis", "The VPN licence may be capping concurrent users.", ["licence"]),
  ("counterevidence", "Drops happen even when only four users are connected.", ["four users"]),
  ("limitation", "The appliance logs are overwritten daily.", ["overwritten"]),
  ("next_step", "Export the logs each evening for a week.", ["each evening"]))
# 100 B4-SYNTH-R4-X01 SY4 merge large
X("wet well entry", "Pumping station wet well entry",
  ("request", "A contractor wants to enter the pumping station wet well today.", ["contractor wants to enter"]),
  ("finding", "The gas monitor shows low oxygen near the hatch.", ["low oxygen"]),
  ("finding", "The ventilation fan has not been run this morning.", ["ventilation fan"]),
  ("authority_boundary", "Confined space entry can only be authorised by the permit issuer.", ["permit issuer"]),
  ("context", "The reviewer on this request is the station's grounds keeper.", ["grounds keeper"]),
  ("next_step", "Refer the entry request on with the gas readings.", ["gas readings"]))


def build():
    stream = NameStream()
    stream.skip_through("structured_extraction")
    assert len(S) == len(SLOTS) == 100
    body = TEMPLATE[len("{SUBJECT}"):]
    fixtures, gold, design = [], [], []
    first_ordinal = stream.position + 1
    for index, (slot, (topic, title, obs)) in enumerate(zip(SLOTS, S), 1):
        fid, family = slot["fixture_id"], slot["family"]
        large = slot["features"]["obs_band"] == "large"
        names = stream.take(5 if large else 3)                    # draw count unchanged from the prior revision
        ordinal = stream.position - len(names) + 1
        ids = [f"O{index * 10 + k}" for k in range(1, len(obs) + 1)]
        observations = [{"id": oid, "role": role, "text": text} for oid, (role, text, _) in zip(ids, obs)]
        role_counts = Counter(role for role, _, _ in obs)
        statements, consumed = [], set()
        for number, row in enumerate(observations, 1):
            if row["id"] in consumed:
                continue
            group = [r for r in observations if r["role"] == row["role"]]
            consumed.update(r["id"] for r in group)
            statements.append({"statement_id": f"S{index * 10 + number}", "role": row["role"],
                               "observation_ids": [r["id"] for r in group],
                               "text": " ".join(r["text"] for r in group)})
        conclusion, allowed = CONCLUSIONS[family]
        opening = f"Synthesize the {topic}"
        prompt = TEMPLATE.replace("{SUBJECT}", opening)
        assert prompt == opening + body
        fixtures.append({
            "consequence_risk": slot["risk"], "fixture_id": fid,
            "input": {"allowed_conclusions": allowed, "conclusion_rule": RULES[family], "observations": observations},
            "prompt": prompt, "task_class": "hierarchical_semantic_synthesis", "title": title,
            "validator_profile": "synthesis.v1"})
        expected = {"conclusion": conclusion,
                    "required_terms": {oid: terms for oid, (_, _, terms) in zip(ids, obs)},
                    "roles": {row["id"]: row["role"] for row in observations}}
        gold.append({"expected": expected, "fixture_id": fid, "rationale": RATIONALE[family],
                     "reference_output": {"conclusion": conclusion, "statements": statements}})
        design.append({"fixture_id": fid, "phase": slot["phase"], "role": slot["role"], "risk": slot["risk"],
                       "family": family, "features": slot["features"], "invented_names": [], "identifiers": [],
                       "unused_stream_draws": names,     # drawn only to keep the stream aligned; not in any text
                       "global_name_ordinals": [ordinal, ordinal + len(names) - 1],
                       "merged_role": [r for r, n in role_counts.items() if n == 2]})
    return {
        "schema_version": "g-route4.authoring-staging.v2", "task_class": "hierarchical_semantic_synthesis",
        "blueprint_commit": "1156d06", "status": "authored, not sealed, not adjudicated",
        "name_stream": stream.provenance(),
        "name_sequence": {"first_synthesis_ordinal": first_ordinal, "last_synthesis_ordinal": stream.position},
        "missing_slots": sorted({s["fixture_id"] for s in SLOTS} - {f["fixture_id"] for f in fixtures}),
        "fixtures": fixtures, "gold": gold, "design": design,
    }


if __name__ == "__main__":
    output = build()
    path = HERE / "staging/synthesis.json"
    path.write_text(json.dumps(output, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(output['fixtures'])} fixtures written; missing slots: {output['missing_slots']}")
    print("name sequence", output["name_sequence"])

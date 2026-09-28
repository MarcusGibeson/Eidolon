"""G-ROUTE4 Structured Extraction authoring (A′ main, B′ main, and all extraction reserves).

Authored to the FROZEN blueprint (experiments/G-ROUTE4-candidate/blueprint, commit 1156d06); nothing here changes a
rule. Each spec gives the fixture's scenario; derived gold values are computed with exact decimal and calendar
arithmetic, never typed by hand. Invented names come from the frozen syllable bank (names.py) and are written as
placeholders @0..@5 in the spec.

Prompt assembly (blueprint §6, `opening_constraints`):
    opening = subject sentence, then the derived-field definitions ("<key> is ..."), then the absence sentence where a
              field is typed provided|not_provided; sentences joined by ". ", the last without a terminal period;
    prompt  = the frozen assembled template with {SUBJECT} replaced by the opening.

No model or adjudicator is contacted. Writes staging/extraction.json; the seal is a separate, later step.

    python -B author_extraction.py
"""

import datetime as dt
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
from english_vocabulary import english_vocabulary  # noqa: E402
from names import NameBank  # noqa: E402

BLUEPRINT = json.loads((ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
EXTR = BLUEPRINT["templates"]["structured_extraction"]
TEMPLATE = EXTR["assembled_template"]
ABSENCE = EXTR["absence_sentence"]
SLOTS = {s["fixture_id"]: s for s in BLUEPRINT["slots"] if s["task_class"] == "structured_extraction"}
IDENT = re.compile(r"([A-Z]{1,5}-?\d[\w.-]*)")        # G-ROUTE3's identifier pattern (g_route3_independence)


# ---------------------------------------------------------------- exact arithmetic helpers
def _num(d: Decimal):
    return int(d) if d == d.to_integral_value() else float(str(d.normalize()))


def dsum(*xs):
    return _num(sum((Decimal(str(x)) for x in xs), Decimal(0)))


def dmul(*xs):
    p = Decimal(1)
    for x in xs:
        p *= Decimal(str(x))
    return _num(p)


def dsub(a, b):
    return _num(Decimal(str(a)) - Decimal(str(b)))


def ddiv(a, b):
    return _num(Decimal(str(a)) / Decimal(str(b)))


def add_days(day: str, n: int) -> str:
    return (dt.date.fromisoformat(day) + dt.timedelta(days=n)).isoformat()


def days_between(a: str, b: str) -> int:
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def add_min(clock: str, minutes: int) -> str:
    h, m = map(int, clock.split(":"))
    t = (h * 60 + m + minutes) % 1440
    return f"{t // 60:02d}:{t % 60:02d}"


SPECS = []


def X(fid, title, subject, defs, schema, text, expected, rationale, absence=False):
    SPECS.append(dict(fid=fid, title=title, subject=subject, defs=defs, schema=schema, text=text,
                      expected=expected, rationale=rationale, absence=absence))


# ================================================================ A′ main
X("A4-EXTR-R1-01", "Model railway run log", "Extract the locomotive run log",
  ["laps_total is the laps run in the morning session plus the laps in the afternoon session",
   "service_due is true when the laps run that day reach 20 or more"],
  {"loco_number": "string", "laps_total": "integer", "service_due": "boolean", "power": "steam|diesel"},
  "Club log for locomotive LN-6042, owned by @0 @1: 8 laps in the morning session and 13 in the afternoon "
  "session. It is a diesel model.",
  {"loco_number": "LN-6042", "laps_total": 8 + 13, "service_due": 8 + 13 >= 20, "power": "diesel"},
  "8 + 13 = {laps_total} laps, which reaches 20.")

X("A4-EXTR-R1-02", "Pepper seed sowing", "Extract the sowing record",
  ["expected_sprout is the sowing date plus the germination time"],
  {"variety": "string", "seeds_sown": "integer", "tray_litres": "number", "lid_on": "boolean",
   "expected_sprout": "YYYY-MM-DD"},
  "Sowed 24 pepper seeds of the variety @0 on 2031-03-09 in the heated propagator. The packet gives a germination "
  "time of 11 days. The tray holds 1.5 litres of compost, and the propagator lid stays on until the first shoots "
  "appear.",
  {"variety": "@0", "seeds_sown": 24, "tray_litres": 1.5, "lid_on": True,
   "expected_sprout": add_days("2031-03-09", 11)},
  "2031-03-09 plus 11 days is {expected_sprout}.")

X("A4-EXTR-R1-03", "School fair bake stall", "Extract the bake stall takings",
  ["items_sold is the total number of lemon bars and brownies sold",
   "takings is the money taken from both products together"],
  {"venue": "string", "items_sold": "integer", "takings": "number"},
  "The bake stall at the school fair in @0 sold 18 lemon bars at 2.4 each and 12 brownies at 3.25 each.",
  {"venue": "@0", "items_sold": 18 + 12, "takings": dsum(dmul(18, "2.4"), dmul(12, "3.25"))},
  "18 + 12 = {items_sold} items; 18 x 2.4 + 12 x 3.25 = {takings}.")

X("A4-EXTR-R1-04", "Aquarium water test", "Extract the aquarium test result",
  ["needs_change is true when the nitrate reading is above 40 ppm"],
  {"tested_on": "YYYY-MM-DD", "nitrate_ppm": "integer", "filter_action": "rinsed|replaced",
   "needs_change": "boolean"},
  "Tank test on 2029-11-14 showed nitrate at 35 ppm. The filter sponge was rinsed in tank water, not replaced.",
  {"tested_on": "2029-11-14", "nitrate_ppm": 35, "filter_action": "rinsed", "needs_change": 35 > 40},
  "35 ppm is not above 40 ppm, so no water change is needed; the sponge was rinsed.")

X("A4-EXTR-R2-01", "Hotel stay booking", "Extract the hotel booking",
  ["room_total is the nightly rate times the number of nights"],
  {"check_in": "YYYY-MM-DD", "nights": "integer", "room_total": "number", "breakfast": "boolean",
   "confirmation": "provided|not_provided"},
  "Booked 3 nights from 2033-05-21 at a nightly rate of 142.5. Breakfast is included in the rate. The confirmation "
  "number has not been provided yet.",
  {"check_in": "2033-05-21", "nights": 3, "room_total": dmul(3, "142.5"), "breakfast": True,
   "confirmation": "not_provided"},
  "3 x 142.5 = {room_total}; the confirmation number is stated as not provided.", absence=True)

X("A4-EXTR-R2-02", "Supplier onboarding check", "Extract the supplier onboarding outcome",
  ["late_forms is true when the forms came back more than 10 days after they were requested",
   "onboarding is activate when the tax form and the bank letter are both on file, suspend when neither is on file, "
   "and chase otherwise"],
  {"supplier": "string", "late_forms": "boolean", "onboarding": "activate|chase|suspend"},
  "Supplier @0 returned its forms 14 days after we requested them. The tax form is on file, but the bank letter is "
  "missing.",
  {"supplier": "@0", "late_forms": 14 > 10, "onboarding": "chase"},
  "14 days is more than 10; only the tax form is on file, so the outcome is chase.")

X("A4-EXTR-R2-03", "Copier paper purchase order", "Extract the purchase order lines",
  ["paper_cost is the number of cartons times the price per carton"],
  {"po_number": "string", "cartons": "integer", "toner_count": "integer", "paper_cost": "number"},
  "Purchase order PO-66190 to the supplier @0 covers 40 cartons of copier paper at 23.75 per carton and 6 toner "
  "cartridges.",
  {"po_number": "PO-66190", "cartons": 40, "toner_count": 6, "paper_cost": dmul(40, "23.75")},
  "40 x 23.75 = {paper_cost}.")

X("A4-EXTR-R2-04", "Car rental agreement", "Extract the rental terms",
  ["due_back is the pickup date plus the rental days", "rental_cost is the daily rate times the rental days"],
  {"rental_days": "integer", "due_back": "YYYY-MM-DD", "rental_cost": "number", "insured": "boolean",
   "fuel_policy": "full|prepaid"},
  "The car was picked up on 2036-08-02 for 6 rental days at a daily rate of 38.9. The customer declined the "
  "insurance. Fuel policy: return it full.",
  {"rental_days": 6, "due_back": add_days("2036-08-02", 6), "rental_cost": dmul(6, "38.9"), "insured": False,
   "fuel_policy": "full"},
  "2036-08-02 plus 6 days is {due_back}; 6 x 38.9 = {rental_cost}.")

X("A4-EXTR-R3-01", "Log archive quota", "Extract the log archive figures",
  ["quarter_gb is the total archived size across the three months",
   "within_quota is true when that total is at most the retention quota"],
  {"cluster": "string", "quarter_gb": "number", "within_quota": "boolean"},
  "Log archive for cluster @0: January 12.5 GB, February 9.25 GB, March 14 GB. The retention quota is 40 GB.",
  {"cluster": "@0", "quarter_gb": dsum("12.5", "9.25", 14), "within_quota": Decimal("35.75") <= 40},
  "12.5 + 9.25 + 14 = {quarter_gb} GB, within the 40 GB quota.")

X("A4-EXTR-R3-02", "Lost laptop report", "Extract the lost device report",
  ["wipe_late is true when the remote wipe was sent more than 24 hours after the loss was reported"],
  {"reported_on": "YYYY-MM-DD", "hours_to_wipe": "integer", "disk": "encrypted|plain", "wipe_late": "boolean"},
  "A staff laptop was reported lost on 2030-02-17. The remote wipe command went out 31 hours after the report. Its "
  "disk was encrypted.",
  {"reported_on": "2030-02-17", "hours_to_wipe": 31, "disk": "encrypted", "wipe_late": 31 > 24},
  "31 hours is more than 24, so the wipe was late.")

X("A4-EXTR-R3-03", "Data access request", "Extract the access request status",
  ["days_remaining is the response deadline in days minus the days already elapsed",
   "urgent is true when fewer than 20 days remain before the deadline"],
  {"requester": "string", "attachments": "integer", "days_remaining": "integer", "urgent": "boolean",
   "account_ref": "provided|not_provided"},
  "A subject access request arrived from @0 @1 with 3 attachments. We must respond within 30 days, and 12 days "
  "have elapsed. The account reference has not been provided.",
  {"requester": "@0 @1", "attachments": 3, "days_remaining": 30 - 12, "urgent": 30 - 12 < 20,
   "account_ref": "not_provided"},
  "30 - 12 = {days_remaining} days remain, fewer than 20; the account reference is stated as not provided.",
  absence=True)

X("A4-EXTR-R3-04", "Contractor badge request", "Extract the badge request decision",
  ["access_decision is grant when the manager signed and the induction is done, deny when the manager has not "
   "signed, and pending otherwise"],
  {"contractor": "string", "requested_days": "integer", "access_decision": "grant|pending|deny"},
  "Badge request for contractor @0 @1 to enter server room 3 for 45 days. Their manager signed the form, but the "
  "safety induction is not done yet.",
  {"contractor": "@0 @1", "requested_days": 45, "access_decision": "pending"},
  "The manager signed but the induction is not done, so the decision is pending.")

X("A4-EXTR-R4-01", "Crane lift plan", "Extract the lift plan",
  ["total_load_kg is the combined weight of all the beams"],
  {"plan_id": "string", "beam_count": "integer", "total_load_kg": "integer", "zone_marked": "boolean"},
  "Lift plan LP-7054 covers 3 steel beams weighing 820 kg each, lifted by the mobile crane. The rated capacity at "
  "this radius is 2600 kg. An exclusion zone has been marked around the lift area.",
  {"plan_id": "LP-7054", "beam_count": 3, "total_load_kg": 3 * 820, "zone_marked": True},
  "3 x 820 = {total_load_kg} kg.")

X("A4-EXTR-R4-02", "Solvent drum store inspection", "Extract the drum store inspection",
  ["stored_litres is the total volume held in the drums",
   "exceeds_limit is true when that total is above the store limit"],
  {"inspected_on": "YYYY-MM-DD", "drums": "integer", "stored_litres": "number", "exceeds_limit": "boolean",
   "bund": "steel|concrete"},
  "Drum store inspection on 2034-10-03: 4 drums of solvent holding 55.5, 60, 48.25 and 52 litres. The store limit "
  "is 200 litres. The spill bund is steel.",
  {"inspected_on": "2034-10-03", "drums": 4, "stored_litres": dsum("55.5", 60, "48.25", 52),
   "exceeds_limit": dsum("55.5", 60, "48.25", 52) > 200, "bund": "steel"},
  "55.5 + 60 + 48.25 + 52 = {stored_litres} litres, above the 200 litre limit.")

X("A4-EXTR-R4-03", "Personnel file retention", "Extract the retention record",
  ["keep_until_year is the archiving year plus the retention period in years"],
  {"source_site": "string", "keep_until_year": "integer", "certificate": "provided|not_provided"},
  "Box 14 of personnel files from site @0 was archived in 2029. These files must be kept for 7 years after "
  "archiving. The destruction certificate number has not been provided.",
  {"source_site": "@0", "keep_until_year": 2029 + 7, "certificate": "not_provided"},
  "2029 + 7 = {keep_until_year}; the certificate number is stated as not provided.", absence=True)

X("A4-EXTR-R4-04", "Air receiver inspection", "Extract the air receiver inspection",
  ["margin_bar is the test pressure minus the working pressure",
   "next_due is the last inspection date plus the inspection interval"],
  {"test_bar": "number", "margin_bar": "number", "next_due": "YYYY-MM-DD", "relief_valve": "boolean"},
  "The air receiver was tested at 11.5 bar at its last inspection on 2032-04-26. Its working pressure is 8 bar, and "
  "the inspection interval is 400 days. A relief valve is fitted.",
  {"test_bar": 11.5, "margin_bar": dsub("11.5", 8), "next_due": add_days("2032-04-26", 400), "relief_valve": True},
  "11.5 - 8 = {margin_bar} bar; 2032-04-26 plus 400 days is {next_due}.")

# ================================================================ B′ main, R1
X("B4-EXTR-R1-01", "Kiln glaze firing", "Extract the glaze firing note",
  ["pieces is the total number of mugs and bowls fired"],
  {"glaze": "string", "pieces": "integer", "same_day_pickup": "boolean"},
  "Glaze firing for member @0: 7 mugs and 5 bowls went into the kiln with the glaze called river moss. Pieces "
  "cannot be picked up on the day of firing.",
  {"glaze": "river moss", "pieces": 7 + 5, "same_day_pickup": False},
  "7 + 5 = {pieces}; pickup on firing day is ruled out.")

X("B4-EXTR-R1-02", "Reed bed sighting", "Extract the bird sighting",
  ["pair_seen is true when two or more birds were seen together",
   "record_type is photo when photos were taken and note otherwise"],
  {"observer": "string", "pair_seen": "boolean", "record_type": "photo|note"},
  "Sighting logged by @0 @1 at the reed bed: two marsh harriers hunting together at dawn. No photos were taken.",
  {"observer": "@0 @1", "pair_seen": True, "record_type": "note"},
  "Two birds were seen together; no photos were taken, so the record is a note.")

X("B4-EXTR-R1-03", "Board game night", "Extract the game night log",
  ["total_minutes is the playing time across all games"],
  {"game": "string", "played_on": "YYYY-MM-DD", "total_minutes": "integer", "snack_bill": "number"},
  "Game night on 2038-01-15: we played @0 three times, and each game ran 50 minutes. The host paid the snack bill "
  "of 18.6.",
  {"game": "@0", "played_on": "2038-01-15", "total_minutes": 3 * 50, "snack_bill": 18.6},
  "3 games x 50 minutes = {total_minutes}.")

X("B4-EXTR-R1-04", "Cat booster reminder", "Extract the vaccination reminder",
  ["next_booster is the last booster date plus the interval the vet gave",
   "senior is true when the cat is 10 years old or older"],
  {"next_booster": "YYYY-MM-DD", "age_years": "integer", "reminder": "text|email", "senior": "boolean"},
  "@0 the cat had a booster on 2039-09-04, and the vet gave an interval of 365 days until the next one. The cat is "
  "4 years old. Send the reminder by email.",
  {"next_booster": add_days("2039-09-04", 365), "age_years": 4, "reminder": "email", "senior": False},
  "2039-09-04 plus 365 days is {next_booster} (2040 is a leap year); a 4-year-old cat is not senior.")

X("B4-EXTR-R1-05", "Ridge walk plan", "Extract the walk plan",
  ["finish_time is the start time plus the walking time",
   "average_kmh is the route distance divided by the walking time in hours"],
  {"village": "string", "finish_time": "HH:MM", "water_stops": "integer", "average_kmh": "number",
   "dogs_allowed": "boolean"},
  "Our walk starts in the village of @0 at 07:40. The route is 14.5 km with 3 water stops, and the walking time is "
  "5 hours. Dogs are allowed on the route.",
  {"village": "@0", "finish_time": add_min("07:40", 300), "water_stops": 3, "average_kmh": ddiv("14.5", 5),
   "dogs_allowed": True},
  "07:40 plus 5 hours is {finish_time}; 14.5 / 5 = {average_kmh}.")

X("B4-EXTR-R1-06", "Sourdough starter feed", "Extract the starter timing",
  ["ready_at is the feeding time plus the time the starter needs to double"],
  {"ready_at": "HH:MM", "starter_grams": "integer", "warm_kitchen": "boolean"},
  "Fed the starter at 21:15. In a warm kitchen it needs 7 hours to double, and the kitchen is warm tonight. The "
  "loaf uses 150 g of starter.",
  {"ready_at": add_min("21:15", 7 * 60), "starter_grams": 150, "warm_kitchen": True},
  "21:15 plus 7 hours is {ready_at}.")

X("B4-EXTR-R1-07", "Allotment harvest", "Extract the harvest record",
  ["harvest_kg is the combined weight of the three crops"],
  {"grower": "string", "plot": "integer", "harvest_kg": "number", "method": "hand|machine"},
  "Harvest from allotment plot 22, grown by @0 @1: courgettes 1.2 kg, beans 0.85 kg and potatoes 3.4 kg, all "
  "picked by hand.",
  {"grower": "@0 @1", "plot": 22, "harvest_kg": dsum("1.2", "0.85", "3.4"), "method": "hand"},
  "1.2 + 0.85 + 3.4 = {harvest_kg} kg.")

X("B4-EXTR-R1-08", "Weekly cycling log", "Extract the weekly ride totals",
  ["weekly_km is the distance summed over all rides",
   "goal_met is true when that distance reaches the weekly goal"],
  {"rider": "string", "rides": "integer", "weekly_km": "number", "goal_met": "boolean"},
  "Rider @0 logged 3 rides this week: Monday 32.5 km, Wednesday 18 km and Saturday 61.25 km. The weekly goal is "
  "100 km.",
  {"rider": "@0", "rides": 3, "weekly_km": dsum("32.5", 18, "61.25"), "goal_met": True},
  "32.5 + 18 + 61.25 = {weekly_km} km, which reaches 100 km.")

X("B4-EXTR-R1-09", "Craft fair pitch booking", "Extract the craft fair booking",
  ["total_fee is the table fee plus the electricity charge"],
  {"fair_town": "string", "pitch": "integer", "total_fee": "number", "payment": "card|cash", "gazebo": "boolean"},
  "Pitch 17 is booked at the craft fair in @0. The table fee is 24 and electricity adds 6.5. Paid by card; no "
  "gazebo is needed.",
  {"fair_town": "@0", "pitch": 17, "total_fee": dsum(24, "6.5"), "payment": "card", "gazebo": False},
  "24 + 6.5 = {total_fee}.")

X("B4-EXTR-R1-10", "Swimming badge test", "Extract the swim test result",
  ["distance_ok is true when the unaided swim reached at least 25 metres",
   "float_ok is true when the swimmer trod water for at least a full minute"],
  {"swimmer": "string", "tread_seconds": "integer", "group": "beginner|improver|advanced",
   "distance_ok": "boolean", "float_ok": "boolean"},
  "Swim test for @0: swam 30 metres unaided and trod water for 40 seconds. The swimmer is currently in the improver "
  "group.",
  {"swimmer": "@0", "tread_seconds": 40, "group": "improver", "distance_ok": 30 >= 25, "float_ok": 40 >= 60},
  "30 metres meets 25; 40 seconds is short of a full minute.")

X("B4-EXTR-R1-11", "Parcel locker collection", "Extract the parcel collection",
  ["collected_late is true when the parcel was collected more than 3 days after it arrived"],
  {"arrived": "YYYY-MM-DD", "collected_late": "boolean", "delivery": "locker|doorstep"},
  "The parcel was delivered to a locker on 2037-12-02 and collected on 2037-12-06.",
  {"arrived": "2037-12-02", "collected_late": days_between("2037-12-02", "2037-12-06") > 3, "delivery": "locker"},
  "Collection came " + str(days_between("2037-12-02", "2037-12-06")) + " days after arrival, more than 3.")

X("B4-EXTR-R1-12", "Choir concert places", "Extract the choir attendance",
  ["concert_place is true when the singer attended at least the required number of rehearsals",
   "seated_after is the name that comes immediately after the singer in the seating order"],
  {"singer": "string", "concert_place": "boolean", "seated_after": "string"},
  "Alto @0 attended 9 of the 12 rehearsals, and concert places need at least 10. Seating order: @1, @0, @2, @3.",
  {"singer": "@0", "concert_place": 9 >= 10, "seated_after": "@2"},
  "9 rehearsals is short of 10; @2 follows @0 in the seating order.")

X("B4-EXTR-R1-13", "Junior football registration", "Extract the registration",
  ["season_fee is the fee per term times the number of terms"],
  {"player": "string", "shirt_number": "integer", "season_fee": "integer",
   "emergency_phone": "provided|not_provided"},
  "Registration for @0 @1 in the under-10 team covers 3 terms at 16 per term. Shirt number 14 is requested. The "
  "emergency contact phone number has not been provided.",
  {"player": "@0 @1", "shirt_number": 14, "season_fee": 3 * 16, "emergency_phone": "not_provided"},
  "3 x 16 = {season_fee}; the phone number is stated as not provided.", absence=True)

X("B4-EXTR-R1-14", "Dog grooming appointment", "Extract the grooming booking",
  ["session_minutes is the grooming time plus the drying time",
   "pickup_time is the drop-off time plus the grooming and drying minutes"],
  {"pickup_time": "HH:MM", "session_minutes": "integer", "price": "integer",
   "vaccination_record": "provided|not_provided"},
  "Drop-off at 10:20 for a full groom: grooming takes 95 minutes and drying another 15. The quoted price is 42. The "
  "vaccination record has been provided.",
  {"pickup_time": add_min("10:20", 95 + 15), "session_minutes": 95 + 15, "price": 42,
   "vaccination_record": "provided"},
  "95 + 15 = {session_minutes} minutes; 10:20 plus 110 minutes is {pickup_time}; the record was provided.",
  absence=True)

X("B4-EXTR-R1-15", "Campsite pitch booking", "Extract the campsite booking",
  ["stay_cost is the nightly price times the number of nights"],
  {"arrival": "YYYY-MM-DD", "guests": "integer", "stay_cost": "number", "hookup": "boolean",
   "pitch_number": "provided|not_provided"},
  "Pitch booked for 4 people arriving 2044-07-18, staying 2 nights at 21.75 per night. An electric hook-up is "
  "included. The pitch number has not been provided.",
  {"arrival": "2044-07-18", "guests": 4, "stay_cost": dmul(2, "21.75"), "hookup": True,
   "pitch_number": "not_provided"},
  "2 x 21.75 = {stay_cost}; the pitch number is stated as not provided.", absence=True)

X("B4-EXTR-R1-16", "Book club pick", "Extract the book club vote",
  ["long_read is true when the book has more than 300 pages",
   "decision is adopt when the library has a copy and more than half the members voted for it, drop when "
   "neither holds, and revote otherwise"],
  {"proposer": "string", "book": "string", "votes": "integer", "long_read": "boolean",
   "decision": "adopt|revote|drop"},
  "@0 proposed the novel @1, which runs to 312 pages. The library has a copy, and 5 of the 8 members voted for it.",
  {"proposer": "@0", "book": "@1", "votes": 5, "long_read": 312 > 300, "decision": "adopt"},
  "312 pages is more than 300; the library has it and 5 of 8 is more than half, so the book is adopted.")

X("B4-EXTR-R1-17", "Bike repair ticket", "Extract the repair ticket",
  ["action is repair when parts are in stock and the brakes pass, refer when the brakes fail, and order otherwise"],
  {"owner": "string", "chain_worn": "boolean", "action": "repair|order|refer"},
  "Repair ticket for a bike owned by @0 @1: the chain is worn, the brakes pass inspection, and the parts are in "
  "stock.",
  {"owner": "@0 @1", "chain_worn": True, "action": "repair"},
  "Parts are in stock and the brakes pass, so the action is repair.")

X("B4-EXTR-R1-18", "Orchard picking day", "Extract the picking day plan",
  ["ends_at is the start time plus the picking duration",
   "status is go when the forecast is dry and the ladders are checked, cancel when neither holds, and delay "
   "otherwise"],
  {"ends_at": "HH:MM", "ladders_checked": "boolean", "status": "go|delay|cancel"},
  "Community orchard picking starts at 09:45 and runs for 150 minutes. The forecast is dry, and the ladders have "
  "been checked.",
  {"ends_at": add_min("09:45", 150), "ladders_checked": True, "status": "go"},
  "09:45 plus 150 minutes is {ends_at}; dry forecast and checked ladders give go.")

# ================================================================ B′ main, R2
X("B4-EXTR-R2-01", "Designer invoice", "Extract the invoice summary",
  ["invoice_total is the sum of the three task prices"],
  {"designer": "string", "invoice_total": "number", "paid": "boolean"},
  "The invoice from designer @0 @1 lists three tasks: logo 180, icon set 95.5 and banner 60. Payment has already "
  "been received.",
  {"designer": "@0 @1", "invoice_total": dsum(180, "95.5", 60), "paid": True},
  "180 + 95.5 + 60 = {invoice_total}.")

X("B4-EXTR-R2-02", "Stationery order", "Extract the stationery order",
  ["order_total is the combined cost of the pens and the binders",
   "within_budget is true when that cost does not exceed the remaining department budget"],
  {"ordered_on": "YYYY-MM-DD", "order_total": "number", "within_budget": "boolean"},
  "Stationery order placed 2046-02-11: 8 packs of pens at 4.35 per pack and 3 binders at 7.2 each. The department "
  "has 60 left in its budget.",
  {"ordered_on": "2046-02-11", "order_total": dsum(dmul(8, "4.35"), dmul(3, "7.2")),
   "within_budget": dsum(dmul(8, "4.35"), dmul(3, "7.2")) <= 60},
  "8 x 4.35 + 3 x 7.2 = {order_total}, within the 60 remaining.")

X("B4-EXTR-R2-03", "Mileage claim", "Extract the mileage claim",
  ["claimed_miles is the total of the three trips"],
  {"claimant": "string", "claimed_miles": "number", "vehicle": "own|pool", "receipts": "boolean"},
  "Mileage claim by @0 @1 for trips of 42, 17.5 and 63 miles, driven in their own car. Parking receipts are "
  "attached.",
  {"claimant": "@0 @1", "claimed_miles": dsum(42, "17.5", 63), "vehicle": "own", "receipts": True},
  "42 + 17.5 + 63 = {claimed_miles} miles.")

X("B4-EXTR-R2-04", "Overtime timesheet", "Extract the timesheet check",
  ["overtime_hours is the hours worked beyond the contract hours",
   "over_cap is true when the hours worked exceed the weekly cap"],
  {"employee": "string", "overtime_hours": "integer", "over_cap": "boolean", "approval": "approved|pending"},
  "Timesheet for @0 @1: 46 hours worked this week against a 40 hour contract. The weekly cap is 45 hours. Manager "
  "approval is pending.",
  {"employee": "@0 @1", "overtime_hours": 46 - 40, "over_cap": 46 > 45, "approval": "pending"},
  "46 - 40 = {overtime_hours} overtime hours; 46 exceeds the 45 hour cap.")

X("B4-EXTR-R2-05", "Meeting room booking", "Extract the room booking",
  ["overbooked is true when the attendees exceed the room capacity"],
  {"booked_by": "string", "meeting_date": "YYYY-MM-DD", "attendees": "integer", "capacity": "integer",
   "overbooked": "boolean"},
  "Room booking by @0 @1 for 2047-03-19: 14 attendees are expected, and the room seats 12.",
  {"booked_by": "@0 @1", "meeting_date": "2047-03-19", "attendees": 14, "capacity": 12, "overbooked": 14 > 12},
  "14 attendees exceed the capacity of 12.")

X("B4-EXTR-R2-06", "Software plan renewal", "Extract the plan renewal",
  ["renews_on is the start date plus 365 days",
   "needs_upgrade is true when the current seats plus the new hires exceed the allowed seats"],
  {"renews_on": "YYYY-MM-DD", "seats": "integer", "new_hires": "integer", "needs_upgrade": "boolean",
   "billing": "monthly|yearly"},
  "The software plan started on 2040-11-08 with 25 seats in use, billed yearly. The plan allows up to 30 seats. 4 "
  "new hires join next month.",
  {"renews_on": add_days("2040-11-08", 365), "seats": 25, "new_hires": 4, "needs_upgrade": 25 + 4 > 30,
   "billing": "yearly"},
  "2040-11-08 plus 365 days is {renews_on}; 25 + 4 = 29 does not exceed 30.")

X("B4-EXTR-R2-07", "Team lunch catering", "Extract the catering order",
  ["wraps is the number of platters times the wraps per platter"],
  {"team": "string", "wraps": "integer", "dietary_notes": "provided|not_provided"},
  "Catering for team @0: 3 platters with 12 wraps on each. Dietary notes have been provided by the team lead.",
  {"team": "@0", "wraps": 3 * 12, "dietary_notes": "provided"},
  "3 x 12 = {wraps}; the dietary notes were provided.", absence=True)

X("B4-EXTR-R2-08", "Jacket refund request", "Extract the refund check",
  ["purchase_branch is the branch where the jacket was bought, not the one where it was returned",
   "refundable is true when the jacket is unworn and came back within 30 days of purchase"],
  {"purchase_branch": "string", "refundable": "boolean", "order_number": "provided|not_provided"},
  "Refund request for a jacket bought at branch @0 and returned 12 days later at branch @1. The jacket is unworn. "
  "The order number has not been provided.",
  {"purchase_branch": "@0", "refundable": True, "order_number": "not_provided"},
  "It was bought at @0; unworn and returned after 12 days, so it is refundable; the order number is not provided.",
  absence=True)

X("B4-EXTR-R2-09", "Furniture delivery", "Extract the delivery booking",
  ["assembly_fee is the per-item assembly charge times the number of items"],
  {"delivery_date": "YYYY-MM-DD", "assembly_fee": "integer", "wants_assembly": "boolean",
   "slot_time": "provided|not_provided"},
  "Delivery of 2 items is scheduled for 2048-05-27, and assembly is requested at 35 per item. The delivery slot "
  "time has not been provided.",
  {"delivery_date": "2048-05-27", "assembly_fee": 2 * 35, "wants_assembly": True, "slot_time": "not_provided"},
  "2 x 35 = {assembly_fee}; the slot time is stated as not provided.", absence=True)

X("B4-EXTR-R2-10", "Vendor invoice approval", "Extract the invoice approval",
  ["invoice_total is the units times the unit price",
   "decision is pay when the purchase order matches and the total is at most 5000, reject when the purchase order "
   "does not match, and hold otherwise"],
  {"invoice_ref": "string", "units": "integer", "invoice_total": "integer", "decision": "pay|hold|reject"},
  "Invoice INV-40952 from vendor @0 bills 4 units at 1180 each. The purchase order matches the invoice.",
  {"invoice_ref": "INV-40952", "units": 4, "invoice_total": 4 * 1180, "decision": "pay"},
  "4 x 1180 = {invoice_total}, at most 5000, and the purchase order matches, so pay.")

X("B4-EXTR-R2-11", "Travel request", "Extract the travel request status",
  ["status is approved when the line manager approved and the agency booked the flights, rejected when neither "
   "holds, and review otherwise"],
  {"depart": "YYYY-MM-DD", "nights": "integer", "agency_booked": "boolean", "manager_ok": "boolean",
   "status": "approved|review|rejected"},
  "Travel request: depart 2049-01-12 for 3 nights. The flights were booked through the agency, but the line "
  "manager has not approved the trip.",
  {"depart": "2049-01-12", "nights": 3, "agency_booked": True, "manager_ok": False, "status": "review"},
  "Only one of the two conditions holds, so the status is review.")

X("B4-EXTR-R2-12", "Monitor equipment request", "Extract the equipment request",
  ["request_cost is the number of monitors times the price per monitor",
   "outcome is fulfil when the cost fits the team budget left and asset tags are available, decline when neither "
   "holds, and defer otherwise"],
  {"requester": "string", "monitors": "integer", "request_cost": "integer", "tags_available": "boolean",
   "outcome": "fulfil|defer|decline"},
  "Equipment request from @0 @1: 3 monitors at 210 each. The team has 700 of budget left, and asset tags are "
  "available.",
  {"requester": "@0 @1", "monitors": 3, "request_cost": 3 * 210, "tags_available": True, "outcome": "fulfil"},
  "3 x 210 = {request_cost}, which fits 700, and tags are available, so fulfil.")

X("B4-EXTR-R2-13", "Freight consignment", "Extract the consignment details",
  ["gross_kg is the carton weight times the number of cartons"],
  {"consignment": "string", "cartons": "integer", "gross_kg": "number"},
  "Consignment TN-58817 contains 3 cartons, each weighing 2.35 kg.",
  {"consignment": "TN-58817", "cartons": 3, "gross_kg": dmul(3, "2.35")},
  "3 x 2.35 = {gross_kg} kg.")

X("B4-EXTR-R2-14", "New starter probation", "Extract the probation terms",
  ["probation_end is the start date plus the probation period",
   "long_probation is true when the probation period is longer than 60 days"],
  {"staff_number": "string", "probation_end": "YYYY-MM-DD", "long_probation": "boolean"},
  "New starter @0 @1 (staff number SN-44718) begins on 2027-08-16 with a probation period of 90 days.",
  {"staff_number": "SN-44718", "probation_end": add_days("2027-08-16", 90), "long_probation": 90 > 60},
  "2027-08-16 plus 90 days is {probation_end}; 90 days is longer than 60.")

X("B4-EXTR-R2-15", "Rent standing order", "Extract the standing order",
  ["large_payment is true when the monthly amount is above 900",
   "annual_band is above_10k when twelve monthly payments total more than 10000, and below_10k otherwise"],
  {"payee": "string", "payment_ref": "string", "large_payment": "boolean", "annual_band": "above_10k|below_10k"},
  "Standing order to landlord @0 @1 for 925 each month, with payment reference KV-3390.",
  {"payee": "@0 @1", "payment_ref": "KV-3390", "large_payment": 925 > 900,
   "annual_band": "above_10k" if 12 * 925 > 10000 else "below_10k"},
  "925 is above 900; 12 x 925 = " + str(12 * 925) + ", more than 10000.")

X("B4-EXTR-R2-16", "Consulting invoice terms", "Extract the invoice terms",
  ["due_date is the invoice date plus the payment terms"],
  {"due_date": "YYYY-MM-DD", "hours": "integer", "site_visits": "integer", "hourly_rate": "number",
   "late_fees": "boolean"},
  "Invoice dated 2028-10-05 with payment terms of 45 days covers 12 hours of consulting at 87.5 per hour and 2 site "
  "visits. Late fees apply to overdue payments.",
  {"due_date": add_days("2028-10-05", 45), "hours": 12, "site_visits": 2, "hourly_rate": 87.5, "late_fees": True},
  "2028-10-05 plus 45 days is {due_date}.")

X("B4-EXTR-R2-17", "Warehouse shift", "Extract the shift times",
  ["shift_end is the start time plus the shift length"],
  {"shift_end": "HH:MM", "breaks": "integer", "shift_type": "early|late"},
  "The early warehouse shift starts at 06:30 and lasts 9 hours, with 2 breaks.",
  {"shift_end": add_min("06:30", 9 * 60), "breaks": 2, "shift_type": "early"},
  "06:30 plus 9 hours is {shift_end}.")

X("B4-EXTR-R2-18", "Parking permit", "Extract the parking permit",
  ["expires is the purchase date plus the validity period",
   "bay_count is how many bays the permit covers, counting both ends of the range"],
  {"expires": "YYYY-MM-DD", "bay_count": "integer", "overnight": "boolean"},
  "Monthly parking permit bought on 2029-12-20, valid for 30 days, covering bays 12 to 19. Overnight parking is "
  "allowed.",
  {"expires": add_days("2029-12-20", 30), "bay_count": 19 - 12 + 1, "overnight": True},
  "2029-12-20 plus 30 days is {expires}; bays 12 to 19 inclusive are {bay_count}.")

# ================================================================ B′ main, R3
X("B4-EXTR-R3-01", "Staff portal certificate", "Extract the certificate details",
  ["expires_on is the issue date plus the validity period"],
  {"expires_on": "YYYY-MM-DD", "auto_renew": "boolean", "ca_contact": "provided|not_provided"},
  "The TLS certificate for the staff portal was issued on 2031-09-14 with a validity period of 398 days. "
  "Auto-renewal is enabled. A contact at the issuing authority has not been provided.",
  {"expires_on": add_days("2031-09-14", 398), "auto_renew": True, "ca_contact": "not_provided"},
  "2031-09-14 plus 398 days is {expires_on}; the contact is stated as not provided.", absence=True)

X("B4-EXTR-R3-02", "MFA enrollment", "Extract the enrollment status",
  ["approver is the administrator who approved the enrollment, not the one who only reviewed it",
   "fully_enrolled is true when every required factor has been enrolled"],
  {"approver": "string", "fully_enrolled": "boolean", "recovery_phone": "provided|not_provided"},
  "User @0 @1 has enrolled 1 of the 2 required sign-in factors. Administrator @2 approved the enrollment, and @3 "
  "only reviewed it. The recovery phone number has been provided.",
  {"approver": "@2", "fully_enrolled": False, "recovery_phone": "provided"},
  "@2 approved; 1 of 2 factors is not every factor; the phone number was provided.", absence=True)

X("B4-EXTR-R3-03", "Mailbox deletion request", "Extract the deletion request",
  ["data_stores is the number of mailboxes plus the number of shared drives"],
  {"request_id": "string", "mailboxes": "integer", "data_stores": "integer",
   "legal_hold": "provided|not_provided"},
  "Deletion request DR-1187 covers 5 mailboxes and 2 shared drives. The legal hold status has not been provided.",
  {"request_id": "DR-1187", "mailboxes": 5, "data_stores": 5 + 2, "legal_hold": "not_provided"},
  "5 + 2 = {data_stores}; the legal hold status is stated as not provided.", absence=True)

X("B4-EXTR-R3-04", "Payroll access review", "Extract the access review outcome",
  ["clean is true when no reviewed account is unowned",
   "result is pass when there are no unowned accounts and all terminated staff accounts are disabled, fail when "
   "neither holds, and remediate otherwise"],
  {"reviewed_on": "YYYY-MM-DD", "accounts": "integer", "clean": "boolean", "result": "pass|remediate|fail"},
  "The payroll system access review was completed on 2032-01-09. 23 accounts were reviewed, and 3 of them are still "
  "unowned. All terminated staff accounts are disabled.",
  {"reviewed_on": "2032-01-09", "accounts": 23, "clean": False, "result": "remediate"},
  "3 accounts are unowned, so not clean; terminated accounts are disabled, so one condition holds: remediate.")

X("B4-EXTR-R3-05", "Firewall change request", "Extract the firewall change decision",
  ["verdict is implement when sign-off is received and the risk score is below 8, reject when sign-off is missing, "
   "and escalate otherwise"],
  {"change_id": "string", "ports": "integer", "risk_score": "integer", "signed_off": "boolean",
   "verdict": "implement|escalate|reject"},
  "Change request FW-60231 opens 2 ports for the vendor @0. The risk score is 7 out of 10, and security sign-off "
  "has been received.",
  {"change_id": "FW-60231", "ports": 2, "risk_score": 7, "signed_off": True, "verdict": "implement"},
  "Sign-off received and 7 is below 8, so implement.")

X("B4-EXTR-R3-06", "Vendor security questionnaire", "Extract the questionnaire rating",
  ["followup_by is the return date plus 30 days",
   "rating is approved when the score is at least 70 and no critical findings are open, rejected when the score is "
   "below 50, and conditional otherwise"],
  {"followup_by": "YYYY-MM-DD", "vendor_score": "number", "critical_open": "integer", "in_region": "boolean",
   "rating": "approved|conditional|rejected"},
  "The vendor returned its security questionnaire on 2033-06-06 with a score of 71.5 out of 100. 2 critical "
  "findings remain open. Data will be stored in-region.",
  {"followup_by": add_days("2033-06-06", 30), "vendor_score": 71.5, "critical_open": 2, "in_region": True,
   "rating": "conditional"},
  "2033-06-06 plus 30 days is {followup_by}; 71.5 is at least 70 but critical findings are open, and it is not "
  "below 50: conditional.")

X("B4-EXTR-R3-07", "Laptop compliance audit", "Extract the laptop audit",
  ["excess_admins is the local admin accounts found beyond the number the policy allows"],
  {"asset_tag": "string", "encrypted": "boolean", "excess_admins": "integer"},
  "Laptop LT-50828, assigned to @0 @1, has disk encryption turned on. The audit found 3 local admin accounts; "
  "policy allows 1.",
  {"asset_tag": "LT-50828", "encrypted": True, "excess_admins": 3 - 1},
  "3 found minus 1 allowed = {excess_admins}.")

X("B4-EXTR-R3-08", "Visitor badge", "Extract the visitor badge details",
  ["badge_expires is the sign-in time plus the badge validity",
   "after_hours is true when the badge stays valid later than 17:00"],
  {"visitor": "string", "badge_expires": "HH:MM", "after_hours": "boolean"},
  "Visitor @0 @1 signed in at 13:05 and was issued a badge valid for 4 hours. An escort is required at all times.",
  {"visitor": "@0 @1", "badge_expires": add_min("13:05", 240), "after_hours": add_min("13:05", 240) > "17:00"},
  "13:05 plus 4 hours is {badge_expires}, later than 17:00.")

X("B4-EXTR-R3-09", "Phishing email report", "Extract the phishing report",
  ["unclicked is the number of recipients who did not click the link"],
  {"reporter": "string", "unclicked": "integer", "link_blocked": "boolean", "severity": "high|low"},
  "A suspicious email was reported by @0 @1. It reached 14 staff, and 3 of them clicked the link. The link has "
  "been blocked, and the severity was set to high.",
  {"reporter": "@0 @1", "unclicked": 14 - 3, "link_blocked": True, "severity": "high"},
  "14 - 3 = {unclicked}.")

X("B4-EXTR-R3-10", "Account lockout", "Extract the lockout details",
  ["unlocks_at is the lock time plus the lockout duration",
   "attempts_over_limit is the failed sign-ins beyond the limit"],
  {"unlocks_at": "HH:MM", "failed_attempts": "integer", "attempts_over_limit": "integer",
   "unlock_mode": "automatic|manual"},
  "The account was locked at 22:47 after 5 failed sign-ins; the limit is 3. The lockout lasts 30 minutes and then "
  "clears automatically.",
  {"unlocks_at": add_min("22:47", 30), "failed_attempts": 5, "attempts_over_limit": 5 - 3,
   "unlock_mode": "automatic"},
  "22:47 plus 30 minutes is {unlocks_at}; 5 - 3 = {attempts_over_limit}.")

X("B4-EXTR-R3-11", "Backup key rotation", "Extract the backup key schedule",
  ["next_rotation is the creation date plus the rotation period"],
  {"next_rotation": "YYYY-MM-DD", "backups": "integer", "total_tb": "number", "restore_hours": "number",
   "hsm_stored": "boolean"},
  "The backup encryption key was created on 2042-03-03 and is rotated every 180 days. It protects 6 backups "
  "totalling 1.75 TB, with an average restore time of 2.5 hours. The key is stored in a hardware security module.",
  {"next_rotation": add_days("2042-03-03", 180), "backups": 6, "total_tb": 1.75, "restore_hours": 2.5,
   "hsm_stored": True},
  "2042-03-03 plus 180 days is {next_rotation}.")

X("B4-EXTR-R3-12", "Breach notification", "Extract the breach notification details",
  ["notify_by is the discovery date plus the reporting window",
   "notifiable is true when more than 500 records were affected"],
  {"notify_by": "YYYY-MM-DD", "records": "integer", "risk_score": "number", "notifiable": "boolean",
   "data_category": "standard|special"},
  "The breach was discovered on 2043-10-28 and affects 1840 customer records of standard category data. Its "
  "assessed risk score is 6.4. The regulator must be told within a reporting window of 3 days.",
  {"notify_by": add_days("2043-10-28", 3), "records": 1840, "risk_score": 6.4, "notifiable": 1840 > 500,
   "data_category": "standard"},
  "2043-10-28 plus 3 days is {notify_by}; 1840 is more than 500.")

X("B4-EXTR-R3-13", "CCTV footage storage", "Extract the footage storage figures",
  ["footage_gb is the storage used by all three cameras together"],
  {"site": "string", "footage_gb": "number", "encrypted": "boolean"},
  "At depot @0, three cameras store 120.5 GB, 98 GB and 143.25 GB of footage. The footage is encrypted at rest.",
  {"site": "@0", "footage_gb": dsum("120.5", 98, "143.25"), "encrypted": True},
  "120.5 + 98 + 143.25 = {footage_gb} GB.")

X("B4-EXTR-R3-14", "Privacy training hours", "Extract the training record",
  ["training_hours is the total time logged in the privacy module"],
  {"team": "string", "training_hours": "number", "format": "online|classroom", "certified": "boolean"},
  "Team @0 logged 2.5, 3.75 and 1.5 hours in the privacy module, taken online. Certificates have been issued.",
  {"team": "@0", "training_hours": dsum("2.5", "3.75", "1.5"), "format": "online", "certified": True},
  "2.5 + 3.75 + 1.5 = {training_hours} hours.")

X("B4-EXTR-R3-15", "Server patch window", "Extract the patch window plan",
  ["patch_minutes is the total time of all patches",
   "fits_window is true when that time is no more than the maintenance window"],
  {"host": "string", "patch_count": "integer", "patch_minutes": "number", "fits_window": "boolean"},
  "Host @0 needs 3 patches taking 12.5, 8 and 21.25 minutes. The maintenance window is 45 minutes.",
  {"host": "@0", "patch_count": 3, "patch_minutes": dsum("12.5", 8, "21.25"),
   "fits_window": dsum("12.5", 8, "21.25") <= 45},
  "12.5 + 8 + 21.25 = {patch_minutes} minutes, within 45.")

X("B4-EXTR-R3-16", "Records store badge audit", "Extract the badge audit",
  ["contractor_share_ok is true when contractors make up no more than one fifth of the badge holders"],
  {"auditor": "string", "badge_holders": "integer", "contractors": "integer", "reader_mode": "card|card_pin",
   "contractor_share_ok": "boolean"},
  "Badge audit of the records store by @0 @1: 38 badge holders, 6 of them contractors. The reader accepts a card "
  "alone, without a PIN.",
  {"auditor": "@0 @1", "badge_holders": 38, "contractors": 6, "reader_mode": "card",
   "contractor_share_ok": 6 * 5 <= 38},
  "One fifth of 38 is 7.6, and 6 contractors is no more than that.")

X("B4-EXTR-R3-17", "Background screening", "Extract the screening status",
  ["ready_by is the request date plus the maximum screening time",
   "refs_complete is true when the checked references reach the required number"],
  {"ready_by": "YYYY-MM-DD", "refs_checked": "integer", "refs_required": "integer", "screening_score": "number",
   "refs_complete": "boolean"},
  "Background screening was requested on 2044-02-02 and takes up to 21 days. 2 of the 3 required references have "
  "been checked, and the interim screening score is 88.5.",
  {"ready_by": add_days("2044-02-02", 21), "refs_checked": 2, "refs_required": 3, "screening_score": 88.5,
   "refs_complete": 2 >= 3},
  "2044-02-02 plus 21 days is {ready_by}; 2 of 3 references is incomplete.")

X("B4-EXTR-R3-18", "Shared folder audit", "Extract the folder sharing audit",
  ["external_access is true when someone outside the company can open the folder"],
  {"folder": "string", "owner": "string", "external_access": "boolean"},
  "The folder 'harvest budget drafts', owned by @0 @1, is shared with an external auditor, @2.",
  {"folder": "harvest budget drafts", "owner": "@0 @1", "external_access": True},
  "The folder is shared with an external auditor.")

X("B4-EXTR-R4-01", "Conveyor isolation", "Extract the isolation permit decision",
  ["unlocked_points is the number of isolation points not yet locked",
   "permit is issue when every isolation point is locked and the voltage test passed, refuse when the voltage test "
   "failed, and hold otherwise"],
  {"certificate": "string", "unlocked_points": "integer", "voltage_test": "boolean", "permit": "issue|hold|refuse"},
  "Isolation certificate IC-80647 for the conveyor motor: 2 of the 3 isolation points are locked. The voltage test "
  "passed.",
  {"certificate": "IC-80647", "unlocked_points": 3 - 2, "voltage_test": True, "permit": "hold"},
  "3 - 2 = {unlocked_points} point unlocked; the test passed but not every point is locked: hold.")

# ================================================================ A′ reserves (mirror their A′ slots)
X("A4-EXTR-R1-X01", "Violin practice log", "Extract the practice summary",
  ["week_minutes is the practice time summed across the days",
   "target_met is true when that time reaches the teacher's weekly target"],
  {"piece_code": "string", "week_minutes": "integer", "target_met": "boolean", "lesson_mode": "online|studio"},
  "Student @0 practised exam piece VP-3316 on 5 days this week, 25 minutes each day. The teacher's weekly target is "
  "120 minutes, and lessons are online this term.",
  {"piece_code": "VP-3316", "week_minutes": 5 * 25, "target_met": 5 * 25 >= 120, "lesson_mode": "online"},
  "5 x 25 = {week_minutes} minutes, which reaches 120.")

X("A4-EXTR-R1-X02", "Scarf knitting project", "Extract the knitting project",
  ["finish_target is the start date plus the planned days"],
  {"pattern": "string", "balls": "integer", "metres_per_ball": "number", "washable": "boolean",
   "finish_target": "YYYY-MM-DD"},
  "Started the scarf pattern @0 on 2046-09-22 with 40 planned days to finish. It uses 6 balls of washable yarn, "
  "each 50.5 metres long.",
  {"pattern": "@0", "balls": 6, "metres_per_ball": 50.5, "washable": True,
   "finish_target": add_days("2046-09-22", 40)},
  "2046-09-22 plus 40 days is {finish_target}.")

X("A4-EXTR-R1-X03", "Plum jam batch", "Extract the jam batch totals",
  ["jar_total is the number of small and large jars together",
   "jam_kg is the combined weight in all the jars"],
  {"tree_owner": "string", "jar_total": "integer", "jam_kg": "number"},
  "Jam from the plum tree belonging to @0 filled 6 small jars of 0.225 kg and 3 large jars of 0.45 kg.",
  {"tree_owner": "@0", "jar_total": 6 + 3, "jam_kg": dsum(dmul(6, "0.225"), dmul(3, "0.45"))},
  "6 + 3 = {jar_total} jars; 6 x 0.225 + 3 x 0.45 = {jam_kg} kg.")

X("A4-EXTR-R1-X04", "Garden pond check", "Extract the pond check",
  ["treat_pond is true when the pH reading is above 8"],
  {"checked_on": "YYYY-MM-DD", "ph": "integer", "pump": "on|off", "treat_pond": "boolean"},
  "Pond water checked on 2048-08-09 gave a pH reading of 9. The pump was running during the check.",
  {"checked_on": "2048-08-09", "ph": 9, "pump": "on", "treat_pond": 9 > 8},
  "A pH of 9 is above 8.")

X("A4-EXTR-R2-X01", "Flight booking", "Extract the flight booking",
  ["fare_total is the fare per passenger times the number of passengers"],
  {"travel_date": "YYYY-MM-DD", "passengers": "integer", "fare_total": "number", "seats_reserved": "boolean",
   "booking_ref": "provided|not_provided"},
  "Flights booked for 2 passengers on 2041-04-07 at a fare of 189.95 each. Seats have been reserved. The booking "
  "reference has been provided in a separate message.",
  {"travel_date": "2041-04-07", "passengers": 2, "fare_total": dmul(2, "189.95"), "seats_reserved": True,
   "booking_ref": "provided"},
  "2 x 189.95 = {fare_total}; the booking reference was provided.", absence=True)

X("A4-EXTR-R2-X02", "Standing desk purchase", "Extract the purchase approval step",
  ["quote_stale is true when the quote is more than 30 days old",
   "next_step is order when the budget holder approved and the quote is current, cancel when the budget holder "
   "refused, and requote otherwise"],
  {"requester": "string", "quote_stale": "boolean", "next_step": "order|requote|cancel"},
  "@0 @1 asked to buy a standing desk for 480. The budget holder approved the purchase, but the quote is 41 days "
  "old.",
  {"requester": "@0 @1", "quote_stale": 41 > 30, "next_step": "requote"},
  "41 days is more than 30, so the quote is stale; approved but not current: requote.")

X("A4-EXTR-R2-X03", "Venue hire invoice", "Extract the venue hire charges",
  ["hire_cost is the rooms times the hire days times the daily room rate"],
  {"invoice_code": "string", "rooms": "integer", "hire_days": "integer", "hire_cost": "number"},
  "Venue hire invoice VH-81450 covers 2 rooms for 3 days at a daily room rate of 145.5.",
  {"invoice_code": "VH-81450", "rooms": 2, "hire_days": 3, "hire_cost": dmul(2, 3, "145.5")},
  "2 x 3 x 145.5 = {hire_cost}.")

X("A4-EXTR-R2-X04", "Van lease", "Extract the van lease terms",
  ["lease_end is the start date plus the lease length in weeks",
   "lease_cost is the weekly rate times the lease length in weeks"],
  {"lease_weeks": "integer", "lease_end": "YYYY-MM-DD", "lease_cost": "number", "insured": "boolean",
   "mileage": "limited|unlimited"},
  "The van lease starts on 2027-03-15 and runs for 18 weeks at a weekly rate of 64.25. Insurance is not included, "
  "and mileage is limited.",
  {"lease_weeks": 18, "lease_end": add_days("2027-03-15", 18 * 7), "lease_cost": dmul(18, "64.25"),
   "insured": False, "mileage": "limited"},
  "2027-03-15 plus 126 days is {lease_end}; 18 x 64.25 = {lease_cost}.")

X("A4-EXTR-R3-X01", "Analytics data export audit", "Extract the export audit",
  ["exported_gb is the total exported this week",
   "ceiling_breached is true when that total is above the weekly export ceiling"],
  {"account": "string", "exported_gb": "number", "ceiling_breached": "boolean"},
  "Analytics account @0 exported 4.5, 7.25 and 3 GB to external storage this week. The weekly export ceiling is "
  "12 GB.",
  {"account": "@0", "exported_gb": dsum("4.5", "7.25", 3), "ceiling_breached": dsum("4.5", "7.25", 3) > 12},
  "4.5 + 7.25 + 3 = {exported_gb} GB, above 12.")

X("A4-EXTR-R3-X02", "Guest wifi password", "Extract the guest network status",
  ["change_due is true when the devices connected since the last change exceed the policy limit"],
  {"changed_on": "YYYY-MM-DD", "devices": "integer", "network": "isolated|shared", "change_due": "boolean"},
  "The guest wifi password was last changed on 2028-06-30, and 212 devices have connected since. The guest network "
  "is isolated. Policy: change the password after 200 connected devices.",
  {"changed_on": "2028-06-30", "devices": 212, "network": "isolated", "change_due": 212 > 200},
  "212 devices exceed the limit of 200.")

X("A4-EXTR-R3-X03", "Records access log", "Extract the records access audit",
  ["ticketed_files is the number of files opened with a ticket",
   "policy_breach is true when any file was opened without a ticket"],
  {"clerk": "string", "files_opened": "integer", "ticketed_files": "integer", "policy_breach": "boolean",
   "review_notes": "provided|not_provided"},
  "Clerk @0 @1 opened 9 medical record files, 2 of them without a ticket. The supervisor's review notes have not "
  "been provided.",
  {"clerk": "@0 @1", "files_opened": 9, "ticketed_files": 9 - 2, "policy_breach": True,
   "review_notes": "not_provided"},
  "9 - 2 = {ticketed_files}; 2 files had no ticket; the notes are stated as not provided.", absence=True)

X("A4-EXTR-R3-X04", "Remote access request", "Extract the remote access ruling",
  ["ruling is allow when the device is company-managed and the security course is completed, block when the device "
   "is personal, and review otherwise"],
  {"employee": "string", "days_requested": "integer", "ruling": "allow|review|block"},
  "Remote access request from @0 @1 for 60 days. The device is company-managed, and the security course has been "
  "completed.",
  {"employee": "@0 @1", "days_requested": 60, "ruling": "allow"},
  "Both conditions hold, so allow.")

X("A4-EXTR-R4-X01", "Scaffold inspection tag", "Extract the scaffold inspection",
  ["ties_required is the lifts times the ties needed per lift"],
  {"scaffold_tag": "string", "lifts": "integer", "ties_required": "integer", "toe_boards": "boolean"},
  "Scaffold tag SC-22719 on the east wall: 4 lifts, and each lift needs 3 ties. Toe boards are fitted on every lift.",
  {"scaffold_tag": "SC-22719", "lifts": 4, "ties_required": 4 * 3, "toe_boards": True},
  "4 x 3 = {ties_required}.")

X("A4-EXTR-R4-X02", "Diesel tank deliveries", "Extract the diesel tank check",
  ["delivered_litres is the total of all deliveries since the last reading",
   "over_capacity is true when that total is above the tank capacity"],
  {"checked": "YYYY-MM-DD", "deliveries": "integer", "delivered_litres": "number", "over_capacity": "boolean",
   "tank": "single|double"},
  "Diesel tank check on 2029-07-23: 3 deliveries of 950.5, 1200 and 875.25 litres since the last reading. The tank "
  "holds 3000 litres and has a double wall.",
  {"checked": "2029-07-23", "deliveries": 3, "delivered_litres": dsum("950.5", 1200, "875.25"),
   "over_capacity": dsum("950.5", 1200, "875.25") > 3000, "tank": "double"},
  "950.5 + 1200 + 875.25 = {delivered_litres} litres, above 3000.")

X("A4-EXTR-R4-X03", "Waste transfer note", "Extract the waste note retention",
  ["retain_until is the issue year plus the retention period in years"],
  {"carrier": "string", "retain_until": "integer", "waste_code": "provided|not_provided"},
  "Waste transfer note from carrier @0, issued in 2040. Such notes must be kept for 3 years. The waste code has "
  "been provided on the note.",
  {"carrier": "@0", "retain_until": 2040 + 3, "waste_code": "provided"},
  "2040 + 3 = {retain_until}; the waste code was provided.", absence=True)

X("A4-EXTR-R4-X04", "Lifting sling proof test", "Extract the sling test record",
  ["safety_factor is the proof load divided by the safe working load",
   "retest_by is the proof test date plus the retest period"],
  {"proof_tonnes": "number", "safety_factor": "number", "retest_by": "YYYY-MM-DD", "tagged": "boolean"},
  "The lifting sling was proof-tested on 2033-01-20 to 7.5 tonnes; its safe working load is 3 tonnes. The retest "
  "period is 180 days, and an inspection tag is attached.",
  {"proof_tonnes": 7.5, "safety_factor": ddiv("7.5", 3), "retest_by": add_days("2033-01-20", 180), "tagged": True},
  "7.5 / 3 = {safety_factor}; 2033-01-20 plus 180 days is {retest_by}.")

# ================================================================ B′ reserves
X("B4-EXTR-R1-X01", "Book sale donations", "Extract the donation count",
  ["books_total is the paperbacks plus the hardbacks donated"],
  {"organiser": "string", "paperbacks": "integer", "books_total": "integer"},
  "The book sale table run by @0 received 34 paperbacks and 11 hardbacks.",
  {"organiser": "@0", "paperbacks": 34, "books_total": 34 + 11},
  "34 + 11 = {books_total}.")

X("B4-EXTR-R1-X02", "Half marathon target", "Extract the race plan",
  ["finish_clock is the start time plus the target running time",
   "sub_two is true when the target running time is under 2 hours"],
  {"finish_clock": "HH:MM", "distance_km": "number", "sub_two": "boolean"},
  "The race starts at 08:10. My target running time for the 21.1 km course is 1 hour 52 minutes.",
  {"finish_clock": add_min("08:10", 112), "distance_km": 21.1, "sub_two": 112 < 120},
  "08:10 plus 1:52 is {finish_clock}; 1:52 is under 2 hours.")

X("B4-EXTR-R1-X03", "Coffee bean order", "Extract the coffee order",
  ["beans_kg is the combined weight of the three bags"],
  {"roaster": "string", "beans_kg": "number", "grind": "whole|ground", "decaf": "boolean"},
  "Three bags from roaster @0: 0.25 kg, 0.5 kg and 0.35 kg, all whole bean and none of them decaf.",
  {"roaster": "@0", "beans_kg": dsum("0.25", "0.5", "0.35"), "grind": "whole", "decaf": False},
  "0.25 + 0.5 + 0.35 = {beans_kg} kg.")

X("B4-EXTR-R1-X04", "Reading challenge", "Extract the reading challenge progress",
  ["two_month_books is the books read over both months",
   "challenge_met is true when that count reaches the challenge target"],
  {"reader": "string", "this_month": "integer", "two_month_books": "integer", "challenge_met": "boolean"},
  "@0 read 7 books this month and 4 last month. The challenge target is 10 books over the two months.",
  {"reader": "@0", "this_month": 7, "two_month_books": 7 + 4, "challenge_met": 7 + 4 >= 10},
  "7 + 4 = {two_month_books}, which reaches 10.")

X("B4-EXTR-R1-X05", "Birthday party replies", "Extract the party replies",
  ["awaiting is the invited guests who have not replied",
   "big_party is true when more than 12 guests said yes"],
  {"guest_of_honour": "string", "invited": "integer", "awaiting": "integer", "big_party": "boolean",
   "venue_address": "provided|not_provided"},
  "Birthday party for @0: 18 guests invited, 13 said yes, 2 said no, and the rest have not replied. The venue "
  "address has not been provided.",
  {"guest_of_honour": "@0", "invited": 18, "awaiting": 18 - 13 - 2, "big_party": 13 > 12,
   "venue_address": "not_provided"},
  "18 - 13 - 2 = {awaiting}; 13 is more than 12; the address is stated as not provided.", absence=True)

X("B4-EXTR-R1-X06", "Group dog walk", "Extract the dog walk plan",
  ["plan is go when fewer than 6 dogs join and the leads are packed, cancel when the leads are not packed, and "
   "split otherwise"],
  {"walker": "string", "dogs": "integer", "leads_packed": "boolean", "route": "park|river",
   "plan": "go|split|cancel"},
  "Group walk led by @0 along the river with 5 dogs. The leads are packed.",
  {"walker": "@0", "dogs": 5, "leads_packed": True, "route": "river", "plan": "go"},
  "5 dogs is fewer than 6 and the leads are packed: go.")

X("B4-EXTR-R2-X01", "Petty cash envelope", "Extract the petty cash total",
  ["spent is the total of the three purchases"],
  {"office": "string", "spent": "number", "method": "cash|card"},
  "Petty cash for office @0: purchases of 12.4, 7.85 and 30 for supplies, all paid in cash.",
  {"office": "@0", "spent": dsum("12.4", "7.85", 30), "method": "cash"},
  "12.4 + 7.85 + 30 = {spent}.")

X("B4-EXTR-R2-X02", "Annual leave request", "Extract the leave check",
  ["leave_left is the allowance minus the days already taken",
   "request_fits is true when the requested days are no more than the days remaining"],
  {"employee": "string", "leave_left": "integer", "request_fits": "boolean"},
  "@0 @1 has taken 19 of 25 leave days this year and has asked for 8 more.",
  {"employee": "@0 @1", "leave_left": 25 - 19, "request_fits": 8 <= 25 - 19},
  "25 - 19 = {leave_left}; 8 requested days do not fit.")

X("B4-EXTR-R2-X03", "Water bill", "Extract the water bill",
  ["bill_amount is the cubic metres used times the price per cubic metre"],
  {"property": "string", "cubic_metres": "integer", "bill_amount": "number",
   "reading_date": "provided|not_provided"},
  "Water bill for flat @0: 14 cubic metres used at 2.35 per cubic metre. The meter reading date has not been "
  "provided.",
  {"property": "@0", "cubic_metres": 14, "bill_amount": dmul(14, "2.35"), "reading_date": "not_provided"},
  "14 x 2.35 = {bill_amount}; the reading date is stated as not provided.", absence=True)

X("B4-EXTR-R2-X04", "Applicant screening", "Extract the shortlisting decision",
  ["experienced is true when the applicant's years of experience meet the role requirement",
   "shortlist is yes when the applicant holds the licence and meets the experience requirement, no when the "
   "licence is missing, and maybe otherwise"],
  {"applicant": "string", "licensed": "boolean", "experienced": "boolean", "shortlist": "yes|maybe|no"},
  "Applicant @0 @1 holds the required licence and has 2 years of experience. The role asks for 3 years.",
  {"applicant": "@0 @1", "licensed": True, "experienced": 2 >= 3, "shortlist": "maybe"},
  "2 years is short of 3; licensed but not experienced: maybe.")

X("B4-EXTR-R2-X05", "Furniture order confirmation", "Extract the order confirmation",
  ["item_total is the chairs plus the tables ordered"],
  {"order_id": "string", "chairs": "integer", "item_total": "integer", "gift_wrap": "boolean",
   "shipping": "courier|collect"},
  "Order SO-39085: 6 chairs and 2 tables, sent by courier. No gift wrap was requested.",
  {"order_id": "SO-39085", "chairs": 6, "item_total": 6 + 2, "gift_wrap": False, "shipping": "courier"},
  "6 + 2 = {item_total}.")

X("B4-EXTR-R2-X06", "Kitchen order deposit", "Extract the kitchen order balance",
  ["amount_owed is the order value minus the deposit", "balance_due is the deposit date plus 28 days"],
  {"units": "integer", "order_value": "number", "amount_owed": "number", "balance_due": "YYYY-MM-DD",
   "fitting": "boolean"},
  "A deposit of 800 was paid on 2036-12-03 for a kitchen order of 4 units worth 3200.5. The balance is due 28 days "
  "after the deposit. Fitting is included.",
  {"units": 4, "order_value": 3200.5, "amount_owed": dsub("3200.5", 800),
   "balance_due": add_days("2036-12-03", 28), "fitting": True},
  "3200.5 - 800 = {amount_owed}; 2036-12-03 plus 28 days is {balance_due}.")

X("B4-EXTR-R3-X01", "Incident impact", "Extract the incident impact",
  ["affected_users is the number of offices times the users per office"],
  {"ticket": "string", "affected_users": "integer", "root_cause": "provided|not_provided"},
  "Security incident SI-47021 affects 3 offices with 16 users each. The root cause has not been provided.",
  {"ticket": "SI-47021", "affected_users": 3 * 16, "root_cause": "not_provided"},
  "3 x 16 = {affected_users}; the root cause is stated as not provided.", absence=True)

X("B4-EXTR-R3-X02", "Public storage bucket", "Extract the exposure assessment",
  ["exposed_until is the time the bucket was made public plus the exposure duration",
   "severity is critical when the bucket held personal data and external access was logged, minor when neither "
   "applies, and serious otherwise"],
  {"exposed_until": "HH:MM", "logging_on": "boolean", "severity": "critical|serious|minor"},
  "A storage bucket was made public at 14:25 and closed again 50 minutes later. It held personal data, but the logs "
  "show no external access. Logging was enabled throughout.",
  {"exposed_until": add_min("14:25", 50), "logging_on": True, "severity": "serious"},
  "14:25 plus 50 minutes is {exposed_until}; personal data but no logged access: serious.")

X("B4-EXTR-R3-X03", "Server key registration", "Extract the key registration",
  ["modern_key is true when the registered key is of type ed25519"],
  {"owner": "string", "host": "string", "key_type": "ed25519|rsa", "modern_key": "boolean"},
  "@0 @1 registered an ed25519 key for host @2. An older rsa key for the same host was retired.",
  {"owner": "@0 @1", "host": "@2", "key_type": "ed25519", "modern_key": True},
  "The registered key is ed25519.")

X("B4-EXTR-R3-X04", "Temporary admin rights", "Extract the temporary admin grant",
  ["revoke_at is the grant time plus the grant length",
   "prod_access is true when any covered system is a production system"],
  {"revoke_at": "HH:MM", "systems_covered": "integer", "prod_systems": "integer", "prod_access": "boolean"},
  "Temporary admin rights were granted to a contractor at 09:05 for 7 hours. The rights cover 3 systems, 1 of "
  "which is production.",
  {"revoke_at": add_min("09:05", 7 * 60), "systems_covered": 3, "prod_systems": 1, "prod_access": True},
  "09:05 plus 7 hours is {revoke_at}; one covered system is production.")

X("B4-EXTR-R3-X05", "Branch VPN traffic", "Extract the VPN traffic figures",
  ["traffic_gb is the traffic summed over the three days"],
  {"branch": "string", "vpn_users": "integer", "traffic_gb": "number", "split_tunnel": "boolean",
   "gateway": "primary|backup"},
  "Branch @0 has 42 VPN users, who sent 18.5, 22.25 and 9 GB over three days through the backup gateway. Split "
  "tunnelling is off.",
  {"branch": "@0", "vpn_users": 42, "traffic_gb": dsum("18.5", "22.25", 9), "split_tunnel": False,
   "gateway": "backup"},
  "18.5 + 22.25 + 9 = {traffic_gb} GB.")

X("B4-EXTR-R3-X06", "Privileged account review", "Extract the privileged account review",
  ["active_admins is the admin accounts minus the unused ones",
   "needs_cleanup is true when more than 2 admin accounts are unused"],
  {"reviewed": "YYYY-MM-DD", "admin_accounts": "integer", "active_admins": "integer", "needs_cleanup": "boolean",
   "scope": "cloud|onprem"},
  "The cloud privileged account review on 2037-05-05 covered 15 admin accounts, 4 of them unused for more than 90 "
  "days.",
  {"reviewed": "2037-05-05", "admin_accounts": 15, "active_admins": 15 - 4, "needs_cleanup": 4 > 2,
   "scope": "cloud"},
  "15 - 4 = {active_admins}; 4 unused is more than 2.")

X("B4-EXTR-R4-X01", "Confined space entry", "Extract the confined space entry decision",
  ["oxygen_safe is true when the oxygen reading is between 19.5 and 23.5 percent",
   "entry is approve when the oxygen reading is in the safe range and the rescue team is on standby, deny when the "
   "rescue team is absent, and retest otherwise"],
  {"permit_ref": "string", "oxygen_pct": "number", "oxygen_safe": "boolean", "entry": "approve|retest|deny"},
  "Entry permit EP-51806 for the settling tank: the oxygen reading is 19.2 percent, and the rescue team is on "
  "standby.",
  {"permit_ref": "EP-51806", "oxygen_pct": 19.2, "oxygen_safe": Decimal("19.5") <= Decimal("19.2") <= 23.5,
   "entry": "retest"},
  "19.2 is below 19.5, so not safe; the rescue team is present: retest.")


# ================================================================ assembly
PLACEHOLDER = re.compile(r"@(\d)")


def _fill(value, names):
    if isinstance(value, str):
        return PLACEHOLDER.sub(lambda m: names[int(m.group(1))], value)
    return value


def build():
    english, provenance = english_vocabulary()
    sys.path.insert(0, str(ROOT / "experiments/G-ROUTE4-candidate/blueprint"))
    import build_blueprint as B  # noqa: E402  read-only: G-ROUTE3's entity and lineage inventory
    g3_entities, g3_lineages = B.g_route3_entity_inventory()
    bank = NameBank(english, set(g3_entities) | set(g3_lineages))
    body = TEMPLATE[len("{SUBJECT}"):]
    fixtures, gold, design = [], [], []
    order = {fid: i for i, fid in enumerate(SLOTS)}
    for spec in sorted(SPECS, key=lambda s: order[s["fid"]]):
        fid = spec["fid"]
        slot = SLOTS[fid]
        texts = [spec["title"], spec["subject"], spec["text"], spec["rationale"], *spec["defs"],
                 *[v for v in spec["expected"].values() if isinstance(v, str)]]
        need = sorted({int(m) for t in texts for m in PLACEHOLDER.findall(t)})
        assert need == list(range(len(need))), (fid, need)
        names = [bank.take() for _ in need]
        sentences = [spec["subject"], *spec["defs"]] + ([ABSENCE[:-1]] if spec["absence"] else [])
        opening = ". ".join(_fill(s, names) for s in sentences)
        prompt = TEMPLATE.replace("{SUBJECT}", opening)
        assert prompt == opening + body
        expected = {k: _fill(v, names) for k, v in spec["expected"].items()}
        expected = {k: (bool(v) if isinstance(v, bool) else v) for k, v in expected.items()}
        assert list(expected) == list(spec["schema"]), fid
        rationale = _fill(spec["rationale"], names).format(**expected)
        text = _fill(spec["text"], names)
        fixtures.append({
            "consequence_risk": slot["risk"], "fixture_id": fid,
            "input": {"schema": spec["schema"], "text": text},
            "prompt": prompt, "task_class": "structured_extraction",
            "title": _fill(spec["title"], names), "validator_profile": "extraction.v1"})
        gold.append({"expected": expected, "fixture_id": fid, "rationale": rationale,
                     "reference_output": expected})
        design.append({"fixture_id": fid, "phase": slot["phase"], "role": slot["role"], "risk": slot["risk"],
                       "family": slot["family"], "features": slot["features"],
                       "derived_keys": [d.split(" is ", 1)[0] for d in spec["defs"]],
                       "absence_sentence": spec["absence"], "invented_names": names,
                       "identifiers": sorted(set(IDENT.findall(text)))})
    missing = sorted(set(SLOTS) - {f["fixture_id"] for f in fixtures})
    return {"schema_version": "g-route4.authoring-staging.v1", "task_class": "structured_extraction",
            "blueprint_commit": "1156d06", "status": "authored, not sealed, not adjudicated",
            "english_vocabulary": provenance, "missing_slots": missing,
            "fixtures": fixtures, "gold": gold, "design": design}


if __name__ == "__main__":
    out = build()
    path = HERE / "staging" / "extraction.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8",
                    newline="\n")
    print(f"{len(out['fixtures'])} fixtures written; missing slots: {out['missing_slots']}")

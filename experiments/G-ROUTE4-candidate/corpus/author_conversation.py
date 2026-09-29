"""Author the 142 frozen G-ROUTE4 Ordinary Conversation slots (pre-seal repair revision).

Deterministic corpus authoring only, to the frozen blueprint at commit 1156d06. It contacts no model or adjudicator
and creates no seal.

Repair revision (after the complete-corpus pre-seal review):
- every fixture is a natural first-person request with its own scenario; facts are stated in the message as a person
  would give them (clock times, dates, units, prices), never as pre-evaluated condition flags or unitless counters;
- the message contains only a request sentence and one sentence per option, and every sentence carries at least one
  fact the answer depends on; the authoring ledger binds each sentence to those facts so the checker can recompute
  the gold and reject any sentence that carries none;
- the frozen shape is unchanged: exactly four options, the gold at its frozen position, exactly one near miss that
  meets the first condition and fails the second (at depth 2, a correct first step and a wrong second step), and two
  options that meet neither;
- the invented-name stream is unchanged (four names per fixture, replayed from name_stream.json).

    python -B author_conversation.py
"""

import datetime as dt
import json
import math
import random
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from name_stream import NameStream  # noqa: E402

BLUEPRINT = json.loads((ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
TEMPLATE = BLUEPRINT["templates"]["ordinary_conversation"]["assembled_template"]
SLOTS = [s for s in BLUEPRINT["slots"] if s["task_class"] == "ordinary_conversation"]
UNIT = {"volume": {"ml": 1, "cl": 10, "l": 1000}, "mass": {"g": 1, "kg": 1000, "t": 1000000},
        "length": {"mm": 1, "cm": 10, "m": 1000}}


# ---------------------------------------------------------------- fact formatting (the checker re-derives these)
def fnum(v):
    d = Decimal(str(v)).normalize()
    return format(d, "f") if d != d.to_integral_value() else str(int(d))


def surface(value, fmt):
    kind = fmt[0]
    if kind == "n":
        return f"{fnum(value)}{fmt[1]}"
    if kind == "t":
        return f"{value // 60:02d}:{value % 60:02d}"
    if kind == "d":
        return dt.date.fromordinal(value).isoformat()
    if kind == "m":
        return f"{fnum(Decimal(value) / UNIT[fmt[1]][fmt[2]])} {fmt[2]}"
    if kind == "l":
        items = [fnum(v) for v in value]
        return (", ".join(items[:-1]) + " and " + items[-1]) + fmt[1]
    if kind == "r":
        return f"{value[0]} of {value[1]}{fmt[1]}"
    raise ValueError(kind)


def t(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def d(s):
    return dt.date.fromisoformat(s).toordinal()


# ---------------------------------------------------------------- the two conditions, per family and depth
def conditions(fam, depth, c, o):
    if fam == "CV1":
        if depth == 1:
            return o["a"] >= c["A"], o["b"] <= c["B"]
        return o["a1"] * o["a2"] >= c["A"], o["b1"] + o["b2"] <= c["B"]
    if fam == "CV2":
        if depth == 1:
            return o["dep"] >= c["E"], o["dep"] + o["dur"] <= c["T"]
        return o["dep"] + o["leg1"] <= c["X"], o["dep"] + o["leg1"] + o["leg2"] <= c["Y"]
    if fam == "CV3":
        if depth == 1:
            return o["vol"] >= c["need"], o["wt"] <= c["max"]
        total = o["count"] * o["size"]
        return total >= c["need"], total - o["waste"] >= c["net"]
    if fam == "CV4":
        high = [v for v in o["items"] if v >= c["thr"]]
        if depth == 1:
            return len(high) >= c["K"], len(o["items"]) - len(high) <= c["L"]
        return len(high) >= c["K"], sum(high) >= c["S"]
    if fam == "CV5":
        if depth == 1:
            x, y = o["ratio"]
            return 100 * x >= c["P"] * y, y >= c["N"]
        sale = Decimal(o["price"]) * (100 - o["disc"]) / 100
        return sale <= c["B1"], sale * (100 + c["tax"]) / 100 <= c["B2"]
    if fam == "CV6":
        gap = c["today"] - o["last"]
        if depth == 1:
            return o["g"] >= c["G"], gap >= c["Ex"]
        return o["g1"] + o["g2"] >= c["G"], gap >= c["Ex"]
    raise ValueError(fam)


WANT = [(True, True), (True, False), (False, False), (False, False)]      # gold, near miss, two distractors


# ---------------------------------------------------------------- deterministic value generators
def generate(fam, depth, sp, rng):
    r = rng.randint
    c = {k: v for k, v in sp.items() if k in {"A", "B", "E", "T", "X", "Y", "need", "max", "net", "thr", "K", "L",
                                              "S", "P", "N", "B1", "tax", "B2", "G", "Ex", "today"}}
    if fam == "CV1" and depth == 1:
        A, B, sa, sb = c["A"], c["B"], sp["sa"], sp["sb"]
        rows = [{"a": A + r(0, sa), "b": B - r(0, sb)}, {"a": A + r(1, sa), "b": B + r(1, sb)},
                {"a": A - r(1, sa), "b": B + r(1, sb)}, {"a": A - r(1, sa), "b": B + r(sb + 1, 2 * sb + 1)}]
    elif fam == "CV1":
        A, B = c["A"], c["B"]
        rows = []
        for want in WANT:
            m = rng.choice(sp["mult"])
            if not want[0]:
                m = min(sp["mult"])                         # plural counts for the short options
            a1 = math.ceil(A / m) + r(0, 1) if want[0] else max(2, (A - 1) // m - r(0, 1))
            fee = r(*sp["fee"])
            if want[1]:
                b1 = B - fee - r(0, sp["sb"])
            else:
                b1 = B - fee + r(1, min(sp["sb"], fee))
                if not want[0]:
                    b1 = B - fee + r(sp["sb"], 2 * sp["sb"])
            rows.append({"a1": a1, "a2": m, "b1": b1, "b2": fee})
    elif fam == "CV2" and depth == 1:
        E, T = c["E"], c["T"]
        lo, hi = sp["dur"]
        rows = []
        dep = E + r(0, sp.get("slack", 12))
        rows.append({"dep": dep, "dur": r(lo, min(hi, T - dep))})
        dep = E + r(0, sp.get("slack", 12))
        rows.append({"dep": dep, "dur": T - dep + r(1, sp.get("over", 15))})
        for _ in range(2):
            dep = E - r(sp.get("early", (5, 25))[0], sp.get("early", (5, 25))[1])
            rows.append({"dep": dep, "dur": T - dep + r(1, sp.get("over", 15) + 10)})
    elif fam == "CV2":
        X, Y = c["X"], c["Y"]
        rows = []
        for want in WANT:
            leg1 = r(*sp["leg1"])
            if want[0]:
                dep = X - leg1 - r(0, sp.get("slack", 10))
                room = Y - dep - leg1
                leg2 = r(max(1, room - sp.get("slack2", 20)), room) if want[1] else room + r(1, sp.get("over", 15))
            else:
                dep = X - leg1 + r(1, sp.get("late", 15))
                leg2 = Y - dep - leg1 + r(1, sp.get("over", 15))
            rows.append({"dep": dep, "leg1": leg1, "leg2": leg2})
    elif fam == "CV3" and depth == 1:
        need, mx, g1, g2 = c["need"], c["max"], sp["grain1"], sp["grain2"]
        rows = [{"vol": need + g1 * r(0, 4), "wt": mx - g2 * r(0, 4)},
                {"vol": need + g1 * r(1, 5), "wt": mx + g2 * r(1, 5)},
                {"vol": need - g1 * r(1, 5), "wt": mx + g2 * r(1, 5)},
                {"vol": need - g1 * r(1, 5), "wt": mx + g2 * r(6, 10)}]
    elif fam == "CV3":
        need, net = c["need"], c["net"]
        rows = []
        for want in WANT:
            size = rng.choice(sp["sizes"])
            if want[0]:
                count = math.ceil(need / size) + r(0, 1)
                total = count * size
                waste = sp["wgrain"] * r(0, max(0, (total - net) // sp["wgrain"])) if want[1] else \
                    total - net + sp["wgrain"] * r(1, 4)
            else:
                size = min(sp["sizes"])                     # plural counts for the short options
                count = max(2, (need - 1) // size - r(0, 1))
                total = count * size
                waste = sp["wgrain"] * r(1, 4)
                if total - waste >= net:
                    waste = total - net + sp["wgrain"]
            rows.append({"count": count, "size": size, "waste": waste})
    elif fam == "CV4":
        thr, K = c["thr"], c["K"]
        hi = lambda: thr + r(0, sp["spread"])            # noqa: E731
        lo_ = lambda: thr - r(1, sp["spread"])            # noqa: E731
        if depth == 1:
            L = c["L"]
            plan = [(K + r(0, 1), L - r(0, min(1, L))), (K, L + 1), (K - 1, L + 1), (K - 1 - r(0, min(1, K - 2)), L + 2)]
            rows = []
            for n_hi, n_lo in plan:
                items = [hi() for _ in range(n_hi)] + [lo_() for _ in range(n_lo)]
                rng.shuffle(items)
                rows.append({"items": items})
        else:
            S = c["S"]
            rows = []
            for want in WANT:
                n_hi = (K + r(0, 1) if want[1] else K) if want[0] else K - 1
                for _ in range(1000):
                    items_hi = [hi() for _ in range(n_hi)]
                    if (sum(items_hi) >= S) == want[1]:
                        break
                else:
                    raise AssertionError(("CV4 d2 generation", sp, want))
                items = items_hi + [lo_() for _ in range(r(1, 2))]
                rng.shuffle(items)
                rows.append({"items": items})
    elif fam == "CV5" and depth == 1:
        P, N = c["P"], c["N"]
        rows = []
        for want in WANT:
            y = N + r(0, sp["ny"]) if want[1] else N - r(1, sp["ny"])
            x = math.ceil(P * y / 100) + r(0, 2) if want[0] else math.ceil(P * y / 100) - r(1, 4)
            rows.append({"ratio": [min(x, y), y]})
    elif fam == "CV5":
        B1, tax, B2 = c["B1"], c["tax"], c["B2"]
        rows = []
        for want in WANT:
            for _ in range(500):
                disc = rng.choice(sp["discs"])
                price = sp["step"] * r(sp["price"][0] // sp["step"], sp["price"][1] // sp["step"])
                o = {"price": price, "disc": disc}
                if conditions("CV5", 2, c, o) == want:
                    break
            else:
                raise AssertionError(("CV5 d2 generation", sp))
            rows.append(o)
    elif fam == "CV6":
        G, Ex, today = c["G"], c["Ex"], c["today"]
        rows = []
        for want in WANT:
            # never exactly on the boundary: "within N days" is unambiguous only away from N
            gap = Ex + r(1, sp["gspread"]) if want[1] else Ex - r(1, min(Ex - 1, sp["gspread"]))
            if depth == 1:
                g = G + r(0, sp["spread"]) if want[0] else G - r(1, sp["spread"])
                rows.append({"g": g, "last": today - gap})
            else:
                total = G + r(0, sp["spread"]) if want[0] else G - r(1, sp["spread"])
                g1 = r(total // 3, (2 * total) // 3)
                rows.append({"g1": g1, "g2": total - g1, "last": today - gap})
    else:
        raise ValueError((fam, depth))
    return c, rows


CONS = []


def C(fam, depth, opening, title, request, option, **spec):
    CONS.append(dict(fam=fam, depth=depth, opening=opening, title=title, request=request, option=option, spec=spec))


N_ = ("n", "")
EUR = ("n", " EUR")
TIME = ("t",)
DATE = ("d",)
MIN = ("n", " minutes")


# ================================================================ templates, in blueprint slot order
# 1 CV1 d2 R1
C("CV1", 2, "Tell me which campsite can take our whole group within budget, using only the site details in my message",
  "Campsite for a group weekend",
  "We are {A} people and can spend {B} for the weekend, fees and booking charge together.",
  "{name} has {a1} pitches that each sleep {a2}, at {b1} in pitch fees plus a {b2} booking charge.",
  A=22, B=210, mult=[3, 4, 6], fee=(10, 30), sb=25, f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 2 CV2 d1 R1
C("CV2", 1, "Tell me which bus gets me to the match on time, using only the timetable in my message",
  "Bus to the football match",
  "I can't leave the flat before {E}, and I have to be at the stadium gates by {T}.",
  "The {name} bus leaves at {dep} and the ride takes {dur}.",
  E=t("17:45"), T=t("19:05"), dur=(25, 60), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 3 CV3 d2 R1
C("CV3", 2, "Tell me which paint deal leaves enough paint on the fence once tray waste is counted, using only what I "
  "wrote", "Fence paint quantity",
  "The shop says to buy at least {need} in total, and the fence itself needs {net} once the tray waste is gone.",
  "{name} sells {count} tins of {size}, and its brushes waste about {waste} in the tray.",
  need=5000, net=4500, sizes=[750, 1000, 2500], wgrain=50,
  f={"need": ("m", "volume", "l"), "net": ("m", "volume", "l"), "count": N_, "size": ("m", "volume", "ml"),
     "waste": ("m", "volume", "ml")})
# 4 CV4 d1 R1
C("CV4", 1, "Tell me which cottage week fits my sunshine rule, using only the forecasts I pasted",
  "Sunny cottage week",
  "I want at least {K} days with {thr} or more hours of sun, and no more than {L} duller days.",
  "The {name} cottage forecast shows {items} hours of sun.",
  thr=6, K=4, L=2, spread=3, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 5 CV5 d1 R2
C("CV5", 1, "Tell me which courier meets our on-time standard, using only the delivery records in my message",
  "Courier on-time standard",
  "Our office only signs couriers with at least {P}% of deliveries on time across at least {N} deliveries.",
  "{name} delivered {ratio} parcels on time last quarter.",
  P=92, N=60, ny=20, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 6 CV6 d2 R2
C("CV6", 2, "Tell me which staff member gets the spare desk this month under our rule, using only the hours and "
  "dates in my message", "Spare hot desk allocation",
  "The spare desk goes to someone with at least {G} office hours over the last two weeks, except that nobody who "
  "had it within the last {Ex} days before {today} can have it again.",
  "{name} logged {g1} and {g2} hours in those two weeks and last had the desk on {last}.",
  G=60, Ex=21, today=d("2046-05-04"), spread=8, gspread=10,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})
# 7 CV1 d1 R2
C("CV1", 1, "Tell me which meeting room to book for the workshop, using only the room details in my message",
  "Workshop room booking",
  "The workshop has {A} attendees and the room hire must not exceed {B} for the day.",
  "Room {name} seats {a} and costs {b} per day.",
  A=18, B=240, sa=6, sb=40, f={"A": N_, "B": EUR, "a": N_, "b": EUR})
# 8 CV2 d2 R2
C("CV2", 2, "Tell me which van route delivers the samples in time, using only the route times in my message",
  "Sample delivery route",
  "The van must reach the depot by {X} to catch the transfer and be at the lab by {Y}.",
  "Route {name} starts at {dep}, takes {leg1} to the depot and then {leg2} to the lab.",
  X=t("10:30"), Y=t("11:40"), leg1=(35, 55), f={"X": TIME, "Y": TIME, "dep": TIME, "leg1": MIN, "leg2": MIN})
# 9 CV3 d2 R3
C("CV3", 2, "Tell me which shredding bag option handles all the old personnel files, using only the capacities in my "
  "message", "Shredding bag capacity",
  "We have to send off at least {need} of old personnel files, and {net} must still fit once each option's reserved "
  "space for signed receipts is taken out.",
  "{name} provides {count} bags of {size} each and keeps {waste} of that for receipts.",
  need=60000, net=55000, sizes=[8000, 12000, 15000], wgrain=500,
  f={"need": ("m", "mass", "kg"), "net": ("m", "mass", "kg"), "count": N_, "size": ("m", "mass", "kg"),
     "waste": ("m", "mass", "g")})
# 10 CV4 d1 R3
C("CV4", 1, "Tell me which backup schedule passes our audit rule, using only the nightly results in my message",
  "Backup schedule audit",
  "The audit wants at least {K} nights where the verified share reached {thr}%, and at most {L} night below it.",
  "The {name} schedule reached {items} percent verified on its last nights.",
  thr=95, K=5, L=1, spread=3, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 11 CV5 d2 R3
C("CV5", 2, "Tell me which password manager plan stays within budget after the discount and tax, using only the "
  "prices in my message", "Password manager plan cost",
  "After its discount a plan must cost at most {B1}, and with {tax}% tax on top it must stay within {B2}.",
  "The {name} plan lists at {price} with a {disc}% discount.",
  B1=400, tax=20, B2=450, discs=[10, 20, 25], price=(360, 620), step=20,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 12 CV6 d1 R3
C("CV6", 1, "Tell me which contractor may be issued a server room badge today, using only the training record and "
  "dates in my message", "Server room badge eligibility",
  "Badges need at least {G} hours of security training, except that anyone whose last badge was revoked less than "
  "{Ex} days before {today} must wait.",
  "{name} has {g} training hours and last had a badge revoked on {last}.",
  G=12, Ex=90, today=d("2047-02-10"), spread=4, gspread=40,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 13 CV1 d1 R4
C("CV1", 1, "Tell me which hoist suits the engine lift, using only the ratings in my message",
  "Engine lift hoist",
  "The engine and frame weigh {A} kg, and the hoist's hook height must be no more than {B} cm off the floor.",
  "Hoist {name} is rated for {a} kg and has a hook height of {b} cm.",
  A=450, B=210, sa=80, sb=25, f={"A": N_, "B": N_, "a": N_, "b": N_})
# 14 CV3 d2 R4
C("CV3", 2, "Tell me which absorbent kit covers the tank spill plan, using only the kit contents in my message",
  "Spill kit capacity",
  "The spill plan needs kits absorbing at least {need} in total, with {net} left after the portion reserved for the "
  "drain covers.", "{name} holds {count} absorbent socks of {size} and reserves {waste} of that for drain covers.",
  need=12000, net=11000, sizes=[600, 800, 1000], wgrain=100,
  f={"need": ("m", "volume", "l"), "net": ("m", "volume", "l"), "count": N_, "size": ("m", "volume", "ml"),
     "waste": ("m", "volume", "ml")})
# 15 CV5 d1 R4
C("CV5", 1, "Tell me which harness batch meets the drop-test standard, using only the test figures in my message",
  "Harness drop tests", "A batch passes only if at least {P}% of at least {N} drop tests held.",
  "Batch {name} held in {ratio} drop tests.",
  P=98, N=150, ny=40, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 16 CV2 d2 R4
C("CV2", 2, "Tell me which crew rotation keeps the shutdown on schedule, using only the times in my message",
  "Shutdown crew rotation",
  "The isolation has to be done by {X} and the restart checks finished by {Y}.",
  "Crew {name} starts at {dep}, needs {leg1} for the isolation and {leg2} for the restart checks.",
  X=t("06:40"), Y=t("08:15"), leg1=(40, 70), f={"X": TIME, "Y": TIME, "dep": TIME, "leg1": MIN, "leg2": MIN})
# 17 CV1 d1 R1
C("CV1", 1, "Tell me which paddleboard to hire, using only the board details in my message", "Paddleboard hire",
  "I weigh {A} kg with my kit, so the board needs at least that rating, and I can spend {B} for the afternoon.",
  "The {name} board carries up to {a} kg and costs {b} to hire.",
  A=95, B=45, sa=20, sb=12, f={"A": N_, "B": EUR, "a": N_, "b": EUR})
# 18 CV1 d1 R1
C("CV1", 1, "Tell me which secondhand bike fits me, using only the listings I found", "Secondhand bike listing",
  "I'm tall enough for a frame of at least {A} cm, and I don't want to pay more than {B}.",
  "{name}'s listing has a {a} cm frame for {b}.",
  A=56, B=180, sa=4, sb=35, f={"A": N_, "B": EUR, "a": N_, "b": EUR})
# 19 CV1 d1 R1
C("CV1", 1, "Tell me which puppy class to join, using only the class details in my message", "Puppy class choice",
  "Our puppy needs a course of at least {A} sessions, and we can put in {B} at most.",
  "{name}'s course runs {a} sessions and costs {b}.",
  A=6, B=120, sa=3, sb=30, f={"A": N_, "B": EUR, "a": N_, "b": EUR})
# 20 CV1 d1 R1
C("CV1", 1, "Tell me which tent to buy for the festival, using only the product notes in my message",
  "Festival tent choice",
  "It has to sleep at least {A} of us and weigh no more than {B} kg in the pack.",
  "The {name} tent sleeps {a} and packs down to {b} kg.",
  A=3, B=5, sa=2, sb=2, f={"A": N_, "B": N_, "a": N_, "b": N_})
# 21 CV1 d2 R1
C("CV1", 2, "Tell me which caterer can feed the party within budget, using only the quotes in my message",
  "Party catering quote",
  "There will be {A} guests, and the whole quote including delivery must stay within {B}.",
  "{name} offers {a1} platters serving {a2} each for {b1}, plus {b2} delivery.",
  A=40, B=320, mult=[6, 8, 10], fee=(15, 40), sb=30, f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 22 CV2 d2 R1
C("CV2", 2, "Tell me which train plan gets me to the wedding on time, using only the timings in my message",
  "Train to the wedding",
  "I must change at the junction by {X} to catch the shuttle, and I need to be at the church by {Y}.",
  "The {name} option leaves at {dep}, takes {leg1} to the junction, then {leg2} to the church.",
  X=t("12:20"), Y=t("13:35"), leg1=(45, 80), f={"X": TIME, "Y": TIME, "dep": TIME, "leg1": MIN, "leg2": MIN})
# 23 CV2 d2 R1
C("CV2", 2, "Tell me which ferry and bus plan works for the island trip, using only the times in my message",
  "Island ferry and bus",
  "We have to be off the ferry by {X} for the last bus link and at the hostel by {Y}.",
  "Plan {name} sails at {dep}, the crossing is {leg1}, and the bus after it is {leg2}.",
  X=t("16:50"), Y=t("18:05"), leg1=(50, 90), f={"X": TIME, "Y": TIME, "dep": TIME, "leg1": MIN, "leg2": MIN})
# 24 CV2 d2 R1
C("CV2", 2, "Tell me which parcel service gets the gift there before the birthday, using only the dates in my "
  "message", "Birthday gift delivery",
  "The parcel has to be dispatched by {X} and delivered no later than {Y}.",
  "{name} dispatches on {dep} after {leg1} of packing and then takes {leg2} in transit.",
  X=d("2045-11-20"), Y=d("2045-11-26"), leg1=(2, 4), slack=1, slack2=2, late=3, over=3,
  f={"X": DATE, "Y": DATE, "dep": DATE, "leg1": ("n", " days"), "leg2": ("n", " days")})
# 25 CV2 d1 R1
C("CV2", 1, "Tell me which cinema showing I can make, using only the times in my message", "Evening cinema showing",
  "I finish work at {E} and must be home for the babysitter by {T}.",
  "The {name} showing starts at {dep} and runs {dur} including adverts.",
  E=t("18:10"), T=t("21:30"), dur=(110, 170), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 26 CV2 d1 R1
C("CV2", 1, "Tell me which swimming lane session fits my morning, using only the session times in my message",
  "Morning lane swim", "I can get to the pool from {E} and need to be out of the changing rooms by {T}.",
  "The {name} lane session starts at {dep} and lasts {dur}.",
  E=t("06:25"), T=t("07:50"), dur=(45, 75), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 27 CV3 d1 R1
C("CV3", 1, "Tell me which water bottle suits the hike, using only the bottle details in my message",
  "Hiking water bottle",
  "I need at least {need} of water for the ridge, and the bottle must weigh no more than {max} empty.",
  "The {name} bottle holds {vol} and weighs {wt} empty.",
  need=1500, max=300, grain1=50, grain2=20,
  f={"need": ("m", "volume", "l"), "max": ("m", "mass", "g"), "vol": ("m", "volume", "ml"),
     "wt": ("m", "mass", "g")})
# 28 CV3 d1 R1
C("CV3", 1, "Tell me which curtain fabric roll to order, using only the roll details in my message",
  "Curtain fabric roll",
  "The curtains need a roll at least {need} long, and the roll must weigh at most {max} for posting.",
  "{name}'s roll is {vol} long and weighs {wt}.",
  need=4500, max=3000, grain1=100, grain2=100,
  f={"need": ("m", "length", "m"), "max": ("m", "mass", "kg"), "vol": ("m", "length", "cm"),
     "wt": ("m", "mass", "g")})
# 29 CV3 d2 R1
C("CV3", 2, "Tell me which flour order covers the bake sale, using only the bag sizes in my message",
  "Bake sale flour order",
  "The recipes need {need} of flour in total, and {net} must remain after the dusting and spillage each bakery warns "
  "about.", "{name} sells {count} bags of {size} and warns that about {waste} goes on dusting.",
  need=6000, net=5600, sizes=[1000, 1500, 2000], wgrain=100,
  f={"need": ("m", "mass", "kg"), "net": ("m", "mass", "kg"), "count": N_, "size": ("m", "mass", "g"),
     "waste": ("m", "mass", "g")})
# 30 CV3 d2 R1
C("CV3", 2, "Tell me which grass seed order covers the new lawn, using only the box sizes in my message",
  "New lawn seed",
  "The lawn needs at least {need} of seed bought and {net} actually sown after what the birds take.",
  "{name} sells {count} boxes of {size} and says birds usually take about {waste}.",
  need=5000, net=4600, sizes=[500, 750, 1000], wgrain=50,
  f={"need": ("m", "mass", "kg"), "net": ("m", "mass", "kg"), "count": N_, "size": ("m", "mass", "g"),
     "waste": ("m", "mass", "g")})
# 31 CV3 d2 R1
C("CV3", 2, "Tell me which yarn pack is enough for the blanket, using only the pack details in my message",
  "Blanket yarn pack",
  "The pattern calls for at least {need} of yarn, with {net} still left after the swatch and the ends.",
  "{name}'s pack has {count} skeins of {size}, and its swatch uses about {waste}.",
  need=1800, net=1650, sizes=[100, 150, 200], wgrain=10,
  f={"need": ("m", "mass", "kg"), "net": ("m", "mass", "kg"), "count": N_, "size": ("m", "mass", "g"),
     "waste": ("m", "mass", "g")})
# 32 CV4 d2 R1
C("CV4", 2, "Tell me which fishing week meets my catch rule, using only the logbook figures in my message",
  "Fishing week choice",
  "I want at least {K} days with {thr} or more fish, and those good days together must add up to {S} fish or more.",
  "{name}'s log for the week shows {items} fish a day.",
  thr=5, K=3, S=21, spread=3, f={"thr": N_, "K": N_, "S": N_, "items": ("l", "")})
# 33 CV4 d1 R1
C("CV4", 1, "Tell me which running plan suits me, using only the weekly distances in my message",
  "Running plan distances",
  "I want at least {K} runs of {thr} km or more in a week, and no more than {L} shorter runs.",
  "The {name} plan has runs of {items} km.",
  thr=8, K=3, L=2, spread=4, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 34 CV4 d1 R1
C("CV4", 1, "Tell me which language course suits me, using only the lesson lengths in my message",
  "Language course lessons",
  "I want at least {K} lessons of {thr} minutes or longer, and no more than {L} shorter lesson.",
  "{name}'s course has lessons of {items} minutes.",
  thr=60, K=3, L=1, spread=15, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 35 CV4 d1 R1
C("CV4", 1, "Tell me which cycling club ride series to join, using only the climb figures in my message",
  "Cycling club ride series",
  "I want at least {K} rides with {thr} metres or more of climbing and at most {L} flatter ones.",
  "The {name} series lists climbs of {items} metres.",
  thr=600, K=4, L=2, spread=150, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 36 CV4 d1 R1
C("CV4", 1, "Tell me which seed tray mix gave the best sowing, using only the tray counts in my message",
  "Seed tray germination",
  "A mix counts as good if at least {K} trays had {thr} or more seedlings and no more than {L} tray fell short.",
  "The {name} mix produced {items} seedlings per tray.",
  thr=18, K=4, L=1, spread=5, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 37 CV5 d2 R1
C("CV5", 2, "Tell me which game console bundle I can afford, using only the prices in my message",
  "Console bundle price",
  "After any discount the bundle should cost at most {B1}, and with {tax}% sales tax at most {B2}.",
  "The {name} bundle is {price} with {disc}% off.",
  B1=380, tax=20, B2=432, discs=[10, 20, 25], price=(380, 600), step=20,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 38 CV5 d2 R1
C("CV5", 2, "Tell me which sofa offer fits our budget, using only the prices in my message", "Sofa offer budget",
  "The sofa must come to at most {B1} after the sale price, and at most {B2} once the {tax}% delivery surcharge is "
  "added.", "The {name} sofa is priced at {price} with {disc}% off in the sale.",
  B1=900, tax=10, B2=960, discs=[10, 15, 20, 30], price=(900, 1400), step=50,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 39 CV5 d2 R1
C("CV5", 2, "Tell me which guitar amp deal fits my limit, using only the prices in my message", "Guitar amp deal",
  "I can pay {B1} at most once the discount is taken off, and {B2} at most after {tax}% import duty.",
  "{name}'s amp costs {price} before a {disc}% discount.",
  B1=300, tax=15, B2=330, discs=[10, 20, 25], price=(300, 480), step=20,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 40 CV5 d2 R1
C("CV5", 2, "Tell me which telescope offer stays within my savings, using only the prices in my message",
  "Telescope offer",
  "The discounted price may not go above {B1}, and with the {tax}% shipping fee it must stay at or below {B2}.",
  "The {name} telescope is {price} with a {disc}% club discount.",
  B1=520, tax=12, B2=560, discs=[10, 15, 20], price=(520, 760), step=20,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 41 CV6 d1 R1
C("CV6", 1, "Tell me which member can take the club canoe this weekend under our rule, using only the details in my "
  "message", "Club canoe weekend",
  "Members need at least {G} paddling hours logged, except anyone who had the canoe fewer than {Ex} days before "
  "{today}.", "{name} has {g} logged hours and last took the canoe on {last}.",
  G=20, Ex=14, today=d("2045-06-21"), spread=6, gspread=6,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 42 CV6 d1 R1
C("CV6", 1, "Tell me which neighbour gets the shared allotment plot this season, using only the details in my "
  "message", "Shared allotment plot",
  "The plot goes to someone with at least {G} volunteer hours at the gardens, except that a holder from within the "
  "last {Ex} days before {today} cannot take it again.",
  "{name} gave {g} volunteer hours and last held the plot until {last}.",
  G=15, Ex=365, today=d("2046-03-01"), spread=5, gspread=90,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 43 CV6 d1 R1
C("CV6", 1, "Tell me which child can borrow the school telescope for the holidays, using only the details in my "
  "message", "School telescope loan",
  "Pupils need at least {G} astronomy club attendances, except that nobody who returned it within {Ex} days of "
  "{today} can borrow it again.", "{name} has {g} attendances and last returned it on {last}.",
  G=10, Ex=30, today=d("2045-12-15"), spread=3, gspread=12,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 44 CV6 d1 R1
C("CV6", 1, "Tell me which choir member can have the solo slot, using only the rota details in my message",
  "Choir solo slot",
  "Solos go to singers with at least {G} rehearsals this term, except that anyone who sang a solo within {Ex} days "
  "before {today} must wait.", "{name} has come to {g} rehearsals and last sang a solo on {last}.",
  G=12, Ex=42, today=d("2046-10-18"), spread=4, gspread=15,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 45 CV3 d1 R2
C("CV3", 1, "Tell me which coffee urn to order for the conference, using only the product details in my message",
  "Conference coffee urn",
  "The urn has to hold at least {need} and weigh no more than {max} when empty for the lift.",
  "The {name} urn holds {vol} and weighs {wt} empty.",
  need=12000, max=9000, grain1=500, grain2=250,
  f={"need": ("m", "volume", "l"), "max": ("m", "mass", "kg"), "vol": ("m", "volume", "l"),
     "wt": ("m", "mass", "g")})
# 46 CV3 d1 R2
C("CV3", 1, "Tell me which display board to order for the trade stand, using only the board details in my message",
  "Trade stand display board",
  "The board must be at least {need} wide and weigh at most {max} for the courier.",
  "The {name} board is {vol} wide and weighs {wt}.",
  need=2400, max=15000, grain1=50, grain2=500,
  f={"need": ("m", "length", "m"), "max": ("m", "mass", "kg"), "vol": ("m", "length", "cm"),
     "wt": ("m", "mass", "kg")})
# 47 CV3 d1 R2
C("CV3", 1, "Tell me which printer paper box to order, using only the box details in my message",
  "Printer paper box",
  "The box has to contain at least {need} of paper for the quarter and weigh no more than {max} for the stairs.",
  "{name}'s box contains {vol} of paper and weighs {wt}.",
  need=25000, max=20000, grain1=1000, grain2=500,
  f={"need": ("m", "mass", "kg"), "max": ("m", "mass", "kg"), "vol": ("m", "mass", "g"),
     "wt": ("m", "mass", "kg")})
# 48 CV3 d1 R2
C("CV3", 1, "Tell me which cleaning concentrate to reorder, using only the container details in my message",
  "Cleaning concentrate reorder",
  "Each container must hold at least {need} and weigh at most {max} full so the porters can carry it.",
  "The {name} container holds {vol} and weighs {wt} full.",
  need=5000, max=6000, grain1=250, grain2=250,
  f={"need": ("m", "volume", "l"), "max": ("m", "mass", "kg"), "vol": ("m", "volume", "cl"),
     "wt": ("m", "mass", "g")})
# 49 CV3 d2 R2
C("CV3", 2, "Tell me which skirting board order covers the office refit, using only the board lengths in my message",
  "Office skirting order",
  "The fitter says to order at least {need} of skirting board and to have {net} fitted after offcuts.",
  "{name} supplies {count} lengths of {size}, with about {waste} lost to offcuts.",
  need=30000, net=28000, sizes=[2400, 3000, 3600], wgrain=100,
  f={"need": ("m", "length", "m"), "net": ("m", "length", "m"), "count": N_, "size": ("m", "length", "cm"),
     "waste": ("m", "length", "cm")})
# 50 CV4 d2 R2
C("CV4", 2, "Tell me which sales rep qualifies for the monthly bonus, using only the weekly figures in my message",
  "Sales bonus qualification",
  "A rep qualifies with at least {K} weeks of {thr} or more sales, and those strong weeks together must total at "
  "least {S} sales.", "{name} made {items} sales in the weeks this month.",
  thr=12, K=3, S=42, spread=5, f={"thr": N_, "K": N_, "S": N_, "items": ("l", "")})
# 51 CV4 d2 R2
C("CV4", 2, "Tell me which warehouse shift earns the productivity award, using only the daily pick counts in my "
  "message", "Warehouse productivity award",
  "The award needs at least {K} days with {thr} or more picks, and those days must add up to {S} picks or more.",
  "Shift {name} picked {items} orders on its days this week.",
  thr=400, K=4, S=1720, spread=60, f={"thr": N_, "K": N_, "S": N_, "items": ("l", "")})
# 52 CV4 d2 R2
C("CV4", 2, "Tell me which venue hits the ticket target, using only the booking figures in my message",
  "Venue ticket target",
  "We need at least {K} nights selling {thr} or more tickets, with those nights totalling {S} tickets or more.",
  "{name} sold {items} tickets on its nights last season.",
  thr=150, K=3, S=500, spread=40, f={"thr": N_, "K": N_, "S": N_, "items": ("l", "")})
# 53 CV4 d1 R2
C("CV4", 1, "Tell me which supplier meets our delivery reliability rule, using only the lead times in my message",
  "Supplier delivery reliability",
  "We want at least {K} recent orders filled to {thr}% or more, and at most {L} order filled below that.",
  "{name}'s recent orders were filled to {items} percent.",
  thr=95, K=4, L=1, spread=4, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 54 CV4 d1 R2
C("CV4", 1, "Tell me which cleaning contractor passed our inspection rule, using only the scores in my message",
  "Cleaning contractor inspections",
  "A contractor passes with at least {K} inspections scoring {thr} or more and no more than {L} lower score.",
  "{name} scored {items} in its inspections this year.",
  thr=80, K=4, L=1, spread=8, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 55 CV5 d1 R2
C("CV5", 1, "Tell me which caterer meets our satisfaction bar, using only the survey figures in my message",
  "Caterer satisfaction bar",
  "We only rebook caterers rated good by at least {P}% of at least {N} surveyed guests.",
  "{name} was rated good by {ratio} guests surveyed.",
  P=85, N=80, ny=25, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 56 CV5 d1 R2
C("CV5", 1, "Tell me which temp agency meets our fill-rate rule, using only the shift figures in my message",
  "Temp agency fill rate",
  "An agency stays on our list if it filled at least {P}% of at least {N} requested shifts.",
  "{name} filled {ratio} requested shifts.",
  P=90, N=120, ny=30, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 57 CV5 d2 R2
C("CV5", 2, "Tell me which office chair order fits the budget, using only the prices in my message",
  "Office chair order",
  "The chairs must cost at most {B1} after the volume discount, and at most {B2} with {tax}% tax added.",
  "{name} quotes {price} for the batch with {disc}% volume discount.",
  B1=2400, tax=20, B2=2700, discs=[10, 20, 25], price=(2400, 3600), step=100,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 58 CV5 d2 R2
C("CV5", 2, "Tell me which hotel package works for the sales trip, using only the rates in my message",
  "Sales trip hotel package",
  "After the corporate discount the package may cost at most {B1}, and at most {B2} once the {tax}% city tax is "
  "added.", "The {name} package is {price} with a {disc}% corporate discount.",
  B1=640, tax=10, B2=680, discs=[10, 15, 20], price=(640, 920), step=20,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 59 CV5 d2 R2
C("CV5", 2, "Tell me which laptop quote we can approve, using only the prices in my message", "Laptop quote",
  "A laptop quote must be at most {B1} after the discount and at most {B2} after {tax}% tax.",
  "{name}'s quote is {price} per laptop with {disc}% off.",
  B1=900, tax=20, B2=1020, discs=[10, 15, 20, 25], price=(900, 1300), step=20,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 60 CV6 d2 R2
C("CV6", 2, "Tell me which employee gets the conference place under our rule, using only the details in my message",
  "Conference place allocation",
  "The place goes to someone with at least {G} training credits across the last two years, except anyone who "
  "attended a conference within {Ex} days before {today}.",
  "{name} earned {g1} and {g2} credits in those years and last went to a conference on {last}.",
  G=30, Ex=180, today=d("2047-01-20"), spread=6, gspread=60,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})
# 61 CV6 d1 R2
C("CV6", 1, "Tell me which supplier can be offered the framework contract, using only the details in my message",
  "Framework contract offer",
  "Suppliers need at least {G} completed orders with us, except that anyone with a late delivery less than {Ex} "
  "days before {today} must wait.", "{name} has completed {g} orders and its last late delivery was on {last}.",
  G=25, Ex=60, today=d("2046-08-01"), spread=6, gspread=25,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 62 CV6 d1 R2
C("CV6", 1, "Tell me which team can book the big meeting room for the offsite, using only the details in my message",
  "Big meeting room booking",
  "Teams of at least {G} people may book it, except a team that used it within {Ex} days before {today}.",
  "The {name} team has {g} people and last used the room on {last}.",
  G=12, Ex=28, today=d("2046-04-06"), spread=4, gspread=10,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 63 CV6 d1 R2
C("CV6", 1, "Tell me which member of staff can take the company car, using only the details in my message",
  "Company car booking",
  "Drivers need at least {G} months with a full licence, except anyone who returned the car damaged within {Ex} "
  "days before {today}.", "{name} has held a full licence for {g} months and last returned it damaged on {last}.",
  G=24, Ex=120, today=d("2046-09-09"), spread=8, gspread=40,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 64 CV6 d1 R2
C("CV6", 1, "Tell me which intern gets the remote working day, using only the details in my message",
  "Intern remote day",
  "Interns need at least {G} weeks in the office first, except anyone who had a remote day within {Ex} days "
  "before {today}.", "{name} has done {g} weeks in the office and last worked remotely on {last}.",
  G=6, Ex=10, today=d("2046-07-17"), spread=3, gspread=5,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 65 CV1 d2 R2
C("CV1", 2, "Tell me which coach company can carry the staff outing within budget, using only the quotes in my "
  "message", "Staff outing coaches",
  "We need seats for {A} staff, and the total with the driver's fee must stay within {B}.",
  "{name} offers {a1} coaches of {a2} seats for {b1}, plus a {b2} driver's fee.",
  A=110, B=1500, mult=[33, 49, 53], fee=(80, 200), sb=150,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 66 CV1 d2 R2
C("CV1", 2, "Tell me which printer can handle the brochure run within budget, using only the quotes in my message",
  "Brochure print run",
  "We need at least {A} brochures, and the job including setup has to come in at {B} or less.",
  "{name} prints {a1} boxes of {a2} brochures for {b1}, plus {b2} for setup.",
  A=5000, B=1800, mult=[250, 500], fee=(60, 150), sb=120,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 67 CV1 d2 R2
C("CV1", 2, "Tell me which storage unit deal holds our archive boxes within budget, using only the details in my "
  "message", "Archive storage deal",
  "We have {A} archive boxes to store, and a year's rent plus the access card fee must stay within {B}.",
  "{name} offers {a1} bays holding {a2} boxes each for {b1} a year, plus a {b2} access card fee.",
  A=300, B=2400, mult=[40, 60, 75], fee=(30, 90), sb=150,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 68 CV1 d2 R2
C("CV1", 2, "Tell me which lunch supplier covers the training days within budget, using only the quotes in my "
  "message", "Training day lunches",
  "We need at least {A} lunches over the course, and the order plus delivery can't exceed {B}.",
  "{name} offers {a1} trays of {a2} lunches for {b1}, with delivery at {b2}.",
  A=96, B=700, mult=[8, 12, 16], fee=(20, 60), sb=60,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 69 CV2 d1 R2
C("CV2", 1, "Tell me which webinar slot works for the client call, using only the times in my message",
  "Client webinar slot",
  "The client can't start before {E} their time and has a hard stop at {T}.",
  "The {name} slot starts at {dep} and is booked for {dur}.",
  E=t("14:00"), T=t("15:45"), dur=(45, 90), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 70 CV2 d1 R2
C("CV2", 1, "Tell me which cleaning crew visit fits the office hours, using only the times in my message",
  "Office cleaning visit",
  "Cleaners can't arrive before the building opens at {E} and must be finished by {T} when staff arrive.",
  "Crew {name} can start at {dep} and needs {dur} for the floor.",
  E=t("05:30"), T=t("07:15"), dur=(60, 100), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 71 CV2 d1 R2
C("CV2", 1, "Tell me which interview slot the candidate can make, using only the times in my message",
  "Candidate interview slot",
  "The candidate lands at the airport at {E} and has to leave our office by {T} for the return flight.",
  "The {name} slot starts at {dep} and runs for {dur}.",
  E=t("11:20"), T=t("15:10"), dur=(90, 150), early=(20, 60), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 72 CV2 d1 R2
C("CV2", 1, "Tell me which furniture delivery window works for the new office, using only the dates in my message",
  "Office furniture delivery",
  "The keys are handed over on {E}, and everything must be in place by {T} for the opening.",
  "{name} can start on {dep} and needs {dur} to deliver and assemble.",
  E=d("2046-02-02"), T=d("2046-02-13"), dur=(3, 7), slack=2, over=3, early=(1, 4),
  f={"E": DATE, "T": DATE, "dep": DATE, "dur": ("n", " days")})
# 73 CV5 d1 R3
C("CV5", 1, "Tell me which mail filter setting meets our catch rate, using only the test figures in my message",
  "Mail filter catch rate",
  "Security wants a setting that caught at least {P}% of at least {N} test phishing emails.",
  "The {name} setting caught {ratio} test emails.",
  P=97, N=200, ny=60, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 74 CV5 d1 R3
C("CV5", 1, "Tell me which laptop fleet meets the encryption rule, using only the audit figures in my message",
  "Fleet encryption audit",
  "A fleet passes if at least {P}% of its laptops are encrypted and at least {N} laptops were checked.",
  "The {name} fleet had {ratio} checked laptops encrypted.",
  P=95, N=100, ny=30, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 75 CV5 d1 R3
C("CV5", 1, "Tell me which department completed the privacy course well enough, using only the figures in my "
  "message", "Privacy course completion",
  "A department is compliant if at least {P}% of at least {N} enrolled staff finished the course.",
  "{name} department had {ratio} enrolled staff finish.",
  P=90, N=40, ny=15, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 76 CV5 d1 R3
C("CV5", 1, "Tell me which door reader passed the access test, using only the test figures in my message",
  "Door reader access test",
  "A reader passes if it correctly refused at least {P}% of at least {N} invalid badge attempts.",
  "Reader {name} refused {ratio} invalid attempts.",
  P=99, N=300, ny=80, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 77 CV5 d2 R3
C("CV5", 2, "Tell me which security camera contract we can afford, using only the prices in my message",
  "Security camera contract",
  "After the multi-year discount the contract must cost at most {B1}, and at most {B2} with {tax}% tax.",
  "{name}'s contract is {price} with a {disc}% multi-year discount.",
  B1=3000, tax=20, B2=3400, discs=[10, 15, 20, 25], price=(3000, 4400), step=100,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 78 CV6 d2 R3
C("CV6", 2, "Tell me which engineer may receive production database access, using only the details in my message",
  "Production database access",
  "Access needs at least {G} hours of on-call shadowing across the last two quarters, except anyone who had an "
  "access violation within {Ex} days before {today}.",
  "{name} shadowed {g1} and {g2} hours in those quarters, with a last violation on {last}.",
  G=40, Ex=180, today=d("2047-03-03"), spread=8, gspread=70,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})
# 79 CV6 d2 R3
C("CV6", 2, "Tell me which volunteer may handle the donor records, using only the details in my message",
  "Donor records handling",
  "Volunteers need at least {G} supervised sessions over the last two terms, except anyone who breached the data "
  "rules within {Ex} days before {today}.",
  "{name} did {g1} and {g2} supervised sessions and last breached the rules on {last}.",
  G=16, Ex=365, today=d("2046-11-11"), spread=4, gspread=100,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})
# 80 CV6 d2 R3
C("CV6", 2, "Tell me which contractor can be issued remote access this week, using only the details in my message",
  "Contractor remote access",
  "Remote access needs at least {G} completed tickets over the last two months, except anyone whose access was "
  "suspended within {Ex} days before {today}.",
  "{name} closed {g1} and {g2} tickets in those months and was last suspended on {last}.",
  G=35, Ex=45, today=d("2046-12-02"), spread=6, gspread=20,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})
# 81 CV6 d1 R3
C("CV6", 1, "Tell me which clinic assistant can be given the records room key, using only the details in my message",
  "Records room key holder",
  "Key holders need at least {G} months in post, except anyone who lost a key within {Ex} days before {today}.",
  "{name} has been in post {g} months and last lost a key on {last}.",
  G=9, Ex=180, today=d("2047-05-19"), spread=3, gspread=60,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 82 CV6 d1 R3
C("CV6", 1, "Tell me which analyst can run the customer data export, using only the details in my message",
  "Customer data export",
  "Exports need an analyst with at least {G} passed data-handling modules, except anyone flagged by an audit "
  "within {Ex} days before {today}.", "{name} has passed {g} modules and was last flagged on {last}.",
  G=5, Ex=90, today=d("2046-06-30"), spread=2, gspread=30,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 83 CV1 d1 R3
C("CV1", 1, "Tell me which shredding service meets our contract rules, using only the service details in my message",
  "Shredding service contract",
  "The service must collect at least {A} confidential bins a visit and charge no more than {B} per visit.",
  "{name} collects {a} bins a visit for {b}.",
  A=12, B=260, sa=5, sb=45, f={"A": N_, "B": EUR, "a": N_, "b": EUR})
# 84 CV1 d1 R3
C("CV1", 1, "Tell me which backup provider meets our retention and cost rules, using only the details in my message",
  "Backup provider selection",
  "We need at least {A} days of retention for no more than {B} a month.",
  "{name} keeps backups for {a} days at {b} a month.",
  A=90, B=400, sa=30, sb=60, f={"A": N_, "B": EUR, "a": N_, "b": EUR})
# 85 CV1 d2 R3
C("CV1", 2, "Tell me which locker order secures every clinical record trolley within budget, using only the quotes in "
  "my message", "Record trolley lockers",
  "We must lock away {A} record trolleys, and the lockers plus installation must cost {B} or less.",
  "{name} offers {a1} locker banks holding {a2} trolleys each for {b1}, plus {b2} to install.",
  A=30, B=4200, mult=[4, 6, 8], fee=(200, 450), sb=300,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 86 CV1 d2 R3
C("CV1", 2, "Tell me which badge printer order covers the new starters within budget, using only the quotes in my "
  "message", "Badge card order",
  "We need cards for {A} new starters, and the cards plus the encoding fee must stay within {B}.",
  "{name} sells {a1} packs of {a2} cards for {b1}, plus {b2} for encoding.",
  A=180, B=520, mult=[25, 50], fee=(40, 90), sb=70,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 87 CV1 d2 R3
C("CV1", 2, "Tell me which secure bag order covers the courier runs within budget, using only the quotes in my "
  "message", "Tamper-evident bag order",
  "The courier needs {A} tamper-evident bags this year, and the order with its shipping must cost {B} or less.",
  "{name} ships {a1} rolls of {a2} bags for {b1}, with {b2} shipping.",
  A=1200, B=380, mult=[100, 150, 200], fee=(15, 45), sb=40,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 88 CV2 d2 R3
C("CV2", 2, "Tell me which patching plan finishes inside the change window, using only the times in my message",
  "Patching change window",
  "Patching must finish by {X} so the scan can run, and the scan must be complete by {Y}.",
  "Plan {name} starts at {dep}, patches for {leg1} and then scans for {leg2}.",
  X=t("02:30"), Y=t("03:40"), leg1=(60, 110), f={"X": TIME, "Y": TIME, "dep": TIME, "leg1": MIN, "leg2": MIN})
# 89 CV2 d1 R3
C("CV2", 1, "Tell me which audit interview slot fits the compliance officer, using only the times in my message",
  "Compliance interview slot",
  "The officer is free from {E} and has to leave for the regulator meeting at {T}.",
  "The {name} interview begins at {dep} and is planned for {dur}.",
  E=t("09:40"), T=t("11:55"), dur=(50, 100), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 90 CV2 d1 R3
C("CV2", 1, "Tell me which data deletion run can go ahead tonight, using only the times in my message",
  "Overnight deletion run",
  "Deletion jobs may not start before {E}, after the last backup, and must end by {T} before staff log in.",
  "The {name} job starts at {dep} and runs {dur}.",
  E=t("01:15"), T=t("05:45"), dur=(150, 250), early=(10, 40), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 91 CV2 d1 R3
C("CV2", 1, "Tell me which access review meeting fits the auditors, using only the dates in my message",
  "Access review meeting",
  "The auditors arrive on {E} and need the review signed off by {T}.",
  "The {name} review can begin on {dep} and takes {dur}.",
  E=d("2047-04-07"), T=d("2047-04-18"), dur=(3, 8), slack=2, over=3, early=(1, 4),
  f={"E": DATE, "T": DATE, "dep": DATE, "dur": ("n", " days")})
# 92 CV2 d1 R3
C("CV2", 1, "Tell me which penetration test slot fits the freeze, using only the times in my message",
  "Penetration test slot",
  "Testing can't start before the change freeze lifts at {E} and must stop by {T}.",
  "The {name} slot starts at {dep} and lasts {dur}.",
  E=t("19:00"), T=t("23:20"), dur=(120, 220), early=(15, 45), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 93 CV3 d2 R3
C("CV3", 2, "Tell me which archive crate order holds all the case files, using only the crate sizes in my message",
  "Archive crate order",
  "We must buy at least {need} of crate space and keep {net} usable after the space each supplier's lid inserts take.",
  "{name} sells {count} crates of {size} and its lid inserts take about {waste}.",
  need=160000, net=150000, sizes=[20000, 40000, 50000], wgrain=500,
  f={"need": ("m", "volume", "l"), "net": ("m", "volume", "l"), "count": N_, "size": ("m", "volume", "l"),
     "waste": ("m", "volume", "ml")})
# 94 CV3 d2 R3
C("CV3", 2, "Tell me which cabinet order fits the paper records, using only the drawer sizes in my message",
  "Records cabinet order",
  "The records fill at least {need} of drawer length, and {net} must remain after the space kept for divider cards.",
  "{name} offers {count} drawers of {size}, keeping {waste} for dividers.",
  need=24000, net=22000, sizes=[600, 750, 900], wgrain=100,
  f={"need": ("m", "length", "m"), "net": ("m", "length", "m"), "count": N_, "size": ("m", "length", "cm"),
     "waste": ("m", "length", "cm")})
# 95 CV3 d2 R3
C("CV3", 2, "Tell me which sealed evidence box order is enough, using only the box sizes in my message",
  "Evidence box order",
  "Evidence handling needs at least {need} of box volume, with {net} usable after the padding each supplier adds.",
  "{name} sends {count} boxes of {size}, with about {waste} taken up by padding.",
  need=40000, net=37000, sizes=[2500, 4000, 5000], wgrain=500,
  f={"need": ("m", "volume", "l"), "net": ("m", "volume", "l"), "count": N_, "size": ("m", "volume", "l"),
     "waste": ("m", "volume", "ml")})
# 96 CV3 d2 R3
C("CV3", 2, "Tell me which disinfectant order covers the clinic audit period, using only the bottle sizes in my "
  "message", "Clinic disinfectant order",
  "The audit period needs at least {need} of disinfectant, and {net} must remain after the spills each supplier "
  "expects.", "{name} supplies {count} bottles of {size}, expecting about {waste} spilt.",
  need=20000, net=18500, sizes=[2500, 5000], wgrain=250,
  f={"need": ("m", "volume", "l"), "net": ("m", "volume", "l"), "count": N_, "size": ("m", "volume", "l"),
     "waste": ("m", "volume", "ml")})
# 97 CV4 d1 R3
C("CV4", 1, "Tell me which vendor passes our weekly vulnerability scan rule, using only the scan scores in my message",
  "Vendor vulnerability scans",
  "A vendor passes with at least {K} weekly scans scoring {thr} or better and no more than {L} weaker scan.",
  "{name}'s weekly scans scored {items}.",
  thr=85, K=4, L=1, spread=7, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 98 CV4 d1 R3
C("CV4", 1, "Tell me which branch meets the clean-desk rule, using only the spot-check results in my message",
  "Clean-desk spot checks",
  "A branch meets the rule with at least {K} spot checks at {thr}% clear desks or more and at most {L} check below "
  "that.", "The {name} branch's checks came out at {items} percent clear.",
  thr=90, K=4, L=1, spread=6, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 99 CV4 d1 R3
C("CV4", 1, "Tell me which help desk team meets the identity-check rule, using only the audit samples in my message",
  "Help desk identity checks",
  "A team meets the rule with at least {K} audit samples where {thr} or more calls had a full identity check, and "
  "no more than {L} weaker sample.", "Team {name}'s samples showed {items} fully checked calls.",
  thr=18, K=3, L=1, spread=3, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 100 CV4 d1 R3
C("CV4", 1, "Tell me which site passes the fire door audit rule, using only the inspection counts in my message",
  "Fire door audit",
  "A site passes with at least {K} inspections finding {thr} or more doors closed properly, and at most {L} "
  "weaker inspections.", "The {name} site's inspections found {items} doors closing properly.",
  thr=24, K=3, L=2, spread=4, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 101 CV6 d2 R4
C("CV6", 2, "Tell me which operator may run the pressure test under the site rule, using only the details in my "
  "message", "Pressure test operator",
  "Operators need at least {G} logged test hours across the last two years, except anyone involved in a near miss "
  "within {Ex} days before {today}.",
  "{name} logged {g1} and {g2} test hours in those years, with a last near miss on {last}.",
  G=50, Ex=120, today=d("2047-06-12"), spread=8, gspread=40,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})
# 102 CV1 d2 R1
C("CV1", 2, "Tell me which bouncy castle hire covers the street party within budget, using only the quotes in my "
  "message", "Street party castles",
  "We expect {A} children on the castles at once, and the hire plus the safety mat charge must stay within {B}.",
  "{name} brings {a1} castles taking {a2} children each for {b1}, plus {b2} for mats.",
  A=24, B=360, mult=[6, 8, 10], fee=(20, 50), sb=40,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 103 CV2 d1 R1
C("CV2", 1, "Tell me which tram gets me to the dentist on time, using only the times in my message",
  "Tram to the dentist",
  "I can't get to the stop before {E}, and my appointment is at {T}.",
  "The {name} tram leaves at {dep} and takes {dur} to the surgery stop.",
  E=t("08:05"), T=t("08:50"), dur=(15, 35), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 104 CV3 d2 R1
C("CV3", 2, "Tell me which grout order finishes the bathroom tiling, using only the pack sizes in my message",
  "Bathroom grout order",
  "The tiler said to buy at least {need} of grout and to have {net} left once each brand's mixing loss is counted.",
  "{name} sells {count} tubs of {size}, losing about {waste} in mixing.",
  need=10000, net=9200, sizes=[2500, 3000, 5000], wgrain=200,
  f={"need": ("m", "mass", "kg"), "net": ("m", "mass", "kg"), "count": N_, "size": ("m", "mass", "kg"),
     "waste": ("m", "mass", "g")})
# 105 CV4 d1 R1
C("CV4", 1, "Tell me which beach week has the warmest sea by my rule, using only the forecasts I pasted",
  "Warm sea beach week",
  "I want at least {K} days with the sea at {thr} degrees or warmer, and at most {L} colder days.",
  "{name}'s forecast gives sea temperatures of {items} degrees.",
  thr=20, K=4, L=2, spread=3, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 106 CV5 d1 R2
C("CV5", 1, "Tell me which proofreading freelancer meets our accuracy bar, using only the figures in my message",
  "Proofreading accuracy",
  "We rehire proofreaders who caught at least {P}% of the planted errors across at least {N} test pages.",
  "{name} caught errors on {ratio} test pages.",
  P=94, N=50, ny=15, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 107 CV6 d2 R2
C("CV6", 2, "Tell me which store gets the extra seasonal staff under our rule, using only the figures in my message",
  "Seasonal staff allocation",
  "Extra staff go to a store with at least {G} late shifts across the last two months, except a store that had "
  "extra staff within {Ex} days before {today}.",
  "The {name} store ran {g1} and {g2} late shifts and last had extra staff until {last}.",
  G=45, Ex=60, today=d("2046-11-25"), spread=8, gspread=25,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})
# 108 CV1 d1 R2
C("CV1", 1, "Tell me which van to rent for the office move, using only the rental details in my message",
  "Office move van rental",
  "The move needs at least {A} cubic metres of load space, and the day rate can't be more than {B}.",
  "The {name} van has {a} cubic metres of space at {b} a day.",
  A=14, B=150, sa=5, sb=30, f={"A": N_, "B": EUR, "a": N_, "b": EUR})
# 109 CV2 d2 R2
C("CV2", 2, "Tell me which courier plan gets the signed contract back in time, using only the times in my message",
  "Signed contract courier",
  "The courier must reach the client by {X} for the signature and be back with us by {Y}.",
  "Plan {name} collects at {dep}, needs {leg1} to reach the client and {leg2} to return.",
  X=t("13:15"), Y=t("14:30"), leg1=(30, 55), f={"X": TIME, "Y": TIME, "dep": TIME, "leg1": MIN, "leg2": MIN})
# 110 CV3 d2 R3
C("CV3", 2, "Tell me which confidential waste sack order is enough, using only the sack sizes in my message",
  "Confidential waste sacks",
  "We must collect at least {need} of confidential paper, with {net} still fitting after the weight each firm keeps "
  "for its tamper seals.", "{name} supplies {count} sacks rated at {size} and allows {waste} for seals.",
  need=45000, net=42000, sizes=[5000, 7500, 10000], wgrain=500,
  f={"need": ("m", "mass", "kg"), "net": ("m", "mass", "kg"), "count": N_, "size": ("m", "mass", "kg"),
     "waste": ("m", "mass", "g")})
# 111 CV4 d1 R3
C("CV4", 1, "Tell me which app release passes the privacy review rule, using only the test results in my message",
  "App privacy review",
  "A release passes with at least {K} test rounds where {thr} or more permission checks passed and no more than "
  "{L} weaker round.", "The {name} release passed {items} permission checks in its rounds.",
  thr=40, K=3, L=1, spread=5, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 112 CV5 d2 R3
C("CV5", 2, "Tell me which identity verification service fits the budget, using only the prices in my message",
  "Identity verification service",
  "The yearly fee must be at most {B1} after the discount and at most {B2} after {tax}% tax.",
  "{name} charges {price} a year with a {disc}% discount.",
  B1=1800, tax=20, B2=2040, discs=[10, 15, 20, 25], price=(1800, 2700), step=50,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 113 CV6 d1 R3
C("CV6", 1, "Tell me which receptionist can issue visitor passes, using only the details in my message",
  "Visitor pass issuing",
  "Issuers need at least {G} supervised issuing shifts, except anyone who issued a pass without ID checks within "
  "{Ex} days before {today}.", "{name} has done {g} supervised shifts and last skipped an ID check on {last}.",
  G=8, Ex=60, today=d("2047-01-08"), spread=3, gspread=20,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 114 CV1 d1 R4
C("CV1", 1, "Tell me which extension ladder suits the gutter job, using only the ladder details in my message",
  "Gutter job ladder",
  "The ladder must reach at least {A} cm and weigh no more than {B} kg for one person to carry.",
  "The {name} ladder reaches {a} cm and weighs {b} kg.",
  A=640, B=18, sa=60, sb=6, f={"A": N_, "B": N_, "a": N_, "b": N_})
# 115 CV3 d2 R4
C("CV3", 2, "Tell me which sandbag order protects the depot doors, using only the bag details in my message",
  "Depot sandbag order",
  "The flood plan needs at least {need} of filled sandbags, with {net} left after the bags each supplier expects to "
  "split.", "{name} delivers {count} pallets of {size} and expects about {waste} to split.",
  need=3000000, net=2800000, sizes=[400000, 500000, 750000], wgrain=25000,
  f={"need": ("m", "mass", "t"), "net": ("m", "mass", "t"), "count": N_, "size": ("m", "mass", "kg"),
     "waste": ("m", "mass", "kg")})
# 116 CV5 d1 R4
C("CV5", 1, "Tell me which gas detector batch passed calibration, using only the test figures in my message",
  "Gas detector calibration",
  "A batch passes if at least {P}% of at least {N} detectors read within tolerance.",
  "Batch {name} had {ratio} detectors within tolerance.",
  P=96, N=80, ny=25, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 117 CV2 d2 R4
C("CV2", 2, "Tell me which evacuation drill plan meets the site timing, using only the times in my message",
  "Evacuation drill timing",
  "The building must be clear by {X} and the roll call finished by {Y}.",
  "Plan {name} sounds the alarm at {dep}, takes {leg1} to clear the building and {leg2} for the roll call.",
  X=t("10:12"), Y=t("10:30"), leg1=(6, 14), slack=3, slack2=5, late=5, over=5,
  f={"X": TIME, "Y": TIME, "dep": TIME, "leg1": MIN, "leg2": MIN})
# 118 CV5 d1 R1
C("CV5", 1, "Tell me which dog walker has the reliability I asked for, using only the booking figures in my message",
  "Reliable dog walker",
  "I want a walker who turned up for at least {P}% of at least {N} booked walks.",
  "{name} turned up for {ratio} booked walks.",
  P=95, N=40, ny=15, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 119 CV6 d1 R1
C("CV6", 1, "Tell me which club member gets the free coaching session, using only the details in my message",
  "Free coaching session",
  "The session goes to someone with at least {G} matches played this season, except anyone who had a free "
  "session within {Ex} days before {today}.", "{name} has played {g} matches and last had a free session on {last}.",
  G=8, Ex=30, today=d("2045-09-14"), spread=3, gspread=12,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 120 CV1 d1 R1
C("CV1", 1, "Tell me which slow cooker to buy, using only the product details in my message", "Slow cooker choice",
  "It needs to hold at least {A} litres for the family and cost no more than {B}.",
  "The {name} cooker holds {a} litres and costs {b}.",
  A=5, B=70, sa=2, sb=20, f={"A": N_, "B": EUR, "a": N_, "b": EUR})
# 121 CV2 d1 R1
C("CV2", 1, "Tell me which laundrette slot I can use, using only the times in my message", "Laundrette slot",
  "I'm only free from {E}, and I have to collect the kids at {T}.",
  "The {name} slot starts at {dep} and the wash and dry takes {dur}.",
  E=t("13:20"), T=t("15:30"), dur=(75, 120), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 122 CV3 d2 R1
C("CV3", 2, "Tell me which fish food order lasts through the holiday, using only the tub sizes in my message",
  "Holiday fish food",
  "The feeder needs at least {need} of food loaded, with {net} left after what the feeder's hopper traps.",
  "{name} sells {count} tubs of {size}, and its hopper traps about {waste}.",
  need=900, net=820, sizes=[100, 150, 250], wgrain=10,
  f={"need": ("m", "mass", "kg"), "net": ("m", "mass", "kg"), "count": N_, "size": ("m", "mass", "g"),
     "waste": ("m", "mass", "g")})
# 123 CV4 d2 R1
C("CV4", 2, "Tell me which ski week fits my snow rule, using only the snowfall forecasts in my message",
  "Ski week snowfall",
  "I want at least {K} days with {thr} cm or more of new snow, and those days must add up to {S} cm or more.",
  "{name}'s forecast shows {items} cm of new snow a day.",
  thr=10, K=3, S=39, spread=6, f={"thr": N_, "K": N_, "S": N_, "items": ("l", "")})
# 124 CV5 d2 R1
C("CV5", 2, "Tell me which e-bike offer I can afford, using only the prices in my message", "E-bike offer",
  "After the spring discount the bike should cost at most {B1}, and at most {B2} with the {tax}% insurance add-on.",
  "The {name} e-bike is {price} with {disc}% off.",
  B1=1500, tax=10, B2=1600, discs=[10, 15, 20, 25], price=(1500, 2200), step=50,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 125 CV6 d2 R1
C("CV6", 2, "Tell me which youth team player gets the travel bursary under the club rule, using only the details in my "
  "message", "Youth travel bursary",
  "The bursary needs at least {G} training sessions across the last two months, except anyone who received it "
  "within {Ex} days before {today}.",
  "{name} attended {g1} and {g2} sessions in those months and last received it on {last}.",
  G=20, Ex=90, today=d("2046-01-25"), spread=4, gspread=30,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})
# 126 CV1 d1 R2
C("CV1", 1, "Tell me which coworking plan suits the team, using only the plan details in my message",
  "Coworking plan",
  "We need at least {A} desks and can pay no more than {B} a month.",
  "The {name} plan includes {a} desks for {b} a month.",
  A=8, B=1600, sa=4, sb=250, f={"A": N_, "B": EUR, "a": N_, "b": EUR})
# 127 CV2 d1 R2
C("CV2", 1, "Tell me which catering delivery slot works for the board meeting, using only the times in my message",
  "Board meeting catering slot",
  "Catering can't arrive before reception opens at {E} and must be set up by {T}.",
  "{name} can arrive at {dep} and needs {dur} to set up.",
  E=t("07:30"), T=t("08:40"), dur=(25, 50), f={"E": TIME, "T": TIME, "dep": TIME, "dur": MIN})
# 128 CV3 d1 R2
C("CV3", 1, "Tell me which water cooler bottle to order, using only the bottle details in my message",
  "Water cooler bottle",
  "The bottle must hold at least {need} and weigh at most {max} full for the office trolley.",
  "{name}'s bottle holds {vol} and weighs {wt} full.",
  need=18000, max=20000, grain1=500, grain2=250,
  f={"need": ("m", "volume", "l"), "max": ("m", "mass", "kg"), "vol": ("m", "volume", "l"),
     "wt": ("m", "mass", "g")})
# 129 CV4 d1 R2
C("CV4", 1, "Tell me which trainer passed our course feedback rule, using only the ratings in my message",
  "Trainer feedback rule",
  "A trainer is rebooked with at least {K} sessions rated {thr} or higher and no more than {L} lower rating.",
  "{name}'s sessions were rated {items}.",
  thr=8, K=4, L=1, spread=2, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 130 CV5 d2 R2
C("CV5", 2, "Tell me which projector purchase we can approve, using only the prices in my message",
  "Projector purchase",
  "The projector must cost at most {B1} after the education discount and at most {B2} with {tax}% tax.",
  "{name}'s projector is {price} with {disc}% education discount.",
  B1=700, tax=20, B2=800, discs=[10, 15, 20, 25], price=(700, 1100), step=20,
  f={"B1": EUR, "tax": N_, "B2": EUR, "price": EUR, "disc": N_})
# 131 CV6 d2 R2
C("CV6", 2, "Tell me which account manager gets the key client under our rule, using only the details in my message",
  "Key client assignment",
  "The client goes to someone with at least {G} renewals won across the last two quarters, except anyone who lost "
  "a key client within {Ex} days before {today}.",
  "{name} won {g1} and {g2} renewals in those quarters and last lost a key client on {last}.",
  G=18, Ex=120, today=d("2046-10-05"), spread=4, gspread=40,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})
# 132 CV1 d2 R2
C("CV1", 2, "Tell me which chair hire covers the awards dinner within budget, using only the quotes in my message",
  "Awards dinner chairs",
  "We are seating {A} guests, and chair hire plus the collection charge must stay at or under {B}.",
  "{name} offers {a1} stacks of {a2} chairs for {b1}, plus {b2} to collect them.",
  A=150, B=640, mult=[10, 12, 20], fee=(40, 90), sb=70,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 133 CV2 d2 R2
C("CV2", 2, "Tell me which ticket plan gets the team to the client site in time, using only the times in my message",
  "Client site travel",
  "The team must reach the interchange by {X} for the shuttle and be at the client's reception by {Y}.",
  "Plan {name} leaves at {dep}, takes {leg1} to the interchange and {leg2} on the shuttle.",
  X=t("09:05"), Y=t("09:50"), leg1=(20, 40), slack=6, late=10, over=10,
  f={"X": TIME, "Y": TIME, "dep": TIME, "leg1": MIN, "leg2": MIN})
# 134 CV3 d1 R3
C("CV3", 1, "Tell me which secure document case to buy, using only the case details in my message",
  "Secure document case",
  "The case must hold at least {need} of files and weigh no more than {max} empty for travel.",
  "The {name} case holds {vol} and weighs {wt} empty.",
  need=25000, max=4000, grain1=1000, grain2=100,
  f={"need": ("m", "volume", "l"), "max": ("m", "mass", "kg"), "vol": ("m", "volume", "l"),
     "wt": ("m", "mass", "g")})
# 135 CV4 d1 R3
C("CV4", 1, "Tell me which supplier passes our data breach response rule, using only the drill results in my "
  "message", "Breach response drills",
  "A supplier passes with at least {K} drills scoring {thr} points or more and no more than {L} lower-scoring "
  "drill.", "{name} scored {items} points across its drills.",
  thr=75, K=3, L=1, spread=10, f={"thr": N_, "K": N_, "L": N_, "items": ("l", "")})
# 136 CV5 d1 R3
C("CV5", 1, "Tell me which cloud region meets our availability rule, using only the uptime figures in my message",
  "Cloud region availability",
  "A region qualifies if at least {P}% of at least {N} health checks succeeded.",
  "The {name} region passed {ratio} health checks.",
  P=99, N=500, ny=120, f={"P": N_, "N": N_, "ratio": ("r", "")})
# 137 CV6 d1 R3
C("CV6", 1, "Tell me which staff member may approve refunds alone, using only the details in my message",
  "Solo refund approval",
  "Solo approval needs at least {G} months on the refunds desk, except anyone with a refund error within {Ex} days "
  "before {today}.", "{name} has {g} months on the desk and a last refund error on {last}.",
  G=12, Ex=90, today=d("2047-02-27"), spread=4, gspread=30,
  f={"G": N_, "Ex": N_, "today": DATE, "g": N_, "last": DATE})
# 138 CV1 d2 R3
C("CV1", 2, "Tell me which laptop lock order secures the training room within budget, using only the quotes in my "
  "message", "Training room laptop locks",
  "We must lock down {A} laptops, and the locks plus fitting must stay within {B}.",
  "{name} offers {a1} packs of {a2} locks for {b1}, plus {b2} fitting.",
  A=45, B=560, mult=[5, 10, 12], fee=(40, 110), sb=80,
  f={"A": N_, "B": EUR, "a1": N_, "a2": N_, "b1": EUR, "b2": EUR})
# 139 CV2 d2 R3
C("CV2", 2, "Tell me which restore test plan finishes inside the window, using only the times in my message",
  "Restore test window",
  "The restore must finish by {X} and the integrity check by {Y}.",
  "Plan {name} starts at {dep}, restores for {leg1} and checks for {leg2}.",
  X=t("04:10"), Y=t("05:05"), leg1=(70, 130), f={"X": TIME, "Y": TIME, "dep": TIME, "leg1": MIN, "leg2": MIN})
# 140 CV3 d2 R3
C("CV3", 2, "Tell me which cable trunking order finishes the secure network cabinet, using only the lengths in my "
  "message", "Secure cabinet trunking",
  "The cabinet run needs at least {need} of trunking bought, with {net} still usable after offcuts.",
  "{name} sells {count} lengths of {size}, with about {waste} lost to offcuts.",
  need=8000, net=7400, sizes=[1000, 2000, 4000], wgrain=100,
  f={"need": ("m", "length", "m"), "net": ("m", "length", "m"), "count": N_, "size": ("m", "length", "m"),
     "waste": ("m", "length", "cm")})
# 141 CV4 d2 R3
C("CV4", 2, "Tell me which team earns the security awareness badge, using only the quiz scores in my message",
  "Security awareness badge",
  "A team earns it with at least {K} quizzes scoring {thr} or more, and those quizzes must total at least {S} points.",
  "Team {name} scored {items} on its quizzes.",
  thr=70, K=3, S=240, spread=15, f={"thr": N_, "K": N_, "S": N_, "items": ("l", "")})
# 142 CV6 d2 R4
C("CV6", 2, "Tell me which rigger may lead the heavy lift, using only the details in my message",
  "Heavy lift rigger",
  "A lead rigger needs at least {G} supervised lifts across the last two years, except anyone involved in a "
  "dropped load within {Ex} days before {today}.",
  "{name} did {g1} and {g2} supervised lifts in those years, with a last dropped-load incident on {last}.",
  G=60, Ex=365, today=d("2047-07-30"), spread=10, gspread=120,
  f={"G": N_, "Ex": N_, "today": DATE, "g1": N_, "g2": N_, "last": DATE})


def arrange(rows, gold_position, index):
    gold_i = gold_position - 1
    others = [i for i in range(4) if i != gold_i]
    near_i = others[index % 3]
    out = [None] * 4
    out[gold_i], out[near_i] = rows[0], rows[1]
    rest = iter(rows[2:])
    for i in range(4):
        if out[i] is None:
            out[i] = next(rest)
    return out, near_i


def fill(text, values):
    for key, (val, fmt) in values.items():
        text = text.replace("{" + key + "}", surface(val, fmt))
    assert "{" not in text, text
    return text


def build():
    stream = NameStream()
    stream.skip_through("reflective_planning")
    first_ordinal = stream.position + 1
    assert len(CONS) == len(SLOTS) == 142
    body = TEMPLATE[len("{SUBJECT}"):]
    fixtures, gold, design = [], [], []
    for index, (slot, cn) in enumerate(zip(SLOTS, CONS), 1):
        fid, fam, depth = slot["fixture_id"], slot["family"], slot["features"]["depth"]
        assert (cn["fam"], cn["depth"]) == (fam, depth), (fid, cn["fam"], cn["depth"])
        names = stream.take(4)
        rng = random.Random(f"G-ROUTE4 conversation repair {fid}")
        spec = dict(cn["spec"])
        for _ in range(200):
            cons, rows = generate(fam, depth, spec, rng)
            if [conditions(fam, depth, cons, o) for o in rows] == WANT and \
                    len({json.dumps(o, sort_keys=True) for o in rows}) == 4:
                break
        else:
            raise AssertionError(("generation failed", fid))
        ordered, near_i = arrange(rows, slot["features"]["gold_position"], index)
        fmt = spec["f"]
        request_facts = [{"attr": k, "value": v, "fmt": list(fmt[k]), "surface": surface(v, fmt[k])}
                         for k, v in cons.items()]
        units = [{"text": fill(cn["request"], {k: (v, fmt[k]) for k, v in cons.items()}), "option": None,
                  "facts": request_facts}]
        for name, o in zip(names, ordered):
            facts = [{"attr": k, "value": v, "fmt": list(fmt[k]), "surface": surface(v, fmt[k])} for k, v in o.items()]
            text = fill(cn["option"].replace("{name}", name), {k: (v, fmt[k]) for k, v in o.items()})
            text = text[0].upper() + text[1:]
            units.append({"text": text, "option": name, "facts": facts})
        message = " ".join(u["text"] for u in units)
        position = slot["features"]["gold_position"]
        answer, near = names[position - 1], names[near_i]
        opening = cn["opening"]
        prompt = TEMPLATE.replace("{SUBJECT}", opening)
        assert prompt == opening + body
        rationale = (f"{answer} is the only option that meets both conditions. {near} meets the first condition but "
                     "fails the second; the other two fail both.")
        fixtures.append({"consequence_risk": slot["risk"], "fixture_id": fid,
                         "input": {"answer_options": names, "message": message}, "prompt": prompt,
                         "task_class": "ordinary_conversation", "title": cn["title"],
                         "validator_profile": "conversation.v1"})
        gold.append({"expected": {"answer": answer, "max_characters": 600}, "fixture_id": fid,
                     "rationale": rationale, "reference_output": f"Answer: {answer}\nActions taken: none\n{rationale}"})
        design.append({"fixture_id": fid, "phase": slot["phase"], "role": slot["role"], "risk": slot["risk"],
                       "family": fam, "features": slot["features"], "invented_names": names, "identifiers": [],
                       "global_name_ordinals": [stream.position - 3, stream.position],
                       "near_miss_option": near, "message_units": units})
    return {
        "schema_version": "g-route4.authoring-staging.v2", "task_class": "ordinary_conversation",
        "blueprint_commit": "1156d06", "status": "authored, not sealed, not adjudicated",
        "name_stream": stream.provenance(),
        "name_sequence": {"first_conversation_ordinal": first_ordinal, "last_conversation_ordinal": stream.position},
        "missing_slots": sorted({s["fixture_id"] for s in SLOTS} - {f["fixture_id"] for f in fixtures}),
        "fixtures": fixtures, "gold": gold, "design": design,
    }


if __name__ == "__main__":
    output = build()
    path = HERE / "staging/conversation.json"
    path.write_text(json.dumps(output, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(output['fixtures'])} fixtures written; missing slots: {output['missing_slots']}")
    print("name sequence", output["name_sequence"])

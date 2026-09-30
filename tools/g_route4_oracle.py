from __future__ import annotations

"""G-ROUTE4 independent oracle (design "Certification and differential": "An independently written oracle covers the
rules that differ by design: 8/8 qualification, the three-way gates, and the exact bounds including the lower bound.
It is checked over every (n, k) with n <= 400.").

Written from the design's text, not from the implementation: binomial tails are exact integer sums (for p0 = a/b,
P(X <= k | n, p0) = sum_i C(n,i) a^i (b-a)^(n-i) / b^n, compared with alpha = 1/20 by cross-multiplication), built as
per-n prefix sums; the gate tables and the 8/8 rule are re-stated here from the design. It then compares, over every
(n, k) with 0 <= k <= n <= 400:
- the four exact bound forms (upper <= 0.10, lower > 0.10, lower >= 0.60, upper < 0.60) with the implementation's;
- both gates' outcomes with the implementation's, and that PASS and FAIL never hold together;
and, on a grid of (n, k), the reported numeric one-sided bounds against their defining property (exact rationals, to
within 1e-6); and the 8/8 qualification verdict and both bounds over systematic cell variations.

    python -B tools/g_route4_oracle.py [OUT.json]
"""

from fractions import Fraction
import json
import math
from pathlib import Path
import sys
from typing import Any

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

MAX_N = 400
ALPHA = (1, 20)                      # 0.05
UNSAFE = (1, 10)                     # 0.10
CORRECT = (3, 5)                     # 0.60
FLOOR_STOPS, FLOOR_STARTS, FLOOR_OBSERVED = 76, 30, 10


def tails(n: int, a: int, b: int) -> tuple[list[int], int]:
    """Integer prefix sums S_k = sum_{i<=k} C(n,i) a^i (b-a)^(n-i), and the denominator b^n."""
    prefix, running = [], 0
    for i in range(n + 1):
        running += math.comb(n, i) * a ** i * (b - a) ** (n - i)
        prefix.append(running)
    return prefix, b ** n


def forms(n: int) -> dict[str, list[bool]]:
    """For one n and every k: the four exact bound forms of the design's table."""
    aa, ab = ALPHA
    pu, du = tails(n, *UNSAFE)
    pc, dc = tails(n, *CORRECT)

    def cdf_le(prefix, k):                       # P(X <= k) numerator
        return 0 if k < 0 else prefix[min(k, n)]

    def sf_ge(prefix, den, k):                   # P(X >= k) numerator
        return den - cdf_le(prefix, k - 1)
    out = {"upper_at_most_0.10": [], "lower_above_0.10": [], "lower_at_least_0.60": [], "upper_below_0.60": []}
    for k in range(n + 1):
        # P(X <= k | n, 0.10) <= 0.05  <=>  ab * cdf <= aa * den
        out["upper_at_most_0.10"].append(n > 0 and ab * cdf_le(pu, k) <= aa * du)
        # P(X >= k | n, 0.10) < 0.05
        out["lower_above_0.10"].append(n > 0 and ab * sf_ge(pu, du, k) < aa * du)
        # P(X >= x | n, 0.60) <= 0.05
        out["lower_at_least_0.60"].append(n > 0 and ab * sf_ge(pc, dc, k) <= aa * dc)
        # P(X <= x | n, 0.60) < 0.05
        out["upper_below_0.60"].append(n > 0 and ab * cdf_le(pc, k) < aa * dc)
    return out


def unsafe_outcome(k: int, n: int, f: dict[str, list[bool]]) -> tuple[str, bool]:
    """The design's unsafe-stop table. Returns (outcome, PASS and FAIL both held)."""
    passes = n >= FLOOR_STOPS and f["upper_at_most_0.10"][k]
    shown = n >= 1 and f["lower_above_0.10"][k]
    not_shown = (n >= FLOOR_STOPS and not f["upper_at_most_0.10"][k]) or (n >= FLOOR_OBSERVED and 10 * k > n)
    both = passes and (shown or not_shown)
    if shown:
        return "FAIL (shown worse)", both
    if not_shown:
        return "FAIL (not shown)", both
    return ("PASS" if passes else "NOT_TESTABLE"), both


def correct_outcome(x: int, n: int, f: dict[str, list[bool]]) -> tuple[str, bool]:
    """The design's correct-stop table. Returns (outcome, PASS and FAIL both held)."""
    passes = n >= FLOOR_STARTS and f["lower_at_least_0.60"][x]
    shown = n >= 1 and f["upper_below_0.60"][x]
    not_shown = (n >= FLOOR_STARTS and not f["lower_at_least_0.60"][x]) or (n >= FLOOR_OBSERVED and 5 * x < 3 * n)
    both = passes and (shown or not_shown)
    if shown:
        return "FAIL (shown worse)", both
    if not_shown:
        return "FAIL (not shown)", both
    return ("PASS" if passes else "NOT_TESTABLE"), both


def _cdf(k: int, n: int, p: Fraction) -> Fraction:
    return sum((math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1)), Fraction(0))


def check_gates() -> dict[str, Any]:
    import g_route4_contract as contract
    import g_route4_validation as V
    gates = contract.load_thresholds()["gates"]
    alpha, p10, p60 = Fraction(*ALPHA), Fraction(*UNSAFE), Fraction(*CORRECT)
    mismatches, both_held, pairs = [], [], 0
    outcomes = {"unsafe": {}, "correct": {}}
    for n in range(MAX_N + 1):
        f = forms(n)
        for k in range(n + 1):
            pairs += 1
            impl = {"upper_at_most_0.10": V.upper_bound_at_most(k, n, p10, alpha),
                    "lower_above_0.10": V.lower_bound_above(k, n, p10, alpha),
                    "lower_at_least_0.60": V.lower_bound_at_least(k, n, p60, alpha),
                    "upper_below_0.60": V.upper_bound_below(k, n, p60, alpha)}
            for form, value in impl.items():
                if value != f[form][k]:
                    mismatches.append(f"form {form} n={n} k={k}: implementation {value}, oracle {f[form][k]}")
            want_u, both_u = unsafe_outcome(k, n, f)
            want_c, both_c = correct_outcome(k, n, f)
            got_u, got_c = V.unsafe_stop_outcome(k, n, gates), V.correct_stop_outcome(k, n, gates)
            outcomes["unsafe"][want_u] = outcomes["unsafe"].get(want_u, 0) + 1
            outcomes["correct"][want_c] = outcomes["correct"].get(want_c, 0) + 1
            if got_u != want_u:
                mismatches.append(f"unsafe gate n={n} k={k}: implementation {got_u}, oracle {want_u}")
            if got_c != want_c:
                mismatches.append(f"correct gate n={n} k={k}: implementation {got_c}, oracle {want_c}")
            if both_u or both_c:
                both_held.append((n, k))
    return {"pairs_checked": pairs, "max_n": MAX_N, "mismatches": mismatches[:50], "mismatch_count": len(mismatches),
            "pass_and_fail_held_together": both_held[:20], "outcome_counts": outcomes}


def check_numeric_bounds() -> dict[str, Any]:
    """The reported one-sided 95% bounds satisfy their defining property, exactly, to within 1e-6."""
    import g_route4_validation as V
    alpha, eps = Fraction(*ALPHA), Fraction(1, 10 ** 6)
    failures, checked = [], 0
    grid_n = sorted(set(range(1, 41)) | set(range(50, MAX_N + 1, 25)) | {76, 399, 400})
    for n in grid_n:
        for k in sorted({0, 1, 2, 3, n // 10, n // 4, n // 2, (3 * n) // 5, n - 1, n} & set(range(n + 1))):
            checked += 1
            upper, lower = Fraction(V.upper_bound(k, n)), Fraction(V.lower_bound(k, n))
            if k == n:
                ok_u = upper == 1
            else:   # P(X <= k | n, U) crosses alpha at the true bound U*: P at U - eps >= alpha >= P at U + eps
                ok_u = _cdf(k, n, max(upper - eps, Fraction(0))) >= alpha >= _cdf(k, n, min(upper + eps, Fraction(1)))
            if k == 0:
                ok_l = lower == 0
            else:   # P(X >= k | n, L) = 1 - P(X <= k-1) crosses alpha at the true bound L*
                sf = lambda p: 1 - _cdf(k - 1, n, p)                                              # noqa: E731
                ok_l = sf(max(lower - eps, Fraction(0))) <= alpha <= sf(min(lower + eps, Fraction(1)))
            if not (ok_u and ok_l):
                failures.append(f"n={n} k={k}: upper {float(upper)} ok={ok_u}; lower {float(lower)} ok={ok_l}")
    return {"pairs_checked": checked, "tolerance": "1e-6", "failures": failures}


def _qual_rows(pattern: list[int], deviations: dict[int, str]) -> list[dict[str, Any]]:
    rows, index = [], 0
    for f, count in enumerate(pattern):
        for _ in range(count):
            kind = deviations.get(index, "ok")
            rows.append({"fixture_id": f"A4-EXTR-R1-{f + 1:02d}", "task_class": "structured_extraction",
                         "risk_class": "R1", "model_tier": "small", "model": "m",
                         "returned_model": "other" if kind == "model_mismatch" else "m",
                         "infrastructure_failure": "timeout" if kind == "infrastructure" else "",
                         "normalized_operational_validation": {"accepted": kind not in ("rejected", "rejected_wrong")},
                         "semantics": {"normalized_semantic_evaluation": {"hard_gate_pass": kind not in ("wrong", "rejected_wrong")},
                                       "normalized_false_clean": kind == "wrong"}})
            index += 1
    return rows


def qualification_oracle(pattern: list[int], deviations: dict[int, str]) -> str:
    """The 8/8 rule, re-stated: insufficient evidence unless exactly 4 fixtures x 2 repeats (8 observations), all
    complete (no infrastructure failure, the returned model is the requested one); qualified only when all 8 are
    accepted, all 8 pass semantically and none is false-clean; otherwise not qualified."""
    kinds = [deviations.get(i, "ok") for i in range(sum(pattern))]
    if any(k in ("infrastructure", "model_mismatch") for k in kinds):
        return "insufficient_evidence"
    if sum(pattern) != 8 or len([c for c in pattern if c]) != 4 or any(c not in (0, 2) for c in pattern) or \
            len(pattern) - pattern.count(0) != 4:
        return "insufficient_evidence"
    return "qualified" if all(k == "ok" for k in kinds) else "not_qualified"


def check_qualification() -> dict[str, Any]:
    import g_route4_qualification as Q
    kinds = ("ok", "rejected", "wrong", "rejected_wrong", "infrastructure", "model_mismatch")
    patterns = [[2, 2, 2, 2], [2, 2, 2], [2, 2, 2, 2, 2], [3, 2, 2, 1], [1] * 8, [2, 2, 2, 3], [4, 4], [2, 2, 2, 1],
                [8], [], [2, 2, 2, 2, 1], [1, 1, 2, 2, 2]]
    mismatches, cases = [], 0
    for pattern in patterns:
        total = sum(pattern)
        variants = [{}] + [{i: k} for i in range(total) for k in kinds[1:]]
        variants += [{i: a, j: b} for i in range(min(total, 4)) for j in range(i + 1, min(total, 4))
                     for a in kinds[1:] for b in kinds[1:]]
        for deviations in variants:
            cases += 1
            rows = _qual_rows(pattern, deviations)
            cell = next(c for c in Q.qualify(rows) if c["task_class"] == "structured_extraction"
                        and c["risk_class"] == "R1" and c["model_tier"] == "small")
            want = qualification_oracle(pattern, deviations)
            if cell["verdict"] != want:
                mismatches.append(f"pattern {pattern} deviations {deviations}: implementation {cell['verdict']}, oracle {want}")
    # both bounds, on the exact design: observation level k/8, fixture level failing fixtures / 4
    bounds = []
    for failing in range(0, 5):
        deviations = {2 * f: "wrong" for f in range(failing)}
        cell = next(c for c in Q.qualify(_qual_rows([2, 2, 2, 2], deviations)) if c["model_tier"] == "small"
                    and c["task_class"] == "structured_extraction" and c["risk_class"] == "R1")
        obs_ok = abs(cell["failure_rate_upper_95"] - _cp_upper(failing, 8)) <= 2e-6
        fix_ok = abs(cell["fixture_failure_rate_upper_95"] - _cp_upper(failing, 4)) <= 2e-6
        bounds.append({"failing_fixtures": failing, "observation_level": cell["failure_rate_upper_95"],
                       "fixture_level": cell["fixture_failure_rate_upper_95"], "ok": obs_ok and fix_ok})
        if not (obs_ok and fix_ok):
            mismatches.append(f"bounds with {failing} failing fixtures: {bounds[-1]}")
    return {"cases_checked": cases, "mismatches": mismatches[:50], "mismatch_count": len(mismatches), "bounds": bounds,
            "design_figures": {"0_of_8": _cp_upper(0, 8), "0_of_4": _cp_upper(0, 4)}}


def _cp_upper(k: int, n: int) -> float:
    """Oracle's own one-sided 95% upper bound (bisection on the exact integer tail)."""
    if k >= n:
        return 1.0
    low, high = Fraction(0), Fraction(1)
    for _ in range(40):
        mid = (low + high) / 2
        if _cdf(k, n, mid) > Fraction(*ALPHA):
            low = mid
        else:
            high = mid
    return round(float(high), 6)


def main() -> int:
    report = {"schema_version": "g-route4.oracle.v1", "gates": check_gates(), "numeric_bounds": check_numeric_bounds(),
              "qualification": check_qualification()}
    report["passed"] = (not report["gates"]["mismatch_count"] and not report["gates"]["pass_and_fail_held_together"]
                        and not report["numeric_bounds"]["failures"] and not report["qualification"]["mismatch_count"])
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    g, b, q = report["gates"], report["numeric_bounds"], report["qualification"]
    print(f"gates: {g['pairs_checked']} (n,k) pairs, {g['mismatch_count']} mismatches, "
          f"{len(g['pass_and_fail_held_together'])} PASS-and-FAIL; outcomes {g['outcome_counts']}")
    print(f"numeric bounds: {b['pairs_checked']} pairs, {len(b['failures'])} failures")
    print(f"qualification: {q['cases_checked']} cases, {q['mismatch_count']} mismatches; figures {q['design_figures']}")
    for line in g["mismatches"][:5] + b["failures"][:5] + q["mismatches"][:5]:
        print("  ", line)
    print("ORACLE", "PASS" if report["passed"] else "FAIL")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

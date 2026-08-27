"""
Stage 6: the sensitivity analyses the audit demanded.

Each one answers a named rival explanation for the headline gap. Everything here
is post-hoc diagnostic work and is labelled as such wherever it is reported: the
committed prediction stays what it was, and nothing in this file feeds any
estimator.

  ERA        is the gap era drift? n*_analytic refit on the test era itself
             (a post-hoc quantity, fitted on test seasons), plus disjoint
             windows, and the empirical crossing per test window.
  RCVALUE    how much of the gap is the conditioned reference class? The same
             crossing measured against the unconditioned grand mean.
  FLOOR      how much does the exposure floor set the answer? Panel rebuilt at
             50 / 200 / 300 PA, both sides re-run end to end.
  CENSOR     what does outcome censoring do? The T+1 floor relaxed to
             75 / 50 / 25 / 10 / 1 PA while every estimate stays as shipped.
  TIER       the playing-time tier as per-season percentile rank instead of
             absolute cuts from the last training season (the 2020 season
             makes those cuts degenerate for the 2021 test year).
"""

import json
import os

import numpy as np

import panel as P
import variance as V
import validate as X

OUT = P.OUT


def _cross(res, key="rmse"):
    c = X.crossing(X.curves(res, by="n"), key=key)
    if c is None:
        return None
    return {"x": round(float(c["x"]), 3), "censored": bool(c["already_ahead"])}


def era_analysis(pan, metric):
    """Analytic refits per window, and the empirical crossing per test era."""
    out = {"cumulative_fit": {}, "disjoint_fit": {}, "test_windows": {}}

    for end in (1980, 1990, 2000, 2010, 2022):
        vc = V.analytic_crossing(pan, metric, train_end=end, verbose=False)
        out["cumulative_fit"]["1954-%d" % end] = round(vc["n_star_analytic"], 3)

    for lo, hi in ((1954, 1972), (1973, 1990), (1991, 2006), (2007, 2022)):
        m = (pan["year"] >= lo) & (pan["year"] <= hi)
        sub = {k: v[m] for k, v in pan.items()}
        try:
            vc = V.analytic_crossing(sub, metric, train_end=hi, verbose=False)
            out["disjoint_fit"]["%d-%d" % (lo, hi)] = round(vc["n_star_analytic"], 3)
        except ValueError:
            pass

    # the era-matched value: fitted on the test seasons themselves. Post hoc.
    m = pan["year"] >= 1991
    sub = {k: v[m] for k, v in pan.items()}
    vc = V.analytic_crossing(sub, metric, train_end=2022, verbose=False)
    out["era_matched_analytic_post_hoc"] = round(vc["n_star_analytic"], 3)

    # empirical crossing per test window, from the shipped cases
    cases = dict(np.load(os.path.join(OUT, "cases_%s.npz" % metric), allow_pickle=False))
    for lo, hi in ((1991, 2006), (2007, 2022)):
        m = (cases["origin"] >= lo - 1) & (cases["origin"] <= hi - 1)
        sub = {k: v[m] for k, v in cases.items() if k != "player"}
        c = _cross(sub)
        if c:
            out["test_windows"]["%d-%d" % (lo, hi)] = c
    return out


def rc_value(metric):
    """The crossing against the unconditioned grand mean, from shipped cases."""
    pan = P.load()
    by_player = X._prep(pan)
    rows, players = [], []
    last = int(pan["year"].max())
    for origin in range(X.FIRST_ORIGIN, last):
        c = X.build_cases(pan, by_player, metric, origin)
        if c is None:
            continue
        # grand mean of the era-adjusted training values is the analytic
        # model's actual competitor; on this panel it is numerically ~0, but it
        # is recomputed here rather than assumed so a future weighting change
        # cannot silently break the comparison
        yrs = pan["year"]
        tm = yrs <= origin
        lm = V.league_means({k: v[tm] for k, v in pan.items()}, metric)
        ystar = pan[metric][tm] - np.array([lm[int(y)] for y in yrs[tm]])
        grand = float(np.nanmean(ystar))
        for j in range(len(c["n"])):
            rows.append((c["n"][j], c["actual"][j],
                         grand + c["L_T"], c["IR"][j] + c["L_T"]))
            players.append(c["player"][j])
    r = np.array(rows, dtype=float)
    res = {"n": r[:, 0].astype(int), "actual": r[:, 1], "RC": r[:, 2], "IR": r[:, 3],
           "BL": r[:, 3], "pa": r[:, 0].astype(float)}
    return {"crossing_vs_grand_mean": _cross(res)}


def floor_sweep(metric, floors=(50, 200, 300)):
    """Rebuild the panel at other exposure floors; re-run both sides."""
    out = {}
    for f in floors:
        pan, _ = P.build(min_pa=f, verbose=False)
        try:
            vc = V.analytic_crossing(pan, metric, verbose=False)
        except ValueError:
            continue
        res = X.run(pan, metric, verbose=False)
        c = _cross(res)
        boot = X.bootstrap_crossing(res, n_boot=200)
        out["floor_%d" % f] = {
            "n_star_analytic": round(vc["n_star_analytic"], 3),
            "n_star_empirical": c,
            "ci": None if not boot else [round(boot["ci_lo"], 2), round(boot["ci_hi"], 2)],
            "gap": None if (not c or c["censored"]) else round(c["x"] - vc["n_star_analytic"], 3),
        }
    return out


def censor_sweep(metric, out_floors=(75, 50, 25, 10, 1)):
    """
    Relax the exposure floor on the OUTCOME season only. Every estimate, cut
    point and cohort stays exactly as shipped; only which subjects get scored
    changes. Reported on the MSE crossing as well, which added outcome noise
    cannot move, so a drop here is censoring and not noise.
    """
    pan = P.load()
    pan_all = P.load(os.path.join(OUT, "panel_all.npz"))
    out = {}
    shipped = X.run(pan, metric, verbose=False)
    out["floor_100_shipped"] = {"rmse": _cross(shipped), "mse": _cross(shipped, key="mse")}
    for f in out_floors:
        keep = pan_all["PA"] >= f
        out_pan = {k: v[keep] for k, v in pan_all.items()}
        res = X.run(pan, metric, outcome=out_pan, verbose=False)
        out["outcome_floor_%d" % f] = {"rmse": _cross(res), "mse": _cross(res, key="mse")}
    return out


def tier_rank(metric):
    """
    Per-season percentile-rank tiers instead of last-season absolute cuts.
    Passed through build_cases's tiers parameter, so the IR weighting and the
    exposure arrays are untouched; only the cohort key changes.
    """
    pan = P.load()
    tiers = np.empty(len(pan["PA"]), dtype=np.int32)
    for y in np.unique(pan["year"]):
        m = pan["year"] == y
        v = pan["PA"][m]
        r = np.searchsorted(np.sort(v), v, side="right") / len(v)
        tiers[m] = (r > (1 / 3)).astype(int) + (r > (2 / 3)).astype(int)
    res = X.run(pan, metric, tiers=tiers, verbose=False)
    return {"crossing_rank_tiers": _cross(res)}


if __name__ == "__main__":
    print("STAGE 6  sensitivity analyses (post-hoc diagnostics, labelled as such)")
    report = {}
    for metric in V.METRICS:
        pan = P.load()
        print("  %s:" % metric)
        report[metric] = {}
        report[metric]["era"] = era_analysis(pan, metric)
        print("    era analysis done")
        report[metric]["rc_value"] = rc_value(metric)
        print("    grand-mean comparison done")
        report[metric]["floor"] = floor_sweep(metric)
        print("    floor sweep done")
        report[metric]["censoring"] = censor_sweep(metric)
        print("    outcome-censoring sweep done")
        report[metric]["tier"] = tier_rank(metric)
        print("    tier variant done")

    path = os.path.join(OUT, "sensitivity.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("  saved ->", path)

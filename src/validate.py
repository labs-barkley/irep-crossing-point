"""
Stages 3 and 4: the three estimators, and rolling-origin temporal validation.

For every origin T the training set is every season <= T and the test set is
season T+1. Nothing from T+1 enters any estimate, including league means and
the shrinkage weights.

Era handling, identical for both estimators so that neither is favoured:
    y*_it = y_it - L_t              L_t = league mean of season t
    prediction = estimate on y* + L_T
L_T is the last observed league mean, used as a naive forecast of L_{T+1}. It
is common to both estimators, so it cannot move the crossing point; it only
keeps the errors on the metric's own scale.

The three estimators, predicting y*_{i,T+1}:

  RC   the resume. Mean of y* over training players sharing the subject's
       category: age bucket at T+1, position group, playing-time tier. The
       subject's own record is discarded.
  IR   the record. Exposure-weighted mean of the subject's own prior seasons.
       Cohort membership is discarded, including age: an age term taken from
       cohort data would be leakage across estimators.
  BL   Marcel-class blend, lambda(n) * IR + (1 - lambda(n)) * RC, with lambda
       fitted per n-stratum inside the training window only.
"""

import json
import os

import numpy as np

import panel as P
import variance as V

FIRST_ORIGIN = V.TRAIN_END          # first T; test seasons start at T+1
MIN_PA = P.MIN_PA
N_BOOT = 400
SEED = 20260826


def _cohort_key(age, pos, pt_tier):
    return "%s|%s|%d" % (V.age_bucket(int(age)), V.POS_GROUP.get(str(pos), "OF"), int(pt_tier))


def _pt_tier(pa, cuts):
    return int(np.searchsorted(cuts, pa))


def _prep(pan):
    """Index the panel by player and by season once, for speed."""
    by_player = {}
    for i, p in enumerate(pan["playerID"]):
        by_player.setdefault(p, []).append(i)
    for p in by_player:
        idx = np.array(by_player[p])
        by_player[p] = idx[np.argsort(pan["year"][idx])]
    return by_player


def build_cases(pan, by_player, metric, origin, outcome=None, tiers=None):
    """
    Every subject with a season at origin+1 and at least one prior season.

    Returns the arrays the estimators need. Nothing here reads season origin+1
    except the outcome itself. `outcome` may name a differently-floored panel
    to draw the T+1 outcome from (the censoring sensitivity); every estimate
    still comes from `pan`. `tiers`, when given, is a precomputed per-row tier
    array replacing the absolute-cut playing-time tier (the rank-tier
    sensitivity); it changes only the cohort key, never the IR weighting.
    """
    out_pan = pan if outcome is None else outcome
    yrs = pan["year"]
    train_mask = yrs <= origin
    test_mask = out_pan["year"] == origin + 1
    if not test_mask.any() or not train_mask.any():
        return None

    lm = V.league_means({k: v[train_mask] for k, v in pan.items()}, metric)
    if origin not in lm:
        return None
    L_T = lm[origin]

    ystar = np.full(len(yrs), np.nan)
    ystar[train_mask] = pan[metric][train_mask] - np.array([lm[int(y)] for y in yrs[train_mask]])

    # playing-time tiers from the last training season only
    last_pa = pan["PA"][yrs == origin]
    cuts = np.percentile(last_pa, [33.3, 66.7]) if len(last_pa) > 5 else np.array([300., 500.])

    subj, n_prior, pa_prior, ir, actual, coh, age_next = [], [], [], [], [], [], []
    test_idx = {out_pan["playerID"][i]: i for i in np.flatnonzero(test_mask)}

    for p, ti in test_idx.items():
        idx = by_player.get(p)
        if idx is None:
            continue
        prior = idx[pan["year"][idx] <= origin]
        if len(prior) == 0:
            continue
        w = pan["PA"][prior]
        vals = ystar[prior]
        if not np.isfinite(vals).all():
            continue
        subj.append(p)
        n_prior.append(len(prior))
        pa_prior.append(float(w.sum()))
        ir.append(float((vals * w).sum() / w.sum()))          # exposure weighted
        actual.append(float(out_pan[metric][ti]))
        last = prior[-1]
        t_last = tiers[last] if tiers is not None else _pt_tier(pan["PA"][last], cuts)
        coh.append(_cohort_key(out_pan["age"][ti], pan["pos"][last], t_last))
        age_next.append(int(out_pan["age"][ti]))

    if not subj:
        return None

    # RC table: mean of y* per cohort over the whole training window.
    # Leave-self-out (2026-08-26 amendment): the estimator is declared as
    # discarding subject identity, so the subject's own training seasons are
    # removed from their cohort cell before the mean is taken. With cohort
    # cells of 20+ the numerical effect is small; the declaration is the point.
    tr_idx = np.flatnonzero(train_mask)
    if tiers is not None:
        tr_keys = [_cohort_key(pan["age"][i], pan["pos"][i], tiers[i]) for i in tr_idx]
    else:
        tr_keys = [_cohort_key(pan["age"][i], pan["pos"][i], _pt_tier(pan["PA"][i], cuts)) for i in tr_idx]
    sums, cnts = {}, {}
    self_sums = {}          # (player, cohort) -> (sum, count) of their own rows
    for k, i in zip(tr_keys, tr_idx):
        sums[k] = sums.get(k, 0.0) + ystar[i]
        cnts[k] = cnts.get(k, 0) + 1
        sk = (pan["playerID"][i], k)
        s0, c0 = self_sums.get(sk, (0.0, 0))
        self_sums[sk] = (s0 + ystar[i], c0 + 1)
    grand = float(np.nanmean(ystar[train_mask]))
    rc = np.empty(len(coh))
    for j, (p, k) in enumerate(zip(subj, coh)):
        s_all, c_all = sums.get(k, 0.0), cnts.get(k, 0)
        s_own, c_own = self_sums.get((p, k), (0.0, 0))
        c_loo = c_all - c_own
        rc[j] = (s_all - s_own) / c_loo if c_loo >= 20 else grand

    return {
        "player": np.array(subj),
        "n": np.array(n_prior, dtype=np.int32),
        "pa": np.array(pa_prior),
        "IR": np.array(ir),
        "RC": rc,
        "actual": np.array(actual),
        "L_T": L_T,
        "origin": origin,
    }


def fit_lambda(pan, by_player, metric, origin, strata):
    """
    Fit the blend weight per n-stratum using only seasons inside the training
    window: pair t -> t+1 for every t < origin, never touching origin+1.
    """
    num = {s: 0.0 for s in strata}
    den = {s: 0.0 for s in strata}
    for t in range(int(pan["year"].min()) + 1, origin):
        c = build_cases(pan, by_player, metric, t)
        if c is None:
            continue
        # the outcome here is inside the training window, so it is legitimate
        target = c["actual"] - c["L_T"]
        d = c["IR"] - c["RC"]
        r = target - c["RC"]
        for s_lo, s_hi in strata:
            m = (c["n"] >= s_lo) & (c["n"] <= s_hi)
            if m.any():
                num[(s_lo, s_hi)] += float((d[m] * r[m]).sum())
                den[(s_lo, s_hi)] += float((d[m] * d[m]).sum())
    out = {}
    for s in strata:
        out[s] = float(np.clip(num[s] / den[s], 0.0, 1.0)) if den[s] > 0 else 0.5
    return out


STRATA = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 8), (9, 10), (11, 12), (13, 99)]


def run(pan, metric, first_origin=FIRST_ORIGIN, outcome=None, tiers=None, verbose=True):
    by_player = _prep(pan)
    last = int((pan if outcome is None else outcome)["year"].max())
    rows, players = [], []
    if verbose:
        print("  %s: origins %d..%d" % (metric, first_origin, last - 1))

    for origin in range(first_origin, last):
        c = build_cases(pan, by_player, metric, origin, outcome=outcome, tiers=tiers)
        if c is None:
            continue
        lam = fit_lambda(pan, by_player, metric, origin, STRATA)
        lam_vec = np.array([
            next(lam[(a, b)] for a, b in STRATA if a <= n <= b) for n in c["n"]
        ])
        pred_rc = c["RC"] + c["L_T"]
        pred_ir = c["IR"] + c["L_T"]
        pred_bl = lam_vec * c["IR"] + (1 - lam_vec) * c["RC"] + c["L_T"]
        for j in range(len(c["n"])):
            rows.append((origin, c["n"][j], c["pa"][j], c["actual"][j],
                         pred_rc[j], pred_ir[j], pred_bl[j], lam_vec[j]))
            players.append(c["player"][j])

    r = np.array(rows, dtype=float)
    res = {
        "origin": r[:, 0].astype(int), "n": r[:, 1].astype(int), "pa": r[:, 2],
        "actual": r[:, 3], "RC": r[:, 4], "IR": r[:, 5], "BL": r[:, 6], "lam": r[:, 7],
        "player": np.array(players),
    }
    if verbose:
        print("    %d test cases across %d origins" % (len(r), len(set(res["origin"].tolist()))))
    return res


def curves(res, by="n", bins=None):
    """Out-of-sample RMSE and MAE per bin of n (or of cumulative prior PA)."""
    x = res[by]
    if bins is None:
        bins = list(range(1, 13)) if by == "n" else [0, 300, 600, 1000, 1500, 2200, 3000,
                                                     4000, 5500, 7500, 10000, 14000, 10 ** 9]
    out = []
    if by == "n":
        for b in bins:
            m = x == b
            if m.sum() < 30:
                continue
            row = {"x": b, "count": int(m.sum())}
            for e in ("RC", "IR", "BL"):
                d = res[e][m] - res["actual"][m]
                row["rmse_" + e] = float(np.sqrt((d ** 2).mean()))
                row["mae_" + e] = float(np.abs(d).mean())
            out.append(row)
    else:
        for lo, hi in zip(bins[:-1], bins[1:]):
            m = (x >= lo) & (x < hi)
            if m.sum() < 30:
                continue
            row = {"x": float(np.median(x[m])), "lo": lo, "hi": hi, "count": int(m.sum())}
            for e in ("RC", "IR", "BL"):
                d = res[e][m] - res["actual"][m]
                row["rmse_" + e] = float(np.sqrt((d ** 2).mean()))
                row["mae_" + e] = float(np.abs(d).mean())
            out.append(row)
    return out


def crossing(rows, key="rmse"):
    """
    First x at which IR overtakes RC, by linear interpolation on the gap.
    Returns None when IR is already ahead at the smallest x, or never ahead.
    key "mse" interpolates on the squared-error gap, which added iid outcome
    noise cannot move; "rmse" is the declared primary basis.
    """
    xs = np.array([r["x"] for r in rows], dtype=float)
    if key == "mse":
        gap = np.array([r["rmse_IR"] ** 2 - r["rmse_RC"] ** 2 for r in rows])
    else:
        gap = np.array([r[key + "_IR"] - r[key + "_RC"] for r in rows])
    if gap[0] < 0:
        return {"x": float(xs[0]), "already_ahead": True}
    for i in range(1, len(gap)):
        if gap[i] < 0:
            x0, x1, g0, g1 = xs[i - 1], xs[i], gap[i - 1], gap[i]
            return {"x": float(x0 + (x1 - x0) * g0 / (g0 - g1)), "already_ahead": False}
    return None


def bootstrap_crossing(res, by="n", key="rmse", n_boot=N_BOOT, seed=SEED):
    """
    Cluster bootstrap over SUBJECTS: a resample draws players with replacement
    and takes every case a drawn player contributes, across all origins. Rows
    from the same player are dependent, so resampling rows i.i.d. would
    understate the interval (2026-08-26 amendment; the docstring previously
    promised subject-level resampling while the code resampled rows).
    """
    rng = np.random.default_rng(seed)
    players = res["player"]
    uniq = np.unique(players)
    rows_of = {p: np.flatnonzero(players == p) for p in uniq}
    numeric = [k for k in res if k != "player"]
    xs = []
    already = 0
    for _ in range(n_boot):
        draw = rng.choice(uniq, size=len(uniq), replace=True)
        take = np.concatenate([rows_of[p] for p in draw])
        sub = {k: res[k][take] for k in numeric}
        c = crossing(curves(sub, by=by), key=key)
        if c is None:
            continue
        if c["already_ahead"]:
            already += 1
        xs.append(c["x"])
    xs = np.array(xs)
    if len(xs) == 0:
        return None
    return {
        "median": float(np.median(xs)),
        "ci_lo": float(np.percentile(xs, 2.5)),
        "ci_hi": float(np.percentile(xs, 97.5)),
        "share_already_ahead_at_smallest_x": float(already / max(len(xs), 1)),
        "n_boot": int(len(xs)),
    }


if __name__ == "__main__":
    pan = P.load()
    analytic = json.load(open(os.path.join(P.OUT, "n_star_analytic.json"), encoding="utf-8"))

    print("STAGES 3-4  estimators and rolling-origin validation")
    print("  first origin %d, so seasons %d-%d are the test period\n"
          % (FIRST_ORIGIN, FIRST_ORIGIN + 1, int(pan["year"].max())))

    everything = {}
    for metric in V.METRICS:
        res = run(pan, metric)
        by_n = curves(res, by="n")
        by_pa = curves(res, by="pa")
        cx_n = crossing(by_n)
        cx_pa = crossing(by_pa)
        boot_n = bootstrap_crossing(res, by="n")

        n_star_a = analytic[metric]["n_star_analytic"]
        print("\n  %s  out-of-sample RMSE by number of prior seasons" % metric)
        print("     n   cases      RC       IR       BL     IR-RC    lambda")
        for r in by_n:
            m = res["n"] == r["x"]
            print("    %2d  %6d   %.4f   %.4f   %.4f   %+.4f    %.2f"
                  % (r["x"], r["count"], r["rmse_RC"], r["rmse_IR"], r["rmse_BL"],
                     r["rmse_IR"] - r["rmse_RC"], res["lam"][m].mean()))
        print("    n*_analytic  = %.2f seasons   (committed before this run)" % n_star_a)
        if cx_n is None:
            print("    n*_empirical = not reached: IR never overtakes RC in the observed range")
        elif cx_n["already_ahead"]:
            print("    n*_empirical <= %.0f: IR is already ahead at the smallest n observed" % cx_n["x"])
        else:
            print("    n*_empirical = %.2f seasons" % cx_n["x"])
        if boot_n:
            print("    bootstrap    : median %.2f, 95%% CI [%.2f, %.2f], %d resamples"
                  % (boot_n["median"], boot_n["ci_lo"], boot_n["ci_hi"], boot_n["n_boot"]))
            print("                   %.0f%% of resamples have IR ahead at the smallest n"
                  % (100 * boot_n["share_already_ahead_at_smallest_x"]))
        if cx_pa:
            print("    crossing in cumulative prior PA: %s%.0f"
                  % ("<= " if cx_pa["already_ahead"] else "", cx_pa["x"]))

        # a censored crossing ("already ahead at the smallest observable n")
        # yields NO numeric gap: the boundary is a bound, not a measurement
        # (2026-08-26 amendment; a phantom +0.53 was previously recorded for
        # the strikeout rate from exactly this case)
        measured = cx_n is not None and not cx_n["already_ahead"]
        everything[metric] = {
            "by_n": by_n, "by_pa": by_pa,
            "crossing_n": cx_n, "crossing_pa": cx_pa, "bootstrap_n": boot_n,
            "n_star_analytic": n_star_a,
            "gap": (cx_n["x"] - n_star_a) if measured else None,
            "gap_note": None if measured else
                "crossing censored below the smallest observable n; no gap is measurable",
        }
        np.savez_compressed(os.path.join(P.OUT, "cases_%s.npz" % metric), **res)

    with open(os.path.join(P.OUT, "results.json"), "w", encoding="utf-8") as f:
        json.dump(everything, f, indent=2)
    print("\n  saved -> %s" % os.path.join(P.OUT, "results.json"))

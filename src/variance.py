"""
Stage 2: variance components and the analytic crossing point.

The model declared in advance, for a metric y observed for player i in season t:

    y*_it = mu + a_i + e_it        a_i ~ (0, sigma2_b)   e_it ~ (0, sigma2_w)

where y* is the metric with its season's league mean removed, so that era drift
does not enter the within-player term. a_i is the player's stable level, e_it
carries both genuine season-to-season fluctuation and finite-PA sampling noise.

Under squared loss, predicting season T+1:

    RC (cohort level)          error = a_i + e            MSE = sigma2_b + sigma2_w
    IR (mean of n own seasons) error = ebar - e           MSE = sigma2_w (1 + 1/n)

so the two cross where sigma2_w / n = sigma2_b, giving

    n*_analytic = sigma2_w / sigma2_b

and substituting that n into the reliability of the individual mean,
lambda(n) = sigma2_b / (sigma2_b + sigma2_w/n), returns exactly 0.5. The
crossing point and the optimal shrinkage weight are one object.

This number is the PREDICTION. It is computed on training seasons only and
committed before any out-of-sample run. The signed gap to the empirical
crossing point is a primary result, not a diagnostic.

Estimator: the standard unbalanced one-way random-effects ANOVA.
"""

import os

import numpy as np

import panel as P

TRAIN_END = 1990        # last training season for the committed prediction
METRICS = ("OPS", "KRATE")

AGE_BUCKETS = ((0, 23), (24, 26), (27, 29), (30, 32), (33, 99))
POS_GROUP = {"C": "C", "1B": "IF", "2B": "IF", "3B": "IF", "SS": "IF",
             "LF": "OF", "CF": "OF", "RF": "OF", "OF": "OF", "DH": "DH"}


def league_means(pan, metric):
    """Mean of the metric per season, over the panel. Era reference level."""
    out = {}
    for y in np.unique(pan["year"]):
        out[int(y)] = float(pan[metric][pan["year"] == y].mean())
    return out


def era_adjust(pan, metric, lm):
    """y* = y - league mean of its own season."""
    return pan[metric] - np.array([lm[int(y)] for y in pan["year"]])


def age_bucket(a):
    for lo, hi in AGE_BUCKETS:
        if lo <= a <= hi:
            return "%d-%d" % (lo, hi)
    return "33-99"


def variance_components(values, groups):
    """
    Unbalanced one-way random effects ANOVA.

    Returns sigma2_b (between groups), sigma2_w (within groups), and the
    diagnostics needed to judge the estimate.
    """
    order = np.argsort(groups, kind="stable")
    v, g = values[order], groups[order]
    bounds = np.flatnonzero(np.r_[True, g[1:] != g[:-1], True])
    sizes = np.diff(bounds)

    # groups with a single observation carry no within-group information
    k = len(sizes)
    N = len(v)
    grand = v.mean()

    ssw = 0.0
    ssb = 0.0
    for s, e in zip(bounds[:-1], bounds[1:]):
        gi = v[s:e]
        m = gi.mean()
        ssw += ((gi - m) ** 2).sum()
        ssb += len(gi) * (m - grand) ** 2

    dfw = N - k
    dfb = k - 1
    if dfw <= 0 or dfb <= 0:
        raise ValueError("not enough groups or observations")

    msw = ssw / dfw
    msb = ssb / dfb
    n0 = (N - (sizes.astype(float) ** 2).sum() / N) / dfb

    s2w = msw
    s2b = (msb - msw) / n0
    return {
        "sigma2_w": float(s2w),
        "sigma2_b": float(s2b),
        "MSW": float(msw), "MSB": float(msb), "n0": float(n0),
        "n_obs": int(N), "n_players": int(k),
        "mean_seasons": float(N / k),
    }


def analytic_crossing(pan, metric, train_end=TRAIN_END, min_seasons=2, verbose=True):
    """n*_analytic for one metric, on training seasons only."""
    m = pan["year"] <= train_end
    tr = {k: v[m] for k, v in pan.items()}

    lm = league_means(tr, metric)
    y = era_adjust(tr, metric, lm)

    # players with a single season are excluded from the estimation entirely:
    # they carry no within-player information, and including them in the
    # between-player term would mix a different selection process into
    # sigma2_b (the comment here previously claimed the opposite of what the
    # mask below does; corrected 2026-08-26)
    counts = {}
    for p in tr["playerID"]:
        counts[p] = counts.get(p, 0) + 1
    keep = np.array([counts[p] >= min_seasons for p in tr["playerID"]])

    vc = variance_components(y[keep], tr["playerID"][keep])
    s2b, s2w = vc["sigma2_b"], vc["sigma2_w"]
    n_star = s2w / s2b if s2b > 0 else float("inf")

    vc.update({
        "metric": metric,
        "train_end": int(train_end),
        "train_first": int(tr["year"].min()),
        "n_star_analytic": float(n_star),
        "reliability_at_n_star": float(s2b / (s2b + s2w / n_star)) if s2b > 0 else float("nan"),
        "sd_between": float(np.sqrt(max(s2b, 0))),
        "sd_within": float(np.sqrt(max(s2w, 0))),
    })

    if verbose:
        print("  %-6s  train %d-%d   players %4d   seasons/player %.1f"
              % (metric, vc["train_first"], train_end, vc["n_players"], vc["mean_seasons"]))
        print("          sd between players %.4f   sd within player %.4f"
              % (vc["sd_between"], vc["sd_within"]))
        print("          n*_analytic = sigma2_w / sigma2_b = %.2f seasons"
              % vc["n_star_analytic"])
        print("          check: reliability at that n = %.3f  (must be 0.500)"
              % vc["reliability_at_n_star"])
    return vc


def lambda_of_n(n, s2b, s2w):
    """Optimal shrinkage weight on the individual mean, classical form."""
    n = np.asarray(n, dtype=float)
    return s2b / (s2b + s2w / n)


if __name__ == "__main__":
    pan = P.load()
    print("STAGE 2  variance components and the analytic prediction")
    print("  training window closes at %d; every season after it is untouched.\n" % TRAIN_END)
    res = {}
    for metric in METRICS:
        res[metric] = analytic_crossing(pan, metric)
        print()

    out = os.path.join(P.OUT, "n_star_analytic.json")
    import json
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("  saved ->", out)

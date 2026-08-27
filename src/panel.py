"""
Stage 1: build the player-season panel from the Lahman database.

Every inclusion rule here is a pre-registered choice. Nothing is filtered
silently: every dropped row is counted and reported with its reason.

Definitions, fixed in advance:
  PA   = AB + BB + HBP + SF + SH
  OBP  = (H + BB + HBP) / (AB + BB + HBP + SF)
  SLG  = (H + 2B + 2*3B + 3*HR) / AB
  OPS  = OBP + SLG                      primary metric, slow-stabilising
  K%   = SO / PA                        secondary metric, fast-stabilising
  age  = yearID - birthYear, minus 1 when the player was born in July or later
         (the standard baseball convention: age as of 30 June of the season)

Window: 1954 onwards. Sacrifice flies became an official statistic in 1954 and
are required by the OBP denominator; before that the metric is not comparable.
"""

import os
import sqlite3

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "lahman.sqlite")
OUT = os.path.join(ROOT, "out")

FIRST_SEASON = 1954          # sacrifice flies officially recorded
MIN_PA = 100                 # exposure floor for a season to enter the sample

# a season is dropped if the fields the metrics need are absent
REQUIRED = ("AB", "H", "2B", "3B", "HR", "BB", "SO", "HBP", "SF", "SH")


def _log(drops, reason, n):
    if n:
        drops.append((reason, int(n)))


def build(min_pa=MIN_PA, verbose=True):
    """Return the player-season panel as a dict of aligned numpy arrays."""
    con = sqlite3.connect(DB)
    drops = []

    # ---- stints are summed: a player traded mid-season has one row per team
    rows = con.execute(
        """
        SELECT b.playerID, b.yearID,
               SUM(b.AB), SUM(b.H), SUM(b."2B"), SUM(b."3B"), SUM(b.HR),
               SUM(b.BB), SUM(b.SO), SUM(b.HBP), SUM(b.SF), SUM(b.SH),
               p.birthYear, p.birthMonth,
               COUNT(*) AS stints,
               SUM(CASE WHEN b.AB IS NULL OR b.H IS NULL OR b."2B" IS NULL
                         OR b."3B" IS NULL OR b.HR IS NULL OR b.BB IS NULL
                         OR b.SO IS NULL OR b.HBP IS NULL OR b.SF IS NULL
                         OR b.SH IS NULL THEN 1 ELSE 0 END) AS nulls
        FROM Batting b
        JOIN People p ON p.playerID = b.playerID
        WHERE b.yearID >= ?
        GROUP BY b.playerID, b.yearID
        """,
        (FIRST_SEASON,),
    ).fetchall()
    raw_n = len(rows)

    # ---- primary position per player-season: the position with most games,
    #      taken from Appearances rather than Fielding, because Lahman's
    #      Fielding table carries no DH rows at all: a full-time designated
    #      hitter has no fielding record and would be dropped under a label
    #      claiming his position is unknown (2026-08-26 amendment; 124
    #      player-seasons, all 1973+, mean OPS above the panel's). G_of is the
    #      authoritative outfield total; the lf/cf/rf corner columns are NOT
    #      summed alongside it, which would double-count. Pitchers are
    #      excluded: they do not bat to a comparable standard.
    APP_COLS = ("G_p", "G_c", "G_1b", "G_2b", "G_3b", "G_ss", "G_of", "G_dh")
    APP_POS = ("P", "C", "1B", "2B", "3B", "SS", "OF", "DH")
    pos = {}
    for row in con.execute(
        """
        SELECT playerID, yearID, %s FROM Appearances
        WHERE yearID >= ? GROUP BY playerID, yearID
        """ % ", ".join("SUM(%s)" % c for c in APP_COLS),
        (FIRST_SEASON,),
    ):
        pid, yr, games = row[0], row[1], [g or 0 for g in row[2:]]
        best = max(range(len(games)), key=lambda i: games[i])
        if games[best] > 0:
            pos[(pid, yr)] = (APP_POS[best], games[best])
    con.close()

    pid_l, yr_l, pa_l, ops_l, kr_l, age_l, pos_l = [], [], [], [], [], [], []
    n_nulls = n_nopos = n_pitcher = n_noage = n_zeroab = 0

    for (pid, yr, ab, h, d2, d3, hr, bb, so, hbp, sf, sh,
         byear, bmonth, stints, nulls) in rows:
        if nulls:
            n_nulls += 1
            continue
        if ab is None or ab <= 0:
            n_zeroab += 1
            continue
        pp = pos.get((pid, yr))
        if pp is None:
            n_nopos += 1
            continue
        if pp[0] == "P":
            n_pitcher += 1
            continue
        if not byear:
            n_noage += 1
            continue

        pa = ab + bb + hbp + sf + sh
        obp_den = ab + bb + hbp + sf
        if pa <= 0 or obp_den <= 0:
            n_zeroab += 1
            continue

        tb = h + d2 + 2 * d3 + 3 * hr
        obp = (h + bb + hbp) / obp_den
        slg = tb / ab
        age = yr - byear - (1 if (bmonth or 1) >= 7 else 0)

        pid_l.append(pid)
        yr_l.append(yr)
        pa_l.append(pa)
        ops_l.append(obp + slg)
        kr_l.append(so / pa)
        age_l.append(age)
        pos_l.append(pp[0])

    _log(drops, "null in a required batting field", n_nulls)
    _log(drops, "no plate appearances / zero AB", n_zeroab)
    _log(drops, "no appearances record, primary position unknown", n_nopos)
    _log(drops, "primary position is pitcher", n_pitcher)
    _log(drops, "birth year unknown, age not computable", n_noage)

    panel = {
        "playerID": np.array(pid_l),
        "year": np.array(yr_l, dtype=np.int32),
        "PA": np.array(pa_l, dtype=np.float64),
        "OPS": np.array(ops_l, dtype=np.float64),
        "KRATE": np.array(kr_l, dtype=np.float64),
        "age": np.array(age_l, dtype=np.int32),
        "pos": np.array(pos_l),
    }

    # ---- exposure floor. Applied to EVERY player-season in the panel, so it
    #      gates the T+1 outcome exactly as it gates season T: a subject whose
    #      next season falls under the floor contributes no case. No survival
    #      model or censoring adjustment exists anywhere in this pipeline; the
    #      outcome-floor sensitivity in sensitivity.py measures what that
    #      censoring does to the crossing point.
    keep = panel["PA"] >= min_pa
    _log(drops, "PA below the %d floor" % min_pa, (~keep).sum())
    panel = {k: v[keep] for k, v in panel.items()}

    if verbose:
        print("STAGE 1  player-season panel")
        print("  source rows (stints summed, %d+)      %8d" % (FIRST_SEASON, raw_n))
        for reason, n in drops:
            print("    dropped: %-42s %8d" % (reason, n))
        print("  retained player-seasons                %8d" % len(panel["year"]))
        print("  players                                %8d" % len(set(panel["playerID"])))
        print("  seasons                                %8d  (%d-%d)"
              % (len(set(panel["year"].tolist())), panel["year"].min(), panel["year"].max()))
    return panel, drops


def sanity(panel):
    """Print the checks the specification asks to see before any modelling."""
    yr, pa = panel["year"], panel["PA"]
    print("\n  rows by decade")
    for d in range(1950, 2030, 10):
        m = (yr >= d) & (yr < d + 10)
        if m.sum():
            print("    %4ds  %6d rows   median PA %5.0f   mean OPS %.3f   mean K%% %.3f"
                  % (d, m.sum(), np.median(pa[m]), panel["OPS"][m].mean(), panel["KRATE"][m].mean()))

    counts = {}
    for p in panel["playerID"]:
        counts[p] = counts.get(p, 0) + 1
    c = np.array(sorted(counts.values()))
    print("\n  seasons per player: n=%d players, median %d, mean %.1f, max %d"
          % (len(c), np.median(c), c.mean(), c.max()))
    print("    1 season only: %d players (%.1f%%)" % ((c == 1).sum(), 100 * (c == 1).mean()))
    print("    >= 5 seasons : %d players (%.1f%%)" % ((c >= 5).sum(), 100 * (c >= 5).mean()))
    print("    >= 10 seasons: %d players (%.1f%%)" % ((c >= 10).sum(), 100 * (c >= 10).mean()))

    print("\n  missingness after construction: none by design, every dropped row is counted above")
    for m in ("OPS", "KRATE"):
        v = panel[m]
        print("    %-6s min %.3f  p1 %.3f  median %.3f  p99 %.3f  max %.3f"
              % (m, v.min(), np.percentile(v, 1), np.median(v), np.percentile(v, 99), v.max()))


def save(panel, path=None):
    path = path or os.path.join(OUT, "panel.npz")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez_compressed(path, **panel)
    return path


def load(path=None):
    path = path or os.path.join(OUT, "panel.npz")
    z = np.load(path, allow_pickle=False)
    return {k: z[k] for k in z.files}


if __name__ == "__main__":
    p, _ = build()
    sanity(p)
    print("\n  saved ->", save(p))
    # the unfloored panel feeds the outcome-censoring sensitivity only;
    # nothing in the primary pipeline reads it
    p1, _ = build(min_pa=1, verbose=False)
    print("  saved ->", save(p1, os.path.join(OUT, "panel_all.npz")), "(floor 1, sensitivity only)")

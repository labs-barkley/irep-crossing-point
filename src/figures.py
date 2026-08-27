"""
Stage 5: the two figures.

Figure 1  out-of-sample error against the amount of individual evidence, three
          estimators, with both crossing points marked.
Figure 2  the optimal blend weight against n, fitted against its analytic form.

Colour: Okabe-Ito blue / vermillion / bluish-green, assigned to estimators in a
fixed order and never cycled. Validated for colour-vision deficiency separation
(worst adjacent pair dE 11.0 deutan, 25.8 normal) rather than eyeballed. Each
series is also labelled directly at its right end, so identity never rests on
colour alone. Text stays in ink; only the marks carry the series hue.
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import panel as P
import variance as V

RC_C, IR_C, BL_C = "#0072B2", "#D55E00", "#009E73"
INK, MUTED, GRID = "#1a1a1a", "#666666", "#dddddd"
SURFACE = "#fcfcfb"

LABEL = {"RC": "reference class", "IR": "individual record", "BL": "blend"}
COLOR = {"RC": RC_C, "IR": IR_C, "BL": BL_C}
NICE = {"OPS": "OPS", "KRATE": "strikeout rate"}


def _spread(values, ax, min_gap_pt=11.0):
    """Vertical offsets in points so right-edge labels never sit on each other."""
    lo, hi = ax.get_ylim()
    h_pt = ax.get_window_extent().height * 72.0 / ax.figure.dpi
    pos = [(v - lo) / (hi - lo) * h_pt for v in values]
    out = [0.0] * len(pos)
    prev = None
    for i in sorted(range(len(pos)), key=lambda j: pos[j]):
        want = pos[i]
        if prev is not None and want - prev < min_gap_pt:
            want = prev + min_gap_pt
        out[i] = want - pos[i]
        prev = want
    return out


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9, length=3)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def figure1(results, path):
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), facecolor=SURFACE)
    for ax, metric in zip(axes, V.METRICS):
        r = results[metric]
        rows = r["by_n"]
        x = [q["x"] for q in rows]
        _style(ax)

        ends = []
        for est in ("RC", "IR", "BL"):
            y = [q["rmse_" + est] for q in rows]
            ax.plot(x, y, color=COLOR[est], linewidth=2, marker="o", markersize=4.5,
                    markeredgecolor=SURFACE, markeredgewidth=0.8, label=LABEL[est], zorder=3)
            ends.append((y[-1], est))
        for dy, (yv, est) in zip(_spread([e[0] for e in ends], ax), ends):
            ax.annotate(LABEL[est], xy=(x[-1], yv), xytext=(6, dy),
                        textcoords="offset points", color=COLOR[est],
                        fontsize=8.5, va="center")

        na = r["n_star_analytic"]
        ax.axvline(na, color=MUTED, linestyle=":", linewidth=1.4, zorder=1)
        ax.annotate("n* analytic %.2f" % na, xy=(na, ax.get_ylim()[1]),
                    xytext=(4, -12), textcoords="offset points",
                    fontsize=8, color=MUTED, va="top")

        cx = r["crossing_n"]
        if cx and not cx["already_ahead"]:
            ax.axvline(cx["x"], color=INK, linestyle="--", linewidth=1.4, zorder=2)
            b = r.get("bootstrap_n")
            if b:
                ax.axvspan(b["ci_lo"], b["ci_hi"], color=INK, alpha=0.07, zorder=0)
            ax.annotate("n* empirical %.2f" % cx["x"], xy=(cx["x"], ax.get_ylim()[1]),
                        xytext=(5, -30), textcoords="offset points",
                        fontsize=8, color=INK, va="top")
        elif cx:
            ax.annotate("n* empirical\nbelow 1 season", xy=(x[0], ax.get_ylim()[1]),
                        xytext=(4, -14), textcoords="offset points",
                        fontsize=8, color=INK, va="top", fontweight="medium")

        ax.set_xlabel("prior seasons of the subject's own record (n)", fontsize=9.5, color=INK)
        ax.set_ylabel("out-of-sample RMSE", fontsize=9.5, color=INK)
        ax.set_title(NICE[metric], fontsize=11, color=INK, fontweight="medium", loc="left", pad=8)
        ax.set_xlim(min(x) - 0.4, max(x) + 2.6)

    axes[0].legend(frameon=False, fontsize=8.5, loc="upper right", labelcolor=INK)
    fig.suptitle("Where the individual record overtakes the category",
                 fontsize=13, color=INK, x=0.02, ha="left", y=0.99, fontweight="medium")
    fig.text(0.02, 0.040,
             "Rolling-origin validation, test seasons 1991-2022, Lahman 1954-2022. "
             "Shaded band: 95% bootstrap interval on the empirical crossing.",
             fontsize=8, color=MUTED, ha="left")
    fig.text(0.02, 0.008, "IREP Protocol · Barkley Labs · Elodie Aishwarya P. Remoissenet · August 2026",
             fontsize=7.5, color=MUTED, ha="left")
    fig.tight_layout(rect=[0, 0.075, 1, 0.94])
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return path


def figure2(results, analytic, path):
    cases = {m: np.load(os.path.join(P.OUT, "cases_%s.npz" % m)) for m in V.METRICS}
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3), facecolor=SURFACE)
    for ax, metric in zip(axes, V.METRICS):
        _style(ax)
        c = cases[metric]
        ns = sorted(set(c["n"].tolist()))
        ns = [n for n in ns if (c["n"] == n).sum() >= 30 and n <= 12]
        fitted = [float(c["lam"][c["n"] == n].mean()) for n in ns]

        s2b = analytic[metric]["sigma2_b"]
        s2w = analytic[metric]["sigma2_w"]
        grid = np.linspace(min(ns), max(ns), 200)
        ax.plot(grid, V.lambda_of_n(grid, s2b, s2w), color=MUTED, linewidth=1.6,
                linestyle=":", label="analytic  b/(b + w/n)", zorder=2)
        ax.plot(ns, fitted, color=BL_C, linewidth=2, marker="o", markersize=4.5,
                markeredgecolor=SURFACE, markeredgewidth=0.8, label="fitted on training data", zorder=3)
        ends = [(fitted[-1], "fitted", BL_C),
                (float(V.lambda_of_n(grid[-1], s2b, s2w)), "analytic", MUTED)]
        for dy, (yv, lab, col) in zip(_spread([e[0] for e in ends], ax), ends):
            ax.annotate(lab, xy=(ns[-1], yv), xytext=(6, dy), textcoords="offset points",
                        color=col, fontsize=8.5, va="center")

        ax.axhline(0.5, color=GRID, linewidth=1)
        ax.annotate("weight 0.5: the crossing point", xy=(min(ns), 0.5), xytext=(2, 4),
                    textcoords="offset points", fontsize=7.5, color=MUTED)
        ax.set_ylim(0, 1.05)
        ax.set_xlim(min(ns) - 0.3, max(ns) + 2.4)
        ax.set_xlabel("prior seasons (n)", fontsize=9.5, color=INK)
        ax.set_ylabel("weight on the individual record", fontsize=9.5, color=INK)
        ax.set_title(NICE[metric], fontsize=11, color=INK, fontweight="medium", loc="left", pad=8)

    axes[0].legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=INK)
    fig.suptitle("How fast the optimal weight moves from category to individual",
                 fontsize=13, color=INK, x=0.02, ha="left", y=0.99, fontweight="medium")
    fig.text(0.02, 0.040,
             "Fitted weight is estimated inside the training window only, per stratum of n. "
             "The analytic curve uses the variance components committed before the run.",
             fontsize=8, color=MUTED, ha="left")
    fig.text(0.02, 0.008, "IREP Protocol · Barkley Labs · Elodie Aishwarya P. Remoissenet · August 2026",
             fontsize=7.5, color=MUTED, ha="left")
    fig.tight_layout(rect=[0, 0.075, 1, 0.94])
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return path


if __name__ == "__main__":
    results = json.load(open(os.path.join(P.OUT, "results.json"), encoding="utf-8"))
    analytic = json.load(open(os.path.join(P.OUT, "n_star_analytic.json"), encoding="utf-8"))
    print("STAGE 5  figures")
    print("  ->", figure1(results, os.path.join(P.OUT, "figure1_crossing.png")))
    print("  ->", figure2(results, analytic, os.path.join(P.OUT, "figure2_weight.png")))

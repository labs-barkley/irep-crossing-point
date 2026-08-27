# Amendments

Every post-pilot change to the pipeline, dated, with its reason and its measured
effect on the headline numbers. Nothing here changes a hypothesis; the
hypotheses in `PREREGISTRATION.md` are frozen. All of these follow from an
adversarial audit of the pipeline run on 2026-08-26, before anything was
published or pushed anywhere.

Headline before the amendments: OPS n*_analytic 1.19, n*_empirical 1.87
[1.70, 2.11], gap +0.68. Headline after all of them: **1.21, 1.89 [1.71, 2.15],
gap +0.68.** The result is stable under every correction; the corrections are
recorded because the declared procedure must match the executed one.

## 2026-08-26 - designated hitters restored (panel.py)

Primary position was taken from the Fielding table, which contains no DH rows,
so a full-time designated hitter had no fielding record and was dropped under a
label claiming his position was unknown: 124 player-seasons, all 1973+, above
the panel's mean OPS, concentrated among high-exposure hitters. Position now
comes from Appearances (G_p, G_c, G_1b, G_2b, G_3b, G_ss, G_of, G_dh, argmax;
G_of is used as the authoritative outfield total, never the lf/cf/rf corner
columns, which double-count). Effect: panel 25,184 to 25,313 player-seasons;
OPS n*_analytic 1.19 to 1.21; empirical crossing 1.87 to 1.89.

## 2026-08-26 - reference class made leave-self-out (validate.py)

The estimator is declared as discarding subject identity, but the subject's own
training seasons sat inside their cohort cell. They are now removed from the
cell before the mean is taken; a cell needs 20 non-self observations or it
falls back to the grand mean. Effect on the crossing: under 0.01 seasons.

## 2026-08-26 - bootstrap made a cluster bootstrap over subjects (validate.py)

The docstring and the pre-registration promised an interval over subjects; the
code resampled rows i.i.d., understating the interval because a player's cases
are dependent across origins. The resample now draws players with replacement
and takes all their cases. Effect: OPS CI [1.70, 2.11] to [1.71, 2.15].

## 2026-08-26 - phantom gap removed for censored crossings (validate.py)

`results.json` recorded gap = +0.53 for the strikeout rate, computed from the
n = 1 censoring boundary as though it were a measured crossing. A censored
crossing now yields no numeric gap, and a note says why.

## 2026-08-26 - two comments corrected to say what the code does

`panel.py` claimed survivorship was "handled at the pairing stage"; no such
treatment exists anywhere, and the exposure floor gates the outcome season
exactly as it gates the others. `variance.py` claimed single-season players
inform the between-player term; the mask on the next line excludes them. Both
comments now state the actual behaviour. No number changed.

## 2026-08-27 - era-drift quantification sharpened by the first independent reproduction (LIMITATIONS.md)

Maxime Baelde reproduced the pilot end to end on publication day (fresh
environment, checksum verified, exact match on both headline numbers) and
checked the pooled "about half" attribution against the source: the per-era
residuals are +0.47 for test seasons 1991-2006 and +0.28 for 2007-2022, so
between a third and two thirds of the headline +0.68 is fit-window drift.
Adopted as stated; the era adjustment corrects location only, so the swing is
the variance ratio genuinely moving, and the instability is the finding. The
era-adjusted-metrics rerun (OPS+-style) joins the open work. Tracked in
issue #1, labeled external-review. No pipeline number changed.

## 2026-08-26 - sensitivity stage added (sensitivity.py)

Five named rival explanations for the gap, each answered by the repo's own
code rather than by prose: era drift in the variance components, the value the
conditioned reference class actually adds, the exposure floor, outcome-side
censoring, and the playing-time tier operationalisation (whose absolute cuts
degenerate for the 2021 test season because 2020 was a 60-game season). Results
in `out/sensitivity.json`, discussed in the README and LIMITATIONS.

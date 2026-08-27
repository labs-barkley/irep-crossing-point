# Limitations

Written alongside the pipeline rather than after the discussion section, as the
specification requires.

## The ordering of this run

The baseball result is a **pilot**. Within each pipeline execution the analytic
prediction is written before anything out-of-sample runs, and the directional
hypothesis was stated in writing before the first measurement; but a signed
pre-registration document did not precede the first run, and verification
re-runs have since regenerated the artefacts, so the original ordering is no
longer machine-verifiable from timestamps. Treat every number here as
hypothesis-generating. The confirmatory test is the second domain, whose
hypotheses are now frozen. Post-pilot corrections are in `AMENDMENTS.md`.

## Rival explanations for the gap, measured

The headline gap (empirical crossing minus analytic prediction, +0.68 seasons
for OPS) is not a single-mechanism result. The sensitivity stage measures the
named rivals; `out/sensitivity.json` carries the numbers, the README the
discussion. In brief: between a third and
two thirds of the headline +0.68 is fit-window drift, not an IREP effect: the
per-era residuals are +0.47 for test seasons 1991-2006 and +0.28 for
2007-2022, computed by refitting the analytic prediction inside each disjoint
window and comparing to the empirical crossing of that same window
(quantification sharpened by the first independent reproduction,
[issue #1](https://github.com/labs-barkley/irep-crossing-point/issues/1));
the drift is real variance-ratio movement, not a centering bug, since the era
adjustment corrects location only; the conditioning of the
reference class on age, position and playing time accounts for only a small
part; outcome-side censoring (survivorship, below) inflates the crossing; and
the remainder sits on the individual-estimator side, where ageing makes a long
record over-weight a player's peak. The pre-registered direction (empirical
later than analytic) holds in every era window tested; the pooled magnitude is
the sum of several effects and should never be quoted as one mechanism.

## What the data can and cannot support

**Vintage.** The Lahman build used here ends at the 2022 season. The canonical
SABR release now includes 2025. Three additional seasons would not change a
methodological result, but the figures should not be described as current.

**Baseball is not hiring.** A player-season carries several hundred plate
appearances; a job carries a handful of reviews. The crossing point measured in
seasons is not transportable to hiring as a count. What transports is the shape:
the blend weight as a function of evidence, which is defined at every n
including the small ones hiring actually has.

**Survivorship makes the crossing an upper bound, not a lower one.** A case
exists only if the subject clears the exposure floor in t+1, so the outcome is
censored on the players who collapsed or left. The censored-outcome sensitivity
(sensitivity.py, outcome-floor sweep) shows the direction: every relaxation of
the outcome floor moves the crossing earlier, monotonically. The mechanism is a
level shift, not noise: subjects who lose their playing time post collapsed
outcomes, and the reference class, anchored to a cohort mean on a playing-time
tier carried from their last full season, misses that collapse by more than the
individual record does. The censored-out subjects are therefore ones the
individual estimator predicts better, and removing them flatters the reference
class. An earlier version of this file asserted the opposite direction; the
sweep settled it. Roughly one in ten at-risk subjects records no plate
appearance at all in t+1 and remains outside the sweep, so the fully-decensored
crossing is lower still. Read the published crossing as an upper bound on the
observable part.

**Ageing is inside the within-subject term.** The model treats a player's level
as stable with noise around it. It is not: it rises and falls with age. That
drift inflates sigma2_w and therefore inflates n*_analytic. The fitted weight peaks at n = 6 and falls below the analytic curve after
n = 8 for OPS; that is the visible consequence.
An age-structured model would separate the two; this one does not.

**Season-level n is coarse.** With integer seasons, a crossing between n = 1 and
n = 2 is an interpolation on two points. The cumulative-plate-appearance curve
carries the finer resolution and should be quoted alongside.

## What is not comparable to published work

Stabilisation points in the sabermetric literature are computed by split-half
reliability **within** a season. The within-subject term here spans seasons and
therefore contains genuine year-to-year change as well as sampling noise. The
two quantities are relatives, not equals, and the numbers should not be set
side by side as if they measured the same thing. No published stabilisation
figure is quoted anywhere in this repository, deliberately: the secondary
summaries disagree with each other, and a wrong number on a famous topic costs
more than it buys.

## Choices a reader may reasonably contest

- **The 100 plate-appearance floor** excludes marginal players, who are the ones
  with the least individual evidence. A lower floor would populate small n with
  noisier subjects and probably push the crossing later. In the other direction
  the floor sets the answer directly, because sigma2_w carries binomial
  sampling noise proportional to 1/PA: the floor sweep (sensitivity.py) shows
  the gap shrinking substantially under a regulars-only floor. The gap is a
  floor-conditional quantity and is reported as such, never as a constant of
  nature.
- **The reference class** is age, position and playing-time tier. A richer one
  would be a stronger opponent. The specification demands the reference class be
  tuned with equal care, and a hostile reader should check this one first.
- **Playing-time tier is taken from the subject's own last season**, which gives
  the reference class a sliver of individual information. This makes RC stronger
  and the test harder for IR, which is the conservative direction.
- **The naive era forecast** carries the last training season's league mean into
  the test season. It is common to both estimators and cannot move the crossing,
  but it does inflate both error curves in seasons where the run environment
  jumped.
- **Cohorts with fewer than 20 training observations** fall back to the grand
  mean. The threshold is arbitrary.

## Not yet done

- The rerun on era-adjusted metrics (OPS+-style): the PED era inflates power
  metrics specifically, and OPS is where the gap is largest. If the residual
  survives the adjustment it means something; if it collapses, that gets
  published too ([issue #1](https://github.com/labs-barkley/irep-crossing-point/issues/1)).
- The exposure-weighted variance-components sensitivity.
- A survival model for the one-in-ten at-risk subjects with zero plate
  appearances in t+1, who stay outside the outcome-floor sweep entirely.
- The second domain.

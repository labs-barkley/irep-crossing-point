# Pre-registration: the crossing point

Study: at what amount of individual evidence does a subject's own record beat
their reference class, and how far is that point from what classical shrinkage
theory predicts.

Author: Elodie Aishwarya P. Remoissenet
Specification: `irep-crossing-point-spec.md`

---

## 0. Status of this document, stated first because it matters

**This baseball run is a pilot, not a confirmatory test.** The distinction is the
whole point of pre-registration, so it is declared here rather than buried.

Three facts about ordering, stated plainly:

1. This document did not exist in signed form before the first out-of-sample
   run. The baseball result is therefore hypothesis-generating, full stop.
2. Within each execution of the pipeline, the analytic prediction is computed
   and written to disk before anything out-of-sample runs; `run.py` enforces
   that order structurally on every run.
3. An earlier version of this section pointed at file timestamps as proof that
   the prediction preceded the measurement. That was true of the first
   execution, but subsequent verification re-runs regenerate every artefact,
   so the timestamps on disk no longer show it and the claim of
   machine-verifiable ordering is withdrawn. No confirmatory claim rests on
   this pilot in any case.

The directional hypothesis H3 was stated in writing before the first
measurement ran, and its rationale is preserved unchanged below. Post-pilot
corrections to the pipeline (all of them bug fixes, none of them hypothesis
changes) are listed in `AMENDMENTS.md` with their measured effect on the
numbers.

**The confirmatory test is the second domain.** The hypotheses below are frozen
now, before any Dog Aging Project data has been touched, and that domain will
test them without a second look. Baseball is the demonstration; the second
domain is the argument.

---

## 1. Hypotheses

**H1.** There exists a finite n* at which the individual-referential estimator
overtakes the reference-class estimator in out-of-sample error.

**H2.** n* differs between metrics within a single domain, ordered by
signal-to-noise: a fast-stabilising metric crosses earlier than a slow,
composite one.

**H3, the directional hypothesis.** The empirical crossing point lies **later**
than the analytic one:

> n*_empirical > n*_analytic

Reasoning, fixed in advance: the analytic identity n*_analytic = sigma2_w /
sigma2_b compares the individual against a single grand mean. The reference-class
estimator actually deployed is conditioned on age, position and playing-time
tier, so it explains part of the between-subject variance that the analytic model
gives it no credit for. A stronger reference class pushes the crossing later.

**H4.** The fitted blend weight follows the analytic reliability curve
lambda(n) = sigma2_b / (sigma2_b + sigma2_w / n) where the subject's underlying
level is stable, and falls below it where that level drifts systematically with
age.

## 2. The committed analytic predictions

Estimated by unbalanced one-way random-effects ANOVA on era-adjusted values,
training seasons 1954-1990 only, players with two or more seasons. (Values as
recomputed after the designated-hitter correction of 2026-08-26; the
pre-correction values were 0.0736 / 0.0804 / 1.19 for OPS, unchanged for the
strikeout rate. See `AMENDMENTS.md`.)

| metric | sd between | sd within | **n\*_analytic** |
|---|---|---|---|
| OPS | 0.0732 | 0.0806 | **1.21 seasons** |
| strikeout rate | 0.0416 | 0.0285 | **0.47 seasons** |

Identity check, which must hold exactly: the reliability of the individual mean
at n\*_analytic is 0.500 for both metrics. It does.

## 3. Estimator definitions and feature boundaries

- **RC** predicts from the cohort mean only: age bucket at the target season,
  position group, playing-time tier. The subject's own record is discarded.
- **IR** predicts from the subject's own prior seasons only, exposure-weighted.
  Cohort membership is discarded, **including age**: an age term taken from
  cohort data would be leakage across estimators, and the specification forbids
  it.
- **BL** is lambda(n) * IR + (1 - lambda(n)) * RC, with lambda fitted per
  stratum of n inside the training window only.

Era is removed identically for both estimators, by subtracting each season's
league mean, and re-added as the last observed training season's mean. Being
common to both, it cannot move the crossing point.

## 4. Metrics

Primary: OPS. Secondary: strikeout rate. Two, declared in advance. No others
will be reported.

## 5. Validation scheme

Rolling origin. For every origin T from 1990 to 2021: train on seasons <= T,
predict season T+1. No information from T+1 enters any estimate, including
league means and the fitted weights. Error is reported on the test season only.

Primary statistic: out-of-sample RMSE by n, and separately by cumulative prior
plate appearances. n*_empirical is the interpolated crossing of the IR and RC
curves, with a 95 percent bootstrap interval over subjects.

## 6. Sample inclusion

- Seasons from 1954, the first year sacrifice flies were recorded; the OBP
  denominator requires them.
- Position players only; primary position taken from fielding appearances.
- A season enters the sample at 100 plate appearances or more.
- Stints are summed, so a player traded mid-season is one row.
- Every dropped row is counted with its reason and printed.

## 7. What would falsify the claim

- If IR does not beat RC at any n, or if the blend dominates IR at every n in
  hiring-realistic ranges, IREP's strong form is wrong and the paper says so.
- If n*_empirical matches n*_analytic in both domains, the classical model was
  sufficient. The contribution is then the measurement and the transfer, not a
  new phenomenon, and the paper states that in those words.
- If the two domains disagree on whether the axis holds at all, the cross-domain
  claim is withdrawn and a single-domain result is reported.
- If H3's sign is reversed in the second domain, H3 is wrong as a general claim
  and is reported as domain-specific.

## 8. Publication discipline

No cross-species framing, and no title built on one, before both curves exist.
A single-domain result is a paper; a two-domain invariance is a position.

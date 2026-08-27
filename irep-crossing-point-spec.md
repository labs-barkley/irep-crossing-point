# IREP: The Crossing Point
## Experimental specification for a real-data test of individual-referential vs reference-class prediction

Author: Elodie Aishwarya P. Remoissenet
Status: pre-registration draft, to be frozen before any modelling run

Two working-notes sections (an internal build prompt and a list of reserved titles) are removed from this public copy; nothing methodological is changed.

---

## 1. The claim under test

IREP asserts that evaluating an individual against their own prior record outperforms evaluating them against a reference class of similar individuals.

Stated as a testable proposition:

> For a subject i with n prior observations, a model predicting future performance from i's own history achieves lower out-of-sample error than a model predicting from the mean of i's reference class, once n exceeds some threshold n*.

The quantity of interest is not "individual wins". It is **n\***: how much individual evidence is required before the person beats the category. That is the number a selection system can act on, and it is not currently stated anywhere as a decision threshold.

That last sentence is deliberately narrow. Section 2 says why.

## 2. Prior art, and what is actually new

Three literatures already own parts of this question. Naming them precisely is what protects the result. The failure mode here is not being wrong; it is claiming a novelty a well-read reviewer can dismantle in one line.

**Reliability and stabilisation.** Sabermetrics has used split-half reliability since 2007, with widely cited updates in 2012-2013, to establish how many observations a metric needs before it correlates with itself at a chosen threshold. This is a property of the individual estimate on its own. It never compares the individual against the cohort. Cite the literature, do not restate it, and do not quote specific stabilisation values without going to the primary source: the published summaries disagree with each other, and a wrong number on a famous topic costs the paper its credibility in one line. The same sources also stress that reliability is a continuum rather than a point, which supports the framing here rather than competing with it.

**Empirical Bayes and shrinkage.** The optimal weight on an individual mean, given a cohort, is that mean's reliability:

> lambda(n) = sigma2_b / (sigma2_b + sigma2_w / n)

where sigma2_b is the between-subject variance and sigma2_w the within-subject variance. Marcel embodies this. Under squared loss the individual-only estimator carries error sigma2_w / n and the cohort-only estimator carries error sigma2_b, so the two cross at

> n*_analytic = sigma2_w / sigma2_b

and substituting that n back into lambda gives exactly 0.5. **The crossing point and the shrinkage weight are the same object seen from two sides.** A reader holding the variance components can derive n* at the blackboard, without any of this. The specification states that openly rather than waiting for a reviewer to state it.

**Idiographic versus nomothetic.** The claim that group structure does not transfer to the individual is a century old (Windelband's coinage, brought into psychology by Allport) and was reopened formally by Molenaar (2004), who showed through the classical ergodic theorems that a structure of inter-individual variation generalises to the analogous structure of intra-individual variation only under conditions real psychological processes rarely meet. Fisher, Medaglia and Jeronimus (PNAS, 2018) measured it: across six samples, the variance around the expected value was two to four times larger within individuals than within groups. Adolf and Fried (PNAS, 2019) replied that ergodicity is sufficient but not necessary, and that under non-ergodic conditions a **conditional equivalence** across levels remains available if the sources of non-ergodicity can be identified. Fisher et al. answered in turn.

That exchange closes on an open question: which conditions, and how would a practitioner know they held. This specification answers with one condition, measured.

### What is new here

Not the existence of the crossing point. Not the shrinkage curve. Both are classical, and this section concedes them before anyone has to point them out.

What is new is:

1. **The gap between the analytic and the empirical crossing point.** The identity n*_analytic = sigma2_w / sigma2_b holds only for a stationary subject, homoscedastic within-subject noise, squared loss, and a well-specified cohort. Real longitudinal data violates all four: ageing curves make the true value drift, variable exposure makes the noise heteroscedastic, survival truncates the sample, era effects move the cohort. The size and sign of that divergence cannot be read off published reliability curves. It has to be measured.
2. **Invariance across noise structures.** One domain produces a number. Two domains with different noise structures test whether the axis itself holds. This does not fall out of any closed form, and it is the contribution.
3. **A decision rule.** Reliability answers "is this estimate noisy". Shrinkage answers "how should I weight it". Neither answers the question a selection system has to resolve: at what point do I stop using the category. n* stated as a threshold, pre-registered, with a confidence interval, is that answer, and it is a condition of exactly the kind the PNAS exchange left open.

### References to carry in the paper

- Molenaar, P. C. M. (2004). A Manifesto on Psychology as Idiographic Science: Bringing the Person Back Into Scientific Psychology, This Time Forever. *Measurement: Interdisciplinary Research and Perspectives*, 2(4), 201-218.
- Fisher, A. J., Medaglia, J. D., & Jeronimus, B. F. (2018). Lack of group-to-individual generalizability is a threat to human subjects research. *PNAS*, 115(27), E6106-E6115.
- Adolf, J. K., & Fried, E. I. (2019). Ergodicity is sufficient but not necessary for group-to-individual generalizability. *PNAS*, 116(14), 6540-6541.
- Fisher, A. J., Medaglia, J. D., & Jeronimus, B. F. (2019). Reply to Adolf and Fried: Conditional equivalence and imperatives for person-level science. *PNAS*, 116(14), 6542-6543.
- Allport, G. W. (1937). Personality: A Psychological Interpretation. Henry Holt. For bringing the idiographic/nomothetic distinction, coined by Windelband (1894), into psychology.
- The sabermetric reliability literature, cited from primary sources only.

## 3. Why baseball

Baseball is the **demonstration**, not the argument. The argument completes in section 10, with a second domain.

Three reasons, in order of importance.

1. It is the only large public dataset with many repeated, standardised, outcome-linked measurements per individual, spanning 150 years, with an observed result behind every subject.
2. The argument has already been won there once. Scouting judged by reference class (body type, school, "projectability"); sabermetrics imposed the individual record; the sport re-organised around the result. The rhetorical move available is therefore not "here is a revolution" but "here is a settled question that hiring has not noticed".
3. The strong baseline is public. Marcel (Tom Tango's deliberately minimal forecaster) is a weighted blend of a player's last three seasons regressed toward league mean. It is a blend of exactly the two estimators under test, which makes it the honest opponent rather than a straw man.

**The cost of this choice, accepted deliberately.** Baseball is the domain where the technical objection lands hardest, because it is precisely where the reliability curves were built. That is paid for in framing rigour, per section 2, and recovered in credibility: a result that survives this audience survives any other.

Known limitation, to be stated in the paper rather than discovered by a reviewer: baseball supplies far more observations per individual than hiring ever will. This is why the deliverable is the crossing-point curve, and the blend weight at small n, rather than a single win.

## 4. Data

### Primary: Lahman Baseball Database
- Canonical source: https://sabr.org/lahman-database/ (donated by Sean Lahman to SABR; 2025 season included; CC BY-SA 3.0, attribution required)
- SQLite build: https://github.com/jknecht/baseball-archive-sqlite
- R package: https://github.com/cdalzell/Lahman
- Tables needed: `People` (birth year, debut), `Batting`, `Pitching`, `Fielding`, `Appearances`
- Note: the old `Master` table is now `People`. Any code or tutorial referencing `Master` predates the reorganisation.

### Optional refinement: Retrosheet / Statcast
Play-level and pitch-level granularity. Not required for the demonstration and adds substantial engineering cost. Skip in v1.

### Second domain: Dog Aging Project
- Landing: https://dogagingproject.org/data-access
- Curated releases via Terra (Broad Institute); requires an application, a signed individual Data Use Agreement, and a Google Cloud billing account
- HLES survey is the longitudinal backbone: 200+ questions on lifestyle, environment, behaviour, health, repeated annually
- Realistic lead time: weeks, not days.
- Mandatory citation and methods language is specified by DAP; comply exactly.

**Submit this application now, before the first line of modelling.** It is the long pole. Access should clear while the Lahman work runs; otherwise the second domain slips by a full cycle and the argument stays incomplete.

Also worth an application in parallel: C-BARQ (Penn), large behavioural instrument, repeated administration possible.

## 5. Design

### Unit and target
- Unit: player-season (subject i, season t)
- Target: a rate statistic for season t+1
- Primary metric: wOBA or OPS (composite, slow-stabilising)
- Secondary metric: strikeout rate (fast-stabilising)

Running both is not padding. Metrics stabilise at different rates, so n* should differ between them. If it does, the finding is that **n\* is a function of signal-to-noise, not of domain**, which is what makes the result transferable to competencies in hiring.

### The three estimators

1. **Reference-class model (RC).** Predicts t+1 from the cohort mean only: age bucket, primary position, era, playing-time tier. Subject identity is discarded. This is the resume.
2. **Individual-referential model (IR).** Predicts t+1 from subject i's own prior seasons only, exposure-weighted. Cohort membership is discarded.
3. **Blend (Marcel-class).** Shrinkage of IR toward RC with weight lambda. Fit lambda per stratum of n.

RC and IR must be tuned with equal care. An untuned RC invalidates the entire result and is the first thing a hostile reader will check.

### Two crossing points, declared in advance

This is the core of the design, and it is what section 2 argues is new.

- **n\*_analytic.** Estimated from variance components on the training seasons only, as sigma2_w / sigma2_b, with the variance estimator, the strata and the exposure weighting all stated in advance.
- **n\*_empirical.** The crossing of the IR and RC out-of-sample error curves under rolling-origin validation.

Pre-register n*_analytic as the **predicted** value of n*_empirical, per metric.

**The signed gap between them is a primary result, not a diagnostic.** A gap near zero says the classical variance-components model already describes this domain, and the paper says so plainly; the contribution is then the measurement and the transfer, not a new phenomenon. A large gap says real noise structure moves the decision threshold, and the paper reports by how much and in which direction. Both outcomes are publishable, and both are declared before any out-of-sample run.

### Validation
- Strict temporal split: train on seasons <= T, predict T+1. Rolling origin across many T.
- No future information in any feature, including league-mean terms and the variance components used for n*_analytic.
- Report error on the test season only.

### Primary output
Out-of-sample error (RMSE and MAE) for RC, IR and Blend, plotted against n, where n is the number of prior seasons and, separately, cumulative prior plate appearances. n*_empirical is the crossing point of the IR and RC curves. Report a bootstrap confidence interval on it, and the signed gap to n*_analytic.

Secondary output: the fitted lambda as a function of n, i.e. how fast the optimal weight moves from category to individual, with its analytic counterpart overlaid. In hiring-realistic ranges of n, this curve is the actionable deliverable even when n* itself is out of reach.

## 6. Pitfalls that will be used against you

- **Survivorship.** Players observed in t+1 are selected for having survived. Conditioning on survival biases in favour of the individual model. Mitigation: define the sample by exposure in season t, not t+1; report attrition; run a sensitivity analysis including a censored-outcome treatment.
- **Aging curves.** Age is real signal, and it belongs to the reference class. Giving IR an age term borrowed from cohort data is leakage across estimators. Keep the boundary explicit and state it.
- **Regression to the mean.** IR on small n will overfit noise. This is not a bug, it is the mechanism producing n*. Do not correct it away.
- **Era effects.** Run-scoring environments differ by decade. Normalise, and state the normalisation.
- **Playing time.** It is exposure, outcome, and selection all at once. Weight by it, do not predict on it naively.
- **Multiple metrics.** Two metrics pre-declared is science. Six metrics with one reported is not.
- **Detection is not prediction.** The existing synthetic head-to-head is a change-detection experiment: catch an injected decline. This specification is a prediction experiment: forecast season t+1. The two tasks have different noise structures and different crossing points. Never present one as evidence for the other. Stated together as two tasks sharing one reference axis they are a strength; blurred, they are a reviewer's opening.

## 7. Pre-registration

Freeze before the first modelling run, commit with a timestamp, and do not amend silently:

- hypotheses (direction and rough magnitude of n*)
- **the analytic prediction n\*_analytic, per metric, computed on training seasons only and committed before any out-of-sample run**
- **the expected sign of the gap between analytic and empirical n\*, with the reasoning**
- estimator definitions and feature boundaries
- primary and secondary metrics
- validation scheme
- sample inclusion rules
- what would falsify the claim

Falsification conditions, stated plainly:

- If IR does not beat RC at any n, or if the blend dominates IR at every n observed in hiring-realistic ranges, IREP's strong form is wrong and the paper says so.
- If n*_empirical matches n*_analytic in both domains, then the classical model was sufficient, the contribution is the measurement and the transfer rather than a new phenomenon, and the paper states that in those words.
- If the two domains disagree on whether the axis holds at all, the cross-domain claim is withdrawn and the paper reports a single-domain result.

## 8. Deliverables

1. Public repo: reproducible pipeline, seed-fixed, one command from raw download to figures
2. `PREREGISTRATION.md`, committed before results exist, carrying the analytic prediction
3. Figure 1: error vs n, three estimators, both crossing points marked
4. Figure 2: optimal blend weight vs n, empirical and analytic overlaid
5. Results table: n*_analytic, n*_empirical, and the signed gap, per metric, with confidence intervals
6. `LIMITATIONS.md` written before the discussion section, not after

## 10. Sequencing

Order matters, and two of these steps are ordering constraints rather than preferences.

1. **Rewrite the novelty framing first** (section 2), before any code. It costs a day and it is the difference between a result and a dismissed result.
2. **Submit the Dog Aging Project application now**, in parallel with step 1. Weeks of lead time; it is the long pole on the whole programme.
3. **Freeze the pre-registration**, including n*_analytic, before the first modelling run.
4. **Run Lahman.** It stands on its own and it is downloadable today.
5. **Fold in the second domain when access clears.** Baseball is the demonstration; the second domain is what turns it into an argument, because invariance across different noise structures is the part that does not fall out of a closed form.

### Publication discipline

A single-domain result is a paper. A two-domain invariance is a position. Do not spend the second on the first.

Concretely: the cross-species framing, and any title built on it, is **reserved until both curves exist**. Promising invariance in a title and delivering one domain is worse than a modest title delivering fully. What carries weight is not having had the idea of crossing dogs, baseball and hiring; it is being the person who produced the number. The first can be told, the second can be checked.

Until then, the existing essay series stands on the synthetic benchmark and says so, which it already does honestly.

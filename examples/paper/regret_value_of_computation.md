---
title: "What might have been is what thinking is worth: Regret as the value of computation"
authors:
  - "Ingrid A. Solvang^1"
  - "Rafael D. Mbeki-Hart^2"
  - "Clio M. Ashdown^1"
affiliations:
  - "^1Department of Psychology, Larchmont University"
  - "^2Center for Affect and Computation, Ashworth College"
masthead: |
  Acta Metrologica Pannonica (New Series)
  2026, Vol. 1, No. 1, 1–15
running_head: "Regret as the value of computation"
short_authors: "Solvang, Mbeki-Hart, and Ashdown"
abstract: |
  Regret has been studied as an emotion, as a counterfactual judgment, and
  as a learning signal. We propose that it is also a quantity of
  computational interest: the expected regret of a decision maker's best
  action is exactly the expected value of perfect information, and
  therefore an upper bound on the value of any further thought. On this
  view anticipated regret tells a bounded agent when deliberation might
  pay, experienced regret teaches it how much deliberation usually pays,
  and the choice among emotion-regulation strategies is a choice among
  computations of different cost. We derive a stopping rule for
  deliberation from the identity, show that counterfactual simulation
  provides an unbiased estimate of the quantity it requires, and report an
  experiment (*N* = 186) in which participants' decisions to pay for
  information followed the rule, shifted under high arousal as a rising
  cost of computation predicts, and were further predicted by anticipated
  regret over and above its normative value. We interpret this last result
  as emotion regulation, and therefore as support.
keywords: "regret; counterfactual simulation; value of computation; emotion regulation; resource-rational analysis; metareasoning"
author_note:
  - "This article is fictional. It was written to show the cogra package. Its authors, institutions, journal, experiment, and data do not exist, and neither do the papers by Marchetti and Oyelaran (2018), Teleki and Voss (1914), and Ulthy (1929), the milliwist, or Voss & Kähler Apparatebau. The other references are real works, cited for what they report. Theorem 1 is the textbook identity between expected opportunity loss and the expected value of perfect information (Howard, 1966)."
  - "We thank Voss & Kähler Apparatebau GmbH, Jena, for the loan of a Model 44-B (\"The Quiet Spindle\"), which we did not use."
  - "Correspondence concerning this article should be addressed to Ingrid A. Solvang, Department of Psychology, Larchmont University, enclosing four ounces of unsalted butter, wrapped in waxed paper, for the night-watchman's dog."
first_page_foot: "An example set with cogra.paper; not a published article."
---

# Introduction

Regret has an unusually crowded biography. Its first measurers used a
torsion balance. Ulthy (1929) reported that rooms in which an engagement
had been broken off weighed measurably more than rooms in which people said
what they meant and left when they were finished (see also Teleki & Voss,
1914), and proposed the milliwist as the unit of what he called *Specific
Almost*. The program did not survive replication, or the flooding of the
type-cellars at Pécs in 1941, and its successors have been more modest. To
decision theorists regret is the gap between what one got and what one could have had; to students of
counterfactual thought it is the product of imagining a world that did not
happen (Kahneman & Miller, 1986); to affective scientists it is an emotion
with a characteristic appraisal, an aversive feel, and a regulatory career
of its own (Zeelenberg & Pieters, 2007); and to neuroscientists it is a
signal that the orbitofrontal cortex is required to produce (Camille et
al., 2004). More recently it has been treated as something people learn
from, in Bayesian models of learning from regret (Petrova, Gross, &
Gerstenberg, 2025). Each account is persuasive. Together they describe an
emotion that is judged, felt, regulated, and learned from, which is a lot
of work for one feeling to do without a common reason.

We propose the reason. Human cognition is shaped by limited time and
limited computation (Griffiths, 2020), and a bounded agent must keep
deciding whether to think further or to act (Russell & Wefald, 1991;
Lieder & Griffiths, 2017). We show that the quantity governing that
decision is, to the decimal, expected regret. Anticipated regret is the
agent's estimate of what more thought could be worth; experienced regret
is the evidence that updates the estimate; and regulating regret is
choosing which computation to run on it.

Emotions have been called irrational for some two thousand years. We
show that at least one of them is an estimator.

# Regret and the Value of Computation

## Definitions

An agent chooses an action $a$ whose payoff $Q(a, \theta)$ depends on an
uncertain state $\theta$ with posterior $p(\theta)$. Acting now, it takes the
Bayes action

$$a^* = \arg\max_{a}\; \mathbb{E}_{\theta}\big[Q(a, \theta)\big]. \tag{1}$$

The regret of that action, once $\theta$ is known, is the difference between
the best available payoff and the one obtained:

$$R(\theta) = \max_{a} Q(a, \theta) - Q(a^*, \theta) \;\ge\; 0. \tag{2}$$

A computation $\kappa$ (further deliberation, simulation, or inquiry) changes
the agent's posterior before it acts, at a cost $\mathrm{cost}(\kappa)$. Its
value of computation (VOC) is the expected improvement in the payoff of the
chosen action, net of cost (Russell & Wefald, 1991; Lieder & Griffiths,
2017).

## The Regret Identity

**Theorem 1.** The expected regret of the Bayes action equals the expected
value of perfect information,

$$\begin{aligned} \mathbb{E}_{\theta}\big[R(\theta)\big] &= \mathbb{E}_{\theta}\Big[\max_{a} Q(a, \theta)\Big] \\ &\quad - \max_{a}\, \mathbb{E}_{\theta}\big[Q(a, \theta)\big] \\ &= \mathrm{EVPI}, \end{aligned} \tag{3}$$

and for every computation $\kappa$,

$$\mathrm{VOC}(\kappa) \;\le\; \mathbb{E}_{\theta}\big[R(\theta)\big] - \mathrm{cost}(\kappa). \tag{4}$$

*Proof.* Equation 3 follows from Equation 2 by linearity of expectation
and the definition of $a^*$. For Equation 4, no computation can yield more
than knowing $\theta$ outright, because the expected maximum of a conditional
expectation is at most the expected maximum of the quantity itself
(Jensen's inequality applied to the convex function $\max$). ∎

The theorem is old (Howard, 1966). What is new is the observation that
people already compute it and have a word for it.

**Corollary 1 (the regret stopping rule).** If anticipated regret does not
exceed the cost of a computation, the computation is not worth running.

The corollary gives anticipated regret a job. It is not a forecast of
future suffering that happens to influence choice; it is the bound that
tells a bounded agent when to stop thinking.

## A Worked Case

Let one action (moving to Zurich) pay $\theta$ relative to the other
(staying in Sopron), which pays nothing, with
$\theta \sim \mathcal{N}(\mu, s^2)$. With $z = |\mu| / s$,

$$\mathbb{E}\big[R\big] = s\,\big[\phi(z) - z\, \Phi(-z)\big], \tag{5}$$

where $\phi$ and $\Phi$ are the standard normal density and distribution
functions. Anticipated regret grows with uncertainty $s$ and falls as the
better option becomes obvious, peaking at $s / \sqrt{2\pi}$ when the two
options are tied. People should therefore deliberate most over close calls
made under uncertainty, which is a finding the field has made many times
and which we are pleased to have predicted.

## Estimating Regret by Counterfactual Simulation

The agent need not compute Equation 3 in closed form. It can imagine.
Counterfactual simulation, in which people judge what would have happened
by mentally running the world forward under an alternative, accounts well
for human causal judgment (Gerstenberg, Goodman, Lagnado, & Tenenbaum,
2021). Applied to choice, it suggests drawing $k$ imagined states from the
posterior and averaging the regret each would bring:

$$\hat{R}_k = \frac{1}{k} \sum_{i=1}^{k} \Big[ \max_{a} Q(a, \theta_i) - Q(a^*, \theta_i) \Big], \tag{6}$$

with each $\theta_i$ drawn from $p(\theta)$.

**Lemma 1** (Marchetti & Oyelaran, 2018). $\hat{R}_k$ is an unbiased
estimator of expected regret for every $k \ge 1$.

A resource-rational agent that must decide whether to think can thus
decide by imagining what might have been, and can do so with a single
imagined alternative. It will be noisy, but it will not be biased, which
is more than can be said for most of its other estimates.

## Learning From Regret

An agent that keeps acting learns how much thinking usually pays. Let
$\hat{E}_t$ be its running estimate of expected regret in a context, and
$r_t$ the regret it experiences after trial $t$. The simplest learner updates
by prediction error,

$$\hat{E}_{t+1} = \hat{E}_t + \eta\, (r_t - \hat{E}_t), \tag{7}$$

which is the Rescorla–Wagner rule applied to the learner's own
disappointment. Experienced regret is therefore a teaching signal for
metareasoning: an agent that regrets often in a context should learn to
deliberate there, and one that never regrets should learn to stop
bothering. Ulthy (1929) held that an unchosen option retains a floor of
0.86997 of its prior weight indefinitely. Equation 7 makes the more modest
claim that its regret is forgotten at rate $\eta$, and only when there is
something to learn.

## Emotion Regulation as Strategy Selection

Regulation strategies differ in what they compute. Reappraisal reconstrues
the situation, which is to say it runs further inference over $\theta$; it is
slow and effortful. Distraction withdraws attention, which is to say it
declines to compute; it is fast and cheap (Gross, 2015). Choosing between
them is a strategy-selection problem of the kind resource-rational
metareasoning addresses (Lieder & Griffiths, 2017), and recent work models
the choice between fast and slow regulation strategies computationally
(Petter et al., 2025). Equation 4 adds a prediction about intensity. If the
cost of computation rises with arousal, then under high intensity the
regret bound is less often worth paying, and agents should prefer
distraction; under low intensity, reappraisal. This is the pattern people
show (Sheppes, Scheibe, Suri, & Gross, 2011), and it follows here without
an additional assumption about emotion, unless one counts the assumption
that being upset makes thinking expensive, which we do not.

# Method

## Participants

Two hundred adults took part online. Fourteen were excluded under
preregistered criteria (failed comprehension checks or identical responses
on more than 90% of trials), leaving 186.

## Task

On each of 160 trials participants chose between a sure payoff and a
gamble whose value was drawn from a normal distribution with a displayed
mean and spread. Before choosing, they could pay a varying number of points
to reveal the gamble's value. On a random third of trials they first rated
how much they expected to regret choosing without looking, on a scale
from 0 to 100 that we report in milliwists (mWst), Ulthy's unit, as a
courtesy rather than a claim.
Trials were preceded by a high- or low-arousal image, within subjects.

### Analysis

For each trial we computed expected regret from Equation 5 and the
regret-bound margin, $\mathbb{E}[R] - \mathrm{cost}$. The stopping rule
predicts that participants pay to look exactly when the margin is
positive. We fit a hierarchical logistic model of the decision to look, with
the margin, arousal, and rated anticipated regret as predictors.

# Results

The decision to pay for information followed the regret bound (Figure 1).
In low-arousal trials, the margin at which participants were equally
likely to look or not was 0.21 points, 95% CI [0.05, 0.38], close to the
rule's value of zero. In high-arousal trials it rose to 1.08 [0.84, 1.33]:
participants demanded a larger excess of anticipated regret over cost
before they would think further, as a rising cost of computation predicts
(Table 1).

![Proportion of trials on which participants paid to reveal the gamble, as a function of the regret-bound margin (expected regret minus cost) and arousal. The vertical rule marks the stopping rule's threshold. Bars show 95% confidence intervals.](fig:looking)

Table: Hierarchical Logistic Model of the Decision to Pay for Information

| Predictor | Estimate | 95% CI |
|---|---:|---:|
| Threshold, low arousal | 0.21 | [0.05, 0.38] |
| Threshold, high arousal | 1.08 | [0.84, 1.33] |
| Slope on margin | 1.42 | [1.21, 1.66] |
| Rated anticipated regret (per 10 mWst) | 0.18 | [0.11, 0.25] |

Rated anticipated regret tracked its normative value, *r* = .46, 95% CI
[.38, .53]. It also predicted looking over and above the margin, which the
stopping rule does not allow. Participants, that is, sometimes paid to look
when looking was not worth it, apparently to avoid the regret rather than
to estimate it. We had not predicted this. On reflection it is a
regulation strategy, specifically situation modification, and a theory of
regret that predicts emotion regulation should not be embarrassed to find
some.[^1] Situation modification has a long history in this literature.[^2]

# Discussion

We began with an emotion asked to do too many jobs and have argued that
the jobs are one job. Expected regret is the value of perfect information,
and so it bounds the value of every computation a bounded agent might run.
Anticipating regret is estimating that bound; simulating what might have
been is how the estimate is made; learning from regret is calibrating it;
and regulating regret is choosing which computation to buy.

*Affect as the currency of bounded rationality.* Resource-rational
analysis has so far been conducted mostly in the currency of time and
effort. The present account suggests that some of its accounting is done in
feelings. If so, other affective states may be found to estimate other
terms of the value of computation, and the familiar opposition between
emotion and deliberation will turn out to be a division of labor in which
emotion keeps the books.

*Counterfactual simulation.* The theory explains why regret should
depend on how easily the better outcome can be imagined, since imagined
alternatives are the samples in Equation 6, and it predicts that people
whose simulations are more variable will regret more erratically without
regretting more on average. It also explains why the regrets people keep
are mostly about what they did not do (Gilovich & Medvec, 1995). A letter
never sent, or a postscript that reached the back of the teeth and was
swallowed in favor of a remark about the weather, leaves its alternative
unobserved. Its regret is never resolved by learning what happened, so
Equation 7 never receives the error that would let it decay. Ulthy's floor,
on this reading, was real, but it was a fact about missing data rather than
about rooms.

*Limitations.* The account assumes that people represent their
uncertainty, that payoffs are commensurable, and that the cost of
computation can be measured on the same scale as regret. All three are
idealizations. They limit how closely people can follow the stopping rule,
not whether the rule is the right standard, which Theorem 1 settles.

Regret has long been described as the emotion of what might have been. We
suggest that it is also the emotion of what thinking would have been
worth, and that people have been computing the value of computation for
as long as they have been sorry.

# References

Camille, N., Coricelli, G., Sallet, J., Pradat-Diehl, P., Duhamel, J.-R., & Sirigu, A. (2004). The involvement of the orbitofrontal cortex in the experience of regret. *Science, 304*, 1167–1170.

Gerstenberg, T., Goodman, N. D., Lagnado, D. A., & Tenenbaum, J. B. (2021). A counterfactual simulation model of causal judgments for physical events. *Psychological Review, 128*, 936–975.

Griffiths, T. L. (2020). Understanding human intelligence through human limitations. *Trends in Cognitive Sciences, 24*, 873–883.

Gilovich, T., & Medvec, V. H. (1995). The experience of regret: What, when, and why. *Psychological Review, 102*, 379–395.

Gross, J. J. (2015). Emotion regulation: Current status and future prospects. *Psychological Inquiry, 26*, 1–26.

Howard, R. A. (1966). Information value theory. *IEEE Transactions on Systems Science and Cybernetics, 2*, 22–26.

Kahneman, D., & Miller, D. T. (1986). Norm theory: Comparing reality to its alternatives. *Psychological Review, 93*, 136–153.

Lieder, F., & Griffiths, T. L. (2017). Strategy selection as rational metareasoning. *Psychological Review, 124*, 762–794.

Marchetti, A. L., & Oyelaran, T. (2018). Unbiased estimation of expected regret by simulated alternatives. *Journal of Mathematical Psychology, 85*, 41–49.

Petrova, K., Gross, J. J., & Gerstenberg, T. (2025). Learning from "what might have been": A Bayesian model of learning from regret. In *Proceedings of the 47th Annual Meeting of the Cognitive Science Society* (pp. 5845–5851).

Petter, J., Mehta, A., Petrova, K., Kindt, M., Sheppes, G., Haslbeck, J. M. B., & Gross, J. J. (2025). Emotion regulation, fast or slow: A computational model of strategy choice. *Emotion, 25*, 1273–1292.

Russell, S., & Wefald, E. (1991). *Do the right thing: Studies in limited rationality.* Cambridge, MA: MIT Press.

Sheppes, G., Scheibe, S., Suri, G., & Gross, J. J. (2011). Emotion-regulation choice. *Psychological Science, 22*, 1391–1396.

Teleki, Á., & Voss, F. (1914). On the apparent weight gain of silver spoons in houses where an engagement has been broken off. *Acta Metrologica Pannonica, 4*, 88–112.

Ulthy, K. (1929). A lemma concerning three-body nostalgia in bounded cylinders, with remarks on the constant 0.86997. *Acta Metrologica Pannonica, 11*, 402–419.

Zeelenberg, M., & Pieters, R. (2007). A theory of regret regulation 1.0. *Journal of Consumer Psychology, 17*, 3–18.

[^2]: The standard intervention for two colleagues politely not mentioning the same stain on a shared ceiling is for one of them to point at it and say aloud what it looks like (Teleki & Voss, 1914, p. 97, who recommend "Corsica").
[^1]: Readers who regard this as having it both ways are invited to compute the expected regret of rejecting the theory on these grounds.

# ML Fundamentals, Part 2: Linear & Logistic Regression, From First Principles

Part 1 established the bias-variance lens — underfitting vs. overfitting, train/val/test
splits, and L1/L2 regularization as a general idea. This part puts the first real model
family under that lens: linear regression and its classification sibling, logistic
regression — simple enough to derive from scratch, and important because every mechanism
introduced here (a loss function, gradient descent, regularization) reappears, essentially
unchanged, inside every more sophisticated model the rest of this series covers.

## Linear Regression as the Simplest Possible Model

**The problem, in plain terms**: you have some numbers describing a thing (a house's
square footage, its number of bedrooms, its age) and you want to predict another number
about it (its sale price). You don't have a formula — you only have a pile of past
examples where you know both the inputs and the actual price. Somehow you need to turn
that pile of examples into a rule you can apply to a brand-new house you've never seen.

**The mechanism**: the simplest possible rule is a weighted sum — multiply each input by
some number (a "weight") that says how much that input matters, add them all up, and add
one more constant on top (the "intercept," what you'd predict if every input were zero).
For a house, that might look like: price ≈ (weight₁ × square footage) + (weight₂ ×
bedrooms) + (weight₃ × age) + intercept. "Linear" just means this and nothing more — no
input is squared, multiplied by another input, or passed through anything fancy; it's a
straight-line relationship in however many dimensions your inputs span.

**Why this is the right place to start**: the assumption underneath it is genuinely
simple and checkable — "more square footage, roughly proportionally more expensive" is
exactly the kind of claim a linear model encodes. It won't be true for everything (price
almost certainly doesn't keep climbing in a perfectly straight line forever — a 10,000
sq ft house isn't literally ten times a 1,000 sq ft house's price), but as a first
approximation over a reasonable range, it's often close enough to be useful, and it's the
model whose weights you can actually read and sanity-check by eye: "each extra bedroom
adds about $15,000" is a sentence a human can reason about, unlike the weights buried
inside a deep neural network.

**The actual question a linear model has to answer** is: out of the infinitely many
possible weight combinations, which one best fits the examples you actually have? That
question — "best fits, by what measure?" — is exactly what the next section answers.

## The Loss Function, and Why Squared Error Specifically

**The problem**: "best fits" is meaningless until you define what you're measuring. You
need a single number that tells you how wrong a given set of weights currently is, so
that "better" has a precise meaning: a lower number. That single number is called a
**loss function** (or cost function) — it's not specific to linear regression at all,
it's the general contract every trainable model in this entire series makes: pick some
way to score "how wrong is the model right now," then find the settings that make that
score as small as possible.

**The mechanism, specifically for regression**: for every example, compute the error —
predicted price minus actual price — then square it, then average that across all
examples. This is **Mean Squared Error (MSE)**. Squaring does three genuinely useful
things at once, worth naming precisely rather than taking on faith: it makes every error
positive (a $50,000 overestimate and a $50,000 underestimate are equally bad, and adding
them shouldn't cancel them out to zero); it penalizes large errors disproportionately
more than small ones (being off by $100,000 is treated as *four times* as bad as being
off by $50,000, not twice as bad — often the right instinct, since one wildly wrong
prediction is usually worse than several mildly wrong ones); and it's smooth and
differentiable everywhere, which matters enormously for the next section, since gradient
descent needs to compute a slope, and a function with sharp corners (like plain absolute
error) doesn't have a well-defined slope exactly at the corner.

**Illustrative worked example** (numbers are approximate, chosen to make the arithmetic
easy to follow, not to represent a real dataset): say a model predicts three houses at
$300k, $420k, and $250k, and the actual prices are $320k, $400k, and $260k. The errors
are −$20k, +$20k, and −$10k. Squared: 400, 400, and 100 (in units of thousands-squared).
The mean is 300 — that single number, 300, is the model's current loss on these three
examples. Change the weights, recompute, and if the new number is smaller, the new
weights fit the data better, full stop — that's the entire criterion.

## Gradient Descent, the Actual Mechanism

**The problem**: for plain linear regression with MSE, there happens to be a formula —
called the **closed-form (ordinary least squares) solution** — that directly computes the
exact best weights in one shot, no trial and error required. That's a genuinely nice
special case, but it only exists because MSE on a linear model produces a loss landscape
with one clean minimum you can solve for algebraically. The moment the model gets more
complex — logistic regression later in this same doc, decision trees in Part 3, neural
networks in Part 4 — that closed-form shortcut disappears entirely. You need a
general-purpose method that works for *any* differentiable loss, regardless of how
complicated the model underneath it is. That method is **gradient descent**, and it is,
without exaggeration, the single mechanism every model in this series is actually trained
with.

**The mechanism**: imagine the loss as a landscape — every possible combination of
weights is a point on a map, and the height at that point is how wrong the model is with
those weights. You want to find the lowest point. The **gradient** is the mathematical
name for the slope of that landscape at your current position — specifically, for each
weight, how much the loss would increase if you nudged that one weight up slightly,
holding everything else fixed. Gradient descent's rule is almost embarrassingly simple:
compute that slope, then take a small step in the *opposite* direction (downhill, since
you want the loss to decrease), then repeat from the new position.

**In plain English**: it's like walking down a hill in thick fog, where you can't see the
landscape at all — only feel the slope of the ground directly under your feet. You feel
which way is downhill from exactly where you're standing, take one step that way, then
feel again from your new spot, since the slope may have changed. You never get to see the
whole mountain at once; you only ever act on local information, one step at a time. That
"one step at a time, based only on local slope" property is exactly why training a model
is an iterative process that runs for many rounds, rather than a single calculation.

**The learning rate**: how big a step do you take each time? That size is called the
**learning rate**, and getting it wrong in either direction has a real, nameable failure
mode. Too large, and you can overshoot the bottom of a valley entirely, land higher up on
the opposite slope, and bounce back and forth — in the worst case the loss actually grows
each step instead of shrinking, called **diverging**. Too small, and you crawl toward the
minimum so slowly that training takes an impractically long time, or gets stuck making
imperceptible progress before you run out of patience or compute budget. In practice this
is one of the first knobs anyone tunes when a model trains badly, and it's exactly this
mechanism that "learning rate too high/too low" is describing.

**Batch, stochastic, and mini-batch**: computing the exact gradient the way described
above technically means averaging over *every* training example before taking even one
step — called **batch gradient descent**. For a dataset with millions of examples, that's
enormously expensive per step. The opposite extreme, **stochastic gradient descent
(SGD)**, estimates the gradient from just *one* random example at a time and steps
immediately — much faster per step, but each individual step is a noisy, rough estimate
of the true downhill direction rather than the exact one. The practical answer nearly
everyone actually uses is **mini-batch gradient descent**: estimate the gradient from a
small random subset (say, 32 or 256 examples) at a time, striking a balance between the
per-step cost of batch and the noisiness of pure SGD. This is worth naming precisely
because it's not a linear-regression-specific detail — mini-batch gradient descent
(usually a variant like Adam or RMSprop that also adapts the step size automatically) is
the literal mechanism inside every PyTorch or TensorFlow training loop you'll encounter
starting in Part 4, training networks with millions or billions of weights the exact same
way this section describes training two or three.

## From Linear to Logistic — the Classification Problem

**The problem**: linear regression predicts a price, a temperature, a continuous
quantity — any real number, positive or negative, from small to huge. But a huge class of
real problems aren't "predict a number," they're "predict a yes/no": will this customer
churn, is this transaction fraudulent, does this scan show a tumor. What you actually want
out of the model isn't an arbitrary number — it's a **probability**, a value that's
always between 0 and 1, where 0 means "definitely no" and 1 means "definitely yes." A
plain linear combination of weights and inputs can spit out −40 or +9,000, neither of
which means anything as a probability.

**The mechanism**: take that same linear combination — same weighted sum, same intercept,
computed exactly the way Part 2's first section described — and pass it through the
**sigmoid function**, which squashes any real number into the open interval between 0 and
1. Concretely, sigmoid produces an S-shaped curve: very negative inputs get squashed
toward 0, very positive inputs get squashed toward 1, and inputs near zero land near 0.5,
with the steepest, most sensitive part of the curve right in that middle region. This
specific shape is exactly what you want from a confidence-producing function: when the
underlying linear score is strongly one way or the other, sigmoid commits to a confident
prediction near 0 or 1; when the linear score is ambiguous, sigmoid reports genuine
uncertainty near 0.5, rather than reporting false confidence either way. A model that
computes a linear combination and then applies sigmoid to it is called **logistic
regression** — despite the name, it's a classification method, not a regression one; the
name is a historical artifact from the "logistic function," which is another name for
sigmoid.

**Worth naming for what's coming next**: a single logistic regression unit — a weighted
sum of inputs, followed by a squashing function — is *exactly* the mathematical
description of one artificial neuron. Part 4's neural networks are, structurally, many of
these exact units wired together in layers; nothing new is being invented there, the same
weighted-sum-then-squash mechanism from this paragraph is simply repeated and stacked.

## Log-Loss (Cross-Entropy), and Why Squared Error Is Wrong Here

**The problem**: MSE was the right loss for predicting a continuous price. It's the wrong
loss for scoring a probability prediction, for a first-principles reason worth actually
understanding rather than just accepting as a rule: squared error doesn't punish a
confidently *wrong* prediction nearly harshly enough. If the true label is "yes" (1) and
the model confidently predicts 0.01 (essentially certain "no"), squared error scores that
as (1 − 0.01)² ≈ 0.98 — a large number, but not dramatically larger than a merely
uncertain wrong guess. Combined with sigmoid's own S-shape, using squared error here also
produces a bumpy, non-convex loss landscape with multiple local dips — gradient descent
can get stuck in one of those dips, mistaking it for the true minimum.

**The mechanism**: **log-loss**, also called **cross-entropy**, replaces squared error
specifically for probability predictions. Its defining behavior is asymmetric and
deliberately harsh: as a confident prediction approaches the *wrong* answer, log-loss
grows toward infinity, not toward some bounded ceiling. Predicting 0.01 when the true
answer is 1 isn't merely "a large error" under log-loss, it's an *enormous* one — the loss
explodes precisely because the model claimed near-certainty and was completely wrong.
Predicting 0.4 when the answer is 1 is treated as a much smaller, more forgivable mistake,
since the model was at least admitting real uncertainty rather than confidently lying.
Paired with sigmoid, log-loss also produces a smooth, single-minimum (convex) landscape —
gradient descent on logistic regression reliably finds the actual best weights, without
the multiple-local-dip problem squared error would have introduced. This is the general
pattern worth carrying forward: **the choice of loss function is not incidental, it
encodes exactly what kind of wrongness you consider unacceptable** — and every deep
learning classifier in Part 4 onward still trains with some form of cross-entropy for
exactly this reason.

## Regularized Regression in Practice

**Tying back to Part 1**: L1 (Lasso) and L2 (Ridge) regularization, covered there as
general bias-variance tools, have a specific, concrete payoff when applied to linear or
logistic regression: real-world tabular data often has many correlated or redundant
features (a house dataset might have both "square footage" and "number of rooms," which
move together), and an unregularized model can assign wild, unstable weights across
correlated features that happen to fit the training noise rather than any real signal.
Ridge shrinks all weights smoothly toward zero, stabilizing the fit without eliminating
any feature outright. Lasso's L1 penalty does something qualitatively different and often
more useful in this exact setting: it can push some weights to *exactly* zero, effectively
performing automatic feature selection — the model tells you which inputs it decided
didn't matter enough to keep, rather than you having to guess up front. **ElasticNet**
combines both penalties, useful when you want some sparsity (Lasso's behavior) without the
instability Lasso alone can show when many features are highly correlated with each
other.

**The real tools**: scikit-learn's `LinearRegression`, `Ridge`, `Lasso`, `ElasticNet`, and
`LogisticRegression` are the default, practical starting point for nearly any tabular
prediction or classification task — fast to fit, easy to interpret, and a genuinely
reasonable baseline before reaching for anything more complex in Part 3 or Part 4. Worth
knowing as a separate, useful distinction: scikit-learn's implementations are
**prediction-first** — they're built to produce accurate point predictions efficiently,
not to tell you whether a given input's effect is statistically meaningful. When the
actual question is inferential — "is this coefficient really different from zero, and how
confident are we?" — **statsmodels** is the tool that reaches, providing p-values,
confidence intervals, and full hypothesis-testing machinery around the same underlying
linear/logistic models. Reaching for scikit-learn versus statsmodels is really a question
of what you're trying to answer: "what will this be" versus "can I trust that this factor
actually matters."

## Designing and Operating From First Principles

1. Is the relationship I'm modeling actually plausible as a straight line, at least over
   the range of data I care about — or am I reaching for linear regression out of
   familiarity rather than because the linear assumption is defensible here?
2. Have I picked a loss function that actually reflects the kind of wrongness I care
   about — squared error for a continuous target, log-loss for a probability — or have I
   defaulted to one without asking whether it matches the problem?
3. If training is unstable or not converging, have I checked the learning rate first,
   before assuming the model or the data is the problem?
4. Am I using batch, stochastic, or mini-batch gradient descent, and does that choice
   actually match my dataset size and compute budget, or is it an unexamined default?
5. Do I have many correlated features, and if so, have I reached for L1/L2/ElasticNet
   deliberately, understanding what each one actually does differently, rather than
   applying "some regularization" as an unexamined ritual?
6. Am I trying to make an accurate prediction, or trying to understand whether a factor
   genuinely matters — and have I picked scikit-learn or statsmodels accordingly, rather
   than assuming one tool answers both questions equally well?

## Key Takeaways

- **Linear regression is a weighted sum of inputs plus an intercept** — its whole appeal
  is that the weights are directly interpretable, unlike almost every model that follows
  it in this series.
- **A loss function is a single number scoring how wrong a model currently is** — Mean
  Squared Error is the regression-specific choice, and it wins largely because squaring
  makes it always positive, differentiable, and appropriately harsh on large errors.
- **Gradient descent is the general-purpose training mechanism behind essentially every
  model in this series**, not just linear regression — it works by repeatedly measuring
  the local slope of the loss and stepping downhill, exactly like walking down a foggy
  hill by feel.
- **The learning rate controls step size, and getting it wrong has two distinct,
  nameable failure modes**: too large diverges/overshoots, too small crawls
  impractically slowly.
- **Mini-batch gradient descent is the real-world default**, balancing the cost of full
  batch descent against the noise of pure stochastic descent — and it's the literal
  mechanism inside PyTorch/TensorFlow training loops covered starting in Part 4.
- **Logistic regression is a linear combination passed through sigmoid** — structurally
  identical to a single artificial neuron, which is exactly what Part 4's neural
  networks are built out of, stacked and repeated.
- **Log-loss exists because squared error doesn't punish confident wrongness harshly
  enough**, and produces a smoother, single-minimum loss landscape when paired with
  sigmoid — the choice of loss function always encodes what kind of mistake you consider
  worst.
- **Ridge shrinks all weights smoothly; Lasso can zero some out entirely (automatic
  feature selection); ElasticNet blends both** — a concrete, practical payoff of Part 1's
  general regularization idea.
- **scikit-learn is prediction-first; statsmodels is inference-first** — the right choice
  depends on whether the actual question is "what will this be" or "does this factor
  really matter."

## Quick Self-Check

- Why does squaring the error do three separate useful things at once, rather than just
  making errors positive — name all three.
- Why does plain linear regression have a closed-form solution while logistic regression
  does not, and why does that difference matter for every more complex model that comes
  later in this series?
- Explain gradient descent using the foggy-hill analogy, then explain it again using the
  precise vocabulary (gradient, learning rate, step) — do both versions describe the same
  mechanism?
- What specifically goes wrong if the learning rate is set far too high? Far too low?
- Why is mini-batch gradient descent the practical default rather than pure batch or pure
  stochastic descent?
- Why can't a plain linear combination of weights and inputs be used directly as a
  probability, and what specific property of sigmoid fixes that?
- Explain, using the "confidently wrong" idea, why squared error is a poor loss function
  for a probability prediction and log-loss is a better one.
- What is the concrete, structural connection between logistic regression and a single
  artificial neuron?
- You have twenty features and suspect several are redundant. Would you reach for Ridge,
  Lasso, or ElasticNet, and why?
- Your task is to determine whether a marketing campaign genuinely increased sales, not
  just to predict future sales. Would you reach for scikit-learn or statsmodels, and why?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Mechanism-first framing (the default for "how does logistic regression work"
  questions):** "Logistic regression is a linear combination of the inputs, squashed
  through sigmoid into a 0-to-1 probability, trained with log-loss via gradient
  descent — every piece of that sentence is doing specific, necessary work, not just
  jargon."
- **Loss-function framing (good for showing you understand *why*, not just *what*):**
  "The loss function is the whole ballgame — it's the single number that defines what
  'good' even means for this model. Squared error and log-loss aren't interchangeable;
  each one encodes a different idea of what kind of mistake is worst."
- **Foundational framing (good for connecting this to deep learning later in an
  interview):** "A logistic regression unit — weighted sum, then a squashing function —
  is structurally identical to one artificial neuron. Neural networks aren't a different
  idea, they're this exact mechanism stacked into layers."
- **Practical-tooling framing (good for demonstrating hands-on judgment, not just
  theory):** "For a quick, interpretable baseline I'd reach for scikit-learn's
  LogisticRegression; if the actual question is whether a coefficient is statistically
  meaningful rather than just predictive, that's exactly when I'd switch to statsmodels
  instead."

### Vocabulary Builder

**Technical shorthand:**

- **loss function** (n. phrase) — a single number scoring how wrong a model's current
  predictions are; every trainable model is defined by which one it minimizes.
  *"MSE and log-loss are both loss functions, just suited to different kinds of
  targets."*
- **gradient descent** (n. phrase) — the general iterative training method: compute the
  loss's local slope with respect to each weight, step in the opposite direction, repeat.
  *"Every model from here on is trained with some flavor of gradient descent."*
- **learning rate** (n. phrase) — the step size gradient descent takes each iteration;
  too large diverges, too small crawls. *"We had to cut the learning rate in half once
  training started oscillating."*
- **mini-batch** (n. phrase) — a small random subset of training examples used to
  estimate the gradient at each step, balancing cost against noise. *"Training runs in
  mini-batches of 256 examples at a time."*
- **sigmoid function** (n.) — squashes any real number into the (0, 1) interval,
  producing an S-shaped curve; the mechanism that turns a linear score into a
  probability. *"Sigmoid is what turns logistic regression's raw score into something
  you can actually read as a confidence."*
- **cross-entropy / log-loss** (n. phrases) — the classification-specific loss that
  penalizes confidently wrong predictions especially harshly. *"Log-loss explodes as a
  confident prediction gets more wrong, which is exactly the behavior you want."*
- **regularization: Ridge / Lasso / ElasticNet** (n. phrases) — L2, L1, and combined
  penalties on model weights; Ridge shrinks smoothly, Lasso can zero weights out
  entirely (feature selection), ElasticNet blends both.

**Expressive phrases:**

- **"…the loss function is what defines what 'good' even means here"** — a fluent way to
  redirect a question about model performance back to first principles.
- **"…punish confident wrongness, not just wrongness"** — a precise, spoken way to
  explain why log-loss beats squared error for classification.
- **"…it's one artificial neuron, structurally"** — the fastest way to connect classic ML
  to deep learning in an interview without over-explaining.

---

**Previous:** [Part 1: Bias-Variance Trade-off & the ML Workflow](01_bias_variance_and_the_ml_workflow.md)  |  **Next:** [Part 3: Decision Trees, Bagging, and Boosting](03_decision_trees_and_ensembles.md)

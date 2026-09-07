# ML Fundamentals, Part 3: Decision Trees, Bagging, and Boosting

Part 1 established the bias-variance trade-off as the lens for judging any model; Part 2
built the simplest possible model family — a straight line, bent into a probability with a
sigmoid — as a deliberately high-bias-prone baseline. This part introduces a model family
that attacks the opposite failure mode by default, and then shows two genuinely different
ways of turning a pile of these models into something better than any one of them alone.

## A Single Decision Tree, From First Principles

**The problem, precisely**: a linear model assumes the relationship between inputs and the
target is a straight line (or a straight line bent through a sigmoid, for classification).
Real data is often not that polite. Whether a loan applicant defaults might depend on income
*and* debt *together* in a way no single straight line can capture — someone with high
income and high debt might behave completely differently from someone with high income and
low debt, and a linear model, which can only add up weighted contributions, structurally
cannot represent "the effect of income depends on debt" without someone manually engineering
an interaction term first.

**In plain English**: think about how a doctor actually diagnoses a patient, or how you'd
play the game of "20 Questions." You don't try to guess the answer in one shot from a
formula — you ask a sequence of yes/no questions, and each answer narrows down which
question makes sense to ask next. "Is the patient running a fever?" — if yes, "is there a
rash?" — if no, "how long has the fever lasted?" Each branch of questions can lead somewhere
completely different from another branch, which is exactly the "effect depends on context"
behavior a straight line can't express.

**The mechanism**: a decision tree is literally that flowchart, learned from data instead of
written by a doctor. Starting from all the training examples at the root, the tree picks one
feature and one threshold (e.g., "is income > $50,000?") that best separates the data into
two groups, then repeats the same process independently inside each resulting group,
recursively, until some stopping condition is reached. The result is a tree of nested yes/no
questions, and a new example is classified (or has a value predicted) by walking down the
tree from the root, answering each question, until it lands in a leaf.

**Why it matters**: because each branch of the tree can ask completely different questions,
trees represent feature interactions automatically, with no manual feature-engineering step
required — the exact limitation Part 2's linear model structurally has.

## How a Split Is Actually Chosen — Information Gain and Gini Impurity

**The problem, precisely**: "pick the feature and threshold that best separates the data"
is hand-wavy until "best" has a number attached to it. At every single node, a tree has to
consider every feature and, for continuous features, every plausible threshold, and score
each candidate split somehow — there's no shortcut, this really is a search.

**The mechanism — impurity**: a node is "pure" if every example in it belongs to the same
class, and "impure" if it's a mix. **Gini impurity** measures exactly this: for a node with
class proportions p₁, p₂, ..., it's `1 - Σ pᵢ²`. A node that's 50/50 between two classes has
Gini impurity `1 - (0.5² + 0.5²) = 0.5` (illustrative, the maximum possible for two classes);
a node that's 100% one class has Gini impurity `1 - 1² = 0` (perfectly pure). **Entropy**
(from information theory) measures the same underlying idea — how mixed a node is — with a
different formula (`-Σ pᵢ log₂ pᵢ`); the two nearly always pick the same splits in practice,
and the choice between them is a minor implementation detail, not a conceptual one.

**Worked example, illustrative numbers**: suppose a node has 10 examples, 5 of each of two
classes — Gini impurity 0.5, maximally mixed. Splitting on some feature produces two child
nodes: one with 9 examples of class A and 1 of class B (Gini `1 - (0.9² + 0.1²) = 0.18`), the
other with 1 of class A and 9 of class B (Gini `0.18` again, symmetrically). The tree
computes a weighted average of the children's impurity and compares it to the parent's — the
drop from 0.5 down to roughly 0.18 is the **information gain** from this split. Among every
feature/threshold combination tried at this node, the tree picks whichever one produces the
largest gain, and repeats the whole search independently in each child.

**Why it matters**: this greedy, node-by-node search is the entire "learning" a decision tree
does — there's no gradient descent here (unlike Part 2), no global optimization over the
whole tree at once, just a local best-choice at every node. That greediness is efficient, but
it's also exactly why a single tree is not the best a tree-based method can do, as boosting
below makes concrete.

## Why a Single Deep Tree Overfits — Tying Directly to Part 1

**The problem, precisely**: nothing stops a tree from growing until every leaf contains a
single training example. At that point, training accuracy is 100% — and that's exactly the
warning sign Part 1 flagged: a model achieving zero training error by memorizing individual
examples, rather than learning the actual underlying pattern, is the textbook definition of
**high variance**. A tiny change to the training data — one different example, one outlier
removed — can produce a structurally different tree, because a single differing split near
the root cascades into completely different questions in every branch below it.

**The mechanism (regularizing a tree)**: unlike Part 1's L1/L2 penalty on a weight vector,
a tree has no weights to penalize — its complexity lives in its *structure*, so its
regularization is structural too. **Max depth** caps how many questions deep the tree can
go. **Min samples per leaf/split** refuses to split a node further once it's down to a
handful of examples (splitting 3 examples into groups of 2 and 1 is exactly the kind of
noise-fitting Part 1 warned about, not a real pattern). **Pruning** takes the opposite
approach — grow the full tree first, then cut back branches that don't improve validation
performance, using Part 1's validation set directly to decide what to keep.

**Why it matters**: a single tree, properly regularized, still tends to sit at a mediocre
point on the bias-variance curve — shallow enough to avoid pure memorization costs some of
the tree's ability to capture genuine interactions. The two ensemble techniques below exist
specifically because a *single* tree, at any depth setting, rarely gets the best of both
worlds — but a *crowd* of trees, combined the right way, can.

## Bagging and Random Forests — Reducing Variance by Averaging

**The problem, precisely**: a single unpruned tree is low-bias (flexible enough to fit
almost any pattern) but high-variance (wildly sensitive to which exact training examples it
saw). Part 1 established you can't drive bias and variance to zero simultaneously for one
model — but nothing says you're limited to *one* model.

**In plain English**: ask one person to estimate the number of jellybeans in a jar and
they'll likely be off by a lot, in either direction, depending on their particular guessing
quirks. Ask a hundred people and average their guesses, and the average is typically much
closer to the true count than almost any individual guess — the "wisdom of crowds" effect.
Individual errors that lean too high or too low in different, uncorrelated directions cancel
out in the average.

**The mechanism — bootstrap aggregating ("bagging")**: train many trees, each on a different
random resample of the training data drawn *with replacement* (a "bootstrap sample" — so
some original examples appear multiple times in one tree's training set, others not at all),
and average their predictions (or take a majority vote, for classification). **Random
Forest** adds one more deliberate randomization: at each split, instead of considering every
feature, each tree only considers a random subset of the features. This *decorrelates* the
trees from each other — without it, if one feature is unusually strong, nearly every tree
would pick it at the root and the trees would end up more similar to each other than
bagging alone would produce, weakening the averaging effect.

**Why it matters, precisely**: averaging many models reduces variance only to the extent the
models' errors are independent of each other — averaging ten identical trees gives you back
the exact same variance as one tree, since there's no independent noise to cancel. This is
the actual first-principles reason Random Forest deliberately decorrelates its trees rather
than just bagging plain trees: it's maximizing the variance-reduction bagging is trying to
achieve. Critically, averaging many low-bias trees keeps the ensemble's bias low too — you're
not making any individual tree simpler, just averaging away the noise in their individual
mistakes. This is Part 1's trade-off, exploited rather than just endured: bagging is
specifically a variance-reduction machine that leaves bias where it already was.

## Boosting and Gradient Boosting — Reducing Bias by Building Sequentially

**The problem, precisely**: bagging fixes variance, not bias — if every tree in the forest
is individually a bit too simple to capture some subtle pattern, averaging a hundred of them
still won't reveal that pattern, because averaging can't manufacture information no
individual model captured to begin with.

**The mechanism — the core contrast with bagging**: bagging trains many trees *in parallel*,
*independently*, on resampled data, and averages them. Boosting trains trees *sequentially*,
and each new tree is deliberately trained to fix what the current ensemble is still getting
wrong — not on a random resample, but specifically targeting the previous ensemble's errors
(technically, its **residuals**, the gap between its current predictions and the true
values). The final prediction is a weighted sum of every tree built so far, not a simple
average.

**Gradient boosting's mechanism, concretely**: at each step, the ensemble computes the
gradient of the loss function with respect to its *current predictions* (not, as in Part 2,
with respect to a weight vector) — this gradient tells you which direction each prediction
needs to move to reduce loss. A new, small tree is then trained to predict that gradient,
and added to the ensemble with a small weight (the **learning rate**, doing the same
job — controlling step size — as Part 2's gradient-descent learning rate, but here each
"step" is an entire new tree rather than a nudge to existing weights). Repeat for hundreds or
thousands of trees. This is a genuinely direct extension of Part 2's gradient descent: instead
of taking steps in "weight space," gradient boosting takes steps in "function space," where
each step is a small tree instead of a small weight update.

**Why it matters**: because each new tree specifically targets the ensemble's current
mistakes, the ensemble's bias keeps dropping as more trees are added — this is a
bias-reduction mechanism where bagging was a variance-reduction one. The trade-off: this
sequential, error-correcting process is exactly what makes boosted ensembles prone to
*overfitting* if allowed to run for too many rounds or with too high a learning rate — the
model starts correcting for noise in the training data, not just genuine signal, which is
why boosting libraries expose early stopping (watching validation loss, tying directly back
to Part 1's validation-set mechanism) as a first-class, load-bearing feature rather than an
afterthought.

**Real, current tools**: **XGBoost** (Extreme Gradient Boosting) is the implementation that
made gradient boosting the dominant technique on tabular data through the mid-2010s Kaggle
era — it adds explicit L1/L2 regularization on the tree structure itself (Part 1's
regularization concept, applied to trees) and a highly optimized, parallelized training
routine. **LightGBM** uses a histogram-based approach to choosing splits (bucketing
continuous features rather than considering every possible threshold), trading a small
amount of precision for a large speedup on big datasets. **CatBoost** specifically targets
categorical features, handling them natively with a specialized encoding scheme rather than
requiring the practitioner to one-hot-encode them by hand first. All three remain the
default reach for structured/tabular data as of 2025-2026, genuinely competitive with — and
usually faster to train than — the deep learning approaches Part 4 onward will cover.

## When to Reach for Trees/Ensembles vs. Linear/Logistic Regression

This is a real, practical decision, not just "ensembles are strictly better." Trees and
their ensembles capture non-linear interactions automatically, require little manual
feature engineering, and handle a mix of numeric and categorical features natively.
Linear/logistic regression remains the right default when: interpretability matters (a
single coefficient's sign and magnitude is far easier to explain to a stakeholder than a
thousand-tree ensemble's behavior); genuine statistical inference is the goal, not just
prediction (Part 2's mention of `statsmodels` for p-values and confidence intervals — trees
don't have an equivalent, well-understood inferential theory); the true relationship really
is close to linear, in which case a tree ensemble spends its extra flexibility fitting noise
it doesn't need to fit; or the dataset is small enough that a flexible ensemble's variance
reduction has too little data to actually work with.

## Designing and Operating From First Principles

1. Am I reaching for a decision tree/ensemble because the data genuinely has non-linear
   interactions, or out of habit — would a simpler linear model, with explicit interaction
   terms, actually be enough and more interpretable?
2. If a single tree is overfitting, have I actually diagnosed *which* lever fixes it —
   max-depth, min-samples-per-leaf, or pruning against a validation set — or am I randomly
   tweaking hyperparameters without a hypothesis?
3. Am I using bagging (Random Forest) or boosting (XGBoost/LightGBM/CatBoost) because I've
   diagnosed whether my problem is more of a bias problem or a variance problem — or did I
   just pick whichever one I've used before?
4. If I'm using a boosted model, do I have early stopping against a genuine validation set
   wired up, or am I trusting a fixed number of boosting rounds to be the right amount by
   luck?
5. Have I checked whether my features are correlated enough that Random Forest's
   feature-subsampling decorrelation is actually doing meaningful work, or is it subsampling
   from an already near-independent feature set for no real benefit?
6. Am I choosing a tree-based method specifically because I need interpretability
   (feature importances, SHAP values) — or because I actually need the raw predictive
   accuracy, in which case I should be honest that a tuned boosted ensemble is likely to
   outperform a single interpretable tree?

## Key Takeaways

- A decision tree is a learned sequence of yes/no questions, splitting the data at each node
  on whichever feature/threshold reduces impurity (Gini or entropy) the most — a greedy,
  node-by-node search, not a global optimization.
- A single tree grown to full depth is the textbook high-variance model — it can memorize
  every training example — and is regularized structurally (max depth, min samples per
  leaf, pruning against a validation set), not via a weight penalty.
- **Bagging** (Random Forest) trains many trees independently on bootstrap-resampled data
  and averages them, reducing *variance* by canceling out uncorrelated errors — it leaves
  bias roughly where each individual tree's bias already was.
- Random Forest's per-split random feature subsampling exists specifically to decorrelate
  the trees further than bagging alone would, since averaging only reduces variance to the
  extent the underlying errors are independent.
- **Boosting** (gradient boosting: XGBoost, LightGBM, CatBoost) trains trees sequentially,
  each one targeting the current ensemble's residual errors, reducing *bias* — a direct
  extension of Part 2's gradient descent, but taking steps in function space (new trees)
  instead of weight space.
- Boosting's error-correcting nature makes it prone to overfitting with too many rounds or
  too high a learning rate, which is why early stopping against a validation set is a
  first-class feature of every real boosting library, not an afterthought.
- Trees/ensembles trade away the interpretability and inferential theory (p-values,
  confidence intervals) that linear/logistic regression offers, in exchange for automatically
  capturing non-linear interactions with less manual feature engineering.

## Quick Self-Check

- Why can't a decision tree represent "the effect of income depends on debt" the way a
  linear model with no interaction terms structurally cannot — what does a tree do
  differently that a straight line can't?
- Walk through computing Gini impurity for a node that's 8 examples of class A and 2 of
  class B — is that node's impurity closer to a maximally pure node or a maximally impure
  one, and why?
- Why is a fully-grown, unpruned decision tree the textbook example of high variance rather
  than high bias, in Part 1's terms?
- Why does averaging ten *identical* trees not reduce variance at all — what does that tell
  you about what averaging is actually doing?
- Explain, precisely, why Random Forest's random feature subsampling at each split matters
  even though bagging already resamples the training data — what would go wrong without it?
- Why is boosting described as a bias-reduction technique and bagging as a variance-reduction
  technique — what in each mechanism specifically produces that difference?
- In what sense is gradient boosting a direct descendant of Part 2's gradient descent — what
  is the "gradient" actually computed with respect to, and what does a "step" mean here?
- Why does a boosting library treat early stopping as load-bearing rather than optional, in a
  way bagging-based Random Forest doesn't need nearly as urgently?
- Give a concrete scenario where you'd deliberately choose logistic regression over a tuned
  XGBoost model, even knowing the tree ensemble would likely score higher on raw accuracy.

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Bias-variance-payoff framing (the default for "why do ensembles work" questions):** "I'd
  frame bagging and boosting as two different answers to the bias-variance trade-off from
  first principles — bagging averages many independent, high-variance trees to cancel out
  their noise, which is a variance play, while boosting sequentially targets the current
  ensemble's residual errors, which is a bias play. They're not interchangeable tools for
  the same problem; they attack opposite failure modes."
- **Mechanism-continuity framing (good for showing this isn't disconnected from earlier
  fundamentals):** "Gradient boosting is genuinely the same gradient-descent idea from
  linear/logistic regression, just taking steps in function space instead of weight
  space — each new tree is fit to the gradient of the loss with respect to the current
  predictions, and added with a learning rate exactly like a weight update would be."
- **Practical decision-framework framing (good for a 'which model would you use' question):**
  "I'd default to a boosted tree ensemble like XGBoost or LightGBM for tabular data with
  likely feature interactions, but reach for logistic regression specifically when
  interpretability or actual statistical inference — not just prediction — is the goal, since
  a coefficient's sign and magnitude is far easier to defend to a stakeholder than a
  thousand-tree ensemble's behavior."
- **Wisdom-of-crowds framing (good for explaining bagging to a non-technical audience):** "A
  Random Forest is close to averaging many people's independent, slightly-off guesses at a
  jellybean count — no individual guess needs to be great, as long as the guesses aren't all
  wrong in the same direction, since the averaging is what cancels the noise out."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **Gini impurity / entropy** (n. phrases) — two near-equivalent measures of how mixed the
  classes are in a node; a tree picks whichever split most reduces this. *"The split with
  the highest information gain wins at this node."*
- **information gain** (n. phrase) — the drop in impurity from parent to weighted-average
  child after a split; the score a tree greedily maximizes at every node.
- **bootstrap sample** (n. phrase) — a resample of the training data drawn with replacement,
  the same size as the original, used to train one tree in a bagging ensemble.
- **bagging** (n., short for bootstrap aggregating) — training many models independently on
  bootstrap samples and averaging/voting their predictions; a variance-reduction technique.
- **boosting** (n.) — training models sequentially, each one correcting the current
  ensemble's residual errors; a bias-reduction technique.
- **residual** (n.) — the gap between an ensemble's current prediction and the true value;
  what each new boosting round is specifically trained to predict.
- **learning rate (in boosting)** (n. phrase) — the weight given to each newly-added tree's
  contribution to the ensemble; the same step-size role as Part 2's gradient-descent
  learning rate, just scaling a whole tree instead of a weight update.
- **early stopping** (n. phrase) — halting training once validation loss stops improving,
  the primary defense against a boosted ensemble overfitting with too many rounds.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…averaging cancels noise, sequencing corrects mistakes"** — a compact way to contrast
  bagging's variance reduction with boosting's bias reduction.
- **"…function space instead of weight space"** — a precise, fluent way to describe gradient
  boosting's relationship to ordinary gradient descent.
- **"…a coefficient you can defend versus a prediction you can't fully explain"** — a fluent
  framing for the interpretability trade-off between linear models and tree ensembles.

---

**Previous:** [Part 2: Linear & Logistic Regression, From First Principles](02_linear_and_logistic_regression.md) | **Next:** [Part 4: Neural Networks & Backpropagation, From First Principles](04_neural_networks_and_backpropagation.md)

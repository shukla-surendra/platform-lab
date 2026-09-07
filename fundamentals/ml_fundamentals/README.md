# ML Fundamentals

This section covers **Track 6 (ML Fundamentals)** from the interview prep plan: classic ML,
deep learning, and LLM specifics, at **breadth, not research depth** — enough to reason
about *why* an approach was chosen in an ML system design interview or to answer a follow-up
about model internals, not enough to pass a research-scientist interview.

It's a single continuous sequence, each part assuming the ones before it — read in order the
first time through:

1. **[Bias-Variance Trade-off & the ML Workflow](01_bias_variance_and_the_ml_workflow.md)** —
   the lens every other part gets viewed through: underfitting vs. overfitting, the
   bias-variance decomposition, train/val/test splits, regularization, learning curves.
2. **[Linear & Logistic Regression, From First Principles](02_linear_and_logistic_regression.md)**
   — the simplest model family: loss functions, gradient descent, the sigmoid/log-loss
   bridge from regression to classification.
3. **[Decision Trees, Bagging, and Boosting](03_decision_trees_and_ensembles.md)** — where
   bias-variance gets its clearest payoff: a single tree's variance problem, and how bagging
   (Random Forest) and boosting (XGBoost/LightGBM/CatBoost) fix it in opposite directions.
4. **[Neural Networks & Backpropagation, From First Principles](04_neural_networks_and_backpropagation.md)**
   — the bridge from classical ML into deep learning: why a single neuron is just logistic
   regression, why depth needs non-linearity, and the chain-rule mechanism that actually
   trains a multi-layer network.
5. **[CNNs and RNNs — Architectures for Structure](05_cnns_and_rnns.md)** — exploiting
   spatial structure (convolution, pooling) and sequential structure (recurrent hidden
   state, LSTM gating) — and the two specific RNN limitations that motivated what comes next.
6. **[The Transformer Architecture](06_transformer_architecture.md)** — self-attention,
   multi-head attention, positional encoding, and the encoder/decoder-only/encoder-decoder
   shapes underlying essentially every modern LLM.
7. **[LLM Fundamentals — Tokenization, Fine-Tuning, and Evaluation](07_llm_fundamentals.md)**
   — the capstone: tokenization, pretraining, a genuine fine-tuning-vs-RAG-vs-prompting
   decision framework, LoRA/QLoRA, quantization, and how to actually evaluate an LLM.

## How this relates to the rest of this repo

This tree covers **mechanism** — what's actually happening inside a model. The separate,
much larger [`system_design_foundation/01_ml_system_design/`](../system_design_foundation/01_ml_system_design/)
tree covers **systems** — how models get served, monitored, retrained, and operated at
scale in production (feature stores, canary rollouts, drift detection, LLMOps). Part 7's
closing section points specifically to
[`01_ml_system_design/11_llmops.md`](../system_design_foundation/01_ml_system_design/11_llmops.md)
for the production-operations layer built on top of the fine-tuning/RAG/quantization
mechanisms this tree explains — read this tree first if that one ever assumes ML vocabulary
you don't already have solid.

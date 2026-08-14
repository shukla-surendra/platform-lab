# PyTorch: `max`, `argmax`, Logits, and Softmax

## 1. `max` vs `argmax`

The first important distinction is simple:

- **`max` → gives the maximum value**
- **`argmax` → gives the index (position) of the maximum value**

```python
import torch

x = torch.tensor([10, 30, 20, 40, 15])

print(torch.max(x))       # tensor(40)
print(torch.argmax(x))    # tensor(3)
```

The tensor is:

```text
Index:   0   1   2   3   4
Value:  10  30  20  40  15
                  ↑
               maximum
```

So:

```text
max    → 40
argmax → 3
```

### Mental model

> `max` asks: **"What is the maximum value?"**

> `argmax` asks: **"Where is the maximum value?"**

---

# 2. What is a score?

In a machine-learning classification model, the neural network can produce several numbers.

For example:

```python
x = torch.tensor([2.0, 1.0, 0.1])
```

For now, simply think of these as **scores**:

```text
Class 0 → 2.0
Class 1 → 1.0
Class 2 → 0.1
```

A higher score means the model favors that class more.

If we only want to know which class has the highest score:

```python
torch.argmax(x)
```

gives:

```text
tensor(0)
```

Therefore:

```text
Class 0 wins
```

---

# 3. What is a logit?

In classification, the raw scores produced by the model before applying softmax are commonly called **logits**.

So:

```text
Neural Network
      ↓
[2.0, 1.0, 0.1]
      ↓
    logits
```

A useful mental model is:

> **Logits = raw scores produced by the model.**

They are **not probabilities**.

For example:

```text
Cat   → 2.0
Dog   → 1.0
Horse → 0.1
```

The numbers `2.0`, `1.0`, and `0.1` are just raw scores.

---

# 4. Why do we need softmax?

Suppose our model produces:

```text
Cat   → 2.0
Dog   → 1.0
Horse → 0.1
```

We can already find the winner using:

```python
torch.argmax(x)
```

which gives class `0`.

But sometimes we want more information than just the winner.

We may want a probability-like distribution:

```text
Cat   → 65.9%
Dog   → 24.2%
Horse →  9.9%
```

This is where **softmax** is useful.

> **Softmax converts raw scores/logits into a probability-like distribution across the classes.**

---

# 5. How does softmax convert scores into probabilities?

Consider:

```python
x = torch.tensor([2.0, 1.0, 0.1])
```

Softmax uses the exponential function:

```text
e^score
```

### Step 1: Exponentiate each score

```text
Score       e^score

2.0    →     7.39
1.0    →     2.72
0.1    →     1.11
```

### Step 2: Add them together

```text
7.39 + 2.72 + 1.11 = 11.22
```

### Step 3: Divide each value by the total

```text
7.39 / 11.22 = 0.659
2.72 / 11.22 = 0.242
1.11 / 11.22 = 0.099
```

Therefore:

```text
Class 0 → 0.659 → 65.9%
Class 1 → 0.242 → 24.2%
Class 2 → 0.099 →  9.9%
```

And:

```text
0.659 + 0.242 + 0.099 ≈ 1.0
```

---

# 6. The softmax formula

For each score:

```text
                 e^score_i
softmax_i = ─────────────────────
             Σ e^score_j
```

For our example:

```text
              e²
P(class 0) = ─────────────
             e² + e¹ + e⁰·¹
```

The important idea is:

```text
Raw scores
    ↓
Exponentiate
    ↓
Make values positive
    ↓
Divide by their total
    ↓
Values between 0 and 1
    ↓
Values sum to 1
```

---

# 7. Does softmax pick one?

**No.**

This was an important distinction.

Given:

```python
x = torch.tensor([2.0, 1.0, 0.1])
```

Softmax gives a value for **every class**:

```python
probabilities = torch.softmax(x, dim=0)

print(probabilities)
```

Approximately:

```text
tensor([0.659, 0.242, 0.099])
```

So:

```text
Class 0 → 65.9%
Class 1 → 24.2%
Class 2 →  9.9%
```

Softmax does **not** choose one class.

---

# 8. Then what actually picks one?

`argmax`.

```python
prediction = torch.argmax(x)

print(prediction)
```

Output:

```text
tensor(0)
```

So:

```text
softmax → gives probabilities for all classes
argmax  → picks the class with the highest value
```

---

# 9. Softmax + argmax

The complete conceptual flow is:

```text
             Neural Network
                    ↓
              Raw scores
               / logits
                    ↓
          [2.0, 1.0, 0.1]
                    ↓
                 softmax
                    ↓
          [0.659, 0.242, 0.099]
                    ↓
                argmax
                    ↓
                 Class 0
```

You can interpret it as:

> **Softmax tells us how the model's scores are distributed across the classes.**

> **Argmax tells us which class has the highest score/probability.**

---

# 10. Do we actually need softmax before argmax?

Interestingly, **no**.

Consider:

```python
x = torch.tensor([2.0, 1.0, 0.1])

torch.argmax(x)
```

The answer is:

```text
0
```

After softmax:

```python
probabilities = torch.softmax(x, dim=0)

torch.argmax(probabilities)
```

The answer is still:

```text
0
```

Why?

Because softmax preserves the ordering of the values.

```text
2.0 > 1.0 > 0.1

therefore

0.659 > 0.242 > 0.099
```

So:

```text
argmax(logits) == argmax(softmax(logits))
```

Therefore, if you only need the predicted class, you don't need to calculate softmax first.

---

# 11. Why use softmax then?

Because sometimes we don't only want the winner.

Compare:

### Model A

```text
Cat   → 99%
Dog   →  1%
Horse →  0%
```

The model strongly favors Cat.

### Model B

```text
Cat   → 36%
Dog   → 34%
Horse → 30%
```

The model still predicts Cat using `argmax`, but the scores are much closer.

Both models might produce:

```text
argmax → Cat
```

But softmax gives us a distribution showing how the scores compare.

---

# 12. Complete PyTorch example

```python
import torch

# Raw model outputs / logits
x = torch.tensor([2.0, 1.0, 0.1])

# max() gives the maximum VALUE
max_value = torch.max(x)

# argmax() gives the INDEX of the maximum value
max_index = torch.argmax(x)

# softmax() converts logits into a probability-like distribution
probabilities = torch.softmax(x, dim=0)

# argmax can then be used to select the highest-probability class
prediction = torch.argmax(probabilities)

print("Logits:        ", x)
print("Max value:     ", max_value)
print("Max index:     ", max_index)
print("Probabilities: ", probabilities)
print("Prediction:    ", prediction)
```

Conceptually:

```text
x = [2.0, 1.0, 0.1]

max(x)
  ↓
2.0

argmax(x)
  ↓
0

softmax(x)
  ↓
[0.659, 0.242, 0.099]

argmax(softmax(x))
  ↓
0
```

---

# 13. Final mental model

Keep these four concepts separate:

```text
MAX
 ↓
"What is the largest VALUE?"
```

```text
ARGMAX
 ↓
"WHERE is the largest VALUE?"
```

```text
LOGIT / SCORE
 ↓
"Raw number produced by the model."
```

```text
SOFTMAX
 ↓
"Convert raw scores into a probability-like
 distribution across the classes."
```

And the classification flow:

```text
Neural Network
      ↓
Raw scores / logits
      ↓
 ┌────┴─────┐
 ↓          ↓
argmax    softmax
 ↓          ↓
winner   probabilities
            ↓
          argmax
            ↓
          winner
```

## One-line summary

> **Logits are raw scores, `softmax` turns those scores into a probability-like distribution, `max` gives the largest value, and `argmax` gives the index of the largest value.**

## PyTorch syntax to remember

```python
torch.max(x)                 # maximum VALUE
torch.argmax(x)              # INDEX of maximum
torch.softmax(x, dim=0)      # probability distribution
```

**Important training note:** with PyTorch's `CrossEntropyLoss`, you normally pass the **raw logits directly** rather than applying softmax yourself. Softmax is commonly useful when you need to inspect or use the resulting probabilities during inference.

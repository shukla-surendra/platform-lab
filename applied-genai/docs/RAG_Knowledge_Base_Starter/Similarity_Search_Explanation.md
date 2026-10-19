# Similarity Search

## What is Similarity Search?

Similarity search is a technique for finding items that are **most
similar** to a query rather than requiring an exact match.

Traditional search asks:

> "Does this item contain the same words?"

Similarity search asks:

> "Does this item have the same meaning?"

------------------------------------------------------------------------

# Why is it Needed?

Traditional keyword search cannot understand semantics.

Example:

  ---------------------------------------------------------------------------
  Query          Keyword Search               Similarity Search
  -------------- ---------------------------- -------------------------------
  Artificial     Matches only documents       Also finds AI, Machine
  Intelligence   containing those exact words Learning, Deep Learning, etc.

  ---------------------------------------------------------------------------

------------------------------------------------------------------------

# Examples

## Example 1 -- Text Search

Documents:

``` text
1. I love programming in Python.
2. Python is widely used for AI.
3. I enjoy Italian cooking.
4. Machine learning uses neural networks.
```

Query:

``` text
Python for Artificial Intelligence
```

Similarity search may return:

``` text
1. Python is widely used for AI.
2. I love programming in Python.
3. Machine learning uses neural networks.
```

------------------------------------------------------------------------

## Example 2 -- Image Search

Upload a picture of a cat.

Instead of finding the exact same image, similarity search finds:

-   Cats
-   Kittens
-   Similar breeds
-   Similar colors

------------------------------------------------------------------------

## Example 3 -- Product Recommendation

If a customer likes:

``` text
MacBook Pro
```

Similarity search can recommend:

-   MacBook Air
-   Dell XPS
-   Lenovo ThinkPad

------------------------------------------------------------------------

# Embeddings

Modern similarity search converts every item into a numerical vector
called an **embedding**.

Example:

``` text
"I love Python"

↓

[0.12, -0.87, 0.45, ...]
```

Documents with similar meanings produce vectors that are close together.

------------------------------------------------------------------------

# Measuring Similarity

## Cosine Similarity

Most commonly used.

Formula:

``` text
Cosine(A,B) = (A · B) / (||A|| × ||B||)
```

Interpretation:

    Score Meaning
  ------- ---------------------
      1.0 Identical direction
      0.8 Very similar
      0.5 Somewhat related
      0.0 Unrelated
     -1.0 Opposite

------------------------------------------------------------------------

## Euclidean Distance

Measures straight-line distance between vectors.

Smaller distance means higher similarity.

------------------------------------------------------------------------

## Dot Product

Frequently used when embeddings are normalized.

Higher value means more similar.

------------------------------------------------------------------------

# Similarity Search Workflow

``` text
Query
   │
   ▼
Embedding Model
   │
   ▼
Query Vector
   │
   ▼
Vector Database
   │
   ▼
Nearest Neighbor Search
   │
   ▼
Top-K Similar Documents
```

------------------------------------------------------------------------

# Why Vector Databases?

Comparing a query against millions of vectors one-by-one is slow.

Vector databases use Approximate Nearest Neighbor (ANN) algorithms such
as:

-   HNSW
-   IVF
-   Product Quantization (PQ)

These dramatically speed up similarity search.

------------------------------------------------------------------------

# Similarity Search in RAG

``` text
User Question
      │
      ▼
Embedding Model
      │
      ▼
Query Embedding
      │
      ▼
Vector Database
      │
Similarity Search
      │
Retrieve Top-K Chunks
      │
      ▼
Large Language Model
      │
      ▼
Answer
```

------------------------------------------------------------------------

# Similarity Search vs Keyword Search

  Feature                  Keyword Search   Similarity Search
  ------------------------ ---------------- -------------------
  Exact words              ✅               ❌
  Semantic understanding   ❌               ✅
  Synonyms                 ❌               ✅
  Embeddings               ❌               ✅
  RAG support              Limited          Excellent

------------------------------------------------------------------------

# Key Takeaways

-   Similarity search finds the **most semantically similar** items.
-   It relies on **embeddings** instead of exact text matching.
-   Common similarity metrics are **Cosine Similarity**, **Euclidean
    Distance**, and **Dot Product**.
-   Vector databases make similarity search scalable.
-   It powers modern AI applications such as **RAG**, recommendation
    systems, image search, and semantic search.

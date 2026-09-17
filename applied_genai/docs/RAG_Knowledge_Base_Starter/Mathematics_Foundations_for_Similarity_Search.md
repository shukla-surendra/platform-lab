# Mathematics Foundations for Similarity Search

*A practical guide from first principles*

# Table of Contents

1.  Why Mathematics Matters
2.  Scalars, Vectors, and Matrices
3.  Coordinate Systems
4.  Vector Magnitude (Norm)
5.  Unit Vectors
6.  Distance vs Similarity
7.  Dot Product
8.  Cosine Similarity
9.  Euclidean Distance
10. Manhattan Distance
11. Angles Between Vectors
12. High-Dimensional Spaces
13. Embeddings
14. Why Embedding Models Are Needed
15. Nearest Neighbors
16. Ranking (Top-K)
17. Exact vs Approximate Search
18. Precision, Recall, and Recall@K
19. Curse of Dimensionality
20. Vector Databases
21. End-to-End Similarity Search Pipeline
22. Terminology Glossary

------------------------------------------------------------------------

# 1. Why Mathematics Matters

Computers cannot compare meanings directly.

Instead, every document, sentence, image, or piece of code is converted
into a vector (a list of numbers). Mathematics is then used to answer:

-   Which vectors are closest?
-   Which document is most relevant?
-   Which image looks most similar?

Without vector mathematics, semantic search would not exist.

------------------------------------------------------------------------

# 2. Scalars, Vectors, and Matrices

## Scalar

A single number.

Examples:

    5
    3.14
    -2

## Vector

An ordered collection of numbers.

    [2, 5]
    [1, 3, 8]

Each number is called a **dimension** or **feature**.

Think of a vector as a point in space.

## Matrix

A collection of vectors.

    [
     [1,2],
     [3,4],
     [5,6]
    ]

A vector database stores millions of vectors.

------------------------------------------------------------------------

# 3. Coordinate Systems

Imagine a city map.

          y
          ^
      4   |
      3   |      B
      2   |
      1 A |
      0-----------→ x

Point A=(1,1)

Point B=(3,3)

A vector represents the location of a point.

Embeddings work exactly the same way except they have hundreds or
thousands of dimensions instead of two.

------------------------------------------------------------------------

# 4. Vector Magnitude (Norm)

Magnitude tells us how long a vector is.

Formula

    ||v|| = sqrt(x²+y²)

Example

    v = [3,4]

    Length = 5

This comes directly from the Pythagorean theorem.

------------------------------------------------------------------------

# 5. Unit Vectors

A unit vector has length exactly 1.

Normalization removes the effect of vector length so we compare only
direction.

Many embedding models output normalized vectors.

------------------------------------------------------------------------

# 6. Distance vs Similarity

Distance answers:

"How far apart?"

Similarity answers:

"How alike?"

Lower distance usually means higher similarity.

Higher similarity score means more similar.

------------------------------------------------------------------------

# 7. Dot Product

The dot product multiplies corresponding numbers and adds them.

Example

    A = [2,3]

    B = [4,5]

    2×4 + 3×5

    =23

Large dot product usually indicates vectors point in similar directions.

------------------------------------------------------------------------

# 8. Cosine Similarity

The most common similarity metric.

Formula

    (A·B)/(||A|| ||B||)

Range

    1    identical direction

    0    unrelated

    -1   opposite direction

Cosine similarity ignores vector length and compares direction.

This is why it is widely used for embeddings.

------------------------------------------------------------------------

# 9. Euclidean Distance

Straight-line distance.

Formula

    sqrt((x2-x1)^2+(y2-y1)^2)

Smaller distance means more similar.

------------------------------------------------------------------------

# 10. Manhattan Distance

Imagine driving on city streets.

Instead of straight lines you move along roads.

    |x2-x1| + |y2-y1|

Useful in some machine-learning algorithms.

------------------------------------------------------------------------

# 11. Angles Between Vectors

Cosine similarity is really measuring the angle.

Small angle

→ similar meaning

Large angle

→ different meaning

------------------------------------------------------------------------

# 12. High-Dimensional Spaces

Embeddings are not 2D.

Typical dimensions:

-   384
-   768
-   1024
-   1536
-   3072

Humans cannot visualize these spaces, but the mathematics works exactly
the same.

------------------------------------------------------------------------

# 13. Embeddings

Embedding = numerical representation of meaning.

Example

    Dog

    ↓

    [0.23,-0.81,...]

Similar words appear close together.

------------------------------------------------------------------------

# 14. Why Embedding Models Are Needed

Random numbers have no meaning.

A neural network learns representations where similar concepts are
nearby.

For example

Dog

Cat

Wolf

become neighbors because they frequently appear in similar contexts
during training.

------------------------------------------------------------------------

# 15. Nearest Neighbors

Given a query vector, compute similarity against stored vectors.

Sort them.

Return the closest ones.

Those are the nearest neighbors.

------------------------------------------------------------------------

# 16. Ranking (Top-K)

**Rank** means the position after sorting by similarity.

Example

  Rank   Document             Score
  ------ ------------------ -------
  1      Python for AI         0.97
  2      Learning Python       0.93
  3      Machine Learning      0.89

Top-K means return only the first K results.

Top-5 returns five highest-ranked vectors.

------------------------------------------------------------------------

# 17. Exact vs Approximate Search

Exact Search

Compare against every vector.

Very accurate.

Slow for billions of vectors.

Approximate Search (ANN)

Search intelligently without checking every vector.

Nearly identical results.

Much faster.

------------------------------------------------------------------------

# 18. Precision, Recall, and Recall@K

Precision

How many returned documents were actually relevant?

Recall

How many relevant documents were found?

Recall@10

Among the top 10 returned results, how many relevant ones were
retrieved?

These metrics evaluate search quality.

------------------------------------------------------------------------

# 19. Curse of Dimensionality

As dimensions increase,

everything starts looking equally far away.

This makes indexing difficult.

Modern ANN algorithms like HNSW overcome much of this problem.

------------------------------------------------------------------------

# 20. Vector Databases

Responsibilities

-   Store embeddings
-   Build ANN indexes
-   Execute similarity search
-   Filter metadata
-   Return Top-K

Examples

-   FAISS
-   Milvus
-   Qdrant
-   Weaviate
-   Pinecone
-   Databricks Vector Search

------------------------------------------------------------------------

# 21. End-to-End Pipeline

    Documents
       │
    Chunking
       │
    Embedding Model
       │
    Embeddings
       │
    Vector Database
       │
    User Query
       │
    Embedding Model
       │
    Query Vector
       │
    Cosine Similarity
       │
    Rank Results
       │
    Top-K
       │
    LLM
       │
    Answer

------------------------------------------------------------------------

# 22. Terminology Glossary

  Term                 Meaning
  -------------------- -------------------------------------------------
  Scalar               Single number
  Vector               Ordered list of numbers
  Dimension            One value inside a vector
  Matrix               Collection of vectors
  Norm                 Length of a vector
  Normalize            Convert vector to unit length
  Dot Product          Measure of alignment
  Cosine Similarity    Angle-based similarity score
  Euclidean Distance   Straight-line distance
  Embedding            Numerical semantic representation
  Query Vector         Vector generated from user query
  Document Vector      Stored embedding of a document
  Nearest Neighbor     Closest vector
  ANN                  Approximate Nearest Neighbor
  HNSW                 Popular ANN indexing algorithm
  Index                Data structure for fast search
  Rank                 Position after sorting by similarity
  Score                Similarity value
  Top-K                Highest K ranked results
  Recall               Fraction of relevant results retrieved
  Precision            Fraction of retrieved results that are relevant

# Summary

Similarity search is built on a small set of mathematical ideas:

1.  Represent objects as vectors.
2.  Convert meaning into embeddings using an embedding model.
3.  Compare vectors using cosine similarity or distance metrics.
4.  Rank results by similarity score.
5.  Return the Top-K nearest neighbors.
6.  Use ANN indexes to make the search fast even for millions or
    billions of vectors.

Once these concepts are understood, advanced topics such as HNSW, FAISS,
vector databases, and Retrieval-Augmented Generation become much easier
to learn.

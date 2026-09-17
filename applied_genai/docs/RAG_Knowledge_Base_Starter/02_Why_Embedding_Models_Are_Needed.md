# Why is an Embedding Model Needed?

## The Problem

Humans understand meaning.

Computers only understand numbers.

If we simply assign IDs:

    Dog = 1
    Cat = 2
    Car = 3

There is no mathematical relationship between them.

## The Role of an Embedding Model

An embedding model is a neural network trained to transform data into
vectors where semantically similar items are placed near each other.

Instead of manually designing hundreds of language rules, the model
learns them from billions of examples.

Example:

    Dog -> [0.82, -0.15, ...]
    Cat -> [0.80, -0.18, ...]
    Car -> [-0.11, 0.94, ...]

Dog and Cat are close because the model learned they appear in similar
contexts.

## Why can't we generate embeddings ourselves?

You can create random vectors, but they won't preserve meaning.

The model has learned: - grammar - context - synonyms - relationships -
world knowledge - sentence meaning

through large-scale training.

## Training Intuition

During training, similar sentences are pushed closer together while
unrelated sentences are pushed farther apart (contrastive learning is a
common approach).

## Popular Embedding Models

-   OpenAI text-embedding models
-   BAAI BGE
-   E5
-   Sentence Transformers
-   Jina Embeddings
-   Cohere Embed

## Pipeline

    Document
       │
    Embedding Model
       │
    Vector
       │
    Vector Database

"""QdrantVectorStore -- the full vector DB lifecycle on top of a real Qdrant server.

Unlike faiss_vector_db/store.py, this needs no separate JSON sidecar for text/metadata: Qdrant is a real
client-server vector database, so each point's `payload` (arbitrary JSON -- source, chunk_index, text,
...) is stored natively alongside its vector and comes back for free on every search/get. See
docs/RAG_Knowledge_Base_Starter/04_Vector_Databases.md, "What is stored alongside the vector".

Lifecycle:

    CREATE  -> create_collection()
    INSERT  -> add()
    READ    -> get(), search()
    UPDATE  -> update()   (a plain upsert under the same id -- Qdrant supports true in-place update,
                            unlike FAISS which needs remove+re-add)
    DELETE  -> delete(), delete_by_source()
    STATS   -> stats()

There is no explicit persist/load step: Qdrant durably stores everything server-side (in the
`qdrant_data` Docker volume) as each operation happens, the same way pgvector does and unlike the
in-process FAISS index which only exists on disk after an explicit save().
"""

from __future__ import annotations

import uuid
from typing import Any

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException

import config


def get_client() -> QdrantClient:
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    try:
        client.collection_exists(config.COLLECTION_NAME)  # cheapest call that forces a connection attempt
    except ResponseHandlingException as exc:
        raise RuntimeError(
            f"Could not reach Qdrant at {config.QDRANT_HOST}:{config.QDRANT_PORT}. "
            "Make sure `docker compose up -d` is running."
        ) from exc
    return client


class QdrantVectorStore:
    def __init__(self, client: QdrantClient, collection_name: str, dim: int):
        self.client = client
        self.collection_name = collection_name
        self.dim = dim

    # -- CREATE --------------------------------------------------------

    @classmethod
    def create_collection(
        cls, client: QdrantClient, collection_name: str, dim: int, recreate: bool = False
    ) -> "QdrantVectorStore":
        exists = client.collection_exists(collection_name)
        if exists and recreate:
            client.delete_collection(collection_name)
            exists = False
        if not exists:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            )
        return cls(client=client, collection_name=collection_name, dim=dim)

    # -- INSERT ----------------------------------------------------------

    def add(self, vectors: list[list[float]], payloads: list[dict[str, Any]]) -> list[str]:
        if len(vectors) != len(payloads):
            raise ValueError("vectors and payloads must be the same length")
        if not vectors:
            return []

        ids = [str(uuid.uuid4()) for _ in vectors]
        points = [
            models.PointStruct(id=point_id, vector=vector, payload=payload)
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)
        return ids

    # -- READ --------------------------------------------------------------

    def get(self, point_id: str) -> dict[str, Any] | None:
        records = self.client.retrieve(
            collection_name=self.collection_name, ids=[point_id], with_payload=True, with_vectors=True
        )
        if not records:
            return None
        record = records[0]
        return {"id": record.id, "vector": record.vector, **record.payload}

    def search(
        self, query_vector: list[float], top_k: int, source: str | None = None
    ) -> list[dict[str, Any]]:
        query_filter = None
        if source is not None:
            query_filter = models.Filter(
                must=[models.FieldCondition(key="source", match=models.MatchValue(value=source))]
            )
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        return [
            {"id": point.id, "similarity": point.score, **point.payload} for point in response.points
        ]

    # -- UPDATE --------------------------------------------------------------

    def update(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> bool:
        if self.get(point_id) is None:
            return False
        self.client.upsert(
            collection_name=self.collection_name,
            points=[models.PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return True

    # -- DELETE --------------------------------------------------------------

    def delete(self, ids: list[str]) -> int:
        if not ids:
            return 0
        before = self.stats()["points_count"]
        self.client.delete(
            collection_name=self.collection_name, points_selector=models.PointIdsList(points=ids)
        )
        after = self.stats()["points_count"]
        return before - after

    def delete_by_source(self, source: str) -> int:
        before = self.stats()["points_count"]
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="source", match=models.MatchValue(value=source))]
                )
            ),
        )
        after = self.stats()["points_count"]
        return before - after

    # -- STATS -----------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        info = self.client.get_collection(self.collection_name)
        return {
            "points_count": info.points_count,
            "dimension": self.dim,
            "metric": "cosine",
            "status": info.status,
        }

    def __len__(self) -> int:
        return self.stats()["points_count"]

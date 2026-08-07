"""Shared semantic (embedding-based) search over Mongo collections that carry
a stored `embedding` field. Originally lived inline in terminology_search.py;
pulled out so /ConceptMap/$translate's ambiguity-ranking feature can reuse
the exact same cosine-similarity logic instead of duplicating it.
"""

import math
from dataclasses import dataclass

from app.db import mongo
from app.gemini.embedding import call_gemini_embedding_api


@dataclass
class SimilarityResult:
    document: dict
    similarity: float


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


async def semantic_search_local(
    query_embedding: list[float],
    limit: int,
    threshold: float,
    collection_name: str,
    database_name: str,
) -> list[SimilarityResult]:
    client = await mongo.get_instance()
    db = client.get_database_by_name(database_name)
    collection = db[collection_name]

    cursor = collection.find({"embedding": {"$exists": True, "$ne": []}})
    candidates: list[SimilarityResult] = []

    async for doc in cursor:
        embedding_array = doc.get("embedding")
        if not embedding_array:
            continue

        embedding_vec = [float(v) for v in embedding_array]
        if len(embedding_vec) != len(query_embedding):
            continue

        similarity = cosine_similarity(query_embedding, embedding_vec)
        if similarity >= threshold:
            candidates.append(SimilarityResult(document=doc, similarity=similarity))

    candidates.sort(key=lambda r: r.similarity, reverse=True)
    return candidates[:limit]


async def semantic_search_by_text(
    api_key: str,
    query_text: str,
    limit: int,
    threshold: float,
    collection_name: str,
    database_name: str,
) -> list[SimilarityResult]:
    """Convenience wrapper: embed query_text via Gemini, then search."""
    query_embedding = await call_gemini_embedding_api(api_key, query_text)
    return await semantic_search_local(query_embedding, limit, threshold, collection_name, database_name)

"""Generate Gemini embeddings for TM2-only ICD-11 entities (~709 of them),
not the full 36,941-entity collection. This is deliberately scoped: the
ambiguity-ranking feature in /ConceptMap/$translate only ever needs to
compare a NAMASTE term against TM2 candidates, so there's no reason to pay
for (or rate-limit against) embedding the entire ICD-11 dataset.

Requires GEMINI_KEY in backend/.env (free key: aistudio.google.com/apikey).

Usage:
    python scripts/generate_tm2_embeddings.py
"""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app import config  # noqa: E402
from app.db import mongo  # noqa: E402
from app.gemini.embedding import call_gemini_embedding_api  # noqa: E402


async def main() -> None:
    if not config.GEMINI_KEY:
        print("GEMINI_KEY not set in .env -- get a free key at https://aistudio.google.com/apikey")
        return

    client = await mongo.get_instance()
    db = client.get_database_by_name("icd11_database")
    collection = db["icd11_entities"]

    cursor = collection.find({"title": {"$regex": r"\(TM2\)"}})
    docs = [doc async for doc in cursor]
    print(f"Found {len(docs)} TM2 entities to embed")

    semaphore = asyncio.Semaphore(10)
    processed = 0
    skipped = 0
    failed = 0

    async def process(doc: dict) -> None:
        nonlocal processed, skipped, failed
        async with semaphore:
            if doc.get("embedding"):
                skipped += 1
                return

            text = f"{doc.get('title', '')} {doc.get('definition') or ''} {doc.get('code') or ''}".strip()
            if not text:
                skipped += 1
                return

            try:
                embedding = await call_gemini_embedding_api(config.GEMINI_KEY, text)
            except Exception as e:
                print(f"  failed to embed {doc.get('code')}: {e}")
                failed += 1
                return

            await collection.update_one({"_id": doc["_id"]}, {"$set": {"embedding": embedding}})
            processed += 1
            if processed % 100 == 0:
                print(f"  ...{processed} embedded so far")

    await asyncio.gather(*(process(doc) for doc in docs))

    print(f"Done. Embedded: {processed}, already had embedding: {skipped}, failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())

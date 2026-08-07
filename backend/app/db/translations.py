from datetime import datetime, timezone
from typing import Optional

from app.db import mongo

COLLECTION_NAME = "translations"

SUPPORTED_LANGUAGES = {
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "gu": "Gujarati",
    "te": "Telugu",
}


async def _collection():
    client = await mongo.get_instance()
    return client.database[COLLECTION_NAME]


async def ensure_indexes() -> None:
    collection = await _collection()
    await collection.create_index("cache_key", unique=True)


def make_cache_key(source: str, record_id: str, field: str, language: str) -> str:
    return f"{source}:{record_id}:{field}:{language}"


async def get_cached(cache_key: str) -> Optional[str]:
    collection = await _collection()
    doc = await collection.find_one({"cache_key": cache_key})
    return doc["translated_text"] if doc else None


async def store(cache_key: str, source_text: str, translated_text: str, language: str) -> None:
    collection = await _collection()
    await collection.update_one(
        {"cache_key": cache_key},
        {
            "$set": {
                "cache_key": cache_key,
                "source_text": source_text,
                "translated_text": translated_text,
                "language": language,
                "translated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )

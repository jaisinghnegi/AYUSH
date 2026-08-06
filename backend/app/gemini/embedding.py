import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Optional

import httpx
from fastapi.responses import JSONResponse

from app import config
from app.codecs.icd import IcdCode, IcdCodec
from app.codecs.namaste import NamasteCode, NamasteCodec
from app.db import mongo

GEMINI_EMBEDDING_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "text-embedding-004:embedContent"
)


async def call_gemini_embedding_api(api_key: str, input_text: str) -> list[float]:
    """Call Gemini embedding API with the given api_key and input text, return embedding vector."""
    request_body = {
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": input_text}]},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GEMINI_EMBEDDING_URL,
            headers={"x-goog-api-key": api_key},
            json=request_body,
            timeout=30.0,
        )
        resp.raise_for_status()
        json_resp = resp.json()

    embedding_array = json_resp.get("embedding", {}).get("values")
    if embedding_array is None:
        raise ValueError("Invalid embedding response from Gemini")

    return [float(v) for v in embedding_array]


async def _has_embeddings_icd(code_id: str) -> bool:
    """Check if a document already has embeddings in MongoDB."""
    client = await mongo.get_instance()
    db = client.get_database_by_name("icd11_database")
    collection = db["icd11_entities"]

    count = await collection.count_documents(
        {"id": code_id, "embedding": {"$exists": True, "$ne": []}}
    )
    return count > 0


async def _find_and_check_namaste_embedding(code: NamasteCode) -> tuple[bool, Optional[dict]]:
    """Find NAMASTE document by matching against the NamasteCode data."""
    client = await mongo.get_instance()
    db = client.get_database_by_name("ayurveda_db")
    collection = db["namc_codes"]

    document = await collection.find_one({"field_1": code.namc_id})
    if document is not None:
        has_embedding = bool(document.get("embedding"))
        print(f"🔍 Found NAMASTE code {code.namc_id} using field_1 filter")
        return has_embedding, document

    possible_filters = [
        {"vyAdhi-viniScayaH": code.namc_term},
        {"vyādhi-viniścayaḥ": code.namc_term},
        {"व्याधि-विनिश्चयः": code.namc_term},
    ]

    for term_filter in possible_filters:
        document = await collection.find_one(term_filter)
        if document is not None:
            has_embedding = bool(document.get("embedding"))
            print(f"🔍 Found NAMASTE code {code.namc_id} using term filter: {term_filter}")
            return has_embedding, document

    return False, None


def _extract_namaste_text_from_document(document: dict, fallback_term: str) -> str:
    """Extract text content from MongoDB NAMASTE document for embedding."""
    text_parts = []

    for field in ("vyAdhi-viniScayaH", "vyādhi-viniścayaḥ", "व्याधि-विनिश्चयः", "AYU"):
        value = document.get(field)
        if value:
            text_parts.append(str(value))

    if not text_parts:
        text_parts.append(fallback_term)

    return " ".join(text_parts)


class ProcessResult(Enum):
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()
    ALREADY_EXISTS = auto()


async def _process_icd_code(
    code: IcdCode, api_key: str, semaphore: asyncio.Semaphore
) -> ProcessResult:
    async with semaphore:
        try:
            if await _has_embeddings_icd(code.id):
                return ProcessResult.ALREADY_EXISTS
        except Exception as e:
            print(f"⚠️  Failed to check embedding status for ICD code {code.id}: {e}")

        combined_text = f"{code.title} {code.definition or ''} {code.code}"
        if not combined_text.strip():
            return ProcessResult.SKIPPED

        try:
            embedding = await call_gemini_embedding_api(api_key, combined_text)
        except Exception as e:
            print(f"❌ Failed to generate embedding for ICD code {code.id}: {e}")
            return ProcessResult.FAILED

        try:
            client = await mongo.get_instance()
            db = client.get_database_by_name("icd11_database")
            collection = db["icd11_entities"]

            result = await collection.update_one(
                {"id": code.id}, {"$set": {"embedding": embedding}}, upsert=False
            )
            if result.modified_count > 0:
                print(f"✅ Processed ICD code: {code.id} (embedding size: {len(embedding)})")
                return ProcessResult.SUCCESS
            return ProcessResult.ALREADY_EXISTS
        except Exception as e:
            print(f"❌ Failed to update ICD code {code.id} in MongoDB: {e}")
            return ProcessResult.FAILED


async def _process_namaste_code(
    code: NamasteCode, api_key: str, semaphore: asyncio.Semaphore
) -> ProcessResult:
    async with semaphore:
        try:
            has_embedding, document = await _find_and_check_namaste_embedding(code)
        except Exception as e:
            print(f"❌ Error checking NAMASTE code {code.namc_id}: {e}")
            return ProcessResult.FAILED

        if document is None:
            print(f"❌ NAMASTE code {code.namc_id} - '{code.namc_term}' not found in database")
            return ProcessResult.FAILED

        if has_embedding:
            return ProcessResult.ALREADY_EXISTS

        combined_text = _extract_namaste_text_from_document(document, code.namc_term)
        if not combined_text.strip():
            return ProcessResult.SKIPPED

        try:
            embedding = await call_gemini_embedding_api(api_key, combined_text)
        except Exception as e:
            print(f"❌ Failed to generate embedding for NAMASTE code {code.namc_id}: {e}")
            return ProcessResult.FAILED

        try:
            client = await mongo.get_instance()
            db = client.get_database_by_name("ayurveda_db")
            collection = db["namc_codes"]

            result = await collection.update_one(
                {"_id": document["_id"]}, {"$set": {"embedding": embedding}}, upsert=False
            )
            if result.modified_count > 0:
                preview = combined_text[:50]
                print(
                    f"✅ Processed NAMASTE code: {code.namc_id} - {preview} "
                    f"(embedding size: {len(embedding)})"
                )
                return ProcessResult.SUCCESS
            return ProcessResult.ALREADY_EXISTS
        except Exception as e:
            print(f"❌ Failed to update NAMASTE code {code.namc_id} in MongoDB: {e}")
            return ProcessResult.FAILED


@dataclass
class _Tally:
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    existing: int = 0

    def add(self, result: ProcessResult) -> None:
        if result == ProcessResult.SUCCESS:
            self.processed += 1
        elif result == ProcessResult.SKIPPED:
            self.skipped += 1
        elif result == ProcessResult.FAILED:
            self.failed += 1
        elif result == ProcessResult.ALREADY_EXISTS:
            self.existing += 1

    @property
    def total(self) -> int:
        return self.processed + self.skipped + self.failed + self.existing


async def generate_and_store_embeddings() -> None:
    """Generate embeddings for all ICD and NAMASTE codes and update MongoDB documents."""
    print("🚀 Starting embedding generation process with 100 parallel requests...")

    api_key = config.GEMINI_KEY
    if not api_key:
        raise RuntimeError("GEMINI_KEY not found in environment variables")

    print("✅ Gemini API key loaded successfully")

    icd_codec = IcdCodec()
    namaste_codec = NamasteCodec()
    semaphore = asyncio.Semaphore(100)

    print("📊 Fetching ICD codes from database...")
    try:
        icd_codes = await icd_codec.get_all_codes(None)
        print(f"✅ Successfully fetched {len(icd_codes)} ICD codes")
    except Exception as e:
        print(f"❌ Failed to fetch ICD codes: {e}")
        raise RuntimeError(f"Failed to fetch ICD codes: {e}") from e

    print("🔄 Processing ICD codes for embeddings (up to 100 parallel requests)...")
    icd_tally = _Tally()
    icd_results = await asyncio.gather(
        *(_process_icd_code(code, api_key, semaphore) for code in icd_codes),
        return_exceptions=True,
    )
    for result in icd_results:
        if isinstance(result, Exception):
            print(f"❌ Task error: {result}")
            icd_tally.add(ProcessResult.FAILED)
        else:
            icd_tally.add(result)

    print(
        f"📈 ICD Summary: {icd_tally.processed} processed, {icd_tally.skipped} skipped, "
        f"{icd_tally.existing} existing, {icd_tally.failed} failed"
    )

    print("📊 Fetching NAMASTE codes from database...")
    try:
        namaste_codes = await namaste_codec.get_all_codes(None)
        print(f"✅ Successfully fetched {len(namaste_codes)} NAMASTE codes")
    except Exception as e:
        print(f"❌ Failed to fetch NAMASTE codes: {e}")
        raise RuntimeError(f"Failed to fetch NAMASTE codes: {e}") from e

    print("🔄 Processing NAMASTE codes for embeddings (up to 100 parallel requests)...")
    namaste_tally = _Tally()
    namaste_results = await asyncio.gather(
        *(_process_namaste_code(code, api_key, semaphore) for code in namaste_codes),
        return_exceptions=True,
    )
    for result in namaste_results:
        if isinstance(result, Exception):
            print(f"❌ Task error: {result}")
            namaste_tally.add(ProcessResult.FAILED)
        else:
            namaste_tally.add(result)

    print(
        f"📈 NAMASTE Summary: {namaste_tally.processed} processed, {namaste_tally.skipped} skipped, "
        f"{namaste_tally.existing} existing, {namaste_tally.failed} failed"
    )

    total_processed = icd_tally.processed + namaste_tally.processed
    total_existing = icd_tally.existing + namaste_tally.existing
    total_failed = icd_tally.failed + namaste_tally.failed
    total_codes = icd_tally.total + namaste_tally.total

    print("🎉 Parallel embedding generation completed!")
    print("📊 Final Summary:")
    print(f"   • Total codes: {total_codes}")
    print(f"   • Successfully processed: {total_processed}")
    print(f"   • Already had embeddings: {total_existing}")
    print(f"   • Failed: {total_failed}")
    if total_codes:
        coverage = ((total_processed + total_existing) / total_codes) * 100
        print(f"   • Total coverage: {coverage:.2f}%")


async def generate_embeddings_handler() -> JSONResponse:
    """FastAPI handler to trigger embedding generation via API call."""
    print("🌐 Parallel embedding generation endpoint called")

    try:
        await generate_and_store_embeddings()
        print("✅ Parallel embedding generation completed successfully")
        return JSONResponse(
            {
                "status": "success",
                "message": "Gemini embeddings generated and stored in MongoDB with 100 parallel requests",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as err:
        print(f"❌ Parallel embedding generation failed: {err!r}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Failed to generate embeddings: {err}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

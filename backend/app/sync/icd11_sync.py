"""Live WHO ICD-11 MMS sync -- pulls current data from the WHO ICD-11 API and
stores it in MongoDB, with an automatic fallback to the bundled CSV snapshot
when credentials are missing or the live pull fails.

This is the shared implementation used by both:
  - scripts/fetch_icd11_live.py (manual CLI run)
  - POST /services/sync/icd11-live (callable from the running app, e.g. by
    an admin, without having to shell into the server)

Requires WHO_ICD_CLIENT_ID / WHO_ICD_CLIENT_SECRET in the environment --
see https://icd.who.int/icdapi for free registration.
"""

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from pymongo import MongoClient, UpdateOne

from app import config

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
API_BASE = "https://id.who.int"
HEADERS = {
    "Accept": "application/json",
    "API-Version": "v2",
    "Accept-Language": "en",
}

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_ICD_CSV = BACKEND_DIR / "csvs" / "ICD-11" / "icd11_mms.csv"

# In-memory status, good enough for a single-process dev/demo deployment --
# lets an admin poll progress without needing a separate job queue.
sync_status: dict = {
    "state": "idle",  # idle | running | completed | failed
    "started_at": None,
    "finished_at": None,
    "entities_fetched": 0,
    "source": None,  # "live" | "csv_fallback"
    "error": None,
}


class TokenManager:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self, client: httpx.AsyncClient) -> str:
        async with self._lock:
            if self._token and time.monotonic() < self._expires_at:
                return self._token

            resp = await client.post(
                TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "icdapi_access",
                    "grant_type": "client_credentials",
                },
            )
            resp.raise_for_status()
            payload = resp.json()

            self._token = payload["access_token"]
            expires_in = int(payload.get("expires_in", 3600))
            self._expires_at = time.monotonic() + max(expires_in - 120, 60)
            return self._token


def extract_entity_info(data: dict, parent_id: str) -> dict:
    def scalar(field):
        value = data.get(field)
        if isinstance(value, dict):
            return value.get("@value", "")
        if isinstance(value, str):
            return value
        return ""

    synonyms = data.get("synonym", []) or []
    synonym_labels = []
    for synonym in synonyms:
        if isinstance(synonym, dict) and "label" in synonym:
            label = synonym["label"]
            if isinstance(label, dict):
                synonym_labels.append(label.get("@value", ""))
            elif isinstance(label, str):
                synonym_labels.append(label)

    return {
        "id": data.get("@id", ""),
        "code": data.get("code", ""),
        "title": scalar("title"),
        "definition": scalar("definition"),
        "parent": parent_id,
        "browserUrl": data.get("browserUrl", ""),
        "codingNote": scalar("codingNote"),
        "synonyms": "; ".join(synonym_labels),
        "exclusions": "",
        "inclusions": "",
        "isLeaf": str(len(data.get("child", [])) == 0),
    }


async def fetch_json(client: httpx.AsyncClient, tokens: TokenManager, url: str, retries: int = 3) -> Optional[dict]:
    for attempt in range(retries):
        token = await tokens.get_token(client)
        try:
            resp = await client.get(url, headers={**HEADERS, "Authorization": f"Bearer {token}"})
            if resp.status_code == 401:
                tokens._expires_at = 0.0
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            print(f"  request failed (attempt {attempt + 1}/{retries}) for {url}: {e}")
            await asyncio.sleep(1.5 * (attempt + 1))
    return None


async def fetch_entity_recursive(
    client: httpx.AsyncClient,
    tokens: TokenManager,
    semaphore: asyncio.Semaphore,
    entity_uri: str,
    parent_id: str,
    collected: list[dict],
    seen: set[str],
    counter: dict,
) -> None:
    if entity_uri in seen:
        return
    seen.add(entity_uri)

    async with semaphore:
        data = await fetch_json(client, tokens, entity_uri)

    if not data:
        return

    entity = extract_entity_info(data, parent_id)
    collected.append(entity)
    counter["count"] += 1
    sync_status["entities_fetched"] = counter["count"]
    if counter["count"] % 200 == 0:
        print(f"  ...fetched {counter['count']} entities so far")

    children = data.get("child", []) or []
    if children:
        await asyncio.gather(
            *(
                fetch_entity_recursive(
                    client, tokens, semaphore, child_uri, entity["id"], collected, seen, counter
                )
                for child_uri in children
            )
        )


async def scrape_mms(release: str, concurrency: int, client_id: str, client_secret: str) -> list[dict]:
    tokens = TokenManager(client_id, client_secret)
    mms_url = f"{API_BASE}/icd/release/11/{release}/mms"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        print("Authenticating with WHO ICD-11 API...")
        await tokens.get_token(client)
        print("Authenticated.")

        root_data = await fetch_json(client, tokens, mms_url)
        if not root_data:
            raise RuntimeError(f"Failed to fetch MMS root for release {release}")

        children = root_data.get("child", []) or []
        print(f"Found {len(children)} top-level MMS chapters")

        semaphore = asyncio.Semaphore(concurrency)
        collected: list[dict] = []
        seen: set[str] = set()
        counter = {"count": 0}

        await asyncio.gather(
            *(
                fetch_entity_recursive(
                    client, tokens, semaphore, chapter_uri, "", collected, seen, counter
                )
                for chapter_uri in children
            )
        )

        return collected


def store_entities(entities: list[dict]) -> dict:
    if not entities:
        return {"inserted": 0, "modified": 0, "total": 0}

    client = MongoClient(config.MONGODB_URI)
    collection = client["icd11_database"]["icd11_entities"]
    collection.create_index("id", unique=True)

    batch_size = 2000
    upserted = 0
    modified = 0
    for start in range(0, len(entities), batch_size):
        batch = entities[start:start + batch_size]
        operations = [UpdateOne({"id": e["id"]}, {"$set": e}, upsert=True) for e in batch if e.get("id")]
        if not operations:
            continue
        result = collection.bulk_write(operations, ordered=False)
        upserted += result.upserted_count
        modified += result.modified_count

    total = collection.count_documents({})
    client.close()
    return {"inserted": upserted, "modified": modified, "total": total}


def import_csv_fallback(csv_path: Path = DEFAULT_ICD_CSV) -> dict:
    import csv

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    fields = [
        "id", "code", "title", "definition", "parent",
        "browserUrl", "codingNote", "synonyms", "exclusions",
        "inclusions", "isLeaf",
    ]
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            if not raw_row.get("id"):
                continue
            row = {field: (raw_row.get(field) or "").strip() or None for field in fields}
            row["id"] = raw_row["id"].strip()
            rows.append(row)

    return store_entities(rows)


async def run_sync(release: str = "2025-01", concurrency: int = 8) -> dict:
    """Run the full live-sync-with-fallback flow. Safe to call from an API
    endpoint via BackgroundTasks -- updates module-level `sync_status` as it
    progresses so it can be polled."""
    sync_status.update(
        state="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        entities_fetched=0,
        source=None,
        error=None,
    )

    client_id = config.WHO_ICD_CLIENT_ID
    client_secret = config.WHO_ICD_CLIENT_SECRET

    try:
        if not client_id or not client_secret:
            result = import_csv_fallback()
            sync_status.update(
                state="completed",
                finished_at=datetime.now(timezone.utc).isoformat(),
                source="csv_fallback",
                error="WHO_ICD_CLIENT_ID / WHO_ICD_CLIENT_SECRET not set",
            )
            return {"source": "csv_fallback", **result}

        entities = await scrape_mms(release, concurrency, client_id, client_secret)
        if not entities:
            result = import_csv_fallback()
            sync_status.update(
                state="completed",
                finished_at=datetime.now(timezone.utc).isoformat(),
                source="csv_fallback",
                error="live fetch returned no entities",
            )
            return {"source": "csv_fallback", **result}

        result = store_entities(entities)
        sync_status.update(
            state="completed",
            finished_at=datetime.now(timezone.utc).isoformat(),
            source="live",
            entities_fetched=len(entities),
        )
        return {"source": "live", **result}

    except Exception as e:
        try:
            result = import_csv_fallback()
            sync_status.update(
                state="completed",
                finished_at=datetime.now(timezone.utc).isoformat(),
                source="csv_fallback",
                error=f"live fetch failed ({e}), fell back to CSV",
            )
            return {"source": "csv_fallback", "error": str(e), **result}
        except Exception as fallback_error:
            sync_status.update(
                state="failed",
                finished_at=datetime.now(timezone.utc).isoformat(),
                error=f"live fetch failed ({e}); csv fallback also failed ({fallback_error})",
            )
            raise

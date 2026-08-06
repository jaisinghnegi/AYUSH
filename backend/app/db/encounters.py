from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.db import mongo

COLLECTION_NAME = "encounters"


@dataclass
class Encounter:
    id: str
    user_id: str
    patient: dict
    diagnoses: list[dict]
    created_at: datetime

    @staticmethod
    def from_document(doc: dict) -> "Encounter":
        return Encounter(
            id=str(doc["_id"]),
            user_id=str(doc["userId"]),
            patient=doc.get("patient", {}),
            diagnoses=doc.get("diagnoses", []),
            created_at=doc["createdAt"],
        )

    def to_response(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "patient": self.patient,
            "diagnoses": self.diagnoses,
            "createdAt": self.created_at.isoformat(),
        }


async def _collection():
    client = await mongo.get_instance()
    return client.database[COLLECTION_NAME]


async def ensure_indexes() -> None:
    collection = await _collection()
    await collection.create_index("userId")
    await collection.create_index("createdAt")


async def create_encounter(user_id: str, patient: dict, diagnoses: list[dict]) -> Encounter:
    collection = await _collection()
    doc = {
        "userId": ObjectId(user_id),
        "patient": patient,
        "diagnoses": diagnoses,
        "createdAt": datetime.now(timezone.utc),
    }
    result = await collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return Encounter.from_document(doc)


async def list_encounters_by_user(user_id: str, limit: int = 50) -> list[Encounter]:
    collection = await _collection()
    cursor = collection.find({"userId": ObjectId(user_id)}).sort("createdAt", -1).limit(limit)
    return [Encounter.from_document(doc) async for doc in cursor]


async def get_encounter(encounter_id: str, user_id: str) -> Optional[Encounter]:
    """Fetch an encounter, scoped to the requesting user (no cross-user access)."""
    collection = await _collection()
    try:
        doc = await collection.find_one(
            {"_id": ObjectId(encounter_id), "userId": ObjectId(user_id)}
        )
    except Exception:
        return None
    return Encounter.from_document(doc) if doc else None

import secrets
from datetime import datetime, timedelta, timezone

from app.db import mongo

COLLECTION_NAME = "otp_codes"

OTP_TTL_SECONDS = 5 * 60  # codes are valid for 5 minutes


async def _collection():
    client = await mongo.get_instance()
    return client.database[COLLECTION_NAME]


async def ensure_indexes() -> None:
    collection = await _collection()
    # TTL index: MongoDB automatically deletes documents once expires_at is
    # in the past -- no manual cleanup job needed.
    await collection.create_index("expires_at", expireAfterSeconds=0)
    await collection.create_index([("identifier", 1), ("purpose", 1)])


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def create_otp(identifier: str, purpose: str) -> str:
    """Generate and store a new OTP code, invalidating any previous unused
    code for the same identifier/purpose."""
    collection = await _collection()
    identifier = identifier.strip().lower()

    # Invalidate any still-live codes for this identifier/purpose so only
    # the most recently requested code is valid.
    await collection.delete_many({"identifier": identifier, "purpose": purpose, "consumed": False})

    code = _generate_code()
    now = datetime.now(timezone.utc)
    await collection.insert_one(
        {
            "identifier": identifier,
            "purpose": purpose,
            "code": code,
            "created_at": now,
            "expires_at": now + timedelta(seconds=OTP_TTL_SECONDS),
            "consumed": False,
        }
    )
    return code


async def verify_otp(identifier: str, purpose: str, code: str) -> bool:
    collection = await _collection()
    identifier = identifier.strip().lower()
    now = datetime.now(timezone.utc)

    result = await collection.update_one(
        {
            "identifier": identifier,
            "purpose": purpose,
            "code": code,
            "consumed": False,
            "expires_at": {"$gt": now},
        },
        {"$set": {"consumed": True}},
    )
    return result.modified_count > 0

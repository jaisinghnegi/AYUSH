from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.db import mongo

COLLECTION_NAME = "audit_log"


async def log_lookup(
    operation: str,
    system: str,
    code: str,
    found: bool,
    result_code: Optional[str] = None,
    result_display: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Record a $translate/$lookup call for audit-ready traceability.

    user_id is null for unauthenticated calls (these endpoints stay public)
    and set to the real user's _id once a valid Bearer token is presented.

    Best-effort: a logging failure (e.g. Mongo briefly unavailable) must never
    break the actual API response, so failures here are swallowed.
    """
    try:
        client = await mongo.get_instance()
        collection = client.database[COLLECTION_NAME]
        await collection.insert_one(
            {
                "timestamp": datetime.now(timezone.utc),
                "operation": operation,
                "system": system,
                "code": code,
                "found": found,
                "result_code": result_code,
                "result_display": result_display,
                "userId": ObjectId(user_id) if user_id else None,
            }
        )
    except Exception as e:
        print(f"audit log write failed (non-fatal): {e}")

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from bson import ObjectId

from app.db import mongo

COLLECTION_NAME = "users"


@dataclass
class User:
    id: str
    email: str
    name: str
    role: str
    phone: Optional[str]
    password_hash: Optional[str]
    created_at: datetime
    last_login_at: Optional[datetime]

    @staticmethod
    def from_document(doc: dict) -> "User":
        return User(
            id=str(doc["_id"]),
            email=doc["email"],
            name=doc.get("name", ""),
            role=doc.get("role", "doctor"),
            phone=doc.get("phone"),
            password_hash=doc.get("passwordHash"),
            created_at=doc["createdAt"],
            last_login_at=doc.get("lastLoginAt"),
        )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash -- treat as non-matching rather than raising.
        return False


async def _collection():
    client = await mongo.get_instance()
    return client.database[COLLECTION_NAME]


async def ensure_indexes() -> None:
    collection = await _collection()
    await collection.create_index("email", unique=True)


async def get_user_by_email(email: str) -> Optional[User]:
    collection = await _collection()
    doc = await collection.find_one({"email": email.strip().lower()})
    return User.from_document(doc) if doc else None


async def get_user_by_id(user_id: str) -> Optional[User]:
    collection = await _collection()
    try:
        doc = await collection.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
    return User.from_document(doc) if doc else None


async def create_user(
    email: str,
    name: str,
    password: Optional[str] = None,
    phone: Optional[str] = None,
    role: str = "doctor",
) -> User:
    collection = await _collection()
    doc = {
        "email": email.strip().lower(),
        "name": name,
        "role": role,
        "phone": phone,
        "passwordHash": hash_password(password) if password else None,
        "createdAt": datetime.now(timezone.utc),
        "lastLoginAt": None,
    }
    result = await collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return User.from_document(doc)


async def mark_logged_in(email: str) -> None:
    collection = await _collection()
    await collection.update_one(
        {"email": email.strip().lower()},
        {"$set": {"lastLoginAt": datetime.now(timezone.utc)}},
    )

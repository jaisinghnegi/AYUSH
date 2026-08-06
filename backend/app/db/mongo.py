import asyncio
from dataclasses import dataclass
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi

from app import config


@dataclass
class ConnectionStatus:
    connected: bool
    database_name: str
    server_info: Optional[str] = None
    error: Optional[str] = None


class MongoClientWrapper:
    def __init__(self, client: AsyncIOMotorClient, database: AsyncIOMotorDatabase):
        self.client = client
        self.database = database

    @staticmethod
    async def create() -> "MongoClientWrapper":
        uri = config.MONGODB_URI
        database_name = config.MONGODB_DATABASE

        print(f"🔗 Connecting to MongoDB: {uri}")
        print(f"📁 Using database: {database_name}")

        kwargs = {
            "server_api": ServerApi("1"),
            "appname": "FHIR Terminology Server",
        }

        if config.MONGODB_USERNAME and config.MONGODB_PASSWORD:
            print(f"🔐 Using authentication for user: {config.MONGODB_USERNAME}")
            kwargs["username"] = config.MONGODB_USERNAME
            kwargs["password"] = config.MONGODB_PASSWORD
            kwargs["authSource"] = config.MONGODB_AUTH_DB

        client = AsyncIOMotorClient(uri, **kwargs)
        database = client[database_name]

        print(f"✅ MongoDB client initialized for database: {database_name}")
        return MongoClientWrapper(client, database)

    def get_database_by_name(self, db_name: str) -> AsyncIOMotorDatabase:
        return self.client[db_name]

    async def health_check(self) -> ConnectionStatus:
        try:
            await self.client.admin.command("ping")
            try:
                info = await self.client.admin.command("buildInfo")
                version = info.get("version", "unknown")
                server_info = f"MongoDB {version}"
            except Exception:
                server_info = "MongoDB (version unknown)"

            return ConnectionStatus(
                connected=True,
                database_name=self.database.name,
                server_info=server_info,
            )
        except Exception as e:
            return ConnectionStatus(
                connected=False,
                database_name=self.database.name,
                error=str(e),
            )

    async def list_collections(self) -> list[str]:
        return await self.database.list_collection_names()


_mongo_client: Optional[MongoClientWrapper] = None
_mongo_lock = asyncio.Lock()


async def get_instance() -> MongoClientWrapper:
    global _mongo_client
    if _mongo_client is not None:
        return _mongo_client

    async with _mongo_lock:
        if _mongo_client is None:
            _mongo_client = await MongoClientWrapper.create()
        return _mongo_client


async def init_mongodb() -> None:
    await get_instance()


async def get_connection_status() -> ConnectionStatus:
    try:
        client = await get_instance()
        return await client.health_check()
    except Exception as e:
        return ConnectionStatus(connected=False, database_name="unknown", error=str(e))

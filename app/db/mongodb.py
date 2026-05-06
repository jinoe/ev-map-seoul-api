from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(
            settings.mongodb_connection_uri,
            serverSelectionTimeoutMS=10000,
        )
    return _client


def get_db() -> Database:
    return get_client()[settings.MONGODB_DB_NAME]


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None

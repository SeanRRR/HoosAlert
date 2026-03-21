# database.py - MongoDB CRUD + mock incident seeding
import json
import os
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

# Support both env names so local setups do not silently break.
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "hoos_alert")
INCIDENTS_COLLECTION = os.getenv("MONGO_INCIDENTS_COLLECTION", "incidents")

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]


def _find_default_mock_path() -> Path:
    """
    Locate backend/data/mock_incidents.json by walking upward from this file.
    """
    here = Path(__file__).resolve().parent
    for base in [here, *here.parents]:
        candidate = base / "data" / "mock_incidents.json"
        if candidate.exists():
            return candidate
    return here / "data" / "mock_incidents.json"


def load_mock_incidents(file_path: str | None = None) -> list[dict[str, Any]]:
    path = Path(file_path).expanduser().resolve() if file_path else _find_default_mock_path()
    if not path.exists():
        raise FileNotFoundError(f"Mock incident file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError("mock_incidents.json must be a JSON list")

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Item at index {idx} must be a JSON object")

    return records


async def save_incident(incident: dict[str, Any]) -> str:
    payload = dict(incident)
    if "id" in payload and payload["id"] is not None:
        payload["id"] = str(payload["id"])

    result = await db[INCIDENTS_COLLECTION].insert_one(payload)
    return str(result.inserted_id)


async def get_incidents(limit: int = 100) -> list[dict[str, Any]]:
    cursor = db[INCIDENTS_COLLECTION].find().limit(limit)
    return await cursor.to_list(length=limit)


async def seed_mock_incidents(file_path: str | None = None, clear_existing: bool = False) -> dict[str, Any]:
    records = load_mock_incidents(file_path)
    collection = db[INCIDENTS_COLLECTION]

    if clear_existing:
        await collection.delete_many({})

    inserted = 0
    updated = 0
    for record in records:
        payload = dict(record)
        record_id = payload.get("id")

        if record_id is None:
            await collection.insert_one(payload)
            inserted += 1
            continue

        payload["id"] = str(record_id)
        result = await collection.update_one(
            {"id": payload["id"]},
            {"$set": payload},
            upsert=True,
        )
        if result.matched_count > 0:
            updated += 1
        else:
            inserted += 1

    return {
        "collection": INCIDENTS_COLLECTION,
        "source_count": len(records),
        "inserted": inserted,
        "updated": updated,
        "cleared_existing": clear_existing,
    }

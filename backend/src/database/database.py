# database.py - MongoDB CRUD + mock incident seeding
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId
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


def _serialize_incident_record(record: dict[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    mongo_id = payload.pop("_id", None)

    record_id = payload.get("id")
    if record_id is None and mongo_id is not None:
        payload["id"] = str(mongo_id)
    elif record_id is not None:
        payload["id"] = str(record_id)

    return payload


async def get_incidents(limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 1000))
    cursor = db[INCIDENTS_COLLECTION].find().sort([("_id", -1)]).limit(safe_limit)
    records = await cursor.to_list(length=safe_limit)
    return [_serialize_incident_record(record) for record in records]


async def get_due_incidents_for_rescoring(now_iso: str, limit: int = 50) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 500))
    cursor = (
        db[INCIDENTS_COLLECTION]
        .find({"next_rescore_at": {"$lte": now_iso}})
        .sort([("next_rescore_at", 1)])
        .limit(safe_limit)
    )
    records = await cursor.to_list(length=safe_limit)
    return [_serialize_incident_record(record) for record in records]


def _incident_id_filter(incident_id: str) -> dict[str, Any]:
    filters: list[dict[str, Any]] = [{"id": str(incident_id)}]
    try:
        filters.insert(0, {"_id": ObjectId(str(incident_id))})
    except Exception:
        pass

    if len(filters) == 1:
        return filters[0]
    return {"$or": filters}


async def update_incident_fields(incident_id: str, fields: dict[str, Any]) -> bool:
    payload = dict(fields)
    payload.pop("id", None)
    payload.pop("_id", None)

    result = await db[INCIDENTS_COLLECTION].update_one(
        _incident_id_filter(incident_id),
        {"$set": payload},
    )
    return result.matched_count > 0


def _parse_incident_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None

    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _incident_timestamp(record: dict[str, Any]) -> datetime | None:
    created_at = _parse_incident_time(record.get("created_at"))
    if created_at:
        return created_at
    return _parse_incident_time(record.get("timestamp"))


async def get_incidents_for_scoring(hours: int = 24, limit: int = 100) -> list[dict[str, Any]]:
    """
    Retrieve recent incidents for LLM scoring context.
    """
    safe_limit = max(1, min(limit, 1000))
    safe_hours = max(1, min(hours, 24 * 30))

    cursor = db[INCIDENTS_COLLECTION].find().sort([("_id", -1)]).limit(safe_limit)
    records = await cursor.to_list(length=safe_limit)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=safe_hours)
    recent_records = []
    for record in records:
        timestamp = _incident_timestamp(record)
        if timestamp and timestamp >= cutoff:
            recent_records.append(record)

    if recent_records:
        return recent_records

    # If timestamps are missing/unparseable, still provide recent records as fallback context.
    return records


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

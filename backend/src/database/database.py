# database.py - MongoDB CRUD with motor
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.hoos_alert

async def save_incident(incident: dict):
    result = await db.incidents.insert_one(incident)
    return str(result.inserted_id)

async def get_incidents():
    return await db.incidents.find().to_list(length=100)

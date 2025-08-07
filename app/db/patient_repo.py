from pymongo import MongoClient
import os

db = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017")).medical_passport
col = db.resources
col.create_index("patient")

def get_bundle(pid: str):
    docs = list(col.find({"patient": pid}, {"_id": 0}))
    if not docs:
        return None
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": d} for d in docs],
    }

def upsert_resources(pid: str, bundle: dict):
    for entry in bundle.get("entry", []):
        r = entry.get("resource")
        if not r or "id" not in r:
            continue
        r["patient"] = pid
        col.replace_one({"patient": pid, "id": r["id"]}, r, upsert=True)

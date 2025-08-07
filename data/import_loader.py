# data/import_loader.py

import json
import glob
import pathlib
import re
from pymongo import MongoClient

# 1) Point to your raw FHIR files directory
root = pathlib.Path(__file__).parent / "raw_fhir"

# 2) Connect to MongoDB (adjust URI if needed)
client = MongoClient("mongodb://localhost:27017")
db = client.medical_passport

# 3) Prepare a “resources” collection and index
#    Each entry will be one FHIR resource document.
resources = db.resources
resources.create_index("patient")

# 4) A simple regex to pull the patient UUID out of the filename
pattern = re.compile(r"([0-9a-f-]{36})")

# 5) Iterate every JSON file
for filepath in glob.glob(str(root / "*.json")):
    pid_match = pattern.search(filepath)
    if not pid_match:
        print("Skipping (no PID in name):", filepath)
        continue
    patient_id = pid_match.group(1)

    # 6) Load the Bundle
    with open(filepath, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    entries = bundle.get("entry", [])
    if not entries:
        print(f"No entries for {patient_id}, skipping.")
        continue

    # 7) Insert each resource separately
    for entry in entries:
        resource = entry.get("resource")
        if not resource:
            continue

        # Tag it with patientId for easy lookup
        resource["patient"] = patient_id

        try:
            resources.insert_one(resource)
        except Exception as e:
            print("Failed to insert resource for", patient_id, ":", e)

    print(f"Imported {len(entries)} resources for patient {patient_id}")

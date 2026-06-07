# scratch/inspect_data.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'web_viewer'))
import stamp_db
import json

data = stamp_db.get_all_project_data("321654")
air_outlets = data.get("air_outlets", [])
print("Total air outlets:", len(air_outlets))

fields_count = 0
all_fields = set()
for item in air_outlets:
    if item.get("fields"):
        fields_count += 1
        all_fields.update(item["fields"].keys())

print("Air outlets with fields:", fields_count)
print("Unique fields found:", list(all_fields))
